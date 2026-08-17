"""Release-gated smoke tests using the real native runtimes and verified models.

Set ``ARENA_RUN_LOCAL_INFERENCE_TESTS=1`` after installing a model pack.  When
enabled, missing dependencies or artifacts are failures rather than skips.
"""

import math
import os
from pathlib import Path
import struct
import tempfile
import unittest
import wave

from arena.models import MODEL_PACKS, ModelManager, recommend_runtime
from arena.models.registry import get_model
from arena.providers.base import ResponseMode
from arena.providers.local_chat import LocalChatModel
from arena.providers.local_embedding import LocalEmbeddingModel
from arena.providers.local_speech import LocalSpeechModel


RUN_LOCAL = os.environ.get("ARENA_RUN_LOCAL_INFERENCE_TESTS") == "1"


@unittest.skipUnless(RUN_LOCAL, "real local inference is a release-gated test")
class TestRealLocalRuntime(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        root = Path(os.environ.get("ARENA_MODEL_ROOT", Path.home() / ".arena" / "models"))
        cls.manager = ModelManager(root)
        pack_name = os.environ.get("ARENA_LOCAL_MODEL_PACK", "lite")
        cls.pack = MODEL_PACKS[pack_name]

    def test_real_chat_json_and_embedding(self):
        chat_path = self.manager.verify_model(get_model(self.pack.chat))
        embedding_path = self.manager.verify_model(get_model(self.pack.embedding))

        runtime = recommend_runtime()
        chat = LocalChatModel(
            str(chat_path),
            n_ctx=min(self.pack.context_size, 4096),
            n_gpu_layers=runtime.gpu_layers,
            n_threads=runtime.threads,
        )
        response = chat.complete(
            [{"role": "user", "content": "Return JSON with ok set to true."}],
            temperature=0,
            response_mode=ResponseMode.JSON,
            json_schema={"type": "object", "properties": {"ok": {"type": "boolean"}}},
        )
        self.assertIsInstance(response.parsed, dict)

        embedding = LocalEmbeddingModel(str(embedding_path))
        vectors = embedding.embed(["Arena local inference smoke test"])
        self.assertEqual(len(vectors.embeddings), 1)
        self.assertTrue(all(math.isfinite(value) for value in vectors.embeddings[0]))

    def test_real_speech_with_bundled_silero_vad(self):
        speech_path = self.manager.verify_model(get_model(self.pack.speech))
        speech = LocalSpeechModel(str(speech_path), device="cpu", compute_type="int8")

        with tempfile.TemporaryDirectory() as tempdir:
            audio_path = Path(tempdir) / "tone.wav"
            sample_rate = 16_000
            with wave.open(str(audio_path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(sample_rate)
                samples = (
                    int(1000 * math.sin(2 * math.pi * 440 * index / sample_rate))
                    for index in range(sample_rate)
                )
                output.writeframes(b"".join(struct.pack("<h", value) for value in samples))

            result = speech.transcribe(audio_path)

        self.assertGreaterEqual(result.duration, 0)
        self.assertLessEqual(result.duration, speech.max_audio_duration_seconds)


if __name__ == "__main__":
    unittest.main()
