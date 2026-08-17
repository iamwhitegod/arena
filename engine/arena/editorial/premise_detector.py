"""
Premise Detector

Searches backward from a thought seed (claim) to find where the thought begins.

The premise is the setup, context, or motivation that makes the claim meaningful:
- Question that the claim answers
- Problem that the claim solves
- Story that motivates the claim
- Direct introduction of the topic

This is the "backward search" part of thought unit construction.
"""

from typing import Dict, List, Optional
import json

from .thought_unit import safe_float, safe_text


class PremiseDetector:
    """
    Detects where a thought begins by searching backward from a claim/seed.

    Strategy:
    - Start from the seed (claim)
    - Look backward through preceding sentences
    - Find the natural starting point (premise)
    - Return premise boundary and text
    """

    # Search window configuration
    MAX_LOOKBACK_SENTENCES = 15  # Don't search more than 15 sentences back
    MAX_LOOKBACK_SECONDS = 90.0  # Don't search more than 90 seconds back

    def __init__(self, api_key=None, model: str = "gpt-4o-mini", *, chat=None):
        """
        Initialize premise detector

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
            'premises_detected': 0,
            'premises_failed': 0
        }

    def detect_premise(
        self,
        seed: Dict,
        transcript_segments: List[Dict]
    ) -> Optional[Dict]:
        """
        Detect premise by searching backward from seed.

        Args:
            seed: Thought seed dict with 'timestamp', 'text', 'rhetorical_type'
            transcript_segments: Full transcript segments with 'start', 'end', 'text'

        Returns:
            Premise dict with:
            {
                'premise_start': float,  # Timestamp where premise begins
                'premise_end': float,    # Timestamp where premise ends (seed starts)
                'premise_text': str,     # The premise text
                'premise_type': str,     # 'question', 'problem', 'story', 'direct_claim'
                'reasoning': str,        # Why this is the premise
                'confidence': float,     # Detection confidence (0.0-1.0)
                'sentences_back': int    # How many sentences backward we searched
            }

            Returns None if premise cannot be found
        """
        # Find seed position in transcript
        seed_timestamp = seed['timestamp']
        seed_text = seed['text']

        # Get segments around seed
        context = self._get_backward_context(
            seed_timestamp,
            transcript_segments
        )

        if not context['before_segments']:
            # No context before seed - seed IS the premise
            print(f"      ⚠️  No context before seed at {seed_timestamp:.1f}s")
            self.metrics['premises_failed'] += 1
            return None

        # Call GPT to find premise
        try:
            result = self._analyze_premise(
                seed_text,
                seed.get('rhetorical_type', 'unknown'),
                context
            )

            if result:
                self.metrics['premises_detected'] += 1
                return result
            else:
                self.metrics['premises_failed'] += 1
                return None

        except Exception as e:
            print(f"      ⚠️  Error detecting premise: {e}")
            self.metrics['premises_failed'] += 1
            return None

    def _get_backward_context(
        self,
        seed_timestamp: float,
        segments: List[Dict]
    ) -> Dict:
        """
        Get context before the seed for premise detection.

        Args:
            seed_timestamp: Timestamp of the seed
            segments: All transcript segments

        Returns:
            Dict with:
            {
                'before_segments': List[Dict],  # Segments before seed
                'seed_segment': Dict,           # Segment containing seed
                'lookback_start': float,        # Where we started looking
                'lookback_duration': float      # How far back we looked
            }
        """
        # Find segments before seed (within lookback window)
        min_timestamp = max(0, seed_timestamp - self.MAX_LOOKBACK_SECONDS)

        before_segments = [
            seg for seg in segments
            if seg['start'] >= min_timestamp and seg['end'] <= seed_timestamp
        ]

        # Limit to max sentences
        if len(before_segments) > self.MAX_LOOKBACK_SENTENCES:
            before_segments = before_segments[-self.MAX_LOOKBACK_SENTENCES:]

        # Find seed segment
        seed_segment = None
        for seg in segments:
            if seg['start'] <= seed_timestamp <= seg['end']:
                seed_segment = seg
                break

        lookback_start = before_segments[0]['start'] if before_segments else seed_timestamp
        lookback_duration = seed_timestamp - lookback_start

        return {
            'before_segments': before_segments,
            'seed_segment': seed_segment,
            'lookback_start': lookback_start,
            'lookback_duration': lookback_duration
        }

    def _analyze_premise(
        self,
        seed_text: str,
        rhetorical_type: str,
        context: Dict
    ) -> Optional[Dict]:
        """
        Use GPT to analyze where the premise begins.

        Args:
            seed_text: The seed/claim text
            rhetorical_type: Type of rhetoric (argument, teaching, story, etc.)
            context: Context dict with before_segments

        Returns:
            Premise dict or None if not found
        """
        # Create prompt
        prompt = self._create_premise_prompt(
            seed_text,
            rhetorical_type,
            context['before_segments']
        )

        # Call LLM
        from arena.providers.base import ResponseMode
        from arena.providers.retry import retry_with_backoff

        response = retry_with_backoff(
            lambda: self._chat.complete(
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at identifying where thoughts begin in spoken content. You find the natural starting point (premise) that sets up a claim or insight."
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
            if not isinstance(result, dict):
                return None

            premise_index = result.get('premise_start_index', -1)

            if (
                isinstance(premise_index, bool)
                or not isinstance(premise_index, int)
                or premise_index < 0
                or premise_index >= len(context['before_segments'])
            ):
                return None

            # Build premise dict
            premise_segment = context['before_segments'][premise_index]
            last_segment = context['before_segments'][-1]

            # Collect all text from premise start to seed
            premise_segments = context['before_segments'][premise_index:]
            premise_text = ' '.join(seg['text'] for seg in premise_segments)

            return {
                'premise_start': premise_segment['start'],
                'premise_end': last_segment['end'],
                'premise_text': premise_text,
                'premise_type': safe_text(result.get('premise_type'), 'unknown', 100),
                'reasoning': safe_text(result.get('reasoning')),
                'confidence': safe_float(result.get('confidence'), 0.5),
                'sentences_back': len(context['before_segments']) - premise_index
            }

        except (json.JSONDecodeError, KeyError, IndexError):
            print("      ⚠️  Failed to parse premise response")
            return None

    def _create_premise_prompt(
        self,
        seed_text: str,
        rhetorical_type: str,
        before_segments: List[Dict]
    ) -> str:
        """
        Create prompt for premise detection.

        Args:
            seed_text: The seed/claim text
            rhetorical_type: Type of rhetoric
            before_segments: Segments before the seed

        Returns:
            Prompt string
        """
        # Format preceding sentences with indices
        context_text = ""
        for idx, seg in enumerate(before_segments):
            context_text += f"[{idx}] {seg['text']}\n"

        return f"""You are analyzing spoken content to find where a THOUGHT BEGINS.

CLAIM/SEED (what we're working backward from):
"{seed_text}"

RHETORICAL TYPE: {rhetorical_type}

PRECEDING SENTENCES (indexed):
{context_text}

TASK:
Identify the FIRST sentence (by index) where this thought is introduced or motivated.

Look for the natural beginning:

1. **Question** that the claim answers:
   - "Have you ever wondered..."
   - "So the question is..."
   - "People always ask me..."

2. **Problem** that the claim solves:
   - "The issue is..."
   - "Here's what people get wrong..."
   - "The challenge is..."

3. **Story** that motivates the claim:
   - "Let me tell you about..."
   - "I remember when..."
   - Narrative setup

4. **Direct introduction**:
   - "Let me explain..."
   - "Here's the thing..."
   - "I want to talk about..."

5. **Context setting**:
   - Background information
   - Scene setting
   - Topic introduction

RULES:
- Find the EARLIEST sentence that begins this thought
- Don't go back too far (premise should be relevant to claim)
- Prefer natural topic transitions
- If unsure, it's better to start slightly earlier than too late

RETURN JSON:
{{
  "premise_start_index": <index 0-{len(before_segments)-1}>,
  "premise_type": "question|problem|story|direct_claim|context",
  "reasoning": "Why this is where the thought begins",
  "confidence": <0.0-1.0>
}}

If you cannot find a clear premise (claim appears standalone), return:
{{
  "premise_start_index": -1,
  "premise_type": "none",
  "reasoning": "Claim is self-contained without setup",
  "confidence": 0.0
}}
"""

    def detect_premises_batch(
        self,
        seeds: List[Dict],
        transcript_segments: List[Dict],
        verbose: bool = True
    ) -> List[Optional[Dict]]:
        """
        Detect premises for multiple seeds (batch processing).

        Args:
            seeds: List of seed dicts
            transcript_segments: Full transcript segments
            verbose: Print progress

        Returns:
            List of premise dicts (or None for failed detections)
        """
        premises = []

        for idx, seed in enumerate(seeds, 1):
            if verbose:
                print(f"      Detecting premise {idx}/{len(seeds)} (seed at {seed['timestamp']:.1f}s)...")

            premise = self.detect_premise(seed, transcript_segments)

            if premise:
                if verbose:
                    print(f"      ✓ Found premise {premise['sentences_back']} sentences back ({premise['premise_type']})")
            else:
                if verbose:
                    print(f"      ✗ No premise found")

            premises.append(premise)

        if verbose:
            success_rate = self.metrics['premises_detected'] / len(seeds) * 100 if seeds else 0
            print(f"      Premise detection: {self.metrics['premises_detected']}/{len(seeds)} ({success_rate:.0f}%)")

        return premises
