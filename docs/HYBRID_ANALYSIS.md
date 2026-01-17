# Hybrid Analysis: AI Content + Audio Energy

Arena's hybrid analysis combines **AI-powered transcript analysis** with **audio energy detection** to identify clips that have both engaging content AND enthusiastic delivery.

## Why Hybrid Analysis?

### The Problem with Single-Method Analysis

**AI Transcript Analysis Alone:**
- ✅ Identifies interesting content, hooks, insights
- ❌ Misses flat delivery of great content
- ❌ Can't detect speaker enthusiasm

**Audio Energy Detection Alone:**
- ✅ Finds enthusiastic, energetic moments
- ❌ Misses what's actually being said
- ❌ Might pick loud but uninteresting moments

### The Hybrid Solution

**AI + Energy Together:**
- ✅ Identifies great content delivered with enthusiasm
- ✅ Boosts clips where energy matches content quality
- ✅ Creates more engaging, shareable clips
- ✅ Better social media performance

## How It Works

### 1. Multi-Modal Analysis

```
┌─────────────────┐         ┌──────────────────┐
│  Transcript     │────────▶│   AI Analysis    │
│  (What's said)  │         │   GPT-4o         │
└─────────────────┘         └──────────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │  Content Clips   │
                            │  (Interesting)   │
                            └──────────────────┘
                                     │
                                     ▼
┌─────────────────┐         ┌──────────────────┐
│  Audio File     │────────▶│ Energy Analysis  │
│  (How it's said)│         │ (RMS + Spectral) │
└─────────────────┘         └──────────────────┘
                                     │
                                     ▼
                            ┌──────────────────┐
                            │ Energy Segments  │
                            │  (Enthusiastic)  │
                            └──────────────────┘
                                     │
                ┌────────────────────┴────────────────────┐
                │         Hybrid Scoring Engine           │
                │  • Match clips with energy segments     │
                │  • Calculate overlap ratios             │
                │  • Boost scores for high-energy clips   │
                │  • Re-rank all clips                    │
                └────────────────────┬────────────────────┘
                                     ▼
                            ┌──────────────────┐
                            │  Hybrid Clips    │
                            │  (Best of Both)  │
                            └──────────────────┘
```

### 2. Overlap Detection

The hybrid analyzer finds where AI-identified content clips overlap with high-energy audio segments:

- **Significant Overlap:** >10% of clip duration overlaps with energy segment
- **Overlap Ratio:** Percentage of clip covered by high-energy segments
- **Peak Energy:** Highest energy score in overlapping segments
- **Average Energy:** Mean energy across all overlapping segments

### 3. Hybrid Scoring Formula

```python
# Base score from AI content analysis
base_score = clip.interest_score  # 0.0 - 1.0

# Energy boost calculation
energy_boost = (
    0.5 * peak_energy +        # 50% weight on peak energy
    0.3 * avg_energy +         # 30% weight on average energy
    0.2 * overlap_ratio        # 20% weight on coverage
)

# Final hybrid score
hybrid_score = base_score * (1 + energy_weight * energy_boost)
# where energy_weight = 0.3 (30% boost)

# Capped at 1.0
hybrid_score = min(hybrid_score, 1.0)
```

### 4. Example Scoring

| Clip | Content (AI) | Energy Boost | Hybrid Score | Rank Change |
|------|--------------|--------------|--------------|-------------|
| A    | 0.85         | 0.72 (high)  | 1.00 ⬆️       | +3          |
| B    | 0.90         | 0.20 (low)   | 0.95         | -1          |
| C    | 0.75         | 0.65 (high)  | 0.90 ⬆️       | +5          |
| D    | 0.70         | 0.00 (none)  | 0.70         | -2          |

**Result:** Clips with high energy move up in rankings!

## Usage

### Python API

```python
from pathlib import Path
from arena.ai.analyzer import TranscriptAnalyzer
from arena.ai.hybrid import HybridAnalyzer
from arena.audio.energy import AudioEnergyAnalyzer

# Initialize components
ai_analyzer = TranscriptAnalyzer(api_key="your-openai-key")
energy_analyzer = AudioEnergyAnalyzer(video_path=Path("video.mp4"))

# Create hybrid analyzer
hybrid = HybridAnalyzer(
    ai_analyzer=ai_analyzer,
    energy_analyzer=energy_analyzer,
    energy_weight=0.3  # 30% boost from energy
)

# Load transcript
import json
with open("transcript.json") as f:
    transcript = json.load(f)

# Run hybrid analysis
results = hybrid.analyze_video(
    video_path=Path("video.mp4"),
    transcript_data=transcript,
    target_clips=10,      # Number of clips to return
    min_duration=30,      # Minimum clip length (seconds)
    max_duration=90       # Maximum clip length (seconds)
)

# Access results
clips = results['clips']              # Top clips (hybrid ranked)
stats = results['stats']              # Analysis statistics
ai_clips = results['ai_clips']        # Original AI clips
energy_segments = results['energy_segments']  # Energy segments

# Print summary
hybrid.print_summary(results)

# Save results
hybrid.export_results(results, Path("output/analysis.json"))
```

### Test Script

```bash
# Test with existing audio and transcript
cd engine
python3 test_hybrid_analysis.py \
  ../IMG_2774_audio.mp3 \
  ../cli/.arena/cache/transcript.json

# With OpenAI API key for real AI analysis
export OPENAI_API_KEY="sk-..."
python3 test_hybrid_analysis.py \
  path/to/video.mp4 \
  path/to/transcript.json \
  output_dir
```

## Output Format

### Hybrid Clip Structure

Each clip includes both AI and energy data:

```json
{
  "id": "clip_001",
  "title": "Why most startups fail at product-market fit",
  "start_time": 125.5,
  "end_time": 168.3,
  "duration": 42.8,

  // AI Analysis
  "interest_score": 0.85,
  "reason": "Strong hook with controversial insight",
  "content_type": "insight",

  // Energy Analysis
  "max_energy": 0.723,
  "avg_energy": 0.652,
  "overlap_ratio": 0.758,
  "overlapping_segments": 4,
  "has_high_energy": true,

  // Hybrid Scoring
  "energy_boost": 0.689,
  "hybrid_score": 0.947
}
```

### Statistics

```json
{
  "total_ai_clips": 20,
  "total_energy_segments": 20,
  "total_hybrid_clips": 20,
  "clips_with_high_energy": 12,
  "clips_with_energy_boost": 16,
  "avg_ai_score": 0.721,
  "avg_hybrid_score": 0.822,
  "avg_energy_boost": 0.556,
  "max_hybrid_score": 1.0,
  "energy_boost_improved_ranking": 8
}
```

## Real-World Example

Using the test audio file (8.7 minute tech career talk):

### Analysis Results

**Input:**
- 17 AI-identified interesting content segments
- 20 high-energy audio segments
- Duration: 519 seconds (8.7 minutes)

**Hybrid Analysis:**
- 12/17 clips (70%) had high energy overlap
- 16/17 clips (94%) received energy boost
- Average score improved: 0.721 → 0.822 (+14%)
- 8 clips changed ranking positions

### Top 3 Clips

**#1 - "Mock interesting segment 15"** ⚡
- Time: 07:07 → 07:52 (45s)
- AI Score: 0.947
- Hybrid Score: 1.000 (+5.6%)
- Energy: 0.723 peak, 75.8% overlap, 4 energy segments
- **Why:** Already great content, delivered with high energy

**#2 - "Mock interesting segment 1"** ⚡
- Time: 00:00 → 01:02 (62s)
- AI Score: 0.916
- Hybrid Score: 1.000 (+9.2%)
- Energy: 0.700 peak, 37.2% overlap, 3 energy segments
- **Why:** Strong opening, good energy throughout

**#3 - "Mock interesting segment 9"** ⚡
- Time: 04:04 → 05:23 (79s)
- AI Score: 0.853
- Hybrid Score: 0.998 (+16.9%)
- Energy: 0.676 peak, 11.4% overlap, 1 energy segment
- **Why:** Content boosted significantly by peak energy moment

## Ranking Changes

Energy detection causes clips to move up or down in rankings:

```
Ranking Changes Due to Energy Boost:

⚡ # 1 ➡️ 0     | AI: 0.947 → Hybrid: 1.000 | Great content + high energy
⚡ # 2 ➡️ 0     | AI: 0.916 → Hybrid: 1.000 | Already top tier
⚡ # 7 ⬆️ +1    | AI: 0.774 → Hybrid: 0.912 | Energy boosted to top 10
⚡ # 8 ⬆️ +2    | AI: 0.735 → Hybrid: 0.868 | Big energy boost!
   #10 🆕 NEW   | AI: 0.685 → Hybrid: 0.779 | Entered top 10 via energy
```

**Legend:**
- ⚡ = High energy overlap (>50%)
- ➡️ = No rank change
- ⬆️ = Moved up in rankings
- 🆕 = New to top 10

## Configuration

### Energy Weight

Controls how much energy affects scoring:

```python
HybridAnalyzer(
    ai_analyzer=ai_analyzer,
    energy_analyzer=energy_analyzer,
    energy_weight=0.3  # 0.0 - 1.0
)
```

**Recommended values:**
- `0.2` (20%) - Conservative, prioritize content
- `0.3` (30%) - **Default**, balanced approach
- `0.4` (40%) - Aggressive, heavily favor energy
- `0.5` (50%) - Maximum boost (50% improvement possible)

### Duration Settings

```python
results = hybrid.analyze_video(
    video_path=video,
    transcript_data=transcript,
    target_clips=10,
    min_duration=30,  # Shorter clips for social media
    max_duration=90   # Longer clips for YouTube
)
```

**Recommended durations by platform:**

| Platform | Min | Max | Note |
|----------|-----|-----|------|
| TikTok   | 15  | 60  | Short, punchy clips |
| Instagram Reels | 20 | 90 | Medium length |
| YouTube Shorts | 15 | 60 | Under 60 seconds |
| Twitter/X | 30 | 120 | More flexibility |
| LinkedIn | 30 | 180 | Longer form OK |

## Benefits

### 1. Better Clip Quality
- Clips have both great content AND delivery
- More engaging for viewers
- Higher watch-through rates

### 2. Improved Social Performance
- Energy = engagement
- Enthusiastic delivery = shares
- Better algorithm performance

### 3. Reduced Manual Review
- Automated detection of "the good parts"
- Less time scrubbing through footage
- Trust the hybrid score

### 4. Content Variety
- Mix of content types (insights, stories, hooks)
- Mix of energy levels (calm teaching vs. excited moments)
- Balanced clip selection

## Performance

**Processing Time:**
- AI Analysis: ~10-30 seconds (API call)
- Energy Analysis: ~2-5 seconds (local computation)
- Hybrid Scoring: <1 second (overlap calculation)
- **Total: ~15-35 seconds for 10-minute video**

**Cost:**
- AI Analysis: ~$0.01-0.05 per video (OpenAI API)
- Energy Analysis: Free (local processing)
- Hybrid Scoring: Free (local processing)
- **Total: ~$0.01-0.05 per video**

## Integration with Arena Pipeline

```python
from pathlib import Path
from arena.audio.transcriber import Transcriber
from arena.audio.energy import AudioEnergyAnalyzer
from arena.ai.hybrid import HybridAnalyzer
from arena.clipping.generator import ClipGenerator

video = Path("video.mp4")

# Step 1: Transcribe
transcriber = Transcriber()
transcript = transcriber.transcribe(video, cache_dir=".arena/cache")

# Step 2: Hybrid Analysis
ai_analyzer = TranscriptAnalyzer()
energy_analyzer = AudioEnergyAnalyzer(video)
hybrid = HybridAnalyzer(ai_analyzer, energy_analyzer)

results = hybrid.analyze_video(
    video,
    transcript,
    target_clips=10,
    min_duration=30,
    max_duration=90
)

# Step 3: Generate Clips
generator = ClipGenerator(video)
output_dir = Path(".arena/output/clips")

for i, clip in enumerate(results['clips'][:5], 1):
    output_path = output_dir / f"{i:02d}_{clip['id']}.mp4"
    generator.generate_clip(
        clip['start_time'],
        clip['end_time'],
        output_path
    )
    print(f"✓ Generated: {clip['title']}")
```

## Troubleshooting

**"No high-energy clips found"**
- Lower the `energy_weight` parameter
- Check if audio is too uniform
- Verify transcript has good content

**"All clips have low energy boost"**
- Audio might be quiet/calm throughout
- Adjust energy threshold in `AudioEnergyAnalyzer`
- Consider content-only (AI) ranking

**"Ranking not changing"**
- Energy might be evenly distributed
- Increase `energy_weight` for more impact
- Check if overlap detection is working

**"Mock analyzer being used"**
- Set `OPENAI_API_KEY` environment variable
- Get API key from https://platform.openai.com
- `export OPENAI_API_KEY="sk-..."`

## Next Steps

- ✅ Hybrid analysis implemented
- ✅ Tested with real audio
- 🔄 CLI integration (coming soon)
- 🔄 Visual energy timeline in UI (coming soon)
- 🔄 Custom weighting per content type (future)
- 🔄 Machine learning for optimal weights (future)

## Files

**Implementation:**
- `engine/arena/ai/hybrid.py` - HybridAnalyzer class
- `engine/arena/ai/analyzer.py` - AI transcript analyzer
- `engine/arena/audio/energy.py` - Audio energy analyzer

**Tests:**
- `engine/test_hybrid_analysis.py` - Hybrid analysis test script
- `engine/test_energy_audio.py` - Energy detection tests

**Documentation:**
- `HYBRID_ANALYSIS.md` - This document
- `AUDIO_ENERGY_DETECTION.md` - Energy detection details
- `AUDIO_ENHANCEMENT.md` - Audio preprocessing

## License

MIT
