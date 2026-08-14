"""Tests for provider selection propagation through the pipeline.

Tests actual argument parsing and mock-based verification rather than
inspecting source text.
"""

import sys
import unittest
from unittest.mock import patch, MagicMock

from arena.providers.profile import RuntimeProfile, ModelBinding, Capability
from arena.providers.resolve import resolve_inference
from arena.providers.fake import FakeChatModel, FakeEmbeddingModel, FakeSpeechModel
from arena.providers.registry import ProviderFactories, ProviderRegistry
from arena.providers.base import ProviderError


class TestProfileFromArgs(unittest.TestCase):
    """Test that RuntimeProfile.from_args correctly handles provider args."""

    def test_provider_shorthand_sets_all(self):
        profile = RuntimeProfile.from_args(provider="local")
        self.assertEqual(profile.chat.provider, "local")
        self.assertEqual(profile.embedding.provider, "local")
        self.assertEqual(profile.transcription.provider, "local")

    def test_per_capability_overrides_shorthand(self):
        profile = RuntimeProfile.from_args(
            provider="openai",
            transcription_provider="local",
        )
        self.assertEqual(profile.chat.provider, "openai")
        self.assertEqual(profile.transcription.provider, "local")

    def test_chat_model_override(self):
        profile = RuntimeProfile.from_args(chat_model="gpt-4o-mini")
        self.assertEqual(profile.chat.model, "gpt-4o-mini")

    def test_default_is_gpt4o(self):
        profile = RuntimeProfile.from_args()
        self.assertEqual(profile.chat.model, "gpt-4o")


class TestResolveInferencePropagation(unittest.TestCase):
    """Test that resolve_inference correctly wires provider args to the registry."""

    def _fake_registry(self):
        return ProviderRegistry(ProviderFactories(
            chat={"openai": lambda b, c: FakeChatModel(), "local": lambda b, c: FakeChatModel()},
            embedding={"openai": lambda b, c: FakeEmbeddingModel(), "local": lambda b, c: FakeEmbeddingModel()},
            speech={"openai": lambda b, c: FakeSpeechModel(), "local": lambda b, c: FakeSpeechModel()},
        ))

    def test_provider_arg_reaches_profile(self):
        registry = self._fake_registry()
        bundle = resolve_inference(
            required={Capability.CHAT},
            provider="local",
            registry=registry,
        )
        self.assertIsNotNone(bundle.chat)

    def test_chat_model_arg_reaches_profile(self):
        registry = self._fake_registry()
        bundle = resolve_inference(
            required={Capability.CHAT},
            chat_model="gpt-4o-mini",
            registry=registry,
        )
        self.assertIsNotNone(bundle.chat)


class TestPipelineSignature(unittest.TestCase):
    """Test that run_arena_pipeline accepts provider parameter."""

    def test_accepts_provider_param(self):
        import inspect
        from arena_process import run_arena_pipeline
        sig = inspect.signature(run_arena_pipeline)
        self.assertIn("provider", sig.parameters)
        # Should default to None
        self.assertEqual(sig.parameters["provider"].default, None)


class TestEditorialInferenceIdentity(unittest.TestCase):

    def _bundle(self, chat_model):
        profile = RuntimeProfile(
            chat=ModelBinding(provider="fake", model=chat_model),
            embedding=ModelBinding(provider="fake", model="embed"),
            transcription=ModelBinding(provider="fake", model="speech"),
        )
        return self._registry().build_required(
            profile,
            {Capability.CHAT, Capability.EMBEDDING},
            MagicMock(),
        )

    def _registry(self):
        return ProviderRegistry(ProviderFactories(
            chat={"fake": lambda b, c: FakeChatModel()},
            embedding={"fake": lambda b, c: FakeEmbeddingModel()},
            speech={"fake": lambda b, c: FakeSpeechModel()},
        ))

    def test_adapter_uses_resolved_model_and_profile_fingerprint(self):
        from arena.editorial import FourLayerAdapter

        first = FourLayerAdapter(inference=self._bundle("chat-a"))
        second = FourLayerAdapter(inference=self._bundle("chat-b"))

        self.assertEqual(first.model, "chat-a")
        self.assertEqual(second.model, "chat-b")
        self.assertNotEqual(first._inference_fingerprint, second._inference_fingerprint)

    def test_score_weights_are_validated_and_immutable(self):
        from arena.editorial import FourLayerAdapter

        weights = FourLayerAdapter._validate_score_weights({
            "completeness": 0.6,
            "standalone": 0.4,
        })
        with self.assertRaises(TypeError):
            weights["completeness"] = 1.0

        with self.assertRaisesRegex(ValueError, "exactly"):
            FourLayerAdapter._validate_score_weights({"completeness": 1.0})
        with self.assertRaisesRegex(ValueError, "finite"):
            FourLayerAdapter._validate_score_weights({
                "completeness": float("nan"),
                "standalone": 1.0,
            })


class TestPythonCliArgParsing(unittest.TestCase):
    """Test that Python CLI subparsers correctly parse --provider and --editorial-model."""

    @patch('arena.cli.commands.process.run_process', return_value=0)
    def test_process_subparser_parses_real_provider_options(self, mock_run):
        from arena.cli.main import main

        argv = [
            'arena', 'process', 'test.mp4', '--provider', 'openai',
            '--chat-model', 'gpt-4o-mini',
            '--embedding-model', 'text-embedding-3-large',
            '--transcription-model', 'whisper-1',
        ]
        with patch.object(sys, 'argv', argv):
            self.assertEqual(main(), 0)

        args = mock_run.call_args.args[0]
        self.assertEqual(args.provider, 'openai')
        self.assertEqual(args.chat_model, 'gpt-4o-mini')
        self.assertEqual(args.embedding_model, 'text-embedding-3-large')
        self.assertEqual(args.transcription_model, 'whisper-1')

    @patch('arena.cli.commands.analyze.run_analyze', return_value=0)
    def test_analyze_subparser_parses_real_provider_options(self, mock_run):
        from arena.cli.main import main

        argv = [
            'arena', 'analyze', 'test.mp4', '--provider', 'openai',
            '--overview-chat-model', 'gpt-4o-mini',
        ]
        with patch.object(sys, 'argv', argv):
            self.assertEqual(main(), 0)

        args = mock_run.call_args.args[0]
        self.assertEqual(args.provider, 'openai')
        self.assertEqual(args.overview_chat_model, 'gpt-4o-mini')

    @patch('arena.cli.commands.transcribe.run_transcribe', return_value=0)
    def test_transcribe_subparser_parses_real_provider_options(self, mock_run):
        from arena.cli.main import main

        argv = [
            'arena', 'transcribe', 'test.mp4',
            '--transcription-provider', 'openai',
            '--transcription-model', 'whisper-1',
        ]
        with patch.object(sys, 'argv', argv):
            self.assertEqual(main(), 0)

        args = mock_run.call_args.args[0]
        self.assertEqual(args.transcription_provider, 'openai')
        self.assertEqual(args.transcription_model, 'whisper-1')

    @patch('arena.cli.commands.process.run_process')
    def test_public_cli_does_not_print_provider_cause_traceback(self, mock_run):
        from arena.cli.main import main

        native = RuntimeError("sensitive provider detail")
        normalized = ProviderError("Safe provider failure", code="provider", retryable=False)
        normalized.__cause__ = native
        mock_run.side_effect = normalized

        with (
            patch.object(sys, 'argv', ['arena', 'process', 'test.mp4']),
            patch('traceback.print_exc') as mock_traceback,
        ):
            self.assertEqual(main(), 1)

        mock_traceback.assert_not_called()


class TestProcessForwardsProvider(unittest.TestCase):
    """Test that run_process forwards provider to run_arena_pipeline."""

    @patch('arena.cli.commands.process.run_arena_pipeline')
    def test_provider_forwarded(self, mock_pipeline):
        mock_pipeline.return_value = 0

        from arena.cli.commands.process import run_process
        args = MagicMock()
        args.video = 'test.mp4'
        args.output = 'output'
        args.num_clips = 8
        args.min_duration = 30
        args.max_duration = 90
        args.no_cache = False
        args.fast = False
        args.padding = 0.1
        args.max_adjustment = 10.0
        args.no_enhance = False
        args.scene_detection = False
        args.export_editorial_layers = False
        args.editorial_model = 'gpt-4o'
        args.platform = None
        args.crop = 'center'
        args.pad = 'blur'
        args.pad_color = '#000000'
        args.captions = False
        args.cookies_from_browser = None
        args.provider = 'openai'
        args.chat_provider = 'openai'
        args.chat_model = 'gpt-4o-mini'
        args.overview_chat_provider = 'openai'
        args.overview_chat_model = 'gpt-4o'
        args.embedding_provider = 'openai'
        args.embedding_model = 'text-embedding-3-large'
        args.transcription_provider = 'openai'
        args.transcription_model = 'whisper-1'

        run_process(args)

        call_kwargs = mock_pipeline.call_args
        self.assertEqual(call_kwargs.kwargs['provider'], 'openai')
        self.assertEqual(call_kwargs.kwargs['chat_model'], 'gpt-4o-mini')
        self.assertEqual(call_kwargs.kwargs['embedding_model'], 'text-embedding-3-large')
        self.assertEqual(call_kwargs.kwargs['transcription_model'], 'whisper-1')


if __name__ == "__main__":
    unittest.main()
