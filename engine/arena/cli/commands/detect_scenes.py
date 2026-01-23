"""
Detect Scenes Command - Scene change detection
"""

import json
from pathlib import Path
from typing import Dict, List
import logging

from ...video.scene_detector import SceneDetector

logger = logging.getLogger(__name__)


def run_detect_scenes(args):
    """
    Detect scene changes in a video

    Args:
        args: Command line arguments

    Returns:
        Scene detection results
    """
    try:
        video_path = Path(args.video)
        output_path = Path(args.output)

        # Validate inputs
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize scene detector
        threshold = args.threshold if hasattr(args, 'threshold') and args.threshold else 0.4
        detector = SceneDetector(threshold=threshold)

        logger.info(f"Detecting scenes with threshold {threshold}")
        print(f"🎬 Detecting scene changes in {video_path.name}...")

        # Detect scenes
        min_duration = args.min_duration if hasattr(args, 'min_duration') and args.min_duration else 2.0
        scenes = detector.detect_scenes(video_path, min_scene_duration=min_duration)

        # Calculate statistics
        scene_count = len(scenes)
        durations = []
        for i in range(len(scenes)):
            if i < len(scenes) - 1:
                duration = scenes[i + 1]['time'] - scenes[i]['time']
                durations.append(duration)

        avg_duration = sum(durations) / len(durations) if durations else 0

        # Prepare output
        result = {
            'video_path': str(video_path),
            'threshold': threshold,
            'min_scene_duration': min_duration,
            'scene_count': scene_count,
            'avg_scene_duration': avg_duration,
            'scenes': scenes,
            'metadata': {
                'detection_method': 'ffmpeg_scene_filter',
                'version': '1.0'
            }
        }

        # Save to JSON
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)

        logger.info(f"Scene detection complete: {scene_count} scenes found")
        print(f"✓ Detected {scene_count} scene changes")
        print(f"✓ Average scene duration: {avg_duration:.1f}s")
        print(f"✓ Output saved to: {output_path}")

        # Generate detailed report if requested
        if hasattr(args, 'report') and args.report:
            report_path = output_path.parent / f"{output_path.stem}_report.txt"
            generate_scene_report(scenes, video_path, report_path, threshold, min_duration)
            result['report_path'] = str(report_path)
            print(f"✓ Detailed report: {report_path}")

        # Return result for Node CLI
        return result

    except Exception as e:
        logger.error(f"Scene detection failed: {str(e)}")
        raise


def generate_scene_report(
    scenes: List[Dict],
    video_path: Path,
    report_path: Path,
    threshold: float,
    min_duration: float
):
    """
    Generate a detailed human-readable scene report

    Args:
        scenes: List of detected scenes
        video_path: Path to video file
        report_path: Where to save report
        threshold: Detection threshold used
        min_duration: Minimum scene duration used
    """
    with open(report_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("ARENA SCENE DETECTION REPORT\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Video: {video_path.name}\n")
        f.write(f"Path: {video_path}\n")
        f.write(f"Threshold: {threshold}\n")
        f.write(f"Minimum Scene Duration: {min_duration}s\n")
        f.write(f"Total Scenes: {len(scenes)}\n\n")

        f.write("-" * 80 + "\n")
        f.write("SCENE BOUNDARIES\n")
        f.write("-" * 80 + "\n\n")

        for i, scene in enumerate(scenes, 1):
            time = scene['time']
            score = scene.get('score', 0)
            minutes = int(time // 60)
            seconds = time % 60

            # Calculate duration to next scene
            if i < len(scenes):
                next_time = scenes[i]['time']
                duration = next_time - time
                f.write(f"Scene {i:3d}: {minutes:02d}:{seconds:05.2f} - {int(duration):3d}s (score: {score:.3f})\n")
            else:
                f.write(f"Scene {i:3d}: {minutes:02d}:{seconds:05.2f} - End     (score: {score:.3f})\n")

        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF REPORT\n")
        f.write("=" * 80 + "\n")

    logger.info(f"Scene report generated: {report_path}")
