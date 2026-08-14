"""
Provider registry — constructs model instances from bindings.

Production code uses the default factories. Tests inject fake factories
to build mixed-provider bundles without real adapters.
"""

from dataclasses import dataclass
from typing import Callable, Optional

from .base import ChatModel, EmbeddingModel, ProviderAuthError, SpeechModel
from .credentials import CredentialResolver
from .profile import Capability, ModelBinding, RuntimeProfile


@dataclass
class InferenceBundle:
    """Holds constructed model instances for a pipeline run.

    Only requested capabilities are populated. Callers use require_*()
    to access them, which raises if the capability wasn't built.
    """
    chat: Optional[ChatModel] = None
    overview_chat: Optional[ChatModel] = None
    embedding: Optional[EmbeddingModel] = None
    speech: Optional[SpeechModel] = None

    def require_chat(self) -> ChatModel:
        if self.chat is None:
            raise RuntimeError("Chat model was not constructed. Add CHAT to required capabilities.")
        return self.chat

    def require_overview_chat(self) -> ChatModel:
        """Returns overview_chat if set, otherwise falls back to chat."""
        return self.overview_chat or self.require_chat()

    def require_embedding(self) -> EmbeddingModel:
        if self.embedding is None:
            raise RuntimeError("Embedding model was not constructed. Add EMBEDDING to required capabilities.")
        return self.embedding

    def require_speech(self) -> SpeechModel:
        if self.speech is None:
            raise RuntimeError("Speech model was not constructed. Add SPEECH to required capabilities.")
        return self.speech


# Type aliases for factory callables
ChatFactory = Callable[[ModelBinding, CredentialResolver], ChatModel]
EmbeddingFactory = Callable[[ModelBinding, CredentialResolver], EmbeddingModel]
SpeechFactory = Callable[[ModelBinding, CredentialResolver], SpeechModel]


@dataclass
class ProviderFactories:
    """Injectable factory functions for each provider name."""
    chat: dict[str, ChatFactory]
    embedding: dict[str, EmbeddingFactory]
    speech: dict[str, SpeechFactory]


def _default_factories() -> ProviderFactories:
    """Build production factories. Only OpenAI in Phase 1."""

    def build_openai_chat(binding: ModelBinding, creds: CredentialResolver) -> ChatModel:
        api_key = creds.get(binding.provider, "api_key")
        if not api_key:
            raise ProviderAuthError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable.",
                code="auth", retryable=False,
            )
        from .openai_adapter import OpenAIChatModel
        return OpenAIChatModel(api_key=api_key, model=binding.model)

    def build_openai_embedding(binding: ModelBinding, creds: CredentialResolver) -> EmbeddingModel:
        api_key = creds.get(binding.provider, "api_key")
        if not api_key:
            raise ProviderAuthError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable.",
                code="auth", retryable=False,
            )
        from .openai_adapter import OpenAIEmbeddingModel
        return OpenAIEmbeddingModel(api_key=api_key, model=binding.model)

    def build_openai_speech(binding: ModelBinding, creds: CredentialResolver) -> SpeechModel:
        api_key = creds.get(binding.provider, "api_key")
        if not api_key:
            raise ProviderAuthError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable.",
                code="auth", retryable=False,
            )
        from .openai_adapter import OpenAISpeechModel
        return OpenAISpeechModel(api_key=api_key, model=binding.model)

    return ProviderFactories(
        chat={"openai": build_openai_chat},
        embedding={"openai": build_openai_embedding},
        speech={"openai": build_openai_speech},
    )


class ProviderRegistry:
    """Constructs model instances from bindings using registered factories."""

    def __init__(self, factories: Optional[ProviderFactories] = None):
        self._factories = factories or _default_factories()

    def build_chat(self, binding: ModelBinding, credentials: CredentialResolver) -> ChatModel:
        factory = self._factories.chat.get(binding.provider)
        if factory is None:
            raise ValueError(
                f"Unknown chat provider: '{binding.provider}'. "
                f"Available: {list(self._factories.chat.keys())}"
            )
        return factory(binding, credentials)

    def build_embedding(self, binding: ModelBinding, credentials: CredentialResolver) -> EmbeddingModel:
        factory = self._factories.embedding.get(binding.provider)
        if factory is None:
            raise ValueError(
                f"Unknown embedding provider: '{binding.provider}'. "
                f"Available: {list(self._factories.embedding.keys())}"
            )
        return factory(binding, credentials)

    def build_speech(self, binding: ModelBinding, credentials: CredentialResolver) -> SpeechModel:
        factory = self._factories.speech.get(binding.provider)
        if factory is None:
            raise ValueError(
                f"Unknown speech provider: '{binding.provider}'. "
                f"Available: {list(self._factories.speech.keys())}"
            )
        return factory(binding, credentials)

    def build_required(
        self,
        profile: RuntimeProfile,
        required: set[Capability],
        credentials: CredentialResolver,
    ) -> InferenceBundle:
        """Build only the capabilities needed by this command.

        This prevents arena transcribe from loading chat/embedding models
        and arena analyze --transcript from loading a speech model.
        """
        bundle = InferenceBundle()

        if Capability.CHAT in required:
            bundle.chat = self.build_chat(
                profile.binding_for(Capability.CHAT), credentials,
            )

        if Capability.OVERVIEW_CHAT in required:
            overview_binding = profile.binding_for(Capability.OVERVIEW_CHAT)
            chat_binding = profile.binding_for(Capability.CHAT)
            # Reuse the chat model if bindings are identical
            if overview_binding == chat_binding and bundle.chat is not None:
                bundle.overview_chat = bundle.chat
            else:
                bundle.overview_chat = self.build_chat(overview_binding, credentials)

        if Capability.EMBEDDING in required:
            bundle.embedding = self.build_embedding(
                profile.binding_for(Capability.EMBEDDING), credentials,
            )

        if Capability.SPEECH in required:
            bundle.speech = self.build_speech(
                profile.binding_for(Capability.SPEECH), credentials,
            )

        return bundle
