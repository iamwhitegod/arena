# Arena Setup Guide

## Prerequisites

- **Node.js 18+**: [Download](https://nodejs.org/)
- **Python 3.9+**: [Download](https://www.python.org/downloads/)
- **FFmpeg**: Required for video processing

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

## Installation

### 1. Clone and Navigate
```bash
cd arena
```

### 2. Install CLI Dependencies
```bash
cd cli
npm install
npm run build
cd ..
```

### 3. Install Python Dependencies
```bash
cd engine
pip install -r requirements.txt
# Or use a virtual environment (recommended):
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cd ..
```

### 4. Link CLI Globally (Optional)
```bash
cd cli
npm link
```

Now you can use `arena` from anywhere!

## Configuration

### Set up OpenAI API Key

Arena uses OpenAI for transcription and content analysis. You need an API key:

1. Get your API key from [platform.openai.com](https://platform.openai.com/api-keys)
2. Create global config:

```bash
mkdir -p ~/.arena
cat > ~/.arena/config.json << EOF
{
  "openai_api_key": "sk-your-api-key-here",
  "whisper_mode": "api",
  "clip_duration": [30, 90],
  "output_format": "mp4"
}
EOF
```

Or set as environment variable:
```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

## Quick Start

### Process a Video

```bash
# If linked globally:
arena process path/to/video.mp4

# Or run directly:
cd cli
npm run dev process path/to/video.mp4
```

### Options

```bash
arena process video.mp4 \
  --output .arena/output \
  --clips 10 \
  --min-duration 30 \
  --max-duration 90
```

## Development

### CLI Development

```bash
cd cli
npm run dev          # Run with tsx (no build needed)
npm run watch        # Watch mode for TypeScript
npm run build        # Build for production
```

### Python Engine Development

```bash
cd engine
python3 -m arena.main process video.mp4 --output-dir output
```

### Testing the Bridge

Test that Node.js can communicate with Python:

```bash
cd cli
npm run dev process test_video.mp4
```

## Project Structure

```
arena/
├── cli/                 # Node.js CLI (TypeScript)
│   ├── src/
│   │   ├── index.ts    # Entry point
│   │   ├── commands/   # Command implementations
│   │   ├── bridge/     # Python bridge
│   │   ├── core/       # Config & workspace
│   │   └── ui/         # Progress UI
│   └── package.json
│
├── engine/              # Python processing engine
│   ├── arena/
│   │   ├── main.py     # Entry point
│   │   ├── video/      # Video processing
│   │   ├── audio/      # Audio analysis
│   │   ├── ai/         # AI analysis
│   │   └── ...
│   └── requirements.txt
│
└── .arena/              # Created when you run arena
    ├── config.json      # Project config
    ├── cache/           # Cached data
    └── output/          # Generated clips
        └── clips/
```

## Troubleshooting

### "Python 3 is not installed"

Make sure Python 3.9+ is installed and in your PATH:
```bash
python3 --version
```

### "Python dependencies not installed"

```bash
cd engine
pip install -r requirements.txt
```

### "FFmpeg not found"

Install FFmpeg using instructions above, then verify:
```bash
ffmpeg -version
```

### Module import errors

Make sure you're running from the correct directory and PYTHONPATH is set:
```bash
cd engine
export PYTHONPATH=$(pwd)
python3 -m arena.main --help
```

## Next Steps

1. Read the [implementation plan](/Users/whitegodkingsley/.claude/plans/ancient-doodling-adleman.md)
2. Check out the [README](./README.md)
3. Start developing Sprint 2 features (transcription & analysis)

## Support

For issues or questions:
- Open an issue on GitHub
- Check documentation
- Review the implementation plan
