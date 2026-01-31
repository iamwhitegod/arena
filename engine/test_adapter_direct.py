#!/usr/bin/env python3
"""
Direct test of the new FourLayerAdapter with ThoughtUnit system
"""

import sys
import os
import json

# Add to path
sys.path.insert(0, '.')

from arena.editorial import FourLayerAdapter

# Load test_007 transcript
transcript_paths = [
    '/Users/whitegodkingsley/Desktop/arena/test_007/HOW TO CHOOSE A LIFE PARTNER  PASTOR DOLAPO LAWAL - RELATIONSHIP AND MARRIAGE HUB (480p, h264, youtube)_transcript.json',
    '/Users/whitegodkingsley/Desktop/Reserved Area/Projects/arena/test_007/transcript.json'
]

transcript_file = None
for path in transcript_paths:
    if os.path.exists(path):
        transcript_file = path
        break

if not transcript_file:
    print("❌ Transcript not found")
    sys.exit(1)

with open(transcript_file, 'r') as f:
    transcript_data = json.load(f)

print(f"✓ Loaded transcript: {transcript_data.get('duration', 0):.1f}s\n")

# Get API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ OPENAI_API_KEY not set")
    sys.exit(1)

# Create adapter
adapter = FourLayerAdapter(
    api_key=api_key,
    model='gpt-4o-mini',
    export_layers=True
)

# Run analysis
print("Running ThoughtUnit editorial analysis...")
print("="*70)

clips = adapter.analyze_transcript(
    transcript_data,
    target_clips=3,
    min_duration=30,
    max_duration=90
)

print("\n" + "="*70)
print(f"✓ Generated {len(clips)} clips!")
print("="*70)

# Show clips
for i, clip in enumerate(clips, 1):
    print(f"\n{i}. {clip['title']}")
    print(f"   Duration: {clip['duration']:.1f}s ({clip['start_time']:.1f}s - {clip['end_time']:.1f}s)")
    print(f"   Type: {clip['content_type']}")
    if '_4layer_metadata' in clip:
        meta = clip['_4layer_metadata']
        print(f"   Completeness: {meta['completeness_score']:.2f}")
        print(f"   Standalone: {meta['standalone_score']:.2f}")
        print(f"   Claim: {meta['claim_text'][:80]}...")

print("\n✅ Test complete!")
