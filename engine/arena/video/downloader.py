"""Video/audio download from URLs using yt-dlp"""

import hashlib
import subprocess
import shutil
from pathlib import Path
from typing import Optional


DEFAULT_CACHE_DIR = Path.home() / '.arena' / 'cache' / 'downloads'


def is_url(input_path: str) -> bool:
    """Check if input looks like a URL."""
    return input_path.startswith('http://') or input_path.startswith('https://')


def _check_ytdlp() -> str:
    """Check that yt-dlp is installed and return its path."""
    ytdlp_path = shutil.which('yt-dlp')
    if ytdlp_path is None:
        raise RuntimeError(
            "yt-dlp is required for URL downloads but was not found.\n"
            "Install it with:\n"
            "  pip install yt-dlp\n"
            "  # or: brew install yt-dlp (macOS)\n"
            "  # or: apt install yt-dlp (Debian/Ubuntu)"
        )
    return ytdlp_path


def _get_js_runtimes() -> str:
    """Detect available JS runtimes for yt-dlp to solve YouTube challenges.

    Node.js is the preferred runtime because Arena already requires it.
    """
    runtimes = []
    if shutil.which('node'):
        runtimes.append('node')
    if shutil.which('bun'):
        runtimes.append('bun')
    if shutil.which('deno'):
        runtimes.append('deno')
    if not runtimes:
        print("  ⚠️  No JavaScript runtime found.")
        print("  YouTube downloads require Node.js (already an Arena prerequisite).")
        return 'node'
    return ','.join(runtimes)


def _format_download_error(error_msg: str, url: str, command: str, cookies_from_browser: Optional[str] = None) -> str:
    """Format yt-dlp errors with actionable suggestions."""
    if 'n challenge' in error_msg or 'page needs to be reloaded' in error_msg:
        if cookies_from_browser:
            return (
                f"yt-dlp failed (YouTube challenge — cookies from {cookies_from_browser} didn't help):\n{error_msg}\n\n"
                f"URL: {url}\n\n"
                f"Fixes to try:\n"
                f"  1. Fully quit {cookies_from_browser} (not just close — quit the app) and retry\n"
                f"  2. Update yt-dlp:  pip install -U yt-dlp\n"
                f"  3. Try a different browser:  --cookies-from-browser chrome"
            )
        return (
            f"yt-dlp failed (YouTube challenge solving failed):\n{error_msg}\n\n"
            f"URL: {url}\n\n"
            f"Fixes to try:\n"
            f"  1. Update yt-dlp:  pip install -U yt-dlp\n"
            f"  2. Use cookies:    arena {command} \"{url}\" --cookies-from-browser chrome"
        )
    if 'Sign in to confirm' in error_msg or 'HTTP Error 429' in error_msg:
        if cookies_from_browser:
            return (
                f"yt-dlp failed (auth required — cookies from {cookies_from_browser} didn't help):\n{error_msg}\n\n"
                f"URL: {url}\n\n"
                f"Fixes to try:\n"
                f"  1. Fully quit {cookies_from_browser} (not just close — quit the app) and retry\n"
                f"  2. Update yt-dlp:  pip install -U yt-dlp\n"
                f"  3. Try a different browser:  --cookies-from-browser chrome\n"
                f"  4. Set a default:  arena config set cookies_from_browser {cookies_from_browser}"
            )
        return (
            f"yt-dlp failed (authentication required):\n{error_msg}\n\n"
            f"URL: {url}\n\n"
            f"Fix: Use --cookies-from-browser to authenticate:\n"
            f"  arena {command} \"{url}\" --cookies-from-browser chrome"
        )
    return f"yt-dlp failed to download:\n{error_msg}\n\nURL: {url}"


def _url_cache_key(url: str) -> str:
    """Generate a stable cache key from URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def download_video(
    url: str,
    cache_dir: Optional[Path] = None,
    max_height: int = 1080,
    cookies_from_browser: Optional[str] = None,
) -> Path:
    """
    Download video from URL using yt-dlp. Uses cache to avoid re-downloading.

    Args:
        url: Video URL (YouTube, Vimeo, Twitter, etc.)
        cache_dir: Where to store downloads (default: ~/.arena/cache/downloads/)
        max_height: Maximum video height (default: 1080p)
        cookies_from_browser: Browser to extract cookies from (e.g. 'chrome', 'firefox', 'safari')

    Returns:
        Path to downloaded video file
    """
    ytdlp = _check_ytdlp()
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = _url_cache_key(url)

    # Check cache
    existing = list(cache_dir.glob(f"{cache_key}.*"))
    if existing:
        cached = existing[0]
        print(f"  Using cached download: {cached.name}")
        return cached

    print(f"  Downloading video from URL...")
    print(f"  This may take a minute depending on video length.\n")

    output_template = str(cache_dir / f"{cache_key}.%(ext)s")

    cmd = [
        ytdlp,
        '--no-playlist',
        '-f', f'bestvideo[height<={max_height}]+bestaudio/best[height<={max_height}]/best',
        '--merge-output-format', 'mp4',
        '-o', output_template,
        '--newline',
        '--js-runtimes', _get_js_runtimes(),
        url,
    ]

    if cookies_from_browser:
        cmd.insert(-1, '--cookies-from-browser')
        cmd.insert(-1, cookies_from_browser)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error_msg = result.stderr.strip()
        raise RuntimeError(_format_download_error(error_msg, url, 'process', cookies_from_browser))

    downloaded = list(cache_dir.glob(f"{cache_key}.*"))
    if not downloaded:
        raise RuntimeError(f"Download completed but file not found in {cache_dir}")

    downloaded_path = downloaded[0]
    size_mb = downloaded_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Downloaded: {downloaded_path.name} ({size_mb:.1f} MB)\n")
    return downloaded_path


def download_audio(
    url: str,
    cache_dir: Optional[Path] = None,
    audio_format: str = 'mp3',
    cookies_from_browser: Optional[str] = None,
) -> Path:
    """
    Download audio-only from URL using yt-dlp. Faster and smaller than full video.

    Args:
        url: Video URL
        cache_dir: Where to store downloads
        audio_format: Output audio format (default: mp3)
        cookies_from_browser: Browser to extract cookies from (e.g. 'chrome', 'firefox', 'brave')

    Returns:
        Path to downloaded audio file
    """
    ytdlp = _check_ytdlp()
    cache_dir = cache_dir or DEFAULT_CACHE_DIR
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_key = _url_cache_key(url) + '_audio'

    # Check cache
    existing = list(cache_dir.glob(f"{cache_key}.*"))
    if existing:
        cached = existing[0]
        print(f"  Using cached audio: {cached.name}")
        return cached

    print(f"  Downloading audio from URL...")
    print(f"  (Audio-only download — faster than full video.)\n")

    output_template = str(cache_dir / f"{cache_key}.%(ext)s")

    cmd = [
        ytdlp,
        '--no-playlist',
        '-x',
        '--audio-format', audio_format,
        '-o', output_template,
        '--newline',
        '--js-runtimes', _get_js_runtimes(),
        url,
    ]

    if cookies_from_browser:
        cmd.insert(-1, '--cookies-from-browser')
        cmd.insert(-1, cookies_from_browser)

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error_msg = result.stderr.strip()
        raise RuntimeError(_format_download_error(error_msg, url, 'transcribe', cookies_from_browser))

    downloaded = list(cache_dir.glob(f"{cache_key}.*"))
    if not downloaded:
        raise RuntimeError(f"Audio download completed but file not found in {cache_dir}")

    downloaded_path = downloaded[0]
    size_mb = downloaded_path.stat().st_size / (1024 * 1024)
    print(f"  ✓ Downloaded audio: {downloaded_path.name} ({size_mb:.1f} MB)\n")
    return downloaded_path


def resolve_input(input_path: str, mode: str = 'video', cookies_from_browser: Optional[str] = None) -> Path:
    """
    If input is a URL, download it. If it's a local path, return as-is.

    Args:
        input_path: URL or file path
        mode: 'video' for full video download, 'audio' for audio-only
        cookies_from_browser: Browser to extract cookies from (e.g. 'chrome', 'firefox', 'safari')

    Returns:
        Path to local file (downloaded or original)
    """
    if not is_url(input_path):
        return Path(input_path)

    if mode == 'audio':
        return download_audio(input_path, cookies_from_browser=cookies_from_browser)
    else:
        return download_video(input_path, cookies_from_browser=cookies_from_browser)
