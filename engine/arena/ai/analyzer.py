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

        if not self.api_key:
            raise ValueError("OpenAI API key is required")

    def analyze_transcript(
        self,
        transcript_data: Dict,
        target_clips: int = 10,
        min_duration: int = 30,
        max_duration: int = 90
    ) -> List[Dict]:
        """
        Analyze transcript to identify interesting segments

        Args:
            transcript_data: Transcript dict with 'text' and 'segments'
            target_clips: Number of clips to identify
            min_duration: Minimum clip duration in seconds
            max_duration: Maximum clip duration in seconds

        Returns:
            List of candidate segments with timestamps, titles, and reasons
        """
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )

        client = OpenAI(api_key=self.api_key)

        # Format transcript with timestamps for better context
        formatted_transcript = self._format_transcript_with_timestamps(
            transcript_data.get("segments", [])
        )

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
            raise RuntimeError(f"Failed to analyze transcript with AI: {str(e)}")

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
        min_duration: int,
        max_duration: int
    ) -> str:
        """Create the analysis prompt for GPT"""
        return f"""Analyze this video transcript and identify the {target_clips} most interesting segments that would make engaging short clips for social media.

Each clip should be between {min_duration}-{max_duration} seconds long and should:
- Have a clear hook or attention-grabbing opening
- Contain a complete thought or story arc
- Be engaging and valuable on its own
- Appeal to developers, founders, or technical content creators

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
- Ensure clips are between {min_duration}-{max_duration} seconds
- Use actual timestamp values from the transcript
- Make titles compelling and specific (not generic)
- Interest score should be 0.0 to 1.0
- Content types: "hook", "insight", "advice", "story", "controversial", "emotional"
- Return exactly {target_clips} clips, ranked by interest_score (highest first)
"""

    def _validate_clips(
        self,
        clips: List[Dict],
        min_duration: int,
        max_duration: int
    ) -> List[Dict]:
        """Validate and normalize clip data"""
        validated = []

        for i, clip in enumerate(clips):
            # Ensure required fields exist
            if not all(k in clip for k in ["start_time", "end_time", "title"]):
                continue

            # Calculate duration
            duration = clip["end_time"] - clip["start_time"]

            # Validate duration
            if duration < min_duration or duration > max_duration:
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
