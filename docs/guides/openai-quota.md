# OpenAI API Quota Solutions

You exceeded your OpenAI API quota. Here are your options:

## Option 1: Use Local Whisper (Free Transcription!)

Local Whisper is **FREE** but uses your CPU/GPU instead of the API.

### Setup (in progress):

```bash
# Installing now... wait for completion
cd engine
pip install openai-whisper  # Running in background
```

### Once installed, use local mode:

```bash
# Set environment variable to use local Whisper
export ARENA_WHISPER_MODE="local"

# You still need OpenAI API key for GPT-4 analysis
# But it costs much less (~$0.05-0.15 per video vs $0.36-0.51 total)
export OPENAI_API_KEY="sk-your-key"  # Keep for AI analysis

# Process video
cd cli
npm run dev process /path/to/video.mp4
```

### Cost Comparison:

| Mode | Transcription Cost | AI Analysis Cost | Total (60min video) |
|------|-------------------|------------------|---------------------|
| **API Mode** | $0.36 | $0.10 | **$0.46** |
| **Local Mode** | FREE | $0.10 | **$0.10** ⭐ |

## Option 2: Add Credits to OpenAI

1. Go to: https://platform.openai.com/settings/organization/billing
2. Click "Add payment method"
3. Add $5-10 in credits (plenty for many videos)
4. Wait a few minutes for activation
5. Run Arena normally

### API Mode (default):

```bash
export OPENAI_API_KEY="sk-your-key-with-credits"
# No need to set ARENA_WHISPER_MODE

cd cli
npm run dev process /path/to/video.mp4
```

## Option 3: Hybrid Mode

**Best of both worlds**: Free transcription + AI analysis

```bash
# Use local Whisper (free) but OpenAI for AI analysis
export ARENA_WHISPER_MODE="local"
export OPENAI_API_KEY="sk-your-key"  # Need for GPT-4 analysis

cd cli
npm run dev process /path/to/video.mp4
```

This costs ~$0.10 per video instead of $0.46!

## What Requires OpenAI API?

- ✅ **Whisper transcription** - Can use local mode (free)
- ❌ **GPT-4 analysis** - REQUIRES OpenAI API (no local alternative yet)

**Bottom line**: You need at least some OpenAI credits for the AI analysis part. But using local Whisper saves ~75% on costs!

## Checking Your Status

Check if local Whisper is installed:

```bash
cd engine
python3 -c "import whisper; print('✓ Local Whisper ready!')"
```

Check OpenAI credits:
- Visit: https://platform.openai.com/usage
- Need at least $0.10-0.20 for one video analysis

## Troubleshooting

### "insufficient_quota" error

Your OpenAI account has no credits. Options:
1. Add payment method at platform.openai.com
2. Use local Whisper to reduce costs (still need $0.10+ for AI)

### Local Whisper is slow

First run downloads the model (~100MB). After that:
- Base model: ~2-3x realtime (10min video = 20-30min processing)
- Tiny model: ~1x realtime (faster but less accurate)

To use tiny model, edit `engine/arena/audio/transcriber.py` line 77:
```python
model = whisper.load_model("tiny")  # Change from "base"
```

### "ImportError: No module named 'whisper'"

Wait for pip install to complete, or run:
```bash
cd engine
pip install openai-whisper
```

## Recommended Setup for Cost Savings

```bash
# ~/.zshrc or ~/.bashrc
export ARENA_WHISPER_MODE="local"  # Free transcription
export OPENAI_API_KEY="sk-your-key"  # For AI analysis only

# Add $5-10 credits for ~50-100 video analyses
```

Then just run:
```bash
arena process video.mp4  # Uses local Whisper + OpenAI AI
```

---

**Next Steps**: Once the pip install completes, try local mode!
