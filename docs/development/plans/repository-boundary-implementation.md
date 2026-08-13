# Repository boundary implementation plan

**Status:** Approved for implementation

**Last reviewed:** August 13, 2026

This plan turns the five migration gates in [Repository boundary](../../cloud/repository-boundary.md#migration-gates) into reviewable delivery slices. Gates 1–4 primarily change the public Arena repository. Gate 5 describes acceptance requirements for a future private `arena-cloud` repository; it does not imply that repository or service exists today.

> **Production hold:** The private service must not process production customer media until Gates 1–3 are complete. Prototypes may use synthetic or explicitly approved non-production fixtures only.

## Outcome and non-goals

The target is a one-way dependency: Arena Cloud consumes pinned public Arena releases and versioned contracts; Arena OSS never imports private Cloud code and every existing local command remains usable without Arena Cloud.

This plan does not:

- move the local processing engine into the private repository;
- make every Python module or current JSON file public API;
- enable uploads, sync, accounts, billing, or telemetry as a side effect of schema work;
- choose unresolved worker, schema publication, identity, storage, or upload designs without an architecture decision;
- preserve undocumented artifact quirks forever.

## Gate sequence

| Gate                     | Depends on                                           | Exit outcome                                                      |
| ------------------------ | ---------------------------------------------------- | ----------------------------------------------------------------- |
| 1. Current artifacts     | Boundary decision                                    | Complete, reviewed inventory of observed data and risks           |
| 2. Public contracts      | Gate 1 + schema/versioning decisions                 | Versioned schemas, fixtures, validators/types, compatibility CI   |
| 3. Worker boundary       | Gate 2 + worker/provider/input decisions             | Pinned executable boundary with deterministic, retry-safe results |
| 4. Optional Cloud client | Gates 2–3 + API/auth/consent decisions               | Explicit Cloud UX that cannot weaken local/offline behavior       |
| 5. Private Cloud service | Gates 1–3; Gate 4 only where CLI integration is used | Tenant-safe service consuming public releases/contracts           |

Later-gate design work may run in parallel, but implementation cannot bypass a dependency or the production hold.

## Gate 1: Document current artifacts

**Goal:** Know every relevant persisted and machine-readable shape before declaring a contract.

### PR 1.1 — Inventory and classification

- Land [Current artifact inventory](../../reference/artifact-contracts.md).
- Record producer, consumer, location/channel, representative format, current stability, data class, observed risk, and recommended disposition.
- Cover configuration, credentials, runtime state, caches, transcript, analysis, editorial debug/checkpoint data, scenes, clip metadata, media, subtitles, thumbnails, command results, diagnostics, and legacy outputs.
- Separate current stability from future “portable candidate” status.

**Verification**

- Review JSON/file writers found with searches for `json.dump`, `writeJson`, `writeFile`, `open(..., "w")`, SRT/image/media output functions, and protocol emitters.
- Cross-check every active TypeScript bridge method with its Python command handler.
- Verify all Markdown links.

### PR 1.2 — Resolve inventory defects

- Fix or explicitly record unreachable writers, incompatible variants, undocumented path behavior, and camelCase/snake_case drift.
- Deprecate the legacy `engine/arena/main.py` pipeline and its installed `arena-engine=arena.main:main` console entry point for new integrations. Add an actionable runtime/deprecation notice, announce one compatibility window, and identify Gate 3's worker entry point as its replacement.
- Add sanitized representative fixtures only if they help compare current writers; fixtures remain explicitly non-contractual at this gate.

**Gate 1 exit criteria**

- Maintainers have reviewed the inventory against current source.
- No known durable or machine-readable artifact family is missing.
- Every portable candidate has field-level data classification.
- Gaps found during inventory have owners or linked follow-up issues.

**Rollback/compatibility:** Documentation-only changes are reversible. No runtime reader or writer changes at this gate.

## Gate 2: Publish the first contracts

**Goal:** Publish the smallest useful, versioned artifact surface with identical validation behavior in TypeScript and Python.

### PR 2.1 — Contract architecture decisions

Decide and record:

- schema publication channel;
- minimum compatibility/support window;
- canonical field naming, time units/precision, IDs, hashes, and timestamp format;
- JSON Schema draft and validator implementations;
- generation strategy and source-of-truth rule for TypeScript/Python types;
- whether content-derived fields are core, optional extensions, or separate artifacts.

No schema PR merges until these choices are documented.

### PR 2.2 — Schema foundation

Create the public layout and common definitions:

```text
schemas/
  common/v1/
  project/v1/
  transcript/v1/
  fixtures/
```

- Define the artifact envelope with `schema`, integer `schema_version`, producer name/version, UTC `created_at`, and `data`.
- Use `<arena-version>` in documentation examples; inject the actual version at build/runtime.
- Add valid, invalid, boundary, and unknown-optional-field fixtures.
- Ensure project/source references cannot contain secrets and do not require absolute paths.

### PR 2.3 — Analysis and clip contracts

- Add `arena.analysis/v1` and `arena.clip/v1`.
- Define score scales, time semantics, artifact references, and editorial extension points.
- Exclude `_`-prefixed implementation fields and host filesystem paths.
- Add deterministic migration adapters from every supported current writer variant.

### PR 2.4 — Durable job-event contract

- Add `arena.job-event/v1` for durable/persisted/networked lifecycle events.
- Define stable state names, event ID, sequence, UTC timestamp, operation, progress semantics, safe message rules, and stable error-code reference.
- Keep the existing JSONL terminal protocol internal; add an adapter instead of silently rebranding it as the contract.

Job requests and job results are distinct families delivered in Gate 3.

### PR 2.5 — Generated types, validators, and CI

- Generate or derive Python and TypeScript types/validators from the same schema source.
- Add contract tests outside internal engine packages.
- Validate all fixtures in both languages.
- Add upgrade fixtures and tests for unsupported major versions, unknown optional fields, and withdrawn producer/schema versions.
- Fail CI on schema changes without compatibility fixtures or an explicit new major version.

**Verification**

Current repository checks remain required:

```bash
cd cli && npm run build && npm test
cd engine && pytest tests/
```

This gate must also introduce documented contract-specific commands, for example `npm run test:contracts` and the matching Python contract test target. The exact command names belong to PR 2.5 and must run the same fixtures.

**Gate 2 exit criteria**

- `project`, `transcript`, `analysis`, `clip`, and `job-event` v1 schemas are published with fixtures.
- TypeScript and Python validators agree on every fixture.
- No portable schema includes secrets, absolute host paths, or internal `_`-prefixed fields.
- Compatibility window, publication channel, upgrade policy, and critical schema withdrawal procedure are documented.

**Rollback/compatibility:** Published schema files and fixtures are immutable. A broken release is withdrawn through the security/compatibility process and replaced by a compatible patch or new schema major; it is not rewritten in place.

## Gate 3: Publish a worker boundary

**Goal:** Give any worker implementation one pinned, supported way to execute Arena without importing internal modules.

### PR 3.1 — Worker decisions and threat model

Decide and record:

- container, executable command, public Python facade, or supported combination;
- provider/model normalization without secret leakage;
- direct upload, user-owned storage pull, or both;
- cancellation, timeout, concurrency, resource-limit, and sandbox semantics;
- idempotency scope and output ownership.

If a Python facade is chosen, define its import allowlist and deprecation policy before Cloud relies on it.

### PR 3.2 — Request, result, and error contracts

Add separate schema families:

```text
schemas/job-request/v1/
schemas/job-result/v1/
schemas/job-event/v1/     # already introduced in Gate 2
```

- Request: engine version/image digest, input artifact versions, operation, normalized options, provider/model identifiers, idempotency key, and runtime-supplied output destinations.
- Result: outcome, stable error code, artifact versions/hashes, usage, engine/provider versions, and retry safety.
- Error catalog: stable code, category, retryability, safe public message, and diagnostic correlation ID. Provider exceptions and local paths stay out of the public payload.

### PR 3.3 — Minimal worker entry point

- Implement one documented command/image entry point that reads a request from an explicit channel and writes versioned events/results to an explicit channel.
- Pin the Arena release and dependency set; record commit, package/image digest, and SBOM/provenance where available.
- Reject unsupported schema/engine versions before media processing begins.
- Do not expose `arena.editorial.*`, `arena.clipping.*`, or other internals as accidental API.
- After the replacement passes black-box and compatibility tests, remove the deprecated `arena.main:main` entry point in the next breaking release and retain migration guidance for the documented support window.

### PR 3.4 — Determinism and integrity harness

- Freeze provider responses in contract fixtures.
- Canonicalize JSON before hashing and exclude declared volatile envelope fields from content-integrity comparisons.
- Verify identical normalized request + inputs + provider fixtures + engine version produce identical portable artifacts and hashes.
- Record every deliberate nondeterministic field.

### PR 3.5 — Retry, cancellation, and failure recovery

- Prove an idempotency key cannot create duplicate committed outputs.
- Test retry before execution, during processing, after artifact write, and after result publication.
- Test cancellation/timeout cleanup and checkpoint isolation.
- Verify partial artifacts are either uncommitted or explicitly reported and recoverable.

### PR 3.6 — Optional public facade

Only if the selected worker integration requires a library API:

- publish the named import path and allowlisted requests/results/exceptions;
- test it from outside the engine package;
- document lifecycle, concurrency, cancellation, compatibility, and deprecation;
- prove Cloud integration uses only the allowlist.

**Verification**

- Cross-language request/result/event fixture validation.
- Worker black-box success, stable failure, cancellation, timeout, unsupported-version, and resource-limit tests.
- Determinism and idempotent retry suites.
- Container/package smoke test using a synthetic media fixture and no developer checkout.

**Gate 3 exit criteria**

- The worker executes a pinned public Arena release through a documented boundary.
- Job request, result, and event are distinct versioned contracts.
- Stable errors, integrity hashes, usage fields, retry semantics, and provenance are tested.
- No worker consumer imports undocumented engine internals.
- The production hold may proceed to Gate 5 review only after Gates 1–3 are all complete.

**Rollback/compatibility:** Workers are deployed by immutable version/digest. Rollback selects a previously supported digest; it never mutates an existing image. Requests declare compatible versions, and partially rolled deployments must preserve the documented schema window.

## Gate 4: Add the optional Cloud client

**Goal:** Add explicit Cloud operations to the public CLI without changing local commands, privacy posture, or offline availability.

### PR 4.1 — API/auth decision and inert namespace

- Record API versioning and authentication flow.
- Add the `arena cloud` namespace, help, and local status behavior without performing implicit network requests.
- Keep Cloud dependencies lazy/isolated so importing or running local commands does not initialize Cloud code.

### PR 4.2 — Credential lifecycle

- Choose an OS credential store or owner-only fallback through an architecture/security decision.
- Implement login/token refresh only after that decision.
- Implement logout, revocation feedback, expiry handling, and redaction tests.
- Never store Cloud tokens in project artifacts or public diagnostics.

### PR 4.3 — Inspectable transfer manifest

- Define a local transfer manifest using public artifact IDs and schemas.
- Before any upload, show destination, data classes, approximate size, retention policy, and deletion support.
- Add dry-run/inspect behavior that makes no network mutation.
- Prevent an operational-metadata selection from expanding to transcript, thumbnail, subtitle, audio, or video.

### PR 4.4 — Explicit sync/upload operation

- Implement one narrow operation against a versioned API.
- Require explicit user action for content-derived/media-derived data and separate confirmation for raw media.
- Validate server capability/schema support before transfer.
- Make interrupted transfers resumable or safely restartable without duplicates.

### PR 4.5 — Opaque project identity

- Decide the local-to-Cloud mapping storage and lifecycle.
- Generate identifiers that neither contain nor deterministically derive from absolute paths.
- Transmit mappings only during explicit Cloud operations.
- Test project moves, clones, unlink/relink, logout, and deletion behavior.

### PR 4.6 — Separate telemetry consent surface

- Publish an inspectable telemetry event inventory first.
- Add explicit opt-in, status/inspection, revocation, and a test-enforced no-telemetry mode.
- Authentication and Cloud operation use must not imply telemetry consent.
- Command names and storage location remain UX/security decisions; acceptance behavior is fixed by the boundary.

### PR 4.7 — Offline and privacy regression suite

- Block network access and run every pre-existing local command/help path.
- Assert no DNS/socket attempt for local operations.
- Assert logs, diagnostics, artifacts, and telemetry never contain credentials, cookies, authorization headers, or raw provider errors.
- Test Cloud outage behavior without degrading local work.

**Gate 4 exit criteria**

- Local commands and help work with the network blocked and without an Arena account.
- Every transfer is inspectable, classified, explicit, and constrained to its selected data.
- Credential revocation/logout, opaque identity, and interrupted-transfer behavior are tested.
- Telemetry is off by default and separately consented, inspectable, and revocable.

**Rollback/compatibility:** Cloud commands are optional client features. A server/client incompatibility disables the affected Cloud operation with an actionable error; it cannot block local processing. Credential and mapping migrations must be reversible or retain a supported reader for the compatibility window.

## Gate 5: Create the private Cloud service

**Goal:** Build the hosted control/data plane in a separate private repository that consumes, but does not fork, the public engine and contracts.

Gate 5 work may design against synthetic fixtures earlier, but production media processing remains blocked until the Gate 1–3 completion evidence is reviewed.

### PR 5.1 — Private repository foundation

- Create separate access control, branch protection, CI, release credentials, secret management, ownership, and incident contacts.
- Add generated contract consumption from a pinned public release/channel.
- Add a dependency rule that rejects copied OSS engine modules and imports of undocumented internals.

### PR 5.2 — Tenant-aware control plane

- Implement authenticated job/project APIs with authorization on every resource access.
- Define tenant, role, quota, audit, and destructive-action controls.
- Validate all requests at the public schema boundary before enqueueing work.

### PR 5.3 — Storage, retention, and deletion

- Use tenant-scoped object references and short-lived signed transfers.
- Implement encryption, lifecycle/retention policies, export, deletion, backup, and restore procedures.
- Prove deletion covers primary artifacts, derived artifacts, and documented backup timelines.

### PR 5.4 — Isolated worker execution

- Execute only approved Arena release/image digests through the Gate 3 boundary.
- Isolate jobs from the API/control plane and other tenants; enforce CPU, memory, time, network, and storage limits.
- Keep customer/provider secrets in the responsible secret system and inject them without artifact serialization.
- Record engine/schema/provider provenance for every result.

### PR 5.5 — Metering, entitlements, and billing evidence

- Derive usage from signed/validated worker results and immutable job records.
- Test retry/idempotency so failed or duplicated delivery cannot double bill.
- Add quota enforcement, adjustments, dispute evidence, and auditability.

### PR 5.6 — Compatibility and production-readiness gates

- Test the oldest supported public input against the newest supported worker and current output against the oldest supported consumer.
- Add tenancy, authorization, upload validation, malware/untrusted-media, abuse, load, recovery, and incident exercises.
- Require a release checklist showing Gates 1–3 evidence, pinned digest, schemas, rollback target, retention/deletion behavior, and on-call ownership.

**Gate 5 exit criteria**

- The private repository consumes released schemas/types and a pinned public Arena engine; it contains no divergent copy of the core pipeline.
- Tenant isolation, authorization, retention, deletion, metering, backup/restore, and incident controls pass review and tests.
- Compatibility tests run before accepting any new Arena OSS version.
- A production-readiness review explicitly lifts the production hold.

**Verification**

- Private CI contract/compatibility suite against published OSS fixtures.
- End-to-end synthetic job tests with pinned image digest and provenance assertion.
- Cross-tenant negative tests, destructive-action audit tests, retention/deletion tests, retry/billing tests, load/resource-limit tests, and restore/incident exercises.

**Rollback/compatibility:** Roll back workers by immutable digest and API components by versioned deployment. Database/storage changes require forward/backward-compatible migrations and tested restore paths. An emergency private engine patch is time-limited, tracked, upstreamed, and returned to a pinned public release under the boundary policy.

## Cross-gate definition of done

Every implementation PR must include:

- its contract/privacy impact and data classifications;
- tests at the narrowest boundary plus affected TypeScript/Python suites;
- migration, compatibility, and rollback notes;
- documentation for any new public surface;
- no secrets, user media, absolute developer paths, or customer data in fixtures/logs;
- evidence that the one-way dependency and local-independence invariants still hold.

A gate is complete only when its exit criteria and dependent architecture decisions are reviewed—not merely when code exists.

## Open architecture decisions

These decisions from [Repository boundary](../../cloud/repository-boundary.md#open-decisions) require explicit records before their referenced slices merge:

1. Supported worker boundary: container, executable command, Python facade, or combination — before PR 3.3.
2. Schema publication channel: repository, npm/Python contract package, OCI artifact, or multiple channels — before PR 2.2.
3. Content-derived metadata sync granularity: project, artifact, or reusable policy — before PR 4.3.
4. Minimum schema compatibility window — before PR 2.2.
5. Provider/model version normalization without secret leakage — before PR 3.2.
6. Remote processing input model: direct upload, user-owned storage pull, or both — before PR 3.3.

Additional implementation decisions exposed by the inventory must be recorded without silently expanding the architectural commitment: canonical field naming/score scales, Cloud credential storage, opaque identity mapping storage, and telemetry UX. The legacy entry-point disposition is no longer open: PR 1.2 deprecates it and PR 3.3 owns its tested replacement and breaking-release removal.

## Immediate next work

1. Review and merge Gate 1 inventory corrections.
2. Open PR 1.2 issues for the unreachable editorial export, analysis alignment omission, and clip metadata/result drift.
3. Draft the Gate 2 contract ADR covering publication, support window, JSON Schema draft, naming, time/ID/hash rules, and generation strategy.
4. Do not create Cloud production processing code or upload real media while those foundations are open.

## Related documents

- [Repository boundary](../../cloud/repository-boundary.md)
- [Current artifact inventory](../../reference/artifact-contracts.md)
- [OSS hardening plan](./oss-hardening.md)
- [Data and privacy](../../security/data-and-privacy.md)
- [Threat model](../../security/threat-model.md)
