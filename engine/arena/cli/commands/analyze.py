"""arena analyze - Analyze video with AI + energy"""

import os
import json
from pathlib import Path
from arena.audio.transcriber import Transcriber
from arena.audio.energy import AudioEnergyAnalyzer
from arena.ai.hybrid import HybridAnalyzer
from arena.editorial import FourLayerAdapter
from arena.cli.protocol import progress, result


def run_analyze(args):
    """Analyze video with hybrid AI + energy"""

    video_path = Path(args.video)

    if not video_path.exists():
        print(f"❌ Error: Video file not found: {args.video}")
        return 1

    # Resolve inference providers
    from arena.providers import resolve_inference, Capability
    from arena.providers.base import ProviderAuthError

    has_transcript = args.transcript and Path(args.transcript).exists()
    required = {Capability.CHAT, Capability.EMBEDDING}
    if not has_transcript:
        required.add(Capability.SPEECH)

    try:
        inference = resolve_inference(
            required=required,
            provider=getattr(args, 'provider', None),
            chat_provider=getattr(args, 'chat_provider', None),
            chat_model=getattr(args, 'chat_model', None) or getattr(args, 'editorial_model', None),
            overview_chat_provider=getattr(args, 'overview_chat_provider', None),
            overview_chat_model=getattr(args, 'overview_chat_model', None),
            embedding_provider=getattr(args, 'embedding_provider', None),
            embedding_model=getattr(args, 'embedding_model', None),
            transcription_provider=getattr(args, 'transcription_provider', None),
            transcription_model=getattr(args, 'transcription_model', None),
        )
    except ProviderAuthError as e:
        print(f"❌ Error: {e}")
        return 1
    except ValueError as e:
        print(f"❌ Provider configuration failed: {e}")
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
        progress("transcription", 100, "Loaded existing transcript")
    else:
        print("🎤 Transcribing video...")
        transcriber = Transcriber(speech=inference.require_speech())
        progress("transcription", 5, "Transcribing audio")
        transcript_data = transcriber.transcribe(video_path)
        progress("transcription", 100, "Transcription complete")

    print(f"   ✓ Duration: {transcript_data.get('duration', 0):.1f}s\n")

    try:
        # Initialize analyzers
        print("🔧 Initializing analyzers...")
        ai_analyzer = FourLayerAdapter(inference=inference)
        energy_analyzer = AudioEnergyAnalyzer(video_path=video_path)
        hybrid = HybridAnalyzer(
            ai_analyzer=ai_analyzer,
            energy_analyzer=energy_analyzer,
            energy_weight=args.energy_weight
        )

        # Run analysis
        print("⚡ Running hybrid analysis...\n")
        progress("analysis", 10, "Scoring candidate moments")
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

        clips = results.get("clips", [])
        progress("analysis", 100, "Analysis complete")
        result({"success": True, "videoDuration": transcript_data.get("duration", 0), "wordCount": len(transcript_data.get("words", [])), "momentsFound": len(clips), "estimatedClips": len(clips), "outputFile": str(output_path)})
        return 0

    except Exception as e:
        from arena.providers.base import ProviderError
        if isinstance(e, ProviderError):
            print(f"\n❌ Analysis failed: {e}")
        else:
            print(f"\n❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()
        return 1
