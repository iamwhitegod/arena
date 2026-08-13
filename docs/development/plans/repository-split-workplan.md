# Three-repository split workplan

**Status:** Approved for implementation

**Last reviewed:** August 13, 2026

## Proposal

Use one local workspace containing three independent Git repositories:

```text
arena/                         # Local workspace; not a Git repository
├── arena-oss/                 # Public Git repository
│   ├── cli/
│   ├── engine/
│   ├── schemas/
│   ├── docs/
│   ├── scripts/
│   └── tests/
├── arena-cloud/               # Private Git repository
│   ├── apps/
│   ├── packages/
│   ├── infrastructure/
│   ├── docs/
│   └── tests/
└── arena-website/             # Public Git repository
    ├── src/
    ├── public/
    ├── tests/
    └── package.json
```

The directories are ordinary sibling checkouts. They are not symlinks, Git submodules, or relative package dependencies. The local directory may be named `arena-oss`, while the existing public remote and GitHub repository may continue to be named `arena`.

## Dependency rules

```text
arena-website ── consumes released public metadata/docs ──┐
                                                          ▼
arena-cloud ── consumes pinned releases/contracts ─────> arena-oss

arena-oss ──X──> private Cloud source
arena-oss ──X──> website source checkout
```

- `arena-oss` remains the source of truth for the CLI, engine, public schemas, contract fixtures, local security, and technical documentation.
- `arena-cloud` consumes a pinned Arena release or immutable image and generated public contract types. It must not copy engine modules or import undocumented internals.
- `arena-website` owns marketing, download, and public product presentation. It may render released OSS documentation, but it must not become the canonical source for CLI/engine behavior.
- Cross-repository integration uses releases, packages, OCI digests, published schemas, or explicit APIs—not `../arena-oss` filesystem imports.

## Current-state findings

- The current repository contains `cli/`, `engine/`, `website/`, `docs/`, root packaging, Docker, governance, and release automation.
- `website/` is already a standalone private Next.js package with its own lockfile/build lifecycle.
- Root Docker and GitHub release workflows deliberately build `cli/` and `engine/` together. Those components should remain in one repository.
- The CLI package metadata and public documentation currently point to the existing `iamwhitegod/arena` repository.
- Technical documentation currently links directly to repository files under `docs/`.
- No Cloud implementation repository exists as part of the current source tree.

## Relationship to repository-boundary gates

The split phases organize source control and deployment ownership. The repository-boundary gates organize portable contracts and Cloud execution safety. They are related but not one sequence:

| Split work                            | Gate dependency                    | May proceed when                                             |
| ------------------------------------- | ---------------------------------- | ------------------------------------------------------------ |
| Phase 0 decision and Phase 1 baseline | None                               | Maintainer approves the split decisions                      |
| Phase 2 website extraction            | None of Gates 1–5                  | Phases 0–1 pass; it may run alongside Gate 1                 |
| Phase 3 OSS website removal           | None of Gates 1–5                  | New website passes cutover and its observation window        |
| Phase 4 Cloud repository shell        | None for an empty private scaffold | Phase 0 approves ownership/security; synthetic fixtures only |
| Cloud contract consumption            | Gate 2                             | Public schemas and compatibility policy are published        |
| Cloud worker integration              | Gate 3                             | The supported worker boundary passes its exit criteria       |
| Cloud client integration              | Gate 4                             | Public API/auth/consent decisions and tests pass             |
| Production Cloud service              | Gates 1–3, then Gate 5 readiness   | Production hold is explicitly lifted                         |
| Phase 5 local workspace               | Repository existence only          | At least two approved sibling checkouts exist                |
| Phase 6 website release flow          | No Cloud gate                      | OSS public release metadata is defined                       |
| Phase 6 Cloud release flow            | Gates 2–3                          | Contracts and worker provenance are published                |

The immediate parallel tracks after approval are:

```text
Split approval -> clean baseline -> extract website -> cut over -> remove website from OSS
                         |
                         └-> Gate 1 cleanup -> Gate 2 contracts -> Gate 3 worker -> Cloud readiness
```

## Planning estimates

These are engineering-effort ranges, not calendar commitments. They exclude review queues, hosting propagation, the website observation window, and implementation of the Cloud product itself.

| Phase                                    | Priority                         | Estimated effort                                      |
| ---------------------------------------- | -------------------------------- | ----------------------------------------------------- |
| 0. Decisions and ownership               | Immediate blocker                | 0.5–1 engineer-day                                    |
| 1. Clean baseline                        | Immediate                        | 1–2 engineer-days                                     |
| 2. Website extraction and preview        | High                             | 2–4 engineer-days                                     |
| 3. OSS cleanup after cutover             | High                             | 1–2 engineer-days plus one release observation window |
| 4. Private Cloud repository shell        | Medium; parallel after approval  | 1–2 engineer-days, excluding service features         |
| 5. Local workspace setup                 | Low                              | 0.5 engineer-day                                      |
| 6. Initial cross-repository release flow | High before independent releases | 1–3 engineer-days                                     |

## Safety rules

1. Do not move or delete the current `website/` directory until the extracted repository builds, deploys, and passes route comparison.
2. Preserve the existing public repository, tags, issues, stars, release URLs, package provenance, and commit history unless the maintainer explicitly chooses a new remote.
3. Create repositories from clean clones. Do not rewrite the working repository in place.
4. Never copy untracked build output, caches, credentials, `.env` files, `.vercel/`, media, or local `.arena/` state into a new repository.
5. Do not introduce a parent Git repository around nested repositories unless that is approved as a separate workspace-tooling decision.
6. Cloud production media processing remains blocked until repository-boundary Gates 1–3 are complete.

## Phase 0: Approve the split

### Deliverables

- Approve the decisions in the review checklist at the end of this document.
- Verify [Repository boundary](../../cloud/repository-boundary.md) reflects the approved three-repository decision.
- Assign repository visibility, owner teams, administrator access, and CODEOWNERS.
- Reserve the `arena-website` and private `arena-cloud` remote names.
- Decide the migration window and temporary structural-change freeze.

### Exit criteria

- Repository names, remotes, visibility, ownership, documentation ownership, and history strategy are recorded.
- No extraction or deletion begins before approval.

## Phase 1: Establish a clean baseline

### Work

- Finish, commit, or deliberately set aside current worktree changes.
- Record the source commit SHA and create a protected pre-split tag.
- Run the existing OSS test, build, packaging, container, and website build checks.
- Inventory tracked files under `website/` and confirm local/generated files are ignored.
- Inventory all root files the website will need after extraction: license, security/contact policy, contribution guidance, deployment configuration, environment-variable documentation, and CI.
- Capture current production routes, redirects, metadata, analytics configuration, environment variables, and deployment ownership.

### Verification

```bash
cd cli && npm run build && npm test && npm run lint
cd engine && pytest tests/
cd website && npm run lint && npm run build
docker compose build
git status --short
```

Release and container smoke workflows must also be green at the recorded source commit.

### Rollback

No remote or tree changes occur in this phase. The protected tag identifies the complete pre-split state.

## Phase 2: Extract `arena-website`

### Work

1. Create a fresh clone from the protected source commit.
2. Extract `website/` history into a new root using `git filter-repo` or an equivalent reviewed history-preserving process.
3. Never run the history rewrite against the primary checkout or existing public remote.
4. Add website-specific root files:
   - `README.md`
   - MIT `LICENSE`, matching the current public repository, unless asset review identifies separately licensed material
   - `.gitignore`
   - `SECURITY.md` or a link to the responsible policy
   - `CONTRIBUTING.md`
   - CODEOWNERS and pull-request templates
   - dependency, test, build, preview, and deployment workflows
5. Replace repository-relative assumptions and references to `website/...` with the new repository root.
6. Configure the deployment project to use the new repository without changing the production domain yet.
7. Compare preview output, routes, redirects, metadata, and public assets with the current deployment.
8. Install an initial ownership policy. Proposed minimum:

   ```text
   *               @iamwhitegod
   /.github/       @iamwhitegod
   /src/           @iamwhitegod
   /package*.json  @iamwhitegod
   ```

An example history-extraction command may be documented during implementation, but it must be peer-reviewed against a disposable clone before use.

### Verification

- Clean install, lint, type/build, and browser smoke tests pass from the new repository root.
- A preview deployment matches the current production route inventory.
- Repository secrets and deployment credentials are recreated through the hosting platform; none are committed.
- The extracted history contains website changes and no unrelated engine/CLI files.
- Links to canonical OSS documentation resolve to stable public URLs.

### Cutover and rollback

- Switch the deployment integration to `arena-website` only after preview approval.
- Keep the old deployment integration and current `website/` tree available for one release window.
- Roll back by reconnecting the old repository/deployment at the protected source commit.

## Phase 3: Establish `arena-oss`

### Recommended approach

Retain the existing public GitHub repository and full history. Rename only the local checkout directory from `arena` to `arena-oss`. This avoids breaking issues, stars, forks, releases, package provenance, container references, and public links.

### Work

- Verify CLI package repository/bugs metadata still points to the retained public remote.
- Update architecture documentation to show all three repositories.
- Add links to the new website repository and contribution boundary.
- After the website cutover observation window, remove `website/` in one dedicated OSS commit.
- Remove website-only workflow paths, Dependabot entries, CODEOWNERS entries, and documentation from the OSS repository.
- Keep root Docker/release automation that jointly packages `cli/` and `engine/`.
- Keep canonical CLI, engine, schema, security, and contributor documentation in `arena-oss`.
- Add a repository-boundary check that rejects private Cloud imports, relative sibling dependencies, and accidentally committed credentials.
- Retain the current OSS CODEOWNERS policy initially, then remove only website-specific paths after extraction.

### Verification

- All CLI/engine tests, packaging, installation smoke tests, container builds, security jobs, and releases pass after `website/` removal.
- `rg` finds no build/deploy dependency on the former `website/` path.
- Public documentation and package URLs remain valid.
- The OSS repository can be cloned and developed without either sibling repository.

### Rollback

Revert the dedicated website-removal commit. The public history and remote are never rewritten.

## Phase 4: Create private `arena-cloud`

### Work

- Create an empty private repository with separate administrators, CI, deployment credentials, secret management, incident ownership, branch protection, and audit controls.
- Add only the minimum repository skeleton approved by the Cloud architecture; do not copy CLI/engine source.
- Consume published schemas/types and a pinned Arena release or immutable worker image.
- Add dependency-policy checks preventing undocumented `arena.*` internal imports, copied engine modules, and local `../arena-oss` dependencies.
- Use synthetic fixtures until repository-boundary Gates 1–3 are complete.
- Implement the private service only through Gate 5 of the [Repository boundary implementation plan](./repository-boundary-implementation.md).
- Create CODEOWNERS with a required private maintainer team before implementation begins. Proposed protected paths:

  ```text
  *                  @<cloud-maintainers>
  /.github/          @<cloud-maintainers>
  /infrastructure/   @<cloud-maintainers> @<security-reviewers>
  /packages/auth/    @<cloud-maintainers> @<security-reviewers>
  /packages/billing/ @<cloud-maintainers> @<billing-reviewers>
  ```

  Team handles remain a Phase 0 ownership decision; placeholders must not be committed to the created repository.

### Verification

- A clean Cloud checkout validates public fixtures without an OSS sibling checkout.
- The worker test records the exact Arena version/image digest.
- CI demonstrates that no raw media, credentials, or private configuration enters fixtures/logs.
- Production deployment remains disabled until the Gate 1–3 readiness review explicitly lifts the hold.

### Rollback

The Cloud repository can be archived without affecting local Arena or the website. Any worker rollback selects a previously approved immutable public release/digest.

## Phase 5: Create the local workspace

### Work

- Rename or clone the checkouts into the parent layout:

  ```text
  arena/
    arena-oss/
    arena-cloud/
    arena-website/
  ```

- Keep `arena/` untracked by default.
- Optionally create a local editor workspace file that opens all three directories.
- If repeatable onboarding is needed, publish a bootstrap script in a deliberately scoped tooling repository or internal onboarding document. Do not solve this with Git submodules by default.
- Document that commands run inside the owning repository and that each repository has its own Git status, branches, pull requests, and CI.

### Verification

- Each child reports its own expected Git root and remote.
- Editing one repository does not dirty another.
- Each repository installs/builds without sibling filesystem access.

## Phase 6: Cross-repository release and documentation flow

### Work

- Define the OSS release outputs consumed by Cloud: schemas/package version, worker image digest, compatibility table, fixtures, and provenance.
- Define the public metadata consumed by the website: current stable version, install commands, release/download links, schema/documentation links, and product status.
- Choose an explicit update mechanism such as dependency automation, scheduled fetch, or repository dispatch. Do not grant broad cross-repository write tokens.
- Add link checking across public URLs and compatibility checks across published artifacts.
- Document release order:
  1. publish and verify Arena OSS;
  2. update/verify Cloud compatibility against the released version;
  3. update website release metadata and public announcements.
- Document independent rollback for OSS packages/images, Cloud deployments, and website deployments.

### Completion criteria

- All three repositories have independent CI, ownership, security settings, release or deployment procedures, and contribution guidance.
- Neither Cloud nor website requires a sibling checkout.
- Arena OSS remains fully local-first and network-independent for non-Cloud commands.
- Canonical documentation ownership and public links are unambiguous.
- The old `website/` tree and obsolete automation are absent from `arena-oss` after the observation window.

## Review checklist

The maintainer approved the recommended choices by authorizing implementation on August 13, 2026. Any later change requires an explicit amendment before the affected phase proceeds.

| Decision                | Recommended choice                                                                              | Maintainer review |
| ----------------------- | ----------------------------------------------------------------------------------------------- | ----------------- |
| Parent `arena/`         | Local, non-Git workspace                                                                        | Approved          |
| OSS remote              | Keep existing public `iamwhitegod/arena` repository and history                                 | Approved          |
| OSS local directory     | `arena-oss/`                                                                                    | Approved          |
| Website remote          | New public `arena-website` repository                                                           | Approved          |
| Website history         | Preserve `website/` subtree history with a filtered clone                                       | Approved          |
| Website license         | MIT, matching Arena OSS; review third-party/public assets separately                            | Approved          |
| Cloud remote            | New private `arena-cloud` repository                                                            | Approved          |
| Technical docs          | Canonical in `arena-oss/docs/`; website renders/links released content                          | Approved          |
| Issue tracking          | OSS issues remain in `arena`; website issues move to `arena-website`; Cloud issues stay private | Approved          |
| Cross-repo dependencies | Published release/package/schema/API only; no sibling path dependencies                         | Approved          |
| Website cutover window  | One verified release window before deleting `website/` from OSS                                 | Approved          |
| Production Cloud hold   | No production media before repository-boundary Gates 1–3 pass                                   | Approved          |

## Related documents

- [Repository boundary](../../cloud/repository-boundary.md)
- [Repository boundary implementation plan](./repository-boundary-implementation.md)
- [Current artifact inventory](../../reference/artifact-contracts.md)
- [Release process](../release-process.md)
