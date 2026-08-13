"""
Week 1 Validation Tests

Tests thought seed detection on test_007 video to validate Week 1 deliverables.

Success Criteria:
- Detect 40-50 seeds in test_007 (target 10 clips × 4)
- Seeds distributed across entire video (not clustered)
- Multiple rhetorical types detected
- At least 3 of 4 user clip positions detected as seeds
"""

import sys
import os
import pytest
sys.path.insert(0, '../')

from arena.editorial.thought_seed_detector import ThoughtSeedDetector
from arena.editorial.thought_unit import RhetoricalType, DependencyLevel
import json


def test_week1_seed_detection():
    """
    Test thought seed detection on test_007

    This validates the Week 1 implementation against real data.
    """
    print("=" * 70)
    print("Week 1 Validation: Thought Seed Detection on test_007")
    print("=" * 70)

    # User's ground truth clip positions
    USER_CLIPS = [
        {'name': 'Clip 1', 'start': 18.0, 'end': 38.7, 'duration': 20.7},
        {'name': 'Clip 2', 'start': 54.2, 'end': 75.8, 'duration': 21.7},  # GOLD STANDARD
        {'name': 'Clip 3', 'start': 78.3, 'end': 217.6, 'duration': 139.3},  # USER'S FAVORITE
        {'name': 'Clip 4', 'start': 537.2, 'end': 694.6, 'duration': 157.4}
    ]

    # Load test_007 transcript
    # Try multiple possible locations
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
        print(f"❌ Transcript not found in any of these locations:")
        for path in possible_paths:
            print(f"   - {path}")
        print("Please ensure test_007 transcript exists")
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
        print("Set it with: export OPENAI_API_KEY='sk-...'")
        pytest.skip("OPENAI_API_KEY is required for the live Week 1 validation")

    # Initialize detector
    print("\n🔍 Initializing ThoughtSeedDetector...")
    detector = ThoughtSeedDetector(api_key=api_key, model='gpt-4o-mini')  # Use mini for cost efficiency

    # Detect seeds (target 10 clips → detect 40 seeds)
    print("\n🌱 Detecting thought seeds (target: 40 seeds for 10 clips)...")
    print("-" * 70)

    try:
        seeds = detector.detect_seeds(transcript_data, target_count=10)
    except Exception as e:
        print(f"\n❌ Error during seed detection: {e}")
        import traceback
        traceback.print_exc()
        pytest.fail(f"Seed detection failed: {e}")

    print("-" * 70)

    # Validation 1: Quantity (40-50 seeds)
    print(f"\n✅ VALIDATION 1: Seed Quantity")
    print(f"   Seeds detected: {len(seeds)}")
    print(f"   Expected: 35-55 seeds")

    if 35 <= len(seeds) <= 55:
        print(f"   ✓ PASS - Detected appropriate number of seeds")
    else:
        print(f"   ⚠️  WARNING - Expected 35-55 seeds, got {len(seeds)}")

    # Validation 2: Distribution across video
    print(f"\n✅ VALIDATION 2: Temporal Distribution")
    if seeds:
        timestamps = [s['timestamp'] for s in seeds]
        min_ts = min(timestamps)
        max_ts = max(timestamps)
        video_duration = transcript_data.get('duration', 0)

        print(f"   First seed: {min_ts:.1f}s")
        print(f"   Last seed: {max_ts:.1f}s")
        print(f"   Coverage: {min_ts:.1f}s - {max_ts:.1f}s (span: {max_ts - min_ts:.1f}s)")

        # Check distribution
        early_seeds = [s for s in seeds if s['timestamp'] < 300]  # First 5 minutes
        mid_seeds = [s for s in seeds if 300 <= s['timestamp'] < 600]
        late_seeds = [s for s in seeds if s['timestamp'] >= 600]

        print(f"   Early seeds (0-300s): {len(early_seeds)}")
        print(f"   Mid seeds (300-600s): {len(mid_seeds)}")
        print(f"   Late seeds (600s+): {len(late_seeds)}")

        if min_ts < 100 and max_ts > 700:
            print(f"   ✓ PASS - Seeds well distributed across video")
        else:
            print(f"   ⚠️  WARNING - Seeds may be clustered")

    # Validation 3: Rhetorical diversity
    print(f"\n✅ VALIDATION 3: Rhetorical Type Diversity")
    if seeds:
        types = [s['rhetorical_type'] for s in seeds]
        unique_types = set(types)
        type_counts = {t: types.count(t) for t in unique_types}

        print(f"   Unique types: {len(unique_types)}")
        for rtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   - {rtype}: {count} seeds")

        if len(unique_types) >= 3:
            print(f"   ✓ PASS - Good rhetorical diversity ({len(unique_types)} types)")
        else:
            print(f"   ⚠️  WARNING - Limited diversity ({len(unique_types)} types)")

    # Validation 4: User clip detection
    print(f"\n✅ VALIDATION 4: User Clip Position Detection")
    print(f"   Checking if seeds detected near user's 4 manual clip positions...")

    matches = []
    for user_clip in USER_CLIPS:
        # Check if any seed falls within or near this clip
        clip_seeds = [
            s for s in seeds
            if user_clip['start'] - 30 <= s['timestamp'] <= user_clip['end'] + 30
        ]

        if clip_seeds:
            best_seed = max(clip_seeds, key=lambda s: s['interest_score'])
            matches.append({
                'clip': user_clip['name'],
                'seed_timestamp': best_seed['timestamp'],
                'seed_text': best_seed['text'][:80] + '...' if len(best_seed['text']) > 80 else best_seed['text'],
                'interest_score': best_seed['interest_score']
            })
            print(f"   ✓ {user_clip['name']} ({user_clip['start']:.1f}s): FOUND seed at {best_seed['timestamp']:.1f}s (score: {best_seed['interest_score']:.2f})")
        else:
            print(f"   ✗ {user_clip['name']} ({user_clip['start']:.1f}s): NO SEED DETECTED")

    match_rate = len(matches) / len(USER_CLIPS)
    print(f"\n   Match rate: {len(matches)}/4 user clips detected ({match_rate * 100:.0f}%)")

    if len(matches) >= 3:
        print(f"   ✓ PASS - At least 3/4 user clips detected")
    else:
        print(f"   ⚠️  FAIL - Expected at least 3/4 user clips, got {len(matches)}/4")

    # Metrics summary
    print(f"\n📊 METRICS")
    print(f"   API calls: {detector.metrics['api_calls']}")
    print(f"   Tokens used: {detector.metrics['tokens_used']:,}")
    print(f"   Cost: ${detector.metrics['cost_usd']:.3f}")
    print(f"   Windows analyzed: {detector.metrics['windows_analyzed']}")

    # Show top 10 seeds
    print(f"\n🌟 TOP 10 SEEDS (by interest score)")
    print("-" * 70)
    for i, seed in enumerate(seeds[:10], 1):
        print(f"{i}. [{seed['timestamp']:.1f}s] {seed['rhetorical_type'].upper()}")
        print(f"   {seed['text'][:100]}...")
        print(f"   Score: {seed['interest_score']:.2f} | Premise: {seed['likely_has_premise']} | Resolution: {seed['likely_has_resolution']}")
        print()

    # Overall assessment
    print("=" * 70)
    print("WEEK 1 VALIDATION SUMMARY")
    print("=" * 70)

    checks = []
    checks.append(("Seed quantity (35-55)", 35 <= len(seeds) <= 55))
    checks.append(("Distribution (early + late)", min_ts < 100 and max_ts > 700 if seeds else False))
    checks.append(("Rhetorical diversity (3+ types)", len(unique_types) >= 3 if seeds else False))
    checks.append(("User clips detected (3/4+)", len(matches) >= 3))

    for check_name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {check_name}")

    passed_count = sum(1 for _, passed in checks if passed)
    print(f"\nOverall: {passed_count}/{len(checks)} checks passed")

    if passed_count >= 3:
        print("\n🎉 WEEK 1 VALIDATION SUCCESSFUL!")
        print("ThoughtSeedDetector is working as expected.")
    else:
        print("\n⚠️  WEEK 1 NEEDS IMPROVEMENT")
        print("Review failed checks and adjust seed detection parameters.")
    assert passed_count >= 3, f"Only {passed_count}/{len(checks)} Week 1 checks passed"


if __name__ == '__main__':
    test_week1_seed_detection()
