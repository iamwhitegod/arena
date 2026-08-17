"""Resolve only integrity-verified local model paths beneath Arena's root."""

import os
from pathlib import Path
from typing import Optional

from arena.providers.base import ProviderError

from .manager import ModelManager
from .registry import find_model
from .selection import active_model_for_capability


_ARENA_MODEL_ROOT_ENV = "ARENA_MODEL_ROOT"
_ARENA_MODEL_ROOT_DEFAULT = Path.home() / ".arena" / "models"


class ModelLocator:
    """Resolve registered models or explicitly manifested custom models."""

    def __init__(self, root: Optional[Path] = None):
        configured_root = root or Path(
            os.environ.get(_ARENA_MODEL_ROOT_ENV, str(_ARENA_MODEL_ROOT_DEFAULT))
        )
        self._manager = ModelManager(configured_root)
        self._root = self._manager.root

    @property
    def root(self) -> Path:
        return self._root

    def resolve_gguf(self, name_or_path: str, *, capability: str = "chat") -> Path:
        """Resolve a verified chat or embedding GGUF model.

        Registered identifiers are checked against Arena-published digests.
        Custom files require a sibling ``<model>.sha256`` integrity sidecar.
        ``auto`` selects the registered default for the requested capability;
        it never chooses an arbitrary first file.
        """
        if capability not in {"chat", "embedding"}:
            raise ValueError("GGUF capability must be chat or embedding")

        identifier = (
            active_model_for_capability(capability, self._root)
            if name_or_path == "auto"
            else name_or_path
        )
        spec = find_model(identifier)
        if spec is not None:
            if spec.capability != capability or spec.format != "gguf":
                raise ProviderError(
                    f"Verified model '{identifier}' does not support {capability}.",
                    code="local_model_capability",
                    retryable=False,
                )
            return self._manager.verify_model(spec)

        candidate = Path(identifier)
        if not candidate.is_absolute():
            candidate = self._root / candidate
        return self._manager.verify_custom_gguf(candidate)

    def resolve_speech_model(self, name_or_path: str) -> str:
        """Resolve a verified CTranslate2 speech model directory.

        ``auto`` and the legacy ``base`` alias select Arena's pinned Faster
        Whisper base model. Custom directories require ``.arena-model.json``
        with SHA-256 hashes for every runtime file.
        """
        if name_or_path == "auto":
            identifier = active_model_for_capability("speech", self._root)
        elif name_or_path == "base":
            identifier = "faster-whisper-base"
        else:
            identifier = name_or_path
        spec = find_model(identifier)
        if spec is not None:
            if spec.capability != "speech" or spec.format != "ctranslate2":
                raise ProviderError(
                    f"Verified model '{identifier}' is not a speech model.",
                    code="local_model_capability",
                    retryable=False,
                )
            return str(self._manager.verify_model(spec))

        candidate = Path(identifier)
        if not candidate.is_absolute():
            candidate = self._root / candidate
        return str(self._manager.verify_custom_speech_directory(candidate))
