"""arena transcribe - Transcribe video audio"""

import os
import json
from pathlib import Path
from arena.audio.transcriber import Transcriber


def run_transcribe(args):
    """Transcribe video audio"""

    video_path = Path(args.video)

    if not video_path.exists():
        print(f"❌ Error: Video file not found: {args.video}")
        return 1

    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        print("   Get one at: https://platform.openai.com/api-keys")
        print("   Set it with: export OPENAI_API_KEY='sk-your-key-here'")
        return 1

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = video_path.parent / f"{video_path.stem}_transcript.json"

    # Check cache
    if not args.no_cache and output_path.exists():
        print(f"✓ Using cached transcript: {output_path}")
        return 0

    print(f"\n🎤 Transcribing: {video_path.name}")
    print(f"   Mode: {args.mode}")
    print(f"   Output: {output_path}\n")

    try:
        transcriber = Transcriber(api_key=api_key, mode=args.mode)

        print("⏳ Transcribing (this may take a few minutes)...")
        transcript_data = transcriber.transcribe(video_path)

        # Save transcript
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(transcript_data, f, indent=2)

        print(f"\n✅ Transcription complete!")
        print(f"   Duration: {transcript_data.get('duration', 0):.1f}s")
        print(f"   Words:    {len(transcript_data.get('words', []))}")
        print(f"   Language: {transcript_data.get('language', 'unknown')}")
        print(f"   Saved to: {output_path}\n")

        return 0

    except Exception as e:
        print(f"\n❌ Transcription failed: {e}")
        return 1
