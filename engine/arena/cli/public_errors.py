"""Safe formatting for errors that cross Arena's public CLI boundary."""

import re
import uuid

from arena.providers.base import ProviderError


_ANSI_RE = re.compile(
    r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))"
)
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")
_SECRET_RE = re.compile(
    r"(?i)(?:bearer\s+\S+|sk-[a-z0-9_-]{8,}|"
    r"(?:api[_-]?key|authorization|password|secret|token)\s*[:=]\s*\S+)"
)


def _safe_provider_message(message: str) -> str:
    sanitized = _ANSI_RE.sub("", message)
    sanitized = _CONTROL_RE.sub("", sanitized)
    sanitized = _SECRET_RE.sub("[redacted]", sanitized)
    sanitized = " ".join(sanitized.split())
    return sanitized[:500] or "Provider request failed."


def format_public_error(error: Exception, operation: str = "Error") -> str:
    """Return one safe, correlation-friendly public error line.

    Non-provider exception text is intentionally not exposed because native
    errors may contain paths, subprocess output, media text, or credentials.
    """
    correlation_id = uuid.uuid4().hex[:12]
    if isinstance(error, ProviderError):
        code = re.sub(r"[^a-z0-9_-]", "_", error.code.lower())[:64] or "provider_error"
        message = _safe_provider_message(str(error))
        retryable = str(bool(error.retryable)).lower()
    else:
        code = "internal_error"
        message = "An unexpected internal error occurred."
        retryable = "false"
    return (
        f"❌ {operation} [{code}; retryable={retryable}; ref={correlation_id}]: "
        f"{message}"
    )
