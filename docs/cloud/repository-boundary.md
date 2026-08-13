# Arena OSS and Cloud repository boundary

**Status:** Proposed architecture decision

**Last reviewed:** August 13, 2026

## Decision

Arena uses two repositories with a one-way dependency:

1. The public `arena` repository owns the complete local-first product, processing engine, CLI, public artifact contracts, and public client interfaces.
2. The private `arena-cloud` repository owns the hosted service, customer data plane, control plane, billing, tenant operations, and infrastructure.

`arena-cloud` may depend on published Arena OSS releases and public contracts. Arena OSS must never depend on the private repository or require Arena Cloud to perform local work.

This document specifies ownership and dependency rules. It is not a promise that every proposed directory or Cloud feature already exists.

## Why separate repositories

The split protects four properties:

- **Local independence:** Arena remains useful without an account, network connection to Arena Cloud, or Cloud subscription.
- **Open implementation:** The complete local editorial and media-processing pipeline remains inspectable and modifiable.
- **Commercial isolation:** Billing, tenant data, hosted infrastructure, abuse controls, and operational secrets do not enter the public repository.
- **Stable integration:** Both products meet through versioned artifacts and APIs instead of undocumented imports.

A private-looking directory inside the public repository is not a security boundary. Private Cloud code belongs in a repository with separate access control, CI, release credentials, and incident response.

## Current state

The public repository currently contains:

- `cli/` — the TypeScript CLI and its Python subprocess bridge.
- `engine/` — the Python processing engine and command implementation.
- `website/` — the public marketing and documentation site.
- `docs/` — maintained product documentation and historical records.
- Root packaging, container, governance, and release files.

The following proposed boundary components do not yet exist as stable public contracts:

- A root `schemas/` package.
- Cross-language contract and compatibility tests.
- An authenticated `arena cloud` CLI namespace.
- A published programmatic engine facade intended for Cloud workers.
- A private `arena-cloud` repository.

Until those components exist, Cloud code must not copy or import evolving engine internals and present that coupling as a supported integration.

## Ownership matrix

| Capability | Arena OSS | Arena Cloud |
|---|---|---|
| Local CLI and configuration | Owns | May invoke through public interfaces |
| Editorial analysis and scoring | Owns | Executes a pinned OSS release |
| Transcription, clipping, captions, formatting | Owns | Executes a pinned OSS release |
| Provider interfaces and bring-your-own-key support | Owns | May provide managed adapters through public interfaces |
| Local caches and artifacts | Owns | May import only with explicit user action |
| Public artifact schemas and event vocabulary | Owns | Consumes and compatibility-tests |
| Cloud client commands and API models | Owns when shipped in the public CLI | Implements the server side |
| Authentication and customer accounts | No local dependency | Owns |
| Hosted job orchestration and queues | No | Owns |
| Hosted object storage and retention | No | Owns |
| Billing, entitlements, quotas, and metering | No | Owns |
| Teams, roles, approvals, and audit logs | No | Owns |
| Tenant isolation and abuse prevention | No | Owns |
| Cloud observability and incident operations | No | Owns |
| Publishing integrations | Owns only public/local extension points | Owns managed credentials and hosted execution |

The editorial quality of local and hosted runs must not be differentiated by hiding a better core algorithm in the private repository. Cloud may offer different managed models, more compute, concurrency, or operational features, but the product must describe those differences accurately.

## Dependency direction

```text
arena-cloud
    │
    ├── pins an Arena OSS release or immutable engine image
    ├── validates public artifact schemas
    └── calls documented CLI, worker, or API entry points
             │
             ▼
          arena OSS

arena OSS ──X──> arena-cloud private source
```

Allowed Cloud dependencies:

- A released Arena engine package or immutable container identified by version and digest.
- Versioned JSON Schemas and generated data types published by Arena OSS.
- Documented process events and exit semantics.
- A documented engine facade when one is published.
- Public Cloud API models used by optional CLI client commands.

Disallowed dependencies:

- Imports from internal modules such as `arena.editorial.*` or `arena.clipping.*` unless that module is explicitly promoted to the supported public API.
- Git submodules or relative filesystem links to a developer checkout.
- Copy-pasted engine modules that can silently diverge.
- Database models, queue payloads, or billing objects leaking into OSS artifacts.
- Private Cloud credentials or deployment configuration in public fixtures, examples, CI logs, or issue templates.

## Public contract surface

The boundary should be built in layers rather than treating every internal Python object as public.

### 1. Artifact envelope

Every portable artifact should include an envelope similar to:

```json
{
  "schema": "arena.analysis",
  "schema_version": 1,
  "producer": {
    "name": "arena",
    "version": "0.5.0"
  },
  "created_at": "2026-08-13T09:00:00Z",
  "data": {}
}
```

Required initial schema families:

- `arena.project/v1`
- `arena.transcript/v1`
- `arena.analysis/v1`
- `arena.clip/v1`
- `arena.job-event/v1`

`arena.job-event/v1` covers persisted or networked job events. The newline-delimited progress protocol parsed by `PythonBridge` in `cli/src/bridge/python-bridge.ts` may inform it, but an internal terminal progress message is not automatically a durable Cloud event.

### 2. Execution interface

The first Cloud worker integration should use an immutable Arena worker image or documented command entry point. A long-lived Python library API should be introduced only after the engine has a deliberately small public facade.

A worker request must identify:

- Arena engine version or image digest.
- Input artifact versions.
- Requested operation and normalized options.
- Provider/model configuration by non-secret identifier.
- Idempotency key.
- Output destination identifiers supplied by the Cloud runtime.

A worker result must identify:

- Outcome and stable error code.
- Output artifact versions and integrity hashes.
- Usage measurements needed for billing.
- Engine and provider/model versions.
- Whether the job is safe to retry.

#### Public engine facade

If a programmatic Python facade is published, its supported surface must be explicit rather than inferred from package visibility. Its release must include:

- A named import path and an allowlist of public classes, functions, request types, result types, and exceptions.
- Documented lifecycle, concurrency, cancellation, and error semantics.
- Contract tests that exercise the facade from outside the engine package.
- A compatibility and deprecation policy with at least one supported release of notice before removal, except for an actively exploited security issue.

Everything outside that allowlist remains internal even if Python permits it to be imported. Publishing the worker image or command boundary does not implicitly make its underlying modules a supported library API.

### 3. Optional Cloud client

If `arena cloud` commands are added to the OSS CLI, the public repository owns:

- Command parsing and local UX.
- API request and response types.
- Credential storage behavior.
- Explicit upload and sync confirmation.
- A way to inspect what data will be transmitted.

The private repository owns the API implementation. Local commands must continue to operate when the Cloud API is unavailable.

## Contract versioning

Schema compatibility is independent from package versioning.

- `schema_version` records the schema family’s major version as an integer. It is intentionally not semantic versioning: compatible additive changes do not create a new wire version.
- Additive, optional fields may remain within the same schema major version.
- Readers must determine optional-field availability by inspecting the payload, not by assuming that every producer of a major version emits every optional field. The producer version remains provenance, not a substitute for schema negotiation.
- Removing a field, changing its meaning or type, or making an optional field required creates a new schema major version.
- Readers must reject unsupported major versions with an actionable error.
- Readers should ignore unknown optional fields within a supported major version.
- Writers must emit one declared version; they must not produce ambiguous hybrid payloads.
- Migrations must be deterministic, tested, and available before an old reader/writer pair is retired.

Arena OSS CI should validate example artifacts and upgrade fixtures. Arena Cloud CI should test its oldest supported input version against the newest supported engine, and its current output against the oldest supported consumer.

Support windows and deprecation dates belong in a compatibility table once the first schema is published.

Published schemas and fixtures are immutable. If a contract is found to expose sensitive data or create another critical risk, maintainers must publish a security advisory, stop affected writers and Cloud ingestion, and release a corrected schema major version. Cloud must be able to deny ingestion of a withdrawn schema or producer version without deleting the historical contract needed to identify and migrate affected artifacts. The advisory must define containment, migration or deletion, supported rollback targets, and the conditions for restoring ingestion.

## Data boundary

“Metadata” is not automatically non-sensitive. Titles, timestamps, summaries, scores, thumbnails, transcripts, and generated captions can reveal the content of private media.

Classify data before defining sync behavior:

| Class | Examples | Default Cloud behavior |
|---|---|---|
| Operational | Arena version, schema version, duration bucket, outcome code | May be sent only for an explicit Cloud operation or separately consented telemetry |
| Content-derived | Titles, summaries, timestamps, scores, hashtags | Do not upload until the user selects a sync or Cloud-processing operation |
| Media-derived | Transcript, thumbnail, waveform, caption file | Separate explicit selection and retention disclosure |
| Raw media | Source video and audio | Never upload for metadata-only sync; explicit confirmation for remote processing |
| Secrets | API keys, browser cookies, OAuth tokens, publishing credentials | Never serialize into Arena artifacts; store only in the responsible credential system |
| Identity and billing | Email, organization, subscription, invoices | Cloud repository and systems only |

Before upload, the CLI should show the destination, data classes, approximate size, retention policy, and whether deletion is supported. `arena cloud sync` must not silently expand from operational data to transcripts, thumbnails, or raw media in a later release.

## Security and operational boundary

The public repository owns security for local execution, packaging, artifact parsing, and Cloud client credential handling. The Cloud repository additionally owns:

- Tenant authorization on every resource access.
- Signed upload/download URLs with short expirations.
- Storage encryption and lifecycle policies.
- Queue isolation, job sandboxing, and resource limits.
- Server-side secret management.
- Audit events for administrative and destructive actions.
- Usage metering integrity and billing dispute evidence.
- Data export, deletion, backup, and restore procedures.
- Incident response for hosted customer data.

Cloud workers should treat all media and artifacts as untrusted input. Job execution must be isolated from the API/control plane and from other tenants.

## Release and provenance boundary

Arena Cloud must record the exact OSS version it executes. Recommended deployment evidence includes:

- Source release tag and commit SHA.
- Package or container digest.
- Artifact schema versions.
- Dependency inventory or SBOM.
- Signature or provenance attestation when available.

Cloud may temporarily pin an older OSS version while compatibility is maintained. An emergency private patch may be deployed only as a time-limited incident response. It must be tracked with an owner and expiry, and it must not change artifact meaning or become a normal Cloud release. The equivalent fix must be upstreamed to Arena OSS and the Cloud deployment returned to a pinned public release before the incident is closed. If disclosure must be delayed for security reasons, the incident record must document the embargo and planned public release.

## Target repository shapes

These trees show responsibility, not an instruction to move the existing repository all at once.

### Public `arena`

```text
arena/
├── cli/                         # Local CLI and optional Cloud API client
├── engine/                      # Complete local processing engine
├── schemas/                     # Versioned public artifacts and job events
├── tests/
│   ├── contracts/
│   └── compatibility/
├── website/                     # Public product and documentation site
├── docs/
│   ├── architecture/
│   ├── cloud/
│   ├── getting-started/
│   ├── guides/
│   ├── reference/
│   └── security/
├── scripts/                     # Packaging, release, and verification tooling
└── README.md
```

### Private `arena-cloud`

```text
arena-cloud/
├── apps/
│   ├── web/                     # Customer dashboard
│   ├── api/                     # Control-plane API
│   ├── worker/                  # Isolated Arena engine execution
│   └── scheduler/               # Scheduled and automated jobs
├── packages/
│   ├── auth/
│   ├── billing/
│   ├── contracts/               # Generated from published OSS schemas
│   ├── database/
│   ├── observability/
│   ├── permissions/
│   ├── queues/
│   └── storage/
├── infrastructure/
├── tests/
│   ├── compatibility/
│   ├── integration/
│   ├── load/
│   ├── security/
│   └── tenancy/
└── docs/
```

## Structural invariants

1. Local processing requires no Arena account.
2. Local processing does not depend on Arena Cloud availability.
3. Cloud authentication is scoped to explicit Cloud operations.
4. Upload, synchronization, and telemetry are separate consent surfaces.
5. Arena OSS contains the complete core editorial and media pipeline.
6. Cloud executes a pinned public release instead of importing undocumented internals.
7. Portable artifacts and durable events use versioned public schemas.
8. Secrets never cross the boundary inside ordinary project artifacts.
9. Private billing, tenancy, and infrastructure code never enters the public repository.
10. A new Cloud capability cannot silently change the behavior or privacy posture of an existing local command.

## Migration gates

### Gate 1: Document the current artifacts

- Inventory transcript, analysis, clip metadata, checkpoint, and CLI event shapes.
- Mark each shape internal, portable, or deprecated.
- Add sensitivity classification to every portable field.

### Gate 2: Publish the first contracts

- Create `schemas/` with versioned JSON Schemas and valid/invalid fixtures.
- Add Python and TypeScript generated types or validators.
- Add cross-language serialization and compatibility tests.

### Gate 3: Publish a worker boundary

- Define normalized job request/result envelopes and stable error codes.
- Package an immutable worker image or command entry point.
- Verify deterministic artifact output and idempotent retry behavior.
- If Cloud uses a Python library integration, publish the explicit engine facade, external contract tests, and deprecation policy defined above before that integration is accepted.

### Gate 4: Add the optional Cloud client

- Define the public API version and authentication flow.
- Implement secure credential storage and logout/revocation.
- Add dry-run or inspect behavior for sync/upload operations.
- Keep telemetry disabled by default until a separate consent flow, inspectable event inventory, revocation control, and no-telemetry test mode are implemented. Cloud authentication or use of a Cloud operation must not imply telemetry consent.
- Generate an opaque local project identifier that neither contains nor is deterministically derived from an absolute filesystem path. Store the local-to-Cloud mapping in local configuration and transmit it only during an explicit Cloud operation.
- Prove that all existing local commands work with the network blocked.

### Gate 5: Create the private Cloud service

- Consume published schemas through a release or generated contract package.
- Implement tenant, retention, deletion, metering, and incident controls.
- Run compatibility tests before accepting a new Arena OSS version.

The private repository should not begin production media processing before Gates 1–3 are complete.

## Open decisions

The following decisions need explicit architecture records before implementation:

1. Whether the supported worker boundary is a container, executable command, Python package facade, or a combination.
2. Where public schemas are published: repository files only, an npm/Python contract package, an OCI artifact, or multiple channels.
3. Whether content-derived metadata sync is per project, per artifact, or controlled by reusable policy.
4. The minimum supported schema compatibility window.
5. How provider/model versions are normalized without leaking secrets.
6. Whether remote processing accepts direct upload, pulls from user-owned storage, or supports both.

## Related documents

- [Arena Cloud plan](./plan.md)
- [Arena Cloud pricing model](./pricing.md)
- [Arena OSS data and privacy](../security/data-and-privacy.md)
- [Arena OSS threat model](../security/threat-model.md)
- [OSS hardening plan](../development/plans/oss-hardening.md)
- [CLI and Python bridge architecture](../architecture/cli.md)
