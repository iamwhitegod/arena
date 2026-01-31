"""
Variant Selector

Selects the best variant from a cluster of similar ThoughtUnits.

When multiple ThoughtUnits represent the same moment (duplicates),
this module picks the highest quality one based on:
- Completeness score (40% weight)
- Duration (30% weight - prefer 30-90s)
- Claim strength (20% weight)
- Boundary quality (10% weight)

Example:
- Cluster: 3 units about "God doesn't pick your spouse"
- Unit A: 120s, completeness 0.75, claim 7.5
- Unit B: 60s, completeness 0.77, claim 8.0  ← BEST
- Unit C: 15s, completeness 0.70, claim 7.0
- Selector picks Unit B (best balance)
"""

from typing import List, Dict
from .thought_unit import ThoughtUnit
import math


class VariantSelector:
    """
    Selects best variant from clusters of similar ThoughtUnits.

    Uses multi-criteria scoring:
    - Completeness (how complete is the thought?)
    - Duration (is it the right length?)
    - Claim strength (how powerful is the insight?)
    - Boundary quality (clean start/end?)
    """

    def __init__(
        self,
        ideal_min_duration: float = 30.0,
        ideal_max_duration: float = 90.0
    ):
        """
        Initialize variant selector

        Args:
            ideal_min_duration: Minimum ideal duration (default: 30s)
            ideal_max_duration: Maximum ideal duration (default: 90s)
        """
        self.ideal_min_duration = ideal_min_duration
        self.ideal_max_duration = ideal_max_duration
        self.metrics = {
            'clusters_processed': 0,
            'variants_selected': 0,
            'variants_rejected': 0,
            'avg_cluster_size': 0.0
        }

    def select_best_variants(
        self,
        clusters: List[List[ThoughtUnit]],
        verbose: bool = True
    ) -> List[ThoughtUnit]:
        """
        Select best variant from each cluster.

        Args:
            clusters: List of clusters (each cluster contains similar units)
            verbose: Print progress

        Returns:
            List of best ThoughtUnits (one per cluster)
        """
        if not clusters:
            return []

        if verbose:
            print(f"\n📍 STEP: Variant Selection")
            print(f"   Processing {len(clusters)} clusters...")

        best_variants = []

        for idx, cluster in enumerate(clusters, 1):
            if len(cluster) == 1:
                # Only one variant, use it
                best_variants.append(cluster[0])
                if verbose and idx <= 5:  # Show first 5
                    print(f"      Cluster {idx}: 1 unit (no selection needed)")
            else:
                # Multiple variants, select best
                best = self.select_best_variant(cluster)
                best_variants.append(best)

                if verbose and idx <= 5:  # Show first 5
                    scores = [self._score_variant(u) for u in cluster]
                    best_score = self._score_variant(best)
                    print(f"      Cluster {idx}: {len(cluster)} variants → selected {best.duration:.1f}s " +
                          f"(score: {best_score:.2f}, completeness: {best.completeness_score:.2f})")

        # Update metrics
        self.metrics['clusters_processed'] = len(clusters)
        self.metrics['variants_selected'] = len(best_variants)
        self.metrics['variants_rejected'] = sum(len(c) for c in clusters) - len(best_variants)
        self.metrics['avg_cluster_size'] = sum(len(c) for c in clusters) / len(clusters)

        if verbose:
            print(f"   ✓ Selected {len(best_variants)} best variants")
            print(f"   ✓ Rejected {self.metrics['variants_rejected']} lower quality variants")

        return best_variants

    def select_best_variant(self, cluster: List[ThoughtUnit]) -> ThoughtUnit:
        """
        Select best variant from a cluster.

        Args:
            cluster: List of similar ThoughtUnits

        Returns:
            The best ThoughtUnit
        """
        if len(cluster) == 1:
            return cluster[0]

        # Score all variants
        scores = [(unit, self._score_variant(unit)) for unit in cluster]

        # Sort by score (descending)
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return highest scoring variant
        return scores[0][0]

    def _score_variant(self, unit: ThoughtUnit) -> float:
        """
        Calculate variant quality score.

        Scoring formula:
        - Completeness score: 40% weight
        - Duration score: 30% weight
        - Claim strength: 20% weight
        - Boundary quality: 10% weight

        Args:
            unit: ThoughtUnit to score

        Returns:
            Quality score (0.0-1.0, higher is better)
        """
        # 1. Completeness score (0.0-1.0) - 40% weight
        completeness_score = unit.completeness_score * 0.4

        # 2. Duration score (0.0-1.0) - 30% weight
        duration_score = self._score_duration(unit.duration) * 0.3

        # 3. Claim strength (0.0-1.0) - 20% weight
        claim_score = (unit.claim_strength / 10.0) * 0.2

        # 4. Boundary quality (0.0-1.0) - 10% weight
        boundary_score = self._score_boundaries(unit) * 0.1

        # Total score
        total = completeness_score + duration_score + claim_score + boundary_score

        return total

    def _score_duration(self, duration: float) -> float:
        """
        Score duration based on ideal range.

        Scoring:
        - Too short (<20s): 0.5
        - Ideal range (30-90s): 1.0
        - Too long (>120s): 0.7
        - Extremely long (>180s): 0.5

        Args:
            duration: Duration in seconds

        Returns:
            Duration score (0.0-1.0)
        """
        if duration < 20:
            # Too short
            return 0.5
        elif duration <= self.ideal_min_duration:
            # Short but acceptable, ramp up to 1.0
            return 0.7 + (duration - 20) / (self.ideal_min_duration - 20) * 0.3
        elif duration <= self.ideal_max_duration:
            # Ideal range
            return 1.0
        elif duration <= 120:
            # Slightly too long, ramp down
            return 1.0 - (duration - self.ideal_max_duration) / (120 - self.ideal_max_duration) * 0.3
        elif duration <= 180:
            # Too long
            return 0.7 - (duration - 120) / 60 * 0.2
        else:
            # Extremely long
            return 0.5

    def _score_boundaries(self, unit: ThoughtUnit) -> float:
        """
        Score boundary quality (clean start/end).

        Checks:
        - Does premise start at a sentence boundary?
        - Does resolution end at a sentence boundary?
        - Are there natural pauses?

        Args:
            unit: ThoughtUnit to score

        Returns:
            Boundary score (0.0-1.0)
        """
        # Simple heuristic: Check if text starts/ends with capitals and periods
        score = 0.5  # Base score

        # Check premise start (should start with capital)
        if unit.premise_text and unit.premise_text[0].isupper():
            score += 0.15

        # Check resolution end (should end with punctuation)
        if unit.resolution_text and unit.resolution_text[-1] in '.!?':
            score += 0.15

        # Check claim clarity (not too short)
        if len(unit.claim_text.split()) >= 5:
            score += 0.1

        # Check overall text quality (not too many incomplete words)
        full_text = unit.full_text
        if '...' not in full_text[:50]:  # No ellipsis at start
            score += 0.1

        return min(score, 1.0)

    def analyze_selection(
        self,
        clusters: List[List[ThoughtUnit]],
        selected: List[ThoughtUnit],
        verbose: bool = True
    ) -> Dict:
        """
        Analyze variant selection results.

        Args:
            clusters: Original clusters
            selected: Selected best variants
            verbose: Print analysis

        Returns:
            Analysis dict with statistics
        """
        # Calculate metrics
        total_units = sum(len(c) for c in clusters)
        rejection_rate = (total_units - len(selected)) / total_units * 100

        # Duration distribution
        durations = [u.duration for u in selected]
        avg_duration = sum(durations) / len(durations) if durations else 0
        ideal_count = sum(1 for d in durations if self.ideal_min_duration <= d <= self.ideal_max_duration)

        # Completeness distribution
        completeness = [u.completeness_score for u in selected]
        avg_completeness = sum(completeness) / len(completeness) if completeness else 0

        analysis = {
            'total_input_units': total_units,
            'selected_units': len(selected),
            'rejected_units': total_units - len(selected),
            'rejection_rate': rejection_rate,
            'avg_duration': avg_duration,
            'ideal_duration_count': ideal_count,
            'ideal_duration_rate': ideal_count / len(selected) * 100 if selected else 0,
            'avg_completeness': avg_completeness,
            'production_count': sum(1 for u in selected if u.meets_production_standard())
        }

        if verbose:
            print(f"\n📊 Variant Selection Analysis:")
            print(f"   Input: {analysis['total_input_units']} units")
            print(f"   Selected: {analysis['selected_units']} units")
            print(f"   Rejected: {analysis['rejected_units']} units ({analysis['rejection_rate']:.1f}%)")
            print(f"   Average duration: {analysis['avg_duration']:.1f}s")
            print(f"   Ideal duration (30-90s): {analysis['ideal_duration_count']}/{analysis['selected_units']} ({analysis['ideal_duration_rate']:.0f}%)")
            print(f"   Average completeness: {analysis['avg_completeness']:.2f}")
            print(f"   Production quality: {analysis['production_count']}/{analysis['selected_units']}")

        return analysis

    def get_rejected_variants(
        self,
        clusters: List[List[ThoughtUnit]],
        selected: List[ThoughtUnit]
    ) -> List[ThoughtUnit]:
        """
        Get all rejected variants for analysis.

        Args:
            clusters: Original clusters
            selected: Selected best variants

        Returns:
            List of rejected ThoughtUnits
        """
        selected_set = set(selected)
        rejected = []

        for cluster in clusters:
            for unit in cluster:
                if unit not in selected_set:
                    rejected.append(unit)

        return rejected
