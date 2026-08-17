"""
Runtime profile — per-capability model binding configuration.

A RuntimeProfile describes which provider and model to use for each
inference capability. It contains no credentials and is safe to
serialize for diagnostics.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import math
import re
from types import MappingProxyType
from typing import Mapping, Optional


_PROVIDER_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_SENSITIVE_OPTION_RE = re.compile(
    r"(^|_)(api_?key|authorization|cookie|password|secret|token)($|_)",
    re.IGNORECASE,
)
_PROVIDER_OPTION_ALLOWLIST: dict[str, frozenset[str]] = {
    "openai": frozenset(),
    "local": frozenset({
        "compute_type", "device", "n_ctx", "n_gpu_layers",
        "n_threads", "threads", "timeout_seconds",
    }),
    "ollama": frozenset({"concurrency", "timeout_seconds"}),
    "fake": frozenset(),
}
_OPENAI_MODEL_ALLOWLIST = frozenset({
    "gpt-4o",
    "gpt-4o-mini",
    "text-embedding-3-large",
    "text-embedding-3-small",
    "whisper-1",
})


def _freeze_option(value):
    """Validate and recursively freeze a provider option value."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Provider option numbers must be finite")
        return value
    if isinstance(value, Mapping):
        frozen = {}
        for key, nested in value.items():
            if not isinstance(key, str) or not key:
                raise ValueError("Provider option keys must be non-empty strings")
            if _SENSITIVE_OPTION_RE.search(key.replace("-", "_")):
                raise ValueError(f"Provider option '{key}' may contain credentials")
            frozen[key] = _freeze_option(nested)
        return MappingProxyType(frozen)
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_option(item) for item in value)
    raise ValueError(f"Unsupported provider option value type: {type(value).__name__}")


def _json_safe(value):
    if isinstance(value, Mapping):
        return {key: _json_safe(nested) for key, nested in sorted(value.items())}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


_PROVIDER_DEFAULT_MODELS: dict[str, dict[str, str]] = {
    "local": {
        "chat": "qwen3.5-4b-q4_k_m",
        "embedding": "nomic-embed-text-v1.5-q4_k_m",
        "transcription": "faster-whisper-small",
    },
    "ollama": {
        "chat": "llama3.2",
        "embedding": "nomic-embed-text",
    },
}


def _provider_default_model(provider: str, capability: str, openai_default: str) -> str:
    """Return the default model for a provider/capability, falling back to the OpenAI default."""
    provider_defaults = _PROVIDER_DEFAULT_MODELS.get(provider)
    if provider_defaults and capability in provider_defaults:
        if provider == "local":
            from arena.models.selection import active_model_for_capability

            model_capability = "speech" if capability == "transcription" else capability
            return active_model_for_capability(model_capability)
        return provider_defaults[capability]
    return openai_default


class Capability(str, Enum):
    """Inference capabilities that can be independently bound."""
    CHAT = "chat"
    OVERVIEW_CHAT = "overview_chat"
    EMBEDDING = "embedding"
    SPEECH = "speech"


@dataclass(frozen=True)
class ModelBinding:
    """Binds a capability to a specific provider and model."""
    provider: str
    model: str
    options: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.provider, str) or not _PROVIDER_RE.fullmatch(self.provider):
            raise ValueError("Provider names must use lowercase letters, numbers, '_' or '-'")
        if (
            not isinstance(self.model, str)
            or not self.model.strip()
            or len(self.model) > 256
            or any(ord(char) < 32 for char in self.model)
        ):
            raise ValueError("Model identifiers must be non-empty, bounded text without controls")
        if self.provider == "openai" and self.model not in _OPENAI_MODEL_ALLOWLIST:
            raise ValueError(f"Unsupported OpenAI model: '{self.model}'")
        if not isinstance(self.options, Mapping):
            raise ValueError("Provider options must be a mapping")

        allowed = _PROVIDER_OPTION_ALLOWLIST.get(self.provider, frozenset())
        normalized_options = {}
        for key, value in self.options.items():
            if not isinstance(key, str) or not key:
                raise ValueError("Provider option keys must be non-empty strings")
            normalized_key = key.lower().replace("-", "_")
            if _SENSITIVE_OPTION_RE.search(normalized_key):
                raise ValueError(f"Provider option '{key}' may contain credentials")
            if normalized_key not in allowed:
                raise ValueError(
                    f"Unsupported option '{key}' for provider '{self.provider}'"
                )
            normalized_options[normalized_key] = _freeze_option(value)

        object.__setattr__(self, "options", MappingProxyType(normalized_options))

    def safe_dict(self) -> dict:
        """Return a deterministic, credential-free serialization."""
        return {
            "provider": self.provider,
            "model": self.model,
            "options": _json_safe(self.options),
        }


@dataclass(frozen=True)
class RuntimeProfile:
    """Complete inference configuration for a pipeline run.

    Each capability is independently bindable. --provider sets all
    as shorthand; per-capability args override.
    """
    chat: ModelBinding
    overview_chat: Optional[ModelBinding] = None  # Falls back to chat
    embedding: ModelBinding = field(
        default_factory=lambda: ModelBinding(provider="openai", model="text-embedding-3-small")
    )
    transcription: ModelBinding = field(
        default_factory=lambda: ModelBinding(provider="openai", model="whisper-1")
    )

    def __post_init__(self):
        bindings = {
            "chat": self.chat,
            "embedding": self.embedding,
            "transcription": self.transcription,
        }
        if self.overview_chat is not None:
            bindings["overview_chat"] = self.overview_chat
        for capability, binding in bindings.items():
            if not isinstance(binding, ModelBinding):
                raise ValueError(f"{capability} must be a ModelBinding")

        openai_models = {
            "chat": {"gpt-4o", "gpt-4o-mini"},
            "overview_chat": {"gpt-4o", "gpt-4o-mini"},
            "embedding": {"text-embedding-3-small", "text-embedding-3-large"},
            "transcription": {"whisper-1"},
        }
        for capability, binding in bindings.items():
            allowed = openai_models.get(capability)
            if binding.provider == "openai" and binding.model not in allowed:
                raise ValueError(
                    f"Unsupported OpenAI {capability} model: '{binding.model}'"
                )

        # Providers that lack certain capabilities
        _unsupported = {"ollama": {"transcription"}}
        for capability, binding in bindings.items():
            blocked = _unsupported.get(binding.provider, set())
            if capability in blocked:
                raise ValueError(
                    f"Provider '{binding.provider}' does not support {capability}. "
                    f"Use --transcription-provider to select a different provider."
                )

    def binding_for(self, capability: Capability) -> ModelBinding:
        """Look up the binding for a capability."""
        if capability == Capability.CHAT:
            return self.chat
        if capability == Capability.OVERVIEW_CHAT:
            return self.overview_chat or self.chat
        if capability == Capability.EMBEDDING:
            return self.embedding
        if capability == Capability.SPEECH:
            return self.transcription
        raise ValueError(f"Unknown capability: {capability}")

    def safe_dict(self, capabilities: Optional[set[Capability]] = None) -> dict:
        """Serialize selected bindings without credentials."""
        selected = set(Capability) if capabilities is None else capabilities
        payload = {}
        for capability in sorted(selected, key=lambda item: item.value):
            payload[capability.value] = self.binding_for(capability).safe_dict()
        return payload

    def fingerprint(
        self,
        capabilities: Optional[set[Capability]] = None,
        *,
        namespace: str = "arena-inference-v1",
    ) -> str:
        """Return a stable cache identity for output-affecting inference settings."""
        payload = {
            "namespace": namespace,
            "bindings": self.safe_dict(capabilities),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()[:20]

    @classmethod
    def from_args(
        cls,
        provider: Optional[str] = None,
        chat_provider: Optional[str] = None,
        chat_model: Optional[str] = None,
        overview_chat_provider: Optional[str] = None,
        overview_chat_model: Optional[str] = None,
        embedding_provider: Optional[str] = None,
        embedding_model: Optional[str] = None,
        transcription_provider: Optional[str] = None,
        transcription_model: Optional[str] = None,
    ) -> "RuntimeProfile":
        """Build from CLI args.

        --provider sets all capabilities as shorthand.
        Per-capability --X-provider and --X-model override.
        """
        defaults = cls.default_openai()

        # Resolve provider: per-capability > global > default
        chat_prov = chat_provider or provider or defaults.chat.provider
        emb_prov = embedding_provider or provider or defaults.embedding.provider
        trans_prov = transcription_provider or provider or defaults.transcription.provider

        # Resolve models: per-capability > provider default > openai default
        chat_mod = chat_model or _provider_default_model(chat_prov, "chat", defaults.chat.model)
        emb_mod = embedding_model or _provider_default_model(emb_prov, "embedding", defaults.embedding.model)
        trans_mod = transcription_model or _provider_default_model(trans_prov, "transcription", defaults.transcription.model)

        # Overview chat: only set if explicitly specified
        overview = None
        if overview_chat_provider or overview_chat_model:
            ov_prov = overview_chat_provider or chat_prov
            if overview_chat_model:
                ov_mod = overview_chat_model
            elif ov_prov == chat_prov:
                ov_mod = chat_mod
            else:
                ov_mod = _provider_default_model(
                    ov_prov, "chat", defaults.chat.model
                )
            overview = ModelBinding(provider=ov_prov, model=ov_mod)

        return cls(
            chat=ModelBinding(provider=chat_prov, model=chat_mod),
            overview_chat=overview,
            embedding=ModelBinding(provider=emb_prov, model=emb_mod),
            transcription=ModelBinding(provider=trans_prov, model=trans_mod),
        )

    @classmethod
    def default_openai(cls) -> "RuntimeProfile":
        """Current behavior: all OpenAI with gpt-4o as the editorial model.

        Preserves the current process/analyze CLI default exactly.
        """
        return cls(
            chat=ModelBinding(provider="openai", model="gpt-4o"),
            overview_chat=None,
            embedding=ModelBinding(provider="openai", model="text-embedding-3-small"),
            transcription=ModelBinding(provider="openai", model="whisper-1"),
        )
