# Changelog

All notable user-facing changes will be documented here. Arena follows [Semantic Versioning](https://semver.org/); before 1.0, minor releases may contain documented breaking changes.

## [Unreleased]

### Security

- Hardened installation, package staging, dependency integrity, credential storage, release gates, and container defaults.
- Added Python hash lockfiles, dependency audits, secret scanning, CodeQL, dependency review, SBOM generation, and build provenance.

### Changed

- Defined the strict editorial production-quality contract.
- API keys are stored separately from ordinary configuration with owner-only permissions and are no longer accepted as command-line values.

## [0.4.1] - 2026-08-12

- Current pre-hardening CLI release baseline.

[Unreleased]: https://github.com/iamwhitegod/arena/compare/v0.4.1...HEAD
[0.4.1]: https://github.com/iamwhitegod/arena/releases/tag/v0.4.1
