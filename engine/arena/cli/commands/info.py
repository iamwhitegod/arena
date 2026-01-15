"""arena info - Show video information"""

import json
from pathlib import Path
from arena.clipping.generator import ClipGenerator


def run_info(args):
    """Show video information"""

    video_path = Path(args.video)

    if not video_path.exists():
        print(f"❌ Error: Video file not found: {args.video}")
        return 1

    try:
        generator = ClipGenerator(video_path)
        info = generator.get_video_info()

        if args.json:
            # Output as JSON
            print(json.dumps(info, indent=2))
        else:
            # Pretty print
            print(f"\n📹 Video Information: {video_path.name}\n")
            print(f"Duration:    {info['duration']:.2f}s ({info['duration']/60:.1f}min)")
            print(f"Size:        {info['size_bytes']/(1024*1024):.1f} MB")
            print(f"Bitrate:     {info['bitrate']/1000:.0f} kbps")
            print(f"Resolution:  {info['width']}x{info['height']}")
            print(f"FPS:         {info['fps']:.2f}")
            print(f"Video Codec: {info['video_codec']}")
            print(f"Audio Codec: {info['audio_codec']}")
            print(f"Has Audio:   {'Yes' if info['has_audio'] else 'No'}\n")

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1
