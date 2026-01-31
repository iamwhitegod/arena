"""
Demo: Thought Seed Detection

Quick demo of the new ThoughtSeedDetector with sliding window approach.
Run this to test seed detection on a small sample.
"""

import os
import sys
from arena.editorial.thought_seed_detector import ThoughtSeedDetector


def demo_seed_detection():
    """Demo seed detection with sample transcript"""

    print("=" * 70)
    print("ThoughtSeedDetector Demo")
    print("=" * 70)

    # Sample transcript (simplified version of test_007 clip 2)
    sample_transcript = {
        'segments': [
            {'start': 50.0, 'end': 54.0, 'text': 'Let me tell you something about marriage.'},
            {'start': 54.0, 'end': 59.0, 'text': 'I believe, I personally believe that God can tell you who to marry.'},
            {'start': 59.0, 'end': 63.0, 'text': 'The reason why I believe it is because a lot of people said so.'},
            {'start': 63.0, 'end': 67.0, 'text': 'I cannot judge your walk with God.'},
            {'start': 67.0, 'end': 72.0, 'text': 'But what I have seen in the Bible is that there is not one place'},
            {'start': 72.0, 'end': 76.0, 'text': 'where God picked a wife for someone.'},
            {'start': 76.0, 'end': 78.0, 'text': 'Not one place.'},
        ],
        'duration': 78.0
    }

    print(f"\n📝 Sample Transcript:")
    print(f"Duration: {sample_transcript['duration']}s")
    print(f"Segments: {len(sample_transcript['segments'])}")
    print()

    # Show transcript
    for seg in sample_transcript['segments']:
        print(f"[{seg['start']:.1f}s] {seg['text']}")

    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("\n❌ OPENAI_API_KEY not set")
        print("Set it with: export OPENAI_API_KEY='sk-...'")
        print("\nSkipping API call. To run full demo, set your API key.")
        return

    # Initialize detector
    print("\n🔍 Initializing ThoughtSeedDetector...")
    detector = ThoughtSeedDetector(api_key=api_key, model='gpt-4o-mini')

    # Detect seeds (target 2 clips → detect 8 seeds)
    print("\n🌱 Detecting thought seeds...")
    print("-" * 70)

    try:
        seeds = detector.detect_seeds(sample_transcript, target_count=2)

        print("-" * 70)
        print(f"\n✅ Detected {len(seeds)} seeds")

        # Show results
        print("\n🌟 DETECTED SEEDS:")
        print("-" * 70)

        for i, seed in enumerate(seeds, 1):
            print(f"\nSeed {i}: {seed['seed_id']}")
            print(f"  Timestamp: {seed['timestamp']:.1f}s")
            print(f"  Type: {seed['rhetorical_type']}")
            print(f"  Interest: {seed['interest_score']:.2f}")
            print(f"  Text: {seed['text']}")
            print(f"  Reasoning: {seed['reasoning']}")
            print(f"  Has Premise: {seed['likely_has_premise']}")
            print(f"  Has Resolution: {seed['likely_has_resolution']}")

        # Show metrics
        print("\n" + "=" * 70)
        print("📊 METRICS")
        print("=" * 70)
        print(f"API calls: {detector.metrics['api_calls']}")
        print(f"Tokens used: {detector.metrics['tokens_used']:,}")
        print(f"Cost: ${detector.metrics['cost_usd']:.4f}")
        print(f"Windows analyzed: {detector.metrics['windows_analyzed']}")

        print("\n✨ Demo complete!")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    demo_seed_detection()
