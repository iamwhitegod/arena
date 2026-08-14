"""
Provider-aware retry with exponential backoff and jitter.

Retry decisions are driven by ProviderError.retryable — no provider_type
strings or exception-message matching.
"""

import random
import time
import math
from typing import Callable, TypeVar

from .base import ProviderError

T = TypeVar("T")

# Maximum delay between retries, regardless of retry_after header
MAX_RETRY_DELAY = 120.0  # 2 minutes


def retry_with_backoff(
    fn: Callable[[], T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    verbose: bool = True,
) -> T:
    """Retry fn on retryable ProviderErrors with exponential backoff and jitter.

    - If ProviderError.retryable is False, re-raises immediately.
    - If ProviderError.retry_after is set, uses that (capped at MAX_RETRY_DELAY).
    - Adds jitter (50-150% of base delay) to avoid thundering herd.
    - Non-ProviderError exceptions propagate without retry.
    """
    delay = initial_delay

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except ProviderError as e:
            if not e.retryable or attempt >= max_retries:
                raise

            if e.retry_after is not None and math.isfinite(e.retry_after):
                wait = min(max(e.retry_after, 0.0), MAX_RETRY_DELAY)
            else:
                # Jitter: 50-150% of current delay
                wait = delay * (0.5 + random.random())

            wait = min(max(wait, 0.0), MAX_RETRY_DELAY)

            if verbose:
                print(
                    f"      Retrying ({attempt + 1}/{max_retries}) "
                    f"after {wait:.1f}s: {e.code}"
                )
            time.sleep(wait)
            delay *= backoff_factor

    # Unreachable, but satisfies type checker
    raise RuntimeError("Retry loop exited unexpectedly")
