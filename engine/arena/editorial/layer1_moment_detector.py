"""
Layer 1: Moment Detector

Identifies interesting moments in transcripts without worrying about completeness.
Casts a wide net to find hooks, insights, controversial statements, advice, etc.

Includes chunking support for large transcripts (>21k tokens) based on the
rate limit fix we implemented for the single-layer analyzer.
"""

from typing import List, Dict
import json
import time
from .utils import format_transcript_with_timestamps


class MomentDetector:
    """
    Layer 1: Identifies interesting moments without worrying about completeness.

    Strategy:
        - Cast wide net: Find hooks, insights, controversial statements, advice, emotional peaks
        - Return rough timestamps (not exact boundaries)
        - Focus on "idea density", not polish
        - Over-identify rather than miss content

    Handles large transcripts via chunking:
        - Detects when transcript exceeds token limits
        - Splits into manageable chunks with overlap
        - Processes sequentially with rate limit delays
        - Merges and deduplicates results
    """

    # Chunking constants (from rate limit fix)
    MAX_TOKENS_PER_REQUEST = 24000      # 20% safety margin below 30k limit
    PROMPT_OVERHEAD_TOKENS = 3000       # System message + instructions
    MAX_TRANSCRIPT_TOKENS = 21000       # Max for transcript content
    DEFAULT_OVERLAP_RATIO = 0.10        # 10% segment overlap
    DEDUP_THRESHOLD = 0.5               # 50% time overlap = duplicate moment

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize moment detector

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
            'moments_found': 0,
            'chunks_processed': 0
        }

    def detect(
        self,
        transcript_data: Dict,
        target_moments: int = 25
    ) -> List[Dict]:
        """
        Detect interesting moments in transcript.

        Automatically handles chunking for large transcripts.

        Args:
            transcript_data: Transcript dict with 'segments', 'text', 'duration'
            target_moments: Number of candidate moments to find (default: 25)

        Returns:
            List of moment dicts sorted by interest_score:
            {
                'rough_start': float,      # Approximate start time
                'rough_end': float,        # Approximate end time
                'core_idea': str,          # One-sentence summary
                'why_interesting': str,    # Why this moment matters
                'interest_score': float,   # 0.0-1.0
                'content_type': str        # "hook", "insight", "advice", "story"
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

        # Format transcript with timestamps
        formatted_transcript = format_transcript_with_timestamps(segments)

        # Check if chunking is needed
        total_tokens = self._estimate_tokens(formatted_transcript)

        if total_tokens <= self.MAX_TRANSCRIPT_TOKENS:
            # No chunking needed
            print(f"      Transcript size: {total_tokens:,} tokens (no chunking needed)")
            moments = self._detect_single_chunk(
                client,
                formatted_transcript,
                target_moments
            )
            self.metrics['chunks_processed'] = 1
        else:
            # Chunking needed
            print(f"      ⚠️  Large transcript: {total_tokens:,} tokens")
            print(f"      Splitting into chunks (max {self.MAX_TRANSCRIPT_TOKENS:,} tokens each)")

            chunks = self._chunk_segments(segments, self.MAX_TRANSCRIPT_TOKENS)
            print(f"      Created {len(chunks)} chunks")

            chunk_results = []
            for i, chunk_segments in enumerate(chunks, 1):
                print(f"      Processing chunk {i}/{len(chunks)}...")

                chunk_transcript = format_transcript_with_timestamps(chunk_segments)
                chunk_tokens = self._estimate_tokens(chunk_transcript)
                print(f"      Chunk {i}: {len(chunk_segments)} segments, {chunk_tokens:,} tokens")

                # Detect moments in this chunk
                chunk_target = target_moments if len(chunks) == 1 else int(target_moments * 1.5)

                try:
                    chunk_moments = self._detect_single_chunk(
                        client,
                        chunk_transcript,
                        chunk_target
                    )
                    chunk_results.append(chunk_moments)
                    print(f"      ✓ Found {len(chunk_moments)} moments in chunk {i}")
                except Exception as e:
                    print(f"      ⚠️  Chunk {i} failed: {e}")
                    chunk_results.append([])

                # Rate limit: Wait between chunks
                if i < len(chunks):
                    print(f"      ⏳ Waiting 60s for rate limit...")
                    time.sleep(60)

            self.metrics['chunks_processed'] = len(chunks)

            # Merge results from all chunks
            print(f"      Merging {len(chunk_results)} chunks...")
            moments = self._merge_chunk_results(chunk_results)
            print(f"      ✓ After deduplication: {len(moments)} unique moments")

            # Take top N by interest_score
            moments = sorted(moments, key=lambda m: m['interest_score'], reverse=True)[:target_moments]

        self.metrics['moments_found'] = len(moments)
        return moments

    def _detect_single_chunk(
        self,
        client,
        formatted_transcript: str,
        target_moments: int
    ) -> List[Dict]:
        """
        Detect moments in a single transcript chunk with retry logic for rate limits

        Args:
            client: OpenAI client
            formatted_transcript: Formatted transcript with timestamps
            target_moments: Number of moments to find

        Returns:
            List of moment dicts
        """
        # Create prompt
        prompt = self._create_prompt(formatted_transcript, target_moments)

        # Retry configuration
        max_retries = 5
        base_delay = 2.0  # Start with 2 second delay

        for attempt in range(max_retries):
            try:
                # Call GPT-4o
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a senior content analyst identifying interesting moments in video content."
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

                # Calculate cost (GPT-4o pricing: $2.50/1M input, $10/1M output tokens)
                input_cost = (response.usage.prompt_tokens / 1_000_000) * 2.50
                output_cost = (response.usage.completion_tokens / 1_000_000) * 10.00
                self.metrics['cost_usd'] += input_cost + output_cost

                # Parse response
                try:
                    result = json.loads(response.choices[0].message.content)
                    moments = self._parse_moments(result)
                    return moments
                except (json.JSONDecodeError, KeyError) as e:
                    print(f"      ⚠️  Failed to parse GPT response: {e}")
                    return []

            except Exception as e:
                error_str = str(e)

                # Check if this is a rate limit error (429)
                if "rate_limit_exceeded" in error_str or "429" in error_str:
                    # Try to extract wait time from error message
                    wait_time = base_delay * (2 ** attempt)  # Exponential backoff

                    # Try to parse suggested wait time from error
                    import re
                    match = re.search(r'try again in (\d+\.?\d*)s', error_str)
                    if match:
                        wait_time = float(match.group(1)) + 1.0  # Add 1 second buffer

                    if attempt < max_retries - 1:
                        print(f"      ⚠️  Rate limit hit. Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}...")
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"      ❌ Rate limit exceeded after {max_retries} retries")
                        raise
                else:
                    # Non-rate-limit error, raise immediately
                    raise

        # Should not reach here, but return empty list as fallback
        return []

    def _create_prompt(self, transcript: str, target_moments: int) -> str:
        """
        Create Layer 1 prompt for moment detection

        Based on EDITORIAL_ARCHITECTURE.md lines 214-261

        Args:
            transcript: Formatted transcript with timestamps
            target_moments: Number of moments to identify

        Returns:
            Prompt string
        """
        return f"""ROLE: Senior content analyst.

TASK:
Identify the {target_moments} most interesting and valuable moments in this transcript
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
8. Surprising facts or statistics
9. Relatable struggles or experiences

DO NOT:
- Try to perfectly align sentence boundaries
- Optimize for standalone completeness (that's Layer 3's job)
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
- Return exactly {target_moments} candidates
- Rank by interest_score (highest first)
- Timestamps may be imprecise (we refine in Layer 2)
- Focus on *idea density*, not polish
- Content types: "hook", "insight", "advice", "story", "controversial", "emotional", "problem-solution"
- Interest scores should range 0.5-1.0 (we're only looking at good content)"""

    def _parse_moments(self, result: Dict) -> List[Dict]:
        """
        Parse API response into moment dicts

        Args:
            result: Parsed JSON response from GPT

        Returns:
            List of moment dicts
        """
        moments = []
        for idx, candidate in enumerate(result.get('candidates', [])):
            try:
                moment = {
                    'rough_start': float(candidate['rough_start']),
                    'rough_end': float(candidate['rough_end']),
                    'core_idea': candidate['core_idea'],
                    'why_interesting': candidate['why_interesting'],
                    'interest_score': float(candidate['interest_score']),
                    'content_type': candidate.get('content_type', 'general')
                }
                moments.append(moment)
            except (KeyError, ValueError, TypeError) as e:
                print(f"      ⚠️  Skipping invalid moment {idx}: {e}")
                continue

        return sorted(moments, key=lambda m: m['interest_score'], reverse=True)

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text using tiktoken

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except ImportError:
            # Fallback: rough estimation (1 token ~= 4 characters)
            return len(text) // 4
        except Exception:
            # Fallback for unknown models
            return len(text) // 4

    def _chunk_segments(
        self,
        segments: List[Dict],
        max_tokens: int
    ) -> List[List[Dict]]:
        """
        Split segments into chunks based on token count with overlap

        Based on chunking logic from analyzer.py rate limit fix.

        Args:
            segments: List of transcript segments
            max_tokens: Maximum tokens per chunk

        Returns:
            List of segment chunks
        """
        chunks = []
        current_chunk = []
        current_tokens = 0

        for segment in segments:
            # Format segment to estimate tokens
            from .utils import format_timestamp
            formatted = f"[{format_timestamp(segment['start'])}] {segment['text']}\n"
            segment_tokens = self._estimate_tokens(formatted)

            # Check if adding this segment would exceed limit
            if current_tokens + segment_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append(current_chunk)

                # Calculate overlap: last 10% of segments
                overlap_size = int(len(current_chunk) * self.DEFAULT_OVERLAP_RATIO)
                overlap_segments = current_chunk[-overlap_size:] if overlap_size > 0 else []

                # Start new chunk with overlap
                current_chunk = overlap_segments.copy()
                current_tokens = sum(
                    self._estimate_tokens(
                        f"[{format_timestamp(s['start'])}] {s['text']}\n"
                    )
                    for s in current_chunk
                )

            # Add segment to current chunk
            current_chunk.append(segment)
            current_tokens += segment_tokens

        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _merge_chunk_results(
        self,
        chunk_results: List[List[Dict]]
    ) -> List[Dict]:
        """
        Merge moments from multiple chunks, removing duplicates

        Args:
            chunk_results: List of moment lists from each chunk

        Returns:
            Merged and deduplicated list of moments
        """
        all_moments = []
        for chunk_idx, moments in enumerate(chunk_results):
            for moment in moments:
                moment['source_chunk'] = chunk_idx
                all_moments.append(moment)

        # Sort by start time
        all_moments.sort(key=lambda m: m['rough_start'])

        # Deduplicate based on temporal overlap
        deduped = []
        skip_indices = set()

        for i, moment1 in enumerate(all_moments):
            if i in skip_indices:
                continue

            # Check for overlaps with later moments
            for j in range(i + 1, len(all_moments)):
                if j in skip_indices:
                    continue

                moment2 = all_moments[j]

                # If moment2 starts after moment1 ends, no more overlaps possible
                if moment2['rough_start'] > moment1['rough_end']:
                    break

                # Calculate overlap
                overlap = self._calculate_overlap(moment1, moment2)

                if overlap > self.DEDUP_THRESHOLD:
                    # Keep the one with higher score
                    if moment2['interest_score'] > moment1['interest_score']:
                        skip_indices.add(i)
                        break  # moment1 is duplicate, move to next
                    else:
                        skip_indices.add(j)  # moment2 is duplicate

            if i not in skip_indices:
                # Remove source_chunk metadata before returning
                moment_copy = {k: v for k, v in moment1.items() if k != 'source_chunk'}
                deduped.append(moment_copy)

        return deduped

    def _calculate_overlap(self, moment1: Dict, moment2: Dict) -> float:
        """
        Calculate temporal overlap ratio between two moments

        Args:
            moment1: First moment with rough_start and rough_end
            moment2: Second moment with rough_start and rough_end

        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        start = max(moment1['rough_start'], moment2['rough_start'])
        end = min(moment1['rough_end'], moment2['rough_end'])

        if start >= end:
            return 0.0

        overlap_duration = end - start
        moment1_duration = moment1['rough_end'] - moment1['rough_start']
        moment2_duration = moment2['rough_end'] - moment2['rough_start']

        # Use smaller moment duration as denominator
        min_duration = min(moment1_duration, moment2_duration)

        return overlap_duration / min_duration if min_duration > 0 else 0.0
