"""
Local embedding adapter using llama-cpp-python with GGUF models.

Embedding dimensions vary by model.  Do not mix cached embeddings across
different model bindings.  Arena's profile fingerprinting handles cache
isolation automatically.
"""

from decimal import Decimal
from pathlib import Path
import threading
import time
from typing import Optional

from .base import (
    EmbeddingModel,
    EmbeddingResponse,
    ProviderError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUsage,
)
from .local_limits import (
    MAX_INFERENCE_SECONDS,
    validate_embedding_inputs,
    validate_embedding_vectors,
)
from ..models.hardware import (
    LocalResourceError,
    clamp_context,
    clamp_threads,
    enforce_model_resources,
)


class LocalEmbeddingModel(EmbeddingModel):
    """Embedding inference via llama-cpp-python on the local device."""

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 512,
        n_gpu_layers: int = 0,
        n_threads: Optional[int] = None,
        timeout_seconds: float = 120.0,
    ):
        try:
            from llama_cpp import Llama
            try:
                from llama_cpp import llama_supports_gpu_offload
            except ImportError:
                llama_supports_gpu_offload = None
        except ImportError:
            raise ProviderError(
                "llama-cpp-python is required for local embedding inference. "
                "Install with: pip install 'arena-engine[local]'",
                code="local_unavailable",
                retryable=False,
            )

        bounded_context = clamp_context(n_ctx)
        bounded_gpu_layers = max(-1, min(n_gpu_layers, 256))
        if bounded_gpu_layers != 0 and (
            llama_supports_gpu_offload is None or not llama_supports_gpu_offload()
        ):
            bounded_gpu_layers = 0
        try:
            enforce_model_resources(
                Path(model_path),
                context_size=bounded_context,
                gpu_layers=bounded_gpu_layers,
            )
        except LocalResourceError as e:
            raise ProviderError(
                str(e), code="local_resource_limit", retryable=False
            ) from e

        try:
            self._llm = Llama(
                model_path=model_path,
                n_ctx=bounded_context,
                n_gpu_layers=bounded_gpu_layers,
                n_threads=clamp_threads(n_threads),
                embedding=True,
                verbose=False,
            )
        except MemoryError as e:
            raise ProviderError(
                "Local embedding model does not fit in available memory.",
                code="local_oom",
                retryable=False,
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Failed to load local embedding model: {type(e).__name__}",
                code="local_load_failed",
                retryable=False,
            ) from e

        self._model_path = model_path
        self._timeout_seconds = max(1.0, min(float(timeout_seconds), MAX_INFERENCE_SECONDS))
        self._cancelled = threading.Event()

    def __repr__(self) -> str:
        return f"LocalEmbeddingModel(model_path={self._model_path!r})"

    def cancel(self) -> None:
        """Prevent another embedding call and discard an in-flight result."""
        self._cancelled.set()

    def _is_cancelled(self) -> bool:
        event = getattr(self, "_cancelled", None)
        return bool(event and event.is_set())

    def embed(self, texts: list[str]) -> EmbeddingResponse:
        validate_embedding_inputs(texts)
        if self._is_cancelled():
            raise ProviderError(
                "Local embedding was cancelled.", code="local_cancelled", retryable=False
            )
        embeddings: list[list[float]] = []
        total_tokens = 0
        deadline = time.monotonic() + getattr(self, "_timeout_seconds", 120.0)

        for text in texts:
            if self._is_cancelled():
                raise ProviderError(
                    "Local embedding was cancelled.", code="local_cancelled", retryable=False
                )
            if time.monotonic() >= deadline:
                raise ProviderTimeoutError("Local embedding exceeded Arena's time limit.")
            try:
                result = self._llm.embed(text)
                if time.monotonic() >= deadline:
                    raise ProviderTimeoutError("Local embedding exceeded Arena's time limit.")
                embeddings.append(result)
                total_tokens += len(self._llm.tokenize(text.encode()))
            except ProviderError:
                raise
            except MemoryError as e:
                raise ProviderError(
                    "Local embedding ran out of memory.",
                    code="local_oom",
                    retryable=False,
                ) from e
            except Exception as e:
                raise ProviderUnavailableError(
                    f"Local embedding failed: {type(e).__name__}",
                    code="local_inference_error",
                    retryable=True,
                ) from e

        validated = validate_embedding_vectors(embeddings, len(texts))
        return EmbeddingResponse(
            embeddings=validated,
            usage=ProviderUsage(
                input_tokens=total_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=Decimal("0"),
            ),
        )
