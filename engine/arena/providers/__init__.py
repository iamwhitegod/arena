"""
Arena inference providers.

Two-layer architecture:
    Application Services (Transcriber, EditorialEngine)
        |
    Inference Ports (ChatModel, EmbeddingModel, SpeechModel)
        |
    Provider Adapters (OpenAI, local, Ollama, etc.)

Public API for consumers:
    - base: ABCs, response types, errors
    - profile: RuntimeProfile, ModelBinding, Capability
    - registry: ProviderRegistry, InferenceBundle
    - resolve: resolve_inference() entry point
    - credentials: CredentialResolver protocol
    - retry: retry_with_backoff()
    - fake: FakeChatModel, FakeEmbeddingModel, FakeSpeechModel (testing)
"""

from .base import (
    ChatModel,
    ChatResponse,
    EmbeddingModel,
    EmbeddingResponse,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUsage,
    ResponseMode,
    SpeechModel,
    TranscriptionResponse,
    TranscriptionSegment,
    WordTimestamp,
)
from .credentials import CredentialResolver, EnvironmentCredentialResolver
from .profile import Capability, ModelBinding, RuntimeProfile
from .registry import InferenceBundle, ProviderRegistry
from .resolve import resolve_inference
from .retry import retry_with_backoff

__all__ = [
    # Inference ports
    "ChatModel",
    "EmbeddingModel",
    "SpeechModel",
    # Response types
    "ChatResponse",
    "EmbeddingResponse",
    "TranscriptionResponse",
    "TranscriptionSegment",
    "WordTimestamp",
    "ProviderUsage",
    "ResponseMode",
    # Errors
    "ProviderError",
    "ProviderAuthError",
    "ProviderInvalidRequestError",
    "ProviderRateLimitError",
    "ProviderResponseError",
    "ProviderTimeoutError",
    "ProviderUnavailableError",
    # Configuration
    "Capability",
    "ModelBinding",
    "RuntimeProfile",
    # Construction
    "InferenceBundle",
    "ProviderRegistry",
    "resolve_inference",
    # Credentials
    "CredentialResolver",
    "EnvironmentCredentialResolver",
    # Retry
    "retry_with_backoff",
]
