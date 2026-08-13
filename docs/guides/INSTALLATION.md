# Installing Arena OSS

Arena is local-first software. The npm package installs the TypeScript CLI; `arena setup` creates a private Python processing runtime on the same machine. Videos remain local unless a user explicitly calls an external service such as the OpenAI API or, in the future, Arena Cloud.

## Supported environment

| Dependency | Supported | Purpose |
| --- | --- | --- |
| Node.js | 18 or newer | Arena CLI and the JavaScript runtime used by yt-dlp |
| Python | 3.10–3.12 | Creates Arena's private processing environment |
| FFmpeg and ffprobe | Available on `PATH` | Local video and audio processing |
| macOS, Linux, Windows | Current supported releases | Host operating system |

Python 3.13 is not supported yet because Arena's current scientific-processing dependency set targets Python 3.10–3.12. Deno is not required; Arena already runs on Node.js.

## Install from npm

```bash
npm install -g @whitegodkingsley/arena-cli
arena setup
arena setup --check
arena init
```

`npm install` is intentionally lightweight and does not download executables, run `pip`, or modify system packages. The explicit `arena setup` command:

1. verifies the bundled engine against its SHA-256 manifest;
2. finds a compatible system Python;
3. verifies or offers to install FFmpeg through a known package manager;
4. builds a temporary virtual environment;
5. installs the bundled Arena engine and its Python dependencies;
6. verifies required imports; and
7. atomically promotes the verified environment to the active runtime.

The active runtime is recorded in `~/.arena/runtime/install.json` and stored under `~/.arena/runtime/environments/`. Versioned environment paths are never renamed, which keeps Python console-script launchers portable. Arena does not install packages into the global Python environment.

## Setup commands

```bash
# Read-only installation health check
arena setup --check

# Rebuild a damaged or outdated runtime
arena setup --force

# Approve supported FFmpeg package-manager installation in CI
arena setup --yes
```

Setup is idempotent. If the current CLI version, runtime imports, FFmpeg, and ffprobe are healthy, rerunning it exits without reinstalling anything. Interrupted installs are removed on the next setup run, and an existing working runtime is preserved until its replacement passes verification.

Python package installation has a 15-minute overall timeout. On unusually slow networks, set a larger positive number of minutes before running setup:

```bash
export ARENA_SETUP_TIMEOUT_MINUTES=30
arena setup --force
```

## Custom Arena home

Use `ARENA_HOME` to relocate runtime files, configuration, logs, and cache:

```bash
export ARENA_HOME=/path/with/enough/space/arena
arena setup
```

The Python runtime currently uses approximately 650 MB on macOS arm64. Allow additional space for cached source videos, transcripts, and generated clips.

## Install from source

```bash
git clone https://github.com/iamwhitegod/arena.git
cd arena/cli
npm install
npm link
arena setup
arena setup --check
```

Contributors may still create a separate engine environment for Python development, but end-user commands always prefer the Arena-managed runtime.

## Troubleshooting

### Unsupported or missing Python

Install Python 3.12, then rerun setup:

```bash
# macOS
brew install python@3.12

# Windows
winget install --id Python.Python.3.12 --exact
```

On Linux, install Python 3.10–3.12 and its `venv` module with the distribution package manager.

### FFmpeg is missing

Run `arena setup` in an interactive terminal to approve a detected package-manager command, install FFmpeg manually, or use `arena setup --yes` in a trusted automated environment.

### A download or dependency install was interrupted

```bash
arena setup --force
```

Arena cleans stale temporary environments before it starts. It uses a setup lock to prevent concurrent installers from modifying the runtime.

### Validate the complete environment

```bash
arena setup --check
arena diagnose
```

Do not use global `pip install` as a repair step. Arena setup owns and verifies its Python environment.

## Publishing contract

Maintainers publish only the generated `cli/.package/` directory:

```bash
cd cli
npm run package:stage
npm pack .package --dry-run
npm publish .package --provenance --access public
```

Direct publication from `cli/` is blocked. The staged package uses an explicit allowlist and excludes tests, caches, environment files, development scripts, and downloaded binaries.
