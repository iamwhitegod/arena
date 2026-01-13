"""Scoring algorithm for ranking and filtering video segments"""
from typing import List, Dict, Optional


class SegmentScorer:
    """Scores and ranks video segments based on multiple signals"""

    def __init__(
        self,
        ai_weight: float = 0.4,
        audio_weight: float = 0.3,
        visual_weight: float = 0.3
    ):
        """
        Initialize scorer with signal weights

        Args:
            ai_weight: Weight for AI analysis score (0-1)
            audio_weight: Weight for audio energy score (0-1)
            visual_weight: Weight for visual change score (0-1)
        """
        # Normalize weights to sum to 1
        total = ai_weight + audio_weight + visual_weight
        self.ai_weight = ai_weight / total
        self.audio_weight = audio_weight / total
        self.visual_weight = visual_weight / total

    def score_segments(
        self,
        ai_segments: List[Dict],
        audio_segments: Optional[List[Dict]] = None,
        visual_segments: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """
        Score and rank segments using multiple signals

        Args:
            ai_segments: Segments identified by AI analysis
            audio_segments: Segments with high audio energy (optional)
            visual_segments: Segments with scene changes (optional)

        Returns:
            Scored and ranked segments
        """
        scored_segments = []

        for segment in ai_segments:
            # Start with AI score
            ai_score = segment.get("interest_score", 0.5)

            # Find overlapping audio segments
            audio_score = self._get_audio_score(
                segment, audio_segments or []
            )

            # Find overlapping visual segments
            visual_score = self._get_visual_score(
                segment, visual_segments or []
            )

            # Calculate combined score
            combined_score = (
                self.ai_weight * ai_score +
                self.audio_weight * audio_score +
                self.visual_weight * visual_score
            )

            # Add scores to segment
            segment["scores"] = {
                "ai_interest": round(ai_score, 2),
                "audio_energy": round(audio_score, 2),
                "visual_change": round(visual_score, 2),
                "combined": round(combined_score, 2)
            }

            scored_segments.append(segment)

        # Sort by combined score (highest first)
        scored_segments.sort(
            key=lambda x: x["scores"]["combined"],
            reverse=True
        )

        return scored_segments

    def filter_overlapping(
        self,
        segments: List[Dict],
        overlap_threshold: float = 0.3
    ) -> List[Dict]:
        """
        Remove overlapping segments, keeping highest scored ones

        Args:
            segments: List of segments (must be sorted by score)
            overlap_threshold: Max allowed overlap ratio (0-1)

        Returns:
            Filtered list with no significant overlaps
        """
        if not segments:
            return []

        filtered = [segments[0]]  # Keep highest scored

        for segment in segments[1:]:
            # Check if it overlaps with any already selected segment
            has_overlap = False

            for selected in filtered:
                overlap_ratio = self._calculate_overlap(segment, selected)
                if overlap_ratio > overlap_threshold:
                    has_overlap = True
                    break

            if not has_overlap:
                filtered.append(segment)

        return filtered

    def select_top_clips(
        self,
        segments: List[Dict],
        target_count: int,
        min_duration: int = 30,
        max_duration: int = 90
    ) -> List[Dict]:
        """
        Select top N clips meeting duration requirements

        Args:
            segments: Scored segments
            target_count: Number of clips to select
            min_duration: Minimum duration in seconds
            max_duration: Maximum duration in seconds

        Returns:
            Top N clips
        """
        # Filter by duration
        valid_segments = [
            s for s in segments
            if min_duration <= s.get("duration", 0) <= max_duration
        ]

        # Remove overlaps
        non_overlapping = self.filter_overlapping(valid_segments)

        # Return top N
        return non_overlapping[:target_count]

    def _get_audio_score(
        self,
        segment: Dict,
        audio_segments: List[Dict]
    ) -> float:
        """Calculate audio energy score for segment"""
        if not audio_segments:
            return 0.5  # Neutral score if no audio data

        start = segment["start_time"]
        end = segment["end_time"]
        overlapping_scores = []

        for audio_seg in audio_segments:
            # Check for overlap
            audio_start = audio_seg.get("start", 0)
            audio_end = audio_seg.get("end", 0)

            if self._has_overlap(start, end, audio_start, audio_end):
                overlapping_scores.append(
                    audio_seg.get("energy_score", 0.5)
                )

        # Return average of overlapping audio scores
        if overlapping_scores:
            return sum(overlapping_scores) / len(overlapping_scores)

        return 0.5

    def _get_visual_score(
        self,
        segment: Dict,
        visual_segments: List[Dict]
    ) -> float:
        """Calculate visual change score for segment"""
        if not visual_segments:
            return 0.5  # Neutral score if no visual data

        start = segment["start_time"]
        end = segment["end_time"]
        scene_changes = 0

        for visual_seg in visual_segments:
            # Check if scene change occurs within segment
            change_time = visual_seg.get("time", 0)
            if start <= change_time <= end:
                scene_changes += 1

        # Normalize: more scene changes = higher score (but cap it)
        # 0 changes = 0.3, 1-2 changes = 0.6, 3+ changes = 0.9
        if scene_changes == 0:
            return 0.3
        elif scene_changes <= 2:
            return 0.6
        else:
            return 0.9

    def _has_overlap(
        self,
        start1: float,
        end1: float,
        start2: float,
        end2: float
    ) -> bool:
        """Check if two time ranges overlap"""
        return start1 < end2 and start2 < end1

    def _calculate_overlap(
        self,
        segment1: Dict,
        segment2: Dict
    ) -> float:
        """
        Calculate overlap ratio between two segments

        Returns:
            Overlap ratio (0-1), where 1 means complete overlap
        """
        start1 = segment1["start_time"]
        end1 = segment1["end_time"]
        start2 = segment2["start_time"]
        end2 = segment2["end_time"]

        # Calculate overlap
        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_start >= overlap_end:
            return 0.0  # No overlap

        overlap_duration = overlap_end - overlap_start

        # Calculate ratio relative to shorter segment
        duration1 = end1 - start1
        duration2 = end2 - start2
        min_duration = min(duration1, duration2)

        return overlap_duration / min_duration if min_duration > 0 else 0.0
