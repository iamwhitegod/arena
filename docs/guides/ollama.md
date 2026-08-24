# Ollama

Arena can use an Ollama server on the same computer for editorial chat and
embeddings. Ollama does not provide Arena's speech-to-text capability, so a
full `arena process` run must pair it with local or OpenAI transcription.

## Requirements

- Linux, macOS, or Windows supported by Ollama and Arena.
- Ollama installed and running on its default loopback endpoint,
  `http://127.0.0.1:11434`.
- The selected chat and embedding models pulled before processing starts.
- At least 8 GiB RAM for the default small models; 16 GiB RAM and 8 logical
  CPU cores are recommended for more consistent throughput while processing
  video. Larger custom models require correspondingly more RAM or VRAM.

Arena connects only to `localhost`, `127.0.0.1`, or `::1`, ignores proxy
environment variables for Ollama requests, does not send provider credentials,
rejects redirects, and limits request time and response size. Selecting Ollama
does not make transcription local automatically.

## Prepare Ollama

Start the Ollama desktop application or run its server command:

```bash
ollama serve
```

Pull Arena's default models:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```

Arena checks the server and both required models during preflight. A missing
server or model fails before transcription or analysis begins and prints the
command needed to recover.

## Process with local transcription

Install Arena's verified local runtime and speech model pack once:

```bash
arena setup --local --model-pack lite
```

Then use Ollama for analysis and embeddings while keeping transcription local:

```bash
arena process video.mp4 \
  --provider ollama \
  --transcription-provider local
```

Use the `default` Arena pack instead of `lite` on a machine with at least 16
GiB RAM. The selected Arena pack controls the transcription model in this
mixed-provider command; its bundled chat and embedding models are not loaded.

## Process with OpenAI transcription

If `OPENAI_API_KEY` is configured, only the audio transcription is sent to
OpenAI. Editorial transcript text and embeddings remain with the local Ollama
server:

```bash
arena process video.mp4 \
  --provider ollama \
  --transcription-provider openai
```

Arena never falls back from Ollama or local inference to OpenAI automatically.

To persist the mixed profile instead of repeating flags:

```bash
arena config set provider ollama
arena config set transcription_provider local
```

Changing the stored provider clears model names associated with the previous
provider. Set `chat_model` or `embedding_model` afterward when using custom
Ollama tags.

## Analyze an existing transcript

Speech is not needed when an Arena-compatible transcript already exists:

```bash
arena analyze video.mp4 \
  --transcript transcript.json \
  --provider ollama
```

## Select different Ollama models

Pull custom models first and then bind each capability explicitly:

```bash
ollama pull qwen3:8b
ollama pull mxbai-embed-large

arena process video.mp4 \
  --chat-provider ollama \
  --chat-model qwen3:8b \
  --embedding-provider ollama \
  --embedding-model mxbai-embed-large \
  --transcription-provider local
```

The chat model must reliably produce JSON. Arena uses a compact, bounded
editorial path for configured context windows of 16K tokens or less.

## Capability matrix

| Capability | Ollama | Default model |
| --- | --- | --- |
| Editorial chat | Yes | `llama3.2` |
| Overview chat | Yes | Falls back to the chat model |
| Embeddings | Yes | `nomic-embed-text` |
| Transcription | No | Use `local` or `openai` |

`arena transcribe --provider ollama` is intentionally rejected with an
actionable capability error.

## Troubleshooting

### Ollama is not running

Open the Ollama application or run:

```bash
ollama serve
```

Arena deliberately does not start or install an external service on the
user's behalf.

### A model is missing

Run the exact `ollama pull ...` commands printed by Arena's preflight check.
Use `ollama list` to inspect installed tags.

### Inference times out

The Ollama chat budget is three minutes per request. Close memory-intensive
applications, select a smaller chat model, reduce the requested clip count, or
move chat to OpenAI explicitly. Arena does not retry by silently changing
providers.

## Release validation

The regular test suite uses bounded fake HTTP responses. Release candidates
must additionally exercise a real loopback server:

```bash
ARENA_RUN_OLLAMA_TESTS=1 \
python -m pytest engine/tests/integration/test_ollama_runtime_smoke.py
```

Custom release-gate model tags can be selected with
`ARENA_OLLAMA_CHAT_MODEL` and `ARENA_OLLAMA_EMBEDDING_MODEL`.
