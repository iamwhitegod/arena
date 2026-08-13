# Arena documentation

This directory contains the maintained documentation for Arena. Start with the section that matches what you are trying to do; documents under [`archive/`](./archive) are historical records and are not the current product contract.

## Start here

- [Quick start](./getting-started/quickstart.md) — install Arena and generate the first clips.
- [Installation](./getting-started/installation.md) — supported environments, npm installation, source setup, and repair.
- [Workflow guide](./guides/workflows.md) — common processing and publishing workflows.
- [CLI reference](./reference/cli.md) — commands and options.
- [Troubleshooting](./guides/troubleshooting.md) — diagnosis and recovery.

## Guides

- [Audio enhancement](./guides/audio-enhancement.md)
- [OpenAI quota and billing issues](./guides/openai-quota.md)
- [CLI output states](./reference/cli-output.md)

## Feature documentation

- [Audio enhancement](./features/audio/enhancement.md)
- [Audio energy detection](./features/audio/energy-detection.md)
- [Clip generation](./features/clip-generation.md)
- [Hybrid analysis](./architecture/hybrid-analysis.md)

## Reference

- [CLI commands](./reference/cli.md)
- [CLI output and engine event protocol](./reference/cli-output.md)
- [Engine API](./reference/engine-api.md)
- [Audio enhancement settings](./reference/audio-enhancement-settings.md)
- [Clip naming](./reference/clip-naming.md)
- [AI prompts](./reference/prompts.md)

## Architecture

- [Editorial system](./architecture/editorial-system.md)
- [CLI and Python bridge](./architecture/cli.md)
- [Hybrid analysis](./architecture/hybrid-analysis.md)
- [Layer 1 two-pass design](./architecture/editorial/layer1-two-pass.md)
- [Architecture decisions](./architecture/decisions/README.md)

## Arena Cloud proposals

Cloud documents describe proposed product boundaries and are not commitments for the open-source release.

- [Cloud plan](./cloud/plan.md)
- [Pricing model](./cloud/pricing.md)
- [Repository boundary](./cloud/repository-boundary.md)

## Security and privacy

- [Data and privacy](./security/data-and-privacy.md)
- [Threat model](./security/threat-model.md)
- [Security policy](../SECURITY.md)

## Development and release

- [Contributing](../CONTRIBUTING.md)
- [Release process](./development/release-process.md)
- [Installation verification plan](./development/plans/installation-verification.md)
- [OSS hardening plan](./development/plans/oss-hardening.md)
- [Platform-formatting verification](./development/testing/platform-formatting.md)
- [CLI test guide](../cli/tests/README.md)

## Historical material

The [archive](./archive) contains completed sprint notes, superseded implementation plans, validation snapshots, and research. It remains available for engineering context, but it must not be used as the source of truth for current commands or behavior.

## Documentation conventions

- Keep root-level project policies in the repository root so GitHub can discover them.
- Keep component-specific instructions beside their component, such as `cli/README.md` and `website/README.md`.
- Use lowercase kebab-case filenames under `docs/`.
- Put current user tasks in `getting-started/` or `guides/`, stable interfaces in `reference/`, system explanations in `architecture/`, and completed or superseded work in `archive/`.
- Link to one canonical page instead of copying the same instructions into multiple files.
