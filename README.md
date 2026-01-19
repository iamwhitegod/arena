# Arena

AI-powered video clip generation tool that runs in your terminal. Create engaging short clips from long-form content automatically.

## What is Arena?

Arena helps developers, indie founders, technical content creators, DevRels, and startup engineers transform their long-form videos into shareable short clips - without spending hours in video editing software.

## Features

- **Hybrid AI + Energy Analysis**: Combines AI content analysis with audio energy detection to find clips with great content AND enthusiastic delivery
- **Auto-clip generation**: Automatically identify and extract interesting segments from your videos
- **AI-powered audio enhancement**: Professional sound quality with noise removal and volume normalization (Adobe Podcast-style)
- **Multi-modal analysis**: Combines AI transcript analysis, audio energy detection, and visual scene detection
- **Smart subtitles**: Generate and burn stylized subtitles automatically
- **Terminal-native**: Fast, efficient, and scriptable workflow
- **Flexible output**: Get raw clips, subtitled versions, thumbnails, and metadata JSON

## Quick Start

Arena uses a git-style CLI with simple commands:

### Option 1: Quick Demo (No API Key Needed)

```bash
cd engine
./arena-cli demo
```

Generates 3 sample clips from existing test data in seconds!

### Option 2: Process Your Own Video

```bash
cd engine

# Set your OpenAI API key
export OPENAI_API_KEY="sk-your-key-here"

# Process video - generates 5 clips automatically
./arena-cli process path/to/your/video.mp4

# Generate 10 short clips for social media
./arena-cli process video.mp4 -n 10 --min 15 --max 30 --fast
```

See [CLI_REFERENCE.md](./CLI_REFERENCE.md) for all commands and [QUICKSTART.md](./QUICKSTART.md) for detailed instructions.

### All Commands

```bash
arena demo              # Run demo (no API key needed)
arena process <video>   # Full pipeline
arena extract-audio <video> # Extract audio from video
arena transcribe <video> # Transcribe only
arena analyze <video>   # Analyze only
arena generate <video> <analysis> # Generate clips
arena info <video>      # Show video info
```

## Installation

```bash
# Clone repository
git clone <repository-url>
cd arena/engine

# Install Python dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x arena-cli

# Test it works
./arena-cli --help
```

**Optional:** Create global symlink:

```bash
sudo ln -s $(pwd)/arena-cli /usr/local/bin/arena

# Then use from anywhere
arena demo
arena process video.mp4
```

## How It Works

Arena uses a hybrid Python + Node.js architecture:

1. **CLI Layer (Node.js)**: Beautiful terminal interface with progress indicators
2. **Processing Engine (Python)**: Heavy lifting for AI, video, and audio processing
3. **Multi-modal Detection**:
   - AI analyzes transcripts for engaging content
   - Audio analysis detects speaker energy and enthusiasm
   - Computer vision identifies scene changes and visual interest

## Requirements

- Node.js 18+
- Python 3.9+
- FFmpeg installed on your system
- OpenAI API key (for transcription and analysis)

## Project Status

**Sprint 4 Complete - Clip Generation!** Arena can now:
- ✅ Transcribe videos with OpenAI Whisper (API or local)
- ✅ AI-powered audio enhancement (noise removal, volume normalization)
- ✅ Audio energy detection (detect speaker enthusiasm and emphasis)
- ✅ Hybrid AI + Energy analysis (combines content quality with delivery energy)
- ✅ **NEW: Video clip generation** (FFmpeg-based extraction with metadata)
- ✅ **NEW: Thumbnail generation** (extract preview images at any timestamp)
- ✅ **NEW: Batch processing** (generate multiple clips efficiently)
- ✅ Analyze transcripts with GPT-4 to identify interesting segments
- ✅ Score and rank clips by engagement potential
- ✅ Cache transcripts and enhanced audio for cost/time savings

**Coming Soon (Sprint 5+):**
- Scene change detection
- Subtitle burning with customizable styles
- Interactive review mode in CLI
- Adobe Podcast API integration
- CLI command for end-to-end processing

See [SPRINT2.md](./SPRINT2.md) for sprint details, [AUDIO_ENHANCEMENT_QUICKSTART.md](./AUDIO_ENHANCEMENT_QUICKSTART.md) for audio enhancement, [AUDIO_ENERGY_DETECTION.md](./AUDIO_ENERGY_DETECTION.md) for energy detection, [HYBRID_ANALYSIS.md](./HYBRID_ANALYSIS.md) for hybrid analysis, and [CLIP_GENERATION.md](./CLIP_GENERATION.md) for clip generation.

## License

MIT
