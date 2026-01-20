# Arena CLI

> AI-powered video clip generation for the terminal - Turn long-form content into viral clips

[![npm version](https://badge.fury.io/js/%40arena%2Fcli.svg)](https://www.npmjs.com/package/@arena/cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Arena CLI is a professional video clip generation tool that uses AI to automatically identify and extract the best moments from your long-form content. Perfect for content creators, podcasters, and course producers who want to repurpose their content for social media.

## Features

✨ **AI-Powered Clip Detection** - Automatically finds the most engaging moments in your videos
🎯 **4-Layer Editorial System** - Professional-grade quality validation (optional)
⚡ **Hybrid Analysis** - Combines AI transcript analysis with audio energy detection
📐 **Multi-Platform Formatting** - Format clips for TikTok, Instagram, YouTube, LinkedIn (7 platforms)
💰 **Cost-Optimized** - Support for gpt-4o-mini ($0.20/video average)
🎬 **Social Media Ready** - Smart cropping, blur padding, aspect ratio conversion
🔧 **Flexible Workflow** - Analyze, review, and generate clips in separate steps
📝 **Whisper Transcription** - Accurate AI transcription powered by OpenAI

## Quick Start

```bash
# Install globally
npm install -g @arena/cli

# Interactive setup
arena init

# Set up your OpenAI API key
export OPENAI_API_KEY="sk-..."

# Process a video (all-in-one)
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini

# Or use the step-by-step workflow
arena transcribe video.mp4                  # Step 1: Transcribe
arena analyze video.mp4 --use-4layer        # Step 2: Analyze
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

Arena provides 8 commands for flexible video clip generation workflows:

| Command | Purpose | Use Case |
|---------|---------|----------|
| `arena init` | Interactive setup wizard | First-time setup, configure preferences |
| `arena process` | All-in-one processing | Quick results, single command |
| `arena transcribe` | Transcription only | Reuse transcripts, save costs |
| `arena analyze` | Find moments (no video) | Fast preview, review before generating |
| `arena generate` | Generate from analysis | Selective clip generation |
| `arena format` | Format for social platforms | TikTok, Instagram, YouTube formatting |
| `arena config` | Manage configuration | API keys, settings |
| `arena extract-audio` | Audio extraction | Audio-only workflows |

### `arena init`

Interactive setup wizard for first-time configuration.

```bash
arena init
```

Guides you through:
- Workflow type selection (content creator, podcast, course)
- Clip duration preferences
- Quality vs cost balance
- OpenAI API key setup

### `arena process <video>`

Process a video and generate clips automatically (all-in-one).

```bash
arena process video.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 5 \
  --min 30 \
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
- `--export-editorial-layers` - Export intermediate layer results for debugging

### `arena transcribe <video>`

Transcribe video audio only (saves time and money for multiple runs).

```bash
# Transcribe to default location
arena transcribe video.mp4

# Transcribe to specific file
arena transcribe video.mp4 -o transcript.json

# Force new transcription
arena transcribe video.mp4 --no-cache
```

**Why use this:** Transcribe once, reuse for multiple analysis runs with different parameters.

### `arena analyze <video>`

Analyze video and find moments without generating video files (fast preview).

```bash
# Analyze with 4-layer system
arena analyze video.mp4 --use-4layer -o moments.json

# Use existing transcript
arena analyze video.mp4 --transcript transcript.json -n 10

# Cost-optimized
arena analyze video.mp4 --use-4layer --editorial-model gpt-4o-mini
```

**Options:**
- `-o, --output <file>` - Output analysis path (default: `analysis.json`)
- `-n, --num-clips <number>` - Number of clips to find (default: `5`)
- `--min <seconds>` - Minimum clip duration (default: `30`)
- `--max <seconds>` - Maximum clip duration (default: `90`)
- `--use-4layer` - Use 4-layer editorial system
- `--editorial-model <model>` - Use `gpt-4o` or `gpt-4o-mini`
- `--transcript <file>` - Use existing transcript

**Why use this:** Fast, cheap preview of what Arena would create. Review before generating videos.

### `arena generate <video> <analysis>`

Generate video clips from existing analysis JSON.

```bash
# Generate all clips
arena generate video.mp4 moments.json -o clips/

# Generate only selected clips
arena generate video.mp4 moments.json --select 1,3,5

# Fast mode with stream copy
arena generate video.mp4 moments.json --fast
```

**Options:**
- `-o, --output <dir>` - Output directory for clips (default: `output/clips`)
- `--select <1,3,5>` - Generate only specific clips by index
- `--fast` - Fast mode with stream copy (10x faster)
- `--padding <seconds>` - Padding before/after clips (default: `0.5`)

**Why use this:** Generate only the clips you want after reviewing analysis.

### `arena format <input>`

Format clips for specific social media platforms with optimal specs.

```bash
# Format single clip for TikTok
arena format clip.mp4 -p tiktok -o tiktok/

# Batch format directory for Instagram Reels
arena format clips/ -p instagram-reels --crop smart -o reels/

# Format for YouTube with blur padding
arena format video.mp4 -p youtube --pad blur -o youtube/
```

**Options:**
- `-p, --platform <platform>` - Target platform (required):
  - `tiktok` - 1080×1920 (9:16), max 180s, 287MB
  - `instagram-reels` - 1080×1920 (9:16), max 90s, 100MB
  - `youtube-shorts` - 1080×1920 (9:16), max 60s, 100MB
  - `youtube` - 1920×1080 (16:9), unlimited duration
  - `instagram-feed` - 1080×1080 (1:1), max 60s, 100MB
  - `twitter` - 1280×720 (16:9), max 140s, 512MB
  - `linkedin` - 1920×1080 (16:9), max 600s, 5GB
- `-o, --output <dir>` - Output directory for formatted clips
- `--crop <strategy>` - Crop strategy: `center`, `smart`, `top`, `bottom` (default: `center`)
- `--pad <strategy>` - Pad strategy: `blur`, `black`, `white`, `color` (default: `blur`)
- `--pad-color <color>` - Padding color in hex (default: `#000000`)
- `--no-quality` - Disable high quality encoding (faster, smaller files)

**Why use this:** Automatically convert clips to platform-optimal specs with smart cropping and padding.

### `arena extract-audio <video>`

Extract audio from video in various formats.

```bash
# Extract to MP3
arena extract-audio video.mp4

# Extract to WAV for processing
arena extract-audio video.mp4 --format wav --bitrate 320k

# Mono for speech processing
arena extract-audio video.mp4 --mono --format mp3
```

**Options:**
- `-o, --output <file>` - Output audio path
- `--format <mp3|wav|aac|flac>` - Audio format (default: `mp3`)
- `--bitrate <rate>` - Audio bitrate (default: `192k`)
- `--sample-rate <rate>` - Sample rate in Hz
- `--mono` - Convert to mono

### `arena config`

View and manage Arena configuration.

```bash
# View all config
arena config

# Set API key
arena config set openai_api_key "sk-..."

# Get specific value
arena config get whisper_mode

# Reset to defaults
arena config reset
```

## Workflows

### Workflow 1: Quick Start (All-in-One)

Best for beginners or single videos.

```bash
# All-in-one command
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 5
```

**Cost:** ~$0.20 | **Time:** 5-8 minutes

### Workflow 2: Review-Before-Generate (Recommended)

Cost-optimized workflow with manual review.

```bash
# Step 1: Analyze without generating (fast, cheap)
arena analyze video.mp4 --use-4layer -n 10 -o moments.json

# Step 2: Review moments.json
cat moments.json | jq '.clips[] | {id, title, duration, standalone_score}'

# Step 3: Generate only the best clips
arena generate video.mp4 moments.json --select 1,3,5,7
```

**Benefits:** Review quality before generating, save processing time, generate only best clips.

### Workflow 3: Reuse Transcript (Multiple Iterations)

Transcribe once, experiment with different parameters.

```bash
# Step 1: Transcribe once
arena transcribe video.mp4 -o transcript.json

# Step 2: Try different parameters (reuses transcript)
arena analyze video.mp4 --transcript transcript.json -n 5 --min 30 --max 60
arena analyze video.mp4 --transcript transcript.json -n 10 --min 15 --max 45

# Step 3: Generate from best analysis
arena generate video.mp4 best-moments.json --select 1,2,3
```

**Saves:** Transcription costs and time on subsequent runs.

### Workflow 4: Content Creator (TikTok, Instagram Reels)

Optimized for short-form social media content.

```bash
# Short clips for social media
arena process video.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 3 \
  --min 15 \
  --max 30 \
  --fast
```

**Output:** 15-30 second viral-ready clips.

### Workflow 5: Podcast Highlights

Extract best moments from long-form podcast episodes.

```bash
# Longer clips for podcast highlights
arena process podcast-episode.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 8 \
  --min 60 \
  --max 120
```

**Output:** 60-120 second story-focused clips.

### Workflow 6: Course Creator

Extract educational snippets from lectures or tutorials.

```bash
# Educational content
arena process lecture.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 8 \
  --min 45 \
  --max 90
```

**Output:** 45-90 second teaching moments.

### Workflow 7: Multi-Platform Distribution

Generate clips once, format for every platform.

```bash
# Step 1: Generate high-quality clips
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 5

# Step 2: Format for each platform
arena format output/clips/ -p tiktok --crop smart -o social/tiktok/
arena format output/clips/ -p instagram-reels --crop smart -o social/reels/
arena format output/clips/ -p youtube-shorts --crop smart -o social/shorts/
arena format output/clips/ -p youtube -o social/youtube/
arena format output/clips/ -p instagram-feed --crop center -o social/feed/
```

**Result:** 1 video → 5 clips → 5 platforms = 25 optimized videos!

### Workflow 8: Batch Processing

Process multiple videos efficiently.

```bash
# Process all videos in a directory
for video in videos/*.mp4; do
  echo "Processing: $video"
  arena process "$video" \
    --use-4layer \
    --editorial-model gpt-4o-mini \
    -n 5 \
    -o "output/$(basename $video .mp4)"
done
```

**Note:** Rate limits are handled automatically!

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

### "Command not found: arena"

```bash
# Reinstall globally
npm install -g @arena/cli

# Or use npx
npx @arena/cli process video.mp4

# Verify installation
which arena
arena --version
```

### "Python not found"

```bash
# macOS
brew install python3

# Ubuntu
sudo apt install python3

# Verify installation
python3 --version  # Should be 3.9+
```

### "FFmpeg not found"

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Verify installation
ffmpeg -version
```

### "API key not set"

```bash
# Set via environment variable
export OPENAI_API_KEY="sk-..."

# Or set via config
arena config set openai_api_key "sk-..."

# Verify it's set
arena config get openai_api_key
```

### "No clips generated" or "No clips passed validation"

Common with 4-layer mode when duration constraints are too strict.

**Solutions:**
```bash
# Option 1: Relax duration constraints
arena process video.mp4 --use-4layer --min 20 --max 90

# Option 2: Analyze first to see what was found
arena analyze video.mp4 --use-4layer --export-editorial-layers
cat output/editorial_layers/layer3_validated.json | jq '.[] | {verdict, rejection_reason}'

# Option 3: Use standard mode for experimentation
arena process video.mp4 -n 10
```

**Common rejection reasons:**
- Duration constraints too strict
- Content has lots of context references
- Incomplete thoughts in the time range

### Rate Limit Errors (429)

**Good news:** Rate limits are now handled automatically!

Arena includes intelligent retry logic:
- Automatically retries on rate limit errors
- Parses suggested wait time from OpenAI
- Shows progress: "⏳ Rate limit hit. Waiting 2.5s..."
- Up to 5 retries per API call

**You don't need to do anything** - just watch the progress!

If you're consistently hitting rate limits during batch processing, add delays:
```bash
for video in videos/*.mp4; do
  arena process "$video" --use-4layer -n 5
  sleep 30  # Wait between videos
done
```

### "Video too large" or "Out of memory"

```bash
# Option 1: Generate fewer clips
arena process large-video.mp4 -n 3

# Option 2: Use step-by-step workflow
arena analyze large-video.mp4 -n 5
arena generate large-video.mp4 analysis.json --select 1,2,3
```

### 4-Layer too expensive

```bash
# Option 1: Use gpt-4o-mini (60% cheaper, same quality)
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini

# Option 2: Generate fewer clips
arena process video.mp4 --use-4layer -n 3

# Option 3: Analyze first, generate selectively
arena analyze video.mp4 --use-4layer -n 10 -o moments.json
arena generate video.mp4 moments.json --select 1,3,5
```

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

Contributions are welcome! Please see the [GitHub repository](https://github.com/iamwhitegod/arena) for details.

## License

MIT © Arena Contributors

## Links

- **GitHub**: https://github.com/iamwhitegod/arena
- **Issues**: https://github.com/iamwhitegod/arena/issues
- **npm**: https://www.npmjs.com/package/@arena/cli

---

**Made with ❤️ for content creators**
