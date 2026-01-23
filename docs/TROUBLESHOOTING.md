# Troubleshooting Guide

Common issues and solutions for Arena CLI.

## Table of Contents

- [Installation Issues](#installation-issues)
- [Python Issues](#python-issues)
- [FFmpeg Issues](#ffmpeg-issues)
- [API Issues](#api-issues)
- [Processing Issues](#processing-issues)
- [Quality Issues](#quality-issues)

---

## Installation Issues

### "npm install -g @whitegodkingsley/arena-cli" fails

**Symptoms**: Installation fails with permission errors

**Solution 1**: Use sudo (not recommended)
```bash
sudo npm install -g @whitegodkingsley/arena-cli
```

**Solution 2**: Configure npm to use a different directory (recommended)
```bash
# Create directory for global packages
mkdir ~/.npm-global

# Configure npm
npm config set prefix '~/.npm-global'

# Add to PATH (add this to ~/.bashrc or ~/.zshrc)
export PATH=~/.npm-global/bin:$PATH

# Install without sudo
npm install -g @whitegodkingsley/arena-cli
```

**Solution 3**: Use npx (no installation)
```bash
npx @whitegodkingsley/arena-cli process video.mp4
```

### "arena: command not found"

**Symptoms**: After installation, `arena` command is not recognized

**Cause**: npm global bin directory is not in PATH

**Solution**:
```bash
# Find where npm installs global packages
npm config get prefix

# Add to PATH (example for ~/.npm-global)
export PATH="$HOME/.npm-global/bin:$PATH"

# Add to shell config (~/.bashrc or ~/.zshrc)
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

---

## Python Issues

### "Python not found"

**Symptoms**: `Python 3 is not installed or not in PATH`

**Solution (macOS)**:
```bash
# Using Homebrew
brew install python3

# Verify installation
python3 --version
```

**Solution (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install python3 python3-pip

# Verify installation
python3 --version
```

### "Python version too old"

**Symptoms**: `Python 3.9 or higher is required, found Python 3.7`

**Solution (macOS with Homebrew)**:
```bash
brew install python@3.11
brew link python@3.11
```

**Solution (Ubuntu with deadsnakes PPA)**:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install python3.11
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

**Solution (using pyenv - recommended)**:
```bash
# Install pyenv
curl https://pyenv.run | bash

# Install Python
pyenv install 3.11.0
pyenv global 3.11.0
```

### "Python dependencies missing"

**Symptoms**: `Python dependencies are not installed`

**Cause**: Arena's Python engine dependencies are not installed

**Solution**:
```bash
# Navigate to engine directory
cd path/to/arena/engine

# Install dependencies
pip install -r requirements.txt

# Or use virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## FFmpeg Issues

### "FFmpeg not found"

**Symptoms**: Video processing fails with FFmpeg-related errors

**Solution (macOS)**:
```bash
brew install ffmpeg
```

**Solution (Ubuntu/Debian)**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Solution (Windows via Chocolatey)**:
```bash
choco install ffmpeg
```

**Verify Installation**:
```bash
ffmpeg -version
```

### "Unsupported codec" or "Unable to encode"

**Symptoms**: Video generation fails with codec errors

**Cause**: FFmpeg was compiled without certain codecs

**Solution**: Reinstall FFmpeg with all codecs
```bash
# macOS (with all codecs)
brew reinstall ffmpeg

# Ubuntu (enable multiverse repository)
sudo add-apt-repository multiverse
sudo apt update
sudo apt install ffmpeg
```

---

## API Issues

### "OpenAI API key not found"

**Symptoms**: `OpenAI API key not found`

**Solution 1**: Set environment variable
```bash
export OPENAI_API_KEY="sk-..."

# Make permanent (add to ~/.bashrc or ~/.zshrc)
echo 'export OPENAI_API_KEY="sk-..."' >> ~/.zshrc
source ~/.zshrc
```

**Solution 2**: Set via config
```bash
arena config set openai_api_key "sk-..."
```

**Verify**:
```bash
# Check if key is set
arena config get openai_api_key
```

### "OpenAI API key has invalid format"

**Symptoms**: `OpenAI API key has invalid format`

**Cause**: API key doesn't start with "sk-" or is incomplete

**Solution**: Get a new key from https://platform.openai.com/api-keys

- Keys should start with `sk-`
- Keys are typically 51 characters long
- Ensure you copied the entire key

### "Rate limit exceeded"

**Symptoms**: `Error code: 429 - Rate limit reached for gpt-4o`

**Cause**: Too many requests to OpenAI API

**Solution 1**: Wait and retry
```bash
# Wait 60 seconds and retry
sleep 60
arena process video.mp4
```

**Solution 2**: Use gpt-4o-mini (higher rate limits)
```bash
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini
```

**Solution 3**: Increase delays (edit Python engine if needed)

**Solution 4**: Upgrade OpenAI tier

### "Insufficient quota"

**Symptoms**: `Error: You exceeded your current quota`

**Cause**: OpenAI account has no credits or insufficient balance

**Solution**:
1. Add credits to your OpenAI account: https://platform.openai.com/account/billing
2. Check usage: https://platform.openai.com/account/usage
3. Set up billing alerts

---

## Processing Issues

### "No clips generated"

**Symptoms**: Processing completes but generates 0 clips

**Cause 1**: Video is too short
```bash
# Check video duration
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 video.mp4

# Solution: Use longer videos (> 2 minutes for best results)
```

**Cause 2**: No interesting moments detected
```bash
# Solution: Lower minimum duration
arena process video.mp4 --min 15 --max 45
```

**Cause 3**: All clips failed quality validation (4-layer mode)
```bash
# Solution 1: Disable 4-layer temporarily
arena process video.mp4  # Without --use-4layer

# Solution 2: Export layers to debug
arena process video.mp4 --use-4layer --export-layers

# Check exported JSON files to see why clips were rejected
```

### "Transcription failed"

**Symptoms**: Processing fails during transcription step

**Cause 1**: Audio format not supported

**Solution**: Extract audio first
```bash
arena extract-audio video.mp4 --format mp3
# Then transcribe the audio directly (if supported)
```

**Cause 2**: API timeout (very long videos)

**Solution**: Split video into smaller chunks
```bash
# Split video into 30-minute chunks
ffmpeg -i video.mp4 -c copy -map 0 -segment_time 1800 -f segment output%03d.mp4

# Process each chunk
for file in output*.mp4; do
  arena process "$file"
done
```

### "Processing is very slow"

**Symptoms**: Processing takes much longer than expected

**Cause 1**: Using 4-layer system (expected)
- 4-layer mode requires multiple API calls per clip
- Can be 5-10x slower than standard mode

**Solution 1**: Use gpt-4o-mini instead of gpt-4o
```bash
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini
```

**Solution 2**: Reduce number of clips
```bash
arena process video.mp4 -n 3  # Instead of default 5
```

**Cause 2**: Network latency to OpenAI API

**Solution**: Check internet connection speed

### "Memory error" or "Out of memory"

**Symptoms**: Process crashes with memory-related error

**Cause**: Video file is too large or system has insufficient RAM

**Solution 1**: Use fast mode (stream copy)
```bash
arena process video.mp4 --fast
```

**Solution 2**: Reduce video resolution before processing
```bash
# Scale video to 720p
ffmpeg -i video.mp4 -vf scale=-1:720 -c:a copy video_720p.mp4
arena process video_720p.mp4
```

---

## Quality Issues

### "Clips have poor cut points"

**Symptoms**: Clips start/end mid-sentence or awkwardly

**Cause**: Not using 4-layer system or boundary refinement

**Solution**: Enable 4-layer mode
```bash
arena process video.mp4 --use-4layer --editorial-model gpt-4o-mini
```

**Alternative**: Add more padding
```bash
arena process video.mp4 --padding 1.0  # 1 second padding
```

### "Clips are too similar"

**Symptoms**: Generated clips cover similar content

**Cause**: Video has repetitive content or limited variety

**Solution 1**: Reduce number of clips
```bash
arena process video.mp4 -n 3  # Generate fewer, more diverse clips
```

**Solution 2**: Increase duration range
```bash
arena process video.mp4 --min 45 --max 90  # Longer clips capture more context
```

### "Clips are low quality (blurry, artifacts)"

**Symptoms**: Output video quality is poor

**Cause**: Using `--fast` mode (stream copy)

**Solution**: Remove `--fast` flag for full re-encode
```bash
arena process video.mp4  # Without --fast
```

**Note**: Re-encoding takes 10x longer but produces better quality

---

## Debug Mode

For any issue, enable debug mode for more information:

```bash
arena process video.mp4 --debug
```

This will show:
- Full error stack traces
- Detailed processing steps
- API request/response details
- Python subprocess output

---

## Getting More Help

If none of these solutions work:

1. **Check GitHub Issues**: https://github.com/YOUR_USERNAME/arena/issues
2. **Create New Issue**: Include:
   - Full error message
   - Command you ran
   - Output from `arena --version`
   - Output from `python3 --version`
   - Output from `ffmpeg -version`
   - Your OS and version
   - Debug output if possible

3. **Community**: Join discussions in GitHub Discussions

---

## Useful Diagnostic Commands

```bash
# Check Arena version
arena --version

# Check if arena is installed globally
which arena

# Check Node version
node --version

# Check Python version
python3 --version

# Check FFmpeg version
ffmpeg -version

# Check API key is set
echo $OPENAI_API_KEY

# View current config
arena config

# Test with a small video
arena process small-test.mp4 -n 1 --min 10 --max 20

# Enable all debug output
arena process video.mp4 --debug 2>&1 | tee debug.log
```
