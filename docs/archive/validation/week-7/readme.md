# Week 7: Multi-Video Validation - Quick Start

## Current Status: ⏳ READY TO RUN (Waiting for API Key)

All preparation work is complete. Just needs `OPENAI_API_KEY` to execute tests.

---

## What's Been Done

✅ **Week 7 Validation Plan** (`WEEK7_VALIDATION_REPORT.md`)
- Complete test suites for financial, tech, and wealth content
- Success criteria and validation checklist
- Cross-content comparison framework

✅ **Expected Results Analysis** (`WEEK7_EXPECTED_RESULTS.md`)
- Predictions based on OLD system performance
- Content-type specific expectations
- Calibration guidelines

✅ **Test Script Ready** (`test_week7_finance.py`)
- Tests NEW ThoughtUnit system on 2h financial video
- Uses cached transcript (no re-transcription cost)
- Outputs comprehensive validation report

---

## Quick Start: Run Week 7 Validation

### Step 1: Set API Key
```bash
export OPENAI_API_KEY="sk-..."
```

### Step 2: Run Financial Content Test
```bash
cd /Users/whitegodkingsley/Desktop/Reserved\ Area/Projects/arena/engine
python3 test_week7_finance.py
```

**Expected Output**:
- 5-8 clips from 2h financial video
- Avg completeness: 0.60-0.75
- Cost: ~$0.61
- Runtime: ~8-12 minutes
- Results saved to: `test_week7_finance_results.json`

### Step 3: Review Results
```bash
# Check the output
cat test_week7_finance_results.json | python3 -m json.tool | head -50

# Key metrics to verify:
# - avg_completeness within 0.60-0.75? ✓
# - financial_terms_detected >= 5? ✓
# - difference from religious content < 0.15? ✓
```

### Step 4: Run Tech Content Test (Optional)
```bash
cd engine
python3 -u -m arena.cli.main process \
  /Users/whitegodkingsley/Desktop/arena/test_001/clips/breaking-the-mold-my-unconventional-tech-journey_001_00m00s-00m28s.mp4 \
  -o /Users/whitegodkingsley/Desktop/arena/test_week7_tech \
  -n 3 --editorial-model gpt-4o-mini --min 30 --max 90
```

---

## What to Look For

### ✅ Success Indicators:
1. **Completeness Consistency**:
   - Financial avg completeness: 0.60-0.75
   - Difference from religious (0.66): < 0.15
   - No systematic bias toward any content type

2. **Content-Aware Validation Working**:
   - Financial terms detected: "debt", "mortgage", "invest", "wealth"
   - No false "unresolved references" for these terms
   - System recognizes domain-specific vocabulary

3. **Quality Maintained**:
   - Production units: 20-30% of total ThoughtUnits
   - Clips are complete arguments with premise/claim/resolution
   - Deduplication works on long video (40-60% for 2h content)

### ⚠️ Warning Signs:
1. **Completeness Too Low** (< 0.55):
   - May indicate production bar (0.75) is too strict for financial content
   - Consider lowering to 0.70 for complex economic arguments

2. **False Unresolved References**:
   - If system flags "debt", "mortgage" as unresolved
   - Need to strengthen content-aware prompts in standalone_validator.py

3. **Quality Degradation**:
   - If clips lack complete arguments
   - May need domain-specific calibration

---

## Current Validation Status

| Content Type | Status | Avg Completeness | Production % | Cost |
|--------------|--------|------------------|--------------|------|
| Religious (test_007) | ✅ VALIDATED | 0.66 | 25% | $0.068 |
| Financial (test_002) | ⏳ PENDING | ? | ? | ~$0.61 |
| Tech (test_004) | ⏳ PENDING | ? | ? | ~$0.023 |
| Wealth (test_009) | ⏳ OPTIONAL | ? | ? | ~$0.046 |

**Week 7 Progress**: 1/3 content types validated (33%)

---

## Expected Timeline

| Task | Duration | Notes |
|------|----------|-------|
| Run financial test | 8-12 min | Large 2h video |
| Review results | 5 min | Check metrics |
| Run tech test | 2-3 min | Small 5min video |
| Review results | 5 min | Check metrics |
| Cross-content comparison | 10 min | Analyze consistency |
| **TOTAL** | **30-35 min** | Plus any adjustments |

---

## Files Created for Week 7

```
engine/
├── test_week7_finance.py              # Main test script
├── WEEK7_VALIDATION_REPORT.md         # Comprehensive test plan
├── WEEK7_EXPECTED_RESULTS.md          # Expected outcomes analysis
└── WEEK7_README.md                    # This file (quick start)

Output (after running tests):
└── test_week7_finance_results.json    # Validation results
```

---

## After Week 7: Next Steps

Once Week 7 is complete, proceed to **Week 8: Production Polish**:

### Priority 1: Performance Optimization
- Batch API calls (save 10-20% on costs)
- Parallel processing for scoring (2-3x faster)
- Optimize deduplication algorithm (currently O(n²))

### Priority 2: Error Handling
- Graceful API failure recovery
- Progress checkpointing (resume on crash)
- Better error messages for users

### Priority 3: Documentation
- API reference for all modules
- Content-type calibration guide
- Troubleshooting guide

### Priority 4: Testing
- Unit tests for Weeks 1-4 modules
- Integration tests for full pipeline
- Regression tests for calibration changes

---

## Troubleshooting

### "OPENAI_API_KEY not set"
**Solution**: Export the key in your shell:
```bash
export OPENAI_API_KEY="sk-..."
```

### "Transcript not found"
**Solution**: Verify transcript exists:
```bash
ls "/Users/whitegodkingsley/Desktop/arena/test_002/.cache/"
```

### "Test takes too long" (>15 minutes)
**Expected**: 2h video with 500+ ThoughtUnits takes time
**Normal**: 8-12 minutes for full processing
**Workaround**: None needed, this is normal for long videos

### "Completeness scores too low"
**Investigation Steps**:
1. Check which clips scored low
2. Read the premise/claim/resolution text
3. Determine if bar is too strict or clips genuinely incomplete
4. Adjust production bar if needed (see WEEK7_EXPECTED_RESULTS.md)

---

## Quick Command Reference

```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Run Week 7 financial test
cd /Users/whitegodkingsley/Desktop/Reserved\ Area/Projects/arena/engine
python3 test_week7_finance.py

# View results
cat test_week7_finance_results.json | python3 -m json.tool

# Run full pipeline test on new video
python3 -u -m arena.cli.main process VIDEO.mp4 \
  -o OUTPUT_DIR -n 5 --editorial-model gpt-4o-mini

# Check Week 7 status
grep "VALIDATED\|PENDING" WEEK7_README.md
```

---

## Contact / Issues

If Week 7 validation reveals issues:

1. **Content-aware validation failing**: Update `standalone_validator.py` prompts
2. **Completeness consistently low**: Adjust production bar in `thought_unit.py`
3. **System crashes**: Add error handling in `adapter.py`
4. **Costs too high**: Consider optimization strategies in Week 8

---

**Last Updated**: Week 6 Complete, Week 7 Ready
**Status**: 🟡 Waiting for API key to execute tests
**Estimated Completion**: 30 minutes once API key is set
