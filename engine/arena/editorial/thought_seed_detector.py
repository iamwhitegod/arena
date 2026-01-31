"""
Thought Seed Detector (Layer 1 Redesign)

Detects "seeds" - claim/insight moments that anchor complete thoughts.

Strategy:
- Use sliding window approach (2-minute windows)
- Find 3-5 seeds per window
- Detect rhetorical type for each seed
- Over-detect by 4x (will be filtered by later layers)

This replaces the traditional "moment detection" approach which finds emotional
peaks. Instead, we find CLAIMS/INSIGHTS that form the centers of complete thoughts,
each with a premise before it and resolution after it.
"""

from typing import List, Dict, Optional
from .thought_unit import RhetoricalType
import json
import time


class ThoughtSeedDetector:
    """
    Detects thought seeds - moments that anchor complete thoughts.

    A "seed" is a claim, insight, or key moment that likely has:
    - A premise before it (setup/context)
    - A resolution after it (conclusion/closure)

    Unlike traditional "moment detection" which finds emotional peaks,
    this finds CLAIMS/INSIGHTS that form centers of complete thoughts.
    """

    # Window configuration
    WINDOW_SIZE = 120  # 2 minutes per window
    WINDOW_OVERLAP = 30  # 30 second overlap between windows

    # Deduplication threshold
    DEDUP_TIME_THRESHOLD = 10.0  # Seeds within 10 seconds
    DEDUP_TEXT_THRESHOLD = 0.7   # 70% text similarity = duplicate

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize thought seed detector

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4o)
        """
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

        Over-detects by 4x (target 10 clips → detect 40 seeds) to ensure
        we have enough candidates for later filtering.

        Args:
            transcript_data: Transcript dict with 'segments', 'text', 'duration'
            target_count: Target number of final clips (will detect 4x this)

        Returns:
            List of seed dicts with:
            {
                'seed_id': 'seed_001',
                'timestamp': float,  # Approximate timestamp
                'text': str,  # The exact seed sentence/phrase
                'rhetorical_type': str,  # 'argument', 'teaching', 'story', 'advice', 'qa'
                'interest_score': float,  # 0.0-1.0
                'reasoning': str,  # Why this is a good seed
                'likely_has_premise': bool,
                'likely_has_resolution': bool,
                'context_before': str,  # Previous sentences for context
                'context_after': str  # Following sentences for context
            }
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package required. Install with: pip install openai")

        client = OpenAI(api_key=self.api_key)
        segments = transcript_data.get('segments', [])

        if not segments:
            print("      ⚠️  No segments in transcript")
            return []

        # Over-detect by 4x to cast a wide net
        target_seeds = target_count * 4
        print(f"      Detecting thought seeds (target: {target_seeds} seeds for {target_count} clips)...")

        # Create sliding windows
        windows = self._create_windows(segments)
        print(f"      Created {len(windows)} sliding windows ({self.WINDOW_SIZE}s each, {self.WINDOW_OVERLAP}s overlap)")

        # Calculate seeds per window
        seeds_per_window = max(3, target_seeds // len(windows))

        # Detect seeds in each window
        all_seeds = []
        for idx, window in enumerate(windows, 1):
            print(f"      Analyzing window {idx}/{len(windows)} ({window['start']:.1f}s - {window['end']:.1f}s)...")

            try:
                window_seeds = self._detect_seeds_in_window(
                    client,
                    window,
                    seeds_per_window
                )
                all_seeds.extend(window_seeds)
                print(f"      ✓ Found {len(window_seeds)} seeds in window {idx}")
                self.metrics['windows_analyzed'] += 1
            except Exception as e:
                print(f"      ⚠️  Error in window {idx}: {e}")
                continue

            # Rate limit delay between windows
            if idx < len(windows):
                time.sleep(1.0)  # Short delay to avoid rate limits

        print(f"      Total seeds before deduplication: {len(all_seeds)}")

        # Deduplicate seeds from overlapping windows
        unique_seeds = self._deduplicate_seeds(all_seeds)
        print(f"      After deduplication: {len(unique_seeds)} unique seeds")

        # Sort by interest score and take top N
        top_seeds = sorted(
            unique_seeds,
            key=lambda s: s['interest_score'],
            reverse=True
        )[:target_seeds]

        # Assign final seed IDs
        for idx, seed in enumerate(top_seeds, 1):
            seed['seed_id'] = f"seed_{idx:03d}"

        self.metrics['seeds_detected'] = len(top_seeds)
        print(f"      ✓ Detected {len(top_seeds)} thought seeds")

        return top_seeds

    def _create_windows(self, segments: List[Dict]) -> List[Dict]:
        """
        Create sliding windows over transcript.

        Args:
            segments: List of transcript segments with 'start', 'end', 'text'

        Returns:
            List of window dicts:
            {
                'start': float,
                'end': float,
                'segments': List[Dict],
                'text': str
            }
        """
        if not segments:
            return []

        windows = []

        # Get total duration from last segment
        total_duration = segments[-1]['end'] if segments else 0

        # Create sliding windows
        start = 0.0
        while start < total_duration:
            end = min(start + self.WINDOW_SIZE, total_duration)

            # Get segments in this window
            window_segments = [
                seg for seg in segments
                if seg['start'] >= start and seg['start'] < end
            ]

            if window_segments:
                # Combine text from all segments
                window_text = ' '.join(seg['text'] for seg in window_segments)

                windows.append({
                    'start': start,
                    'end': end,
                    'segments': window_segments,
                    'text': window_text
                })

            # Move window forward (with overlap)
            start += (self.WINDOW_SIZE - self.WINDOW_OVERLAP)

        return windows

    def _detect_seeds_in_window(
        self,
        client,
        window: Dict,
        target_count: int
    ) -> List[Dict]:
        """
        Detect seeds in a single window using GPT.

        Args:
            client: OpenAI client
            window: Window dict with 'text', 'start', 'end', 'segments'
            target_count: Number of seeds to find in this window

        Returns:
            List of seed dicts
        """
        prompt = self._create_seed_detection_prompt(window['text'], target_count)

        # Retry logic for rate limits
        max_retries = 3
        for attempt in range(max_retries):
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
                    temperature=0.3,  # Lower temperature for more consistent detection
                    response_format={"type": "json_object"}
                )

                # Track metrics
                self.metrics['api_calls'] += 1
                self.metrics['tokens_used'] += response.usage.total_tokens

                # Calculate cost (GPT-4o pricing: $2.50/1M input, $10/1M output tokens)
                input_cost = (response.usage.prompt_tokens / 1_000_000) * 2.50
                output_cost = (response.usage.completion_tokens / 1_000_000) * 10.00
                self.metrics['cost_usd'] += input_cost + output_cost

                # Parse response
                result = json.loads(response.choices[0].message.content)
                seeds = result.get('seeds', [])

                # Add window context and extract context snippets
                processed_seeds = []
                for seed in seeds:
                    # Map timestamp to window coordinates
                    seed['timestamp'] = window['start'] + seed.get('timestamp_approx', 0)

                    # Extract context before/after from window text
                    seed_text = seed['text']
                    window_text = window['text']

                    # Simple context extraction (50 chars before/after)
                    pos = window_text.find(seed_text)
                    if pos != -1:
                        context_start = max(0, pos - 100)
                        context_end = min(len(window_text), pos + len(seed_text) + 100)
                        seed['context_before'] = window_text[context_start:pos].strip()
                        seed['context_after'] = window_text[pos + len(seed_text):context_end].strip()
                    else:
                        seed['context_before'] = ''
                        seed['context_after'] = ''

                    processed_seeds.append(seed)

                return processed_seeds

            except Exception as e:
                error_str = str(e)
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    if attempt < max_retries - 1:
                        wait_time = 2.0 * (2 ** attempt)  # Exponential backoff
                        print(f"      ⚠️  Rate limit, waiting {wait_time:.1f}s...")
                        time.sleep(wait_time)
                        continue
                raise

        return []

    def _create_seed_detection_prompt(
        self,
        window_text: str,
        target_count: int
    ) -> str:
        """
        Create prompt for seed detection.

        This is the CRITICAL prompt that determines detection quality.

        Args:
            window_text: Text from the window
            target_count: Number of seeds to find

        Returns:
            Prompt string
        """
        return f"""You are analyzing a segment of spoken content to find THOUGHT SEEDS.

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
   - Controversial or strong statements

2. **Teaching moments** (Explanations):
   - "Let me show you...", "The key is...", "Here's what..."
   - Concepts being explained
   - Frameworks or principles being shared

3. **Story pivots** (Turning points):
   - "Then this happened...", "What I realized..."
   - Revelations, surprises, lessons learned
   - Key moments in narratives

4. **Practical advice** (Actionable insights):
   - "You should...", "Don't...", "The way to..."
   - Specific recommendations
   - Warnings or best practices

5. **Questions being answered**:
   - "People ask me...", "The answer is..."
   - Problems being solved
   - Clarifications being made

RETURN JSON:
{{
  "seeds": [
    {{
      "timestamp_approx": 45.5,
      "text": "The exact sentence or phrase that is the seed",
      "rhetorical_type": "argument",
      "interest_score": 0.85,
      "reasoning": "Why this is a good seed",
      "likely_has_premise": true,
      "likely_has_resolution": true
    }}
  ]
}}

RHETORICAL TYPES:
- "argument" - Claims, opinions, theses
- "teaching" - Explanations, how-tos, concepts
- "story" - Narratives, anecdotes, examples
- "advice" - Practical recommendations, warnings
- "qa" - Questions being answered
- "comparison" - Contrasts, alternatives, choices
- "insight" - Observations, realizations, wisdom

RULES:
- Return exactly {target_count} seeds (or fewer if there aren't enough good ones)
- Seeds must be SPECIFIC sentences/phrases from the transcript, not summaries
- Interest score 0.0-1.0 (be honest, not all moments are great)
- Only include seeds that likely have BOTH premise AND resolution
- Prefer diverse types (not all arguments or all stories)
- timestamp_approx should be relative to the start of this segment (0.0 - 120.0)
"""

    def _deduplicate_seeds(self, seeds: List[Dict]) -> List[Dict]:
        """
        Remove duplicate seeds from overlapping windows.

        Seeds are duplicates if:
        - Similar timestamp (within DEDUP_TIME_THRESHOLD seconds)
        - Similar text (>DEDUP_TEXT_THRESHOLD similarity)

        Args:
            seeds: List of seed dicts

        Returns:
            Deduplicated list of seeds
        """
        if len(seeds) <= 1:
            return seeds

        # Sort by timestamp
        sorted_seeds = sorted(seeds, key=lambda s: s.get('timestamp', 0))

        unique = []
        for seed in sorted_seeds:
            is_duplicate = False

            for existing in unique:
                # Check time proximity
                time_diff = abs(
                    seed.get('timestamp', 0) - existing.get('timestamp', 0)
                )

                if time_diff < self.DEDUP_TIME_THRESHOLD:
                    # Check text similarity
                    similarity = self._text_similarity(
                        seed.get('text', ''),
                        existing.get('text', '')
                    )

                    if similarity > self.DEDUP_TEXT_THRESHOLD:
                        is_duplicate = True
                        # Keep the one with higher interest score
                        if seed.get('interest_score', 0) > existing.get('interest_score', 0):
                            unique.remove(existing)
                            unique.append(seed)
                        break

            if not is_duplicate:
                unique.append(seed)

        return unique

    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate simple Jaccard similarity between two texts.

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score (0.0-1.0)
        """
        if not text1 or not text2:
            return 0.0

        # Convert to lowercase and split into words
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        # Calculate Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2

        return len(intersection) / len(union) if union else 0.0
