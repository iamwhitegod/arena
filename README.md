# Arena

> AI-powered video clip generation for the terminal - Turn long-form content into viral clips

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Arena is a professional video clip generation tool that uses AI to automatically identify and extract the best moments from your long-form content. Perfect for content creators, podcasters, course producers, and anyone who wants to repurpose their content for social media.

## ✨ Features

### 🎯 **4-Layer Editorial System**
Professional-grade clip generation with quality validation:
- **Layer 1:** Detect interesting moments (hooks, insights, stories)
- **Layer 2:** Expand to complete thought boundaries
- **Layer 3:** Validate standalone context (strict quality gate)
- **Layer 4:** Package with titles, descriptions, and hashtags

### 📐 **Multi-Platform Formatting**
Convert clips for any social media platform with optimal specs:
- TikTok, Instagram Reels, YouTube Shorts (9:16 vertical)
- YouTube, LinkedIn (16:9 horizontal)
- Instagram Feed (1:1 square)
- Smart cropping and blur background padding

### 🎬 **Hybrid AI + Energy Analysis**
- AI content analysis finds engaging narratives
- Audio energy detection identifies enthusiastic delivery
- Combined scoring for clips with great content AND delivery

### 🚀 **Production-Ready CLI**
- 8 powerful commands for flexible workflows
- Beautiful progress tracking with multi-stage visualization
- Automatic rate limit handling with intelligent retry
- TypeScript + Python architecture for speed and power

### 💰 **Cost-Optimized**
- Smart caching saves time and money
- Support for gpt-4o-mini (~60% cheaper than gpt-4o)
- Typical cost: $0.05-0.50 per video depending on quality settings

## 🚀 Quick Start

### Installation

```bash
# Install CLI globally via npm
npm install -g @arena/cli

# Or clone the repository
git clone <repository-url>
cd arena
npm install -g ./cli

# Set up your OpenAI API key
export OPENAI_API_KEY="sk-..."
```

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
# All-in-one: Generate professional clips
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 5

# Format for TikTok
arena format output/clips/ -p tiktok -o tiktok/

# Format for Instagram Reels
arena format output/clips/ -p instagram-reels -o reels/
```

## 📚 Commands

Arena provides 8 commands for flexible video clip generation workflows:

| Command | Purpose | Example |
|---------|---------|---------|
| `arena init` | Interactive setup wizard | `arena init` |
| `arena process` | All-in-one processing | `arena process video.mp4 --use-4layer` |
| `arena transcribe` | Transcription only | `arena transcribe video.mp4` |
| `arena analyze` | Find moments (no video generation) | `arena analyze video.mp4 --use-4layer` |
| `arena generate` | Generate clips from analysis | `arena generate video.mp4 analysis.json` |
| `arena format` | Format for social platforms | `arena format clips/ -p tiktok` |
| `arena config` | Manage configuration | `arena config set openai_api_key "sk-..."` |
| `arena extract-audio` | Extract audio from video | `arena extract-audio video.mp4` |

See [docs/guides/USAGE.md](./docs/guides/USAGE.md) for comprehensive documentation.

## 🎯 Workflows

### Workflow 1: Quick Clips

```bash
# Generate 5 professional clips
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 5
```

**Cost:** ~$0.20 | **Time:** 5-8 minutes

### Workflow 2: Review Before Generate

```bash
# Step 1: Analyze (fast, cheap)
arena analyze video.mp4 --use-4layer -n 10 -o moments.json

# Step 2: Review moments.json

# Step 3: Generate only the best
arena generate video.mp4 moments.json --select 1,3,5,7
```

**Benefits:** Review quality before generating, save processing time

### Workflow 3: Multi-Platform Distribution

```bash
# Step 1: Generate high-quality clips
arena process video.mp4 --use-4layer -n 5

# Step 2: Format for each platform
arena format output/clips/ -p tiktok -o social/tiktok/
arena format output/clips/ -p instagram-reels -o social/reels/
arena format output/clips/ -p youtube-shorts -o social/shorts/
arena format output/clips/ -p youtube -o social/youtube/
```

**Result:** 1 video → 5 clips → 4 platforms = 20 optimized videos!

## 📊 4-Layer Editorial System

The optional 4-layer system applies professional editorial standards:

**Standard Mode** (Fast & Cheap)
- AI analyzes transcript for interesting moments
- Generates clips with basic metadata
- ~$0.05 per video, 2-4 minutes
- Good for experimentation

**4-Layer Mode** (Professional Quality)
- Layer 1: Find 25 candidate moments
- Layer 2: Expand to complete thought boundaries
- Layer 3: Validate standalone context (7-10% pass rate)
- Layer 4: Package with professional titles/descriptions
- ~$0.20-0.50 per video, 5-8 minutes
- Production-ready clips

### When to Use 4-Layer

✅ **Use 4-Layer when:**
- You need professional-quality clips for distribution
- Standalone context matters (viewers clicking from feeds)
- You want better titles and descriptions
- Quality > cost is your priority

❌ **Use Standard when:**
- You're experimenting/testing
- You need fast iteration
- Cost is primary concern
- You'll manually review clips anyway

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

- **Node.js** 18 or higher
- **Python 3.9+** (for video processing engine)
- **FFmpeg** (for video encoding)
- **OpenAI API Key** (for AI analysis)

### Install Node CLI

```bash
# Option 1: Install from npm (when published)
npm install -g @arena/cli

# Option 2: Install from source
git clone <repository-url>
cd arena
npm install -g ./cli

# Verify installation
arena --version
arena --help
```

### Install Python Engine

```bash
cd engine
pip install -r requirements.txt

# Verify FFmpeg is installed
ffmpeg -version
```

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
  "use4Layer": true,
  "editorialModel": "gpt-4o-mini"
}
```

Manage via CLI:

```bash
arena config                          # View current config
arena config set use4Layer true       # Enable 4-layer
arena config get editorialModel       # Get specific value
arena config reset                    # Reset to defaults
```

## 📈 Cost Optimization

Typical costs per 10-minute video:

| Mode | Model | Cost | Time |
|------|-------|------|------|
| Standard | gpt-4o-mini | $0.05 | 2-4 min |
| 4-Layer | gpt-4o-mini | $0.20 | 5-8 min |
| 4-Layer | gpt-4o | $0.50 | 5-8 min |

**Tips to reduce costs:**
- Use `--editorial-model gpt-4o-mini` (60% cheaper, same quality)
- Analyze first, generate later (reuse analysis)
- Cache transcripts (reuse for multiple runs)
- Use selective generation (`--select 1,3,5`)

## 🎓 Examples

### Content Creator Pipeline

```bash
# Generate short-form clips for social media
arena process video.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 3 \
  --min 15 \
  --max 30

# Format for TikTok
arena format output/clips/ -p tiktok --crop smart -o social/tiktok/
```

### Podcast Highlights

```bash
# Extract 8 longer clips from podcast
arena process podcast.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 8 \
  --min 60 \
  --max 120

# Format for YouTube and LinkedIn
arena format output/clips/ -p youtube -o social/youtube/
arena format output/clips/ -p linkedin -o social/linkedin/
```

### Course Creator

```bash
# Extract educational snippets
arena process lecture.mp4 \
  --use-4layer \
  -n 8 \
  --min 45 \
  --max 90

# Format for YouTube (keep horizontal)
arena format output/clips/ -p youtube -o youtube/
```

## 📖 Documentation

- [USAGE.md](./docs/guides/USAGE.md) - Comprehensive usage guide
- [TROUBLESHOOTING.md](./cli/docs/TROUBLESHOOTING.md) - Common issues and solutions
- [CONTRIBUTING.md](./cli/CONTRIBUTING.md) - Contribution guidelines
- [EDITORIAL_ARCHITECTURE.md](./docs/architecture/EDITORIAL_ARCHITECTURE.md) - 4-layer system details

## 🛠️ Development

```bash
# Clone repository
git clone <repository-url>
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
npm install -g @arena/cli

# Or use npx
npx @arena/cli process video.mp4
```

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

### "No clips passed validation"

Your duration constraints may be too strict:

```bash
# Relax constraints
arena process video.mp4 --use-4layer --min 20 --max 90
```

See [TROUBLESHOOTING.md](./cli/docs/TROUBLESHOOTING.md) for more solutions.

## 🚀 Roadmap

**Current (v0.1.0):**
- ✅ 8-command CLI
- ✅ 4-layer editorial system
- ✅ Multi-platform formatting
- ✅ Hybrid AI + energy analysis
- ✅ Automatic rate limit handling
- ✅ Cost optimization with gpt-4o-mini

**Coming Soon:**
- [ ] Interactive clip review TUI
- [ ] Subtitle burning with custom styles
- [ ] Scene change detection
- [ ] Cloud processing option
- [ ] Web dashboard
- [ ] Plugin system

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](./cli/CONTRIBUTING.md) for details.

## 📄 License

MIT © Arena Contributors

## 🔗 Links

- **Documentation**: [docs/guides/USAGE.md](./docs/guides/USAGE.md)
- **Issues**: [GitHub Issues](https://github.com/YOUR_USERNAME/arena/issues)
- **Discussions**: [GitHub Discussions](https://github.com/YOUR_USERNAME/arena/discussions)

---

**Made with ❤️ for content creators**

Turn 1 video into 25 social media posts in minutes, not hours.
