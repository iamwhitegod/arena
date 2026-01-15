"""Sentence boundary detection for professional video editing"""
from typing import List, Dict, Tuple, Optional
import re


class SentenceBoundaryDetector:
    """
    Detects natural sentence boundaries in transcripts for clean video cuts.

    A professional video editor would cut at:
    - Sentence endings (periods, exclamation marks, question marks)
    - Natural pauses between thoughts
    - Paragraph breaks or topic transitions
    - Speaker breaths or silence gaps
    """

    def __init__(self, min_pause_threshold: float = 0.5):
        """
        Initialize sentence boundary detector

        Args:
            min_pause_threshold: Minimum pause (in seconds) to consider a boundary
        """
        self.min_pause_threshold = min_pause_threshold

        # Sentence ending punctuation
        self.sentence_endings = {'.', '!', '?', '...'}

        # Strong transition words that often start new thoughts
        self.transition_starters = {
            'so', 'now', 'but', 'however', 'because', 'and',
            'first', 'second', 'next', 'finally', 'also',
            'then', 'therefore', 'meanwhile', 'additionally'
        }

    def find_sentence_boundaries(
        self,
        transcript_segments: List[Dict]
    ) -> List[Dict]:
        """
        Find all sentence boundaries in transcript with timestamps

        Args:
            transcript_segments: List of transcript segments with 'start', 'end', 'text'

        Returns:
            List of boundaries with timestamps and metadata
        """
        boundaries = []

        for i, segment in enumerate(transcript_segments):
            text = segment.get('text', '').strip()
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)

            # Check for sentence endings
            if self._has_sentence_ending(text):
                boundaries.append({
                    'time': end_time,
                    'type': 'sentence_end',
                    'text': text,
                    'confidence': 0.9,
                    'segment_index': i
                })

            # Check for pauses between segments
            if i < len(transcript_segments) - 1:
                next_segment = transcript_segments[i + 1]
                next_start = next_segment.get('start', 0)
                pause_duration = next_start - end_time

                if pause_duration >= self.min_pause_threshold:
                    # Natural pause between segments
                    boundaries.append({
                        'time': end_time,
                        'type': 'pause',
                        'pause_duration': pause_duration,
                        'confidence': 0.7,
                        'segment_index': i
                    })

                # Check for topic transitions (sentence ending + transition word)
                next_text = next_segment.get('text', '').strip()
                if self._has_sentence_ending(text) and self._starts_with_transition(next_text):
                    boundaries.append({
                        'time': next_start,
                        'type': 'topic_transition',
                        'text': text,
                        'next_text': next_text,
                        'confidence': 0.85,
                        'segment_index': i
                    })

        # Remove duplicates (same timestamp)
        boundaries = self._deduplicate_boundaries(boundaries)

        # Sort by time
        boundaries.sort(key=lambda x: x['time'])

        return boundaries

    def find_nearest_boundary_before(
        self,
        timestamp: float,
        boundaries: List[Dict],
        max_distance: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Find the nearest sentence boundary before a given timestamp

        Args:
            timestamp: Target timestamp
            boundaries: List of boundaries from find_sentence_boundaries()
            max_distance: Maximum allowed distance (seconds) to search back

        Returns:
            Nearest boundary before timestamp, or None if none found within max_distance
        """
        candidates = [b for b in boundaries if b['time'] <= timestamp]

        if not candidates:
            return None

        # Sort by distance to timestamp (closest first)
        candidates.sort(key=lambda b: timestamp - b['time'])

        nearest = candidates[0]

        # Check distance constraint
        if max_distance is not None:
            distance = timestamp - nearest['time']
            if distance > max_distance:
                return None

        return nearest

    def find_nearest_boundary_after(
        self,
        timestamp: float,
        boundaries: List[Dict],
        max_distance: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Find the nearest sentence boundary after a given timestamp

        Args:
            timestamp: Target timestamp
            boundaries: List of boundaries from find_sentence_boundaries()
            max_distance: Maximum allowed distance (seconds) to search forward

        Returns:
            Nearest boundary after timestamp, or None if none found within max_distance
        """
        candidates = [b for b in boundaries if b['time'] >= timestamp]

        if not candidates:
            return None

        # Sort by distance to timestamp (closest first)
        candidates.sort(key=lambda b: b['time'] - timestamp)

        nearest = candidates[0]

        # Check distance constraint
        if max_distance is not None:
            distance = nearest['time'] - timestamp
            if distance > max_distance:
                return None

        return nearest

    def align_clip_to_boundaries(
        self,
        start_time: float,
        end_time: float,
        boundaries: List[Dict],
        max_adjustment: float = 10.0,
        min_clip_duration: Optional[float] = None,
        max_clip_duration: Optional[float] = None
    ) -> Tuple[float, float, Dict]:
        """
        Align clip start/end to nearest sentence boundaries for clean cuts

        Args:
            start_time: Original clip start time
            end_time: Original clip end time
            boundaries: List of sentence boundaries
            max_adjustment: Maximum seconds to adjust start/end (default: 10s)
            min_clip_duration: Optional minimum clip duration constraint
            max_clip_duration: Optional maximum clip duration constraint

        Returns:
            Tuple of (adjusted_start, adjusted_end, metadata)
        """
        # Find nearest boundaries
        start_boundary = self.find_nearest_boundary_before(
            start_time, boundaries, max_distance=max_adjustment
        )
        end_boundary = self.find_nearest_boundary_after(
            end_time, boundaries, max_distance=max_adjustment
        )

        # Use boundaries if found, otherwise use original times
        adjusted_start = start_boundary['time'] if start_boundary else start_time
        adjusted_end = end_boundary['time'] if end_boundary else end_time

        # Ensure clip doesn't get inverted
        if adjusted_end <= adjusted_start:
            adjusted_end = end_time

        # Check if alignment dramatically reduced clip duration
        # If alignment shrinks clip by >80%, it's likely found bad boundaries - revert to original
        original_duration = end_time - start_time
        adjusted_duration = adjusted_end - adjusted_start

        if original_duration > 0 and adjusted_duration < (original_duration * 0.2):
            # Alignment destroyed the clip - revert to original timestamps
            adjusted_start = start_time
            adjusted_end = end_time

        # Apply duration constraints only if specified
        duration = adjusted_end - adjusted_start

        if min_clip_duration is not None and duration < min_clip_duration:
            # Clip too short - try to extend end
            extended_end = adjusted_start + min_clip_duration
            end_extension = self.find_nearest_boundary_after(
                extended_end, boundaries, max_distance=5.0
            )
            if end_extension:
                adjusted_end = end_extension['time']

        if max_clip_duration is not None and duration > max_clip_duration:
            # Clip too long - try to trim end
            trimmed_end = adjusted_start + max_clip_duration
            end_trim = self.find_nearest_boundary_before(
                trimmed_end, boundaries, max_distance=5.0
            )
            if end_trim:
                adjusted_end = end_trim['time']

        # Final sanity check: If alignment resulted in absurdly short clip, revert entirely
        # This catches cases where bad sentence boundaries created unusable clips
        final_duration = adjusted_end - adjusted_start
        if final_duration < 8.0:
            # Alignment failed to maintain viable clip - use original timestamps
            adjusted_start = start_time
            adjusted_end = end_time
            final_duration = original_duration

        # Metadata about adjustments
        metadata = {
            'original_start': start_time,
            'original_end': end_time,
            'original_duration': end_time - start_time,
            'adjusted_start': adjusted_start,
            'adjusted_end': adjusted_end,
            'adjusted_duration': adjusted_end - adjusted_start,
            'start_adjustment': adjusted_start - start_time,
            'end_adjustment': adjusted_end - end_time,
            'start_aligned': start_boundary is not None,
            'end_aligned': end_boundary is not None,
            'start_boundary_type': start_boundary['type'] if start_boundary else None,
            'end_boundary_type': end_boundary['type'] if end_boundary else None
        }

        return adjusted_start, adjusted_end, metadata

    def _has_sentence_ending(self, text: str) -> bool:
        """Check if text ends with sentence-ending punctuation"""
        text = text.strip()
        if not text:
            return False

        # Check for explicit sentence endings
        if any(text.endswith(ending) for ending in self.sentence_endings):
            return True

        # Check for quoted sentence endings
        if text.endswith('"') or text.endswith("'"):
            # Look at character before quote
            if len(text) > 1:
                return any(text[-2].endswith(ending.strip('.!?')) for ending in self.sentence_endings)

        return False

    def _starts_with_transition(self, text: str) -> bool:
        """Check if text starts with a transition word"""
        words = text.lower().strip().split()
        if not words:
            return False

        first_word = words[0].strip('.,!?;:')
        return first_word in self.transition_starters

    def _deduplicate_boundaries(self, boundaries: List[Dict]) -> List[Dict]:
        """Remove duplicate boundaries at same timestamp"""
        seen_times = set()
        unique = []

        for boundary in boundaries:
            time = boundary['time']
            if time not in seen_times:
                seen_times.add(time)
                unique.append(boundary)
            else:
                # Keep the one with higher confidence
                existing = next(b for b in unique if b['time'] == time)
                if boundary['confidence'] > existing['confidence']:
                    unique.remove(existing)
                    unique.append(boundary)

        return unique

    def get_transcript_segment_text(
        self,
        start_time: float,
        end_time: float,
        transcript_segments: List[Dict]
    ) -> str:
        """
        Extract transcript text for a time range

        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            transcript_segments: List of transcript segments

        Returns:
            Concatenated text for the time range
        """
        segments = []

        for segment in transcript_segments:
            seg_start = segment.get('start', 0)
            seg_end = segment.get('end', 0)

            # Check if segment overlaps with time range
            if seg_end > start_time and seg_start < end_time:
                segments.append(segment.get('text', '').strip())

        return ' '.join(segments)
