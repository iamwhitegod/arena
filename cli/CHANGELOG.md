# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
