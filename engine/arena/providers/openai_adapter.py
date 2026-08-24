"""
OpenAI provider adapters.

Wraps the OpenAI Python SDK behind Arena's inference port contracts.
Each adapter translates provider-native exceptions into ProviderError
subclasses and computes usage/cost via the centralized pricing table.
"""

import json
import math
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
from .local_limits import (
    bounded_usage_count,
    validate_embedding_inputs,
    validate_embedding_vectors,
    validate_temperature,
)
from .pricing import calculate_chat_cost, calculate_embedding_cost, calculate_speech_cost


_DEFAULT_TIMEOUT = 120.0  # seconds per HTTP attempt
_MAX_OUTPUT_TOKENS = 8_192
_MAX_PROMPT_CHARS = 1_000_000
_MAX_RESPONSE_CHARS = 1_000_000
_MAX_TRANSCRIPTION_CHARS = 2_000_000
_MAX_TRANSCRIPTION_DURATION_SECONDS = 86_400.0
_MAX_TRANSCRIPTION_SEGMENTS = 50_000
_MAX_TRANSCRIPTION_WORDS = 500_000
_MAX_SEGMENT_CHARS = 10_000
_MAX_WORD_CHARS = 1_000


class _CredentialProtectedAdapter:
    """Prevent accidental serialization of credential-bearing adapters."""

    def __getstate__(self):
        raise TypeError("Provider adapters cannot be serialized")

    def __reduce_ex__(self, protocol):
        raise TypeError("Provider adapters cannot be serialized")

    def close(self) -> None:
        """Close the lazy SDK client's connection pool, if it was created."""
        client = getattr(self, "_client", None)
        self._client = None
        # The factory closure contains the API key until first use. Clear it
        # even when the adapter is closed before an SDK client is constructed.
        self._build_client = None
        close = getattr(client, "close", None)
        if callable(close):
            close()


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
        if not isinstance(message, dict) or set(message) - {"role", "content"}:
            raise ProviderInvalidRequestError("Chat messages contain unsupported fields.")
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
            factory = self._build_client
            if factory is None:
                raise ProviderError(
                    "OpenAI adapter has been closed.",
                    code="provider_closed",
                    retryable=False,
                )
            try:
                self._client = factory()
            finally:
                self._build_client = None

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
        temperature = validate_temperature(temperature)
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
        except ProviderError:
            raise
        except Exception as e:
            raise self._translate_error(e) from e

        try:
            choices = response.choices
            if not isinstance(choices, list) or not choices:
                raise TypeError
            content = choices[0].message.content
            if content is None:
                content = ""
        except (AttributeError, IndexError, TypeError) as e:
            raise ProviderResponseError(
                "OpenAI returned an invalid chat response.",
                code="invalid_chat_response",
                retryable=False,
            ) from e
        if not isinstance(content, str) or len(content) > _MAX_RESPONSE_CHARS:
            raise ProviderResponseError(
                "OpenAI returned an invalid or oversized chat response.",
                code="invalid_chat_response",
                retryable=False,
            )

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

        response_usage = getattr(response, "usage", None)
        input_tokens = bounded_usage_count(
            getattr(response_usage, "prompt_tokens", 0)
        )
        output_tokens = bounded_usage_count(
            getattr(response_usage, "completion_tokens", 0)
        )
        total_tokens = bounded_usage_count(
            getattr(response_usage, "total_tokens", input_tokens + output_tokens)
        )
        usage = ProviderUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=calculate_chat_cost(
                "openai", self._model,
                input_tokens,
                output_tokens,
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
            factory = self._build_client
            if factory is None:
                raise ProviderError(
                    "OpenAI adapter has been closed.",
                    code="provider_closed",
                    retryable=False,
                )
            try:
                self._client = factory()
            finally:
                self._build_client = None

    def embed(self, texts: list[str]) -> EmbeddingResponse:
        validate_embedding_inputs(texts)
        try:
            self._ensure_client()
            response = self._client.embeddings.create(
                model=self._model,
                input=texts,
            )
        except ProviderError:
            raise
        except Exception as e:
            raise OpenAIChatModel._translate_error(e) from e

        try:
            response_data = response.data
            if not isinstance(response_data, list):
                raise TypeError
            embeddings = validate_embedding_vectors(
                [item.embedding for item in response_data], len(texts)
            )
        except ProviderResponseError:
            raise
        except (AttributeError, TypeError) as e:
            raise ProviderResponseError(
                "OpenAI returned an invalid embedding response.",
                code="invalid_embedding_response",
                retryable=False,
            ) from e

        response_usage = getattr(response, "usage", None)
        input_tokens = bounded_usage_count(
            getattr(response_usage, "total_tokens", 0)
        )
        usage = ProviderUsage(
            input_tokens=input_tokens,
            total_tokens=input_tokens,
            estimated_cost_usd=calculate_embedding_cost(
                "openai", self._model, input_tokens,
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
            factory = self._build_client
            if factory is None:
                raise ProviderError(
                    "OpenAI adapter has been closed.",
                    code="provider_closed",
                    retryable=False,
                )
            try:
                self._client = factory()
            finally:
                self._build_client = None

    @property
    def max_file_size_mb(self) -> float:
        return 24.0  # OpenAI's 25MB limit with 1MB safety buffer

    @property
    def max_audio_duration_seconds(self) -> float:
        return 600.0

    def transcribe(self, audio_path: Path) -> TranscriptionResponse:
        if not isinstance(audio_path, Path) or not audio_path.is_file():
            raise ProviderInvalidRequestError("Audio input must be a regular file.")
        try:
            if audio_path.stat().st_size > int(self.max_file_size_mb * 1024 * 1024):
                raise ProviderInvalidRequestError(
                    "Audio input exceeds the OpenAI upload size limit."
                )
        except OSError as e:
            raise ProviderInvalidRequestError("Audio input could not be read.") from e
        try:
            self._ensure_client()
            with open(audio_path, "rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    model=self._model,
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["word", "segment"],
                )
        except ProviderError:
            raise
        except Exception as e:
            raise OpenAIChatModel._translate_error(e) from e

        try:
            duration_value = getattr(response, "duration", 0.0)
            duration = 0.0 if duration_value is None else duration_value
            if (
                isinstance(duration, bool)
                or not isinstance(duration, (int, float))
                or not math.isfinite(duration)
                or duration < 0
                or duration > _MAX_TRANSCRIPTION_DURATION_SECONDS
            ):
                raise TypeError
            duration = float(duration)

            text = response.text
            language = getattr(response, "language", "unknown") or "unknown"
            if not isinstance(text, str) or len(text) > _MAX_TRANSCRIPTION_CHARS:
                raise TypeError
            if not isinstance(language, str) or not language or len(language) > 32:
                raise TypeError

            raw_words = getattr(response, "words", None) or []
            raw_segments = getattr(response, "segments", None) or []
            if not isinstance(raw_words, (list, tuple)) or len(raw_words) > _MAX_TRANSCRIPTION_WORDS:
                raise TypeError
            if not isinstance(raw_segments, (list, tuple)) or len(raw_segments) > _MAX_TRANSCRIPTION_SEGMENTS:
                raise TypeError

            words = []
            for item in raw_words:
                word = item.word
                start = item.start
                end = item.end
                self._validate_timestamp(start, end, duration)
                if not isinstance(word, str) or len(word) > _MAX_WORD_CHARS:
                    raise TypeError
                words.append(WordTimestamp(word=word, start=float(start), end=float(end)))

            segments = []
            for item in raw_segments:
                segment_id = item.id
                start = item.start
                end = item.end
                segment_text = item.text
                self._validate_timestamp(start, end, duration)
                if (
                    isinstance(segment_id, bool)
                    or not isinstance(segment_id, int)
                    or segment_id < 0
                    or not isinstance(segment_text, str)
                    or len(segment_text) > _MAX_SEGMENT_CHARS
                ):
                    raise TypeError
                segments.append(TranscriptionSegment(
                    id=segment_id,
                    start=float(start),
                    end=float(end),
                    text=segment_text,
                ))
        except ProviderResponseError:
            raise
        except (AttributeError, TypeError) as e:
            raise ProviderResponseError(
                "OpenAI returned an invalid transcription response.",
                code="invalid_transcription_response",
                retryable=False,
            ) from e

        usage = ProviderUsage(
            input_audio_seconds=duration,
            estimated_cost_usd=calculate_speech_cost(
                "openai", self._model, duration,
            ),
        )

        return TranscriptionResponse(
            text=text,
            language=language,
            duration=duration,
            words=words,
            segments=segments,
            usage=usage,
        )

    @staticmethod
    def _validate_timestamp(start, end, duration: float) -> None:
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in (start, end)
        ):
            raise ProviderResponseError(
                "OpenAI returned an invalid transcription timestamp.",
                code="invalid_transcription_response",
                retryable=False,
            )
        if start < 0 or end < start or end > duration + 1.0:
            raise ProviderResponseError(
                "OpenAI returned an out-of-range transcription timestamp.",
                code="invalid_transcription_response",
                retryable=False,
            )
