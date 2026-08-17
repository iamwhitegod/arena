# Current artifact inventory

**Status:** Gate 1 inventory; observed implementation, not a stable contract

**Last reviewed:** August 13, 2026

This document inventories the data Arena currently persists or emits across the TypeScript CLI and Python engine. It is the evidence base for the versioned contracts proposed in [Repository boundary](../cloud/repository-boundary.md).

Nothing listed here is a public wire contract today. **Current stability** describes what consumers may rely on now; **boundary disposition** recommends what should happen later. A “portable candidate” therefore remains internal and unversioned until a schema, compatibility policy, fixtures, and tests are published under `schemas/`.

## Scope and execution paths

The active Node-to-Python path is:

```text
CLI command
  -> PythonBridge
  -> python -m arena.cli.main <command>
  -> arena.cli.commands.<command>
```

For `arena process`, `arena.cli.commands.process.run_process()` wraps the active `engine/arena_process.py` pipeline with `PipelineEventStream`. `engine/arena/main.py` is a separate legacy process entry point. Its `metadata.json`, `transcript.json`, and result payload are inventoried below, but they must not be mistaken for the active bridge behavior.

The inventory covers durable local state, output files, caches that cross process boundaries, and machine-readable stdout. Temporary files that exist only during one function call are excluded. Human-readable terminal output and rotating logs are presentation/diagnostic streams rather than structured artifacts; they remain internal and must never be parsed as contracts.

## Inventory summary

| Family                             | Producer and consumer                                                       | Location or channel                                         | Current stability                                               | Data class                                       | Boundary disposition                                     |
| ---------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------- | --------------------------------------------------------------- | ------------------------------------------------ | -------------------------------------------------------- |
| Global configuration               | `ConfigManager`; CLI setup, config, preflight, and process commands         | `~/.arena/config.json`                                      | Internal, unversioned                                           | Operational; may contain a legacy secret         | Keep local; define a separate portable project model     |
| Credential store                   | `ConfigManager`; API-key resolution                                         | `~/.arena/credentials.json`                                 | Internal, versioned locally                                     | Secrets                                          | Never portable                                           |
| Project configuration              | `ConfigManager.createProjectConfig()`; project commands                     | `<project>/.arena/config.json`                              | Internal, unversioned                                           | Operational + source locator                     | Replace paths with opaque identity in any Cloud model    |
| Workspace marker/cache             | `Workspace`; CLI lifecycle                                                  | `<project>/.arena/`                                         | Internal; marker version `1`                                    | Operational + local paths                        | Keep marker internal; validate cache payloads separately |
| Runtime manifest                   | setup/runtime helpers                                                       | `~/.arena/runtime/install.json`                             | Internal; schema version `1`                                    | Operational + absolute executable path           | Local only                                               |
| Download and audio cache           | downloader, transcriber, enhancer; pipeline reuse                           | `~/.arena/cache/downloads/`, `<output>/.cache/`             | Internal, filename-convention based                             | Raw media                                        | Never metadata-sync by default                           |
| Transcript                         | `Transcriber` and command/pipeline writers; analyzer and subtitle generator | requested output, `<output>/transcript.json`, cache         | Internal, unversioned                                           | Media-derived                                    | Portable candidate after normalization/versioning        |
| Analysis export and clip candidate | `HybridAnalyzer.export_results()`; generator and reviewers                  | requested analysis JSON or `<output>/analysis_results.json` | Internal, unversioned                                           | Content-derived + operational                    | Portable candidate with internal fields removed          |
| Editorial debug exports            | `FourLayerAdapter.export_layer_outputs()`; developers                       | `<output>/editorial/*.json`                                 | Internal, unversioned, currently not invoked by active pipeline | Content-derived                                  | Keep debug-only                                          |
| Editorial checkpoints              | `CheckpointManager`; `FourLayerAdapter` resume path                         | `.checkpoint/*.json` relative to engine working directory   | Internal, unversioned                                           | Content-derived + operational                    | Keep internal                                            |
| Scene detection                    | `run_detect_scenes()`; CLI/user                                             | requested JSON and optional sibling text report             | Internal; metadata label `1.0` only                             | Content-derived + local path                     | Possible future analysis sub-artifact                    |
| Clip metadata                      | clip generator and process/generate commands; user/formatter                | `<clips>/*_metadata.json`                                   | Internal, unversioned, multiple variants                        | Content-derived + paths                          | Portable candidate after convergence                     |
| Media outputs                      | downloader, extractor, generator, formatter, caption burner                 | requested output, `clips/`, `formatted/`, `captioned/`      | File-format contracts only                                      | Raw media                                        | Transfer only with explicit media consent                |
| Subtitles                          | `SubtitleBurner.generate_srt()`; caption burner/formatter                   | `<clips>/<clip-id>.srt`                                     | Internal SRT convention                                         | Media-derived                                    | Portable media candidate with retention disclosure       |
| Thumbnails                         | `ClipGenerator.generate_thumbnail()`; user/metadata                         | `<clips>/*_thumb.jpg`                                       | Internal JPEG convention                                        | Media-derived                                    | Portable media candidate with explicit selection         |
| Format result                      | `PlatformFormatter`; format/process commands                                | In memory, then summarized over result protocol             | Internal, unversioned                                           | Operational + local paths                        | Do not publish unchanged                                 |
| CLI protocol and command results   | Python command handlers; `PythonBridge.runCommand()`                        | stdout JSON Lines                                           | Internal, unversioned                                           | Operational, sometimes paths/errors              | Replace durable use with versioned job events/results    |
| Diagnostics                        | `diagnoseCommand()`; user/support                                           | `<cwd>/arena-diagnostics.txt`                               | Internal text format                                            | Operational; may expose environment/path details | Local/support only; redact before sharing                |
| Legacy exporter output             | `engine/arena/main.py` and `Exporter`; legacy consumers                     | `<output>/metadata.json`, `<output>/transcript.json`        | Deprecated integration path                                     | Mixed                                            | Migrate or remove before publishing contracts            |

## Local configuration and state

### Global configuration

- **Producer:** `ConfigManager.ensureGlobalConfig()`, `updateGlobalConfig()`, and the `init`/`config` commands.
- **Consumer:** CLI defaults and process options.
- **Representative shape:** keys include `whisper_mode`, `clip_duration`, `output_format`, `subtitle_style`, and wizard-written keys such as `workflow`, `minDuration`, `maxDuration`, `editorialModel`, `numClips`, and `padding`.
- **Observed risks:** there is no schema version and naming already mixes snake_case with camelCase. `openai_api_key` is a deprecated legacy field that is migrated to the credential store when read.
- **Recommendation:** keep this user preference file local. Do not turn its open-ended object directly into `arena.project/v1`.

### Credential store

```json
{
  "version": 1,
  "openai_api_key": "<secret>"
}
```

- **Producer/consumer:** `ConfigManager.setOpenAIApiKey()`, `readCredentials()`, and `resolveOpenAIApiKey()`.
- **Protection:** written with owner-only directory/file modes where supported.
- **Observed risks:** it contains a live secret; the local `version` is a storage-format version, not a public artifact schema.
- **Recommendation:** never include this file or any field from it in project artifacts, fixtures, telemetry, or Cloud requests.

### Project configuration

```json
{
  "video_path": "/absolute/path/or/source-url",
  "created_at": "2026-08-13T09:00:00.000Z",
  "preferences": {
    "clip_count": 10,
    "focus_topics": []
  }
}
```

- **Producer:** `ConfigManager.createProjectConfig()` in `processCommand()`.
- **Consumer:** `ConfigManager` project reads/updates; current processing does not use it as a portable request.
- **Observed risks:** source locations may reveal usernames, directories, or private URLs; there is no project ID or schema version.
- **Recommendation:** a future project contract should use an opaque ID and explicit source references. It should not serialize local paths by default.

### Workspace marker and generic cache

```json
{
  "schemaVersion": 1,
  "root": "/absolute/path/to/project/.arena"
}
```

- **Producer/consumer:** `Workspace.initialize()` and `Workspace.clean()`.
- **Location:** `.arena/.arena-workspace.json`; `.arena/cache/` may contain arbitrary JSON written through `Workspace.saveCache()`.
- **Observed risks:** `root` is absolute; the marker version protects cleanup safety only. Generic cache values have no common shape.
- **Recommendation:** keep the marker and cache internal. Portable artifacts stored in the cache must be validated by their own schemas.

### Runtime manifest

```json
{
  "schemaVersion": 1,
  "cliVersion": "<package-version>",
  "pythonPath": "/absolute/path/to/python",
  "pythonVersion": "3.12.4",
  "installedAt": "2026-08-13T09:00:00.000Z"
}
```

- **Producer:** setup promotion through `writeRuntimeManifest()`.
- **Consumer:** runtime resolution, setup checks, diagnostics, and dependency checks.
- **Observed risks:** contains an absolute executable path and describes one installation rather than project content.
- **Recommendation:** local-only. Cloud provenance should record an immutable engine release/image digest instead.

## Processing artifacts

### Transcript

```json
{
  "text": "full transcript",
  "language": "en",
  "duration": 566.6,
  "words": [{ "word": "Hello", "start": 0.0, "end": 0.42 }],
  "segments": [{ "id": 0, "start": 0.0, "end": 4.2, "text": "Hello ..." }]
}
```

- **Producer:** `Transcriber._transcribe_with_provider()` and `_transcribe_chunked()` normalize provider responses to this Arena subset. Command and pipeline functions perform the JSON writes.
- **Consumer:** hybrid/editorial analysis, subtitle generation, cache reuse, and users.
- **Locations:** command-selected transcript path; active process cache `<output>/.cache/<source-stem>_transcript.json`; copied output `<output>/transcript.json`; the legacy engine uses `<output-parent>/cache/transcript.json` and `Exporter.export_transcript()`.
- **Current stability:** internal and unversioned.
- **Field sensitivity:** `text`, `words`, and `segments` are media-derived; `language` and exact `duration` are also media-derived. A future envelope’s schema/producer/timestamp fields would be operational.
- **Observed risks:** cache/output naming differs between entry points; word and segment availability can vary by provider; there is no declared producer/model/version.
- **Recommendation:** portable candidate. Specify nullability/optional arrays, timestamp precision, ordering, provider normalization, and upgrade rules.

### Analysis export and editorial clip

The on-disk shape written by `HybridAnalyzer.export_results()` is not the same as the larger in-memory value returned by `analyze_video()`:

```json
{
  "clips": [
    {
      "id": "clip_001",
      "start_time": 60.0,
      "end_time": 120.0,
      "duration": 60.0,
      "title": "...",
      "reason": "...",
      "interest_score": 0.88,
      "content_type": "insight",
      "_4layer_metadata": {
        "completeness_score": 0.88,
        "standalone_score": 9.0,
        "premise_clarity": 8.0,
        "claim_strength": 9.0,
        "resolution_closure": 7.5,
        "rhetorical_type": "insight",
        "premise_text": "...",
        "claim_text": "...",
        "resolution_text": "..."
      },
      "hybrid_score": 1.0,
      "energy_boost": 0.2,
      "max_energy": 0.9,
      "avg_energy": 0.5,
      "overlap_ratio": 0.8,
      "overlapping_segments": 3,
      "has_high_energy": false
    }
  ],
  "stats": {},
  "config": {},
  "metadata": {
    "total_ai_clips": 10,
    "total_energy_segments": 20
  }
}
```

- **Producer:** `FourLayerAdapter.analyze_transcript()` creates editorial clips; `HybridAnalyzer._compute_hybrid_scores()` augments them; `HybridAnalyzer.export_results()` selects the persisted fields.
- **Consumer:** `arena generate`, the active process pipeline, reviewers, and tests.
- **Current stability:** internal and unversioned; portable candidate after redesign.
- **Field sensitivity:** titles, reasons, timings, types, scores, and all editorial text are content-derived. Counts/configuration are operational but may still reveal workflow choices.
- **Observed risks:** `_4layer_metadata` is labeled internal but persisted. The in-memory `ai_clips` and `energy_segments` arrays are deliberately replaced by counts on export. `alignment_stats` is added to the in-memory result by the process pipeline but is not included by `export_results()`. Score scales are not consistently obvious from names alone.
- **Recommendation:** define a stable clip object, named editorial extension, explicit score ranges, and a deliberate choice about whether alignment and energy detail are public.

### Editorial debug exports and checkpoints

`FourLayerAdapter.export_layer_outputs()` can write:

```text
<output>/editorial/week1_seeds.json
<output>/editorial/week2_units.json
<output>/editorial/week3_scored.json
<output>/editorial/week4_deduplicated.json
```

These files contain layer-specific lists with transcript text, timing, rhetorical labels, validations, and scores. The active process option populates `layer_outputs`, but no active call to `export_layer_outputs()` was found, so the documented export option does not currently complete the write. Treat the shapes as internal debug structures.

`CheckpointManager` writes atomic checkpoint files under `.checkpoint/` relative to the engine working directory:

```json
{
  "job_id": "a1b2c3d4e5f6_two_pass_v1",
  "stage": "seed_detection",
  "timestamp": "2026-08-13T10:00:00.123456",
  "data": [],
  "metadata": { "count": 10 }
}
```

- **Current persisted stages:** `seed_detection` and `construction` only.
- **Identifier:** the first 12 hex characters of an MD5 of the first 500 transcript characters, plus `_two_pass_v1` in the adapter.
- **Observed risks:** the identifier is content-derived, collision-prone, and not suitable as a Cloud job ID; `datetime.now().isoformat()` does not assert UTC; stage payloads expose transcript-derived text and internal types. Successful runs clear their checkpoints.
- **Recommendation:** keep checkpoints internal. A Cloud idempotency key and durable job event are separate contracts.

### Scene detection

```json
{
  "video_path": "/local/path/video.mp4",
  "threshold": 0.4,
  "min_scene_duration": 2.0,
  "scene_count": 2,
  "avg_scene_duration": 12.5,
  "scenes": [{ "time": 10.5, "score": 0.4, "type": "scene_change" }],
  "metadata": { "detection_method": "ffmpeg_scene_filter", "version": "1.0" }
}
```

- **Producer/consumer:** `run_detect_scenes()` writes the requested JSON; the user/CLI consumes it. `--report` adds a sibling `*_report.txt` and path fields to the emitted result after the JSON has already been written.
- **Current stability:** internal. `metadata.version` labels the detector output but is not a repository-wide schema contract.
- **Sensitivity:** scene timestamps are content-derived; the absolute video/report paths are operational and identifying.
- **Recommendation:** if promoted, remove local paths, define whether the score is measured or configured, and make report linkage explicit.

## Clip and media artifacts

### Clip metadata variants

The common fields across generator paths are:

```json
{
  "output_path": "/absolute/path/clip.mp4",
  "start_time": 60.0,
  "end_time": 120.5,
  "duration": 60.5,
  "size_bytes": 5242880,
  "size_mb": 5.0,
  "success": true,
  "clip_id": "title_001_01m00s-02m00s",
  "clip_filename": "title_001_01m00s-02m00s.mp4",
  "title": "...",
  "index": 1,
  "segment": {},
  "scores": {}
}
```

- **Producer:** `ClipGenerator.generate_multiple_clips()`, the active process metadata loop, standalone `run_generate()`, and the library helper `generate_clip_with_metadata()`.
- **Consumer:** users, formatters, and downstream publishing workflows.
- **Current stability:** internal, unversioned, and divergent.
- **Observed variants:** re-encoded results include requested times, padding, codec, and CRF; fast results include `method`. The active process adds `clip_number`, description, content type, three scores, and a relative thumbnail filename. Standalone generate writes a different score object. `generate_clip_with_metadata()` uses absolute thumbnail paths; it adds `metadata_file` only after writing the JSON, so the returned and persisted values differ.
- **Sensitivity:** timing, title, description, nested segment, and scores are content-derived; paths and encoding details are operational; the referenced clip/thumbnail are media-derived/raw media.
- **Recommendation:** converge writers before publishing `arena.clip/v1`; use artifact IDs and relative manifest references instead of host paths.

### Binary media, subtitles, and thumbnails

| Artifact                  | Observed locations/formats                                           | Sensitivity                               | Recommendation                                                     |
| ------------------------- | -------------------------------------------------------------------- | ----------------------------------------- | ------------------------------------------------------------------ |
| URL download cache        | `~/.arena/cache/downloads/<url-hash>.*`                              | Raw media; filename hash derives from URL | Local cache only; never infer upload consent from presence         |
| Extracted/enhanced audio  | requested output and `<output>/.cache/*_audio.mp3`, `*_enhanced.wav` | Raw media                                 | Explicit remote-processing selection only                          |
| Generated clips           | `<output>/clips/*.mp4`                                               | Raw media                                 | Address by artifact ID/hash in portable manifests                  |
| Formatted/captioned clips | `<output>/formatted/*.mp4`, `<output>/captioned/*.mp4`               | Raw media                                 | Same consent/retention requirements as source media                |
| Subtitles                 | `<output>/clips/*.srt`                                               | Media-derived text                        | Separate selectable artifact; UTF-8/SRT behavior must be specified |
| Thumbnails                | `<output>/clips/*_thumb.jpg`                                         | Media-derived image                       | Separate explicit selection and retention disclosure               |

## Runtime results and diagnostics

### Platform formatter result

`PlatformFormatter.format_for_platform()` returns an in-memory object containing `success`, platform, absolute `output_path`, source/output dimensions, file sizes, target spec, and warnings. Batch mode adds `clip_index` and `original_clip`, or an error object. The CLI result protocol reduces this to `success`, `clipCount`, `outputDir`, and `warnings`.

This is internal operational state, not an on-disk metadata contract. If formatting provenance becomes portable, it should record a normalized preset/version and output artifact ID rather than local paths or free-form warnings.

### CLI progress and result protocol

The protocol is one JSON object per stdout line:

```json
{ "type": "progress", "stage": "analysis", "progress": 45, "message": "Scoring candidate moments" }
{ "type": "result", "data": {} }
```

- **Producer:** `arena.cli.protocol`, command-specific handlers, and `PipelineEventStream` for the active process pipeline.
- **Consumer:** `PythonBridge.runCommand()` dispatches progress callbacks and retains the latest result payload.
- **Current stability:** internal and unversioned. Stage vocabulary differs across commands (`transcription`, `analysis`, `alignment`, `generation`, `formatting`, `detection`, and `extraction`).
- **Observed risks:** messages and errors are free text; the bridge treats any JSON-looking line as a possible protocol object; there is no event ID, sequence, timestamp, schema version, stable error code, or cancellation state.

Command result payloads also drift between snake_case and camelCase:

| Command         | Representative result fields                                                                         |
| --------------- | ---------------------------------------------------------------------------------------------------- |
| `process`       | `success`, `outputDir`                                                                               |
| `transcribe`    | `success`, `cached`, `duration`, `wordCount`, `language`, `outputFile`                               |
| `analyze`       | `success`, `videoDuration`, `wordCount`, `momentsFound`, `estimatedClips`, `outputFile`              |
| `generate`      | `success`, `clips`, `failed`, `totalSizeMb`, `outputDir`                                             |
| `extract-audio` | `success`, `audioPath`, `fileSize`                                                                   |
| `format`        | `success`, `clipCount`, `outputDir`, `warnings`, or `error`                                          |
| `detect-scenes` | persisted snake_case fields plus `sceneCount`, `avgSceneDuration`, and optional `reportPath` aliases |

`info --json` prints a bare video-info object directly rather than a protocol result. The legacy `engine/arena/main.py` process path emits `clips`, `metadata_path`, `transcript_path`, and `success`, which is another incompatible variant. Its installed `arena-engine=arena.main:main` console entry point is deprecated for new integrations: it remains for one announced compatibility window, will be replaced by the Gate 3 worker entry point, and will then be removed in the next breaking release.

**Recommendation:** keep terminal progress internal. Define `arena.job-event/v1`, `arena.job-request/v1`, and `arena.job-result/v1` separately, with stable states/error codes and sanitized artifact references.

### Diagnostics report

`diagnoseCommand()` writes `arena-diagnostics.txt` in the current directory. It includes generation time, OS/release/architecture, Node version, dependency and API-key status, disk/storage checks, configuration locations, messages, and suggested fixes.

The format is internal human-readable text. Although it does not intentionally print the API key, it can expose machine details and absolute paths. It should be redacted and explicitly reviewed before a user shares it; it must not become implicit telemetry.

## Gate 1 conclusions

1. Arena has local format versions for the workspace marker, credential store, and runtime manifest, plus a detector metadata version. None is a portable repository-boundary schema.
2. The strongest portable candidates are a newly sanitized project descriptor, transcript, analysis/clip objects, selected media manifests, and durable job request/result/event envelopes.
3. Absolute paths, mixed naming conventions, free-form errors, writer-specific clip variants, and persisted internal editorial text must be resolved before schema publication.
4. Secrets remain in the credential system only. Raw and media-derived artifacts require consent distinct from metadata sync and telemetry.
5. Checkpoints, generic caches, runtime/configuration files, formatter return objects, diagnostics, and human terminal output remain internal.

## Related documents

- [Repository boundary](../cloud/repository-boundary.md)
- [Repository boundary implementation plan](../development/plans/repository-boundary-implementation.md)
- [CLI and Python bridge architecture](../architecture/cli.md)
- [Data and privacy](../security/data-and-privacy.md)
