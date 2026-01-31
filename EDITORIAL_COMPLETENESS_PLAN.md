# Arena Editorial Completeness - Implementation Plan

## Executive Summary

**Problem**: Arena generates clips at semantic peaks (emotion/insight) rather than rhetorical boundaries (complete thoughts), producing contextually dependent clips that feel unfinished.

**Goal**: Transform Arena from a "moment detector" into a "thought constructor" that produces standalone, rhetorically complete clips.

**Impact**: This is the most critical quality issue - fixes will dramatically improve clip usability and trust in automation.

---

## Phase 1: Thought Unit Detection (Layer 1 Redesign)

### Current Behavior
- Detects sentences with high emotional/insight scores
- Treats each sentence as independent
- Optimizes for "interesting language"

### Target Behavior
- Detects **thought units** (premise → claim → resolution)
- Identifies where thoughts BEGIN (not just peak)
- Maps rhetorical relationships between sentences

### Implementation Tasks

#### 1.1 Define Thought Unit Structure
**File**: `engine/arena/editorial/thought_unit.py` (NEW)

```python
@dataclass
class ThoughtUnit:
    """A complete rhetorical unit"""
    premise_start: float      # Where setup begins
    claim_peak: float          # Where core insight appears
    resolution_end: float      # Where thought completes

    premise_text: str          # Setup sentences
    claim_text: str            # Core statement
    resolution_text: str       # Supporting reasoning/conclusion

    rhetorical_type: str       # story | argument | example | teaching
    dependency_level: str      # standalone | needs_context | unsalvageable

    def is_complete(self) -> bool:
        """Validate rhetorical completeness"""
        return (
            self.has_premise() and
            self.has_claim() and
            self.has_resolution() and
            self.dependency_level == "standalone"
        )
```

#### 1.2 Enhance Layer 1 Moment Detector
**File**: `engine/arena/editorial/layer1_moment_detector.py`

**Changes**:
```python
# OLD: Detect interesting sentences
def detect_moments(self, transcript):
    moments = []
    for sentence in sentences:
        if is_emotionally_strong(sentence):
            moments.append(sentence)
    return moments

# NEW: Detect thought units
def detect_thought_units(self, transcript):
    thought_units = []

    # 1. Find claim peaks (emotional/insight highs)
    claim_peaks = self._detect_claim_peaks(transcript)

    # 2. For each peak, find its premise
    for peak in claim_peaks:
        premise = self._find_premise_backward(peak, transcript)
        resolution = self._find_resolution_forward(peak, transcript)

        thought = ThoughtUnit(
            premise_start=premise.start,
            claim_peak=peak.timestamp,
            resolution_end=resolution.end,
            ...
        )

        # 3. Validate completeness
        if thought.is_complete():
            thought_units.append(thought)

    return thought_units
```

**New Methods Required**:
- `_detect_claim_peaks()` - Current moment detection logic
- `_find_premise_backward()` - **NEW**: Search backward for thought beginning
- `_find_resolution_forward()` - **NEW**: Search forward for resolution
- `_classify_rhetorical_type()` - **NEW**: Identify thought structure
- `_assess_dependency()` - **NEW**: Check if standalone

#### 1.3 Premise Detection Logic
**Prompt Pattern** (for GPT-4o-mini):

```
You are analyzing a transcript to find where a THOUGHT BEGINS.

CLAIM (what we're working backward from):
"{peak_sentence}"

CONTEXT (preceding sentences):
"{previous_5_sentences}"

Your task:
1. Identify the FIRST sentence where this thought is introduced or motivated
2. Look for:
   - Setup phrases: "So here's the thing...", "Let me explain...", "Think about this..."
   - Question that the claim answers
   - Problem that the claim solves
   - Story that motivates the claim

Return:
{
  "premise_start_index": <sentence_index>,
  "premise_text": "<first sentence of the thought>",
  "premise_type": "question|problem|story|direct_claim",
  "reasoning": "Why this is the true beginning"
}
```

#### 1.4 Resolution Detection Logic
**Prompt Pattern**:

```
You are analyzing a transcript to find where a THOUGHT COMPLETES.

CLAIM (core statement):
"{claim_sentence}"

CONTEXT (following sentences):
"{next_5_sentences}"

Your task:
1. Identify the LAST sentence needed for the thought to feel complete
2. Look for:
   - Supporting reasoning
   - Examples that clarify
   - Natural transition to new topic
   - Rhetorical closure signal

Return:
{
  "resolution_end_index": <sentence_index>,
  "resolution_text": "<final sentence>",
  "completion_type": "reasoning|example|transition|restatement",
  "is_complete": true|false,
  "reasoning": "Why this completes the thought"
}
```

---

## Phase 2: Rhetorical Boundary Refinement (Layer 2 Redesign)

### Current Behavior
- Adjusts boundaries for sentence completeness
- Optimizes for grammatical correctness
- Uses audio energy for fine-tuning

### Target Behavior
- Validates premise inclusion
- Confirms resolution completeness
- Rejects clips without rhetorical closure

### Implementation Tasks

#### 2.1 Thought Boundary Validator
**File**: `engine/arena/editorial/layer2_boundary_analyzer.py`

**New Method**:
```python
def validate_thought_boundaries(self, thought_unit):
    """
    Validate that boundaries capture complete thought

    Returns:
        {
            'is_valid': bool,
            'issues': List[str],
            'suggested_start': float,
            'suggested_end': float,
            'confidence': float
        }
    """
    issues = []

    # Check 1: Does it start with premise/setup?
    if not self._starts_with_premise(thought_unit):
        issues.append("Starts mid-thought (missing premise)")
        thought_unit = self._expand_backward_to_premise(thought_unit)

    # Check 2: Does it end with resolution?
    if not self._ends_with_resolution(thought_unit):
        issues.append("Ends before thought completes")
        thought_unit = self._expand_forward_to_resolution(thought_unit)

    # Check 3: Is it standalone?
    if not self._is_contextually_standalone(thought_unit):
        issues.append("Contains unresolved references")
        return {'is_valid': False, 'issues': issues, 'confidence': 0.0}

    return {
        'is_valid': len(issues) == 0,
        'issues': issues,
        'suggested_start': thought_unit.premise_start,
        'suggested_end': thought_unit.resolution_end,
        'confidence': self._calculate_completeness_confidence(thought_unit)
    }
```

#### 2.2 Standalone Context Validator
**New Method**:
```python
def _is_contextually_standalone(self, thought_unit):
    """
    Check for unresolved references that break standalone comprehension

    Red flags:
    - "That's why..." (what's "that"?)
    - "So the point is..." (what point?)
    - "This is the problem..." (which problem?)
    - Pronouns without clear antecedents
    - Demonstrative references ("this", "that", "these")
    """

    # Use GPT-4o-mini to analyze
    prompt = f"""
    Analyze if this clip is STANDALONE (understandable without prior context).

    CLIP TEXT:
    {thought_unit.full_text}

    Check for:
    1. Unresolved pronouns (he, she, it, they - without clear reference)
    2. Demonstrative references (this, that, these - pointing to unknown things)
    3. Incomplete comparisons ("better than..." - better than what?)
    4. Assumed context ("that's why..." - why what?)

    Return:
    {{
      "is_standalone": true|false,
      "unresolved_references": [list of phrases],
      "missing_context": "What a viewer would need to know",
      "fix_suggestion": "How to make it standalone (or mark unsalvageable)"
    }}
    """

    response = self._call_gpt(prompt)
    return response['is_standalone']
```

---

## Phase 3: Completeness Validation (Layer 3 Enhancement)

### Current Behavior
- Refines boundaries based on sentence structure
- Adds padding for natural flow
- Validates technical correctness

### Target Behavior
- Validates **rhetorical completeness**
- Rejects incomplete thoughts
- Measures "cognitive closure"

### Implementation Tasks

#### 3.1 Rhetorical Completeness Scorer
**File**: `engine/arena/editorial/layer3_context_refiner.py`

**New Validation**:
```python
def assess_rhetorical_completeness(self, thought_unit):
    """
    Score a thought unit on editorial completeness

    Returns score 0.0-1.0 and detailed breakdown
    """

    prompt = f"""
    You are a professional video editor evaluating if this clip is EDITORIALLY COMPLETE.

    CLIP:
    {thought_unit.full_text}

    Rate these dimensions (0-10 each):

    1. SETUP: Does the clip establish what it's about?
       - 0: Starts mid-argument
       - 10: Clear premise/question/problem introduced

    2. DEVELOPMENT: Is the core idea fully expressed?
       - 0: Claim stated but not explained
       - 10: Idea thoroughly developed with reasoning

    3. RESOLUTION: Does the clip feel finished?
       - 0: Ends abruptly, unresolved
       - 10: Natural stopping point, thought complete

    4. STANDALONE: Can viewers understand without context?
       - 0: Requires prior knowledge
       - 10: Completely self-contained

    5. COGNITIVE CLOSURE: Does it satisfy the "itch" it creates?
       - 0: Raises question but doesn't answer
       - 10: Every question posed is resolved

    Return:
    {{
      "setup_score": <0-10>,
      "development_score": <0-10>,
      "resolution_score": <0-10>,
      "standalone_score": <0-10>,
      "cognitive_closure_score": <0-10>,
      "overall_completeness": <0-10>,
      "editorial_decision": "PUBLISH|NEEDS_WORK|REJECT",
      "reasoning": "Specific editorial feedback",
      "improvement_suggestions": []
    }}
    """

    response = self._call_gpt(prompt)

    # Require minimum 7/10 on all dimensions for PUBLISH
    min_threshold = 7.0
    can_publish = all([
        response['setup_score'] >= min_threshold,
        response['development_score'] >= min_threshold,
        response['resolution_score'] >= min_threshold,
        response['standalone_score'] >= min_threshold,
        response['cognitive_closure_score'] >= min_threshold
    ])

    return {
        'completeness_score': response['overall_completeness'] / 10.0,
        'editorial_decision': 'PUBLISH' if can_publish else 'REJECT',
        'breakdown': response,
        'passed': can_publish
    }
```

---

## Phase 4: Deduplication & Selection (Layer 4 Enhancement)

### Current Behavior
- Removes overlapping clips by timestamp
- Keeps highest-scoring variants
- May keep multiple versions of same idea

### Target Behavior
- Detects **semantic duplication** (same idea, different timestamps)
- Selects ONE best expression of each unique idea
- Reduces output volume, increases variety

### Implementation Tasks

#### 4.1 Semantic Deduplication
**File**: `engine/arena/editorial/layer4_packaging.py`

**New Method**:
```python
def deduplicate_by_core_idea(self, thoughts: List[ThoughtUnit]):
    """
    Group thoughts by core idea, select best expression of each

    Current bug: Multiple clips saying "avoid debt" from different timestamps
    Fix: Recognize these as duplicates, keep only the best one
    """

    # Step 1: Cluster by semantic similarity
    idea_clusters = self._cluster_by_core_idea(thoughts)

    # Step 2: For each cluster, select the best variant
    unique_thoughts = []
    for cluster in idea_clusters:
        best = self._select_best_variant(cluster)
        unique_thoughts.append(best)

    return unique_thoughts

def _cluster_by_core_idea(self, thoughts):
    """
    Use embeddings to group thoughts expressing same idea
    """
    from sklearn.cluster import DBSCAN
    import numpy as np

    # Get embeddings for each thought's core claim
    embeddings = []
    for thought in thoughts:
        emb = self._get_embedding(thought.claim_text)
        embeddings.append(emb)

    # Cluster with tight threshold (0.15 = very similar)
    embeddings_array = np.array(embeddings)
    clustering = DBSCAN(eps=0.15, min_samples=1, metric='cosine')
    labels = clustering.fit_predict(embeddings_array)

    # Group thoughts by cluster
    clusters = {}
    for idx, label in enumerate(labels):
        if label not in clusters:
            clusters[label] = []
        clusters[label].append(thoughts[idx])

    return list(clusters.values())

def _select_best_variant(self, cluster: List[ThoughtUnit]):
    """
    From multiple variants of same idea, pick the best one

    Criteria:
    1. Highest completeness score
    2. Best standalone comprehension
    3. Most engaging delivery (emotion + clarity)
    """

    scored = []
    for thought in cluster:
        score = (
            thought.completeness_score * 0.4 +
            thought.standalone_score * 0.4 +
            thought.engagement_score * 0.2
        )
        scored.append((score, thought))

    scored.sort(reverse=True)
    return scored[0][1]  # Best variant
```

---

## Phase 5: Variable Length Acceptance

### Current Behavior
- Strong preference for 30-60s clips
- Penalizes longer clips
- Forces thoughts into time boxes

### Target Behavior
- Accept **natural length** of complete thoughts
- Allow 15s-120s range
- Prioritize completeness over duration

### Implementation Tasks

#### 5.1 Remove Length Penalties
**Files to modify**:
- `layer3_context_refiner.py` - Remove duration scoring
- `layer4_packaging.py` - Update filtering logic

**Changes**:
```python
# OLD
def score_clip(clip):
    duration_penalty = 0 if 30 <= duration <= 60 else -0.3
    return base_score + duration_penalty

# NEW
def score_clip(clip):
    # Accept any duration if thought is complete
    if clip.is_rhetorically_complete:
        duration_bonus = 0  # No penalty OR bonus
    else:
        # Only penalize incomplete thoughts
        duration_penalty = -0.5

    return base_score + duration_bonus
```

#### 5.2 Update Platform Formatting
**Consideration**: TikTok/Instagram have max durations

**Solution**:
```python
# After generating complete thoughts, THEN adapt to platform
def adapt_to_platform(thought_unit, platform):
    max_duration = PLATFORM_LIMITS[platform]  # e.g., 60s for TikTok

    if thought_unit.duration > max_duration:
        # Option 1: Reject (thought too long for platform)
        # Option 2: Intelligently compress (remove examples, not core)
        # Option 3: Split into Part 1/2

        return compress_thought_intelligently(thought_unit, max_duration)

    return thought_unit
```

---

## Phase 6: Integration & Testing

### 6.1 Update Pipeline Flow
**File**: `engine/arena_process.py`

```python
# OLD FLOW
1. Transcribe
2. Detect moments (sentences)
3. Expand boundaries
4. Validate
5. Package

# NEW FLOW
1. Transcribe
2. Detect thought units (premise → claim → resolution)
3. Validate rhetorical completeness
4. Expand/reject based on completeness
5. Deduplicate by core idea
6. Package best variants
7. Adapt to platform if needed
```

### 6.2 Metrics to Track
**Add to output**:
```json
{
  "thoughts_detected": 45,
  "thoughts_complete": 12,
  "thoughts_rejected": 33,
  "rejection_reasons": {
    "no_premise": 15,
    "no_resolution": 10,
    "not_standalone": 8
  },
  "duplicates_merged": 8,
  "final_clips": 4,
  "avg_completeness_score": 0.85
}
```

### 6.3 Test Cases
**Create test suite**:
- `tests/editorial/test_thought_units.py`
- `tests/editorial/test_premise_detection.py`
- `tests/editorial/test_standalone_validation.py`
- `tests/editorial/test_deduplication.py`

**Test videos**:
1. Sermon (long argumentative structure)
2. Podcast (conversational, many tangents)
3. Teaching (instructional, step-by-step)
4. Interview (Q&A format)

---

## Success Criteria

### Quantitative
- ✅ 90%+ of generated clips score 8+/10 on completeness
- ✅ 0 clips with unresolved references (standalone)
- ✅ 50%+ reduction in duplicate ideas
- ✅ Accept variable lengths (15-120s based on thought, not preference)

### Qualitative
- ✅ Clips feel like human-edited selections
- ✅ Viewers don't need context to understand
- ✅ Each clip has clear beginning, development, resolution
- ✅ No "mid-thought" starts or abrupt endings

### User Feedback
- ✅ "These clips feel professionally edited"
- ✅ "I don't need to manually adjust boundaries anymore"
- ✅ "The clips are actually usable without editing"

---

## Implementation Timeline

### Sprint 1 (Week 1-2): Foundation
- [ ] Create ThoughtUnit data structure
- [ ] Implement premise detection (backward search)
- [ ] Implement resolution detection (forward search)
- [ ] Update Layer 1 to detect thought units

### Sprint 2 (Week 3-4): Validation
- [ ] Build standalone context validator
- [ ] Create rhetorical completeness scorer
- [ ] Update Layer 3 with new validation
- [ ] Add rejection logic for incomplete thoughts

### Sprint 3 (Week 5-6): Deduplication
- [ ] Implement semantic clustering
- [ ] Build variant selection logic
- [ ] Update Layer 4 packaging
- [ ] Remove duration penalties

### Sprint 4 (Week 7-8): Testing & Refinement
- [ ] Build test suite
- [ ] Run on diverse content types
- [ ] Measure completeness scores
- [ ] Refine prompts based on results

---

## Risk Assessment

### High Risk
1. **Increased processing time**: More analysis per thought unit
   - Mitigation: Use gpt-4o-mini for premise/resolution detection

2. **Lower clip count**: Stricter completeness may reduce output
   - Mitigation: This is intentional - quality over quantity

3. **False rejections**: May reject valid clips as incomplete
   - Mitigation: Tune thresholds, add override options

### Medium Risk
1. **Prompt tuning complexity**: Many new prompts to optimize
   - Mitigation: Start with clear rubrics, iterate based on results

2. **Variable length clips**: Harder to format for platforms
   - Mitigation: Post-process for platform after validation

---

## Next Steps

1. **Review this plan** - Confirm approach aligns with vision
2. **Prioritize phases** - Which to implement first?
3. **Allocate resources** - Development time needed
4. **Set success metrics** - How to measure improvement?
5. **Create test content** - Videos that expose current failures

---

## Conclusion

This is not a prompt tweak. This is an **architectural redesign** of Arena's editorial logic.

**Current**: Find interesting sentences
**Future**: Construct complete thoughts

The work is substantial but necessary. Arena cannot claim "professional quality" until it masters rhetorical completeness.

Once implemented, Arena will produce clips that feel **edited by a human**, not detected by AI.
