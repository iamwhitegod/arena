# Cross-Platform Installation Readiness Work Plan

**Status:** In progress — release claim blocked
**Created:** August 14, 2026
**Scope:** npm, source, and Docker installation for the supported Arena OSS platforms
**Canonical verification checklist:** [Installation verification plan](./installation-verification.md)

## Outcome

Make Arena installation release-grade on every supported operating-system family, runtime boundary, and published distribution path.

Arena must not be described as "flawless on every OS" until every release gate in this plan passes from clean environments using the exact artifacts intended for publication.

## Current Baseline

The latest inspected `main` commit is `6520a80ca0c84ce93d5e3f5a255f3b0fbd2ae15c`.

| Path | Passing evidence | Release blocker |
| --- | --- | --- |
| npm | Exact artifact build; Ubuntu and macOS consumer installation on Node.js 22 and 24 | Windows Node.js 22 and 24 fail `Install and start as an isolated consumer` |
| Source | Ubuntu and macOS Node/Python jobs pass | Windows Node.js 22/Python 3.10 and Node.js 24/Python 3.12 fail the TypeScript formatting gate on `main` |
| Docker | AMD64 and ARM64 builds reach hardened-runtime or scan stages; the published `0.4.2` image is multi-architecture | CI platform-image scan and Security container scan are not green |

Baseline workflow evidence:

- [Install smoke](https://github.com/iamwhitegod/arena/actions/runs/31814462599)
- [Source test matrix](https://github.com/iamwhitegod/arena/actions/runs/31814462547)
- [Container smoke](https://github.com/iamwhitegod/arena/actions/runs/31814462618)
- [Security](https://github.com/iamwhitegod/arena/actions/runs/31814462496)

The branch `agent/repository-split-foundation` proved that LF normalization can make both Windows source-test jobs pass. Its Windows npm consumer jobs still failed, so its conditional ASCII npm-prefix change is not sufficient evidence of a complete fix. Those commits are not on `main`.

## Release Definition

All three installation paths must satisfy the following contract:

1. Start from a clean supported host or runner with no repository-local dependencies.
2. Use the exact generated or published artifact being evaluated.
3. Require no undocumented manual repair, administrator access, or global Python mutation.
4. Pass startup, health, managed-runtime, idempotency, local-processing, and uninstall checks applicable to the path.
5. Produce sanitized retained evidence with artifact identity, platform, runtime versions, exit codes, and failure context.
6. Pass the required security and vulnerability gates without unreviewed suppressions.
7. Pass twice: once for the candidate commit and once for the exact release artifact.

## Execution Order

### Phase 0 — Establish a Clean Integration Baseline

Work from a dedicated installation-readiness branch based on the latest `origin/main`. Do not mix provider abstraction, downloader authentication, repository-split, or other feature work into this release-hardening patch series.

- [ ] Create or select a clean branch from the latest `origin/main`.
- [ ] Reimplement or cherry-pick the `.gitattributes` LF normalization as an isolated change.
- [ ] Reimplement or cherry-pick the deterministic retry timing test as an isolated test-hardening change.
- [ ] Review the conditional ASCII npm-prefix change independently; retain it only if evidence shows it is part of the final Windows solution.
- [ ] Confirm no generated evidence, credentials, caches, or unrelated worktree changes enter the commits.
- [ ] Record the candidate commit SHA used by every subsequent workflow.

**Exit criterion:** a reviewable installation-only patch series based on current `main`.

### Phase 1 — Repair Source Installation and Windows Quality Gates

Normalize repository text files at the Git boundary so Windows developers and runners receive LF content where formatters and shell tooling require it.

- [ ] Add root `.gitattributes` with the reviewed LF policy.
- [ ] Check tracked text for accidental CRLF or mixed-line-ending content.
- [ ] Renormalize only files that actually require it; do not create an unrelated repository-wide formatting diff.
- [ ] Run formatting, lint, build, CLI tests, and Python tests locally on supported runtimes.
- [ ] Run the complete GitHub source matrix:
  - [ ] Ubuntu: Node.js 22/24 and Python 3.10/3.12 combinations.
  - [ ] Windows: Node.js 22 + Python 3.10.
  - [ ] Windows: Node.js 24 + Python 3.12.
  - [ ] macOS: Node.js 22 + Python 3.10.
  - [ ] macOS: Node.js 24 + Python 3.12.
- [ ] Confirm the retry test remains deterministic under repeated macOS runs.

**Exit criterion:** every job in `.github/workflows/test.yml` is green on the same commit.

### Phase 2 — Diagnose and Fix Windows npm Consumer Installation

Do not guess at the remaining failure. Retrieve the failed job logs and retained consumer evidence for both supported Node.js versions before changing installer behavior.

- [ ] Restore authenticated GitHub Actions log and artifact access.
- [ ] Download the Node.js 22 and Node.js 24 Windows consumer evidence artifacts.
- [ ] Identify the first failing command, exact exit code, npm version, resolved prefix, executable path, `PATHEXT`, and sanitized stderr.
- [ ] Reproduce the failure on a clean non-administrator Windows environment.
- [ ] Determine whether the failure is in:
  - npm global-prefix parsing;
  - `arena.cmd` creation or discovery;
  - tarball path handling;
  - Unicode workspace, cache, home, or temporary paths;
  - postinstall behavior;
  - process spawning or quoting; or
  - managed Python/FFmpeg setup.
- [ ] Add a regression assertion for the confirmed root cause before or with the fix.
- [ ] Preserve Unicode coverage for Arena-controlled paths even if npm itself requires an ASCII prefix.
- [ ] Ensure failure evidence is written before the smoke harness exits so future CI failures remain diagnosable.
- [ ] Verify both Windows Node.js versions from an empty npm cache.
- [ ] Verify the installed `arena.cmd` from outside the repository and outside the package directory.
- [ ] Verify uninstall leaves only explicitly retained Arena user data.

**Exit criterion:** Windows Node.js 22 and 24 consumer jobs pass the same packed tarball that passes Ubuntu and macOS.

### Phase 3 — Prove Managed Runtime Setup on Native Hosts

Consumer startup alone is not a complete Arena installation. Verify the explicit `arena setup` lifecycle on supported Python boundaries.

- [ ] Run `arena setup --yes` and `arena setup --check` on:
  - [ ] Ubuntu Node.js 22 + Python 3.10.
  - [ ] Ubuntu Node.js 24 + Python 3.12.
  - [ ] Windows Node.js 22 + Python 3.10.
  - [ ] Windows Node.js 24 + Python 3.12.
  - [ ] macOS Node.js 22 + Python 3.10.
  - [ ] macOS Node.js 24 + Python 3.12.
- [ ] Confirm the managed environment stays inside isolated `ARENA_HOME`.
- [ ] Confirm hash-locked Python dependency installation.
- [ ] Verify Windows virtual-environment launchers and executable resolution.
- [ ] Prove setup idempotency, forced repair, timeout rollback, stale-state cleanup, and concurrent-install locking.
- [ ] Process the deterministic local fixture without Arena Cloud or provider credentials.
- [ ] Retain sanitized machine-readable evidence from every target.

**Exit criterion:** the managed runtime is healthy, repairable, isolated, and functional on every required native boundary pair.

### Phase 4 — Clear Docker Runtime and Security Gates

Treat scan failures as release blockers until the exact findings are understood.

- [ ] Retrieve Trivy output for the Security scan and each platform-image scan.
- [ ] Classify each failure as an actual package vulnerability, scanner database/configuration problem, or workflow artifact-selection problem.
- [ ] Record affected package, installed version, fixed version, severity, and originating image layer for real findings.
- [ ] Update the pinned base image or dependency locks when a supported fix exists.
- [ ] Do not suppress a finding without a CVE-specific justification, owner, and expiration date.
- [ ] Rebuild `linux/amd64` and `linux/arm64` from the same commit.
- [ ] On both architectures, verify:
  - [ ] expected architecture and non-root user;
  - [ ] read-only root filesystem;
  - [ ] dropped capabilities and `no-new-privileges`;
  - [ ] offline `arena --version` and local fixture processing;
  - [ ] documented writable mounts only; and
  - [ ] zero release-blocking scan findings.
- [ ] Run Compose configuration and startup smoke tests for every architecture claimed as supported.
- [ ] Retain image digests, sizes, runtime evidence, SBOMs, provenance, and scan reports.

**Exit criterion:** Container smoke and the Security container scan are green for both published architectures.

### Phase 5 — Verify Published Release Candidates

Prove registry delivery without rebuilding between verification and promotion.

- [ ] Produce one npm tarball and record its digest and inventory.
- [ ] Publish it under a non-default npm tag such as `next` with maintainer approval.
- [ ] Install the exact canary version from the public npm registry on clean Ubuntu, Windows, and macOS hosts.
- [ ] Compare registry identity and provenance with the candidate artifact.
- [ ] Run startup, setup, health check, fixture processing, repair, and uninstall.
- [ ] Build and publish a Docker release candidate for AMD64 and ARM64 under an immutable tag.
- [ ] Pull the registry manifests by digest and repeat hardened runtime and scan verification.
- [ ] Promote the already-tested npm version and Docker digest; do not rebuild them.

**Exit criterion:** the artifacts users download are byte-identical or digest-identical to the artifacts that passed the release matrix.

### Phase 6 — Documentation and Release Claim

- [ ] Update the installation guide, quick start, troubleshooting guide, and release process with verified behavior only.
- [ ] Include Windows PowerShell, macOS, and Linux commands tested by the matrix.
- [ ] Document exact supported Node.js, Python, Docker, host OS, and CPU boundaries.
- [ ] Document recovery for every intentionally tested failure mode.
- [ ] Link retained release evidence from the release checklist.
- [ ] Remove the warning that cross-platform validation is incomplete only after every gate above is green.

**Exit criterion:** documentation matches the exact released artifacts and no longer relies on unverified platform claims.

## Required Merge Gates

The final installation-readiness pull request must require:

- [ ] Source `Test` workflow: all matrix jobs green.
- [ ] `Install smoke`: artifact build plus Ubuntu, Windows, and macOS on Node.js 22 and 24 green.
- [ ] `Container smoke`: AMD64 and ARM64 build, runtime, Compose where supported, and scan gates green.
- [ ] `Security`: CodeQL, secret scan, dependency review when applicable, and container scan green.
- [ ] Managed-runtime setup matrix green on the documented Node/Python boundaries.
- [ ] No skipped release-blocking job caused by path filters or conditional logic.
- [ ] Required evidence artifacts uploaded and reviewed.

Do not merge with "rerun until green" as the explanation for a flaky result. A flaky release gate must be made deterministic or explicitly removed from the release contract with documented rationale.

## Completion Checklist

Arena installation is cross-platform verified only when all of the following are true:

- [ ] npm installation passes on clean Ubuntu, Windows, and macOS hosts using the same artifact.
- [ ] Source installation and tests pass on every supported Node/Python boundary.
- [ ] Managed runtime setup, health checking, repair, and local processing pass on every native OS family.
- [ ] Docker AMD64 and ARM64 images pass hardened runtime and vulnerability gates.
- [ ] Public npm and Docker candidates pass the same tests as their pre-publication artifacts.
- [ ] Every required GitHub workflow is green on the release commit.
- [ ] Evidence and documentation are complete and sanitized.

Until then, the approved statement remains: **Arena installation is verified on selected Linux and macOS paths; complete Windows and container-security validation is still in progress.**
