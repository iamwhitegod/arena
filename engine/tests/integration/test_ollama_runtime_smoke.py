"""Release-gated smoke test against a real loopback Ollama server.

Set ``ARENA_RUN_OLLAMA_TESTS=1`` after starting Ollama and pulling the selected
models. When enabled, connection, model, and response failures fail the release
gate rather than being skipped.
"""

import math
import os
import unittest

from arena.providers.base import ResponseMode
from arena.providers.ollama_adapter import OllamaChatModel, OllamaEmbeddingModel


RUN_OLLAMA = os.environ.get("ARENA_RUN_OLLAMA_TESTS") == "1"


@unittest.skipUnless(RUN_OLLAMA, "real Ollama inference is a release-gated test")
class TestRealOllamaRuntime(unittest.TestCase):

    def test_real_chat_json_and_embedding(self):
        chat_model = os.environ.get("ARENA_OLLAMA_CHAT_MODEL", "llama3.2")
        embedding_model = os.environ.get(
            "ARENA_OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"
        )

        chat = OllamaChatModel(chat_model)
        response = chat.complete(
            [{"role": "user", "content": "Return only JSON with ok set to true."}],
            temperature=0,
            response_mode=ResponseMode.JSON,
            max_output_tokens=64,
        )
        self.assertIsInstance(response.parsed, dict)
        self.assertIs(response.parsed.get("ok"), True)

        embedding = OllamaEmbeddingModel(embedding_model)
        vectors = embedding.embed(["Arena Ollama inference smoke test"])
        self.assertEqual(len(vectors.embeddings), 1)
        self.assertGreater(len(vectors.embeddings[0]), 0)
        self.assertTrue(all(math.isfinite(value) for value in vectors.embeddings[0]))


if __name__ == "__main__":
    unittest.main()
