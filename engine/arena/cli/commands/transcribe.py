"""arena transcribe - Transcribe video audio"""

import hashlib
import json
from contextlib import suppress
from pathlib import Path
from arena.audio.transcriber import Transcriber
from arena.cli.protocol import progress, result


def run_transcribe(args):
    """Transcribe video or audio file (supports URLs)"""
    from arena.video.downloader import resolve_input

    try:
        video_path = resolve_input(args.video, mode='audio', cookies_from_browser=getattr(args, 'cookies_from_browser', None))
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        return 1

    if not video_path.exists():
        print(f"❌ Error: File not found: {args.video}")
        return 1

    # Build a non-secret transcription identity before constructing adapters.
    # --mode local is deprecated; redirect through the provider system.
    effective_provider = getattr(args, 'provider', None)
    effective_trans_provider = getattr(args, 'transcription_provider', None)
    effective_trans_model = getattr(args, 'transcription_model', None)

    if args.mode == "local" and not effective_provider and not effective_trans_provider:
        import warnings
        warnings.warn(
            "--mode local is deprecated. Use --provider local instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        effective_provider = "local"

    from arena.providers import Capability, RuntimeProfile
    try:
        runtime_profile = RuntimeProfile.from_args(
            provider=effective_provider,
            transcription_provider=effective_trans_provider,
            transcription_model=effective_trans_model,
        )
    except ValueError as e:
        from arena.cli.public_errors import format_public_error
        print(format_public_error(e, "Provider configuration failed"))
        return 1
    transcription_fingerprint = runtime_profile.fingerprint(
        {Capability.SPEECH}, namespace="arena-transcription-v1"
    )
    speech = None
    inference = None

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = video_path.parent / f"{video_path.stem}_transcript.json"

    cache_metadata_path = output_path.with_suffix(output_path.suffix + ".arena-cache.json")

    # Reuse only artifacts produced by the same transcription binding.
    cache_matches = False
    if not args.no_cache and output_path.exists() and cache_metadata_path.exists():
        try:
            with open(cache_metadata_path) as f:
                cache_metadata = json.load(f)
            cache_matches = cache_metadata.get("transcription_fingerprint") == transcription_fingerprint
        except (OSError, ValueError, TypeError):
            cache_matches = False

    if cache_matches:
        with open(output_path) as f:
            transcript_data = json.load(f)
        progress("transcription", 100, "Using cached transcript")
        result({"success": True, "cached": True, "duration": transcript_data.get("duration", 0), "wordCount": len(transcript_data.get("words", [])), "language": transcript_data.get("language", "unknown"), "outputFile": str(output_path)})
        return 0

    from arena.providers import resolve_inference, Capability
    from arena.providers.base import ProviderAuthError
    try:
        inference = resolve_inference(
            required={Capability.SPEECH}, profile=runtime_profile,
        )
        speech = inference.require_speech()
    except ProviderAuthError as e:
        from arena.cli.public_errors import format_public_error
        print(format_public_error(e))
        print("   Get one at: https://platform.openai.com/api-keys")
        print("   Set it with: export OPENAI_API_KEY='sk-your-key-here'")
        return 1

    print(f"\n🎤 Transcribing: {video_path.name}")
    print(f"   Mode: {args.mode}")
    print(f"   Output: {output_path}\n")

    try:
        progress("transcription", 5, "Preparing audio")
        transcriber = Transcriber(speech=speech)

        print("⏳ Transcribing (this may take a few minutes)...")
        progress("transcription", None, "Transcribing audio")
        transcript_data = transcriber.transcribe(video_path)

        # Save transcript
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(transcript_data, f, indent=2)
        with open(cache_metadata_path, 'w') as f:
            json.dump({"transcription_fingerprint": transcription_fingerprint}, f, indent=2)

        print(f"\n✅ Transcription complete!")
        print(f"   Duration: {transcript_data.get('duration', 0):.1f}s")
        print(f"   Words:    {len(transcript_data.get('words', []))}")
        print(f"   Language: {transcript_data.get('language', 'unknown')}")
        print(f"   Saved to: {output_path}\n")

        progress("transcription", 100, "Transcription complete")
        result({"success": True, "cached": False, "duration": transcript_data.get("duration", 0), "wordCount": len(transcript_data.get("words", [])), "language": transcript_data.get("language", "unknown"), "outputFile": str(output_path)})
        return 0

    except Exception as e:
        from arena.cli.public_errors import format_public_error
        print(f"\n{format_public_error(e, 'Transcription failed')}")
        return 1
    finally:
        if inference is not None:
            with suppress(Exception):
                inference.close()
