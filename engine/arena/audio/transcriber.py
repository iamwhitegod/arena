"""Audio transcription using OpenAI Whisper"""
from pathlib import Path
from typing import Dict, List, Optional
import os
import subprocess
import tempfile
import shutil

from arena.providers.subprocess_env import scrubbed_env


class Transcriber:
    """Handles audio transcription with word-level timestamps"""

    MAX_TRANSCRIPTION_CHUNKS = 1000

    def __init__(self, api_key: str = None, mode: str = "api", *, speech=None):
        """
        Initialize transcriber

        Args:
            api_key: OpenAI API key (used when no speech model is provided)
            mode: 'api' for OpenAI Whisper API, 'local' for local Whisper model
            speech: Optional SpeechModel instance (takes precedence over api_key/mode)
        """
        if speech is not None:
            self._speech = speech
            self.mode = "provider"
        elif mode == "local":
            self._speech = None
            self.mode = "local"
        elif api_key is not None or os.getenv("OPENAI_API_KEY"):
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            from arena.providers.openai_adapter import OpenAISpeechModel
            self._speech = OpenAISpeechModel(api_key=api_key)
            self.mode = "provider"
        else:
            raise ValueError(
                "Either speech model, api_key, or mode='local' required"
            )
        self.api_key = api_key  # keep for backward compat

    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus'}

    def _is_audio_file(self, file_path: Path) -> bool:
        """Check if the input file is an audio-only format."""
        return file_path.suffix.lower() in self.AUDIO_EXTENSIONS

    def transcribe(self, video_path: Path, cache_dir: Optional[Path] = None) -> Dict:
        """
        Transcribe audio from a video or audio file with word-level timestamps.

        Args:
            video_path: Path to video or audio file
            cache_dir: Optional directory to cache audio file

        Returns:
            Dict containing full transcript and word-level timestamps
        """
        video_path = Path(video_path)

        # If input is already an audio file, use it directly
        if self._is_audio_file(video_path):
            audio_path = video_path
            is_direct_audio = True
        else:
            # Extract audio from video
            if cache_dir:
                cache_dir = Path(cache_dir)
                cache_dir.mkdir(parents=True, exist_ok=True)
                audio_path = cache_dir / f"{video_path.stem}_audio.mp3"
            else:
                temp_dir = tempfile.mkdtemp()
                audio_path = Path(temp_dir) / "audio.mp3"

            self.extract_audio(video_path, audio_path)
            is_direct_audio = False

        # Transcribe based on mode
        if self.mode == "local":
            result = self._transcribe_local(audio_path)
        else:
            result = self._transcribe_with_provider(audio_path)

        # Clean up temporary file if not cached (don't delete user's audio file)
        if not is_direct_audio and not cache_dir and audio_path.exists():
            audio_path.unlink()

        return result

    @staticmethod
    def _response_to_dict(response, offset: float = 0.0, segment_id_start: int = 0) -> Dict:
        """Convert a TranscriptionResponse to the plain-dict format Arena expects.

        Args:
            response: TranscriptionResponse from a SpeechModel
            offset: Timestamp offset to add (for chunked transcription)
            segment_id_start: Starting segment ID (for chunked transcription)
        """
        words = [
            {"word": w.word, "start": w.start + offset, "end": w.end + offset}
            for w in response.words
        ]
        segments = [
            {
                "id": segment_id_start + i,
                "start": s.start + offset,
                "end": s.end + offset,
                "text": s.text,
            }
            for i, s in enumerate(response.segments)
        ]
        return {
            "text": response.text,
            "language": response.language,
            "duration": response.duration,
            "words": words,
            "segments": segments,
        }

    def _transcribe_with_provider(self, audio_path: Path) -> Dict:
        """Transcribe using the injected SpeechModel."""
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        limit = self._speech.max_file_size_mb

        if file_size_mb > limit:
            print(f"⚠️  Audio file is {file_size_mb:.1f}MB (limit: {limit:.0f}MB)")
            print(f"   Chunking audio into smaller segments...")
            return self._transcribe_chunked(audio_path)

        response = self._speech.transcribe(audio_path)
        return self._response_to_dict(response)

    def _transcribe_chunked(self, audio_path: Path) -> Dict:
        """
        Transcribe large audio files by chunking into smaller segments.

        Args:
            audio_path: Path to audio file exceeding the provider's size limit

        Returns:
            Merged transcript from all chunks
        """
        import math

        duration = self._get_audio_duration(audio_path)
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError("Audio duration must be a positive finite number")

        limit_mb = self._speech.max_file_size_mb
        if not math.isfinite(limit_mb) or limit_mb <= 0:
            raise ValueError("Speech provider file-size limit must be positive and finite")

        limit_bytes = int(limit_mb * 1024 * 1024)
        # Chunks are encoded as 64 kbps mono MP3. Reserve 10% for container
        # overhead and bitrate variation, then verify the actual output size.
        encoded_bytes_per_second = 64_000 / 8
        chunk_duration = min(600.0, (limit_bytes * 0.9) / encoded_bytes_per_second)
        minimum_chunk_duration = 0.25
        if chunk_duration < minimum_chunk_duration:
            raise ValueError("Speech provider file-size limit is too small for audio chunks")

        estimated_chunks = max(math.ceil(duration / chunk_duration), 1)
        if estimated_chunks > self.MAX_TRANSCRIPTION_CHUNKS:
            raise ValueError(
                f"Transcription would require more than {self.MAX_TRANSCRIPTION_CHUNKS} chunks"
            )
        print(
            f"   Splitting {duration/60:.1f} minutes into "
            f"approximately {estimated_chunks} chunks..."
        )

        all_words = []
        all_segments = []
        full_text = []
        last_language = "en"

        temp_dir = Path(tempfile.mkdtemp())

        try:
            start_time = 0.0
            chunk_index = 0
            while start_time < duration:
                if chunk_index >= self.MAX_TRANSCRIPTION_CHUNKS:
                    raise ValueError(
                        f"Transcription exceeded {self.MAX_TRANSCRIPTION_CHUNKS} chunks"
                    )
                candidate_duration = min(chunk_duration, duration - start_time)
                chunk_path = temp_dir / f"chunk_{chunk_index:03d}.mp3"

                while True:
                    end_time = min(start_time + candidate_duration, duration)
                    self._extract_audio_chunk(audio_path, chunk_path, start_time, end_time)
                    if chunk_path.stat().st_size <= limit_bytes:
                        break

                    chunk_path.unlink(missing_ok=True)
                    candidate_duration /= 2
                    if candidate_duration < minimum_chunk_duration:
                        raise ValueError(
                            "Unable to create an audio chunk within the provider file-size limit"
                        )

                # If real encoded output was larger than estimated, retain the
                # smaller proven duration for subsequent chunks.
                chunk_duration = min(chunk_duration, candidate_duration)
                print(
                    f"   Transcribing chunk {chunk_index + 1} "
                    f"({start_time/60:.1f}-{end_time/60:.1f} min)..."
                )

                response = self._speech.transcribe(chunk_path)
                chunk_dict = self._response_to_dict(
                    response,
                    offset=start_time,
                    segment_id_start=len(all_segments),
                )

                all_words.extend(chunk_dict["words"])
                all_segments.extend(chunk_dict["segments"])
                full_text.append(chunk_dict["text"])
                last_language = chunk_dict["language"]

                chunk_path.unlink()
                start_time = end_time
                chunk_index += 1

            print(f"   ✓ Transcription complete ({chunk_index} chunks merged)\n")

            return {
                "text": " ".join(full_text),
                "language": last_language,
                "duration": duration,
                "words": all_words,
                "segments": all_segments,
            }

        finally:
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _get_audio_duration(self, audio_path: Path) -> float:
        """Get audio duration in seconds using ffprobe"""
        command = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path)
        ]

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=scrubbed_env(),
        )

        return float(result.stdout.strip())

    def _extract_audio_chunk(
        self,
        audio_path: Path,
        output_path: Path,
        start_time: float,
        end_time: float
    ):
        """Extract a specific time range from audio file"""
        duration = end_time - start_time

        command = [
            "ffmpeg",
            "-i", str(audio_path),
            "-ss", str(start_time),
            "-t", str(duration),
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            "-y",
            str(output_path)
        ]

        subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            env=scrubbed_env(),
        )

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
                check=True,
                env=scrubbed_env(),
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
