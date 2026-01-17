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
│  │   - analyze                        │ │
│  │   - generate                       │ │
│  │   - transcribe                     │ │
│  │   - config                         │ │
│  │   - init                           │ │
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
- `--use-4layer` - Use 4-layer editorial system (higher quality)
- `--editorial-model <model>` - gpt-4o or gpt-4o-mini (default: gpt-4o)
- `--export-layers` - Export intermediate layer results
- `--fast` - Fast mode (stream copy)
- `--no-cache` - Force re-transcription

**UX Flow:**
```
$ arena process video.mp4 --use-4layer

✓ Video file found: video.mp4 (1.6 GB)
✓ Python environment ready (3.12.0)
✓ Dependencies installed
✓ Workspace initialized

▶ Processing video with 4-layer editorial system...

[1/4] 📝 Transcription
  ⠋ Transcribing audio... 45%
  ✓ Transcription complete (520s, 889 words)

[2/4] 🧠 AI Analysis
  ⠋ Layer 1: Detecting moments... 12/40
  ✓ Found 40 candidate moments
  ⠋ Layer 2: Analyzing boundaries... 15/40 (parallel)
  ✓ Analyzed 40 complete thoughts
  ⠋ Layer 3: Validating standalone context... 8/40
  ✓ 3 clips passed quality gate (7.5% pass rate)
  ⠋ Layer 4: Packaging clips...
  ✓ Packaged 3 professional clips

[3/4] ⚡ Hybrid Analysis
  ✓ Audio energy analyzed (20 segments)
  ✓ Hybrid scores computed

[4/4] ✂️  Clip Generation
  ⠋ Generating clip 2/3... 67%
  ✓ Generated 3 clips

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✨ Success! Generated 3 professional clips

📊 Summary:
  • Duration: 8m 40s
  • Cost: $0.19 (4-layer with gpt-4o-mini)
  • Pass Rate: 7.5% (strict quality gate)
  • Processing Time: 6m 23s

📁 Output: ~/Desktop/arena/clips/
  1. questions-to-ask-before-learning-tech-skills (46s)
  2. what-i-learned-from-building-my-first-website (37s)
  3. how-to-define-your-tech-goals-as-an-engineer (46s)

💡 Next steps:
  • Review clips: ls ~/Desktop/arena/clips/
  • Try cost-optimized: --editorial-model gpt-4o-mini
  • Debug layers: --export-layers
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

Let's set up your video editing workspace.

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
  ❯ Balanced (4-layer + gpt-4o-mini, $0.20/video)
    High Quality (4-layer + gpt-4o, $0.50/video)
    Cost Optimized (standard mode, $0.05/video)

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
arena analyze video.mp4 [--use-4layer]
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

## Python Bridge Design

### Communication Protocol

**Method:** JSON-RPC over stdout/stderr

**Request Format:**
```json
{
  "command": "process",
  "params": {
    "video_path": "/path/to/video.mp4",
    "output_dir": "/path/to/output",
    "use_4layer": true,
    "editorial_model": "gpt-4o-mini",
    "num_clips": 5,
    "min_duration": 20,
    "max_duration": 90
  }
}
```

**Progress Updates (streamed on stdout):**
```json
{"type": "progress", "stage": "transcription", "percent": 45, "message": "Transcribing audio..."}
{"type": "progress", "stage": "layer1", "percent": 30, "message": "Found 12/40 moments"}
{"type": "progress", "stage": "layer2", "percent": 50, "message": "Analyzing 20/40 boundaries"}
{"type": "progress", "stage": "layer3", "percent": 20, "message": "Validating 8/40 thoughts"}
{"type": "progress", "stage": "clip_generation", "percent": 67, "message": "Generating clip 2/3"}
```

**Final Result:**
```json
{
  "type": "result",
  "success": true,
  "data": {
    "clips": [...],
    "cost": 0.19,
    "pass_rate": 0.075,
    "processing_time": 383
  }
}
```

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

**Package name:** `@arena/cli` or `arena-cli`

**Install:**
```bash
npm install -g arena-cli

# Or run without installing:
npx arena-cli process video.mp4
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

## Implementation Checklist

### Phase 1: Core Infrastructure
- [x] Python bridge with JSON protocol
- [x] Progress tracking system
- [x] Config management
- [x] Workspace initialization
- [ ] Error handling framework

### Phase 2: Commands
- [x] `arena process` (basic)
- [ ] `arena process` (4-layer support)
- [ ] `arena init`
- [ ] `arena analyze`
- [ ] `arena transcribe`
- [ ] `arena generate`
- [ ] `arena config`

### Phase 3: Polish
- [ ] Interactive prompts
- [ ] Better progress bars
- [ ] Colored output
- [ ] Emoji support
- [ ] Help text improvements

### Phase 4: Distribution
- [ ] NPM package setup
- [ ] Build scripts
- [ ] CI/CD for releases
- [ ] Documentation

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
