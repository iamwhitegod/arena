# Arena

AI-powered video editing tool that runs in your terminal. Create engaging short clips from long-form content automatically.

## What is Arena?

Arena helps developers, indie founders, technical content creators, DevRels, and startup engineers transform their long-form videos into shareable short clips - without spending hours in video editing software.

## Features

- **Auto-clip generation**: Automatically identify and extract interesting segments from your videos
- **AI-powered audio enhancement**: Professional sound quality with noise removal and volume normalization (Adobe Podcast-style)
- **Multi-modal analysis**: Combines AI transcript analysis, audio energy detection, and visual scene detection
- **Smart subtitles**: Generate and burn stylized subtitles automatically
- **Terminal-native**: Fast, efficient, and scriptable workflow
- **Flexible output**: Get raw clips, subtitled versions, thumbnails, and metadata JSON

## Quick Start

```bash
# Process a video and generate clips automatically
arena process video.mp4

# Or use the multi-step pipeline for more control
arena analyze video.mp4   # Analyze the video
arena review              # Review and select clips
arena generate            # Generate selected clips
```

## Installation

```bash
# Install globally via npm
npm install -g arena-cli

# Or use directly with npx
npx arena-cli process video.mp4
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

**Sprint 2 Complete + Audio Enhancement!** Arena can now:
- ✅ Transcribe videos with OpenAI Whisper (API or local)
- ✅ **NEW: AI-powered audio enhancement** (noise removal, volume normalization)
- ✅ Analyze transcripts with GPT-4 to identify interesting segments
- ✅ Score and rank clips by engagement potential
- ✅ Generate metadata with clip recommendations
- ✅ Cache transcripts and enhanced audio for cost/time savings

**Coming Soon (Sprint 3-5):**
- Audio energy detection
- Scene change detection
- Actual video clip generation
- Subtitle burning
- Interactive review mode
- Adobe Podcast API integration

See [SPRINT2.md](./SPRINT2.md) for details and [AUDIO_ENHANCEMENT_QUICKSTART.md](./AUDIO_ENHANCEMENT_QUICKSTART.md) for audio enhancement.

## License

MIT
