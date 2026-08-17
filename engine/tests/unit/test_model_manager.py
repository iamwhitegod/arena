"""Security and integrity tests for verified local model management."""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from arena.models.manager import (
    ModelManager,
    _ValidatedRedirectHandler,
    _safe_download_url,
    _verified_download_opener,
)
from arena.models.registry import MODEL_PACKS, ModelArtifact, ModelSpec
from arena.models.selection import active_model_for_capability
from arena.providers.base import ProviderError


class TestModelManager(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "models"
        self.manager = ModelManager(self.root)
        self.payload = b"verified model payload"
        self.artifact = ModelArtifact(
            filename="source.gguf",
            url="https://huggingface.co/example/model/resolve/revision/source.gguf",
            sha256=hashlib.sha256(self.payload).hexdigest(),
            max_bytes=1024,
            expected_bytes=len(self.payload),
        )
        self.spec = ModelSpec(
            identifier="test-chat",
            capability="chat",
            format="gguf",
            install_name="test-chat.gguf",
            source="example/model",
            revision="revision",
            license="test-only",
            artifacts=(self.artifact,),
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def test_install_is_verified_before_becoming_visible(self):
        path = self.manager.install_model(
            self.spec,
            fetcher=lambda _artifact, destination: destination.write_bytes(self.payload),
        )

        self.assertEqual(path.read_bytes(), self.payload)
        self.assertEqual(path, self.root.resolve() / self.spec.install_name)
        self.assertFalse(any(item.name.startswith(".arena-model-") for item in self.root.iterdir()))

    def test_corrupt_download_leaves_no_target_or_staging_directory(self):
        with self.assertRaises(ProviderError) as ctx:
            self.manager.install_model(
                self.spec,
                fetcher=lambda _artifact, destination: destination.write_bytes(b"corrupt"),
            )

        self.assertEqual(ctx.exception.code, "model_hash_mismatch")
        self.assertFalse((self.root / self.spec.install_name).exists())
        self.assertFalse(any(item.name.startswith(".arena-model-") for item in self.root.iterdir()))

    @patch("arena.models.manager.shutil.disk_usage")
    def test_install_rejects_insufficient_disk_before_fetch(self, disk_usage):
        disk_usage.return_value = MagicMock(free=512)
        fetcher = MagicMock()

        with self.assertRaises(ProviderError) as ctx:
            self.manager.install_model(self.spec, fetcher=fetcher)

        self.assertEqual(ctx.exception.code, "model_disk_limit")
        fetcher.assert_not_called()

    def test_corrupted_installed_model_is_rejected(self):
        target = self.root / self.spec.install_name
        self.manager.ensure_root()
        target.write_bytes(b"corrupt")

        with self.assertRaises(ProviderError) as ctx:
            self.manager.verify_model(self.spec)

        self.assertEqual(ctx.exception.code, "model_hash_mismatch")

    def test_registry_install_name_cannot_escape_root(self):
        unsafe = ModelSpec(
            identifier="unsafe",
            capability="chat",
            format="gguf",
            install_name="../escape.gguf",
            source="example/model",
            revision="revision",
            license="test-only",
            artifacts=(self.artifact,),
        )

        with self.assertRaises(ProviderError) as ctx:
            self.manager.installed_path(unsafe)

        self.assertEqual(ctx.exception.code, "local_path_traversal")

    @unittest.skipIf(os.name == "nt", "symlink creation requires elevated Windows privileges")
    def test_custom_model_rejects_symlinked_parent_component(self):
        self.manager.ensure_root()
        real = self.root / "real"
        real.mkdir()
        model = real / "custom.gguf"
        model.write_bytes(self.payload)
        Path(f"{model}.sha256").write_text(
            hashlib.sha256(self.payload).hexdigest(), encoding="ascii"
        )
        link = self.root / "linked"
        link.symlink_to(real, target_is_directory=True)

        with self.assertRaises(ProviderError) as ctx:
            self.manager.verify_custom_gguf(link / "custom.gguf")

        self.assertEqual(ctx.exception.code, "local_path_traversal")

    def test_non_object_speech_manifest_returns_typed_error(self):
        model_dir = self.root / "speech"
        model_dir.mkdir(parents=True)
        (model_dir / ".arena-model.json").write_text(json.dumps([]), encoding="utf-8")

        with self.assertRaises(ProviderError) as ctx:
            self.manager.verify_custom_speech_directory(model_dir)

        self.assertEqual(ctx.exception.code, "model_hash_invalid")

    def test_download_allowlist_rejects_credentials_and_unapproved_hosts(self):
        self.assertTrue(_safe_download_url(self.artifact.url))
        self.assertFalse(_safe_download_url("http://huggingface.co/model.gguf"))
        self.assertFalse(_safe_download_url("https://user@huggingface.co/model.gguf"))
        self.assertFalse(_safe_download_url("https://huggingface.co.example.com/model.gguf"))

    def test_redirect_to_unapproved_host_is_rejected(self):
        handler = _ValidatedRedirectHandler()

        with self.assertRaises(ProviderError) as ctx:
            handler.redirect_request(
                MagicMock(),
                MagicMock(),
                302,
                "Found",
                MagicMock(),
                "https://example.com/model.gguf",
            )

        self.assertEqual(ctx.exception.code, "model_download_redirect")

    @patch.dict(os.environ, {}, clear=True)
    @patch("arena.models.manager.build_opener")
    @patch("arena.models.manager.ssl.create_default_context")
    def test_download_opener_uses_locked_ca_bundle(self, create_context, build_opener):
        import certifi

        _verified_download_opener()

        create_context.assert_called_once_with(cafile=certifi.where())
        self.assertEqual(len(build_opener.call_args.args), 2)

    @patch.dict(os.environ, {"SSL_CERT_FILE": "/operator/ca.pem"}, clear=True)
    @patch("arena.models.manager.build_opener")
    @patch("arena.models.manager.ssl.create_default_context")
    def test_download_opener_preserves_explicit_ca_policy(self, create_context, build_opener):
        _verified_download_opener()

        create_context.assert_called_once_with(cafile=None)

    @patch("arena.models.manager.build_opener")
    def test_declared_oversized_download_is_rejected_before_streaming(self, build_opener):
        response = MagicMock()
        response.headers = {"Content-Length": "2048"}
        build_opener.return_value.open.return_value.__enter__.return_value = response
        destination = self.root / "download.gguf"
        self.manager.ensure_root()

        with self.assertRaises(ProviderError) as ctx:
            self.manager._download(self.artifact, destination)

        self.assertEqual(ctx.exception.code, "model_oversized")
        response.read.assert_not_called()
        self.assertFalse(destination.exists())

    @patch("arena.models.manager.build_opener")
    def test_stream_over_size_limit_is_removed(self, build_opener):
        response = MagicMock()
        response.headers = {}
        response.read.side_effect = [b"x" * 1025, b""]
        build_opener.return_value.open.return_value.__enter__.return_value = response
        destination = self.root / "download.gguf"
        self.manager.ensure_root()

        with self.assertRaises(ProviderError) as ctx:
            self.manager._download(self.artifact, destination)

        self.assertEqual(ctx.exception.code, "model_oversized")
        self.assertFalse(destination.exists())

    @patch("arena.models.manager.get_model")
    def test_pack_selection_is_written_only_after_all_models_install(self, get_model):
        pack = MODEL_PACKS["lite"]
        get_model.side_effect = lambda identifier: MagicMock(identifier=identifier)
        self.manager.install_model = MagicMock(
            side_effect=[self.root / "chat", self.root / "embedding", self.root / "speech"]
        )

        self.manager.install_pack(pack)

        manifest = json.loads((self.root / ".arena-pack.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["pack"], "lite")
        self.assertEqual(manifest["models"]["speech"], pack.speech)

    def test_active_pack_manifest_fails_closed_when_tampered(self):
        self.manager.ensure_root()
        (self.root / ".arena-pack.json").write_text(
            '{"version":1,"pack":"lite","models":{"chat":"tampered"}}',
            encoding="utf-8",
        )

        with self.assertRaisesRegex(ValueError, "does not match"):
            active_model_for_capability("chat", self.root)


if __name__ == "__main__":
    unittest.main()
