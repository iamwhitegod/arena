< Clip Generation

Arena's clip generation system uses FFmpeg to extract high-quality video clips from analyzed segments with full metadata and thumbnails.

## Features

- **FFmpeg-based extraction** - Fast, reliable video processing
- **Dual extraction modes** - Quality re-encoding or fast stream copy
- **Batch processing** - Generate multiple clips efficiently
- **Progress tracking** - Real-time feedback during generation
- **Metadata generation** - JSON files with clip details and scores
- **Thumbnail extraction** - Create preview images at any timestamp
- **Flexible encoding** - Customize quality, codec, and presets

## How It Works

```
Video File → ClipGenerator → FFmpeg → Output Clips
                  ↓
           Video Analysis
           (duration, codec, resolution)
                  ↓
           Segment Extraction
           (start/end with padding)
                  ↓
           Encoding/Copy
           (quality or speed)
                  ↓
           Metadata + Thumbnails
```

## Usage

### Basic Clip Generation

```python
from pathlib import Path
from arena.clipping.generator import ClipGenerator

# Initialize
video = Path("video.mp4")
generator = ClipGenerator(video)

# Get video info
info = generator.get_video_info()
print(f"Duration: {info['duration']}s")
print(f"Resolution: {info['width']}x{info['height']}")

# Generate a single clip
clip_info = generator.generate_clip(
    start_time=125.5,    # Start at 2:05
    end_time=168.3,      # End at 2:48
    output_path=Path("clip_001.mp4"),
    padding=0.5          # Add 0.5s before/after
)

print(f"Clip saved: {clip_info['output_path']}")
print(f"Size: {clip_info['size_mb']} MB")
```

### Batch Clip Generation

```python
# Define segments (from hybrid analysis)
segments = [
    {
        'id': 'clip_001',
        'start_time': 125.5,
        'end_time': 168.3,
        'title': 'Product-market fit insights'
    },
    {
        'id': 'clip_002',
        'start_time': 245.0,
        'end_time': 289.5,
        'title': 'Growth strategy'
    },
    {
        'id': 'clip_003',
        'start_time': 420.2,
        'end_time': 465.8,
        'title': 'Funding advice'
    }
]

# Progress callback
def on_progress(current, total, clip_info):
    if clip_info.get('success'):
        print(f"[{current}/{total}] ✓ {clip_info['clip_id']} "
              f"({clip_info['duration']:.1f}s)")
    else:
        print(f"[{current}/{total}] ✗ {clip_info['clip_id']} "
              f"- {clip_info['error']}")

# Generate all clips
results = generator.generate_multiple_clips(
    segments=segments,
    output_dir=Path("output/clips"),
    padding=0.5,
    fast_mode=False,  # Use quality re-encoding
    progress_callback=on_progress
)

# Check results
successful = sum(1 for r in results if r.get('success'))
print(f"Generated {successful}/{len(segments)} clips")
```

### Fast Mode (Stream Copy)

For quick extraction without re-encoding:

```python
# Much faster but less precise timing
clip_info = generator.generate_clip_fast(
    start_time=125.0,
    end_time=180.0,
    output_path=Path("clip_fast.mp4"),
    padding=1.0
)

# Pros: 10-50x faster
# Cons: Less precise timing, larger file size
```

### Thumbnail Generation

```python
# Extract thumbnail at specific timestamp
thumb_path = generator.generate_thumbnail(
    timestamp=150.0,              # At 2:30
    output_path=Path("thumb.jpg"),
    width=640                     # Maintains aspect ratio
)

# Or with specific dimensions
thumb_path = generator.generate_thumbnail(
    timestamp=150.0,
    output_path=Path("thumb.jpg"),
    width=1280,
    height=720                    # Exact dimensions
)
```

### Full Clip with Metadata

```python
# Generate clip with metadata and thumbnail
segment = {
    'id': 'clip_001',
    'start_time': 125.5,
    'end_time': 168.3,
    'title': 'Why most startups fail',
    'reason': 'Strong hook with insights',
    'content_type': 'insight',
    'interest_score': 0.85,
    'hybrid_score': 0.92,
    'energy_score': 0.75
}

clip_info = generator.generate_clip_with_metadata(
    segment=segment,
    output_dir=Path("output"),
    padding=0.5,
    generate_thumb=True
)

# Outputs:
# - clip_001.mp4 (video clip)
# - clip_001_thumb.jpg (thumbnail)
# - clip_001_metadata.json (full metadata)
```

## Quality Settings

### CRF (Constant Rate Factor)

Controls video quality (lower = better quality, larger file):

```python
# High quality (larger files)
generator.generate_clip(..., crf=18)  # Near lossless

# Balanced (default)
generator.generate_clip(..., crf=23)  # Good quality

# Smaller files
generator.generate_clip(..., crf=28)  # Acceptable quality
```

### Encoding Presets

Control encoding speed vs. file size:

```python
# Faster encoding, larger files
generator.generate_clip(..., preset="ultrafast")
generator.generate_clip(..., preset="fast")

# Balanced (default)
generator.generate_clip(..., preset="medium")

# Slower encoding, smaller files
generator.generate_clip(..., preset="slow")
generator.generate_clip(..., preset="veryslow")
```

## Output Formats

### Clip Info Dictionary

```python
{
    'output_path': '/path/to/clip_001.mp4',
    'start_time': 125.0,
    'end_time': 168.5,
    'duration': 43.5,
    'requested_start': 125.5,
    'requested_end': 168.3,
    'padding': 0.5,
    'size_bytes': 8472956,
    'size_mb': 8.08,
    'codec': 'libx264',
    'crf': 23,
    'success': True
}
```

### Metadata JSON File

```json
{
  "output_path": "clip_001.mp4",
  "start_time": 125.0,
  "end_time": 168.5,
  "duration": 43.5,
  "size_mb": 8.08,
  "clip_id": "clip_001",
  "title": "Why most startups fail at product-market fit",
  "description": "Strong hook with controversial insight",
  "content_type": "insight",
  "thumbnail": "clip_001_thumb.jpg",
  "scores": {
    "interest": 0.85,
    "hybrid": 0.92,
    "energy": 0.75
  }
}
```

## Integration with Analysis Pipeline

Complete workflow from analysis to clips:

```python
from pathlib import Path
from arena.audio.transcriber import Transcriber
from arena.audio.energy import AudioEnergyAnalyzer
from arena.ai.hybrid import HybridAnalyzer, TranscriptAnalyzer
from arena.clipping.generator import ClipGenerator

video = Path("video.mp4")
output_dir = Path("output")

# Step 1: Transcribe
print("Transcribing...")
transcriber = Transcriber()
transcript = transcriber.transcribe(video)

# Step 2: Hybrid Analysis
print("Analyzing...")
ai_analyzer = TranscriptAnalyzer()
energy_analyzer = AudioEnergyAnalyzer(video)
hybrid = HybridAnalyzer(ai_analyzer, energy_analyzer)

results = hybrid.analyze_video(
    video,
    transcript,
    target_clips=10,
    min_duration=30,
    max_duration=90
)

print(f"Found {len(results['clips'])} clips")

# Step 3: Generate Clips
print("Generating clips...")
generator = ClipGenerator(video)

def progress(current, total, clip_info):
    print(f"[{current}/{total}] {clip_info.get('clip_id', 'unknown')}")

clip_results = generator.generate_multiple_clips(
    segments=results['clips'][:5],  # Top 5 clips
    output_dir=output_dir / "clips",
    padding=0.5,
    progress_callback=progress
)

print(f"✅ Generated {len(clip_results)} clips")
```

## Test Script

Test clip generation with the included test script:

```bash
cd engine

# Test with audio (creates test video)
python3 test_clip_generation.py ../IMG_2774_audio.mp3

# Test with video
python3 test_clip_generation.py path/to/video.mp4 output_dir

# Tests performed:
# 1. Video info extraction
# 2. Single clip generation
# 3. Fast clip generation (stream copy)
# 4. Thumbnail generation
# 5. Batch clip generation
# 6. Clip with metadata and thumbnail
```

## Test Results

All tests passed successfully:

```
======================================================================
TEST SUMMARY
======================================================================

✅ Passed: 6/6
❌ Failed: 0/6

Generated clips:
- test_clip_single.mp4 (11s, 0.1 MB)
- test_clip_fast.mp4 (10s, 0.13 MB)
- test_thumbnail.jpg (1.6 KB)
- clip_001.mp4 to clip_003.mp4 (batch)
- clip_meta.mp4 with metadata and thumbnail
```

## Performance

**Encoding Speeds (1080p video):**
- **Stream Copy (fast mode):** ~10-50x real-time
- **Re-encode (medium):** ~1-3x real-time
- **Re-encode (fast):** ~3-5x real-time
- **Re-encode (slow):** ~0.5-1x real-time

**Example:** Generating a 60-second clip from a 1080p video:
- Stream copy: ~2 seconds
- Medium preset: ~30 seconds
- Fast preset: ~15 seconds

**File Sizes (60s clip, 1080p):**
- CRF 18 (high quality): ~50-80 MB
- CRF 23 (balanced): ~25-40 MB
- CRF 28 (smaller): ~10-20 MB
- Stream copy: Depends on source bitrate

## Error Handling

The ClipGenerator handles errors gracefully:

```python
try:
    clip_info = generator.generate_clip(
        start_time=125.0,
        end_time=180.0,
        output_path=Path("clip.mp4")
    )
except FileNotFoundError:
    print("Video file not found")
except RuntimeError as e:
    print(f"FFmpeg error: {e}")
except ValueError as e:
    print(f"Invalid parameters: {e}")
```

Batch processing continues on error:

```python
results = generator.generate_multiple_clips(segments, output_dir)

# Check individual results
for result in results:
    if result.get('success'):
        print(f"✓ {result['clip_id']}")
    else:
        print(f"✗ {result['clip_id']}: {result['error']}")
```

## Padding

Add context before/after clips:

```python
# No padding (exact timing)
generator.generate_clip(..., padding=0.0)

# Small padding (0.5s before/after)
generator.generate_clip(..., padding=0.5)  # Default

# More padding (2s before/after)
generator.generate_clip(..., padding=2.0)
```

**Use cases:**
- **No padding (0s):** Precise timing, social media
- **Small padding (0.5s):** Natural transitions
- **More padding (2s+):** Extra context, storytelling

## Video Info

Extract detailed video metadata:

```python
info = generator.get_video_info()

# Available fields:
{
    'duration': 1245.5,        # seconds
    'size_bytes': 512000000,   # bytes
    'bitrate': 3280000,        # bits per second
    'width': 1920,             # pixels
    'height': 1080,            # pixels
    'video_codec': 'h264',     # codec name
    'audio_codec': 'aac',      # codec name
    'fps': 30.0,               # frames per second
    'has_audio': True          # bool
}
```

## Requirements

- **FFmpeg:** Must be installed and in PATH
- **Python:** 3.9+
- **Storage:** Adequate space for output clips

Install FFmpeg:
- **macOS:** `brew install ffmpeg`
- **Ubuntu:** `sudo apt install ffmpeg`
- **Windows:** Download from https://ffmpeg.org/download.html

## Troubleshooting

**"FFmpeg is not installed"**
- Install FFmpeg and ensure it's in PATH
- Test: `ffmpeg -version`

**"Video file not found"**
- Check file path is correct
- Use absolute paths

**"FFmpeg failed to generate clip"**
- Check start/end times are within video duration
- Verify video file is not corrupted
- Check disk space

**Clips are imprecise with fast mode**
- Use regular mode (re-encoding) for precise timing
- Fast mode seeks to keyframes only

**Large file sizes**
- Lower CRF value (try 28 instead of 23)
- Use slower preset for better compression
- Check source video bitrate

## Best Practices

1. **Use re-encoding for precision** - Critical for social media timing
2. **Use fast mode for previews** - Quick generation during development
3. **Add small padding** - Improves clip flow and transitions
4. **Generate thumbnails** - Helpful for review and selection
5. **Save metadata** - Track scores and clip details
6. **Batch process** - More efficient than one-by-one
7. **Monitor disk space** - Clips can add up quickly
8. **Choose appropriate CRF** - Balance quality vs. file size

## Advanced: Custom Encoding

```python
# H.265/HEVC (smaller files, slower encoding)
clip_info = generator.generate_clip(
    ...,
    codec="libx265",
    crf=28,
    preset="slow"
)

# VP9 (WebM, good for web)
clip_info = generator.generate_clip(
    ...,
    codec="libvpx-vp9",
    crf=31,
    preset="medium"
)

# Custom audio
clip_info = generator.generate_clip(
    ...,
    audio_codec="libopus",  # Opus audio
    # Audio bitrate set to 128k by default
)
```

## Next Steps

- ✅ Clip generation implemented
- ✅ Batch processing with progress tracking
- ✅ Metadata and thumbnail generation
- 🔄 Subtitle burning (coming soon)
- 🔄 Video filters and effects (future)
- 🔄 Multi-clip compilation (future)

## Files

**Implementation:**
- `engine/arena/clipping/generator.py` - ClipGenerator class (450+ lines)
- `engine/arena/clipping/__init__.py` - Module exports

**Tests:**
- `engine/test_clip_generation.py` - Comprehensive test suite

**Documentation:**
- `CLIP_GENERATION.md` - This document

## License

MIT
