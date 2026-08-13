"""
API Retry Logic with Exponential Backoff

Provides robust error handling for API calls with automatic retry logic.
"""

import time
from typing import Callable, TypeVar, Optional
from functools import wraps

T = TypeVar('T')


class APIRetryError(Exception):
    """Raised when API retries are exhausted"""
    pass


def call_api_with_retry(
    api_func: Callable[[], T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    verbose: bool = True
) -> T:
    """
    Call API with exponential backoff retry logic.

    Args:
        api_func: Function that makes API call
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for delay between retries (default: 2.0)
        initial_delay: Initial delay in seconds (default: 1.0)
        verbose: Print retry messages (default: True)

    Returns:
        API response from successful call

    Raises:
        APIRetryError: If all retries exhausted

    Example:
        >>> from openai import OpenAI
        >>> client = OpenAI(api_key="sk-...")
        >>>
        >>> response = call_api_with_retry(
        ...     lambda: client.chat.completions.create(
        ...         model="gpt-4o-mini",
        ...         messages=[{"role": "user", "content": "Hello"}]
        ...     )
        ... )
    """
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return api_func()

        except Exception as e:
            last_error = e

            # Don't retry on final attempt
            if attempt >= max_retries:
                if verbose:
                    print(f"      ❌ API call failed after {max_retries + 1} attempts")
                raise APIRetryError(
                    f"API call failed after {max_retries + 1} attempts: {str(e)}"
                ) from e

            # Retry with exponential backoff
            if verbose:
                print(f"      ⚠️  API call failed (attempt {attempt + 1}/{max_retries + 1}): {str(e)[:80]}")
                print(f"      ⏳ Retrying in {delay:.1f}s...")

            time.sleep(delay)
            delay *= backoff_factor

    # Should never reach here
    raise APIRetryError(f"API call failed: {last_error}")


def with_retry(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    verbose: bool = True
):
    """
    Decorator to add retry logic to a function.

    Args:
        max_retries: Maximum retry attempts
        backoff_factor: Delay multiplier
        initial_delay: Initial delay in seconds
        verbose: Print retry messages

    Example:
        >>> @with_retry(max_retries=3)
        ... def call_api():
        ...     return client.chat.completions.create(...)
        ...
        >>> response = call_api()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return call_api_with_retry(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                backoff_factor=backoff_factor,
                initial_delay=initial_delay,
                verbose=verbose
            )
        return wrapper
    return decorator


def _extract_retry_after(error: Exception) -> Optional[float]:
    """Extract Retry-After seconds from an OpenAI RateLimitError, if present."""
    response = getattr(error, 'response', None)
    if response is not None:
        header = getattr(response, 'headers', {}).get('retry-after')
        if header is not None:
            try:
                return float(header)
            except (ValueError, TypeError):
                pass
    return None


def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error should trigger a retry.

    Args:
        error: Exception to check

    Returns:
        True if error is retryable (network, rate limit, etc.)

    Common retryable errors:
    - RateLimitError (429)
    - APIConnectionError (network issues)
    - APITimeoutError (request timeout)
    - InternalServerError (500)

    Non-retryable errors:
    - AuthenticationError (401)
    - InvalidRequestError (400)
    - PermissionDeniedError (403)
    """
    error_str = str(error).lower()

    # Retryable conditions
    retryable_keywords = [
        'rate limit',
        'timeout',
        'connection',
        'network',
        'internal server',
        '429',
        '500',
        '502',
        '503',
        '504'
    ]

    # Non-retryable conditions
    non_retryable_keywords = [
        'authentication',
        'invalid',
        'permission',
        '400',
        '401',
        '403',
        '404'
    ]

    # Check non-retryable first
    if any(keyword in error_str for keyword in non_retryable_keywords):
        return False

    # Check retryable
    if any(keyword in error_str for keyword in retryable_keywords):
        return True

    # Default: retry on unknown errors (conservative approach)
    return True


def call_api_with_smart_retry(
    api_func: Callable[[], T],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    verbose: bool = True
) -> T:
    """
    Call API with smart retry logic (only retries retryable errors).

    Args:
        api_func: Function that makes API call
        max_retries: Maximum retry attempts
        backoff_factor: Delay multiplier
        initial_delay: Initial delay in seconds
        verbose: Print retry messages

    Returns:
        API response

    Raises:
        APIRetryError: If retries exhausted
        Original exception: If error is non-retryable

    Example:
        >>> response = call_api_with_smart_retry(
        ...     lambda: client.chat.completions.create(...)
        ... )
    """
    delay = initial_delay
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return api_func()

        except Exception as e:
            last_error = e

            # Check if error is retryable
            if not is_retryable_error(e):
                if verbose:
                    print(f"      ❌ Non-retryable error: {str(e)[:100]}")
                raise  # Re-raise non-retryable errors immediately

            # Don't retry on final attempt
            if attempt >= max_retries:
                if verbose:
                    print(f"      ❌ API call failed after {max_retries + 1} attempts")
                raise APIRetryError(
                    f"API call failed after {max_retries + 1} attempts: {str(e)}"
                ) from e

            # Prefer the server's Retry-After header over the local backoff
            retry_after = _extract_retry_after(e)
            wait = retry_after if retry_after is not None else delay

            if verbose:
                print(f"      ⚠️  Retryable error (attempt {attempt + 1}/{max_retries + 1}): {str(e)[:80]}")
                print(f"      ⏳ Retrying in {wait:.1f}s...")

            time.sleep(wait)
            delay *= backoff_factor

    # Should never reach here
    raise APIRetryError(f"API call failed: {last_error}")
