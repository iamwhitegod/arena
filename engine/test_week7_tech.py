#!/usr/bin/env python3
"""
Week 7 Validation: Test ThoughtUnit system on tech/career content
"""

import sys
import os
import json
from pathlib import Path

# Add to path
sys.path.insert(0, '.')

from arena.editorial import FourLayerAdapter

# Find tech content video (test_004)
test_004_base = Path('/Users/whitegodkingsley/Desktop/arena/test_004')

# Look for transcript in cache
cache_dir = test_004_base / '.cache'
transcript_file = None

if cache_dir.exists():
    transcripts = list(cache_dir.glob('*_transcript.json'))
    if transcripts:
        transcript_file = transcripts[0]

if not transcript_file or not transcript_file.exists():
    print(f"❌ Transcript not found in: {cache_dir}")
    print(f"   Run transcription first or use full pipeline")
    sys.exit(1)

with open(transcript_file, 'r') as f:
    transcript_data = json.load(f)

duration = transcript_data.get('duration', 0)
print(f"✓ Loaded transcript: {duration:.1f}s ({duration/60:.1f} minutes)")
print(f"  Content: Tech/Career Advice")
print()

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
print("Running ThoughtUnit editorial analysis on TECH content...")
print("="*70)

clips = adapter.analyze_transcript(
    transcript_data,
    target_clips=5,
    min_duration=30,
    max_duration=90
)

print("\n" + "="*70)
print(f"✓ Generated {len(clips)} clips from TECH content!")
print("="*70)

# Analyze results
print("\n📊 WEEK 7 VALIDATION: Tech Content")
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

# Check for content-aware validation
print("\n" + "="*70)
print("CONTENT-AWARE VALIDATION CHECK")
print("="*70)

tech_terms = ['tech', 'engineer', 'software', 'code', 'build', 'learn',
              'website', 'app', 'skills', 'career', 'developer', 'programming']

claims_text = ' '.join([
    clip['_4layer_metadata']['claim_text'].lower()
    for clip in clips
    if '_4layer_metadata' in clip
])

found_terms = [term for term in tech_terms if term in claims_text]
print(f"Tech terms detected: {len(found_terms)}/{len(tech_terms)}")
print(f"Examples: {', '.join(found_terms[:5])}")

if len(found_terms) >= 5:
    print("✓ System correctly identifies tech content")
else:
    print("⚠️  May not be detecting tech concepts well")

# Compare with test_007 (religious content)
print("\n" + "="*70)
print("COMPARISON: Religious vs Tech Content")
print("="*70)

avg_completeness_tech = sum(
    clip['_4layer_metadata']['completeness_score']
    for clip in clips
    if '_4layer_metadata' in clip
) / len(clips) if clips else 0

print(f"Religious content (test_007): avg completeness 0.74")
print(f"Tech content (test_004): avg completeness {avg_completeness_tech:.2f}")
print()

if abs(avg_completeness_tech - 0.74) < 0.15:
    print("✓ System performs consistently across content types")
else:
    print("⚠️  Significant performance difference between content types")

# Check standalone validation (should recognize tech terms)
if clips and '_4layer_metadata' in clips[0]:
    standalone_scores = [
        clip['_4layer_metadata']['standalone_score']
        for clip in clips
        if '_4layer_metadata' in clip
    ]
    avg_standalone = sum(standalone_scores) / len(standalone_scores) if standalone_scores else 0

    print(f"\nStandalone Validation:")
    print(f"  Avg standalone score: {avg_standalone:.2f}")

    if avg_standalone >= 0.7:
        print("  ✓ Content-aware validation working (recognizes tech context)")
    elif avg_standalone >= 0.5:
        print("  ⚠️  Borderline - may need to enhance tech term recognition")
    else:
        print("  ❌ Content-aware validation failing for tech terms")

# Save results
output_file = '/Users/whitegodkingsley/Desktop/arena/test_week7_tech_results.json'
with open(output_file, 'w') as f:
    json.dump({
        'clips': clips,
        'validation': {
            'content_type': 'tech/career_advice',
            'avg_completeness': avg_completeness_tech,
            'avg_standalone': avg_standalone if clips else 0,
            'tech_terms_detected': found_terms,
            'comparison_to_religious': {
                'religious_avg': 0.74,
                'tech_avg': avg_completeness_tech,
                'difference': abs(avg_completeness_tech - 0.74)
            }
        }
    }, f, indent=2)

print(f"\n✓ Results saved: {output_file}")
print("\n✅ Week 7 tech content validation complete!")
