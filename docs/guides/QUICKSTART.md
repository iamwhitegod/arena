# Arena Quick Start Guide

Get started with Arena in 5 minutes!

## Prerequisites

1. **Python 3.9+** installed
2. **FFmpeg** installed (`brew install ffmpeg` on macOS)
3. **OpenAI API Key** (get from https://platform.openai.com/api-keys)

## Installation

```bash
cd engine

# Install Python dependencies
pip install -r requirements.txt

# Set your OpenAI API key
export OPENAI_API_KEY="sk-your-key-here"
```

## Option 1: Quick Demo (No API Key Needed)

Run the demo with existing test data:

```bash
cd engine
python3 arena_process_demo.py
```

This will:
- ✅ Use existing test audio (no API calls)
- ✅ Generate 3 sample clips
- ✅ Show you how everything works
- ✅ Output to `demo_output/clips/`

**Output:**
```
demo_output/
├── clips/
│   ├── clip_001.mp4
│   ├── clip_001_thumb.jpg
│   ├── clip_001_metadata.json
│   ├── clip_002.mp4
│   └── ...
└── analysis_results.json
```

## Option 2: Process Your Own Video

### Basic Usage

```bash
cd engine

# Set API key (required)
export OPENAI_API_KEY="sk-your-key-here"

# Process video - generates 5 clips (30-90s each)
python3 arena_process.py path/to/your/video.mp4
```

### Custom Options

```bash
# Generate 10 shorter clips (20-60s each)
python3 arena_process.py video.mp4 -n 10 --min 20 --max 60

# Custom output directory
python3 arena_process.py video.mp4 -o my_clips

# Fast mode (10x faster, no re-encoding)
python3 arena_process.py video.mp4 --fast

# More padding around clips
python3 arena_process.py video.mp4 --padding 2.0
```

### Full Options

```bash
python3 arena_process.py --help

Options:
  -o, --output DIR      Output directory (default: output)
  -n, --num-clips N     Number of clips (default: 5)
  --min SECONDS         Minimum clip duration (default: 30)
  --max SECONDS         Maximum clip duration (default: 90)
  --fast                Fast mode - stream copy (10x faster)
  --padding SECONDS     Padding before/after clips (default: 0.5)
  --no-cache            Force re-transcription
```

## What Happens During Processing

### Step 1: Transcription (2-5 min)
```
🎤 Transcribing video with OpenAI Whisper...
✓ Transcription complete
  Duration: 520.3s
  Words: 920
```

The transcript is **cached** - subsequent runs are instant!

### Step 2: Analysis (30-60 sec)
```
🧠 Analyzing transcript content with AI...
   ✓ Found 17 interesting content segments

⚡ Analyzing audio energy...
   ✓ Found 20 high-energy segments

🎯 Computing hybrid scores...
   ✓ Selected top 5 clips by hybrid score
```

Combines:
- **AI analysis** - identifies interesting content
- **Energy detection** - finds enthusiastic delivery
- **Hybrid scoring** - boosts clips with both

### Step 3: Clip Generation (varies)
```
🎬 Generating 5 clips (quality mode)...
   [1/5] ✓ clip_001 (43.5s, 8.2MB)
   [2/5] ✓ clip_002 (38.2s, 7.1MB)
   ...

📸 Generating thumbnails and metadata...
✓ Clip generation complete
```

- **Quality mode:** ~1-3x real-time (30s for 60s clip)
- **Fast mode:** ~10-50x real-time (2s for 60s clip)

## Output Structure

```
output/
├── clips/
│   ├── clip_001.mp4              # Video clip
│   ├── clip_001_thumb.jpg        # Thumbnail
│   ├── clip_001_metadata.json    # Full metadata
│   ├── clip_002.mp4
│   ├── clip_002_thumb.jpg
│   └── ...
├── analysis_results.json         # Complete analysis
└── .cache/
    └── video_transcript.json     # Cached transcript
```

## Understanding the Output

### Top Clips (Ranked by Hybrid Score)

```
🎯 Top 3 Clips Generated:

   1. clip_015.mp4
      Why most startups fail at product-market fit
      Time: 07:07 → 07:52
      Scores: AI=0.95, Hybrid=1.00

   2. clip_001.mp4
      Getting started with AI
      Time: 00:00 → 01:02
      Scores: AI=0.92, Hybrid=1.00

   3. clip_009.mp4
      The key to growth
      Time: 04:04 → 05:23
      Scores: AI=0.85, Hybrid=0.998
```

### Scores Explained

- **AI Score (0-1):** How interesting is the content?
  - Hook, insight, advice, story, etc.

- **Hybrid Score (0-1):** Content quality + delivery energy
  - Clips with high energy get boosted
  - Best clips have great content AND enthusiastic delivery

### Metadata JSON

```json
{
  "clip_id": "clip_001",
  "title": "Why most startups fail",
  "start_time": 125.5,
  "end_time": 168.3,
  "duration": 42.8,
  "size_mb": 8.08,
  "thumbnail": "clip_001_thumb.jpg",
  "scores": {
    "ai_score": 0.85,
    "hybrid_score": 0.92,
    "energy_score": 0.75
  }
}
```

## Examples by Use Case

### Short Social Media Clips (TikTok, Reels)

```bash
# Generate 10 short clips (15-30s)
python3 arena_process.py video.mp4 -n 10 --min 15 --max 30
```

### Medium Clips (YouTube Shorts)

```bash
# Generate 5 medium clips (30-60s)
python3 arena_process.py video.mp4 -n 5 --min 30 --max 60
```

### Longer Clips (LinkedIn, Twitter)

```bash
# Generate 3 longer clips (60-120s)
python3 arena_process.py video.mp4 -n 3 --min 60 --max 120
```

### Quick Preview (Fast Mode)

```bash
# Generate clips 10x faster (stream copy)
python3 arena_process.py video.mp4 --fast
```

## Common Issues

### "OPENAI_API_KEY not set"

```bash
# Set the key in your terminal
export OPENAI_API_KEY="sk-your-key-here"

# Or add to your shell profile (~/.zshrc or ~/.bashrc)
echo 'export OPENAI_API_KEY="sk-your-key-here"' >> ~/.zshrc
```

### "FFmpeg is not installed"

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Check installation
ffmpeg -version
```

### "Video file not found"

```bash
# Use absolute paths or relative from engine/ directory
python3 arena_process.py ../videos/my_video.mp4

# Or with full path
python3 arena_process.py /path/to/video.mp4
```

### Processing is slow

```bash
# Use fast mode (stream copy - 10x faster)
python3 arena_process.py video.mp4 --fast

# Transcription is cached - only slow on first run
# Use --no-cache to force re-transcription
```

### Out of disk space

Generated clips can be large. Each 60s clip @ 1080p ≈ 25-40 MB.

```bash
# Use fast mode for smaller files
python3 arena_process.py video.mp4 --fast

# Or generate fewer clips
python3 arena_process.py video.mp4 -n 3
```

## Advanced: Python API

Use Arena in your own scripts:

```python
from pathlib import Path
from arena.audio.transcriber import Transcriber
from arena.audio.energy import AudioEnergyAnalyzer
from arena.ai.analyzer import TranscriptAnalyzer
from arena.ai.hybrid import HybridAnalyzer
from arena.clipping.generator import ClipGenerator

# 1. Transcribe
transcriber = Transcriber(api_key="sk-...")
transcript = transcriber.transcribe(Path("video.mp4"))

# 2. Analyze
ai = TranscriptAnalyzer(api_key="sk-...")
energy = AudioEnergyAnalyzer(Path("video.mp4"))
hybrid = HybridAnalyzer(ai, energy)

results = hybrid.analyze_video(
    Path("video.mp4"),
    transcript,
    target_clips=5
)

# 3. Generate
generator = ClipGenerator(Path("video.mp4"))
clips = generator.generate_multiple_clips(
    segments=results['clips'],
    output_dir=Path("output/clips")
)

print(f"Generated {len(clips)} clips!")
```

## Next Steps

### Review Your Clips

Open the output directory and review the generated clips:

```bash
# View clips
open output/clips/

# Or on Linux
xdg-open output/clips/
```

### Adjust Parameters

Try different settings to find what works for your content:

- **More clips:** `-n 10` for more options
- **Shorter clips:** `--min 15 --max 30` for social media
- **Longer clips:** `--min 60 --max 120` for YouTube
- **More padding:** `--padding 2.0` for extra context
- **Fast mode:** `--fast` for quick iteration

### Check Analysis Results

View the complete analysis:

```bash
cat output/analysis_results.json | python3 -m json.tool
```

### Share on Social Media

Your clips are ready to upload:
- TikTok: 15-60s clips
- Instagram Reels: 15-90s clips
- YouTube Shorts: <60s clips
- Twitter/X: Up to 2:20 clips
- LinkedIn: Up to 10min clips

## Getting Help

- **Documentation:** Check the `.md` files in the project root
- **Examples:** See `test_*.py` files for code examples
- **Issues:** Report bugs at GitHub (when public)

## Summary

```bash
# 1. Quick demo (no API key)
python3 arena_process_demo.py

# 2. Process your video
export OPENAI_API_KEY="sk-..."
python3 arena_process.py your-video.mp4

# 3. Review output
open output/clips/

# 4. Share your clips!
```

That's it! You're ready to create engaging video clips with Arena. 🎬
