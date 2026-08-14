"""
OpenAI provider adapters.

Wraps the OpenAI Python SDK behind Arena's inference port contracts.
Each adapter translates provider-native exceptions into ProviderError
subclasses and computes usage/cost via the centralized pricing table.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Optional

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
from .pricing import calculate_chat_cost, calculate_embedding_cost, calculate_speech_cost


class OpenAIChatModel(ChatModel):
    """Chat inference via OpenAI API (GPT-4o, GPT-4o-mini, etc.)."""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)

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
    ) -> ChatResponse:
        self._ensure_client()

        response_format = self._translate_response_mode(response_mode)

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=temperature,
                response_format=response_format,
            )
        except Exception as e:
            raise self._translate_error(e) from e

        content = response.choices[0].message.content or ""

        # Parse JSON when requested
        parsed = None
        if response_mode == ResponseMode.JSON:
            try:
                parsed = json.loads(content)
            except (json.JSONDecodeError, ValueError) as e:
                raise ProviderResponseError(
                    f"Model returned invalid JSON: {content[:200]}",
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
                str(e), code="unknown", retryable=False,
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
                f"OpenAI rejected the request: {e}",
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
            f"OpenAI error: {e}", code="unknown", retryable=False,
        )


class OpenAIEmbeddingModel(EmbeddingModel):
    """Embedding inference via OpenAI API (text-embedding-3-small, etc.)."""

    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)

    def embed(self, texts: list[str]) -> EmbeddingResponse:
        self._ensure_client()

        try:
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


class OpenAISpeechModel(SpeechModel):
    """Speech-to-text inference via OpenAI Whisper API."""

    def __init__(self, api_key: str, model: str = "whisper-1"):
        self._api_key = api_key
        self._model = model
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self._api_key)

    @property
    def max_file_size_mb(self) -> float:
        return 24.0  # OpenAI's 25MB limit with 1MB safety buffer

    def transcribe(self, audio_path: Path) -> TranscriptionResponse:
        self._ensure_client()

        try:
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
