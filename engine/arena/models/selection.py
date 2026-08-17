"""Resolve the explicitly installed active model pack without network access."""

import json
import os
from pathlib import Path
from typing import Optional

from .registry import DEFAULT_MODEL_BY_CAPABILITY, MODEL_PACKS, ModelCapability


_PACK_MANIFEST = ".arena-pack.json"
_MAX_MANIFEST_BYTES = 4096


def configured_model_root() -> Path:
    return Path(os.environ.get("ARENA_MODEL_ROOT", Path.home() / ".arena" / "models"))


def active_model_for_capability(
    capability: ModelCapability,
    root: Optional[Path] = None,
) -> str:
    """Return the active pack's exact model, or the registry default.

    A present but malformed manifest fails closed so a corrupted selection can
    never silently change the model and checkpoint identity.
    """
    model_root = (root or configured_model_root()).expanduser().absolute()
    manifest_path = model_root / _PACK_MANIFEST
    if not manifest_path.exists():
        return DEFAULT_MODEL_BY_CAPABILITY[capability]
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ValueError("Local model pack selection is unsafe")
    try:
        if manifest_path.stat().st_size > _MAX_MANIFEST_BYTES:
            raise ValueError("Local model pack selection is oversized")
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Local model pack selection is invalid") from exc
    if not isinstance(payload, dict) or payload.get("version") != 1:
        raise ValueError("Local model pack selection is invalid")
    pack_name = payload.get("pack")
    pack = MODEL_PACKS.get(pack_name) if isinstance(pack_name, str) else None
    expected = (
        {"chat": pack.chat, "embedding": pack.embedding, "speech": pack.speech}
        if pack is not None
        else None
    )
    if payload.get("models") != expected:
        raise ValueError("Local model pack selection does not match Arena's registry")
    return expected[capability]
