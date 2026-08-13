# Arena Content Guide

**Status:** Draft for review<br />
**Purpose:** Define Arena's product language and proposed website copy before implementation.<br />
**Scope:** Website, documentation entry points, GitHub README, npm package page, and product announcements.

## 1. Product positioning

### Canonical description

> Arena is an AI-powered, open-source, local-first video clipping engine for the terminal. It finds the best moments in your videos and exports ready-to-publish clips for TikTok, Reels, and Shorts.

### Short description

> Local-first AI video clipping engine for the terminal.

### One-line benefit

> Turn long videos into ready-to-publish social clips—without uploading them first.

### Positioning hierarchy

Present Arena's value in this order:

1. **Outcome:** Find strong moments and create social clips.
2. **Immediate advantage:** Start without uploading the source video first.
3. **Product model:** Open source, local first, and terminal based.
4. **Differentiator:** A four-layer editorial system selects complete, standalone moments.
5. **Destinations:** TikTok, Instagram Reels, and YouTube Shorts.

Do not lead with implementation details such as GPT models, FFmpeg, embeddings, or hybrid scoring. Introduce those details when users are evaluating how Arena works.

## 2. Audience

### Creators

Creators want to publish more useful clips with less repetitive editing. Emphasize outcomes, control, privacy, saved upload time, and platform-ready exports.

### Developers and technical creators

Developers want a predictable tool they can inspect, script, and automate. Emphasize the terminal, open source, explicit files, reproducible commands, and stable artifacts.

### Teams evaluating Arena Cloud

Teams want managed compute, collaboration, automation, and operational reliability. Explain that Cloud is optional and does not restrict the local product.

## 3. Voice and tone

Arena should sound:

- **Direct:** Say what the product does before explaining how.
- **Grounded:** Make verifiable claims and label future work clearly.
- **Confident:** Use simple statements without hype or defensiveness.
- **Technical when useful:** Respect developers without making every visitor parse implementation details.
- **Creator aware:** Describe publishing workflows in familiar language.

Arena should not sound:

- Sensational: avoid “viral,” “revolutionary,” “magic,” and guaranteed outcomes.
- Vague: avoid “AI-powered solution” without stating the user benefit.
- Corporate: avoid “leverage,” “synergy,” “best-in-class,” and “seamless.”
- Absolute: do not imply that all processing is offline while external AI providers are currently used.
- Premature: do not describe planned Cloud, Desktop, Mobile, or local-model features as available.

## 4. UX-writing principles

### Lead with the user's outcome

Prefer:

> Turn long videos into ready-to-publish social clips.

Avoid:

> Arena combines advanced NLP, audio analytics, and precision FFmpeg processing.

### Use concrete language

Prefer “source video,” “upload,” “clip,” “terminal,” and “your computer” over abstract terms such as “content,” “assets,” “solution,” and “ecosystem.”

### Keep one idea per sentence

Break long descriptions into a benefit followed by supporting detail. Cards should normally contain one sentence and stay below 25 words where possible.

### Explain limits where the decision happens

- Near local-first claims, disclose when external providers may receive data.
- Near Cloud pricing, label plans as proposed until generally available.
- Near local-model language, label it as future direction.

### Use parallel construction

Card titles and list items should follow a consistent grammatical pattern. Benefit titles should describe outcomes, not mix features, audiences, and slogans.

### Write calls to action as actions

Use labels that predict the next step:

- `Install Arena`
- `Read the docs`
- `View the roadmap`
- `See Cloud pricing`
- `Join the discussion`

Avoid vague labels such as `Learn more`, `Explore`, or `Get started` when a more specific action is available.

## 5. Terminology

| Use                     | Avoid                                     | Reason                                                     |
| ----------------------- | ----------------------------------------- | ---------------------------------------------------------- |
| AI-powered              | A.I powered                               | Standard spelling and easier scanning                      |
| open-source (adjective) | open Source                               | Standard capitalization and hyphenation                    |
| open source (noun)      | Open Source everywhere                    | Use normal sentence case                                   |
| local-first             | local first (adjective)                   | Consistent product term                                    |
| terminal                | command line, console (interchangeably)   | Keep the primary experience clear                          |
| source video            | content, asset                            | Concrete and recognizable                                  |
| ready-to-publish clips  | viral clips                               | Describes an outcome Arena can deliver                     |
| Instagram Reels         | Reels on first mention                    | Clear platform name                                        |
| YouTube Shorts          | Shorts on first mention                   | Clear platform name                                        |
| Arena Terminal          | Arena CLI when naming the product surface | Separates the product from its implementation              |
| Arena OSS               | free tier                                 | It is a complete standalone product, not a restricted tier |

## 6. Proposed homepage copy

### Hero

**Eyebrow badges**

- Open source
- Local first
- Built for the terminal

**Headline**

> Turn long videos into clips worth sharing.

**Supporting copy**

> Arena finds complete, engaging moments in your videos and exports ready-to-publish clips for TikTok, Instagram Reels, and YouTube Shorts—all from your terminal.

**Primary action**

> Install Arena

**Secondary action**

> View on GitHub

**Installation label**

> Install with npm

### Built for quality

**Heading**

> Find moments that stand on their own.

**Supporting copy**

> Arena looks beyond isolated sound bites. Its four-layer editorial system finds promising moments, restores their context, checks completeness, and removes duplicates.

**Feature cards**

#### Complete moments

> Finds the setup, key idea, and resolution so clips make sense without the original video.

#### Content and delivery

> Combines transcript analysis with audio energy to find ideas delivered with impact.

#### Platform-ready exports

> Formats clips for vertical, square, or horizontal publishing with captions and safe-zone-aware layouts.

#### Files and URLs

> Processes local video and audio files or downloads supported URLs through yt-dlp.

## 7. Proposed local-first section

**Placement:** Immediately after the quality section and before “How it works.”

**Heading**

> Start with the video already on your computer.

**Supporting copy**

> Arena processes your source video locally, so you can begin without waiting for a cloud upload.

### Start without uploading

> Run Arena from your terminal and begin processing immediately. No upfront source-video upload is required.

### Save time and bandwidth

> Skip long uploads and avoid using data just to move a video before processing begins.

### Keep working on unreliable connections

> A dropped connection does not force you to restart a large source-video upload.

### Keep project files on your computer

> Source videos, transcripts, analysis, and generated clips stay on your machine unless you choose an external provider or Arena Cloud.

### Prepare for local AI models

> Arena's architecture creates a path to optional local transcription and analysis models in the future.

### Create or automate

> Creators get a focused clipping workflow. Developers get scriptable commands, inspectable files, and automation-friendly output.

### Accuracy note

“Local first” does not currently mean “fully offline.” Arena processes media locally but may send audio, transcripts, or related inputs to configured AI providers. Documentation must explain each external data flow.

## 8. Proposed “How it works” copy

### 1. Point Arena at a video

> Use a local file or a supported URL.

### 2. Let Arena find complete moments

> Arena transcribes, analyzes, validates, and ranks potential clips.

### 3. Export for your platform

> Generate captioned clips formatted for TikTok, Reels, Shorts, or another supported layout.

## 9. Product and roadmap language

### Arena Terminal — Available now

> The complete open-source, local-first clipping engine and CLI.

### Arena Cloud — Planned

> Optional managed processing, storage, collaboration, automation, and publishing.

### Arena Desktop — Exploring

> A visual local workflow for reviewing clips, adjusting edits, styling captions, and managing projects.

### Arena Mobile — Exploring

> A companion for uploading, monitoring jobs, reviewing clips, approving work, and publishing on the go.

Use “planned” only when work has an accepted product direction. Use “exploring” when scope, demand, or feasibility is still being validated.

## 10. Pricing language

### Arena OSS

> Complete local processing with no Arena usage quota. Bring your own computer and configured AI provider.

### Arena Cloud

> Pay for managed compute and hosted workflows when you need them. Cloud is optional; Arena Terminal remains complete and free.

Until Cloud is generally available, display `Proposed` next to every price and include:

> Arena Cloud is not generally available. Plans, limits, and features may change before launch.

## 11. Error and status copy

Error messages should answer three questions in this order:

1. What failed?
2. What can the user do next?
3. Where can they get more detail?

Example:

> **YouTube could not complete the download.**<br />
> Check your connection, update Arena's runtime with `arena setup --force`, then try again. If YouTube requires authentication, pass cookies from a supported browser.<br />
> Run `arena diagnose` for environment details.

Avoid blaming the user, printing raw stack traces before the explanation, or listing speculative fixes without prioritization.

## 12. Content checklist

Before publishing copy, confirm:

- The first sentence states a user outcome.
- Claims match the current product.
- Planned capabilities are labeled as planned or exploratory.
- Local-first copy acknowledges relevant external providers.
- Headings remain meaningful when scanned without body text.
- Card descriptions are concise and structurally parallel.
- Calls to action name the next step.
- “Viral” is not used as a product guarantee.
- “Arena Terminal,” “Arena Cloud,” “Arena Desktop,” and “Arena Mobile” are used consistently.
- TikTok, Instagram Reels, and YouTube Shorts use their full names on first mention.

## 13. Implementation sequence

No website changes should be made from this draft until its messaging is approved.

After approval:

1. Update the homepage hero and metadata.
2. Rewrite the quality feature section.
3. Replace the current local-first section copy.
4. Update “How it works” and calls to action.
5. Align pricing and roadmap language.
6. Align the GitHub README, npm README, and documentation entry pages.
7. Review mobile layouts, accessibility, metadata, and social previews.
8. Search for obsolete descriptions and unsupported claims before release.
