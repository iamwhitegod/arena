# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [Unreleased]

## [0.3.10] - 2026-01-23

### Fixed
- **CRITICAL: Windows AssignProcessToJobObject error - ROOT CAUSE RESOLVED** - Fixed "The parameter is incorrect" error on Windows
  - **ROOT CAUSE #1**: `utils/deps.ts` - `commandExists()` function spawned without Windows options
    - Used by getPythonPath(), getFFmpegPath(), getPipPath(), checkDependencies()
    - This was the source of the "Checking Python environment..." error
  - **ROOT CAUSE #2**: `utils/resilience.ts` - `spawnWithErrorHandling()` lacked proper Windows options
    - Used by setup.ts for Python package installation
  - **SOLUTION**: Fixed utility functions once instead of patching individual spawn calls
  - All subprocess spawning now uses proper Windows options (windowsHide, detached:false, shell:false)
  - Also fixed: python-bridge.ts, validation/index.ts spawn calls
  - This is the definitive fix - all Windows subprocess issues resolved
- **CRITICAL: Pip cache hash mismatch errors** - Fixed "THESE PACKAGES DO NOT MATCH THE HASHES" errors
  - Added `--no-cache-dir` flag to avoid stale/corrupted cache files
  - Added `--upgrade` flag to ensure latest compatible versions
  - Detects hash errors and provides cache purge instructions
- **Security: Shell injection warning** - Fixed deprecation warning about shell=true with args
  - Changed to shell=false with properly escaped arguments for pip install
  - Eliminates security vulnerability from concatenated arguments

### Improved
- **Cross-platform Python execution** - Unified approach for running Python scripts
  - Windows: Uses `python arena-cli [command]` explicitly
  - Unix: Uses `arena-cli [command]` with shebang
  - Eliminates Windows job object conflicts
  - Better subprocess handling on all platforms
- **Better error messages for cache issues** - Specific guidance when pip cache is corrupted
  - Shows cache purge command
  - Explains why --no-cache-dir flag was added
  - All manual installation instructions now include --no-cache-dir

## [0.3.9] - 2026-01-23

### Fixed
- **CRITICAL: Pip cache hash mismatch errors** - Initial fix attempt (superseded by 0.3.10)

### Changed
- Initial Windows compatibility improvements (completed in 0.3.10)

## [0.3.8] - 2026-01-23

### Fixed
- **CRITICAL: PATH refresh issues after Python installation** - Fixed pip installation failing when Python just installed
  - Smart installation sequencing: Python installs first, then waits for PATH refresh
  - Automatic retry with delay (up to 10 seconds) to detect newly installed Python
  - Terminal restart prompt when Python installed but not in PATH
  - Detects which dependencies were installed but not found (PATH issue)
  - Platform-specific instructions to restart terminal or source shell config

### Improved
- **Better post-installation guidance** - Clear instructions when dependencies installed but not in PATH
  - Shows which specific tools need PATH refresh
  - Provides option to restart terminal or source config file
  - Detects shell type (.bashrc, .zshrc, .profile) and provides exact command

## [0.3.7] - 2026-01-23

### Added
- **NEW: `arena diagnose` command** - Comprehensive system diagnostics and troubleshooting
  - Checks system info, dependencies, Python packages, network connectivity, API key
  - Validates disk space and configuration
  - Generates diagnostic report with actionable solutions
  - Saves report to arena-diagnostics.txt
- **Resilience utilities** - Production-ready error handling framework
  - Retry logic with exponential backoff for transient failures
  - Timeout handling for all long operations
  - Network connectivity checks
  - API key validation and testing
  - Disk space monitoring
  - User-friendly error messages
- **Logging system** - Debug and troubleshoot user issues
  - Automatic log rotation (10MB max per file)
  - Logs stored in ~/.arena/logs/
  - Debug mode with console output
  - Log statistics and analysis
  - Helps diagnose hidden bugs users encounter

### Improved
- **Better error handling in setup command**
  - Uses retry logic for network failures
  - Better subprocess error handling with spawnWithErrorHandling
  - Timeout detection and user-friendly messages
  - Comprehensive logging of all operations
  - Graceful error recovery and fallbacks

### Changed
- **Enhanced reliability** - All critical operations now have retry logic and timeouts
- **Better diagnostics** - Users can now self-diagnose issues with `arena diagnose`
- **Improved observability** - All commands now log to ~/.arena/logs for debugging

## [0.3.6] - 2026-01-23

### Fixed
- **CRITICAL: Windows Python package installation** - Fixed permission errors on Windows
  - Added `--user` flag to pip install on Windows to avoid "Access is denied" errors
  - Packages now install to user directory instead of requiring Administrator privileges
  - Added time expectation warning (5-10 minutes for torch) to prevent premature cancellation
  - Enhanced error detection for permission issues with specific solutions
  - Users no longer need to run as Administrator for Python package installation

### Improved
- **Better Windows UX** - Installation process now provides clear feedback
  - Shows expected installation time before starting (prevents confusion)
  - Detects permission errors and provides two solutions (--user or Admin)
  - Clearer guidance when installations take longer than expected

## [0.3.5] - 2026-01-23

### Fixed
- **Universal OS installation support** - Complete overhaul for Windows, macOS, and Linux
  - All changes from 0.3.4 consolidated and production-ready

### Added
- Comprehensive TEST_SETUP_ALL_PLATFORMS.md documentation

## [0.3.4] - 2026-01-23

### Fixed
- **CRITICAL: Auto-installation on all platforms** - Fixed automatic dependency installation across Windows, macOS, and Linux
  - Re-check now uses proper cross-platform detection (checkPython, checkPip, checkFFmpeg)
  - Added non-interactive flags for all package managers:
    - Linux apt: `-y` flag and `apt-get update` before install
    - Linux dnf/yum: `-y` flag for auto-confirmation
    - Linux pacman: `--noconfirm` flag
    - Linux zypper: `-n` flag (non-interactive)
    - Windows winget: `--accept-source-agreements --accept-package-agreements`
    - Windows chocolatey: `-y` flag
  - Added intelligent error detection with specific solutions:
    - Repository not found → Shows how to enable universe/EPEL/RPM Fusion
    - Permission denied → Shows how to run as Admin or use sudo
    - Command not found → Shows how to install Homebrew/Chocolatey
    - Package not available → Shows repository enablement commands
  - Added PATH restart warnings when dependencies not found after installation

### Improved
- **Better user guidance** - Shows platform-specific notes before auto-installation
  - Windows: Warns about Administrator privileges requirement
  - Linux: Warns about sudo password prompts
- **Comprehensive error detection** - Detects and provides solutions for:
  - Ubuntu/Debian: Missing universe repository
  - RHEL/CentOS: Missing EPEL repository
  - Fedora: Missing RPM Fusion for FFmpeg
  - macOS: Missing Homebrew
  - Windows: Missing Chocolatey or winget version requirements
- **PATH restart guidance** - Clear instructions to restart terminal after installation
  - Windows: Close/reopen PowerShell/CMD
  - macOS/Linux: Source ~/.bashrc or ~/.zshrc
- **Testing documentation** - Added comprehensive TEST_SETUP_ALL_PLATFORMS.md with:
  - Test scenarios for each platform
  - Known issues and workarounds
  - Test results template

## [0.3.3] - 2026-01-23

### Fixed
- **CRITICAL: Windows Python installation** - Fixed Python package installation failing on Windows
  - Added cross-platform pip detection (tries `pip`, `pip3`, `python -m pip`, `python3 -m pip`)
  - Added cross-platform Python detection (tries `python`, `python3`, `py` on Windows)
  - Setup command now correctly detects and uses the right pip/python commands on all platforms
  - Postinstall script now properly detects Python on Windows (`python` vs `python3`)
  - Python packages now install successfully on Windows, macOS, and Linux
- **CRITICAL: Windows FFmpeg detection** - Fixed FFmpeg not being detected on Windows
  - Added cross-platform FFmpeg detection that checks common Windows installation paths
  - Checks PATH first, then falls back to common locations (Program Files, chocolatey, winget paths)
  - Postinstall script now properly detects FFmpeg even if not in PATH
  - Shows helpful PATH instructions when FFmpeg is found but not in system PATH
  - FFmpeg detection now works reliably on Windows, macOS, and Linux
- **Version command** - Fixed `arena --version` showing outdated 0.1.0 instead of reading from package.json dynamically
  - Now reads version from package.json using ES module-compatible file reading
  - Version will always stay in sync with package.json

### Changed
- **Documentation** - Rewrote README following Open Core standards
  - Reduced from 693 to 315 lines (55% reduction)
  - More concise, action-oriented, and scannable
  - Improved quick start section
  - Better visual hierarchy and structure
  - Focused on getting users productive quickly

### Improved
- **Better error handling** - Python package installation now shows helpful tips on failure
- **Windows compatibility** - Added shell mode for pip spawning on Windows for better compatibility
- **Windows PATH guidance** - Shows instructions to add FFmpeg to PATH when found in common locations

## [0.3.2] - 2026-01-23

### Fixed
- **CRITICAL: Windows installation** - Fixed postinstall script not being included in npm package
- Added `scripts/` directory to published files so postinstall.cjs is available on Windows

## [0.3.1] - 2026-01-20

### Changed
- **🌍 UNIVERSAL PLATFORM SUPPORT** - Arena now supports ALL platforms and package managers
  - Windows: winget, chocolatey, manual
  - macOS: Homebrew, MacPorts
  - Linux: apt, yum, dnf, pacman, zypper
- **Better messaging** - Postinstall now clearly shows "Works on ALL platforms"
- **Auto-detection** - Setup command automatically detects your package manager
- **More helpful** - Shows platform-specific instructions for your system

### Added
- Support for 10+ package managers across all platforms
- Automatic package manager detection in setup command
- Platform-specific installation instructions

## [0.3.0] - 2026-01-20

### Added
- **🚀 MAJOR: Automatic dependency checking on install** - Post-install script checks for Python and FFmpeg
- **Smart dependency resolution** - Automatically finds system or bundled dependencies
- **Improved onboarding** - Users get immediate feedback on what's needed after `npm install`
- **Dependency utilities** - New utils/deps.ts for finding Python/FFmpeg paths

### Changed
- **Simplified installation** - Just `npm install -g @whitegodkingsley/arena-cli` and you're guided through setup
- **Better error messages** - Clear guidance on what's missing and how to install it
- **Post-install guidance** - Platform-specific installation instructions shown automatically

### Installation Flow (New)
```bash
# 1. Install Arena
npm install -g @whitegodkingsley/arena-cli

# Post-install automatically checks dependencies and shows:
# ✓ Python 3.9+ found
# ✗ FFmpeg missing
# Run: arena setup (to auto-install)

# 2. Run setup to auto-install missing deps
arena setup

# 3. Start using
arena process video.mp4 -p tiktok
```

## [0.2.0] - 2026-01-20

### Added
- **🔧 NEW: `arena setup` command** - Automated dependency checker and installer
  - Checks for Python 3.9+, pip, and FFmpeg
  - Auto-installs missing dependencies (macOS/Linux)
  - Installs required Python packages (openai-whisper, openai, ffmpeg-python, torch, etc.)
  - Interactive prompts guide users through installation
  - Platform-specific installation commands for macOS, Linux, Windows

### Changed
- **Improved onboarding experience** - Users no longer need to manually install all dependencies
- **Better error messages** - Setup command provides clear installation instructions

### Usage
```bash
# After installing Arena CLI with npm
npm install -g @whitegodkingsley/arena-cli

# Run setup to install all dependencies automatically
arena setup

# Start using Arena
arena process video.mp4 -p tiktok
```

## [0.1.4] - 2026-01-20

### Added
- **One-step platform formatting** - Added `-p, --platform` flag to `process` command for automatic platform formatting
- Platform formatting options: `--crop`, `--pad`, `--pad-color` can now be used with `process` command
- Auto-format clips for TikTok, Instagram Reels, YouTube Shorts, and other platforms in one command

### Changed
- Improved workflow: No longer need to run separate `format` command after `process`
- Clips are now automatically formatted for target platform if `-p` flag is specified

### Example
```bash
# Old workflow (still works):
arena process video.mp4 -o output
arena format output/clips -p tiktok -o output/tiktok

# New workflow (one command):
arena process video.mp4 -o output -p tiktok
```

## [0.1.3] - 2026-01-20

### Fixed
- **CRITICAL: ES Module compatibility** - Fixed `__dirname is not defined` error by replacing with ES module equivalent using `import.meta.url` and `fileURLToPath`
- This fix resolves the runtime error when running the CLI after npm installation

## [0.1.2] - 2026-01-20

### Fixed
- **CRITICAL: Windows compatibility** - Fixed ES Module error by switching from CommonJS to ES2022 modules
- **Package description** - Updated from "video editing" to "video clip generation tool"
- **Terminology consistency** - All references updated to "video clip generation"

### Changed
- Module system: CommonJS → ES2022 (fixes Windows `ERR_REQUIRE_ESM` error)
- Added `"type": "module"` to package.json

## [0.1.1] - 2026-01-20

### Changed
- Updated package description and terminology

## [0.1.0] - 2026-01-20

### Added
- **Scene Detection System** - New `detect-scenes` command and `--scene-detection` flag
  - Standalone `arena detect-scenes` command for analyzing scene boundaries
  - `--scene-detection` flag for `process` and `analyze` commands
  - FFmpeg-based visual scene change detection
  - Configurable threshold and minimum scene duration
  - Detailed scene report generation
  - Align clip boundaries to natural scene transitions

### Changed
- Updated command count from 8 to 9 commands
- Enhanced documentation with scene detection workflows

## [0.1.0] - 2026-01-19

### Added
- **Complete production-ready CLI implementation**
- **All 8 commands fully functional:**
  - `arena init` - Interactive setup wizard
  - `arena process` - All-in-one processing with 4-layer support
  - `arena transcribe` - Transcription only
  - `arena analyze` - Analysis without video generation
  - `arena generate` - Generate clips from analysis
  - `arena format` - Platform formatting for social media (NEW!)
  - `arena config` - Configuration management
  - `arena extract-audio` - Audio extraction
- **Platform formatting system** supporting 7 social media platforms:
  - TikTok (1080×1920, 9:16)
  - Instagram Reels (1080×1920, 9:16)
  - YouTube Shorts (1080×1920, 9:16)
  - YouTube (1920×1080, 16:9)
  - Instagram Feed (1080×1080, 1:1)
  - Twitter/X (1280×720, 16:9)
  - LinkedIn (1920×1080, 16:9)
- **Smart cropping strategies:** center, smart (face-aware), top, bottom
- **Padding strategies:** blur background, black, white, custom color
- **Automatic aspect ratio conversion** for all platforms
- **Batch processing support** for formatting multiple clips
- Comprehensive error handling with actionable messages
- Multi-stage progress tracking with visual feedback
- TypeScript support with full type definitions
- ESLint and Prettier configuration
- Comprehensive documentation (README, USAGE, CLI_REFERENCE, QUICKSTART, SETUP)

### Changed
- Enhanced `process` command with 4-layer system support
- Improved error messages with contextual help and suggestions
- Better progress visualization for long operations
- Updated all documentation to reflect v0.1.0 production state
- Changed terminology from "video editing" to "video clip generation"

### Fixed
- **Permission denied errors** - Added `postbuild` script to set execute permissions automatically
- **Python CLI path errors** - Fixed `runFormat` method to use correct `arena-cli` path
- Graceful shutdown on Ctrl+C with proper cleanup
- Proper handling of Python subprocess errors
- Path resolution for cross-platform compatibility
- Merge conflicts in README.md

### Documentation
- Complete rewrite of main README.md (132 → 475 lines)
- Updated CLI-specific README.md with all 8 commands
- Updated USAGE.md with platform formatting workflows
- Updated CLI_REFERENCE.md with complete command documentation
- Updated QUICKSTART.md with modern CLI examples
- Updated SETUP.md with current installation instructions
- Updated STATUS.md to v0.1.0 production state

## [0.0.1] - 2024-01-17

### Added
- Initial alpha release
- Basic video processing functionality (process command only)
- OpenAI Whisper integration for transcription
- AI-powered clip generation
- 4-layer editorial system (optional)
- Hybrid analysis (AI + audio energy)
- Configuration management (basic)
- Other commands showed "coming soon" placeholders

### Known Issues
- Only `process` command functional
- Basic progress tracking
- Limited error handling
- Documentation incomplete

[Unreleased]: https://github.com/iamwhitegod/arena/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/iamwhitegod/arena/releases/tag/v0.1.0
[0.0.1]: https://github.com/iamwhitegod/arena/releases/tag/v0.0.1
