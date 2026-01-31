"""
Demo: Thought Unit Construction

Quick demo of complete thought unit construction pipeline:
1. Seed detection
2. Premise detection (backward search)
3. Resolution detection (forward search)
4. ThoughtUnit construction
"""

import os
from arena.editorial.thought_seed_detector import ThoughtSeedDetector
from arena.editorial.thought_unit_constructor import ThoughtUnitConstructor


def demo_construction():
    """Demo complete thought unit construction"""

    print("=" * 70)
    print("ThoughtUnit Construction Demo")
    print("=" * 70)

    # Sample transcript (test_007 clip 2)
    sample_transcript = {
        'segments': [
            {'start': 50.0, 'end': 54.0, 'text': 'Let me tell you something about marriage.'},
            {'start': 54.0, 'end': 59.0, 'text': 'I believe, I personally believe that God can tell you who to marry.'},
            {'start': 59.0, 'end': 63.0, 'text': 'The reason why I believe it is because a lot of people said so.'},
            {'start': 63.0, 'end': 67.0, 'text': 'I cannot judge your walk with God.'},
            {'start': 67.0, 'end': 72.0, 'text': 'But what I have seen in the Bible is that there is not one place'},
            {'start': 72.0, 'end': 76.0, 'text': 'where God picked a wife for someone.'},
            {'start': 76.0, 'end': 78.0, 'text': 'Not one place.'},
            {'start': 78.0, 'end': 82.0, 'text': 'So that is my perspective on the matter.'},
        ],
        'duration': 82.0
    }

    print(f"\n📝 Sample Transcript: {len(sample_transcript['segments'])} segments")

    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ OPENAI_API_KEY not set")
        print("Skipping API call. Set your API key to run full demo.")
        return

    # Step 1: Detect seeds
    print(f"\n🌱 STEP 1: Detecting seeds...")
    print("-" * 70)

    seed_detector = ThoughtSeedDetector(api_key=api_key, model='gpt-4o-mini')

    try:
        seeds = seed_detector.detect_seeds(sample_transcript, target_count=2)
        print(f"✓ Detected {len(seeds)} seeds")

        for i, seed in enumerate(seeds, 1):
            print(f"\n  Seed {i}:")
            print(f"    Text: {seed['text']}")
            print(f"    Type: {seed['rhetorical_type']}")
            print(f"    Score: {seed['interest_score']:.2f}")

    except Exception as e:
        print(f"❌ Seed detection failed: {e}")
        return

    # Step 2: Construct ThoughtUnits
    print(f"\n🏗️  STEP 2: Constructing ThoughtUnits...")
    print("-" * 70)

    constructor = ThoughtUnitConstructor(
        api_key=api_key,
        model='gpt-4o-mini',
        verbose=True
    )

    try:
        thought_units = constructor.construct_from_seeds(
            seeds,
            sample_transcript['segments']
        )

        print(f"\n✅ Constructed {len(thought_units)} ThoughtUnit(s)")

        # Show results
        print(f"\n" + "=" * 70)
        print("CONSTRUCTED THOUGHTUNITS")
        print("=" * 70)

        for i, unit in enumerate(thought_units, 1):
            complete_str = "✓ COMPLETE" if unit.is_complete() else "⚠ INCOMPLETE"
            print(f"\nThoughtUnit {i}: {complete_str}")
            print(f"  Duration: {unit.duration:.1f}s ({unit.premise_start:.1f}s - {unit.resolution_end:.1f}s)")
            print(f"  Type: {unit.rhetorical_type.value}")
            print(f"  Dependency: {unit.dependency_level.value}")
            print(f"  Completeness: {unit.completeness_score:.2f}")
            print(f"\n  Premise: {unit.premise_text}")
            print(f"  Claim: {unit.claim_text}")
            print(f"  Resolution: {unit.resolution_text}")

        # Metrics
        print(f"\n" + "=" * 70)
        print("METRICS")
        print("=" * 70)
        print(f"Total cost: ${constructor.metrics['total_cost_usd']:.4f}")
        print(f"Premises found: {constructor.metrics['premises_found']}")
        print(f"Resolutions found: {constructor.metrics['resolutions_found']}")
        print(f"Construction success: {constructor.metrics['thought_units_constructed']}/{constructor.metrics['seeds_processed']}")

        print("\n✨ Demo complete!")

    except Exception as e:
        print(f"\n❌ Construction failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    demo_construction()
