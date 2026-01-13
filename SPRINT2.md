# Sprint 2 Complete: Transcription & AI Analysis

Sprint 2 has been implemented! Arena can now transcribe videos and use AI to identify the most interesting segments for clips.

## What's New

### ✓ Audio Extraction & Transcription
- Extract audio from video using FFmpeg
- Transcribe with OpenAI Whisper API
- Word-level and segment-level timestamps
- Support for both API and local Whisper models
- Automatic caching to save time and costs

### ✓ AI Content Analysis
- GPT-4o powered transcript analysis
- Identifies engaging segments automatically
- Generates compelling titles for each clip
- Scores segments by interest level (0-1)
- Categorizes content types (hook, insight, advice, etc.)

### ✓ Scoring & Ranking
- Unified scoring algorithm
- Filters overlapping segments
- Ranks clips by engagement potential
- Selects top N clips based on your preferences

### ✓ Smart Caching
- Transcripts cached in `.arena/cache/`
- Reuse cached transcripts to save API costs
- Only re-transcribe if video changes

## Files Modified/Created

**New Files:**
- `engine/arena/clipping/scorer.py` - Scoring algorithm

**Updated Files:**
- `engine/arena/audio/transcriber.py` - Full Whisper integration
- `engine/arena/ai/analyzer.py` - GPT-4 content analysis
- `engine/arena/main.py` - Complete pipeline integration

## Testing Sprint 2

### Prerequisites

1. **Install Python dependencies:**
```bash
cd engine
pip install -r requirements.txt
```

2. **Set your OpenAI API key:**
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

3. **Make sure FFmpeg is installed:**
```bash
ffmpeg -version
```

### Run a Test

```bash
# From the CLI directory
cd cli
npm install  # If you haven't already
npm run dev process path/to/your/video.mp4
```

### What You'll Get

After processing, check `.arena/output/`:

```
.arena/
├── cache/
│   └── transcript.json           # Cached transcript (reusable!)
└── output/
    ├── metadata.json              # Clip recommendations with scores
    ├── transcript.json            # Full transcript with timestamps
    └── clips/                     # (Empty for now - Sprint 4 will fill this)
```

### Example metadata.json

```json
{
  "source_video": "my-talk.mp4",
  "duration": 3600,
  "clips": [
    {
      "id": "clip_001",
      "start_time": 125.3,
      "end_time": 168.7,
      "duration": 43.4,
      "title": "Why most startups fail at product-market fit",
      "reason": "Strong hook with controversial insight",
      "interest_score": 0.95,
      "content_type": "insight",
      "scores": {
        "ai_interest": 0.95,
        "audio_energy": 0.0,
        "visual_change": 0.0,
        "combined": 0.95
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

## Cost Estimates

Per video:
- **Whisper API**: ~$0.006 per minute of audio
- **GPT-4o**: ~$0.05-0.15 per analysis (depends on transcript length)

**Example**: A 60-minute video costs approximately $0.36-0.51 to process.

**Caching saves money**: Second run is free! The transcript is cached.

## What Works Right Now

✅ Process any video format supported by FFmpeg
✅ Automatic transcription with word-level timestamps
✅ AI identifies 5-10 interesting segments
✅ Generates compelling titles for each clip
✅ Scores and ranks clips by engagement
✅ Filters overlapping segments
✅ Exports metadata JSON
✅ Caches transcripts for reuse

## What's Coming Next

### Sprint 3: Multi-Modal Detection
- Audio energy detection (speaker enthusiasm)
- Scene change detection (visual interest)
- Combined scoring with all three signals

### Sprint 4: Clip Generation
- Extract actual video segments
- Generate and burn subtitles
- Create thumbnails
- Full export pipeline

### Sprint 5: Multi-Step Pipeline
- `arena analyze` - just analyze, don't generate
- `arena review` - interactive clip selection
- `arena generate` - generate only selected clips
- `arena config` - settings management

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"
```bash
export OPENAI_API_KEY="sk-your-actual-key"
```

Or add to your global config:
```bash
# Edit ~/.arena/config.json
{
  "openai_api_key": "sk-your-key-here",
  ...
}
```

### "FFmpeg is not installed"
Install FFmpeg:
- macOS: `brew install ffmpeg`
- Ubuntu: `sudo apt install ffmpeg`
- Windows: Download from ffmpeg.org

### "openai package is required"
```bash
cd engine
pip install openai
```

### Transcription is slow
First run always takes time for transcription. Subsequent runs use the cache and are much faster!

To force re-transcription, delete the cache:
```bash
rm -rf .arena/cache/transcript.json
```

### AI analysis gives weird results
The AI prompt is tuned for developer/startup/technical content. If your content is different, you can modify the prompt in `engine/arena/ai/analyzer.py` line ~80.

## Testing Checklist

- [ ] Run with a video file
- [ ] Check transcript.json is created
- [ ] Verify metadata.json has clip recommendations
- [ ] Check cache directory has transcript
- [ ] Run again to test cache (should be instant!)
- [ ] Try different clip counts: `--clips 5` vs `--clips 15`
- [ ] Test duration ranges: `--min-duration 20 --max-duration 60`

## API Usage Tips

1. **Start with short videos** (5-10 min) while testing
2. **Cache is your friend** - the first run costs money, subsequent runs are free
3. **Use gpt-4o-mini** for testing if you want to save money (edit `analyzer.py` line 10)
4. **Local Whisper** - Set `whisper_mode: "local"` in config for free transcription (but slower)

## Next Steps

1. **Test with your own video** to see the AI analysis quality
2. **Review the metadata.json** to see what clips were identified
3. **Adjust parameters** if needed (clip count, duration ranges)
4. **Ready for Sprint 3?** Let me know when you want to add audio energy and scene detection!

---

Sprint 2 is complete and ready to use! 🎉
