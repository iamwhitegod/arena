"""Atomic installation and integrity validation for local model artifacts."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import ssl
import stat
import tempfile
from typing import Callable, Optional
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, HTTPSHandler, Request, build_opener

from arena.providers.base import ProviderError

from .registry import MODEL_PACKS, ModelArtifact, ModelPack, ModelSpec, get_model


_ALLOWED_DOWNLOAD_HOSTS = frozenset({"huggingface.co"})
_ALLOWED_DOWNLOAD_SUFFIXES = (".huggingface.co", ".hf.co")
_CUSTOM_MANIFEST = ".arena-model.json"
_PACK_MANIFEST = ".arena-pack.json"
_READ_CHUNK = 1024 * 1024


def _safe_download_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return (
        parsed.scheme == "https"
        and parsed.username is None
        and parsed.password is None
        and (host in _ALLOWED_DOWNLOAD_HOSTS or host.endswith(_ALLOWED_DOWNLOAD_SUFFIXES))
    )


class _ValidatedRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not _safe_download_url(newurl):
            raise ProviderError(
                "Model download redirected to an unapproved host.",
                code="model_download_redirect",
                retryable=False,
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _verified_download_opener():
    """Use an explicit trusted CA bundle without overriding operator policy."""
    cafile = None
    if not os.environ.get("SSL_CERT_FILE"):
        try:
            import certifi

            cafile = certifi.where()
        except ImportError:
            pass
    context = ssl.create_default_context(cafile=cafile)
    return build_opener(_ValidatedRedirectHandler(), HTTPSHandler(context=context))


class ModelManager:
    """Install and verify models beneath an owner-private Arena model root."""

    def __init__(self, root: Path):
        # Keep a lexical absolute path for symlink-component checks. Containment
        # checks separately use the canonical path returned by ensure_root().
        self.root = Path(root).expanduser().absolute()

    def ensure_root(self) -> Path:
        if self.root.is_symlink():
            raise self._unsafe_path("Model root must not be a symlink")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not self.root.is_dir():
            raise self._unsafe_path("Model root is not a directory")
        if os.name != "nt":
            os.chmod(self.root, 0o700)
        return self.root.resolve()

    def installed_path(self, spec: ModelSpec) -> Path:
        root = self.ensure_root()
        candidate = root / spec.install_name
        self._assert_contained(candidate, root)
        return candidate

    def verify_model(self, spec: ModelSpec) -> Path:
        target = self.installed_path(spec)
        if spec.format == "gguf":
            if len(spec.artifacts) != 1:
                raise ProviderError(
                    "Invalid GGUF registry entry.", code="model_registry", retryable=False
                )
            self._verify_file(target, spec.artifacts[0])
            return target

        self._reject_symlink(target)
        if not target.is_dir():
            raise self._missing(spec)
        for artifact in spec.artifacts:
            self._verify_file(target / artifact.filename, artifact)
        return target

    def verify_custom_gguf(self, path: Path) -> Path:
        root = self.ensure_root()
        original = Path(path)
        self._reject_symlink_chain(original, root)
        resolved = original.resolve(strict=False)
        self._assert_contained(resolved, root)
        if resolved.suffix.lower() != ".gguf" or not resolved.is_file():
            raise ProviderError(
                "Custom local models must be regular .gguf files.",
                code="local_no_model",
                retryable=False,
            )
        if resolved.stat().st_size > 64 * 1024 * 1024 * 1024:
            raise ProviderError(
                "Custom model exceeds Arena's size limit.",
                code="model_oversized",
                retryable=False,
            )
        digest_path = Path(f"{resolved}.sha256")
        self._reject_symlink_chain(Path(f"{original}.sha256"), root)
        try:
            expected = digest_path.read_text(encoding="ascii").strip().split()[0].lower()
        except (OSError, IndexError, UnicodeError) as exc:
            raise ProviderError(
                f"Custom model requires an owner-provided SHA-256 sidecar: {digest_path.name}",
                code="model_hash_missing",
                retryable=False,
            ) from exc
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise ProviderError(
                "Custom model SHA-256 sidecar is invalid.",
                code="model_hash_invalid",
                retryable=False,
            )
        self._verify_digest(resolved, expected)
        return resolved

    def verify_custom_speech_directory(self, path: Path) -> Path:
        root = self.ensure_root()
        original = Path(path)
        self._reject_symlink_chain(original, root)
        resolved = original.resolve(strict=False)
        self._assert_contained(resolved, root)
        if not resolved.is_dir():
            raise ProviderError(
                "Custom speech model directory was not found.",
                code="local_no_model",
                retryable=False,
            )
        manifest_path = resolved / _CUSTOM_MANIFEST
        self._reject_symlink_chain(original / _CUSTOM_MANIFEST, root)
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeError) as exc:
            raise ProviderError(
                f"Custom speech models require {_CUSTOM_MANIFEST} with file hashes.",
                code="model_hash_missing",
                retryable=False,
            ) from exc
        if not isinstance(manifest, dict):
            raise ProviderError(
                "Custom speech model manifest is invalid.",
                code="model_hash_invalid",
                retryable=False,
            )
        files = manifest.get("files")
        if manifest.get("version") != 1 or not isinstance(files, dict) or not files:
            raise ProviderError(
                "Custom speech model manifest is invalid.",
                code="model_hash_invalid",
                retryable=False,
            )
        for relative_name, expected in files.items():
            if (
                not isinstance(relative_name, str)
                or not isinstance(expected, str)
                or Path(relative_name).is_absolute()
                or ".." in Path(relative_name).parts
            ):
                raise self._unsafe_path("Custom speech manifest contains an unsafe path")
            file_path = resolved / relative_name
            self._assert_contained(file_path.resolve(strict=False), resolved)
            self._reject_symlink_chain(original / relative_name, root)
            if not file_path.is_file():
                raise ProviderError(
                    "Custom speech model is incomplete.",
                    code="local_no_model",
                    retryable=False,
                )
            self._verify_digest(file_path, expected.lower())
        return resolved

    def install_model(
        self,
        spec: ModelSpec,
        *,
        fetcher: Optional[Callable[[ModelArtifact, Path], None]] = None,
    ) -> Path:
        root = self.ensure_root()
        target = self.installed_path(spec)
        if target.exists() or target.is_symlink():
            return self.verify_model(spec)

        required_bytes = sum(
            artifact.expected_bytes or artifact.max_bytes for artifact in spec.artifacts
        )
        try:
            free_bytes = shutil.disk_usage(root).free
        except OSError as exc:
            raise ProviderError(
                "Available model storage could not be measured.",
                code="model_storage_unknown",
                retryable=False,
            ) from exc
        # Preserve a 1 GiB operating-system reserve in addition to staging.
        if free_bytes < required_bytes + 1024 ** 3:
            raise ProviderError(
                "There is not enough free disk space for this verified model.",
                code="model_disk_limit",
                retryable=False,
            )

        staging: Optional[Path] = Path(tempfile.mkdtemp(prefix=".arena-model-", dir=root))
        try:
            for artifact in spec.artifacts:
                assert staging is not None
                destination = staging / artifact.filename
                destination.parent.mkdir(parents=True, exist_ok=True)
                (fetcher or self._download)(artifact, destination)
                self._verify_file(destination, artifact)
                if os.name != "nt":
                    os.chmod(destination, 0o600)

            if spec.format == "gguf":
                assert staging is not None
                source = staging / spec.artifacts[0].filename
                os.replace(source, target)
                return self.verify_model(spec)

            assert staging is not None
            os.replace(staging, target)
            staging = None
            return self.verify_model(spec)
        finally:
            if staging is not None and staging.exists():
                shutil.rmtree(staging)

    def install_pack(
        self,
        pack: ModelPack,
        *,
        fetcher: Optional[Callable[[ModelArtifact, Path], None]] = None,
    ) -> dict[str, Path]:
        if MODEL_PACKS.get(pack.name) != pack:
            raise ProviderError(
                "Only an immutable Arena model pack can be installed.",
                code="model_registry",
                retryable=False,
            )
        installed = {
            capability: self.install_model(get_model(identifier), fetcher=fetcher)
            for capability, identifier in (
                ("chat", pack.chat),
                ("embedding", pack.embedding),
                ("speech", pack.speech),
            )
        }
        root = self.ensure_root()
        manifest = root / _PACK_MANIFEST
        if manifest.is_symlink():
            raise self._unsafe_path("Model pack manifest must not be a symlink")
        payload = {
            "version": 1,
            "pack": pack.name,
            "models": {
                "chat": pack.chat,
                "embedding": pack.embedding,
                "speech": pack.speech,
            },
        }
        descriptor, temporary_name = tempfile.mkstemp(prefix=".arena-pack-", dir=root)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as output:
                json.dump(payload, output, sort_keys=True, separators=(",", ":"))
                output.flush()
                os.fsync(output.fileno())
            if os.name != "nt":
                os.chmod(temporary, 0o600)
            os.replace(temporary, manifest)
        finally:
            temporary.unlink(missing_ok=True)
        return installed

    def _download(self, artifact: ModelArtifact, destination: Path) -> None:
        if not _safe_download_url(artifact.url):
            raise ProviderError(
                "Model source is not allowlisted.",
                code="model_download_source",
                retryable=False,
            )
        opener = _verified_download_opener()
        request = Request(artifact.url, headers={"User-Agent": "Arena-ModelManager/1"})
        total = 0
        try:
            with opener.open(request, timeout=60) as response, destination.open("xb") as output:
                length_header = response.headers.get("Content-Length")
                if length_header and int(length_header) > artifact.max_bytes:
                    raise ProviderError(
                        "Model download exceeds its registered size limit.",
                        code="model_oversized",
                        retryable=False,
                    )
                while True:
                    chunk = response.read(_READ_CHUNK)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > artifact.max_bytes:
                        raise ProviderError(
                            "Model download exceeds its registered size limit.",
                            code="model_oversized",
                            retryable=False,
                        )
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
        except ProviderError:
            destination.unlink(missing_ok=True)
            raise
        except Exception as exc:
            destination.unlink(missing_ok=True)
            raise ProviderError(
                "Verified model download failed.",
                code="model_download_failed",
                retryable=True,
            ) from exc

    def _verify_file(self, path: Path, artifact: ModelArtifact) -> None:
        self._reject_symlink(path)
        try:
            info = path.stat()
        except OSError as exc:
            raise ProviderError(
                f"Required model artifact is missing: {artifact.filename}",
                code="local_no_model",
                retryable=False,
            ) from exc
        if not stat.S_ISREG(info.st_mode):
            raise self._unsafe_path("Model artifact is not a regular file")
        if info.st_size > artifact.max_bytes:
            raise ProviderError(
                "Model artifact exceeds its registered size limit.",
                code="model_oversized",
                retryable=False,
            )
        if artifact.expected_bytes is not None and info.st_size != artifact.expected_bytes:
            raise ProviderError(
                f"Model artifact size mismatch: {artifact.filename}",
                code="model_hash_mismatch",
                retryable=False,
            )
        self._verify_digest(path, artifact.sha256)

    @staticmethod
    def _verify_digest(path: Path, expected: str) -> None:
        if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected):
            raise ProviderError(
                "Registered model digest is invalid.",
                code="model_registry",
                retryable=False,
            )
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(_READ_CHUNK), b""):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise ProviderError(
                f"Model integrity verification failed: {path.name}",
                code="model_hash_mismatch",
                retryable=False,
            )

    @staticmethod
    def _reject_symlink(path: Path) -> None:
        try:
            if path.is_symlink():
                raise ProviderError(
                    "Model paths must not contain symlinks.",
                    code="local_path_traversal",
                    retryable=False,
                )
        except OSError as exc:
            raise ProviderError(
                "Unable to validate model path.",
                code="local_path_traversal",
                retryable=False,
            ) from exc

    def _reject_symlink_chain(self, path: Path, root: Path) -> None:
        """Reject symlinks in every existing component beneath ``root``."""
        del root  # canonical containment is checked separately after resolution
        root_absolute = self.root
        candidate = path if path.is_absolute() else root_absolute / path
        candidate = candidate.absolute()
        try:
            relative = candidate.relative_to(root_absolute)
        except ValueError as exc:
            raise ModelManager._unsafe_path(
                "Model path escaped the configured root"
            ) from exc

        current = root_absolute
        self._reject_symlink(current)
        for part in relative.parts:
            current = current / part
            self._reject_symlink(current)

    @staticmethod
    def _assert_contained(candidate: Path, root: Path) -> None:
        try:
            candidate.resolve(strict=False).relative_to(root.resolve(strict=False))
        except ValueError as exc:
            raise ModelManager._unsafe_path("Model path escaped the configured root") from exc

    @staticmethod
    def _unsafe_path(message: str) -> ProviderError:
        return ProviderError(message, code="local_path_traversal", retryable=False)

    @staticmethod
    def _missing(spec: ModelSpec) -> ProviderError:
        return ProviderError(
            f"Verified local model '{spec.identifier}' is not installed.",
            code="local_no_model",
            retryable=False,
        )
