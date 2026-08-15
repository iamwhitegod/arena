# Installing Arena OSS

Arena is an AI-powered, open-source, local-first video clipping engine for the terminal that automatically finds the best moments in your videos and exports platform-ready clips for TikTok, Reels, and Shorts. The npm package installs the TypeScript CLI; `arena setup` creates a private Python processing runtime on the same machine. Videos remain local unless a user explicitly calls an external service such as the OpenAI API or, in the future, Arena Cloud.

## Supported environment

| Dependency            | Supported                  | Purpose                                             |
| --------------------- | -------------------------- | --------------------------------------------------- |
| Node.js               | 22–24                      | Arena CLI and the JavaScript runtime used by yt-dlp |
| Python                | 3.10–3.12                  | Creates Arena's private processing environment      |
| FFmpeg and ffprobe    | Available on `PATH`        | Local video and audio processing                    |
| macOS, Linux, Windows | Current supported releases | Host operating system                               |

Python 3.13 is not supported yet because Arena's current scientific-processing dependency set targets Python 3.10–3.12. Deno is not required; Arena already runs on Node.js.

When multiple supported Python installations exist, set `ARENA_PYTHON` to the exact interpreter path before running `arena setup`. Arena validates that interpreter before creating its private runtime.

## Verification status

Release-candidate verification is active. The release-blocking hosted matrix is green; the remaining gate is verification of the exact npm and Docker artifacts after public registry publication.

| Path   | Verified progress                                                                                                                                                                                                                                                                                                                                                                                                                          | Remaining release evidence                                                                                                                                   |
| ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| npm    | The exact packed release artifact passes clean installation and CLI startup on Ubuntu x64, Windows x64, and macOS ARM64 with Node.js 22 and 24. Managed-runtime run [31828709997](https://github.com/iamwhitegod/arena/actions/runs/31828709997) passed Node.js 22/Python 3.10 and Node.js 24/Python 3.12 on all three OS families, including isolated setup, health checks, idempotency, credential-free local processing, and uninstall. | Publish `0.4.3-rc.1` under the non-default `next` tag, verify npm signatures/provenance, and rerun the same installation contract from the public registry   |
| Source | The complete TypeScript/Python source matrix is green. The source-install workflow now exercises the documented `npm install`, `npm link`, setup, health-check, local-processing, and unlink path at every release-blocking Node/Python boundary.                                                                                                                                                                                          | Retain a green source-install workflow run from the exact release commit                                                                                     |
| Docker | Arena `0.4.2` remains published as one attested OCI index for Linux AMD64 and ARM64 at digest `sha256:b1bfbc0ca0696d550ba5520a7fbff196721af6cd8a0643ec8d08e13583495b1b`. Both exact registry manifests passed non-root, read-only, network-disabled, capability-dropped startup. Release-candidate builds for both architectures pass local processing and high/critical vulnerability scans.                                              | Publish the exact `0.4.3-rc.1` multi-architecture index and verify its registry digest, platform manifests, SBOM/provenance attestations, scans, and runtime |

These results mean Arena is hardened across the declared release-blocking platforms. Do not describe the release candidate as registry-verified until the public npm and Docker canaries in the [installation verification plan](../development/plans/installation-verification.md) are green.

The production container intentionally excludes npm, npx, Corepack, and their package-manager shims. They are used in the builder stage only; the runtime executes the already-built `arena` CLI. This removes build-only tooling and its transitive advisories from the image without changing the user-facing container command.

## Install from the official Docker image

Docker users should not clone the repository or install Node.js, Python, or FFmpeg. Pull a released multi-architecture image and mount only the directory containing the media to process:

```bash
export ARENA_IMAGE=whitegodkingsley/arena:0.4.2
docker pull "$ARENA_IMAGE"
docker volume create arena-data

docker run --rm \
  --read-only \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g \
  --mount "type=bind,source=$PWD,target=/workspace" \
  --mount type=volume,source=arena-data,target=/home/node/.arena \
  --env OPENAI_API_KEY \
  "$ARENA_IMAGE" process /workspace/video.mp4 -n 5
```

Use an exact version in scripts and production workflows. `latest` tracks the newest stable release only; pre-releases cannot update it. Docker selects the AMD64 or ARM64 image matching the host.

Arena `0.4.2` is published at `docker.io/whitegodkingsley/arena`. The `latest`, `0`, `0.4`, `0.4.2`, and immutable `sha-7f7fd269d130` tags currently resolve to OCI index digest `sha256:b1bfbc0ca0696d550ba5520a7fbff196721af6cd8a0643ec8d08e13583495b1b`. Each platform manifest includes SBOM and provenance attestations. Source builds remain available to contributors, but they are not the Docker installation path.

In Windows PowerShell, use the native path from `$PWD.Path` for the bind mount:

```powershell
$env:ARENA_IMAGE = "whitegodkingsley/arena:0.4.2"
docker pull $env:ARENA_IMAGE
docker run --rm `
  --read-only `
  --cap-drop ALL `
  --security-opt no-new-privileges `
  --tmpfs /tmp:rw,noexec,nosuid,nodev,size=2g `
  --mount "type=bind,source=$($PWD.Path),target=/workspace" `
  --mount type=volume,source=arena-data,target=/home/node/.arena `
  --env OPENAI_API_KEY `
  $env:ARENA_IMAGE process /workspace/video.mp4 -n 5
```

## Install from npm

```bash
npm install --global @whitegodkingsley/arena-cli@0.4.2
arena --version
arena setup
arena setup --check
arena init
```

Arena `0.4.2` is the current npm `latest` release. Use the exact version above for reproducible installation; use `npm install --global @whitegodkingsley/arena-cli` only when you intentionally want the moving `latest` tag. The public package is available at [npmjs.com/package/@whitegodkingsley/arena-cli](https://www.npmjs.com/package/@whitegodkingsley/arena-cli).

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

Each Python package-installation subprocess has a 15-minute timeout. On unusually slow networks, set a larger positive number of minutes before running setup:

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

## Maintainer next steps

1. Require the source, packed-tarball, managed-runtime, security, and container workflows on pull requests and release commits.
2. Publish the approved release candidate under non-default npm and Docker tags and dispatch the public-registry canary.
3. Retain provenance, registry metadata, setup, processing, recovery, and per-platform container evidence for the exact release commit.
4. Promote the exact verified candidate without rebuilding it; keep stable tags unchanged when any canary fails.
5. Add native Linux ARM64, Intel macOS, and Windows ARM64 runners if those best-effort platforms move into the release-blocking support tier.

Publishing or changing npm distribution tags remains an explicit maintainer action.

## Publishing contract

Maintainers publish only the generated `cli/.package/` directory:

```bash
cd cli
npm run package:stage
npm pack .package --dry-run
npm publish .package --provenance --access public
```

Direct publication from `cli/` is blocked. The staged package uses an explicit allowlist and excludes tests, caches, environment files, development scripts, and downloaded binaries.

The npm package page renders `cli/README.md` from the published tarball. Updating that README in Git does not mutate an existing npm version; its changes appear on npm only when a new immutable package version is published.
