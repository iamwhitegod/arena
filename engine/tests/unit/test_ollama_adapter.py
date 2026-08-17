"""Tests for the Ollama provider adapter."""

import json
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from arena.providers.base import (
    ProviderError,
    ProviderInvalidRequestError,
    ProviderResponseError,
    ProviderUnavailableError,
    ResponseMode,
)
from arena.providers.ollama_adapter import (
    OllamaChatModel,
    OllamaEmbeddingModel,
    _post,
    _validate_base_url,
)


class TestBaseUrlValidation(unittest.TestCase):

    def test_localhost_accepted(self):
        self.assertEqual(_validate_base_url("http://localhost:11434"), "http://localhost:11434")

    def test_127_0_0_1_accepted(self):
        self.assertEqual(_validate_base_url("http://127.0.0.1:11434"), "http://127.0.0.1:11434")

    def test_remote_host_rejected(self):
        with self.assertRaises(ProviderError) as ctx:
            _validate_base_url("http://ollama.example.com:11434")
        self.assertEqual(ctx.exception.code, "ollama_invalid_url")

    def test_trailing_slash_stripped(self):
        self.assertEqual(_validate_base_url("http://localhost:11434/"), "http://localhost:11434")

    def test_credentials_path_and_https_are_rejected(self):
        for value in (
            "http://user:pass@localhost:11434",
            "http://localhost:11434/api",
            "https://localhost:11434",
        ):
            with self.subTest(value=value), self.assertRaises(ProviderError):
                _validate_base_url(value)


class TestOllamaTransport(unittest.TestCase):
    @patch("requests.Session")
    def test_session_ignores_proxy_environment(self, session_class):
        session = session_class.return_value
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        response.iter_content.return_value = [b'{"ok": true}']
        session.post.return_value = response

        self.assertEqual(_post("http://localhost:11434", "/api/test", {}, 10), {"ok": True})
        self.assertFalse(session.trust_env)
        session.close.assert_called_once()
        response.close.assert_called_once()

    @patch("requests.Session")
    def test_connection_failure_still_closes_session(self, session_class):
        import requests

        session = session_class.return_value
        session.post.side_effect = requests.ConnectionError("refused")

        with self.assertRaises(ProviderUnavailableError):
            _post("http://localhost:11434", "/api/test", {}, 10)

        session.close.assert_called_once()

    @patch("requests.sessions.Session.post")
    def test_non_object_json_is_typed_response_error(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.headers = {}
        response.iter_content.return_value = [b"[]"]
        mock_post.return_value = response

        with self.assertRaises(ProviderResponseError) as ctx:
            _post("http://localhost:11434", "/api/test", {}, 10)

        self.assertEqual(ctx.exception.code, "ollama_invalid_response")

    @patch("requests.sessions.Session.post")
    def test_declared_oversized_response_is_rejected_before_reading(self, mock_post):
        response = MagicMock()
        response.status_code = 200
        response.headers = {"Content-Length": str(11 * 1024 * 1024)}
        mock_post.return_value = response

        with self.assertRaises(ProviderResponseError) as ctx:
            _post("http://localhost:11434", "/api/test", {}, 10)

        self.assertEqual(ctx.exception.code, "ollama_oversized")
        response.iter_content.assert_not_called()


class TestOllamaChatModel(unittest.TestCase):

    def test_repr(self):
        model = OllamaChatModel(model="llama3.2")
        self.assertEqual(repr(model), "OllamaChatModel(model='llama3.2')")

    def test_concurrency_hint(self):
        model = OllamaChatModel(model="llama3.2")
        self.assertEqual(model.concurrency_hint, 1)

    def test_configured_concurrency_hint_is_bounded(self):
        self.assertEqual(
            OllamaChatModel(model="llama3.2", concurrency_hint=3).concurrency_hint,
            3,
        )
        with self.assertRaises(ProviderInvalidRequestError):
            OllamaChatModel(model="llama3.2", concurrency_hint=5)

    def test_supports_json_mode(self):
        model = OllamaChatModel(model="llama3.2")
        self.assertTrue(model.supports_json_mode())

    @patch("requests.sessions.Session.post")
    def test_text_completion(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [
            json.dumps({
                "message": {"content": "Hello!"},
                "prompt_eval_count": 10,
                "eval_count": 5,
            }).encode()
        ]
        mock_post.return_value = mock_resp

        model = OllamaChatModel(model="llama3.2")
        result = model.complete(
            messages=[{"role": "user", "content": "hi"}],
            response_mode=ResponseMode.TEXT,
        )

        self.assertEqual(result.content, "Hello!")
        self.assertIsNone(result.parsed)
        self.assertEqual(result.usage.estimated_cost_usd, Decimal("0"))

    @patch("requests.sessions.Session.post")
    def test_connection_error(self, mock_post):
        import requests
        mock_post.side_effect = requests.ConnectionError("refused")

        model = OllamaChatModel(model="llama3.2")
        with self.assertRaises(ProviderUnavailableError):
            model.complete(
                messages=[{"role": "user", "content": "hi"}],
                response_mode=ResponseMode.TEXT,
            )

    @patch("requests.sessions.Session.post")
    def test_server_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_post.return_value = mock_resp

        model = OllamaChatModel(model="llama3.2")
        with self.assertRaises(ProviderUnavailableError):
            model.complete(
                messages=[{"role": "user", "content": "hi"}],
                response_mode=ResponseMode.TEXT,
            )


class TestOllamaEmbeddingModel(unittest.TestCase):

    @patch("requests.sessions.Session.post")
    def test_embed_returns_vectors(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [
            json.dumps({
                "embeddings": [[0.1, 0.2], [0.3, 0.4]],
                "prompt_eval_count": 10,
            }).encode()
        ]
        mock_post.return_value = mock_resp

        model = OllamaEmbeddingModel(model="nomic-embed-text")
        result = model.embed(["hello", "world"])

        self.assertEqual(len(result.embeddings), 2)
        self.assertEqual(result.usage.estimated_cost_usd, Decimal("0"))

    @patch("requests.sessions.Session.post")
    def test_mismatched_count_raises(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_content.return_value = [
            json.dumps({
                "embeddings": [[0.1, 0.2]],  # only 1, but asked for 2
                "prompt_eval_count": 10,
            }).encode()
        ]
        mock_post.return_value = mock_resp

        model = OllamaEmbeddingModel(model="nomic-embed-text")
        with self.assertRaises(ProviderResponseError):
            model.embed(["hello", "world"])


if __name__ == "__main__":
    unittest.main()
