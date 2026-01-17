"""
FourLayerAdapter - Drop-in replacement for TranscriptAnalyzer

This adapter maintains the same interface as TranscriptAnalyzer but uses
the 4-layer editorial architecture internally for higher quality clips.
"""

from typing import List, Dict, Optional
from pathlib import Path
import json


class FourLayerAdapter:
    """
    Drop-in replacement for TranscriptAnalyzer using 4-layer editorial system.

    Maintains exact same interface for backward compatibility with HybridAnalyzer:
    - analyze_transcript(transcript_data, target_clips, min_duration, max_duration)
    - generate_clip_title(transcript_segment)  # For ProfessionalClipAligner

    The 4-layer system:
        Layer 1: Find interesting moments (25 candidates)
        Layer 2: Expand to complete thought boundaries (18 candidates)
        Layer 3: Validate standalone context (12 pass, quality gate)
        Layer 4: Package with titles/descriptions/metadata

    Example:
        >>> from arena.editorial import FourLayerAdapter
        >>> analyzer = FourLayerAdapter(api_key="sk-...")
        >>> clips = analyzer.analyze_transcript(transcript_data, target_clips=10)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o",
        export_layers: bool = False,
        score_weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize 4-layer editorial adapter

        Args:
            api_key: OpenAI API key
            model: Base model to use (default: gpt-4o)
            export_layers: Whether to export intermediate layer results for debugging
            score_weights: Custom scoring weights (default: {'interest': 0.6, 'standalone': 0.4})
        """
        self.api_key = api_key
        self.model = model
        self.export_layers = export_layers
        self.layer_outputs = {}  # Store for export

        # Default scoring weights (60% interest, 40% standalone)
        self.score_weights = score_weights or {
            'interest': 0.6,
            'standalone': 0.4
        }

        # Layers will be initialized on first use
        # (lazy initialization to avoid loading if not needed)

    def analyze_transcript(
        self,
        transcript_data: Dict,
        target_clips: int = 10,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None
    ) -> List[Dict]:
        """
        Run 4-layer editorial analysis and return clips compatible with HybridAnalyzer.

        Args:
            transcript_data: Transcript dict with 'segments', 'text', 'duration'
            target_clips: Number of clips to generate
            min_duration: Optional minimum clip duration in seconds
            max_duration: Optional maximum clip duration in seconds

        Returns:
            List[Dict] with format:
            {
                'id': str,              # "clip_001"
                'start_time': float,
                'end_time': float,
                'duration': float,
                'title': str,
                'reason': str,
                'interest_score': float,
                'content_type': str,
                # Metadata for debugging
                '_4layer_metadata': {
                    'standalone_score': float,
                    'hashtags': List[str],
                    'thumbnail_time': float,
                    'layer1': Dict,
                    'layer2': Dict,
                    'layer3': Dict
                }
            }
        """
        from .layer1_moment_detector import MomentDetector
        from .layer2_boundary_analyzer import ThoughtBoundaryAnalyzer
        from .layer3_context_refiner import StandaloneContextRefiner
        from .layer4_packaging import PackagingLayer

        print("\n🎬 4-LAYER EDITORIAL ANALYSIS")
        print("="*70)

        # Layer 1: Find interesting moments (over-detect 2.5x)
        print("\n[1/4] 🔍 Detecting interesting moments...")
        self.moment_detector = MomentDetector(self.api_key, model=self.model)
        moments = self.moment_detector.detect(
            transcript_data,
            target_moments=int(target_clips * 2.5)
        )
        print(f"      ✓ Found {len(moments)} candidate moments")

        if not moments:
            print("      ❌ No interesting moments found")
            return []

        # Store Layer 1 output
        if self.export_layers:
            self.layer_outputs['layer1_moments'] = moments

        # Layer 2: Expand to complete thought boundaries
        print("\n[2/4] 🧠 Analyzing thought boundaries...")
        self.boundary_analyzer = ThoughtBoundaryAnalyzer(self.api_key, model=self.model)
        thoughts = self.boundary_analyzer.analyze_all(
            moments,
            transcript_data,
            parallel=True
        )
        print(f"      ✓ Analyzed {len(thoughts)} complete thoughts")

        if not thoughts:
            print("      ❌ No complete thoughts identified")
            return []

        # Store Layer 2 output
        if self.export_layers:
            self.layer_outputs['layer2_boundaries'] = thoughts

        # Layer 3: Validate standalone context (QUALITY GATE)
        print("\n[3/4] ✂️  Validating standalone context...")
        self.context_refiner = StandaloneContextRefiner(self.api_key, model="gpt-4o-mini")
        validated_clips = self.context_refiner.refine_all(
            thoughts,
            transcript_data,
            min_duration,
            max_duration
        )

        # Filter to only PASS clips
        passed_clips = [c for c in validated_clips if c['verdict'] == 'PASS']
        print(f"      ✓ {len(passed_clips)} clips passed validation")
        print(f"      ✗ {len(validated_clips) - len(passed_clips)} clips rejected/revised")

        if not passed_clips:
            print("      ❌ No clips passed standalone validation")
            return []

        # Store Layer 3 output
        if self.export_layers:
            self.layer_outputs['layer3_validated'] = validated_clips

        # Layer 4: Package top clips
        print("\n[4/4] 📦 Packaging clips...")
        self.packager = PackagingLayer(self.api_key, model="gpt-4o-mini")
        packaged_clips = self.packager.package_all(passed_clips, transcript_data)

        # Select top N by combined score (configurable weights)
        def combined_score(c):
            return (
                c['interest_score'] * self.score_weights['interest'] +
                c['standalone_score'] * self.score_weights['standalone']
            )

        top_clips = sorted(packaged_clips, key=combined_score, reverse=True)[:target_clips]

        print(f"      ✓ Packaged {len(top_clips)} final clips")

        # Store Layer 4 output
        if self.export_layers:
            self.layer_outputs['layer4_packaged'] = packaged_clips

        # Convert to TranscriptAnalyzer format
        legacy_clips = self._convert_to_legacy_format(top_clips)

        # Print summary
        self._print_summary(legacy_clips)

        return legacy_clips

    def generate_clip_title(self, transcript_segment: str) -> str:
        """
        Generate title for clip (called by ProfessionalClipAligner).

        This is called after professional alignment adjusts boundaries,
        so we need to regenerate the title based on the final content.

        Args:
            transcript_segment: Text content of the aligned clip

        Returns:
            str: Generated title (max 60 chars)
        """
        # Initialize packager if not already done
        if not hasattr(self, 'packager'):
            from .layer4_packaging import PackagingLayer
            self.packager = PackagingLayer(self.api_key, model="gpt-4o-mini")

        # Use Layer 4 to generate title
        return self.packager.generate_title_only(transcript_segment)

    def extract_transcript_text(
        self,
        transcript_segments: List[Dict],
        start_time: float,
        end_time: float
    ) -> str:
        """
        Extract transcript text for a specific time range.

        This method is called by ProfessionalClipAligner when regenerating
        titles after boundary alignment.

        Args:
            transcript_segments: List of transcript segments with 'start', 'end', 'text'
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Concatenated transcript text for the time range
        """
        text_parts = []

        for segment in transcript_segments:
            seg_start = segment.get('start', 0)
            seg_end = segment.get('end', 0)

            # Check if segment overlaps with our time range
            if seg_start < end_time and seg_end > start_time:
                text_parts.append(segment.get('text', '').strip())

        return ' '.join(text_parts)

    def export_layer_outputs(self, output_dir: Path):
        """
        Export intermediate layer results for debugging

        Creates files:
            - output_dir/editorial/layer1_moments.json
            - output_dir/editorial/layer2_boundaries.json
            - output_dir/editorial/layer3_validated.json
            - output_dir/editorial/layer4_packaged.json

        Args:
            output_dir: Directory to export results to
        """
        if not self.export_layers:
            return

        layer_dir = output_dir / "editorial"
        layer_dir.mkdir(exist_ok=True, parents=True)

        for layer_name, data in self.layer_outputs.items():
            output_file = layer_dir / f"{layer_name}.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"   ✓ Exported {layer_name}.json")

    def _convert_to_legacy_format(self, clips: List[Dict]) -> List[Dict]:
        """
        Convert 4-layer output to format expected by HybridAnalyzer

        Args:
            clips: Packaged clips from Layer 4

        Returns:
            List[Dict] in TranscriptAnalyzer format
        """
        legacy_clips = []
        for i, clip in enumerate(clips, 1):
            legacy_clips.append({
                # Required fields (HybridAnalyzer expects these)
                'id': f"clip_{i:03d}",
                'start_time': clip['start_time'],
                'end_time': clip['end_time'],
                'duration': clip['duration'],
                'title': clip['title'],
                'reason': clip['description'],  # Use description as reason
                'interest_score': clip['interest_score'],
                'content_type': clip['content_type'],
                # Extra metadata (preserved through pipeline)
                '_4layer_metadata': {
                    'standalone_score': clip['standalone_score'],
                    'hashtags': clip['hashtags'],
                    'thumbnail_time': clip['thumbnail_time'],
                    'layer1': clip.get('_layer1'),
                    'layer2': clip.get('_layer2'),
                    'layer3': clip.get('_layer3')
                }
            })
        return legacy_clips

    def _print_summary(self, clips: List[Dict]):
        """
        Print summary of 4-layer analysis

        Args:
            clips: Final clips in legacy format
        """
        print("\n" + "="*70)
        print("📊 EDITORIAL SUMMARY")
        print("="*70)
        print(f"Final clips: {len(clips)}")

        # Calculate total cost from all layers
        total_cost = 0.0
        total_tokens = 0
        total_api_calls = 0

        if hasattr(self, 'moment_detector'):
            total_cost += self.moment_detector.metrics.get('cost_usd', 0)
            total_tokens += self.moment_detector.metrics.get('tokens_used', 0)
            total_api_calls += self.moment_detector.metrics.get('api_calls', 0)

        if hasattr(self, 'boundary_analyzer'):
            total_cost += self.boundary_analyzer.metrics.get('cost_usd', 0)
            total_tokens += self.boundary_analyzer.metrics.get('tokens_used', 0)
            total_api_calls += self.boundary_analyzer.metrics.get('api_calls', 0)

        if hasattr(self, 'context_refiner'):
            total_cost += self.context_refiner.metrics.get('cost_usd', 0)
            total_tokens += self.context_refiner.metrics.get('tokens_used', 0)
            total_api_calls += self.context_refiner.metrics.get('api_calls', 0)

        if hasattr(self, 'packager'):
            total_cost += self.packager.metrics.get('cost_usd', 0)
            total_tokens += self.packager.metrics.get('tokens_used', 0)
            total_api_calls += self.packager.metrics.get('api_calls', 0)

        print(f"Total cost: ${total_cost:.2f}")
        print(f"Total tokens: {total_tokens:,}")
        print(f"Total API calls: {total_api_calls}")

        # Show layer breakdown
        if hasattr(self, 'context_refiner'):
            pass_rate = self.context_refiner.metrics.get('pass_rate', 0)
            print(f"Layer 3 pass rate: {pass_rate:.1%}")

        # Show top 3 clips
        print("\nTop 3 Clips:")
        for i, clip in enumerate(clips[:3], 1):
            print(f"  {i}. [{clip['duration']:.1f}s] {clip['title']}")
            if '_4layer_metadata' in clip:
                score = (clip['interest_score'] * 0.6) + (clip['_4layer_metadata']['standalone_score'] * 0.4)
                print(f"     Combined Score: {score:.2f} (Interest: {clip['interest_score']:.2f}, Standalone: {clip['_4layer_metadata']['standalone_score']:.2f})")

        print("="*70 + "\n")
