"""
Thought Unit Constructor

Constructs complete ThoughtUnit instances by combining:
- Premises (from premise detector)
- Seeds/Claims (from seed detector)
- Resolutions (from resolution detector)

This is the integration layer that builds the complete rhetorical structure.
"""

from typing import Dict, List, Optional
from .thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel
from .premise_detector import PremiseDetector
from .resolution_detector import ResolutionDetector


class ThoughtUnitConstructor:
    """
    Constructs complete ThoughtUnit instances from seeds + premises + resolutions.

    Pipeline:
    1. Start with seeds (claims/insights)
    2. Detect premise for each seed (backward search)
    3. Detect resolution for each seed (forward search)
    4. Construct ThoughtUnit if both premise and resolution found
    5. Validate completeness
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        verbose: bool = True
    ):
        """
        Initialize thought unit constructor

        Args:
            api_key: OpenAI API key
            model: Model to use for detection
            verbose: Print progress messages
        """
        self.api_key = api_key
        self.model = model
        self.verbose = verbose

        # Initialize detectors
        self.premise_detector = PremiseDetector(api_key, model)
        self.resolution_detector = ResolutionDetector(api_key, model)

        # Metrics
        self.metrics = {
            'seeds_processed': 0,
            'premises_found': 0,
            'resolutions_found': 0,
            'thought_units_constructed': 0,
            'thought_units_complete': 0,
            'construction_failures': 0,
            'total_cost_usd': 0.0
        }

    def construct_from_seeds(
        self,
        seeds: List[Dict],
        transcript_segments: List[Dict]
    ) -> List[ThoughtUnit]:
        """
        Construct ThoughtUnit instances from seeds.

        Args:
            seeds: List of seed dicts from ThoughtSeedDetector
            transcript_segments: Full transcript segments

        Returns:
            List of constructed ThoughtUnit instances
            (only includes successfully constructed units)
        """
        thought_units = []

        if self.verbose:
            print(f"\n🏗️  Constructing thought units from {len(seeds)} seeds...")
            print("=" * 70)

        # Step 1: Detect all premises
        if self.verbose:
            print(f"\n📍 STEP 1: Premise Detection (backward search)")
            print("-" * 70)

        premises = self.premise_detector.detect_premises_batch(
            seeds,
            transcript_segments,
            verbose=self.verbose
        )

        self.metrics['premises_found'] = sum(1 for p in premises if p is not None)

        # Step 2: Detect all resolutions
        if self.verbose:
            print(f"\n📍 STEP 2: Resolution Detection (forward search)")
            print("-" * 70)

        resolutions = self.resolution_detector.detect_resolutions_batch(
            seeds,
            transcript_segments,
            verbose=self.verbose
        )

        self.metrics['resolutions_found'] = sum(1 for r in resolutions if r is not None)

        # Step 3: Construct ThoughtUnit instances
        if self.verbose:
            print(f"\n📍 STEP 3: ThoughtUnit Construction")
            print("-" * 70)

        for idx, (seed, premise, resolution) in enumerate(zip(seeds, premises, resolutions), 1):
            self.metrics['seeds_processed'] += 1

            # Check if we have all components
            if premise is None:
                if self.verbose:
                    print(f"      [{idx}/{len(seeds)}] Skipping seed at {seed['timestamp']:.1f}s - no premise")
                self.metrics['construction_failures'] += 1
                continue

            if resolution is None:
                if self.verbose:
                    print(f"      [{idx}/{len(seeds)}] Skipping seed at {seed['timestamp']:.1f}s - no resolution")
                self.metrics['construction_failures'] += 1
                continue

            # Construct ThoughtUnit
            try:
                thought_unit = self._construct_unit(seed, premise, resolution)

                if thought_unit:
                    thought_units.append(thought_unit)
                    self.metrics['thought_units_constructed'] += 1

                    if thought_unit.is_complete():
                        self.metrics['thought_units_complete'] += 1

                    if self.verbose:
                        complete_str = "✓ COMPLETE" if thought_unit.is_complete() else "⚠ INCOMPLETE"
                        print(f"      [{idx}/{len(seeds)}] {complete_str}: {thought_unit.duration:.1f}s | {thought_unit.rhetorical_type.value}")
                else:
                    if self.verbose:
                        print(f"      [{idx}/{len(seeds)}] Failed to construct unit from seed at {seed['timestamp']:.1f}s")
                    self.metrics['construction_failures'] += 1

            except Exception as e:
                if self.verbose:
                    print(f"      [{idx}/{len(seeds)}] Error constructing unit: {e}")
                self.metrics['construction_failures'] += 1
                continue

        # Calculate total cost
        self.metrics['total_cost_usd'] = (
            self.premise_detector.metrics['cost_usd'] +
            self.resolution_detector.metrics['cost_usd']
        )

        if self.verbose:
            print("\n" + "=" * 70)
            print(f"✅ CONSTRUCTION COMPLETE")
            print("=" * 70)
            print(f"Seeds processed: {self.metrics['seeds_processed']}")
            print(f"Premises found: {self.metrics['premises_found']} ({self.metrics['premises_found']/len(seeds)*100:.0f}%)")
            print(f"Resolutions found: {self.metrics['resolutions_found']} ({self.metrics['resolutions_found']/len(seeds)*100:.0f}%)")
            print(f"ThoughtUnits constructed: {self.metrics['thought_units_constructed']}")
            print(f"Complete thoughts: {self.metrics['thought_units_complete']} ({self.metrics['thought_units_complete']/self.metrics['thought_units_constructed']*100:.0f}% if self.metrics['thought_units_constructed'] else 0)")
            print(f"Construction failures: {self.metrics['construction_failures']}")
            print(f"Total cost: ${self.metrics['total_cost_usd']:.3f}")

        return thought_units

    def _construct_unit(
        self,
        seed: Dict,
        premise: Dict,
        resolution: Dict
    ) -> Optional[ThoughtUnit]:
        """
        Construct a single ThoughtUnit from components.

        Args:
            seed: Seed dict
            premise: Premise dict
            resolution: Resolution dict

        Returns:
            ThoughtUnit instance or None if construction fails
        """
        try:
            # Map rhetorical type string to enum
            rhetorical_type_str = seed.get('rhetorical_type', 'insight')
            rhetorical_type = self._map_rhetorical_type(rhetorical_type_str)

            # Determine dependency level (will be validated later in Week 3)
            # For now, assume standalone if resolution is marked complete
            dependency_level = (
                DependencyLevel.STANDALONE
                if resolution.get('is_complete', False)
                else DependencyLevel.NEEDS_CONTEXT
            )

            # Create ThoughtUnit
            thought_unit = ThoughtUnit(
                premise_start=premise['premise_start'],
                claim_peak=seed['timestamp'],
                resolution_end=resolution['resolution_end'],
                premise_text=premise['premise_text'],
                claim_text=seed['text'],
                resolution_text=resolution['resolution_text'],
                rhetorical_type=rhetorical_type,
                dependency_level=dependency_level,
                completeness_score=0.0,  # Will be calculated by validator in Week 3
                premise_clarity=0.0,     # Will be scored in Week 3
                claim_strength=seed.get('interest_score', 0.0) * 10,  # Convert 0-1 to 0-10
                resolution_closure=resolution.get('confidence', 0.0) * 10,  # Convert 0-1 to 0-10
                has_unresolved_refs=False,  # Will be validated in Week 3
                confidence=min(premise.get('confidence', 0.5), resolution.get('confidence', 0.5)),
                seed_id=seed.get('seed_id', ''),
                _detection_metadata={
                    'premise_type': premise.get('premise_type', 'unknown'),
                    'premise_sentences_back': premise.get('sentences_back', 0),
                    'resolution_type': resolution.get('completion_type', 'unknown'),
                    'resolution_sentences_forward': resolution.get('sentences_forward', 0),
                    'seed_rhetorical_type': rhetorical_type_str,
                    'seed_reasoning': seed.get('reasoning', '')
                }
            )

            # Calculate preliminary completeness score
            thought_unit.completeness_score = thought_unit.calculate_completeness_score()

            return thought_unit

        except Exception as e:
            if self.verbose:
                print(f"      ⚠️  Error in unit construction: {e}")
            return None

    def _map_rhetorical_type(self, type_str: str) -> RhetoricalType:
        """
        Map seed rhetorical type string to ThoughtUnit.RhetoricalType enum.

        Args:
            type_str: String like 'argument', 'teaching', 'advice', etc.

        Returns:
            RhetoricalType enum value
        """
        mapping = {
            'argument': RhetoricalType.ARGUMENT,
            'teaching': RhetoricalType.TEACHING,
            'story': RhetoricalType.STORY,
            'advice': RhetoricalType.EXAMPLE,  # Map advice to example
            'qa': RhetoricalType.QUESTION_ANSWER,
            'question': RhetoricalType.QUESTION_ANSWER,
            'comparison': RhetoricalType.COMPARISON,
            'insight': RhetoricalType.INSIGHT,
        }

        return mapping.get(type_str.lower(), RhetoricalType.INSIGHT)
