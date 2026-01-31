#!/usr/bin/env python3
"""
Test temporal overlap detection in semantic deduplicator
"""

import sys
sys.path.insert(0, '.')

from arena.editorial.thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel
from arena.editorial.semantic_deduplicator import SemanticDeduplicator

# Create mock ThoughtUnits with overlapping time ranges
# These match the clips from test_007_e2e_v2 that were duplicates:
# Clip 1: 00:08 → 01:28 (79.6s)
# Clip 2: 00:00 → 01:28 (88.1s)

unit1 = ThoughtUnit(
    premise_start=8.0,
    claim_peak=45.0,  # Middle of the clip
    resolution_end=88.0,  # 1:28 in seconds
    premise_text="Nobody should be forced into marriage. Amen.",
    claim_text="The anxiety of being single is nothing compared to the regret of being in the wrong marriage.",
    resolution_text="It's right before you. Many single people want to get married...",
    rhetorical_type=RhetoricalType.INSIGHT,
    dependency_level=DependencyLevel.STANDALONE,
    has_unresolved_refs=False
)

unit2 = ThoughtUnit(
    premise_start=0.0,
    claim_peak=44.0,  # Middle of the clip
    resolution_end=88.0,  # 1:28 in seconds
    premise_text="God did not force anyone to accept him even though he wants everyone to be his wife...",
    claim_text="There is not one place where God picked a wife for someone.",
    resolution_text="You have to wake up. And a lot of people say, I believe...",
    rhetorical_type=RhetoricalType.ARGUMENT,
    dependency_level=DependencyLevel.STANDALONE,
    has_unresolved_refs=False
)

# Create deduplicator (don't need API key for overlap calculation)
deduplicator = SemanticDeduplicator(api_key="dummy")

# Calculate overlap ratio
overlap_ratio = deduplicator._calculate_overlap_ratio(unit1, unit2)

print("="*70)
print("TEMPORAL OVERLAP TEST")
print("="*70)
print()
print(f"Unit 1: {unit1.premise_start:.1f}s → {unit1.resolution_end:.1f}s ({unit1.duration:.1f}s)")
print(f"  Claim: {unit1.claim_text[:60]}...")
print()
print(f"Unit 2: {unit2.premise_start:.1f}s → {unit2.resolution_end:.1f}s ({unit2.duration:.1f}s)")
print(f"  Claim: {unit2.claim_text[:60]}...")
print()
print(f"Overlap ratio: {overlap_ratio:.2%}")
print()

# Check if they would be clustered together with 50% threshold
threshold = 0.5
if overlap_ratio >= threshold:
    print(f"✅ PASS: Units would be clustered together (overlap {overlap_ratio:.2%} >= threshold {threshold:.0%})")
    print("   These overlapping clips would be deduplicated!")
else:
    print(f"❌ FAIL: Units would NOT be clustered (overlap {overlap_ratio:.2%} < threshold {threshold:.0%})")

print()
print("="*70)
print("OVERLAP CALCULATION BREAKDOWN")
print("="*70)
print(f"Unit 1 range: {unit1.premise_start:.1f}s - {unit1.resolution_end:.1f}s")
print(f"Unit 2 range: {unit2.premise_start:.1f}s - {unit2.resolution_end:.1f}s")
print()
overlap_start = max(unit1.premise_start, unit2.premise_start)
overlap_end = min(unit1.resolution_end, unit2.resolution_end)
overlap_duration = max(0, overlap_end - overlap_start)
shorter_duration = min(unit1.duration, unit2.duration)
print(f"Overlap start: {overlap_start:.1f}s (max of both starts)")
print(f"Overlap end: {overlap_end:.1f}s (min of both ends)")
print(f"Overlap duration: {overlap_duration:.1f}s")
print(f"Shorter unit duration: {shorter_duration:.1f}s")
print(f"Ratio: {overlap_duration:.1f}s / {shorter_duration:.1f}s = {overlap_ratio:.2%}")
print()

# Test another case: non-overlapping units
unit3 = ThoughtUnit(
    premise_start=200.0,
    claim_peak=230.0,
    resolution_end=260.0,
    premise_text="Test premise",
    claim_text="Test claim",
    resolution_text="Test resolution",
    rhetorical_type=RhetoricalType.TEACHING,
    dependency_level=DependencyLevel.STANDALONE,
    has_unresolved_refs=False
)

overlap_ratio_2 = deduplicator._calculate_overlap_ratio(unit1, unit3)
print(f"Non-overlapping test (Unit 1 vs Unit 3): {overlap_ratio_2:.2%}")
if overlap_ratio_2 < 0.1:
    print("✅ PASS: Non-overlapping units correctly identified")
else:
    print(f"❌ FAIL: Expected near-zero overlap, got {overlap_ratio_2:.2%}")
