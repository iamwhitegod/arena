"""Export functionality for clips, metadata, and thumbnails"""
from pathlib import Path
from typing import List, Dict
import json


class Exporter:
    """Handles exporting clips, metadata, and thumbnails"""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.clips_dir = self.output_dir / "clips"

    def export_metadata(
        self,
        source_video: Path,
        clips: List[Dict],
        output_path: Path = None
    ) -> Path:
        """
        Export metadata JSON for all clips

        Args:
            source_video: Original video file path
            clips: List of clip dictionaries with metadata
            output_path: Optional custom output path

        Returns:
            Path to metadata file
        """
        if output_path is None:
            output_path = self.output_dir / "metadata.json"

        metadata = {
            "source_video": str(source_video),
            "duration": 0,  # TODO: Get from video
            "clips": clips
        }

        with open(output_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        return output_path

    def export_transcript(
        self,
        transcript: Dict,
        output_path: Path = None
    ) -> Path:
        """
        Export full transcript as JSON

        Args:
            transcript: Transcript dictionary with words/segments
            output_path: Optional custom output path

        Returns:
            Path to transcript file
        """
        if output_path is None:
            output_path = self.output_dir / "transcript.json"

        with open(output_path, 'w') as f:
            json.dump(transcript, f, indent=2)

        return output_path

    def generate_thumbnail(
        self,
        video_path: Path,
        timestamp: float,
        output_path: Path
    ) -> Path:
        """
        Generate thumbnail from video at specific timestamp

        Args:
            video_path: Video file to extract from
            timestamp: Time in seconds for thumbnail
            output_path: Where to save thumbnail

        Returns:
            Path to generated thumbnail
        """
        # TODO: Implement with opencv or moviepy
        # from moviepy.editor import VideoFileClip
        # clip = VideoFileClip(str(video_path))
        # frame = clip.get_frame(timestamp)
        #
        # from PIL import Image
        # img = Image.fromarray(frame)
        # img.save(str(output_path))

        return output_path

    def create_summary_report(self, clips: List[Dict]) -> str:
        """
        Create a text summary of generated clips

        Args:
            clips: List of clip dictionaries

        Returns:
            Formatted summary text
        """
        lines = [
            "=" * 60,
            "ARENA PROCESSING SUMMARY",
            "=" * 60,
            f"\nTotal Clips Generated: {len(clips)}\n"
        ]

        for i, clip in enumerate(clips, 1):
            lines.append(f"{i}. {clip.get('title', 'Untitled')}")
            lines.append(f"   Duration: {clip.get('duration', 0):.1f}s")
            lines.append(f"   Score: {clip.get('scores', {}).get('combined', 0):.2f}")
            lines.append(f"   Files: {clip.get('files', {}).get('subtitled', 'N/A')}")
            lines.append("")

        return "\n".join(lines)
