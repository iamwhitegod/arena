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


class TestRuntimeProfile(unittest.TestCase):

    def test_default_openai(self):
        p = RuntimeProfile.default_openai()
        self.assertEqual(p.chat.provider, "openai")
        self.assertEqual(p.chat.model, "gpt-4o")
        self.assertEqual(p.embedding.model, "text-embedding-3-small")
        self.assertEqual(p.transcription.model, "whisper-1")
        self.assertIsNone(p.overview_chat)

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


class TestCapability(unittest.TestCase):

    def test_is_str_enum(self):
        self.assertEqual(Capability.CHAT, "chat")
        self.assertEqual(Capability.SPEECH, "speech")


if __name__ == "__main__":
    unittest.main()
