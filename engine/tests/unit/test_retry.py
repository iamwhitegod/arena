#!/usr/bin/env python3
"""
Unit Tests for arena.editorial.retry

Tests the API retry logic with exponential backoff.
"""

import unittest
import time
import sys
from pathlib import Path
from unittest.mock import call, patch

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arena.editorial.retry import (
    call_api_with_retry,
    call_api_with_smart_retry,
    with_retry,
    is_retryable_error,
    APIRetryError
)


class TestRetryLogic(unittest.TestCase):
    """Test basic retry logic"""

    def test_successful_call_no_retry(self):
        """Test that successful calls don't trigger retries"""
        call_count = {'count': 0}

        def successful_func():
            call_count['count'] += 1
            return {'success': True}

        result = call_api_with_retry(
            successful_func,
            max_retries=3,
            verbose=False
        )

        self.assertEqual(result, {'success': True})
        self.assertEqual(call_count['count'], 1, "Should only call once for success")

    def test_retry_on_failure(self):
        """Test that failures trigger retries"""
        call_count = {'count': 0}

        def failing_then_success():
            call_count['count'] += 1
            if call_count['count'] < 3:
                raise Exception("Simulated failure")
            return {'success': True}

        result = call_api_with_retry(
            failing_then_success,
            max_retries=3,
            initial_delay=0.01,
            verbose=False
        )

        self.assertEqual(result, {'success': True})
        self.assertEqual(call_count['count'], 3, "Should retry until success")

    def test_max_retries_exhausted(self):
        """Test that exhausted retries raise APIRetryError"""
        call_count = {'count': 0}

        def always_failing():
            call_count['count'] += 1
            raise Exception("Persistent failure")

        with self.assertRaises(APIRetryError) as context:
            call_api_with_retry(
                always_failing,
                max_retries=2,
                initial_delay=0.01,
                verbose=False
            )

        self.assertEqual(call_count['count'], 3, "Should try initial + 2 retries")
        self.assertIn("Persistent failure", str(context.exception))

    def test_exponential_backoff_timing(self):
        """Test that exponential backoff requests the expected delays"""
        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Test failure")

        with patch('arena.editorial.retry.time.sleep') as mock_sleep:
            with self.assertRaises(APIRetryError):
                call_api_with_retry(
                    failing_func,
                    max_retries=2,
                    initial_delay=0.1,
                    backoff_factor=2.0,
                    verbose=False
                )

        self.assertEqual(call_count, 3)
        self.assertEqual(mock_sleep.call_args_list, [call(0.1), call(0.2)])


class TestSmartRetry(unittest.TestCase):
    """Test smart retry logic (retryable vs non-retryable errors)"""

    def test_is_retryable_error_detection(self):
        """Test error classification"""
        # Retryable errors
        self.assertTrue(is_retryable_error(Exception("Rate limit exceeded (429)")))
        self.assertTrue(is_retryable_error(Exception("503 Service Unavailable")))
        self.assertTrue(is_retryable_error(Exception("Connection timeout")))
        self.assertTrue(is_retryable_error(Exception("Network error")))

        # Non-retryable errors
        self.assertFalse(is_retryable_error(Exception("Authentication failed (401)")))
        self.assertFalse(is_retryable_error(Exception("Invalid request (400)")))
        self.assertFalse(is_retryable_error(Exception("Forbidden (403)")))
        self.assertFalse(is_retryable_error(Exception("Invalid API key")))

    def test_smart_retry_retryable_error(self):
        """Test smart retry retries on retryable errors"""
        call_count = {'count': 0}

        def rate_limit_error():
            call_count['count'] += 1
            raise Exception("Rate limit exceeded (429)")

        with self.assertRaises(APIRetryError):
            call_api_with_smart_retry(
                rate_limit_error,
                max_retries=2,
                initial_delay=0.01,
                verbose=False
            )

        self.assertEqual(call_count['count'], 3, "Should retry on rate limit")

    def test_smart_retry_non_retryable_error(self):
        """Test smart retry doesn't retry on non-retryable errors"""
        call_count = {'count': 0}

        def auth_error():
            call_count['count'] += 1
            raise Exception("Authentication failed (401)")

        with self.assertRaises(Exception) as context:
            call_api_with_smart_retry(
                auth_error,
                max_retries=3,
                initial_delay=0.01,
                verbose=False
            )

        self.assertEqual(call_count['count'], 1, "Should NOT retry on auth error")
        self.assertIn("Authentication", str(context.exception))


class TestRetryDecorator(unittest.TestCase):
    """Test @with_retry decorator"""

    def test_decorator_on_function(self):
        """Test decorator works on regular functions"""
        call_count = {'count': 0}

        @with_retry(max_retries=2, initial_delay=0.01)
        def decorated_func():
            call_count['count'] += 1
            if call_count['count'] < 2:
                raise Exception("Fail once")
            return "success"

        result = decorated_func()
        self.assertEqual(result, "success")
        self.assertEqual(call_count['count'], 2)

    def test_decorator_with_arguments(self):
        """Test decorator works with function arguments"""
        @with_retry(max_retries=1, initial_delay=0.01)
        def func_with_args(x, y, z=10):
            return x + y + z

        result = func_with_args(5, 3, z=2)
        self.assertEqual(result, 10)

    def test_decorator_preserves_exceptions(self):
        """Test decorator preserves original exception on exhausted retries"""
        @with_retry(max_retries=1, initial_delay=0.01)
        def failing_func():
            raise ValueError("Custom error")

        with self.assertRaises(APIRetryError) as context:
            failing_func()

        self.assertIn("Custom error", str(context.exception))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    def test_zero_retries(self):
        """Test with max_retries=0"""
        call_count = {'count': 0}

        def failing_func():
            call_count['count'] += 1
            raise Exception("Fail")

        with self.assertRaises(APIRetryError):
            call_api_with_retry(
                failing_func,
                max_retries=0,
                initial_delay=0.01,
                verbose=False
            )

        self.assertEqual(call_count['count'], 1, "Should only try once with 0 retries")

    def test_very_short_delay(self):
        """Test with very short initial delay"""
        call_count = {'count': 0}

        def failing_func():
            call_count['count'] += 1
            raise Exception("Fail")

        start_time = time.time()
        try:
            call_api_with_retry(
                failing_func,
                max_retries=2,
                initial_delay=0.001,
                verbose=False
            )
        except APIRetryError:
            pass
        elapsed = time.time() - start_time

        # Should complete quickly with short delays
        self.assertLess(elapsed, 0.1, "Should complete quickly with short delays")

    def test_none_return_value(self):
        """Test function that returns None"""
        def returns_none():
            return None

        result = call_api_with_retry(
            returns_none,
            max_retries=1,
            verbose=False
        )

        self.assertIsNone(result)

    def test_exception_in_exception(self):
        """Test nested exception handling"""
        def nested_exception():
            try:
                raise ValueError("Inner error")
            except ValueError as e:
                raise Exception(f"Outer error: {e}")

        with self.assertRaises(APIRetryError) as context:
            call_api_with_retry(
                nested_exception,
                max_retries=1,
                initial_delay=0.01,
                verbose=False
            )

        self.assertIn("Outer error", str(context.exception))


class TestRetryMetrics(unittest.TestCase):
    """Test retry metrics and logging"""

    def test_verbose_output(self):
        """Test that verbose mode produces output"""
        # This is more of a smoke test - just ensure verbose doesn't crash
        call_count = {'count': 0}

        def failing_func():
            call_count['count'] += 1
            if call_count['count'] < 2:
                raise Exception("Fail")
            return "success"

        result = call_api_with_retry(
            failing_func,
            max_retries=2,
            initial_delay=0.01,
            verbose=True  # Enable verbose output
        )

        self.assertEqual(result, "success")

    def test_retry_preserves_error_message(self):
        """Test that error messages are preserved through retries"""
        custom_message = "Very specific error message: ABC123"

        def custom_error():
            raise Exception(custom_message)

        with self.assertRaises(APIRetryError) as context:
            call_api_with_retry(
                custom_error,
                max_retries=1,
                initial_delay=0.01,
                verbose=False
            )

        self.assertIn(custom_message, str(context.exception))


if __name__ == '__main__':
    # Run tests with verbosity
    unittest.main(verbosity=2)
