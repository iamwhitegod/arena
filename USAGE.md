# Arena Usage Guide

Quick reference for using Arena CLI.

## Basic Command

```bash
arena process <video-file> [options]
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `-o, --output <dir>` | Output directory | `.arena/output` |
| `-c, --clips <number>` | Target number of clips | `10` |
| `--min-duration <seconds>` | Minimum clip duration | `30` |
| `--max-duration <seconds>` | Maximum clip duration | `90` |

## Examples

### Basic Usage

```bash
# Process a video with defaults
arena process my-video.mp4

# Or if not installed globally:
cd cli
npm run dev process ../my-video.mp4
```

### Custom Clip Count

```bash
# Generate 15 clips instead of 10
arena process my-video.mp4 --clips 15
```

### Shorter Clips

```bash
# Generate clips between 15-45 seconds
arena process my-video.mp4 \
  --min-duration 15 \
  --max-duration 45
```

### Custom Output Location

```bash
# Save to a specific directory
arena process my-video.mp4 \
  --output ./my-clips
```

### Full Example

```bash
# Generate 20 short clips (20-60s) in custom directory
arena process ~/Videos/my-presentation.mp4 \
  --clips 20 \
  --min-duration 20 \
  --max-duration 60 \
  --output ~/Desktop/arena-clips
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

```json
{
  "source_video": "my-video.mp4",
  "duration": 3600,
  "clips": [
    {
      "id": "clip_001",
      "start_time": 125.3,      // When clip starts in video
      "end_time": 168.7,        // When clip ends
      "duration": 43.4,         // Clip length in seconds
      "title": "Why startups fail at PMF",  // AI-generated title
      "reason": "Strong hook with insight",  // Why this clip is interesting
      "interest_score": 0.95,   // AI interest rating (0-1)
      "content_type": "insight", // Type: hook, insight, advice, etc.
      "scores": {
        "ai_interest": 0.95,    // AI analysis score
        "audio_energy": 0.0,    // Audio energy (Sprint 3)
        "visual_change": 0.0,   // Visual changes (Sprint 3)
        "combined": 0.95        // Final combined score
      },
      "files": {
        "raw": "clips/clip_001_raw.mp4",
        "subtitled": "clips/clip_001_subtitled.mp4",
        "thumbnail": "clips/clip_001_thumbnail.jpg"
      }
    }
  ]
}
```

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

## Tips & Tricks

### 1. Reuse Cached Transcripts

Once transcribed, the cache saves time and money:

```bash
# First run: 2-5 minutes (transcribes)
arena process video.mp4

# Second run: ~30 seconds (uses cache)
arena process video.mp4 --clips 15
```

### 2. Start Small

Test with shorter videos first:

```bash
# Cut a test segment with ffmpeg
ffmpeg -i long-video.mp4 -t 300 -c copy test-5min.mp4

# Process the test
arena process test-5min.mp4
```

### 3. Review Metadata First

Check what Arena found before generating videos:

```bash
arena process video.mp4
cat .arena/output/metadata.json | jq '.clips[].title'
```

### 4. Adjust for Your Content

Different content needs different clip lengths:

```bash
# Quick tips/insights: shorter clips
arena process tips-video.mp4 --min-duration 15 --max-duration 45

# Storytelling/interviews: longer clips
arena process interview.mp4 --min-duration 60 --max-duration 120
```

### 5. Use Local Whisper for Free

Save on API costs (but slower):

```json
// In ~/.arena/config.json
{
  "whisper_mode": "local"
}
```

Then install local Whisper:
```bash
pip install openai-whisper
```

## Common Workflows

### Workflow 1: Quick Process

```bash
# One command, done
arena process video.mp4
cat .arena/output/metadata.json
```

### Workflow 2: Iterative Refinement

```bash
# Initial run (creates cache)
arena process video.mp4

# Try different clip counts
arena process video.mp4 --clips 5
arena process video.mp4 --clips 20

# Try different durations
arena process video.mp4 --min-duration 20 --max-duration 45
```

### Workflow 3: Batch Processing

```bash
# Process multiple videos
for video in videos/*.mp4; do
  echo "Processing: $video"
  arena process "$video" --output "output/$(basename $video .mp4)"
done
```

## Troubleshooting

### Command not found: arena

```bash
# If not installed globally, use:
cd cli
npm run dev process ../video.mp4

# Or install globally:
cd cli
npm link
```

### Can't find video file

Use absolute paths or verify the file exists:

```bash
# Use absolute path
arena process /full/path/to/video.mp4

# Or relative from current directory
arena process ./videos/my-video.mp4
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
arena process large-video.mp4 --clips 5
```

## Getting Help

```bash
# Show help
arena --help
arena process --help

# Check version
arena --version
```

## What's Next?

- Read [SPRINT2.md](./SPRINT2.md) for implementation details
- Check [SETUP.md](./SETUP.md) for installation instructions
- See the [implementation plan](/Users/whitegodkingsley/.claude/plans/ancient-doodling-adleman.md) for future features
