"""
Ollama provider adapters.

Communicates with a local Ollama server over HTTP.  Ollama is treated as
an untrusted network peer: hard timeouts, response size caps, and
localhost-only base URLs are enforced.
"""

import json
import math
import time
from decimal import Decimal
from typing import Optional
from urllib.parse import urlparse

from .base import (
    ChatModel,
    ChatResponse,
    EmbeddingModel,
    EmbeddingResponse,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUsage,
    ResponseMode,
)
from .json_utils import extract_json
from .local_limits import (
    MAX_OUTPUT_TOKENS,
    MAX_RESPONSE_CHARS,
    bounded_usage_count,
    validate_embedding_inputs,
    validate_embedding_vectors,
    validate_messages,
    validate_temperature,
)

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_CHAT_TIMEOUT_SECONDS = 180.0
_DEFAULT_EMBEDDING_TIMEOUT_SECONDS = 60.0
_MAX_RESPONSE_BYTES = 10 * 1024 * 1024  # 10 MB
_LOCALHOST_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})


def _validate_base_url(base_url: str) -> str:
    """Ensure the base URL is a credential-free loopback HTTP origin."""
    parsed = urlparse(base_url)
    hostname = (parsed.hostname or "").lower()
    try:
        port = parsed.port
    except ValueError as exc:
        raise ProviderError(
            "Ollama base URL contains an invalid port.",
            code="ollama_invalid_url",
            retryable=False,
        ) from exc
    if (
        parsed.scheme != "http"
        or hostname not in _LOCALHOST_HOSTS
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
        or (port is not None and not 1 <= port <= 65535)
    ):
        raise ProviderError(
            "Ollama base URL must be a credential-free localhost HTTP origin.",
            code="ollama_invalid_url",
            retryable=False,
        )
    host = f"[{hostname}]" if ":" in hostname else hostname
    return f"http://{host}{f':{port}' if port is not None else ''}"


def _post(
    base_url: str,
    path: str,
    payload: dict,
    timeout: float,
) -> dict:
    """Make a POST request to the Ollama API with safety limits."""
    try:
        import requests
    except ImportError:
        raise ProviderError(
            "requests is required for Ollama. "
            "Install with: pip install 'arena-engine[ollama]'",
            code="ollama_unavailable",
            retryable=False,
        )

    if not math.isfinite(timeout) or timeout < 1 or timeout > 300:
        raise ProviderInvalidRequestError("Ollama timeout is outside Arena's limit.")

    url = f"{base_url}{path}"
    deadline = time.monotonic() + timeout
    session = requests.Session()
    session.trust_env = False
    resp = None
    try:
        try:
            resp = session.post(
                url,
                json=payload,
                timeout=(5.0, timeout),  # (connect, read)
                stream=True,
                allow_redirects=False,
            )
        except requests.ConnectionError as exc:
            raise ProviderUnavailableError(
                "Could not connect to Ollama. Is the server running?",
                code="ollama_connection",
                retryable=True,
            ) from exc
        except requests.Timeout as exc:
            raise ProviderTimeoutError(
                "Ollama request timed out.",
                code="timeout",
                retryable=True,
            ) from exc
        except requests.RequestException as exc:
            raise ProviderUnavailableError(
                "Ollama request failed.", code="ollama_connection", retryable=True
            ) from exc

        if time.monotonic() >= deadline:
            raise ProviderTimeoutError("Ollama request exceeded Arena's time limit.")

        if 300 <= resp.status_code < 400:
            raise ProviderError(
                "Ollama returned a redirect, which is not allowed.",
                code="ollama_redirect",
                retryable=False,
            )
        if resp.status_code >= 500:
            raise ProviderUnavailableError(
                f"Ollama server error (HTTP {resp.status_code}).",
                code="ollama_server_error",
                retryable=True,
            )
        if resp.status_code == 404:
            raise ProviderInvalidRequestError(
                "Ollama could not find the selected model or API endpoint.",
                code="ollama_not_found",
                retryable=False,
            )
        if resp.status_code >= 400:
            raise ProviderInvalidRequestError(
                f"Ollama rejected the request (HTTP {resp.status_code}).",
                code="ollama_bad_request",
                retryable=False,
            )

        length_header = resp.headers.get("Content-Length")
        if length_header:
            try:
                if int(length_header) > _MAX_RESPONSE_BYTES:
                    raise ProviderResponseError(
                        "Ollama response exceeded size limit.",
                        code="ollama_oversized",
                        retryable=False,
                    )
            except ValueError as exc:
                raise ProviderResponseError(
                    "Ollama returned an invalid Content-Length.",
                    code="ollama_invalid_response",
                    retryable=False,
                ) from exc

        chunks: list[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=8192):
            if time.monotonic() >= deadline:
                raise ProviderTimeoutError("Ollama request exceeded Arena's time limit.")
            total += len(chunk)
            if total > _MAX_RESPONSE_BYTES:
                raise ProviderResponseError(
                    "Ollama response exceeded size limit.",
                    code="ollama_oversized",
                    retryable=False,
                )
            chunks.append(chunk)

        try:
            decoded = json.loads(
                b"".join(chunks),
                parse_constant=lambda value: (_ for _ in ()).throw(
                    ValueError(f"invalid constant: {value}")
                ),
            )
        except (json.JSONDecodeError, ValueError, RecursionError) as exc:
            raise ProviderResponseError(
                "Ollama returned invalid JSON.",
                code="ollama_invalid_response",
                retryable=False,
            ) from exc
        if not isinstance(decoded, dict):
            raise ProviderResponseError(
                "Ollama returned a non-object response.",
                code="ollama_invalid_response",
                retryable=False,
            )
        return decoded
    finally:
        if resp is not None:
            resp.close()
        session.close()


class OllamaChatModel(ChatModel):
    """Chat inference via a local Ollama server."""

    def __init__(
        self,
        model: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = _DEFAULT_CHAT_TIMEOUT_SECONDS,
        concurrency_hint: int = 1,
        context_window_tokens: int = 8_192,
    ):
        if (
            isinstance(concurrency_hint, bool)
            or not isinstance(concurrency_hint, int)
            or not 1 <= concurrency_hint <= 4
        ):
            raise ProviderInvalidRequestError(
                "Ollama concurrency must be between 1 and 4."
            )
        self._model = model
        self._base_url = _validate_base_url(base_url)
        self._timeout = timeout_seconds
        self._concurrency_hint = concurrency_hint
        self._context_window_tokens = max(2_048, min(context_window_tokens, 128_000))

    def __repr__(self) -> str:
        return f"OllamaChatModel(model={self._model!r})"

    @property
    def concurrency_hint(self) -> int:
        return self._concurrency_hint

    @property
    def context_window_tokens(self) -> int:
        return self._context_window_tokens

    @property
    def max_output_tokens(self) -> int:
        return MAX_OUTPUT_TOKENS

    def supports_json_mode(self) -> bool:
        return True  # Ollama supports format: "json"

    def complete(
        self,
        messages: list[dict],
        temperature: float = 0.3,
        response_mode: ResponseMode = ResponseMode.TEXT,
        json_schema: Optional[dict] = None,
        max_output_tokens: Optional[int] = None,
    ) -> ChatResponse:
        validate_messages(messages)
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
        payload: dict = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": self._context_window_tokens,
                "num_predict": min(
                    max_output_tokens or MAX_OUTPUT_TOKENS, MAX_OUTPUT_TOKENS
                ),
            },
        }
        if response_mode == ResponseMode.JSON:
            payload["format"] = "json"

        data = _post(self._base_url, "/api/chat", payload, self._timeout)

        message = data.get("message", {})
        if not isinstance(message, dict):
            raise ProviderResponseError(
                "Ollama returned an invalid chat message.",
                code="ollama_invalid_response",
                retryable=False,
            )
        content = message.get("content", "") or ""
        if not isinstance(content, str) or len(content) > MAX_RESPONSE_CHARS:
            raise ProviderResponseError(
                "Ollama returned invalid or oversized chat content.",
                code="ollama_invalid_response",
                retryable=False,
            )

        parsed = None
        if response_mode == ResponseMode.JSON:
            parsed = extract_json(content)

        input_tokens = bounded_usage_count(data.get("prompt_eval_count", 0))
        output_tokens = bounded_usage_count(data.get("eval_count", 0))

        usage = ProviderUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=Decimal("0"),
        )

        return ChatResponse(content=content, parsed=parsed, usage=usage)


class OllamaEmbeddingModel(EmbeddingModel):
    """Embedding inference via a local Ollama server."""

    def __init__(
        self,
        model: str,
        base_url: str = _DEFAULT_BASE_URL,
        timeout_seconds: float = _DEFAULT_EMBEDDING_TIMEOUT_SECONDS,
    ):
        self._model = model
        self._base_url = _validate_base_url(base_url)
        self._timeout = timeout_seconds

    def __repr__(self) -> str:
        return f"OllamaEmbeddingModel(model={self._model!r})"

    def embed(self, texts: list[str]) -> EmbeddingResponse:
        validate_embedding_inputs(texts)
        payload = {
            "model": self._model,
            "input": texts,
        }

        data = _post(self._base_url, "/api/embed", payload, self._timeout)

        embeddings = validate_embedding_vectors(data.get("embeddings"), len(texts))

        return EmbeddingResponse(
            embeddings=embeddings,
            usage=ProviderUsage(
                input_tokens=bounded_usage_count(data.get("prompt_eval_count", 0)),
                total_tokens=bounded_usage_count(data.get("prompt_eval_count", 0)),
                estimated_cost_usd=Decimal("0"),
            ),
        )
