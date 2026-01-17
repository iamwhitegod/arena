"""
Layer 3: Standalone Context Refiner

QUALITY GATE: Validates that clips are understandable without prior context.

This is the most critical layer - it ensures clips can stand alone as
independent pieces of content that make sense to viewers who just clicked.

Implements iterative refinement to adjust boundaries if needed.
"""

from typing import List, Dict, Optional, Tuple
import json
from enum import Enum
from .utils import extract_clip_text, format_timestamp


class RejectionReason(Enum):
    """Why clips are rejected"""
    MISSING_PREMISE = "missing_premise"  # Doesn't explain what topic is about
    DANGLING_REFERENCE = "dangling_reference"  # Unresolved "it", "this", "that"
    INCOMPLETE_RESOLUTION = "incomplete_resolution"  # Cuts off mid-thought
    TOPIC_DRIFT = "topic_drift"  # Starts on one topic, ends on another
    DURATION_CONSTRAINT = "duration_constraint"  # Too short/long
    STRUCTURAL_ISSUE = "structural_issue"  # No clear beginning/middle/end


class StandaloneContextRefiner:
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

    Strategy:
        - Ask: Can someone who JUST clicked on this clip understand it?
        - Validate: Who? What? Why? Missing assumptions?
        - Score 0.0-1.0 for standalone quality
        - Iterate up to 2 times to fix boundary issues
        - Final verdict: PASS (≥0.7), REVISE (0.4-0.7), REJECT (<0.4)

    Success Criteria:
        - Pass rate should be 50-70%
        - If too high (>80%), not selective enough
        - If too low (<40%), Layer 2 boundaries are poor
    """

    PASS_THRESHOLD = 0.7      # Must score ≥0.7 to pass
    REVISE_THRESHOLD = 0.4    # Below 0.4 = auto-reject
    MAX_ITERATIONS = 2        # Try refinement up to 2 times

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize standalone context refiner

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o-mini for cost efficiency)
        """
        self.api_key = api_key
        self.model = model
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0,
            'cost_usd': 0.0,
            'passed': 0,
            'revised': 0,
            'rejected': 0,
            'pass_rate': 0.0,
            'no_changes_needed': 0,  # Layer 2 boundaries were perfect
            'boundary_quality_rate': 0.0  # no_changes / (passed + revised)
        }

    def refine_all(
        self,
        thoughts: List[Dict],
        transcript_data: Dict,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None
    ) -> List[Dict]:
        """
        Validate and refine all thoughts for standalone context.

        Args:
            thoughts: List of thoughts from Layer 2
            transcript_data: Full transcript data with segments
            min_duration: Optional minimum clip duration in seconds
            max_duration: Optional maximum clip duration in seconds

        Returns:
            List of validated clip dicts:
            {
                'thought_id': str,
                'refined_start': float,
                'refined_end': float,
                'standalone_score': float,
                'verdict': str,           # "PASS", "REVISE", "REJECT"
                'editor_notes': str,
                'complete_thought': Dict  # Preserve Layer 2 output
            }
        """
        if not thoughts:
            print("      ⚠️  No thoughts to refine")
            return []

        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

        client = OpenAI(api_key=self.api_key)
        segments = transcript_data.get('segments', [])

        if not segments:
            print("      ⚠️  No segments in transcript")
            return []

        validated_clips = []

        print(f"      Validating {len(thoughts)} thoughts...")

        for idx, thought in enumerate(thoughts, 1):
            try:
                clip = self._validate_and_refine(
                    client,
                    thought,
                    segments,
                    min_duration,
                    max_duration
                )

                if clip:
                    validated_clips.append(clip)

                    # Track metrics
                    if clip['verdict'] == 'PASS':
                        self.metrics['passed'] += 1

                        # Track if Layer 3 made changes to Layer 2 boundaries
                        if not clip.get('changes_made', True):  # Default True for backward compat
                            self.metrics['no_changes_needed'] += 1

                    elif clip['verdict'] == 'REVISE':
                        self.metrics['revised'] += 1
                    elif clip['verdict'] == 'REJECT':
                        self.metrics['rejected'] += 1

                    verdict_icon = {
                        'PASS': '✓',
                        'REVISE': '↻',
                        'REJECT': '✗'
                    }.get(clip['verdict'], '?')

                    print(f"      {verdict_icon} Thought {idx}/{len(thoughts)}: {clip['verdict']} "
                          f"(score: {clip['standalone_score']:.2f})")

            except Exception as e:
                print(f"      ⚠️  Thought {idx} validation failed: {e}")
                continue

        # Calculate pass rate
        total = self.metrics['passed'] + self.metrics['revised'] + self.metrics['rejected']
        if total > 0:
            self.metrics['pass_rate'] = self.metrics['passed'] / total

            # Calculate boundary quality rate (how often Layer 2 boundaries are kept as-is)
            eligible = self.metrics['passed'] + self.metrics['revised']
            if eligible > 0:
                self.metrics['boundary_quality_rate'] = self.metrics['no_changes_needed'] / eligible

        return validated_clips

    def _validate_and_refine(
        self,
        client,
        thought: Dict,
        segments: List[Dict],
        min_duration: Optional[int],
        max_duration: Optional[int]
    ) -> Optional[Dict]:
        """
        Validate and iteratively refine a single thought

        Args:
            client: OpenAI client
            thought: Thought from Layer 2
            segments: Transcript segments
            min_duration: Optional min duration
            max_duration: Optional max duration

        Returns:
            Validated clip dict or None if failed
        """
        current_start = thought['expanded_start']
        current_end = thought['expanded_end']
        iteration = 0
        refinement_history = []

        while iteration < self.MAX_ITERATIONS:
            iteration += 1

            # Extract clip text
            clip_text = extract_clip_text(segments, current_start, current_end)

            if not clip_text:
                return None

            # Validate standalone quality
            result = self._validate_single(
                client,
                clip_text,
                current_start,
                current_end,
                thought
            )

            if not result:
                return None

            refined_start, refined_end, standalone_score, editor_notes, rejection_reason = result

            # Check duration constraints
            duration = refined_end - refined_start
            if min_duration and duration < min_duration:
                return {
                    'thought_id': thought['moment_id'],
                    'refined_start': current_start,
                    'refined_end': current_end,
                    'standalone_score': standalone_score,
                    'verdict': 'REJECT',
                    'rejection_reason': 'duration_constraint',
                    'editor_notes': f"Duration {duration:.1f}s below minimum {min_duration}s",
                    'complete_thought': thought
                }

            if max_duration and duration > max_duration:
                return {
                    'thought_id': thought['moment_id'],
                    'refined_start': current_start,
                    'refined_end': current_end,
                    'standalone_score': standalone_score,
                    'verdict': 'REJECT',
                    'rejection_reason': 'duration_constraint',
                    'editor_notes': f"Duration {duration:.1f}s exceeds maximum {max_duration}s",
                    'complete_thought': thought
                }

            refinement_history.append({
                'iteration': iteration,
                'start': current_start,
                'end': current_end,
                'score': standalone_score
            })

            # Determine verdict
            if standalone_score >= self.PASS_THRESHOLD:
                # PASS: Standalone quality is good
                return {
                    'thought_id': thought['moment_id'],
                    'refined_start': refined_start,
                    'refined_end': refined_end,
                    'standalone_score': standalone_score,
                    'verdict': 'PASS',
                    'rejection_reason': None,
                    'editor_notes': editor_notes,
                    'complete_thought': thought,
                    '_refinement_history': refinement_history
                }

            elif standalone_score >= self.REVISE_THRESHOLD:
                # REVISE: Try adjusting boundaries
                if iteration < self.MAX_ITERATIONS:
                    # Validate refinement bounds before applying
                    if not self._validate_refinement_bounds(
                        thought['expanded_start'], thought['expanded_end'],
                        refined_start, refined_end
                    ):
                        # Refinement exceeds limits - reject instead
                        return {
                            'thought_id': thought['moment_id'],
                            'refined_start': current_start,
                            'refined_end': current_end,
                            'standalone_score': standalone_score,
                            'verdict': 'REJECT',
                            'rejection_reason': rejection_reason or 'structural_issue',
                            'editor_notes': f"Needed adjustments exceed 15s limit. {editor_notes}",
                            'complete_thought': thought,
                            '_refinement_history': refinement_history
                        }

                    # Try refined boundaries
                    current_start = refined_start
                    current_end = refined_end
                    continue
                else:
                    # Out of iterations, mark as REVISE (marginal quality)
                    return {
                        'thought_id': thought['moment_id'],
                        'refined_start': refined_start,
                        'refined_end': refined_end,
                        'standalone_score': standalone_score,
                        'verdict': 'REVISE',
                        'rejection_reason': None,
                        'editor_notes': f"After {iteration} iterations: {editor_notes}",
                        'complete_thought': thought,
                        '_refinement_history': refinement_history
                    }

            else:
                # REJECT: Score too low, fundamentally requires prior context
                return {
                    'thought_id': thought['moment_id'],
                    'refined_start': current_start,
                    'refined_end': current_end,
                    'standalone_score': standalone_score,
                    'verdict': 'REJECT',
                    'rejection_reason': rejection_reason,
                    'editor_notes': editor_notes,
                    'complete_thought': thought,
                    '_refinement_history': refinement_history
                }

        # Should not reach here, but handle gracefully
        return {
            'thought_id': thought['moment_id'],
            'refined_start': current_start,
            'refined_end': current_end,
            'standalone_score': 0.0,
            'verdict': 'REJECT',
            'editor_notes': 'Max iterations exceeded',
            'complete_thought': thought
        }

    def _validate_refinement_bounds(
        self,
        original_start: float,
        original_end: float,
        refined_start: float,
        refined_end: float
    ) -> bool:
        """
        Ensure refinements don't exceed hard limits

        Args:
            original_start: Original start time from Layer 2
            original_end: Original end time from Layer 2
            refined_start: Proposed refined start time
            refined_end: Proposed refined end time

        Returns:
            bool: True if adjustments are within limits, False otherwise
        """
        MAX_ADJUSTMENT_SECONDS = 15.0

        start_adjustment = abs(original_start - refined_start)
        end_adjustment = abs(original_end - refined_end)

        if start_adjustment > MAX_ADJUSTMENT_SECONDS:
            return False
        if end_adjustment > MAX_ADJUSTMENT_SECONDS:
            return False

        return True

    def _validate_single(
        self,
        client,
        clip_text: str,
        start: float,
        end: float,
        thought: Dict
    ) -> Optional[Tuple[float, float, float, str, Optional[str]]]:
        """
        Validate standalone quality of a single clip

        Args:
            client: OpenAI client
            clip_text: Extracted transcript text for clip
            start: Current start time
            end: Current end time
            thought: Original thought from Layer 2

        Returns:
            Tuple of (refined_start, refined_end, standalone_score, editor_notes, rejection_reason)
            or None if failed
        """
        prompt = self._create_prompt(clip_text, start, end, thought)

        # Retry configuration for rate limits
        max_retries = 5
        base_delay = 2.0

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a senior video editor evaluating whether clips can stand alone without prior context."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,  # Low temp for consistent evaluation
                    response_format={"type": "json_object"}
                )

                # Track metrics
                self.metrics['api_calls'] += 1
                self.metrics['tokens_used'] += response.usage.total_tokens

                # Calculate cost (GPT-4o-mini pricing: $0.15/1M input, $0.60/1M output)
                input_cost = (response.usage.prompt_tokens / 1_000_000) * 0.15
                output_cost = (response.usage.completion_tokens / 1_000_000) * 0.60
                self.metrics['cost_usd'] += input_cost + output_cost

                # Parse response
                result = json.loads(response.choices[0].message.content)

                refined_start = float(result.get('refined_start', start))
                refined_end = float(result.get('refined_end', end))
                standalone_score = float(result['standalone_score'])
                editor_notes = result['editor_notes']
                rejection_reason = result.get('rejection_reason')

                return (refined_start, refined_end, standalone_score, editor_notes, rejection_reason)

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"      ⚠️  Failed to parse validation response: {e}")
                return None

            except Exception as e:
                error_str = str(e)

                # Check if this is a rate limit error
                if "rate_limit_exceeded" in error_str or "429" in error_str:
                    # Calculate wait time
                    wait_time = base_delay * (2 ** attempt)

                    # Try to parse suggested wait time from error
                    import re
                    match = re.search(r'try again in (\d+\.?\d*)s', error_str)
                    if match:
                        wait_time = float(match.group(1)) + 1.0

                    if attempt < max_retries - 1:
                        print(f"      ⚠️  API error during validation: {e}")
                        print(f"      ⏳ Retrying in {wait_time:.1f}s (attempt {attempt + 2}/{max_retries})...")
                        import time
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"      ❌ Validation failed after {max_retries} retries")
                        return None
                else:
                    # Non-rate-limit error
                    print(f"      ⚠️  API error during validation: {e}")
                    return None

        return None

    def _create_prompt(
        self,
        clip_text: str,
        start: float,
        end: float,
        thought: Dict
    ) -> str:
        """
        Create Layer 3 validation prompt

        Based on EDITORIAL_ARCHITECTURE.md lines 751-783

        Args:
            clip_text: Extracted transcript text
            start: Current start time
            end: Current end time
            thought: Thought from Layer 2

        Returns:
            Prompt string
        """
        duration = end - start
        start_ts = format_timestamp(start)
        end_ts = format_timestamp(end)

        return f"""ROLE: Senior video editor evaluating standalone clip quality.

CONTEXT:
You're evaluating a {duration:.1f}s clip for a short-form video platform (YouTube Shorts, TikTok, Instagram Reels).

Clip timestamps: [{start_ts}] to [{end_ts}]
Original core idea: {thought['original_moment']['core_idea']}

CRITICAL QUESTION:
Can someone who JUST clicked on this clip understand it without any prior context from the video?

CLIP TRANSCRIPT:
{clip_text}

EVALUATION CRITERIA:

1. **Who/What Context:**
   - Is it clear WHO is speaking or who/what this is about?
   - If pronouns are used ("he", "she", "they", "it"), is the referent clear?
   - Score 0.0 if critical context is missing

2. **Topic/Situation:**
   - Is the topic or situation explained within the clip?
   - Can a viewer understand what's being discussed?
   - Score 0.0 if viewer would be confused about the topic

3. **Stakes/Relevance:**
   - Is it clear WHY this matters or why the viewer should care?
   - Are the stakes or implications explained?
   - Lower score if motivation is unclear

4. **Unresolved References:**
   - Are there references to "this", "that", "the problem", "the solution" without explanation?
   - Are there assumed facts not stated in the clip?
   - Significantly reduce score for vague references

5. **Beginning/Middle/End:**
   - Does the clip have a clear beginning (setup)?
   - Does it have substance (middle)?
   - Does it have resolution or payoff (end)?
   - Reduce score if clip feels incomplete

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

BOUNDARY REFINEMENT RULES:
- You may suggest MINOR adjustments only
- MAX ADJUSTMENT: ±2 sentences (±15 seconds)
- Only adjust if standalone_score < 0.7
- Focus on fixing missing context, NOT restructuring the clip
- If major changes needed (>15s adjustment), REJECT instead

Example acceptable adjustments:
- Add 1 sentence at start to clarify "the problem" being discussed
- Add 1 sentence at end to complete resolution

Example unacceptable adjustments:
- Expanding 20+ seconds backward for full backstory
- Reworking the entire clip structure

OUTPUT JSON ONLY:
{{
  "standalone_score": 0.75,
  "refined_start": {start},
  "refined_end": {end},
  "changes_made": false,
  "adjustment_type": null,
  "rejection_reason": null,
  "editor_notes": "Brief explanation of score and any issues",
  "missing_context": ["List of", "missing context", "if any"],
  "strengths": ["What works", "well"],
  "weaknesses": ["What's", "problematic"]
}}

FIELD DEFINITIONS:
- changes_made: boolean - Did you adjust the boundaries at all?
- adjustment_type: null | "expanded_start" | "expanded_end" | "both" - What changed?
- rejection_reason: null | "missing_premise" | "dangling_reference" | "incomplete_resolution" | "topic_drift" | "duration_constraint" | "structural_issue" - Why rejected (if score < 0.4)

RULES:
- Be honest and strict - we want GREAT standalone clips, not mediocre ones
- Default refined times to current times unless you have specific boundary suggestions
- If no changes made, set changes_made=false and adjustment_type=null
- Editor notes should be actionable and specific
- Score based on what's IN the clip, not what COULD be added
- REJECT clips needing >15s adjustment rather than expanding them
"""

    def get_metrics_summary(self) -> str:
        """
        Get formatted metrics summary

        Returns:
            Formatted string with metrics
        """
        return f"""Layer 3 Metrics:
  API Calls: {self.metrics['api_calls']}
  Tokens Used: {self.metrics['tokens_used']:,}
  Cost: ${self.metrics['cost_usd']:.3f}
  Passed: {self.metrics['passed']}
  Revised: {self.metrics['revised']}
  Rejected: {self.metrics['rejected']}
  Pass Rate: {self.metrics['pass_rate']:.1%}
  Boundary Quality: {self.metrics['boundary_quality_rate']:.1%} (Layer 2 boundaries kept as-is)"""
