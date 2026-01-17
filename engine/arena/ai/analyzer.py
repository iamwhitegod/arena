"""AI-powered transcript analysis using OpenAI GPT"""
import os
import json
from typing import List, Dict, Optional


class TranscriptAnalyzer:
    """Uses AI to identify interesting segments in transcripts"""

    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        """
        Initialize analyzer

        Args:
            api_key: OpenAI API key
            model: Model to use (gpt-4o, gpt-4-turbo, etc.)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model

        # Chunking constants for handling large transcripts
        self.MAX_TOKENS_PER_REQUEST = 24000      # 20% safety margin below 30k limit
        self.PROMPT_OVERHEAD_TOKENS = 3000       # System message + instructions
        self.MAX_TRANSCRIPT_TOKENS = 21000       # Max for transcript content
        self.DEFAULT_OVERLAP_RATIO = 0.10        # 10% segment overlap
        self.DEDUP_THRESHOLD = 0.7              # 70% overlap = duplicate

        if not self.api_key:
            raise ValueError("OpenAI API key is required")

    def _analyze_single_chunk(
        self,
        formatted_transcript: str,
        target_clips: int,
        min_duration: Optional[int],
        max_duration: Optional[int]
    ) -> List[Dict]:
        """
        Analyze a single transcript chunk with OpenAI

        Args:
            formatted_transcript: Formatted transcript with timestamps
            target_clips: Number of clips to identify
            min_duration: Optional minimum clip duration in seconds
            max_duration: Optional maximum clip duration in seconds

        Returns:
            List of candidate clips
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        client = OpenAI(api_key=self.api_key)

        # Create the analysis prompt
        prompt = self._create_analysis_prompt(
            formatted_transcript,
            target_clips,
            min_duration,
            max_duration
        )

        # Call GPT-4 for analysis
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert video editor and content strategist "
                            "who specializes in identifying engaging moments in "
                            "long-form content for short-form social media."
                        )
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                response_format={"type": "json_object"},
                temperature=0.7
            )

            # Parse the response
            result = json.loads(response.choices[0].message.content)
            clips = result.get("clips", [])

            # Validate and normalize the clips
            validated_clips = self._validate_clips(
                clips, min_duration, max_duration
            )

            return validated_clips

        except Exception as e:
            raise RuntimeError(f"Failed to analyze transcript chunk with AI: {str(e)}")

    def analyze_transcript(
        self,
        transcript_data: Dict,
        target_clips: int = 10,
        min_duration: Optional[int] = None,
        max_duration: Optional[int] = None
    ) -> List[Dict]:
        """
        Analyze transcript to identify interesting segments
        Automatically chunks large transcripts to handle OpenAI rate limits

        Args:
            transcript_data: Transcript dict with 'text' and 'segments'
            target_clips: Number of clips to identify
            min_duration: Optional minimum clip duration in seconds (None = no constraint)
            max_duration: Optional maximum clip duration in seconds (None = no constraint)

        Returns:
            List of candidate segments with timestamps, titles, and reasons
        """
        import time

        segments = transcript_data.get("segments", [])

        # Format transcript with timestamps for better context
        formatted_transcript = self._format_transcript_with_timestamps(segments)

        # Check if chunking is needed
        total_tokens = self._estimate_tokens(formatted_transcript)

        if total_tokens <= self.MAX_TRANSCRIPT_TOKENS:
            # No chunking needed - use existing method
            return self._analyze_single_chunk(
                formatted_transcript,
                target_clips,
                min_duration,
                max_duration
            )

        # Chunking needed
        print(f"⚠️  Transcript is large ({total_tokens:,} tokens)")
        print(f"   Splitting into chunks (max {self.MAX_TRANSCRIPT_TOKENS:,} tokens each)...\n")

        chunks = self._chunk_segments(
            segments,
            self.MAX_TRANSCRIPT_TOKENS,
            overlap_ratio=self.DEFAULT_OVERLAP_RATIO
        )

        print(f"   Created {len(chunks)} chunks\n")

        chunk_results = []

        for i, chunk_segments in enumerate(chunks, 1):
            print(f"   Analyzing chunk {i}/{len(chunks)}...")

            # Format this chunk
            chunk_transcript = self._format_transcript_with_timestamps(chunk_segments)
            chunk_tokens = self._estimate_tokens(chunk_transcript)
            print(f"   Chunk {i}: {len(chunk_segments)} segments, {chunk_tokens:,} tokens")

            # Analyze this chunk
            # Ask for more clips per chunk to account for deduplication
            chunk_target = target_clips if len(chunks) == 1 else target_clips * 2

            try:
                chunk_clips = self._analyze_single_chunk(
                    chunk_transcript,
                    chunk_target,
                    min_duration,
                    max_duration
                )
                chunk_results.append(chunk_clips)
                print(f"   ✓ Found {len(chunk_clips)} clips in chunk {i}\n")

            except Exception as e:
                print(f"   ⚠️  Chunk {i} failed: {e}")
                # Continue with other chunks
                chunk_results.append([])

            # Rate limit: Wait 60 seconds between chunks
            if i < len(chunks):
                print(f"   ⏳ Waiting 60s for rate limit...")
                time.sleep(60)
                print()

        # Merge results
        print(f"   Merging {len(chunk_results)} chunks...")
        merged_clips = self._merge_chunk_results(
            chunk_results,
            dedup_threshold=self.DEDUP_THRESHOLD
        )
        print(f"   ✓ After deduplication: {len(merged_clips)} unique clips\n")

        # Take top N by interest_score
        final_clips = merged_clips[:target_clips]

        return final_clips

    def _format_transcript_with_timestamps(self, segments: List[Dict]) -> str:
        """Format transcript segments with timestamps"""
        lines = []
        for segment in segments:
            start = segment.get("start", 0)
            end = segment.get("end", 0)
            text = segment.get("text", "").strip()
            timestamp = self._format_timestamp(start)
            lines.append(f"[{timestamp}] {text}")

        return "\n".join(lines)

    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to MM:SS format"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _create_analysis_prompt(
        self,
        transcript: str,
        target_clips: int,
        min_duration: Optional[int],
        max_duration: Optional[int]
    ) -> str:
        """Create the analysis prompt for GPT"""

        # Build duration guidance
        if min_duration is not None and max_duration is not None:
            duration_guidance = f"Each clip should be between {min_duration}-{max_duration} seconds long."
            duration_constraint = f"- Ensure clips are between {min_duration}-{max_duration} seconds"
        elif min_duration is not None:
            duration_guidance = f"Each clip should be at least {min_duration} seconds long."
            duration_constraint = f"- Ensure clips are at least {min_duration} seconds"
        elif max_duration is not None:
            duration_guidance = f"Each clip should be no longer than {max_duration} seconds."
            duration_constraint = f"- Ensure clips are no longer than {max_duration} seconds"
        else:
            duration_guidance = "Identify complete thoughts, stories, or insights. Each clip MUST contain a full arc: setup/context → core statement → resolution/conclusion. A complete standalone idea typically requires at least 15-20 seconds to establish context and deliver value. Let the natural boundaries of the content determine the exact length, but ensure every clip has complete context."
            duration_constraint = "- Each clip must be a complete, self-contained idea with full context\n- Include setup, development, and conclusion\n- Do NOT cut mid-thought or mid-explanation\n- Clips should be substantial enough that a viewer can understand and appreciate the idea without prior context"

        return f"""Analyze this video transcript and identify the {target_clips} most interesting segments that would make engaging short clips for social media.

{duration_guidance}

Each clip should:
- Have a clear hook or attention-grabbing opening
- Contain a complete thought or story arc
- Be engaging and valuable on its own
- Appeal to developers, founders, or technical content creators
- Start and end at natural sentence boundaries (complete sentences)

Look for:
1. Hooks and attention-grabbing statements
2. Key insights or "aha" moments
3. Controversial or thought-provoking statements
4. Actionable advice or tips
5. Emotional or passionate moments
6. Clear problem-solution narratives
7. Surprising facts or statistics
8. Relatable struggles or experiences

Transcript with timestamps:
{transcript}

Return ONLY a JSON object in this exact format:
{{
  "clips": [
    {{
      "start_time": 125.5,
      "end_time": 168.3,
      "title": "Why most startups fail at product-market fit",
      "reason": "Strong hook with controversial insight, complete narrative arc",
      "interest_score": 0.95,
      "content_type": "insight"
    }}
  ]
}}

Important:
{duration_constraint}
- Use actual timestamp values from the transcript
- Make titles compelling and specific (not generic)
- Interest score should be 0.0 to 1.0
- Content types: "hook", "insight", "advice", "story", "controversial", "emotional"
- Return exactly {target_clips} clips, ranked by interest_score (highest first)
- Prioritize complete thoughts over arbitrary time constraints
"""

    def _validate_clips(
        self,
        clips: List[Dict],
        min_duration: Optional[int],
        max_duration: Optional[int]
    ) -> List[Dict]:
        """Validate and normalize clip data"""
        validated = []

        for i, clip in enumerate(clips):
            # Ensure required fields exist
            if not all(k in clip for k in ["start_time", "end_time", "title"]):
                continue

            # Calculate duration
            duration = clip["end_time"] - clip["start_time"]

            # Sanity filter: Remove physically impossible clips
            # This is NOT a user constraint - it's quality control
            # A clip under 8 seconds cannot contain:
            # - Setup/context for the idea
            # - The core statement/insight
            # - Resolution/conclusion
            # This filters AI mistakes, not enforces user preferences
            if duration < 8.0:
                continue

            # Validate user-specified duration constraints (if provided)
            if min_duration is not None and duration < min_duration:
                continue
            if max_duration is not None and duration > max_duration:
                continue

            # Normalize the clip
            validated_clip = {
                "id": f"clip_{i+1:03d}",
                "start_time": float(clip["start_time"]),
                "end_time": float(clip["end_time"]),
                "duration": duration,
                "title": clip["title"],
                "reason": clip.get("reason", "Interesting segment"),
                "interest_score": float(clip.get("interest_score", 0.5)),
                "content_type": clip.get("content_type", "general")
            }

            validated.append(validated_clip)

        return validated

    def _chunk_segments(
        self,
        segments: List[Dict],
        max_tokens: int,
        overlap_ratio: float = 0.10
    ) -> List[List[Dict]]:
        """
        Split segments into chunks based on token count with overlap

        Args:
            segments: List of transcript segments
            max_tokens: Maximum tokens per chunk
            overlap_ratio: Ratio of overlap between chunks (0.0 to 1.0)

        Returns:
            List of segment chunks
        """
        chunks = []
        current_chunk = []
        current_tokens = 0
        overlap_segments = []

        for i, segment in enumerate(segments):
            # Format segment with timestamp
            formatted = f"[{self._format_timestamp(segment['start'])}] {segment['text']}\n"
            segment_tokens = self._estimate_tokens(formatted)

            # Check if adding this segment would exceed limit
            if current_tokens + segment_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append(current_chunk)

                # Calculate overlap: last N% of segments
                overlap_size = int(len(current_chunk) * overlap_ratio)
                overlap_segments = current_chunk[-overlap_size:] if overlap_size > 0 else []

                # Start new chunk with overlap
                current_chunk = overlap_segments.copy()
                current_tokens = sum(
                    self._estimate_tokens(
                        f"[{self._format_timestamp(s['start'])}] {s['text']}\n"
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
        chunk_results: List[List[Dict]],
        dedup_threshold: float = 0.7
    ) -> List[Dict]:
        """
        Merge clips from multiple chunks, removing duplicates

        Args:
            chunk_results: List of clip lists from each chunk
            dedup_threshold: Overlap threshold for considering clips as duplicates

        Returns:
            Merged and deduplicated list of clips
        """
        all_clips = []
        for chunk_idx, clips in enumerate(chunk_results):
            for clip in clips:
                clip['source_chunk'] = chunk_idx
                all_clips.append(clip)

        # Sort by start time
        all_clips.sort(key=lambda x: x['start_time'])

        # Deduplicate
        deduped = []
        skip_indices = set()

        for i, clip1 in enumerate(all_clips):
            if i in skip_indices:
                continue

            # Check for overlaps with later clips
            for j in range(i + 1, len(all_clips)):
                if j in skip_indices:
                    continue

                clip2 = all_clips[j]

                # If clip2 starts after clip1 ends, no more overlaps possible
                if clip2['start_time'] > clip1['end_time']:
                    break

                # Calculate overlap
                overlap = self._calculate_overlap(clip1, clip2)

                if overlap > dedup_threshold:
                    # Keep the one with higher score
                    if clip2['interest_score'] > clip1['interest_score']:
                        skip_indices.add(i)
                        break  # clip1 is duplicate, move to next
                    else:
                        skip_indices.add(j)  # clip2 is duplicate

            if i not in skip_indices:
                deduped.append(clip1)

        # Re-sort by interest_score
        deduped.sort(key=lambda x: x['interest_score'], reverse=True)

        # Re-assign IDs
        for i, clip in enumerate(deduped):
            clip['id'] = f"clip_{i+1:03d}"

        return deduped

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

    def _calculate_overlap(self, clip1: Dict, clip2: Dict) -> float:
        """
        Calculate temporal overlap ratio between two clips

        Args:
            clip1: First clip with start_time and end_time
            clip2: Second clip with start_time and end_time

        Returns:
            Overlap ratio (0.0 to 1.0)
        """
        start = max(clip1['start_time'], clip2['start_time'])
        end = min(clip1['end_time'], clip2['end_time'])

        if start >= end:
            return 0.0

        overlap_duration = end - start
        clip1_duration = clip1['end_time'] - clip1['start_time']
        clip2_duration = clip2['end_time'] - clip2['start_time']

        # Use smaller clip duration as denominator
        min_duration = min(clip1_duration, clip2_duration)

        return overlap_duration / min_duration if min_duration > 0 else 0.0

    def generate_clip_title(self, transcript_segment: str) -> str:
        """Generate an engaging title for a clip"""
        try:
            from openai import OpenAI
        except ImportError:
            return "Untitled Clip"

        client = OpenAI(api_key=self.api_key)

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Use smaller model for cost efficiency
                messages=[
                    {
                        "role": "user",
                        "content": f"Create a compelling, specific title (max 60 chars) for this video clip:\n\n{transcript_segment}"
                    }
                ],
                temperature=0.8,
                max_tokens=50
            )

            return response.choices[0].message.content.strip().strip('"')
        except:
            return "Untitled Clip"

    def suggest_hashtags(self, transcript_segment: str, max_tags: int = 5) -> List[str]:
        """Suggest relevant hashtags for a clip"""
        try:
            from openai import OpenAI
        except ImportError:
            return []

        client = OpenAI(api_key=self.api_key)

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": f"Suggest {max_tags} relevant hashtags for this video clip (return only hashtag words without #):\n\n{transcript_segment}"
                    }
                ],
                temperature=0.7,
                max_tokens=50
            )

            # Parse hashtags from response
            tags = response.choices[0].message.content.strip().split()
            return [tag.strip().lstrip('#') for tag in tags[:max_tags]]
        except:
            return []

    def extract_transcript_text(
        self,
        transcript_segments: List[Dict],
        start_time: float,
        end_time: float
    ) -> str:
        """
        Extract transcript text for a specific time range

        Args:
            transcript_segments: List of transcript segments with 'start', 'end', 'text'
            start_time: Start time in seconds
            end_time: End time in seconds

        Returns:
            Concatenated transcript text for the time range
        """
        text_parts = []

        for segment in transcript_segments:
            seg_start = segment.get('start', 0)
            seg_end = segment.get('end', 0)

            # Check if segment overlaps with our time range
            if seg_start < end_time and seg_end > start_time:
                text_parts.append(segment.get('text', '').strip())

        return ' '.join(text_parts)
