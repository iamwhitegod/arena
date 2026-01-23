# Cross-Platform Python Installation Testing

**Version:** 0.3.3
**Date:** 2026-01-23
**Status:** ✅ FIXED - Python packages now install correctly on all platforms

## Issues Fixed

### 1. **Windows Python Detection**
**Problem:** Hardcoded `python3` command doesn't exist on Windows
**Solution:** Added platform-aware Python detection

**Detection Order:**
- **Windows:** `python` → `python3` → `py`
- **macOS/Linux:** `python3` → `python`

### 2. **Windows pip Detection**
**Problem:** Hardcoded `pip3` command doesn't exist on Windows
**Solution:** Added platform-aware pip detection with fallbacks

**Detection Order:**
- **Windows:** `pip` → `pip3` → `python -m pip` → `python3 -m pip`
- **macOS/Linux:** `pip3` → `pip` → `python3 -m pip` → `python -m pip`

### 3. **Python Package Installation**
**Problem:** Used hardcoded `pip3 install` command
**Solution:** Dynamic pip command detection + platform-specific handling

**Features:**
- Detects available pip command automatically
- Handles `python -m pip` format correctly
- Uses shell mode on Windows for better compatibility
- Shows helpful error messages with manual commands

### 4. **Windows FFmpeg Detection**
**Problem:** FFmpeg not detected even when installed on Windows (not in PATH)
**Solution:** Added intelligent FFmpeg detection with common path checking

**Detection Strategy:**
1. Check if `ffmpeg` is in PATH (works on all platforms)
2. On Windows, check common installation paths:
   - `C:\Program Files\ffmpeg\bin\ffmpeg.exe`
   - `C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe`
   - `C:\ffmpeg\bin\ffmpeg.exe`
   - `%ProgramData%\chocolatey\bin\ffmpeg.exe`

**Features:**
- Detects FFmpeg even if not added to PATH
- Shows version when found
- Provides helpful instructions to add to PATH
- Works with winget, chocolatey, and manual installations

### 5. **Postinstall Check**
**Problem:** Postinstall script checked for `python3` only and didn't check common FFmpeg paths
**Solution:** Cross-platform Python and FFmpeg detection in postinstall.cjs

## Files Modified

### `src/commands/setup.ts`
```typescript
// Added functions:
- checkPython() - Tries multiple Python commands
- checkPip() - Tries multiple pip commands
- getPipCommand() - Returns best available pip command
- installPythonPackages() - Updated with dynamic pip detection

// Updated logic:
- Platform-aware command selection
- Shell mode on Windows
- Better error messages
```

### `scripts/postinstall.cjs`
```typescript
// Added function:
- checkPython() - Cross-platform Python detection

// Updated logic:
- Uses checkPython() instead of hardcoded python3
```

## Platform-Specific Behavior

### Windows
```powershell
# Python detection tries:
1. python --version
2. python3 --version
3. py --version

# Pip detection tries:
1. pip --version
2. pip3 --version
3. python -m pip --version
4. python3 -m pip --version

# Installation uses:
python -m pip install openai-whisper openai ffmpeg-python torch numpy scipy
# OR
pip install openai-whisper openai ffmpeg-python torch numpy scipy
```

### macOS / Linux
```bash
# Python detection tries:
1. python3 --version
2. python --version

# Pip detection tries:
1. pip3 --version
2. pip --version
3. python3 -m pip --version
4. python -m pip --version

# Installation uses:
pip3 install openai-whisper openai ffmpeg-python torch numpy scipy
```

## Testing Instructions

### Test on Windows
```powershell
# 1. Install Arena
npm install -g @whitegodkingsley/arena-cli

# 2. Check postinstall detection
# Should show: ✓ Python found or ✗ Python missing
# Should show: ✓ FFmpeg found or ✗ FFmpeg missing

# 3. Run setup
arena setup

# Should:
# - Detect Windows and package manager (winget/choco/manual)
# - Find Python using 'python' command
# - Find pip using 'pip' or 'python -m pip'
# - Find FFmpeg in PATH or common locations
# - If FFmpeg not in PATH, show helpful instructions
# - Install packages successfully

# 4. Test FFmpeg detection scenarios:

# Scenario A: FFmpeg in PATH (ideal)
winget install Gyan.FFmpeg
# Restart terminal
arena setup  # Should show: ✓ FFmpeg 6.x.x

# Scenario B: FFmpeg installed but not in PATH
# Install manually to C:\ffmpeg\
arena setup  # Should show: ✓ FFmpeg found
# Plus helpful message about adding to PATH

# Scenario C: FFmpeg not installed
arena setup  # Should show: ✗ FFmpeg not found
# Then auto-install with: winget install Gyan.FFmpeg
```

### Test on macOS
```bash
# 1. Install Arena
npm install -g @whitegodkingsley/arena-cli

# 2. Check postinstall detection
# Should show: ✓ Python 3.9+ found

# 3. Run setup
arena setup

# Should:
# - Detect macOS and Homebrew/MacPorts
# - Find Python using 'python3' command
# - Find pip using 'pip3' command
# - Install packages successfully
```

### Test on Linux (Ubuntu/Debian)
```bash
# 1. Install Arena
npm install -g @whitegodkingsley/arena-cli

# 2. Check postinstall detection
# Should show: ✓ Python 3.9+ found

# 3. Run setup
arena setup

# Should:
# - Detect Linux and apt/yum/dnf/pacman
# - Find Python using 'python3' command
# - Find pip using 'pip3' command
# - Install packages successfully
```

## Python Packages Installed

All platforms install the same packages:
- `openai-whisper` - Transcription
- `openai` - OpenAI API client
- `ffmpeg-python` - FFmpeg Python bindings
- `torch` - PyTorch for Whisper
- `numpy` - Numerical computing
- `scipy` - Scientific computing

## Error Handling

### If pip not found
```
✗ Failed to install Python packages

💡 Tip: Try running manually:
  pip install openai-whisper openai ffmpeg-python torch numpy scipy
```

### If installation fails
Shows full error output and suggests manual installation with the detected pip command.

## Verification

### Before (v0.3.2 and earlier)
❌ Windows: Failed with "pip3 not found"
❌ Windows: Postinstall showed Python missing when it was installed
❌ Windows: Python packages couldn't be installed

### After (v0.3.3)
✅ Windows: Correctly detects `python` and `pip`
✅ Windows: Postinstall correctly identifies Python
✅ Windows: Python packages install successfully
✅ macOS: Still works (uses `python3` and `pip3`)
✅ Linux: Still works (uses `python3` and `pip3`)

## Command Compatibility Matrix

### Python & pip

| Command | Windows | macOS | Linux | Notes |
|---------|---------|-------|-------|-------|
| `python` | ✅ Primary | ⚠️ May be Python 2 | ⚠️ May be Python 2 | Windows default |
| `python3` | ⚠️ Sometimes | ✅ Primary | ✅ Primary | Unix default |
| `py` | ✅ Fallback | ❌ | ❌ | Windows Python Launcher |
| `pip` | ✅ Primary | ⚠️ May be Python 2 | ⚠️ May be Python 2 | Windows default |
| `pip3` | ⚠️ Sometimes | ✅ Primary | ✅ Primary | Unix default |
| `python -m pip` | ✅ Always works | ✅ Always works | ✅ Always works | Most reliable |

### FFmpeg

| Location | Windows | macOS | Linux | Notes |
|----------|---------|-------|-------|-------|
| In PATH | ✅ Ideal | ✅ Standard | ✅ Standard | Works everywhere |
| `C:\Program Files\ffmpeg\bin\` | ✅ Checked | ❌ | ❌ | Common Windows location |
| `C:\ffmpeg\bin\` | ✅ Checked | ❌ | ❌ | Manual install location |
| `%ProgramData%\chocolatey\bin\` | ✅ Checked | ❌ | ❌ | Chocolatey install |
| `/usr/local/bin/ffmpeg` | ❌ | ✅ Standard | ✅ Standard | Homebrew/apt default |
| Winget install | ✅ May not add to PATH | ❌ | ❌ | Requires PATH setup |
| Chocolatey install | ✅ Usually in PATH | ❌ | ❌ | Better PATH handling |

## Verification

### Before (v0.3.2 and earlier)
❌ Windows: Failed with "pip3 not found"
❌ Windows: Postinstall showed Python missing when it was installed
❌ Windows: Python packages couldn't be installed
❌ Windows: FFmpeg not detected even when installed (not in PATH)
❌ Windows: No guidance for adding FFmpeg to PATH

### After (v0.3.3)
✅ Windows: Correctly detects `python` and `pip`
✅ Windows: Postinstall correctly identifies Python
✅ Windows: Python packages install successfully
✅ Windows: FFmpeg detected in common locations even without PATH
✅ Windows: Shows helpful PATH instructions when FFmpeg found
✅ macOS: Still works (uses `python3`, `pip3`, finds FFmpeg in PATH)
✅ Linux: Still works (uses `python3`, `pip3`, finds FFmpeg in PATH)

## Summary

**Problem:** Arena couldn't install Python packages on Windows because commands were Unix-specific. FFmpeg was also not detected when installed outside PATH.

**Solution:** Implemented intelligent cross-platform command detection that tries multiple variations and uses the first available one. Added intelligent FFmpeg detection that checks common Windows installation paths.

**Result:** Arena now works seamlessly on Windows, macOS, and Linux with zero user configuration needed. All dependencies are properly detected regardless of installation method.

---

**Tested By:** Arena Development Team
**Last Updated:** 2026-01-23
**Version:** 0.3.3
