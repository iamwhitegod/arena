"""Tests for local and ollama provider factory registration."""

import unittest
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from arena.providers.base import ProviderError
from arena.providers.credentials import EnvironmentCredentialResolver
from arena.providers.profile import Capability, ModelBinding, RuntimeProfile
from arena.providers.registry import ProviderRegistry
from arena.models.registry import (
    MODEL_PACKS,
    MODEL_SPECS,
    chat_model_context_size,
)


class TestLocalProviderRegistered(unittest.TestCase):

    def test_local_in_chat_factories(self):
        registry = ProviderRegistry()
        self.assertIn("local", registry._factories.chat)

    def test_local_in_embedding_factories(self):
        registry = ProviderRegistry()
        self.assertIn("local", registry._factories.embedding)

    def test_local_in_speech_factories(self):
        registry = ProviderRegistry()
        self.assertIn("local", registry._factories.speech)

    def test_verified_pack_context_caps_hardware_recommendation(self):
        pack = MODEL_PACKS["lite"]
        recommendation = SimpleNamespace(
            context_size=8192,
            gpu_layers=0,
            threads=4,
        )
        with (
            patch(
                "arena.models.hardware.recommend_runtime",
                return_value=recommendation,
            ),
            patch(
                "arena.models.locator.ModelLocator.resolve_gguf",
                return_value=Path("/verified/lite.gguf"),
            ),
            patch("arena.providers.local_chat.LocalChatModel") as local_chat,
        ):
            ProviderRegistry().build_chat(
                ModelBinding(provider="local", model=pack.chat),
                EnvironmentCredentialResolver(),
            )

        self.assertEqual(local_chat.call_args.kwargs["n_ctx"], pack.context_size)


class TestOllamaProviderRegistered(unittest.TestCase):

    def test_ollama_in_chat_factories(self):
        registry = ProviderRegistry()
        self.assertIn("ollama", registry._factories.chat)

    def test_ollama_in_embedding_factories(self):
        registry = ProviderRegistry()
        self.assertIn("ollama", registry._factories.embedding)

    def test_ollama_not_in_speech_factories(self):
        registry = ProviderRegistry()
        self.assertNotIn("ollama", registry._factories.speech)


class TestProfileFromArgsLocalDefaults(unittest.TestCase):

    def test_local_provider_defaults_to_verified_chat(self):
        with tempfile.TemporaryDirectory() as tempdir, patch.dict(
            os.environ, {"ARENA_MODEL_ROOT": tempdir}
        ):
            profile = RuntimeProfile.from_args(provider="local")
        self.assertEqual(profile.chat.model, "qwen3.5-4b-q4_k_m")
        self.assertEqual(profile.chat.provider, "local")

    def test_local_provider_defaults_to_verified_transcription(self):
        with tempfile.TemporaryDirectory() as tempdir, patch.dict(
            os.environ, {"ARENA_MODEL_ROOT": tempdir}
        ):
            profile = RuntimeProfile.from_args(provider="local")
        self.assertEqual(profile.transcription.model, "faster-whisper-small")

    def test_local_provider_with_explicit_model(self):
        profile = RuntimeProfile.from_args(
            provider="local",
            chat_model="my-model.gguf",
        )
        self.assertEqual(profile.chat.model, "my-model.gguf")

    def test_local_defaults_follow_explicitly_installed_pack(self):
        with tempfile.TemporaryDirectory() as tempdir:
            pack = MODEL_PACKS["lite"]
            Path(tempdir, ".arena-pack.json").write_text(
                json.dumps({
                    "version": 1,
                    "pack": pack.name,
                    "models": {
                        "chat": pack.chat,
                        "embedding": pack.embedding,
                        "speech": pack.speech,
                    },
                }),
                encoding="utf-8",
            )
            previous = os.environ.get("ARENA_MODEL_ROOT")
            os.environ["ARENA_MODEL_ROOT"] = tempdir
            try:
                profile = RuntimeProfile.from_args(provider="local")
            finally:
                if previous is None:
                    os.environ.pop("ARENA_MODEL_ROOT", None)
                else:
                    os.environ["ARENA_MODEL_ROOT"] = previous

        self.assertEqual(profile.chat.model, pack.chat)
        self.assertEqual(profile.embedding.model, pack.embedding)
        self.assertEqual(profile.transcription.model, pack.speech)

    def test_cross_provider_overview_uses_its_provider_default(self):
        profile = RuntimeProfile.from_args(
            provider="local",
            overview_chat_provider="openai",
        )
        self.assertEqual(profile.overview_chat.provider, "openai")
        self.assertEqual(profile.overview_chat.model, "gpt-4o")

    def test_ollama_provider_defaults(self):
        # Ollama has no speech capability, so transcription must use another provider
        profile = RuntimeProfile.from_args(
            provider="ollama",
            transcription_provider="local",
        )
        self.assertEqual(profile.chat.model, "llama3.2")
        self.assertEqual(profile.embedding.model, "nomic-embed-text")
        self.assertEqual(profile.transcription.provider, "local")

    def test_ollama_rejects_transcription(self):
        with self.assertRaisesRegex(ValueError, "does not support transcription"):
            RuntimeProfile.from_args(provider="ollama")

    def test_ollama_allows_transcript_only_profile(self):
        profile = RuntimeProfile.from_args(
            provider="ollama",
            required_capabilities={Capability.CHAT, Capability.EMBEDDING},
        )
        self.assertEqual(profile.chat.provider, "ollama")
        self.assertEqual(profile.embedding.provider, "ollama")
        self.assertEqual(profile.transcription.provider, "openai")

    def test_explicit_ollama_transcription_is_rejected_when_unused(self):
        with self.assertRaisesRegex(ValueError, "does not support transcription"):
            RuntimeProfile.from_args(
                provider="ollama",
                transcription_provider="ollama",
                required_capabilities={Capability.CHAT, Capability.EMBEDDING},
            )

    def test_openai_provider_defaults_unchanged(self):
        profile = RuntimeProfile.from_args(provider="openai")
        self.assertEqual(profile.chat.model, "gpt-4o")
        self.assertEqual(profile.embedding.model, "text-embedding-3-small")


class TestVerifiedModelPacks(unittest.TestCase):

    def test_tiers_use_distinct_chat_and_speech_models(self):
        self.assertEqual(len({pack.chat for pack in MODEL_PACKS.values()}), 3)
        self.assertEqual(len({pack.speech for pack in MODEL_PACKS.values()}), 3)

    def test_every_artifact_has_immutable_revision_hash_and_size(self):
        for spec in MODEL_SPECS.values():
            with self.subTest(model=spec.identifier):
                self.assertEqual(len(spec.revision), 40)
                self.assertTrue(spec.upstream)
                self.assertTrue(spec.license)
                for artifact in spec.artifacts:
                    self.assertIn(f"/resolve/{spec.revision}/", artifact.url)
                    self.assertEqual(len(artifact.sha256), 64)
                    self.assertIsNotNone(artifact.expected_bytes)

    def test_pack_capacity_tiers_increase_monotonically(self):
        tiers = [MODEL_PACKS[name] for name in ("lite", "default", "pro")]
        self.assertEqual(
            [pack.minimum_memory_gib for pack in tiers],
            sorted(pack.minimum_memory_gib for pack in tiers),
        )
        self.assertEqual(
            [pack.context_size for pack in tiers],
            sorted(pack.context_size for pack in tiers),
        )

    def test_verified_chat_models_expose_pack_context(self):
        for pack in MODEL_PACKS.values():
            with self.subTest(pack=pack.name):
                self.assertEqual(
                    chat_model_context_size(pack.chat), pack.context_size
                )
        self.assertIsNone(chat_model_context_size("custom.gguf"))


if __name__ == "__main__":
    unittest.main()
