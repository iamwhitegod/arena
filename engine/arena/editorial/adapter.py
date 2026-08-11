"""
FourLayerAdapter - The primary editorial analysis engine for Arena.

Uses the ThoughtUnit editorial system (4 layers) for high quality clips.

New Architecture (Weeks 1-4):
    Week 1: Seed Detection → Find 40 interesting moment seeds
    Week 2: Construction → Expand to complete ThoughtUnits (premise/claim/resolution)
    Week 3: Validation → Score completeness + validate standalone context
    Week 4: Deduplication → Cluster similar units and select best variants

This replaces the old 4-layer system with a more robust approach.
"""

from typing import List, Dict, Optional
from pathlib import Path
import json
import sys


class FourLayerAdapter:
    """
    The primary editorial analysis engine for Arena.

    Implements the interface expected by HybridAnalyzer:
    - analyze_transcript(transcript_data, target_clips, min_duration, max_duration)
    - generate_clip_title(transcript_segment)  # For ProfessionalClipAligner

    The new system (Weeks 1-4):
        Week 1: Detect 40 thought seeds (interesting moments)
        Week 2: Construct ThoughtUnits with premise/claim/resolution
        Week 3: Score completeness + validate standalone context
        Week 4: Deduplicate semantically similar units, select best variants

    Example:
        >>> from arena.editorial import FourLayerAdapter
        >>> analyzer = FourLayerAdapter(api_key="sk-...")
        >>> clips = analyzer.analyze_transcript(transcript_data, target_clips=10)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        export_layers: bool = False,
        score_weights: Optional[Dict[str, float]] = None,
        enable_checkpoints: bool = True,
        checkpoint_dir: str = ".checkpoint",
        max_workers: int = 2
    ):
        """
        Initialize editorial adapter

        Args:
            api_key: OpenAI API key
            model: Base model to use (default: gpt-4o-mini for cost efficiency)
            export_layers: Whether to export intermediate results for debugging
            score_weights: Custom scoring weights (default: {'completeness': 0.75, 'standalone': 0.25})
            enable_checkpoints: Enable progress checkpointing (default: True)
            checkpoint_dir: Directory for checkpoints (default: .checkpoint)
            max_workers: Max parallel API calls for scoring/validation (default: 2)
                        Higher = faster but more API pressure. Keep low for strict rate limits.
        """
        self.api_key = api_key
        self.model = model
        self.export_layers = export_layers
        self.layer_outputs = {}  # Store for export
        self.enable_checkpoints = enable_checkpoints
        self.checkpoint_dir = checkpoint_dir
        self.max_workers = max_workers

        # Default scoring weights (75% completeness, 25% standalone)
        self.score_weights = score_weights or {
            'completeness': 0.75,
            'standalone': 0.25
        }

        # Modules will be initialized on first use
        # (lazy initialization to avoid loading if not needed)

    def analyze_transcript(
        self,
        transcript_data: Dict,
        target_clips: int = 10,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None
    ) -> List[Dict]:
        """
        Run ThoughtUnit editorial analysis and return clips compatible with HybridAnalyzer.

        Args:
            transcript_data: Transcript dict with 'segments', 'text', 'duration'
            target_clips: Number of clips to generate
            min_duration: Optional minimum clip duration in seconds
            max_duration: Optional maximum clip duration in seconds

        Returns:
            List[Dict] with clip format:
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
                    'completeness_score': float,
                    'standalone_score': float,
                    'premise_clarity': float,
                    'claim_strength': float,
                    'resolution_closure': float,
                    'rhetorical_type': str
                }
            }
        """
        from .thought_seed_detector import ThoughtSeedDetector
        from .thought_unit_constructor import ThoughtUnitConstructor
        from .completeness_scorer import CompletenessScorer
        from .standalone_validator import StandaloneValidator
        from .semantic_deduplicator import SemanticDeduplicator
        from .variant_selector import VariantSelector
        from .checkpoint import CheckpointManager

        print("\n🎬 THOUGHTUNIT EDITORIAL SYSTEM")
        print("="*70)
        print(f"Model: {self.model} | Target clips: {target_clips}")
        if min_duration or max_duration:
            print(f"Duration constraints: {min_duration or 'any'}-{max_duration or 'any'}s")
        print()
        sys.stdout.flush()

        # Initialize checkpoint manager
        checkpoint_mgr = CheckpointManager(
            checkpoint_dir=self.checkpoint_dir,
            enabled=self.enable_checkpoints
        )
        job_id = CheckpointManager.generate_job_id(transcript_data)

        if self.enable_checkpoints:
            existing_checkpoints = checkpoint_mgr.list_checkpoints(job_id)
            if existing_checkpoints:
                print(f"      ♻️  Found {len(existing_checkpoints)} existing checkpoint(s)")
                sys.stdout.flush()

        # =========================================================================
        # WEEK 1: Seed Detection
        # =========================================================================
        print("[1/4] 🌱 Week 1: Detecting Thought Seeds")
        print("-" * 70)
        sys.stdout.flush()

        # Try to load from checkpoint
        seeds = checkpoint_mgr.load_checkpoint(job_id, "seed_detection")

        if seeds is None:
            # Run seed detection
            self.seed_detector = ThoughtSeedDetector(self.api_key, model=self.model)
            seeds = self.seed_detector.detect_seeds(
                transcript_data,
                target_count=target_clips
            )

            # Save checkpoint
            checkpoint_mgr.save_checkpoint(
                job_id,
                "seed_detection",
                seeds,
                metadata={'count': len(seeds)}
            )
        else:
            print(f"      ♻️  Resumed from checkpoint")
            sys.stdout.flush()

        print(f"      ✓ Found {len(seeds)} thought seeds")
        sys.stdout.flush()

        if not seeds:
            print("      ❌ No interesting moments found")
            sys.stdout.flush()
            return []

        # Store Week 1 output
        if self.export_layers:
            self.layer_outputs['week1_seeds'] = seeds

        # =========================================================================
        # WEEK 2: ThoughtUnit Construction
        # =========================================================================
        print("\n[2/4] 🏗️  Week 2: Constructing ThoughtUnits")
        print("-" * 70)
        sys.stdout.flush()

        # Try to load from checkpoint
        thought_units_data = checkpoint_mgr.load_checkpoint(job_id, "construction")

        if thought_units_data is None:
            # Run construction
            self.constructor = ThoughtUnitConstructor(
                self.api_key,
                model=self.model,
                verbose=False
            )

            thought_units = self.constructor.construct_from_seeds(
                seeds,
                transcript_data['segments']
            )

            # Save checkpoint (serialize ThoughtUnits)
            checkpoint_mgr.save_checkpoint(
                job_id,
                "construction",
                [
                    {
                        'premise_start': u.premise_start,
                        'claim_peak': u.claim_peak,
                        'resolution_end': u.resolution_end,
                        'premise_text': u.premise_text,
                        'claim_text': u.claim_text,
                        'resolution_text': u.resolution_text,
                        'rhetorical_type': u.rhetorical_type.value,
                        'dependency_level': u.dependency_level.value,
                        'has_unresolved_refs': u.has_unresolved_refs
                    }
                    for u in thought_units
                ],
                metadata={'count': len(thought_units)}
            )
        else:
            # Reconstruct ThoughtUnits from checkpoint
            from .thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel
            print(f"      ♻️  Resumed from checkpoint")
            thought_units = [
                ThoughtUnit(
                    premise_start=u['premise_start'],
                    claim_peak=u['claim_peak'],
                    resolution_end=u['resolution_end'],
                    premise_text=u['premise_text'],
                    claim_text=u['claim_text'],
                    resolution_text=u['resolution_text'],
                    rhetorical_type=RhetoricalType(u['rhetorical_type']),
                    dependency_level=DependencyLevel(u['dependency_level']),
                    has_unresolved_refs=u['has_unresolved_refs']
                )
                for u in thought_units_data
            ]
            sys.stdout.flush()

        print(f"      ✓ Constructed {len(thought_units)} ThoughtUnits")
        sys.stdout.flush()

        if not thought_units:
            print("      ❌ No complete ThoughtUnits identified")
            sys.stdout.flush()
            return []

        # Filter by duration constraints
        if min_duration or max_duration:
            before_count = len(thought_units)
            thought_units = [
                u for u in thought_units
                if (min_duration is None or u.duration >= min_duration) and
                   (max_duration is None or u.duration <= max_duration)
            ]
            filtered = before_count - len(thought_units)
            if filtered > 0:
                print(f"      ⚠️  Filtered out {filtered} units (duration constraints)")
                sys.stdout.flush()

        # Store Week 2 output
        if self.export_layers:
            self.layer_outputs['week2_units'] = [
                {
                    'duration': u.duration,
                    'premise_start': u.premise_start,
                    'claim_peak': u.claim_peak,
                    'resolution_end': u.resolution_end,
                    'premise_text': u.premise_text,
                    'claim_text': u.claim_text,
                    'resolution_text': u.resolution_text,
                    'rhetorical_type': u.rhetorical_type.value
                }
                for u in thought_units
            ]

        # =========================================================================
        # WEEK 3: Completeness Validation & Scoring
        # =========================================================================
        print("\n[3/4] 🎯 Week 3: Completeness Validation & Scoring")
        print("-" * 70)
        sys.stdout.flush()

        # Standalone validation (parallel processing for speed)
        print("      Running standalone validation...")
        sys.stdout.flush()
        self.standalone_validator = StandaloneValidator(self.api_key, model=self.model)
        validations = self.standalone_validator.validate_batch_parallel(thought_units, max_workers=self.max_workers, verbose=False)
        thought_units = self.standalone_validator.update_thought_units(thought_units, validations)

        standalone_rate = sum(1 for v in validations if v['is_standalone']) / len(validations) * 100 if validations else 0
        print(f"      ✓ Standalone validation: {standalone_rate:.0f}% passed")
        sys.stdout.flush()

        # Completeness scoring (parallel processing for speed)
        print("      Running completeness scoring...")
        sys.stdout.flush()
        self.completeness_scorer = CompletenessScorer(self.api_key, model=self.model)
        scores = self.completeness_scorer.score_batch_parallel(thought_units, max_workers=self.max_workers, verbose=False)
        thought_units = self.completeness_scorer.update_thought_units(thought_units, scores)

        avg_completeness = sum(u.completeness_score for u in thought_units) / len(thought_units) if thought_units else 0
        production_count = sum(1 for u in thought_units if u.meets_production_standard())
        print(f"      ✓ Average completeness: {avg_completeness:.2f}")
        print(f"      ✓ Production quality: {production_count}/{len(thought_units)} units")
        sys.stdout.flush()

        # Store Week 3 output
        if self.export_layers:
            self.layer_outputs['week3_scored'] = [
                {
                    'duration': u.duration,
                    'completeness_score': u.completeness_score,
                    'premise_clarity': u.premise_clarity,
                    'claim_strength': u.claim_strength,
                    'resolution_closure': u.resolution_closure,
                    'standalone_score': validations[i]['standalone_score'],
                    'is_standalone': validations[i]['is_standalone'],
                    'meets_production': u.meets_production_standard()
                }
                for i, u in enumerate(thought_units)
            ]

        # =========================================================================
        # WEEK 4: Deduplication & Variant Selection
        # =========================================================================
        print("\n[4/4] 🔄 Week 4: Deduplication & Variant Selection")
        print("-" * 70)
        sys.stdout.flush()

        # Semantic + Temporal deduplication
        self.deduplicator = SemanticDeduplicator(self.api_key)
        unique_units, clusters = self.deduplicator.deduplicate(
            thought_units,
            similarity_threshold=0.92,
            temporal_overlap_threshold=0.65,  # 65% overlap = duplicate
            verbose=False
        )

        dedup_rate = (len(thought_units) - len(clusters)) / len(thought_units) * 100 if thought_units else 0
        print(f"      ✓ Clustering: {len(clusters)} unique moments ({dedup_rate:.0f}% reduction)")
        sys.stdout.flush()

        # Variant selection
        self.variant_selector = VariantSelector(
            ideal_min_duration=min_duration or 30,
            ideal_max_duration=max_duration or 90
        )
        best_variants = self.variant_selector.select_best_variants(clusters, verbose=False)

        print(f"      ✓ Selected {len(best_variants)} best variants")
        sys.stdout.flush()

        # Store Week 4 output
        if self.export_layers:
            self.layer_outputs['week4_deduplicated'] = [
                {
                    'duration': u.duration,
                    'completeness_score': u.completeness_score,
                    'claim_text': u.claim_text
                }
                for u in best_variants
            ]

        # =========================================================================
        # Select Top N Clips
        # =========================================================================

        # Sort by combined score
        def combined_score(unit):
            # Get standalone score from validation
            standalone_score = 0.0
            for i, u in enumerate(thought_units):
                if u == unit:
                    standalone_score = validations[i]['standalone_score']
                    break

            return (
                unit.completeness_score * self.score_weights['completeness'] +
                standalone_score * self.score_weights['standalone']
            )

        sorted_units = sorted(best_variants, key=combined_score, reverse=True)
        top_units = sorted_units[:target_clips]

        print(f"\n      ✓ Selected top {len(top_units)} clips for export")
        sys.stdout.flush()

        # =========================================================================
        # Convert to Legacy Format
        # =========================================================================

        legacy_clips = []
        for i, unit in enumerate(top_units, 1):
            # Find standalone score from validations
            standalone_score = 0.0
            for j, u in enumerate(thought_units):
                if u == unit:
                    standalone_score = validations[j]['standalone_score']
                    break

            # Generate title from claim text
            title = self._generate_title(unit.claim_text)

            # Generate reason/description
            reason = f"{unit.rhetorical_type.value.title()}: {unit.claim_text[:100]}"

            legacy_clips.append({
                # Required fields (HybridAnalyzer expects these)
                'id': f"clip_{i:03d}",
                'start_time': unit.premise_start,
                'end_time': unit.resolution_end,
                'duration': unit.duration,
                'title': title,
                'reason': reason,
                'interest_score': unit.completeness_score,  # Use completeness as interest
                'content_type': unit.rhetorical_type.value,
                # Extra metadata (preserved through pipeline)
                '_4layer_metadata': {
                    'completeness_score': unit.completeness_score,
                    'standalone_score': standalone_score,
                    'premise_clarity': unit.premise_clarity,
                    'claim_strength': unit.claim_strength,
                    'resolution_closure': unit.resolution_closure,
                    'rhetorical_type': unit.rhetorical_type.value,
                    'premise_text': unit.premise_text,
                    'claim_text': unit.claim_text,
                    'resolution_text': unit.resolution_text
                }
            })

        # Print summary
        self._print_summary(legacy_clips)

        # Clean up checkpoints on successful completion
        if self.enable_checkpoints:
            checkpoint_mgr.clear_checkpoints(job_id)

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
        return self._generate_title(transcript_segment)

    def _generate_title(self, text: str) -> str:
        """
        Generate a title from text (max 60 chars).

        Uses simple extraction: first sentence or claim text.

        Args:
            text: Text to generate title from

        Returns:
            Title string (max 60 chars)
        """
        # Clean text
        text = text.strip()

        # Take first sentence or first 60 chars
        sentences = text.split('.')
        if sentences:
            title = sentences[0].strip()
        else:
            title = text

        # Truncate to 60 chars
        if len(title) > 60:
            title = title[:57] + "..."

        # Convert to title case
        title = title.title()

        return title

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
            - output_dir/editorial/week1_seeds.json
            - output_dir/editorial/week2_units.json
            - output_dir/editorial/week3_scored.json
            - output_dir/editorial/week4_deduplicated.json

        Args:
            output_dir: Directory to export results to
        """
        if not self.export_layers:
            return

        layer_dir = output_dir / "editorial"
        layer_dir.mkdir(exist_ok=True, parents=True)

        for week_name, data in self.layer_outputs.items():
            output_file = layer_dir / f"{week_name}.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            print(f"   ✓ Exported {week_name}.json")

    def _print_summary(self, clips: List[Dict]):
        """
        Print summary of ThoughtUnit editorial analysis

        Args:
            clips: Final clips in legacy format
        """
        print("\n" + "="*70)
        print("📊 THOUGHTUNIT EDITORIAL SUMMARY")
        print("="*70)
        print(f"Final clips: {len(clips)}")

        # Calculate total cost from all modules
        total_cost = 0.0
        total_tokens = 0
        total_api_calls = 0

        if hasattr(self, 'seed_detector'):
            total_cost += self.seed_detector.metrics.get('cost_usd', 0)
            total_tokens += self.seed_detector.metrics.get('tokens_used', 0)
            total_api_calls += self.seed_detector.metrics.get('api_calls', 0)

        if hasattr(self, 'constructor'):
            total_cost += self.constructor.metrics.get('total_cost_usd', 0)
            total_tokens += self.constructor.metrics.get('total_tokens_used', 0)
            total_api_calls += self.constructor.metrics.get('total_api_calls', 0)

        if hasattr(self, 'standalone_validator'):
            total_cost += self.standalone_validator.metrics.get('cost_usd', 0)
            total_tokens += self.standalone_validator.metrics.get('tokens_used', 0)
            total_api_calls += self.standalone_validator.metrics.get('api_calls', 0)

        if hasattr(self, 'completeness_scorer'):
            total_cost += self.completeness_scorer.metrics.get('cost_usd', 0)
            total_tokens += self.completeness_scorer.metrics.get('tokens_used', 0)
            total_api_calls += self.completeness_scorer.metrics.get('api_calls', 0)

        if hasattr(self, 'deduplicator'):
            total_cost += self.deduplicator.metrics.get('cost_usd', 0)
            total_tokens += self.deduplicator.metrics.get('tokens_used', 0)
            total_api_calls += self.deduplicator.metrics.get('api_calls', 0)

        print(f"Total cost: ${total_cost:.3f}")
        print(f"Total tokens: {total_tokens:,}")
        print(f"Total API calls: {total_api_calls}")

        # Show average scores
        if clips:
            avg_completeness = sum(c['_4layer_metadata']['completeness_score'] for c in clips) / len(clips)
            avg_standalone = sum(c['_4layer_metadata']['standalone_score'] for c in clips) / len(clips)
            production_count = sum(1 for c in clips if c['_4layer_metadata']['completeness_score'] >= 0.60)

            print(f"\nQuality Metrics:")
            print(f"  Average completeness: {avg_completeness:.2f}")
            print(f"  Average standalone: {avg_standalone:.2f}")
            print(f"  Production quality: {production_count}/{len(clips)} clips")

        # Show top 3 clips
        print("\nTop 3 Clips:")
        for i, clip in enumerate(clips[:3], 1):
            metadata = clip['_4layer_metadata']
            combined = (
                metadata['completeness_score'] * self.score_weights['completeness'] +
                metadata['standalone_score'] * self.score_weights['standalone']
            )
            print(f"  {i}. [{clip['duration']:.1f}s] {clip['title']}")
            print(f"     Score: {combined:.2f} (C:{metadata['completeness_score']:.2f}, S:{metadata['standalone_score']:.2f})")
            print(f"     {metadata['rhetorical_type'].title()}: {metadata['claim_text'][:60]}...")

        print("="*70 + "\n")
