# Arena CLI

> AI-powered video editing for the terminal - Turn long-form content into viral clips

[![npm version](https://badge.fury.io/js/%40arena%2Fcli.svg)](https://www.npmjs.com/package/@arena/cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Arena CLI is a professional video editing tool that uses AI to automatically identify and extract the best moments from your long-form content. Perfect for content creators, podcasters, and course producers who want to repurpose their content for social media.

## Features

✨ **AI-Powered Clip Detection** - Automatically finds the most engaging moments in your videos
🎯 **4-Layer Editorial System** - Professional-grade quality validation (optional)
⚡ **Hybrid Analysis** - Combines AI transcript analysis with audio energy detection
💰 **Cost-Optimized** - Support for gpt-4o-mini ($0.20/video average)
🎬 **Social Media Ready** - Perfect for TikTok, YouTube Shorts, Instagram Reels
🔧 **Flexible Workflow** - Analyze, review, and generate clips in separate steps
📝 **Whisper Transcription** - Accurate AI transcription powered by OpenAI

## Quick Start

```bash
# Install globally
npm install -g @arena/cli

# Set up your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Process a video (all-in-one)
arena process video.mp4 --use-4layer

# Or use the step-by-step workflow
arena transcribe video.mp4          # Step 1: Transcribe
arena analyze video.mp4              # Step 2: Analyze
arena generate video.mp4 analysis.json --select 1,3,5  # Step 3: Generate
```

## Installation

### Prerequisites

- **Node.js** 18 or higher
- **Python 3.9+** (for video processing engine)
- **FFmpeg** (for video encoding)
- **OpenAI API Key** (for AI analysis)

### Install Arena CLI

```bash
npm install -g @arena/cli
```

### Setup

Run the interactive setup wizard:

```bash
arena init
```

This will guide you through:
- Choosing your workflow type (content creator, podcast, course)
- Setting clip duration preferences
- Configuring quality vs cost settings
- Setting your OpenAI API key

## Commands

### `arena process <video>`

Process a video and generate clips automatically (all-in-one).

```bash
arena process video.mp4 \\
  --use-4layer \\
  --editorial-model gpt-4o-mini \\
  -n 5 \\
  --min 30 \\
  --max 90
```

**Options:**
- `-o, --output <dir>` - Output directory (default: `output`)
- `-n, --num-clips <number>` - Target number of clips (default: `5`)
- `--min <seconds>` - Minimum clip duration (default: `30`)
- `--max <seconds>` - Maximum clip duration (default: `90`)
- `--use-4layer` - Use 4-layer editorial system for higher quality
- `--editorial-model <model>` - Use `gpt-4o` or `gpt-4o-mini` (default: `gpt-4o`)
- `--fast` - Fast mode with stream copy (10x faster, less precise cuts)
- `--no-cache` - Force re-transcription
- `--padding <seconds>` - Padding before/after clips (default: `0.5`)

### `arena transcribe <video>`

Transcribe video audio only.

```bash
arena transcribe video.mp4 -o transcript.json
```

### `arena analyze <video>`

Analyze video without generating clips (fast preview).

```bash
arena analyze video.mp4 -o moments.json --use-4layer
```

### `arena generate <video> <analysis>`

Generate clips from existing analysis.

```bash
# Generate all clips
arena generate video.mp4 moments.json -o clips/

# Generate only selected clips
arena generate video.mp4 moments.json --select 1,3,5
```

### `arena extract-audio <video>`

Extract audio from video in various formats.

```bash
arena extract-audio video.mp4 --format mp3 --bitrate 192k
```

### `arena config`

Manage Arena configuration.

```bash
# View current config
arena config

# Set a value
arena config set openai_api_key "sk-..."

# Get specific value
arena config get whisper_mode
```

## Workflows

### Content Creator Workflow (TikTok, Instagram Reels)

```bash
# Process for short-form content
arena process video.mp4 \\
  --use-4layer \\
  --editorial-model gpt-4o-mini \\
  -n 3 \\
  --min 15 \\
  --max 30
```

### Podcast Highlights Workflow

```bash
# Step 1: Analyze without generating (fast, cheap)
arena analyze podcast.mp4 -n 10 --min 60 --max 120

# Step 2: Review moments.json, pick favorites

# Step 3: Generate only selected clips
arena generate podcast.mp4 moments.json --select 2,5,7 --fast
```

### Course Creator Workflow

```bash
# Extract educational snippets
arena process lecture.mp4 \\
  -n 8 \\
  --min 45 \\
  --max 90 \\
  --use-4layer
```

## 4-Layer Editorial System

The optional 4-layer system applies professional editorial standards:

**Layer 1: Candidate Detection** - Finds potential moments using AI
**Layer 2: Boundary Refinement** - Adjusts start/end points for natural cuts
**Layer 3: Quality Validation** - Checks for coherence, completeness, standalone value
**Layer 4: Content Scoring** - Rates clips on hook, value, and entertainment

**Trade-offs:**
- Higher quality clips (7-10% pass rate vs 50%+ without)
- More API cost (~$0.50 vs $0.05 per video with gpt-4o)
- Use `gpt-4o-mini` to reduce cost to ~$0.20 per video

```bash
# High quality, balanced cost
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini

# Maximum quality
arena process video.mp4 --use-4layer --editorial-model gpt-4o
```

## Configuration

Global config is stored at `~/.arena/config.json`:

```json
{
  "openai_api_key": "sk-...",
  "whisper_mode": "api",
  "clip_duration": [30, 90],
  "output_format": "mp4"
}
```

## Cost Estimation

Typical costs per 10-minute video:

| Mode | Model | Cost |
|------|-------|------|
| Standard | gpt-4o-mini | $0.05 |
| 4-Layer | gpt-4o-mini | $0.20 |
| 4-Layer | gpt-4o | $0.50 |

**Tips to reduce costs:**
- Use `--no-cache` sparingly (transcription costs add up)
- Use `gpt-4o-mini` for Layer 1-2 analysis
- Analyze first, generate later (reuse analysis)

## Requirements

### System Requirements

- **OS**: macOS, Linux (Windows via WSL)
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 2GB free space for processing
- **FFmpeg**: Install via `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Ubuntu)

### API Requirements

- **OpenAI API Key** with access to:
  - Whisper API (for transcription)
  - GPT-4o or GPT-4o-mini (for analysis)

Get an API key at: https://platform.openai.com/api-keys

## Troubleshooting

### "Python not found"

```bash
# macOS
brew install python3

# Ubuntu
sudo apt install python3
```

### "FFmpeg not found"

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg
```

### "API key not set"

```bash
# Set via environment variable
export OPENAI_API_KEY="sk-..."

# Or set via config
arena config set openai_api_key "sk-..."
```

### "No clips generated"

Common causes:
1. Video too short (< 30 seconds)
2. No interesting moments detected
3. All clips failed quality validation (with 4-layer)

Solutions:
- Use longer videos (> 2 minutes)
- Lower min duration: `--min 15`
- Disable 4-layer temporarily
- Export layers to debug: `--export-layers`

## Examples

### Generate 3 viral clips from a podcast

```bash
arena process podcast.mp4 \\
  --use-4layer \\
  --editorial-model gpt-4o-mini \\
  -n 3 \\
  --min 30 \\
  --max 60
```

### Extract best moments for Instagram Reels

```bash
arena process video.mp4 \\
  -n 5 \\
  --min 15 \\
  --max 30 \\
  --fast
```

### Review before generating

```bash
# Analyze first (cheap)
arena analyze video.mp4 -o moments.json

# Review moments.json manually

# Generate only the best clips
arena generate video.mp4 moments.json --select 1,4,7
```

## Contributing

Contributions are welcome! Please see the [GitHub repository](https://github.com/YOUR_USERNAME/arena) for details.

## License

MIT © Arena Contributors

## Links

- **GitHub**: https://github.com/YOUR_USERNAME/arena
- **Issues**: https://github.com/YOUR_USERNAME/arena/issues
- **npm**: https://www.npmjs.com/package/@arena/cli

---

**Made with ❤️ for content creators**
