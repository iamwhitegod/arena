#!/usr/bin/env python3
"""
Week 7 Cross-Content Analysis

Compares results from religious, financial, and tech content tests
to verify system consistency across domains.
"""

import json
import sys
from pathlib import Path

print("="*70)
print("WEEK 7 CROSS-CONTENT ANALYSIS")
print("="*70)
print()

# Load results from all three content types
results_dir = Path('/Users/whitegodkingsley/Desktop/arena')

# Test 007: Religious content (baseline)
religious_file = results_dir / 'test_007_e2e_v2' / 'analysis_results.json'

# Week 7 tests
financial_file = Path('test_week7_finance_results.json')
tech_file = Path('test_week7_tech_results.json')

results = {}

# Load religious results (baseline)
if religious_file.exists():
    with open(religious_file, 'r') as f:
        religious_data = json.load(f)

    # Calculate avg completeness from thought units
    if 'thought_units' in religious_data:
        completeness_scores = [
            tu.get('completeness_score', 0)
            for tu in religious_data['thought_units']
            if tu.get('is_production_quality', False)
        ]
        avg_completeness = sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0

        results['religious'] = {
            'avg_completeness': avg_completeness,
            'production_units': len(completeness_scores),
            'total_units': len(religious_data.get('thought_units', [])),
            'production_pct': len(completeness_scores) / len(religious_data.get('thought_units', [])) * 100 if religious_data.get('thought_units') else 0
        }
        print(f"✓ Loaded religious content results (test_007)")
    else:
        print(f"⚠️  Religious results missing thought_units data")
else:
    print(f"⚠️  Religious results not found: {religious_file}")

# Load financial results
if financial_file.exists():
    with open(financial_file, 'r') as f:
        financial_data = json.load(f)

    results['financial'] = financial_data.get('validation', {})
    print(f"✓ Loaded financial content results")
else:
    print(f"❌ Financial results not found: {financial_file}")
    print(f"   Run: python3 test_week7_finance.py")

# Load tech results
if tech_file.exists():
    with open(tech_file, 'r') as f:
        tech_data = json.load(f)

    results['tech'] = tech_data.get('validation', {})
    print(f"✓ Loaded tech content results")
else:
    print(f"❌ Tech results not found: {tech_file}")
    print(f"   Run: python3 test_week7_tech.py")

print()

if len(results) < 2:
    print("❌ Need at least 2 content types to compare")
    print("   Run test_week7_finance.py and/or test_week7_tech.py first")
    sys.exit(1)

# Cross-content comparison
print("="*70)
print("COMPLETENESS SCORE COMPARISON")
print("="*70)
print()

completeness_scores = {}
for content_type, data in results.items():
    score = data.get('avg_completeness', 0)
    completeness_scores[content_type] = score
    print(f"{content_type.capitalize():12s}: {score:.2f}")

print()

# Calculate variance
if completeness_scores:
    avg = sum(completeness_scores.values()) / len(completeness_scores)
    variance = max(abs(score - avg) for score in completeness_scores.values())

    print(f"Average: {avg:.2f}")
    print(f"Max variance from avg: {variance:.2f}")
    print()

    if variance < 0.15:
        print("✅ PASS: Completeness scores are consistent (variance < 0.15)")
    elif variance < 0.20:
        print("⚠️  BORDERLINE: Variance within acceptable range (< 0.20)")
    else:
        print("❌ FAIL: High variance detected (≥ 0.20) - system may be biased")

print()
print("="*70)
print("CONTENT-AWARE VALIDATION CHECK")
print("="*70)
print()

# Check for domain-specific term detection
for content_type, data in results.items():
    if content_type == 'religious':
        continue

    terms = data.get(f'{content_type}_terms_detected', [])
    print(f"{content_type.capitalize()} terms detected: {len(terms)}")
    if terms:
        print(f"  Examples: {', '.join(terms[:5])}")

    if len(terms) >= 5:
        print(f"  ✅ Content-aware validation working for {content_type}")
    else:
        print(f"  ⚠️  May need to enhance {content_type} term recognition")
    print()

# Standalone validation comparison (if available)
print("="*70)
print("STANDALONE VALIDATION COMPARISON")
print("="*70)
print()

standalone_scores = {}
for content_type, data in results.items():
    score = data.get('avg_standalone', None)
    if score is not None:
        standalone_scores[content_type] = score
        print(f"{content_type.capitalize():12s}: {score:.2f}")

if standalone_scores:
    print()
    avg_standalone = sum(standalone_scores.values()) / len(standalone_scores)
    print(f"Average: {avg_standalone:.2f}")

    if avg_standalone >= 0.7:
        print("✅ Strong standalone performance across domains")
    elif avg_standalone >= 0.5:
        print("⚠️  Moderate standalone performance - ARSC may need tuning")
    else:
        print("❌ Weak standalone performance - content-aware rules need work")
else:
    print("(No standalone data available)")

print()
print("="*70)
print("WEEK 7 VALIDATION SUMMARY")
print("="*70)
print()

# Final verdict
issues = []
warnings = []

# Check completeness variance
if completeness_scores:
    avg_completeness = sum(completeness_scores.values()) / len(completeness_scores)
    variance = max(abs(score - avg_completeness) for score in completeness_scores.values())

    if variance >= 0.20:
        issues.append(f"High completeness variance ({variance:.2f})")
    elif variance >= 0.15:
        warnings.append(f"Moderate completeness variance ({variance:.2f})")

# Check content-aware validation
for content_type, data in results.items():
    if content_type == 'religious':
        continue
    terms = data.get(f'{content_type}_terms_detected', [])
    if len(terms) < 5:
        warnings.append(f"{content_type.capitalize()} term detection may be weak ({len(terms)} terms)")

# Check standalone scores
if standalone_scores:
    avg_standalone = sum(standalone_scores.values()) / len(standalone_scores)
    if avg_standalone < 0.5:
        issues.append(f"Low standalone scores ({avg_standalone:.2f})")
    elif avg_standalone < 0.7:
        warnings.append(f"Moderate standalone scores ({avg_standalone:.2f})")

# Print summary
if not issues and not warnings:
    print("✅ WEEK 7 VALIDATION: PASSED")
    print()
    print("System demonstrates:")
    print("  ✓ Consistent completeness scoring across domains")
    print("  ✓ Content-aware validation working")
    print("  ✓ Production-ready for multi-domain content")
    print()
    print("→ Ready to proceed to Week 8: Production Polish")
elif issues:
    print("❌ WEEK 7 VALIDATION: FAILED")
    print()
    print("Issues found:")
    for issue in issues:
        print(f"  ❌ {issue}")
    print()
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    print()
    print("→ Address issues before proceeding to Week 8")
else:
    print("⚠️  WEEK 7 VALIDATION: PASSED WITH WARNINGS")
    print()
    print("Warnings:")
    for warning in warnings:
        print(f"  ⚠️  {warning}")
    print()
    print("System is functional but may benefit from tuning.")
    print("→ Can proceed to Week 8, but monitor these areas")

print()
print("="*70)

# Save analysis
analysis_output = {
    'week7_status': 'passed' if not issues else 'failed',
    'completeness_scores': completeness_scores,
    'completeness_variance': variance if completeness_scores else None,
    'standalone_scores': standalone_scores,
    'issues': issues,
    'warnings': warnings,
    'content_types_tested': list(results.keys())
}

with open('test_week7_analysis.json', 'w') as f:
    json.dump(analysis_output, f, indent=2)

print(f"✓ Analysis saved: test_week7_analysis.json")
