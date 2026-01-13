#!/usr/bin/env python3
import argparse
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
        from arena.ai.analyzer import TranscriptAnalyzer
        from arena.clipping.scorer import SegmentScorer
        from arena.export.exporter import Exporter

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

        # Stage 2: Transcription
        transcript_cache_path = cache_dir / "transcript.json"
        transcript = None

        # Check cache first
        if transcript_cache_path.exists():
            reporter.report("Transcription", 0, "Loading cached transcript...")
            try:
                with open(transcript_cache_path, 'r') as f:
                    transcript = json.load(f)
                reporter.report("Transcription", 100, "Loaded from cache")
            except:
                transcript = None

        # Transcribe if not cached
        if transcript is None:
            reporter.report("Transcription", 0, "Starting transcription...")

            # Determine whisper mode from environment variable
            whisper_mode = os.getenv("ARENA_WHISPER_MODE", "api").lower()
            api_key = os.getenv("OPENAI_API_KEY")

            # Validate configuration based on mode
            if whisper_mode == "api":
                if not api_key:
                    reporter.error(
                        "OPENAI_API_KEY environment variable not set.\n"
                        "Option 1: Set API key: export OPENAI_API_KEY='sk-...'\n"
                        "Option 2: Use local Whisper: export ARENA_WHISPER_MODE='local'"
                    )
                    return 1
                reporter.report("Transcription", 10, "Using OpenAI Whisper API...")
            else:
                reporter.report("Transcription", 10, "Using local Whisper model (first run downloads model)...")
                # No API key needed for local mode
                api_key = None

            try:
                transcriber = Transcriber(api_key=api_key, mode=whisper_mode)
            except ValueError as e:
                reporter.error(str(e))
                return 1

            # Check if audio enhancement is enabled
            enhance_audio = os.getenv("ARENA_ENHANCE_AUDIO", "false").lower() == "true"

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
                    reporter.error(f"Audio enhancement failed: {str(e)}\nFalling back to original audio")
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
                reporter.error(f"Transcription failed: {str(e)}")
                return 1

        # Stage 3: AI Analysis
        reporter.report("Analysis", 0, "Analyzing transcript with AI...")

        try:
            analyzer = TranscriptAnalyzer(api_key=os.getenv("OPENAI_API_KEY"))
            ai_segments = analyzer.analyze_transcript(
                transcript,
                target_clips=args.clip_count,
                min_duration=args.min_duration,
                max_duration=args.max_duration
            )
            reporter.report("Analysis", 100, f"Identified {len(ai_segments)} interesting segments")
        except Exception as e:
            reporter.error(f"AI analysis failed: {str(e)}")
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
        reporter.error(str(e))
        import traceback
        traceback.print_exc(file=sys.stderr)
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

    args = parser.parse_args()

    if args.command == 'process':
        return process_video(args)
    else:
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
