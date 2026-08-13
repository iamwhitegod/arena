# Layer 1 Redesign: Full-Context, Two-Pass Seed Detection

**Status:** Implementation specification  
**Date:** August 13, 2026  
**Product requirement:** Support recordings up to at least 8 hours without
discarding transcript coverage.

## Decision

Replace Layer 1's isolated two-minute window analysis with an editorially
informed workflow:

1. Build an understanding of the complete video.
2. Find the strongest thought seeds relative to that complete video.

When the transcript fits safely in one model request, Layer 1 normally makes
two calls: one overview call and one seed-detection call. When it does not fit,
Layer 1 uses token-bounded chunks, merges their content maps, detects candidates
with the shared global overview, and reranks the combined candidate pool.

Eight-hour lectures, conferences, and livestreams are a supported use case, not
an exceptional case to defer. Chunking is determined by tokens rather than by a
fixed duration or a fixed number of chunks.

## Editorial model

A human editor first understands the recording, then identifies its best
moments. Arena should follow the same sequence:

```text
Layer 1, Pass 1: Understand the video
    -> summary, themes, structure, strong and weak regions

Layer 1, Pass 2: Discover and globally rank thought seeds
    -> the best claims, insights, explanations, stories, and advice

Layer 2: Find each seed's premise and resolution
    -> natural clip start and end

Layer 3: Validate completeness and standalone meaning
    -> reject clips that require missing context

Layer 4: Deduplicate and select variants
```

Layer 1 discovers promising centers of thought. It does not choose final clip
boundaries or prove that a clip is complete. `likely_has_premise` and
`likely_has_resolution` remain heuristics for Layer 2.

## Why the current Layer 1 fails

`thought_seed_detector.py` currently creates 120-second windows with 30-second
overlap and asks the model to find seeds in every window independently.

This creates predictable editorial problems:

- The model never sees the video's overall argument, story, or recurring themes.
- It cannot recognize callbacks, later payoffs, repeated ideas, or the best
  version of an idea presented elsewhere.
- Filler windows are forced to produce candidates.
- `interest_score` is calibrated within a local window but later compared
  globally.
- A good moment in a weak window can outrank the video's truly best moment.
- Thoughts crossing window boundaries can be misread or missed.
- API calls and artificial rate-limit delays grow with video duration.

The redesign changes Layer 1 from “find something in every two-minute block” to
“understand the recording, then find its genuinely strongest moments.”

## Required output contract

Layer 2 continues to receive `List[Dict]`. Every normalized seed must contain:

| Field | Type | Requirement |
|---|---|---|
| `timestamp` | `float` | Absolute seconds derived from a real segment |
| `text` | `str` | Exact phrase grounded in the transcript |
| `rhetorical_type` | `str` | `argument`, `teaching`, `story`, `advice`, `qa`, `comparison`, or `insight` |
| `interest_score` | `float` | Globally calibrated value from `0.0` to `1.0` |
| `seed_id` | `str` | Final deterministic ID such as `seed_001` |
| `reasoning` | `str` | Why the moment matters relative to the video |
| `likely_has_premise` | `bool` | Heuristic only |
| `likely_has_resolution` | `bool` | Heuristic only |
| `context_before` | `str` | Extracted locally from neighboring segments |
| `context_after` | `str` | Extracted locally from neighboring segments |

The model may return a compact internal `segment_id`, but it must not be trusted
to calculate final timestamps or context. Those fields are derived locally.

## Compact transcript representation

Use stable, compact segment references instead of verbose start/end timestamp
labels:

```text
[S123|321.4] The exact segment text...
```

`S123` is the segment index and `321.4` is its start time in seconds. The model
returns the segment ID and exact seed phrase. Arena uses the original segment to
recover precise start/end values.

This representation provides enough timeline information for an overview while
avoiding the token overhead of labels such as:

```text
[S000123 00:05:21.400-00:05:25.820]
```

Pass 1 does not need sub-second end timestamps. Pass 2 needs reliable grounding,
which the compact ID provides.

If a phrase spans adjacent transcript segments, grounding may inspect the
identified segment plus a small number of following segments. Reject a seed
that cannot be matched unambiguously after whitespace normalization.

## Context-budget policy

Do not decide whether a video fits from duration alone. Spoken word rate,
language, transcript segmentation, overview size, and output size all affect
the prompt budget.

Layer 1 must calculate separate safe budgets for:

- **Overview input:** transcript plus overview instructions and response reserve.
- **Detection input:** transcript plus overview, detection instructions, and seed
  response reserve.
- **Rerank input:** overview plus normalized candidate evidence and response
  reserve.

Use `tiktoken` when available and `len(text) // 4` as the fallback. The fallback
must catch both missing-package and tokenizer-loading failures.

For a configured 128k context capacity, 90k transcript tokens is a reasonable
initial upper bound, but the effective detection budget will usually be lower
because Pass 2 also includes the overview and a larger response. Keep the
capacity and reserves in named constants rather than scattering `90_000`
through the implementation.

## Processing paths

### Path A: Full transcript fits both passes

This is the normal two-call path:

1. Send the complete compact transcript to `_generate_content_overview()`.
2. Send the complete compact transcript plus the overview to
   `_detect_seeds_with_context()`.
3. Ground, validate, deduplicate, and return the best `target_count * 4` seeds.

Because the detection call sees the complete recording, it can rank candidates
directly against everything else in the video.

### Path B: Overview fits, detection does not

The overview prompt may fit while the detection prompt does not because Pass 2
also carries the overview and reserves more output tokens.

1. Generate one overview from the complete compact transcript.
2. Split the transcript into contiguous detection chunks with boundary overlap.
3. Pass the same global overview to every detection chunk.
4. Combine and ground all candidates.
5. Deduplicate boundary-overlap candidates.
6. Globally rerank the combined candidate pool using the overview and compact
   candidate evidence.
7. Return the best `target_count * 4` seeds.

### Path C: Transcript does not fit the overview budget

This path is required for dense or very long recordings, including supported
eight-hour inputs that exceed one context window.

1. Split the transcript into contiguous, token-bounded overview chunks.
2. Generate the same structured local content map for each chunk.
3. Merge the local maps into one global overview.
4. Run detection over contiguous token-bounded chunks with boundary overlap,
   passing the global overview to every call.
5. Combine, ground, and deduplicate all candidates.
6. Globally rerank the complete candidate pool.
7. Return the best `target_count * 4` seeds.

Every usable transcript segment must appear in at least one overview chunk and
at least one detection chunk. Do not sample every Nth segment and do not create
a “compressed transcript” by dropping arbitrary content.

The long path is a small bounded map/merge workflow, not a general-purpose
framework. Implement only the helpers Layer 1 requires.

## Pass 1: Content overview

Add a private method:

```python
_generate_content_overview(
    client,
    formatted_transcript: str,
) -> Dict
```

For Path C, add private helpers that call the same overview schema for each
chunk and merge the maps:

```python
_generate_chunk_overviews(client, chunks: List[str]) -> List[Dict]
_merge_content_overviews(client, overviews: List[Dict]) -> Dict
```

The validated overview structure is intentionally small:

```json
{
  "summary": "What the complete recording is about",
  "main_themes": [
    {
      "name": "Theme",
      "start_segment": "S10",
      "end_segment": "S90",
      "importance": 0.9
    }
  ],
  "sections": [
    {
      "start_segment": "S1",
      "end_segment": "S100",
      "summary": "What this section contributes"
    }
  ],
  "high_interest_regions": [
    {
      "start_segment": "S50",
      "end_segment": "S75",
      "priority": 0.95,
      "reason": "Why an editor should inspect it"
    }
  ],
  "low_interest_regions": [
    {
      "start_segment": "S1",
      "end_segment": "S12",
      "reason": "Greeting and housekeeping"
    }
  ]
}
```

Requirements:

- Use the configured Layer 1 model for the initial implementation.
- Use `call_api_with_smart_retry()` rather than an inline retry loop.
- Use low-temperature structured JSON output.
- Validate keys, types, score ranges, segment IDs, and range ordering.
- Treat high/low-interest regions as guidance, not hard inclusion/exclusion
  filters.
- When merging chunk maps, preserve their original segment ranges and produce a
  summary of the recording as a whole.

## Pass 2: Context-aware detection

Add a private method:

```python
_detect_seeds_with_context(
    client,
    formatted_transcript: str,
    overview: Dict,
    target_seeds: int,
) -> List[Dict]
```

The prompt must instruct the model to:

- Judge moments relative to the whole video's overview.
- Concentrate on strong regions without requiring equal density over time.
- Prefer the strongest occurrence when an idea is repeated.
- Preserve useful diversity across themes and rhetorical types when quality is
  comparable.
- Avoid greetings, housekeeping, sponsor reads, generic statements, and
  unfinished tangents unless editorially important.
- Return a compact segment ID plus an exact transcript phrase.
- Return fewer seeds instead of inventing content when quality is insufficient.

For chunked detection, create a candidate pool larger than the final seed
budget. A simple initial rule is:

```text
per_chunk_target = max(3, ceil(1.5 * target_seeds / chunk_count))
```

The multiplier is an implementation constant and should be tuned with real
videos. It gives global reranking alternatives without forcing every chunk to
return `target_seeds` candidates.

## Global reranking for chunked paths

Scores produced by separate model calls are not reliably comparable. Existing
deduplication removes overlaps but does not calibrate chunk-local interest
scores.

Paths B and C therefore require one final reranking call:

```python
_rerank_candidates(
    client,
    overview: Dict,
    candidates: List[Dict],
    target_seeds: int,
) -> List[Dict]
```

The reranker receives:

- The global overview.
- Candidate IDs.
- Exact seed text.
- A short locally extracted context excerpt.
- Rhetorical type and original reasoning.
- The candidate's region or segment reference.

It returns selected candidate IDs, globally calibrated interest scores, and
updated reasoning. It must select only supplied IDs and must not generate new
seed text.

If reranking fails after smart retries, use deterministic local ordering as a
degraded fallback and log that global calibration was unavailable.

## `detect_seeds()` orchestration

Keep the existing public interface unchanged:

```python
detect_seeds(transcript_data: Dict, target_count: int = 10) -> List[Dict]
```

High-level behavior:

```text
validate and normalize segments
return [] without an API call when no usable segments exist
target_seeds = target_count * 4
format compact transcript
estimate overview and detection prompt sizes

if full transcript fits detection budget:
    run Path A
elif full transcript fits overview budget:
    run Path B
else:
    run Path C

ground raw candidates in transcript segments
reject invalid or hallucinated candidates
deduplicate candidates
globally rerank when detection was chunked
derive final context fields locally
sort deterministically
assign seed IDs
return at most target_seeds
```

The adapter continues to call `detect_seeds()` exactly as it does today.

## Grounding and normalization

Before a candidate can be returned:

1. Resolve its compact segment ID against the original segment list.
2. Verify that `text` is an exact contiguous phrase in that segment or its
   immediately adjacent segments after whitespace normalization.
3. Reject paraphrases, unknown segment IDs, and ambiguous matches.
4. Derive `timestamp` from the first matched segment.
5. Extract `context_before` and `context_after` from neighboring segments rather
   than from a fixed number of characters.
6. Require a valid rhetorical type.
7. Require a finite `interest_score` within `0.0-1.0`.
8. Require real booleans for premise/resolution likelihood.

After grounding:

- Deduplicate by temporal proximity and normalized text similarity.
- Keep the higher globally calibrated candidate when duplicates collide.
- Use deterministic tie-breaking.
- Assign seed IDs only after final selection and ordering.

Keep `_deduplicate_seeds()` and `_text_similarity()`. Remove
`_compress_transcript()` if it exists or is added during development; arbitrary
sampling is not part of this design.

## Failure behavior

### Overview failure on Path A or B

After smart retries are exhausted, run detection with the full or chunked
transcript and an empty overview. The transcript is still covered; only the
content map is unavailable.

### Local overview failure on Path C

Do not silently omit the failed chunk. After smart retries are exhausted, fail
the Layer 1 stage with the chunk range in the error. Complete overview coverage
is required before claiming global understanding.

### Overview merge failure

Use the validated local maps together as the shared overview input. Detection
may proceed, but record that no synthesized global summary was available.

### Detection chunk failure

Do not silently skip its transcript range. Exhaust smart retries and then fail
the Layer 1 stage with the affected range.

### Malformed structured output

- Allow one bounded JSON/schema repair attempt.
- Preserve valid candidates when individual candidates are malformed.
- Reject ungrounded candidates and record the rejection count.
- Do not retry the same request merely at a higher temperature.

### Too few seeds

Return fewer seeds. Do not add a separate gap-fill mechanism in the initial
implementation. Real-video evaluation will determine whether one is needed.

## Checkpoint compatibility

Keep final Layer 1 checkpointing at the adapter level. Do not add a public
`detect_seeds_from_overview()` method or an intermediate overview checkpoint in
the initial implementation.

Old interrupted checkpoints must not bypass the new Layer 1 or mix with new
downstream results. `arena setup --force` rebuilds the managed Python runtime; it
does not clear editorial checkpoints.

Use a lightweight versioned job ID for the entire four-layer run:

```python
base_job_id = CheckpointManager.generate_job_id(transcript_data)
job_id = f"{base_job_id}_two_pass_v1"
```

This is a small adapter change and automatically isolates seed, construction,
validation, and selection checkpoints. Successful runs continue to use the
existing cleanup behavior.

## Metrics and logging

Retain the metrics that are useful for the initial implementation:

- `api_calls`
- `tokens_used`
- `cost_usd`
- `seeds_detected`
- `overview_calls`
- `detection_calls`
- `rerank_calls`
- `chunks_analyzed`
- `invalid_seeds_rejected`
- `processing_path` (`full`, `chunked_detection`, or `hierarchical`)
- `overview_fallback_used`
- `rerank_fallback_used`

Remove `windows_analyzed`. Logs should state the selected path, estimated prompt
size, safe budget, chunk coverage, raw candidate count, rejection count, and
final seed count. Never log full transcripts or API keys.

## Files to modify

### `engine/arena/editorial/thought_seed_detector.py`

- Add token estimation and separate prompt-budget helpers.
- Add compact transcript formatting and segment grounding.
- Add overview generation and overview-map merging.
- Add full and token-bounded detection paths.
- Add global candidate reranking for chunked detection.
- Replace inline retry logic with `call_api_with_smart_retry()`.
- Remove the per-window delay.
- Remove `WINDOW_SIZE`, `WINDOW_OVERLAP`, `_create_windows()`,
  `_detect_seeds_in_window()`, and the window-only prompt once all three new
  paths are implemented.
- Explicitly remove or avoid `_compress_transcript()` and Nth-segment sampling.
- Preserve the public `detect_seeds()` signature and normalized output contract.
- Retain and harden `_deduplicate_seeds()` and `_text_similarity()`.

### `engine/arena/editorial/adapter.py`

- Add the `two_pass_v1` suffix to the checkpoint job ID.
- Keep the existing `detect_seeds()` call and final seed checkpoint flow.

### `engine/tests/test_thought_seed_detector.py`

- Remove sliding-window creation and overlap tests.
- Mock model responses for deterministic unit tests.
- Add the focused tests below.

### Existing modules to reuse

- `engine/arena/editorial/retry.py` for `call_api_with_smart_retry()`.
- `engine/arena/editorial/checkpoint.py` for final stage checkpoints.
- `engine/arena/editorial/utils.py` where its timestamp helpers remain useful.
- Existing Layer 1 deduplication logic for chunk overlaps.

## Required tests

### Focused unit tests

- Empty input returns no seeds and makes no API calls.
- Path A makes exactly one overview and one detection call.
- Overview failure falls back to detection without the overview.
- Compact segment IDs resolve to locally derived timestamps and context.
- Hallucinated, ambiguous, and malformed candidates are rejected.
- Output matches the existing Layer 2 seed contract.
- Deduplication uses deterministic tie-breaking.
- Token boundaries select Paths A, B, and C correctly.
- Every segment is covered by Path C overview and detection chunks.
- Boundary overlap does not create duplicate final seeds.
- Chunked paths run global reranking and accept only existing candidate IDs.
- The checkpoint namespace prevents old stages from being loaded.

### Integration and editorial evaluation

1. Run `cd engine && python -m pytest tests/test_thought_seed_detector.py -v`.
2. Run `cd engine && python -m pytest tests/test_week1_validation.py -v` with an
   explicitly configured API key.
3. Process the same representative videos using the old and new Layer 1.
4. Blind-review whether the new seeds represent the recording's actual strongest
   moments rather than the best item from each two-minute window.
5. Include short-form, one-hour, three-hour, and eight-hour inputs.
6. Verify that Layers 2, 3, and 4 consume the seeds without contract changes.
7. Verify all prompts remain below their calculated context budgets.
8. Interrupt an in-progress run and confirm the versioned checkpoint namespace
   never mixes old and new pipeline artifacts.

## Implementation order

Implement in two milestones within the same redesign:

### Milestone 1: Prove the editorial hypothesis

- Compact transcript formatting and grounding.
- Path A overview and contextual seed detection.
- Smart retry and overview fallback.
- Output normalization and focused tests.
- Old-versus-new real-video comparison.

### Milestone 2: Complete the supported duration requirement

- Paths B and C with token-bounded coverage.
- Overview-map merge.
- Global candidate reranking.
- Eight-hour validation.
- Remove the old sliding-window implementation.

The redesign is not production-complete until both milestones pass. Milestone 1
exists to validate prompt quality before adding the long-video calls, not to
defer eight-hour support indefinitely.

## Acceptance criteria

The redesign is complete when:

- Normal transcripts use the two-call full-context path.
- Layer 1 ranks candidates relative to the complete video rather than per window.
- Recordings up to at least eight hours are processed without dropping transcript
  segments or exceeding calculated prompt budgets.
- Chunked candidates receive a global reranking step.
- Every returned seed is grounded in exact transcript text and a real segment.
- The Layer 2 output contract remains unchanged.
- Old and new checkpoints cannot be mixed.
- Focused unit and existing four-layer tests pass.
- Blind old-versus-new review shows better editorial relevance or, at minimum,
  no regression while normal inputs materially reduce API calls.

## Expected API-call behavior

- **Path A:** 2 calls under normal conditions.
- **Path B:** 1 overview + N detection chunks + 1 rerank.
- **Path C:** N overview maps + 1 merge + M detection chunks + 1 rerank.

Repair attempts and fallbacks are bounded exceptions. The implementation must
report the actual path and call count rather than promising that every video,
regardless of length, takes two calls.
