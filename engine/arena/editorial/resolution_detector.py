"""
Resolution Detector

Searches forward from a thought seed (claim) to find where the thought completes.

The resolution is the closure, explanation, or conclusion that makes the thought feel complete:
- Supporting reasoning for the claim
- Examples that clarify the point
- Natural transition to next topic
- Rhetorical closure signal

This is the "forward search" part of thought unit construction.
"""

from typing import Dict, List, Optional
import json


class ResolutionDetector:
    """
    Detects where a thought completes by searching forward from a claim/seed.

    Strategy:
    - Start from the seed (claim)
    - Look forward through following sentences
    - Find the natural ending point (resolution)
    - Return resolution boundary and text
    """

    # Search window configuration
    MAX_LOOKAHEAD_SENTENCES = 20  # Don't search more than 20 sentences forward
    MAX_LOOKAHEAD_SECONDS = 120.0  # Don't search more than 2 minutes forward

    def __init__(self, api_key=None, model: str = "gpt-4o-mini", *, chat=None):
        """
        Initialize resolution detector

        Args:
            api_key: OpenAI API key (legacy, creates OpenAIChatModel internally)
            model: Model to use (default: gpt-4o-mini for cost efficiency)
            chat: ChatModel instance (preferred)
        """
        if chat is not None:
            self._chat = chat
        elif api_key is not None:
            from arena.providers.openai_adapter import OpenAIChatModel
            self._chat = OpenAIChatModel(api_key=api_key, model=model)
        else:
            raise ValueError("Either chat or api_key required")
        self.model = model
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0,
            'cost_usd': 0.0,
            'resolutions_detected': 0,
            'resolutions_failed': 0
        }

    def detect_resolution(
        self,
        seed: Dict,
        transcript_segments: List[Dict]
    ) -> Optional[Dict]:
        """
        Detect resolution by searching forward from seed.

        Args:
            seed: Thought seed dict with 'timestamp', 'text', 'rhetorical_type'
            transcript_segments: Full transcript segments with 'start', 'end', 'text'

        Returns:
            Resolution dict with:
            {
                'resolution_start': float,  # Timestamp where resolution begins (seed ends)
                'resolution_end': float,    # Timestamp where resolution ends
                'resolution_text': str,     # The resolution text
                'completion_type': str,     # 'reasoning', 'example', 'transition', 'restatement'
                'is_complete': bool,        # Whether thought feels complete
                'reasoning': str,           # Why this is the resolution
                'confidence': float,        # Detection confidence (0.0-1.0)
                'sentences_forward': int    # How many sentences forward we searched
            }

            Returns None if resolution cannot be found
        """
        # Find seed position in transcript
        seed_timestamp = seed['timestamp']
        seed_text = seed['text']

        # Get segments around seed
        context = self._get_forward_context(
            seed_timestamp,
            transcript_segments
        )

        if not context['after_segments']:
            # No context after seed - seed IS the resolution
            print(f"      ⚠️  No context after seed at {seed_timestamp:.1f}s")
            self.metrics['resolutions_failed'] += 1
            return None

        # Call GPT to find resolution
        try:
            result = self._analyze_resolution(
                seed_text,
                seed.get('rhetorical_type', 'unknown'),
                context
            )

            if result:
                self.metrics['resolutions_detected'] += 1
                return result
            else:
                self.metrics['resolutions_failed'] += 1
                return None

        except Exception as e:
            print(f"      ⚠️  Error detecting resolution: {e}")
            self.metrics['resolutions_failed'] += 1
            return None

    def _get_forward_context(
        self,
        seed_timestamp: float,
        segments: List[Dict]
    ) -> Dict:
        """
        Get context after the seed for resolution detection.

        Args:
            seed_timestamp: Timestamp of the seed
            segments: All transcript segments

        Returns:
            Dict with:
            {
                'after_segments': List[Dict],  # Segments after seed
                'seed_segment': Dict,          # Segment containing seed
                'lookahead_end': float,        # Where we stopped looking
                'lookahead_duration': float    # How far forward we looked
            }
        """
        # Find segments after seed (within lookahead window)
        max_timestamp = seed_timestamp + self.MAX_LOOKAHEAD_SECONDS

        after_segments = [
            seg for seg in segments
            if seg['start'] >= seed_timestamp and seg['start'] < max_timestamp
        ]

        # Limit to max sentences
        if len(after_segments) > self.MAX_LOOKAHEAD_SENTENCES:
            after_segments = after_segments[:self.MAX_LOOKAHEAD_SENTENCES]

        # Find seed segment
        seed_segment = None
        for seg in segments:
            if seg['start'] <= seed_timestamp <= seg['end']:
                seed_segment = seg
                break

        lookahead_end = after_segments[-1]['end'] if after_segments else seed_timestamp
        lookahead_duration = lookahead_end - seed_timestamp

        return {
            'after_segments': after_segments,
            'seed_segment': seed_segment,
            'lookahead_end': lookahead_end,
            'lookahead_duration': lookahead_duration
        }

    def _analyze_resolution(
        self,
        seed_text: str,
        rhetorical_type: str,
        context: Dict
    ) -> Optional[Dict]:
        """
        Use GPT to analyze where the resolution ends.

        Args:
            seed_text: The seed/claim text
            rhetorical_type: Type of rhetoric (argument, teaching, story, etc.)
            context: Context dict with after_segments

        Returns:
            Resolution dict or None if not found
        """
        # Create prompt
        prompt = self._create_resolution_prompt(
            seed_text,
            rhetorical_type,
            context['after_segments']
        )

        # Call LLM
        from arena.providers.base import ResponseMode
        from arena.providers.retry import retry_with_backoff

        response = retry_with_backoff(
            lambda: self._chat.complete(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at identifying where thoughts complete in spoken content. You find the natural ending point (resolution) that provides closure to a claim or insight."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.2,
                response_mode=ResponseMode.JSON,
            )
        )

        # Track metrics
        self.metrics['api_calls'] += 1
        self.metrics['tokens_used'] += response.usage.total_tokens
        if response.usage.estimated_cost_usd is not None:
            self.metrics['cost_usd'] += float(response.usage.estimated_cost_usd)

        # Parse response
        try:
            result = response.parsed

            resolution_index = result.get('resolution_end_index', -1)

            if resolution_index < 0 or resolution_index >= len(context['after_segments']):
                return None

            # Build resolution dict
            first_segment = context['after_segments'][0]
            resolution_segment = context['after_segments'][resolution_index]

            # Collect all text from seed to resolution end
            resolution_segments = context['after_segments'][:resolution_index + 1]
            resolution_text = ' '.join(seg['text'] for seg in resolution_segments)

            return {
                'resolution_start': first_segment['start'],
                'resolution_end': resolution_segment['end'],
                'resolution_text': resolution_text,
                'completion_type': result.get('completion_type', 'unknown'),
                'is_complete': result.get('is_complete', False),
                'reasoning': result.get('reasoning', ''),
                'confidence': result.get('confidence', 0.5),
                'sentences_forward': resolution_index + 1
            }

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            print(f"      ⚠️  Failed to parse resolution response: {e}")
            return None

    def _create_resolution_prompt(
        self,
        seed_text: str,
        rhetorical_type: str,
        after_segments: List[Dict]
    ) -> str:
        """
        Create prompt for resolution detection.

        Args:
            seed_text: The seed/claim text
            rhetorical_type: Type of rhetoric
            after_segments: Segments after the seed

        Returns:
            Prompt string
        """
        # Format following sentences with indices
        context_text = ""
        for idx, seg in enumerate(after_segments):
            context_text += f"[{idx}] {seg['text']}\n"

        return f"""You are analyzing spoken content to find where a THOUGHT COMPLETES.

CLAIM/SEED (core statement):
"{seed_text}"

RHETORICAL TYPE: {rhetorical_type}

FOLLOWING SENTENCES (indexed):
{context_text}

TASK:
Identify the LAST sentence (by index) needed for this thought to feel COMPLETE.

Look for natural closure:

1. **Supporting reasoning**:
   - "Because..."
   - "The reason is..."
   - Explanation that supports the claim

2. **Examples that clarify**:
   - "For instance..."
   - "Let me give you an example..."
   - Concrete illustration

3. **Transition to new topic**:
   - "So that's why..."
   - "Now let's talk about..."
   - Clear topic shift

4. **Restatement/emphasis**:
   - "That's the key point"
   - Rephrasing the claim
   - Rhetorical emphasis

5. **Conclusion markers**:
   - "So remember..."
   - "The point is..."
   - Clear ending signal

RULES:
- Find where the thought feels COMPLETE (not abrupt)
- Don't include the NEXT thought (stop at natural boundary)
- Prefer shorter if complete over longer without closure
- A complete thought has: claim + support/explanation + sense of closure

COMPLETENESS CHECK:
- Would this make sense as a standalone clip?
- Does it answer the question raised by the claim?
- Does it feel finished (not mid-thought)?

RETURN JSON:
{{
  "resolution_end_index": <index 0-{len(after_segments)-1}>,
  "completion_type": "reasoning|example|transition|restatement|conclusion",
  "is_complete": <true|false>,
  "reasoning": "Why this is where the thought completes",
  "confidence": <0.0-1.0>
}}

If you cannot find a clear resolution (claim trails off or changes topics), return:
{{
  "resolution_end_index": -1,
  "completion_type": "incomplete",
  "is_complete": false,
  "reasoning": "Thought does not complete properly",
  "confidence": 0.0
}}
"""

    def detect_resolutions_batch(
        self,
        seeds: List[Dict],
        transcript_segments: List[Dict],
        verbose: bool = True
    ) -> List[Optional[Dict]]:
        """
        Detect resolutions for multiple seeds (batch processing).

        Args:
            seeds: List of seed dicts
            transcript_segments: Full transcript segments
            verbose: Print progress

        Returns:
            List of resolution dicts (or None for failed detections)
        """
        resolutions = []

        for idx, seed in enumerate(seeds, 1):
            if verbose:
                print(f"      Detecting resolution {idx}/{len(seeds)} (seed at {seed['timestamp']:.1f}s)...")

            resolution = self.detect_resolution(seed, transcript_segments)

            if resolution:
                if verbose:
                    complete_str = "complete" if resolution['is_complete'] else "incomplete"
                    print(f"      ✓ Found resolution {resolution['sentences_forward']} sentences forward ({resolution['completion_type']}, {complete_str})")
            else:
                if verbose:
                    print(f"      ✗ No resolution found")

            resolutions.append(resolution)

        if verbose:
            success_rate = self.metrics['resolutions_detected'] / len(seeds) * 100 if seeds else 0
            complete_rate = sum(1 for r in resolutions if r and r['is_complete']) / len(seeds) * 100 if seeds else 0
            print(f"      Resolution detection: {self.metrics['resolutions_detected']}/{len(seeds)} ({success_rate:.0f}%)")
            print(f"      Complete thoughts: {sum(1 for r in resolutions if r and r['is_complete'])}/{len(seeds)} ({complete_rate:.0f}%)")

        return resolutions
