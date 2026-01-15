"""arena extract-audio - Extract audio from video"""

import subprocess
from pathlib import Path


def run_extract_audio(args):
    """Extract audio from video file"""

    video_path = Path(args.video)

    if not video_path.exists():
        print(f"❌ Error: Video file not found: {args.video}")
        return 1

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = video_path.parent / f"{video_path.stem}_audio.{args.format}"

    # Check if output exists
    if output_path.exists():
        response = input(f"⚠️  {output_path.name} already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Cancelled.")
            return 0

    print(f"\n🎵 Extracting audio from: {video_path.name}")
    print(f"   Format: {args.format.upper()}")
    print(f"   Bitrate: {args.bitrate}")
    if args.sample_rate:
        print(f"   Sample rate: {args.sample_rate} Hz")
    if args.mono:
        print(f"   Channels: Mono")
    print(f"   Output: {output_path.name}\n")

    try:
        # Build FFmpeg command
        command = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # No video
        ]

        # Audio codec based on format
        codec_map = {
            'mp3': 'libmp3lame',
            'wav': 'pcm_s16le',
            'aac': 'aac',
            'm4a': 'aac',
            'flac': 'flac'
        }

        codec = codec_map.get(args.format, 'libmp3lame')

        if args.format == 'wav':
            # WAV doesn't use bitrate, use PCM
            command.extend([
                "-acodec", codec,
            ])
        else:
            # Compressed formats use bitrate
            command.extend([
                "-acodec", codec,
                "-b:a", args.bitrate,
            ])

        # Sample rate
        if args.sample_rate:
            command.extend(["-ar", str(args.sample_rate)])

        # Mono conversion
        if args.mono:
            command.extend(["-ac", "1"])

        # Output
        command.extend([
            "-y",  # Overwrite
            str(output_path)
        ])

        # Run FFmpeg
        print("⏳ Extracting...")
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        # Get file size
        size_mb = output_path.stat().st_size / (1024 * 1024)

        print(f"\n✅ Audio extracted successfully!")
        print(f"   Output: {output_path}")
        print(f"   Size: {size_mb:.2f} MB\n")

        return 0

    except subprocess.CalledProcessError as e:
        print(f"\n❌ FFmpeg error: {e.stderr.decode('utf-8')}")
        return 1
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
