# Audio Energy Detection

Arena now includes advanced audio energy detection to identify high-energy segments where the speaker is enthusiastic, emphasizing points, or delivering engaging content.

## How It Works

The audio energy analyzer uses multiple audio features to detect speaker enthusiasm:

### 1. **RMS Energy (70% weight)**
- Measures audio loudness/volume
- Higher energy = louder, more emphatic speech
- Detects when speaker raises their voice for emphasis

### 2. **Spectral Centroid (25% weight)**
- Measures "brightness" of the audio spectrum
- Higher values indicate more high-frequency content
- Enthusiastic speech tends to have brighter tone

### 3. **Zero Crossing Rate (5% weight)**
- Measures speech activity and dynamics
- Higher values indicate more dynamic speech patterns
- Helps distinguish speech from background noise

### Algorithm

1. **Extract Audio**: Convert video to mono audio (22kHz)
2. **Compute Features**: Calculate RMS energy, spectral centroid, and ZCR
3. **Normalize**: Scale all features to 0-1 range
4. **Combine**: Create weighted combined energy score
5. **Find Peaks**: Use adaptive thresholding to detect energy peaks
6. **Create Segments**: Expand peaks into time segments with boundaries
7. **Rank**: Sort segments by energy score

## Features

- **Adaptive Thresholding**: Automatically adjusts based on audio characteristics
- **Smart Segmentation**: Finds natural boundaries around energy peaks
- **Duration Control**: Enforces min/max segment lengths
- **Peak Detection**: Uses scipy to find significant energy peaks
- **Timeline Export**: Get frame-by-frame energy values for visualization

## Usage

### Python API

```python
from pathlib import Path
from arena.audio.energy import AudioEnergyAnalyzer

# Initialize analyzer
video_path = Path("video.mp4")
analyzer = AudioEnergyAnalyzer(video_path)

# Find high-energy segments
segments = analyzer.analyze(
    min_duration=3.0,        # Minimum segment length (seconds)
    max_duration=15.0,       # Maximum segment length (seconds)
    energy_threshold=0.6,    # Energy threshold (0-1)
    top_n=10                 # Number of top segments to return
)

# Results
for seg in segments:
    print(f"Segment: {seg['start_time']:.1f}s - {seg['end_time']:.1f}s")
    print(f"Energy Score: {seg['energy_score']:.3f}")
    print(f"Duration: {seg['duration']:.1f}s")
```

### Get Energy Timeline

```python
# Get frame-by-frame energy values
timeline = analyzer.get_energy_timeline(
    hop_length=512,      # Frames between samples
    window_size=0.5      # Smoothing window (seconds)
)

# Timeline data
times = timeline['times']                    # Timestamps
energy = timeline['combined_energy']         # Combined energy score
rms = timeline['rms_energy']                 # Volume/loudness
centroid = timeline['spectral_centroid']     # Brightness
zcr = timeline['zero_crossing_rate']         # Speech activity
```

### Test Script

Run the included test script to analyze a video:

```bash
cd engine
python test_energy.py path/to/video.mp4
```

Output:
```
============================================================
Testing Audio Energy Detection
============================================================

📹 Video: presentation.mp4

🔧 Initializing audio energy analyzer...
📊 Computing energy timeline...
   ✓ Analyzed 2847 frames
   ✓ Duration: 125.3 seconds
   ✓ Max energy: 0.892
   ✓ Avg energy: 0.456

🎯 Detecting high-energy segments...
   ✓ Found 10 high-energy segments

============================================================
Top High-Energy Segments
============================================================

#1 - energy_001
   Time: 02:15 → 02:28 (13.0s)
   Peak Energy: 0.892
   Avg Energy:  0.785
   Peak at:     02:21

#2 - energy_002
   Time: 05:42 → 05:55 (13.0s)
   Peak Energy: 0.856
   Avg Energy:  0.734
   Peak at:     05:48
...

============================================================
✅ Results saved to: presentation_energy_analysis.json
============================================================
```

## Output Format

Each segment includes:

```python
{
    'id': 'energy_001',           # Unique identifier
    'start_time': 135.5,          # Start time (seconds)
    'end_time': 148.3,            # End time (seconds)
    'duration': 12.8,             # Duration (seconds)
    'peak_time': 141.2,           # Time of peak energy (seconds)
    'energy_score': 0.892,        # Peak energy score (0-1)
    'avg_energy': 0.785,          # Average energy in segment (0-1)
    'source': 'audio_energy'      # Detection source
}
```

## Integration with AI Analysis

Audio energy detection complements transcript-based AI analysis:

1. **AI Analysis**: Identifies interesting content (hooks, insights, stories)
2. **Energy Detection**: Identifies enthusiastic delivery
3. **Combined**: Best clips have both interesting content AND high energy

### Future Integration

```python
# Coming soon: Hybrid scoring
from arena.ai.analyzer import TranscriptAnalyzer
from arena.audio.energy import AudioEnergyAnalyzer

# Analyze with both methods
ai_clips = TranscriptAnalyzer().analyze_transcript(transcript)
energy_segments = AudioEnergyAnalyzer(video).analyze()

# Boost scores for clips with high energy
for clip in ai_clips:
    # Find overlapping energy segments
    overlapping = find_overlapping(clip, energy_segments)
    if overlapping:
        clip['interest_score'] *= (1 + overlapping['energy_score'] * 0.3)
```

## Parameters

### `analyze()` Parameters

- **min_duration** (default: 3.0)
  - Minimum segment length in seconds
  - Shorter segments will be expanded

- **max_duration** (default: 15.0)
  - Maximum segment length in seconds
  - Longer segments will be trimmed

- **energy_threshold** (default: 0.6)
  - Minimum energy level to consider (0-1)
  - Lower = more segments, higher = only most energetic

- **top_n** (default: 10)
  - Number of top segments to return
  - Results are sorted by energy score

### `get_energy_timeline()` Parameters

- **hop_length** (default: 512)
  - Samples between analysis frames
  - Lower = more detailed, slower

- **window_size** (default: 0.5)
  - Smoothing window in seconds
  - Larger = smoother, less noisy

## Technical Details

### Dependencies

All required packages are already in `requirements.txt`:
- `librosa>=0.10.0` - Audio analysis
- `scipy>=1.11.0` - Signal processing
- `numpy>=1.24.0` - Numerical operations
- `soundfile>=0.12.0` - Audio I/O

### Performance

- **Speed**: ~2-5x real-time (10min video analyzed in 2-5min)
- **Memory**: ~100-200MB for typical videos
- **Audio Format**: Automatically converts to 22kHz mono WAV

### Audio Extraction

The analyzer automatically extracts audio from video using FFmpeg:
- Format: 16-bit PCM WAV
- Sample Rate: 22,050 Hz (optimal for speech)
- Channels: Mono (speech analysis doesn't need stereo)

## Tips for Best Results

1. **Adjust threshold for content type**
   - Podcast/interview: 0.5-0.6 (moderate energy)
   - Presentation: 0.6-0.7 (higher energy)
   - Quiet video: 0.4-0.5 (lower threshold)

2. **Segment duration**
   - Short clips (TikTok): min=5, max=15
   - Medium (Reels): min=10, max=30
   - Longer (YouTube): min=30, max=90

3. **Combine with transcript analysis**
   - Energy alone finds enthusiasm
   - AI analysis finds interesting content
   - Together = most engaging clips

## Example: Integration with Arena Pipeline

```python
from pathlib import Path
from arena.audio.transcriber import Transcriber
from arena.audio.energy import AudioEnergyAnalyzer
from arena.ai.analyzer import TranscriptAnalyzer

# Full pipeline
video = Path("video.mp4")

# Step 1: Transcribe
transcriber = Transcriber()
transcript = transcriber.transcribe(video)

# Step 2: AI analysis for content
ai_analyzer = TranscriptAnalyzer()
ai_clips = ai_analyzer.analyze_transcript(transcript)

# Step 3: Energy analysis for enthusiasm
energy_analyzer = AudioEnergyAnalyzer(video)
energy_segments = energy_analyzer.analyze()

# Step 4: Boost scores for clips with high energy
# (Implementation coming in next sprint)

# Step 5: Generate clips
from arena.clipping.generator import ClipGenerator
generator = ClipGenerator(video)
for clip in ai_clips[:5]:  # Top 5 clips
    generator.generate_clip(
        clip['start_time'],
        clip['end_time'],
        output_dir / f"{clip['id']}.mp4"
    )
```

## Next Steps

- ✅ Audio energy detection implemented
- 🔄 Integration with transcript analysis (coming soon)
- 🔄 Hybrid scoring system (coming soon)
- 🔄 Energy visualization in CLI (coming soon)
- 🔄 Real-time energy monitoring (future)

## Troubleshooting

**"No high-energy segments found"**
- Lower the `energy_threshold` parameter
- Check if audio is very quiet (enhance first)
- Verify video has audio track

**"Failed to extract audio"**
- Ensure FFmpeg is installed
- Check video file is valid
- Try providing audio_path directly

**Segments seem off**
- Adjust `min_duration` and `max_duration`
- Try different `energy_threshold` values
- Use `get_energy_timeline()` to visualize energy levels

## License

MIT
