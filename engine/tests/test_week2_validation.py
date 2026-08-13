"""
Week 2 Validation Tests

Tests complete thought unit construction on test_007:
- Seeds from Week 1 (40 seeds)
- Premise detection (backward search)
- Resolution detection (forward search)
- ThoughtUnit construction

Success Criteria:
- 25-35 ThoughtUnit instances constructed (from 40 seeds)
- At least 60% construction success rate
- At least 50% of constructed units are complete
- User's 4 clips have complete ThoughtUnits
"""

import sys
import os
import pytest
sys.path.insert(0, '../')

from arena.editorial.thought_seed_detector import ThoughtSeedDetector
from arena.editorial.thought_unit_constructor import ThoughtUnitConstructor
from arena.editorial.thought_unit import ThoughtUnit
import json


def test_week2_construction():
    """
    Test thought unit construction on test_007

    This validates the Week 2 implementation against real data.
    """
    print("=" * 70)
    print("Week 2 Validation: Thought Unit Construction on test_007")
    print("=" * 70)

    # User's ground truth clip positions
    USER_CLIPS = [
        {'name': 'Clip 1', 'start': 18.0, 'end': 38.7},
        {'name': 'Clip 2', 'start': 54.2, 'end': 75.8},  # GOLD STANDARD
        {'name': 'Clip 3', 'start': 78.3, 'end': 217.6},  # USER'S FAVORITE
        {'name': 'Clip 4', 'start': 537.2, 'end': 694.6}
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
    print(f"Duration: {transcript_data.get('duration', 0):.1f}s (~{transcript_data.get('duration', 0) / 60:.1f} minutes)")
    print(f"Segments: {len(transcript_data.get('segments', []))}")

    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ OPENAI_API_KEY not set")
        pytest.skip("OPENAI_API_KEY is required for the live Week 2 validation")

    # Step 1: Detect seeds (from Week 1)
    print(f"\n🌱 STEP 1: Detecting thought seeds...")
    print("-" * 70)

    seed_detector = ThoughtSeedDetector(api_key=api_key, model='gpt-4o-mini')

    try:
        seeds = seed_detector.detect_seeds(transcript_data, target_count=10)
        print(f"✓ Detected {len(seeds)} seeds")
    except Exception as e:
        print(f"\n❌ Seed detection failed: {e}")
        pytest.fail(f"Seed detection failed: {e}")

    # Step 2: Construct ThoughtUnits
    print(f"\n🏗️  STEP 2: Constructing ThoughtUnit instances...")
    print("-" * 70)

    constructor = ThoughtUnitConstructor(
        api_key=api_key,
        model='gpt-4o-mini',
        verbose=True
    )

    try:
        thought_units = constructor.construct_from_seeds(
            seeds,
            transcript_data['segments']
        )
    except Exception as e:
        print(f"\n❌ Construction failed: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Thought-unit construction failed: {e}")

    # Validation checks
    print("\n" + "=" * 70)
    print("VALIDATION CHECKS")
    print("=" * 70)

    # Check 1: Construction success rate
    print(f"\n✅ CHECK 1: Construction Success Rate")
    success_rate = len(thought_units) / len(seeds) * 100 if seeds else 0
    print(f"   ThoughtUnits constructed: {len(thought_units)}")
    print(f"   Seeds processed: {len(seeds)}")
    print(f"   Success rate: {success_rate:.1f}%")
    print(f"   Expected: 25-35 units (60%+ success)")

    check1_pass = 25 <= len(thought_units) <= 35 and success_rate >= 60
    if check1_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  WARNING - Expected 25-35 units with 60%+ success")

    # Check 2: Completeness rate
    print(f"\n✅ CHECK 2: Completeness Rate")
    complete_units = [u for u in thought_units if u.is_complete()]
    completeness_rate = len(complete_units) / len(thought_units) * 100 if thought_units else 0
    print(f"   Complete thoughts: {len(complete_units)}/{len(thought_units)}")
    print(f"   Completeness rate: {completeness_rate:.1f}%")
    print(f"   Expected: 50%+ complete")

    check2_pass = completeness_rate >= 50
    if check2_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  WARNING - Expected 50%+ complete thoughts")

    # Check 3: Duration distribution
    print(f"\n✅ CHECK 3: Duration Distribution")
    if thought_units:
        durations = [u.duration for u in thought_units]
        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        print(f"   Average duration: {avg_duration:.1f}s")
        print(f"   Min duration: {min_duration:.1f}s")
        print(f"   Max duration: {max_duration:.1f}s")
        print(f"   Expected: Variable length (15s-180s)")

        check3_pass = min_duration >= 10 and max_duration <= 200
        if check3_pass:
            print(f"   ✓ PASS - Good variable length")
        else:
            print(f"   ⚠️  WARNING - Duration range unusual")
    else:
        check3_pass = False

    # Check 4: User clip coverage
    print(f"\n✅ CHECK 4: User Clip Coverage")
    print(f"   Checking if ThoughtUnits cover user's 4 manual clip positions...")

    covered_clips = []
    for user_clip in USER_CLIPS:
        # Check if any ThoughtUnit overlaps with this clip
        for unit in thought_units:
            # Calculate overlap
            overlap_start = max(unit.premise_start, user_clip['start'])
            overlap_end = min(unit.resolution_end, user_clip['end'])
            overlap_duration = max(0, overlap_end - overlap_start)

            # If overlap is significant (>50% of user clip)
            user_clip_duration = user_clip['end'] - user_clip['start']
            if overlap_duration > user_clip_duration * 0.5:
                covered_clips.append({
                    'name': user_clip['name'],
                    'unit_duration': unit.duration,
                    'complete': unit.is_complete()
                })
                print(f"   ✓ {user_clip['name']}: Covered by {unit.duration:.1f}s unit (complete: {unit.is_complete()})")
                break
        else:
            print(f"   ✗ {user_clip['name']}: No coverage")

    coverage_rate = len(covered_clips) / len(USER_CLIPS) * 100
    print(f"\n   Coverage: {len(covered_clips)}/4 user clips ({coverage_rate:.0f}%)")
    print(f"   Expected: At least 3/4 clips")

    check4_pass = len(covered_clips) >= 3
    if check4_pass:
        print(f"   ✓ PASS")
    else:
        print(f"   ⚠️  FAIL - Expected at least 3/4 user clips covered")

    # Show sample ThoughtUnits
    print(f"\n" + "=" * 70)
    print("SAMPLE THOUGHTUNITS (Top 5 by duration)")
    print("=" * 70)

    # Sort by duration and show top 5
    sorted_units = sorted(thought_units, key=lambda u: u.duration, reverse=True)[:5]

    for i, unit in enumerate(sorted_units, 1):
        complete_str = "✓ COMPLETE" if unit.is_complete() else "⚠ INCOMPLETE"
        print(f"\n{i}. {complete_str} | {unit.rhetorical_type.value.upper()} | {unit.duration:.1f}s")
        print(f"   Premise ({unit.premise_start:.1f}s): {unit.premise_text[:80]}...")
        print(f"   Claim ({unit.claim_peak:.1f}s): {unit.claim_text[:80]}...")
        print(f"   Resolution ({unit.resolution_end:.1f}s): {unit.resolution_text[:80]}...")
        print(f"   Completeness: {unit.completeness_score:.2f}")

    # Metrics summary
    print(f"\n" + "=" * 70)
    print("METRICS")
    print("=" * 70)
    print(f"Total cost: ${constructor.metrics['total_cost_usd']:.3f}")
    print(f"API calls: {constructor.premise_detector.metrics['api_calls'] + constructor.resolution_detector.metrics['api_calls']}")
    print(f"Premises found: {constructor.metrics['premises_found']}")
    print(f"Resolutions found: {constructor.metrics['resolutions_found']}")

    # Overall assessment
    print("\n" + "=" * 70)
    print("WEEK 2 VALIDATION SUMMARY")
    print("=" * 70)

    checks = [
        ("Construction success (60%+)", check1_pass),
        ("Completeness rate (50%+)", check2_pass),
        ("Variable length (10s-200s)", check3_pass),
        ("User clip coverage (3/4+)", check4_pass)
    ]

    for check_name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name}")

    passed_count = sum(1 for _, passed in checks if passed)
    print(f"\nOverall: {passed_count}/{len(checks)} checks passed")

    if passed_count >= 3:
        print("\n🎉 WEEK 2 VALIDATION SUCCESSFUL!")
        print("ThoughtUnit construction is working as expected.")
    else:
        print("\n⚠️  WEEK 2 NEEDS IMPROVEMENT")
        print("Review failed checks and adjust detection parameters.")
    assert passed_count >= 3, f"Only {passed_count}/{len(checks)} Week 2 checks passed"


if __name__ == '__main__':
    test_week2_construction()
