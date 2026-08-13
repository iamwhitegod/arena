# Recommended Arena Repository Structure

**Status:** Proposed
**Reviewed:** August 12, 2026

## Overview

Arena should use two repositories:

1. A public `arena` repository containing the complete local-first OSS product.
2. A private `arena-cloud` repository containing the paid hosted service.

Arena Cloud source should not live in a private-looking directory inside the public repository. The two products should integrate through versioned public schemas and APIs.

## Arena OSS Repository

```text
arena/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── bug.yml
│   │   ├── feature.yml
│   │   └── config.yml
│   ├── workflows/
│   │   ├── ci.yml
│   │   ├── security.yml
│   │   ├── package.yml
│   │   └── release.yml
│   ├── CODEOWNERS
│   └── pull_request_template.md
│
├── cli/
│   ├── src/
│   │   ├── bridge/
│   │   ├── commands/
│   │   │   └── cloud/             # Optional Arena Cloud client commands
│   │   ├── config/
│   │   ├── core/
│   │   ├── errors/
│   │   ├── security/
│   │   ├── ui/
│   │   ├── validation/
│   │   └── index.ts
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── e2e/
│   │   └── security/
│   ├── scripts/
│   ├── package.json
│   └── tsconfig.json
│
├── engine/
│   ├── arena/
│   │   ├── ai/
│   │   ├── audio/
│   │   ├── clipping/
│   │   ├── editorial/
│   │   ├── export/
│   │   ├── providers/             # OpenAI, local, and future adapters
│   │   ├── security/
│   │   ├── subtitles/
│   │   ├── video/
│   │   └── main.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── contract/
│   │   └── security/
│   ├── pyproject.toml
│   └── requirements.lock
│
├── schemas/                       # Public OSS and Cloud contract
│   ├── project/
│   │   └── v1.schema.json
│   ├── transcript/
│   │   └── v1.schema.json
│   ├── analysis/
│   │   └── v1.schema.json
│   ├── clip/
│   │   └── v1.schema.json
│   ├── events/
│   │   └── v1.schema.json
│   └── README.md
│
├── tests/                         # Cross-language and release tests
│   ├── contracts/
│   ├── fixtures/
│   ├── packaging/
│   └── compatibility/
│
├── scripts/
│   ├── build/
│   ├── release/
│   ├── security/
│   └── verify-package/
│
├── docs/
│   ├── architecture/
│   │   ├── OSS_CLOUD_BOUNDARY.md
│   │   ├── threat-model.md
│   │   └── DATA_FLOW.md
│   ├── adr/                       # Architecture decision records
│   ├── contributing/
│   ├── guides/
│   ├── reference/
│   ├── release/
│   ├── security/
│   └── OSS_HARDENING_PLAN.md
│
├── website/                       # Public product and documentation site
├── docker/
│   ├── Dockerfile
│   └── compose.yml
│
├── CHANGELOG.md
├── CODE_OF_CONDUCT.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── SECURITY.md
├── SUPPORT.md
└── Makefile                       # Optional unified developer commands
```

## Arena Cloud Private Repository

```text
arena-cloud/
├── apps/
│   ├── web/                       # Customer dashboard
│   ├── api/                       # Arena Cloud API
│   ├── worker/                    # Isolated media-processing workers
│   └── scheduler/                 # Automations and scheduled jobs
│
├── packages/
│   ├── auth/
│   ├── billing/
│   ├── database/
│   ├── observability/
│   ├── permissions/
│   ├── queues/
│   └── storage/
│
├── integrations/
│   ├── analytics/
│   ├── publishing/
│   └── webhooks/
│
├── infrastructure/
│   ├── environments/
│   ├── containers/
│   ├── migrations/
│   └── monitoring/
│
├── tests/
│   ├── integration/
│   ├── tenancy/
│   ├── security/
│   └── load/
│
└── docs/
```

## Repository Responsibilities

### Arena OSS owns

- The local CLI and processing engine
- The four-layer editorial system
- Local transcription, clip generation, captions, and formatting
- Model-provider interfaces
- Versioned artifact schemas
- Optional Arena Cloud client commands
- Public documentation and extension points

### Arena Cloud owns

- Authentication and customer accounts
- Managed compute and queues
- Hosted storage and synchronization
- Billing and subscriptions
- Teams, roles, approvals, and audit logs
- Analytics and publishing integrations
- Automation and scheduling
- Tenant isolation, quotas, and abuse prevention

## Integration Boundary

The relationship should remain:

```text
Arena OSS engine
      │
      ▼
Versioned public artifacts and APIs
      │
      ▼
Arena Cloud
```

Arena Cloud should consume the published contracts in `schemas/`. It should not import private modules such as `engine/arena/editorial` directly.

The initial schema families should be:

- `arena.project/v1`
- `arena.transcript/v1`
- `arena.analysis/v1`
- `arena.clip/v1`
- `arena.events/v1`

## Structural Rules

1. Arena OSS must remain useful without an Arena account.
2. Local processing must not depend on Arena Cloud availability.
3. Cloud authentication must apply only to Cloud-specific commands.
4. Telemetry and Cloud synchronization must be explicit opt-in operations.
5. Public schema changes must be versioned and compatibility-tested.
6. Cloud services must not rely on undocumented OSS internals.
7. Shared code belongs in OSS only when it is genuinely part of the public product contract.
8. Secrets, billing logic, tenant data, and hosted infrastructure remain in the private Cloud repository.

## Migration Approach

The structure should be introduced incrementally rather than through a single large move:

1. Add root governance files and reorganize GitHub workflows.
2. Introduce `schemas/` and cross-language contract tests.
3. Add provider and security boundaries inside the existing CLI and engine.
4. Move packaging to explicit staging and verification scripts.
5. Reorganize documentation without rewriting historical content unnecessarily.
6. Create `arena-cloud` only after the first public artifact schemas are stable.

This approach keeps existing development usable while establishing a clear OSS and commercial boundary.
