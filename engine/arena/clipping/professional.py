"""Professional clip alignment for A-list editing quality"""
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING
from arena.ai.sentence_detector import SentenceBoundaryDetector
from arena.video.scene_detector import SceneDetector

if TYPE_CHECKING:
    from arena.ai.analyzer import TranscriptAnalyzer


class ProfessionalClipAligner:
    """
    Aligns clips to sentence boundaries for professional editing quality.

    This ensures clips:
    - Start at sentence beginnings (not mid-sentence)
    - End at sentence completions (not mid-sentence)
    - Use natural pauses and transitions for cut points
    - Preserve complete thoughts and narrative flow
    """

    def __init__(
        self,
        sentence_detector: Optional[SentenceBoundaryDetector] = None,
        scene_detector: Optional[SceneDetector] = None,
        max_adjustment: float = 10.0,
        use_scene_detection: bool = False
    ):
        """
        Initialize professional aligner

        Args:
            sentence_detector: SentenceBoundaryDetector instance (creates default if None)
            scene_detector: SceneDetector instance for visual transition detection
            max_adjustment: Maximum seconds to adjust start/end for alignment (default: 10s)
            use_scene_detection: Enable scene detection for cut point optimization
        """
        self.detector = sentence_detector or SentenceBoundaryDetector()
        self.scene_detector = scene_detector or SceneDetector(threshold=0.4)
        self.max_adjustment = max_adjustment
        self.use_scene_detection = use_scene_detection

    def align_clips(
        self,
        clips: List[Dict],
        transcript_segments: List[Dict],
        min_duration: Optional[float] = None,
        max_duration: Optional[float] = None,
        analyzer: Optional['TranscriptAnalyzer'] = None,
        video_path: Optional[Path] = None
    ) -> List[Dict]:
        """
        Align all clips to sentence boundaries and optionally scene changes

        Args:
            clips: List of clips from analysis with start_time, end_time
            transcript_segments: List of transcript segments with timestamps
            min_duration: Optional minimum duration constraint
            max_duration: Optional maximum duration constraint
            analyzer: Optional TranscriptAnalyzer to regenerate titles after alignment
            video_path: Optional video path for scene detection

        Returns:
            List of professionally aligned clips with metadata
        """
        # Find all sentence boundaries in transcript
        boundaries = self.detector.find_sentence_boundaries(transcript_segments)

        if not boundaries:
            print("⚠️  Warning: No sentence boundaries found, using original timestamps")
            return clips

        print(f"🔍 Found {len(boundaries)} sentence boundaries")

        # Optionally detect scene changes
        scene_boundaries = []
        if self.use_scene_detection and video_path:
            try:
                print(f"🎬 Detecting scene changes...")
                scenes = self.scene_detector.detect_scenes(video_path, min_scene_duration=2.0)
                scene_boundaries = [{'time': s['time'], 'type': 'scene_change'} for s in scenes]
                print(f"   Found {len(scene_boundaries)} scene changes")

                # Mark boundaries that align with both sentences AND scenes
                for boundary in boundaries:
                    for scene in scene_boundaries:
                        if abs(boundary['time'] - scene['time']) < 1.0:  # Within 1 second
                            boundary['double_boundary'] = True
                            break

            except Exception as e:
                print(f"⚠️  Scene detection failed: {e}")
                print(f"   Continuing with sentence boundaries only")

        aligned_clips = []
        adjustments_made = 0

        for i, clip in enumerate(clips, 1):
            # Align this clip to sentence boundaries
            aligned_start, aligned_end, metadata = self.detector.align_clip_to_boundaries(
                start_time=clip['start_time'],
                end_time=clip['end_time'],
                boundaries=boundaries,
                max_adjustment=self.max_adjustment,
                min_clip_duration=min_duration,
                max_clip_duration=max_duration
            )

            # Create aligned clip
            aligned_clip = clip.copy()
            aligned_clip.update({
                'original_start': clip['start_time'],
                'original_end': clip['end_time'],
                'original_duration': clip['end_time'] - clip['start_time'],
                'start_time': aligned_start,
                'end_time': aligned_end,
                'duration': aligned_end - aligned_start,
                'alignment': metadata,
                'professionally_aligned': metadata['start_aligned'] or metadata['end_aligned']
            })

            # Regenerate title based on aligned content if analyzer provided
            if analyzer and (metadata['start_aligned'] or metadata['end_aligned']):
                try:
                    # Extract transcript text for the aligned time range
                    aligned_text = analyzer.extract_transcript_text(
                        transcript_segments,
                        aligned_start,
                        aligned_end
                    )

                    # Generate new title based on actual aligned content
                    if aligned_text:
                        new_title = analyzer.generate_clip_title(aligned_text)
                        aligned_clip['title'] = new_title
                        aligned_clip['original_title'] = clip.get('title', '')
                except Exception as e:
                    # If title regeneration fails, keep original
                    print(f"   ⚠️  Failed to regenerate title for clip {i}: {e}")

            aligned_clips.append(aligned_clip)

            # Track adjustments
            if metadata['start_aligned'] or metadata['end_aligned']:
                adjustments_made += 1

        print(f"   ✓ Aligned {adjustments_made}/{len(clips)} clips to sentence boundaries\n")

        return aligned_clips

    def generate_alignment_report(
        self,
        aligned_clips: List[Dict],
        top_n: int = 10
    ) -> str:
        """
        Generate a human-readable alignment report

        Args:
            aligned_clips: List of aligned clips
            top_n: Number of clips to show in report

        Returns:
            Formatted alignment report string
        """
        report = []
        report.append("=" * 70)
        report.append("📊 Professional Editing Report")
        report.append("=" * 70)
        report.append("")

        for i, clip in enumerate(aligned_clips[:top_n], 1):
            title = clip.get('title', 'Untitled')[:60]
            alignment = clip.get('alignment', {})

            report.append(f"Clip {i}: {title}")
            report.append(f"  Original:  {self._format_time(clip['original_start'])} → "
                         f"{self._format_time(clip['original_end'])} "
                         f"({clip['original_duration']:.1f}s)")
            report.append(f"  Aligned:   {self._format_time(clip['start_time'])} → "
                         f"{self._format_time(clip['end_time'])} "
                         f"({clip['duration']:.1f}s)")

            # Show adjustments
            start_adj = alignment.get('start_adjustment', 0)
            end_adj = alignment.get('end_adjustment', 0)

            if start_adj != 0 or end_adj != 0:
                report.append(f"  Adjustment: Start {start_adj:+.1f}s, End {end_adj:+.1f}s")
            else:
                report.append(f"  Adjustment: None (already aligned)")

            # Show boundary types
            start_type = alignment.get('start_boundary_type')
            end_type = alignment.get('end_boundary_type')

            if start_type or end_type:
                boundaries = []
                if start_type:
                    boundaries.append(f"start={start_type}")
                if end_type:
                    boundaries.append(f"end={end_type}")
                report.append(f"  Boundaries: {', '.join(boundaries)}")

            # Quality indicator
            if clip.get('professionally_aligned'):
                report.append(f"  Quality:    ✓ Sentence aligned")
            else:
                report.append(f"  Quality:    ⚠ No boundaries nearby")

            report.append("")

        # Summary statistics
        total = len(aligned_clips)
        aligned = sum(1 for c in aligned_clips if c.get('professionally_aligned'))
        avg_start_adj = sum(abs(c.get('alignment', {}).get('start_adjustment', 0))
                           for c in aligned_clips) / total if total > 0 else 0
        avg_end_adj = sum(abs(c.get('alignment', {}).get('end_adjustment', 0))
                         for c in aligned_clips) / total if total > 0 else 0

        report.append("=" * 70)
        report.append("Summary:")
        report.append(f"  Total clips:          {total}")
        report.append(f"  Professionally aligned: {aligned} ({aligned/total*100:.0f}%)")
        report.append(f"  Avg start adjustment: {avg_start_adj:.2f}s")
        report.append(f"  Avg end adjustment:   {avg_end_adj:.2f}s")
        report.append("=" * 70)

        return "\n".join(report)

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def get_alignment_stats(self, aligned_clips: List[Dict]) -> Dict:
        """
        Get statistical summary of alignment results

        Args:
            aligned_clips: List of aligned clips

        Returns:
            Dict with alignment statistics
        """
        if not aligned_clips:
            return {}

        total = len(aligned_clips)
        aligned = sum(1 for c in aligned_clips if c.get('professionally_aligned'))

        start_adjustments = [c.get('alignment', {}).get('start_adjustment', 0)
                            for c in aligned_clips]
        end_adjustments = [c.get('alignment', {}).get('end_adjustment', 0)
                          for c in aligned_clips]

        return {
            'total_clips': total,
            'professionally_aligned': aligned,
            'alignment_rate': aligned / total if total > 0 else 0,
            'avg_start_adjustment': sum(abs(a) for a in start_adjustments) / total if total > 0 else 0,
            'avg_end_adjustment': sum(abs(a) for a in end_adjustments) / total if total > 0 else 0,
            'max_start_adjustment': max(abs(a) for a in start_adjustments) if start_adjustments else 0,
            'max_end_adjustment': max(abs(a) for a in end_adjustments) if end_adjustments else 0,
            'zero_adjustment_count': sum(1 for c in aligned_clips
                                        if c.get('alignment', {}).get('start_adjustment', 0) == 0
                                        and c.get('alignment', {}).get('end_adjustment', 0) == 0)
        }
