"""
Provider-aware retry with exponential backoff.

Retry decisions are driven by ProviderError.retryable — no provider_type
strings or exception-message matching.
"""

import time
from typing import Callable, TypeVar

from .base import ProviderError

T = TypeVar("T")


def retry_with_backoff(
    fn: Callable[[], T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    verbose: bool = True,
) -> T:
    """Retry fn on retryable ProviderErrors with exponential backoff.

    - If ProviderError.retryable is False, re-raises immediately.
    - If ProviderError.retry_after is set, uses that delay instead of backoff.
    - Non-ProviderError exceptions propagate without retry.
    """
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except ProviderError as e:
            if not e.retryable or attempt >= max_retries:
                raise

            wait = e.retry_after if e.retry_after is not None else delay
            if verbose:
                print(
                    f"      Retrying ({attempt + 1}/{max_retries}) "
                    f"after {wait:.1f}s: {e.code}"
                )
            time.sleep(wait)
            delay *= backoff_factor

    # Unreachable, but satisfies type checker
    raise RuntimeError("Retry loop exited unexpectedly")
