"""Tests for OpenAI adapter — request serialization, error normalization, and sanitization."""

import json
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from arena.providers.base import (
    ProviderAuthError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ResponseMode,
)
from arena.providers.openai_adapter import OpenAIChatModel, OpenAIEmbeddingModel


class TestOpenAIChatModelRequestSerialization(unittest.TestCase):

    def _mock_client_response(self, content="{}", prompt_tokens=100, completion_tokens=50):
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = content
        response.usage.prompt_tokens = prompt_tokens
        response.usage.completion_tokens = completion_tokens
        response.usage.total_tokens = prompt_tokens + completion_tokens
        return response

    @patch("arena.providers.openai_adapter.OpenAIChatModel._ensure_client")
    def test_text_mode_omits_response_format(self, _):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")
        model._client = MagicMock()
        model._client.chat.completions.create.return_value = self._mock_client_response("hello")

        model.complete(
            messages=[{"role": "user", "content": "hi"}],
            response_mode=ResponseMode.TEXT,
        )

        call_kwargs = model._client.chat.completions.create.call_args
        self.assertNotIn("response_format", call_kwargs.kwargs)

    @patch("arena.providers.openai_adapter.OpenAIChatModel._ensure_client")
    def test_json_mode_includes_response_format(self, _):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")
        model._client = MagicMock()
        model._client.chat.completions.create.return_value = self._mock_client_response('{"key": "val"}')

        result = model.complete(
            messages=[{"role": "user", "content": "hi"}],
            response_mode=ResponseMode.JSON,
        )

        call_kwargs = model._client.chat.completions.create.call_args
        self.assertEqual(call_kwargs.kwargs.get("response_format"), {"type": "json_object"})
        self.assertEqual(result.parsed, {"key": "val"})

    @patch("arena.providers.openai_adapter.OpenAIChatModel._ensure_client")
    def test_text_mode_returns_none_parsed(self, _):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")
        model._client = MagicMock()
        model._client.chat.completions.create.return_value = self._mock_client_response("hello world")

        result = model.complete(
            messages=[{"role": "user", "content": "hi"}],
            response_mode=ResponseMode.TEXT,
        )

        self.assertEqual(result.content, "hello world")
        self.assertIsNone(result.parsed)

    @patch("arena.providers.openai_adapter.OpenAIChatModel._ensure_client")
    def test_usage_has_decimal_cost(self, _):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")
        model._client = MagicMock()
        model._client.chat.completions.create.return_value = self._mock_client_response("{}")

        result = model.complete(
            messages=[{"role": "user", "content": "hi"}],
            response_mode=ResponseMode.JSON,
        )

        self.assertIsInstance(result.usage.estimated_cost_usd, Decimal)


class TestOpenAIChatModelErrorNormalization(unittest.TestCase):

    def test_auth_error(self):
        error = OpenAIChatModel._translate_error(
            _make_openai_error("AuthenticationError")
        )
        self.assertIsInstance(error, ProviderAuthError)
        self.assertFalse(error.retryable)

    def test_rate_limit_error(self):
        error = OpenAIChatModel._translate_error(
            _make_openai_error("RateLimitError")
        )
        self.assertIsInstance(error, ProviderRateLimitError)
        self.assertTrue(error.retryable)

    def test_bad_request_error(self):
        error = OpenAIChatModel._translate_error(
            _make_openai_error("BadRequestError")
        )
        self.assertIsInstance(error, ProviderInvalidRequestError)
        self.assertFalse(error.retryable)

    def test_timeout_error(self):
        error = OpenAIChatModel._translate_error(
            _make_openai_error("APITimeoutError")
        )
        self.assertIsInstance(error, ProviderTimeoutError)
        self.assertTrue(error.retryable)

    def test_connection_error(self):
        error = OpenAIChatModel._translate_error(
            _make_openai_error("APIConnectionError")
        )
        self.assertIsInstance(error, ProviderUnavailableError)
        self.assertTrue(error.retryable)


class TestOpenAIChatModelErrorSanitization(unittest.TestCase):

    def test_invalid_json_error_does_not_leak_content(self):
        """ProviderResponseError must not contain model output."""
        model = OpenAIChatModel.__new__(OpenAIChatModel)
        model._client = MagicMock()
        model._model = "gpt-4o"

        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = "This is SECRET transcript content that should not leak"
        response.usage.prompt_tokens = 100
        response.usage.completion_tokens = 50
        response.usage.total_tokens = 150
        model._client.chat.completions.create.return_value = response

        with self.assertRaises(ProviderResponseError) as ctx:
            model.complete(
                messages=[{"role": "user", "content": "hi"}],
                response_mode=ResponseMode.JSON,
            )

        self.assertNotIn("SECRET", str(ctx.exception))
        self.assertNotIn("transcript", str(ctx.exception))

    def test_bad_request_error_does_not_leak_exception(self):
        error = OpenAIChatModel._translate_error(
            _make_openai_error("BadRequestError", "Sensitive details here")
        )
        self.assertNotIn("Sensitive", str(error))

    def test_unknown_error_does_not_leak_exception(self):
        error = OpenAIChatModel._translate_error(
            ValueError("Internal secret data")
        )
        self.assertNotIn("secret", str(error))


def _make_openai_error(error_type: str, message: str = "test error"):
    """Create a mock that isinstance-matches OpenAI error classes."""
    try:
        import openai
        error_cls = getattr(openai, error_type, None)
        if error_cls is None:
            raise ImportError
        # Create mock exception instances
        mock = MagicMock(spec=error_cls)
        mock.__class__ = error_cls
        mock.__str__ = lambda self: message
        mock.response = None
        return mock
    except ImportError:
        # If openai not installed, return a generic exception
        # The translate_error function handles ImportError gracefully
        return ValueError(message)


if __name__ == "__main__":
    unittest.main()
