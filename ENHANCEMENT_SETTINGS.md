# Audio Enhancement Settings

## Changes Made

Fixed overly aggressive enhancement that was degrading audio quality.

### New Enhancement Levels

Control enhancement intensity with `ARENA_ENHANCEMENT_LEVEL`:

```bash
# Gentle (Default - Recommended)
export ARENA_ENHANCEMENT_LEVEL=gentle
- Light noise reduction (80% strength)
- Only boosts volume if very quiet
- Preserves natural sound character
- No compression

# Moderate
export ARENA_ENHANCEMENT_LEVEL=moderate
- Medium noise reduction
- Standard loudness normalization
- No compression

# Aggressive
export ARENA_ENHANCEMENT_LEVEL=aggressive
- Strong noise reduction
- Full loudness normalization
- Dynamic compression applied

# None (Just normalize, no processing)
export ARENA_ENHANCEMENT_LEVEL=none
- No noise reduction
- Only gentle volume normalization
```

## Recommended Usage

### For Most Videos (Default)
```bash
export ARENA_ENHANCE_AUDIO=true
export ARENA_ENHANCEMENT_LEVEL=gentle  # or omit (gentle is default)
```

### For Very Noisy Audio
```bash
export ARENA_ENHANCE_AUDIO=true
export ARENA_ENHANCEMENT_LEVEL=moderate
```

### For Clean Studio Audio
```bash
# Don't enhance at all
unset ARENA_ENHANCE_AUDIO

# Or use minimal processing
export ARENA_ENHANCE_AUDIO=true
export ARENA_ENHANCEMENT_LEVEL=none
```

## Comparing Enhancement Levels

Test different levels to find what works best:

```bash
# Test 1: No enhancement
unset ARENA_ENHANCE_AUDIO
arena process video.mp4
# Listen to: .arena/cache/video_audio.mp3

# Test 2: Gentle enhancement
export ARENA_ENHANCE_AUDIO=true
export ARENA_ENHANCEMENT_LEVEL=gentle
rm -rf .arena/cache/*
arena process video.mp4
# Listen to: .arena/cache/video_enhanced.wav

# Test 3: Moderate enhancement
export ARENA_ENHANCEMENT_LEVEL=moderate
rm -rf .arena/cache/*
arena process video.mp4
```

## What Changed from v0.1.0

**Old (Too Aggressive):**
- Used first 1 second as noise profile (wrong if speech starts immediately)
- -16 LUFS normalization (caused clipping)
- 3:1 compression always applied
- Stationary noise reduction (removes voice frequencies)

**New (Gentle by Default):**
- Non-stationary noise reduction (preserves speech)
- -18 LUFS target (gentler, less clipping)
- Only boosts if audio is very quiet
- Blends original + processed audio (70/30)
- Compression only in aggressive mode
- Automatic clipping prevention

## Troubleshooting

### "Audio sounds muffled"
Try: `ARENA_ENHANCEMENT_LEVEL=none` or disable enhancement

### "Audio sounds distorted/robotic"
Try: `ARENA_ENHANCEMENT_LEVEL=gentle` (should be fixed now)

### "Audio too quiet"
Try: `ARENA_ENHANCEMENT_LEVEL=moderate`

### "Audio has artifacts/crackling"
Try: `ARENA_ENHANCEMENT_LEVEL=gentle` or disable enhancement

### "Original audio was better"
Disable enhancement: `unset ARENA_ENHANCE_AUDIO`

## Technical Details

### Gentle Mode (Default)
- Non-stationary noise reduction at 80% strength
- Frequency mask smoothing: 500 Hz
- Time mask smoothing: 50 ms
- Only normalizes if >3 dB below target
- Blends 70% processed + 30% original
- No compression
- Clipping prevention

### Why Gentle is Better
The original aggressive settings were:
1. Removing too much of the voice frequencies
2. Over-normalizing and causing clipping
3. Making everything sound "processed"

The new gentle mode:
1. Preserves natural voice character
2. Removes only obvious noise
3. Doesn't over-process already good audio
4. Sounds more natural

## Quick Reference

```bash
# Best for most cases (new default)
export ARENA_ENHANCE_AUDIO=true
export ARENA_ENHANCEMENT_LEVEL=gentle

# For very clean audio
unset ARENA_ENHANCE_AUDIO

# For very noisy audio
export ARENA_ENHANCEMENT_LEVEL=moderate

# For extreme noise (use sparingly)
export ARENA_ENHANCEMENT_LEVEL=aggressive
```

## Testing Your Audio

```bash
# Original audio location
.arena/cache/your-video_audio.mp3

# Enhanced audio location
.arena/cache/your-video_enhanced.wav

# Compare them with your audio player
```

Use an audio player to A/B test and choose what sounds best for your content!
