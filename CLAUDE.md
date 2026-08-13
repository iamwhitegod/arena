# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arena is an AI-powered video clip generation tool that extracts the best moments from long-form video content and repurposes them for social media. It uses a hybrid TypeScript (CLI) + Python (engine) architecture.

## Build & Development Commands

All CLI commands run from the `cli/` directory:

```bash
# Install dependencies
cd cli && npm install
cd engine && pip install -r requirements.txt

# Build
npm run build          # TypeScript -> dist/ (runs clean + tsc + chmod)
npm run watch          # Watch mode

# Dev (no build needed)
npm run dev            # Runs directly via tsx

# Test
npm test               # Vitest (run all tests)
npm run test:watch     # Watch mode
npm run test:coverage  # Coverage report

# Lint & Format
npm run lint           # ESLint check
npm run lint:fix       # ESLint auto-fix
npm run format         # Prettier write
npm run format:check   # Prettier check only

# Python engine tests
cd engine && pytest tests/
pytest tests/test_week1_validation.py   # Single test file
```

## Pre-commit Hooks

Husky runs on every commit (from `.husky/pre-commit`):
1. `cd cli && npx lint-staged` - runs Prettier + ESLint on staged `.ts` files
2. `npm test` - runs the full Vitest suite

Both must pass for commits to succeed.

## Architecture

```
CLI (TypeScript/Node.js)          Engine (Python)
─────────────────────             ──────────────────
index.ts (commander)              arena_process.py (pipeline orchestrator)
  └─ commands/*.ts                  ├─ audio/ (transcriber, energy analysis)
       └─ PythonBridge              ├─ ai/ (GPT analysis, hybrid scoring)
            │                       ├─ editorial/ (4-layer system)
            │ spawn + JSON stdout   ├─ clipping/ (FFmpeg extraction)
            └───────────────────►   ├─ video/ (scene detection)
                                    └─ export/ (platform formatting)
```

### CLI-to-Engine Communication

`PythonBridge` (`cli/src/bridge/python-bridge.ts`) spawns the Python engine as a child process. The engine writes JSON lines to stdout for progress updates. The CLI parses these in real-time to drive `ProgressTracker` UI. Final results are written to JSON files on disk.

Key bridge methods: `runProcess()`, `runAnalyze()`, `runTranscribe()`, `runGenerate()`, `runFormat()`, `runDetectScenes()`.

### Command Flow

Every CLI command follows this pattern:
1. Parse options via Commander
2. Run preflight checks (`core/preflight.ts`) - validates inputs, API key, Python env
3. Initialize workspace (`core/workspace.ts`) - creates `.arena/` cache dirs
4. Call PythonBridge method with translated args
5. Track progress via callbacks
6. Display summary (`ui/summary.ts`)
7. Catch and format errors (`errors/formatter.ts`)

### 4-Layer Editorial System

The core differentiator, in `engine/arena/editorial/`. Orchestrated by `FourLayerAdapter` (`adapter.py`), the primary analysis engine:

- **Layer 1** (`thought_seed_detector.py`): Scans transcript in sliding 2-min windows, detects ~40 "seeds" (claims, insights, hooks), deduplicates by time + text similarity
- **Layer 2** (`thought_unit_constructor.py`): Expands seeds into complete thought units (premise -> claim -> resolution) using `premise_detector.py` and `resolution_detector.py`
- **Layer 3** (`completeness_scorer.py` + `standalone_validator.py`): Scores completeness 0-10, validates clips make sense without surrounding context. Strict gate (~7-10% pass rate)
- **Layer 4** (`semantic_deduplicator.py` + `variant_selector.py`): Deduplicates using text-embedding-3-small cosine similarity, selects best variant per cluster

The `CheckpointManager` (`checkpoint.py`) saves intermediate results between layers, enabling resume on failure. Job ID = hash of first 500 chars of transcript.

### Hybrid Analysis

`HybridAnalyzer` (`engine/arena/ai/hybrid.py`) combines two signals:
- AI content scores from GPT analysis
- Audio energy scores from RMS + spectral centroid analysis (`engine/arena/audio/energy.py`)
- Final score = `ai_score * (1 - energy_weight) + energy_score * energy_weight` (default 30% energy weight)

## Key Configuration

- **Global config**: `~/.arena/config.json` (API key, defaults)
- **Project config**: `.arena/config.json` (per-project overrides)
- **Workspace cache**: `.arena/cache/` (transcripts, analysis results)
- **Logs**: `~/.arena/logs/arena-YYYY-MM-DD.log` (rotating, 10MB max)

## TypeScript Conventions

- ES2022 target, ES modules (`"type": "module"`)
- Strict mode enabled
- Unused vars prefixed with `_` (ESLint rule)
- `no-console` is off (CLI app)
- `@typescript-eslint/no-explicit-any` is warn-only
- Vitest uses `forks` pool (needed for `process.chdir()` in tests)
- Test timeout: 30 seconds

## Python Conventions

- Python 3.10–3.12
- Entry point: `arena-engine=arena.main:main` (via setup.py)
- Direct invocation: `python3 engine/arena_process.py --video-path input.mp4`
- Concurrency via `ThreadPoolExecutor` for batch API calls (default 5 workers)
- Retry with exponential backoff for OpenAI API calls (`editorial/retry.py`)
- Every module tracks metrics dict: `api_calls`, `tokens_used`, `cost_usd`

## External Dependencies

- **OpenAI API** (GPT-4o/4o-mini for analysis, Whisper for transcription, text-embedding-3-small for dedup)
- **FFmpeg/ffprobe** (video processing, clip extraction, format conversion)
