# Arena Cross-Platform Installation Verification Plan

**Status:** Release-candidate verification in progress — release-blocking hosted and Docker matrices green; public registry canary pending
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
- The exact 185-file tarball from current checkpoint `6df3cd4`, SHA-256 `06c1b6806a8e93ee1f7971b96285fb7c4f42e9eaea9f4e6de9a3620d0e4f77b1`, passed a non-root Linux ARM64 consumer install with Node.js 24, an empty npm cache, Python/FFmpeg absent during postinstall, Unicode paths, CLI startup, and uninstall.
- The public npm `latest` tag resolves to `@whitegodkingsley/arena-cli@0.4.2`. On August 13, 2026, that exact registry version installed into an isolated prefix on macOS ARM64 with Node.js 24 and passed version and help startup checks. The version-pinned npx command also reported `0.4.2` in a clean supported Node.js 22 Linux container.
- The installer-code-equivalent artifact from `a9feb04`, SHA-256 `e371bef79a775ec64fec0e535bcfb44df89f77c7d705c3ca4e5da80441112123`, completed a 7.6-minute cold managed-runtime install on containerized Linux ARM64 with Node.js 22 and Python 3.11, idempotent rerun, live-lock rejection, stale-state cleanup, forced-timeout rollback preserving the healthy runtime, damaged-runtime detection and atomic repair, credential-free local processing, and uninstall.
- Current checkpoint `6df3cd4` built for `linux/amd64` under emulation and passed non-root, read-only, network-disabled, capability-dropped runtime processing and Compose startup. This supplements but does not replace native evidence.
- The final hardened AMD64 runtime image for `6df3cd4`, with local image ID `sha256:a95d37705d65986107c09ad318898df7b2977d0ba69501701f178470c03a7e49`, removed npm, npx, Corepack, and other build-only package-manager shims. It then passed an offline local-processing smoke test and a fixable-vulnerability scan with 0 critical, high, medium, or low findings across 657 detected packages.
- Arena `0.4.2` from commit `7f7fd269d130b918be9940175864ef6158b1f2a1` is published at OCI index digest `sha256:b1bfbc0ca0696d550ba5520a7fbff196721af6cd8a0643ec8d08e13583495b1b`. Docker Hub exposes Linux AMD64 manifest `sha256:5ebd0354b18811650766b09bd03656bcba1831905f73e38173b264a6bca3583a` and Linux ARM64 manifest `sha256:104c90a724a05eaffa221d687e491f37beb2830084ba665b2f6fc7f5fe35a14a`, each with SBOM and provenance attestations. Both exact registry manifests ran with the hardened runtime contract and reported version `0.4.2`; the release candidates for both platforms passed deterministic local-processing checks and fixable-vulnerability scans with 0 critical, high, medium, or low findings.
- Managed-runtime run [31828709997](https://github.com/iamwhitegod/arena/actions/runs/31828709997) passed from exact commit `2a1532560870f5f1e6d9a7b9525dd21a7b7882af` on Ubuntu x64, Windows x64, and macOS ARM64 for Node.js 22/Python 3.10 and Node.js 24/Python 3.12. All six jobs installed the same packed artifact, built an isolated runtime, passed health checks, processed local media without credentials, proved setup idempotency, and retained JSON evidence. The Linux recovery job also passed lock, stale-state, timeout rollback, and damaged-runtime repair assertions.
- Release-candidate PR [#10](https://github.com/iamwhitegod/arena/pull/10) passed the packed-artifact consumer matrix on Ubuntu, Windows, and macOS with Node.js 22 and 24, the complete source test matrix, and container build/runtime/scan jobs for Linux AMD64 and ARM64. GitHub Dependency Graph was enabled on August 15, 2026 to make dependency review an enforceable repository gate.

This evidence covers the declared release-blocking hosted targets and both Docker architectures. It does not yet prove registry delivery of `0.4.3-rc.1`, the exact documented source-link workflow, or best-effort native Linux ARM64, Intel macOS, and Windows ARM64 targets.

## Next Execution Steps

Execute these in order; workflow configuration alone is not verification:

1. Run the clean-source workflow for the documented `npm install`, `npm link`, setup, local-processing, and unlink path on the full release-blocking matrix.
2. Merge the release-candidate PR and rerun packed-artifact, source, managed-runtime, security, and container gates against the exact release commit.
3. Publish `0.4.3-rc.1` to npm under `next` and Docker Hub under exact-version and commit tags; pre-releases must not move stable tags.
4. Dispatch the published npm canary on Ubuntu x64, Windows x64, and macOS ARM64, verify registry signatures/provenance, and retain setup and processing evidence.
5. Review the published Docker manifest, platform digests, attestations, scans, and hardened runtime evidence for AMD64 and ARM64.
6. Extend recovery coverage with read-only-path, insufficient-disk, symlink-escape, missing-prerequisite, and post-dependency interruption cases.
7. Promote only the exact verified candidate to stable without rebuilding it. Provision native best-effort runners separately when reliable Linux ARM64, Intel macOS, or Windows ARM64 capacity is available.

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

| Host       | Architecture  | Boundary pair A       | Boundary pair B       | Status                                                                                              |
| ---------- | ------------- | --------------------- | --------------------- | --------------------------------------------------------------------------------------------------- |
| Ubuntu LTS | x86_64        | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Managed-runtime boundaries verified at `2a15325`; exact source and registry canaries pending        |
| Ubuntu LTS | ARM64         | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Containerized Node 24 consumer and Node 22/Python 3.11 recovery verified; native boundaries pending |
| Windows    | x86_64        | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Managed-runtime boundaries verified at `2a15325`; exact source and registry canaries pending        |
| macOS      | Apple Silicon | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Managed-runtime boundaries verified at `2a15325`; exact source and registry canaries pending        |
| macOS      | Intel         | Node 22 + Python 3.10 | Node 24 + Python 3.12 | Unverified                                                                                          |

Additional primary-Linux combinations:

- [ ] Node 22 + Python 3.12
- [ ] Node 24 + Python 3.10

If a required architecture is unavailable on hosted CI, use an ephemeral self-hosted runner or a clean-machine provider. Emulation may supplement but must not replace at least one native run for Windows and both macOS architectures.

## Required Docker Matrix

| Target        | Build    | Runtime smoke test | Compose smoke test | Status                                                                                            |
| ------------- | -------- | ------------------ | ------------------ | ------------------------------------------------------------------------------------------------- |
| `linux/amd64` | Required | Required           | Required           | Local emulated build/runtime/Compose and fixable-vulnerability scan verified; CI evidence pending |
| `linux/arm64` | Required | Required           | Required           | Local build/start/media/Compose verified; CI scan pending                                         |

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

The local AMD64 image passed Docker Scout's fixable-vulnerability gate with no findings. The checklist remains open until the configured Trivy scan passes for both exact platform images in CI.

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
- [ ] Verify paths containing spaces and Unicode on Windows, macOS, and Linux. macOS ARM64 and containerized Linux ARM64 are locally verified; Windows is pending.
- [ ] Confirm npm postinstall remains read-only and never makes installation fail because FFmpeg or Python is absent on every OS family. macOS ARM64 and containerized Linux ARM64 are locally verified; Windows is pending.
- [ ] Confirm a missing prerequisite produces one clear actionable message.
- [ ] Test non-administrator Windows installation and a standard non-root POSIX account. Non-root Linux ARM64 is locally verified; Windows is pending.
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

Local Linux ARM64 evidence now proves the Python 3.11 path for hash-locked setup, idempotency, live-lock rejection, stale-state recovery, configured timeout behavior, preservation of the last healthy runtime, damaged-runtime repair, and cleanup of all staging state. The Python 3.10/3.12 and native OS matrix remains release-blocking.

## Phase 4: Functional Local Processing Smoke Test

Use a tiny, repository-owned fixture that requires no network or paid provider:

- [x] Validate local media probing with ffprobe.
- [x] Extract audio with FFmpeg.
- [x] Detect scenes or perform another deterministic engine operation.
- [x] Write output beneath the isolated workspace.
- [x] Verify output is non-empty and media metadata is valid.
- [x] Confirm local processing succeeds without credentials; the hardened container smoke additionally runs with networking disabled.
- [ ] Record execution time and peak disk usage to detect packaging regressions.

AI-provider integration belongs in a separate opt-in workflow using test credentials. It must not block proof that local installation works.

## Phase 5: Docker Multi-Architecture Verification

- [x] Configure Buildx for `linux/amd64` and `linux/arm64`.
- [x] Build both platforms from the same commit and Dockerfile.
- [x] Publish both platform images as one attested OCI index under immutable and stable tags.
- [x] Run the full hardened-runtime assertions on each architecture.
- [ ] Run `docker compose config` and a Compose startup smoke test.
- [x] Process the local fixture through a mounted workspace and named Arena data volume.
- [x] Scan each platform release candidate rather than only the multi-architecture index.
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
- [x] Setup is invoked concurrently on the local Linux recovery path.
- [x] A previous Arena runtime remains healthy when a forced rebuild times out on the local Linux recovery path.

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
- `.github/workflows/setup-smoke.yml` for scheduled Python 3.10/3.12 managed-runtime boundary tests plus Linux lock, stale-state, timeout-rollback, and damaged-runtime repair assertions; and
- `.github/workflows/container-smoke.yml` for Buildx `linux/amd64` and `linux/arm64`, hardened startup, Compose startup on AMD64, per-platform scanning, and retained image evidence; and
- `.github/workflows/publish-container.yml` for protected, version-matched Docker Hub publication, a single AMD64/ARM64 manifest, immutable version and commit tags, stable-only moving tags, SBOM/provenance attestations, and post-publish registry verification.

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
- [x] An exact generated npm tarball passes consumer installation tests; native matrix and registry delivery remain separate gates.
- [ ] The registry-delivered canary matches and passes the same tests.
- [ ] Setup, idempotency, repair, interruption recovery, and concurrency are verified.
- [x] A local media fixture succeeds without Arena Cloud or external AI credentials.
- [ ] Failure cases are actionable and preserve the last healthy state.
- [ ] Installation evidence is retained for the release.
- [x] Installation and troubleshooting documentation matches the currently observed local behavior and clearly labels native evidence still pending.

Until every item above is complete, the accurate claim is: **Arena is hardened and verified on selected paths, with cross-platform installation validation still in progress.**
