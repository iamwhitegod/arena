"""Tests for arena.providers.base — contracts, types, and errors."""

import unittest
from decimal import Decimal
from pathlib import Path

from arena.providers.base import (
    ChatModel,
    ChatResponse,
    EmbeddingModel,
    EmbeddingResponse,
    ProviderAuthError,
    ProviderError,
    ProviderInvalidRequestError,
    ProviderRateLimitError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    ProviderUsage,
    ResponseMode,
    SpeechModel,
    TranscriptionResponse,
    TranscriptionSegment,
    WordTimestamp,
)


class TestProviderUsage(unittest.TestCase):

    def test_defaults(self):
        u = ProviderUsage()
        self.assertEqual(u.input_tokens, 0)
        self.assertEqual(u.total_tokens, 0)
        self.assertIsNone(u.estimated_cost_usd)
        self.assertIsNone(u.input_audio_seconds)

    def test_decimal_cost(self):
        u = ProviderUsage(estimated_cost_usd=Decimal("0.0025"))
        self.assertEqual(u.estimated_cost_usd, Decimal("0.0025"))

    def test_zero_cost_for_local(self):
        u = ProviderUsage(estimated_cost_usd=Decimal("0"))
        self.assertEqual(u.estimated_cost_usd, Decimal("0"))
        self.assertIsNotNone(u.estimated_cost_usd)  # Not None — known zero

    def test_audio_seconds(self):
        u = ProviderUsage(input_audio_seconds=120.5)
        self.assertEqual(u.input_audio_seconds, 120.5)


class TestResponseMode(unittest.TestCase):

    def test_is_str_enum(self):
        self.assertEqual(ResponseMode.TEXT, "text")
        self.assertEqual(ResponseMode.JSON, "json")
        self.assertIsInstance(ResponseMode.TEXT, str)


class TestChatResponse(unittest.TestCase):

    def test_text_response(self):
        r = ChatResponse(content="Hello world")
        self.assertEqual(r.content, "Hello world")
        self.assertIsNone(r.parsed)

    def test_json_response(self):
        r = ChatResponse(content='{"key": "val"}', parsed={"key": "val"})
        self.assertEqual(r.parsed["key"], "val")


class TestEmbeddingResponse(unittest.TestCase):

    def test_basic(self):
        r = EmbeddingResponse(embeddings=[[0.1, 0.2], [0.3, 0.4]])
        self.assertEqual(len(r.embeddings), 2)


class TestTranscriptionResponse(unittest.TestCase):

    def test_typed_fields(self):
        r = TranscriptionResponse(
            text="Hello",
            language="en",
            duration=5.0,
            words=[WordTimestamp(word="Hello", start=0.0, end=0.5)],
            segments=[TranscriptionSegment(id=0, start=0.0, end=0.5, text="Hello")],
        )
        self.assertIsInstance(r.words[0], WordTimestamp)
        self.assertIsInstance(r.segments[0], TranscriptionSegment)


class TestProviderErrors(unittest.TestCase):

    def test_base_error(self):
        e = ProviderError("test", code="test", retryable=False)
        self.assertEqual(e.code, "test")
        self.assertFalse(e.retryable)
        self.assertIsNone(e.retry_after)

    def test_timeout_defaults(self):
        e = ProviderTimeoutError()
        self.assertEqual(e.code, "timeout")
        self.assertTrue(e.retryable)

    def test_auth_defaults(self):
        e = ProviderAuthError()
        self.assertEqual(e.code, "auth")
        self.assertFalse(e.retryable)

    def test_rate_limit_with_retry_after(self):
        e = ProviderRateLimitError(retry_after=30.0)
        self.assertTrue(e.retryable)
        self.assertEqual(e.retry_after, 30.0)

    def test_response_error(self):
        e = ProviderResponseError("bad json")
        self.assertEqual(e.code, "response_error")
        self.assertTrue(e.retryable)

    def test_invalid_request(self):
        e = ProviderInvalidRequestError()
        self.assertFalse(e.retryable)

    def test_unavailable(self):
        e = ProviderUnavailableError()
        self.assertTrue(e.retryable)

    def test_exception_chaining(self):
        original = ValueError("original")
        try:
            raise ProviderError("wrapped", code="test", retryable=False) from original
        except ProviderError as e:
            self.assertIs(e.__cause__, original)


class TestABCEnforcement(unittest.TestCase):

    def test_cannot_instantiate_chat_model(self):
        with self.assertRaises(TypeError):
            ChatModel()

    def test_cannot_instantiate_embedding_model(self):
        with self.assertRaises(TypeError):
            EmbeddingModel()

    def test_cannot_instantiate_speech_model(self):
        with self.assertRaises(TypeError):
            SpeechModel()


if __name__ == "__main__":
    unittest.main()
