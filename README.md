# Arena

> AI-powered, open-source, local-first video clipping for the terminal

[![npm](https://img.shields.io/npm/v/@whitegodkingsley/arena-cli)](https://www.npmjs.com/package/@whitegodkingsley/arena-cli)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Arena is an AI-powered, open-source, local-first video clipping engine for the terminal that automatically finds the best moments in your videos and exports platform-ready clips for TikTok, Reels, and Shorts. It works with local video and audio files plus URLs from YouTube, Vimeo, Twitter/X, TikTok, and 1,000+ sites supported by `yt-dlp`.

## Why local-first?

- **No upfront upload:** Start processing immediately from your terminal. Arena does not require you to upload large source videos to the cloud.
- **Save time and data:** Avoid lengthy uploads and unnecessary bandwidth usage before processing can begin.
- **Built for unreliable connections:** Process videos locally without repeatedly restarting failed uploads when your connection drops.
- **Your files stay with you:** Source videos, transcripts, analysis results, and generated clips remain on your machine unless you explicitly use an external provider or Arena Cloud.
- **Local AI models available:** Use Arena's verified cross-platform local packs for transcription, analysis, and embeddings, or use a loopback Ollama server for analysis and embeddings.
- **Creator and developer friendly:** Creators get a fast, private workflow; developers get a scriptable terminal interface, inspectable artifacts, and automation-friendly commands.

## ✨ Features

### 🎯 **4-Layer Editorial System**
Professional-grade clip generation with quality validation:
- **Layer 1:** Detect interesting moments (hooks, insights, stories)
- **Layer 2:** Expand to complete thought boundaries
- **Layer 3:** Validate standalone context (strict quality gate)
- **Layer 4:** Package with titles, descriptions, and hashtags

### 🌐 **URL & Audio Support**
Process content from anywhere:
- YouTube, Vimeo, Twitter/X, TikTok, and 1000+ sites via `yt-dlp`
- All audio formats: MP3, WAV, FLAC, AAC, OGG, M4A, WMA, Opus
- Cached downloads — same URL won't re-download

### 📐 **Multi-Platform Formatting**
Convert clips for any social media platform with optimal specs:
- TikTok, Instagram Reels, YouTube Shorts (9:16 vertical)
- YouTube, LinkedIn (16:9 horizontal)
- Instagram Feed (1:1 square)
- Smart cropping and blur background padding

### 📝 **Captions**
Burn subtitles into clips from the Whisper transcript:
- Traditional subtitle style with configurable font, color, and position
- Platform-aware safe zones (avoids TikTok/Reels UI overlap)
- Integrated into the formatting pipeline (single FFmpeg pass)

### 🎬 **Hybrid AI + Energy Analysis**
- AI content analysis finds engaging narratives
- Audio energy detection identifies enthusiastic delivery
- Combined scoring for clips with great content AND delivery

### 🎥 **Scene Detection**
- Automatic detection of visual scene changes
- Align clip boundaries to natural scene transitions
- Standalone scene analysis for video structure insights

### 🚀 **Production-Ready CLI**
- 11 commands for flexible workflows
- Beautiful progress tracking with multi-stage visualization
- Automatic rate limit handling with intelligent retry
- TypeScript + Python architecture for speed and power

### 💰 **Cost-Optimized**
- Smart caching saves time and money
- Support for gpt-4o-mini (~60% cheaper than gpt-4o)
- Typical cost: $0.20-0.50 per video depending on model choice

## 🚀 Quick Start

### Installation

```bash
# Install the current stable CLI from npm
npm install --global @whitegodkingsley/arena-cli@0.4.2

# Create and verify Arena's private processing runtime
arena setup
arena setup --check

# Set up your OpenAI API key
export OPENAI_API_KEY="sk-..."
```

This npm path requires Node.js 22–24, Python 3.10–3.12, and FFmpeg/ffprobe. Docker users can run the [published multi-architecture image](#-docker) without installing those host runtimes. Contributors should follow the [source installation guide](./docs/getting-started/installation.md#install-from-source).

### Run Interactive Setup

```bash
arena init
```

This wizard helps you configure:
- Workflow type (content creator, podcast, course)
- Clip duration preferences
- Quality vs cost balance

### Process Your First Video

```bash
# From a local file
arena process video.mp4 -n 5

# From a YouTube URL
arena process https://www.youtube.com/watch?v=VIDEO_ID -n 5

# Transcribe audio (any format)
arena transcribe podcast.mp3

# With captions burned in
arena process video.mp4 --captions -p tiktok

# Format for TikTok
arena format output/clips/ -p tiktok -o tiktok/
```

## 📚 Commands

Arena provides 11 commands for flexible video clip generation workflows:

| Command | Purpose | Example |
|---------|---------|---------|
| `arena init` | Interactive setup wizard | `arena init` |
| `arena process` | All-in-one clip generation | `arena process video.mp4` |
| `arena transcribe` | Transcription only (files + URLs) | `arena transcribe podcast.mp3` |
| `arena analyze` | Find moments (no video generation) | `arena analyze video.mp4 -n 10` |
| `arena generate` | Generate clips from analysis | `arena generate video.mp4 analysis.json` |
| `arena format` | Format for social platforms | `arena format clips/ -p tiktok` |
| `arena detect-scenes` | Detect scene changes | `arena detect-scenes video.mp4` |
| `arena config` | Manage configuration | `arena config set openai_api_key` |
| `arena extract-audio` | Extract audio from video | `arena extract-audio video.mp4` |
| `arena setup` | Install dependencies automatically | `arena setup` |
| `arena diagnose` | System diagnostics | `arena diagnose` |

All commands that accept a video file also accept audio files and URLs.

See the [documentation index](./docs/README.md) for installation, workflows, reference material, architecture, and troubleshooting.

### Local and Ollama providers

Run all inference with Arena's verified local model packs:

```bash
arena setup --local --model-pack lite
arena process video.mp4 --provider local
```

Or use Ollama for chat and embeddings with a separate transcription provider:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
arena process video.mp4 --provider ollama --transcription-provider local
```

See [Local inference](./docs/guides/local-inference.md) and the [Ollama guide](./docs/guides/ollama.md) for hardware requirements, provider combinations, and release validation.

## 🎯 Workflows

### Workflow 1: Quick Clips

```bash
# Generate 5 professional clips
arena process video.mp4 --editorial-model gpt-4o-mini -n 5
```

**Cost:** ~$0.20 | **Time:** 5-8 minutes

### Workflow 2: Review Before Generate

```bash
# Step 1: Analyze (fast, cheap)
arena analyze video.mp4 -n 10 -o moments.json

# Step 2: Review moments.json

# Step 3: Generate only the best
arena generate video.mp4 moments.json --select 1,3,5,7
```

**Benefits:** Review quality before generating, save processing time

### Workflow 3: Multi-Platform Distribution

```bash
# Step 1: Generate high-quality clips with captions
arena process video.mp4 -n 5 --captions

# Step 2: Format for each platform
arena format output/clips/ -p tiktok -o social/tiktok/
arena format output/clips/ -p instagram-reels -o social/reels/
arena format output/clips/ -p youtube-shorts -o social/shorts/
arena format output/clips/ -p youtube -o social/youtube/
```

**Result:** 1 video → 5 captioned clips → 4 platforms = 20 optimized videos!

### Workflow 4: Process from URL

```bash
# Transcribe a YouTube video
arena transcribe "https://www.youtube.com/watch?v=VIDEO_ID" -o transcript.json

# Generate clips from a YouTube video
arena process "https://www.youtube.com/watch?v=VIDEO_ID" -n 5 --captions -p tiktok

# Use browser cookies if YouTube requires authentication
arena process "https://www.youtube.com/watch?v=VIDEO_ID" --cookies-from-browser chrome -n 5

# Works with any yt-dlp supported site (YouTube, Vimeo, Twitter, TikTok, etc.)
arena transcribe https://vimeo.com/123456789
```

URL support is included in Arena's private runtime. Node.js provides yt-dlp's JavaScript runtime, and downloads are cached.

## 📊 4-Layer Editorial System

Arena uses a 4-layer editorial system for every analysis:

- **Layer 1:** Find 25+ candidate moments (hooks, insights, stories)
- **Layer 2:** Expand to complete thought boundaries (premise → claim → resolution)
- **Layer 3:** Validate standalone context (strict quality gate)
- **Layer 4:** Package with professional titles, descriptions, and hashtags

**Cost:** ~$0.20-0.50 per video | **Time:** 5-8 minutes

Use `--editorial-model gpt-4o-mini` for ~60% cost savings with similar quality.

## 📐 Platform Formatting

Format clips for any social media platform with optimal specs:

| Platform | Resolution | Aspect Ratio | Max Duration | Max Size |
|----------|-----------|--------------|--------------|----------|
| TikTok | 1080×1920 | 9:16 | 180s | 287MB |
| Instagram Reels | 1080×1920 | 9:16 | 90s | 100MB |
| YouTube Shorts | 1080×1920 | 9:16 | 60s | 100MB |
| YouTube | 1920×1080 | 16:9 | Unlimited | 256GB |
| Instagram Feed | 1080×1080 | 1:1 | 60s | 100MB |
| Twitter/X | 1280×720 | 16:9 | 140s | 512MB |
| LinkedIn | 1920×1080 | 16:9 | 600s | 5GB |

**Features:**
- Smart cropping strategies (center, smart, top, bottom)
- Blur background padding for letterboxing
- Automatic aspect ratio conversion
- File size and duration validation
- Batch processing support

```bash
# Format single clip
arena format clip.mp4 -p tiktok -o tiktok/

# Batch format directory
arena format clips/ -p instagram-reels --crop smart -o reels/

# With blur background
arena format video.mp4 -p youtube --pad blur -o youtube/
```

## 💻 Architecture

Arena uses a hybrid TypeScript + Python architecture:

```
┌─────────────────────────────────────┐
│   Node.js CLI (TypeScript)          │
│   - Beautiful terminal UI            │
│   - Progress tracking                │
│   - Command routing                  │
└──────────────┬──────────────────────┘
               │ Python Bridge
┌──────────────▼──────────────────────┐
│   Python Engine                      │
│   - Video processing (FFmpeg)        │
│   - AI analysis (OpenAI)             │
│   - 4-layer editorial system         │
│   - Platform formatting              │
└─────────────────────────────────────┘
```

**Why Hybrid?**
- Node.js: Fast CLI, beautiful UX, modern tooling
- Python: Rich ecosystem for video/AI processing
- Best of both worlds

## 📦 Installation Details

### Prerequisites

- **Node.js** 22–24
- **Python 3.10–3.12** (used only to create Arena's private processing runtime)
- **FFmpeg** (for video encoding)
- **OpenAI API Key** (for AI-backed analysis; local-only utilities do not require one)

Node.js supplies yt-dlp's JavaScript runtime; Deno is not required.

### Install Node CLI

```bash
# Option 1: Install the current stable npm release
npm install --global @whitegodkingsley/arena-cli@0.4.2

# To follow the npm latest tag instead
npm install --global @whitegodkingsley/arena-cli

# Verify the CLI, then build and verify its private runtime
arena --version
arena setup
arena setup --check

# Option 2: Install from source
git clone https://github.com/iamwhitegod/arena.git
cd arena/cli
npm install
npm link

arena setup
arena setup --check
```

### Install Python Engine

Do not install Arena's Python packages globally. `arena setup` creates and verifies an isolated runtime under `~/.arena/runtime/environments/`. See the [installation guide](./docs/getting-started/installation.md) for repair, CI, source-install, and publishing details.

### Set Up API Key

```bash
# Option 1: Environment variable
export OPENAI_API_KEY="sk-..."

# Option 2: Via config command
arena config set openai_api_key "sk-..."

# Verify it's set
arena config get openai_api_key
```

## 🔧 Configuration

Global config is stored at `~/.arena/config.json`:

```json
{
  "openai_api_key": "sk-...",
  "whisper_mode": "api",
  "minDuration": 30,
  "maxDuration": 90,
  "editorialModel": "gpt-4o-mini"
}
```

Manage via CLI:

```bash
arena config                          # View current config
arena config get editorialModel       # Get specific value
arena config reset                    # Reset to defaults
```

## 📈 Cost Optimization

Typical costs per 10-minute video:

| Model | Cost | Time |
|-------|------|------|
| gpt-4o-mini | $0.20 | 5-8 min |
| gpt-4o | $0.50 | 5-8 min |

**Tips to reduce costs:**
- Use `--editorial-model gpt-4o-mini` (60% cheaper, same quality)
- Analyze first, generate later (reuse analysis)
- Cache transcripts (reuse for multiple runs)
- Use selective generation (`--select 1,3,5`)

## 🎓 Examples

### Content Creator Pipeline

```bash
# Generate captioned short-form clips for social media
arena process video.mp4 \
  --editorial-model gpt-4o-mini \
  -n 3 \
  --min 15 \
  --max 30 \
  --captions \
  -p tiktok
```

### Podcast Highlights

```bash
# From a YouTube podcast URL — extract 8 clips
arena process https://www.youtube.com/watch?v=PODCAST_ID \
  -n 8 \
  --min 60 \
  --max 120 \
  --captions

# Format for YouTube and LinkedIn
arena format output/clips/ -p youtube -o social/youtube/
arena format output/clips/ -p linkedin -o social/linkedin/
```

### Transcribe a Podcast Audio

```bash
# Transcribe an MP3, WAV, FLAC, or any audio format
arena transcribe podcast.mp3 -o transcript.json

# Transcribe from URL
arena transcribe https://www.youtube.com/watch?v=VIDEO_ID
```

### Course Creator

```bash
# Extract educational snippets with captions
arena process lecture.mp4 \
  -n 8 \
  --min 45 \
  --max 90 \
  --captions \
  --caption-color yellow
```

## 📖 Documentation

- [Documentation index](./docs/README.md) — authoritative documentation map
- [Quick start](./docs/getting-started/quickstart.md) — first installation and run
- [CLI reference](./docs/reference/cli.md) — commands and options
- [Workflow guide](./docs/guides/workflows.md) — common processing and publishing workflows
- [Troubleshooting](./docs/guides/troubleshooting.md) — diagnosis and recovery
- [Editorial architecture](./docs/architecture/editorial-system.md) — four-layer system design
- [Contributing](./CONTRIBUTING.md) — development and review process

## 🐳 Docker

End users run the published image; cloning the repository is not part of Docker installation. Arena `0.4.2` is available from [Docker Hub](https://hub.docker.com/r/whitegodkingsley/arena) for Linux AMD64 and ARM64:

```bash
docker pull whitegodkingsley/arena:0.4.2
docker run --rm \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
  --mount "type=bind,source=$PWD,target=/workspace" \
  --mount type=volume,source=arena-data,target=/home/node/.arena \
  --env OPENAI_API_KEY \
  whitegodkingsley/arena:0.4.2 process /workspace/video.mp4 -n 5
```

The `latest`, `0`, `0.4`, `0.4.2`, and immutable `sha-7f7fd269d130` tags resolve to OCI index digest `sha256:b1bfbc0ca0696d550ba5520a7fbff196721af6cd8a0643ec8d08e13583495b1b`. Pin `0.4.2` or the digest in automated deployments. Maintainers and contributors can build checked-out source with `docker compose build`; see the [installation guide](./docs/getting-started/installation.md) for the complete container security contract.

## 🛠️ Development

```bash
# Clone repository
git clone https://github.com/iamwhitegod/arena.git
cd arena

# Install CLI dependencies
cd cli
npm install

# Build TypeScript
npm run build

# Link globally for development
npm link

# Test
npm test

# Make changes and rebuild
npm run build
arena --version  # Test immediately
```

## 🐛 Troubleshooting

### "Command not found: arena"

```bash
# Reinstall globally
npm install --global @whitegodkingsley/arena-cli@0.4.2

# Or use the exact package without a global install
npx --yes @whitegodkingsley/arena-cli@0.4.2 setup
npx --yes @whitegodkingsley/arena-cli@0.4.2 process video.mp4
```

### "Python not found"

```bash
# macOS
brew install python@3.12

# Ubuntu
sudo apt install python3 python3-venv

# Then repair Arena's private runtime
arena setup --force
```

### "FFmpeg not found"

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg
```

### "No clips passed validation"

Your duration constraints may be too strict:

```bash
# Relax constraints
arena process video.mp4 --min 20 --max 90
```

See [Troubleshooting](./docs/guides/troubleshooting.md) for more solutions.

## 🚀 Roadmap

See the [Arena product roadmap](./docs/roadmap.md) for the maintained plan across Arena Terminal, Cloud, Desktop, and Mobile.

**Current (v0.4):**
- ✅ 11-command CLI
- ✅ 4-layer editorial system
- ✅ Multi-platform formatting
- ✅ Hybrid AI + energy analysis
- ✅ Scene change detection
- ✅ Automatic rate limit handling
- ✅ Cost optimization with gpt-4o-mini
- ✅ Caption/subtitle burning
- ✅ URL support (YouTube, Vimeo, Twitter, 1000+ sites)
- ✅ Audio file transcription (MP3, WAV, FLAC, etc.)
- ✅ Docker support

**Coming Soon:**
- [ ] Interactive clip review TUI
- [ ] Word-by-word animated captions (TikTok style)
- [ ] Cloud processing option
- [ ] Web dashboard
- [ ] Plugin system

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for details.

## 📄 License

MIT © Arena Contributors

## 🔗 Links

- **Website**: [getarena.vercel.app](https://getarena.vercel.app)
- **Documentation**: [getarena.vercel.app/docs](https://getarena.vercel.app/docs)
- **Issues**: [GitHub Issues](https://github.com/iamwhitegod/arena/issues)
- **Feedback**: [GitHub Issues](https://github.com/iamwhitegod/arena/issues)

---

**Made with ❤️ for content creators**

Turn 1 video into 25 social media posts in minutes, not hours.
