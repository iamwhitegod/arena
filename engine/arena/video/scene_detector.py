"""Video scene detection for identifying visual transitions"""
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Optional


class SceneDetector:
    """
    Detects scene changes in video using FFmpeg's scene detection filter.

    Scene changes are identified by measuring pixel differences between frames.
    These scene boundaries can be used as additional cut points for professional editing.
    """

    def __init__(self, threshold: float = 0.4):
        """
        Initialize scene detector

        Args:
            threshold: Scene detection sensitivity (0.0-1.0)
                      Lower = more sensitive (more scenes detected)
                      Higher = less sensitive (only major changes)
                      Default: 0.4 (balanced)
        """
        self.threshold = threshold

    def detect_scenes(
        self,
        video_path: Path,
        min_scene_duration: float = 2.0
    ) -> List[Dict]:
        """
        Detect scene changes in video

        Args:
            video_path: Path to video file
            min_scene_duration: Minimum duration between scenes (seconds)
                               Filters out very quick cuts

        Returns:
            List of scene boundaries with timestamps
            Example: [
                {'time': 10.5, 'score': 0.87, 'type': 'scene_change'},
                {'time': 45.2, 'score': 0.92, 'type': 'scene_change'},
            ]
        """
        video_path = Path(video_path)

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        try:
            # Use FFmpeg scene detection filter
            command = [
                "ffmpeg",
                "-i", str(video_path),
                "-filter:v", f"select='gt(scene,{self.threshold})',showinfo",
                "-f", "null",
                "-"
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Parse scene timestamps from ffmpeg output
            scenes = self._parse_scene_output(result.stderr)

            # Filter scenes by minimum duration
            if min_scene_duration > 0:
                scenes = self._filter_by_min_duration(scenes, min_scene_duration)

            return scenes

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Scene detection failed: {e.stderr}")
        except Exception as e:
            raise RuntimeError(f"Scene detection error: {str(e)}")

    def _parse_scene_output(self, ffmpeg_output: str) -> List[Dict]:
        """
        Parse scene timestamps from FFmpeg showinfo output

        Args:
            ffmpeg_output: FFmpeg stderr output containing showinfo data

        Returns:
            List of scene dictionaries with timestamps
        """
        scenes = []

        for line in ffmpeg_output.split('\n'):
            # Look for showinfo lines with pts_time
            if 'showinfo' in line and 'pts_time:' in line:
                try:
                    # Extract timestamp
                    # Example line: [Parsed_showinfo_1 @ 0x...] n:42 pts:1260 pts_time:10.5 ...
                    for part in line.split():
                        if part.startswith('pts_time:'):
                            time_str = part.split(':')[1]
                            timestamp = float(time_str)

                            scenes.append({
                                'time': timestamp,
                                'score': self.threshold,  # Approximate score
                                'type': 'scene_change'
                            })
                            break
                except (ValueError, IndexError):
                    continue

        return sorted(scenes, key=lambda x: x['time'])

    def _filter_by_min_duration(
        self,
        scenes: List[Dict],
        min_duration: float
    ) -> List[Dict]:
        """
        Filter out scenes that are too close together

        Args:
            scenes: List of scene dictionaries
            min_duration: Minimum time between scenes

        Returns:
            Filtered list of scenes
        """
        if not scenes:
            return []

        filtered = [scenes[0]]  # Always keep first scene

        for scene in scenes[1:]:
            last_time = filtered[-1]['time']
            if scene['time'] - last_time >= min_duration:
                filtered.append(scene)

        return filtered

    def get_scene_boundaries(
        self,
        video_path: Path,
        start_time: float,
        end_time: float,
        min_scene_duration: float = 2.0
    ) -> List[float]:
        """
        Get scene boundaries within a specific time range

        Args:
            video_path: Path to video file
            start_time: Start of time range (seconds)
            end_time: End of time range (seconds)
            min_scene_duration: Minimum duration between scenes

        Returns:
            List of scene boundary timestamps within the range
        """
        all_scenes = self.detect_scenes(video_path, min_scene_duration)

        # Filter to time range
        boundaries = [
            scene['time']
            for scene in all_scenes
            if start_time <= scene['time'] <= end_time
        ]

        return boundaries

    def align_to_nearest_scene(
        self,
        video_path: Path,
        timestamp: float,
        max_adjustment: float = 5.0,
        min_scene_duration: float = 2.0
    ) -> Optional[float]:
        """
        Find nearest scene boundary to a given timestamp

        Args:
            video_path: Path to video file
            timestamp: Target timestamp (seconds)
            max_adjustment: Maximum distance to search (seconds)
            min_scene_duration: Minimum duration between scenes

        Returns:
            Nearest scene boundary timestamp, or None if none found within range
        """
        all_scenes = self.detect_scenes(video_path, min_scene_duration)

        if not all_scenes:
            return None

        # Find scenes within adjustment range
        candidates = [
            scene['time']
            for scene in all_scenes
            if abs(scene['time'] - timestamp) <= max_adjustment
        ]

        if not candidates:
            return None

        # Return closest scene
        return min(candidates, key=lambda t: abs(t - timestamp))

    def generate_scene_report(
        self,
        video_path: Path,
        min_scene_duration: float = 2.0
    ) -> str:
        """
        Generate a human-readable scene detection report

        Args:
            video_path: Path to video file
            min_scene_duration: Minimum duration between scenes

        Returns:
            Formatted report string
        """
        scenes = self.detect_scenes(video_path, min_scene_duration)

        report = []
        report.append("=" * 70)
        report.append("🎬 Scene Detection Report")
        report.append("=" * 70)
        report.append(f"Video: {video_path.name}")
        report.append(f"Threshold: {self.threshold}")
        report.append(f"Min scene duration: {min_scene_duration}s")
        report.append(f"Total scenes detected: {len(scenes)}")
        report.append("")

        if scenes:
            report.append("Scene Changes:")
            for i, scene in enumerate(scenes, 1):
                timestamp = self._format_timestamp(scene['time'])
                report.append(f"  {i:3d}. {timestamp}")

        report.append("=" * 70)

        return "\n".join(report)

    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
