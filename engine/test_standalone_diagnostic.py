#!/usr/bin/env python3
"""
Diagnostic test for standalone validation
Check what issues GPT is finding in religious content
"""

import sys
import os
sys.path.insert(0, '.')

from arena.editorial.thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel
from arena.editorial.standalone_validator import StandaloneValidator

# Get API key
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("❌ OPENAI_API_KEY not set")
    sys.exit(1)

# Create a test ThoughtUnit with biblical references
# This should be STANDALONE according to our content-aware rules
unit = ThoughtUnit(
    premise_start=0.0,
    claim_peak=44.0,
    resolution_end=88.0,
    premise_text="God did not force anyone to accept him even though he wants everyone to be his wife through the church. Nobody should be forced into marriage. Amen.",
    claim_text="The anxiety of being single is nothing compared to the regret of being in the wrong marriage.",
    resolution_text="Many single people want to get married. Many married people want to be single. You are wishing for what people don't like. You have to wake up. And a lot of people say, I believe God can tell you who to marry. But what I've seen in the Bible is that there is not one place where God picked a wife for someone.",
    rhetorical_type=RhetoricalType.ARGUMENT,
    dependency_level=DependencyLevel.STANDALONE,
    has_unresolved_refs=False
)

print("="*70)
print("STANDALONE VALIDATION DIAGNOSTIC")
print("="*70)
print()
print("📝 Testing clip with biblical references:")
print(f"   Premise: {unit.premise_text[:80]}...")
print(f"   Claim: {unit.claim_text[:80]}...")
print(f"   Resolution: {unit.resolution_text[:80]}...")
print()

# Validate
validator = StandaloneValidator(api_key=api_key, model='gpt-4o-mini')
result = validator.validate(unit)

print("🔍 VALIDATION RESULTS:")
print("="*70)
print(f"Is Standalone: {result['is_standalone']}")
print(f"Standalone Score: {result['standalone_score']:.2f}")
print(f"Dependency Level: {result['dependency_level'].value}")
print(f"Confidence: {result['confidence']:.2f}")
print()

if result['issues']:
    print("❌ Issues Found:")
    for i, issue in enumerate(result['issues'], 1):
        print(f"   {i}. {issue}")
    print()

if result['unresolved_refs']:
    print("⚠️  Unresolved References:")
    for ref in result['unresolved_refs']:
        print(f"   - {ref}")
    print()

print("💭 Reasoning:")
print(f"   {result['reasoning']}")
print()

print("="*70)
print("ANALYSIS")
print("="*70)

# Check if score is correct according to our rules
expected_score = 0.9  # Should be 0.9+ for biblical references with our content-aware rules
if result['standalone_score'] >= 0.7:
    print("✅ PASS: Score 0.7+ (counts as standalone)")
elif result['standalone_score'] >= 0.5:
    print("⚠️  BORDERLINE: Score 0.5-0.7 (counts as needs_context)")
    print("   Expected: 0.7+ for biblical references")
    print("   Issue: GPT may not be following content-aware rules")
else:
    print("❌ FAIL: Score <0.5 (severe issues)")
    print("   Expected: 0.7+ for biblical references")
    print("   Issue: Content-aware rules not working")

print()

# Check specific content-aware rules
if result['unresolved_refs']:
    biblical_refs = ['God', 'Bible', 'Jesus', 'Holy Spirit']
    flagged_biblical = [ref for ref in result['unresolved_refs'] if any(b.lower() in ref.lower() for b in biblical_refs)]

    if flagged_biblical:
        print("🚨 CRITICAL ISSUE:")
        print(f"   GPT flagged biblical references as unresolved: {flagged_biblical}")
        print("   Content-aware rules are NOT being followed!")
    else:
        print("✓ No biblical references flagged (good)")
else:
    print("✓ No unresolved references detected")

print()
print("="*70)
