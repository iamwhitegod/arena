# Release Process

Arena uses Semantic Versioning. Before 1.0, breaking changes increment the minor version and must include migration notes; after 1.0, they require a major release. Deprecated public behavior should remain for at least one minor release when security and feasibility permit.

## Maintainer checklist

1. Confirm `main` is green in Test and Security workflows.
2. Review dependency updates, action SHAs, Python lockfile headers, and audit results.
3. Update package versions and `CHANGELOG.md` in one pull request.
4. Run `npm run package:inspect` from `cli/` and inspect the tarball allowlist.
5. Confirm the protected `container` environment contains `DOCKERHUB_USERNAME` and a scoped `DOCKERHUB_TOKEN` for `whitegodkingsley/arena`.
6. Build both container architectures and verify they run as a non-root user and pass the configured scans.
7. Tag the exact reviewed commit with a signed `vX.Y.Z` tag matching `cli/package.json`.
8. Publish the GitHub release from that tag.
9. Let the protected `npm` and `container` environments publish; do not publish either artifact from a developer workstation.
10. Retain and inspect the npm tarball, CycloneDX SBOMs, container SBOM/provenance, and publication evidence.
11. Verify the npm package and `arena setup --check` on a clean machine, then verify the versioned Docker image manifest and runtime on AMD64 and ARM64.

The publication workflow must not be bypassed when a gate fails. A security hotfix may reduce the normal announcement window, but it still requires tests, artifact inspection, audits, SBOMs, and provenance.

The public container contract is `docker.io/whitegodkingsley/arena`. Stable releases publish immutable `X.Y.Z` and commit tags plus moving `X.Y`, `X`, and `latest` tags. Pre-releases publish only the exact version and commit tags, so they cannot replace `latest`. The release workflow rejects a Git tag that does not match the CLI package version, publishes one multi-architecture manifest for Linux AMD64 and ARM64, and verifies the registry digest before completion.
