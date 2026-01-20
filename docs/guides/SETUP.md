# Arena Setup Guide

Complete setup instructions for Arena CLI - from installation to first clip.

## Prerequisites

- **Node.js 18+**: [Download](https://nodejs.org/)
- **Python 3.9+**: [Download](https://www.python.org/downloads/)
- **FFmpeg**: Required for video processing
- **OpenAI API Key**: Get from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

### Installing FFmpeg

**macOS (with Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) or use:
```bash
winget install ffmpeg
```

**Verify Installation:**
```bash
ffmpeg -version
```

## Installation

### Option 1: Install from npm (when published)

```bash
npm install -g @arena/cli
```

That's it! Skip to [Configuration](#configuration).

### Option 2: Install from Source

#### 1. Clone and Navigate

```bash
git clone https://github.com/iamwhitegod/arena.git
cd arena
```

#### 2. Install CLI Dependencies

```bash
cd cli
npm install
npm run build
cd ..
```

#### 3. Install Python Dependencies

```bash
cd engine
pip install -r requirements.txt

# Or use a virtual environment (recommended):
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

#### 4. Link CLI Globally

```bash
cd cli
npm link
```

Now you can use `arena` from anywhere!

**Verify Installation:**
```bash
arena --version
arena --help
```

## Configuration

### Option 1: Interactive Setup (Recommended)

```bash
arena init
```

This wizard guides you through:
- Workflow type selection (content creator, podcast, course)
- Clip duration preferences
- Quality vs cost balance
- OpenAI API key setup

### Option 2: Manual Configuration

**Via CLI Command:**
```bash
arena config set openai_api_key "sk-your-api-key-here"
```

**Via Environment Variable:**
```bash
export OPENAI_API_KEY="sk-your-api-key-here"

# Add to ~/.bashrc or ~/.zshrc for persistence:
echo 'export OPENAI_API_KEY="sk-your-api-key-here"' >> ~/.bashrc
source ~/.bashrc
```

**Via Config File:**
```bash
mkdir -p ~/.arena
cat > ~/.arena/config.json << EOF
{
  "openai_api_key": "sk-your-api-key-here",
  "whisper_mode": "api",
  "minDuration": 30,
  "maxDuration": 90,
  "use4Layer": true,
  "editorialModel": "gpt-4o-mini"
}
EOF
```

**View Current Config:**
```bash
arena config
```

## Quick Start

### Generate Your First Clips

**Basic (Standard Mode):**
```bash
arena process video.mp4
```

**Professional Quality (Recommended):**
```bash
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 5
```

**Custom Parameters:**
```bash
# Short clips for TikTok/Reels
arena process video.mp4 --use-4layer -n 10 --min 15 --max 30

# Longer clips for YouTube/LinkedIn
arena process video.mp4 --use-4layer -n 8 --min 60 --max 120

# Custom output directory
arena process video.mp4 --use-4layer -o my_clips/

# Fast mode (10x faster)
arena process video.mp4 --fast
```

### Format for Social Media

```bash
# Format for TikTok
arena format output/clips/ -p tiktok --crop smart -o social/tiktok/

# Format for Instagram Reels
arena format output/clips/ -p instagram-reels --crop smart -o social/reels/

# Format for YouTube
arena format output/clips/ -p youtube -o social/youtube/
```

### All Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `arena init` | Interactive setup | `arena init` |
| `arena process` | All-in-one processing | `arena process video.mp4 --use-4layer` |
| `arena transcribe` | Transcription only | `arena transcribe video.mp4` |
| `arena analyze` | Find moments | `arena analyze video.mp4 --use-4layer` |
| `arena generate` | Generate from analysis | `arena generate video.mp4 analysis.json` |
| `arena format` | Format for platforms | `arena format clips/ -p tiktok` |
| `arena config` | Manage configuration | `arena config` |
| `arena extract-audio` | Extract audio | `arena extract-audio video.mp4` |

## Development

### CLI Development

```bash
cd cli

# Run with tsx (no build needed)
npm run dev process video.mp4

# Watch mode for TypeScript
npm run watch

# Build for production
npm run build

# Run tests (when implemented)
npm test
```

### Python Engine Development

```bash
cd engine

# Run Python CLI directly
./arena-cli process video.mp4 --use-4layer

# Or via Python module
python3 -m arena.cli.main process video.mp4
```

### Testing the Bridge

Test that Node.js can communicate with Python:

```bash
cd cli
npm run dev process test_video.mp4
```

Should see:
```
✓ Checking Python environment...
✓ Checking dependencies...
✓ Initializing workspace...
🎤 Transcribing video...
```

## Project Structure

```
arena/
├── cli/                    # Node.js CLI (TypeScript)
│   ├── src/
│   │   ├── index.ts       # Entry point
│   │   ├── commands/      # All 8 commands
│   │   │   ├── init.ts
│   │   │   ├── process.ts
│   │   │   ├── analyze.ts
│   │   │   ├── transcribe.ts
│   │   │   ├── generate.ts
│   │   │   ├── format.ts
│   │   │   ├── config.ts
│   │   │   └── extract-audio.ts
│   │   ├── bridge/        # Python bridge
│   │   │   └── python-bridge.ts
│   │   ├── core/          # Config & workspace
│   │   └── ui/            # Progress UI
│   ├── dist/              # Built output
│   └── package.json
│
├── engine/                 # Python processing engine
│   ├── arena/
│   │   ├── cli/           # CLI commands
│   │   │   ├── main.py
│   │   │   └── commands/
│   │   ├── analysis/      # AI analysis
│   │   │   ├── analyzer.py
│   │   │   └── editorial_layers.py  # 4-layer system
│   │   ├── audio/         # Audio processing
│   │   ├── video/         # Video processing
│   │   ├── export/        # Export & formatting
│   │   │   ├── exporter.py
│   │   │   └── platform_formatter.py  # 7 platforms
│   │   └── transcription/ # Whisper integration
│   ├── arena-cli          # Executable entry point
│   └── requirements.txt
│
├── docs/                   # Documentation
│   ├── guides/
│   │   ├── USAGE.md
│   │   ├── QUICKSTART.md
│   │   ├── SETUP.md (this file)
│   │   └── CLI_REFERENCE.md
│   └── architecture/
│       └── EDITORIAL_ARCHITECTURE.md
│
└── output/                 # Created when you run arena
    ├── clips/             # Generated video clips
    ├── analysis.json      # Analysis results
    └── .cache/            # Cached data (transcripts, etc.)
        └── video_transcript.json
```

## Troubleshooting

### "Command not found: arena"

**If installed from source:**
```bash
cd cli
npm link

# Verify
arena --version
```

**If installed from npm:**
```bash
npm install -g @arena/cli

# Or use npx
npx @arena/cli process video.mp4
```

### "Python 3 is not installed"

Make sure Python 3.9+ is installed and in your PATH:
```bash
python3 --version

# Should output: Python 3.9.x or higher
```

**Install Python:**
- macOS: `brew install python3`
- Ubuntu: `sudo apt install python3`
- Windows: Download from [python.org](https://www.python.org/downloads/)

### "Python dependencies not installed"

```bash
cd engine
pip install -r requirements.txt

# Verify
python3 -c "import openai; print('OK')"
```

### "FFmpeg not found"

Install FFmpeg using instructions above, then verify:
```bash
ffmpeg -version

# Should show FFmpeg version info
```

### "OPENAI_API_KEY not set"

```bash
# Set via environment
export OPENAI_API_KEY="sk-..."

# Or via config
arena config set openai_api_key "sk-..."

# Verify
arena config get openai_api_key
```

### "Permission denied" when running arena

```bash
# Fix permissions on built CLI
cd cli
chmod +x dist/index.js

# Or rebuild (postbuild script handles this)
npm run build
```

### Module import errors (Python)

Make sure you're running from the correct directory:
```bash
cd engine

# Python CLI should be executable
./arena-cli --help

# Or use Python module
python3 -m arena.cli.main --help
```

### "No clips passed validation" (4-layer mode)

This is normal! The 4-layer system has strict quality gates. Try:

```bash
# Relax duration constraints
arena process video.mp4 --use-4layer --min 20 --max 90

# Generate more candidates
arena process video.mp4 --use-4layer -n 10

# Or try standard mode first
arena process video.mp4 -n 10
```

## Platform-Specific Notes

### macOS

All features fully supported. Use Homebrew for dependencies:
```bash
brew install node python3 ffmpeg
```

### Linux (Ubuntu/Debian)

All features fully supported:
```bash
sudo apt update
sudo apt install nodejs npm python3 python3-pip ffmpeg
```

### Windows

Arena works on Windows with some caveats:
- Use WSL2 for best compatibility
- PowerShell or Git Bash recommended
- Path handling may differ (use forward slashes)

**WSL2 Setup:**
```bash
wsl --install
# Then follow Linux instructions inside WSL
```

## Next Steps

Now that Arena is set up:

1. **Generate your first clips**: [QUICKSTART.md](./QUICKSTART.md)
2. **Learn all commands**: [CLI_REFERENCE.md](./CLI_REFERENCE.md)
3. **Explore workflows**: [USAGE.md](./USAGE.md)
4. **Understand 4-layer system**: [EDITORIAL_ARCHITECTURE.md](../architecture/EDITORIAL_ARCHITECTURE.md)

### Recommended First Steps

```bash
# 1. Run interactive setup
arena init

# 2. Generate test clips
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini -n 3

# 3. Format for social media
arena format output/clips/ -p tiktok -o social/tiktok/

# 4. Explore other commands
arena --help
```

## Getting Help

- **Documentation**: Check [docs/guides/](.)
- **Command help**: `arena <command> --help`
- **Configuration**: `arena config`
- **GitHub Issues**: Report bugs or request features
- **Troubleshooting**: [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)

---

**Need more help?** Check out the full [documentation](.) or open an issue on GitHub.
