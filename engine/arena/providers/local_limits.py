"""Shared Arena-controlled validation and resource bounds for local adapters."""

import math

from .base import ProviderInvalidRequestError, ProviderResponseError


MAX_PROMPT_CHARS = 200_000
MAX_OUTPUT_TOKENS = 4_096
MAX_RESPONSE_CHARS = 1_000_000
MAX_EMBEDDING_BATCH = 512
MAX_EMBEDDING_TEXT_CHARS = 100_000
MAX_EMBEDDING_TOTAL_CHARS = 1_000_000
MAX_EMBEDDING_DIMENSION = 16_384
MAX_INFERENCE_SECONDS = 300.0
# Speech work scales with media duration and can legitimately take longer than
# chat or embedding calls on CPU-only systems. This remains a per-chunk hard
# budget; Transcriber limits each local chunk to ten minutes of audio. The
# native generator is cooperative, so Arena checks the budget when it yields.
MAX_SPEECH_INFERENCE_SECONDS = 1_800.0


def validate_messages(messages: list[dict]) -> None:
    if not isinstance(messages, list) or not messages:
        raise ProviderInvalidRequestError("Chat messages must be a non-empty list.")
    total = 0
    for message in messages:
        if not isinstance(message, dict) or set(message) - {"role", "content"}:
            raise ProviderInvalidRequestError("Chat messages contain unsupported fields.")
        role = message.get("role")
        content = message.get("content")
        if role not in {"system", "user", "assistant"} or not isinstance(content, str):
            raise ProviderInvalidRequestError("Chat messages contain unsupported values.")
        total += len(role) + len(content)
        if total > MAX_PROMPT_CHARS:
            raise ProviderInvalidRequestError("Chat prompt exceeds Arena's local size limit.")


def validate_temperature(temperature: object) -> float:
    if (
        isinstance(temperature, bool)
        or not isinstance(temperature, (int, float))
        or not math.isfinite(temperature)
        or temperature < 0
        or temperature > 2
    ):
        raise ProviderInvalidRequestError("temperature must be between 0 and 2.")
    return float(temperature)


def validate_embedding_inputs(texts: list[str]) -> None:
    if not isinstance(texts, list) or not texts or len(texts) > MAX_EMBEDDING_BATCH:
        raise ProviderInvalidRequestError("Embedding batch size is outside Arena's limit.")
    total = 0
    for text in texts:
        if not isinstance(text, str) or len(text) > MAX_EMBEDDING_TEXT_CHARS:
            raise ProviderInvalidRequestError("Embedding input is invalid or oversized.")
        total += len(text)
        if total > MAX_EMBEDDING_TOTAL_CHARS:
            raise ProviderInvalidRequestError("Embedding batch exceeds Arena's size limit.")


def validate_embedding_vectors(vectors: object, expected_count: int) -> list[list[float]]:
    if not isinstance(vectors, list) or len(vectors) != expected_count:
        raise ProviderResponseError(
            "Provider returned an unexpected embedding count.",
            code="invalid_embedding_response",
            retryable=False,
        )
    dimension = None
    validated: list[list[float]] = []
    for vector in vectors:
        if (
            not isinstance(vector, list)
            or not vector
            or len(vector) > MAX_EMBEDDING_DIMENSION
        ):
            raise ProviderResponseError(
                "Provider returned an invalid embedding vector.",
                code="invalid_embedding_response",
                retryable=False,
            )
        if dimension is None:
            dimension = len(vector)
        elif len(vector) != dimension:
            raise ProviderResponseError(
                "Provider returned inconsistent embedding dimensions.",
                code="invalid_embedding_response",
                retryable=False,
            )
        normalized: list[float] = []
        for value in vector:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ProviderResponseError(
                    "Provider returned a non-numeric embedding value.",
                    code="invalid_embedding_response",
                    retryable=False,
                )
            number = float(value)
            if not math.isfinite(number):
                raise ProviderResponseError(
                    "Provider returned a non-finite embedding value.",
                    code="invalid_embedding_response",
                    retryable=False,
                )
            normalized.append(number)
        validated.append(normalized)
    return validated


def bounded_usage_count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return min(value, 1_000_000_000)
