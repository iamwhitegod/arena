# Arena Editorial Architecture: 4-Layer AI System

## Problem with Single-Layer Design

**Current Approach** (Single AI Call):
```
One GPT-4o prompt tries to:
- Identify interesting moments
- Determine boundaries
- Ensure standalone context
- Create titles/metadata
```

**Issues**:
1. **Conflicting Objectives**: "Find interesting moments" vs. "Ensure completeness" creates tension
2. **No Validation**: Can't verify if a clip makes sense standalone
3. **Premature Packaging**: Titles before boundaries are finalized
4. **All-or-Nothing**: Can't iterate on one aspect without redoing everything

---

## 4-Layer Editorial System

### Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    VIDEO TRANSCRIPT                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: MOMENT DETECTOR                                    │
│  "What's interesting?"                                       │
│  → Identifies raw moments of interest (hooks, insights, etc) │
│  → Loose timestamps, no completeness guarantee               │
└─────────────────────────────────────────────────────────────┘
                            ↓
              [Raw Moments: 20-30 candidates]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 2: THOUGHT BOUNDARY ANALYZER                          │
│  "Where does this idea truly start/end?"                     │
│  → Expands/contracts each moment to thought boundaries       │
│  → Finds natural beginning (setup/context) and end (payoff)  │
└─────────────────────────────────────────────────────────────┘
                            ↓
         [Complete Thoughts: 15-20 candidates]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 3: STANDALONE CONTEXT REFINER                         │
│  "Can this live alone?"                                      │
│  → Tests if clip is understandable without prior context     │
│  → Validates: Who/what/why are clear                         │
│  → Filters/adjusts clips that lack context                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
          [Validated Clips: 10-15 standalone]
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Layer 4: PACKAGING LAYER                                    │
│  "How do we present this?"                                   │
│  → Generates titles, descriptions, hashtags                  │
│  → Suggests thumbnail timestamps                             │
│  → Creates social media copy                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
              [Packaged Final Clips]
```

---

## Layer 1: Moment Detector

### Purpose
Identify potentially interesting moments WITHOUT worrying about completeness.

### Prompt Strategy
```
"Scan this transcript and mark every moment that contains:
- A hook or attention-grabbing statement
- An insight or 'aha' moment
- Controversial or surprising statement
- Actionable advice
- Emotional peak
- Story climax
- Problem statement or solution reveal

For each moment, provide:
- Approximate center timestamp
- Type of moment (hook/insight/advice/story/emotional)
- Interest score (0.0-1.0)
- 1-sentence description

Do NOT worry about:
- Whether it's complete
- Whether it has context
- Exact start/end boundaries

Goal: Cast a wide net. We'll refine later."
```

### Model Choice
**GPT-4o** - Needs strong pattern recognition for diverse content types

### Output Format
```json
{
  "moments": [
    {
      "center_time": 145.2,
      "type": "insight",
      "interest_score": 0.92,
      "description": "Explains why most startups fail at PMF",
      "context_snippet": "...the real issue isn't finding product-market fit..."
    }
  ]
}
```

### Design Decisions
- **20-30 candidates**: Over-identify rather than miss good content
- **Center timestamp**: Not start/end - just "around here"
- **No completeness check**: That's Layer 3's job
- **Context snippet**: For human debugging/review

---

## Layer 2: Thought Boundary Analyzer

### Purpose
For each moment, find where the complete thought ACTUALLY begins and ends.

### Approach
For each moment from Layer 1:
1. Look backward: Where does the speaker START setting up this idea?
2. Look forward: Where does the idea reach COMPLETION/PAYOFF?
3. Identify natural entry/exit points

### Prompt Strategy
```
"Given this moment of interest:
- Center time: {center_time}
- Type: {type}
- Description: {description}

Context (30s before and after):
{transcript_context}

Your job: Find the TRUE boundaries of this complete thought.

Start Boundary: Look backward from center time:
- Where does the speaker begin setting up this idea?
- Where's the natural entry point for someone jumping in?
- Include necessary context/setup

End Boundary: Look forward from center time:
- Where does the idea reach its payoff/conclusion?
- Where's the natural exit point?
- Include the resolution/takeaway

Return:
{
  "start_time": X,
  "end_time": Y,
  "start_reasoning": "Why this start point",
  "end_reasoning": "Why this end point",
  "completeness_score": 0.0-1.0
}

Key: A complete thought has setup → development → payoff."
```

### Model Choice
**GPT-4o** - Needs deep comprehension of narrative structure

### Output Format
```json
{
  "moment_id": "moment_001",
  "original_center": 145.2,
  "boundaries": {
    "start_time": 132.8,
    "end_time": 168.5,
    "duration": 35.7,
    "start_reasoning": "Speaker introduces problem context",
    "end_reasoning": "Completes explanation with concrete example",
    "completeness_score": 0.88
  }
}
```

### Design Decisions
- **Per-moment analysis**: Each moment gets individual attention
- **Reasoning required**: AI must explain boundary choices
- **Completeness score**: Self-assessment for Layer 3 validation
- **30s context window**: Balance between context and token cost

---

## Layer 3: Standalone Context Refiner

### Purpose
The quality gate: Verify each clip can be understood in isolation.

### Core Questions
For a clip to pass:
1. **Who**: Is the speaker/subject clear? (Or doesn't matter?)
2. **What**: Is the topic/situation explained?
3. **Why**: Is the relevance/importance clear?
4. **Assumptions**: Does it require prior knowledge to understand?

### Prompt Strategy
```
"You are a context validator. Your job: Can someone who JUST clicked on this clip
understand and appreciate it WITHOUT watching what came before?

Clip transcript:
{clip_transcript}

Evaluate:
1. Who is speaking/who is this about? Is that clear or irrelevant?
2. What topic/situation is being discussed? Is that clear?
3. Why should the viewer care? Is the stakes/relevance clear?
4. Does this require prior context to understand?

Scoring:
- standalone_score: 0.0-1.0 (how well it works alone)
- missing_context: List what's unclear
- suggested_fixes: How to improve context

Pass threshold: 0.7+

If score < 0.7, suggest:
- Extend start to include more setup?
- Add verbal context (if speaker provides it nearby)?
- Reject if fundamentally requires prior knowledge
"
```

### Model Choice
**GPT-4o** or **GPT-4o-mini** - Context validation is somewhat simpler than boundary detection

### Output Format
```json
{
  "clip_id": "clip_001",
  "standalone_score": 0.75,
  "evaluation": {
    "who_clear": true,
    "what_clear": true,
    "why_clear": true,
    "requires_prior_knowledge": false
  },
  "missing_context": [],
  "suggested_fixes": [],
  "verdict": "PASS",
  "reasoning": "Topic is introduced clearly, stakes are explained, no prior knowledge needed"
}
```

### Verdicts
- **PASS**: standalone_score ≥ 0.7 → Include in final set
- **REVISE**: 0.4-0.69 with fixable issues → Adjust boundaries
- **REJECT**: < 0.4 or unfixable → Discard

### Design Decisions
- **Strict validation**: Better 8 great clips than 15 mediocre ones
- **Fixable vs. unfixable**: Some clips just reference earlier content
- **Pass threshold**: 0.7 is high bar for quality
- **Human-like evaluation**: "Can MY AUDIENCE understand this?"

---

## Layer 4: Packaging Layer

### Purpose
Polish and presentation after content is locked.

### Components

#### A. Title Generation
```
"Generate a compelling, specific title (max 60 chars) for this clip:

{clip_transcript}

Requirements:
- Specific, not generic
- Captures the core insight/hook
- Compelling for social media
- No clickbait - accurate representation

Examples of good titles:
- "Why most startups fail at product-market fit"
- "The counterintuitive secret to 10x growth"
- "Three mistakes that killed our MVP"

Avoid:
- Generic: "Important startup advice"
- Vague: "Interesting discussion"
- Clickbait: "You won't believe what happened next"
"
```

#### B. Description Generation
```
"Write a 2-3 sentence description for this clip:

{clip_transcript}

Format:
1. Hook sentence (what's interesting)
2. Context sentence (why it matters)
3. [Optional] Call-to-action

Target: Developers, founders, technical creators
Platform: Twitter/LinkedIn/YouTube Shorts
"
```

#### C. Hashtag Suggestion
```
"Suggest 5 relevant hashtags for this clip:

{clip_transcript}

Requirements:
- Mix of broad (#startups) and specific (#productmarketfit)
- Relevant to tech/business audience
- Searchable but not over-saturated
- No overly generic tags (#content, #video)
"
```

#### D. Thumbnail Timestamp
```
"Identify the best frame for a thumbnail from this clip:

Clip: {start_time} → {end_time}
Transcript: {clip_transcript}

Find:
- A moment of peak emotion/energy
- Or a clear visual of the speaker engaged
- Or a moment that represents the core idea

Return:
- thumbnail_time: Exact timestamp
- reasoning: Why this frame
"
```

### Model Choice
**GPT-4o-mini** - All packaging tasks are lighter, cost-optimize here

### Output Format
```json
{
  "clip_id": "clip_001",
  "packaging": {
    "title": "Why most startups fail at product-market fit",
    "description": "Most founders think PMF is about building features users want. The real issue is understanding what problem you're actually solving. Here's the framework that finally made it click.",
    "hashtags": ["#startups", "#productmarketfit", "#founders", "#entrepreneurship", "#saas"],
    "thumbnail_time": 145.8,
    "thumbnail_reasoning": "Speaker's hand gesture emphasizing key point",
    "social_copy": {
      "twitter": "The PMF mistake that kills 80% of startups 🚀\n\n(Watch the full breakdown)",
      "linkedin": "After 3 failed products, I finally understood product-market fit...",
      "youtube": "Why Most Startups Fail at Product-Market Fit"
    }
  }
}
```

---

## Pipeline Integration

### Sequential Processing
```python
def run_editorial_pipeline(transcript_data, video_path, num_clips=10):
    # Layer 1: Find interesting moments (20-30 candidates)
    moment_detector = MomentDetector(model="gpt-4o")
    raw_moments = moment_detector.detect(transcript_data)
    # Returns: ~25 moments

    # Layer 2: Expand to complete thoughts (15-20 candidates)
    boundary_analyzer = ThoughtBoundaryAnalyzer(model="gpt-4o")
    complete_thoughts = boundary_analyzer.analyze(raw_moments, transcript_data)
    # Returns: ~18 thoughts with clear boundaries

    # Layer 3: Validate standalone context (10-15 final clips)
    context_refiner = StandaloneContextRefiner(model="gpt-4o-mini")
    validated_clips = context_refiner.refine(complete_thoughts, transcript_data)
    # Returns: ~12 standalone clips (some rejected/revised)

    # Apply professional alignment (sentence boundaries)
    aligner = ProfessionalClipAligner()
    aligned_clips = aligner.align_clips(validated_clips, transcript_data, video_path)

    # Select top N by interest score
    top_clips = sorted(aligned_clips, key=lambda c: c['interest_score'], reverse=True)[:num_clips]

    # Layer 4: Package for distribution
    packager = PackagingLayer(model="gpt-4o-mini")
    final_clips = packager.package(top_clips, transcript_data)
    # Returns: Clips with titles, descriptions, hashtags, etc.

    return final_clips
```

### Parallel Processing (Optimization)
```python
# Layers 2-4 can process clips in parallel
from concurrent.futures import ThreadPoolExecutor

# Layer 2: Analyze all moments in parallel
with ThreadPoolExecutor(max_workers=5) as executor:
    complete_thoughts = list(executor.map(
        lambda m: boundary_analyzer.analyze_single(m, transcript_data),
        raw_moments
    ))

# Layer 3: Validate all thoughts in parallel
with ThreadPoolExecutor(max_workers=5) as executor:
    validation_results = list(executor.map(
        lambda t: context_refiner.validate_single(t, transcript_data),
        complete_thoughts
    ))
```

---

## Cost Analysis

### Token Estimates (per video)

**Layer 1: Moment Detection**
- Input: Full transcript (~5000 tokens)
- Output: 25 moments (~1000 tokens)
- Model: GPT-4o
- Cost: ~$0.20 per video

**Layer 2: Boundary Analysis** (per moment)
- Input: Context window (~500 tokens) × 25 moments
- Output: Boundaries (~200 tokens) × 25 moments
- Model: GPT-4o
- Cost: ~$0.50 per video

**Layer 3: Context Validation** (per thought)
- Input: Clip transcript (~300 tokens) × 18 thoughts
- Output: Validation (~150 tokens) × 18 thoughts
- Model: GPT-4o-mini
- Cost: ~$0.05 per video

**Layer 4: Packaging** (per clip)
- Input: Clip transcript (~300 tokens) × 10 clips
- Output: Full package (~400 tokens) × 10 clips
- Model: GPT-4o-mini
- Cost: ~$0.03 per video

**Total: ~$0.78 per video** (vs. current ~$0.20)

**Trade-off**: 4x cost increase for significantly better clip quality

---

## Advantages Over Single-Layer

### 1. Separation of Concerns
Each layer has ONE job, does it well

### 2. Explicit Quality Gates
Layer 3 is a hard validation step - no "maybe good enough"

### 3. Iterative Refinement
Can re-run Layer 3/4 without redoing Layer 1/2

### 4. Better Debugging
Can inspect output at each stage:
- "Are we finding interesting moments?" → Check Layer 1
- "Are boundaries correct?" → Check Layer 2
- "Why did clips get rejected?" → Check Layer 3
- "Are titles compelling?" → Check Layer 4

### 5. Model Optimization
Use expensive models where needed (Layers 1-2), cheap models where possible (Layers 3-4)

### 6. Solves Short Clip Problem
**Layer 2** ensures complete thoughts, **Layer 3** validates standalone context - no more 0-1s garbage clips

### 7. Content-First Design
Boundaries are determined by thought completeness (Layer 2) + standalone context (Layer 3), not arbitrary time limits

---

## Implementation Strategy

### Phase 1: Core Architecture
1. Create `arena/editorial/` module
2. Implement base classes:
   - `MomentDetector`
   - `ThoughtBoundaryAnalyzer`
   - `StandaloneContextRefiner`
   - `PackagingLayer`
3. Define interfaces between layers

### Phase 2: Layer Implementation
1. Implement Layer 1 (Moment Detection)
2. Test: Does it find all interesting moments?
3. Implement Layer 2 (Boundary Analysis)
4. Test: Are boundaries complete?
5. Implement Layer 3 (Context Validation)
6. Test: Pass rate, rejection reasons
7. Implement Layer 4 (Packaging)
8. Test: Title quality, description clarity

### Phase 3: Pipeline Integration
1. Update `arena_process.py` to use 4-layer system
2. Add progress indicators per layer
3. Export intermediate results for debugging
4. Add CLI flags for layer control

### Phase 4: Optimization
1. Parallelize Layer 2/3 processing
2. Add caching for expensive operations
3. Batch API calls where possible
4. Monitor cost vs. quality

---

## Future Enhancements

### A. Feedback Loop
```
Packaging Layer → User ratings → Moment Detector
```
Learn what types of moments produce highest-rated clips

### B. Multi-Pass Refinement
If Layer 3 rejects too many clips, Layer 2 can re-analyze with different parameters

### C. Audience Adaptation
Layer 4 can generate different packaging for different platforms:
- YouTube: Longer descriptions
- TikTok: Shorter, punchier
- LinkedIn: More professional tone

### D. Visual Analysis
Layer 1 could also analyze video frames, not just transcript:
- Scene changes
- Speaker energy (facial expressions)
- Visual highlights (slides, demos)

---

## Success Metrics

### Layer 1 (Moment Detection)
- Recall: % of human-identified moments found
- Precision: % of AI moments that humans agree are interesting

### Layer 2 (Boundaries)
- Completeness: % of clips with full thought arcs
- Alignment: How well boundaries match sentence boundaries

### Layer 3 (Context)
- Pass rate: % of clips passing standalone test
- Rejection analysis: Why clips fail

### Layer 4 (Packaging)
- Title quality: Human ratings 1-5
- Engagement: CTR on social media

### Overall Pipeline
- Clips per video: Should be 8-15 high-quality
- Manual review time: Should decrease (fewer bad clips)
- User satisfaction: Better than single-layer approach

---

## Conclusion

The 4-layer editorial architecture treats video clip generation as a **real editorial process**, not a single AI call. Each layer has clear responsibilities, explicit validation, and focused optimization.

This solves the fundamental problem: **You can't identify interesting moments AND ensure completeness in one step.** Separating these concerns produces better clips at slightly higher cost - a worthwhile trade-off for professional-quality output.
