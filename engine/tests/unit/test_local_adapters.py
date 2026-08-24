"""Deterministic local-adapter bounds, cancellation, and translation tests."""

import unittest
from decimal import Decimal
from pathlib import Path
import threading
from unittest.mock import MagicMock, patch

from arena.providers.base import (
    ProviderError,
    ProviderInvalidRequestError,
    ProviderResponseError,
    ProviderUsage,
    ResponseMode,
    TranscriptionSegment,
    WordTimestamp,
)


class TestLocalSpeechModelImportError(unittest.TestCase):

    def test_missing_faster_whisper_raises_provider_error(self):
        with patch.dict("sys.modules", {"faster_whisper": None}):
            # Force re-import to trigger the lazy import check
            import importlib
            import arena.providers.local_speech as mod
            importlib.reload(mod)
            with self.assertRaises(ProviderError) as ctx:
                mod.LocalSpeechModel()
            self.assertEqual(ctx.exception.code, "local_unavailable")
            self.assertIn("faster-whisper", str(ctx.exception))

    def test_model_alias_cannot_trigger_implicit_download(self):
        with patch.dict("sys.modules", {"faster_whisper": MagicMock()}):
            import importlib
            import arena.providers.local_speech as mod
            importlib.reload(mod)
            with self.assertRaises(ProviderError) as ctx:
                mod.LocalSpeechModel("base")
            self.assertEqual(ctx.exception.code, "local_no_model")


class TestLocalSpeechModelTranscribe(unittest.TestCase):

    def test_close_unloads_native_model_once(self):
        from arena.providers.local_speech import LocalSpeechModel

        wrapper = MagicMock()
        model = LocalSpeechModel.__new__(LocalSpeechModel)
        model._model = wrapper

        model.close()
        model.close()

        wrapper.model.unload_model.assert_called_once_with()
        self.assertIsNone(model._model)

    @patch("arena.providers.local_speech.WhisperModel", create=True)
    def test_transcribe_returns_typed_response(self, _mock_cls):
        # Build a mock faster-whisper model
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.start = 0.0
        mock_segment.end = 5.0
        mock_segment.text = " Hello world"
        mock_word1 = MagicMock(word="Hello", start=0.0, end=0.5)
        mock_word2 = MagicMock(word="world", start=0.5, end=1.0)
        mock_segment.words = [mock_word1, mock_word2]

        mock_info = MagicMock()
        mock_info.duration = 5.0
        mock_info.language = "en"

        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        # Patch the import and construct
        with patch("arena.providers.local_speech.WhisperModel", return_value=mock_model):
            from arena.providers.local_speech import LocalSpeechModel
            model = LocalSpeechModel.__new__(LocalSpeechModel)
            model._model = mock_model

        result = model.transcribe(Path("test.mp3"))

        self.assertEqual(result.text, "Hello world")
        self.assertEqual(result.language, "en")
        self.assertEqual(result.duration, 5.0)
        self.assertEqual(len(result.words), 2)
        self.assertEqual(len(result.segments), 1)
        self.assertEqual(result.usage.estimated_cost_usd, Decimal("0"))
        self.assertEqual(result.usage.input_audio_seconds, 5.0)
        _, kwargs = mock_model.transcribe.call_args
        self.assertTrue(kwargs["vad_filter"])
        self.assertEqual(kwargs["vad_parameters"]["threshold"], 0.5)

    def test_cancelled_transcription_never_calls_runtime(self):
        from arena.providers.local_speech import LocalSpeechModel
        model = LocalSpeechModel.__new__(LocalSpeechModel)
        model._model = MagicMock()
        model._cancelled = threading.Event()
        model.cancel()

        with self.assertRaises(ProviderError) as ctx:
            model.transcribe(Path("test.mp3"))

        self.assertEqual(ctx.exception.code, "local_cancelled")
        model._model.transcribe.assert_not_called()

    @patch("arena.providers.local_speech.time.monotonic", side_effect=[0.0, 301.0])
    def test_transcription_timeout_stops_segment_consumption(self, _clock):
        from arena.providers.local_speech import LocalSpeechModel
        model = LocalSpeechModel.__new__(LocalSpeechModel)
        model._model = MagicMock()
        model._model.transcribe.return_value = ([MagicMock()], MagicMock())
        model._timeout_seconds = 300.0

        with self.assertRaises(ProviderError) as ctx:
            model.transcribe(Path("test.mp3"))

        self.assertEqual(ctx.exception.code, "timeout")

    @patch("arena.providers.local_speech.time.monotonic", side_effect=[0.0, 601.0])
    def test_transcription_timeout_scales_with_audio_duration(self, _clock):
        mock_model = MagicMock()
        mock_segment = MagicMock(start=0.0, end=1.0, text=" Hello", words=[])
        mock_info = MagicMock(duration=600.0, language="en")
        mock_model.transcribe.return_value = ([mock_segment], mock_info)

        from arena.providers.local_speech import LocalSpeechModel
        model = LocalSpeechModel.__new__(LocalSpeechModel)
        model._model = mock_model
        model._timeout_seconds = 300.0

        result = model.transcribe(Path("test.mp3"))

        self.assertEqual(result.text, "Hello")
        self.assertEqual(model._effective_timeout_seconds(600.0), 1320.0)

    def test_transcription_timeout_remains_bounded(self):
        from arena.providers.local_limits import MAX_SPEECH_INFERENCE_SECONDS
        from arena.providers.local_speech import LocalSpeechModel

        model = LocalSpeechModel.__new__(LocalSpeechModel)
        model._timeout_seconds = 300.0

        self.assertEqual(
            model._effective_timeout_seconds(10_000.0),
            MAX_SPEECH_INFERENCE_SECONDS,
        )

    def test_duration_over_cap_is_rejected(self):
        mock_model = MagicMock()
        mock_info = MagicMock(duration=700.0, language="en")
        mock_model.transcribe.return_value = ([], mock_info)

        from arena.providers.local_speech import LocalSpeechModel
        model = LocalSpeechModel.__new__(LocalSpeechModel)
        model._model = mock_model

        with self.assertRaises(ProviderResponseError) as ctx:
            model.transcribe(Path("test.mp3"))
        self.assertEqual(ctx.exception.code, "local_invalid_response")

    @patch("arena.providers.local_speech._MAX_SEGMENTS", 1)
    def test_segment_cap_raises_instead_of_truncating(self):
        mock_model = MagicMock()
        mock_info = MagicMock(duration=5.0, language="en")
        mock_model.transcribe.return_value = ([MagicMock(), MagicMock()], mock_info)

        from arena.providers.local_speech import LocalSpeechModel
        model = LocalSpeechModel.__new__(LocalSpeechModel)
        model._model = mock_model

        with self.assertRaises(ProviderResponseError) as ctx:
            model.transcribe(Path("test.mp3"))
        self.assertEqual(ctx.exception.code, "local_resource_limit")


class TestLocalChatModelImportError(unittest.TestCase):

    def test_missing_llama_cpp_raises_provider_error(self):
        with patch.dict("sys.modules", {"llama_cpp": None}):
            import importlib
            import arena.providers.local_chat as mod
            importlib.reload(mod)
            with self.assertRaises(ProviderError) as ctx:
                mod.LocalChatModel(model_path="/fake/model.gguf")
            self.assertEqual(ctx.exception.code, "local_unavailable")
            self.assertIn("llama-cpp-python", str(ctx.exception))


class TestLocalChatModelComplete(unittest.TestCase):

    def _make_model(self):
        from arena.providers.local_chat import LocalChatModel
        model = LocalChatModel.__new__(LocalChatModel)
        model._llm = MagicMock()
        model._model_path = "/fake/model.gguf"
        model._context_window_tokens = 4096
        model._default_output_tokens = 512
        model._timeout_seconds = 120.0
        return model

    def test_rejects_non_finite_temperature_before_inference(self):
        model = self._make_model()

        with self.assertRaises(ProviderInvalidRequestError):
            model.complete(
                messages=[{"role": "user", "content": "hi"}],
                temperature=float("nan"),
            )

        model._llm.create_chat_completion.assert_not_called()

    def test_text_mode_returns_content(self):
        model = self._make_model()
        model._llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        result = model.complete(
            messages=[{"role": "user", "content": "hi"}],
            response_mode=ResponseMode.TEXT,
        )

        self.assertEqual(result.content, "Hello!")
        self.assertIsNone(result.parsed)
        self.assertEqual(result.usage.estimated_cost_usd, Decimal("0"))

    def test_json_mode_returns_parsed(self):
        model = self._make_model()
        model._llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": '{"score": 0.9}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        result = model.complete(
            messages=[{"role": "user", "content": "score"}],
            response_mode=ResponseMode.JSON,
        )

        self.assertEqual(result.parsed, {"score": 0.9})

    def test_json_mode_with_decorated_output(self):
        model = self._make_model()
        model._llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": 'Here:\n```json\n{"a": 1}\n```'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }

        result = model.complete(
            messages=[{"role": "user", "content": "json"}],
            response_mode=ResponseMode.JSON,
        )

        self.assertEqual(result.parsed, {"a": 1})

    def test_json_mode_recovers_completed_items_from_length_truncation(self):
        model = self._make_model()
        model._llm.create_chat_completion.return_value = {
            "choices": [{
                "message": {
                    "content": '{"seeds":[{"text":"one"},{"text":"unfinished'
                },
                "finish_reason": "length",
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 512},
        }

        result = model.complete(
            messages=[{"role": "user", "content": "seeds"}],
            response_mode=ResponseMode.JSON,
        )

        self.assertEqual(result.parsed, {"seeds": [{"text": "one"}]})

    def test_concurrency_hint_is_one(self):
        model = self._make_model()
        self.assertEqual(model.concurrency_hint, 1)

    def test_exposes_context_and_bounds_per_call_output(self):
        model = self._make_model()
        model._llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "ok"}}],
            "usage": {},
        }

        model.complete(
            [{"role": "user", "content": "hi"}], max_output_tokens=512
        )

        self.assertEqual(model.context_window_tokens, 4096)
        self.assertEqual(model.max_output_tokens, 512)
        self.assertEqual(
            model._llm.create_chat_completion.call_args.kwargs["max_tokens"], 512
        )

    def test_supports_json_mode(self):
        model = self._make_model()
        self.assertTrue(model.supports_json_mode())

    def test_cancelled_chat_never_calls_runtime(self):
        model = self._make_model()
        model._cancelled = threading.Event()
        model.cancel()

        with self.assertRaises(ProviderError) as ctx:
            model.complete([{"role": "user", "content": "hi"}])

        self.assertEqual(ctx.exception.code, "local_cancelled")
        model._llm.create_chat_completion.assert_not_called()

    @patch("arena.providers.local_chat.time.monotonic", side_effect=[0.0, 121.0])
    def test_chat_timeout_discards_partial_response(self, _clock):
        model = self._make_model()
        model._llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "partial"}}],
            "usage": {},
        }

        with self.assertRaises(ProviderError) as ctx:
            model.complete([{"role": "user", "content": "hi"}])

        self.assertEqual(ctx.exception.code, "timeout")
        self.assertFalse(ctx.exception.retryable)

    @patch("arena.providers.local_chat.time.monotonic", side_effect=[0.0, 0.1, 121.0])
    def test_streaming_timeout_closes_native_generator(self, _clock):
        model = self._make_model()
        closed = MagicMock()

        def chunks():
            try:
                yield {"choices": [{"delta": {"content": "a"}}]}
                yield {"choices": [{"delta": {"content": "b"}}]}
            finally:
                closed()

        model._llm.create_chat_completion.return_value = chunks()

        with self.assertRaises(ProviderError) as ctx:
            model.complete([{"role": "user", "content": "hi"}])

        self.assertEqual(ctx.exception.code, "timeout")
        closed.assert_called_once_with()

    def test_chat_memory_pressure_is_normalized(self):
        model = self._make_model()
        model._llm.create_chat_completion.side_effect = MemoryError()

        with self.assertRaises(ProviderError) as ctx:
            model.complete([{"role": "user", "content": "hi"}])

        self.assertEqual(ctx.exception.code, "local_oom")

    def test_oversized_prompt_is_rejected_before_inference(self):
        from arena.providers.local_limits import MAX_PROMPT_CHARS
        model = self._make_model()

        with self.assertRaises(ProviderInvalidRequestError):
            model.complete([{"role": "user", "content": "x" * (MAX_PROMPT_CHARS + 1)}])

        model._llm.create_chat_completion.assert_not_called()

    @patch("arena.providers.local_chat.MAX_RESPONSE_CHARS", 5)
    def test_oversized_response_is_rejected(self):
        model = self._make_model()
        model._llm.create_chat_completion.return_value = {
            "choices": [{"message": {"content": "too long"}}],
            "usage": {},
        }

        with self.assertRaises(ProviderResponseError):
            model.complete([{"role": "user", "content": "hi"}])


class TestLocalEmbeddingModelImportError(unittest.TestCase):

    def test_missing_llama_cpp_raises_provider_error(self):
        with patch.dict("sys.modules", {"llama_cpp": None}):
            import importlib
            import arena.providers.local_embedding as mod
            importlib.reload(mod)
            with self.assertRaises(ProviderError) as ctx:
                mod.LocalEmbeddingModel(model_path="/fake/model.gguf")
            self.assertEqual(ctx.exception.code, "local_unavailable")


class TestLocalEmbeddingModelEmbed(unittest.TestCase):

    def _make_model(self):
        from arena.providers.local_embedding import LocalEmbeddingModel
        model = LocalEmbeddingModel.__new__(LocalEmbeddingModel)
        model._llm = MagicMock()
        model._model_path = "/fake/embed.gguf"
        model._timeout_seconds = 120.0
        return model

    def test_embed_returns_vectors_with_zero_cost(self):
        model = self._make_model()

        model._llm.embed.side_effect = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        model._llm.tokenize.return_value = [1, 2, 3]

        result = model.embed(["hello", "world"])

        self.assertEqual(len(result.embeddings), 2)
        self.assertEqual(result.usage.estimated_cost_usd, Decimal("0"))

    def test_non_finite_embedding_is_rejected(self):
        model = self._make_model()
        model._llm.embed.return_value = [0.1, float("nan")]
        model._llm.tokenize.return_value = [1]

        with self.assertRaises(ProviderResponseError):
            model.embed(["hello"])

    def test_cancelled_embedding_never_calls_runtime(self):
        model = self._make_model()
        model._cancelled = threading.Event()
        model.cancel()

        with self.assertRaises(ProviderError) as ctx:
            model.embed(["hello"])

        self.assertEqual(ctx.exception.code, "local_cancelled")
        model._llm.embed.assert_not_called()

    @patch("arena.providers.local_embedding.time.monotonic", side_effect=[0.0, 121.0])
    def test_embedding_timeout_prevents_next_native_call(self, _clock):
        model = self._make_model()

        with self.assertRaises(ProviderError) as ctx:
            model.embed(["hello"])

        self.assertEqual(ctx.exception.code, "timeout")
        model._llm.embed.assert_not_called()


if __name__ == "__main__":
    unittest.main()
