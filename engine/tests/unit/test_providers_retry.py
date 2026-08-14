"""Tests for retry_with_backoff — retryable vs non-retryable, jitter, cap."""

import unittest
from unittest.mock import patch

from arena.providers.base import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
)
from arena.providers.retry import MAX_RETRY_DELAY, retry_with_backoff


class TestRetryWithBackoff(unittest.TestCase):

    @patch("arena.providers.retry.time.sleep")
    def test_success_no_retry(self, mock_sleep):
        result = retry_with_backoff(lambda: "ok", verbose=False)
        self.assertEqual(result, "ok")
        mock_sleep.assert_not_called()

    @patch("arena.providers.retry.time.sleep")
    def test_non_retryable_raises_immediately(self, mock_sleep):
        calls = []

        def failing():
            calls.append(1)
            raise ProviderAuthError("denied", code="auth", retryable=False)

        with self.assertRaises(ProviderAuthError):
            retry_with_backoff(failing, max_retries=3, verbose=False)

        self.assertEqual(len(calls), 1)  # Only called once
        mock_sleep.assert_not_called()

    @patch("arena.providers.retry.time.sleep")
    def test_retryable_retries_up_to_max(self, mock_sleep):
        calls = []

        def failing():
            calls.append(1)
            raise ProviderRateLimitError("limited", code="rate_limit", retryable=True)

        with self.assertRaises(ProviderRateLimitError):
            retry_with_backoff(failing, max_retries=3, verbose=False)

        self.assertEqual(len(calls), 4)  # 1 initial + 3 retries
        self.assertEqual(mock_sleep.call_count, 3)

    @patch("arena.providers.retry.time.sleep")
    def test_succeeds_after_retry(self, mock_sleep):
        calls = []

        def eventually_succeeds():
            calls.append(1)
            if len(calls) < 3:
                raise ProviderRateLimitError("limited", code="rate_limit", retryable=True)
            return "success"

        result = retry_with_backoff(eventually_succeeds, max_retries=5, verbose=False)
        self.assertEqual(result, "success")
        self.assertEqual(len(calls), 3)

    @patch("arena.providers.retry.time.sleep")
    def test_retry_after_is_honored(self, mock_sleep):
        calls = []

        def failing():
            calls.append(1)
            if len(calls) == 1:
                raise ProviderRateLimitError(
                    "limited", code="rate_limit", retryable=True, retry_after=30.0
                )
            return "ok"

        result = retry_with_backoff(failing, max_retries=3, verbose=False)
        self.assertEqual(result, "ok")
        # First sleep should be 30.0 (from retry_after)
        first_sleep = mock_sleep.call_args_list[0][0][0]
        self.assertEqual(first_sleep, 30.0)

    @patch("arena.providers.retry.time.sleep")
    def test_retry_after_capped_at_max(self, mock_sleep):
        calls = []

        def failing():
            calls.append(1)
            if len(calls) == 1:
                raise ProviderRateLimitError(
                    "limited", code="rate_limit", retryable=True, retry_after=3600.0
                )
            return "ok"

        result = retry_with_backoff(failing, max_retries=3, verbose=False)
        self.assertEqual(result, "ok")
        first_sleep = mock_sleep.call_args_list[0][0][0]
        self.assertLessEqual(first_sleep, MAX_RETRY_DELAY)

    @patch("arena.providers.retry.time.sleep")
    def test_invalid_retry_after_never_reaches_sleep(self, mock_sleep):
        calls = []

        def failing():
            calls.append(1)
            if len(calls) == 1:
                raise ProviderRateLimitError(
                    "limited", code="rate_limit", retryable=True, retry_after=-5.0
                )
            return "ok"

        self.assertEqual(
            retry_with_backoff(failing, max_retries=1, verbose=False),
            "ok",
        )
        mock_sleep.assert_called_once_with(0.0)

    @patch("arena.providers.retry.random.random", return_value=0.5)
    @patch("arena.providers.retry.time.sleep")
    def test_jitter_applied(self, mock_sleep, mock_random):
        calls = []

        def failing():
            calls.append(1)
            if len(calls) == 1:
                raise ProviderError("err", code="err", retryable=True)
            return "ok"

        retry_with_backoff(failing, max_retries=3, initial_delay=1.0, verbose=False)
        # With random()=0.5, jitter = 1.0 * (0.5 + 0.5) = 1.0
        first_sleep = mock_sleep.call_args_list[0][0][0]
        self.assertAlmostEqual(first_sleep, 1.0)

    @patch("arena.providers.retry.time.sleep")
    def test_non_provider_error_propagates(self, mock_sleep):
        def failing():
            raise ValueError("not a provider error")

        with self.assertRaises(ValueError):
            retry_with_backoff(failing, max_retries=3, verbose=False)

        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
