"""Hybrid analysis combining AI content analysis with audio energy detection"""
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json


class HybridAnalyzer:
    """
    Combines AI transcript analysis with audio energy detection
    to identify clips with both great content AND enthusiastic delivery
    """

    def __init__(
        self,
        ai_analyzer,
        energy_analyzer,
        energy_weight: float = 0.3
    ):
        """
        Initialize hybrid analyzer

        Args:
            ai_analyzer: TranscriptAnalyzer instance
            energy_analyzer: AudioEnergyAnalyzer instance
            energy_weight: Weight for energy boost (0-1, default 0.3 = 30% boost)
        """
        self.ai_analyzer = ai_analyzer
        self.energy_analyzer = energy_analyzer
        self.energy_weight = energy_weight

    def analyze_video(
        self,
        video_path: Path,
        transcript_data: Dict,
        target_clips: int = 10,
        min_duration: int = 30,
        max_duration: int = 90
    ) -> Dict:
        """
        Perform hybrid analysis combining AI content and audio energy

        Args:
            video_path: Path to video file
            transcript_data: Transcript dict with 'text' and 'segments'
            target_clips: Number of clips to identify
            min_duration: Minimum clip duration in seconds
            max_duration: Maximum clip duration in seconds

        Returns:
            Dict with AI clips, energy segments, hybrid scored clips, and stats
        """
        print("🧠 Analyzing transcript content with AI...")
        ai_clips = self.ai_analyzer.analyze_transcript(
            transcript_data,
            target_clips=target_clips * 2,  # Get more clips for better selection
            min_duration=min_duration,
            max_duration=max_duration
        )

        print(f"   ✓ Found {len(ai_clips)} interesting content segments\n")

        print("⚡ Analyzing audio energy...")
        energy_segments = self.energy_analyzer.analyze(
            min_duration=float(min_duration * 0.3),  # Allow shorter energy segments
            max_duration=float(max_duration),
            energy_threshold=0.5,
            top_n=20  # Get many energy segments for overlap detection
        )

        print(f"   ✓ Found {len(energy_segments)} high-energy segments\n")

        print("🎯 Computing hybrid scores...")
        hybrid_clips = self._compute_hybrid_scores(
            ai_clips,
            energy_segments,
            transcript_data
        )

        # Sort by hybrid score and take top N
        hybrid_clips.sort(key=lambda x: x['hybrid_score'], reverse=True)
        top_clips = hybrid_clips[:target_clips]

        print(f"   ✓ Selected top {len(top_clips)} clips by hybrid score\n")

        # Generate statistics
        stats = self._generate_stats(ai_clips, energy_segments, hybrid_clips)

        return {
            'clips': top_clips,
            'ai_clips': ai_clips,
            'energy_segments': energy_segments,
            'stats': stats,
            'config': {
                'target_clips': target_clips,
                'min_duration': min_duration,
                'max_duration': max_duration,
                'energy_weight': self.energy_weight
            }
        }

    def _compute_hybrid_scores(
        self,
        ai_clips: List[Dict],
        energy_segments: List[Dict],
        transcript_data: Dict
    ) -> List[Dict]:
        """
        Compute hybrid scores for AI clips based on energy overlap

        Args:
            ai_clips: List of AI-identified clips
            energy_segments: List of high-energy audio segments
            transcript_data: Original transcript data

        Returns:
            List of clips with hybrid scores
        """
        hybrid_clips = []

        for clip in ai_clips:
            # Find overlapping energy segments
            overlaps = self._find_overlapping_segments(
                clip['start_time'],
                clip['end_time'],
                energy_segments
            )

            # Calculate energy boost
            if overlaps:
                # Use the highest energy score from overlapping segments
                max_energy = max(seg['energy_score'] for seg in overlaps)
                avg_energy = sum(seg['energy_score'] for seg in overlaps) / len(overlaps)
                overlap_ratio = sum(seg['overlap_ratio'] for seg in overlaps)

                # Energy boost is weighted combination of:
                # - Peak energy in overlapping segments (50%)
                # - Average energy (30%)
                # - Overlap coverage (20%)
                energy_boost = (
                    0.5 * max_energy +
                    0.3 * avg_energy +
                    0.2 * min(overlap_ratio, 1.0)
                )
            else:
                energy_boost = 0.0
                max_energy = 0.0
                avg_energy = 0.0
                overlap_ratio = 0.0

            # Compute hybrid score
            # Base score from AI interest_score, boosted by energy
            base_score = clip.get('interest_score', 0.5)
            hybrid_score = base_score * (1 + self.energy_weight * energy_boost)

            # Cap at 1.0
            hybrid_score = min(hybrid_score, 1.0)

            # Create hybrid clip
            hybrid_clip = clip.copy()
            hybrid_clip.update({
                'hybrid_score': hybrid_score,
                'energy_boost': energy_boost,
                'max_energy': max_energy,
                'avg_energy': avg_energy,
                'overlap_ratio': overlap_ratio,
                'overlapping_segments': len(overlaps),
                'has_high_energy': energy_boost > 0.5
            })

            hybrid_clips.append(hybrid_clip)

        return hybrid_clips

    def _find_overlapping_segments(
        self,
        clip_start: float,
        clip_end: float,
        energy_segments: List[Dict]
    ) -> List[Dict]:
        """
        Find energy segments that overlap with a clip

        Args:
            clip_start: Clip start time in seconds
            clip_end: Clip end time in seconds
            energy_segments: List of energy segments

        Returns:
            List of overlapping segments with overlap metadata
        """
        overlapping = []

        clip_duration = clip_end - clip_start

        for segment in energy_segments:
            seg_start = segment['start_time']
            seg_end = segment['end_time']

            # Calculate overlap
            overlap_start = max(clip_start, seg_start)
            overlap_end = min(clip_end, seg_end)

            if overlap_start < overlap_end:
                # There is overlap
                overlap_duration = overlap_end - overlap_start
                overlap_ratio = overlap_duration / clip_duration

                # Only count significant overlaps (>10% of clip)
                if overlap_ratio > 0.1:
                    overlapping.append({
                        **segment,
                        'overlap_start': overlap_start,
                        'overlap_end': overlap_end,
                        'overlap_duration': overlap_duration,
                        'overlap_ratio': overlap_ratio
                    })

        return overlapping

    def _generate_stats(
        self,
        ai_clips: List[Dict],
        energy_segments: List[Dict],
        hybrid_clips: List[Dict]
    ) -> Dict:
        """Generate statistics about the hybrid analysis"""

        # Count clips with high energy
        high_energy_count = sum(1 for c in hybrid_clips if c['has_high_energy'])

        # Calculate average scores
        avg_ai_score = sum(c.get('interest_score', 0) for c in ai_clips) / len(ai_clips) if ai_clips else 0
        avg_hybrid_score = sum(c['hybrid_score'] for c in hybrid_clips) / len(hybrid_clips) if hybrid_clips else 0

        # Find clips with highest boost
        clips_with_boost = [c for c in hybrid_clips if c['energy_boost'] > 0]
        avg_boost = sum(c['energy_boost'] for c in clips_with_boost) / len(clips_with_boost) if clips_with_boost else 0

        return {
            'total_ai_clips': len(ai_clips),
            'total_energy_segments': len(energy_segments),
            'total_hybrid_clips': len(hybrid_clips),
            'clips_with_high_energy': high_energy_count,
            'clips_with_energy_boost': len(clips_with_boost),
            'avg_ai_score': round(avg_ai_score, 3),
            'avg_hybrid_score': round(avg_hybrid_score, 3),
            'avg_energy_boost': round(avg_boost, 3),
            'max_hybrid_score': round(max((c['hybrid_score'] for c in hybrid_clips), default=0), 3),
            'energy_boost_improved_ranking': self._count_ranking_changes(ai_clips, hybrid_clips)
        }

    def _count_ranking_changes(
        self,
        ai_clips: List[Dict],
        hybrid_clips: List[Dict]
    ) -> int:
        """
        Count how many clips changed position in ranking due to energy boost

        Args:
            ai_clips: Original AI clips sorted by interest_score
            hybrid_clips: Hybrid clips sorted by hybrid_score

        Returns:
            Number of clips that changed ranking position
        """
        # Create ranking maps
        ai_ranking = {clip['id']: i for i, clip in enumerate(ai_clips)}
        hybrid_ranking = {clip['id']: i for i, clip in enumerate(hybrid_clips)}

        # Count significant position changes (>2 positions)
        changes = 0
        for clip_id in ai_ranking:
            if clip_id in hybrid_ranking:
                position_change = abs(ai_ranking[clip_id] - hybrid_ranking[clip_id])
                if position_change > 2:
                    changes += 1

        return changes

    def export_results(self, results: Dict, output_path: Path) -> Path:
        """
        Export hybrid analysis results to JSON

        Args:
            results: Results dict from analyze_video()
            output_path: Path to save JSON file

        Returns:
            Path to exported file
        """
        # Make results JSON-serializable
        export_data = {
            'clips': results['clips'],
            'stats': results['stats'],
            'config': results['config'],
            'metadata': {
                'total_ai_clips': len(results['ai_clips']),
                'total_energy_segments': len(results['energy_segments'])
            }
        }

        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)

        return output_path

    def print_summary(self, results: Dict) -> None:
        """
        Print a summary of hybrid analysis results

        Args:
            results: Results dict from analyze_video()
        """
        stats = results['stats']
        clips = results['clips']

        print(f"\n{'='*70}")
        print("HYBRID ANALYSIS SUMMARY")
        print(f"{'='*70}\n")

        print(f"📊 Analysis Stats:")
        print(f"   AI Content Clips:      {stats['total_ai_clips']}")
        print(f"   Energy Segments:       {stats['total_energy_segments']}")
        print(f"   Clips with High Energy: {stats['clips_with_high_energy']}/{stats['total_hybrid_clips']}")
        print(f"   Clips with Energy Boost: {stats['clips_with_energy_boost']}/{stats['total_hybrid_clips']}")
        print()

        print(f"📈 Score Improvements:")
        print(f"   Avg AI Score:          {stats['avg_ai_score']:.3f}")
        print(f"   Avg Hybrid Score:      {stats['avg_hybrid_score']:.3f}")
        print(f"   Avg Energy Boost:      {stats['avg_energy_boost']:.3f}")
        print(f"   Max Hybrid Score:      {stats['max_hybrid_score']:.3f}")
        print(f"   Ranking Changes:       {stats['energy_boost_improved_ranking']} clips")
        print()

        print(f"{'='*70}")
        print(f"TOP {len(clips)} CLIPS (Hybrid Ranked)")
        print(f"{'='*70}\n")

        for i, clip in enumerate(clips[:10], 1):  # Show top 10
            ai_score = clip.get('interest_score', 0)
            hybrid_score = clip['hybrid_score']
            energy_boost = clip['energy_boost']

            # Show boost indicator
            boost_indicator = "⚡" if clip['has_high_energy'] else "  "

            print(f"{boost_indicator} #{i} - {clip['title'][:55]}")
            print(f"      Time: {self._format_time(clip['start_time'])} → "
                  f"{self._format_time(clip['end_time'])} ({clip['duration']:.0f}s)")
            print(f"      AI Score:     {ai_score:.3f}")
            print(f"      Hybrid Score: {hybrid_score:.3f} "
                  f"(+{((hybrid_score - ai_score) / ai_score * 100):.1f}%)")

            if clip['overlapping_segments'] > 0:
                print(f"      Energy: {clip['max_energy']:.3f} peak, "
                      f"{clip['overlap_ratio']:.1%} overlap, "
                      f"{clip['overlapping_segments']} segments")
            else:
                print(f"      Energy: No high-energy overlap")

            print()

    def _format_time(self, seconds: float) -> str:
        """Format seconds as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
