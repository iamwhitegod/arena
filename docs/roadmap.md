# Arena Product Roadmap

Arena is an AI-powered, open-source, local-first video clipping engine for the terminal that automatically finds the best moments in your videos and exports platform-ready clips for TikTok, Reels, and Shorts.

The terminal product is Arena's foundation. Cloud, Desktop, and Mobile should build on the same engine and public artifact contracts without weakening the complete, account-free local workflow.

This roadmap communicates direction, not guaranteed dates. Priorities may change as Arena learns from users and validates technical, security, and business assumptions.

## Product principles

1. **Terminal first:** the CLI remains the reference workflow and fastest path to new engine capabilities.
2. **Local remains complete:** core processing must not require an Arena account or Cloud subscription.
3. **One engine, multiple experiences:** Terminal, Desktop, Cloud, and Mobile should share versioned jobs, transcripts, analyses, and clip artifacts.
4. **Cloud is explicit:** uploads, remote processing, retention, and cost must be visible before work begins.
5. **Ship by evidence:** move products between stages only after reliability, security, and user-demand gates are met.

## Why local-first matters

- Processing starts immediately from the terminal without requiring a large source-video upload to the cloud.
- Creators save upload time and bandwidth and avoid repeated upload failures on unreliable connections.
- Source videos, transcripts, analysis results, and generated clips remain on the user's machine unless they explicitly use an external provider or Arena Cloud.
- The architecture leaves room for optional local transcription, analysis, and embedding models in the future.
- Creators get a fast, private workflow while developers get scriptable commands and inspectable artifacts.

## Product tracks

| Product | Status | Role | Near-term focus |
|---|---|---|---|
| **Arena Terminal** | Available now | Complete open-source, local-first engine and CLI | Reliability, editorial quality, installation, performance, and stable artifact contracts |
| **Arena Cloud** | Planned | Optional managed compute, storage, collaboration, automation, and publishing | Public API contracts, secure job isolation, billing model, hosted projects, and private alpha |
| **Arena Desktop** | Exploration | Visual local workflow powered by the Arena engine | Clip review, timeline adjustments, caption styling, project management, and local/Cloud handoff |
| **Arena Mobile** | Exploration | Companion experience for capture, review, approval, and publishing | Mobile upload, job monitoring, clip review, approvals, and social export |

## Stage 1 — Strengthen Arena Terminal

The terminal product must be dependable enough to serve as the engine and contract for every later surface.

- Stabilize installation, diagnostics, upgrades, and supported platforms.
- Improve download, transcription, editorial, and FFmpeg failure recovery.
- Version project, transcript, analysis, event, and clip-manifest schemas.
- Expand deterministic fixtures, end-to-end tests, and release verification.
- Improve clip review, caption quality, batch workflows, and performance.
- Document privacy boundaries, provider costs, and reproducible processing.

**Exit gate:** stable public artifacts, trustworthy releases, and production-grade job recovery.

## Stage 2 — Validate Arena Cloud

Arena Cloud adds operational convenience around the same processing model; it is not a replacement for Arena Terminal.

- Define authenticated Cloud APIs and an explicit `arena cloud` CLI boundary.
- Build isolated remote jobs, object storage, retention controls, and deletion flows.
- Add hosted project history, job monitoring, retries, and notifications.
- Validate source-video-minute billing with a trial and proposed paid plans.
- Run a private alpha before introducing collaboration, automation, analytics, and publishing.

**Exit gate:** secure tenant isolation, predictable unit economics, reliable processing, and evidence that users value managed workflows.

## Stage 3 — Build Arena Desktop

Arena Desktop should make the local engine approachable without creating a separate processing stack.

- Package or connect to the same versioned Arena engine.
- Add visual import, processing progress, and project history.
- Create a clip-review queue with accept, reject, trim, and regenerate actions.
- Add caption styling, crop previews, and platform export controls.
- Support local-only projects first, then optional Cloud sync and remote compute.

**Exit gate:** feature parity for the primary local clipping workflow and safe upgrades across engine versions.

## Stage 4 — Launch Arena Mobile Companion

Arena Mobile should begin as a companion to Cloud and Desktop. Running the complete editorial and encoding pipeline on-device is not an initial requirement.

- Capture or upload source media from a phone.
- Start and monitor Cloud jobs.
- Review, approve, reject, and share generated clips.
- Adjust titles, captions, crops, and publishing metadata.
- Add team approvals, notifications, and platform publishing where APIs permit.
- Explore selective on-device processing only after measuring demand, battery, storage, and model constraints.

**Exit gate:** a fast capture-to-review workflow with clear privacy, upload, and publishing controls.

## What is not promised yet

- Public release dates for Cloud, Desktop, or Mobile.
- Feature parity across every product surface at launch.
- Silent Cloud uploads or a Cloud account requirement for local processing.
- Full on-device mobile transcription, editorial analysis, or encoding.

Follow progress or propose priorities in [GitHub Issues](https://github.com/iamwhitegod/arena/issues).
