# Arena OSS Threat Model

**Version:** 1.0
**Reviewed:** August 13, 2026

## Scope

This model covers the local Arena CLI, Python engine, media tools, package installer, configuration, caches, release artifacts, and container. Arena Cloud is a separate trust domain and must maintain its own server-side threat model.

## Security objectives

- Keep user credentials, media, transcripts, and generated artifacts confidential from unrelated local users and Arena-operated services.
- Prevent untrusted media, URLs, metadata, dependencies, or repository contributions from escaping intended process and filesystem boundaries.
- Make released code and dependencies inspectable, reproducible, and attributable.
- Preserve explicit user control over network access and destructive operations.

Arena does not protect data from an administrator/root user, a fully compromised operating system, or a malicious model provider intentionally selected by the user.

## Assets and trust boundaries

| Asset | Boundary | Main controls |
| --- | --- | --- |
| Provider API keys | Environment or `~/.arena/credentials.json` | No CLI argument, `0600` file, `0700` directory, log redaction |
| Source media and transcripts | User workspace and `.arena/` cache | Local by default, private modes, explicit output paths |
| Downloaded media | Network to yt-dlp/FFmpeg process | User-selected URL, subprocess argument arrays, timeouts |
| Python runtime | PyPI to private virtual environment | Universal lockfiles, SHA-256 hashes, isolated runtime |
| npm release | GitHub Actions to npm registry | Tests, allowlisted staging, audits, SBOMs, provenance |
| Container | Host mounts to non-root process | Pinned base, read-only root, dropped capabilities, explicit writable mounts |

## Primary threats and mitigations

### Dependency or release compromise

An attacker may compromise a package, mutable CI action, build environment, or published artifact. Runtime and developer Python dependencies are transitively locked with hashes; GitHub Actions are pinned to full commits; npm uses its lockfile; releases run both suites, audits, secret scanning, package allowlist checks, SBOM generation, and provenance attestation. Maintainers must review automated dependency changes and rotate pins deliberately.

### Credential disclosure

Secrets can leak through shell history, permissive files, exceptions, diagnostics, or commits. Arena refuses an API key passed to `arena config set`, prompts without echo, separates credentials from settings, enforces owner-only permissions, migrates legacy keys, and recursively redacts recognized secret fields and token patterns. Environment variables remain visible to sufficiently privileged local processes and should be scoped accordingly.

### Malicious media and metadata

FFmpeg, codecs, image libraries, subtitle parsers, and model inputs process attacker-controlled data. Arena runs tools without a shell, updates dependencies through audited locks, and supports an unprivileged read-only container. Users should process untrusted content in the container or another OS sandbox and avoid mounting unrelated directories.

### URL download abuse

The local CLI connects to URLs intentionally supplied by the local user. Redirects, cookies, site metadata, and downloaded files are untrusted. This local behavior must never be reused directly in Arena Cloud: the Cloud implementation must block private, loopback, link-local, metadata-service, and reserved addresses; revalidate redirects and DNS; impose size/time/bandwidth limits; and isolate each job.

yt-dlp JavaScript challenge support is a separately tracked trust decision. Remote executable components must not become an implicit release dependency; any future use requires explicit opt-in, integrity controls, and documentation.

### Filesystem escape or destructive cleanup

Paths and symlinks can redirect writes or cleanup outside the intended workspace. Sensitive configuration and cache data use atomic private writes. Workspace helpers resolve targets beneath an approved root, reject traversal and symlink escapes, require a versioned marker before cleanup, limit parsed cache size, and test adversarial names. New filesystem APIs must preserve the same containment contract.

### Model-provider data disclosure and prompt injection

When AI features are enabled, Arena sends audio or transcript content to the provider selected by the user. Media text may contain adversarial instructions; model output is untrusted data and must not be treated as shell commands, code, credentials, or authorization. Provider calls must be documented and secrets must never be included in prompts.

## Security assumptions

- The user controls the local machine and chooses inputs and providers.
- Node.js, Python, FFmpeg, and the operating system are supported and patched.
- The official npm/PyPI/GitHub/Docker identities have not been compromised.
- Container isolation is defense in depth, not a substitute for a patched host runtime.

## Review triggers

Update this model when Arena adds telemetry, plugins, local model execution, automatic publishing, a daemon, shared workspaces, remote job execution, new executable downloads, or any Arena Cloud data path.
