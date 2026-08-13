# Week 1 Implementation Plan - Phase 1: Thought Unit Detection

**Goal**: Build the foundational ThoughtUnit data structure and implement thought seed detection

**Timeline**: Days 1-5 (Week 1)
**Validation**: Detect 40-50 thought seeds in test_007 (15-minute sermon)

---

## Day 1-2: ThoughtUnit Data Structure (Foundation)

### Deliverables

#### 1. Create `engine/arena/editorial/thought_unit.py` (NEW)

```python
"""
Thought Unit Data Structure

A ThoughtUnit represents a complete rhetorical unit with:
- Premise (where the thought begins)
- Claim (the core insight/peak)
- Resolution (where the thought completes)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict
import json


class RhetoricalType(Enum):
    """Types of rhetorical structures in content"""
    STORY = "story"                    # Narrative with arc
    ARGUMENT = "argument"              # Thesis + reasoning (sermons, debates)
    EXAMPLE = "example"                # Illustration/case study
    TEACHING = "teaching"              # How-to/tutorial (tech talks, courses)
    QUESTION_ANSWER = "qa"             # Interview format (podcasts)
    COMPARISON = "comparison"          # Product reviews, vs discussions
    INSIGHT = "insight"                # Standalone wisdom/observation


class DependencyLevel(Enum):
    """How standalone is this thought?"""
    STANDALONE = "standalone"          # Fully self-contained
    NEEDS_CONTEXT = "needs_context"    # Requires prior context
    UNSALVAGEABLE = "unsalvageable"    # Too fragmented to fix


@dataclass
class ThoughtUnit:
    """
    A complete rhetorical unit - the atomic building block of clips.

    Represents premise → claim → resolution structure that forms
    a complete, standalone thought.
    """

    # Temporal boundaries
    premise_start: float      # Where setup/context begins (seconds)
    claim_peak: float         # Where core insight appears (seconds)
    resolution_end: float     # Where thought completes (seconds)

    # Text content
    premise_text: str         # Setup sentences
    claim_text: str           # Core statement/insight
    resolution_text: str      # Supporting reasoning/conclusion

    # Classification
    rhetorical_type: RhetoricalType
    dependency_level: DependencyLevel

    # Quality metrics
    completeness_score: float = 0.0       # 0.0-1.0
    premise_clarity: float = 0.0          # 0.0-10.0
    claim_strength: float = 0.0           # 0.0-10.0
    resolution_closure: float = 0.0       # 0.0-10.0

    # Metadata
    seed_id: str = ""                     # Original seed that generated this
    has_unresolved_refs: bool = False
    confidence: float = 0.0

    # Debug info
    _detection_metadata: Dict = field(default_factory=dict)

    @property
    def duration(self) -> float:
        """Total duration of thought unit in seconds"""
        return self.resolution_end - self.premise_start

    @property
    def full_text(self) -> str:
        """Complete text of the thought unit"""
        return f"{self.premise_text} {self.claim_text} {self.resolution_text}"

    def has_premise(self) -> bool:
        """Does this unit have a clear premise?"""
        return bool(self.premise_text and len(self.premise_text.strip()) > 20)

    def has_claim(self) -> bool:
        """Does this unit have a clear claim?"""
        return bool(self.claim_text and len(self.claim_text.strip()) > 10)

    def has_resolution(self) -> bool:
        """Does this unit have a clear resolution?"""
        return bool(self.resolution_text and len(self.resolution_text.strip()) > 20)

    def is_complete(self) -> bool:
        """
        Validate rhetorical completeness

        A thought is complete if it has:
        1. Clear premise (setup/context)
        2. Clear claim (core insight)
        3. Clear resolution (closure)
        4. No unresolved references
        5. Standalone dependency level
        """
        return (
            self.has_premise() and
            self.has_claim() and
            self.has_resolution() and
            not self.has_unresolved_refs and
            self.dependency_level == DependencyLevel.STANDALONE
        )

    def meets_production_standard(self) -> bool:
        """
        Does this meet 90%+ production quality bar?

        Requirements:
        - Completeness score >= 0.85
        - All three components score >= 8.0/10
        - No unresolved references
        - Standalone
        """
        return (
            self.completeness_score >= 0.85 and
            self.premise_clarity >= 8.0 and
            self.claim_strength >= 8.0 and
            self.resolution_closure >= 8.0 and
            not self.has_unresolved_refs and
            self.dependency_level == DependencyLevel.STANDALONE
        )

    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            'premise_start': self.premise_start,
            'claim_peak': self.claim_peak,
            'resolution_end': self.resolution_end,
            'duration': self.duration,
            'premise_text': self.premise_text,
            'claim_text': self.claim_text,
            'resolution_text': self.resolution_text,
            'full_text': self.full_text,
            'rhetorical_type': self.rhetorical_type.value,
            'dependency_level': self.dependency_level.value,
            'completeness_score': self.completeness_score,
            'premise_clarity': self.premise_clarity,
            'claim_strength': self.claim_strength,
            'resolution_closure': self.resolution_closure,
            'is_complete': self.is_complete(),
            'meets_production_standard': self.meets_production_standard(),
            'has_unresolved_refs': self.has_unresolved_refs,
            'confidence': self.confidence,
            'seed_id': self.seed_id,
            '_metadata': self._detection_metadata
        }

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict) -> 'ThoughtUnit':
        """Deserialize from dictionary"""
        return cls(
            premise_start=data['premise_start'],
            claim_peak=data['claim_peak'],
            resolution_end=data['resolution_end'],
            premise_text=data['premise_text'],
            claim_text=data['claim_text'],
            resolution_text=data['resolution_text'],
            rhetorical_type=RhetoricalType(data['rhetorical_type']),
            dependency_level=DependencyLevel(data['dependency_level']),
            completeness_score=data.get('completeness_score', 0.0),
            premise_clarity=data.get('premise_clarity', 0.0),
            claim_strength=data.get('claim_strength', 0.0),
            resolution_closure=data.get('resolution_closure', 0.0),
            has_unresolved_refs=data.get('has_unresolved_refs', False),
            confidence=data.get('confidence', 0.0),
            seed_id=data.get('seed_id', ''),
            _detection_metadata=data.get('_metadata', {})
        )


class ThoughtUnitError(Exception):
    """Base exception for thought unit issues"""
    pass


class IncompletePremiseError(ThoughtUnitError):
    """Raised when premise cannot be found"""
    def __init__(self, claim_position: float, message: str):
        self.claim_position = claim_position
        super().__init__(message)


class IncompleteResolutionError(ThoughtUnitError):
    """Raised when resolution cannot be found"""
    def __init__(self, claim_position: float, message: str):
        self.claim_position = claim_position
        super().__init__(message)


class AmbiguousBoundaryError(ThoughtUnitError):
    """Raised when boundary detection is uncertain"""
    def __init__(self, candidates: List[float], message: str):
        self.candidates = candidates
        super().__init__(message)
```

**Tests to Write**:
```python
# tests/test_thought_unit.py

def test_thought_unit_creation():
    """Test basic ThoughtUnit creation"""
    unit = ThoughtUnit(
        premise_start=10.0,
        claim_peak=25.0,
        resolution_end=45.0,
        premise_text="Setup context here",
        claim_text="Core insight",
        resolution_text="Conclusion and closure",
        rhetorical_type=RhetoricalType.ARGUMENT,
        dependency_level=DependencyLevel.STANDALONE
    )
    assert unit.duration == 35.0
    assert unit.is_complete() == True

def test_completeness_validation():
    """Test completeness checks"""
    # Missing premise
    unit = ThoughtUnit(
        premise_text="",  # Empty
        claim_text="Core insight",
        resolution_text="Conclusion",
        ...
    )
    assert unit.is_complete() == False
    assert unit.has_premise() == False

def test_production_standard():
    """Test production quality bar"""
    unit = ThoughtUnit(...)
    unit.completeness_score = 0.90
    unit.premise_clarity = 9.0
    unit.claim_strength = 8.5
    unit.resolution_closure = 8.0
    unit.has_unresolved_refs = False
    unit.dependency_level = DependencyLevel.STANDALONE

    assert unit.meets_production_standard() == True

def test_serialization():
    """Test to_dict/from_dict roundtrip"""
    unit = ThoughtUnit(...)
    data = unit.to_dict()
    restored = ThoughtUnit.from_dict(data)
    assert restored.premise_start == unit.premise_start
```

---

## Day 3-4: Thought Seed Detection

### Deliverables

#### 2. Rename & Enhance `layer1_moment_detector.py` → `thought_seed_detector.py`

**Key Changes**:

1. **Sliding Window Approach** (instead of analyzing entire transcript at once)
2. **Detect 4x target** (target 10 clips → detect 40 seeds)
3. **Content-type awareness** (detect rhetorical types)

```python
"""
Thought Seed Detector (Layer 1 Redesign)

Detects "seeds" - claim/insight moments that anchor complete thoughts.

Strategy:
- Use sliding window approach (2-minute windows)
- Find 3-5 seeds per window
- Detect rhetorical type for each seed
- Over-detect by 4x (will be filtered by later layers)
"""

from typing import List, Dict, Optional
from .thought_unit import RhetoricalType, ThoughtUnit
import json


class ThoughtSeedDetector:
    """
    Detects thought seeds - moments that anchor complete thoughts.

    A "seed" is a claim, insight, or key moment that likely has:
    - A premise before it (setup/context)
    - A resolution after it (conclusion/closure)

    Unlike traditional "moment detection" which finds emotional peaks,
    this finds CLAIMS/INSIGHTS that form centers of complete thoughts.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0,
            'cost_usd': 0.0,
            'windows_analyzed': 0,
            'seeds_detected': 0
        }

    def detect_seeds(
        self,
        transcript_data: Dict,
        target_count: int = 10
    ) -> List[Dict]:
        """
        Detect thought seeds using sliding window approach.

        Args:
            transcript_data: Transcript with segments
            target_count: Target number of final clips (will detect 4x this)

        Returns:
            List of seed dicts with:
            {
                'seed_id': 'seed_001',
                'timestamp': 45.5,
                'text': 'The core claim or insight',
                'rhetorical_type': 'argument',
                'interest_score': 0.85,
                'context_before': 'Previous sentences',
                'context_after': 'Following sentences'
            }
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required")

        client = OpenAI(api_key=self.api_key)
        segments = transcript_data.get('segments', [])
        duration = transcript_data.get('duration', 0)

        if not segments:
            print("      ⚠️  No segments in transcript")
            return []

        # Over-detect by 4x
        target_seeds = target_count * 4

        print(f"      Detecting thought seeds (target: {target_seeds})...")

        # Sliding window approach
        WINDOW_SIZE = 120  # 2 minutes
        WINDOW_OVERLAP = 30  # 30 second overlap

        windows = self._create_windows(segments, WINDOW_SIZE, WINDOW_OVERLAP)
        seeds_per_window = max(3, target_seeds // len(windows))

        all_seeds = []

        for idx, window in enumerate(windows, 1):
            print(f"      Analyzing window {idx}/{len(windows)}...")

            window_seeds = self._detect_seeds_in_window(
                client,
                window,
                seeds_per_window
            )

            all_seeds.extend(window_seeds)
            self.metrics['windows_analyzed'] += 1

        # Deduplicate seeds from overlapping windows
        unique_seeds = self._deduplicate_seeds(all_seeds)

        # Sort by interest score and take top N
        top_seeds = sorted(
            unique_seeds,
            key=lambda s: s['interest_score'],
            reverse=True
        )[:target_seeds]

        self.metrics['seeds_detected'] = len(top_seeds)
        print(f"      ✓ Detected {len(top_seeds)} thought seeds")

        return top_seeds

    def _create_windows(
        self,
        segments: List[Dict],
        window_size: float,
        overlap: float
    ) -> List[Dict]:
        """
        Create sliding windows over transcript.

        Returns list of window dicts:
        {
            'start': 0.0,
            'end': 120.0,
            'segments': [...]
        }
        """
        windows = []
        start = 0.0

        # Get total duration from last segment
        total_duration = segments[-1]['end'] if segments else 0

        while start < total_duration:
            end = min(start + window_size, total_duration)

            # Get segments in this window
            window_segments = [
                seg for seg in segments
                if seg['start'] >= start and seg['end'] <= end
            ]

            if window_segments:
                windows.append({
                    'start': start,
                    'end': end,
                    'segments': window_segments
                })

            start += (window_size - overlap)

        return windows

    def _detect_seeds_in_window(
        self,
        client,
        window: Dict,
        target_count: int
    ) -> List[Dict]:
        """
        Detect seeds in a single window using GPT.

        Returns list of seed dicts.
        """
        # Extract text from window
        window_text = ' '.join(seg['text'] for seg in window['segments'])

        prompt = self._create_seed_detection_prompt(window_text, target_count)

        # Call GPT
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at identifying key claims, insights, and moments in spoken content that form the centers of complete thoughts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            # Track metrics
            self.metrics['api_calls'] += 1
            self.metrics['tokens_used'] += response.usage.total_tokens
            # Calculate cost (GPT-4o pricing)
            input_cost = (response.usage.prompt_tokens / 1_000_000) * 2.50
            output_cost = (response.usage.completion_tokens / 1_000_000) * 10.00
            self.metrics['cost_usd'] += input_cost + output_cost

            # Parse response
            result = json.loads(response.choices[0].message.content)
            seeds = result.get('seeds', [])

            # Add window context to each seed
            for seed in seeds:
                seed['window_start'] = window['start']
                seed['window_end'] = window['end']

            return seeds

        except Exception as e:
            print(f"      ⚠️  Error detecting seeds in window: {e}")
            return []

    def _create_seed_detection_prompt(
        self,
        window_text: str,
        target_count: int
    ) -> str:
        """
        Create prompt for seed detection.

        This is the CRITICAL prompt that determines quality.
        """
        return f"""You are analyzing a 2-minute segment of spoken content to find THOUGHT SEEDS.

A THOUGHT SEED is:
- A claim, insight, controversial statement, or key idea
- Something that likely has a PREMISE before it (setup/context)
- Something that likely has a RESOLUTION after it (conclusion/closure)
- NOT just an emotional peak or interesting phrase
- The CENTER of a complete thought

TRANSCRIPT SEGMENT:
{window_text}

TASK:
Find the top {target_count} thought seeds in this segment.

Look for:

1. **Arguments** (Thesis + reasoning):
   - "I believe...", "The problem is...", "Here's why..."
   - Claims that need support
   - Controversial statements

2. **Teaching moments** (Explanations):
   - "Let me show you...", "The key is...", "Here's what..."
   - Concepts being explained
   - Frameworks being shared

3. **Story pivots** (Turning points):
   - "Then this happened...", "What I realized..."
   - Revelations, surprises, lessons learned

4. **Practical advice** (Actionable insights):
   - "You should...", "Don't...", "The way to..."
   - Specific recommendations
   - Warnings or best practices

5. **Questions being answered**:
   - "People ask me...", "The answer is..."
   - Problems being solved

RETURN JSON:
{{
  "seeds": [
    {{
      "seed_id": "seed_001",
      "timestamp_approx": 45.5,
      "text": "The exact sentence or phrase that is the seed",
      "rhetorical_type": "argument|teaching|story|advice|qa",
      "interest_score": 0.85,
      "reasoning": "Why this is a good seed",
      "likely_has_premise": true,
      "likely_has_resolution": true
    }},
    ...
  ]
}}

RULES:
- Return exactly {target_count} seeds (or fewer if there aren't enough good ones)
- Seeds must be SPECIFIC sentences/phrases, not summaries
- Interest score 0.0-1.0 (be honest, not all moments are great)
- Only include seeds that likely have premise AND resolution
- Diverse types preferred (not all arguments or all stories)
"""

    def _deduplicate_seeds(self, seeds: List[Dict]) -> List[Dict]:
        """
        Remove duplicate seeds from overlapping windows.

        Seeds are duplicates if:
        - Similar timestamp (within 10 seconds)
        - Similar text (high semantic similarity)
        """
        if len(seeds) <= 1:
            return seeds

        # Sort by timestamp
        sorted_seeds = sorted(seeds, key=lambda s: s['timestamp_approx'])

        unique = []
        for seed in sorted_seeds:
            # Check if similar to any existing unique seed
            is_duplicate = False
            for existing in unique:
                time_diff = abs(seed['timestamp_approx'] - existing['timestamp_approx'])
                if time_diff < 10:  # Within 10 seconds
                    # Check text similarity (simple overlap for now)
                    # TODO: Use embeddings for better similarity
                    if self._text_similarity(seed['text'], existing['text']) > 0.7:
                        is_duplicate = True
                        # Keep higher scoring one
                        if seed['interest_score'] > existing['interest_score']:
                            unique.remove(existing)
                            unique.append(seed)
                        break

            if not is_duplicate:
                unique.append(seed)

        return unique

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Simple Jaccard similarity for deduplication"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0
```

---

## Day 5: Validation & Testing

### Deliverables

#### 3. Test on test_007

**Create `tests/test_week1.py`**:

```python
"""
Week 1 Validation Tests

Test thought seed detection on test_007 video
"""

def test_thought_unit_structure():
    """Validate ThoughtUnit data structure"""
    from arena.editorial.thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel

    unit = ThoughtUnit(
        premise_start=10.0,
        claim_peak=25.0,
        resolution_end=45.0,
        premise_text="The anxiety of being single",
        claim_text="is nothing compared to the regret of being in the wrong marriage",
        resolution_text="Many single people want to get married. Many married people want to be single.",
        rhetorical_type=RhetoricalType.ARGUMENT,
        dependency_level=DependencyLevel.STANDALONE
    )

    assert unit.duration == 35.0
    assert unit.is_complete() == True
    assert unit.has_premise() == True
    assert unit.has_claim() == True
    assert unit.has_resolution() == True


def test_seed_detection_on_test_007():
    """
    Test seed detection on test_007 sermon

    Success criteria:
    - Detects 40-50 seeds (target 10 clips × 4)
    - Seeds distributed across video
    - Multiple rhetorical types detected
    - User's 4 clips appear in seeds
    """
    from arena.editorial.thought_seed_detector import ThoughtSeedDetector
    import json

    # Load test_007 transcript
    with open('path/to/test_007/transcript.json') as f:
        transcript = json.load(f)

    detector = ThoughtSeedDetector(api_key=os.getenv('OPENAI_API_KEY'))
    seeds = detector.detect_seeds(transcript, target_count=10)

    # Should detect 40-50 seeds
    assert 35 <= len(seeds) <= 55, f"Expected 35-55 seeds, got {len(seeds)}"

    # Seeds should be distributed (not all at beginning/end)
    timestamps = [s['timestamp_approx'] for s in seeds]
    assert min(timestamps) < 100  # Some in first 100 seconds
    assert max(timestamps) > 700  # Some after 700 seconds (test_007 is ~900s)

    # Should have diverse rhetorical types
    types = [s['rhetorical_type'] for s in seeds]
    unique_types = set(types)
    assert len(unique_types) >= 2, "Should detect at least 2 different rhetorical types"

    # Check if user's clip positions appear in seeds
    # (You'll provide these timestamps)
    user_clip_timestamps = [
        # clip_01: [timestamp]
        # clip_02: [timestamp]
        # clip_03: [timestamp]
        # clip_04: [timestamp]
    ]

    # At least 3 of 4 user clips should be detected as seeds
    detected_user_clips = 0
    for user_ts in user_clip_timestamps:
        for seed in seeds:
            if abs(seed['timestamp_approx'] - user_ts) < 30:  # Within 30 seconds
                detected_user_clips += 1
                break

    assert detected_user_clips >= 3, f"Only detected {detected_user_clips}/4 user clips as seeds"

    print(f"✓ Detected {len(seeds)} seeds")
    print(f"✓ Types: {unique_types}")
    print(f"✓ Found {detected_user_clips}/4 user clips")
```

#### 4. Manual Validation

**Run on test_007**:
```bash
# After implementation
python -c "
from arena.editorial.thought_seed_detector import ThoughtSeedDetector
import json

with open('path/to/test_007/transcript.json') as f:
    transcript = json.load(f)

detector = ThoughtSeedDetector(api_key='...')
seeds = detector.detect_seeds(transcript, target_count=10)

# Export for review
with open('test_007_seeds.json', 'w') as f:
    json.dump(seeds, f, indent=2)

print(f'Detected {len(seeds)} seeds')
"
```

**Review `test_007_seeds.json`**:
- Are seeds spread across the video?
- Do they correspond to your 4 manual clips?
- Are rhetorical types correct?
- Are interest scores reasonable?

---

## Week 1 Success Criteria

By end of Day 5, we should have:

✅ **ThoughtUnit data structure**:
- Fully implemented with all methods
- Unit tests passing
- Serialization working
- Production quality checks implemented

✅ **Thought seed detection**:
- Detects 40-50 seeds in test_007
- Seeds distributed across video (not clustered)
- Multiple rhetorical types detected
- 3 of 4 user clips detected as seeds

✅ **Code quality**:
- All unit tests passing
- Type hints throughout
- Docstrings on all public methods
- No linting errors

✅ **Metrics**:
```python
{
  'seeds_detected': 42,
  'windows_analyzed': 8,
  'rhetorical_types': ['argument', 'teaching', 'story'],
  'user_clips_detected': 3,
  'cost': '$0.15'
}
```

---

## What I Need from You to Start

### 1. test_007 Video File
- Need the actual video file to run full pipeline tests
- Or at minimum, confirm the transcript.json I have is correct

### 2. Your 4 Clip Timestamps
Please provide timestamps for your manually selected clips:

```json
{
  "clip_01": {
    "start": "MM:SS",
    "end": "MM:SS",
    "text": "The anxiety of being single..."
  },
  "clip_02": {
    "start": "MM:SS",
    "end": "MM:SS",
    "text": "I believe God can tell you..."
  },
  "clip_03": {
    "start": "MM:SS",
    "end": "MM:SS",
    "text": "God does not describe how to pick a wife..."
  },
  "clip_04": {
    "start": "MM:SS",
    "end": "MM:SS",
    "text": "Somebody called me some months ago..."
  }
}
```

This gives me ground truth for validation throughout all 8 weeks.

### 3. Approval to Start
- Confirm you're ready for me to begin Week 1 implementation
- Any concerns or questions about the approach?

---

## Next Steps

Once you provide the above, I will:

**Day 1-2** (Today/Tomorrow):
1. Create `thought_unit.py` with full implementation
2. Write comprehensive unit tests
3. Validate data structure works

**Day 3-4**:
4. Implement `thought_seed_detector.py`
5. Test on test_007 transcript
6. Tune prompts and thresholds

**Day 5**:
7. Full validation against your 4 clips
8. Document Week 1 results
9. Prepare Week 2 plan (premise/resolution detection)

**Ready to start Week 1?**
