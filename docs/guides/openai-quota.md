# OpenAI API Quota Options

If OpenAI reports `insufficient_quota`, either add provider credits or move one or more capabilities to a verified local model. Arena never falls back from local inference to OpenAI automatically.

## Use verified local transcription

Install the hash-locked local runtime dependencies and a verified model pack:

```bash
arena setup --local --model-pack lite
```

Then keep OpenAI for editorial analysis while transcribing locally:

```bash
export OPENAI_API_KEY="your-key"
arena process video.mp4 --transcription-provider local
```

The legacy `ARENA_WHISPER_MODE=local` selector also uses this verified faster-whisper installation. It no longer installs or downloads `openai-whisper` implicitly.

## Add OpenAI credits

Add or update billing in the [OpenAI platform settings](https://platform.openai.com/settings/organization/billing), then run Arena with its default OpenAI profile:

```bash
export OPENAI_API_KEY="your-key"
arena process video.mp4
```

## Fully local inference

After installing a verified Arena model pack, select the local provider for every capability:

```bash
arena process video.mp4 --provider local
```

Local inference uses your machine's CPU, GPU, RAM, and storage. Arena validates model hashes and applies bounded context, thread, output, response, and transcription limits before use.

See [Local inference](local-inference.md) for Linux, macOS, and Windows requirements, model tiers, Silero VAD behavior, and provenance.

## Troubleshooting

- `local_no_model` means the selected verified model is not installed beneath `~/.arena/models` (or `ARENA_MODEL_ROOT`).
- `local_unavailable` means the hash-locked local runtime dependencies are not installed in the Python environment running Arena.
- `model_hash_mismatch` means an artifact is corrupt or differs from Arena's pinned registry metadata; remove that artifact and reinstall it rather than bypassing verification.
- `insufficient_quota` still applies to any capability that remains bound to OpenAI.
