#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
import os
from pathlib import Path
from typing import Dict, Any

class ProgressReporter:
    """Handles progress reporting to the Node.js CLI"""

    @staticmethod
    def report(stage: str, progress: float, message: str):
        """Send progress update to stdout as JSON"""
        update = {
            "type": "progress",
            "stage": stage,
            "progress": progress,
            "message": message
        }
        print(json.dumps(update), flush=True)

    @staticmethod
    def result(data: Dict[str, Any]):
        """Send final result to stdout as JSON"""
        result = {
            "type": "result",
            "data": data
        }
        print(json.dumps(result), flush=True)

    @staticmethod
    def error(message: str):
        """Send error to stderr"""
        print(f"ERROR: {message}", file=sys.stderr, flush=True)


def process_video(args):
    """Main video processing pipeline"""
    reporter = ProgressReporter()

    try:
        from arena.video.loader import VideoLoader
        from arena.audio.transcriber import Transcriber
        from arena.editorial import FourLayerAdapter
        from arena.clipping.scorer import SegmentScorer
        from arena.export.exporter import Exporter
        from arena.providers import Capability, RuntimeProfile, resolve_inference
        from arena.providers.base import ProviderAuthError

        video_path = Path(args.video_path)
        output_dir = Path(args.output_dir)
        cache_dir = output_dir.parent / "cache"

        # Validate input
        if not video_path.exists():
            reporter.error(f"Video file not found: {video_path}")
            return 1

        # Create output directories
        output_dir.mkdir(parents=True, exist_ok=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "clips").mkdir(exist_ok=True)

        # Stage 1: Load Video
        reporter.report("Loading", 0, "Reading video file...")
        loader = VideoLoader(video_path)
        if not loader.validate():
            reporter.error(f"Invalid video file: {video_path}")
            return 1
        video_metadata = loader.load()
        reporter.report("Loading", 100, f"Video loaded: {video_metadata['filename']}")

        runtime_profile = RuntimeProfile.from_args(
            provider=getattr(args, "provider", None),
            chat_provider=getattr(args, "chat_provider", None),
            chat_model=getattr(args, "chat_model", None),
            overview_chat_provider=getattr(args, "overview_chat_provider", None),
            overview_chat_model=getattr(args, "overview_chat_model", None),
            embedding_provider=getattr(args, "embedding_provider", None),
            embedding_model=getattr(args, "embedding_model", None),
            transcription_provider=getattr(args, "transcription_provider", None),
            transcription_model=getattr(args, "transcription_model", None),
        )

        # Stage 2: Transcription
        whisper_mode = os.getenv("ARENA_WHISPER_MODE", "api").lower()
        enhance_audio = os.getenv("ARENA_ENHANCE_AUDIO", "false").lower() == "true"
        if whisper_mode == "local":
            speech_binding_fingerprint = hashlib.sha256(
                b"arena-transcription-v1:local:faster-whisper-base:verified"
            ).hexdigest()[:20]
        else:
            speech_binding_fingerprint = runtime_profile.fingerprint(
                {Capability.SPEECH}, namespace="arena-transcription-v1"
            )
        speech_fingerprint = hashlib.sha256(
            (
                f"arena-transcript-cache-v2:{speech_binding_fingerprint}:"
                f"enhance_audio={enhance_audio}"
            ).encode("utf-8")
        ).hexdigest()[:20]
        transcript_cache_path = cache_dir / f"transcript_{speech_fingerprint}.json"
        transcript = None

        # Check cache first
        if transcript_cache_path.exists():
            reporter.report("Transcription", 0, "Loading cached transcript...")
            try:
                with open(transcript_cache_path, 'r') as f:
                    transcript = json.load(f)
                reporter.report("Transcription", 100, "Loaded from cache")
            except (json.JSONDecodeError, IOError, OSError) as e:
                import logging
                logging.getLogger(__name__).warning(f"Failed to load transcript cache: {e}")
                transcript = None

        # Transcribe if not cached
        if transcript is None:
            reporter.report("Transcription", 0, "Starting transcription...")

            if whisper_mode == "local":
                reporter.report("Transcription", 10, "Using verified local Whisper model...")
                try:
                    transcriber = Transcriber(mode="local")
                except ValueError as e:
                    reporter.error(str(e))
                    return 1
            else:
                reporter.report("Transcription", 10, "Using Whisper API...")
                try:
                    speech_bundle = resolve_inference(
                        required={Capability.SPEECH}, profile=runtime_profile,
                    )
                    transcriber = Transcriber(speech=speech_bundle.require_speech())
                except ProviderAuthError as e:
                    reporter.error(
                        f"{e}\n"
                        "Option 1: Set API key: export OPENAI_API_KEY='sk-...'\n"
                        "Option 2: Install the verified local model and set "
                        "ARENA_WHISPER_MODE='local'"
                    )
                    return 1
                except ValueError as e:
                    reporter.error(str(e))
                    return 1

            # Check if audio enhancement is enabled
            if enhance_audio:
                reporter.report("Transcription", 20, "Enhancing audio quality...")
                try:
                    from arena.audio.enhance import AudioEnhancer

                    provider = os.getenv("ARENA_AUDIO_PROVIDER", "local")
                    enhancer = AudioEnhancer(provider=provider)

                    # Check if audio needs enhancement
                    enhanced_cache_path = cache_dir / f"{video_path.stem}_enhanced.wav"

                    if not enhanced_cache_path.exists():
                        # Extract and enhance audio
                        temp_audio_path = cache_dir / f"{video_path.stem}_audio.mp3"
                        transcriber.extract_audio(video_path, temp_audio_path)

                        # Enhance the audio
                        enhancer.enhance(temp_audio_path, enhanced_cache_path)
                        reporter.report("Transcription", 30, "Audio enhanced (cached)")
                    else:
                        reporter.report("Transcription", 30, "Using cached enhanced audio")

                    # Use enhanced audio for transcription
                    # Temporarily replace video path with enhanced audio
                    original_video_path = video_path
                    video_path = enhanced_cache_path

                except Exception as e:
                    from arena.cli.public_errors import format_public_error
                    reporter.error(format_public_error(e, "Audio enhancement failed"))
                    enhance_audio = False

            if not enhance_audio:
                reporter.report("Transcription", 30, "Extracting audio...")

            try:
                transcript = transcriber.transcribe(video_path, cache_dir=cache_dir)
                reporter.report("Transcription", 90, "Transcription complete")

                # Cache the transcript
                with open(transcript_cache_path, 'w') as f:
                    json.dump(transcript, f, indent=2)
                reporter.report("Transcription", 100, "Cached for future use")
            except Exception as e:
                from arena.cli.public_errors import format_public_error
                reporter.error(format_public_error(e, "Transcription failed"))
                return 1

        # Stage 3: AI Analysis
        reporter.report("Analysis", 0, "Analyzing transcript with AI...")

        try:
            try:
                edit_bundle = resolve_inference(
                    required={Capability.CHAT, Capability.EMBEDDING},
                    profile=runtime_profile,
                )
            except ProviderAuthError as e:
                reporter.error(str(e))
                return 1
            analyzer = FourLayerAdapter(inference=edit_bundle)
            ai_segments = analyzer.analyze_transcript(
                transcript,
                target_clips=args.clip_count,
                min_duration=args.min_duration,
                max_duration=args.max_duration
            )
            reporter.report("Analysis", 100, f"Identified {len(ai_segments)} interesting segments")
        except Exception as e:
            from arena.cli.public_errors import format_public_error
            reporter.error(format_public_error(e, "AI analysis failed"))
            return 1

        # Stage 4: Scoring
        reporter.report("Scoring", 0, "Scoring and ranking segments...")

        # For Sprint 2, we only have AI scores
        # Sprint 3 will add audio energy and visual detection
        scorer = SegmentScorer(ai_weight=1.0, audio_weight=0.0, visual_weight=0.0)
        scored_segments = scorer.score_segments(ai_segments)

        # Select top clips
        selected_clips = scorer.select_top_clips(
            scored_segments,
            target_count=args.clip_count,
            min_duration=args.min_duration,
            max_duration=args.max_duration
        )
        reporter.report("Scoring", 100, f"Selected {len(selected_clips)} top clips")

        # Stage 5: Clip Generation (Placeholder for Sprint 4)
        reporter.report("Clipping", 0, "Preparing clip metadata...")
        # Sprint 4 will implement actual video extraction and subtitle burning
        # For now, we just prepare the metadata

        for i, clip in enumerate(selected_clips):
            clip["files"] = {
                "raw": f"clips/clip_{clip['id']}_raw.mp4",
                "subtitled": f"clips/clip_{clip['id']}_subtitled.mp4",
                "thumbnail": f"clips/clip_{clip['id']}_thumbnail.jpg"
            }

        reporter.report("Clipping", 100, "Clip metadata prepared (actual generation in Sprint 4)")

        # Stage 6: Export
        reporter.report("Export", 0, "Saving metadata and transcript...")

        exporter = Exporter(output_dir)

        # Export metadata
        metadata_path = exporter.export_metadata(video_path, selected_clips)

        # Export full transcript
        transcript_output_path = exporter.export_transcript(transcript)

        reporter.report("Export", 100, "Export complete")

        # Generate summary
        summary = exporter.create_summary_report(selected_clips)
        print("\n" + summary, file=sys.stderr)

        # Send final result
        reporter.result({
            "clips": selected_clips,
            "metadata_path": str(metadata_path),
            "transcript_path": str(transcript_output_path),
            "success": True
        })

        return 0

    except Exception as e:
        from arena.cli.public_errors import format_public_error
        reporter.error(format_public_error(e))
        return 1


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Arena - AI-powered video processing engine"
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Process command
    process_parser = subparsers.add_parser('process', help='Process a video file')
    process_parser.add_argument('video_path', help='Path to video file')
    process_parser.add_argument('--output-dir', required=True, help='Output directory')
    process_parser.add_argument('--min-duration', type=int, default=30,
                                help='Minimum clip duration in seconds')
    process_parser.add_argument('--max-duration', type=int, default=90,
                                help='Maximum clip duration in seconds')
    process_parser.add_argument('--clip-count', type=int, default=10,
                                help='Target number of clips to generate')
    process_parser.add_argument('--provider', choices=['openai', 'local', 'ollama'], default=None)
    process_parser.add_argument('--chat-provider', choices=['openai', 'local', 'ollama'], default=None)
    process_parser.add_argument('--chat-model', default=None)
    process_parser.add_argument('--overview-chat-provider', choices=['openai', 'local', 'ollama'], default=None)
    process_parser.add_argument('--overview-chat-model', default=None)
    process_parser.add_argument('--embedding-provider', choices=['openai', 'local', 'ollama'], default=None)
    process_parser.add_argument('--embedding-model', default=None)
    process_parser.add_argument('--transcription-provider', choices=['openai', 'local', 'ollama'], default=None)
    process_parser.add_argument('--transcription-model', default=None)

    args = parser.parse_args()

    if args.command == 'process':
        return process_video(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
