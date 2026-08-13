# Arena Node CLI - Production Design

## Design Philosophy

**Goal:** Create an industry-standard CLI tool that other developers love to use.

**Inspiration:** Vercel CLI, Next.js CLI, Prisma CLI, Netlify CLI

**Core Principles:**
1. **Fast startup** (<100ms for help, <200ms for commands)
2. **Clear feedback** (progress bars, spinners, emojis)
3. **Helpful errors** (actionable suggestions, not stack traces)
4. **Smart defaults** (works out of box, configurable when needed)
5. **Discoverable** (help text guides users to next action)
6. **Interruptible** (Ctrl+C works cleanly)

---

## Architecture

```
┌─────────────────────────────────────────┐
│         Arena CLI (Node/TypeScript)      │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │   Commands (user-facing)           │ │
│  │   - process                        │ │
│  │   - transcribe                     │ │
│  │   - analyze                        │ │
│  │   - generate                       │ │
│  │   - format                         │ │
│  │   - detect-scenes                  │ │
│  │   - extract-audio                  │ │
│  │   - config                         │ │
│  │   - init                           │ │
│  │   - setup                          │ │
│  │   - diagnose                       │ │
│  └────────────────────────────────────┘ │
│              ↓                           │
│  ┌────────────────────────────────────┐ │
│  │   Core Services                    │ │
│  │   - PythonBridge (subprocess)      │ │
│  │   - Workspace (file management)    │ │
│  │   - ConfigManager (settings)       │ │
│  │   - ProgressTracker (UI feedback)  │ │
│  └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
              ↓ (subprocess + JSON)
┌─────────────────────────────────────────┐
│      Python Engine (Processing Core)     │
│      - arena_process.py                  │
│      - 4-layer editorial system          │
│      - Video/audio processing            │
└─────────────────────────────────────────┘
```

---

## Command Structure

### `arena process` (Main Command)
**Purpose:** One-step video → clips pipeline

**Usage:**
```bash
arena process video.mp4 [options]
```

**Options:**
- `-o, --output <dir>` - Output directory (default: output)
- `-n, --num-clips <number>` - Number of clips (default: 5)
- `--min <seconds>` - Minimum duration (default: 30)
- `--max <seconds>` - Maximum duration (default: 90)
- `--editorial-model <model>` - gpt-4o or gpt-4o-mini (default: gpt-4o)
- `--export-layers` - Export intermediate layer results
- `--fast` - Fast mode (stream copy)
- `--no-cache` - Force re-transcription
- `-p, --platform <platform>` - Auto-format for platform (tiktok, instagram-reels, etc.)
- `--captions` - Burn subtitle captions into clips
- `--cookies-from-browser <browser>` - Use browser cookies for YouTube downloads
- `--scene-detection` - Enable scene detection for clip boundaries

**UX Flow:**
```
$ arena process video.mp4

Arena

Input   video.mp4
Output  /path/to/output
Target  8 clips · 30–90s

✓ Preflight passed
[1/4] ✓ Transcription — Transcription complete
[2/4] ◐ Analysis
      [████████████░░░░░░░░] 62% · Scoring candidate moments
[3/4] ○ Clip Alignment
[4/4] ○ Clip Generation

✓ Done — generated 3 clips in 6m 23s

Input   video.mp4
Output  /path/to/output
```

---

### `arena init` (New Command)
**Purpose:** Initialize Arena in project with interactive setup

**Usage:**
```bash
arena init
```

**UX Flow:**
```
$ arena init

✨ Welcome to Arena!

Let's set up your video clip generation workspace.

? Select your workflow:
  ❯ Content Creator (social media clips)
    Podcast Editor (long-form → highlights)
    Course Creator (educational snippets)
    Custom (configure manually)

? Default clip duration:
  ❯ Short (15-30s) - TikTok, Instagram Reels
    Medium (30-60s) - YouTube Shorts
    Long (60-120s) - Full segments

? Quality vs Cost preference:
  ❯ Balanced (gpt-4o-mini, $0.20/video)
    High Quality (gpt-4o, $0.50/video)

✓ Created ~/.arena/config.json
✓ Workspace ready!

💡 Try it now:
  arena process video.mp4
```

---

### `arena analyze`
**Purpose:** Analyze video without generating clips (fast preview)

**Usage:**
```bash
arena analyze video.mp4 []
```

**Output:**
- Transcript JSON
- Interesting moments detected
- Preview of what clips would be generated

---

### `arena transcribe`
**Purpose:** Transcribe only (for review/editing)

**Usage:**
```bash
arena transcribe video.mp4 [-o transcript.json]
```

---

### `arena generate`
**Purpose:** Generate clips from existing analysis

**Usage:**
```bash
arena generate analysis.json [--select 1,3,5]
```

**Workflow:**
```bash
# Step 1: Analyze (fast, cheap)
arena analyze video.mp4 > moments.json

# Step 2: Review moments.json, pick favorites

# Step 3: Generate only selected clips
arena generate moments.json --select 1,5,7
```

---

### `arena config`
**Purpose:** Manage configuration interactively

**Usage:**
```bash
arena config              # View current config
arena config set <key> <value>
arena config get <key>
arena config reset
```

---

### `arena format`
**Purpose:** Format clips for social media platforms with optimal specs

**Usage:**
```bash
arena format <input> -p <platform> [options]
```

**Options:**
- `-p, --platform <platform>` - Target platform (tiktok, instagram-reels, youtube-shorts, youtube, instagram-feed, twitter, linkedin)
- `-o, --output <dir>` - Output directory
- `--crop <strategy>` - Crop strategy: center, smart, top, bottom (default: center)
- `--pad <strategy>` - Pad strategy: blur, black, white, color (default: blur)
- `--pad-color <color>` - Padding color hex (default: #000000)

---

### `arena detect-scenes`
**Purpose:** Detect visual scene changes in video

**Usage:**
```bash
arena detect-scenes <video> [options]
```

**Options:**
- `-o, --output <file>` - Output scene data file
- `--threshold <value>` - Detection sensitivity (default: 0.4)
- `--min-duration <seconds>` - Minimum scene duration (default: 2.0)
- `--report` - Generate visual report

---

### `arena extract-audio`
**Purpose:** Extract audio from video in various formats

**Usage:**
```bash
arena extract-audio <video> [options]
```

**Options:**
- `-o, --output <file>` - Output audio path
- `--format <mp3|wav|aac|flac>` - Audio format (default: mp3)
- `--bitrate <rate>` - Audio bitrate (default: 192k)
- `--sample-rate <rate>` - Sample rate in Hz
- `--mono` - Convert to mono

---

### `arena setup`
**Purpose:** Check and install Arena dependencies automatically

**Usage:**
```bash
arena setup
```

Detects your OS and package manager, then installs missing dependencies (Python, FFmpeg, Deno, pip packages).

---

### `arena diagnose`
**Purpose:** Run comprehensive system diagnostics

**Usage:**
```bash
arena diagnose
```

Checks system info, dependencies (Python, FFmpeg, Deno), Python packages, API key, network, and disk space.

---

## Python Bridge Design

### Communication Protocol

**Method:** newline-delimited JSON events over stdout. Stderr and unstructured output are buffered for failure diagnostics.

**Progress Updates (streamed on stdout):**
```json
{"type": "progress", "stage": "transcription", "progress": 45, "message": "Transcribing audio"}
{"type": "progress", "stage": "analysis", "progress": 62, "message": "Scoring candidate moments"}
{"type": "progress", "stage": "alignment", "progress": 100, "message": "Clip boundaries aligned"}
{"type": "progress", "stage": "generation", "progress": 67, "message": "Generated clip 2 of 3"}
{"type": "progress", "stage": "formatting", "progress": 100, "message": "Platform formatting complete"}
```

**Final Result:**
```json
{
  "type": "result",
  "data": {
    "success": true,
    "outputDir": "/path/to/output"
  }
}
```

The Node CLI is the only presentation owner. Python commands must not emit human-oriented banners on the protocol channel. See [CLI output and states](../guides/CLI_OUTPUT.md) for state semantics and supported stage IDs.

**Error Format:**
```json
{
  "type": "error",
  "code": "TRANSCRIPTION_FAILED",
  "message": "OpenAI API key not set",
  "suggestion": "Set OPENAI_API_KEY environment variable"
}
```

---

## Error Handling

### Error Categories

1. **Pre-flight errors** (before processing)
   - File not found
   - Python not installed
   - Dependencies missing
   - API key not set

2. **Processing errors** (during execution)
   - Transcription failed
   - API rate limit
   - Out of memory
   - No clips passed validation

3. **System errors** (unexpected)
   - Python crashed
   - Disk full
   - Permission denied

### Error UX

**Good Error (actionable):**
```
✗ OpenAI API key not set

  Arena needs an OpenAI API key to transcribe and analyze videos.

  → Get an API key:
    https://platform.openai.com/api-keys

  → Set it in one of these ways:

    1. Environment variable:
       export OPENAI_API_KEY="sk-..."

    2. Config file (~/.arena/config.json):
       {
         "openai_api_key": "sk-..."
       }

  → Then try again:
    arena process video.mp4
```

**Bad Error (not actionable):**
```
Error: APIError: 401 Unauthorized
  at OpenAI.request (node_modules/openai/core.ts:123)
  at OpenAI.transcribe (node_modules/openai/audio.ts:45)
  ...
```

---

## Progress Tracking

### Design Principles

1. **Show what's happening now** (current stage)
2. **Show overall progress** (X/Y complete)
3. **Show time estimates** (when possible)
4. **Keep it compact** (single line updates)
5. **Be honest** (don't fake progress)

### Progress Bar Styles

**Spinner (indeterminate):**
```
⠋ Transcribing audio...
```

**Progress Bar (determinate):**
```
[████████░░] 80% Layer 2: Analyzing boundaries (32/40)
```

**Multi-stage:**
```
[2/4] 🧠 AI Analysis
  ✓ Layer 1: Found 40 moments
  ⠋ Layer 2: Analyzing boundaries... 20/40
  ⏳ Layer 3: Pending
  ⏳ Layer 4: Pending
```

---

## Distribution

### NPM Package

**Package name:** `@whitegodkingsley/arena-cli` or `@whitegodkingsley/arena-cli`

**Install:**
```bash
npm install -g @whitegodkingsley/arena-cli

# Or run without installing:
npx @whitegodkingsley/arena-cli process video.mp4
```

### Standalone Binary (Future)

**Using `pkg` or `nexe`:**
```bash
# Download and run (no Node.js required)
curl -L https://arena.dev/install.sh | bash
arena process video.mp4
```

---

## Testing Strategy

### Unit Tests
- Command parsing
- Config management
- Python bridge communication

### Integration Tests
- Full pipeline with mock Python engine
- Error handling scenarios
- Progress tracking updates

### E2E Tests
- Real video processing (short test video)
- 4-layer system validation
- All commands work end-to-end

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Startup time (help) | <100ms | Fast feedback |
| Startup time (process) | <200ms | Before actual processing |
| Memory usage | <50MB | CLI overhead only |
| Python subprocess spawn | <500ms | One-time cost |
| Progress update latency | <100ms | Real-time feel |

---

## Implementation Status

### Core Infrastructure
- [x] Python bridge with JSON protocol
- [x] Progress tracking system
- [x] Config management
- [x] Workspace initialization
- [x] Error handling framework (structured errors with suggestions)
- [x] Graceful shutdown (SIGINT/SIGTERM)

### Commands
- [x] `arena process` (full pipeline with 4-layer editorial)
- [x] `arena init` (interactive setup wizard)
- [x] `arena analyze` (analysis without clip generation)
- [x] `arena transcribe` (transcription only, supports URLs)
- [x] `arena generate` (clips from existing analysis)
- [x] `arena config` (configuration management)
- [x] `arena format` (multi-platform formatting)
- [x] `arena detect-scenes` (scene change detection)
- [x] `arena extract-audio` (audio extraction)
- [x] `arena setup` (dependency installation)
- [x] `arena diagnose` (system diagnostics)

### Polish
- [x] Interactive prompts (inquirer)
- [x] Progress bars and spinners (ora)
- [x] Colored output (chalk)
- [x] Terminal hyperlinks (clickable file paths)
- [x] Box-formatted summaries

### Distribution
- [x] NPM package (@whitegodkingsley/arena-cli)
- [x] Build scripts (TypeScript compilation)
- [x] CI/CD (GitHub Actions: test + publish)
- [x] Docker support
- [x] URL support (YouTube, Vimeo, 1000+ sites via yt-dlp)

---

## Success Metrics

**User Experience:**
- Clear what's happening at every step
- Errors are actionable
- Fast feedback (<200ms startup)
- Works first try for 80% of users

**Developer Experience:**
- Easy to add new commands
- Well-tested
- Clean separation Python/Node
- Good documentation

**Production Ready:**
- <0.1% crash rate
- Handles Ctrl+C gracefully
- Works on Mac/Linux/Windows
- Clear upgrade path
