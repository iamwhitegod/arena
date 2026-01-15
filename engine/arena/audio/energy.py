"""Audio energy analysis for detecting speaker enthusiasm"""
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import subprocess
import tempfile


class AudioEnergyAnalyzer:
    """Analyzes audio for energy peaks indicating enthusiasm or emphasis"""

    def __init__(self, video_path: Path, audio_path: Optional[Path] = None):
        """
        Initialize audio energy analyzer

        Args:
            video_path: Path to video file
            audio_path: Optional path to extracted audio (will extract if not provided)
        """
        self.video_path = video_path
        self.audio_path = audio_path
        self._audio_data = None
        self._sample_rate = None

    def analyze(
        self,
        min_duration: float = 3.0,
        max_duration: float = 15.0,
        energy_threshold: float = 0.6,
        top_n: int = 10
    ) -> List[Dict]:
        """
        Analyze audio energy to find high-energy segments

        Args:
            min_duration: Minimum segment duration in seconds
            max_duration: Maximum segment duration in seconds
            energy_threshold: Energy threshold (0-1) for detecting peaks
            top_n: Number of top segments to return

        Returns:
            List of high-energy timestamp ranges with scores
        """
        try:
            import librosa
            from scipy.signal import find_peaks
        except ImportError:
            raise ImportError(
                "Required packages not installed. "
                "Run: pip install librosa scipy"
            )

        # Load audio if not already loaded
        if self._audio_data is None:
            self._load_audio()

        y, sr = self._audio_data, self._sample_rate

        # Compute energy features
        hop_length = 512
        rms_energy = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        spectral_centroid = librosa.feature.spectral_centroid(
            y=y, sr=sr, hop_length=hop_length
        )[0]

        # Normalize features to 0-1 range
        rms_normalized = self._normalize(rms_energy)
        centroid_normalized = self._normalize(spectral_centroid)

        # Combine features: RMS energy (70%) + spectral brightness (30%)
        # High energy + high spectral centroid = enthusiastic speech
        combined_energy = 0.7 * rms_normalized + 0.3 * centroid_normalized

        # Convert frame indices to time
        frame_times = librosa.frames_to_time(
            np.arange(len(combined_energy)),
            sr=sr,
            hop_length=hop_length
        )

        # Find energy peaks
        # Use adaptive threshold based on energy distribution
        threshold_value = np.percentile(combined_energy, 70)
        threshold_value = max(threshold_value, energy_threshold)

        # Minimum distance between peaks (prevent clustering)
        min_distance_frames = int(sr / hop_length * 2)  # 2 seconds apart

        peaks, properties = find_peaks(
            combined_energy,
            height=threshold_value,
            distance=min_distance_frames,
            prominence=0.1  # Require significant prominence
        )

        if len(peaks) == 0:
            return []

        # Convert peaks to segments
        segments = self._peaks_to_segments(
            peaks,
            frame_times,
            combined_energy,
            min_duration,
            max_duration
        )

        # Sort by energy score and return top N
        segments.sort(key=lambda x: x['energy_score'], reverse=True)
        return segments[:top_n]

    def get_energy_timeline(
        self,
        hop_length: int = 512,
        window_size: float = 0.5
    ) -> Dict[str, np.ndarray]:
        """
        Get frame-by-frame energy values

        Args:
            hop_length: Number of samples between frames
            window_size: Smoothing window size in seconds

        Returns:
            Dict with 'times', 'rms_energy', 'spectral_centroid', 'combined_energy'
        """
        try:
            import librosa
            from scipy.ndimage import uniform_filter1d
        except ImportError:
            raise ImportError(
                "Required packages not installed. "
                "Run: pip install librosa scipy"
            )

        # Load audio if not already loaded
        if self._audio_data is None:
            self._load_audio()

        y, sr = self._audio_data, self._sample_rate

        # Compute RMS energy (volume/loudness)
        rms_energy = librosa.feature.rms(y=y, hop_length=hop_length)[0]

        # Compute spectral centroid (brightness/emphasis)
        spectral_centroid = librosa.feature.spectral_centroid(
            y=y, sr=sr, hop_length=hop_length
        )[0]

        # Compute zero crossing rate (speech activity)
        zcr = librosa.feature.zero_crossing_rate(y=y, hop_length=hop_length)[0]

        # Normalize all features
        rms_normalized = self._normalize(rms_energy)
        centroid_normalized = self._normalize(spectral_centroid)
        zcr_normalized = self._normalize(zcr)

        # Combined energy score
        # RMS (70%) + Spectral Centroid (25%) + ZCR (5%)
        combined_energy = (
            0.70 * rms_normalized +
            0.25 * centroid_normalized +
            0.05 * zcr_normalized
        )

        # Smooth the timeline to reduce noise
        window_frames = int(window_size * sr / hop_length)
        if window_frames > 1:
            combined_energy = uniform_filter1d(
                combined_energy, size=window_frames, mode='nearest'
            )

        # Convert frame indices to timestamps
        times = librosa.frames_to_time(
            np.arange(len(rms_energy)),
            sr=sr,
            hop_length=hop_length
        )

        return {
            'times': times,
            'rms_energy': rms_normalized,
            'spectral_centroid': centroid_normalized,
            'zero_crossing_rate': zcr_normalized,
            'combined_energy': combined_energy
        }

    def _load_audio(self) -> None:
        """Load audio from video file"""
        try:
            import librosa
        except ImportError:
            raise ImportError("librosa is required. Install with: pip install librosa")

        # Extract audio if path not provided
        if self.audio_path is None or not self.audio_path.exists():
            self.audio_path = self._extract_audio_temp()

        # Load audio with librosa
        y, sr = librosa.load(str(self.audio_path), sr=None, mono=True)
        self._audio_data = y
        self._sample_rate = sr

    def _extract_audio_temp(self) -> Path:
        """Extract audio to temporary file"""
        temp_dir = tempfile.mkdtemp()
        audio_path = Path(temp_dir) / f"{self.video_path.stem}_audio.wav"

        command = [
            "ffmpeg",
            "-i", str(self.video_path),
            "-vn",  # No video
            "-acodec", "pcm_s16le",  # WAV format
            "-ar", "22050",  # 22kHz sample rate (good for speech)
            "-ac", "1",  # Mono
            "-y",  # Overwrite
            str(audio_path)
        ]

        try:
            subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
            return audio_path
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to extract audio: {e.stderr.decode('utf-8')}")

    def _normalize(self, data: np.ndarray) -> np.ndarray:
        """Normalize array to 0-1 range"""
        min_val = np.min(data)
        max_val = np.max(data)
        if max_val - min_val < 1e-10:  # Avoid division by zero
            return np.zeros_like(data)
        return (data - min_val) / (max_val - min_val)

    def _peaks_to_segments(
        self,
        peaks: np.ndarray,
        frame_times: np.ndarray,
        energy_values: np.ndarray,
        min_duration: float,
        max_duration: float
    ) -> List[Dict]:
        """
        Convert energy peaks to time segments

        Args:
            peaks: Peak frame indices
            frame_times: Time value for each frame
            energy_values: Energy values for each frame
            min_duration: Minimum segment duration
            max_duration: Maximum segment duration

        Returns:
            List of segment dictionaries
        """
        segments = []

        for i, peak_idx in enumerate(peaks):
            peak_time = frame_times[peak_idx]
            peak_energy = energy_values[peak_idx]

            # Find segment boundaries around the peak
            # Extend backwards and forwards to find energy drop-off points
            start_idx, end_idx = self._find_segment_boundaries(
                peak_idx,
                energy_values,
                threshold_ratio=0.5  # Drop to 50% of peak energy
            )

            start_time = frame_times[start_idx]
            end_time = frame_times[end_idx]
            duration = end_time - start_time

            # Ensure minimum duration
            if duration < min_duration:
                # Expand segment symmetrically
                expand = (min_duration - duration) / 2
                start_time = max(0, start_time - expand)
                end_time = min(frame_times[-1], end_time + expand)
                duration = end_time - start_time

            # Clip to maximum duration
            if duration > max_duration:
                # Keep the peak centered, trim edges
                trim = (duration - max_duration) / 2
                start_time += trim
                end_time -= trim
                duration = max_duration

            # Calculate average energy in segment
            seg_start_idx = np.searchsorted(frame_times, start_time)
            seg_end_idx = np.searchsorted(frame_times, end_time)
            avg_energy = np.mean(energy_values[seg_start_idx:seg_end_idx])

            segments.append({
                'id': f'energy_{i+1:03d}',
                'start_time': float(start_time),
                'end_time': float(end_time),
                'duration': float(duration),
                'peak_time': float(peak_time),
                'energy_score': float(peak_energy),
                'avg_energy': float(avg_energy),
                'source': 'audio_energy'
            })

        return segments

    def _find_segment_boundaries(
        self,
        peak_idx: int,
        energy_values: np.ndarray,
        threshold_ratio: float = 0.5
    ) -> Tuple[int, int]:
        """
        Find segment start and end around a peak

        Args:
            peak_idx: Index of peak frame
            energy_values: Energy timeline
            threshold_ratio: Energy threshold relative to peak (0-1)

        Returns:
            Tuple of (start_index, end_index)
        """
        peak_energy = energy_values[peak_idx]
        threshold = peak_energy * threshold_ratio

        # Search backwards for start
        start_idx = peak_idx
        for i in range(peak_idx - 1, -1, -1):
            if energy_values[i] < threshold:
                break
            start_idx = i

        # Search forwards for end
        end_idx = peak_idx
        for i in range(peak_idx + 1, len(energy_values)):
            if energy_values[i] < threshold:
                break
            end_idx = i

        return start_idx, end_idx
