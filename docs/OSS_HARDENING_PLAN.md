# Arena OSS Hardening Plan

**Status:** Phase 0 and Phase 1 implemented, except the explicitly deferred yt-dlp remote-component decision
**Reviewed:** August 13, 2026

## Executive Summary

Arena has a strong product core, but the repository is not yet ready for a security-conscious open source release. The primary blockers are supply-chain integrity, a failing Python quality gate, incomplete release validation, and missing OSS governance.

The intended product boundary is:

- **Arena OSS:** A complete, local-first video processing and editorial product.
- **Arena Cloud:** A paid operational layer for managed compute, collaboration, analytics, automation, and scale.

Arena OSS should remain useful without an Arena account or dependency on Arena Cloud.

## Implementation Update

The release-blocking editorial contract, full-language release gates, minimal package staging, credential isolation, workspace containment, hash-locked Python dependencies, immutable CI actions, non-root container, container scanning, and OSS governance files are implemented in the current hardening changeset. Runtime and development dependency audits both pass with no known vulnerabilities at the review date.

The yt-dlp remote-component item was intentionally excluded from this hardening pass at the product owner's request. It remains a separately owned decision and is not represented as work completed by this changeset.

## Current Assessment

### Release Blockers

#### 1. Unverified executable downloads

`cli/scripts/download-deps.cjs` downloads Python, FFmpeg, and `get-pip.py`, then extracts or executes them without checksum or signature verification.

The URL downloader also enables yt-dlp's GitHub-hosted remote JavaScript component at runtime. This expands the runtime trust boundary beyond the installed Arena release.

Required changes:

- Pin every downloaded artifact to an immutable version.
- Verify SHA-256 checksums or upstream signatures before extraction or execution.
- Reject redirects to unexpected hosts.
- Remove runtime remote-code loading where possible.
- If remote components remain necessary, require explicit user opt-in and document the risk.

#### 2. Failing Python quality gate

The Python test suite currently reports:

- 100 passing tests
- 7 failing tests
- 4 warnings

Several failures show that the production-quality thresholds in `engine/arena/editorial/thought_unit.py` no longer agree with the tests and the documented strict editorial gate.

This must be resolved as a product decision. The team should define the intended production threshold contract first, then update the implementation, tests, and documentation together.

#### 3. Incomplete publication checks

The npm publication workflow runs TypeScript tests and the TypeScript build, but it does not run the shipped Python engine tests. A release can therefore publish even when the engine suite is failing.

Every release must require:

- TypeScript tests
- Python tests
- TypeScript lint and formatting checks
- Type checking and build
- Package-content validation
- Production dependency audits
- Secret scanning
- SBOM and provenance generation

#### 4. Fragile package construction

The current `prepack` process copies most of the engine into the CLI package directory. This may include tests, experiments, cached artifacts, reports, local configuration, or other unintended files.

Cleanup depends on `postpack`. If packaging fails or is interrupted, copied files remain in the working tree.

Required changes:

- Assemble release artifacts inside a disposable staging directory.
- Use an explicit allowlist of engine modules and runtime files.
- Never package tests, caches, local configuration, result files, or development scripts.
- Add a CI test that inspects the final tarball and rejects unexpected content.
- Generate and inspect the package before publication.

## Security Findings

### Credentials and local configuration

Arena permits OpenAI API keys to be stored in `~/.arena/config.json`. The value is masked in CLI output, but the file is ordinary JSON and owner-only permissions are not explicitly enforced.

Recommended policy:

- Prefer environment variables or operating-system credential storage.
- Do not encourage API keys as command-line arguments because shell history may retain them.
- Create configuration directories with owner-only access.
- Write any legacy secret-bearing configuration with `0600` permissions.
- Warn users when migrating an existing plaintext key.
- Ensure diagnostics and logs always redact recognized credentials.

### URL processing

Arena accepts arbitrary HTTP and HTTPS URLs and passes them to yt-dlp. For the local CLI, this is primarily a user-controlled operation, but it will become a server-side request forgery risk if reused by Arena Cloud.

Before Cloud reuse:

- Keep Cloud URL ingestion separate from the local downloader.
- Block loopback, link-local, private, metadata-service, and reserved addresses.
- Revalidate every redirect destination.
- Enforce download size, duration, bandwidth, and execution time limits.
- Process media in an isolated, unprivileged environment.
- Treat downloaded media and metadata as untrusted input.

### Filesystem boundaries

Workspace helpers accept filenames and base paths without an explicit containment check. Internal callers currently control most values, but public APIs should not permit path traversal or deletion outside the Arena workspace.

Required changes:

- Resolve and validate paths against an approved workspace root.
- Reject `..`, absolute-path escapes, symlink escapes, and unsafe filenames.
- Add safety guards around workspace cleanup.
- Use atomic writes for configuration, checkpoints, and result files.
- Apply file-size limits before parsing JSON or media metadata.

### Containers

The current Docker image:

- Runs as root.
- Uses `curl | bash` installation flows.
- Includes compilers and build tooling in the runtime image.
- Does not pin its base image by digest.

Required changes:

- Use a multi-stage build.
- Pin base images and external downloads.
- Run Arena as a dedicated non-root user.
- Remove compilers, package managers, and temporary assets from the runtime stage.
- Use a read-only root filesystem where practical.
- Define explicit writable cache and output mounts.
- Add container vulnerability scanning in CI.

### Dependencies and automation

The production npm audit found no known vulnerabilities across the current 102 production dependencies at review time. This is a point-in-time result, not a continuing guarantee.

Remaining work:

- Lock Python dependencies with hashes.
- Audit Python dependencies in CI.
- Pin GitHub Actions to immutable commit SHAs.
- Enable automated dependency updates.
- Add CodeQL or equivalent static analysis.
- Add secret scanning and dependency review.
- Produce SPDX or CycloneDX SBOMs for releases.
- Sign or attest release artifacts.

## OSS Repository Standards

The repository should add the following root-level files:

- `LICENSE`
- `SECURITY.md`
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `SUPPORT.md`
- `CHANGELOG.md`
- `CODEOWNERS`
- Pull request template
- Bug report template
- Feature request template
- Security report instructions

The policies should define:

- Supported release versions
- Security response and disclosure process
- Contributor expectations
- Release cadence
- Semantic versioning policy
- Deprecation policy
- Maintainer and review responsibilities
- Developer Certificate of Origin or contributor license policy
- Trademark usage for Arena and Arena Cloud

Generated JavaScript and source-map copies of TypeScript tests should not be committed unless they are deliberate test fixtures. Development reports and historical sprint notes should also be separated from current user-facing documentation.

## Arena OSS and Arena Cloud Boundary

### Arena OSS

Arena OSS should include:

- Local transcription and analysis
- The four-layer editorial engine
- Local clip generation
- Captioning and platform formatting
- Scene and audio-energy analysis
- Stable local project and artifact formats
- Bring-your-own provider credentials
- Provider and extension interfaces
- Documented CLI and engine APIs

Arena OSS should guarantee:

- No Arena account is required.
- No Arena Cloud connection is required.
- No undisclosed telemetry is collected.
- User media remains local unless the user explicitly selects an external provider.
- Cloud-related commands are optional and visibly separated.

Some AI-assisted features may require a user-selected external model provider, so the product should avoid claiming that every feature works fully offline unless local model support is actually present.

### Arena Cloud

Arena Cloud should monetize operational leverage rather than withholding the core local workflow:

- Managed processing and job queues
- Hosted storage and synchronization
- Teams, roles, approvals, and audit logs
- Cross-platform performance analytics
- Publishing integrations
- Scheduled and event-driven automation
- Managed model usage and consolidated billing
- Organization-level policies
- Enterprise identity and support

### Stable interoperability contract

Create versioned, provider-neutral artifact schemas such as:

- `arena.project/v1`
- `arena.transcript/v1`
- `arena.analysis/v1`
- `arena.clip/v1`

Arena Cloud should consume these public formats instead of importing private engine internals. Compatibility tests should verify that old artifacts remain readable and that migrations are explicit.

Recommended architectural packages:

```text
arena/
├── cli/                 # OSS command-line interface
├── engine/              # OSS local processing engine
├── schemas/             # OSS versioned artifact contracts
├── providers/           # OSS provider adapters
├── cloud-client/        # Optional OSS client for Arena Cloud APIs
└── cloud/               # Private service, or a separate repository
```

## Implementation Roadmap

### Phase 0: Release blockers

- [x] Decide and document the editorial production threshold contract.
- [x] Restore the Python test suite to green.
- [x] Require Python tests in the publication workflow.
- [x] Eliminate the unverified executable-download installer path.
- [ ] Remove or gate runtime remote-code loading. Deferred by explicit product decision; excluded from this changeset.
- [x] Replace mutable package construction with a staging-directory build.
- [x] Add final-package allowlist validation.
- [x] Secure local configuration and credential handling.

Exit criteria:

- All local and CI tests pass.
- A release cannot publish without testing the shipped engine.
- Every executable artifact has a verifiable origin and checksum.
- The npm tarball contains only intended runtime files.

### Phase 1: OSS foundation

- [x] Add root governance and community health files.
- [x] Document supported platforms and dependency versions.
- [x] Lock and audit Python dependencies.
- [x] Add CodeQL, secret scanning, dependency review, SBOM generation, and container scanning.
- [x] Pin CI actions and container inputs.
- [x] Harden the Docker image.
- [x] Remove committed generated test artifacts.
- [x] Document network calls, privacy, caches, and data retention.
- [x] Publish a basic threat model.

Exit criteria:

- The repository meets standard GitHub community-health expectations.
- Security reporting and supported versions are public.
- Releases are reproducible enough to inspect and attest.

### Phase 2: Stable OSS architecture

- [ ] Publish the versioned artifact schemas.
- [ ] Separate core logic from model-provider adapters.
- [ ] Define stable engine and CLI extension points.
- [ ] Add schema migration and compatibility tests.
- [ ] Establish semantic versioning and deprecation policies.
- [ ] Maintain a changelog and architecture decision records.
- [ ] Document the permanent OSS versus Cloud feature boundary.

Exit criteria:

- Arena Cloud can integrate through public contracts.
- OSS contributors can extend providers without changing core internals.
- Artifact compatibility is tested across supported versions.

### Phase 3: Arena Cloud preparation

- [ ] Isolate Cloud services from the OSS runtime.
- [ ] Authenticate only Cloud-specific commands.
- [ ] Design tenant isolation and authorization.
- [ ] Encrypt credentials and customer data.
- [ ] Add job quotas, rate limits, audit logs, and abuse prevention.
- [ ] Sandbox all media processing.
- [ ] Define retention, deletion, backup, and incident-response policies.
- [ ] Perform a dedicated Cloud threat model before accepting customer data.

Exit criteria:

- Local Arena continues to operate independently.
- Cloud access is explicit and least-privileged.
- Tenant, media-processing, billing, and credential risks have enforceable controls.

## Recommended Order of Work

The immediate sequence should be:

1. Resolve the editorial test-contract mismatch.
2. Secure downloads and package construction.
3. Make publication depend on the complete test suite.
4. Add repository governance and security policy.
5. Harden credentials, filesystem boundaries, CI, and containers.
6. Establish public schemas before implementing Arena Cloud features.

Arena Cloud development should begin only after the OSS artifact contract and security boundary are stable. This prevents Cloud concerns from leaking into the local engine and keeps the open source product trustworthy, forkable, and independently useful.
