"""Platform formatting command for Arena CLI"""
import argparse
import json
from pathlib import Path
from arena.export.platform_formatter import PlatformFormatter
from arena.cli.protocol import progress


def _emit_result(data):
    """Emit a JSON result line for the TypeScript bridge to parse."""
    print(json.dumps({"type": "result", "data": data}), flush=True)


def setup_format_command(subparsers):
    """Setup format subcommand"""
    parser = subparsers.add_parser(
        'format',
        help='Format clips for specific social media platforms',
        description='Convert clips to optimal format for TikTok, Instagram, YouTube, etc.'
    )

    parser.add_argument(
        'input',
        type=str,
        help='Path to video file or directory of clips'
    )

    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output directory for formatted clips'
    )

    parser.add_argument(
        '-p', '--platform',
        type=str,
        required=True,
        choices=[
            'tiktok',
            'instagram-reels',
            'youtube-shorts',
            'youtube',
            'instagram-feed',
            'twitter',
            'linkedin'
        ],
        help='Target platform'
    )

    parser.add_argument(
        '--crop',
        type=str,
        default='center',
        choices=['center', 'smart', 'top', 'bottom'],
        help='Crop strategy for aspect ratio conversion (default: center)'
    )

    parser.add_argument(
        '--pad',
        type=str,
        default='blur',
        choices=['blur', 'black', 'white', 'color'],
        help='Pad strategy for aspect ratio conversion (default: blur)'
    )

    parser.add_argument(
        '--pad-color',
        type=str,
        default='#000000',
        help='Padding color in hex format (default: #000000)'
    )

    parser.add_argument(
        '--no-quality',
        action='store_true',
        help='Disable high quality encoding (faster, smaller files)'
    )
    parser.add_argument(
        '--captions',
        type=str,
        default=None,
        help='Path to SRT subtitle file to burn into clips'
    )
    parser.add_argument(
        '--caption-font-size',
        type=int,
        default=None,
        help='Caption font size (default: 24)'
    )
    parser.add_argument(
        '--caption-color',
        type=str,
        default=None,
        help='Caption text color: white, yellow, red, black (default: white)'
    )
    parser.add_argument(
        '--caption-position',
        type=str,
        default=None,
        choices=['bottom', 'top', 'middle'],
        help='Caption position (default: bottom)'
    )

    parser.set_defaults(func=run_format)


def run_format(args):
    """Execute platform formatting"""
    print("\n📐 PLATFORM FORMATTING")
    print("=" * 70)

    input_path = Path(args.input)
    output_dir = Path(args.output)

    # Validate input
    if not input_path.exists():
        print(f"❌ Error: Input not found: {input_path}")
        _emit_result({"success": False, "error": f"Input not found: {input_path}"})
        return 1

    # Initialize formatter
    formatter = PlatformFormatter()

    # Get platform spec
    spec = formatter.get_platform_spec(args.platform)
    print(f"\nTarget Platform: {spec.name}")
    print(f"Resolution: {spec.width}x{spec.height} ({spec.aspect_ratio})")
    print(f"Max Duration: {spec.max_duration}s" if spec.max_duration else "Max Duration: Unlimited")
    print(f"Bitrate: {spec.recommended_bitrate}")

    caption_style = {}
    if args.caption_font_size:
        caption_style['font_size'] = args.caption_font_size
    if args.caption_color:
        caption_style['color'] = args.caption_color
    if args.caption_position:
        caption_style['position'] = args.caption_position
    caption_style = caption_style or None

    # Process input
    if input_path.is_file():
        # Single file
        print(f"\nInput: {input_path.name}")

        # Show preview
        source_dims = formatter.get_video_dimensions(input_path)
        preview = formatter.get_format_preview(
            source_dims['width'],
            source_dims['height'],
            args.platform
        )
        print(f"\nTransformation Preview:")
        print(f"  Source: {source_dims['width']}x{source_dims['height']}")
        print(f"  Target: {spec.width}x{spec.height}")
        print(f"  Action: {preview['transformation']['description']}")

        # Format
        print(f"\n⏳ Formatting...")
        output_dir.mkdir(parents=True, exist_ok=True)

        stem = input_path.stem
        output_filename = f"{stem}_{args.platform}.mp4"
        output_path = output_dir / output_filename

        # Build caption style if provided
        subtitle_path = None
        if args.captions:
            subtitle_path = Path(args.captions)
            if not subtitle_path.exists():
                subtitle_path = None

        progress("formatting", 5, "Formatting video")
        progress("formatting", None, "Encoding formatted video")
        result = formatter.format_for_platform(
            input_path,
            output_path,
            args.platform,
            crop_strategy=args.crop,
            pad_strategy=args.pad,
            pad_color=args.pad_color,
            maintain_quality=not args.no_quality,
            subtitle_path=subtitle_path,
            subtitle_style=caption_style
        )

        if result['success']:
            print(f"\n✅ Success!")
            print(f"   Output: {output_path}")
            print(f"   Size: {result['file_size_mb']} MB")

            if result['warnings']:
                print(f"\n⚠️  Warnings:")
                for warning in result['warnings']:
                    print(f"   • {warning}")

            _emit_result({
                "success": True,
                "clipCount": 1,
                "outputDir": str(output_dir),
                "warnings": result.get('warnings', [])
            })
            progress("formatting", 100, "Formatting complete")
        else:
            print(f"\n❌ Failed: {result.get('error', 'Unknown error')}")
            _emit_result({"success": False, "error": result.get('error', 'Unknown error')})
            return 1

    elif input_path.is_dir():
        # Directory of clips
        print(f"\nInput Directory: {input_path}")

        # Find all video files
        video_files = list(input_path.glob('*.mp4'))
        if not video_files:
            print(f"❌ Error: No MP4 files found in {input_path}")
            _emit_result({"success": False, "error": f"No MP4 files found in {input_path}"})
            return 1

        print(f"Found {len(video_files)} clip(s)")

        # Batch format
        clips = [{'path': str(f)} for f in video_files]

        def progress_callback(current, total, result):
            progress("formatting", current / total * 100, f"Formatted clip {current} of {total}")
            if result['success']:
                print(f"  [{current}/{total}] ✅ {Path(result['output_path']).name}")
            else:
                print(f"  [{current}/{total}] ❌ {result.get('error', 'Failed')}")

        print(f"\n⏳ Formatting {len(clips)} clips...")
        results = formatter.batch_format(
            clips,
            output_dir,
            args.platform,
            crop_strategy=args.crop,
            pad_strategy=args.pad,
            progress_callback=progress_callback,
            subtitle_style=caption_style
        )

        # Summary
        successful = sum(1 for r in results if r['success'])
        failed = len(results) - successful

        print(f"\n✅ Complete!")
        print(f"   Successful: {successful}")
        if failed > 0:
            print(f"   Failed: {failed}")
        print(f"   Output: {output_dir}")

        # Show warnings
        all_warnings = [w for r in results if r['success'] for w in r.get('warnings', [])]
        if all_warnings:
            print(f"\n⚠️  Warnings:")
            for warning in set(all_warnings):  # Deduplicate
                print(f"   • {warning}")

        _emit_result({
            "success": successful > 0,
            "clipCount": successful,
            "outputDir": str(output_dir),
            "warnings": list(set(all_warnings))
        })

    else:
        print(f"❌ Error: Invalid input path: {input_path}")
        _emit_result({"success": False, "error": f"Invalid input path: {input_path}"})
        return 1

    print("\n" + "=" * 70)
    return 0
