# 4-Layer Editorial System - Architectural Refinement Plan

## Executive Summary

**Task:** Refine the completed 4-layer editorial system to address architectural issues identified in production review.

**Status:** Implementation complete (1,450 lines) → Now addressing real architectural flaws before production testing

**Approach:** Minimal, surgical changes to fix 4 critical problems + 4 high-impact refinements

---

## Context: What Was Built

The 4-layer system is **fully implemented and working**:
- ✅ Layer 1: MomentDetector (finds 25 moments)
- ✅ Layer 2: ThoughtBoundaryAnalyzer (expands to complete thoughts)
- ✅ Layer 3: StandaloneContextRefiner (quality gate)
- ✅ Layer 4: PackagingLayer (titles, descriptions, hashtags)
- ✅ Integrated with arena_process.py via `--use-4layer` flag
- ✅ Comprehensive test suite

---

## Architectural Review Findings

### ✅ What's Working (Don't Touch)
- Core separation of concerns is excellent
- Layer 3 as quality gate is the killer feature
- Metrics-first thinking throughout
- Drop-in adapter pattern works perfectly

### ❌ 4 Real Problems to Fix
1. **Layer 2/3 Overlap:** Both modify boundaries for similar reasons → waste & conflict
2. **No Hard Stops:** LLMs will expand indefinitely without explicit constraints
3. **Standalone Score Drift:** Subjective scoring without concrete anchors
4. **Cost Overuse:** Layer 2 uses GPT-4o where gpt-4o-mini would work

### 🔧 4 Concrete Refinements to Add
1. **Editorial Contract:** Document layer responsibilities to prevent future drift
2. **Rejection Reasons:** Enum for why clips fail (debugging + UX)
3. **Configurable Scoring:** Make interest/standalone weight tunable
4. **"No Changes" Flag:** Track when Layer 3 keeps Layer 2's boundaries

---

## Problem 1: Layer 2/3 Overlap

### Current State (Confirmed by Code Analysis)

**Layer 2 (`layer2_boundary_analyzer.py`):**
```python
# Lines 280-289: Expands boundaries for narrative completeness
STRATEGY:
1. Look BACKWARD: Where does speaker BEGIN setting up idea?
2. Look FORWARD: Where does idea reach COMPLETION/PAYOFF?
3. Ensure COMPLETENESS: beginning → middle → end
```

**Layer 3 (`layer3_context_refiner.py`):**
```python
# Lines 426-430: ALSO expands boundaries
BOUNDARY REFINEMENT:
- Suggest extending start time earlier to include missing setup
- Suggest extending end time later to include resolution
```

**The Conflict:**
- Layer 2 says: "boundaries should be [100s, 200s] for complete thought"
- Layer 3 says: "actually, make it [80s, 200s] because viewers need setup"
- Layer 3 iterates and **applies these changes** (lines 243-247)

### Solution: Clear Separation of Concerns

**New Contract:**
```
Layer 2: Structural completeness (beginning → middle → end)
         - Focus on narrative flow
         - Never consider pronouns/references

Layer 3: Contextual independence (Who? What? Why?)
         - Validate understanding
         - Max ±2 sentences adjustment
         - Only refine if score < 0.7
```

### Implementation Changes

**File:** `arena/editorial/layer2_boundary_analyzer.py`

**Change 1 - Update prompt (line 280-314):**
```python
TASK:
Find the COMPLETE THOUGHT BOUNDARIES for this moment.

YOUR FOCUS: Narrative structure ONLY
- Where does the idea BEGIN (setup)?
- Where does the idea END (payoff)?

DO NOT WORRY ABOUT:
- Whether pronouns are clear (Layer 3's job)
- Whether viewers understand context (Layer 3's job)
- Missing background information (Layer 3's job)

ONLY FOCUS ON:
- Narrative flow: Does it have beginning/middle/end?
- Topical coherence: Does it stay on one idea?
```

**Change 2 - Add hard constraints (line 308-314):**
```python
RULES:
- expanded_start should be ≤ {rough_start} (earlier or same)
- expanded_end should be ≥ {rough_end} (later or same)
- MAX EXPANSION BACKWARD: 30 seconds OR ~100 words
- MAX EXPANSION FORWARD: 30 seconds OR ~100 words
- Typical expansion: 20-50% longer
- Stop expanding when thought is complete, not when context is perfect
```

**File:** `arena/editorial/layer3_context_refiner.py`

**Change 3 - Limit refinement scope (line 426-430):**
```python
BOUNDARY REFINEMENT RULES:
- You may suggest MINOR adjustments only
- MAX ADJUSTMENT: ±2 sentences (±15 seconds)
- Only adjust if standalone_score < 0.7
- Focus on fixing missing context, NOT restructuring the clip
- If major changes needed, REJECT instead

Example acceptable adjustments:
- Add 1 sentence at start to clarify "the problem" being discussed
- Add 1 sentence at end to complete resolution

Example unacceptable adjustments:
- Expanding 20+ seconds backward for full backstory
- Reworking the entire clip structure
```

**Change 4 - Track if changes made (line 432-441):**
```python
OUTPUT JSON ONLY:
{
  "standalone_score": 0.75,
  "refined_start": {start},
  "refined_end": {end},
  "changes_made": false,  // NEW FIELD
  "adjustment_type": null,  // "expanded_start" | "expanded_end" | "both" | null
  "editor_notes": "...",
  "missing_context": [...],
  "strengths": [...],
  "weaknesses": [...]
}
```

---

## Problem 2: No Hard Stops on Expansion Drift

### Current State

**Layer 2:** Says "Typical expansion: 20-50%" but no hard maximum
**Layer 3:** No limits mentioned at all

**Risk:** LLMs will expand indefinitely, creating 5-minute "clips"

### Solution: Explicit Hard Constraints

**File:** `arena/editorial/layer2_boundary_analyzer.py` (line 308-314)

**Add to prompt:**
```python
HARD CONSTRAINTS:
- NEVER expand more than 30 seconds backward
- NEVER expand more than 30 seconds forward
- NEVER expand beyond topically-related content
- If idea needs >60s expansion total, confidence should be <0.5
```

**File:** `arena/editorial/layer3_context_refiner.py` (line 426-430)

**Add to prompt:**
```python
HARD CONSTRAINTS ON REFINEMENT:
- MAX adjustment: ±15 seconds (±2 sentences)
- If more than 15s adjustment needed → REJECT with reason
- Never suggest changes >10% of original clip length
```

**Add validation in code (new method in `StandaloneContextRefiner`):**
```python
def _validate_refinement_bounds(
    self,
    original_start: float,
    original_end: float,
    refined_start: float,
    refined_end: float
) -> bool:
    """Ensure refinements don't exceed hard limits"""
    MAX_ADJUSTMENT_SECONDS = 15.0

    start_adjustment = abs(original_start - refined_start)
    end_adjustment = abs(original_end - refined_end)

    if start_adjustment > MAX_ADJUSTMENT_SECONDS:
        return False
    if end_adjustment > MAX_ADJUSTMENT_SECONDS:
        return False

    return True
```

---

## Problem 3: Standalone Score Lacks Anchors

### Current State

Layer 3 has a scoring guide but it's vague:
```python
- 0.9-1.0: Perfect standalone clip, anyone can understand
- 0.7-0.9: Good standalone quality, minor context assumptions
```

**Problem:** "Good standalone quality" is subjective → Claude drifts

### Solution: Concrete Calibration Examples

**File:** `arena/editorial/layer3_context_refiner.py` (line 419-424)

**Replace vague guide with concrete examples:**
```python
SCORING GUIDE WITH CONCRETE EXAMPLES:

0.9-1.0: PERFECT STANDALONE
Example: "Today I'm going to show you how to fix rate limit errors in Python.
         The problem is when you make too many API calls, you get a 429 error.
         Here's the solution: implement exponential backoff..."
Why 0.9+: Topic stated, problem defined, solution clear. No prior knowledge needed.

0.7-0.9: GOOD STANDALONE (Minor gaps acceptable)
Example: "So after we implemented this caching system, our performance improved by 50%.
         The key was using Redis instead of in-memory caching..."
Why 0.7-0.9: Clear outcome and solution. Minor: doesn't explain why caching was needed,
            but viewer can infer performance was a problem.

0.5-0.7: MARGINAL (Some prior knowledge helpful)
Example: "This approach solved our problem completely. We went from 30-second load times
         to under 2 seconds by implementing this pattern..."
Why 0.5-0.7: Clear improvement, but "this approach" and "this pattern" are vague.
            Viewer gets value but would benefit from knowing what the approach was.

0.3-0.5: POOR (Requires significant context)
Example: "And that's why it didn't work. So we had to completely rethink our architecture
         and move to a different pattern..."
Why 0.3-0.5: "It", "that", "our architecture" - all undefined. Viewer lost without backstory.

0.0-0.3: UNUSABLE (Completely dependent on prior context)
Example: "After that failed, we tried the second approach, which also didn't work.
         So then we moved to option three..."
Why 0.0-0.3: No idea what "that", "second approach", or "option three" are.
            Meaningless without full video context.

SCORING INSTRUCTIONS:
1. Compare clip to these examples
2. Which example does it most resemble?
3. Assign score in that range
4. Be strict: When in doubt, score lower
```

---

## Problem 4: GPT-4o Overuse in Layer 2

### Current State

Layer 2 uses `gpt-4o` for boundary detection (line 41, 100)

**Cost:** ~$0.60 per 30-min video for Layer 2 alone

### Solution: Downgrade to gpt-4o-mini After Validation

**Approach:**
1. **Phase 1 (Now):** Keep gpt-4o, add flag to test gpt-4o-mini
2. **Phase 2 (After testing):** Switch default if quality maintained

**File:** `arena/editorial/layer2_boundary_analyzer.py`

**Change constructor (line 41):**
```python
def __init__(self, api_key: str, model: str = "gpt-4o"):
    """
    Initialize thought boundary analyzer

    Args:
        api_key: OpenAI API key
        model: Model to use (default: gpt-4o, can use gpt-4o-mini for cost savings)
              Note: gpt-4o-mini requires prompt tuning for quality
    """
    self.api_key = api_key
    self.model = model  # Allow override
```

**File:** `arena/editorial/adapter.py` (line 115)

**Add parameter:**
```python
self.boundary_analyzer = ThoughtBoundaryAnalyzer(
    self.api_key,
    model=self.model  # Use same model as Layer 1 by default
)
```

**File:** `arena_process.py`

**Add CLI flag for testing:**
```python
parser.add_argument(
    '--editorial-model',
    choices=['gpt-4o', 'gpt-4o-mini'],
    default='gpt-4o',
    help='Model to use for Layers 1-2 (default: gpt-4o, mini saves cost but may reduce quality)'
)
```

**Testing Strategy:**
1. Run 3 videos with `--editorial-model gpt-4o`
2. Run same 3 videos with `--editorial-model gpt-4o-mini`
3. Compare Layer 2 confidence scores and Layer 3 pass rates
4. If pass rates within 10%, switch default to mini

---

## Refinement 1: Editorial Contract Documentation

### Solution: Add Clear Docstrings

**File:** `arena/editorial/layer2_boundary_analyzer.py` (line 17-32)

**Add to class docstring:**
```python
"""
Layer 2: Identifies complete thought boundaries.

EDITORIAL CONTRACT:
- Input: Rough moments from Layer 1
- Focus: NARRATIVE STRUCTURE (beginning → middle → end)
- Output: Expanded boundaries for complete thoughts
- NOT responsible for: Standalone comprehension (Layer 3's job)

Separation from Layer 3:
- Layer 2 asks: "Where does this idea naturally begin and end?"
- Layer 3 asks: "Can someone understand this without prior context?"

These are DIFFERENT questions with DIFFERENT solutions.
Layer 2 focuses on structural completeness, Layer 3 on contextual independence.
"""
```

**File:** `arena/editorial/layer3_context_refiner.py` (line 18-35)

**Add to class docstring:**
```python
"""
Layer 3: Standalone Context Refiner (QUALITY GATE)

EDITORIAL CONTRACT:
- Input: Complete thought boundaries from Layer 2
- Focus: CONTEXTUAL INDEPENDENCE (Who? What? Why?)
- Output: Validated clips OR rejection
- Minor refinement allowed: ±2 sentences (±15s max)

Separation from Layer 2:
- Layer 2 ensures: Structural completeness
- Layer 3 ensures: Standalone understandability

Layer 3 should TRUST Layer 2's boundaries and only make minor adjustments.
If major changes needed (>15s adjustment), REJECT instead of expanding.
"""
```

---

## Refinement 2: Rejection Reason Enum

### Solution: Add Structured Rejection Reasons

**File:** `arena/editorial/layer3_context_refiner.py`

**Add enum at top (after imports):**
```python
from enum import Enum

class RejectionReason(Enum):
    """Why clips are rejected"""
    MISSING_PREMISE = "missing_premise"  # Doesn't explain what topic is about
    DANGLING_REFERENCE = "dangling_reference"  # Unresolved "it", "this", "that"
    INCOMPLETE_RESOLUTION = "incomplete_resolution"  # Cuts off mid-thought
    TOPIC_DRIFT = "topic_drift"  # Starts on one topic, ends on another
    DURATION_CONSTRAINT = "duration_constraint"  # Too short/long
    STRUCTURAL_ISSUE = "structural_issue"  # No clear beginning/middle/end
```

**Update output format (line 432-441):**
```python
OUTPUT JSON ONLY:
{
  "standalone_score": 0.35,
  "refined_start": {start},
  "refined_end": {end},
  "changes_made": false,
  "rejection_reason": "dangling_reference",  // NEW FIELD (if score < 0.4)
  "editor_notes": "Clip uses 'this approach' and 'it' without defining them",
  ...
}
```

**Update `_validate_single` return type:**
```python
def _validate_single(...) -> Optional[Tuple[float, float, float, str, Optional[str]]]:
    """
    Returns:
        (refined_start, refined_end, standalone_score, editor_notes, rejection_reason)
    """
```

---

## Refinement 3: Configurable Composite Scoring

### Solution: Make Scoring Weights Tunable

**File:** `arena/editorial/adapter.py`

**Add to constructor (line 33):**
```python
def __init__(
    self,
    api_key: str,
    model: str = "gpt-4o",
    export_layers: bool = False,
    score_weights: Optional[Dict[str, float]] = None
):
    """
    Initialize 4-layer editorial adapter

    Args:
        api_key: OpenAI API key
        model: Base model to use
        export_layers: Export intermediate results
        score_weights: Custom scoring weights (default: {'interest': 0.6, 'standalone': 0.4})
    """
    self.api_key = api_key
    self.model = model
    self.export_layers = export_layers

    # Default scoring weights
    self.score_weights = score_weights or {
        'interest': 0.6,
        'standalone': 0.4
    }
```

**Update scoring logic (line 160):**
```python
# Select top N by combined score
def combined_score(c):
    return (
        c['interest_score'] * self.score_weights['interest'] +
        c['standalone_score'] * self.score_weights['standalone']
    )

top_clips = sorted(packaged_clips, key=combined_score, reverse=True)[:target_clips]
```

**File:** `arena_process.py`

**Add CLI flag (future enhancement):**
```python
parser.add_argument(
    '--score-weight',
    action='append',
    metavar='KEY=VALUE',
    help='Custom scoring weights (e.g., --score-weight interest=0.5 --score-weight standalone=0.5)'
)
```

---

## Refinement 4: Track "No Changes" from Layer 3

### Solution: Add Metrics for Layer 2 Quality

**File:** `arena/editorial/layer3_context_refiner.py`

**Update metrics dict (line 51-57):**
```python
self.metrics = {
    'api_calls': 0,
    'tokens_used': 0,
    'cost_usd': 0.0,
    'passed': 0,
    'revised': 0,
    'rejected': 0,
    'pass_rate': 0.0,
    'no_changes_needed': 0,  # NEW: Layer 2 boundaries were perfect
    'boundary_quality_rate': 0.0  # NEW: no_changes / (passed + revised)
}
```

**Track in validation loop (after line 158):**
```python
if clip:
    validated_clips.append(clip)

    # Track metrics
    if clip['verdict'] == 'PASS':
        self.metrics['passed'] += 1

        # NEW: Check if Layer 3 made changes
        if not clip.get('changes_made', True):  # Default True for backward compat
            self.metrics['no_changes_needed'] += 1
```

**Calculate quality rate (after line 169):**
```python
# Calculate pass rate
total = self.metrics['passed'] + self.metrics['revised'] + self.metrics['rejected']
if total > 0:
    self.metrics['pass_rate'] = self.metrics['passed'] / total

    # Calculate boundary quality rate
    eligible = self.metrics['passed'] + self.metrics['revised']
    if eligible > 0:
        self.metrics['boundary_quality_rate'] = self.metrics['no_changes_needed'] / eligible
```

**Update metrics summary (line 450-458):**
```python
def get_metrics_summary(self) -> str:
    return f"""Layer 3 Metrics:
  API Calls: {self.metrics['api_calls']}
  Tokens Used: {self.metrics['tokens_used']:,}
  Cost: ${self.metrics['cost_usd']:.3f}
  Passed: {self.metrics['passed']}
  Revised: {self.metrics['revised']}
  Rejected: {self.metrics['rejected']}
  Pass Rate: {self.metrics['pass_rate']:.1%}
  Boundary Quality: {self.metrics['boundary_quality_rate']:.1%} (Layer 2 boundaries kept as-is)"""
```

---

## What NOT to Build (Scope Control)

### ❌ Do NOT Implement Yet:
1. **Reinforcement learning:** Wait for thousands of clips + user feedback
2. **Fine-tuning:** Prompt iteration gets 80% gains for 10% effort
3. **Social platform analytics:** Phase 3-4 feature
4. **Multi-video batch processing:** Optimize single-video first
5. **Custom quality thresholds per content type:** Add after baseline metrics

---

## Testing Strategy

### Phase 1: Validate Refinements (Don't Run Yet)

After implementing refinements, run on 3 real videos:

**Video 1: User's video (baseline)**
**Video 2: Boring video (e.g., tutorial with minimal hooks)**
**Video 3: Chaotic video (e.g., podcast with topic jumps)**

### Metrics to Track:

```bash
python arena_process.py video1.mp4 --use-4layer --export-editorial-layers -n 5

# Check these metrics:
1. Layer 2 confidence scores (should be >0.7 for most)
2. Layer 3 pass rate (target: 50-70%)
3. Layer 3 "no changes needed" rate (target: >30%)
4. Final clip quality (manual review: 9/10 should be usable)
```

### Key Questions to Answer:

1. **Which layer causes most human "ugh"?**
   - Bad moments → Layer 1 problem
   - Incomplete thoughts → Layer 2 problem
   - Missing context → Layer 3 problem
   - Bad titles → Layer 4 problem

2. **Are Layer 2/3 still fighting?**
   - Check `changes_made` field in exported Layer 3 results
   - If >70% need changes, Layer 2 prompts need work

3. **Are scores stable?**
   - Run same video twice
   - Standalone scores should be within ±0.1

### Phase 2: Model Cost Comparison (After Phase 1)

```bash
# Test gpt-4o-mini for Layer 2
python arena_process.py video1.mp4 --use-4layer --editorial-model gpt-4o-mini

# Compare:
- Cost difference (should be ~60% cheaper)
- Layer 2 confidence scores
- Layer 3 pass rate
- Final clip quality
```

---

## Implementation Order (When Approved)

1. **Problem 1 (Layer 2/3 Overlap):**
   - Update Layer 2 prompt (~10 lines)
   - Update Layer 3 prompt (~15 lines)
   - Add `changes_made` field (~5 lines)

2. **Problem 2 (Hard Stops):**
   - Add constraints to Layer 2 prompt (~5 lines)
   - Add constraints to Layer 3 prompt (~5 lines)
   - Add validation method (~15 lines)

3. **Problem 3 (Score Anchors):**
   - Replace scoring guide in Layer 3 (~40 lines)

4. **Problem 4 (Model Cost):**
   - Add model parameter to Layer 2 (~3 lines)
   - Add CLI flag (~5 lines)

5. **Refinement 1 (Contract):**
   - Update docstrings (~20 lines)

6. **Refinement 2 (Rejection Reasons):**
   - Add enum (~10 lines)
   - Update validation logic (~10 lines)

7. **Refinement 3 (Configurable Scoring):**
   - Add score_weights parameter (~15 lines)
   - Update scoring logic (~5 lines)

8. **Refinement 4 (Track Changes):**
   - Add metrics (~5 lines)
   - Update tracking (~10 lines)

**Total: ~170 lines of changes across 4 files**

---

## Files to Modify

1. **`arena/editorial/layer2_boundary_analyzer.py`** (~30 line changes)
   - Update prompt for clear separation
   - Add hard constraints
   - Add model parameter

2. **`arena/editorial/layer3_context_refiner.py`** (~80 line changes)
   - Update prompt for limited refinement
   - Add concrete scoring examples
   - Add rejection reasons
   - Add "no changes" tracking
   - Add boundary validation

3. **`arena/editorial/adapter.py`** (~20 line changes)
   - Add score_weights parameter
   - Update combined scoring logic

4. **`arena_process.py`** (~10 line changes)
   - Add --editorial-model flag
   - (Future: Add --score-weight flag)

5. **Tests:** Update test expectations (~30 line changes)
   - Update test_layer2_boundary_analyzer.py
   - Update test_layer3_context_refiner.py
   - Update test_4layer_integration.py

---

## Success Criteria (After Implementation)

### Quality Metrics:
- [ ] Layer 3 pass rate: 50-70%
- [ ] Layer 3 "no changes needed": >30%
- [ ] Layer 2 confidence: >0.7 average
- [ ] Manual review: >90% clips usable

### Performance Metrics:
- [ ] Cost reduction: 40-60% if using gpt-4o-mini for Layer 2
- [ ] Processing time: <2 min per 30-min video
- [ ] Score stability: ±0.1 on repeated runs

### Validation:
- [ ] Layer 2/3 boundary adjustments < 15s
- [ ] No clips expanded > 60s total from original moment
- [ ] Rejection reasons tracked and actionable

---

## Next Immediate Step

**User Decision Required:**

Which testing approach?

**Option A: Implement all refinements first, then test**
- Pros: Complete solution
- Cons: Harder to debug if issues arise
- Time: ~2-3 hours implementation + testing

**Option B: Implement problems 1-2 first (overlap + hard stops), test, then continue**
- Pros: Validate approach before full implementation
- Cons: Two implementation cycles
- Time: ~1 hour first batch + testing, then ~1.5 hours second batch

**Option C: Just implement Problem 1 (overlap fix) as proof-of-concept**
- Pros: Fastest validation
- Cons: Other issues remain
- Time: ~30 min implementation + testing

**Recommendation: Option B** - Fix the two most critical architectural issues (overlap + hard stops) first, validate on 3 videos, then proceed with remaining refinements based on learnings.
