"""Video clip extraction and generation"""
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import json
import shutil
import re


class ClipGenerator:
    """Generates video clips from selected segments using FFmpeg"""

    def __init__(self, video_path: Path):
        """
        Initialize clip generator

        Args:
            video_path: Path to source video file
        """
        self.video_path = Path(video_path)
        self._video_info = None
        self._validate_video()
        self._check_ffmpeg()

    def _validate_video(self) -> None:
        """Validate that video file exists"""
        if not self.video_path.exists():
            raise FileNotFoundError(f"Video file not found: {self.video_path}")

    def _check_ffmpeg(self) -> None:
        """Check if FFmpeg is available"""
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "FFmpeg is not installed or not in PATH. "
                "Install from: https://ffmpeg.org/download.html"
            )

    def get_video_info(self) -> Dict:
        """
        Get video metadata using ffprobe

        Returns:
            Dict with video duration, resolution, codec, etc.
        """
        if self._video_info:
            return self._video_info

        try:
            # Use ffprobe to get video info
            command = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(self.video_path)
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            data = json.loads(result.stdout.decode('utf-8'))

            # Extract relevant info
            format_info = data.get('format', {})
            video_stream = next(
                (s for s in data.get('streams', []) if s['codec_type'] == 'video'),
                {}
            )
            audio_stream = next(
                (s for s in data.get('streams', []) if s['codec_type'] == 'audio'),
                {}
            )

            self._video_info = {
                'duration': float(format_info.get('duration', 0)),
                'size_bytes': int(format_info.get('size', 0)),
                'bitrate': int(format_info.get('bit_rate', 0)),
                'width': int(video_stream.get('width', 0)),
                'height': int(video_stream.get('height', 0)),
                'video_codec': video_stream.get('codec_name', 'unknown'),
                'audio_codec': audio_stream.get('codec_name', 'unknown'),
                'fps': self._parse_fps(video_stream.get('r_frame_rate', '0/1')),
                'has_audio': bool(audio_stream)
            }

            return self._video_info

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to get video info: {e.stderr.decode('utf-8')}")
        except Exception as e:
            raise RuntimeError(f"Failed to parse video info: {str(e)}")

    def _parse_fps(self, fps_string: str) -> float:
        """Parse FPS from ffprobe format (e.g., '30/1')"""
        try:
            num, denom = fps_string.split('/')
            return float(num) / float(denom)
        except:
            return 0.0

    def _sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """
        Sanitize text for use in filenames

        Args:
            text: Text to sanitize
            max_length: Maximum length of output

        Returns:
            Safe filename string
        """
        # Convert to lowercase
        text = text.lower()

        # Replace spaces and special chars with hyphens
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[-\s]+', '-', text)

        # Remove leading/trailing hyphens
        text = text.strip('-')

        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length].rsplit('-', 1)[0]  # Cut at word boundary

        return text or 'untitled'

    def _format_timestamp_short(self, seconds: float) -> str:
        """Format seconds as MMmSSs (e.g., 02m05s)"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}m{secs:02d}s"

    def generate_clip_filename(
        self,
        index: int,
        title: str = "",
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        include_timestamps: bool = True
    ) -> str:
        """
        Generate a professional, descriptive filename for a clip

        Args:
            index: Clip number (1-based)
            title: Clip title/description
            start_time: Start time in seconds
            end_time: End time in seconds
            include_timestamps: Include timestamp range in filename

        Returns:
            Filename string (without extension)

        Examples:
            why-startups-fail_001_02m05s-02m48s
            ai-revolution_003
            product-tips_005_15m30s-16m15s
        """
        parts = []

        # Title/description (first, most important)
        if title:
            sanitized_title = self._sanitize_filename(title, max_length=50)
            parts.append(sanitized_title)

        # Index number (always included)
        parts.append(f"{index:03d}")

        # Timestamp range
        if include_timestamps and start_time is not None and end_time is not None:
            start_str = self._format_timestamp_short(start_time)
            end_str = self._format_timestamp_short(end_time)
            parts.append(f"{start_str}-{end_str}")

        # Fallback if no title
        if not title:
            parts.insert(0, 'clip')

        return '_'.join(parts)

    def generate_clip(
        self,
        start_time: float,
        end_time: float,
        output_path: Path,
        padding: float = 0.0,
        codec: str = "libx264",
        crf: int = 23,
        preset: str = "medium",
        audio_codec: str = "aac"
    ) -> Dict:
        """
        Extract a clip from the video using FFmpeg

        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Where to save the clip
            padding: Seconds to add before/after for context
            codec: Video codec (default: libx264)
            crf: Constant Rate Factor for quality (default: 23, lower=better)
            preset: Encoding preset (ultrafast, fast, medium, slow, veryslow)
            audio_codec: Audio codec (default: aac)

        Returns:
            Dict with clip metadata
        """
        # Get video info to validate bounds
        video_info = self.get_video_info()
        duration = video_info['duration']

        # Apply padding and clamp to video bounds
        actual_start = max(0, start_time - padding)
        actual_end = min(duration, end_time + padding)
        actual_duration = actual_end - actual_start

        if actual_duration <= 0:
            raise ValueError(
                f"Invalid clip duration: start={actual_start}, end={actual_end}"
            )

        # Create output directory if needed
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        # Using -ss before -i for fast seeking
        command = [
            "ffmpeg",
            "-ss", str(actual_start),           # Seek to start (fast seek)
            "-i", str(self.video_path),         # Input file
            "-t", str(actual_duration),         # Duration
            "-c:v", codec,                      # Video codec
            "-crf", str(crf),                   # Quality
            "-preset", preset,                  # Encoding speed
            "-c:a", audio_codec,                # Audio codec
            "-b:a", "128k",                     # Audio bitrate
            "-movflags", "+faststart",          # Enable fast start for web
            "-y",                               # Overwrite output
            str(output_path)
        ]

        try:
            # Run FFmpeg
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            # Get output file size
            output_size = output_path.stat().st_size

            # Return metadata
            return {
                'output_path': str(output_path),
                'start_time': actual_start,
                'end_time': actual_end,
                'duration': actual_duration,
                'requested_start': start_time,
                'requested_end': end_time,
                'padding': padding,
                'size_bytes': output_size,
                'size_mb': round(output_size / (1024 * 1024), 2),
                'codec': codec,
                'crf': crf,
                'success': True
            }

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode('utf-8')
            raise RuntimeError(f"FFmpeg failed to generate clip: {error_msg}")

    def generate_clip_fast(
        self,
        start_time: float,
        end_time: float,
        output_path: Path,
        padding: float = 0.0
    ) -> Dict:
        """
        Fast clip extraction using stream copy (no re-encoding)

        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Where to save the clip
            padding: Seconds to add before/after

        Returns:
            Dict with clip metadata

        Note: This is much faster but less precise than re-encoding.
        Use for quick previews or when timing precision isn't critical.
        """
        video_info = self.get_video_info()
        duration = video_info['duration']

        actual_start = max(0, start_time - padding)
        actual_end = min(duration, end_time + padding)
        actual_duration = actual_end - actual_start

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "ffmpeg",
            "-ss", str(actual_start),
            "-i", str(self.video_path),
            "-t", str(actual_duration),
            "-c", "copy",                       # Copy streams (no re-encode)
            "-avoid_negative_ts", "1",          # Handle timing issues
            "-y",
            str(output_path)
        ]

        try:
            subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )

            output_size = output_path.stat().st_size

            return {
                'output_path': str(output_path),
                'start_time': actual_start,
                'end_time': actual_end,
                'duration': actual_duration,
                'size_bytes': output_size,
                'size_mb': round(output_size / (1024 * 1024), 2),
                'method': 'stream_copy',
                'success': True
            }

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"FFmpeg failed: {e.stderr.decode('utf-8')}")

    def generate_multiple_clips(
        self,
        segments: List[Dict],
        output_dir: Path,
        padding: float = 0.0,
        fast_mode: bool = False,
        progress_callback: Optional[callable] = None,
        include_timestamps: bool = True
    ) -> List[Dict]:
        """
        Generate multiple clips from a list of segments

        Args:
            segments: List of segment dicts with start_time, end_time, id
            output_dir: Directory to save clips
            padding: Seconds to add before/after each clip
            fast_mode: Use stream copy (faster but less precise)
            progress_callback: Optional callback(current, total, clip_info)
            include_timestamps: Include timestamp range in filename

        Returns:
            List of clip metadata dicts
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        total = len(segments)

        for i, segment in enumerate(segments, 1):
            # Generate professional clip filename
            clip_basename = self.generate_clip_filename(
                index=i,
                title=segment.get('title', ''),
                start_time=segment['start_time'],
                end_time=segment['end_time'],
                include_timestamps=include_timestamps
            )
            clip_filename = f"{clip_basename}.mp4"
            clip_path = output_dir / clip_filename

            try:
                # Generate clip
                if fast_mode:
                    clip_info = self.generate_clip_fast(
                        segment['start_time'],
                        segment['end_time'],
                        clip_path,
                        padding=padding
                    )
                else:
                    clip_info = self.generate_clip(
                        segment['start_time'],
                        segment['end_time'],
                        clip_path,
                        padding=padding
                    )

                # Add segment metadata
                clip_info.update({
                    'clip_id': clip_basename,
                    'clip_filename': clip_filename,
                    'title': segment.get('title', 'Untitled'),
                    'index': i,
                    'segment': segment
                })

                results.append(clip_info)

                # Call progress callback
                if progress_callback:
                    progress_callback(i, total, clip_info)

            except Exception as e:
                # Log error but continue with other clips
                error_info = {
                    'clip_id': clip_basename,
                    'clip_filename': clip_filename,
                    'error': str(e),
                    'success': False,
                    'index': i
                }
                results.append(error_info)

                if progress_callback:
                    progress_callback(i, total, error_info)

        return results

    def generate_thumbnail(
        self,
        timestamp: float,
        output_path: Path,
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> Path:
        """
        Generate a thumbnail image from video at specific timestamp

        Args:
            timestamp: Time in seconds
            output_path: Where to save thumbnail
            width: Optional width (maintains aspect ratio if only width given)
            height: Optional height (maintains aspect ratio if only height given)

        Returns:
            Path to generated thumbnail
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "ffmpeg",
            "-ss", str(timestamp),
            "-i", str(self.video_path),
            "-frames:v", "1",                   # Extract 1 frame
        ]

        # Add scaling if specified
        if width or height:
            if width and height:
                scale = f"scale={width}:{height}"
            elif width:
                scale = f"scale={width}:-1"     # Auto height
            else:
                scale = f"scale=-1:{height}"    # Auto width

            command.extend(["-vf", scale])

        command.extend([
            "-y",
            str(output_path)
        ])

        try:
            subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return output_path

        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Failed to generate thumbnail: {e.stderr.decode('utf-8')}"
            )

    def generate_clip_with_metadata(
        self,
        segment: Dict,
        output_dir: Path,
        index: int = 1,
        padding: float = 0.0,
        generate_thumb: bool = True,
        include_timestamps: bool = True
    ) -> Dict:
        """
        Generate a clip with full metadata and optional thumbnail

        Args:
            segment: Segment dict with timing and metadata
            output_dir: Output directory
            index: Clip index number
            padding: Padding in seconds
            generate_thumb: Whether to generate thumbnail
            include_timestamps: Include timestamp range in filename

        Returns:
            Dict with clip info, metadata, and paths
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate professional filename
        clip_basename = self.generate_clip_filename(
            index=index,
            title=segment.get('title', ''),
            start_time=segment['start_time'],
            end_time=segment['end_time'],
            include_timestamps=include_timestamps
        )

        # Generate clip
        clip_path = output_dir / f"{clip_basename}.mp4"
        clip_info = self.generate_clip(
            segment['start_time'],
            segment['end_time'],
            clip_path,
            padding=padding
        )

        # Generate thumbnail at midpoint
        if generate_thumb:
            try:
                midpoint = (segment['start_time'] + segment['end_time']) / 2
                thumb_path = output_dir / f"{clip_basename}_thumb.jpg"
                self.generate_thumbnail(midpoint, thumb_path, width=640)
                clip_info['thumbnail'] = str(thumb_path)
            except Exception as e:
                clip_info['thumbnail_error'] = str(e)

        # Add segment metadata
        clip_info.update({
            'clip_id': clip_basename,
            'clip_filename': f"{clip_basename}.mp4",
            'title': segment.get('title', 'Untitled'),
            'description': segment.get('reason', ''),
            'content_type': segment.get('content_type', 'general'),
            'scores': {
                'interest': segment.get('interest_score', 0),
                'hybrid': segment.get('hybrid_score', 0),
                'energy': segment.get('energy_score', 0)
            }
        })

        # Save metadata JSON
        metadata_path = output_dir / f"{clip_basename}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(clip_info, f, indent=2)

        clip_info['metadata_file'] = str(metadata_path)

        return clip_info
