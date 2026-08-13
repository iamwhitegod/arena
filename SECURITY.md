# Security Policy

## Supported versions

Until Arena reaches 1.0, security fixes are provided for the latest published minor release. Maintainers may backport a critical fix when practical, but older pre-1.0 releases should be considered unsupported.

| Version | Supported |
| --- | --- |
| Latest published minor | Yes |
| Older pre-1.0 releases | No |
| Unreleased branches | Best effort |

## Report a vulnerability privately

Use [GitHub private vulnerability reporting](https://github.com/iamwhitegod/arena/security/advisories/new). Do not open a public issue, discussion, or pull request containing exploit details, credentials, private media, or personal data.

Include, when possible:

- affected version and platform;
- reproduction steps or a minimal proof of concept;
- expected impact and required user interaction;
- suggested mitigations;
- whether the issue is already public.

If private reporting is unavailable, open a public issue that asks a maintainer to establish private contact, without including vulnerability details.

## Response targets

Maintainers aim to acknowledge reports within three business days and provide an initial triage within seven business days. Fix and disclosure timing depends on severity, exploitability, upstream coordination, and release risk. These are targets, not a service-level agreement.

We will coordinate credit and disclosure with the reporter. Please allow a reasonable remediation window before publication.

## Security scope

In scope includes the CLI, Python engine, installers, package/release pipeline, container, credential handling, local file boundaries, and documented Arena-operated integrations. Vulnerabilities in an upstream dependency should also be reported upstream; tell Arena maintainers when Arena needs a mitigation or upgrade.

The following are generally not vulnerabilities by themselves:

- costs caused by a user intentionally supplying their own provider key;
- processing untrusted media without demonstrating a boundary escape or material impact;
- unsupported releases or modified third-party builds;
- social engineering without a product defect.

See [docs/security/THREAT_MODEL.md](docs/security/THREAT_MODEL.md) for trust boundaries and known risks.
