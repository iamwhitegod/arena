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
[1/5] ✓ Transcription — Transcription complete
[2/5] ◐ Analysis
      [████████████░░░░░░░░] 62% · Scoring candidate moments
[3/5] ○ Clip Alignment
[4/5] ○ Clip Generation
[5/5] ○ Platform Formatting
```

The formatting stage appears only when `--platform` is supplied. A cached transcript is reported as `Using cached transcript`; internal cache paths and download implementation details are not printed.

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

Known third-party warnings are hidden when a command succeeds. They are retained as diagnostics and included when processing fails. This keeps successful output readable without losing failure evidence.

```text
✗ Analysis failed

Reason  OpenAI request timed out
Resume  The transcript was preserved
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

Stdout is a protocol channel. Human-readable presentation belongs in the TypeScript CLI. Stderr and unstructured engine output are buffered for failure diagnostics instead of being interleaved with progress.

The supported stage IDs are:

- `transcription`
- `analysis`
- `alignment`
- `generation`
- `formatting`
- `extraction`
- `detection`

Use stable IDs in engine events; user-facing names and styling belong to the CLI.
