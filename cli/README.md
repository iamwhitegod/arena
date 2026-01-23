# Arena CLI

**AI-powered video clip generation for the terminal**

[![npm version](https://badge.fury.io/js/@whitegodkingsley/arena-cli.svg)](https://www.npmjs.com/package/@whitegodkingsley/arena-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Node.js](https://img.shields.io/badge/node-%3E%3D18.0.0-brightgreen.svg)](https://nodejs.org/)

Arena automatically identifies and extracts the best moments from long-form video content using AI. Transform podcasts, lectures, and streams into viral-ready clips optimized for TikTok, Instagram Reels, YouTube Shorts, and more.

## Quick Start

```bash
# Install
npm install -g @whitegodkingsley/arena-cli

# Set up dependencies (Python, FFmpeg, packages)
arena setup

# Set API key
export OPENAI_API_KEY="sk-..."

# Generate clips
arena process video.mp4 -p tiktok --use-4layer
```

Your clips are ready in `output/formatted/`

## Features

- **AI Analysis** - Automatically finds engaging moments using GPT-4o/GPT-4o-mini
- **4-Layer Quality System** - Professional editorial validation (optional)
- **Multi-Platform** - Format for 7 platforms (TikTok, Instagram, YouTube, LinkedIn, Twitter)
- **Scene Detection** - Align cuts to visual transitions
- **Hybrid Detection** - Combines transcript analysis with audio energy
- **Cost-Optimized** - ~$0.20/video with gpt-4o-mini
- **Flexible Workflow** - Analyze, review, and generate separately
- **Universal Install** - Works on Windows, macOS, Linux with auto-setup

## Installation

### Automated Setup

```bash
npm install -g @whitegodkingsley/arena-cli
arena setup
```

The `setup` command automatically:
- Detects your OS and package manager
- Installs Python 3.9+ and FFmpeg if missing
- Installs required Python packages
- Verifies everything works

### Manual Setup

**Prerequisites:** Node.js 18+, Python 3.9+, FFmpeg

**macOS:**
```bash
brew install python3 ffmpeg
pip3 install openai-whisper openai ffmpeg-python torch numpy scipy
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install python3 python3-pip ffmpeg
pip3 install openai-whisper openai ffmpeg-python torch numpy scipy
```

**Windows:**
```bash
winget install Python.Python.3.11 Gyan.FFmpeg
pip3 install openai-whisper openai ffmpeg-python torch numpy scipy
```

## Commands

| Command | Description |
|---------|-------------|
| `arena setup` | Check and install dependencies |
| `arena init` | Interactive configuration wizard |
| `arena process` | All-in-one: analyze + generate clips |
| `arena analyze` | Find moments without generating video |
| `arena generate` | Generate clips from analysis |
| `arena transcribe` | Extract transcript only |
| `arena format` | Format clips for social platforms |
| `arena detect-scenes` | Find scene boundaries |
| `arena config` | Manage settings |
| `arena extract-audio` | Extract audio tracks |

## Usage Examples

### Basic Processing

```bash
# Generate 5 clips with default settings
arena process video.mp4

# High quality with 4-layer system
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini

# Auto-format for TikTok
arena process video.mp4 -p tiktok -n 3 --min 15 --max 30
```

### Review-Before-Generate Workflow

```bash
# Step 1: Analyze (fast, cheap)
arena analyze video.mp4 --use-4layer -n 10 -o moments.json

# Step 2: Review moments.json

# Step 3: Generate only selected clips
arena generate video.mp4 moments.json --select 1,3,5
```

### Multi-Platform Distribution

```bash
# Generate clips once
arena process video.mp4 --use-4layer -n 5

# Format for each platform
arena format output/clips/ -p tiktok -o social/tiktok/
arena format output/clips/ -p instagram-reels -o social/reels/
arena format output/clips/ -p youtube-shorts -o social/shorts/
```

## Platform Formats

| Platform | Resolution | Aspect Ratio | Max Duration |
|----------|-----------|--------------|--------------|
| TikTok | 1080×1920 | 9:16 | 180s |
| Instagram Reels | 1080×1920 | 9:16 | 90s |
| YouTube Shorts | 1080×1920 | 9:16 | 60s |
| YouTube | 1920×1080 | 16:9 | Unlimited |
| Instagram Feed | 1080×1080 | 1:1 | 60s |
| Twitter/X | 1280×720 | 16:9 | 140s |
| LinkedIn | 1920×1080 | 16:9 | 600s |

## Configuration

### Set API Key

```bash
# Environment variable (recommended)
export OPENAI_API_KEY="sk-..."

# Or via config
arena config set openai_api_key "sk-..."
```

### Interactive Setup

```bash
arena init
```

Choose workflow type, clip preferences, and quality settings.

### Config File

Located at `~/.arena/config.json`:

```json
{
  "openai_api_key": "sk-...",
  "whisper_mode": "api",
  "clip_duration": [30, 90],
  "output_format": "mp4"
}
```

## 4-Layer Editorial System

Enable professional quality filtering with `--use-4layer`:

1. **Candidate Detection** - Find potential moments
2. **Boundary Refinement** - Adjust cut points
3. **Quality Validation** - Check coherence and completeness
4. **Content Scoring** - Rate entertainment value

**Trade-offs:**
- Higher quality (7-10% pass rate vs 50%)
- More cost (~$0.20 vs $0.05 per video with gpt-4o-mini)
- Longer processing time

**Recommended:**
```bash
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini
```

## Common Options

```bash
# Clip generation
-n, --num-clips <number>     Number of clips (default: 5)
--min <seconds>              Minimum duration (default: 30)
--max <seconds>              Maximum duration (default: 90)

# Quality
--use-4layer                 Enable 4-layer system
--editorial-model <model>    Use gpt-4o or gpt-4o-mini (default: gpt-4o)

# Platform formatting
-p, --platform <platform>    Auto-format for platform
--crop <strategy>            Crop: center, smart, top, bottom
--pad <strategy>             Pad: blur, black, white, color

# Performance
--fast                       Stream copy mode (10x faster)
--no-cache                   Force re-transcription

# Debugging
--debug                      Show debug information
--export-layers              Export intermediate layer results
```

## Troubleshooting

### No clips generated

4-layer mode has strict quality filtering. Try:

```bash
# Relax duration constraints
arena process video.mp4 --use-4layer --min 20 --max 120

# Analyze first to see what was found
arena analyze video.mp4 --use-4layer --export-layers

# Use standard mode for testing
arena process video.mp4 -n 10
```

### Dependencies not found

```bash
# Auto-install everything
arena setup

# Or manually check
python3 --version  # Should be 3.9+
ffmpeg -version
pip3 list | grep whisper
```

### API key issues

```bash
# Verify key is set
echo $OPENAI_API_KEY

# Or set via config
arena config set openai_api_key "sk-..."
```

### Rate limits

Arena automatically handles rate limits with intelligent retry logic. If you're batch processing, add delays:

```bash
for video in videos/*.mp4; do
  arena process "$video" --use-4layer
  sleep 30
done
```

## Cost Estimation

Typical costs per 10-minute video:

| Mode | Model | Cost |
|------|-------|------|
| Standard | gpt-4o-mini | $0.05 |
| 4-Layer | gpt-4o-mini | $0.20 |
| 4-Layer | gpt-4o | $0.50 |

**Tips:**
- Use `gpt-4o-mini` for cost-effective quality
- Analyze first, generate selectively
- Reuse transcripts for multiple runs

## Documentation

- [Full Documentation](https://github.com/iamwhitegod/arena#readme)
- [Command Reference](https://github.com/iamwhitegod/arena/blob/main/docs/CLI_REFERENCE.md)
- [Troubleshooting Guide](https://github.com/iamwhitegod/arena/blob/main/docs/TROUBLESHOOTING.md)
- [Examples](https://github.com/iamwhitegod/arena/tree/main/examples)

## Requirements

- **Node.js** 18+
- **Python** 3.9+
- **FFmpeg** 4.0+
- **OpenAI API Key** ([Get one](https://platform.openai.com/api-keys))

**Supported OS:** macOS, Linux, Windows

## Contributing

Contributions welcome! See our [GitHub repository](https://github.com/iamwhitegod/arena) for guidelines.

## License

MIT © Arena Contributors

---

**Get your API key:** https://platform.openai.com/api-keys
**Report issues:** https://github.com/iamwhitegod/arena/issues
**npm package:** https://www.npmjs.com/package/@whitegodkingsley/arena-cli
