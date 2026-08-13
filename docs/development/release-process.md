# Release Process

Arena uses Semantic Versioning. Before 1.0, breaking changes increment the minor version and must include migration notes; after 1.0, they require a major release. Deprecated public behavior should remain for at least one minor release when security and feasibility permit.

## Maintainer checklist

1. Confirm `main` is green in Test and Security workflows.
2. Review dependency updates, action SHAs, Python lockfile headers, and audit results.
3. Update package versions and `CHANGELOG.md` in one pull request.
4. Run `npm run package:inspect` from `cli/` and inspect the tarball allowlist.
5. Build the container and verify it runs as a non-root user.
6. Tag the exact reviewed commit with a signed `vX.Y.Z` tag.
7. Create the GitHub release from that tag.
8. Let the protected `npm` environment publish; do not publish from a developer workstation.
9. Retain and inspect the uploaded npm tarball, CycloneDX SBOMs, and provenance attestation.
10. Verify the npm package, provenance, installation, and `arena setup --check` on a clean machine.

The publication workflow must not be bypassed when a gate fails. A security hotfix may reduce the normal announcement window, but it still requires tests, artifact inspection, audits, SBOMs, and provenance.
