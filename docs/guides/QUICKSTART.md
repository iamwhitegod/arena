# Arena Quick Start Guide

Get started with Arena in 5 minutes! Generate professional video clips from long-form content.

## Prerequisites

1. **Node.js 18+** - Download from [nodejs.org](https://nodejs.org)
2. **Python 3.9+** - Check with `python3 --version`
3. **FFmpeg** - Install with `brew install ffmpeg` (macOS) or `apt install ffmpeg` (Ubuntu)
4. **OpenAI API Key** - Get from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

## Installation

### Option 1: Install from npm (when published)

```bash
npm install -g @arena/cli
```

### Option 2: Install from source

```bash
git clone <repository-url>
cd arena

# Install CLI
cd cli
npm install
npm run build
npm link

# Install Python engine
cd ../engine
pip install -r requirements.txt

# Verify installation
arena --version
```

## Setup

### Interactive Setup (Recommended)

```bash
arena init
```

This wizard helps you:
- Choose your workflow type (content creator, podcast, course)
- Set clip duration preferences
- Configure quality vs cost balance
- Set up your OpenAI API key

### Manual Setup

```bash
# Set API key via environment
export OPENAI_API_KEY="sk-..."

# Or set via config
arena config set openai_api_key "sk-..."
```

## Quick Start: Generate Your First Clips

### 1. Basic Usage (All-in-One)

```bash
arena process video.mp4
```

This generates 5 clips (30-90s each) using standard mode.

### 2. Professional Quality (Recommended)

```bash
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini
```

Uses the 4-layer editorial system for professional-grade clips with cost optimization.

### 3. Customize Parameters

```bash
# Generate 10 short clips for TikTok/Reels
arena process video.mp4 --use-4layer -n 10 --min 15 --max 30

# Generate 8 longer clips for YouTube/LinkedIn
arena process video.mp4 --use-4layer -n 8 --min 60 --max 120

# Custom output directory
arena process video.mp4 --use-4layer -o my_clips/

# Fast mode (10x faster, less precise cuts)
arena process video.mp4 --fast
```

## What Happens During Processing

### Step 1: Transcription (2-5 min)

```
🎤 Transcribing video with OpenAI Whisper...
✓ Transcription complete
  Duration: 520.3s
  Words: 920
```

The transcript is **cached** - subsequent runs are instant!

### Step 2: AI Analysis (30-60 sec or 3-5 min with 4-layer)

**Standard Mode:**
```
🧠 Analyzing transcript content with AI...
✓ Found 17 interesting content segments

⚡ Analyzing audio energy...
✓ Found 20 high-energy segments

🎯 Computing hybrid scores...
✓ Selected top 5 clips by hybrid score
```

**4-Layer Mode:**
```
🎯 4-Layer Editorial System

[1/4] 🔍 Layer 1: Candidate Detection
  ✓ Found 25 candidate moments

[2/4] 📐 Layer 2: Boundary Refinement
  ✓ Adjusted 25 boundaries

[3/4] ✅ Layer 3: Quality Validation
  ✓ Validated: 2 clips passed (8% pass rate)
  ✗ Rejected: 23 clips (incomplete context, references missing info)

[4/4] 📝 Layer 4: Content Packaging
  ✓ Generated professional titles and descriptions
```

The 4-layer system applies strict quality gates - only 7-10% of candidates pass!

### Step 3: Clip Generation (1-3 min)

```
🎬 Generating 2 clips...
   [1/2] ✓ questions-to-ask-before-learning-tech-skills (46s)
   [2/2] ✓ how-to-define-your-tech-goals-as-an-engineer (46s)

✓ Clip generation complete
```

## Output Structure

```
output/
├── clips/
│   ├── questions-to-ask-before-learning-tech-skills.mp4
│   ├── how-to-define-your-tech-goals-as-an-engineer.mp4
│   └── ...
├── analysis.json                    # Complete analysis
└── .cache/
    └── video_transcript.json        # Cached transcript
```

With 4-layer system (`--export-editorial-layers`):
```
output/
├── clips/
│   └── ...
├── editorial_layers/
│   ├── layer1_candidates.json       # 25 initial moments
│   ├── layer2_refined.json          # Boundary adjustments
│   ├── layer3_validated.json        # Quality validation
│   └── layer4_final.json            # Final packaged clips
└── analysis.json
```

## Review Your Clips

```bash
# List generated clips
ls -lh output/clips/

# Get clip metadata
cat output/analysis.json | jq '.clips[] | {title, duration, scores}'
```

Example output:
```json
{
  "title": "Questions to ask before learning tech skills",
  "duration": 46.2,
  "scores": {
    "ai_score": 0.92,
    "hybrid_score": 0.95,
    "standalone_score": 0.85
  }
}
```

## Next Steps

### Option 1: Try Different Parameters

```bash
# Analyze without generating (fast preview)
arena analyze video.mp4 --use-4layer -o moments.json

# Review moments.json

# Generate only selected clips
arena generate video.mp4 moments.json --select 1,3,5
```

### Option 2: Format for Social Media

```bash
# Format clips for TikTok
arena format output/clips/ -p tiktok --crop smart -o social/tiktok/

# Format for Instagram Reels
arena format output/clips/ -p instagram-reels --crop smart -o social/reels/

# Format for YouTube
arena format output/clips/ -p youtube -o social/youtube/
```

Now you have clips optimized for every platform!

### Option 3: Batch Processing

```bash
# Process multiple videos
for video in videos/*.mp4; do
  echo "Processing: $video"
  arena process "$video" --use-4layer --editorial-model gpt-4o-mini -n 5
done
```

## Understanding 4-Layer vs Standard

### Standard Mode

**Best for:** Testing, experimentation, quick iteration

```bash
arena process video.mp4
```

- Fast (2-4 minutes)
- Cheap ($0.05 per 10min video)
- Good quality
- 50%+ clips pass basic filters

### 4-Layer Mode

**Best for:** Production, distribution, professional quality

```bash
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini
```

- Professional quality (5-8 minutes)
- Affordable ($0.20 per 10min video with gpt-4o-mini)
- Strict quality validation
- 7-10% clips pass all gates
- Standalone context validated
- Professional titles/descriptions

## Common Commands Reference

| Task | Command |
|------|---------|
| **Generate clips** | `arena process video.mp4 --use-4layer` |
| **Analyze only** | `arena analyze video.mp4 --use-4layer -o moments.json` |
| **Generate from analysis** | `arena generate video.mp4 moments.json --select 1,3,5` |
| **Format for TikTok** | `arena format clips/ -p tiktok -o tiktok/` |
| **Transcribe only** | `arena transcribe video.mp4` |
| **Extract audio** | `arena extract-audio video.mp4` |
| **View config** | `arena config` |
| **Set API key** | `arena config set openai_api_key "sk-..."` |

## Cost Estimates

Typical costs per 10-minute video:

| Mode | Model | Cost | Time |
|------|-------|------|------|
| Standard | gpt-4o-mini | $0.05 | 2-4 min |
| 4-Layer | gpt-4o-mini | $0.20 | 5-8 min |
| 4-Layer | gpt-4o | $0.50 | 5-8 min |

**Cost-saving tips:**
- Use `--editorial-model gpt-4o-mini` (60% cheaper, same quality)
- Analyze first, generate later (reuse analysis)
- Transcribe once, experiment with parameters

## Troubleshooting

### "Command not found: arena"

```bash
# Reinstall
npm install -g @arena/cli

# Or use npx
npx @arena/cli process video.mp4
```

### "OPENAI_API_KEY not set"

```bash
# Set via environment
export OPENAI_API_KEY="sk-..."

# Or via config
arena config set openai_api_key "sk-..."
```

### "No clips passed validation" (4-layer mode)

Your duration constraints may be too strict:

```bash
# Relax constraints
arena process video.mp4 --use-4layer --min 20 --max 90

# Or try standard mode first
arena process video.mp4 -n 10
```

### "FFmpeg not found"

```bash
# macOS
brew install ffmpeg

# Ubuntu
sudo apt install ffmpeg

# Verify
ffmpeg -version
```

## Real-World Examples

### Content Creator (TikTok/Reels)

```bash
arena process video.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 3 \
  --min 15 \
  --max 30

arena format output/clips/ -p tiktok --crop smart -o social/tiktok/
```

### Podcast Highlights

```bash
arena process podcast.mp4 \
  --use-4layer \
  --editorial-model gpt-4o-mini \
  -n 8 \
  --min 60 \
  --max 120

arena format output/clips/ -p youtube -o youtube/
arena format output/clips/ -p linkedin -o linkedin/
```

### Course Creator

```bash
arena process lecture.mp4 \
  --use-4layer \
  -n 8 \
  --min 45 \
  --max 90

arena format output/clips/ -p youtube -o youtube/
```

## Learn More

- **Complete Usage Guide**: [USAGE.md](./USAGE.md)
- **Command Reference**: [CLI_REFERENCE.md](./CLI_REFERENCE.md)
- **Setup Guide**: [SETUP.md](./SETUP.md)
- **Troubleshooting**: [../cli/docs/TROUBLESHOOTING.md](../../cli/docs/TROUBLESHOOTING.md)
- **Main README**: [../../README.md](../../README.md)

---

**Ready to create amazing clips?** Run `arena process video.mp4 --use-4layer` and watch the magic happen! ✨
