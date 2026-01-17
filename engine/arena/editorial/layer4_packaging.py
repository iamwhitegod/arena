"""
Layer 4: Packaging Layer

Final polish: Generate titles, descriptions, hashtags, and metadata for validated clips.

This layer takes clips that have passed standalone validation and adds
all the marketing/presentation elements needed for publishing.
"""

from typing import List, Dict
import json
from .utils import extract_clip_text, format_timestamp


class PackagingLayer:
    """
    Layer 4: Package validated clips with titles, descriptions, and metadata.

    Strategy:
        - Generate everything in one API call per clip (efficient)
        - Title: Max 60 chars, specific not generic, compelling
        - Description: 2-3 sentences with hook + context + value
        - Hashtags: 5 relevant tags for target audience
        - Thumbnail: Best frame timestamp within clip

    Uses GPT-4o-mini for cost efficiency (simple generation task).
    """

    MAX_TITLE_LENGTH = 60  # Platform constraint for short-form video

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        """
        Initialize packaging layer

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
            'clips_packaged': 0
        }

    def package_all(
        self,
        validated_clips: List[Dict],
        transcript_data: Dict
    ) -> List[Dict]:
        """
        Package all validated clips with titles, descriptions, and metadata.

        Args:
            validated_clips: List of clips from Layer 3 (PASS or REVISE verdict)
            transcript_data: Full transcript data with segments

        Returns:
            List of packaged clip dicts:
            {
                'clip_id': str,
                'start_time': float,
                'end_time': float,
                'duration': float,
                'title': str,
                'description': str,
                'hashtags': List[str],
                'thumbnail_time': float,
                'thumbnail_reasoning': str,
                'interest_score': float,
                'standalone_score': float,
                'content_type': str,
                '_layer1': Dict,
                '_layer2': Dict,
                '_layer3': Dict
            }
        """
        if not validated_clips:
            print("      ⚠️  No validated clips to package")
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

        packaged_clips = []

        print(f"      Packaging {len(validated_clips)} validated clips...")

        for idx, clip in enumerate(validated_clips, 1):
            try:
                packaged = self._package_single(client, clip, idx, segments)

                if packaged:
                    packaged_clips.append(packaged)
                    print(f"      ✓ Clip {idx}/{len(validated_clips)}: \"{packaged['title'][:50]}...\"")

            except Exception as e:
                print(f"      ⚠️  Clip {idx} packaging failed: {e}")
                continue

        self.metrics['clips_packaged'] = len(packaged_clips)

        return packaged_clips

    def _package_single(
        self,
        client,
        clip: Dict,
        clip_id: int,
        segments: List[Dict]
    ) -> Dict:
        """
        Package a single clip with all metadata

        Args:
            client: OpenAI client
            clip: Validated clip from Layer 3
            clip_id: Numeric ID for this clip
            segments: Transcript segments

        Returns:
            Packaged clip dict with all metadata
        """
        # Extract clip text
        start_time = clip['refined_start']
        end_time = clip['refined_end']
        clip_text = extract_clip_text(segments, start_time, end_time)

        if not clip_text:
            print(f"      ⚠️  No text found for clip {clip_id}")
            return None

        # Generate packaging metadata
        packaging = self._generate_packaging(client, clip_text, start_time, end_time, clip)

        if not packaging:
            return None

        # Assemble final clip dict
        packaged_clip = {
            # Core identifiers
            'clip_id': f"clip_{clip_id:03d}",
            'start_time': start_time,
            'end_time': end_time,
            'duration': end_time - start_time,

            # Packaging metadata
            'title': packaging['title'],
            'description': packaging['description'],
            'hashtags': packaging['hashtags'],
            'thumbnail_time': packaging['thumbnail_time'],
            'thumbnail_reasoning': packaging.get('thumbnail_reasoning', ''),

            # Quality scores
            'interest_score': clip['complete_thought']['original_moment']['interest_score'],
            'standalone_score': clip['standalone_score'],
            'content_type': clip['complete_thought']['original_moment']['content_type'],

            # Preserve layer outputs for debugging
            '_layer1': clip['complete_thought']['original_moment'],
            '_layer2': {
                'expanded_start': clip['complete_thought']['expanded_start'],
                'expanded_end': clip['complete_thought']['expanded_end'],
                'thought_summary': clip['complete_thought']['thought_summary'],
                'confidence': clip['complete_thought']['confidence']
            },
            '_layer3': {
                'refined_start': clip['refined_start'],
                'refined_end': clip['refined_end'],
                'standalone_score': clip['standalone_score'],
                'verdict': clip['verdict'],
                'editor_notes': clip['editor_notes']
            }
        }

        return packaged_clip

    def _generate_packaging(
        self,
        client,
        clip_text: str,
        start_time: float,
        end_time: float,
        clip: Dict
    ) -> Dict:
        """
        Generate title, description, hashtags, and thumbnail time

        Args:
            client: OpenAI client
            clip_text: Extracted transcript text
            start_time: Clip start time
            end_time: Clip end time
            clip: Validated clip from Layer 3

        Returns:
            Dict with packaging metadata or None if failed
        """
        prompt = self._create_prompt(clip_text, start_time, end_time, clip)

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
                            "content": "You are a social media expert creating compelling titles and descriptions for short-form video content."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,  # Moderate creativity for titles
                    response_format={"type": "json_object"}
                )

                # Track metrics
                self.metrics['api_calls'] += 1
                self.metrics['tokens_used'] += response.usage.total_tokens

                # Calculate cost (GPT-4o-mini pricing)
                input_cost = (response.usage.prompt_tokens / 1_000_000) * 0.15
                output_cost = (response.usage.completion_tokens / 1_000_000) * 0.60
                self.metrics['cost_usd'] += input_cost + output_cost

                # Parse response
                result = json.loads(response.choices[0].message.content)

                # Validate and truncate title if needed
                title = result['title']
                if len(title) > self.MAX_TITLE_LENGTH:
                    title = title[:self.MAX_TITLE_LENGTH-3] + "..."

                # Ensure thumbnail is within clip bounds
                thumbnail_time = float(result['thumbnail_time'])
                thumbnail_time = max(start_time, min(end_time, thumbnail_time))

                packaging = {
                    'title': title,
                    'description': result['description'],
                    'hashtags': result['hashtags'][:5],  # Limit to 5 hashtags
                    'thumbnail_time': thumbnail_time,
                    'thumbnail_reasoning': result.get('thumbnail_reasoning', '')
                }

                return packaging

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"      ⚠️  Failed to parse packaging response: {e}")
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
                        print(f"      ⚠️  API error during packaging: {e}")
                        print(f"      ⏳ Retrying in {wait_time:.1f}s (attempt {attempt + 2}/{max_retries})...")
                        import time
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"      ❌ Packaging failed after {max_retries} retries")
                        return None
                else:
                    # Non-rate-limit error
                    print(f"      ⚠️  API error during packaging: {e}")
                    return None

        return None

    def _create_prompt(
        self,
        clip_text: str,
        start_time: float,
        end_time: float,
        clip: Dict
    ) -> str:
        """
        Create Layer 4 packaging prompt

        Based on EDITORIAL_ARCHITECTURE.md lines 879-896

        Args:
            clip_text: Extracted transcript text
            start_time: Clip start time
            end_time: Clip end time
            clip: Validated clip from Layer 3

        Returns:
            Prompt string
        """
        duration = end_time - start_time
        start_ts = format_timestamp(start_time)
        end_ts = format_timestamp(end_time)

        content_type = clip['complete_thought']['original_moment']['content_type']
        core_idea = clip['complete_thought']['original_moment']['core_idea']

        return f"""ROLE: Social media expert creating content for short-form video platforms.

CONTEXT:
You're packaging a {duration:.1f}s clip for YouTube Shorts, TikTok, Instagram Reels.

Clip info:
- Type: {content_type}
- Core idea: {core_idea}
- Timestamps: [{start_ts}] to [{end_ts}]
- Standalone score: {clip['standalone_score']:.2f}/1.0

CLIP TRANSCRIPT:
{clip_text}

TASK:
Generate compelling packaging for this clip to maximize engagement.

TITLE GUIDELINES:
- Max 60 characters (strict limit)
- Be SPECIFIC, not generic
  ❌ "Important Life Lesson"
  ✅ "Why I Stopped Using Cloud Services"
- Use strong hooks when appropriate
  ✅ "The Problem Nobody Talks About"
  ✅ "How I Saved $10K on Development"
- Match the content type:
  * insight/advice → Direct statement or "How to..."
  * controversial → Question or provocative statement
  * story → Focus on outcome or surprise
  * hook → Lead with the surprise/contradiction

DESCRIPTION GUIDELINES:
- 2-3 sentences total
- Sentence 1: Hook or question to grab attention
- Sentence 2: Context or main point
- Sentence 3 (optional): Value or takeaway
- Natural, conversational tone
- Don't oversell or use excessive emojis

HASHTAG GUIDELINES:
- Exactly 5 hashtags
- Mix of:
  * Broad reach: #tech #business #entrepreneur
  * Niche specific: #softwareengineering #cloudcomputing
  * Content type: #lifelessons #techadvice #startup
- Avoid generic/useless tags: #content #video #viral #fyp

THUMBNAIL GUIDELINES:
- Choose best visual moment within clip
- Look for:
  * Speaker making strong point (hand gestures, emphasis)
  * Peak emotional moment
  * Beginning of key insight
  * Avoid: mid-sentence, transitions, awkward expressions
- Provide timestamp (must be between {start_time:.1f} and {end_time:.1f})

OUTPUT JSON ONLY:
{{
  "title": "Specific compelling title under 60 chars",
  "description": "Hook sentence. Main point context. Optional value statement.",
  "hashtags": ["#relevant", "#specific", "#tags", "#only", "#five"],
  "thumbnail_time": {start_time + (duration / 3):.1f},
  "thumbnail_reasoning": "Why this frame (optional debug field)"
}}

RULES:
- Title MUST be under 60 characters
- Description should be 2-3 sentences, natural tone
- Exactly 5 hashtags, no generic tags
- Thumbnail time must be within [{start_time:.1f}, {end_time:.1f}]
- Be authentic and specific, not clickbait-y
"""

    def generate_title_only(self, transcript_segment: str) -> str:
        """
        Generate just a title for a transcript segment.

        Used by ProfessionalClipAligner when clip boundaries change.

        Args:
            transcript_segment: Text content of aligned clip

        Returns:
            Generated title (max 60 chars)
        """
        try:
            from openai import OpenAI
        except ImportError:
            return "Untitled Clip"

        client = OpenAI(api_key=self.api_key)

        prompt = f"""Generate a compelling title (max 60 characters) for this video clip:

{transcript_segment}

Requirements:
- Specific and direct, not generic
- Under 60 characters
- Captures the core idea
- Natural, not clickbait

Return only the title, nothing else."""

        # Retry configuration for rate limits
        max_retries = 5
        base_delay = 2.0

        for attempt in range(max_retries):
            try:
                response = client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are a video title writer."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )

                title = response.choices[0].message.content.strip()

                # Remove quotes if present
                if title.startswith('"') and title.endswith('"'):
                    title = title[1:-1]

                # Truncate if needed
                if len(title) > self.MAX_TITLE_LENGTH:
                    title = title[:self.MAX_TITLE_LENGTH-3] + "..."

                return title

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
                        print(f"      ⚠️  Failed to regenerate title: {e}")
                        print(f"      ⏳ Retrying in {wait_time:.1f}s (attempt {attempt + 2}/{max_retries})...")
                        import time
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"      ❌ Title regeneration failed after {max_retries} retries")
                        return "Untitled Clip"
                else:
                    # Non-rate-limit error, return default title
                    print(f"      ⚠️  Failed to regenerate title: {e}")
                    return "Untitled Clip"

        return "Untitled Clip"

    def get_metrics_summary(self) -> str:
        """
        Get formatted metrics summary

        Returns:
            Formatted string with metrics
        """
        return f"""Layer 4 Metrics:
  API Calls: {self.metrics['api_calls']}
  Tokens Used: {self.metrics['tokens_used']:,}
  Cost: ${self.metrics['cost_usd']:.3f}
  Clips Packaged: {self.metrics['clips_packaged']}"""
