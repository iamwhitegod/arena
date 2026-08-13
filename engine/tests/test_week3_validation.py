"""
Week 3 Validation Tests

Tests completeness validation and scoring on test_007:
- ThoughtUnits from Week 2 (34 complete units)
- Standalone context validation
- Completeness scoring (premise, claim, resolution)
- Filtering to production quality (0.85+)

Success Criteria:
- 80%+ pass standalone validation
- Average completeness score 0.70+
- At least 15-25 units meet production standard (0.85+)
- User's 3 covered clips meet production standard
"""

import sys
import os
import pytest
sys.path.insert(0, '../')

from arena.editorial.thought_seed_detector import ThoughtSeedDetector
from arena.editorial.thought_unit_constructor import ThoughtUnitConstructor
from arena.editorial.standalone_validator import StandaloneValidator
from arena.editorial.completeness_scorer import CompletenessScorer
import json


def test_week3_validation():
    """
    Test completeness validation on test_007

    This validates the Week 3 implementation against real data.
    """
    print("=" * 70)
    print("Week 3 Validation: Completeness Validation on test_007")
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
        pytest.skip("OPENAI_API_KEY is required for the live Week 3 validation")

    # Step 1: Get ThoughtUnits from Week 2 pipeline
    print(f"\n🏗️  STEP 1: Constructing ThoughtUnits (Week 1+2 pipeline)...")
    print("-" * 70)

    seed_detector = ThoughtSeedDetector(api_key=api_key, model='gpt-4o-mini')
    seeds = seed_detector.detect_seeds(transcript_data, target_count=10)

    constructor = ThoughtUnitConstructor(api_key=api_key, model='gpt-4o-mini', verbose=False)
    thought_units = constructor.construct_from_seeds(seeds, transcript_data['segments'])

    print(f"✓ {len(thought_units)} ThoughtUnits constructed")

    # Step 2: Standalone validation
    print(f"\n📍 STEP 2: Standalone Context Validation")
    print("-" * 70)

    standalone_validator = StandaloneValidator(api_key=api_key, model='gpt-4o-mini')
    validations = standalone_validator.validate_batch(thought_units, verbose=True)

    # Update ThoughtUnits with validation results
    thought_units = standalone_validator.update_thought_units(thought_units, validations)

    # Step 3: Completeness scoring
    print(f"\n📍 STEP 3: Completeness Scoring")
    print("-" * 70)

    completeness_scorer = CompletenessScorer(api_key=api_key, model='gpt-4o-mini')
    scores = completeness_scorer.score_batch(thought_units, verbose=True)

    # Update ThoughtUnits with scores
    thought_units = completeness_scorer.update_thought_units(thought_units, scores)

    # Step 4: Filter to production quality
    print(f"\n📍 STEP 4: Filtering to Production Quality")
    print("-" * 70)

    production_units = [
        unit for unit in thought_units
        if unit.meets_production_standard()
    ]

    print(f"✓ {len(production_units)} ThoughtUnits meet production standard (0.85+)")

    # Validation checks
    print("\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)

    # Check 1: Standalone validation rate
    print(f"\n✅ CHECK 1: Standalone Validation Rate")
    standalone_units = [u for u in thought_units if u.dependency_level.value == 'standalone']
    standalone_rate = len(standalone_units) / len(thought_units) * 100 if thought_units else 0
    print(f"   Standalone units: {len(standalone_units)}/{len(thought_units)}")
    print(f"   Standalone rate: {standalone_rate:.1f}%")
    print(f"   Expected: 80%+ standalone")

    check1_pass = standalone_rate >= 80
    if check1_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  WARNING - Expected 80%+ standalone")

    # Check 2: Average completeness score
    print(f"\n✅ CHECK 2: Average Completeness Score")
    if thought_units:
        avg_completeness = sum(u.completeness_score for u in thought_units) / len(thought_units)
        avg_premise = sum(u.premise_clarity for u in thought_units) / len(thought_units)
        avg_claim = sum(u.claim_strength for u in thought_units) / len(thought_units)
        avg_resolution = sum(u.resolution_closure for u in thought_units) / len(thought_units)

        print(f"   Average completeness: {avg_completeness:.2f}")
        print(f"   Average premise: {avg_premise:.1f}/10")
        print(f"   Average claim: {avg_claim:.1f}/10")
        print(f"   Average resolution: {avg_resolution:.1f}/10")
        print(f"   Expected: 0.70+ completeness")

        check2_pass = avg_completeness >= 0.70
        if check2_pass:
            print(f"   ✓ PASS")
        else:
            print(f"   ⚠️  WARNING - Expected 0.70+ average")
    else:
        check2_pass = False
        avg_completeness = 0

    # Check 3: Production quality count
    print(f"\n✅ CHECK 3: Production Quality Count")
    production_count = len(production_units)
    production_rate = production_count / len(thought_units) * 100 if thought_units else 0

    print(f"   Production units: {production_count}")
    print(f"   Total units: {len(thought_units)}")
    print(f"   Production rate: {production_rate:.1f}%")
    print(f"   Expected: 15-25 units (40-70%)")

    check3_pass = 15 <= production_count <= 25 and production_rate >= 40
    if check3_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  WARNING - Expected 15-25 production units")

    # Check 4: User clips quality
    print(f"\n✅ CHECK 4: User Clips Quality")
    print(f"   Checking if user's 3 covered clips meet production standard...")

    user_clip_quality = []
    for user_clip in USER_CLIPS:
        # Find ThoughtUnit covering this clip
        for unit in production_units:
            overlap_start = max(unit.premise_start, user_clip['start'])
            overlap_end = min(unit.resolution_end, user_clip['end'])
            overlap_duration = max(0, overlap_end - overlap_start)

            user_clip_duration = user_clip['end'] - user_clip['start']
            if overlap_duration > user_clip_duration * 0.5:
                user_clip_quality.append({
                    'name': user_clip['name'],
                    'completeness': unit.completeness_score,
                    'production': unit.meets_production_standard()
                })
                print(f"   ✓ {user_clip['name']}: Production quality (score: {unit.completeness_score:.2f})")
                break
        else:
            # Check in non-production units
            for unit in thought_units:
                if unit in production_units:
                    continue
                overlap_start = max(unit.premise_start, user_clip['start'])
                overlap_end = min(unit.resolution_end, user_clip['end'])
                overlap_duration = max(0, overlap_end - overlap_start)

                user_clip_duration = user_clip['end'] - user_clip['start']
                if overlap_duration > user_clip_duration * 0.5:
                    print(f"   ⚠️  {user_clip['name']}: Below production (score: {unit.completeness_score:.2f})")
                    break
            else:
                print(f"   ✗ {user_clip['name']}: No coverage")

    production_clips = sum(1 for c in user_clip_quality if c['production'])
    print(f"\n   User clips at production quality: {production_clips}/3")
    print(f"   Expected: At least 2/3")

    check4_pass = production_clips >= 2
    if check4_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  FAIL - Expected at least 2/3 user clips at production")

    # Show top production units
    print(f"\n" + "=" * 70)
    print("TOP 5 PRODUCTION UNITS (by completeness score)")
    print("=" * 70)

    sorted_production = sorted(production_units, key=lambda u: u.completeness_score, reverse=True)[:5]

    for i, unit in enumerate(sorted_production, 1):
        print(f"\n{i}. {unit.rhetorical_type.value.upper()} | {unit.duration:.1f}s | Score: {unit.completeness_score:.2f}")
        print(f"   Premise ({unit.premise_clarity:.1f}/10): {unit.premise_text[:60]}...")
        print(f"   Claim ({unit.claim_strength:.1f}/10): {unit.claim_text[:60]}...")
        print(f"   Resolution ({unit.resolution_closure:.1f}/10): {unit.resolution_text[:60]}...")

    # Metrics summary
    print(f"\n" + "=" * 70)
    print("METRICS")
    print("=" * 70)
    total_cost = (
        seed_detector.metrics['cost_usd'] +
        constructor.metrics['total_cost_usd'] +
        standalone_validator.metrics['cost_usd'] +
        completeness_scorer.metrics['cost_usd']
    )
    print(f"Total cost: ${total_cost:.3f}")
    print(f"  Seed detection: ${seed_detector.metrics['cost_usd']:.3f}")
    print(f"  Construction: ${constructor.metrics['total_cost_usd']:.3f}")
    print(f"  Standalone validation: ${standalone_validator.metrics['cost_usd']:.3f}")
    print(f"  Completeness scoring: ${completeness_scorer.metrics['cost_usd']:.3f}")

    # Overall assessment
    print("\n" + "=" * 70)
    print("WEEK 3 VALIDATION SUMMARY")
    print("=" * 70)

    checks = [
        ("Standalone rate (80%+)", check1_pass),
        ("Avg completeness (0.70+)", check2_pass),
        ("Production count (15-25)", check3_pass),
        ("User clips quality (2/3+)", check4_pass)
    ]

    for check_name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name}")

    passed_count = sum(1 for _, passed in checks if passed)
    print(f"\nOverall: {passed_count}/{len(checks)} checks passed")

    if passed_count >= 3:
        print("\n🎉 WEEK 3 VALIDATION SUCCESSFUL!")
        print("Completeness validation is working as expected.")
    else:
        print("\n⚠️  WEEK 3 NEEDS IMPROVEMENT")
        print("Review failed checks and adjust scoring/validation.")
    assert passed_count >= 3, f"Only {passed_count}/{len(checks)} Week 3 checks passed"


if __name__ == '__main__':
    test_week3_validation()
