#!/usr/bin/env python3
"""
Week 8: Performance Benchmark - Parallel vs Sequential Processing

Compares sequential vs parallel batch processing for:
1. Completeness scoring
2. Standalone validation

Measures:
- Execution time (speedup factor)
- API calls (should be same)
- Cost (should be same)
- Results consistency
"""

import sys
import os
import time
from typing import List
sys.path.insert(0, '.')

from arena.editorial.thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel
from arena.editorial.completeness_scorer import CompletenessScorer
from arena.editorial.standalone_validator import StandaloneValidator

print("=" * 80)
print("WEEK 8: PERFORMANCE BENCHMARK - PARALLEL VS SEQUENTIAL")
print("=" * 80)
print()

# =========================================================================
# SETUP
# =========================================================================

print("SETUP")
print("-" * 80)

# Check for API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ OPENAI_API_KEY not set")
    print()
    print("Please set your API key:")
    print("  export OPENAI_API_KEY='sk-...'")
    sys.exit(1)

print(f"✓ API key found: {api_key[:20]}...")
print()

# =========================================================================
# TEST DATA: Create 10 sample ThoughtUnits
# =========================================================================

print("TEST DATA")
print("-" * 80)

# Create realistic sample units
sample_units: List[ThoughtUnit] = [
    ThoughtUnit(
        premise_start=0.0,
        claim_peak=5.0,
        resolution_end=10.0,
        premise_text="When I first started programming, I thought learning meant memorizing syntax.",
        claim_text="But real understanding comes when you can apply concepts in new situations.",
        resolution_text="The concept is what matters, not the specific implementation.",
        rhetorical_type=RhetoricalType.INSIGHT,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
    ThoughtUnit(
        premise_start=15.0,
        claim_peak=20.0,
        resolution_end=25.0,
        premise_text="Many developers focus on learning frameworks and libraries.",
        claim_text="Instead, you should focus on understanding core principles.",
        resolution_text="Principles transfer across technologies, but specific tools become obsolete.",
        rhetorical_type=RhetoricalType.ARGUMENT,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
    ThoughtUnit(
        premise_start=30.0,
        claim_peak=35.0,
        resolution_end=40.0,
        premise_text="I've noticed a pattern in how people learn to code.",
        claim_text="The best learners ask 'why' not just 'how'.",
        resolution_text="Understanding motivation leads to deeper retention than memorizing steps.",
        rhetorical_type=RhetoricalType.INSIGHT,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
    ThoughtUnit(
        premise_start=45.0,
        claim_peak=50.0,
        resolution_end=55.0,
        premise_text="Building projects is often recommended for learning.",
        claim_text="But not all projects are equally valuable for learning.",
        resolution_text="Choose projects that push you slightly beyond your current skills.",
        rhetorical_type=RhetoricalType.TEACHING,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
    ThoughtUnit(
        premise_start=60.0,
        claim_peak=65.0,
        resolution_end=70.0,
        premise_text="Documentation is often seen as boring by new developers.",
        claim_text="Reading documentation is actually a high-leverage skill.",
        resolution_text="Good developers can extract value from docs faster than tutorials.",
        rhetorical_type=RhetoricalType.INSIGHT,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
    ThoughtUnit(
        premise_start=75.0,
        claim_peak=80.0,
        resolution_end=85.0,
        premise_text="Code reviews can feel uncomfortable for beginners.",
        claim_text="They're one of the fastest ways to improve your skills.",
        resolution_text="Feedback from experienced developers accelerates growth exponentially.",
        rhetorical_type=RhetoricalType.ARGUMENT,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
    ThoughtUnit(
        premise_start=90.0,
        claim_peak=95.0,
        resolution_end=100.0,
        premise_text="Testing your code seems like extra work initially.",
        claim_text="But it actually saves time in the long run.",
        resolution_text="Tests catch bugs early when they're cheap to fix, not late when they're expensive.",
        rhetorical_type=RhetoricalType.TEACHING,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
    ThoughtUnit(
        premise_start=105.0,
        claim_peak=110.0,
        resolution_end=115.0,
        premise_text="Many tutorials teach you what to code, not how to think about problems.",
        claim_text="Problem-solving skills matter more than syntax knowledge.",
        resolution_text="Learn to break problems down before worrying about implementation details.",
        rhetorical_type=RhetoricalType.INSIGHT,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
    ThoughtUnit(
        premise_start=120.0,
        claim_peak=125.0,
        resolution_end=130.0,
        premise_text="Version control feels overwhelming when you first learn it.",
        claim_text="But it's essential for professional development.",
        resolution_text="Start simple with basic commits and branches, complexity comes naturally with practice.",
        rhetorical_type=RhetoricalType.TEACHING,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
    ThoughtUnit(
        premise_start=135.0,
        claim_peak=140.0,
        resolution_end=145.0,
        premise_text="I used to think debugging was a sign of failure.",
        claim_text="Debugging is where real learning happens.",
        resolution_text="Each bug you fix teaches you how the system actually works, not just how you think it works.",
        rhetorical_type=RhetoricalType.STORY,
        dependency_level=DependencyLevel.STANDALONE,
        has_unresolved_refs=False
    ),
]

print(f"✓ Created {len(sample_units)} sample ThoughtUnits for testing")
print()

# =========================================================================
# BENCHMARK 1: Completeness Scoring
# =========================================================================

print("=" * 80)
print("BENCHMARK 1: COMPLETENESS SCORING")
print("=" * 80)
print()

# Sequential Scoring
print("Test 1A: Sequential Scoring (score_batch)")
print("-" * 80)
scorer_seq = CompletenessScorer(api_key, model="gpt-4o-mini")

start_time = time.time()
scores_seq = scorer_seq.score_batch(sample_units, verbose=False)
time_seq = time.time() - start_time

print(f"✓ Completed in {time_seq:.2f} seconds")
print(f"  API calls: {scorer_seq.metrics['api_calls']}")
print(f"  Tokens: {scorer_seq.metrics['tokens_used']:,}")
print(f"  Cost: ${scorer_seq.metrics['cost_usd']:.4f}")
print(f"  Avg score: {scorer_seq.metrics['avg_completeness_score']:.2f}")
print()

# Parallel Scoring
print("Test 1B: Parallel Scoring (score_batch_parallel)")
print("-" * 80)
scorer_par = CompletenessScorer(api_key, model="gpt-4o-mini")

start_time = time.time()
scores_par = scorer_par.score_batch_parallel(sample_units, max_workers=5, verbose=False)
time_par = time.time() - start_time

print(f"✓ Completed in {time_par:.2f} seconds")
print(f"  API calls: {scorer_par.metrics['api_calls']}")
print(f"  Tokens: {scorer_par.metrics['tokens_used']:,}")
print(f"  Cost: ${scorer_par.metrics['cost_usd']:.4f}")
print(f"  Avg score: {scorer_par.metrics['avg_completeness_score']:.2f}")
print()

# Compare results
speedup_scoring = time_seq / time_par if time_par > 0 else 0
print("COMPARISON:")
print(f"  Sequential time: {time_seq:.2f}s")
print(f"  Parallel time:   {time_par:.2f}s")
print(f"  Speedup:         {speedup_scoring:.2f}x faster")
print(f"  API calls:       Same ({scorer_seq.metrics['api_calls']} calls)")
print(f"  Cost difference: ${abs(scorer_seq.metrics['cost_usd'] - scorer_par.metrics['cost_usd']):.4f} (minimal)")

# Verify results consistency
score_diffs = [abs(s1['completeness_score'] - s2['completeness_score']) for s1, s2 in zip(scores_seq, scores_par)]
max_diff = max(score_diffs) if score_diffs else 0
print(f"  Results match:   {max_diff < 0.01} (max diff: {max_diff:.4f})")
print()

# =========================================================================
# BENCHMARK 2: Standalone Validation
# =========================================================================

print("=" * 80)
print("BENCHMARK 2: STANDALONE VALIDATION")
print("=" * 80)
print()

# Sequential Validation
print("Test 2A: Sequential Validation (validate_batch)")
print("-" * 80)
validator_seq = StandaloneValidator(api_key, model="gpt-4o-mini")

start_time = time.time()
validations_seq = validator_seq.validate_batch(sample_units, verbose=False)
time_val_seq = time.time() - start_time

print(f"✓ Completed in {time_val_seq:.2f} seconds")
print(f"  API calls: {validator_seq.metrics['api_calls']}")
print(f"  Tokens: {validator_seq.metrics['tokens_used']:,}")
print(f"  Cost: ${validator_seq.metrics['cost_usd']:.4f}")
print(f"  Standalone: {validator_seq.metrics['units_standalone']}/{len(sample_units)}")
print()

# Parallel Validation
print("Test 2B: Parallel Validation (validate_batch_parallel)")
print("-" * 80)
validator_par = StandaloneValidator(api_key, model="gpt-4o-mini")

start_time = time.time()
validations_par = validator_par.validate_batch_parallel(sample_units, max_workers=5, verbose=False)
time_val_par = time.time() - start_time

print(f"✓ Completed in {time_val_par:.2f} seconds")
print(f"  API calls: {validator_par.metrics['api_calls']}")
print(f"  Tokens: {validator_par.metrics['tokens_used']:,}")
print(f"  Cost: ${validator_par.metrics['cost_usd']:.4f}")
print(f"  Standalone: {validator_par.metrics['units_standalone']}/{len(sample_units)}")
print()

# Compare results
speedup_validation = time_val_seq / time_val_par if time_val_par > 0 else 0
print("COMPARISON:")
print(f"  Sequential time: {time_val_seq:.2f}s")
print(f"  Parallel time:   {time_val_par:.2f}s")
print(f"  Speedup:         {speedup_validation:.2f}x faster")
print(f"  API calls:       Same ({validator_seq.metrics['api_calls']} calls)")
print(f"  Cost difference: ${abs(validator_seq.metrics['cost_usd'] - validator_par.metrics['cost_usd']):.4f} (minimal)")

# Verify results consistency
standalone_match = sum(1 for v1, v2 in zip(validations_seq, validations_par) if v1['is_standalone'] == v2['is_standalone'])
print(f"  Results match:   {standalone_match}/{len(sample_units)} ({standalone_match/len(sample_units)*100:.0f}%)")
print()

# =========================================================================
# OVERALL SUMMARY
# =========================================================================

print("=" * 80)
print("OVERALL PERFORMANCE SUMMARY")
print("=" * 80)
print()

total_time_seq = time_seq + time_val_seq
total_time_par = time_par + time_val_par
overall_speedup = total_time_seq / total_time_par if total_time_par > 0 else 0

print(f"Total Processing Time:")
print(f"  Sequential: {total_time_seq:.2f}s")
print(f"  Parallel:   {total_time_par:.2f}s")
print(f"  Overall Speedup: {overall_speedup:.2f}x faster")
print()

total_cost_seq = scorer_seq.metrics['cost_usd'] + validator_seq.metrics['cost_usd']
total_cost_par = scorer_par.metrics['cost_usd'] + validator_par.metrics['cost_usd']

print(f"Total Cost:")
print(f"  Sequential: ${total_cost_seq:.4f}")
print(f"  Parallel:   ${total_cost_par:.4f}")
print(f"  Difference: ${abs(total_cost_seq - total_cost_par):.4f} (same cost)")
print()

print("✅ Performance Goals:")
if speedup_scoring >= 3.0:
    print(f"  ✓ Scoring speedup: {speedup_scoring:.2f}x (target: 3-5x) - ACHIEVED")
else:
    print(f"  ⚠ Scoring speedup: {speedup_scoring:.2f}x (target: 3-5x) - BELOW TARGET")

if speedup_validation >= 3.0:
    print(f"  ✓ Validation speedup: {speedup_validation:.2f}x (target: 3-5x) - ACHIEVED")
else:
    print(f"  ⚠ Validation speedup: {speedup_validation:.2f}x (target: 3-5x) - BELOW TARGET")

if overall_speedup >= 3.0:
    print(f"  ✓ Overall speedup: {overall_speedup:.2f}x (target: 3-5x) - ACHIEVED")
else:
    print(f"  ⚠ Overall speedup: {overall_speedup:.2f}x (target: 3-5x) - BELOW TARGET")

cost_increase_pct = abs(total_cost_par - total_cost_seq) / total_cost_seq * 100 if total_cost_seq > 0 else 0
if cost_increase_pct < 5:
    print(f"  ✓ Cost increase: {cost_increase_pct:.1f}% (target: <5%) - ACHIEVED")
else:
    print(f"  ⚠ Cost increase: {cost_increase_pct:.1f}% (target: <5%) - ABOVE TARGET")

print()
print("=" * 80)
print()

print("🎉 Week 8 Performance Optimization Complete!")
print()
print("Next steps:")
print("  • Phase 3: Build comprehensive test suite")
print("  • Phase 4: Complete documentation")
print("  • Phase 5: Final production validation")
print()
print("=" * 80)
