# Arena documentation

Arena is an AI-powered, open-source, local-first video clipping engine for the terminal that automatically finds the best moments in your videos and exports platform-ready clips for TikTok, Reels, and Shorts. This directory contains its maintained documentation; documents under [`archive/`](./archive) are historical records and are not the current product contract.

## Why local-first?

Arena starts processing from the terminal without requiring an upfront cloud upload, saving time and bandwidth—especially on unreliable connections. Source videos, transcripts, analysis results, and generated clips remain on the user's machine unless they explicitly use an external provider or Arena Cloud. This architecture also supports a future path for optional local AI models while keeping Arena useful to both creators and developers.

## Start here

- [Quick start](./getting-started/quickstart.md) — install Arena and generate the first clips.
- [Installation](./getting-started/installation.md) — supported environments, npm installation, source setup, and repair.
- [Workflow guide](./guides/workflows.md) — common processing and publishing workflows.
- [CLI reference](./reference/cli.md) — commands and options.
- [Troubleshooting](./guides/troubleshooting.md) — diagnosis and recovery.
- [Product roadmap](./roadmap.md) — direction for Terminal, Cloud, Desktop, and Mobile.

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
