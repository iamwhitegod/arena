# Arena Cross-Platform Installation Verification Plan

**Status:** In progress — automation implemented; native CI evidence pending
**Created:** August 13, 2026
**Depends on:** OSS hardening checkpoint `e90873b`

## Objective

Prove that a real Arena release artifact installs, configures, repairs, and runs predictably across every supported operating system and CPU architecture.

This plan tests the same npm tarball that would be published. Source-checkout tests alone do not qualify as installation verification.

## Current Evidence

The hardening checkpoint establishes a strong baseline:

- A clean Node.js 22 container install completed with zero npm advisories.
- The CLI suite passed with 144 tests and one intentionally skipped real-video test.
- The Python suite passed with 106 offline tests and four explicitly skipped live-provider tests.
- The final staged npm package contained 180 allowlisted files and passed manifest verification.
- The exact tarball, SHA-256 `1e324ce2e64fe643a1175d524823918e9d7adaccba7a1f30bef2c7974ac9e9ee`, installed from an empty cache and passed startup, manifest, Unicode-path, and uninstall checks on macOS ARM64 with Node.js 22.
- The Linux ARM64 container built and processed a deterministic local video as a non-root user with a read-only root filesystem and dropped capabilities.
- The runtime and development Python locks passed vulnerability auditing.

This evidence does not yet prove native installation on Windows, Linux AMD64, macOS Intel, macOS Apple Silicon, Node.js 24, or each supported Python boundary.

## Next Execution Steps

Execute these in order; workflow configuration alone is not verification:

1. Push this checkpoint and run the source and packed-tarball pull-request matrices on Ubuntu, Windows, and macOS.
2. Review the retained JSON evidence for artifact digest, package and engine versions, architecture, empty-cache installation, executable resolution, setup isolation, and sanitized output.
3. Manually dispatch the managed-runtime matrix for the Node.js 22/Python 3.10 and Node.js 24/Python 3.12 boundary pairs.
4. Run the Buildx AMD64/ARM64 workflow, hardened runtime assertions, Compose smoke test, and per-platform vulnerability scans.
5. Provision native Linux ARM64 and Intel macOS runners for evidence that hosted or emulated jobs cannot provide.
6. Add setup failure-injection coverage for interrupted downloads, locks, repair, read-only paths, insufficient disk, and preservation of the last healthy runtime.
7. After all release-blocking evidence is green, publish an explicitly approved npm canary under a non-default tag and promote that exact artifact without rebuilding it.

Do not check off a platform or release gate until its retained evidence has been reviewed.

## Support Contract to Resolve First

Before expanding the matrix, make the supported-version contract consistent everywhere:

- [x] Make Node.js 22–24 the single documented range in `package.json`, installation docs, CI, diagnostics, and runtime error messages.
- [x] Make Python 3.10–3.12 the single documented range in engine metadata, setup discovery, CI, and user-facing help.
- [x] Add repository runtime selectors such as `.node-version` and `.python-version` for contributors.
- [x] Add an early CLI runtime guard that produces a clear unsupported-Node error instead of relying only on npm's engine warning.
- [x] Update the pre-commit hook so it fails immediately with the supported Node requirement rather than producing an opaque native-binding error.
- [x] Define which operating-system releases receive release-blocking support and which are best-effort.

The previous Node.js 18 documentation inconsistency is corrected. `SUPPORT.md` is the platform-tier policy, while package and engine metadata remain the toolchain source of truth.

## Definition of Flawless Installation

A target passes only when all applicable checks succeed in a clean environment:

1. Install the generated npm tarball without using repository source files.
2. Complete npm lifecycle scripts without unexpected downloads, shell execution, prompts, or errors.
3. Run `arena --version` and `arena --help` from outside the repository.
4. Run `arena setup --yes` with a supported Python and FFmpeg environment.
5. Verify `arena setup --check` exits zero.
6. Verify the managed Python path is inside an isolated `ARENA_HOME`, not the system environment.
7. Verify required engine imports and FFmpeg/ffprobe execution.
8. Rerun setup and confirm it is idempotent.
9. Run `arena setup --force` and confirm atomic replacement preserves a working runtime until the replacement passes.
10. Process a small, local, license-safe fixture without requiring Arena Cloud or URL downloads.
11. Confirm generated artifacts remain inside the selected workspace and Arena home.
12. Confirm logs and diagnostics contain no credentials or environment secrets.
13. Uninstall the npm package and confirm only explicitly retained user data remains.

Any manual intervention not described in the installation guide is a failure.

## Required Native Matrix

At minimum, test the lower and upper supported Node/Python boundaries on each target. Run the complete four-way Node/Python combination on the primary Linux target and boundary pairs elsewhere to control CI cost.

| Host | Architecture | Boundary pair A | Boundary pair B | Status |
| --- | --- | --- | --- | --- |
| Ubuntu LTS | x86_64 | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Unverified |
| Ubuntu LTS | ARM64 | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Unverified natively |
| Windows | x86_64 | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Unverified |
| macOS | Apple Silicon | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Local Node 22 consumer startup verified; setup matrix pending |
| macOS | Intel | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Unverified |

Additional primary-Linux combinations:

- [ ] Node 22 + Python 3.12
- [ ] Node 24 + Python 3.10

If a required architecture is unavailable on hosted CI, use an ephemeral self-hosted runner or a clean-machine provider. Emulation may supplement but must not replace at least one native run for Windows and both macOS architectures.

## Required Docker Matrix

| Target | Build | Runtime smoke test | Compose smoke test | Status |
| --- | --- | --- | --- | --- |
| `linux/amd64` | Required | Required | Required | Unverified |
| `linux/arm64` | Required | Required | Required | Local build/start/media/Compose verified; CI scan pending |

Each target must prove:

- [ ] The digest-pinned base builds through `docker buildx`.
- [ ] The resulting image reports the expected architecture.
- [ ] The image runs as the non-root `node` user.
- [ ] `arena --version` works with a read-only root filesystem.
- [ ] All Linux capabilities are dropped and `no-new-privileges` is enabled.
- [ ] Only `/tmp`, `/workspace`, and the Arena data volume are writable as documented.
- [ ] Node, Python, FFmpeg, ffprobe, Pillow, Arena, and yt-dlp import or execute successfully.
- [ ] A local fixture can be processed through a bind-mounted workspace.
- [ ] The image passes the configured high/critical vulnerability scan.

## Phase 1: Consumer Artifact Harness

Build one cross-platform smoke-test harness and use it everywhere.

- [x] Stage and pack `cli/.package` once per workflow.
- [x] Record the tarball SHA-256 and exact file inventory.
- [x] Create a fresh temporary consumer directory outside the repository.
- [x] Install with `npm install --global <absolute-tarball-path>` or an isolated npm prefix.
- [x] Prevent Arena registry fallback by verifying the tarball digest, prepared-artifact marker, installed package identity, version, and engine manifest.
- [x] Set isolated `ARENA_HOME`, npm cache, temporary directory, and workspace paths.
- [x] Exercise paths containing spaces and non-ASCII characters.
- [x] Capture structured results containing OS, architecture, Node, npm, Python, FFmpeg, CLI, and engine versions.
- [x] Upload logs and the tested tarball as CI artifacts on both success and failure.

Recommended deliverables:

```text
cli/scripts/consumer-install-smoke.cjs
.github/workflows/install-smoke.yml
.github/workflows/setup-smoke.yml
.github/workflows/container-smoke.yml
```

The harness uses Node process APIs rather than Bash-specific syntax so the same assertions run on Windows, macOS, and Linux. The media fixture is generated deterministically with FFmpeg at test time, avoiding a binary fixture and its licensing or repository-size burden.

## Phase 2: Native npm Installation

- [x] Add Windows to the normal test matrix.
- [x] Add a separate installation workflow because consumer installation is slower and has different failure evidence from unit tests.
- [ ] Install the packed tarball on every hosted release-blocking matrix target. The workflow is implemented; target evidence is pending.
- [ ] Verify global executable resolution on POSIX and Windows `PATHEXT` behavior. POSIX is locally verified; Windows is pending.
- [ ] Verify paths containing spaces and Unicode on Windows, macOS, and Linux. macOS ARM64 is locally verified; Windows and Linux are pending.
- [ ] Confirm npm postinstall remains read-only and never makes installation fail because FFmpeg or Python is absent on every OS family. macOS ARM64 is locally verified.
- [ ] Confirm a missing prerequisite produces one clear actionable message.
- [ ] Test non-administrator Windows installation and a standard non-root POSIX account.
- [x] Test installation with an empty npm cache.
- [ ] Test installation behind a deliberately slow or interrupted dependency connection.

Exit criterion: all required native targets install the same tarball and pass CLI startup without repository access.

## Phase 3: Managed Runtime Setup

For each native target:

- [ ] Preinstall FFmpeg for the deterministic release-blocking path.
- [ ] Run `arena setup --yes` with Python 3.10 and 3.12 boundary jobs.
- [ ] Confirm every pip installation uses `--require-hashes` and the bundled lockfiles.
- [ ] Verify engine manifest validation before installation.
- [ ] Confirm the setup timeout returns exit code 124 or a clearly mapped Arena error.
- [ ] Verify setup does not modify global Python packages.
- [ ] Confirm configuration, credential, runtime, and log permissions where the platform supports POSIX modes.
- [ ] Verify Windows launchers inside the managed virtual environment remain valid after installation.
- [ ] Run setup twice to prove idempotency.
- [ ] Run forced repair after deliberately damaging a non-critical runtime file.
- [ ] Interrupt setup and confirm the next invocation cleans temporary state while preserving the prior healthy runtime.
- [ ] Run two concurrent setup attempts and verify the installation lock prevents corruption.

Exit criterion: every supported Python boundary builds a healthy, isolated Arena runtime on each required OS family.

## Phase 4: Functional Local Processing Smoke Test

Use a tiny, repository-owned fixture that requires no network or paid provider:

- [ ] Validate local media probing with ffprobe.
- [ ] Extract audio with FFmpeg.
- [ ] Detect scenes or perform another deterministic engine operation.
- [ ] Write output beneath the isolated workspace.
- [ ] Verify output is non-empty and media metadata is valid.
- [ ] Confirm no Arena Cloud endpoint is contacted.
- [ ] Record execution time and peak disk usage to detect packaging regressions.

AI-provider integration belongs in a separate opt-in workflow using test credentials. It must not block proof that local installation works.

## Phase 5: Docker Multi-Architecture Verification

- [ ] Configure Buildx for `linux/amd64` and `linux/arm64`.
- [ ] Build both platforms from the same commit and Dockerfile.
- [ ] Load or publish architecture-specific test images to an ephemeral registry location.
- [ ] Run the full hardened-runtime assertions on each architecture.
- [ ] Run `docker compose config` and a Compose startup smoke test.
- [ ] Process the local fixture through a mounted workspace and named Arena data volume.
- [ ] Scan each platform image rather than only the multi-architecture index.
- [ ] Record image digest and compressed/uncompressed size per architecture.
- [ ] Add a size regression budget; investigate growth above 10%.

Exit criterion: both platform images build, scan, start, and process local media with identical observable behavior.

## Phase 6: Published-Package Canary

The packed-tarball test proves artifact construction but not npm registry delivery.

- [ ] Publish a release candidate under a non-default npm dist-tag such as `next`.
- [ ] Install the exact version from the public registry on clean Windows, macOS, and Linux machines.
- [ ] Verify npm provenance and compare the registry tarball digest with the CI-produced artifact.
- [ ] Run setup, health check, local fixture processing, repair, and uninstall.
- [ ] Promote the exact already-tested version to `latest`; do not rebuild between canary and promotion.
- [ ] Document rollback and dist-tag recovery commands.

Publishing is an external change and requires explicit maintainer approval when this phase is executed.

## Failure Scenarios

The following cases need automated assertions, not only happy-path testing:

- [x] Unsupported Node 20 and Node 25 fail with actionable guidance.
- [ ] Unsupported Python 3.9 and 3.13 are rejected without partial runtime creation.
- [ ] Python is absent.
- [ ] The Python `venv` module is absent.
- [ ] FFmpeg or ffprobe is absent.
- [ ] The engine manifest is missing or altered.
- [ ] A locked wheel hash does not match.
- [ ] PyPI is unavailable or too slow.
- [ ] Disk space is insufficient.
- [ ] Arena home or workspace is read-only.
- [ ] Arena home, workspace, or config contains a symlink escape.
- [ ] Setup is interrupted after dependency installation but before promotion.
- [ ] Setup is invoked concurrently.
- [ ] A previous Arena runtime exists and the replacement fails verification.

Every failure must leave the system either unchanged or with the previous verified runtime still active.

## CI Gate Design

Pull requests should require:

- Source quality gates on the supported Node/Python matrix.
- Packed-tarball consumer startup on Ubuntu, Windows, and macOS.
- Docker build and runtime smoke tests for both architectures when container files or locks change.

Nightly or scheduled workflows should additionally run:

- Full setup on every Python boundary.
- Interruption, concurrency, and slow-network recovery cases.
- Native Intel macOS and Linux ARM64 when these require scarce runners.
- Full container scans and size-regression comparisons.

Release candidates should require all nightly gates plus the published-package canary.

## Implemented Automation Awaiting CI Evidence

The current worktree now includes:

- `cli/scripts/check-node-version.cjs` and a CLI runtime guard for immediate Node.js 22–24 enforcement;
- cross-platform clean, artifact packing, digest inventory, consumer installation, uninstall, setup-idempotency, and deterministic local-processing assertions;
- `.github/workflows/install-smoke.yml` for the exact tarball on Ubuntu, Windows, and macOS with Node.js 22 and 24;
- Windows in the normal Node/Python source-test matrix;
- `.github/workflows/setup-smoke.yml` for scheduled Python 3.10/3.12 managed-runtime boundary tests; and
- `.github/workflows/container-smoke.yml` for Buildx `linux/amd64` and `linux/arm64`, hardened startup, Compose startup on AMD64, per-platform scanning, and retained image evidence.

Implementation does not count as platform verification. The associated checklist items remain unverified until these workflows run successfully on their target runners and their evidence artifacts are reviewed.

## Evidence and Reporting

For each target, retain:

- Git commit and npm tarball SHA-256.
- OS name/version and CPU architecture.
- Node, npm, Python, pip, FFmpeg, ffprobe, and Arena versions.
- Setup duration and managed-runtime disk usage.
- Exit codes for every command.
- Sanitized setup and diagnostic logs.
- Docker image digest, platform, user, size, and scan result.
- A machine-readable pass/fail summary.

Do not include API keys, credentials, cookies, home-directory contents, or user media in uploaded evidence.

## Completion Checklist

Arena installation may be described as cross-platform verified only when:

- [x] The support contract is consistent and enforced.
- [ ] All required native matrix jobs are green from clean environments.
- [ ] Both Docker architectures build and pass hardened runtime checks.
- [ ] The exact npm tarball passes consumer installation tests.
- [ ] The registry-delivered canary matches and passes the same tests.
- [ ] Setup, idempotency, repair, interruption recovery, and concurrency are verified.
- [x] A local media fixture succeeds without Arena Cloud or external AI credentials.
- [ ] Failure cases are actionable and preserve the last healthy state.
- [ ] Installation evidence is retained for the release.
- [ ] Installation and troubleshooting documentation matches observed behavior.

Until every item above is complete, the accurate claim is: **Arena is hardened and verified on selected paths, with cross-platform installation validation still in progress.**
