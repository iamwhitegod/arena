"""
Layer 2: Thought Boundary Analyzer

Expands rough moments from Layer 1 into complete thought boundaries.
Looks backward for setup and forward for payoff/resolution.

Uses parallel processing to analyze multiple moments simultaneously.
"""

from typing import List, Dict, Optional
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from .utils import format_transcript_with_timestamps, format_timestamp


class ThoughtBoundaryAnalyzer:
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

    Strategy:
        - Extract 60s context window around each moment
        - Look backward: Where does speaker START setting up this idea?
        - Look forward: Where does idea reach COMPLETION/PAYOFF?
        - Include necessary setup and resolution
        - Return confidence score for boundary quality

    Parallel Processing:
        - Uses ThreadPoolExecutor for concurrent API calls
        - Default 5 workers for balance of speed and rate limits
        - Processes multiple moments simultaneously
    """

    CONTEXT_WINDOW_SECONDS = 60.0  # Extract ±60s around moment for context
    DEFAULT_MAX_WORKERS = 5         # Parallel API calls

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize thought boundary analyzer

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o, can use gpt-4o-mini for cost savings)
                  Note: gpt-4o-mini may require validation to ensure quality maintained
        """
        self.api_key = api_key
        self.model = model
        self.metrics = {
            'api_calls': 0,
            'tokens_used': 0,
            'cost_usd': 0.0,
            'thoughts_analyzed': 0,
            'avg_expansion_ratio': 0.0  # How much boundaries expand on average
        }

    def analyze_all(
        self,
        moments: List[Dict],
        transcript_data: Dict,
        parallel: bool = True,
        max_workers: Optional[int] = None
    ) -> List[Dict]:
        """
        Analyze thought boundaries for all moments.

        Args:
            moments: List of moments from Layer 1 with rough_start/rough_end
            transcript_data: Full transcript data with segments
            parallel: Whether to process in parallel (default: True)
            max_workers: Number of parallel workers (default: 5)

        Returns:
            List of thought boundary dicts:
            {
                'moment_id': str,           # "moment_001"
                'expanded_start': float,    # Thought start (earlier than rough_start)
                'expanded_end': float,      # Thought end (later than rough_end)
                'thought_summary': str,     # One-sentence summary
                'confidence': float,        # 0.0-1.0
                'original_moment': Dict     # Preserve Layer 1 data
            }
        """
        if not moments:
            print("      ⚠️  No moments to analyze")
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

        thoughts = []

        if parallel and len(moments) > 1:
            # Parallel processing
            workers = max_workers or self.DEFAULT_MAX_WORKERS
            print(f"      Processing {len(moments)} moments with {workers} parallel workers...")

            with ThreadPoolExecutor(max_workers=workers) as executor:
                # Submit all tasks
                future_to_moment = {
                    executor.submit(
                        self._analyze_single,
                        client,
                        moment,
                        idx,
                        segments
                    ): (idx, moment)
                    for idx, moment in enumerate(moments, 1)
                }

                # Collect results as they complete
                for future in as_completed(future_to_moment):
                    idx, moment = future_to_moment[future]
                    try:
                        thought = future.result()
                        if thought:
                            thoughts.append(thought)
                            print(f"      ✓ Moment {idx}/{len(moments)} analyzed")
                    except Exception as e:
                        print(f"      ⚠️  Moment {idx} failed: {e}")
                        continue
        else:
            # Sequential processing
            print(f"      Processing {len(moments)} moments sequentially...")
            for idx, moment in enumerate(moments, 1):
                try:
                    thought = self._analyze_single(client, moment, idx, segments)
                    if thought:
                        thoughts.append(thought)
                        print(f"      ✓ Moment {idx}/{len(moments)} analyzed")
                except Exception as e:
                    print(f"      ⚠️  Moment {idx} failed: {e}")
                    continue

        # Calculate metrics
        self.metrics['thoughts_analyzed'] = len(thoughts)
        if thoughts:
            expansion_ratios = [
                (t['expanded_end'] - t['expanded_start']) /
                (t['original_moment']['rough_end'] - t['original_moment']['rough_start'])
                for t in thoughts
            ]
            self.metrics['avg_expansion_ratio'] = sum(expansion_ratios) / len(expansion_ratios)

        return thoughts

    def _analyze_single(
        self,
        client,
        moment: Dict,
        moment_id: int,
        segments: List[Dict]
    ) -> Optional[Dict]:
        """
        Analyze thought boundaries for a single moment

        Args:
            client: OpenAI client
            moment: Moment dict from Layer 1
            moment_id: Numeric ID for this moment
            segments: Full transcript segments

        Returns:
            Thought boundary dict or None if failed
        """
        # Extract context window around moment
        rough_start = moment['rough_start']
        rough_end = moment['rough_end']
        rough_center = (rough_start + rough_end) / 2

        context_start = max(0, rough_center - self.CONTEXT_WINDOW_SECONDS)
        context_end = rough_center + self.CONTEXT_WINDOW_SECONDS

        context_segments = [
            seg for seg in segments
            if seg['start'] >= context_start and seg['end'] <= context_end
        ]

        if not context_segments:
            print(f"      ⚠️  No context segments found for moment {moment_id}")
            return None

        # Format context with timestamps
        context_transcript = format_transcript_with_timestamps(context_segments)

        # Create prompt
        prompt = self._create_prompt(moment, context_transcript, rough_start, rough_end)

        # Retry configuration for rate limits
        max_retries = 5
        base_delay = 2.0

        for attempt in range(max_retries):
            try:
                # Call GPT-4o
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a senior video editor analyzing complete thought boundaries in spoken content."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.5,  # Lower temp for more consistent boundary detection
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

                # Validate and create thought dict
                thought = {
                    'moment_id': f"moment_{moment_id:03d}",
                    'expanded_start': float(result['expanded_start']),
                    'expanded_end': float(result['expanded_end']),
                    'thought_summary': result['thought_summary'],
                    'confidence': float(result['confidence']),
                    'original_moment': moment
                }

                return thought

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"      ⚠️  Failed to parse response for moment {moment_id}: {e}")
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
                        print(f"      ⚠️  API error for moment {moment_id}: {e}")
                        print(f"      ⏳ Retrying in {wait_time:.1f}s (attempt {attempt + 2}/{max_retries})...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"      ❌ Failed after {max_retries} retries for moment {moment_id}")
                        return None
                else:
                    # Non-rate-limit error
                    print(f"      ⚠️  API error for moment {moment_id}: {e}")
                    return None

        return None

    def _create_prompt(
        self,
        moment: Dict,
        context_transcript: str,
        rough_start: float,
        rough_end: float
    ) -> str:
        """
        Create Layer 2 prompt for boundary analysis

        Based on EDITORIAL_ARCHITECTURE.md lines 468-505

        Args:
            moment: Moment from Layer 1
            context_transcript: Formatted transcript with ±60s context
            rough_start: Rough start time
            rough_end: Rough end time

        Returns:
            Prompt string
        """
        rough_start_ts = format_timestamp(rough_start)
        rough_end_ts = format_timestamp(rough_end)

        return f"""ROLE: Senior video editor analyzing thought boundaries.

CONTEXT:
You identified an interesting moment in a video:
- Core Idea: {moment['core_idea']}
- Why Interesting: {moment['why_interesting']}
- Rough Timestamps: [{rough_start_ts}] to [{rough_end_ts}]
- Content Type: {moment['content_type']}

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

STRATEGY:
1. Look BACKWARD from [{rough_start_ts}]:
   - Where does the speaker BEGIN setting up this idea?
   - Include setup or framing needed for the narrative
   - Don't include unrelated prior content

2. Look FORWARD from [{rough_end_ts}]:
   - Where does this idea reach COMPLETION or PAYOFF?
   - Include resolution, conclusion, or impact
   - Don't extend into next unrelated topic

3. Ensure STRUCTURAL COMPLETENESS:
   - Does the expanded clip have a clear beginning (setup)?
   - Does it have a clear middle (core idea)?
   - Does it have a clear end (payoff/resolution)?

CONTEXT TRANSCRIPT (±60 seconds around moment):
{context_transcript}

OUTPUT JSON ONLY:
{{
  "expanded_start": 123.4,
  "expanded_end": 198.6,
  "thought_summary": "Complete one-sentence summary of the full thought from setup to payoff",
  "confidence": 0.85,
  "reasoning": "Why these boundaries feel complete (optional debug field)"
}}

HARD CONSTRAINTS:
- expanded_start should be ≤ {rough_start} (earlier or same)
- expanded_end should be ≥ {rough_end} (later or same)
- NEVER expand more than 30 seconds backward from rough_start
- NEVER expand more than 30 seconds forward from rough_end
- NEVER expand beyond topically-related content
- If idea needs >60s total expansion, confidence should be <0.5
- Typical expansion: 20-50% longer than rough timestamps
- Confidence 0.0-1.0 (0.7+ means high confidence in boundaries)
- Focus on COMPLETE THOUGHTS, not arbitrary time windows
- Stop expanding when thought is complete, not when context is perfect"""

    def get_metrics_summary(self) -> str:
        """
        Get formatted metrics summary

        Returns:
            Formatted string with metrics
        """
        return f"""Layer 2 Metrics:
  API Calls: {self.metrics['api_calls']}
  Tokens Used: {self.metrics['tokens_used']:,}
  Cost: ${self.metrics['cost_usd']:.3f}
  Thoughts Analyzed: {self.metrics['thoughts_analyzed']}
  Avg Expansion Ratio: {self.metrics['avg_expansion_ratio']:.2f}x"""
