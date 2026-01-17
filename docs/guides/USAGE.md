# Arena Usage Guide

Quick reference for using Arena CLI.

## Basic Command

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

## Examples

### Basic Usage

```bash
# Process a video with defaults (standard mode)
python3 arena_process.py my-video.mp4

# Generate 10 clips instead of 5
python3 arena_process.py my-video.mp4 -n 10
```

### 4-Layer Editorial System (Recommended)

```bash
# Use 4-layer system for professional quality
python3 arena_process.py my-video.mp4 --use-4layer -n 5

# Cost optimization: Use gpt-4o-mini (saves ~60%)
python3 arena_process.py my-video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 5

# Debug mode: Export intermediate layer results
python3 arena_process.py my-video.mp4 --use-4layer --export-editorial-layers
```

### Custom Duration Constraints

```bash
# Short clips (15-45 seconds) - Great for quick tips
python3 arena_process.py my-video.mp4 --min 15 --max 45

# Medium clips (30-60 seconds) - Default for most content
python3 arena_process.py my-video.mp4 --min 30 --max 60

# Long clips (60-120 seconds) - For stories/interviews
python3 arena_process.py my-video.mp4 --min 60 --max 120
```

**Important:** The 4-layer system respects duration constraints strictly. If you get "No clips passed validation", try:
- Lowering `--min` (e.g., `--min 20` instead of 30)
- Raising `--max` (e.g., `--max 120` instead of 90)
- Checking if your video has complete thoughts that fit within constraints

### Custom Output Location

```bash
# Save to a specific directory
python3 arena_process.py my-video.mp4 -o ./my-clips
```

### Full Production Example

```bash
# Professional quality, optimized cost, custom durations
python3 arena_process.py ~/Videos/podcast-episode.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 8 \
  --min 20 \
  --max 60 \
  -o ~/Desktop/podcast-clips
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

```bash
# Fast, cheap testing
python3 arena_process.py video.mp4 -n 10
cat output/metadata.json | jq '.clips[] | {title, interest_score}'
```

### Workflow 2: Production Quality (4-Layer)

```bash
# Professional clips for distribution
python3 arena_process.py video.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 5 \
  --min 20 \
  --max 60
```

### Workflow 3: Iterative Refinement

```bash
# Initial run (creates cache)
python3 arena_process.py video.mp4 --use-4layer

# Try different clip counts
python3 arena_process.py video.mp4 --use-4layer -n 3
python3 arena_process.py video.mp4 --use-4layer -n 10

# Try different durations
python3 arena_process.py video.mp4 --use-4layer --min 20 --max 45
```

### Workflow 4: Debug Quality Issues

```bash
# Export layer data to diagnose issues
python3 arena_process.py video.mp4 \
  --use-4layer \
  --export-editorial-layers

# Review rejection reasons
cat output/editorial_layers/layer3_validated.json | jq '.[] | select(.verdict=="REJECT") | {thought_id, rejection_reason, standalone_score}'
```

### Workflow 5: Batch Processing

```bash
# Process multiple videos with 4-layer
for video in videos/*.mp4; do
  echo "Processing: $video"
  python3 arena_process.py "$video" \
    --use-4layer \
    --editorial-model gpt-4o-mini \
    -n 5 \
    -o "output/$(basename $video .mp4)"
done
```

## Troubleshooting

### "No clips passed validation" (4-Layer)

This is the most common issue with 4-layer mode. Layer 3 is a strict quality gate.

**Cause:** Your duration constraints are too tight for complete thoughts in your video.

**Solutions:**

```bash
# Solution 1: Lower minimum duration
python3 arena_process.py video.mp4 --use-4layer --min 20 --max 90

# Solution 2: Allow wider range
python3 arena_process.py video.mp4 --use-4layer --min 15 --max 120

# Solution 3: Debug with layer export to see why clips were rejected
python3 arena_process.py video.mp4 --use-4layer --export-editorial-layers
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
python3 arena_process.py video.mp4 --use-4layer
# Look for: "Layer 3 pass rate: X%"

# 2. If <30%, your content may have:
#    - Lots of references to earlier context
#    - Fragmented thoughts spread across timestamps
#    - Heavy use of pronouns without clear referents

# 3. Try more candidates to get enough good clips
python3 arena_process.py video.mp4 --use-4layer -n 10 --min 20 --max 90
```

### Can't find video file

Use absolute paths or verify the file exists:

```bash
# Use absolute path
python3 arena_process.py /full/path/to/video.mp4

# Or relative from current directory
python3 arena_process.py ./videos/my-video.mp4
```

### Transcription failed

Check your API key:

```bash
echo $OPENAI_API_KEY  # Should show: sk-...

# Set it if missing:
export OPENAI_API_KEY="sk-your-key"
```

### Out of memory

For large videos, reduce clip count:

```bash
python3 arena_process.py large-video.mp4 -n 5
```

### 4-Layer too expensive

Use cost optimization strategies:

```bash
# Option 1: Use gpt-4o-mini (60% cheaper)
python3 arena_process.py video.mp4 --use-4layer --editorial-model gpt-4o-mini

# Option 2: Generate fewer clips
python3 arena_process.py video.mp4 --use-4layer -n 3

# Option 3: Use standard mode for bulk, 4-layer for finals
python3 arena_process.py video.mp4 -n 20  # Find candidates (~$0.05)
# Review metadata, then:
python3 arena_process.py video.mp4 --use-4layer -n 5  # Polish top 5 (~$0.20)
```

### Layer export files missing

The `--export-editorial-layers` flag requires `--use-4layer`:

```bash
# Wrong:
python3 arena_process.py video.mp4 --export-editorial-layers

# Correct:
python3 arena_process.py video.mp4 --use-4layer --export-editorial-layers
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
