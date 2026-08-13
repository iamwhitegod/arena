# Arena OSS Data and Privacy

Arena OSS is local-first and does not require an Arena account. The OSS CLI contains no Arena-operated telemetry or analytics pipeline.

## What stays local

Source media, downloaded media, transcripts, analysis checkpoints, clips, configuration, credentials, and logs are stored on the user's machine unless a command explicitly sends content to an external provider or URL host. Arena Cloud is not required for the local workflow.

Default locations include:

- global settings: `~/.arena/config.json`;
- credentials: `~/.arena/credentials.json`;
- logs: `~/.arena/logs/`;
- managed Python runtime: `~/.arena/runtime/`;
- project cache and output: `.arena/` beneath the project.

`ARENA_HOME` can relocate global Arena state. Project output paths can be selected per command.

## Network connections

Arena may connect to:

- the AI/model provider configured by the user; OpenAI transcription uploads audio and editorial analysis uploads relevant transcript text;
- URLs and related CDN/API hosts requested through yt-dlp;
- npm and PyPI during installation or dependency repair;
- operating-system package repositories when the user approves system dependency installation.

Arena OSS does not send media, transcripts, usage events, or credentials to Arena-operated servers. A future optional Arena Cloud client must identify itself clearly and document each Cloud data flow before release.

## Retention and deletion

Arena does not impose a remote retention period because OSS data is local. Users control retention through their filesystem and provider account. To remove local project data, delete that project's `.arena/` directory and chosen output directories. To remove global Arena state, delete the configured `ARENA_HOME` directory after confirming the exact path. Provider-side copies must be managed through the provider's controls.

Logs rotate locally and are intended for troubleshooting. They are redacted defensively, but users should still review logs before sharing them. Never attach credentials, cookies, private media, or full transcripts to a public issue.

## Cookies and third-party content

`--cookies-from-browser` gives yt-dlp access to browser cookies for the selected browser. Use it only on a trusted machine, for content you are authorized to access, and avoid sharing resulting logs or downloaded metadata. Users are responsible for site terms, copyright, consent, and applicable law.
