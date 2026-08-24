"""arena analyze - Analyze video with AI + energy"""

import json
from contextlib import suppress
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

    # Resolve a credential-free profile first. Native models are constructed
    # one stage at a time so speech can be released before editorial analysis.
    from arena.providers import resolve_inference, Capability, RuntimeProfile

    transcript_path = Path(args.transcript) if args.transcript else None
    if transcript_path is not None and not transcript_path.exists():
        print(f"❌ Error: Transcript file not found: {args.transcript}")
        return 1

    has_transcript = transcript_path is not None
    required = {Capability.CHAT, Capability.OVERVIEW_CHAT, Capability.EMBEDDING}
    if not has_transcript:
        required.add(Capability.SPEECH)

    try:
        runtime_profile = RuntimeProfile.from_args(
            provider=getattr(args, 'provider', None),
            chat_provider=getattr(args, 'chat_provider', None),
            chat_model=getattr(args, 'chat_model', None) or getattr(args, 'editorial_model', None),
            overview_chat_provider=getattr(args, 'overview_chat_provider', None),
            overview_chat_model=getattr(args, 'overview_chat_model', None),
            embedding_provider=getattr(args, 'embedding_provider', None),
            embedding_model=getattr(args, 'embedding_model', None),
            transcription_provider=getattr(args, 'transcription_provider', None),
            transcription_model=getattr(args, 'transcription_model', None),
            required_capabilities=required,
        )
    except ValueError as e:
        from arena.cli.public_errors import format_public_error
        print(format_public_error(e, "Provider configuration failed"))
        return 1

    print(f"\n🧠 Analyzing: {video_path.name}\n")

    # Load or generate transcript
    if transcript_path is not None:
        print(f"📖 Loading transcript: {transcript_path.name}")
        with open(transcript_path) as f:
            transcript_data = json.load(f)
        progress("transcription", 100, "Loaded existing transcript")
    else:
        print("🎤 Transcribing video...")
        speech_inference = None
        try:
            speech_inference = resolve_inference(
                required={Capability.SPEECH}, profile=runtime_profile,
            )
            transcriber = Transcriber(speech=speech_inference.require_speech())
            progress("transcription", 5, "Preparing audio")
            progress("transcription", None, "Transcribing audio")
            transcript_data = transcriber.transcribe(video_path)
            progress("transcription", 100, "Transcription complete")
        except Exception as e:
            from arena.cli.public_errors import format_public_error
            print(format_public_error(e, "Transcription failed"))
            return 1
        finally:
            if speech_inference is not None:
                with suppress(Exception):
                    speech_inference.close()

    print(f"   ✓ Duration: {transcript_data.get('duration', 0):.1f}s\n")

    inference = None
    try:
        inference = resolve_inference(
            required={Capability.CHAT, Capability.OVERVIEW_CHAT, Capability.EMBEDDING},
            profile=runtime_profile,
        )
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
        progress("analysis", None, "Analyzing transcript with AI")
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
        from arena.cli.public_errors import format_public_error
        print(f"\n{format_public_error(e, 'Analysis failed')}")
        return 1
    finally:
        if inference is not None:
            with suppress(Exception):
                inference.close()
