"""Tests for RuntimeProfile, ModelBinding, and provider resolution."""

import unittest

from arena.providers.profile import Capability, ModelBinding, RuntimeProfile


class TestModelBinding(unittest.TestCase):

    def test_basic(self):
        b = ModelBinding(provider="openai", model="gpt-4o")
        self.assertEqual(b.provider, "openai")
        self.assertEqual(b.model, "gpt-4o")

    def test_with_options(self):
        b = ModelBinding(provider="local", model="qwen.gguf", options={"n_ctx": 8192})
        self.assertEqual(b.options["n_ctx"], 8192)

    def test_frozen(self):
        b = ModelBinding(provider="openai", model="gpt-4o")
        with self.assertRaises(AttributeError):
            b.provider = "local"

    def test_options_are_recursively_immutable(self):
        b = ModelBinding(provider="local", model="qwen.gguf", options={"n_ctx": 8192})
        with self.assertRaises(TypeError):
            b.options["n_ctx"] = 4096

    def test_rejects_secret_options(self):
        with self.assertRaisesRegex(ValueError, "credentials"):
            ModelBinding(
                provider="local",
                model="qwen.gguf",
                options={"api_key": "secret"},
            )

    def test_rejects_unknown_options(self):
        with self.assertRaisesRegex(ValueError, "Unsupported option"):
            ModelBinding(
                provider="local",
                model="qwen.gguf",
                options={"arbitrary_endpoint": "https://example.test"},
            )

    def test_rejects_unknown_openai_model(self):
        with self.assertRaisesRegex(ValueError, "Unsupported OpenAI model"):
            ModelBinding(provider="openai", model="untrusted-model")


class TestRuntimeProfile(unittest.TestCase):

    def test_default_openai(self):
        p = RuntimeProfile.default_openai()
        self.assertEqual(p.chat.provider, "openai")
        self.assertEqual(p.chat.model, "gpt-4o")
        self.assertEqual(p.embedding.model, "text-embedding-3-small")
        self.assertEqual(p.transcription.model, "whisper-1")
        self.assertIsNone(p.overview_chat)

    def test_profile_is_immutable_after_resolution(self):
        profile = RuntimeProfile.default_openai()
        with self.assertRaises(AttributeError):
            profile.chat = ModelBinding(provider="openai", model="gpt-4o-mini")

    def test_binding_for_chat(self):
        p = RuntimeProfile.default_openai()
        b = p.binding_for(Capability.CHAT)
        self.assertEqual(b.model, "gpt-4o")

    def test_binding_for_overview_falls_back_to_chat(self):
        p = RuntimeProfile.default_openai()
        b = p.binding_for(Capability.OVERVIEW_CHAT)
        self.assertEqual(b.model, "gpt-4o")  # Falls back to chat

    def test_binding_for_overview_explicit(self):
        p = RuntimeProfile(
            chat=ModelBinding(provider="openai", model="gpt-4o-mini"),
            overview_chat=ModelBinding(provider="openai", model="gpt-4o"),
            embedding=ModelBinding(provider="openai", model="text-embedding-3-small"),
            transcription=ModelBinding(provider="openai", model="whisper-1"),
        )
        self.assertEqual(p.binding_for(Capability.OVERVIEW_CHAT).model, "gpt-4o")
        self.assertEqual(p.binding_for(Capability.CHAT).model, "gpt-4o-mini")

    def test_from_args_provider_shorthand(self):
        p = RuntimeProfile.from_args(provider="openai")
        self.assertEqual(p.chat.provider, "openai")
        self.assertEqual(p.embedding.provider, "openai")
        self.assertEqual(p.transcription.provider, "openai")

    def test_from_args_per_capability_override(self):
        p = RuntimeProfile.from_args(
            provider="openai",
            chat_model="gpt-4o-mini",
            embedding_model="text-embedding-3-large",
        )
        self.assertEqual(p.chat.model, "gpt-4o-mini")
        self.assertEqual(p.embedding.model, "text-embedding-3-large")
        self.assertEqual(p.transcription.model, "whisper-1")  # default

    def test_from_args_overview_chat(self):
        p = RuntimeProfile.from_args(
            overview_chat_provider="openai",
            overview_chat_model="gpt-4o",
        )
        self.assertIsNotNone(p.overview_chat)
        self.assertEqual(p.overview_chat.model, "gpt-4o")

    def test_from_args_no_overview_when_not_specified(self):
        p = RuntimeProfile.from_args(provider="openai")
        self.assertIsNone(p.overview_chat)

    def test_rejects_model_bound_to_wrong_openai_capability(self):
        with self.assertRaisesRegex(ValueError, "embedding model"):
            RuntimeProfile(
                chat=ModelBinding(provider="openai", model="gpt-4o"),
                embedding=ModelBinding(provider="openai", model="gpt-4o-mini"),
                transcription=ModelBinding(provider="openai", model="whisper-1"),
            )

    def test_empty_capability_selection_is_empty(self):
        self.assertEqual(RuntimeProfile.default_openai().safe_dict(set()), {})

    def test_fingerprint_changes_with_output_affecting_binding(self):
        first = RuntimeProfile.from_args(chat_model="gpt-4o")
        second = RuntimeProfile.from_args(chat_model="gpt-4o-mini")
        capabilities = {Capability.CHAT, Capability.OVERVIEW_CHAT, Capability.EMBEDDING}
        self.assertNotEqual(first.fingerprint(capabilities), second.fingerprint(capabilities))

    def test_fingerprint_is_stable_and_safe_to_serialize(self):
        profile = RuntimeProfile(
            chat=ModelBinding(
                provider="local", model="qwen.gguf", options={"n_ctx": 8192}
            ),
            embedding=ModelBinding(provider="fake", model="embed"),
            transcription=ModelBinding(provider="fake", model="speech"),
        )
        first = profile.fingerprint()
        second = profile.fingerprint()
        self.assertEqual(first, second)
        self.assertEqual(profile.safe_dict()["chat"]["options"], {"n_ctx": 8192})


class TestCapability(unittest.TestCase):

    def test_is_str_enum(self):
        self.assertEqual(Capability.CHAT, "chat")
        self.assertEqual(Capability.SPEECH, "speech")


if __name__ == "__main__":
    unittest.main()
