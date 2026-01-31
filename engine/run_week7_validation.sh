#!/bin/bash
#
# Week 7 Multi-Video Validation - Master Test Runner
#
# Executes all Week 7 validation tests in sequence and generates
# comprehensive cross-content analysis report.
#
# Requirements:
#   - OPENAI_API_KEY must be set
#   - test_002 transcript must exist (financial content)
#   - test_004 transcript must exist (tech content)
#
# Usage:
#   export OPENAI_API_KEY="sk-..."
#   ./run_week7_validation.sh
#

set -e  # Exit on error

echo "========================================================================"
echo "WEEK 7: MULTI-VIDEO VALIDATION"
echo "========================================================================"
echo ""

# Check API key
if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ ERROR: OPENAI_API_KEY not set"
    echo ""
    echo "Please set your OpenAI API key:"
    echo "  export OPENAI_API_KEY=\"sk-...\""
    echo ""
    exit 1
fi

echo "✓ OpenAI API key detected"
echo ""

# Change to engine directory
cd "$(dirname "$0")"

echo "========================================================================"
echo "TEST 1: FINANCIAL CONTENT (2h15min video)"
echo "========================================================================"
echo ""

echo "Running financial content test..."
python3 test_week7_finance.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Financial content test PASSED"
else
    echo ""
    echo "❌ Financial content test FAILED"
    exit 1
fi

echo ""
echo "========================================================================"
echo "TEST 2: TECH CONTENT (~5min video)"
echo "========================================================================"
echo ""

echo "Running tech content test..."
python3 test_week7_tech.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Tech content test PASSED"
else
    echo ""
    echo "❌ Tech content test FAILED (may be missing transcript)"
    echo "   Continuing with analysis using available data..."
fi

echo ""
echo "========================================================================"
echo "CROSS-CONTENT ANALYSIS"
echo "========================================================================"
echo ""

echo "Analyzing results across all content types..."
python3 test_week7_analysis.py

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Cross-content analysis complete"
else
    echo ""
    echo "⚠️  Analysis completed with warnings"
fi

echo ""
echo "========================================================================"
echo "WEEK 7 VALIDATION COMPLETE"
echo "========================================================================"
echo ""

# Show results
echo "📊 Results files:"
echo "  - test_week7_finance_results.json (financial content)"
echo "  - test_week7_tech_results.json (tech content)"
echo "  - test_week7_analysis.json (cross-content comparison)"
echo ""

# Quick summary
if [ -f "test_week7_analysis.json" ]; then
    echo "📈 Quick Summary:"
    python3 -c "
import json
with open('test_week7_analysis.json', 'r') as f:
    data = json.load(f)
    status = data.get('week7_status', 'unknown')
    completeness = data.get('completeness_scores', {})
    variance = data.get('completeness_variance', 0)

    print(f'  Status: {status.upper()}')
    print(f'  Completeness scores:')
    for content_type, score in completeness.items():
        print(f'    - {content_type}: {score:.2f}')
    if variance is not None:
        print(f'  Max variance: {variance:.2f}')

    issues = data.get('issues', [])
    warnings = data.get('warnings', [])

    if issues:
        print(f'  Issues: {len(issues)}')
    if warnings:
        print(f'  Warnings: {len(warnings)}')
"
fi

echo ""

# Check status and provide next steps
if [ -f "test_week7_analysis.json" ]; then
    STATUS=$(python3 -c "import json; data = json.load(open('test_week7_analysis.json')); print(data.get('week7_status', 'unknown'))")

    if [ "$STATUS" = "passed" ]; then
        echo "🎉 Week 7 validation PASSED!"
        echo ""
        echo "Next steps:"
        echo "  1. Review detailed results in JSON files"
        echo "  2. Update WEEK7_VALIDATION_REPORT.md with findings"
        echo "  3. Proceed to Week 8: Production Polish"
        echo ""
    else
        echo "⚠️  Week 7 validation completed with issues"
        echo ""
        echo "Next steps:"
        echo "  1. Review test_week7_analysis.json for details"
        echo "  2. Address identified issues"
        echo "  3. Re-run validation"
        echo ""
    fi
fi

echo "========================================================================"
