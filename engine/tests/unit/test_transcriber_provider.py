"""Provider-aware transcription orchestration tests."""

from pathlib import Path
import json
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from arena.audio.transcriber import Transcriber
from arena.providers.fake import FakeSpeechModel
from arena.providers.profile import Capability, RuntimeProfile
from arena.providers.registry import InferenceBundle


class SizeRecordingSpeechModel(FakeSpeechModel):
    def __init__(self, file_size_limit_mb):
        super().__init__(file_size_limit_mb=file_size_limit_mb)
        self.submitted_sizes = []

    def transcribe(self, audio_path: Path):
        self.submitted_sizes.append(audio_path.stat().st_size)
        return super().transcribe(audio_path)


class FailingSpeechModel(FakeSpeechModel):
    def transcribe(self, audio_path: Path):
        raise RuntimeError("transcription failed")


class TestProviderChunking(unittest.TestCase):

    @patch("arena.providers.local_speech.LocalSpeechModel")
    @patch("arena.models.locator.ModelLocator.resolve_speech_model")
    def test_legacy_local_mode_uses_verified_path_without_alias_download(
        self, resolve_model, local_model
    ):
        verified_path = "/private/models/faster-whisper-base"
        resolve_model.return_value = verified_path
        local_model.return_value = FakeSpeechModel()

        transcriber = Transcriber(mode="local")

        resolve_model.assert_called_once_with("auto")
        local_model.assert_called_once_with(model_size_or_path=verified_path)
        self.assertEqual(transcriber.mode, "provider")

    def test_oversized_encoded_chunk_is_reduced_before_submission(self):
        limit_mb = 0.01
        limit_bytes = int(limit_mb * 1024 * 1024)
        speech = SizeRecordingSpeechModel(limit_mb)
        transcriber = Transcriber(speech=speech)
        extracted_durations = []

        def fake_extract(_input, output, start, end):
            duration = end - start
            extracted_durations.append(duration)
            # Force the first estimate over the limit; halved chunks fit.
            size = limit_bytes + 100 if duration > 0.5 else limit_bytes - 100
            output.write_bytes(b"x" * size)

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "input.mp3"
            audio_path.write_bytes(b"input")
            with (
                patch.object(transcriber, "_get_audio_duration", return_value=1.0),
                patch.object(transcriber, "_extract_audio_chunk", side_effect=fake_extract),
            ):
                result = transcriber._transcribe_chunked(audio_path)

        self.assertEqual(result["duration"], 1.0)
        self.assertGreater(len(extracted_durations), len(speech.submitted_sizes))
        self.assertTrue(speech.submitted_sizes)
        self.assertTrue(all(size <= limit_bytes for size in speech.submitted_sizes))

    def test_impossibly_small_limit_fails_without_uploading(self):
        speech = SizeRecordingSpeechModel(0.0001)
        transcriber = Transcriber(speech=speech)

        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "input.mp3"
            audio_path.write_bytes(b"input")
            with patch.object(transcriber, "_get_audio_duration", return_value=10.0):
                with self.assertRaisesRegex(ValueError, "too small"):
                    transcriber._transcribe_chunked(audio_path)

        self.assertEqual(speech.submitted_sizes, [])

    @patch("arena.audio.transcriber.subprocess.run")
    def test_chunks_use_bounded_deterministic_bitrate(self, mock_run):
        transcriber = Transcriber(speech=FakeSpeechModel())
        transcriber._extract_audio_chunk(
            Path("input.wav"), Path("output.mp3"), 0.0, 5.0
        )

        command = mock_run.call_args.args[0]
        self.assertIn("64k", command)
        self.assertIn("16000", command)
        self.assertIn("1", command)
        self.assertIn("env", mock_run.call_args.kwargs)


class TestExtractedAudioCleanup(unittest.TestCase):

    def _run_with_temporary_extraction(self, root: Path, speech):
        video = root / "input.mp4"
        video.write_bytes(b"video")
        extracted_dir = root / "arena-extracted-audio"
        extracted_dir.mkdir()
        transcriber = Transcriber(speech=speech)

        def fake_extract(_video, output):
            output.write_bytes(b"audio")
            return output

        with (
            patch(
                "arena.audio.transcriber.tempfile.mkdtemp",
                return_value=str(extracted_dir),
            ),
            patch.object(transcriber, "extract_audio", side_effect=fake_extract),
        ):
            result = transcriber.transcribe(video)
        return extracted_dir, result

    def test_removes_temporary_extraction_after_success(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            extracted_dir, result = self._run_with_temporary_extraction(
                Path(temp_dir), FakeSpeechModel()
            )

            self.assertEqual(result["text"], "Hello world.")
            self.assertFalse(extracted_dir.exists())

    def test_removes_temporary_extraction_after_provider_failure(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            video = root / "input.mp4"
            video.write_bytes(b"video")
            extracted_dir = root / "arena-extracted-audio"
            extracted_dir.mkdir()
            transcriber = Transcriber(speech=FailingSpeechModel())

            def fake_extract(_video, output):
                output.write_bytes(b"audio")
                return output

            with (
                patch(
                    "arena.audio.transcriber.tempfile.mkdtemp",
                    return_value=str(extracted_dir),
                ),
                patch.object(transcriber, "extract_audio", side_effect=fake_extract),
                self.assertRaisesRegex(RuntimeError, "transcription failed"),
            ):
                transcriber.transcribe(video)

            self.assertFalse(extracted_dir.exists())


class TestTranscriptionCacheIdentity(unittest.TestCase):

    def _args(self, video_path, output_path):
        return SimpleNamespace(
            video=str(video_path),
            output=str(output_path),
            mode="api",
            no_cache=False,
            cookies_from_browser=None,
            provider="openai",
            transcription_provider=None,
            transcription_model="whisper-1",
        )

    def test_matching_profile_cache_does_not_construct_provider(self):
        from arena.cli.commands.transcribe import run_transcribe

        profile = RuntimeProfile.default_openai()
        fingerprint = profile.fingerprint(
            {Capability.SPEECH}, namespace="arena-transcription-v1"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "input.mp3"
            output = Path(temp_dir) / "transcript.json"
            metadata = output.with_suffix(output.suffix + ".arena-cache.json")
            video.write_bytes(b"audio")
            output.write_text(json.dumps({"duration": 1.0, "words": []}))
            metadata.write_text(json.dumps({"transcription_fingerprint": fingerprint}))

            with (
                patch("arena.video.downloader.resolve_input", return_value=video),
                patch("arena.providers.resolve_inference") as mock_resolve,
            ):
                self.assertEqual(run_transcribe(self._args(video, output)), 0)

            mock_resolve.assert_not_called()

    def test_mismatched_profile_cache_is_replaced(self):
        from arena.cli.commands.transcribe import run_transcribe

        profile = RuntimeProfile.default_openai()
        bundle = InferenceBundle(profile=profile, speech=FakeSpeechModel())
        expected = profile.fingerprint(
            {Capability.SPEECH}, namespace="arena-transcription-v1"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            video = Path(temp_dir) / "input.mp3"
            output = Path(temp_dir) / "transcript.json"
            metadata = output.with_suffix(output.suffix + ".arena-cache.json")
            video.write_bytes(b"audio")
            output.write_text(json.dumps({"duration": 99.0, "words": []}))
            metadata.write_text(json.dumps({"transcription_fingerprint": "stale"}))

            with (
                patch("arena.video.downloader.resolve_input", return_value=video),
                patch("arena.providers.resolve_inference", return_value=bundle),
            ):
                self.assertEqual(run_transcribe(self._args(video, output)), 0)

            cache_metadata = json.loads(metadata.read_text())
            transcript = json.loads(output.read_text())
            self.assertEqual(cache_metadata["transcription_fingerprint"], expected)
            self.assertEqual(transcript["duration"], 5.0)


if __name__ == "__main__":
    unittest.main()
