"""
Runtime profile — per-capability model binding configuration.

A RuntimeProfile describes which provider and model to use for each
inference capability. It contains no credentials and is safe to
serialize for diagnostics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


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
    options: dict = field(default_factory=dict)


@dataclass
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

        # Resolve models: per-capability > default for that provider
        chat_mod = chat_model or defaults.chat.model
        emb_mod = embedding_model or defaults.embedding.model
        trans_mod = transcription_model or defaults.transcription.model

        # Overview chat: only set if explicitly specified
        overview = None
        if overview_chat_provider or overview_chat_model:
            ov_prov = overview_chat_provider or chat_prov
            ov_mod = overview_chat_model or chat_mod
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
