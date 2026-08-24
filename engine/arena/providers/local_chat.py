"""
Local chat adapter using llama-cpp-python with GGUF models.

Uses ``create_chat_completion()`` for role-aware formatting.  JSON mode
uses GBNF grammar when possible, falling back to ``extract_json()`` for
free-form output.
"""

import json
import time
from decimal import Decimal
from pathlib import Path
import threading
from typing import Optional

from .base import (
    ChatModel,
    ChatResponse,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUsage,
    ResponseMode,
)
from .json_utils import (
    build_gbnf_grammar,
    extract_json,
    recover_truncated_object_array,
)
from .local_limits import (
    MAX_INFERENCE_SECONDS,
    MAX_OUTPUT_TOKENS,
    MAX_RESPONSE_CHARS,
    bounded_usage_count,
    validate_messages,
    validate_temperature,
)
from ..models.hardware import (
    LocalResourceError,
    clamp_context,
    clamp_threads,
    enforce_model_resources,
)


class LocalChatModel(ChatModel):
    """Chat inference via llama-cpp-python on the local device."""

    def __init__(
        self,
        model_path: str,
        n_ctx: int = 4096,
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
                "llama-cpp-python is required for local chat inference. "
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
                verbose=False,
            )
        except MemoryError as e:
            raise ProviderError(
                "Local chat model does not fit in available memory.",
                code="local_oom",
                retryable=False,
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Failed to load local chat model: {type(e).__name__}",
                code="local_load_failed",
                retryable=False,
            ) from e

        self._model_path = model_path
        self._context_window_tokens = bounded_context
        self._default_output_tokens = min(
            MAX_OUTPUT_TOKENS, max(256, bounded_context // 8)
        )
        self._timeout_seconds = max(1.0, min(float(timeout_seconds), MAX_INFERENCE_SECONDS))
        self._cancelled = threading.Event()

    def __repr__(self) -> str:
        return f"LocalChatModel(model_path={self._model_path!r})"

    @property
    def concurrency_hint(self) -> int:
        return 1

    @property
    def context_window_tokens(self) -> int:
        return self._context_window_tokens

    @property
    def max_output_tokens(self) -> int:
        return self._default_output_tokens

    def supports_json_mode(self) -> bool:
        return True

    def cancel(self) -> None:
        """Cooperatively stop generation at the next native token boundary."""
        self._cancelled.set()

    def _is_cancelled(self) -> bool:
        event = getattr(self, "_cancelled", None)
        return bool(event and event.is_set())

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
        output_limit = min(
            max_output_tokens or self._default_output_tokens, MAX_OUTPUT_TOKENS
        )
        if self._is_cancelled():
            raise ProviderError(
                "Local inference was cancelled.", code="local_cancelled", retryable=False
            )
        kwargs: dict = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": output_limit,
            "stream": True,
        }

        # The chat API does not accept StoppingCriteriaList. Consume its native
        # token stream instead so timeout/cancellation checks happen in Python;
        # exceptions raised through a ctypes logits callback are ignored by
        # CPython and cannot safely stop generation.
        deadline = time.monotonic() + self._timeout_seconds

        # JSON mode: try GBNF grammar for constrained generation
        grammar_obj = None
        if response_mode == ResponseMode.JSON:
            try:
                from llama_cpp import LlamaGrammar
                gbnf_str = build_gbnf_grammar(json_schema)
                is_arena_grammar = bool(
                    json_schema
                    and json_schema.get("$id")
                    == "arena://schemas/compact-seeds-v1"
                )
                if is_arena_grammar and gbnf_str is not None:
                    grammar_obj = LlamaGrammar.from_string(gbnf_str)
                elif json_schema is not None and hasattr(
                    LlamaGrammar, "from_json_schema"
                ):
                    try:
                        grammar_obj = LlamaGrammar.from_json_schema(
                            json.dumps(json_schema)
                        )
                    except Exception:
                        grammar_obj = None
                if grammar_obj is None:
                    fallback_gbnf = build_gbnf_grammar(
                        None if json_schema is not None else json_schema
                    )
                    grammar_obj = LlamaGrammar.from_string(fallback_gbnf)
                kwargs["grammar"] = grammar_obj
            except Exception:
                grammar_obj = None  # fall back to extract_json

        try:
            native_response = self._llm.create_chat_completion(**kwargs)
            if isinstance(native_response, dict):
                # Compatibility with test doubles and older non-streaming
                # wrappers that return a complete response despite stream=True.
                response = native_response
            else:
                content_parts: list[str] = []
                finish_reason = None
                usage_data: dict = {}
                close_stream = getattr(native_response, "close", None)
                try:
                    for chunk in native_response:
                        if self._is_cancelled():
                            raise ProviderError(
                                "Local inference was cancelled.",
                                code="local_cancelled",
                                retryable=False,
                            )
                        if time.monotonic() >= deadline:
                            raise ProviderTimeoutError(
                                "Local inference exceeded Arena's time limit.",
                                retryable=False,
                            )
                        if not isinstance(chunk, dict):
                            continue
                        chunk_usage = chunk.get("usage")
                        if isinstance(chunk_usage, dict):
                            usage_data = chunk_usage
                        chunk_choices = chunk.get("choices")
                        if not isinstance(chunk_choices, list) or not chunk_choices:
                            continue
                        chunk_choice = chunk_choices[0]
                        if not isinstance(chunk_choice, dict):
                            continue
                        delta = chunk_choice.get("delta")
                        if isinstance(delta, dict):
                            piece = delta.get("content")
                            if isinstance(piece, str):
                                content_parts.append(piece)
                        if chunk_choice.get("finish_reason") is not None:
                            finish_reason = chunk_choice.get("finish_reason")
                finally:
                    if callable(close_stream):
                        close_stream()
                response = {
                    "choices": [{
                        "message": {"content": "".join(content_parts)},
                        "finish_reason": finish_reason,
                    }],
                    "usage": usage_data,
                }
        except ProviderError:
            raise
        except MemoryError as e:
            raise ProviderError(
                "Local model ran out of memory.",
                code="local_oom",
                retryable=False,
            ) from e
        except ValueError as e:
            message = str(e).lower()
            if "context window" in message or "requested tokens" in message:
                raise ProviderInvalidRequestError(
                    "Local prompt exceeds the configured model context window."
                ) from e
            raise ProviderInvalidRequestError(
                "Local inference rejected Arena's request."
            ) from e
        except Exception as e:
            raise ProviderUnavailableError(
                f"Local inference failed: {type(e).__name__}",
                code="local_inference_error",
                retryable=True,
            ) from e

        if self._is_cancelled():
            raise ProviderError(
                "Local inference was cancelled.", code="local_cancelled", retryable=False
            )
        if time.monotonic() >= deadline:
            raise ProviderTimeoutError(
                "Local inference exceeded Arena's time limit.", retryable=False
            )

        if not isinstance(response, dict):
            raise ProviderResponseError("Local model returned an invalid response.")
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise ProviderResponseError("Local model returned no completion choice.")
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict):
            raise ProviderResponseError("Local model returned an invalid message.")
        content = message.get("content", "") or ""
        if not isinstance(content, str) or len(content) > MAX_RESPONSE_CHARS:
            raise ProviderResponseError("Local model response exceeds Arena's size limit.")

        # Parse JSON when requested
        parsed = None
        if response_mode == ResponseMode.JSON:
            try:
                parsed = extract_json(content)
            except ProviderResponseError:
                is_compact_schema = bool(
                    json_schema
                    and json_schema.get("$id")
                    == "arena://schemas/compact-seeds-v1"
                )
                if choice.get("finish_reason") == "length" or is_compact_schema:
                    parsed = recover_truncated_object_array(content)
                    if parsed is not None:
                        content = json.dumps(parsed, ensure_ascii=False)
                if parsed is None:
                    raise ProviderResponseError(
                        "Local model returned unparseable JSON",
                        code="response_error",
                        retryable=False,
                    )

        # Token counts from llama.cpp
        usage_data = response.get("usage", {})
        if not isinstance(usage_data, dict):
            usage_data = {}
        input_tokens = bounded_usage_count(usage_data.get("prompt_tokens", 0))
        output_tokens = bounded_usage_count(usage_data.get("completion_tokens", 0))

        usage = ProviderUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            estimated_cost_usd=Decimal("0"),
        )

        return ChatResponse(content=content, parsed=parsed, usage=usage)
