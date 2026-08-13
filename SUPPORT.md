# Arena Support Policy

This policy defines the environments the Arena maintainers test and support for the open-source, local-first CLI. Arena OSS is community-supported software provided without warranty under the MIT License. Arena Cloud has a separate service support policy; no paid response-time or uptime commitment applies to this repository.

## Supported toolchains

| Dependency | Supported versions | Source of truth |
| --- | ---: | --- |
| Node.js | 22–24 | `cli/package.json` and `.node-version` |
| Python | 3.10–3.12 | `engine/setup.py` and `.python-version` |
| FFmpeg and ffprobe | Vendor-supported OS release | Managed-runtime installation workflow |
| Docker Engine | Vendor-supported stable release | Container installation workflow |

Node.js versions outside 22–24 fail immediately with an actionable message. Python 3.13 and newer are not supported until Arena's native and ML dependencies are validated against them.

## Platform tiers

### Release-blocking

A release is blocked when the packed npm artifact cannot install and start on any of these environments:

- Ubuntu LTS on x86_64
- Windows on x86_64
- the current and previous macOS major versions on Apple Silicon
- Docker on `linux/amd64` and `linux/arm64`

Release-blocking checks use Node.js 22 and 24. Installation tests must consume the exact packed tarball that will be published, use isolated Arena and npm directories, and run from outside the source checkout.

### Best-effort until native CI is available

- Ubuntu and other Linux distributions on ARM64 outside Docker
- macOS on Intel
- Windows on ARM64
- Linux distributions that are not current Ubuntu LTS releases

Community bug reports for best-effort platforms are welcome. A platform moves into the release-blocking tier only after it has a reliable native runner and produces the same retained installation evidence as the primary matrix.

## What “supported” means

For a release-blocking environment, Arena verifies:

1. the repository builds and its TypeScript and Python test suites pass;
2. the packed npm artifact contains the CLI, engine, and package manifest;
3. a clean consumer can install the tarball and run `arena --version`, `arena --help`, `arena diagnose`, and setup checks outside the repository;
4. deterministic local processing completes without an OpenAI API key;
5. the Docker image starts as a non-root user and passes a health check; and
6. installation evidence records tool versions, artifact identity, duration, and sanitized failure output.

Real hardware verification remains required before claiming flawless behavior on a platform. Emulated or hosted CI expands confidence but does not replace native release testing.

## Reporting installation issues

Run `arena diagnose` and include the generated `arena-diagnostics.txt` report with:

- operating system and architecture;
- Node.js, Python, FFmpeg, and Docker versions as applicable;
- whether installation used npm or Docker; and
- the exact Arena version.

Remove local paths or other sensitive data before publishing diagnostics.

## Where to ask

- Use GitHub Issues for reproducible bugs and focused feature requests.
- Use the installation and troubleshooting documentation plus `arena setup --check` and `arena diagnose` before filing an issue.
- Use [GitHub private vulnerability reporting](https://github.com/iamwhitegod/arena/security/advisories/new) for security issues.

Remove API keys, cookies, local usernames, media content, transcripts, and private paths before sharing output. Maintainers may close reports that cannot be reproduced, concern unsupported versions, or lack the requested information.
