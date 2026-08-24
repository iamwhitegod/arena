# Release Process

Arena uses Semantic Versioning. Before 1.0, breaking changes increment the minor version and must include migration notes; after 1.0, they require a major release. Deprecated public behavior should remain for at least one minor release when security and feasibility permit.

## Maintainer checklist

1. Confirm `main` is green in Test, Security, source-install, managed-runtime, packed-artifact, and container workflows.
2. Review dependency updates, action SHAs, Python lockfile headers, and audit results.
3. Update package versions and `CHANGELOG.md` in one pull request.
4. Run `npm run package:inspect` from `cli/` and inspect the tarball allowlist.
5. Confirm the protected `container` environment contains `DOCKERHUB_USERNAME` and a scoped `DOCKERHUB_TOKEN` for `whitegodkingsley/arena`.
6. Build both container architectures and verify they run as a non-root user and pass the configured scans.
7. Tag the exact reviewed commit with a signed `vX.Y.Z` tag matching `cli/package.json`.
8. Publish the GitHub release from that tag.
9. Let the protected `npm` and `container` environments publish; do not publish either artifact from a developer workstation.
10. Retain and inspect the npm tarball, CycloneDX SBOMs, container SBOM/provenance, and publication evidence.
11. Dispatch `registry-smoke.yml` with the exact published version. Require its npm signature/provenance job and clean Ubuntu, Windows, and macOS installation jobs to pass.
12. Verify the versioned Docker image manifest and hardened runtime on AMD64 and ARM64.
13. Promote only the exact tested candidate; never rebuild between canary verification and promotion.

The publication workflow must not be bypassed when a gate fails. A security hotfix may reduce the normal announcement window, but it still requires tests, artifact inspection, audits, SBOMs, and provenance.

GitHub release events are not passed directly to event-sensitive scanning actions. Each publication workflow instead queries GitHub Actions and requires a completed successful Security run from a `push` or manual dispatch on the exact tagged commit and repository default branch. This reuses the immutable commit's CodeQL, dependency, secret, and container-scan evidence and fails closed when the evidence is missing or belongs to another SHA or branch.

The public container contract is `docker.io/whitegodkingsley/arena`. Stable releases publish immutable `X.Y.Z` and commit tags plus moving `X.Y`, `X`, and `latest` tags. Pre-releases publish only the exact version and commit tags, so they cannot replace `latest`. The npm workflow applies the same rule by publishing pre-releases under `next` and stable releases under `latest`. Both publication workflows reject a Git tag that does not match `cli/package.json`. The container workflow publishes one multi-architecture manifest for Linux AMD64 and ARM64 and verifies the registry digest before completion.
