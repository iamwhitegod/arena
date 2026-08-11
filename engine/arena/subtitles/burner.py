"""Subtitle generation and burning into videos"""
import subprocess
from pathlib import Path
from typing import List, Dict, Optional


class SubtitleBurner:
    """Generates and burns stylized subtitles into videos"""

    def __init__(
        self,
        font: str = "Arial",
        font_size: int = 24,
        color: str = "white",
        bg_color: str = "black",
        position: str = "bottom"
    ):
        self.font = font
        self.font_size = font_size
        self.color = color
        self.bg_color = bg_color
        self.position = position

    def generate_srt(
        self,
        segments: List[Dict],
        output_path: Path,
        clip_start: float = 0.0,
        clip_end: Optional[float] = None
    ) -> Path:
        """
        Generate SRT subtitle file from transcript segments.

        Args:
            segments: List of segment dicts with 'start', 'end', 'text' keys
            output_path: Where to save the SRT file
            clip_start: Start time of the clip in the original video (for offset)
            clip_end: End time of the clip in the original video

        Returns:
            Path to generated SRT file
        """
        output_path = Path(output_path)
        counter = 1

        with open(output_path, 'w', encoding='utf-8') as f:
            for segment in segments:
                seg_start = segment.get('start', 0)
                seg_end = segment.get('end', 0)
                text = segment.get('text', '').strip()

                if not text:
                    continue

                # Skip segments outside clip range
                if clip_end is not None and seg_start >= clip_end:
                    continue
                if seg_end <= clip_start:
                    continue

                # Offset timestamps to be relative to clip start
                rel_start = max(0, seg_start - clip_start)
                rel_end = seg_end - clip_start
                if clip_end is not None:
                    rel_end = min(rel_end, clip_end - clip_start)

                f.write(f"{counter}\n")
                f.write(f"{self._format_timestamp(rel_start)} --> {self._format_timestamp(rel_end)}\n")
                f.write(f"{text}\n\n")
                counter += 1

        return output_path

    def burn_subtitles(
        self,
        video_path: Path,
        subtitle_path: Path,
        output_path: Path
    ) -> Path:
        """
        Burn subtitles into video using FFmpeg.

        Args:
            video_path: Input video file
            subtitle_path: SRT subtitle file
            output_path: Output video with burned subtitles

        Returns:
            Path to output video
        """
        subtitle_filter = self.get_subtitle_filter(subtitle_path)

        command = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', subtitle_filter,
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-c:a', 'copy',
            '-y',
            str(output_path)
        ]

        subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        return output_path

    def get_subtitle_filter(self, subtitle_path: Path) -> str:
        """Return FFmpeg subtitles filter string for embedding in a filter chain."""
        # Escape path for FFmpeg (colons and backslashes)
        escaped_path = str(subtitle_path).replace('\\', '/').replace(':', '\\:')
        alignment = {'bottom': 2, 'top': 8, 'middle': 5}.get(self.position, 2)

        return (
            f"subtitles='{escaped_path}'"
            f":force_style='FontName={self.font},"
            f"FontSize={self.font_size},"
            f"PrimaryColour=&H{self._color_to_bgr_hex(self.color)}&,"
            f"BackColour=&H80{self._color_to_bgr_hex(self.bg_color)}&,"
            f"Alignment={alignment}'"
        )

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to SRT timestamp format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    def _color_to_bgr_hex(self, color: str) -> str:
        """Convert color name to BGR hex (FFmpeg ASS uses &HBBGGRR& order)"""
        colors = {
            "white": "FFFFFF",
            "black": "000000",
            "yellow": "00FFFF",
            "red": "0000FF",
            "green": "00FF00",
            "blue": "FF0000",
            "cyan": "FFFF00",
            "magenta": "FF00FF",
        }
        return colors.get(color.lower(), "FFFFFF")
