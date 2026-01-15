# Arena 4-Layer Editorial System: Implementation Plan

**Planning Approach**: OpenAI/DeepSeek Engineering Standards
- Modular architecture with clear interfaces
- Test-driven development
- Incremental rollout with metrics
- Cost/performance optimization
- Production-ready from day one

---

## System Architecture

### Module Structure

```
arena/
├── editorial/
│   ├── __init__.py
│   ├── base.py                    # Base classes and interfaces
│   ├── layer1_moment_detector.py
│   ├── layer2_boundary_analyzer.py
│   ├── layer3_context_refiner.py
│   ├── layer4_packaging.py
│   ├── pipeline.py                # Orchestration
│   └── validators.py              # Output validation
├── ai/
│   ├── analyzer.py                # DEPRECATED (old single-layer)
│   └── ...
└── ...
```

### Core Interfaces

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class TranscriptSegment:
    """Raw transcript data"""
    start: float
    end: float
    text: str
    speaker: Optional[str] = None

@dataclass
class Moment:
    """Layer 1 output: Raw interesting moment"""
    rough_start: float
    rough_end: float
    core_idea: str
    why_interesting: str
    interest_score: float
    content_type: str  # insight, hook, advice, story, etc.

@dataclass
class CompletThought:
    """Layer 2 output: Thought with proper boundaries"""
    moment_id: str
    expanded_start: float
    expanded_end: float
    thought_summary: str
    confidence: float
    original_moment: Moment

@dataclass
class ValidatedClip:
    """Layer 3 output: Standalone-validated clip"""
    thought_id: str
    refined_start: float
    refined_end: float
    standalone_score: float
    editor_notes: str
    verdict: str  # PASS, REVISE, REJECT
    complete_thought: CompleteThought

@dataclass
class PackagedClip:
    """Layer 4 output: Final clip with metadata"""
    clip_id: str
    start_time: float
    end_time: float
    duration: float
    title: str
    description: str
    hashtags: List[str]
    thumbnail_time: float
    thumbnail_reasoning: str
    interest_score: float
    standalone_score: float
    validated_clip: ValidatedClip

class EditorialLayer(ABC):
    """Base class for all editorial layers"""

    @abstractmethod
    def process(self, input_data, **kwargs):
        """Process input and return output"""
        pass

    @abstractmethod
    def validate_output(self, output):
        """Validate layer output format"""
        pass

    def get_metrics(self) -> Dict:
        """Return processing metrics"""
        return {
            'api_calls': 0,
            'tokens_used': 0,
            'processing_time': 0.0,
            'cost_usd': 0.0
        }
```

---

## Layer 1: Moment Detector

### Implementation

```python
# arena/editorial/layer1_moment_detector.py

from typing import List, Dict
import json
from openai import OpenAI

class MomentDetector:
    """
    Layer 1: Identifies interesting moments without worrying about completeness.

    Role: Senior content analyst
    Goal: Cast wide net, find 20-30 candidate moments
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0,
            'cost_usd': 0.0
        }

    def process(
        self,
        transcript_data: Dict,
        target_clips: int = 25
    ) -> List[Moment]:
        """
        Detect interesting moments in transcript.

        Args:
            transcript_data: Full transcript with segments
            target_clips: Number of candidate moments to find (default: 25)

        Returns:
            List of Moment objects, ranked by interest score
        """
        # Format transcript with timestamps
        formatted_transcript = self._format_transcript(
            transcript_data.get('segments', [])
        )

        # Create prompt
        prompt = self._create_prompt(formatted_transcript, target_clips)

        # Call API
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior content analyst identifying interesting moments."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            # Track metrics
            self.metrics['api_calls'] += 1
            self.metrics['tokens_used'] += response.usage.total_tokens

            # Parse response
            result = json.loads(response.choices[0].message.content)
            moments = self._parse_moments(result)

            print(f"✓ Layer 1: Found {len(moments)} candidate moments")
            return moments

        except Exception as e:
            print(f"❌ Layer 1 failed: {e}")
            return []

    def _format_transcript(self, segments: List[Dict]) -> str:
        """Format transcript with timestamps for prompt"""
        lines = []
        for seg in segments:
            start = seg.get('start', 0)
            text = seg.get('text', '').strip()
            if text:
                lines.append(f"[{start:.1f}s] {text}")
        return '\n'.join(lines)

    def _create_prompt(self, transcript: str, target_clips: int) -> str:
        """Create Layer 1 prompt (improved version from ChatGPT)"""
        return f"""ROLE: Senior content analyst.

TASK:
Identify the {target_clips} most interesting and valuable moments in this transcript
that are strong candidates for short-form clips.

IMPORTANT:
You are identifying *candidate regions*, not final clip boundaries.
Rough timestamps are acceptable at this stage.

LOOK FOR MOMENTS THAT CONTAIN:
1. Strong hooks or pattern interrupts
2. Key insights or "aha" realizations
3. Clear opinions or contrarian takes
4. Actionable advice or lessons
5. Emotional or personal moments
6. Clear problem → realization → outcome patterns
7. Statements a viewer would want to quote or share

DO NOT:
- Try to perfectly align sentence boundaries
- Optimize for standalone completeness
- Over-expand clips for context

Transcript (with timestamps):
{transcript}

OUTPUT JSON ONLY:
{{
  "candidates": [
    {{
      "rough_start": 123.4,
      "rough_end": 152.8,
      "core_idea": "Why cloud tools are inefficient for developers in emerging markets",
      "why_interesting": "Strong opinion rooted in personal frustration",
      "interest_score": 0.85,
      "content_type": "insight"
    }}
  ]
}}

RULES:
- Return exactly {target_clips} candidates
- Rank by interest_score (highest first)
- Timestamps may be imprecise
- Focus on *idea density*, not polish"""

    def _parse_moments(self, result: Dict) -> List[Moment]:
        """Parse API response into Moment objects"""
        moments = []
        for idx, candidate in enumerate(result.get('candidates', [])):
            try:
                moment = Moment(
                    rough_start=float(candidate['rough_start']),
                    rough_end=float(candidate['rough_end']),
                    core_idea=candidate['core_idea'],
                    why_interesting=candidate['why_interesting'],
                    interest_score=float(candidate['interest_score']),
                    content_type=candidate.get('content_type', 'general')
                )
                moments.append(moment)
            except (KeyError, ValueError) as e:
                print(f"⚠️  Skipping invalid moment {idx}: {e}")
                continue

        return sorted(moments, key=lambda m: m.interest_score, reverse=True)
```

---

## Layer 2: Thought Boundary Analyzer

### Implementation

```python
# arena/editorial/layer2_boundary_analyzer.py

from typing import List, Dict
import json
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor, as_completed

class ThoughtBoundaryAnalyzer:
    """
    Layer 2: Expands moments to complete thought boundaries.

    Role: Linguistic discourse analyst
    Goal: Find natural start/end of complete thoughts
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0,
            'cost_usd': 0.0
        }

    def process(
        self,
        moments: List[Moment],
        transcript_data: Dict,
        parallel: bool = True,
        max_workers: int = 5
    ) -> List[CompleteThought]:
        """
        Analyze thought boundaries for all moments.

        Args:
            moments: List of candidate moments from Layer 1
            transcript_data: Full transcript for context
            parallel: Process moments in parallel (default: True)
            max_workers: Max parallel API calls (default: 5)

        Returns:
            List of CompleteThought objects with expanded boundaries
        """
        if parallel:
            return self._process_parallel(moments, transcript_data, max_workers)
        else:
            return self._process_sequential(moments, transcript_data)

    def _process_parallel(
        self,
        moments: List[Moment],
        transcript_data: Dict,
        max_workers: int
    ) -> List[CompleteThought]:
        """Process moments in parallel for speed"""
        thoughts = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(
                    self._analyze_single_moment,
                    moment,
                    transcript_data,
                    idx
                ): idx
                for idx, moment in enumerate(moments)
            }

            for future in as_completed(futures):
                thought = future.result()
                if thought:
                    thoughts.append(thought)

        print(f"✓ Layer 2: Analyzed {len(thoughts)}/{len(moments)} complete thoughts")
        return sorted(thoughts, key=lambda t: t.complete_thought.interest_score, reverse=True)

    def _process_sequential(
        self,
        moments: List[Moment],
        transcript_data: Dict
    ) -> List[CompleteThought]:
        """Process moments sequentially (for debugging)"""
        thoughts = []

        for idx, moment in enumerate(moments):
            thought = self._analyze_single_moment(moment, transcript_data, idx)
            if thought:
                thoughts.append(thought)

        print(f"✓ Layer 2: Analyzed {len(thoughts)}/{len(moments)} complete thoughts")
        return thoughts

    def _analyze_single_moment(
        self,
        moment: Moment,
        transcript_data: Dict,
        moment_idx: int
    ) -> Optional[CompleteThought]:
        """Analyze a single moment to find thought boundaries"""

        # Extract context window (60s before/after moment)
        context_window = self._extract_context_window(
            transcript_data,
            moment.rough_start,
            moment.rough_end,
            window_seconds=60.0
        )

        # Create prompt
        prompt = self._create_prompt(moment, context_window)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a linguistic discourse analyst."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temp for analytical task
                response_format={"type": "json_object"}
            )

            # Track metrics
            self.metrics['api_calls'] += 1
            self.metrics['tokens_used'] += response.usage.total_tokens

            # Parse response
            result = json.loads(response.choices[0].message.content)

            thought = CompleteThought(
                moment_id=f"moment_{moment_idx:03d}",
                expanded_start=float(result['expanded_start']),
                expanded_end=float(result['expanded_end']),
                thought_summary=result['thought_summary'],
                confidence=float(result['confidence']),
                original_moment=moment
            )

            return thought

        except Exception as e:
            print(f"⚠️  Layer 2 failed for moment {moment_idx}: {e}")
            return None

    def _extract_context_window(
        self,
        transcript_data: Dict,
        rough_start: float,
        rough_end: float,
        window_seconds: float = 60.0
    ) -> str:
        """Extract transcript context around moment"""
        segments = transcript_data.get('segments', [])

        window_start = rough_start - window_seconds
        window_end = rough_end + window_seconds

        context_lines = []
        for seg in segments:
            seg_start = seg.get('start', 0)
            seg_end = seg.get('end', 0)

            if seg_end >= window_start and seg_start <= window_end:
                text = seg.get('text', '').strip()
                if text:
                    marker = " <-- CANDIDATE REGION" if rough_start <= seg_start <= rough_end else ""
                    context_lines.append(f"[{seg_start:.1f}s] {text}{marker}")

        return '\n'.join(context_lines)

    def _create_prompt(self, moment: Moment, context_window: str) -> str:
        """Create Layer 2 prompt (improved version from ChatGPT)"""
        return f"""ROLE: Linguistic discourse analyst.

TASK:
Given a transcript segment, identify the natural beginning and ending
of the complete thought being expressed.

DEFINITION:
A complete thought:
- Begins with the setup or premise
- Contains the core statement or idea
- Ends with a resolution, conclusion, or transition

CANDIDATE MOMENT:
- Rough window: {moment.rough_start:.1f}s → {moment.rough_end:.1f}s
- Core idea: {moment.core_idea}
- Why interesting: {moment.why_interesting}

CONTEXT (candidate region marked with <--):
{context_window}

INSTRUCTIONS:
1. Identify the core idea expressed in the candidate window.
2. Move the START backward to include:
   - sentence starts
   - discourse setup ("So", "The reason is", "What happened was")
3. Move the END forward to include:
   - completion of the idea
   - natural verbal closure
4. Stop expansion if a new topic begins.

OUTPUT JSON ONLY:
{{
  "expanded_start": <float>,
  "expanded_end": <float>,
  "thought_summary": "<one-sentence summary>",
  "confidence": 0.0-1.0
}}"""
```

---

## Layer 3: Standalone Context Refiner

### Implementation

```python
# arena/editorial/layer3_context_refiner.py

from typing import List, Dict, Tuple
import json
from openai import OpenAI

class StandaloneContextRefiner:
    """
    Layer 3: Validates and refines clips for standalone context.

    Role: Senior video editor
    Goal: Ensure clips are understandable without prior context
    """

    PASS_THRESHOLD = 0.7
    REVISE_THRESHOLD = 0.4

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model  # Use cheaper model for validation
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0,
            'passed': 0,
            'revised': 0,
            'rejected': 0
        }

    def process(
        self,
        thoughts: List[CompleteThought],
        transcript_data: Dict,
        max_iterations: int = 2
    ) -> List[ValidatedClip]:
        """
        Validate and refine thoughts for standalone context.

        Args:
            thoughts: List of complete thoughts from Layer 2
            transcript_data: Full transcript for context
            max_iterations: Max refinement attempts per thought (default: 2)

        Returns:
            List of ValidatedClip objects that passed validation
        """
        validated_clips = []

        for thought in thoughts:
            clip = self._validate_and_refine(
                thought,
                transcript_data,
                max_iterations
            )

            if clip and clip.verdict == "PASS":
                validated_clips.append(clip)

        print(f"✓ Layer 3: {self.metrics['passed']} passed, "
              f"{self.metrics['revised']} revised, "
              f"{self.metrics['rejected']} rejected")

        return validated_clips

    def _validate_and_refine(
        self,
        thought: CompleteThought,
        transcript_data: Dict,
        max_iterations: int
    ) -> Optional[ValidatedClip]:
        """
        Validate a single thought, refining if needed.

        Returns:
            ValidatedClip if passed, None if rejected
        """
        current_start = thought.expanded_start
        current_end = thought.expanded_end

        for iteration in range(max_iterations):
            # Extract clip transcript
            clip_transcript = self._extract_clip_text(
                transcript_data,
                current_start,
                current_end
            )

            # Validate
            result = self._validate_single(
                clip_transcript,
                current_start,
                current_end,
                transcript_data
            )

            if not result:
                return None

            refined_start, refined_end, standalone_score, editor_notes = result

            # Determine verdict
            if standalone_score >= self.PASS_THRESHOLD:
                self.metrics['passed'] += 1
                return ValidatedClip(
                    thought_id=thought.moment_id,
                    refined_start=refined_start,
                    refined_end=refined_end,
                    standalone_score=standalone_score,
                    editor_notes=editor_notes,
                    verdict="PASS",
                    complete_thought=thought
                )

            elif standalone_score >= self.REVISE_THRESHOLD:
                # Try to refine
                if iteration < max_iterations - 1:
                    current_start = refined_start
                    current_end = refined_end
                    continue
                else:
                    self.metrics['rejected'] += 1
                    return None

            else:
                # Below revise threshold - reject
                self.metrics['rejected'] += 1
                return None

        # Max iterations reached without passing
        self.metrics['rejected'] += 1
        return None

    def _validate_single(
        self,
        clip_transcript: str,
        start_time: float,
        end_time: float,
        transcript_data: Dict
    ) -> Optional[Tuple[float, float, float, str]]:
        """
        Validate a single clip for standalone context.

        Returns:
            (refined_start, refined_end, standalone_score, editor_notes) or None
        """
        # Get surrounding context for reference
        context = self._extract_context_window(
            transcript_data,
            start_time,
            end_time,
            window_seconds=30.0
        )

        prompt = self._create_prompt(clip_transcript, context)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior video editor ensuring clips are standalone."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            self.metrics['api_calls'] += 1
            self.metrics['tokens_used'] += response.usage.total_tokens

            result = json.loads(response.choices[0].message.content)

            return (
                float(result['refined_start']),
                float(result['refined_end']),
                float(result['standalone_score']),
                result['editor_notes']
            )

        except Exception as e:
            print(f"⚠️  Layer 3 validation failed: {e}")
            return None

    def _extract_clip_text(
        self,
        transcript_data: Dict,
        start_time: float,
        end_time: float
    ) -> str:
        """Extract transcript text for clip"""
        segments = transcript_data.get('segments', [])

        clip_lines = []
        for seg in segments:
            seg_start = seg.get('start', 0)
            seg_end = seg.get('end', 0)

            if seg_end >= start_time and seg_start <= end_time:
                text = seg.get('text', '').strip()
                if text:
                    clip_lines.append(f"[{seg_start:.1f}s] {text}")

        return '\n'.join(clip_lines)

    def _extract_context_window(
        self,
        transcript_data: Dict,
        start_time: float,
        end_time: float,
        window_seconds: float = 30.0
    ) -> str:
        """Extract context around clip for validation"""
        segments = transcript_data.get('segments', [])

        window_start = start_time - window_seconds
        window_end = end_time + window_seconds

        context_lines = []
        for seg in segments:
            seg_start = seg.get('start', 0)
            seg_end = seg.get('end', 0)

            if seg_end >= window_start and seg_start <= window_end:
                text = seg.get('text', '').strip()
                if text:
                    if start_time <= seg_start <= end_time:
                        context_lines.append(f"[CLIP] [{seg_start:.1f}s] {text}")
                    else:
                        context_lines.append(f"[CONTEXT] [{seg_start:.1f}s] {text}")

        return '\n'.join(context_lines)

    def _create_prompt(self, clip_transcript: str, context: str) -> str:
        """Create Layer 3 prompt (improved version from ChatGPT)"""
        return f"""ROLE: Senior video editor.

TASK:
Refine the clip boundaries so the segment is fully understandable
without any prior context.

CRITERIA FOR STANDALONE CONTEXT:
- The opening does not reference missing information
- The main idea is fully expressed
- The ending feels complete, not cut off
- No unresolved pronouns or implied context ("this", "that", "it")

CURRENT CLIP:
{clip_transcript}

SURROUNDING CONTEXT (for reference):
{context}

INSTRUCTIONS:
1. Evaluate if the clip stands alone.
2. Adjust start/end minimally to improve clarity.
3. Do NOT add unrelated ideas.
4. Prefer clarity over brevity.

OUTPUT JSON ONLY:
{{
  "refined_start": <float>,
  "refined_end": <float>,
  "standalone_score": 0.0-1.0,
  "editor_notes": "<short explanation>"
}}"""
```

---

## Layer 4: Packaging Layer

### Implementation

```python
# arena/editorial/layer4_packaging.py

from typing import List, Dict
import json
from openai import OpenAI

class PackagingLayer:
    """
    Layer 4: Generates titles, descriptions, and metadata.

    Goal: Polish validated clips for distribution
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.client = OpenAI(api_key=api_key)
        self.model = model  # Use cheaper model for packaging
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0
        }

    def process(
        self,
        validated_clips: List[ValidatedClip],
        transcript_data: Dict
    ) -> List[PackagedClip]:
        """
        Package validated clips with titles, descriptions, etc.

        Args:
            validated_clips: List of validated clips from Layer 3
            transcript_data: Full transcript for context

        Returns:
            List of PackagedClip objects ready for generation
        """
        packaged = []

        for clip in validated_clips:
            package = self._package_single(clip, transcript_data)
            if package:
                packaged.append(package)

        print(f"✓ Layer 4: Packaged {len(packaged)} clips")
        return packaged

    def _package_single(
        self,
        clip: ValidatedClip,
        transcript_data: Dict
    ) -> Optional[PackagedClip]:
        """Package a single clip"""

        # Extract clip transcript
        clip_text = self._extract_clip_text(
            transcript_data,
            clip.refined_start,
            clip.refined_end
        )

        # Generate packaging
        try:
            packaging = self._generate_packaging(clip_text)

            return PackagedClip(
                clip_id=clip.thought_id,
                start_time=clip.refined_start,
                end_time=clip.refined_end,
                duration=clip.refined_end - clip.refined_start,
                title=packaging['title'],
                description=packaging['description'],
                hashtags=packaging['hashtags'],
                thumbnail_time=packaging['thumbnail_time'],
                thumbnail_reasoning=packaging['thumbnail_reasoning'],
                interest_score=clip.complete_thought.original_moment.interest_score,
                standalone_score=clip.standalone_score,
                validated_clip=clip
            )

        except Exception as e:
            print(f"⚠️  Layer 4 packaging failed: {e}")
            return None

    def _generate_packaging(self, clip_text: str) -> Dict:
        """Generate all packaging metadata in one API call"""

        prompt = f"""Generate packaging metadata for this video clip:

{clip_text}

Provide:
1. Title (max 60 chars, compelling and specific)
2. Description (2-3 sentences, hook + context + value)
3. Hashtags (5 relevant tags for tech/business audience)
4. Best thumbnail timestamp within clip timeframe

OUTPUT JSON ONLY:
{{
  "title": "...",
  "description": "...",
  "hashtags": ["tag1", "tag2", ...],
  "thumbnail_time": <float>,
  "thumbnail_reasoning": "..."
}}"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,
            response_format={"type": "json_object"}
        )

        self.metrics['api_calls'] += 1
        self.metrics['tokens_used'] += response.usage.total_tokens

        return json.loads(response.choices[0].message.content)

    def _extract_clip_text(
        self,
        transcript_data: Dict,
        start_time: float,
        end_time: float
    ) -> str:
        """Extract clean clip text"""
        segments = transcript_data.get('segments', [])

        text_parts = []
        for seg in segments:
            seg_start = seg.get('start', 0)
            seg_end = seg.get('end', 0)

            if seg_end >= start_time and seg_start <= end_time:
                text = seg.get('text', '').strip()
                if text:
                    text_parts.append(text)

        return ' '.join(text_parts)
```

---

## Pipeline Orchestration

```python
# arena/editorial/pipeline.py

from typing import List, Dict, Optional
from dataclasses import asdict
import json
from pathlib import Path

class EditorialPipeline:
    """
    Orchestrates the 4-layer editorial pipeline.

    Handles:
    - Sequential layer execution
    - Metrics tracking
    - Intermediate result caching
    - Error recovery
    """

    def __init__(self, api_key: str):
        self.api_key = api_key

        # Initialize layers
        self.layer1 = MomentDetector(api_key, model="gpt-4o")
        self.layer2 = ThoughtBoundaryAnalyzer(api_key, model="gpt-4o")
        self.layer3 = StandaloneContextRefiner(api_key, model="gpt-4o-mini")
        self.layer4 = PackagingLayer(api_key, model="gpt-4o-mini")

    def run(
        self,
        transcript_data: Dict,
        num_final_clips: int = 10,
        cache_dir: Optional[Path] = None
    ) -> List[PackagedClip]:
        """
        Run complete 4-layer pipeline.

        Args:
            transcript_data: Full transcript with segments
            num_final_clips: Number of final clips to return
            cache_dir: Optional directory for caching intermediate results

        Returns:
            List of packaged clips ready for video generation
        """
        print("\n" + "="*70)
        print("🎬 4-LAYER EDITORIAL PIPELINE")
        print("="*70 + "\n")

        # Layer 1: Moment Detection
        print("[1/4] 🔍 Detecting interesting moments...")
        moments = self._run_layer1(transcript_data, cache_dir)
        if not moments:
            print("❌ No moments found")
            return []

        # Layer 2: Thought Boundary Analysis
        print(f"\n[2/4] 🧠 Analyzing thought boundaries...")
        thoughts = self._run_layer2(moments, transcript_data, cache_dir)
        if not thoughts:
            print("❌ No complete thoughts found")
            return []

        # Layer 3: Standalone Context Refinement
        print(f"\n[3/4] ✂️  Refining for standalone context...")
        validated = self._run_layer3(thoughts, transcript_data, cache_dir)
        if not validated:
            print("❌ No clips passed validation")
            return []

        # Select top N by combined score
        top_validated = self._select_top_clips(validated, num_final_clips)

        # Layer 4: Packaging
        print(f"\n[4/4] 📦 Packaging {len(top_validated)} clips...")
        packaged = self._run_layer4(top_validated, transcript_data, cache_dir)

        # Print summary
        self._print_summary(packaged)

        return packaged

    def _run_layer1(
        self,
        transcript_data: Dict,
        cache_dir: Optional[Path]
    ) -> List[Moment]:
        """Run Layer 1 with caching"""
        cache_file = cache_dir / "layer1_moments.json" if cache_dir else None

        if cache_file and cache_file.exists():
            print("   Using cached moments")
            with open(cache_file) as f:
                data = json.load(f)
                return [Moment(**m) for m in data]

        moments = self.layer1.process(transcript_data, target_clips=25)

        if cache_file and moments:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(cache_file, 'w') as f:
                json.dump([asdict(m) for m in moments], f, indent=2)

        return moments

    def _run_layer2(
        self,
        moments: List[Moment],
        transcript_data: Dict,
        cache_dir: Optional[Path]
    ) -> List[CompleteThought]:
        """Run Layer 2 with caching"""
        cache_file = cache_dir / "layer2_thoughts.json" if cache_dir else None

        if cache_file and cache_file.exists():
            print("   Using cached thoughts")
            with open(cache_file) as f:
                data = json.load(f)
                # Reconstruct objects (simplified)
                return data  # TODO: Full deserialization

        thoughts = self.layer2.process(
            moments,
            transcript_data,
            parallel=True,
            max_workers=5
        )

        if cache_file and thoughts:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            # TODO: Serialize CompleteThought objects

        return thoughts

    def _run_layer3(
        self,
        thoughts: List[CompleteThought],
        transcript_data: Dict,
        cache_dir: Optional[Path]
    ) -> List[ValidatedClip]:
        """Run Layer 3 with caching"""
        validated = self.layer3.process(thoughts, transcript_data)
        return validated

    def _run_layer4(
        self,
        validated: List[ValidatedClip],
        transcript_data: Dict,
        cache_dir: Optional[Path]
    ) -> List[PackagedClip]:
        """Run Layer 4 with caching"""
        packaged = self.layer4.package(validated, transcript_data)
        return packaged

    def _select_top_clips(
        self,
        validated: List[ValidatedClip],
        num_clips: int
    ) -> List[ValidatedClip]:
        """Select top N clips by combined score"""
        # Combined score: interest_score (60%) + standalone_score (40%)
        def combined_score(clip):
            interest = clip.complete_thought.original_moment.interest_score
            standalone = clip.standalone_score
            return (interest * 0.6) + (standalone * 0.4)

        sorted_clips = sorted(validated, key=combined_score, reverse=True)
        return sorted_clips[:num_clips]

    def _print_summary(self, packaged: List[PackagedClip]):
        """Print pipeline summary"""
        print("\n" + "="*70)
        print("📊 PIPELINE SUMMARY")
        print("="*70)

        total_cost = (
            self.layer1.metrics.get('cost_usd', 0) +
            self.layer2.metrics.get('cost_usd', 0) +
            self.layer3.metrics.get('cost_usd', 0) +
            self.layer4.metrics.get('cost_usd', 0)
        )

        print(f"Final clips: {len(packaged)}")
        print(f"Total API calls: {sum(l.metrics['api_calls'] for l in [self.layer1, self.layer2, self.layer3, self.layer4])}")
        print(f"Estimated cost: ${total_cost:.2f}")
        print("\nTop 5 clips:")

        for i, clip in enumerate(packaged[:5], 1):
            duration = clip.duration
            print(f"  {i}. [{duration:.1f}s] {clip.title}")
            print(f"     Interest: {clip.interest_score:.2f}, Standalone: {clip.standalone_score:.2f}")

        print("="*70 + "\n")
```

---

## Integration with Existing Pipeline

```python
# arena_process.py

# Add at top
from arena.editorial.pipeline import EditorialPipeline

def run_arena_pipeline(..., use_4layer_editorial: bool = False):
    """
    Run the complete Arena pipeline

    New param:
        use_4layer_editorial: Use 4-layer editorial system (default: False for backward compat)
    """

    # ... existing transcription code ...

    # STEP 2: Analysis
    if use_4layer_editorial:
        # NEW: 4-layer editorial pipeline
        editorial = EditorialPipeline(api_key=api_key)
        packaged_clips = editorial.run(
            transcript_data,
            num_final_clips=num_clips,
            cache_dir=cache_dir
        )

        # Convert to format expected by downstream code
        top_clips = [
            {
                'start_time': clip.start_time,
                'end_time': clip.end_time,
                'title': clip.title,
                'duration': clip.duration,
                'interest_score': clip.interest_score
            }
            for clip in packaged_clips
        ]
    else:
        # OLD: Single-layer analysis (backward compatibility)
        hybrid_analyzer = HybridAnalyzer(...)
        analysis_results = hybrid_analyzer.analyze_video(...)
        top_clips = analysis_results['clips'][:num_clips]

    # ... rest of pipeline (professional alignment, clip generation) ...
```

---

## Testing Strategy

### Unit Tests

```python
# tests/editorial/test_layer1_moment_detector.py

def test_moment_detector_finds_hooks():
    """Test that Layer 1 identifies hooks correctly"""
    detector = MomentDetector(api_key=test_key)

    transcript = mock_transcript_with_hook()
    moments = detector.process(transcript, target_clips=5)

    assert len(moments) > 0
    assert any(m.content_type == 'hook' for m in moments)
    assert all(0 <= m.interest_score <= 1.0 for m in moments)

def test_moment_detector_returns_requested_count():
    """Test that Layer 1 returns requested number of moments"""
    detector = MomentDetector(api_key=test_key)

    transcript = mock_long_transcript()
    moments = detector.process(transcript, target_clips=10)

    assert len(moments) == 10

# Similar tests for layers 2, 3, 4...
```

### Integration Tests

```python
# tests/editorial/test_pipeline_integration.py

def test_full_pipeline_e2e():
    """Test complete 4-layer pipeline end-to-end"""
    pipeline = EditorialPipeline(api_key=test_key)

    transcript = load_test_transcript("tech_talk_30min.json")
    clips = pipeline.run(transcript, num_final_clips=5)

    assert len(clips) == 5
    assert all(clip.standalone_score >= 0.7 for clip in clips)
    assert all(clip.duration >= 10.0 for clip in clips)
    assert all(len(clip.title) <= 60 for clip in clips)

def test_pipeline_handles_poor_content():
    """Test pipeline with low-quality content"""
    pipeline = EditorialPipeline(api_key=test_key)

    transcript = mock_boring_transcript()
    clips = pipeline.run(transcript, num_final_clips=10)

    # Should return fewer clips if quality bar not met
    assert len(clips) < 10
```

### Manual Review Process

```python
# scripts/review_editorial_output.py

def generate_review_report(packaged_clips, transcript_data, output_file):
    """Generate HTML report for human review"""

    html = ["<html><body>"]
    html.append("<h1>Editorial Pipeline Review</h1>")

    for clip in packaged_clips:
        html.append(f"<div class='clip'>")
        html.append(f"<h2>{clip.title}</h2>")
        html.append(f"<p><strong>Time:</strong> {clip.start_time:.1f}s - {clip.end_time:.1f}s ({clip.duration:.1f}s)</p>")
        html.append(f"<p><strong>Interest:</strong> {clip.interest_score:.2f} | <strong>Standalone:</strong> {clip.standalone_score:.2f}</p>")
        html.append(f"<p><strong>Description:</strong> {clip.description}</p>")

        # Show transcript
        clip_text = extract_clip_text(transcript_data, clip.start_time, clip.end_time)
        html.append(f"<pre>{clip_text}</pre>")

        # Review form
        html.append("<form>")
        html.append("<label>Quality (1-5): <input type='number' min='1' max='5'></label>")
        html.append("<label>Issues: <textarea></textarea></label>")
        html.append("</form>")
        html.append("</div><hr>")

    html.append("</body></html>")

    with open(output_file, 'w') as f:
        f.write('\n'.join(html))
```

---

## Rollout Plan

### Phase 1: Build & Unit Test (Week 1)
- [ ] Implement Layer 1 (Moment Detector)
- [ ] Unit tests for Layer 1
- [ ] Implement Layer 2 (Boundary Analyzer)
- [ ] Unit tests for Layer 2
- [ ] Implement Layer 3 (Context Refiner)
- [ ] Unit tests for Layer 3
- [ ] Implement Layer 4 (Packaging)
- [ ] Unit tests for Layer 4

### Phase 2: Integration & Testing (Week 2)
- [ ] Implement pipeline orchestration
- [ ] Integration tests
- [ ] Test on 10 diverse videos
- [ ] Manual review of outputs
- [ ] Tune prompts based on failures

### Phase 3: Optimization (Week 3)
- [ ] Add parallel processing
- [ ] Implement caching
- [ ] Cost optimization (model selection)
- [ ] Performance benchmarks

### Phase 4: Production (Week 4)
- [ ] Integrate with main pipeline
- [ ] Add CLI flags (`--use-4layer`)
- [ ] Documentation
- [ ] Metrics dashboard
- [ ] Production deployment

---

## Success Metrics

### Quality Metrics
- **Clip Validity Rate**: % of generated clips that are usable (target: >90%)
- **Standalone Score**: Average standalone_score (target: >0.75)
- **Duration Distribution**: % of clips 15-90s (target: >80%)
- **Human Rating**: Manual review score 1-5 (target: >4.0)

### Performance Metrics
- **Processing Time**: Total pipeline time (target: <5min for 30min video)
- **API Latency**: Per-layer latency (Layer 1: <30s, Layer 2: <2min, Layer 3: <1min, Layer 4: <30s)
- **Parallelization**: Speedup from parallel processing (target: 3-5x)

### Cost Metrics
- **Cost Per Video**: Total API cost (target: <$1.00)
- **Cost Per Clip**: Cost per final clip (target: <$0.10)
- **Token Efficiency**: Tokens used vs. transcript length ratio

### Comparison Metrics (vs. Single-Layer)
- **Quality Improvement**: +X% in manual review scores
- **Validity Improvement**: +Y% in usable clips
- **Cost Increase**: +Z% in API costs
- **Time Increase**: +W% in processing time

Target: 2-3x quality improvement for 3-4x cost increase

---

## Monitoring & Debugging

### Layer-by-Layer Inspection

```bash
# Export intermediate results
arena process video.mp4 --use-4layer --export-layers layers_output/

# Generates:
# - layers_output/layer1_moments.json
# - layers_output/layer2_thoughts.json
# - layers_output/layer3_validated.json
# - layers_output/layer4_packaged.json
```

### Metrics Dashboard

```python
# scripts/analyze_pipeline_metrics.py

def generate_metrics_report(pipeline):
    """Generate metrics report from pipeline run"""

    report = {
        'layer1': {
            'moments_found': len(pipeline.layer1.outputs),
            'api_calls': pipeline.layer1.metrics['api_calls'],
            'tokens': pipeline.layer1.metrics['tokens_used'],
            'cost': pipeline.layer1.metrics['cost_usd']
        },
        'layer2': {
            'thoughts_analyzed': len(pipeline.layer2.outputs),
            'avg_confidence': np.mean([t.confidence for t in pipeline.layer2.outputs]),
            'api_calls': pipeline.layer2.metrics['api_calls'],
            'tokens': pipeline.layer2.metrics['tokens_used'],
            'cost': pipeline.layer2.metrics['cost_usd']
        },
        'layer3': {
            'passed': pipeline.layer3.metrics['passed'],
            'revised': pipeline.layer3.metrics['revised'],
            'rejected': pipeline.layer3.metrics['rejected'],
            'pass_rate': pipeline.layer3.metrics['passed'] / len(pipeline.layer2.outputs),
            'avg_standalone_score': np.mean([c.standalone_score for c in pipeline.layer3.outputs])
        },
        'layer4': {
            'clips_packaged': len(pipeline.layer4.outputs),
            'avg_title_length': np.mean([len(c.title) for c in pipeline.layer4.outputs])
        },
        'total': {
            'cost': sum(l.metrics.get('cost_usd', 0) for l in [pipeline.layer1, pipeline.layer2, pipeline.layer3, pipeline.layer4]),
            'time': pipeline.total_time,
            'clips_per_dollar': len(pipeline.layer4.outputs) / total_cost
        }
    }

    return report
```

---

## Future Optimizations

### Batch Processing
Process multiple videos in parallel, sharing model instances

### Prompt Caching
Cache prompt prefixes for repeated use (new OpenAI feature)

### Fine-Tuning
Fine-tune smaller models on human-reviewed outputs:
- Layer 1: Fine-tune on moment detection
- Layer 3: Fine-tune on standalone validation

### Hybrid Approach
Use energy detection + scene detection to pre-filter before Layer 1

### Adaptive Thresholds
Adjust Layer 3 thresholds based on content type (interview vs. tutorial vs. talk)

---

## Conclusion

This 4-layer editorial architecture provides:

1. **Clear separation of concerns** - Each layer has one job
2. **Explicit validation** - Layer 3 is quality gate
3. **Better debugging** - Inspect each layer's output
4. **Cost optimization** - Use expensive models only where needed
5. **Solves short clip problem** - Layers 2+3 ensure complete thoughts

Implementation follows OpenAI/DeepSeek standards:
- Modular, testable code
- Comprehensive metrics
- Incremental rollout
- Production-ready from start

Ready to build? 🚀
