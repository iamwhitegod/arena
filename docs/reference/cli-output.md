# CLI output and states

Arena uses one output language across all commands. The Node.js CLI owns terminal presentation; the Python engine emits structured events and does not print subsystem banners or third-party warnings during successful runs.

## State symbols

| Symbol | State | Meaning |
|---|---|---|
| `○` | Pending | The stage has not started. |
| `◐` | Running | Work is active. A percentage is shown when the engine can measure it. |
| `✓` | Completed | The stage or command completed successfully. |
| `!` | Warning | The command can continue, or completed with a non-fatal issue. |
| `✗` | Failed | The stage or command could not complete. |
| `↻` | Cached | Existing work was reused. |
| `–` | Skipped | The stage was unnecessary, cancelled, or could not run after an earlier failure. |

Spinners animate when stdout is an interactive terminal. Logs redirected to a file are append-only and do not contain animation control characters.

## Processing output

`arena process` shows command context, a single preflight result, the pipeline, and one final summary:

```text
Arena

Input   interview.mp4
Output  /Users/you/output
Target  8 clips · 30–90s · tiktok

✓ Preflight passed
Overall [█░░░░░░░░░░░░░░░] 8% (verified)
[1/5] Transcription
      ◐ Transcribing chunk 1 of 1 · 6m 4s elapsed
[2/5] ⏳ Analysis - Pending
[3/5] ⏳ Clip Alignment - Pending
[4/5] ⏳ Clip Generation - Pending
[5/5] ⏳ Platform Formatting - Pending
```

The formatting stage appears only when `--platform` is supplied. A cached transcript is reported as `Using cached transcript`; internal cache paths and download implementation details are not printed.

Arena reports a percentage only when the engine exposes measurable work, such as audio preparation, completed chunks, generated clips, or formatted clips. Opaque model inference uses a running symbol and elapsed time. The UI does not animate invented `1%` through `99%` values, and a stage never moves backwards when events arrive from different output streams. The overall bar is labeled `verified` because it is calculated only from observed stage checkpoints.

Successful completion is compact:

```text
✓ Done — generated 8 clips in 3m 18s

Input   interview.mp4
Output  /Users/you/output
```

If some independent outputs fail, Arena reports partial success instead of presenting the entire run as successful. Stages that cannot run after a failure are skipped.

## Command state coverage

| Command | Active state | Successful terminal state | Other expected states |
|---|---|---|---|
| `arena process` | Multi-stage pipeline | Clip count, elapsed time, output directory | cached transcript, warning, partial success, failed, interrupted |
| `arena transcribe` | Audio preparation/transcription | duration, word count, output file | cached, chunked-input notice, failed |
| `arena analyze` | Transcription plus analysis | candidate count, words, output file | existing transcript, no candidates, duration filtering, failed |
| `arena generate` | Clip number and percentage | generated clips and output directory | selected clips, partial success, no candidates, failed |
| `arena extract-audio` | Extraction percentage | format, size, duration, output file | overwrite prompt, cancelled, failed |
| `arena format` | Formatted clip number and percentage | formatted count and output directory | warning, partial success, empty input, failed |
| `arena detect-scenes` | Frame scan | scene count, average duration, output file | no changes found, optional report, failed |
| `arena init` | Interactive questions | configuration and credential status | existing configuration, cancelled, failed |
| `arena config` | Interactive credential/reset prompt when needed | requested value or mutation | empty configuration, missing key, cancelled, failed |
| `arena setup` | Installation/check spinner | component health or installed runtime | already ready, repair needed, failed with previous runtime preserved |
| `arena diagnose` | Diagnostic checks | health rows and report path | warnings, critical failures |

## Warnings and failures

Known third-party warnings and native runtime startup logs are kept out of the normal terminal display. On failure, Arena prefers its sanitized public error contract over a native log or a terminal progress line. The public line includes a stable error code, retryability, and a reference suitable for an issue report.

```text
✗ Processing timed out

  Transcription failed [timeout; retryable=true; ref=bb7b08805307]:
  Local transcription exceeded Arena's time limit.

  → Retry once; if it repeats, use a faster local transcription model or
    --transcription-provider openai
```

Preflight errors are actionable and stop the engine before expensive work begins:

```text
✗ Video file not found

Could not find: /Users/you/Videos/missing.mp4
```

Pressing Ctrl+C produces an interrupted state, asks the engine to shut down cleanly, and exits with status 130.

## Engine event protocol

The Python engine writes newline-delimited JSON events to stdout when invoked by the Node.js bridge:

```json
{"type":"progress","stage":"analysis","progress":62,"message":"Scoring candidate moments"}
{"type":"result","data":{"success":true,"outputDir":"/Users/you/output"}}
```

Stdout is a protocol channel. Human-readable presentation belongs in the TypeScript CLI. Stderr and unstructured engine output are buffered while the command runs instead of being interleaved with progress. Normal failure output uses the sanitized public error selected from those buffers; native library chatter is not mistaken for the failure reason.

The supported stage IDs are:

- `transcription`
- `analysis`
- `alignment`
- `generation`
- `formatting`
- `extraction`
- `detection`

Use stable IDs in engine events; user-facing names and styling belong to the CLI.
