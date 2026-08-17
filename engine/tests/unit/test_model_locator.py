"""Tests for model path resolution and security."""

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from arena.models.locator import ModelLocator
from arena.providers.base import ProviderError


class TestResolveGguf(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.locator = ModelLocator(root=self.root)

    def tearDown(self):
        self.tempdir.cleanup()

    def _write_custom_model(self, name: str = "model.gguf") -> Path:
        model_path = self.root / name
        payload = b"verified custom gguf"
        model_path.write_bytes(payload)
        Path(f"{model_path}.sha256").write_text(
            hashlib.sha256(payload).hexdigest(), encoding="ascii"
        )
        return model_path

    def test_auto_with_no_registered_model_installed_raises(self):
        with self.assertRaises(ProviderError) as ctx:
            self.locator.resolve_gguf("auto")
        self.assertEqual(ctx.exception.code, "local_no_model")

    def test_auto_never_selects_arbitrary_gguf_file(self):
        self._write_custom_model("test-model.gguf")
        with self.assertRaises(ProviderError) as ctx:
            self.locator.resolve_gguf("auto")
        self.assertEqual(ctx.exception.code, "local_no_model")

    def test_relative_name_resolves_under_root(self):
        model_path = self._write_custom_model("my-model.gguf")
        resolved = self.locator.resolve_gguf("my-model.gguf")
        self.assertEqual(resolved, model_path.resolve())

    def test_relative_name_not_found_raises(self):
        with self.assertRaises(ProviderError) as ctx:
            self.locator.resolve_gguf("nonexistent.gguf")
        self.assertEqual(ctx.exception.code, "local_no_model")

    def test_absolute_path_under_root_succeeds(self):
        model_path = self._write_custom_model()
        resolved = self.locator.resolve_gguf(str(model_path))
        self.assertEqual(resolved, model_path.resolve())

    def test_absolute_path_outside_root_rejected(self):
        outside = Path(tempfile.mktemp(suffix=".gguf"))
        payload = b"outside"
        outside.write_bytes(payload)
        sidecar = Path(f"{outside}.sha256")
        sidecar.write_text(hashlib.sha256(payload).hexdigest(), encoding="ascii")
        try:
            with self.assertRaises(ProviderError) as ctx:
                self.locator.resolve_gguf(str(outside))
            self.assertEqual(ctx.exception.code, "local_path_traversal")
        finally:
            outside.unlink()
            sidecar.unlink()

    def test_path_traversal_rejected(self):
        # Create a file outside root
        outside = self.root.parent / "escape.gguf"
        outside.touch()
        try:
            with self.assertRaises(ProviderError) as ctx:
                self.locator.resolve_gguf("../escape.gguf")
            self.assertIn(ctx.exception.code, ("local_path_traversal", "local_no_model"))
        finally:
            outside.unlink(missing_ok=True)


class TestResolveSpeechModel(unittest.TestCase):

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.locator = ModelLocator(root=self.root)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_unverified_size_keyword_is_rejected(self):
        for size in ("tiny", "small", "medium", "large-v3"):
            with self.assertRaises(ProviderError):
                self.locator.resolve_speech_model(size)

    def test_auto_resolves_registered_verified_model(self):
        expected = self.root / "faster-whisper-base"
        with patch.object(self.locator._manager, "verify_model", return_value=expected):
            self.assertEqual(self.locator.resolve_speech_model("auto"), str(expected))

    def _write_custom_speech_model(self) -> Path:
        model_dir = self.root / "whisper-model"
        model_dir.mkdir()
        artifact = model_dir / "model.bin"
        payload = b"verified speech model"
        artifact.write_bytes(payload)
        (model_dir / ".arena-model.json").write_text(
            json.dumps({
                "version": 1,
                "files": {"model.bin": hashlib.sha256(payload).hexdigest()},
            }),
            encoding="utf-8",
        )
        return model_dir

    def test_absolute_dir_under_root(self):
        model_dir = self._write_custom_speech_model()
        result = self.locator.resolve_speech_model(str(model_dir))
        self.assertEqual(result, str(model_dir.resolve()))


if __name__ == "__main__":
    unittest.main()
