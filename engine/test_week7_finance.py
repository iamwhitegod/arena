#!/usr/bin/env python3
"""
Week 7 Validation: Test ThoughtUnit system on financial content
"""

import sys
import os
import json

# Add to path
sys.path.insert(0, '.')

from arena.editorial import FourLayerAdapter

# Load financial video transcript (test_002)
transcript_file = '/Users/whitegodkingsley/Desktop/arena/test_002/.cache/Passive_Income_Expert-_Buying_A_House_Makes_You_Poorer_Than_Renting! Crypto Isn\'t A Smart Investment_transcript.json'

if not os.path.exists(transcript_file):
    print(f"❌ Transcript not found: {transcript_file}")
    sys.exit(1)

with open(transcript_file, 'r') as f:
    transcript_data = json.load(f)

print(f"✓ Loaded transcript: {transcript_data.get('duration', 0):.1f}s")
print(f"  Content: Financial/Passive Income (2+ hours)")
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
print("Running ThoughtUnit editorial analysis on FINANCIAL content...")
print("="*70)

clips = adapter.analyze_transcript(
    transcript_data,
    target_clips=5,
    min_duration=30,
    max_duration=90
)

print("\n" + "="*70)
print(f"✓ Generated {len(clips)} clips from FINANCIAL content!")
print("="*70)

# Analyze results
print("\n📊 WEEK 7 VALIDATION: Financial Content")
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

financial_terms = ['money', 'debt', 'invest', 'wealth', 'passive income',
                   'buy', 'rent', 'house', 'mortgage', 'financial']

claims_text = ' '.join([
    clip['_4layer_metadata']['claim_text'].lower()
    for clip in clips
    if '_4layer_metadata' in clip
])

found_terms = [term for term in financial_terms if term in claims_text]
print(f"Financial terms detected: {len(found_terms)}/{len(financial_terms)}")
print(f"Examples: {', '.join(found_terms[:5])}")

if len(found_terms) >= 5:
    print("✓ System correctly identifies financial content")
else:
    print("⚠️  May not be detecting financial concepts well")

# Compare with test_007 (religious content)
print("\n" + "="*70)
print("COMPARISON: Religious vs Financial Content")
print("="*70)

avg_completeness_finance = sum(
    clip['_4layer_metadata']['completeness_score']
    for clip in clips
    if '_4layer_metadata' in clip
) / len(clips)

print(f"Religious content (test_007): avg completeness 0.74")
print(f"Financial content (test_002): avg completeness {avg_completeness_finance:.2f}")
print()

if abs(avg_completeness_finance - 0.74) < 0.15:
    print("✓ System performs consistently across content types")
else:
    print("⚠️  Significant performance difference between content types")

# Save results
output_file = '/Users/whitegodkingsley/Desktop/arena/test_week7_finance_results.json'
with open(output_file, 'w') as f:
    json.dump({
        'clips': clips,
        'validation': {
            'content_type': 'financial/passive_income',
            'avg_completeness': avg_completeness_finance,
            'financial_terms_detected': found_terms,
            'comparison_to_religious': {
                'religious_avg': 0.74,
                'financial_avg': avg_completeness_finance,
                'difference': abs(avg_completeness_finance - 0.74)
            }
        }
    }, f, indent=2)

print(f"\n✓ Results saved: {output_file}")
print("\n✅ Week 7 validation complete!")
