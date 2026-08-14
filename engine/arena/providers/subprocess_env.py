"""
Build a scrubbed environment for media subprocesses.

Provider credentials (API keys) should not be inherited by FFmpeg,
ffprobe, yt-dlp, or other media tools. This module builds a minimal
allowlisted environment instead of trying to enumerate every secret.
"""

import os
import re
from typing import Optional

# Variables required for executable lookup, temporary files, locale, dynamic
# libraries, TLS roots, fonts, and browser-profile discovery. Proxy variables
# are deliberately excluded because proxy URLs frequently embed credentials.
_MEDIA_ENV_ALLOWLIST = frozenset({
    "APPDATA",
    "COMSPEC",
    "DYLD_FALLBACK_LIBRARY_PATH",
    "DYLD_LIBRARY_PATH",
    "FFMPEG_DATADIR",
    "FONTCONFIG_FILE",
    "FONTCONFIG_PATH",
    "HOME",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "LD_LIBRARY_PATH",
    "LOCALAPPDATA",
    "PATH",
    "PATHEXT",
    "SSL_CERT_DIR",
    "SSL_CERT_FILE",
    "SYSTEMROOT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "TZ",
    "USERPROFILE",
    "WINDIR",
    "XDG_CACHE_HOME",
    "XDG_CONFIG_HOME",
})
_SENSITIVE_KEY_RE = re.compile(
    r"(^|_)(api_?key|authorization|cookie|credential|password|secret|session|token)($|_)",
    re.IGNORECASE,
)


def scrubbed_env(extra: Optional[dict] = None) -> dict:
    """Return a copy of os.environ with credential variables removed.

    Args:
        extra: Additional environment variables to set (overrides).

    Returns:
        A dict suitable for passing as subprocess env=.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() in _MEDIA_ENV_ALLOWLIST
    }
    if extra:
        sensitive = [key for key in extra if _SENSITIVE_KEY_RE.search(key.replace("-", "_"))]
        if sensitive:
            raise ValueError(
                f"Refusing sensitive media subprocess environment key: {sensitive[0]}"
            )
        unsupported = [key for key in extra if key.upper() not in _MEDIA_ENV_ALLOWLIST]
        if unsupported:
            raise ValueError(
                f"Unsupported media subprocess environment key: {unsupported[0]}"
            )
        env.update(extra)
    return env
