"""
Arena inference ports — abstract base classes for AI model providers.

Two-layer architecture:
    Application Services (Transcriber, EditorialEngine)
        |
    Inference Ports (ChatModel, EmbeddingModel, SpeechModel)  <-- this module
        |
    Provider Adapters (OpenAI, local llama.cpp, Ollama, etc.)

Inference ports are internal to Arena. Application services consume them.
Terminal, Desktop, SDK, and Cloud interfaces consume application services only.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Response mode — provider-neutral output format
# ---------------------------------------------------------------------------

class ResponseMode(str, Enum):
    """How the model should format its output.
    Each provider adapter translates this into native configuration.
    """
    TEXT = "text"
    JSON = "json"


# ---------------------------------------------------------------------------
# Shared usage metadata
# ---------------------------------------------------------------------------

@dataclass
class ProviderUsage:
    """Accumulated usage metrics from a single provider call.

    Cost semantics:
        Decimal("0")  — known zero cost (e.g., local inference)
        None          — cost unknown or not applicable
        Decimal("X")  — computed cost from pricing table
    """
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: Optional[Decimal] = None
    input_audio_seconds: Optional[float] = None  # for speech models


# ---------------------------------------------------------------------------
# Normalized errors
# ---------------------------------------------------------------------------

class ProviderError(Exception):
    """Base error with a safe user-facing message.

    Native exceptions are chained with ``raise ... from error`` for
    internal diagnostics; they are never serialized into public errors
    or artifacts.

    Retry logic reads .retryable and .retry_after instead of inspecting
    provider-specific exception types.
    """

    def __init__(
        self,
        message: str,
        *,
        code: str,
        retryable: bool,
        retry_after: Optional[float] = None,
    ):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.retry_after = retry_after


class ProviderTimeoutError(ProviderError):
    """Request timed out. Generally retryable."""

    def __init__(self, message: str = "Request timed out", **kwargs):
        kwargs.setdefault("code", "timeout")
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class ProviderAuthError(ProviderError):
    """Authentication/authorization failure. Not retryable."""

    def __init__(self, message: str = "Authentication failed", **kwargs):
        kwargs.setdefault("code", "auth")
        kwargs.setdefault("retryable", False)
        super().__init__(message, **kwargs)


class ProviderRateLimitError(ProviderError):
    """Rate limit exceeded. Retryable with backoff."""

    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        kwargs.setdefault("code", "rate_limit")
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class ProviderInvalidRequestError(ProviderError):
    """Invalid request (bad params, too long, etc.). Not retryable."""

    def __init__(self, message: str = "Invalid request", **kwargs):
        kwargs.setdefault("code", "invalid_request")
        kwargs.setdefault("retryable", False)
        super().__init__(message, **kwargs)


class ProviderUnavailableError(ProviderError):
    """Provider is temporarily unavailable (5xx). Retryable."""

    def __init__(self, message: str = "Provider unavailable", **kwargs):
        kwargs.setdefault("code", "unavailable")
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


class ProviderResponseError(ProviderError):
    """Structured output was requested but the response was malformed.

    Raised when ResponseMode.JSON was requested and the model returned
    unparseable content. Generally retryable (model may succeed on retry).
    """

    def __init__(self, message: str = "Malformed structured output", **kwargs):
        kwargs.setdefault("code", "response_error")
        kwargs.setdefault("retryable", True)
        super().__init__(message, **kwargs)


# ---------------------------------------------------------------------------
# Chat inference port
# ---------------------------------------------------------------------------

@dataclass
class ChatResponse:
    """Normalized response from any chat model.

    parsed is None when response_mode is TEXT.
    When response_mode is JSON, parsed is populated or the adapter
    raises ProviderResponseError — it is never silently None.
    Domain-schema validation remains in the application service.
    """
    content: str
    parsed: Optional[dict] = None
    usage: ProviderUsage = field(default_factory=ProviderUsage)


class ChatModel(ABC):
    """Abstract inference port for chat/completion models.

    Model identity is bound at construction time — the adapter knows
    which model it wraps. Callers don't pass model strings.
    """

    @abstractmethod
    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        response_mode: ResponseMode = ResponseMode.TEXT,
        json_schema: Optional[dict] = None,
    ) -> ChatResponse:
        """Run a chat completion.

        Args:
            messages: Chat messages in [{"role": ..., "content": ...}] format.
            temperature: Sampling temperature.
            response_mode: TEXT for free-form, JSON for structured output.
                Each adapter translates this into provider-native config
                (e.g., OpenAI response_format, llama.cpp grammar).
            json_schema: Optional JSON schema hint for structured output.
                Adapters may use this for grammar-constrained generation
                or validation. Ignored when response_mode is TEXT.

        Returns:
            ChatResponse with content and optional parsed JSON.
            When response_mode is JSON, parsed is populated or
            ProviderResponseError is raised.

        Raises:
            ProviderResponseError: if JSON was requested but output is malformed.
            ProviderError subclass: on other failures.
        """
        ...

    def supports_json_mode(self) -> bool:
        """Whether this model reliably produces structured JSON output."""
        return False

    @property
    def concurrency_hint(self) -> int:
        """Suggested max concurrent calls. Cloud: 5-10, Local: 1."""
        return 1


# ---------------------------------------------------------------------------
# Embedding inference port
# ---------------------------------------------------------------------------

@dataclass
class EmbeddingResponse:
    """Normalized response from any embedding model."""
    embeddings: list[list[float]]
    usage: ProviderUsage = field(default_factory=ProviderUsage)


class EmbeddingModel(ABC):
    """Abstract inference port for embedding models.

    Model identity is bound at construction time.
    """

    @abstractmethod
    def embed(self, texts: list[str]) -> EmbeddingResponse:
        """Generate embeddings for a batch of texts.

        Args:
            texts: List of strings to embed.

        Returns:
            EmbeddingResponse with one embedding vector per input text.

        Raises:
            ProviderError subclass on failure.
        """
        ...


# ---------------------------------------------------------------------------
# Speech inference port
# ---------------------------------------------------------------------------

@dataclass
class WordTimestamp:
    """A single word with its time boundaries."""
    word: str
    start: float
    end: float


@dataclass
class TranscriptionSegment:
    """A segment of transcribed speech."""
    id: int
    start: float
    end: float
    text: str


@dataclass
class TranscriptionResponse:
    """Normalized response from any speech-to-text model."""
    text: str
    language: str
    duration: float
    words: list[WordTimestamp]
    segments: list[TranscriptionSegment]
    usage: ProviderUsage = field(default_factory=ProviderUsage)


class SpeechModel(ABC):
    """Abstract inference port for speech-to-text models.

    Model identity is bound at construction time.
    Handles a single audio file — chunking/merging is the
    Transcriber application service's responsibility.
    """

    @abstractmethod
    def transcribe(self, audio_path: Path) -> TranscriptionResponse:
        """Transcribe a single audio file.

        Args:
            audio_path: Path to audio file (wav, mp3, etc.).

        Returns:
            TranscriptionResponse with text, word timestamps, and segments.

        Raises:
            ProviderError subclass on failure.
        """
        ...

    @property
    def max_file_size_mb(self) -> float:
        """Maximum file size this model accepts. inf for local models."""
        return float("inf")
