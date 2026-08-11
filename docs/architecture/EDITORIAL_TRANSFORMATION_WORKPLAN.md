# Work Plan: Achieving Editorial Transformation
## From Semantic Peaks → Complete Thought Units

**Goal**: Transform Arena from the "Current Approach" to the "Future Approach" described in EDITORIAL_COMPARISON.md

**User's Guidance**: test_007 feedback shows how a human editor thinks:
- clip_01: Even "passing" clips can lack completeness
- clip_02: What true standalone looks like (premise → claim)
- clip_03: **THE GOLD STANDARD** - Follow the thought from where it starts to where it completes, regardless of length
- clip_04: Human tolerance for imperfection if there's value

---

## The Fundamental Shift

### Current Behavior (Semantic Peak Detection)
```
1. Scan for emotionally strong sentences
2. Find peaks
3. Expand slightly around peak
4. Validate grammar
5. Output: Fragment that might start mid-thought
```

**Result**:
- Clips like "That's why I always say..." (what's "that"?)
- Missing premise or resolution
- 1-2 usable out of 10 (10-20% usability)

### Target Behavior (Thought Unit Construction)
```
1. Detect claim/insight moments (peaks are clues)
2. Search BACKWARD for premise (where does this thought BEGIN?)
3. Search FORWARD for resolution (where does this thought COMPLETE?)
4. Validate rhetorical completeness (premise + claim + resolution)
5. Output: Complete standalone thought
```

**Result**:
- Clips like your clip_03: Complete biblical argument from premise to resolution
- Every clip has setup → development → closure
- 8-10 usable out of 10 (80-90% usability)

---

## Your Editorial Principles (Learned from test_007)

### Principle 1: Follow the Thought to Completion
**Your words**: "I read the transcript and selected where makes sense to start and ensure to follow on the speaks thought to where it makes sense to end."

**What this means**:
- Don't optimize for duration (30-60s)
- Optimize for **cognitive closure**
- A 3-minute clip is better than 6×30s fragments if it's ONE complete thought

**Implementation**:
```python
# Current (WRONG):
if duration > 60:
    reject()

# Target (RIGHT):
while not is_thought_complete(clip):
    expand_to_next_sentence()
    if duration > 180:  # Hard cap at 3 minutes
        break  # Only stop if thought won't complete
```

### Principle 2: Premise is Non-Negotiable
**Your clip_02**: "I believe God can tell you who to marry... But what I've seen in the Bible is that there is not one place where God picked a wife for someone."

**Structure**:
- ✅ Premise: "People believe God tells you who to marry"
- ✅ Claim: "Bible shows no evidence of this"
- ✅ Standalone: Yes - viewer understands both sides

**Your clip_01** (Arena's output): "The anxiety of being single is nothing compared to the regret of being in the wrong marriage."

**Your note**: "Lacks completeness but can spark interest"

**What's missing**:
- ❌ No setup (why are we talking about this?)
- ❌ No resolution (what should I do about it?)
- It's a CLAIM without PREMISE or RESOLUTION

**Implementation**:
```python
# Layer 2 must search BACKWARD from claim to find premise
def find_premise(claim_position, transcript):
    """
    Walk backward from claim to find where this thought begins

    Look for:
    - Topic introduction ("Let me talk about...")
    - Problem statement ("The issue is...")
    - Question being answered ("People ask me...")
    - Context setting ("Here's what I've noticed...")
    """
    # Search up to 60 seconds before claim
    # Find semantic shift (where this topic/thought begins)
```

### Principle 3: Resolution Provides Closure
**Your clip_03**: After listing all the biblical examples, it concludes with:
> "I'm saying that the Bible describes how people picked. The Bible doesn't show that God picked for somebody."

**This is cognitive closure**:
- ✅ Setup: "People say God picks your spouse"
- ✅ Development: "Here are examples from Bible"
- ✅ Resolution: "Bible describes, doesn't prescribe"
- ✅ Viewer satisfaction: "Ah, I understand the argument now"

**Implementation**:
```python
def find_resolution(claim_position, transcript):
    """
    Walk forward from claim to find where this thought completes

    Look for:
    - Conclusion statements ("So the point is...", "I'm saying that...")
    - Summarization ("That's why...")
    - Answer to question posed in premise
    - Semantic closure (topic shift to new idea)
    """
    # Search up to 90 seconds after claim
    # Find where thought reaches satisfying conclusion
```

### Principle 4: Tolerance for Imperfection
**Your clip_04**: "This clip isn't that great, but I would keep it."

**What this teaches**:
- Don't demand perfection
- If there's VALUE (practical story, relatable example), keep it
- Better to have 8 "good enough" clips than 2 "perfect" clips

**Implementation**:
```python
# Current: Only return PASS clips (score >= 0.7)
# Target: Return PASS + top REVISE clips to reach target count

def select_final_clips(validated_clips, target_count):
    pass_clips = [c for c in validated_clips if c['verdict'] == 'PASS']

    if len(pass_clips) >= target_count:
        return sorted(pass_clips, key=score)[:target_count]

    # Not enough PASS clips - include best REVISE clips
    revise_clips = [c for c in validated_clips if c['verdict'] == 'REVISE']
    needed = target_count - len(pass_clips)
    best_revise = sorted(revise_clips, key=score)[:needed]

    return pass_clips + best_revise
```

---

## Implementation Plan: 4 Phases

### Phase 1: Layer 1 Redesign - Thought Seed Detection (3-4 days)

**Current Problem**: Layer 1 finds "interesting moments" (peaks)

**Target**: Layer 1 should find "thought seeds" (claims/insights that anchor complete thoughts)

#### Changes Needed:

**1.1 Rename Conceptually**
```python
# Old name: MomentDetector
# New name: ThoughtSeedDetector

class ThoughtSeedDetector:
    """
    Detects claim/insight moments that serve as anchors for complete thoughts.

    A "seed" is:
    - A claim, insight, controversial statement, or key idea
    - Something that likely has a premise before it
    - Something that likely has a resolution after it

    NOT just "interesting peaks" or "emotional moments"
    """
```

**1.2 New Detection Strategy**
```python
def detect_thought_seeds(transcript, target_count):
    """
    Instead of finding peaks, find CLAIMS/INSIGHTS

    Look for:
    1. Argument structures:
       - "I believe...", "The problem is...", "Here's why..."
       - Thesis statements, controversial claims

    2. Teaching moments:
       - "Let me show you...", "The key is...", "Here's what..."
       - Explanations, examples, illustrations

    3. Story pivots:
       - "Then this happened...", "What I realized..."
       - Turning points, revelations

    4. Practical advice:
       - "You should...", "Don't...", "The way to..."
       - Actionable insights

    Use sliding window approach (2-min windows, find 3-5 seeds per window)
    """
```

**1.3 Over-Detection Strategy**
```python
# Detect 3-5x more seeds than target clips
# Example: target 10 clips → detect 30-50 seeds
# Layer 2 will expand them to thoughts
# Layer 3 will validate (expect 40-60% pass rate)
# Layer 4 will deduplicate and select top 10

seeds = detect_thought_seeds(transcript, target_count * 4)
```

**Success Criteria**:
- test_007 (15 min) should find 40-50 seeds (not just 1)
- Seeds should be distributed across the video
- Seeds should include diverse content types (arguments, stories, advice, examples)

---

### Phase 2: Layer 2 Enhancement - Thought Unit Construction (4-5 days)

**Current Problem**: Layer 2 expands to "sentence boundaries" around peak

**Target**: Layer 2 should construct complete thought units (premise → claim → resolution)

#### Changes Needed:

**2.1 Backward Search for Premise**
```python
def find_premise_boundary(seed_position, transcript):
    """
    Walk backward from seed to find where this THOUGHT begins

    Algorithm:
    1. Start at seed position
    2. Move backward sentence by sentence
    3. Look for semantic shift (topic change)
    4. Look for setup indicators:
       - "Let me talk about..."
       - "People always ask..."
       - "Here's the issue..."
       - "I was thinking about..."
    5. Stop when you find clear beginning OR reach 60s before seed

    Return: premise_start_time
    """

    # Use semantic similarity to detect topic shift
    # If similarity drops below 0.6, we've left the thought

    # Also use discourse markers:
    # "Now, let's talk about X" = new thought beginning
    # "So going back to..." = continuation of previous thought
```

**2.2 Forward Search for Resolution**
```python
def find_resolution_boundary(seed_position, transcript):
    """
    Walk forward from seed to find where this THOUGHT completes

    Algorithm:
    1. Start at seed position
    2. Move forward sentence by sentence
    3. Look for conclusion indicators:
       - "So the point is..."
       - "That's why..."
       - "I'm saying that..."
       - "Do you see what I mean?"
    4. Look for semantic closure (topic shifts to new idea)
    5. Stop when thought reaches natural conclusion OR 90s after seed

    Return: resolution_end_time
    """

    # Cognitive closure detection:
    # - Summarization language
    # - Return to initial question/premise
    # - Explicit conclusion markers
    # - Topic shift to new idea
```

**2.3 Thought Unit Validation**
```python
def validate_thought_unit(premise_start, seed_position, resolution_end, transcript):
    """
    Ensure we have a COMPLETE thought, not just expanded peak

    Validate:
    1. Has premise (setup/context at beginning)
    2. Has claim/insight (the seed we detected)
    3. Has resolution (conclusion/closure at end)
    4. Total duration is reasonable (30s - 180s)
    5. Semantic coherence (all parts related to same topic)

    Return: ThoughtUnit object or None
    """

    # Use GPT to validate structure:
    prompt = f"""
    Does this transcript segment have:
    1. A clear BEGINNING (premise/setup)?
    2. A clear MIDDLE (claim/insight)?
    3. A clear END (resolution/conclusion)?

    If missing any, suggest where to expand.
    """
```

**Success Criteria**:
- test_007: 40-50 seeds → 30-40 complete thought units
- Each thought unit has identifiable premise, claim, resolution
- Your clip_03 structure should be automatically detected
- Rejection rate: 20-30% (seeds that can't form complete thoughts)

---

### Phase 3: Layer 3 Enhancement - Rhetorical Validation (2-3 days)

**Current State**: Already enhanced with beginning/middle/end scoring (from quick wins)

**Additional Changes Needed**:

**3.1 Stricter Beginning Validation**
```python
# Enhanced evaluation based on your feedback

def validate_beginning(thought_unit):
    """
    Does this clip START at the right place?

    RED FLAGS (auto-score ≤ 4):
    - "That's why..." (what's "that"?)
    - "So the point is..." (starting with conclusion?)
    - "And then..." (starting mid-story?)
    - Pronouns without referents at start

    GREEN FLAGS (score 8-10):
    - Clear topic introduction
    - Problem statement
    - Question being answered
    - Context provided
    """
```

**3.2 Closure Detection**
```python
def validate_ending(thought_unit):
    """
    Does this clip END at the right place?

    RED FLAGS (auto-score ≤ 4):
    - Trails off mid-thought
    - Cuts off before resolution
    - Ends with "and so..." (more coming?)
    - Topic shifts but clip doesn't include new topic

    GREEN FLAGS (score 8-10):
    - Clear conclusion ("So the point is...")
    - Returns to initial question
    - Provides closure/satisfaction
    - Natural semantic boundary
    """
```

**3.3 Two-Tier Pass System** (from your clip_04 feedback)
```python
def determine_verdict(thought_unit):
    """
    Two ways to pass:

    Tier 1: Rhetorical Excellence (PASS)
    - beginning_score ≥ 7
    - middle_score ≥ 7
    - ending_score ≥ 7
    - No unresolved references
    → standalone_score ≥ 0.7

    Tier 2: High Interest Despite Imperfection (PASS)
    - interest_score ≥ 0.85 (very interesting)
    - beginning_score ≥ 5 (acceptable)
    - middle_score ≥ 7 (clear message)
    - ending_score ≥ 5 (acceptable)
    - No critical unresolved refs
    → standalone_score ≥ 0.6

    Tier 3: Good Enough (REVISE - include if needed)
    - Interest OR rhetorical quality is decent
    - standalone_score 0.5-0.7

    Tier 4: Reject
    - standalone_score < 0.5
    """
```

**Success Criteria**:
- Your clip_01 would still pass (Tier 2: high interest despite imperfection)
- Your clip_02 would pass (Tier 1: rhetorical excellence)
- Your clip_03 would pass (Tier 1: perfect structure)
- Your clip_04 would pass as REVISE (Tier 3: good enough)
- Pass rate: 50-70% of thought units

---

### Phase 4: Integration & Testing (3-4 days)

**4.1 End-to-End Pipeline**
```python
def process_video_editorial_v2(video_path, target_clips):
    """
    Complete pipeline with thought unit construction

    1. Transcribe
    2. Detect thought seeds (target × 4)
    3. Construct thought units (premise → claim → resolution)
    4. Validate rhetorical completeness
    5. Deduplicate similar ideas
    6. Select top N (PASS + REVISE if needed)
    7. Package with titles

    Return: List of complete, standalone clips
    """
```

**4.2 Test Matrix**

| Content Type | Test Video | Expected Clips | Success = |
|--------------|------------|----------------|-----------|
| Sermon/Religious | test_007 | 8-10 | Find your 4 clips |
| Educational | Khan Academy | 8-10 | Complete explanations |
| Interview/Podcast | Joe Rogan | 8-10 | Complete stories/insights |
| Tech Talk | Conference talk | 6-8 | Complete concepts |
| Business Advice | Gary Vee | 8-10 | Complete advice units |

**4.3 Quality Metrics**
```python
metrics = {
    # Detection metrics
    'seeds_detected': 40,
    'thought_units_constructed': 35,
    'thought_units_validated': 24,
    'final_clips_selected': 10,

    # Quality metrics
    'avg_beginning_score': 7.8,
    'avg_middle_score': 8.2,
    'avg_ending_score': 7.5,
    'avg_standalone_score': 0.75,

    # User satisfaction (manual review)
    'clips_user_would_keep': 8,
    'usability_rate': 0.80,  # 80% usable

    # Completeness
    'clips_with_premise': 10,  # 100%
    'clips_with_resolution': 10,  # 100%
    'clips_with_unresolved_refs': 0,  # 0%
}
```

**Success Criteria**:
- **test_007**: Generate 8-10 clips, user keeps 7-8 (70-80% usability)
- **Find your clips**: System detects your clip_02, clip_03, clip_04 equivalents
- **No fragments**: 0% clips starting with "That's why..." or ending mid-thought
- **Complete thoughts**: 100% have clear beginning/middle/end
- **User testimony**: "These feel professionally edited"

---

## Implementation Timeline

### Week 1: Phase 1 - Thought Seed Detection
**Days 1-2**: Diagnostic + Understanding
- Run test_007 with current system (--export-layers)
- Analyze exactly where it fails
- Map your 4 clips to transcript timestamps
- Understand why seeds weren't detected

**Days 3-4**: Sliding Window Detection
- Implement 2-minute sliding window approach
- Find 3-5 seeds per window
- Test: Should find 40-50 seeds in test_007

**Day 5**: Validation
- Run on test_007
- Verify: Found seeds at positions of your 4 clips?
- Tune threshold if needed

### Week 2: Phase 2 - Thought Unit Construction
**Days 1-2**: Backward Search (Premise)
- Implement premise boundary detection
- Use semantic similarity + discourse markers
- Test on your clip_03: Does it find the premise?

**Days 3-4**: Forward Search (Resolution)
- Implement resolution boundary detection
- Use conclusion markers + semantic closure
- Test on your clip_03: Does it find the resolution?

**Day 5**: Thought Unit Validation
- Ensure units have all three parts
- Test on test_007: 40 seeds → 30-35 thought units?

### Week 3: Phase 3 - Enhanced Validation
**Days 1-2**: Stricter Beginning/Ending Rules
- Implement red flag detection
- Implement green flag detection
- Test: Would your clip_01 get flagged for weak beginning?

**Days 3-4**: Two-Tier Pass System
- Implement interest-based pass
- Implement "good enough" REVISE tier
- Test: All 4 of your clips should pass or REVISE

**Day 5**: Integration with Quick Wins
- Merge with deduplication (already done)
- Merge with rejection tracking (already done)
- Test full pipeline

### Week 4: Phase 4 - Testing & Tuning
**Days 1-3**: Test Matrix
- Test on 5 diverse videos
- Measure quality metrics
- Tune thresholds

**Days 4-5**: User Validation
- You test on YOUR videos
- Manual review of outputs
- Adjust based on feedback

**Total: 20 days (4 weeks)**

---

## Cost Analysis

### Current Cost (1 clip from test_007)
- Total: ~$0.23

### After Transformation (10 clips from test_007)
**With GPT-4o (current model)**:
- Thought seed detection (50 seeds): ~$0.10
- Premise/resolution search (50 units): ~$1.00
- Rhetorical validation (50 units): ~$1.50
- Packaging (10 clips): ~$0.20
- **Total: ~$2.80 per video**

**With GPT-4o-mini (recommended)**:
- Thought seed detection (50 seeds): ~$0.02
- Premise/resolution search (50 units): ~$0.20
- Rhetorical validation (50 units): ~$0.30
- Packaging (10 clips): ~$0.04
- **Total: ~$0.56 per video**

**ROI**:
- Cost: 2.4x increase (from $0.23 to $0.56)
- Output: 10x increase (from 1 clip to 10 clips)
- Quality: 4x increase (from 25% usable to 80% usable)
- **Overall value**: ~17x improvement for 2.4x cost

---

## Risk Mitigation

### Risk 1: Premise/Resolution Search is Hard
**Mitigation**:
- Start with simple heuristics (discourse markers)
- Use GPT as fallback for complex cases
- Accept "good enough" boundaries initially
- Iterate based on test results

### Risk 2: Processing Time Increases
**Mitigation**:
- Parallel processing for thought unit construction
- Cache intermediate results
- Progress indicators for user
- Async processing option

### Risk 3: Content Type Bias
**Mitigation**:
- Test on diverse content types early
- Tune per-content-type if needed
- Allow user to specify content type hint
- Monitor performance across types

### Risk 4: Over-Engineering
**Mitigation**:
- Build incrementally (Phase 1, test, Phase 2, test...)
- Ship Phase 1+2 as v0.4.0 beta if valuable enough
- Get user feedback between phases
- Don't wait for perfection

---

## Success Definition

**"When can we say this is fixed?"** (from EDITORIAL_COMPARISON.md)

✅ 90%+ of generated clips are used without editing
✅ 0 clips with unresolved references
✅ Users say: "These feel professionally edited"
✅ Each clip has clear beginning, middle, end
✅ No duplicate ideas across clips
✅ Variable lengths accepted based on thought completion

**Specific to your feedback**:
✅ System finds all 4 of your clips from test_007
✅ Clip_03 equivalent (700-word complete argument) is detected and kept
✅ No clips starting with "That's why..." without context
✅ Every clip feels complete, not fragmentary

---

## Deliverables

### Code
- `engine/arena/editorial/thought_seed_detector.py` (renamed from moment_detector)
- `engine/arena/editorial/thought_unit_builder.py` (enhanced boundary_analyzer)
- `engine/arena/editorial/rhetorical_validator.py` (enhanced context_refiner)
- `engine/arena/editorial/adapter.py` (updated pipeline)

### Documentation
- `THOUGHT_UNIT_ARCHITECTURE.md` (how the new system works)
- `EDITORIAL_VALIDATION_GUIDE.md` (what makes clips pass/fail)
- Updated `README.md` with new capabilities

### Tests
- Unit tests for premise detection
- Unit tests for resolution detection
- Integration tests on test_007 (your 4 clips)
- E2E tests on diverse content types

### CLI
- `arena process --editorial-v2` (new system, beta)
- `arena process` (current system, for comparison)
- `--export-thought-units` (debug intermediate results)

---

## Next Steps - Your Approval Needed

**I need from you**:

1. ✅ **Approve this plan?** Any changes needed?

2. 📁 **test_007 video file?** Need it for testing
   - Or provide different 15-min sermon/talk for testing

3. 📍 **Timestamp your 4 clips?**
   - clip_01: [XX:XX] to [XX:XX]
   - clip_02: [XX:XX] to [XX:XX]
   - clip_03: [XX:XX] to [XX:XX]
   - clip_04: [XX:XX] to [XX:XX]
   - This gives me ground truth for testing

4. 🎯 **Priority: Speed vs Perfection?**
   - Ship Phase 1+2 after 2 weeks for early feedback?
   - Or complete all 4 phases before shipping?

5. 💰 **Cost tolerance confirmed?**
   - $0.56/video with gpt-4o-mini acceptable?
   - Or stay with gpt-4o for quality ($2.80/video)?

**Once approved, I'll start with**:
- Week 1, Day 1: Diagnostic run on test_007 (if you provide video)
- OR Week 1, Day 3: Start sliding window implementation (if no video available)

**Ready to transform Arena's editorial system?**
