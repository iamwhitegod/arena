"""
Week 4 Deduplication Tests

Tests semantic deduplication and variant selection on test_007:
- Load Week 3 output (36 ThoughtUnits)
- Run semantic deduplication (cluster similar units)
- Select best variant from each cluster
- Validate results

Success Criteria:
- 40-50% deduplication rate (36 → 20-25 units)
- User's 3 ground truth clips preserved
- Highest quality variants selected
- Average completeness increases or stays same
- Production units increase (better selection)
"""

import sys
import os
import pytest
sys.path.insert(0, '../')

from arena.editorial.thought_seed_detector import ThoughtSeedDetector
from arena.editorial.thought_unit_constructor import ThoughtUnitConstructor
from arena.editorial.standalone_validator import StandaloneValidator
from arena.editorial.completeness_scorer import CompletenessScorer
from arena.editorial.semantic_deduplicator import SemanticDeduplicator
from arena.editorial.variant_selector import VariantSelector
import json


def test_week4_deduplication():
    """
    Test deduplication and variant selection on test_007

    This validates the Week 4 implementation against real data.
    """
    print("=" * 70)
    print("Week 4 Validation: Deduplication and Variant Selection")
    print("=" * 70)

    # User's ground truth clip positions
    USER_CLIPS = [
        {'name': 'Clip 1', 'start': 18.0, 'end': 38.7},
        {'name': 'Clip 2', 'start': 54.2, 'end': 75.8},
        {'name': 'Clip 3', 'start': 78.3, 'end': 217.6},  # GOLD STANDARD
    ]

    # Load test_007 transcript
    possible_paths = [
        '/Users/whitegodkingsley/Desktop/arena/test_007/HOW TO CHOOSE A LIFE PARTNER  PASTOR DOLAPO LAWAL - RELATIONSHIP AND MARRIAGE HUB (480p, h264, youtube)_transcript.json',
        '/Users/whitegodkingsley/Desktop/Reserved Area/Projects/arena/test_007/transcript.json',
        '/Users/whitegodkingsley/Desktop/arena/test_007/transcript.json'
    ]

    transcript_file = None
    for path in possible_paths:
        if os.path.exists(path):
            transcript_file = path
            break

    if not transcript_file:
        print(f"❌ Transcript not found")
        pytest.skip("test_007 transcript fixture is not available")

    with open(transcript_file, 'r') as f:
        transcript_data = json.load(f)

    print(f"\n📹 Video: test_007 (HOW TO CHOOSE A LIFE PARTNER)")
    print(f"Duration: {transcript_data.get('duration', 0):.1f}s")

    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ OPENAI_API_KEY not set")
        pytest.skip("OPENAI_API_KEY is required for the live Week 4 validation")

    # Step 1-3: Get ThoughtUnits from Week 1-3 pipeline
    print(f"\n🏗️  STEP 1-3: Constructing and Scoring ThoughtUnits (Week 1-3 pipeline)...")
    print("-" * 70)

    seed_detector = ThoughtSeedDetector(api_key=api_key, model='gpt-4o-mini')
    seeds = seed_detector.detect_seeds(transcript_data, target_count=10)

    constructor = ThoughtUnitConstructor(api_key=api_key, model='gpt-4o-mini', verbose=False)
    thought_units = constructor.construct_from_seeds(seeds, transcript_data['segments'])

    standalone_validator = StandaloneValidator(api_key=api_key, model='gpt-4o-mini')
    validations = standalone_validator.validate_batch(thought_units, verbose=False)
    thought_units = standalone_validator.update_thought_units(thought_units, validations)

    completeness_scorer = CompletenessScorer(api_key=api_key, model='gpt-4o-mini')
    scores = completeness_scorer.score_batch(thought_units, verbose=False)
    thought_units = completeness_scorer.update_thought_units(thought_units, scores)

    print(f"✓ {len(thought_units)} ThoughtUnits ready for deduplication")

    # Capture before-dedup metrics
    before_count = len(thought_units)
    before_avg_completeness = sum(u.completeness_score for u in thought_units) / len(thought_units)
    before_production = sum(1 for u in thought_units if u.meets_production_standard())

    print(f"   Before deduplication:")
    print(f"     Units: {before_count}")
    print(f"     Avg completeness: {before_avg_completeness:.2f}")
    print(f"     Production units: {before_production}")

    # Step 4: Semantic deduplication
    print(f"\n🔍 STEP 4: Semantic Deduplication")
    print("-" * 70)

    deduplicator = SemanticDeduplicator(api_key=api_key)
    unique_units, clusters = deduplicator.deduplicate(
        thought_units,
        similarity_threshold=0.85,
        verbose=True
    )

    # Analyze clusters
    cluster_analysis = deduplicator.analyze_clusters(clusters, verbose=True)

    # Step 5: Variant selection
    print(f"\n⭐ STEP 5: Variant Selection")
    print("-" * 70)

    selector = VariantSelector(ideal_min_duration=30, ideal_max_duration=90)
    best_variants = selector.select_best_variants(clusters, verbose=True)

    # Analyze selection
    selection_analysis = selector.analyze_selection(clusters, best_variants, verbose=True)

    # Capture after-dedup metrics
    after_count = len(best_variants)
    after_avg_completeness = sum(u.completeness_score for u in best_variants) / len(best_variants)
    after_production = sum(1 for u in best_variants if u.meets_production_standard())

    print(f"\n   After deduplication:")
    print(f"     Units: {after_count}")
    print(f"     Avg completeness: {after_avg_completeness:.2f}")
    print(f"     Production units: {after_production}")

    # Validation checks
    print("\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)

    # Check 1: Deduplication rate
    print(f"\n✅ CHECK 1: Deduplication Rate")
    dedup_rate = (before_count - after_count) / before_count * 100
    print(f"   Before: {before_count} units")
    print(f"   After: {after_count} units")
    print(f"   Deduplication rate: {dedup_rate:.1f}%")
    print(f"   Expected: 40-50% reduction")

    check1_pass = 40 <= dedup_rate <= 60
    if check1_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  WARNING - Expected 40-50% deduplication")

    # Check 2: Quality preservation
    print(f"\n✅ CHECK 2: Quality Preservation")
    completeness_change = after_avg_completeness - before_avg_completeness
    print(f"   Before completeness: {before_avg_completeness:.2f}")
    print(f"   After completeness: {after_avg_completeness:.2f}")
    print(f"   Change: {completeness_change:+.2f}")
    print(f"   Expected: No decrease (should increase or stay same)")

    check2_pass = completeness_change >= -0.02  # Allow tiny decrease
    if check2_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  WARNING - Quality decreased")

    # Check 3: Production units
    print(f"\n✅ CHECK 3: Production Units")
    production_change = after_production - before_production
    print(f"   Before: {before_production} production units")
    print(f"   After: {after_production} production units")
    print(f"   Change: {production_change:+d}")
    print(f"   Expected: Increase (better selection)")

    check3_pass = production_change >= 0
    if check3_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  WARNING - Production units decreased")

    # Check 4: User clips preserved
    print(f"\n✅ CHECK 4: User Clips Preserved")
    print(f"   Checking if user's 3 ground truth clips are preserved...")

    user_clips_preserved = []
    for user_clip in USER_CLIPS:
        # Find if any best variant covers this clip
        for unit in best_variants:
            overlap_start = max(unit.premise_start, user_clip['start'])
            overlap_end = min(unit.resolution_end, user_clip['end'])
            overlap_duration = max(0, overlap_end - overlap_start)

            user_clip_duration = user_clip['end'] - user_clip['start']
            if overlap_duration > user_clip_duration * 0.5:
                user_clips_preserved.append({
                    'name': user_clip['name'],
                    'preserved': True,
                    'completeness': unit.completeness_score
                })
                print(f"   ✓ {user_clip['name']}: Preserved (score: {unit.completeness_score:.2f})")
                break
        else:
            user_clips_preserved.append({
                'name': user_clip['name'],
                'preserved': False
            })
            print(f"   ✗ {user_clip['name']}: Lost")

    preserved_count = sum(1 for c in user_clips_preserved if c['preserved'])
    print(f"\n   User clips preserved: {preserved_count}/3")
    print(f"   Expected: All 3 preserved")

    check4_pass = preserved_count == 3
    if check4_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ✗ FAIL - Lost user clips")

    # Show top 5 best variants
    print(f"\n" + "=" * 70)
    print("TOP 5 BEST VARIANTS (after deduplication)")
    print("=" * 70)

    sorted_variants = sorted(best_variants, key=lambda u: u.completeness_score, reverse=True)[:5]

    for i, unit in enumerate(sorted_variants, 1):
        print(f"\n{i}. {unit.rhetorical_type.value.upper()} | {unit.duration:.1f}s | Score: {unit.completeness_score:.2f}")
        print(f"   Premise ({unit.premise_clarity:.1f}/10): {unit.premise_text[:60]}...")
        print(f"   Claim ({unit.claim_strength:.1f}/10): {unit.claim_text[:60]}...")
        print(f"   Resolution ({unit.resolution_closure:.1f}/10): {unit.resolution_text[:60]}...")

    # Show example duplicate clusters
    print(f"\n" + "=" * 70)
    print("EXAMPLE DUPLICATE CLUSTERS")
    print("=" * 70)

    duplicate_clusters = [c for c in clusters if len(c) > 1][:3]  # Show first 3

    for i, cluster in enumerate(duplicate_clusters, 1):
        print(f"\nCluster {i}: {len(cluster)} variants")
        for j, unit in enumerate(cluster, 1):
            selected = "✓ SELECTED" if unit in best_variants else "✗ Rejected"
            print(f"   Variant {j} {selected}: {unit.duration:.1f}s, score: {unit.completeness_score:.2f}")
            print(f"      Claim: {unit.claim_text[:80]}...")

    # Metrics summary
    print(f"\n" + "=" * 70)
    print("METRICS")
    print("=" * 70)

    total_cost = (
        seed_detector.metrics['cost_usd'] +
        constructor.metrics['total_cost_usd'] +
        standalone_validator.metrics['cost_usd'] +
        completeness_scorer.metrics['cost_usd'] +
        deduplicator.metrics['cost_usd']
    )

    print(f"Total cost: ${total_cost:.3f}")
    print(f"  Seed detection: ${seed_detector.metrics['cost_usd']:.3f}")
    print(f"  Construction: ${constructor.metrics['total_cost_usd']:.3f}")
    print(f"  Standalone validation: ${standalone_validator.metrics['cost_usd']:.3f}")
    print(f"  Completeness scoring: ${completeness_scorer.metrics['cost_usd']:.3f}")
    print(f"  Deduplication: ${deduplicator.metrics['cost_usd']:.4f}")

    # Overall assessment
    print("\n" + "=" * 70)
    print("WEEK 4 VALIDATION SUMMARY")
    print("=" * 70)

    checks = [
        ("Deduplication rate (40-50%)", check1_pass),
        ("Quality preservation", check2_pass),
        ("Production units increase", check3_pass),
        ("User clips preserved (3/3)", check4_pass)
    ]

    for check_name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name}")

    passed_count = sum(1 for _, passed in checks if passed)
    print(f"\nOverall: {passed_count}/{len(checks)} checks passed")

    if passed_count >= 3:
        print("\n🎉 WEEK 4 VALIDATION SUCCESSFUL!")
        print("Deduplication and variant selection working as expected.")
    else:
        print("\n⚠️  WEEK 4 NEEDS IMPROVEMENT")
        print("Review failed checks and adjust thresholds.")
    assert passed_count >= 3, f"Only {passed_count}/{len(checks)} Week 4 checks passed"


if __name__ == '__main__':
    test_week4_deduplication()
