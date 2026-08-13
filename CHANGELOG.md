# Changelog

All notable user-facing changes will be documented here. Arena follows [Semantic Versioning](https://semver.org/); before 1.0, minor releases may contain documented breaking changes.

## [Unreleased]

## [0.4.2] - 2026-08-13

### Added

- Published `@whitegodkingsley/arena-cli@0.4.2` to npm as the `latest` release.
- Published the official `whitegodkingsley/arena:0.4.2` OCI image for Linux AMD64 and ARM64 with per-platform SBOM and provenance attestations.

### Security

- Hardened installation, package staging, dependency integrity, credential storage, release gates, and container defaults.
- Added Python hash lockfiles, dependency audits, secret scanning, CodeQL, dependency review, SBOM generation, and build provenance.

### Changed

- Defined the strict editorial production-quality contract.
- API keys are stored separately from ordinary configuration with owner-only permissions and are no longer accepted as command-line values.
- End-user npm installation now creates the Python engine only through the isolated, verified `arena setup` runtime; global Python package installation is not part of the supported path.

## [0.4.1] - 2026-08-12

- Current pre-hardening CLI release baseline.

[Unreleased]: https://github.com/iamwhitegod/arena/compare/7f7fd269d130b918be9940175864ef6158b1f2a1...HEAD
[0.4.2]: https://www.npmjs.com/package/@whitegodkingsley/arena-cli/v/0.4.2
[0.4.1]: https://github.com/iamwhitegod/arena/releases/tag/v0.4.1
