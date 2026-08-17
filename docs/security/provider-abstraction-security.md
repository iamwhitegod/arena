# Provider Abstraction Security Requirements

**Status:** Required design and release gates  
**Applies to:** Provider abstraction, mixed-provider execution, local inference, and `--offline`  
**Related documents:** [Provider abstraction plan](../architecture/provider-abstraction-plan.md), [Arena OSS threat model](threat-model.md), [Data and privacy](data-and-privacy.md)

## Purpose

Arena's provider abstraction introduces new boundaries around credentials, user media, transcripts, model output, local model files, network access, and native inference runtimes. These requirements must be implemented and tested before the relevant phase is considered complete.

The governing security objectives are:

- keep credentials, media, transcripts, and generated artifacts confidential;
- preserve explicit user control over provider selection and network access;
- treat media, prompts, model responses, provider errors, URLs, and model files as untrusted;
- prevent provider configuration or model output from escaping process and filesystem boundaries;
- make provider/model provenance inspectable without recording secrets.

## Phase 1 release gates

### 1. Credential isolation

Provider credentials must be available only to the code that requires them.

Required controls:

- Never place credentials in command-line arguments, `RuntimeProfile`, `ModelBinding`, provider options, checkpoints, logs, diagnostics, or artifacts.
- Resolve credentials only while constructing a provider adapter.
- Reject secret-like fields in provider configuration and `ModelBinding.options`.
- Ensure provider objects do not reveal credentials through `repr()`, serialization, or exception messages.
- Pass only required provider credentials into the managed Python process.
- Scrub API keys, tokens, authorization values, cookies, and unrelated secrets from FFmpeg, ffprobe, yt-dlp, and other non-provider subprocess environments.
- Continue enforcing owner-only permissions for Arena credential files and directories.

The current process boundary requires special attention: the TypeScript bridge passes its environment to Python, and Python subprocesses inherit their parent's environment by default. Provider keys must not propagate to media tools merely because they share a process tree.

### 2. Safe errors, logs, and diagnostics

Provider SDK exceptions may contain request bodies, endpoints, headers, transcript fragments, or raw provider responses.

Required controls:

- Public errors contain only a stable code, safe message, retryability, and diagnostic correlation ID.
- Native exceptions may be retained as an internal cause, but CLI and debug formatting must not print or serialize the cause chain.
- Redact credentials, cookies, authorization headers, token-shaped values, and configured secret fields recursively.
- Do not persist complete prompts, transcripts, audio, or raw provider responses in logs.
- Any prompt/response debug mode must be explicit, local-only, disabled by default, and display a privacy warning.
- Do not expose absolute local paths or native provider errors in portable artifacts or worker payloads.

### 3. Explicit data disclosure

Audio and transcript transmission must follow the user's resolved provider profile.

Required controls:

- Never fall back from a local provider to a cloud provider automatically.
- Make the resolved provider and model for chat, overview chat, embeddings, and transcription inspectable before processing.
- Document which data each capability sends and where it is sent.
- Send only the minimum audio or transcript content needed for the operation.
- Treat custom base URLs, proxies, and provider endpoint overrides as explicit disclosure destinations.
- Do not send credentials, environment variables, unrelated file content, or local paths in prompts.
- Document provider-side retention and deletion as the provider's responsibility.

### 4. Provider-neutral configuration safety

Provider names and options are an untrusted configuration boundary.

Required controls:

- Strictly allowlist provider names and supported options for each adapter.
- Do not dynamically import arbitrary Python modules from a provider string.
- Validate model identifiers, endpoints, paths, numeric limits, context sizes, and concurrency settings.
- Keep injectable provider factories internal and use them only for composition and testing.
- Require TLS certificate verification for remote providers.
- Document and surface proxy behavior that may route provider traffic through another host.
- Prevent options dictionaries from accepting credentials or authorization headers.

### 5. Prompt injection and untrusted output

Media text and metadata can contain adversarial instructions. Model output is untrusted data, not authority.

Required controls:

- Never execute model output as shell commands, code, SQL, configuration, or authorization decisions.
- Never use model output as a URL to fetch or as an unrestricted filesystem path.
- Validate structured output against bounded domain schemas after provider-level JSON extraction.
- Validate required fields, types, maximum lengths, array sizes, timestamp ranges, finite numbers, and ordering.
- Validate embedding counts, dimensions, and finite values before similarity calculations.
- Constrain transcription words and segments to valid media time ranges.
- Strip ANSI escapes and unsafe control characters before printing model or media text to a terminal.
- Sanitize and bound any generated text used in a filename.
- Treat a structured response that cannot be parsed as a typed provider response error.

### 6. Resource, retry, and cost controls

Untrusted inputs must not cause unbounded local resource consumption or paid API usage.

Required controls:

- Set request timeouts, cancellation behavior, prompt-size limits, output-token limits, and response-size limits.
- Clamp effective concurrency to an Arena-controlled maximum; a provider's `concurrency_hint` is advisory.
- Bound retry count, total retry time, and accepted `Retry-After` values.
- Add jitter to concurrent cloud retry backoff.
- Do not retry authentication, invalid-request, permission, or local OOM errors by default.
- Count malformed structured-output retries against the same retry and cost budget.
- Support per-run limits for provider calls, tokens, audio duration, and estimated spend.
- Stop scheduling new calls after cancellation or budget exhaustion.
- Treat provider-reported usage as operational metadata, not trusted billing evidence.

### 7. Cache and checkpoint isolation

Provider/model changes must not silently reuse incompatible inference results.

Required controls:

- Include provider, model, prompt/schema version, and output-affecting options in cache identity.
- Validate cached artifacts against their declared schemas before use.
- Record provider/model and engine provenance without secrets.
- Keep project caches private and contained beneath approved roots.
- Reject cache and checkpoint symlinks, path traversal, oversized parsed data, and unexpected file types.
- Prevent one project or provider profile from reading another project's cached results accidentally.

### 8. Capability-aware construction

Commands must construct only the provider capabilities they use.

Required controls:

- `arena transcribe` must not initialize chat or embedding providers.
- Analysis with an existing transcript must not initialize a speech provider.
- Credential validation must apply only to required capabilities.
- Unused local models must not be loaded into RAM or VRAM.
- Unused cloud adapters must not create clients or network connections.

## `--offline` security contract

`--offline` is an enforced no-egress policy, not a provider alias.

Required controls:

- Reject every required binding that is not local.
- Reject URL inputs before invoking yt-dlp.
- Disable cloud audio enhancement, remote fallbacks, telemetry, update checks, and model downloads.
- Fail with an actionable error when a required local model is missing.
- Test all offline operations with DNS and socket access blocked.
- Assert that no provider, updater, downloader, or dependency manager attempts a connection.
- Do not claim that Arena disabled network access unless it enforces an operating-system or sandbox network boundary. Otherwise state that no network-dependent operations were selected.

Model installation remains an explicit online operation performed before an offline run. Offline model bundles may be supported separately.

## Phase 2: local model and runtime security

Local inference adds model-file, dependency, native-code, and resource-exhaustion risks.

Required controls:

- Download models only from allowlisted sources and immutable revisions.
- Publish expected SHA-256 hashes and verify them before loading a model.
- Use atomic downloads and reject incomplete files, symlinks, and path traversal.
- Store models beneath the configured Arena model root with private, validated paths.
- Prefer non-executable data formats such as GGUF and safetensors.
- Do not load pickle-based model artifacts.
- Keep Hugging Face `trust_remote_code` disabled.
- Do not execute model-repository scripts or downloaded binaries implicitly.
- Lock and hash llama.cpp, faster-whisper, CTranslate2, and related dependencies.
- Pin and verify any separately distributed native runtime binary.
- Enforce model-size, context-window, RAM, VRAM, CPU, thread, and inference-time limits.
- Treat Ollama and other loopback services as untrusted network peers: set timeouts, limit response sizes, validate responses, and do not send credentials intended for another provider.
- Document licenses and provenance for every model pack.
- Apply the same minimum/recommended capacity policy on Linux, macOS, and Windows; unknown capacity must select the conservative CPU path.
- Enable only bundled, data-only Silero VAD through faster-whisper. Do not add pyannote until speaker-aware contracts and its separate runtime/model trust boundary are reviewed.

## Filesystem and media-tool boundaries

Provider work must preserve Arena's existing protections for untrusted media and paths.

Required controls:

- Continue invoking FFmpeg, ffprobe, yt-dlp, and model tools with argument arrays and without a shell.
- Apply time, file-size, bandwidth, and output-count limits to URL downloads.
- Resolve output, cache, and model paths beneath approved roots and reject symlink escapes.
- Use private temporary directories and deterministic cleanup targets.
- Require marker/version checks before recursive cleanup.
- Do not use model-generated values to choose cleanup targets.
- Process high-risk media in the existing unprivileged container or another operating-system sandbox when practical.

## Future Arena Cloud requirements

The OSS provider abstraction must not be reused as an implicit Cloud security boundary. Before Cloud processing:

- block private, loopback, link-local, metadata-service, and reserved destination addresses;
- revalidate DNS and every redirect to prevent SSRF and DNS rebinding;
- isolate jobs by tenant and inject secrets from a dedicated secret system;
- enforce CPU, memory, time, network, and storage limits;
- use short-lived, tenant-scoped artifact transfers;
- keep provider exceptions, credentials, and local paths out of public job payloads;
- enforce idempotency so retries cannot duplicate outputs or charges;
- treat worker-reported usage as untrusted until validated;
- pin the engine image/release and record schema, engine, provider, and model provenance.

## Mandatory security tests

Phase 1 is not complete until automated tests prove that:

- canary API keys, tokens, cookies, and authorization headers never appear in logs, tracebacks, events, artifacts, or non-provider child environments;
- provider profiles and options reject credentials, unknown fields, unsafe endpoints, and invalid paths;
- no local-to-cloud fallback occurs;
- structured-output and prompt-injection fixtures cannot trigger shell, filesystem, network, or configuration actions;
- malformed, oversized, deeply nested, non-finite, and schema-invalid provider responses fail safely;
- retries, concurrency, output size, and cost remain bounded;
- cancellation prevents new provider calls;
- provider/model changes invalidate incompatible checkpoints;
- only required capabilities are constructed;
- deterministic fake providers produce the same results across processes;
- model, cache, and output paths reject traversal and symlink escape;
- offline tests produce no DNS or socket attempt;
- public errors contain no raw provider exception, transcript content, local path, or secret.

Phase 2 additionally requires tests proving that:

- corrupted or incorrectly hashed models are rejected before loading;
- model paths cannot escape the Arena model root;
- remote model code and unsafe serialization are disabled;
- local runtime resource limits and cancellation work under memory and timeout pressure;
- loopback providers cannot return unbounded or schema-invalid responses.

## Release checklist

- [x] Threat model updated for provider abstraction and local model execution.
- [ ] Credential flow and subprocess environment boundaries reviewed.
- [ ] Provider data disclosures documented.
- [ ] Safe error catalog and redaction tests complete.
- [ ] Prompt/output schemas and bounds documented.
- [x] Retry, timeout, cancellation, concurrency, and cost limits tested.
- [ ] Cache identity includes provider/model/prompt provenance.
- [ ] Required-capability construction tested.
- [ ] Offline network-denial suite passes.
- [x] Dependency locks, hashes, SBOM, and provenance updated.
- [x] Local model sources, hashes, formats, and licenses reviewed before Phase 2 release.
