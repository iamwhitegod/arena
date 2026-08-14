# Arena Provider Abstraction & Local AI Support

## Context

Arena's AI pipeline is 100% hardcoded to OpenAI: 12+ files import `openai`, every module takes an `api_key: str` constructor param, pricing is duplicated per-file, and the CLI validates `OPENAI_API_KEY` at startup. This makes Arena unusable without a cloud API key.

The goal is to make Arena provider-agnostic so it can run with local models (llama.cpp + faster-whisper), cloud providers (OpenAI, Anthropic, Gemini), or a mix. The `--offline` flag becomes a real product feature: "No data left this device."

Three phases: Phase 1 (provider abstraction) establishes contracts and refactors the pipeline. Phase 2 (local backends) wires up llama.cpp and faster-whisper. Phase 3 (model management + --offline) makes it user-facing.

---

## Architecture: Two Abstraction Layers

Arena needs two distinct layers. The original plan collapsed them into one.

```
Terminal / Desktop / SDK / Cloud
               |
      Arena Application Services          <-- stable domain API
  (Transcriber, EditorialEngine, Embedder)
               |
         Inference Ports                   <-- internal, swappable
   (ChatModel, SpeechModel, EmbeddingModel)
               |
   local | OpenAI | Anthropic | Gemini | Arena Cloud
```

**Why two layers:**

- `EditorialEngine.analyze(transcript)` is Arena's stable API. Terminal, Desktop, SDK, and Cloud interfaces call this. It should never change when a provider is added.
- `ChatModel.complete(messages)` is an internal inference port. Prompts and domain-schema validation stay in the application service; provider-specific structured-output configuration, response extraction, and exception translation stay in the adapter. Neither leaks into consumer interfaces.
- `Transcriber` keeps its orchestration (audio extraction, chunking, timestamp merging). It calls `SpeechModel.transcribe()` for each chunk. The model port is a simple single-file transcription call.
- Adding `VisionModel` or `RerankerModel` later doesn't distort Phase 1 contracts.

**What this means for the code:**

| Layer | What it is | Where it lives | Who consumes it |
|-------|-----------|----------------|-----------------|
| **Inference Ports** | `ChatModel`, `SpeechModel`, `EmbeddingModel` ABCs + provider implementations | `engine/arena/providers/` | Arena application services only |
| **Application Services** | `Transcriber`, `EditorialEngine` (the 4-layer pipeline), `Embedder` | `engine/arena/audio/`, `engine/arena/editorial/`, `engine/arena/ai/` | CLI commands, pipeline orchestrator, future SDK |
| **Configuration** | `RuntimeProfile`, `ModelBinding` | `engine/arena/providers/` | Python entry points (composition root) |

---

## Phase 1: Provider Abstraction Layer

### 1.1 Inference ports — contracts and types

**New file: `engine/arena/providers/base.py`**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path


# --- Shared usage metadata ---

@dataclass
class ProviderUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    input_audio_seconds: float | None = None
    # Decimal("0") = known zero provider cost (local); None = unknown.
    estimated_cost_usd: Decimal | None = None


# --- Normalized errors ---

class ProviderError(Exception):
    """Base error with a safe user-facing message.

    Native exceptions are chained with ``raise ... from error`` for internal
    diagnostics; they are never serialized into public errors or artifacts.
    """
    def __init__(self, message: str, *, code: str, retryable: bool,
                 retry_after: float | None = None):
        super().__init__(message)
        self.code = code              # "rate_limit", "auth", "timeout", "oom", "invalid_request"
        self.retryable = retryable
        self.retry_after = retry_after

class ProviderTimeoutError(ProviderError): ...
class ProviderAuthError(ProviderError): ...
class ProviderRateLimitError(ProviderError): ...
class ProviderResponseError(ProviderError): ...  # malformed structured output


# --- Chat inference port ---

class ResponseMode(str, Enum):
    TEXT = "text"
    JSON = "json"

@dataclass
class ChatResponse:
    content: str                       # Raw text
    parsed: dict | None                # Pre-parsed JSON, or None for plain text
    usage: ProviderUsage = field(default_factory=ProviderUsage)

class ChatModel(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        response_mode: ResponseMode = ResponseMode.TEXT,
        json_schema: dict | None = None,
    ) -> ChatResponse: ...

    def supports_json_mode(self) -> bool:
        return False

    @property
    def concurrency_hint(self) -> int:
        return 1


# --- Embedding inference port ---

@dataclass
class EmbeddingResponse:
    embeddings: list[list[float]]
    usage: ProviderUsage = field(default_factory=ProviderUsage)

class EmbeddingModel(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> EmbeddingResponse: ...


# --- Speech inference port ---

@dataclass
class WordTimestamp:
    word: str
    start: float
    end: float

@dataclass
class TranscriptionSegment:
    id: int
    start: float
    end: float
    text: str

@dataclass
class TranscriptionResponse:
    text: str
    language: str
    duration: float
    words: list[WordTimestamp]
    segments: list[TranscriptionSegment]
    usage: ProviderUsage = field(default_factory=ProviderUsage)

class SpeechModel(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path) -> TranscriptionResponse: ...

    @property
    def max_file_size_mb(self) -> float:
        return float('inf')
```

Key design decisions:

- **No `model` parameter on inference calls.** The model is bound at construction time via `ModelBinding`. Cloud adapters receive the model string in their constructor (`OpenAIChatModel(api_key, model="gpt-4o-mini")`). Local adapters receive a model path. This resolves the contradiction in the original plan where local providers had a fixed model but the API expected per-call model strings.
- **Provider-neutral structured output.** Application services request `ResponseMode.JSON` and may provide a JSON schema. Adapters translate that request into OpenAI response formats, llama.cpp grammars, or another provider's native mechanism. OpenAI-shaped `response_format` dictionaries never cross the inference port.
- **`parsed: dict | None`** — not mandatory. Plain-text inference calls return `None`; JSON calls either return a parsed object or raise `ProviderResponseError`.
- **`ProviderUsage` on all responses** including transcription (which the original plan missed).
- **Cost semantics are explicit.** Local adapters return `Decimal("0")`; `None` means the cost is unknown. Metrics remain `Decimal` until artifact/console serialization, avoiding float accumulation across 40+ calls. Speech usage records `input_audio_seconds`.
- **Typed `WordTimestamp` / `TranscriptionSegment`** instead of untyped dicts.
- **Structured-output failure is an error.** If `ResponseMode.JSON` was requested and parsing fails, the adapter raises `ProviderResponseError`; it does not silently return `parsed=None`. Application services still validate the parsed object against their domain contract.
- **`ProviderError` hierarchy** has a safe message plus `code`, `retryable`, and `retry_after`. Each provider adapter wraps native exceptions using exception chaining. Retry logic reads `error.retryable` — no `provider_type` strings or message matching.
- **Public artifact compatibility is preserved.** Typed response objects are internal; `Transcriber` and editorial services continue returning the existing dictionary/JSON artifact shapes at their public boundaries.

### 1.2 Runtime profile — per-capability binding

**New file: `engine/arena/providers/profile.py`**

```python
@dataclass
class ModelBinding:
    """Binds a capability to a specific provider and model."""
    provider: str          # "openai", "local", "ollama"
    model: str             # "gpt-4o-mini", "qwen3.5-4b-q4_k_m.gguf", etc.
    options: dict = field(default_factory=dict)  # Provider-specific (n_ctx, etc.)

@dataclass
class RuntimeProfile:
    """Complete inference configuration. One per pipeline run."""
    chat: ModelBinding
    overview_chat: ModelBinding | None
    embedding: ModelBinding
    transcription: ModelBinding

    @classmethod
    def from_args(
        cls,
        provider: str | None = None,
        chat_provider: str | None = None,
        chat_model: str | None = None,
        overview_chat_provider: str | None = None,
        overview_chat_model: str | None = None,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        transcription_provider: str | None = None,
        transcription_model: str | None = None,
    ) -> "RuntimeProfile":
        """Build from CLI args.
        --provider sets all three as shorthand.
        Per-capability args override."""
        ...

    @classmethod
    def default_openai(cls) -> "RuntimeProfile":
        """Current behavior: all OpenAI."""
        return cls(
            # Preserve the current process/analyze CLI default exactly.
            chat=ModelBinding(provider="openai", model="gpt-4o"),
            overview_chat=None,  # Falls back to chat.
            embedding=ModelBinding(provider="openai", model="text-embedding-3-small"),
            transcription=ModelBinding(provider="openai", model="whisper-1"),
        )
```

This resolves:
- **Mixed providers:** `--provider local --chat-provider openai --chat-model gpt-4o` uses local transcription/embedding but cloud editorial.
- **`--provider local`** is shorthand for all-local bindings.
- **Task-specific chat routing:** `overview_chat` is an optional override and otherwise reuses `chat`. This preserves `ThoughtSeedDetector(overview_model=...)` without reintroducing per-call model identifiers.
- **`--offline`** is a policy check applied to the resolved profile (Phase 3), not a provider name.

`RuntimeProfile` contains no credentials. It is safe to serialize for diagnostics after provider-specific options have been redacted. In Phase 1 the CLI accepts only the implemented `openai` provider; `local` and `ollama` become valid choices when their adapters land in Phase 2.

### 1.3 Provider construction

**New file: `engine/arena/providers/registry.py`**

```python
class ProviderRegistry:
    """Constructs model instances from bindings."""

    def __init__(self, factories: ProviderFactories | None = None):
        """Production factories by default; injectable fake factories in tests."""

    def build_chat(self, binding: ModelBinding, credentials: CredentialResolver) -> ChatModel: ...
    def build_embedding(self, binding: ModelBinding, credentials: CredentialResolver) -> EmbeddingModel: ...
    def build_speech(self, binding: ModelBinding, credentials: CredentialResolver) -> SpeechModel: ...

    def build_required(
        self,
        profile: RuntimeProfile,
        required: set[Capability],
        credentials: CredentialResolver,
    ) -> InferenceBundle: ...

@dataclass
class InferenceBundle:
    """Only requested model instances are constructed."""
    chat: ChatModel | None = None
    overview_chat: ChatModel | None = None
    embedding: EmbeddingModel | None = None
    speech: SpeechModel | None = None

    def require_chat(self) -> ChatModel: ...
    def require_overview_chat(self) -> ChatModel:
        return self.overview_chat or self.require_chat()
    def require_embedding(self) -> EmbeddingModel: ...
    def require_speech(self) -> SpeechModel: ...
```

Phase 1: registry only knows `"openai"`. Phase 2 adds `"local"`, `"ollama"`.

**New file: `engine/arena/providers/credentials.py`**

```python
class CredentialResolver(Protocol):
    def get(self, provider: str, credential: str) -> str | None: ...

class EnvironmentCredentialResolver:
    """Phase 1 maps ("openai", "api_key") to OPENAI_API_KEY.
    Future adapters add their own provider-specific credential names.
    """
```

Credentials are resolved only while constructing an adapter. They are never stored in `RuntimeProfile`, `ModelBinding`, logs, checkpoints, or artifacts. Building only `required` capabilities prevents `arena transcribe` from loading a local chat or embedding model and prevents `arena analyze --transcript ...` from loading a speech model.

### 1.4 Centralized pricing

**New file: `engine/arena/providers/pricing.py`**

```python
@dataclass(frozen=True)
class PricingEntry:
    provider: str
    model: str
    effective_from: date
    input_per_million: Decimal | None = None
    output_per_million: Decimal | None = None
    audio_per_minute: Decimal | None = None

# Values are estimates, verified against the provider's official pricing source
# when updated. Unknown provider/model combinations return None, never zero.
PRICING: dict[tuple[str, str], PricingEntry] = {...}

def calculate_chat_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> Decimal | None: ...
def calculate_embedding_cost(provider: str, model: str, total_tokens: int) -> Decimal | None: ...
def calculate_speech_cost(provider: str, model: str, audio_seconds: float) -> Decimal | None: ...
```

Replaces hardcoded pricing in 6+ editorial modules. Pricing changes do not alter the provider interfaces, and tests use fixture pricing rather than assuming live prices.

### 1.5 OpenAI adapters

**New file: `engine/arena/providers/openai_adapter.py`**

```python
class OpenAIChatModel(ChatModel):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self._api_key = api_key
        self._model = model
        # lazy client init

    @property
    def concurrency_hint(self) -> int:
        return 5

    def supports_json_mode(self) -> bool:
        return True

    def complete(
        self,
        messages,
        temperature=0.3,
        response_mode=ResponseMode.TEXT,
        json_schema=None,
    ):
        try:
            response_format = self._translate_response_mode(response_mode, json_schema)
            response = self._client.chat.completions.create(
                model=self._model, messages=messages,
                temperature=temperature, response_format=response_format,
            )
        except openai.RateLimitError as e:
            raise ProviderRateLimitError(..., retryable=True, retry_after=...)
        except openai.AuthenticationError as e:
            raise ProviderAuthError(..., retryable=False)
        # Parse JSON only when requested. Raise ProviderResponseError if malformed.
        # Domain-schema validation remains in the application service.
        # Build ChatResponse and ProviderUsage using Decimal costs.

class OpenAIEmbeddingModel(EmbeddingModel):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"): ...

class OpenAISpeechModel(SpeechModel):
    def __init__(self, api_key: str, model: str = "whisper-1"): ...
    @property
    def max_file_size_mb(self) -> float:
        return 24.0  # OpenAI's 25MB limit with 1MB buffer
```

### 1.6 Fake adapters for testing

**New file: `engine/arena/providers/fake.py`**

```python
class FakeChatModel(ChatModel):
    """Returns canned responses. Used by every consumer test."""
    def __init__(self, responses: list[ChatResponse]): ...

class FakeEmbeddingModel(EmbeddingModel): ...
class FakeSpeechModel(SpeechModel): ...
```

Fake adapters are deterministic across processes. `FakeEmbeddingModel` derives vectors from `hashlib.sha256(text.encode())`, not Python's randomized `hash()`, and validates that fixed fixture embeddings match the requested batch size.

### 1.7 Retry with normalized errors

**New file: `engine/arena/providers/retry.py`**

```python
def retry_with_backoff(
    fn: Callable[[], T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
) -> T:
    """Retry fn when ProviderError.retryable is True.
    Uses error.retry_after if available, else exponential backoff.
    Non-retryable ProviderErrors re-raise immediately."""
```

**Existing `engine/arena/editorial/retry.py`** — kept as backward-compatible wrappers.

### 1.8 Refactor application services (editorial modules)

Each module's constructor changes from `(api_key, model)` to accept a `ChatModel` (or `EmbeddingModel`), with backward compatibility:

```python
class ThoughtSeedDetector:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o",
        overview_model: str | None = None,
        *,
        chat: ChatModel | None = None,
        overview_chat: ChatModel | None = None,
    ):
        if chat is not None:
            self._chat = chat
            self._overview_chat = overview_chat or chat
        elif api_key is not None:
            self._chat = OpenAIChatModel(api_key=api_key, model=model)
            self._overview_chat = (
                OpenAIChatModel(api_key=api_key, model=overview_model)
                if overview_model and overview_model != model
                else self._chat
            )
        else:
            raise ValueError("Either chat or api_key required")
```

Then `_call_model()` drops the `client` parameter:

```python
def _call_model(self, system, prompt):
    response = retry_with_backoff(
        lambda: self._chat.complete(
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": prompt}],
            temperature=0.3,
            response_mode=ResponseMode.JSON,
        )
    )
    self.metrics["api_calls"] += 1
    self.metrics["tokens_used"] += response.usage.total_tokens
    if response.usage.estimated_cost_usd is not None:
        self.metrics["cost_usd"] += response.usage.estimated_cost_usd
    return response.parsed
```

**`FourLayerAdapter` (the EditorialEngine)** accepts an `InferenceBundle`:

```python
class FourLayerAdapter:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "gpt-4o-mini",
        *,
        inference: InferenceBundle | None = None,
        ...
    ):
        if inference is not None:
            self._chat = inference.require_chat()
            self._overview_chat = inference.require_overview_chat()
            self._embedding = inference.require_embedding()
        elif api_key is not None:
            self._chat = OpenAIChatModel(api_key=api_key, model=model)
            self._overview_chat = self._chat
            self._embedding = OpenAIEmbeddingModel(api_key=api_key)
        # ...

    # When creating sub-modules:
    # self.seed_detector = ThoughtSeedDetector(
    #     chat=self._chat, overview_chat=self._overview_chat
    # )
    # self.deduplicator = SemanticDeduplicator(embedding=self._embedding)
```

**Files to modify (active pipeline only):**

| # | File | Change |
|---|------|--------|
| 1 | `editorial/adapter.py` | Accept `InferenceBundle`. Require chat/embedding capabilities and pass them to consumers |
| 2 | `editorial/thought_seed_detector.py` | Accept default and optional overview `ChatModel`s. Remove `client` param from `_call_model()`, OpenAI import, and pricing |
| 3 | `editorial/premise_detector.py` | Accept `chat: ChatModel`. Remove OpenAI import (line 79) |
| 4 | `editorial/resolution_detector.py` | Accept `chat: ChatModel`. Remove OpenAI import (line 80) |
| 5 | `editorial/thought_unit_constructor.py` | Accept `chat: ChatModel`. Pass to premise/resolution detectors |
| 6 | `editorial/completeness_scorer.py` | Accept `chat: ChatModel`. Remove client creation (lines 99-103), pricing (lines 211-214) |
| 7 | `editorial/standalone_validator.py` | Accept `chat: ChatModel`. Remove client creation (lines 82-86), pricing |
| 8 | `editorial/semantic_deduplicator.py` | Accept `embedding: EmbeddingModel`. Replace `client.embeddings.create()` (line 153) |

### 1.9 Refactor transcription orchestration

`Transcriber` keeps its orchestration role (audio extraction, chunking, timestamp merging). The `SpeechModel` port handles a single-file transcription.

```python
class Transcriber:
    def __init__(
        self,
        api_key: str | None = None,
        mode: str = "api",
        *,
        speech: SpeechModel | None = None,
    ):
        if speech is not None:
            self._speech = speech
            self.mode = "provider"
        elif mode == "local":
            # Existing openai-whisper path preserved for backward compat
            self._speech = None
            self.mode = "local"
        elif api_key is not None:
            self._speech = OpenAISpeechModel(api_key=api_key)
            self.mode = "provider"
```

Chunking stays in `Transcriber`. It checks `self._speech.max_file_size_mb` to decide whether to chunk, then calls `self._speech.transcribe()` per chunk and merges results with timestamp offsets.

The existing `_transcribe_local()` (lines 282-334, uses `openai-whisper` with `base` model) is preserved. Phase 2 replaces it with `LocalSpeechModel` using `faster-whisper`.

### 1.10 Migrate and deprecate legacy layer modules

These are publicly exported in `editorial/__init__.py` but superseded by the active ThoughtUnit pipeline:

| File | OpenAI import | Phase 1 action |
|------|--------------|----------------|
| `layer1_moment_detector.py` | line 85 | Accept `ChatModel`, remove OpenAI import and inline retry/pricing |
| `layer2_boundary_analyzer.py` | line 101 | Same |
| `layer3_context_refiner.py` | line 117 | Same |
| `layer4_packaging.py` | lines 85, 413 | Same, supporting both JSON and text response modes |

The classes and top-level imports remain available for one deprecation cycle so existing consumers do not break. Constructors retain the `api_key` compatibility path and emit `DeprecationWarning` with an appropriate `stacklevel`. Removal is deferred to the next major release, after repository usage and published API commitments are reviewed.

`editorial/__init__.py` therefore remains compatible during Phase 1:
```python
from .adapter import FourLayerAdapter
from .layer1_moment_detector import MomentDetector          # deprecated
from .layer2_boundary_analyzer import ThoughtBoundaryAnalyzer  # deprecated
from .layer3_context_refiner import StandaloneContextRefiner   # deprecated
from .layer4_packaging import PackagingLayer                # deprecated
from .checkpoint import CheckpointManager, CheckpointContext
```

This migration is required for `test_no_openai_leaks.py`: hiding a module from `__all__` does not remove its provider coupling. Direct imports used by `engine/validate_refinements.py` must continue to work.

### 1.11 Pipeline entry points — single composition root

**New file: `engine/arena/providers/resolve.py`**

```python
def resolve_inference(
    profile: RuntimeProfile,
    *,
    required: set[Capability],
    credentials: CredentialResolver,
    offline: bool = False,
) -> InferenceBundle:
    """Build only the capabilities needed by this command/run."""
    registry = ProviderRegistry()
    return registry.build_required(profile, required, credentials)
```

**Files to modify:**

| File | Change |
|------|--------|
| `arena_process.py` (line 263) | Resolve `{CHAT, EMBEDDING, SPEECH}` once and pass the bundle to `FourLayerAdapter` and `Transcriber` |
| `arena/main.py` (lines 94, 170) | Resolve only the capabilities used by the selected operation |
| `arena/cli/commands/analyze.py` (line 23) | Resolve `{CHAT, EMBEDDING}` plus `SPEECH` only when no transcript was supplied |
| `arena/cli/commands/transcribe.py` (line 25) | Resolve `{SPEECH}` only |
| `arena/cli/main.py` (line 169) | Add provider/model selectors, including optional overview-chat selectors |

### 1.12 TypeScript CLI

| File | Change |
|------|--------|
| `cli/src/bridge/python-bridge.ts` | Add provider/model options to `ProcessOptions`. Pass as flags |
| `cli/src/core/config.ts` | Add provider fields to global config |
| `cli/src/core/preflight.ts` | Check credentials required by selected providers; OpenAI is the only Phase 1 implementation |
| `cli/src/commands/process.ts` | Add `--provider` and per-capability options, preserving existing defaults |

TypeScript passes only non-secret selectors to Python. Existing owner-only credential storage may expose the OpenAI key to the managed Python child through its environment, but the profile and command arguments never contain secrets. Python adapter construction remains the authoritative credential check; TypeScript preflight only provides earlier, friendlier errors.

### 1.13 Testing

| Test file | Coverage |
|-----------|----------|
| `tests/unit/test_providers_base.py` | Response dataclasses, ProviderError hierarchy, ABC enforcement |
| `tests/unit/test_providers_openai.py` | OpenAI adapters with mocked SDK, error normalization |
| `tests/unit/test_providers_registry.py` | Registry construction, unknown provider errors |
| `tests/unit/test_providers_profile.py` | RuntimeProfile.from_args, shorthand expansion, mixed providers |
| `tests/unit/test_editorial_with_fake.py` | Active and deprecated editorial modules work through fake models; overview routing is preserved |
| `tests/unit/test_transcriber_with_fake.py` | Chunking + aggregation with FakeSpeechModel |
| `tests/unit/test_bundle_propagation.py` | Required capabilities are built once and reach every consumer; unused local models are not loaded |
| `tests/unit/test_no_openai_leaks.py` | Guard: `from openai` only under `arena/providers/` |
| `tests/unit/test_mixed_providers.py` | Injectable fake registry builds different providers for chat, overview, embedding, and speech |
| `tests/unit/test_provider_credentials.py` | Provider-specific credential lookup, missing-credential errors, and secret redaction |
| `tests/unit/test_provider_responses.py` | TEXT/JSON translation, malformed JSON errors, domain-schema validation boundary |
| `tests/unit/test_fake_providers.py` | Fakes are deterministic across processes and reject malformed fixture batches |

---

## Phase 2: Local Inference Backends

Model/runtime recommendations (Qwen, llama.cpp, faster-whisper, Silero, pyannote) belong here, not in Phase 1 contracts.

### 2.1 Local adapters

| New file | Class | Runtime |
|----------|-------|---------|
| `providers/local_chat.py` | `LocalChatModel(ChatModel)` | `llama-cpp-python` with GGUF |
| `providers/local_embedding.py` | `LocalEmbeddingModel(EmbeddingModel)` | `llama-cpp-python` |
| `providers/local_speech.py` | `LocalSpeechModel(SpeechModel)` | `faster-whisper` (CTranslate2) |
| `providers/ollama_adapter.py` | `OllamaChatModel`, `OllamaEmbeddingModel` | HTTP to localhost:11434 |
| `providers/json_utils.py` | `extract_json(text)` | JSON extraction fallback for local |

### 2.2 Model registry (runtime-specific)

| New file | Purpose |
|----------|---------|
| `models/registry.py` | Model pack definitions (lite/default/pro) with Qwen3.5, Whisper, etc. |
| `models/manager.py` | Download, validate, locate in `~/.arena/models/` |
| `models/hardware.py` | GPU/RAM detection, quantization recommendation |

### 2.3 Dependencies

```python
# setup.py extras_require
extras_require={
    "local": ["llama-cpp-python>=0.3.0", "faster-whisper>=1.0.0"],
    "ollama": ["requests>=2.28.0"],  # not a current direct dep
}
```

---

## Phase 3: --offline as Enforced Policy

`--offline` is not a provider name. It is a no-egress execution policy applied to a resolved `RuntimeProfile`:

1. **Validate profile:** reject any binding where `provider` is not `"local"`. Error with actionable message.
2. **Validate models:** error if local models not installed.
3. **Block outbound:** disable URL downloads, telemetry, and update checks during processing.
4. **Model installation is online:** `arena models install` requires network (one-time). After that, `--offline` works.

```python
# In resolve.py
if offline:
    for capability in required:
        binding = profile.binding_for(capability)
        if binding.provider != "local":
            raise OfflinePolicyError(
                f"--offline requires local providers, but {capability} uses '{binding.provider}'. "
                f"Either remove --offline or set --{capability}-provider local"
            )
```

CLI commands: `arena models install <pack>`, `arena models list`, `arena models remove`.

---

## Risks

| Risk | Mitigation |
|------|-----------|
| JSON reliability with small local models | llama-cpp-python grammar mode; `json_utils.py` extraction fallback |
| Local inference throughput | `concurrency_hint` adapts pipeline parallelism |
| Breaking backward compatibility | Dual constructor: `api_key` still works everywhere |
| Embedding dimension mismatch | Cosine similarity uses vectors from same run only |
| `requests` not a direct dep | Explicit in `setup.py` extras for Ollama |
| Large local models loaded for unused capabilities | Capability-aware resolution constructs only `required` bindings |
| Structured-output API differs by provider | Provider-neutral `ResponseMode`/schema translated inside each adapter |
| Provider secrets leak through profiles/errors | Credential resolver is separate; public errors contain safe messages only |

---

## Verification

1. `cd engine && pytest tests/` -- the configured supported engine suite passes
2. `cd cli && npm test` -- all CLI tests pass
3. `test_no_openai_leaks.py` -- `openai` only imported under `arena/providers/`
4. Compatibility tests cover root-level direct constructors/scripts that are outside `pytest.ini`'s `testpaths`, or those scripts are explicitly classified as non-suite diagnostics
5. Manual: `arena process test.mp4 --provider openai` preserves the current `gpt-4o` default and output behavior
6. Manual: `arena transcribe test.mp4` proves chat/embedding adapters are not constructed
7. (Phase 2+) `arena process test.mp4 --provider local` produces clips
8. (Phase 3) `arena process test.mp4 --offline` works with network access denied at the process boundary

---

## Implementation Order (Phase 1)

1. Contracts: `base.py` (ABCs, dataclasses, errors), `fake.py` (test doubles)
2. OpenAI adapters: `openai_adapter.py`, `pricing.py` -- with mocked contract tests
3. Configuration: `profile.py`, `credentials.py`, injectable `registry.py`, capability-aware `resolve.py`
4. Refactor active editorial pipeline: adapter -> seed_detector -> premise -> resolution -> constructor -> completeness -> standalone -> deduplicator
5. Refactor transcription: `Transcriber` keeps chunking, calls `SpeechModel` per chunk
6. Migrate and deprecate legacy layers: keep imports compatible while removing all direct OpenAI coupling
7. Retry: `providers/retry.py` using `ProviderError.retryable`
8. Entry points: resolve only required capabilities once per run and pass the bundle through
9. TypeScript: provider/model selectors, preserved defaults, provider-aware credential preflight
10. Tests: contracts, deterministic fakes, consumers, legacy compatibility, propagation, import guard, credentials, mixed providers, and chunk aggregation
