"""arena analyze - Analyze video with AI + energy"""

import os
import json
from pathlib import Path
from arena.audio.transcriber import Transcriber
from arena.audio.energy import AudioEnergyAnalyzer
from arena.ai.analyzer import TranscriptAnalyzer
from arena.ai.hybrid import HybridAnalyzer


def run_analyze(args):
    """Analyze video with hybrid AI + energy"""

    video_path = Path(args.video)

    if not video_path.exists():
        print(f"❌ Error: Video file not found: {args.video}")
        return 1

    # Check for API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Error: OPENAI_API_KEY environment variable not set")
        return 1

    print(f"\n🧠 Analyzing: {video_path.name}\n")

    # Load or generate transcript
    if args.transcript:
        transcript_path = Path(args.transcript)
        if not transcript_path.exists():
            print(f"❌ Error: Transcript file not found: {args.transcript}")
            return 1

        print(f"📖 Loading transcript: {transcript_path.name}")
        with open(transcript_path) as f:
            transcript_data = json.load(f)
    else:
        print("🎤 Transcribing video...")
        transcriber = Transcriber(api_key=api_key)
        transcript_data = transcriber.transcribe(video_path)

    print(f"   ✓ Duration: {transcript_data.get('duration', 0):.1f}s\n")

    try:
        # Initialize analyzers
        print("🔧 Initializing analyzers...")
        ai_analyzer = TranscriptAnalyzer(api_key=api_key)
        energy_analyzer = AudioEnergyAnalyzer(video_path=video_path)
        hybrid = HybridAnalyzer(
            ai_analyzer=ai_analyzer,
            energy_analyzer=energy_analyzer,
            energy_weight=args.energy_weight
        )

        # Run analysis
        print("⚡ Running hybrid analysis...\n")
        results = hybrid.analyze_video(
            video_path=video_path,
            transcript_data=transcript_data,
            target_clips=args.num_clips,
            min_duration=args.min_duration,
            max_duration=args.max_duration
        )

        # Print summary
        hybrid.print_summary(results)

        # Save results
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        hybrid.export_results(results, output_path)

        print(f"\n✅ Analysis complete!")
        print(f"   Saved to: {output_path}\n")

        return 0

    except Exception as e:
        print(f"\n❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
