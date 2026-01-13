"""Audio transcription using OpenAI Whisper"""
from pathlib import Path
from typing import Dict, List, Optional
import os
import subprocess
import tempfile


class Transcriber:
    """Handles audio transcription with word-level timestamps"""

    def __init__(self, api_key: str = None, mode: str = "api"):
        """
        Initialize transcriber

        Args:
            api_key: OpenAI API key (required for 'api' mode)
            mode: 'api' for OpenAI Whisper API, 'local' for local Whisper model
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.mode = mode

        if self.mode == "api" and not self.api_key:
            raise ValueError("OpenAI API key is required for 'api' mode")

    def transcribe(self, video_path: Path, cache_dir: Optional[Path] = None) -> Dict:
        """
        Transcribe video audio with word-level timestamps

        Args:
            video_path: Path to video file
            cache_dir: Optional directory to cache audio file

        Returns:
            Dict containing full transcript and word-level timestamps
        """
        # Extract audio to temporary file
        if cache_dir:
            cache_dir = Path(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            audio_path = cache_dir / f"{video_path.stem}_audio.mp3"
        else:
            # Use temporary file
            temp_dir = tempfile.mkdtemp()
            audio_path = Path(temp_dir) / "audio.mp3"

        # Extract audio from video
        self.extract_audio(video_path, audio_path)

        # Transcribe based on mode
        if self.mode == "api":
            result = self._transcribe_with_api(audio_path)
        else:
            result = self._transcribe_local(audio_path)

        # Clean up temporary file if not cached
        if not cache_dir and audio_path.exists():
            audio_path.unlink()

        return result

    def _transcribe_with_api(self, audio_path: Path) -> Dict:
        """Transcribe using OpenAI Whisper API"""
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "openai package is required for API mode. "
                "Install with: pip install openai"
            )

        client = OpenAI(api_key=self.api_key)

        with open(audio_path, "rb") as audio_file:
            # Call Whisper API with verbose JSON format
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["word", "segment"]
            )

        # Convert response to our format
        result = {
            "text": transcript.text,
            "language": getattr(transcript, 'language', 'en'),
            "duration": getattr(transcript, 'duration', 0),
            "words": [],
            "segments": []
        }

        # Extract word-level timestamps
        if hasattr(transcript, 'words') and transcript.words:
            result["words"] = [
                {
                    "word": word.word,
                    "start": word.start,
                    "end": word.end
                }
                for word in transcript.words
            ]

        # Extract segment-level timestamps
        if hasattr(transcript, 'segments') and transcript.segments:
            result["segments"] = [
                {
                    "id": segment.id,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                }
                for segment in transcript.segments
            ]

        return result

    def _transcribe_local(self, audio_path: Path) -> Dict:
        """Transcribe using local Whisper model"""
        try:
            import whisper
        except ImportError:
            raise ImportError(
                "whisper package is required for local mode. "
                "Install with: pip install openai-whisper"
            )

        # Load model (base is a good balance of speed and accuracy)
        model = whisper.load_model("base")

        # Transcribe with word timestamps
        result = model.transcribe(
            str(audio_path),
            word_timestamps=True,
            verbose=False
        )

        # Convert to our format
        formatted_result = {
            "text": result["text"],
            "language": result["language"],
            "duration": 0,  # Will be calculated from segments
            "words": [],
            "segments": []
        }

        # Extract segments
        if "segments" in result:
            for segment in result["segments"]:
                formatted_result["segments"].append({
                    "id": segment["id"],
                    "start": segment["start"],
                    "end": segment["end"],
                    "text": segment["text"]
                })

                # Extract words from segment if available
                if "words" in segment:
                    for word in segment["words"]:
                        formatted_result["words"].append({
                            "word": word["word"],
                            "start": word["start"],
                            "end": word["end"]
                        })

            # Calculate total duration from last segment
            if formatted_result["segments"]:
                formatted_result["duration"] = formatted_result["segments"][-1]["end"]

        return formatted_result

    def extract_audio(self, video_path: Path, output_path: Path) -> Path:
        """
        Extract audio from video file using FFmpeg

        Args:
            video_path: Path to video file
            output_path: Path where audio should be saved

        Returns:
            Path to extracted audio file
        """
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        # Use FFmpeg to extract audio
        # -vn: no video, -acodec: audio codec, -ar: audio sample rate, -ac: audio channels
        command = [
            "ffmpeg",
            "-i", str(video_path),
            "-vn",  # No video
            "-acodec", "libmp3lame",  # MP3 codec
            "-ar", "16000",  # 16kHz sample rate (good for speech)
            "-ac", "1",  # Mono channel
            "-b:a", "128k",  # 128kbps bitrate
            "-y",  # Overwrite output file
            str(output_path)
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return output_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"FFmpeg failed to extract audio: {e.stderr.decode('utf-8')}"
            )
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg is not installed or not in PATH. "
                "Please install FFmpeg: https://ffmpeg.org/download.html"
            )
