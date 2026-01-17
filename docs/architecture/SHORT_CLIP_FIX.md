# Short Clip Problem: Root Cause & Fix

**Issue**: Current system generates meaningless short clips (0-3 seconds) without user specifying `--min`.

**Date**: 2026-01-15

---

## Root Causes Identified

### 1. **No Validation Floor in AI Analysis**
**Location**: `arena/ai/analyzer.py` → `_validate_clips()`

**Problem**:
```python
# Old code (lines 207-211)
# Validate duration only if constraints are specified
if min_duration is not None and duration < min_duration:
    continue
if max_duration is not None and duration > max_duration:
    continue
```

When user doesn't specify `--min`, `min_duration = None`, so ALL durations pass validation, including 0.5-second clips.

**Why This Happened**:
We removed default min/max constraints to be "content-driven", but removed ALL quality control too.

---

### 2. **Weak AI Prompt Guidance**
**Location**: `arena/ai/analyzer.py` → `_create_analysis_prompt()`

**Problem**:
```python
# Old prompt (line 139)
"whether that takes 10 seconds or 2 minutes"
```

This gave AI permission to create ANY duration, including meaningless short clips. "10 seconds" is mentioned but not emphasized as necessary for complete thoughts.

**Why This Happened**:
We tried to avoid "hardcoded constraints" but didn't guide the AI about what constitutes a "complete thought with standalone context."

---

### 3. **Alignment Could Create Short Clips**
**Location**: `arena/ai/sentence_detector.py` → `align_clip_to_boundaries()`

**Problem**:
Even with 80% shrink protection (line 216), if sentence boundaries were close together, alignment could theoretically create short clips without reverting.

---

## The Fix: Sanity Filtering vs. User Constraints

### Key Distinction

| Type | Purpose | Example | Flexible? |
|------|---------|---------|-----------|
| **User Constraint** | User preference for their use case | `--min 30` = "I want clips at least 30s" | YES - Optional flag |
| **Sanity Filter** | Reality check on what's physically possible | "A 2s clip cannot contain setup+core+conclusion" | NO - Always applied |

### What We Fixed

#### 1. **Added 8-Second Sanity Filter** (`analyzer.py`)

```python
# New code (lines 207-215)
# Sanity filter: Remove physically impossible clips
# This is NOT a user constraint - it's quality control
# A clip under 8 seconds cannot contain:
# - Setup/context for the idea
# - The core statement/insight
# - Resolution/conclusion
# This filters AI mistakes, not enforces user preferences
if duration < 8.0:
    continue
```

**Why 8 seconds?**
- Minimum to say something meaningful: ~2 seconds
- Setup context: +2-3 seconds
- Core statement: +2-3 seconds
- Conclusion: +1-2 seconds
- **Total**: ~7-8 seconds for fastest complete thought

**This is NOT a hardcoded minimum** - it's a garbage filter. It says "if you produced a 3-second clip, something went wrong."

---

#### 2. **Strengthened AI Prompt** (`analyzer.py`)

```python
# New prompt (lines 139-140)
duration_guidance = """Identify complete thoughts, stories, or insights.
Each clip MUST contain a full arc: setup/context → core statement → resolution/conclusion.
A complete standalone idea typically requires at least 15-20 seconds to establish context
and deliver value. Let the natural boundaries of the content determine the exact length,
but ensure every clip has complete context."""

duration_constraint = """- Each clip must be a complete, self-contained idea with full context
- Include setup, development, and conclusion
- Do NOT cut mid-thought or mid-explanation
- Clips should be substantial enough that a viewer can understand and appreciate the idea
  without prior context"""
```

**Key Changes**:
- Explicit arc structure: setup → statement → conclusion
- "Typically requires 15-20 seconds" = GUIDANCE (not constraint)
- Emphasizes "complete" and "self-contained"
- Multi-point constraint list for clarity

---

#### 3. **Added Final Sanity Check in Alignment** (`sentence_detector.py`)

```python
# New code (lines 242-249)
# Final sanity check: If alignment resulted in absurdly short clip, revert entirely
# This catches cases where bad sentence boundaries created unusable clips
final_duration = adjusted_end - adjusted_start
if final_duration < 8.0:
    # Alignment failed to maintain viable clip - use original timestamps
    adjusted_start = start_time
    adjusted_end = end_time
    final_duration = original_duration
```

**Protection**:
Even if AI produces good clips, if sentence alignment shrinks them below 8s, revert to original timestamps.

---

## How It Works Now

### Pipeline Flow

```
1. AI Analysis → Produces clips based on complete thought guidance
   ↓
2. Validation → Filters clips < 8s (sanity filter)
   ↓
3. User Constraints → Applies --min/--max if specified
   ↓
4. Professional Alignment → Adjusts to sentence boundaries
   ↓
5. Final Sanity Check → Reverts if alignment created <8s clip
   ↓
6. Clip Generation → Only meaningful clips survive
```

### Examples

#### Scenario 1: No user flags (default)
```bash
arena process video.mp4
```

**What happens**:
- AI guided to produce complete thoughts (15-20s typical)
- 8s sanity filter removes garbage
- No user min/max applied
- Alignment refines boundaries
- Final check prevents alignment from creating short clips

**Result**: Content-driven durations, but all clips are meaningful

---

#### Scenario 2: User specifies minimum
```bash
arena process video.mp4 --min 30
```

**What happens**:
- AI guided to produce complete thoughts
- 8s sanity filter (always applied)
- User min (30s) applied → Filters clips 8-29s
- Alignment refines boundaries
- Final check prevents <8s

**Result**: All clips ≥30s as requested

---

#### Scenario 3: User specifies both min and max
```bash
arena process video.mp4 --min 20 --max 60
```

**What happens**:
- AI receives explicit duration range in prompt
- 8s sanity filter (redundant but harmless)
- User min/max (20-60s) applied
- Alignment refines
- Final check prevents <8s

**Result**: Clips between 20-60s

---

## Testing Validation

### What Should NOT Happen Anymore

❌ **0-3 second clips** - Sanity filter catches these
❌ **Mid-sentence cuts** - Alignment handles this
❌ **Incomplete thoughts** - Prompt guidance prevents this
❌ **Clips without context** - Prompt emphasizes standalone context

### What SHOULD Happen

✅ **Meaningful clips without --min** - Default now produces substantial clips
✅ **Complete thought arcs** - Setup → Core → Conclusion
✅ **Standalone context** - No dangling references
✅ **Professional boundaries** - Aligned to sentences
✅ **Flexible durations** - 15s to 2min+ based on content

### Test Cases

**Test 1: No Flags**
```bash
arena process interview.mp4 -n 5
```
Expected: 5 clips, all >8s, complete thoughts, varying durations

**Test 2: With Min**
```bash
arena process interview.mp4 -n 5 --min 25
```
Expected: 5 clips, all ≥25s, complete thoughts

**Test 3: With Range**
```bash
arena process interview.mp4 --min 15 --max 45
```
Expected: Clips between 15-45s only

---

## Why This Approach is Correct

### Content-Driven ✓
Duration still determined by natural thought boundaries, not arbitrary defaults.

### Quality Control ✓
8s filter prevents garbage without limiting content expression.

### User Control ✓
`--min` and `--max` still work for specific use cases.

### Reality-Based ✓
Acknowledges that <8s cannot contain complete standalone thoughts.

### Not Hardcoded Minimum ✗
8s is a garbage filter, NOT a user-facing constraint. It's invisible quality control.

---

## Philosophy

**Before**: "No constraints whatsoever" → Result: Garbage clips

**Now**: "Content-driven with sanity filtering" → Result: Meaningful clips

**Analogy**:
- Garbage filter = Spell checker catching "asdfjkl"
- User constraint = Style guide requiring "at least 500 words"

One prevents nonsense, the other enforces preference. Both are valid and serve different purposes.

---

## Monitoring

### Metrics to Track

After this fix, monitor:

1. **Clip Duration Distribution**
   - Should show natural distribution starting ~15s
   - Very few 8-12s clips (edge cases only)
   - Most clips 15-90s

2. **User Feedback**
   - "I had to specify --min" → Should not hear this anymore
   - "Clips are too short" → Should not hear this anymore
   - "Clips lack context" → Prompt fix should address

3. **Rejection Rate**
   - Track how many AI-proposed clips get filtered at 8s check
   - High rejection = AI prompt needs more tuning
   - Low rejection = Prompt working well

4. **Manual Review**
   - Sample 20 clips from different videos
   - Check for completeness, context, meaningful content
   - Target: >95% clips are usable

---

## If Problems Persist

### If still getting short clips:

1. **Check AI output before filtering**
   - Is AI producing short clips that get filtered?
   - Or is alignment shrinking good clips?

2. **Increase guidance in prompt**
   - Make "15-20 seconds" more prominent
   - Add examples of complete vs. incomplete thoughts

3. **Adjust sanity threshold**
   - If 8s too low, increase to 10s
   - Document reasoning in code comments

### If clips lack context:

1. **Strengthen "standalone" guidance**
   - Add more examples in prompt
   - Emphasize "no prior knowledge needed"

2. **Consider 4-layer architecture**
   - Layer 3 (Context Refiner) explicitly validates this
   - More thorough but more expensive

---

## Related Files Modified

1. `arena/ai/analyzer.py`
   - Added 8s sanity filter (line 214)
   - Strengthened prompt guidance (lines 139-140)

2. `arena/ai/sentence_detector.py`
   - Added final sanity check (lines 242-249)
   - Prevents alignment from creating short clips

3. `PROMPTS.md`
   - Updated documentation with new prompt text
   - Explained sanity filtering philosophy

4. `SHORT_CLIP_FIX.md` (this file)
   - Complete explanation of problem and solution

---

## Next Steps

1. **Test with real videos**
   - Run on 5-10 diverse videos
   - Verify no short clips without --min
   - Check clip quality manually

2. **Collect metrics**
   - Duration distribution
   - Rejection rates
   - User feedback

3. **If all good, close issue**
   - Document successful fix
   - Update CHANGELOG.md

4. **If problems persist, escalate to 4-layer architecture**
   - Current fix is "quick win"
   - 4-layer is comprehensive solution

---

## Conclusion

**Short clips problem solved via two-pronged approach**:

1. **Sanity filtering** - Prevents physically impossible clips (8s threshold)
2. **Stronger guidance** - AI understands what "complete thought" means

This maintains content-driven philosophy while adding necessary quality control. Users no longer need `--min` for reasonable output, but can still use it for specific requirements.

**Status**: ✅ Fixed - Ready for testing
