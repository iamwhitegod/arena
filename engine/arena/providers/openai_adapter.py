"""
OpenAI provider adapters.

Wraps the OpenAI Python SDK behind Arena's inference port contracts.
Each adapter translates provider-native exceptions into ProviderError
subclasses and computes usage/cost via the centralized pricing table.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Callable, Optional

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
from .json_utils import validate_json_object
from .pricing import calculate_chat_cost, calculate_embedding_cost, calculate_speech_cost


_DEFAULT_TIMEOUT = 120.0  # seconds per HTTP attempt
_MAX_OUTPUT_TOKENS = 8_192
_MAX_PROMPT_CHARS = 1_000_000
_MAX_RESPONSE_CHARS = 1_000_000


class _CredentialProtectedAdapter:
    """Prevent accidental serialization of credential-bearing adapters."""

    def __getstate__(self):
        raise TypeError("Provider adapters cannot be serialized")

    def __reduce_ex__(self, protocol):
        raise TypeError("Provider adapters cannot be serialized")


def _client_factory(api_key: str) -> Callable[[], object]:
    """Capture a credential without exposing it in the adapter dictionary."""
    def build_client():
        from openai import OpenAI
        return OpenAI(api_key=api_key, timeout=_DEFAULT_TIMEOUT, max_retries=0)

    return build_client


def _validate_messages(messages: list[dict]) -> None:
    if not isinstance(messages, list) or not messages:
        raise ProviderInvalidRequestError("Chat messages must be a non-empty list.")
    total_chars = 0
    for message in messages:
        if not isinstance(message, dict):
            raise ProviderInvalidRequestError("Each chat message must be an object.")
        role = message.get("role")
        content = message.get("content")
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            raise ProviderInvalidRequestError("Chat messages contain unsupported fields.")
        total_chars += len(role) + len(content)
        if total_chars > _MAX_PROMPT_CHARS:
            raise ProviderInvalidRequestError("Chat prompt exceeds Arena's size limit.")


class OpenAIChatModel(_CredentialProtectedAdapter, ChatModel):
    """Chat inference via OpenAI API (GPT-4o, GPT-4o-mini, etc.)."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._build_client = _client_factory(api_key)
        self._model = model
        self._client = None

    def __repr__(self) -> str:
        return f"OpenAIChatModel(model={self._model!r})"

    def _ensure_client(self):
        if self._client is None:
            self._client = self._build_client()

    @property
    def concurrency_hint(self) -> int:
        return 5

    def supports_json_mode(self) -> bool:
        return True

    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        response_mode: ResponseMode = ResponseMode.TEXT,
        json_schema: Optional[dict] = None,
        max_output_tokens: Optional[int] = None,
    ) -> ChatResponse:
        _validate_messages(messages)
        if (
            max_output_tokens is not None
            and (
                isinstance(max_output_tokens, bool)
                or not isinstance(max_output_tokens, int)
                or max_output_tokens < 1
            )
        ):
            raise ProviderInvalidRequestError("max_output_tokens must be a positive integer.")
        kwargs = dict(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=min(
                max_output_tokens or _MAX_OUTPUT_TOKENS, _MAX_OUTPUT_TOKENS
            ),
        )
        response_format = self._translate_response_mode(response_mode)
        if response_format is not None:
            kwargs["response_format"] = response_format

        try:
            self._ensure_client()
            response = self._client.chat.completions.create(**kwargs)
        except Exception as e:
            raise self._translate_error(e) from e

        content = response.choices[0].message.content or ""
        if not isinstance(content, str) or len(content) > _MAX_RESPONSE_CHARS:
            raise ProviderResponseError("Model response exceeds Arena's size limit")

        # Parse JSON when requested
        parsed = None
        if response_mode == ResponseMode.JSON:
            try:
                parsed = validate_json_object(json.loads(content))
            except (json.JSONDecodeError, ValueError) as e:
                raise ProviderResponseError(
                    "Model returned invalid JSON",
                    code="response_error",
                    retryable=True,
                ) from e

        usage = ProviderUsage(
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
            total_tokens=response.usage.total_tokens,
            estimated_cost_usd=calculate_chat_cost(
                "openai", self._model,
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            ),
        )

        return ChatResponse(content=content, parsed=parsed, usage=usage)

    @property
    def max_output_tokens(self) -> int:
        return _MAX_OUTPUT_TOKENS

    @staticmethod
    def _translate_response_mode(response_mode: ResponseMode) -> Optional[dict]:
        if response_mode == ResponseMode.JSON:
            return {"type": "json_object"}
        return None

    @staticmethod
    def _translate_error(e: Exception) -> ProviderError:
        """Translate OpenAI SDK exceptions into ProviderError subclasses."""
        try:
            from openai import (
                APIConnectionError,
                APITimeoutError,
                AuthenticationError,
                BadRequestError,
                RateLimitError,
            )
        except ImportError:
            return ProviderError(
                "OpenAI provider dependency is unavailable.",
                code="unavailable",
                retryable=False,
            )

        if isinstance(e, AuthenticationError):
            return ProviderAuthError(
                "OpenAI authentication failed. Check your API key.",
                code="auth", retryable=False,
            )
        if isinstance(e, RateLimitError):
            retry_after = None
            if hasattr(e, "response") and e.response is not None:
                retry_header = e.response.headers.get("Retry-After")
                if retry_header:
                    try:
                        retry_after = float(retry_header)
                    except (ValueError, TypeError):
                        pass
            return ProviderRateLimitError(
                "OpenAI rate limit exceeded.",
                code="rate_limit", retryable=True, retry_after=retry_after,
            )
        if isinstance(e, BadRequestError):
            return ProviderInvalidRequestError(
                "OpenAI rejected the request.",
                code="invalid_request", retryable=False,
            )
        if isinstance(e, APITimeoutError):
            return ProviderTimeoutError(
                "OpenAI request timed out.",
                code="timeout", retryable=True,
            )
        if isinstance(e, APIConnectionError):
            return ProviderUnavailableError(
                "Could not connect to OpenAI.",
                code="unavailable", retryable=True,
            )

        # Check for server errors by status code
        status = getattr(e, "status_code", None)
        if status is not None and 500 <= status < 600:
            return ProviderUnavailableError(
                f"OpenAI server error (HTTP {status}).",
                code="unavailable", retryable=True,
            )

        return ProviderError(
            "Unexpected OpenAI error.", code="unknown", retryable=False,
        )


class OpenAIEmbeddingModel(_CredentialProtectedAdapter, EmbeddingModel):
    """Embedding inference via OpenAI API (text-embedding-3-small, etc.)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self._build_client = _client_factory(api_key)
        self._model = model
        self._client = None

    def __repr__(self) -> str:
        return f"OpenAIEmbeddingModel(model={self._model!r})"

    def _ensure_client(self):
        if self._client is None:
            self._client = self._build_client()

    def embed(self, texts: list[str]) -> EmbeddingResponse:
        try:
            self._ensure_client()
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
        except Exception as e:
            raise OpenAIChatModel._translate_error(e) from e

        embeddings = [item.embedding for item in response.data]

        usage = ProviderUsage(
            input_tokens=response.usage.total_tokens,
            total_tokens=response.usage.total_tokens,
            estimated_cost_usd=calculate_embedding_cost(
                "openai", self._model, response.usage.total_tokens,
            ),
        )

        return EmbeddingResponse(embeddings=embeddings, usage=usage)


class OpenAISpeechModel(_CredentialProtectedAdapter, SpeechModel):
    """Speech-to-text inference via OpenAI Whisper API."""

    def __init__(self, api_key: str, model: str = "whisper-1"):
        self._build_client = _client_factory(api_key)
        self._model = model
        self._client = None

    def __repr__(self) -> str:
        return f"OpenAISpeechModel(model={self._model!r})"

    def _ensure_client(self):
        if self._client is None:
            self._client = self._build_client()

    @property
    def max_file_size_mb(self) -> float:
        return 24.0  # OpenAI's 25MB limit with 1MB safety buffer

    def transcribe(self, audio_path: Path) -> TranscriptionResponse:
        try:
            self._ensure_client()
            with open(audio_path, "rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    model=self._model,
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"],
                )
        except Exception as e:
            raise OpenAIChatModel._translate_error(e) from e

        # Build typed word timestamps
        words = []
        if hasattr(response, "words") and response.words:
            for w in response.words:
                words.append(WordTimestamp(
                    word=w.word,
                    start=w.start,
                    end=w.end,
                ))

        # Build typed segments
        segments = []
        if hasattr(response, "segments") and response.segments:
            for s in response.segments:
                segments.append(TranscriptionSegment(
                    id=s.id,
                    start=s.start,
                    end=s.end,
                    text=s.text,
                ))

        duration = getattr(response, "duration", 0.0) or 0.0

        usage = ProviderUsage(
            input_audio_seconds=duration,
            estimated_cost_usd=calculate_speech_cost(
                "openai", self._model, duration,
            ),
        )

        return TranscriptionResponse(
            text=response.text,
            language=getattr(response, "language", "unknown") or "unknown",
            duration=duration,
            words=words,
            segments=segments,
            usage=usage,
        )
