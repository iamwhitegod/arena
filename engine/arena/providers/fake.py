"""
Fake provider adapters for testing.

These deterministic test doubles let every Arena application service
(EditorialEngine, Transcriber, etc.) be tested without real inference.
They also enable mixed-provider tests with an injectable registry.

Determinism: FakeEmbeddingModel derives vectors from hashlib.sha256,
not Python's randomized hash(), so results are stable across processes.
"""

import hashlib
import struct
from decimal import Decimal
from pathlib import Path
from typing import Optional

from .base import (
    ChatModel,
    ChatResponse,
    EmbeddingModel,
    EmbeddingResponse,
    ProviderUsage,
    ResponseMode,
    SpeechModel,
    TranscriptionResponse,
    TranscriptionSegment,
    WordTimestamp,
)


class FakeChatModel(ChatModel):
    """Returns canned responses in sequence.

    Usage:
        model = FakeChatModel([
            ChatResponse(content='{"seeds": []}', parsed={"seeds": []}),
            ChatResponse(content="A plain text title"),
        ])
        r1 = model.complete(messages=[...], response_mode=ResponseMode.JSON)
        r2 = model.complete(messages=[...], response_mode=ResponseMode.TEXT)
    """

    def __init__(
        self,
        responses: Optional[list[ChatResponse]] = None,
        default_response: Optional[ChatResponse] = None,
        concurrency: int = 1,
        context_window_tokens: int = 128_000,
        max_output_tokens: int = 8_192,
    ):
        self._responses = list(responses or [])
        self._default = default_response or ChatResponse(
            content="{}",
            parsed={},
            usage=ProviderUsage(
                input_tokens=10,
                output_tokens=5,
                total_tokens=15,
                estimated_cost_usd=Decimal("0"),
            ),
        )
        self._call_index = 0
        self._calls: list[dict] = []
        self._concurrency = concurrency
        self._context_window_tokens = context_window_tokens
        self._max_output_tokens = max_output_tokens

    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        response_mode: ResponseMode = ResponseMode.TEXT,
        json_schema: Optional[dict] = None,
        max_output_tokens: Optional[int] = None,
    ) -> ChatResponse:
        self._calls.append({
            "messages": messages,
            "temperature": temperature,
            "response_mode": response_mode,
            "json_schema": json_schema,
            "max_output_tokens": max_output_tokens,
        })
        if self._call_index < len(self._responses):
            response = self._responses[self._call_index]
            self._call_index += 1
            return response
        return self._default

    def supports_json_mode(self) -> bool:
        return True

    @property
    def concurrency_hint(self) -> int:
        return self._concurrency

    @property
    def context_window_tokens(self) -> int:
        return self._context_window_tokens

    @property
    def max_output_tokens(self) -> int:
        return self._max_output_tokens

    @property
    def calls(self) -> list[dict]:
        """Recorded calls for assertion."""
        return self._calls

    @property
    def call_count(self) -> int:
        return len(self._calls)


class FakeEmbeddingModel(EmbeddingModel):
    """Returns deterministic embeddings.

    By default, derives a unit vector per input text from sha256,
    producing stable results across processes and non-trivial
    cosine similarity between different texts.

    When fixed_embeddings is provided, validates that the batch size
    matches the number of input texts.
    """

    def __init__(
        self,
        dimension: int = 64,
        fixed_embeddings: Optional[list[list[float]]] = None,
    ):
        self._dimension = dimension
        self._fixed = fixed_embeddings
        self._calls: list[dict] = []

    def embed(self, texts: list[str]) -> EmbeddingResponse:
        self._calls.append({"texts": texts})

        if self._fixed is not None:
            if len(self._fixed) < len(texts):
                raise ValueError(
                    f"FakeEmbeddingModel: {len(texts)} texts requested "
                    f"but only {len(self._fixed)} fixed embeddings provided"
                )
            embeddings = self._fixed[:len(texts)]
        else:
            embeddings = [self._derive_embedding(text) for text in texts]

        return EmbeddingResponse(
            embeddings=embeddings,
            usage=ProviderUsage(
                input_tokens=sum(len(t.split()) for t in texts),
                total_tokens=sum(len(t.split()) for t in texts),
                estimated_cost_usd=Decimal("0"),
            ),
        )

    def _derive_embedding(self, text: str) -> list[float]:
        """Derive a deterministic unit vector from text via sha256."""
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Unpack as many floats as we need from repeated hashing
        vec = []
        seed = digest
        while len(vec) < self._dimension:
            # Each sha256 gives 32 bytes = 8 floats (4 bytes each)
            for i in range(0, len(seed) - 3, 4):
                if len(vec) >= self._dimension:
                    break
                # Convert 4 bytes to a float in [-1, 1]
                raw = struct.unpack(">I", seed[i:i + 4])[0]
                vec.append((raw / 2147483647.5) - 1.0)
            seed = hashlib.sha256(seed).digest()

        vec = vec[:self._dimension]
        # Normalize to unit vector
        magnitude = sum(v * v for v in vec) ** 0.5
        if magnitude > 0:
            vec = [v / magnitude for v in vec]
        return vec

    @property
    def calls(self) -> list[dict]:
        return self._calls

    @property
    def call_count(self) -> int:
        return len(self._calls)


class FakeSpeechModel(SpeechModel):
    """Returns a canned transcription.

    Useful for testing Transcriber's chunking and aggregation logic.
    """

    def __init__(
        self,
        transcript_text: str = "Hello world.",
        language: str = "en",
        duration: float = 5.0,
        words: Optional[list[WordTimestamp]] = None,
        segments: Optional[list[TranscriptionSegment]] = None,
        file_size_limit_mb: float = float("inf"),
    ):
        self._text = transcript_text
        self._language = language
        self._duration = duration
        self._words = words or [
            WordTimestamp(word="Hello", start=0.0, end=0.5),
            WordTimestamp(word="world.", start=0.6, end=1.0),
        ]
        self._segments = segments or [
            TranscriptionSegment(id=0, start=0.0, end=1.0, text="Hello world."),
        ]
        self._file_size_limit = file_size_limit_mb
        self._calls: list[dict] = []

    def transcribe(self, audio_path: Path) -> TranscriptionResponse:
        self._calls.append({"audio_path": str(audio_path)})
        return TranscriptionResponse(
            text=self._text,
            language=self._language,
            duration=self._duration,
            words=list(self._words),
            segments=list(self._segments),
            usage=ProviderUsage(
                input_audio_seconds=self._duration,
                estimated_cost_usd=Decimal("0"),
            ),
        )

    @property
    def max_file_size_mb(self) -> float:
        return self._file_size_limit

    @property
    def calls(self) -> list[dict]:
        return self._calls

    @property
    def call_count(self) -> int:
        return len(self._calls)
