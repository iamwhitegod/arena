# Local inference

Arena's local provider runs the same verified GGUF and CTranslate2 model data on Linux, macOS, and Windows. CPU inference is supported on every platform. Arena enables Metal or another llama.cpp GPU backend only when both the hardware and installed native runtime report support; faster-whisper uses CUDA only when CTranslate2 confirms that CUDA is available.

## Hardware specification

These are Arena capacity policies, not claims from the model publishers. They include room for the video pipeline, model weights, KV cache, transcription, and the operating system.

| Tier | CPU | RAM | Free disk | GPU | Intended pack |
| --- | ---: | ---: | ---: | --- | --- |
| Minimum supported | 4 logical cores | 8 GiB | 8 GiB | Optional | `lite` |
| Recommended for best results | 8 logical cores | 16 GiB | 16 GiB | Optional; 8 GiB VRAM improves throughput | `default` |
| High-quality workstation | 8+ logical cores | 24–32 GiB | 24 GiB | 8+ GiB VRAM or Apple unified memory | `pro` |

Arena detects physical and available RAM, Linux container limits, Apple unified memory and system memory pressure, NVIDIA VRAM, AMD ROCm devices, and Windows display adapters. Unknown GPU capacity stays on CPU. Before loading native code, Arena checks model size, available RAM, full-offload VRAM, context, threads, and disk capacity. The limits are identical across operating systems.

## Install

Install the local native runtimes and the verified pack suited to your machine:

```bash
arena setup --local --model-pack lite
```

Use `default` on the recommended specification and `pro` only on a high-memory workstation. Model downloads are explicit online operations. Every artifact comes from an allowlisted HTTPS host at an immutable revision and is checked against its expected byte count and SHA-256 digest before becoming visible.

`llama-cpp-python` compiles its bundled llama.cpp runtime from source. Arena installs hash-locked CMake, Ninja, and build-backend packages, but the operating system must provide a compiler:

- Linux: GCC or Clang.
- macOS: Xcode Command Line Tools; Apple silicon builds enable Metal.
- Windows: Visual Studio Build Tools with “Desktop development with C++”, or a compatible Clang/GCC toolchain.

Check the installed runtime without changing it:

```bash
arena setup --check --local
```

Then process entirely with the local provider:

```bash
arena process video.mp4 --provider local
```

For local transcription with OpenAI editorial analysis:

```bash
arena process video.mp4 --transcription-provider local
```

Local transcription can take longer than the source audio on CPU-only systems. While faster-whisper is producing segments, Arena shows the current operation and elapsed time rather than inventing a percentage. Its timeout budget is derived from each audio chunk's duration and capped per chunk, so a valid ten-minute CPU transcription is not rejected by the shorter timeout used for chat and embedding calls. Because faster-whisper exposes segments through a native generator, Arena checks this cooperative budget when the generator yields; press Ctrl+C whenever you do not want to keep waiting.

Arena loads speech first, explicitly unloads its native CTranslate2 weights after transcription, and only then loads local chat and embedding models for analysis. This keeps the model families from competing for unified memory and prevents llama/Metal startup messages from appearing as if they belong to transcription.

Local and self-hosted chat models with context windows of 16K tokens or less use Arena's compact editorial path. The model discovers and scores transcript-grounded thought seeds in bounded chunks with a strict JSON grammar; deterministic transcript logic then expands premise/resolution boundaries and computes completeness scores. This avoids applying the cloud pipeline's dozens of per-seed model calls to a compact device model. Cloud-scale models retain the richer multi-pass overview, construction, and validation path.

Each local chat call is also bounded by the installed pack's verified context size and a tier-scaled output limit. Arena consumes llama.cpp's native token stream so cancellation and timeout checks occur outside native callbacks. A local timeout is not retried with the same deterministic prompt.

## Verified packs

| Pack | Chat | Context | Embedding | Speech | Minimum RAM |
| --- | --- | ---: | --- | --- | ---: |
| `lite` | Qwen3.5 2B Q4_K_M | 4K | Nomic Embed Text v1.5 Q4_K_M | Faster Whisper base | 8 GiB |
| `default` | Qwen3.5 4B Q4_K_M | 8K | Nomic Embed Text v1.5 Q4_K_M | Faster Whisper small | 12 GiB |
| `pro` | Qwen3.5 9B Q4_K_M | 12K | Nomic Embed Text v1.5 Q4_K_M | Faster Whisper medium | 24 GiB |

The GGUF files are portable data and do not contain executable model-repository code. Speech packs contain CTranslate2 model data. Arena never enables `trust_remote_code`, never loads pickle model files, and prevents faster-whisper from downloading aliases implicitly.

Faster-whisper's bundled Silero VAD is enabled with bounded Arena parameters for every local transcription. Pyannote is not part of Phase 2: speaker diarization requires a separate speaker-aware result contract, PyTorch runtime, and commonly gated model credentials. It will not be pulled into local transcription implicitly.

## Provenance and licenses

All packs use Apache-2.0 Qwen and Nomic model data plus MIT-licensed Whisper/CTranslate2 conversions. Exact upstream repositories, quantizers, revisions, artifact sizes, and SHA-256 digests are maintained in `engine/arena/models/registry.py`. Any revision or digest change is a security-sensitive release change.

## Release validation

Deterministic tests exercise platform detection, memory/VRAM pressure, cancellation, timeout, download redirects, size limits, hashes, and schema bounds. A release candidate with installed models must also run:

```bash
ARENA_RUN_LOCAL_INFERENCE_TESTS=1 \
ARENA_LOCAL_MODEL_PACK=lite \
python -m pytest engine/tests/integration/test_local_runtime_smoke.py
```

That gate loads the real llama.cpp and faster-whisper runtimes, produces constrained chat JSON and embeddings, and transcribes synthetic audio with Silero VAD enabled.
