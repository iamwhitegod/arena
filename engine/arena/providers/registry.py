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
    profile: Optional[RuntimeProfile] = None

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

    def close(self) -> None:
        """Release constructed provider resources, closing shared models once."""
        closed: set[int] = set()
        for attribute in ("speech", "embedding", "overview_chat", "chat"):
            model = getattr(self, attribute)
            if model is not None and id(model) not in closed:
                close = getattr(model, "close", None)
                if callable(close):
                    close()
                closed.add(id(model))
            setattr(self, attribute, None)


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
    """Build production factories for all supported providers."""

    local_recommendation = None

    def _recommended_local_runtime():
        nonlocal local_recommendation
        if local_recommendation is None:
            from ..models.hardware import recommend_runtime
            local_recommendation = recommend_runtime()
        return local_recommendation

    # -- OpenAI --

    def _require_openai_key(creds: CredentialResolver, provider: str) -> str:
        api_key = creds.get(provider, "api_key")
        if not api_key:
            raise ProviderAuthError(
                "OpenAI API key not found. Set OPENAI_API_KEY environment variable.",
                code="auth", retryable=False,
            )
        return api_key

    def build_openai_chat(binding: ModelBinding, creds: CredentialResolver) -> ChatModel:
        from .openai_adapter import OpenAIChatModel
        return OpenAIChatModel(api_key=_require_openai_key(creds, binding.provider), model=binding.model)

    def build_openai_embedding(binding: ModelBinding, creds: CredentialResolver) -> EmbeddingModel:
        from .openai_adapter import OpenAIEmbeddingModel
        return OpenAIEmbeddingModel(api_key=_require_openai_key(creds, binding.provider), model=binding.model)

    def build_openai_speech(binding: ModelBinding, creds: CredentialResolver) -> SpeechModel:
        from .openai_adapter import OpenAISpeechModel
        return OpenAISpeechModel(api_key=_require_openai_key(creds, binding.provider), model=binding.model)

    # -- Local (llama-cpp-python / faster-whisper) --

    def build_local_chat(binding: ModelBinding, creds: CredentialResolver) -> ChatModel:
        from .local_chat import LocalChatModel
        from ..models.locator import ModelLocator
        from ..models.registry import chat_model_context_size
        recommendation = _recommended_local_runtime()
        path = ModelLocator().resolve_gguf(binding.model, capability="chat")
        n_threads_raw = binding.options.get("n_threads") or binding.options.get("threads")
        requested_context = int(
            binding.options.get("n_ctx", recommendation.context_size)
        )
        verified_context = chat_model_context_size(binding.model)
        context_size = (
            min(requested_context, verified_context)
            if verified_context is not None
            else requested_context
        )
        return LocalChatModel(
            model_path=str(path),
            n_ctx=context_size,
            n_gpu_layers=int(binding.options.get("n_gpu_layers", recommendation.gpu_layers)),
            n_threads=int(n_threads_raw) if n_threads_raw is not None else recommendation.threads,
            timeout_seconds=float(binding.options.get("timeout_seconds", 120.0)),
        )

    def build_local_embedding(binding: ModelBinding, creds: CredentialResolver) -> EmbeddingModel:
        from .local_embedding import LocalEmbeddingModel
        from ..models.locator import ModelLocator
        recommendation = _recommended_local_runtime()
        path = ModelLocator().resolve_gguf(binding.model, capability="embedding")
        return LocalEmbeddingModel(
            model_path=str(path),
            n_ctx=int(binding.options.get("n_ctx", 512)),
            n_gpu_layers=int(binding.options.get("n_gpu_layers", recommendation.gpu_layers)),
            n_threads=int(
                binding.options.get(
                    "threads", binding.options.get("n_threads", recommendation.threads)
                )
            ),
            timeout_seconds=float(binding.options.get("timeout_seconds", 120.0)),
        )

    def build_local_speech(binding: ModelBinding, creds: CredentialResolver) -> SpeechModel:
        from .local_speech import LocalSpeechModel
        from ..models.locator import ModelLocator
        recommendation = _recommended_local_runtime()
        size_or_path = ModelLocator().resolve_speech_model(binding.model)
        return LocalSpeechModel(
            model_size_or_path=size_or_path,
            device=str(binding.options.get("device", recommendation.speech_device)),
            compute_type=str(
                binding.options.get("compute_type", recommendation.speech_compute_type)
            ),
            cpu_threads=int(
                binding.options.get(
                    "threads", binding.options.get("n_threads", recommendation.threads)
                )
            ),
            timeout_seconds=float(binding.options.get("timeout_seconds", 300.0)),
        )

    # -- Ollama --

    def build_ollama_chat(binding: ModelBinding, creds: CredentialResolver) -> ChatModel:
        from .ollama_adapter import OllamaChatModel
        return OllamaChatModel(
            model=binding.model,
            timeout_seconds=float(binding.options.get("timeout_seconds", 60.0)),
            concurrency_hint=int(binding.options.get("concurrency", 1)),
            context_window_tokens=int(binding.options.get("n_ctx", 8_192)),
        )

    def build_ollama_embedding(binding: ModelBinding, creds: CredentialResolver) -> EmbeddingModel:
        from .ollama_adapter import OllamaEmbeddingModel
        return OllamaEmbeddingModel(
            model=binding.model,
            timeout_seconds=float(binding.options.get("timeout_seconds", 60.0)),
        )

    return ProviderFactories(
        chat={"openai": build_openai_chat, "local": build_local_chat, "ollama": build_ollama_chat},
        embedding={"openai": build_openai_embedding, "local": build_local_embedding, "ollama": build_ollama_embedding},
        speech={"openai": build_openai_speech, "local": build_local_speech},
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
        bundle = InferenceBundle(profile=profile)

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
