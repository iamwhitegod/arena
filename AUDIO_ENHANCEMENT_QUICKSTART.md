# Audio Enhancement - Quick Start

Audio enhancement makes your clips sound professional by removing noise, normalizing volume, and boosting clarity.

## Install Dependencies

```bash
cd engine
pip install noisereduce pyloudnorm scipy
```

## Enable Enhancement

```bash
# Enable local (free) audio enhancement
export ARENA_ENHANCE_AUDIO=true
export ARENA_AUDIO_PROVIDER=local  # Default

# Process video
cd cli
npm run dev process ~/Downloads/your-video.mp4
```

## What It Does

1. **Removes background noise** (fans, AC, traffic)
2. **Cancels echo** and reverb
3. **Normalizes volume** to -16 LUFS (podcast standard)
4. **Compresses dynamic range** for consistent levels

## Cost: FREE

Local enhancement uses open-source libraries on your computer:
- No API costs
- Audio never leaves your machine
- Unlimited processing

## When To Use

### ✅ Use For:
- Laptop/phone mic recordings
- Noisy environments
- Inconsistent audio levels
- Public-facing content

### ❌ Skip For:
- Studio-quality recordings
- Testing/development (faster without)

## Configuration

### Basic (Recommended)

```bash
export ARENA_ENHANCE_AUDIO=true
```

### Advanced

Create `~/.arena/config.json`:

```json
{
  "audio_enhancement": {
    "enabled": true,
    "provider": "local",
    "options": {
      "target_loudness": -16,
      "noise_reduction": "moderate"
    }
  }
}
```

## Processing Time

- Without enhancement: ~25 seconds (your test video)
- With enhancement: ~45-60 seconds (estimated)

Trade-off: Slightly slower but much better audio quality!

## Example

```bash
# Process with enhancement
export ARENA_ENHANCE_AUDIO=true
export ARENA_WHISPER_MODE=local  # Free transcription
export OPENAI_API_KEY=sk-your-key  # For AI analysis

cd cli
npm run dev process ~/Downloads/IMG_2774.MOV
```

## Cached Results

Enhanced audio is cached in `.arena/cache/` so it's only processed once!

Second run with same video = instant enhancement (uses cache).

## Coming Soon

- **Adobe Podcast API**: Industry-leading quality (costs money)
- **Krisp API**: Real-time noise cancellation (costs money)
- **Custom profiles**: Adjust settings per use case

For now, local enhancement is FREE and works great!

## Full Documentation

See [AUDIO_ENHANCEMENT.md](./AUDIO_ENHANCEMENT.md) for complete details.

---

**Next**: Add $5 OpenAI credits, then test with your video!
