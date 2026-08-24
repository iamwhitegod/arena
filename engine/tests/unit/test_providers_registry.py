"""Tests for ProviderRegistry, InferenceBundle, and capability-aware resolution."""

import unittest
from unittest.mock import MagicMock

from arena.providers.base import ChatModel, EmbeddingModel, ProviderAuthError, SpeechModel
from arena.providers.credentials import EnvironmentCredentialResolver
from arena.providers.fake import FakeChatModel, FakeEmbeddingModel, FakeSpeechModel
from arena.providers.profile import Capability, ModelBinding, RuntimeProfile
from arena.providers.registry import InferenceBundle, ProviderFactories, ProviderRegistry
from arena.providers.resolve import resolve_inference


class TestInferenceBundle(unittest.TestCase):

    def test_require_chat_raises_when_none(self):
        bundle = InferenceBundle()
        with self.assertRaises(RuntimeError):
            bundle.require_chat()

    def test_require_chat_returns_when_set(self):
        chat = FakeChatModel()
        bundle = InferenceBundle(chat=chat)
        self.assertIs(bundle.require_chat(), chat)

    def test_require_overview_falls_back_to_chat(self):
        chat = FakeChatModel()
        bundle = InferenceBundle(chat=chat)
        self.assertIs(bundle.require_overview_chat(), chat)

    def test_require_overview_uses_override(self):
        chat = FakeChatModel()
        overview = FakeChatModel()
        bundle = InferenceBundle(chat=chat, overview_chat=overview)
        self.assertIs(bundle.require_overview_chat(), overview)

    def test_require_embedding_raises_when_none(self):
        bundle = InferenceBundle()
        with self.assertRaises(RuntimeError):
            bundle.require_embedding()

    def test_require_speech_raises_when_none(self):
        bundle = InferenceBundle()
        with self.assertRaises(RuntimeError):
            bundle.require_speech()

    def test_optional_members(self):
        """arena transcribe only needs speech — chat and embedding should be None."""
        bundle = InferenceBundle(speech=FakeSpeechModel())
        self.assertIsNone(bundle.chat)
        self.assertIsNone(bundle.embedding)
        self.assertIsNotNone(bundle.speech)

    def test_built_bundle_retains_safe_profile_identity(self):
        profile = RuntimeProfile.default_openai()
        bundle = InferenceBundle(profile=profile, chat=FakeChatModel())
        self.assertIs(bundle.profile, profile)

    def test_close_releases_each_shared_model_once(self):
        shared_chat = MagicMock()
        speech = MagicMock()
        bundle = InferenceBundle(
            chat=shared_chat,
            overview_chat=shared_chat,
            speech=speech,
        )

        bundle.close()

        shared_chat.close.assert_called_once_with()
        speech.close.assert_called_once_with()
        self.assertIsNone(bundle.chat)
        self.assertIsNone(bundle.overview_chat)
        self.assertIsNone(bundle.speech)

    def test_close_continues_after_one_model_fails(self):
        chat = MagicMock()
        speech = MagicMock()
        speech.close.side_effect = RuntimeError("close failed")
        bundle = InferenceBundle(chat=chat, speech=speech)

        with self.assertRaises(RuntimeError):
            bundle.close()

        chat.close.assert_called_once_with()
        self.assertIsNone(bundle.chat)
        self.assertIsNone(bundle.speech)


class TestProviderRegistry(unittest.TestCase):

    def _fake_factories(self):
        return ProviderFactories(
            chat={"fake": lambda b, c: FakeChatModel()},
            embedding={"fake": lambda b, c: FakeEmbeddingModel()},
            speech={"fake": lambda b, c: FakeSpeechModel()},
        )

    def test_unknown_provider_raises(self):
        registry = ProviderRegistry(self._fake_factories())
        binding = ModelBinding(provider="unknown", model="test")
        creds = EnvironmentCredentialResolver()

        with self.assertRaises(ValueError) as ctx:
            registry.build_chat(binding, creds)
        self.assertIn("unknown", str(ctx.exception))

    def test_build_chat_with_fake(self):
        registry = ProviderRegistry(self._fake_factories())
        binding = ModelBinding(provider="fake", model="test")
        creds = EnvironmentCredentialResolver()

        chat = registry.build_chat(binding, creds)
        self.assertIsInstance(chat, FakeChatModel)

    def test_build_required_only_constructs_requested(self):
        """Only SPEECH requested — chat and embedding should be None."""
        registry = ProviderRegistry(self._fake_factories())
        profile = RuntimeProfile(
            chat=ModelBinding(provider="fake", model="chat"),
            embedding=ModelBinding(provider="fake", model="embed"),
            transcription=ModelBinding(provider="fake", model="speech"),
        )
        creds = EnvironmentCredentialResolver()

        bundle = registry.build_required(profile, {Capability.SPEECH}, creds)
        self.assertIsNone(bundle.chat)
        self.assertIsNone(bundle.embedding)
        self.assertIsNotNone(bundle.speech)

    def test_build_required_all_capabilities(self):
        registry = ProviderRegistry(self._fake_factories())
        profile = RuntimeProfile(
            chat=ModelBinding(provider="fake", model="chat"),
            embedding=ModelBinding(provider="fake", model="embed"),
            transcription=ModelBinding(provider="fake", model="speech"),
        )
        creds = EnvironmentCredentialResolver()

        bundle = registry.build_required(
            profile,
            {Capability.CHAT, Capability.EMBEDDING, Capability.SPEECH},
            creds,
        )
        self.assertIsNotNone(bundle.chat)
        self.assertIsNotNone(bundle.embedding)
        self.assertIsNotNone(bundle.speech)

    def test_partial_construction_is_closed_when_later_factory_fails(self):
        chat = MagicMock()

        def fail_embedding(binding, credentials):
            raise RuntimeError("embedding failed")

        registry = ProviderRegistry(ProviderFactories(
            chat={"fake": lambda binding, credentials: chat},
            embedding={"fake": fail_embedding},
            speech={"fake": lambda binding, credentials: FakeSpeechModel()},
        ))
        profile = RuntimeProfile(
            chat=ModelBinding(provider="fake", model="chat"),
            embedding=ModelBinding(provider="fake", model="embed"),
            transcription=ModelBinding(provider="fake", model="speech"),
        )

        with self.assertRaisesRegex(RuntimeError, "embedding failed"):
            registry.build_required(
                profile,
                {Capability.CHAT, Capability.EMBEDDING},
                EnvironmentCredentialResolver(),
            )

        chat.close.assert_called_once_with()

    def test_overview_reuses_chat_when_identical(self):
        registry = ProviderRegistry(self._fake_factories())
        profile = RuntimeProfile(
            chat=ModelBinding(provider="fake", model="same"),
            overview_chat=None,  # Falls back to chat
            embedding=ModelBinding(provider="fake", model="embed"),
            transcription=ModelBinding(provider="fake", model="speech"),
        )
        creds = EnvironmentCredentialResolver()

        bundle = registry.build_required(
            profile,
            {Capability.CHAT, Capability.OVERVIEW_CHAT},
            creds,
        )
        # When overview falls back to chat binding, model should be reused
        self.assertIs(bundle.overview_chat, bundle.chat)


class TestResolveInference(unittest.TestCase):

    def test_missing_api_key_raises_auth_error(self):
        """Without OPENAI_API_KEY, resolve should fail for openai provider."""
        import os
        env_backup = os.environ.pop("OPENAI_API_KEY", None)
        try:
            with self.assertRaises(ProviderAuthError):
                resolve_inference(required={Capability.CHAT})
        finally:
            if env_backup is not None:
                os.environ["OPENAI_API_KEY"] = env_backup

    def test_with_injectable_registry(self):
        """resolve_inference should accept a custom registry."""
        fake_factories = ProviderFactories(
            chat={"openai": lambda b, c: FakeChatModel()},
            embedding={"openai": lambda b, c: FakeEmbeddingModel()},
            speech={"openai": lambda b, c: FakeSpeechModel()},
        )
        registry = ProviderRegistry(fake_factories)

        bundle = resolve_inference(
            required={Capability.CHAT},
            registry=registry,
        )
        self.assertIsInstance(bundle.chat, FakeChatModel)

    def test_transcript_only_ollama_does_not_resolve_speech(self):
        fake_factories = ProviderFactories(
            chat={"ollama": lambda b, c: FakeChatModel()},
            embedding={"ollama": lambda b, c: FakeEmbeddingModel()},
            speech={},
        )
        bundle = resolve_inference(
            required={Capability.CHAT, Capability.EMBEDDING},
            provider="ollama",
            registry=ProviderRegistry(fake_factories),
        )

        self.assertIsInstance(bundle.chat, FakeChatModel)
        self.assertIsInstance(bundle.embedding, FakeEmbeddingModel)
        self.assertIsNone(bundle.speech)
        self.assertEqual(bundle.profile.transcription.provider, "openai")


if __name__ == "__main__":
    unittest.main()
