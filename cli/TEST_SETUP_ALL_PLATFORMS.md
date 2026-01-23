# Setup Testing Guide - All Platforms

This document provides comprehensive testing procedures for Arena CLI setup on Windows, macOS, and Linux.

## Testing Matrix

| Platform | Package Manager | Python Command | pip Command | FFmpeg Install | Status |
|----------|----------------|----------------|-------------|----------------|--------|
| **Windows 10/11** | winget | `python` | `pip` | winget | ⚠️ Needs testing |
| **Windows 10/11** | chocolatey | `python` | `pip` | choco | ⚠️ Needs testing |
| **Windows 10/11** | manual | `python` | `pip` | manual | ⚠️ Needs testing |
| **macOS** | Homebrew | `python3` | `pip3` | brew | ✅ Should work |
| **macOS** | MacPorts | `python3` | `pip3` | port | ⚠️ Needs testing |
| **Ubuntu/Debian** | apt | `python3` | `pip3` | apt | ⚠️ Needs testing |
| **Fedora/RHEL** | dnf/yum | `python3` | `pip3` | dnf/yum | ⚠️ Needs testing |
| **Arch Linux** | pacman | `python3` | `pip3` | pacman | ⚠️ Needs testing |
| **openSUSE** | zypper | `python3` | `pip3` | zypper | ⚠️ Needs testing |

## Platform-Specific Test Cases

### Windows Testing

#### Prerequisites
- Windows 10 version 1809 or later (for winget)
- OR Chocolatey installed
- OR manual installation capability

#### Test Scenarios

**Scenario 1: Fresh Windows 10 with winget**
```powershell
# Clean system test
npm install -g @whitegodkingsley/arena-cli
arena setup

# Expected behavior:
# 1. Detects winget
# 2. Shows: "Automatic installation may require running as Administrator"
# 3. Attempts: winget install Python.Python.3.11
# 4. Attempts: winget install Gyan.FFmpeg
# 5. Installs Python packages with: pip install ...
```

**Known Issues:**
- winget may require accepting source agreements: `winget install --accept-source-agreements --accept-package-agreements`
- May need elevation (Admin)
- PATH not updated until terminal restart

**Scenario 2: Windows with Chocolatey**
```powershell
# With chocolatey installed
arena setup

# Expected behavior:
# 1. Detects choco
# 2. Attempts: choco install python
# 3. Attempts: choco install ffmpeg
# 4. Installs Python packages
```

**Known Issues:**
- Requires Admin privileges
- chocolatey commands need `-y` flag for non-interactive

**Scenario 3: Windows manual installation**
```powershell
# No package manager
arena setup

# Expected behavior:
# 1. Detects no package manager (win32-manual)
# 2. Shows manual URLs:
#    - https://www.python.org/downloads/
#    - https://ffmpeg.org/download.html
# 3. Guides user through manual setup
```

### macOS Testing

#### Prerequisites
- macOS 10.15+ (Catalina or later)
- Homebrew OR MacPorts installed (or willing to install)

#### Test Scenarios

**Scenario 1: macOS with Homebrew**
```bash
# Standard macOS setup
npm install -g @whitegodkingsley/arena-cli
arena setup

# Expected behavior:
# 1. Detects brew
# 2. Checks: python3 --version, pip3 --version, ffmpeg -version
# 3. If missing, runs: brew install python3 ffmpeg
# 4. Installs Python packages with: pip3 install ...
```

**Known Issues:**
- Homebrew might need Xcode Command Line Tools
- May need to run: xcode-select --install

**Scenario 2: macOS with MacPorts**
```bash
# With MacPorts instead of Homebrew
arena setup

# Expected behavior:
# 1. Detects port
# 2. Attempts: sudo port install python311 ffmpeg
# 3. Prompts for sudo password
```

**Scenario 3: macOS without package manager**
```bash
# No brew or port
arena setup

# Expected behavior:
# 1. Shows brew installation command
# 2. Provides manual installation URLs
```

### Linux Testing

#### Ubuntu/Debian (apt)

**Test Scenario:**
```bash
# Fresh Ubuntu/Debian
sudo apt update
npm install -g @whitegodkingsley/arena-cli
arena setup

# Expected behavior:
# 1. Detects apt
# 2. Shows sudo requirement warning
# 3. Attempts: sudo apt-get install python3 python3-pip ffmpeg
# 4. Prompts for password
# 5. Installs Python packages
```

**Known Issues:**
- Needs sudo privileges
- May need to accept prompts: use `-y` flag
- Universe repository might need enabling for ffmpeg

#### Fedora/RHEL (dnf/yum)

**Test Scenario:**
```bash
# Fedora/RHEL/CentOS
npm install -g @whitegodkingsley/arena-cli
arena setup

# Expected behavior:
# 1. Detects dnf (or yum on older systems)
# 2. Attempts: sudo dnf install python3 python3-pip ffmpeg
# 3. Prompts for password
```

**Known Issues:**
- ffmpeg might need RPM Fusion repository
- RHEL/CentOS needs EPEL repository

#### Arch Linux (pacman)

**Test Scenario:**
```bash
# Arch Linux
npm install -g @whitegodkingsley/arena-cli
arena setup

# Expected behavior:
# 1. Detects pacman
# 2. Attempts: sudo pacman -S python python-pip ffmpeg
# 3. Prompts for password
```

**Known Issues:**
- pacman needs `--noconfirm` flag for non-interactive

#### openSUSE (zypper)

**Test Scenario:**
```bash
# openSUSE
npm install -g @whitegodkingsley/arena-cli
arena setup

# Expected behavior:
# 1. Detects zypper
# 2. Attempts: sudo zypper install python3 python3-pip ffmpeg
# 3. Prompts for password
```

## Common Issues Across Platforms

### Issue 1: PATH Not Updated
**Problem:** Newly installed tools not found after installation
**Solution:** Restart terminal or reload PATH
**Fix Status:** ⚠️ Should warn user to restart terminal

### Issue 2: Permission Denied
**Problem:** Installation commands fail due to permissions
**Solution:**
- Windows: Run as Administrator
- macOS/Linux: Use sudo
**Fix Status:** ✅ Shows warning before installation

### Issue 3: Package Manager Not Found
**Problem:** Detection fails even when package manager exists
**Solution:** Check PATH, reload shell
**Fix Status:** ⚠️ Should provide installation instructions

### Issue 4: Interactive Prompts Timeout
**Problem:** sudo password or package manager prompts timeout
**Solution:** Add appropriate flags (-y, --noconfirm, etc.)
**Fix Status:** ❌ Not implemented

### Issue 5: Repository Not Enabled
**Problem:** Packages not found in default repositories
**Solution:** Enable universe/EPEL/RPM Fusion
**Fix Status:** ❌ Not detected or handled

## Recommended Fixes

### 1. Add Non-Interactive Flags
```typescript
// Update installation commands to be non-interactive
installInstructions: {
  'linux-apt': 'sudo apt-get install -y python3 python3-pip',
  'linux-dnf': 'sudo dnf install -y python3 python3-pip ffmpeg',
  'linux-pacman': 'sudo pacman -S --noconfirm python python-pip ffmpeg',
  'linux-zypper': 'sudo zypper install -n python3 python3-pip ffmpeg',
  'win32-choco': 'choco install -y python ffmpeg',
  'win32-winget': 'winget install --accept-source-agreements --accept-package-agreements Python.Python.3.11',
}
```

### 2. Add Post-Install Path Warning
```typescript
// After successful installation
console.log(chalk.yellow('\n⚠️  Important: Restart your terminal'));
console.log(chalk.gray('   Newly installed tools may not be in PATH until you:'));
console.log(chalk.gray('   - Close and reopen your terminal'));
console.log(chalk.gray('   - Or run: source ~/.bashrc (Linux/macOS)'));
console.log(chalk.gray('   - Or restart PowerShell/CMD (Windows)\n'));
```

### 3. Add Repository Checks (Linux)
```typescript
// Check if required repositories are enabled
async function checkLinuxRepositories() {
  // Check for universe (Ubuntu), EPEL (RHEL), RPM Fusion (Fedora)
  // Provide guidance if missing
}
```

### 4. Improved Error Detection
```typescript
// Detect specific errors and provide solutions
if (error.includes('repository')) {
  console.log('Repository not found. Enable with:');
  console.log('  Ubuntu: sudo add-apt-repository universe');
  console.log('  RHEL: sudo yum install epel-release');
}
```

## Test Results Template

### Platform: _______________
**OS Version:** _______________
**Package Manager:** _______________
**Date:** _______________
**Tester:** _______________

#### Test Results

| Test | Result | Notes |
|------|--------|-------|
| Package manager detection | ☐ Pass ☐ Fail | |
| Python detection | ☐ Pass ☐ Fail | |
| pip detection | ☐ Pass ☐ Fail | |
| FFmpeg detection | ☐ Pass ☐ Fail | |
| Python auto-install | ☐ Pass ☐ Fail | |
| FFmpeg auto-install | ☐ Pass ☐ Fail | |
| Python packages install | ☐ Pass ☐ Fail | |
| Post-install verification | ☐ Pass ☐ Fail | |

#### Issues Encountered
```
[Describe any issues here]
```

#### Error Messages
```
[Paste error messages here]
```

#### Recommendations
```
[Your suggestions for improvement]
```

---

**Last Updated:** 2026-01-23
**Version:** 0.3.4
