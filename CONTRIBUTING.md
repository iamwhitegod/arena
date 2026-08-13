# Contributing to Arena

Arena is local-first open source software. Contributions to the CLI, Python engine, documentation, packaging, security, and provider integrations are welcome.

## Before you start

- Use an existing issue for substantial changes, or open one before investing in a large redesign.
- Never include API keys, private media, transcripts, cookies, generated clips, or customer data in an issue, fixture, commit, or log.
- Security vulnerabilities must follow [SECURITY.md](SECURITY.md), not the public issue tracker.
- By participating, you agree to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## Development setup

Arena supports maintained Node.js 22 and 24 releases and Python 3.10 through 3.12.

```bash
cd cli
npm ci
npm run build

cd ../engine
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --require-hashes -r requirements-dev.lock
```

FFmpeg and ffprobe must be available on `PATH` for media integration tests.

## Required checks

Run these before opening a pull request:

```bash
cd cli
npm run format:check
npm run lint
npm test
npm run build

cd ..
ruff check --config engine/ruff.toml engine/arena engine/tests
python -m pytest engine/tests -v --tb=short
npm audit --prefix cli --omit=dev --audit-level=high
python -m pip_audit --require-hashes -r engine/requirements.lock
```

Changes to packaging must also pass `cd cli && npm run package:inspect`. Changes to the container must pass `docker compose config` and a local image build.

## Pull requests

- Keep each pull request focused and explain the user-visible behavior.
- Add or update tests for behavior changes.
- Update current documentation and `CHANGELOG.md` when users are affected.
- Preserve the local-first product boundary: local processing must not require an Arena account or undisclosed Arena service.
- New network calls, telemetry, credential access, or executable downloads require explicit documentation and security review.
- Generated files should be reproducible; document the command used to regenerate lockfiles and artifacts.

Arena uses Conventional Commit prefixes (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `build:`, `ci:`, `chore:`) for clear history.

## Developer Certificate of Origin

Arena uses the [Developer Certificate of Origin 1.1](https://developercertificate.org/). Sign off every commit:

```bash
git commit -s -m "fix: describe the change"
```

The sign-off certifies that you have the right to submit the contribution under this repository's license. It is not a copyright assignment.

## Dependency and lockfile updates

Do not hand-edit generated Python lockfiles. Regenerate them with the pinned resolver command recorded in each lockfile header, review the full diff, and run both dependency audits. GitHub Actions must use immutable full commit SHAs.

## Review and releases

Maintainers may request smaller commits, tests, migration notes, or security changes before merge. A maintainer review is required for release workflows, credentials, installation, downloader behavior, artifact schemas, and the OSS/Cloud boundary. Releases follow [docs/RELEASE_PROCESS.md](docs/RELEASE_PROCESS.md).
