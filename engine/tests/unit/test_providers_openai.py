"""Tests for OpenAI adapter — request serialization, error normalization, and sanitization."""

import json
import pickle
from pathlib import Path
from types import SimpleNamespace
import tempfile
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
from arena.providers.openai_adapter import (
    OpenAIChatModel,
    OpenAIEmbeddingModel,
    OpenAISpeechModel,
)


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
        self.assertEqual(call_kwargs.kwargs["max_completion_tokens"], 8192)

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
    def test_per_call_output_limit_is_forwarded(self, _):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")
        model._client = MagicMock()
        model._client.chat.completions.create.return_value = self._mock_client_response("ok")

        model.complete(
            messages=[{"role": "user", "content": "hi"}],
            max_output_tokens=600,
        )

        call_kwargs = model._client.chat.completions.create.call_args.kwargs
        self.assertEqual(call_kwargs["max_completion_tokens"], 600)

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

    @patch("arena.providers.openai_adapter.OpenAIChatModel._ensure_client")
    def test_json_mode_rejects_non_object_json(self, _):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")
        model._client = MagicMock()
        model._client.chat.completions.create.return_value = self._mock_client_response("[]")

        with self.assertRaises(ProviderResponseError):
            model.complete(
                messages=[{"role": "user", "content": "hi"}],
                response_mode=ResponseMode.JSON,
            )

    @patch("arena.providers.openai_adapter.OpenAIChatModel._ensure_client")
    def test_json_mode_rejects_non_finite_nested_values(self, _):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")
        model._client = MagicMock()
        model._client.chat.completions.create.return_value = self._mock_client_response(
            '{"score": NaN}'
        )

        with self.assertRaises(ProviderResponseError):
            model.complete(
                messages=[{"role": "user", "content": "hi"}],
                response_mode=ResponseMode.JSON,
            )

    def test_rejects_extra_message_fields_and_invalid_temperature(self):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")

        with self.assertRaises(ProviderInvalidRequestError):
            model.complete([{"role": "user", "content": "hi", "name": "hidden"}])
        with self.assertRaises(ProviderInvalidRequestError):
            model.complete([{"role": "user", "content": "hi"}], temperature=float("nan"))

    @patch("arena.providers.openai_adapter.OpenAIChatModel._ensure_client")
    def test_malformed_chat_response_is_normalized(self, _):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")
        model._client = MagicMock()
        model._client.chat.completions.create.return_value = SimpleNamespace(choices=[])

        with self.assertRaisesRegex(ProviderResponseError, "invalid chat response"):
            model.complete([{"role": "user", "content": "hi"}])


class TestOpenAIEmbeddingValidation(unittest.TestCase):

    def test_rejects_empty_input_before_constructing_client(self):
        model = OpenAIEmbeddingModel(api_key="sk-test")

        with self.assertRaises(ProviderInvalidRequestError):
            model.embed([])

        self.assertIsNone(model._client)

    @patch("arena.providers.openai_adapter.OpenAIEmbeddingModel._ensure_client")
    def test_rejects_wrong_embedding_count_and_non_finite_values(self, _):
        model = OpenAIEmbeddingModel(api_key="sk-test")
        model._client = MagicMock()

        model._client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.1, 0.2])],
            usage=SimpleNamespace(total_tokens=3),
        )
        with self.assertRaises(ProviderResponseError):
            model.embed(["one", "two"])

        model._client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(embedding=[float("inf")])],
            usage=SimpleNamespace(total_tokens=3),
        )
        with self.assertRaises(ProviderResponseError):
            model.embed(["one"])


class TestOpenAISpeechValidation(unittest.TestCase):

    def _audio_file(self, directory: str) -> Path:
        audio = Path(directory) / "sample.mp3"
        audio.write_bytes(b"audio")
        return audio

    @patch("arena.providers.openai_adapter.OpenAISpeechModel._ensure_client")
    def test_validates_response_timestamps(self, _):
        model = OpenAISpeechModel(api_key="sk-test")
        model._client = MagicMock()
        model._client.audio.transcriptions.create.return_value = SimpleNamespace(
            text="hello",
            language="en",
            duration=1.0,
            words=[SimpleNamespace(word="hello", start=0.0, end=3.0)],
            segments=[],
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ProviderResponseError):
                model.transcribe(self._audio_file(temp_dir))

    def test_rejects_missing_audio_file_before_constructing_client(self):
        model = OpenAISpeechModel(api_key="sk-test")

        with self.assertRaises(ProviderInvalidRequestError):
            model.transcribe(Path("does-not-exist.mp3"))

        self.assertIsNone(model._client)


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

    def test_credential_bearing_adapters_cannot_be_serialized(self):
        secret = "sk-canary-secret-value"
        adapters = [
            OpenAIChatModel(secret),
            OpenAIEmbeddingModel(secret),
            OpenAISpeechModel(secret),
        ]

        for adapter in adapters:
            with self.subTest(adapter=type(adapter).__name__):
                self.assertNotIn(secret, repr(adapter))
                self.assertNotIn(secret, repr(vars(adapter)))
                with self.assertRaises(TypeError):
                    pickle.dumps(adapter)

    @patch("openai.OpenAI")
    def test_client_disables_sdk_retries_and_sets_timeout(self, mock_openai):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")

        model._ensure_client()

        self.assertEqual(mock_openai.call_args.kwargs["max_retries"], 0)
        self.assertEqual(mock_openai.call_args.kwargs["timeout"], 120.0)

    def test_close_releases_client_and_credential_factory(self):
        model = OpenAIChatModel(api_key="sk-test", model="gpt-4o")
        client = MagicMock()
        model._client = client

        model.close()

        client.close.assert_called_once_with()
        self.assertIsNone(model._client)
        self.assertIsNone(model._build_client)

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
