"""
Local speech-to-text adapter using faster-whisper (CTranslate2).

faster-whisper uses CTranslate2 weights (safetensors internally), not
PyTorch pickle files.  No ``trust_remote_code`` parameter is exposed.
"""

from decimal import Decimal
import math
from pathlib import Path
import threading
import time
from typing import Optional

from .base import (
    ProviderError,
    ProviderResponseError,
    ProviderTimeoutError,
    ProviderUsage,
    SpeechModel,
    TranscriptionResponse,
    TranscriptionSegment,
    WordTimestamp,
)
from .local_limits import MAX_SPEECH_INFERENCE_SECONDS
from ..models.hardware import LocalResourceError, clamp_threads, enforce_model_resources


_MAX_SEGMENTS = 50_000
_MAX_WORDS = 500_000
_MAX_SEGMENT_CHARS = 10_000
_MAX_WORD_CHARS = 1_000
_MAX_TRANSCRIPT_CHARS = 2_000_000


class LocalSpeechModel(SpeechModel):
    """Speech-to-text inference via faster-whisper on the local device."""

    def __init__(
        self,
        model_size_or_path: Optional[str] = None,
        device: str = "auto",
        compute_type: str = "auto",
        cpu_threads: int = 4,
        timeout_seconds: float = 300.0,
    ):
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise ProviderError(
                "faster-whisper is required for local transcription. "
                "Install with: pip install 'arena-engine[local]'",
                code="local_unavailable",
                retryable=False,
            )

        if device == "cuda":
            try:
                import ctranslate2
                if ctranslate2.get_cuda_device_count() < 1:
                    device = "cpu"
                    compute_type = "int8"
            except (ImportError, OSError, RuntimeError):
                device = "cpu"
                compute_type = "int8"

        # faster-whisper accepts aliases such as "base" and downloads them
        # implicitly. Arena permits only paths already verified by ModelLocator.
        if (
            not isinstance(model_size_or_path, str)
            or not model_size_or_path
            or not Path(model_size_or_path).is_absolute()
            or not Path(model_size_or_path).is_dir()
        ):
            raise ProviderError(
                "A verified local speech model path is required.",
                code="local_no_model",
                retryable=False,
            )

        try:
            enforce_model_resources(
                Path(model_size_or_path),
                context_size=512,
                gpu_layers=-1 if device == "cuda" else 0,
            )
        except LocalResourceError as e:
            raise ProviderError(
                str(e), code="local_resource_limit", retryable=False
            ) from e

        try:
            self._model = WhisperModel(
                model_size_or_path,
                device=device,
                compute_type=compute_type,
                cpu_threads=clamp_threads(cpu_threads),
                num_workers=1,
                local_files_only=True,
            )
        except MemoryError as e:
            raise ProviderError(
                "Local speech model does not fit in available memory.",
                code="local_oom",
                retryable=False,
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Failed to load local speech model: {type(e).__name__}",
                code="local_load_failed",
                retryable=False,
            ) from e
        self._timeout_seconds = max(
            1.0,
            min(float(timeout_seconds), MAX_SPEECH_INFERENCE_SECONDS),
        )
        self._cancelled = threading.Event()

    def __repr__(self) -> str:
        return "LocalSpeechModel()"

    @property
    def max_file_size_mb(self) -> float:
        return 24.0

    @property
    def max_audio_duration_seconds(self) -> float:
        return 600.0

    @property
    def concurrency_hint(self) -> int:
        return 1

    def cancel(self) -> None:
        """Stop consuming local transcription output as soon as control returns."""
        self._cancelled.set()

    def close(self) -> None:
        """Explicitly unload native CTranslate2 weights and release references."""
        model = getattr(self, "_model", None)
        native_model = getattr(model, "model", None)
        unload_model = getattr(native_model, "unload_model", None)
        try:
            if callable(unload_model):
                unload_model()
        finally:
            self._model = None

    def _is_cancelled(self) -> bool:
        event = getattr(self, "_cancelled", None)
        return bool(event and event.is_set())

    def transcribe(self, audio_path: Path) -> TranscriptionResponse:
        if self._is_cancelled():
            raise ProviderError(
                "Local transcription was cancelled.", code="local_cancelled", retryable=False
            )
        started_at = time.monotonic()
        try:
            segments_iter, info = self._model.transcribe(
                str(audio_path),
                word_timestamps=True,
                language=None,  # auto-detect
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.5,
                    "min_speech_duration_ms": 250,
                    "min_silence_duration_ms": 500,
                },
            )
            deadline = started_at + self._effective_timeout_seconds(
                getattr(info, "duration", None)
            )
            # Read one extra item so a resource-limit breach is reported
            # instead of silently returning a truncated transcript.
            raw_segments = []
            for seg in segments_iter:
                if self._is_cancelled():
                    raise ProviderError(
                        "Local transcription was cancelled.",
                        code="local_cancelled",
                        retryable=False,
                    )
                if time.monotonic() >= deadline:
                    raise ProviderTimeoutError(
                        "Local transcription exceeded Arena's time limit."
                    )
                raw_segments.append(seg)
                if len(raw_segments) > _MAX_SEGMENTS:
                    break
        except ProviderError:
            raise
        except MemoryError as e:
            raise ProviderError(
                "Local transcription ran out of memory.",
                code="local_oom",
                retryable=False,
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Local transcription failed: {type(e).__name__}",
                code="local_inference_error",
                retryable=False,
            ) from e

        if len(raw_segments) > _MAX_SEGMENTS:
            raise ProviderResponseError(
                "Local transcription exceeded Arena's segment limit.",
                code="local_resource_limit",
                retryable=False,
            )

        duration_value = getattr(info, "duration", None)
        language_value = getattr(info, "language", None)
        duration = duration_value if duration_value is not None else 0.0
        language = language_value if language_value else "unknown"
        if (
            isinstance(duration, bool)
            or not isinstance(duration, (int, float))
            or not math.isfinite(duration)
            or duration < 0
            or duration > self.max_audio_duration_seconds + 5
        ):
            raise ProviderResponseError(
                "Local transcription returned an invalid duration.",
                code="local_invalid_response",
                retryable=False,
            )
        duration = float(duration)
        if not isinstance(language, str) or not language or len(language) > 32:
            raise ProviderResponseError(
                "Local transcription returned an invalid language.",
                code="local_invalid_response",
                retryable=False,
            )

        words: list[WordTimestamp] = []
        segments: list[TranscriptionSegment] = []
        text_parts: list[str] = []
        total_text_chars = 0

        for seg_id, seg in enumerate(raw_segments):
            raw_text = getattr(seg, "text", None)
            start = getattr(seg, "start", None)
            end = getattr(seg, "end", None)
            segment_words = getattr(seg, "words", None)
            text = raw_text.strip() if isinstance(raw_text, str) else None
            self._validate_timestamp(start, end, duration)
            if text is None or len(text) > _MAX_SEGMENT_CHARS:
                raise ProviderResponseError(
                    "Local transcription returned invalid segment text.",
                    code="local_invalid_response",
                    retryable=False,
                )
            total_text_chars += len(text)
            if total_text_chars > _MAX_TRANSCRIPT_CHARS:
                raise ProviderResponseError(
                    "Local transcription exceeded Arena's text limit.",
                    code="local_resource_limit",
                    retryable=False,
                )
            segments.append(TranscriptionSegment(
                id=seg_id,
                start=float(start),
                end=float(end),
                text=text,
            ))
            text_parts.append(text)

            if segment_words is not None and not isinstance(segment_words, (list, tuple)):
                raise ProviderResponseError(
                    "Local transcription returned an invalid word list.",
                    code="local_invalid_response",
                    retryable=False,
                )
            if segment_words:
                for w in segment_words:
                    if len(words) >= _MAX_WORDS:
                        raise ProviderResponseError(
                            "Local transcription exceeded Arena's word limit.",
                            code="local_resource_limit",
                            retryable=False,
                        )
                    word_start = getattr(w, "start", None)
                    word_end = getattr(w, "end", None)
                    word_text = getattr(w, "word", None)
                    self._validate_timestamp(word_start, word_end, duration)
                    if not isinstance(word_text, str) or len(word_text) > _MAX_WORD_CHARS:
                        raise ProviderResponseError(
                            "Local transcription returned an invalid word.",
                            code="local_invalid_response",
                            retryable=False,
                        )
                    words.append(WordTimestamp(
                        word=word_text,
                        start=float(word_start),
                        end=float(word_end),
                    ))

        return TranscriptionResponse(
            text=" ".join(text_parts),
            language=language,
            duration=duration,
            words=words,
            segments=segments,
            usage=ProviderUsage(
                input_audio_seconds=duration,
                estimated_cost_usd=Decimal("0"),
            ),
        )

    def _effective_timeout_seconds(self, audio_duration: object) -> float:
        """Return a bounded timeout budget scaled to the current audio chunk.

        faster-whisper performs the expensive work lazily while its segment
        generator is consumed. A fixed five-minute limit rejects valid
        ten-minute chunks on supported CPU-only machines, so Arena allows up
        to two seconds of processing per second of audio plus startup overhead.
        The budget is checked whenever the native segment generator yields.
        """
        configured_timeout = getattr(self, "_timeout_seconds", 300.0)
        if (
            isinstance(audio_duration, bool)
            or not isinstance(audio_duration, (int, float))
            or not math.isfinite(audio_duration)
            or audio_duration <= 0
        ):
            return configured_timeout

        duration_budget = float(audio_duration) * 2.0 + 120.0
        return min(
            MAX_SPEECH_INFERENCE_SECONDS,
            max(configured_timeout, duration_budget),
        )

    @staticmethod
    def _validate_timestamp(start, end, duration: float) -> None:
        values = (start, end)
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            for value in values
        ):
            raise ProviderResponseError(
                "Local transcription returned a non-finite timestamp.",
                code="local_invalid_response",
                retryable=False,
            )
        if start < 0 or end < start or end > duration + 1.0:
            raise ProviderResponseError(
                "Local transcription returned an out-of-range timestamp.",
                code="local_invalid_response",
                retryable=False,
            )
