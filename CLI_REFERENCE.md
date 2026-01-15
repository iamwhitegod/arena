# Arena CLI Reference

Arena uses a git-style CLI with subcommands. All commands follow the pattern:

```bash
arena <command> [arguments] [options]
```

## Commands

### `arena extract-audio`

Extract audio track from video file

```bash
arena extract-audio <video> [options]
```

**Options:**
- `-o, --output FILE` - Output audio file (default: video_audio.mp3)
- `--format FORMAT` - Audio format: mp3, wav, aac, m4a, flac (default: mp3)
- `--bitrate BITRATE` - Audio bitrate (default: 192k)
- `--sample-rate HZ` - Sample rate: 16000, 22050, 44100, 48000 (default: original)
- `--mono` - Convert to mono (single channel)

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
| MP3    | Small | Good | General purpose, podcasts |
| AAC/M4A | Small | Better | Modern devices, streaming |
| WAV    | Large | Perfect | Editing, processing |
| FLAC   | Medium | Perfect | Archival, lossless |

---

### `arena process`

Run the complete pipeline: transcribe → analyze → generate clips

```bash
arena process <video> [options]
```

**Options:**
- `-o, --output DIR` - Output directory (default: output)
- `-n, --num-clips N` - Number of clips to generate (default: 5)
- `--min SECONDS` - Minimum clip duration (default: 30)
- `--max SECONDS` - Maximum clip duration (default: 90)
- `--fast` - Fast mode - stream copy, 10x faster
- `--padding SECONDS` - Padding before/after clips (default: 0.5)
- `--no-cache` - Force re-transcription
- `--energy-weight 0-1` - Energy boost weight (default: 0.3)

**Examples:**
```bash
# Basic usage - generates 5 clips
arena process video.mp4

# Generate 10 short clips for social media
arena process video.mp4 -n 10 --min 15 --max 30

# Fast mode for quick iteration
arena process video.mp4 --fast

# Custom output directory
arena process video.mp4 -o my_clips

# More padding for smoother transitions
arena process video.mp4 --padding 2.0
```

---

### `arena demo`

Run demo with existing test data (no API key needed)

```bash
arena demo
```

**Options:**
- `-o, --output DIR` - Output directory (default: demo_output)

**Example:**
```bash
arena demo
```

Perfect for testing Arena without an API key!

---

### `arena transcribe`

Transcribe video audio only

```bash
arena transcribe <video> [options]
```

**Options:**
- `-o, --output FILE` - Output transcript file (default: video_transcript.json)
- `--mode api|local` - Transcription mode (default: api)
- `--no-cache` - Force re-transcription

**Examples:**
```bash
# Transcribe with API (fast, accurate)
arena transcribe video.mp4

# Save to specific file
arena transcribe video.mp4 -o my_transcript.json

# Use local Whisper model (slower, free)
arena transcribe video.mp4 --mode local
```

---

### `arena analyze`

Analyze video with AI + energy detection

```bash
arena analyze <video> [options]
```

**Options:**
- `-t, --transcript FILE` - Use existing transcript
- `-o, --output FILE` - Output analysis file (default: analysis_results.json)
- `-n, --num-clips N` - Number of clips to analyze (default: 10)
- `--min SECONDS` - Minimum clip duration (default: 30)
- `--max SECONDS` - Maximum clip duration (default: 90)
- `--energy-weight 0-1` - Energy boost weight (default: 0.3)

**Examples:**
```bash
# Analyze video (will transcribe if needed)
arena analyze video.mp4

# Use existing transcript
arena analyze video.mp4 -t transcript.json

# Analyze for more clips
arena analyze video.mp4 -n 20

# Save to specific file
arena analyze video.mp4 -o my_analysis.json
```

---

### `arena generate`

Generate clips from existing analysis

```bash
arena generate <video> <analysis> [options]
```

**Options:**
- `-o, --output DIR` - Output directory (default: clips)
- `-n, --num-clips N` - Number of clips to generate
- `--fast` - Fast mode - stream copy
- `--padding SECONDS` - Padding before/after (default: 0.5)
- `--no-thumbs` - Skip thumbnail generation

**Examples:**
```bash
# Generate clips from analysis
arena generate video.mp4 analysis_results.json

# Generate only top 3 clips
arena generate video.mp4 analysis_results.json -n 3

# Fast mode
arena generate video.mp4 analysis_results.json --fast

# Custom output directory
arena generate video.mp4 analysis_results.json -o my_clips
```

---

### `arena info`

Show video metadata and information

```bash
arena info <video> [options]
```

**Options:**
- `--json` - Output as JSON

**Examples:**
```bash
# Show video info
arena info video.mp4

# Output as JSON
arena info video.mp4 --json
```

---

## Common Workflows

### Quick Start

```bash
# Try the demo (no API key)
arena demo

# Set API key
export OPENAI_API_KEY="sk-your-key-here"

# Process your video
arena process video.mp4
```

### Separate Steps (More Control)

```bash
# Step 1: Transcribe
arena transcribe video.mp4

# Step 2: Analyze
arena analyze video.mp4 -t video_transcript.json

# Step 3: Generate clips
arena generate video.mp4 analysis_results.json
```

### Social Media Presets

**TikTok / Instagram Reels (15-30s):**
```bash
arena process video.mp4 -n 10 --min 15 --max 30
```

**YouTube Shorts (<60s):**
```bash
arena process video.mp4 -n 5 --min 30 --max 60
```

**Twitter / LinkedIn (30-120s):**
```bash
arena process video.mp4 -n 3 --min 30 --max 120
```

### Development / Testing

**Fast iteration:**
```bash
# Fast mode - 10x faster
arena process video.mp4 --fast

# Use cached transcript
arena process video.mp4  # Automatically uses cache
```

**Force fresh start:**
```bash
# Re-transcribe even if cached
arena process video.mp4 --no-cache
```

---

## Environment Variables

### Required

**`OPENAI_API_KEY`** - OpenAI API key for transcription and analysis

```bash
export OPENAI_API_KEY="sk-your-key-here"
```

Get one at: https://platform.openai.com/api-keys

### Optional

**`ARENA_ENHANCEMENT_LEVEL`** - Audio enhancement level
- `gentle` (default) - Light enhancement
- `moderate` - Balanced enhancement
- `aggressive` - Heavy enhancement

```bash
export ARENA_ENHANCEMENT_LEVEL="moderate"
```

---

## Output Structure

**Default location:** Project root (alongside `cli/` and `engine/` folders)

```
arena/                              # Project root
├── cli/
├── engine/
└── output/                         # Default output directory
    ├── clips/
    │   ├── clip-title_001_02m05s-02m48s.mp4
    │   ├── clip-title_001_02m05s-02m48s_thumb.jpg
    │   ├── clip-title_001_02m05s-02m48s_metadata.json
    │   ├── clip-title_002_05m30s-06m15s.mp4
    │   └── ...
    ├── analysis_results.json       # Complete analysis
    └── .cache/
        └── video_transcript.json   # Cached transcript
```

**Custom output location:**
```bash
# Absolute path
arena process video.mp4 -o /path/to/my/output

# Relative path (from project root)
arena process video.mp4 -o ../my-clips
```

---

## Getting Help

```bash
# General help
arena --help

# Command-specific help
arena process --help
arena transcribe --help
arena analyze --help
arena generate --help
```

---

## Installation

```bash
cd engine

# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x arena-cli

# Optional: Create symlink for global access
sudo ln -s $(pwd)/arena-cli /usr/local/bin/arena
```

Then use `arena` from anywhere:

```bash
arena demo
arena process ~/videos/my-video.mp4
```

---

## Troubleshooting

**"command not found: arena"**
- Use `./arena-cli` from the engine directory
- Or create a symlink (see Installation above)

**"OPENAI_API_KEY not set"**
```bash
export OPENAI_API_KEY="sk-your-key-here"

# Add to your shell profile for persistence
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc
```

**"FFmpeg is not installed"**
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

**"Video file not found"**
- Use absolute paths: `arena process /full/path/to/video.mp4`
- Or relative from current directory

---

## Version

```bash
arena --version
```

Current version: 0.1.0

---

## Tips

1. **Start with demo** - `arena demo` to see how it works
2. **Use cache** - Transcription is cached, subsequent runs are instant
3. **Try fast mode** - Use `--fast` for quick iteration
4. **Check video info first** - `arena info video.mp4` before processing
5. **Separate steps** - Use individual commands for more control
6. **Adjust durations** - Match platform requirements (TikTok, YouTube, etc.)

---

## Examples by Use Case

### Content Creator Pipeline

```bash
# 1. Record video
# 2. Process with Arena
arena process recording.mp4 -n 10 --min 20 --max 45

# 3. Review clips in output/clips/
# 4. Upload to social media
```

### Podcast to Clips

```bash
# Process podcast
arena process podcast.mp4 -n 15 --min 45 --max 90

# Longer clips for more context
```

### Conference Talk

```bash
# Extract key moments
arena process talk.mp4 -n 8 --min 60 --max 120

# Longer clips preserve full ideas
```

### Quick Highlights

```bash
# Short, punchy clips
arena process video.mp4 -n 20 --min 10 --max 20 --fast

# Many short clips, generated quickly
```

---

For more details, see:
- [QUICKSTART.md](./QUICKSTART.md) - Getting started guide
- [README.md](./README.md) - Project overview
- [CLIP_GENERATION.md](./CLIP_GENERATION.md) - Clip generation details
- [HYBRID_ANALYSIS.md](./HYBRID_ANALYSIS.md) - Analysis details
