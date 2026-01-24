"""Arena CLI - Main entry point"""

import sys
import argparse
from pathlib import Path

# Fix Windows console encoding for emoji support
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from . import __version__


def main():
    """Main CLI entry point"""

    parser = argparse.ArgumentParser(
        prog='arena',
        description='Arena - AI-Powered Video Clip Generation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  arena process video.mp4
  arena process video.mp4 -n 10 --min 20 --max 60
  arena process video.mp4 --fast -o my_clips
  arena transcribe video.mp4
  arena analyze video.mp4
  arena demo
  arena info video.mp4

Environment:
  OPENAI_API_KEY    Required for transcription and analysis
                    Get from: https://platform.openai.com/api-keys

Documentation:
  See README.md and QUICKSTART.md for detailed usage
        """
    )

    parser.add_argument(
        '--version',
        action='version',
        version=f'Arena {__version__}'
    )

    subparsers = parser.add_subparsers(
        title='commands',
        dest='command',
        help='Available commands'
    )

    # =========================================================================
    # arena extract-audio
    # =========================================================================
    extract_parser = subparsers.add_parser(
        'extract-audio',
        help='Extract audio from video',
        description='Extract audio track from video file'
    )
    extract_parser.add_argument('video', help='Path to input video file')
    extract_parser.add_argument(
        '-o', '--output',
        help='Output audio file (default: video_audio.mp3)'
    )
    extract_parser.add_argument(
        '--format',
        choices=['mp3', 'wav', 'aac', 'm4a', 'flac'],
        default='mp3',
        help='Audio format (default: mp3)'
    )
    extract_parser.add_argument(
        '--bitrate',
        default='192k',
        help='Audio bitrate (default: 192k)'
    )
    extract_parser.add_argument(
        '--sample-rate',
        type=int,
        choices=[16000, 22050, 44100, 48000],
        help='Sample rate in Hz (default: original)'
    )
    extract_parser.add_argument(
        '--mono',
        action='store_true',
        help='Convert to mono (single channel)'
    )

    # =========================================================================
    # arena process
    # =========================================================================
    process_parser = subparsers.add_parser(
        'process',
        help='Run full pipeline: transcribe → analyze → generate clips',
        description='Process video and generate clips automatically'
    )
    process_parser.add_argument('video', help='Path to input video file')
    process_parser.add_argument(
        '-o', '--output',
        default='output',
        help='Output directory (default: output)'
    )
    process_parser.add_argument(
        '-n', '--num-clips',
        type=int,
        default=5,
        help='Number of clips to generate (default: 5)'
    )
    process_parser.add_argument(
        '--min',
        type=int,
        default=None,
        dest='min_duration',
        help='Minimum clip duration in seconds (optional, no default)'
    )
    process_parser.add_argument(
        '--max',
        type=int,
        default=None,
        dest='max_duration',
        help='Maximum clip duration in seconds (optional, no default)'
    )
    process_parser.add_argument(
        '--max-adjustment',
        type=float,
        default=10.0,
        help='Max seconds to adjust clip boundaries for sentence alignment (default: 10.0)'
    )
    process_parser.add_argument(
        '--fast',
        action='store_true',
        help='Fast mode - use stream copy (10x faster, less precise)'
    )
    process_parser.add_argument(
        '--padding',
        type=float,
        default=0.0,
        help='Seconds of padding before/after clips (default: 0.0)'
    )
    process_parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Force re-transcription, ignore cached transcript'
    )
    process_parser.add_argument(
        '--energy-weight',
        type=float,
        default=0.3,
        help='Energy boost weight 0-1 (default: 0.3)'
    )
    process_parser.add_argument(
        '--no-enhance',
        action='store_true',
        help='Skip audio enhancement (use original audio)'
    )
    process_parser.add_argument(
        '--scene-detection',
        action='store_true',
        help='Enable scene detection for better cut point alignment'
    )
    process_parser.add_argument(
        '--use-4layer',
        action='store_true',
        help='Use 4-layer editorial system (higher quality, slower, more expensive)'
    )
    process_parser.add_argument(
        '--editorial-model',
        choices=['gpt-4o', 'gpt-4o-mini'],
        default='gpt-4o',
        help='Model to use for Layers 1-2 (default: gpt-4o, mini saves ~60%% cost)'
    )
    process_parser.add_argument(
        '--export-editorial-layers',
        action='store_true',
        help='Export intermediate results from each editorial layer (requires --use-4layer)'
    )

    # =========================================================================
    # arena transcribe
    # =========================================================================
    transcribe_parser = subparsers.add_parser(
        'transcribe',
        help='Transcribe video audio with OpenAI Whisper',
        description='Transcribe video using OpenAI Whisper API'
    )
    transcribe_parser.add_argument('video', help='Path to input video file')
    transcribe_parser.add_argument(
        '-o', '--output',
        help='Output transcript file (default: video_transcript.json)'
    )
    transcribe_parser.add_argument(
        '--mode',
        choices=['api', 'local'],
        default='api',
        help='Transcription mode: api or local (default: api)'
    )
    transcribe_parser.add_argument(
        '--no-cache',
        action='store_true',
        help='Force re-transcription'
    )

    # =========================================================================
    # arena analyze
    # =========================================================================
    analyze_parser = subparsers.add_parser(
        'analyze',
        help='Analyze video with AI + energy detection',
        description='Analyze video using hybrid AI + audio energy'
    )
    analyze_parser.add_argument('video', help='Path to input video file')
    analyze_parser.add_argument(
        '-t', '--transcript',
        help='Path to transcript JSON (if already transcribed)'
    )
    analyze_parser.add_argument(
        '-o', '--output',
        default='analysis_results.json',
        help='Output analysis file (default: analysis_results.json)'
    )
    analyze_parser.add_argument(
        '-n', '--num-clips',
        type=int,
        default=10,
        help='Number of clips to analyze (default: 10)'
    )
    analyze_parser.add_argument(
        '--min',
        type=int,
        default=None,
        dest='min_duration',
        help='Minimum clip duration in seconds (optional, no default)'
    )
    analyze_parser.add_argument(
        '--max',
        type=int,
        default=None,
        dest='max_duration',
        help='Maximum clip duration in seconds (optional, no default)'
    )
    analyze_parser.add_argument(
        '--max-adjustment',
        type=float,
        default=10.0,
        help='Max seconds to adjust clip boundaries for sentence alignment (default: 10.0)'
    )
    analyze_parser.add_argument(
        '--energy-weight',
        type=float,
        default=0.3,
        help='Energy boost weight 0-1 (default: 0.3)'
    )

    # =========================================================================
    # arena generate
    # =========================================================================
    generate_parser = subparsers.add_parser(
        'generate',
        help='Generate video clips from analysis results',
        description='Generate clips from analysis JSON'
    )
    generate_parser.add_argument('video', help='Path to input video file')
    generate_parser.add_argument('analysis', help='Path to analysis JSON file')
    generate_parser.add_argument(
        '-o', '--output',
        default='clips',
        help='Output directory for clips (default: clips)'
    )
    generate_parser.add_argument(
        '-n', '--num-clips',
        type=int,
        help='Number of clips to generate (default: all from analysis)'
    )
    generate_parser.add_argument(
        '--fast',
        action='store_true',
        help='Fast mode - use stream copy'
    )
    generate_parser.add_argument(
        '--padding',
        type=float,
        default=0.0,
        help='Seconds of padding before/after clips (default: 0.0)'
    )
    generate_parser.add_argument(
        '--no-thumbs',
        action='store_true',
        help='Skip thumbnail generation'
    )

    # =========================================================================
    # arena demo
    # =========================================================================
    demo_parser = subparsers.add_parser(
        'demo',
        help='Run demo with test data (no API key needed)',
        description='Run Arena demo using existing test data'
    )
    demo_parser.add_argument(
        '-o', '--output',
        default='demo_output',
        help='Output directory (default: demo_output)'
    )

    # =========================================================================
    # arena info
    # =========================================================================
    info_parser = subparsers.add_parser(
        'info',
        help='Show video metadata and information',
        description='Display video file information'
    )
    info_parser.add_argument('video', help='Path to video file')
    info_parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON'
    )

    # =========================================================================
    # arena format
    # =========================================================================
    format_parser = subparsers.add_parser(
        'format',
        help='Format clips for specific social media platforms',
        description='Convert clips to optimal format for TikTok, Instagram, YouTube, etc.'
    )
    format_parser.add_argument(
        'input',
        help='Path to video file or directory of clips'
    )
    format_parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output directory for formatted clips'
    )
    format_parser.add_argument(
        '-p', '--platform',
        required=True,
        choices=['tiktok', 'instagram-reels', 'youtube-shorts', 'youtube', 'instagram-feed', 'twitter', 'linkedin'],
        help='Target platform'
    )
    format_parser.add_argument(
        '--crop',
        default='center',
        choices=['center', 'smart', 'top', 'bottom'],
        help='Crop strategy for aspect ratio conversion (default: center)'
    )
    format_parser.add_argument(
        '--pad',
        default='blur',
        choices=['blur', 'black', 'white', 'color'],
        help='Pad strategy for aspect ratio conversion (default: blur)'
    )
    format_parser.add_argument(
        '--pad-color',
        default='#000000',
        help='Padding color in hex format (default: #000000)'
    )
    format_parser.add_argument(
        '--no-quality',
        action='store_true',
        help='Disable high quality encoding (faster, smaller files)'
    )

    # =========================================================================
    # arena detect-scenes
    # =========================================================================
    detect_scenes_parser = subparsers.add_parser(
        'detect-scenes',
        help='Detect scene changes in video',
        description='Analyze video to find scene boundaries for better clip alignment'
    )
    detect_scenes_parser.add_argument(
        'video',
        help='Path to video file'
    )
    detect_scenes_parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output JSON file for scene data'
    )
    detect_scenes_parser.add_argument(
        '--threshold',
        type=float,
        default=0.4,
        help='Scene detection threshold (0.0-1.0, default: 0.4)'
    )
    detect_scenes_parser.add_argument(
        '--min-duration',
        type=float,
        default=2.0,
        help='Minimum scene duration in seconds (default: 2.0)'
    )
    detect_scenes_parser.add_argument(
        '--report',
        action='store_true',
        help='Generate detailed scene report'
    )

    # Parse arguments
    args = parser.parse_args()

    # Show help if no command
    if not args.command:
        parser.print_help()
        return 0

    # Dispatch to command handlers
    try:
        if args.command == 'extract-audio':
            from .commands.extract_audio import run_extract_audio
            return run_extract_audio(args)
        elif args.command == 'process':
            from .commands.process import run_process
            return run_process(args)
        elif args.command == 'transcribe':
            from .commands.transcribe import run_transcribe
            return run_transcribe(args)
        elif args.command == 'analyze':
            from .commands.analyze import run_analyze
            return run_analyze(args)
        elif args.command == 'generate':
            from .commands.generate import run_generate
            return run_generate(args)
        elif args.command == 'demo':
            from .commands.demo import run_demo
            return run_demo(args)
        elif args.command == 'info':
            from .commands.info import run_info
            return run_info(args)
        elif args.command == 'format':
            from .commands.format import run_format
            return run_format(args)
        elif args.command == 'detect-scenes':
            from .commands.detect_scenes import run_detect_scenes
            return run_detect_scenes(args)
        else:
            parser.print_help()
            return 1

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
