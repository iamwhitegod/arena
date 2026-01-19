# Arena CLI Reference

Complete reference for all Arena CLI commands and options.

## Quick Command Overview

| Command | Purpose | Example |
|---------|---------|---------|
| `arena init` | Interactive setup wizard | `arena init` |
| `arena process` | All-in-one processing | `arena process video.mp4 --use-4layer` |
| `arena transcribe` | Transcription only | `arena transcribe video.mp4` |
| `arena analyze` | Find moments (no video) | `arena analyze video.mp4 --use-4layer` |
| `arena generate` | Generate from analysis | `arena generate video.mp4 analysis.json` |
| `arena format` | Format for social platforms | `arena format clips/ -p tiktok` |
| `arena config` | Manage configuration | `arena config set openai_api_key "sk-..."` |
| `arena extract-audio` | Extract audio | `arena extract-audio video.mp4` |

---

## Command Details

### `arena init`

Interactive setup wizard for first-time configuration.

```bash
arena init
```

**What it does:**
- Guides through workflow type selection (content creator, podcast, course)
- Sets clip duration preferences
- Configures quality vs cost balance
- Helps set up OpenAI API key
- Creates global config at `~/.arena/config.json`

**No options** - fully interactive.

**Example:**
```bash
arena init
```

After running, you'll be guided through a series of questions to configure Arena for your workflow.

---

### `arena process`

Run the complete pipeline: transcribe → analyze → generate clips.

```bash
arena process <video> [options]
```

**Core Options:**
- `-o, --output <dir>` - Output directory (default: `output`)
- `-n, --num-clips <number>` - Target number of clips (default: `5`)
- `--min <seconds>` - Minimum clip duration (default: `30`)
- `--max <seconds>` - Maximum clip duration (default: `90`)
- `--fast` - Fast mode with stream copy (10x faster, less precise)
- `--padding <seconds>` - Padding before/after clips (default: `0.5`)
- `--no-cache` - Force re-transcription, ignore cached transcript
- `--debug` - Show debug information

**4-Layer Editorial System:**
- `--use-4layer` - Use 4-layer editorial system for professional quality
- `--editorial-model <model>` - Model for Layers 1-2: `gpt-4o` or `gpt-4o-mini` (default: `gpt-4o`)
- `--export-editorial-layers` - Export intermediate layer results for debugging

**Examples:**

```bash
# Standard mode - fast and cheap
arena process video.mp4

# 4-Layer mode - professional quality
arena process video.mp4 --use-4layer

# 4-Layer with cost optimization (recommended)
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini

# Generate 10 short clips for social media
arena process video.mp4 --use-4layer -n 10 --min 15 --max 30

# Fast mode for quick iteration
arena process video.mp4 --fast

# Custom output directory
arena process video.mp4 --use-4layer -o my_clips

# Debug mode - export all layer results
arena process video.mp4 --use-4layer --export-editorial-layers

# Production workflow
arena process podcast.mp4 \\
  --use-4layer \\
  --editorial-model gpt-4o-mini \\
  -n 8 \\
  --min 20 \\
  --max 60 \\
  -o podcast_clips
```

**4-Layer vs Standard Mode:**

| Feature | Standard | 4-Layer |
|---------|----------|---------|
| Quality | Good | Professional |
| Standalone context | Basic | Validated |
| Titles | AI-generated | Professional |
| Cost per 10min video | $0.05 | $0.20 (gpt-4o-mini) |
| Speed | 2-4 min | 5-8 min |
| Best for | Testing/iteration | Production |

---

### `arena transcribe`

Transcribe video audio only (no clip generation).

```bash
arena transcribe <video> [options]
```

**Options:**
- `-o, --output <file>` - Output transcript file path (default: auto-generated)
- `--no-cache` - Force re-transcription, ignore cached transcript
- `--debug` - Show debug information

**Examples:**
```bash
# Transcribe to default location
arena transcribe video.mp4

# Transcribe to specific file
arena transcribe video.mp4 -o transcript.json

# Force new transcription (ignore cache)
arena transcribe video.mp4 --no-cache
```

**Why use this:**
- Transcribe once, reuse for multiple analysis runs
- Save transcription costs when experimenting with different parameters
- Debug transcription quality

**Output format:**
```json
{
  "text": "Full transcript...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.5,
      "text": "First segment..."
    }
  ]
}
```

---

### `arena analyze`

Analyze video and find moments without generating video files (fast preview).

```bash
arena analyze <video> [options]
```

**Options:**
- `-o, --output <file>` - Output analysis file path (default: `analysis.json`)
- `-n, --num-clips <number>` - Target number of clips to analyze (default: `5`)
- `--min <seconds>` - Minimum clip duration (default: `30`)
- `--max <seconds>` - Maximum clip duration (default: `90`)
- `--use-4layer` - Use 4-layer editorial system
- `--editorial-model <model>` - Model for Layers 1-2: `gpt-4o` or `gpt-4o-mini` (default: `gpt-4o`)
- `--transcript <file>` - Use existing transcript file
- `--debug` - Show debug information

**Examples:**
```bash
# Analyze with 4-layer system
arena analyze video.mp4 --use-4layer -o moments.json

# Use existing transcript
arena analyze video.mp4 --transcript transcript.json -n 10

# Cost-optimized analysis
arena analyze video.mp4 --use-4layer --editorial-model gpt-4o-mini

# Find many candidates for review
arena analyze video.mp4 --use-4layer -n 20
```

**Why use this:**
- Fast, cheap preview of what Arena would create (~30 seconds vs 5-8 minutes)
- Review quality before generating videos
- Select best moments for generation
- Experiment with different parameters

**Workflow:**
```bash
# Step 1: Analyze
arena analyze video.mp4 --use-4layer -o moments.json

# Step 2: Review moments.json
cat moments.json | jq '.clips[] | {id, title, duration, standalone_score}'

# Step 3: Generate only selected clips
arena generate video.mp4 moments.json --select 1,3,5
```

---

### `arena generate`

Generate video clips from existing analysis JSON.

```bash
arena generate <video> <analysis> [options]
```

**Options:**
- `-o, --output <dir>` - Output directory for clips (default: `output/clips`)
- `-n, --num-clips <number>` - Number of clips to generate (overrides analysis)
- `--select <indices>` - Comma-separated clip indices to generate (e.g., `1,3,5`)
- `--fast` - Fast mode with stream copy (10x faster)
- `--padding <seconds>` - Padding before/after clips (default: `0.5`)
- `--debug` - Show debug information

**Examples:**
```bash
# Generate all clips from analysis
arena generate video.mp4 moments.json -o clips/

# Generate only selected clips
arena generate video.mp4 moments.json --select 1,3,5

# Fast mode with stream copy
arena generate video.mp4 moments.json --fast

# Custom output directory
arena generate video.mp4 moments.json -o best_clips/
```

**Why use this:**
- Generate only the clips you want after reviewing analysis
- Selective generation saves processing time
- Separate analysis from generation for flexibility

**Fast mode:**
- Uses stream copy (no re-encoding)
- 10x faster than normal mode
- Less precise cuts (may miss exact boundaries)
- Good for quick previews

---

### `arena format`

Format clips for specific social media platforms with optimal specs.

```bash
arena format <input> [options]
```

**Required Options:**
- `-p, --platform <platform>` - Target platform (required)

**Optional Options:**
- `-o, --output <dir>` - Output directory for formatted clips
- `--crop <strategy>` - Crop strategy: `center`, `smart`, `top`, `bottom` (default: `center`)
- `--pad <strategy>` - Pad strategy: `blur`, `black`, `white`, `color` (default: `blur`)
- `--pad-color <color>` - Padding color in hex format (default: `#000000`)
- `--no-quality` - Disable high quality encoding (faster, smaller files)

**Supported Platforms:**

| Platform | Resolution | Aspect Ratio | Max Duration | Max Size |
|----------|-----------|--------------|--------------|----------|
| `tiktok` | 1080×1920 | 9:16 | 180s | 287MB |
| `instagram-reels` | 1080×1920 | 9:16 | 90s | 100MB |
| `youtube-shorts` | 1080×1920 | 9:16 | 60s | 100MB |
| `youtube` | 1920×1080 | 16:9 | Unlimited | 256GB |
| `instagram-feed` | 1080×1080 | 1:1 | 60s | 100MB |
| `twitter` | 1280×720 | 16:9 | 140s | 512MB |
| `linkedin` | 1920×1080 | 16:9 | 600s | 5GB |

**Crop Strategies:**
- `center` - Center crop (default, safe choice)
- `smart` - Face-aware cropping (detects faces, keeps them in frame)
- `top` - Crop from top (good for talking heads)
- `bottom` - Crop from bottom (good for lower-third text)

**Pad Strategies:**
- `blur` - Blur background padding (professional look, default)
- `black` - Black bars (classic letterbox)
- `white` - White bars (bright, clean look)
- `color` - Custom color (specify with `--pad-color`)

**Examples:**

```bash
# Format single clip for TikTok
arena format clip.mp4 -p tiktok -o tiktok/

# Batch format directory for Instagram Reels
arena format clips/ -p instagram-reels --crop smart -o reels/

# Format for YouTube with blur padding
arena format video.mp4 -p youtube --pad blur -o youtube/

# Format with custom padding color
arena format clip.mp4 -p instagram-feed --pad color --pad-color "#FF5733" -o feed/

# Smart cropping for talking heads
arena format interview.mp4 -p tiktok --crop smart -o tiktok/

# Fast encoding (lower quality, smaller files)
arena format clip.mp4 -p instagram-reels --no-quality -o reels/
```

**Multi-Platform Workflow:**
```bash
# Generate clips once
arena process video.mp4 --use-4layer -n 5

# Format for every platform
arena format output/clips/ -p tiktok --crop smart -o social/tiktok/
arena format output/clips/ -p instagram-reels --crop smart -o social/reels/
arena format output/clips/ -p youtube-shorts --crop smart -o social/shorts/
arena format output/clips/ -p youtube -o social/youtube/
arena format output/clips/ -p instagram-feed --crop center -o social/feed/

# Result: 1 video → 5 clips → 5 platforms = 25 optimized videos!
```

**Features:**
- Automatic aspect ratio conversion
- Smart cropping strategies
- Blur background padding for professional look
- File size and duration validation
- Batch processing support
- Maintains high quality by default

---

### `arena config`

View and manage Arena configuration.

```bash
arena config [action] [key] [value]
```

**Actions:**
- No arguments - View all configuration
- `set <key> <value>` - Set configuration value
- `get <key>` - Get specific configuration value
- `reset` - Reset configuration to defaults

**Common Config Keys:**
- `openai_api_key` - Your OpenAI API key
- `whisper_mode` - Transcription mode: `api` or `local`
- `minDuration` - Default minimum clip duration
- `maxDuration` - Default maximum clip duration
- `use4Layer` - Enable 4-layer by default: `true` or `false`
- `editorialModel` - Default model: `gpt-4o` or `gpt-4o-mini`

**Examples:**
```bash
# View all config
arena config

# Set API key
arena config set openai_api_key "sk-..."

# Get specific value
arena config get whisper_mode

# Enable 4-layer by default
arena config set use4Layer true

# Set default model
arena config set editorialModel gpt-4o-mini

# Reset to defaults
arena config reset
```

**Config File Location:**
`~/.arena/config.json`

**Example config file:**
```json
{
  "openai_api_key": "sk-...",
  "whisper_mode": "api",
  "minDuration": 30,
  "maxDuration": 90,
  "use4Layer": true,
  "editorialModel": "gpt-4o-mini"
}
```

---

### `arena extract-audio`

Extract audio track from video file in various formats.

```bash
arena extract-audio <video> [options]
```

**Options:**
- `-o, --output <file>` - Output audio file path (default: auto-generated)
- `--format <format>` - Audio format: `mp3`, `wav`, `aac`, `flac` (default: `mp3`)
- `--bitrate <rate>` - Audio bitrate, e.g., `192k`, `320k` (default: `192k`)
- `--sample-rate <rate>` - Sample rate in Hz: `16000`, `44100`, `48000` (default: original)
- `--mono` - Convert to mono (single channel)
- `--debug` - Show debug information

**Examples:**
```bash
# Extract as MP3 (default)
arena extract-audio video.mp4

# Extract as WAV
arena extract-audio video.mp4 --format wav

# Extract as high-quality MP3
arena extract-audio video.mp4 --bitrate 320k

# Extract as mono WAV for speech (16kHz)
arena extract-audio video.mp4 --format wav --mono --sample-rate 16000

# Custom output file
arena extract-audio video.mp4 -o my_audio.mp3

# Extract as FLAC (lossless)
arena extract-audio video.mp4 --format flac
```

**Format Comparison:**

| Format | Size | Quality | Use Case |
|--------|------|---------|----------|
| MP3 | Small | Good | General purpose, podcasts |
| AAC | Small | Better | Modern devices, streaming |
| WAV | Large | Perfect | Editing, processing |
| FLAC | Medium | Perfect | Archival, lossless |

**Why use this:**
- Extract audio for separate processing
- Convert audio formats
- Prepare audio for custom analysis
- Create audio-only content

---

## Global Options

These options work with all commands:

- `--debug` - Show detailed debug information
- `--help` - Show help for specific command

**Examples:**
```bash
# Show help for specific command
arena process --help
arena format --help

# Run with debug output
arena process video.mp4 --debug
```

---

## Common Workflows

### Workflow 1: Quick Start
```bash
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 5
```

### Workflow 2: Review Before Generate
```bash
# Analyze
arena analyze video.mp4 --use-4layer -o moments.json

# Review moments.json

# Generate selected
arena generate video.mp4 moments.json --select 1,3,5
```

### Workflow 3: Multi-Platform Distribution
```bash
# Generate clips
arena process video.mp4 --use-4layer -n 5

# Format for platforms
arena format output/clips/ -p tiktok -o social/tiktok/
arena format output/clips/ -p instagram-reels -o social/reels/
arena format output/clips/ -p youtube -o social/youtube/
```

### Workflow 4: Reuse Transcript
```bash
# Transcribe once
arena transcribe video.mp4 -o transcript.json

# Try different parameters
arena analyze video.mp4 --transcript transcript.json -n 5 --min 30
arena analyze video.mp4 --transcript transcript.json -n 10 --min 15

# Generate from best
arena generate video.mp4 best-moments.json
```

---

## Cost Optimization Tips

1. **Use gpt-4o-mini** - 60% cheaper than gpt-4o, same quality
   ```bash
   arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini
   ```

2. **Analyze first** - Review before generating
   ```bash
   arena analyze video.mp4 --use-4layer -o moments.json
   arena generate video.mp4 moments.json --select 1,3,5
   ```

3. **Reuse transcripts** - Transcribe once, experiment many times
   ```bash
   arena transcribe video.mp4 -o transcript.json
   arena analyze video.mp4 --transcript transcript.json --min 30
   arena analyze video.mp4 --transcript transcript.json --min 15
   ```

4. **Use selective generation** - Only generate the best clips
   ```bash
   arena generate video.mp4 moments.json --select 1,3,5
   ```

---

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Invalid arguments
- `130` - Interrupted by user (Ctrl+C)

---

## Environment Variables

- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `ARENA_CONFIG_PATH` - Custom config file location (optional)

**Example:**
```bash
export OPENAI_API_KEY="sk-..."
arena process video.mp4
```

---

## For More Information

- **Usage Guide**: [USAGE.md](./USAGE.md)
- **Quick Start**: [QUICKSTART.md](./QUICKSTART.md)
- **Setup Guide**: [SETUP.md](./SETUP.md)
- **Troubleshooting**: [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- **Main README**: [../../README.md](../../README.md)
