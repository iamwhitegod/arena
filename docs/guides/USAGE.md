# Arena Usage Guide

Complete reference for using Arena CLI - all 7 commands and workflows.

## Installation

```bash
# Install globally via npm
npm install -g @arena/cli

# Set up your environment
export OPENAI_API_KEY="sk-..."

# Run interactive setup
arena init
```

## Available Commands

Arena CLI provides 7 commands for flexible video editing workflows:

| Command | Purpose | Best For |
|---------|---------|----------|
| `arena init` | Interactive setup wizard | First-time setup, changing preferences |
| `arena process` | All-in-one processing | Quick results, single command workflow |
| `arena transcribe` | Transcription only | Reusing transcripts, debugging |
| `arena analyze` | Find moments without generating clips | Fast preview, cost optimization |
| `arena generate` | Generate clips from analysis | Selective generation, review workflow |
| `arena config` | Manage configuration | API keys, preferences, debugging |
| `arena extract-audio` | Extract audio from video | Audio-only workflows, preprocessing |

## Basic Commands

### Quick Start (All-in-One)

```bash
arena process <video-file> [options]
```

## Options

### Core Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output <dir>` | Output directory | `.arena/output` |
| `-n, --num-clips <number>` | Target number of clips | `5` |
| `--min <seconds>` | Minimum clip duration | `30` |
| `--max <seconds>` | Maximum clip duration | `90` |
| `--no-cache` | Ignore cached transcript and re-transcribe | `false` |
| `--fast` | Use fast mode (stream copy, no re-encoding) | `false` |
| `--padding <seconds>` | Seconds of padding before/after clips | `0.5` |

### 4-Layer Editorial System (New!)

| Option | Description | Default |
|--------|-------------|---------|
| `--use-4layer` | Use 4-layer editorial system for higher quality clips | `false` |
| `--editorial-model` | Model for Layers 1-2: `gpt-4o` or `gpt-4o-mini` | `gpt-4o` |
| `--export-editorial-layers` | Export intermediate results for debugging | `false` |

**What is 4-Layer?**
The 4-layer editorial system uses a sophisticated AI pipeline for professional-quality clips:
- **Layer 1:** Detects interesting moments (25 candidates)
- **Layer 2:** Expands to complete thought boundaries (18 candidates)
- **Layer 3:** Validates standalone context - quality gate (12 pass)
- **Layer 4:** Packages with professional titles and metadata

**Trade-offs:**
- ✅ Higher quality (50%+ better clips)
- ✅ Better standalone context (no confusing references)
- ✅ Professional titles and descriptions
- ⚠️ ~4x cost (but only $0.10-0.50 per video)
- ⚠️ Slower (2-3x processing time)

## Command Reference

### `arena init` - Setup Wizard

Interactive setup wizard for first-time configuration.

```bash
arena init
```

**What it does:**
- Prompts for workflow type (content creator, podcast, course)
- Sets clip duration preferences
- Configures quality vs cost balance
- Sets up global config at `~/.arena/config.json`

**Example:**
```bash
$ arena init
✨ Welcome to Arena!

? Select your workflow: Content Creator (social media clips)
? Default clip duration: Short (15-30s) - TikTok, Instagram Reels
? Quality vs Cost: Balanced (4-layer + gpt-4o-mini, $0.20/video)

✓ Created ~/.arena/config.json
✓ Workspace ready!

💡 Try it now:
  arena process video.mp4
```

### `arena transcribe` - Transcription Only

Transcribe video without analysis or clip generation.

```bash
arena transcribe <video> [options]
```

**Options:**
- `-o, --output <file>` - Output transcript path (default: `transcript.json`)
- `--no-cache` - Force re-transcription

**Examples:**
```bash
# Transcribe video to default location
arena transcribe video.mp4

# Transcribe to specific file
arena transcribe video.mp4 -o my-transcript.json

# Force new transcription (ignore cache)
arena transcribe video.mp4 --no-cache
```

**Use Cases:**
- Pre-transcribe large videos once
- Debug transcription quality
- Reuse transcripts across multiple runs
- Extract transcript for other tools

### `arena analyze` - Find Moments Without Generating

Analyze video and identify clips without generating video files.

```bash
arena analyze <video> [options]
```

**Options:**
- `-o, --output <file>` - Output analysis path (default: `analysis.json`)
- `-n, --num-clips <number>` - Number of clips to analyze (default: `5`)
- `--min <seconds>` - Minimum clip duration (default: `30`)
- `--max <seconds>` - Maximum clip duration (default: `90`)
- `--use-4layer` - Use 4-layer editorial system
- `--editorial-model <model>` - Use `gpt-4o` or `gpt-4o-mini` (default: `gpt-4o`)
- `--transcript <file>` - Use existing transcript

**Examples:**
```bash
# Analyze and find 10 potential clips
arena analyze video.mp4 -n 10

# Use 4-layer system for analysis
arena analyze video.mp4 --use-4layer -o moments.json

# Analyze with existing transcript
arena analyze video.mp4 --transcript transcript.json

# Cost-optimized analysis
arena analyze video.mp4 --use-4layer --editorial-model gpt-4o-mini
```

**Why use this:**
- **Fast preview** - See what clips Arena would create (~$0.05-0.20)
- **Review first** - Check quality before generating videos
- **Selective generation** - Pick only the best clips to generate
- **Cost optimization** - Analyze many videos, generate only the best

### `arena generate` - Generate Clips from Analysis

Generate video clips from existing analysis JSON.

```bash
arena generate <video> <analysis> [options]
```

**Options:**
- `-o, --output <dir>` - Output directory for clips (default: `output/clips`)
- `--select <1,3,5>` - Generate only specific clips by index
- `--fast` - Fast mode with stream copy (10x faster)
- `--padding <seconds>` - Padding before/after clips (default: `0.5`)

**Examples:**
```bash
# Generate all clips from analysis
arena generate video.mp4 analysis.json

# Generate only clips 1, 3, and 5
arena generate video.mp4 analysis.json --select 1,3,5

# Fast generation with stream copy
arena generate video.mp4 analysis.json --fast

# Custom output directory
arena generate video.mp4 analysis.json -o ~/Desktop/clips
```

**Workflow:**
```bash
# Step 1: Analyze (fast, cheap)
arena analyze video.mp4 -o moments.json

# Step 2: Review moments.json, check titles and scores

# Step 3: Generate only the best clips
arena generate video.mp4 moments.json --select 1,3,5
```

### `arena config` - Configuration Management

View and manage Arena configuration.

```bash
arena config [action] [key] [value]
```

**Actions:**
- `arena config` - View current config
- `arena config set <key> <value>` - Set config value
- `arena config get <key>` - Get specific value
- `arena config reset` - Reset to defaults

**Examples:**
```bash
# View all config
arena config

# Set OpenAI API key
arena config set openai_api_key "sk-..."

# Get specific value
arena config get whisper_mode

# Reset to defaults
arena config reset
```

**Common config keys:**
- `openai_api_key` - OpenAI API key
- `whisper_mode` - Transcription mode (`api` or `local`)
- `clip_duration` - Default clip duration range `[30, 90]`
- `output_format` - Video output format (`mp4`)

### `arena extract-audio` - Audio Extraction

Extract audio from video in various formats.

```bash
arena extract-audio <video> [options]
```

**Options:**
- `-o, --output <file>` - Output audio path
- `--format <mp3|wav|aac|flac>` - Audio format (default: `mp3`)
- `--bitrate <rate>` - Audio bitrate (default: `192k`)
- `--sample-rate <rate>` - Sample rate in Hz
- `--mono` - Convert to mono

**Examples:**
```bash
# Extract to MP3 (default)
arena extract-audio video.mp4

# Extract to WAV for processing
arena extract-audio video.mp4 --format wav -o audio.wav

# High-quality extraction
arena extract-audio video.mp4 --bitrate 320k --format flac

# Mono for speech processing
arena extract-audio video.mp4 --mono --bitrate 128k
```

## Examples by Workflow

### Basic Usage (All-in-One)

```bash
# Process a video with defaults (standard mode)
arena process my-video.mp4

# Generate 10 clips instead of 5
arena process my-video.mp4 -n 10
```

### 4-Layer Editorial System (Recommended)

```bash
# Use 4-layer system for professional quality
arena process my-video.mp4 --use-4layer -n 5

# Cost optimization: Use gpt-4o-mini (saves ~60%)
arena process my-video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 5

# Debug mode: Export intermediate layer results
arena process my-video.mp4 --use-4layer --export-editorial-layers
```

### Custom Duration Constraints

```bash
# Short clips (15-45 seconds) - Great for quick tips
arena process my-video.mp4 --min 15 --max 45

# Medium clips (30-60 seconds) - Default for most content
arena process my-video.mp4 --min 30 --max 60

# Long clips (60-120 seconds) - For stories/interviews
arena process my-video.mp4 --min 60 --max 120
```

**Important:** The 4-layer system respects duration constraints strictly. If you get "No clips passed validation", try:
- Lowering `--min` (e.g., `--min 20` instead of 30)
- Raising `--max` (e.g., `--max 120` instead of 90)
- Checking if your video has complete thoughts that fit within constraints

### Custom Output Location

```bash
# Save to a specific directory
arena process my-video.mp4 -o ./my-clips
```

### Full Production Example

```bash
# Professional quality, optimized cost, custom durations
arena process ~/Videos/podcast-episode.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 8 \
  --min 20 \
  --max 60 \
  -o ~/Desktop/podcast-clips
```

### Step-by-Step Workflow (Review Before Generating)

```bash
# Step 1: Transcribe once (saves time and money)
arena transcribe video.mp4 -o transcript.json

# Step 2: Analyze with 4-layer (uses cached transcript)
arena analyze video.mp4 \
  --transcript transcript.json \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 10 \
  -o moments.json

# Step 3: Review moments.json
cat moments.json | jq '.clips[] | {id, title, duration, combined_score}'

# Step 4: Generate only the best clips
arena generate video.mp4 moments.json --select 1,3,5,7 -o best-clips/
```

### Batch Processing Multiple Videos

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

## Output Structure

After processing, you'll find:

```
.arena/
├── cache/
│   ├── transcript.json           # Cached transcript (reusable)
│   └── my-video_audio.mp3        # Extracted audio
│
├── config.json                    # Project configuration
│
└── output/
    ├── clips/                     # Video clips (Sprint 4+)
    ├── metadata.json              # Clip metadata with timestamps
    └── transcript.json            # Full transcript
```

## Understanding metadata.json

### Standard Mode

```json
{
  "source_video": "my-video.mp4",
  "duration": 3600,
  "clips": [
    {
      "id": "clip_001",
      "start_time": 125.3,
      "end_time": 168.7,
      "duration": 43.4,
      "title": "Why startups fail at PMF",
      "reason": "Strong hook with insight",
      "interest_score": 0.95,
      "content_type": "insight",
      "scores": {
        "ai_interest": 0.95,
        "audio_energy": 0.0,
        "visual_change": 0.0,
        "combined": 0.95
      }
    }
  ]
}
```

### 4-Layer Mode (Enhanced Metadata)

```json
{
  "source_video": "my-video.mp4",
  "duration": 3600,
  "clips": [
    {
      "id": "clip_001",
      "start_time": 125.3,
      "end_time": 168.7,
      "duration": 43.4,

      // Professional metadata from Layer 4
      "title": "Why Most Startups Miss Product-Market Fit",
      "description": "Learn the critical mistake that causes 90% of startups...",
      "hook": "Here's what nobody tells you about PMF...",
      "hashtags": ["#startups", "#pmf", "#entrepreneurship"],

      // Quality scores
      "interest_score": 0.89,        // How interesting (Layer 1)
      "standalone_score": 0.85,      // Can be understood without context (Layer 3)
      "combined_score": 0.87,        // Weighted: 60% interest + 40% standalone

      // Editorial metadata
      "content_type": "insight",
      "verdict": "PASS",             // Layer 3 quality gate result
      "editorial_notes": "Strong standalone clip with clear setup",

      // Layer information (if --export-editorial-layers)
      "layers": {
        "layer1_moment": {...},      // Original moment detection
        "layer2_thought": {...},     // Expanded thought boundaries
        "layer3_validation": {...},  // Standalone validation
        "layer4_package": {...}      // Final packaging
      }
    }
  ]
}
```

**Key Differences in 4-Layer Mode:**
- `standalone_score`: Ensures clips make sense without prior context
- `combined_score`: Balances interest (60%) and standalone quality (40%)
- `verdict`: Shows if clip passed quality gate (PASS/REVISE/REJECT)
- Professional metadata: Better titles, descriptions, hooks, hashtags

## Environment Variables

Set these in your shell or in `~/.arena/config.json`:

```bash
# Required
export OPENAI_API_KEY="sk-your-key-here"

# Optional
export ARENA_WHISPER_MODE="api"  # or "local"
```

## Configuration

### Global Config

Create `~/.arena/config.json`:

```json
{
  "openai_api_key": "sk-your-key-here",
  "whisper_mode": "api",
  "clip_duration": [30, 90],
  "output_format": "mp4",
  "subtitle_style": {
    "font": "Arial",
    "size": 24,
    "color": "white",
    "bg_color": "black",
    "position": "bottom"
  }
}
```

### Project Config

Auto-generated in `.arena/config.json`:

```json
{
  "video_path": "/path/to/video.mp4",
  "created_at": "2026-01-12T19:52:00Z",
  "preferences": {
    "clip_count": 10,
    "focus_topics": ["startups", "marketing"]
  }
}
```

## 4-Layer System Guide

### When to Use 4-Layer

**Use 4-Layer when:**
- You need professional-quality clips for distribution
- Standalone context matters (viewers clicking from feeds)
- You want better titles and descriptions
- Quality > cost is your priority

**Use Standard when:**
- You're experimenting/testing
- You need fast iteration
- Cost is primary concern
- You'll manually review all clips anyway

### Cost Optimization

```bash
# Most expensive: gpt-4o (~$0.50 per video)
python3 arena_process.py video.mp4 --use-4layer --editorial-model gpt-4o

# Recommended: gpt-4o-mini (~$0.20 per video, 60% cheaper)
python3 arena_process.py video.mp4 --use-4layer --editorial-model gpt-4o-mini

# Cheapest: Standard mode (~$0.05 per video)
python3 arena_process.py video.mp4
```

**Note:** Layer 3 and Layer 4 always use gpt-4o-mini regardless of `--editorial-model` setting.

### Debugging with Layer Export

```bash
# Export all layer results to output/editorial_layers/
python3 arena_process.py video.mp4 --use-4layer --export-editorial-layers

# Output structure:
# output/editorial_layers/
#   ├── layer1_moments.json       (25 candidates)
#   ├── layer2_thoughts.json      (18 complete thoughts)
#   ├── layer3_validated.json     (12 passed quality gate)
#   └── layer4_packaged.json      (final clips)
```

Use this to understand:
- Why clips were rejected (check `rejection_reason`)
- How boundaries were expanded (compare Layer 1 vs Layer 2)
- Quality gate decisions (check `standalone_score` in Layer 3)

## Tips & Tricks

### 1. Reuse Cached Transcripts

Once transcribed, the cache saves time and money:

```bash
# First run: 2-5 minutes (transcribes)
python3 arena_process.py video.mp4

# Second run: ~30 seconds (uses cache)
python3 arena_process.py video.mp4 -n 10
```

### 2. Start Small

Test with shorter videos first:

```bash
# Cut a test segment with ffmpeg
ffmpeg -i long-video.mp4 -t 300 -c copy test-5min.mp4

# Process the test
python3 arena_process.py test-5min.mp4 --use-4layer
```

### 3. Review Metadata First

Check what Arena found before generating videos:

```bash
python3 arena_process.py video.mp4
cat output/metadata.json | jq '.clips[].title'
```

### 4. Adjust Duration for Your Content

Different content needs different clip lengths:

```bash
# Quick tips/insights: shorter clips
python3 arena_process.py tips-video.mp4 --min 15 --max 45

# Storytelling/interviews: longer clips
python3 arena_process.py interview.mp4 --min 60 --max 120
```

**Common Issue:** If 4-layer returns "No clips passed validation", your duration constraints may be too strict. Try:
```bash
# Relax constraints
python3 arena_process.py video.mp4 --use-4layer --min 20 --max 90
```

### 5. Balance Quality and Cost

For production workflows:

```bash
# Step 1: Test with standard mode (fast, cheap)
python3 arena_process.py video.mp4 -n 20

# Step 2: Review metadata.json and pick best candidates

# Step 3: Re-run with 4-layer on promising videos
python3 arena_process.py video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 5
```

### 6. Optimize for Batch Processing

```bash
# Process multiple videos efficiently
for video in videos/*.mp4; do
  echo "Processing: $video"
  # Use gpt-4o-mini for cost savings on bulk processing
  python3 arena_process.py "$video" \
    --use-4layer \
    --editorial-model gpt-4o-mini \
    -n 5 \
    -o "output/$(basename $video .mp4)"
done
```

## Common Workflows

### Workflow 1: Quick Experiment (Standard Mode)

Fast, cheap testing for initial exploration.

```bash
# Fast, cheap testing
arena process video.mp4 -n 10

# Check what was found
cat output/metadata.json | jq '.clips[] | {title, interest_score}'
```

**Cost:** ~$0.05-0.10 | **Time:** 2-4 minutes

### Workflow 2: Production Quality (4-Layer)

Professional clips ready for distribution.

```bash
# Professional clips for distribution
arena process video.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 5 \
  --min 20 \
  --max 60
```

**Cost:** ~$0.20-0.30 | **Time:** 5-8 minutes

### Workflow 3: Review-Before-Generate (Recommended)

Cost-optimized workflow with manual review step.

```bash
# Step 1: Analyze without generating (fast, cheap)
arena analyze video.mp4 --use-4layer -n 10 -o moments.json

# Step 2: Review moments.json
cat moments.json | jq '.clips[] | {id, title, duration, standalone_score}'

# Step 3: Generate only the best clips
arena generate video.mp4 moments.json --select 1,3,5,7
```

**Benefits:**
- Review clip quality before generating videos
- Generate only the best clips
- Save processing time on rejects
- Total cost same as full pipeline, but more control

### Workflow 4: Iterative Refinement

Experiment with different parameters using cached transcript.

```bash
# Initial run (creates transcript cache)
arena process video.mp4 --use-4layer

# Try different clip counts (reuses cached transcript)
arena process video.mp4 --use-4layer -n 3
arena process video.mp4 --use-4layer -n 10

# Try different durations
arena process video.mp4 --use-4layer --min 20 --max 45
arena process video.mp4 --use-4layer --min 45 --max 90
```

**Tip:** Cached transcripts save time and money on subsequent runs!

### Workflow 5: Debug Quality Issues

Export layer data to understand why clips were rejected.

```bash
# Export layer data to diagnose issues
arena process video.mp4 \
  --use-4layer \
  --export-editorial-layers

# Review rejection reasons
cat output/editorial_layers/layer3_validated.json | \
  jq '.[] | select(.verdict=="REJECT") | {thought_id, rejection_reason, standalone_score}'

# Check pass rate
cat output/editorial_layers/layer3_validated.json | \
  jq '[.[] | select(.verdict=="PASS")] | length'
```

### Workflow 6: Batch Processing

Process multiple videos efficiently.

```bash
# Process all videos in a directory
for video in videos/*.mp4; do
  echo "Processing: $video"

  # Use cost-optimized 4-layer
  arena process "$video" \
    --use-4layer \
    --editorial-model gpt-4o-mini \
    -n 5 \
    -o "output/$(basename $video .mp4)"

  # Wait between videos to avoid rate limits (handled automatically)
  echo "Completed: $video"
done
```

**Note:** Rate limits are now handled automatically with intelligent retry logic!

### Workflow 7: Content Creator Social Media Pipeline

Optimized for TikTok, Instagram Reels, YouTube Shorts.

```bash
# Short-form optimized
arena process video.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 3 \
  --min 15 \
  --max 30 \
  --fast

# Output is ready to upload!
```

### Workflow 8: Podcast Highlights

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

## Troubleshooting

### "No clips passed validation" (4-Layer)

This is the most common issue with 4-layer mode. Layer 3 is a strict quality gate.

**Cause:** Your duration constraints are too tight for complete thoughts in your video.

**Solutions:**

```bash
# Solution 1: Lower minimum duration
arena process video.mp4 --use-4layer --min 20 --max 90

# Solution 2: Allow wider range
arena process video.mp4 --use-4layer --min 15 --max 120

# Solution 3: Debug with layer export to see why clips were rejected
arena process video.mp4 --use-4layer --export-editorial-layers
cat output/editorial_layers/layer3_validated.json | jq '.[] | select(.verdict=="REJECT")'
```

**Common rejection reasons:**
- `duration_constraint`: Clip too short/long after validation
- `missing_premise`: Doesn't explain what it's about
- `dangling_reference`: Uses "it", "this", "that" without defining them
- `incomplete_resolution`: Cuts off mid-thought
- `structural_issue`: Needed >15s adjustment to fix

### Low pass rate (<30%)

If Layer 3 is rejecting most clips:

```bash
# 1. Check pass rate in output
arena process video.mp4 --use-4layer
# Look for: "Layer 3 pass rate: X%"

# 2. If <30%, your content may have:
#    - Lots of references to earlier context
#    - Fragmented thoughts spread across timestamps
#    - Heavy use of pronouns without clear referents

# 3. Try more candidates to get enough good clips
arena process video.mp4 --use-4layer -n 10 --min 20 --max 90
```

### Rate Limit Errors (429)

**Good News:** Rate limits are now handled automatically!

Arena CLI includes intelligent retry logic:
- Automatically retries on rate limit errors
- Parses suggested wait time from OpenAI
- Uses exponential backoff (2s, 4s, 8s, 16s, 32s)
- Up to 5 retries per API call
- Shows clear progress: "⏳ Rate limit hit. Waiting 2.5s before retry 1/5..."

**You don't need to do anything** - just watch the progress bar!

**If you're consistently hitting rate limits:**
```bash
# Option 1: Process fewer clips at once
arena process video.mp4 --use-4layer -n 3

# Option 2: Disable parallel processing in Layer 2 (slower but more rate-limit friendly)
# This is controlled internally - rate limits are handled automatically

# Option 3: Add delays between batch processing
for video in videos/*.mp4; do
  arena process "$video" --use-4layer -n 5
  sleep 30  # Wait 30 seconds between videos
done
```

### Can't find video file

Use absolute paths or verify the file exists:

```bash
# Use absolute path
arena process /full/path/to/video.mp4

# Or relative from current directory
arena process ./videos/my-video.mp4

# Check if file exists
ls -lh ./videos/my-video.mp4
```

### Transcription failed

Check your API key:

```bash
# Check if API key is set
echo $OPENAI_API_KEY  # Should show: sk-...

# Set it if missing:
export OPENAI_API_KEY="sk-your-key"

# Or use config command
arena config set openai_api_key "sk-your-key"
arena config get openai_api_key  # Verify it's set
```

### Command not found: arena

The CLI may not be in your PATH:

```bash
# Reinstall globally
npm install -g @arena/cli

# Or use npx
npx @arena/cli process video.mp4

# Check installation
which arena
arena --version
```

### Out of memory

For large videos, reduce clip count or use analyze-then-generate workflow:

```bash
# Option 1: Generate fewer clips
arena process large-video.mp4 -n 5

# Option 2: Use step-by-step workflow
arena analyze large-video.mp4 -n 5 -o moments.json
arena generate large-video.mp4 moments.json --select 1,2,3
```

### 4-Layer too expensive

Use cost optimization strategies:

```bash
# Option 1: Use gpt-4o-mini (60% cheaper)
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini

# Option 2: Generate fewer clips
arena process video.mp4 --use-4layer -n 3

# Option 3: Analyze first, generate selectively
arena analyze video.mp4 --use-4layer -n 10 -o moments.json
# Review moments.json, then:
arena generate video.mp4 moments.json --select 1,3,5
```

### Python or FFmpeg not found

Arena CLI requires Python 3.9+ and FFmpeg:

```bash
# Check versions
python3 --version  # Should be 3.9+
ffmpeg -version

# Install Python (macOS)
brew install python3

# Install Python (Ubuntu)
sudo apt install python3

# Install FFmpeg (macOS)
brew install ffmpeg

# Install FFmpeg (Ubuntu)
sudo apt install ffmpeg
```

### Layer export files missing

The `--export-editorial-layers` flag requires `--use-4layer`:

```bash
# Wrong:
arena process video.mp4 --export-editorial-layers

# Correct:
arena process video.mp4 --use-4layer --export-editorial-layers
```

## Getting Help

```bash
# Show help
arena --help
arena process --help

# Check version
arena --version
```

## Performance Benchmarks

### Standard Mode
- **Speed:** ~2-4 minutes for 30-minute video
- **Cost:** ~$0.05-0.10 per video
- **Quality:** Good for experimentation

### 4-Layer Mode (gpt-4o)
- **Speed:** ~5-8 minutes for 30-minute video
- **Cost:** ~$0.40-0.60 per video
- **Quality:** Professional, distribution-ready

### 4-Layer Mode (gpt-4o-mini) - Recommended
- **Speed:** ~5-8 minutes for 30-minute video
- **Cost:** ~$0.15-0.25 per video (60% cheaper!)
- **Quality:** Near-identical to gpt-4o

## What's Next?

- Read [EDITORIAL_ARCHITECTURE.md](./engine/EDITORIAL_ARCHITECTURE.md) for 4-layer system details
- Read [REFINEMENT_PLAN.md](./engine/REFINEMENT_PLAN.md) for architectural improvements
- Check [CLI_REFERENCE.md](./CLI_REFERENCE.md) for complete CLI documentation
- See [ARENA_CLOUD_PLAN.md](./engine/ARENA_CLOUD_PLAN.md) for cloud features roadmap
