"""
Thought Seed Detector (Layer 1)

Two-pass, full-context seed detection:

  Pass 1 — Build an overview of the complete video (themes, structure, regions).
  Pass 2 — Find globally ranked thought seeds using the overview as context.

For transcripts that fit the model context, both passes see the full transcript
and Layer 1 makes two API calls. Longer transcripts use token-bounded chunks
with a shared global overview and a final reranking step.
"""

import json
import math
import re
from typing import Dict, List, Optional, Tuple

from arena.providers.base import ResponseMode
from arena.providers.retry import retry_with_backoff

from .thought_unit import RhetoricalType

# ---------------------------------------------------------------------------
# Context-budget constants (128k model)
# ---------------------------------------------------------------------------
MODEL_CONTEXT_CAPACITY = 128_000
SYSTEM_PROMPT_RESERVE = 4_000
OVERVIEW_RESPONSE_RESERVE = 4_000
DETECTION_RESPONSE_RESERVE = 8_000
RERANK_RESPONSE_RESERVE = 4_000

SAFE_OVERVIEW_BUDGET = (
    MODEL_CONTEXT_CAPACITY - SYSTEM_PROMPT_RESERVE - OVERVIEW_RESPONSE_RESERVE
)
SAFE_DETECTION_BUDGET = (
    MODEL_CONTEXT_CAPACITY
    - SYSTEM_PROMPT_RESERVE
    - OVERVIEW_RESPONSE_RESERVE  # overview included in detection prompt
    - DETECTION_RESPONSE_RESERVE
)

CHUNK_OVERLAP_SEGMENTS = 8  # segments of boundary overlap between chunks

# Deduplication
DEDUP_TIME_THRESHOLD = 10.0
DEDUP_TEXT_THRESHOLD = 0.7

_SEGMENT_ID_RE = re.compile(r"S(0|[1-9][0-9]*)")

VALID_RHETORICAL_TYPES = {
    "argument", "teaching", "story", "advice", "qa", "comparison", "insight",
}


def _safe_float(value, default: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Coerce a value to a clamped float or return a default. Never raises.

    Rejects booleans. Accepts numeric strings like "0.9". Clamps to [lo, hi].
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        f = float(value)
        if math.isfinite(f):
            return max(lo, min(hi, f))
        return default
    if isinstance(value, str):
        try:
            f = float(value)
            if math.isfinite(f):
                return max(lo, min(hi, f))
        except (ValueError, OverflowError):
            pass
    return default


class ThoughtSeedDetector:
    """Detect thought seeds using full-video context."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "gpt-4o",
        overview_model: Optional[str] = None,
        *,
        chat=None,
        overview_chat=None,
    ):
        if chat is not None:
            self._chat = chat
            self._overview_chat = overview_chat or chat
        elif api_key is not None:
            from arena.providers.openai_adapter import OpenAIChatModel

            self._chat = OpenAIChatModel(api_key=api_key, model=model)
            self._overview_chat = (
                OpenAIChatModel(api_key=api_key, model=overview_model)
                if overview_model and overview_model != model
                else self._chat
            )
        else:
            raise ValueError("Either chat or api_key required")
        self.api_key = api_key
        self.model = model
        self.overview_model = overview_model or model
        self.metrics: Dict = {
            "api_calls": 0,
            "tokens_used": 0,
            "cost_usd": 0.0,
            "seeds_detected": 0,
            "overview_calls": 0,
            "detection_calls": 0,
            "rerank_calls": 0,
            "chunks_analyzed": 0,
            "invalid_seeds_rejected": 0,
            "processing_path": "",
            "overview_fallback_used": False,
            "rerank_fallback_used": False,
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def detect_seeds(
        self,
        transcript_data: Dict,
        target_count: int = 10,
    ) -> List[Dict]:
        """
        Detect thought seeds with full-video context.

        Args:
            transcript_data: Transcript dict with 'segments', 'text', 'duration'
            target_count: Target number of final clips (detects ~4x this)

        Returns:
            List of seed dicts matching the Layer 2 contract.
        """
        segments = self._normalize_segments(transcript_data.get("segments", []))

        if not segments:
            print("      No usable transcript segments")
            return []

        target_seeds = target_count * 4
        formatted = self._format_compact_transcript(segments)
        transcript_tokens = self._estimate_tokens(formatted)
        duration = segments[-1]["end"]

        print(f"      Transcript: {len(segments)} segments, ~{transcript_tokens:,} tokens, {duration:.0f}s")

        # Choose processing path
        overview_fits = transcript_tokens <= SAFE_OVERVIEW_BUDGET
        detection_fits = transcript_tokens <= SAFE_DETECTION_BUDGET

        if overview_fits and detection_fits:
            seeds = self._path_a(segments, formatted, target_seeds)
        elif overview_fits:
            seeds = self._path_b(segments, formatted, transcript_tokens, target_seeds)
        else:
            seeds = self._path_c(segments, formatted, transcript_tokens, target_seeds)

        self.metrics["seeds_detected"] = len(seeds)
        print(f"      Detected {len(seeds)} thought seeds")
        return seeds

    # ------------------------------------------------------------------
    # Processing paths
    # ------------------------------------------------------------------

    def _path_a(
        self,
        segments: List[Dict],
        formatted: str,
        target_seeds: int,
    ) -> List[Dict]:
        """Full transcript fits both passes. Two API calls."""
        self.metrics["processing_path"] = "full"
        print(f"      Path A: full-context (2 calls)")

        overview = self._generate_overview(formatted)

        # Recalculate: does the actual overview still fit detection budget?
        overview_text = json.dumps(overview, ensure_ascii=False)
        total_detection_tokens = (
            self._estimate_tokens(formatted)
            + self._estimate_tokens(overview_text)
            + SYSTEM_PROMPT_RESERVE
            + DETECTION_RESPONSE_RESERVE
        )
        if total_detection_tokens > MODEL_CONTEXT_CAPACITY:
            print("      Overview too large for full-context detection, switching to Path B")
            return self._path_b_with_overview(segments, formatted, overview, target_seeds)

        raw = self._detect_with_context(formatted, overview, target_seeds)
        return self._finalize(raw, segments, target_seeds)

    def _path_b_with_overview(
        self,
        segments: List[Dict],
        formatted: str,
        overview: Dict,
        target_seeds: int,
    ) -> List[Dict]:
        """Path B variant when overview is already generated."""
        self.metrics["processing_path"] = "chunked_detection"

        overview_text = json.dumps(overview, ensure_ascii=False)
        overview_tokens = self._estimate_tokens(overview_text)
        chunk_budget = SAFE_DETECTION_BUDGET - overview_tokens
        chunks = self._chunk_formatted_transcript(segments, chunk_budget)
        print(f"      Chunked detection: {len(chunks)} chunks")

        raw = self._detect_chunked(chunks, overview, target_seeds)
        seeds = self._ground_and_dedup(raw, segments)
        reranked = self._rerank(overview, seeds, target_seeds)
        self._assign_seed_ids(reranked)
        return reranked

    def _path_b(
        self,
        segments: List[Dict],
        formatted: str,
        transcript_tokens: int,
        target_seeds: int,
    ) -> List[Dict]:
        """Overview fits, detection must be chunked."""
        self.metrics["processing_path"] = "chunked_detection"

        overview = self._generate_overview(formatted)

        overview_text = json.dumps(overview, ensure_ascii=False)
        overview_tokens = self._estimate_tokens(overview_text)
        chunk_budget = SAFE_DETECTION_BUDGET - overview_tokens
        chunks = self._chunk_formatted_transcript(segments, chunk_budget)
        print(f"      Path B: full overview + {len(chunks)} detection chunks")

        raw = self._detect_chunked(chunks, overview, target_seeds)
        seeds = self._ground_and_dedup(raw, segments)
        reranked = self._rerank(overview, seeds, target_seeds)
        self._assign_seed_ids(reranked)
        return reranked

    def _path_c(
        self,
        segments: List[Dict],
        formatted: str,
        transcript_tokens: int,
        target_seeds: int,
    ) -> List[Dict]:
        """Transcript exceeds overview budget. Hierarchical map/merge."""
        self.metrics["processing_path"] = "hierarchical"

        overview_chunks = self._chunk_formatted_transcript(segments, SAFE_OVERVIEW_BUDGET)
        print(f"      Path C: {len(overview_chunks)} overview chunks", end="")

        local_overviews = []
        for i, chunk in enumerate(overview_chunks, 1):
            chunk_formatted = self._format_compact_transcript(chunk)
            local = self._generate_overview(chunk_formatted, required=True)
            local_overviews.append(local)
            self.metrics["chunks_analyzed"] += 1

        overview = self._merge_overviews(local_overviews)

        overview_text = json.dumps(overview, ensure_ascii=False)
        overview_tokens = self._estimate_tokens(overview_text)
        chunk_budget = SAFE_DETECTION_BUDGET - overview_tokens
        det_chunks = self._chunk_formatted_transcript(segments, chunk_budget)
        print(f" + {len(det_chunks)} detection chunks")

        raw = self._detect_chunked(det_chunks, overview, target_seeds)
        seeds = self._ground_and_dedup(raw, segments)
        reranked = self._rerank(overview, seeds, target_seeds)
        self._assign_seed_ids(reranked)
        return reranked

    # ------------------------------------------------------------------
    # Pass 1: Content overview
    # ------------------------------------------------------------------

    def _generate_overview(
        self, formatted_transcript: str, *, required: bool = False,
    ) -> Dict:
        """Generate a content overview from the transcript.

        Args:
            required: When True (Path C chunks), failures propagate instead of
                      returning an empty fallback map.
        """
        print("      Generating content overview...")

        system = (
            "You are an expert video editor analyzing a spoken transcript. "
            "Produce a structured content map that identifies the recording's "
            "themes, structure, and strongest editorial regions."
        )

        prompt = f"""TRANSCRIPT:
{formatted_transcript}

Analyze the complete transcript and return a JSON content map.

RETURN JSON:
{{
  "summary": "2-3 sentence summary of the recording",
  "main_themes": [
    {{
      "name": "Theme name",
      "start_segment": "S10",
      "end_segment": "S90",
      "importance": 0.9
    }}
  ],
  "sections": [
    {{
      "start_segment": "S0",
      "end_segment": "S50",
      "summary": "What this section contributes to the video"
    }}
  ],
  "high_interest_regions": [
    {{
      "start_segment": "S50",
      "end_segment": "S75",
      "priority": 0.95,
      "reason": "Why an editor should inspect this region"
    }}
  ],
  "low_interest_regions": [
    {{
      "start_segment": "S1",
      "end_segment": "S12",
      "reason": "Greeting and housekeeping"
    }}
  ]
}}

RULES:
- Use segment IDs from the transcript (e.g. S0, S10, S50)
- importance and priority are 0.0-1.0
- Report as many or as few high_interest_regions as genuinely exist
- Quality may be concentrated in one section — do not manufacture strong regions
- A recording that is mostly filler should have mostly low_interest_regions
"""

        try:
            overview = self._call_model(
                system,
                prompt,
                use_overview=True,
            )
            overview = self._validate_overview(overview)
            self.metrics["overview_calls"] += 1
            print("      Overview complete")
            return overview
        except Exception as e:
            if required:
                raise
            print(f"      Overview failed: {e}")
            self.metrics["overview_fallback_used"] = True
            return {"summary": "", "main_themes": [], "sections": [],
                    "high_interest_regions": [], "low_interest_regions": []}

    def _merge_overviews(self, overviews: List[Dict]) -> Dict:
        """Merge local chunk overviews into one global overview."""
        system = (
            "You are merging partial content maps from consecutive sections "
            "of the same recording into one unified overview."
        )

        maps_text = "\n\n".join(
            f"--- Section {i+1} ---\n{json.dumps(o, ensure_ascii=False)}"
            for i, o in enumerate(overviews)
        )

        prompt = f"""These are content maps from consecutive sections of one recording:

{maps_text}

Merge them into a single unified content map with the same JSON schema:
- Combine themes that span sections
- Unify the section summaries into a coherent timeline
- Merge and deduplicate high/low interest regions
- Write one summary for the whole recording
- Keep segment IDs from the originals

Return the merged JSON."""

        try:
            merged = self._call_model(system, prompt, use_overview=True)
            self.metrics["overview_calls"] += 1
            return self._validate_overview(merged)
        except Exception:
            # Fallback: concatenate the already-validated local maps
            combined: Dict = {
                "summary": " ".join(str(o.get("summary", "")) for o in overviews),
                "main_themes": [],
                "sections": [],
                "high_interest_regions": [],
                "low_interest_regions": [],
            }
            for o in overviews:
                combined["main_themes"].extend(o.get("main_themes", []))
                combined["sections"].extend(o.get("sections", []))
                combined["high_interest_regions"].extend(o.get("high_interest_regions", []))
                combined["low_interest_regions"].extend(o.get("low_interest_regions", []))
            return combined

    # ------------------------------------------------------------------
    # Pass 2: Context-aware seed detection
    # ------------------------------------------------------------------

    def _detect_with_context(
        self,
        formatted_transcript: str,
        overview: Dict,
        target_seeds: int,
    ) -> List[Dict]:
        """Detect seeds from the full transcript with overview context."""
        print(f"      Detecting seeds (target: {target_seeds})...")

        overview_text = json.dumps(overview, ensure_ascii=False)

        system = (
            "You are an expert at finding the strongest claims, insights, "
            "teaching moments, stories, and advice in spoken content. You have "
            "already analyzed this recording at a high level and now need to "
            "identify specific thought seeds — moments that anchor complete thoughts."
        )

        regions_text = self._format_region_guidance(overview)

        prompt = f"""CONTENT OVERVIEW:
{overview_text}

FULL TRANSCRIPT:
{formatted_transcript}

TASK:
Find the top {target_seeds} thought seeds across this entire transcript.

A THOUGHT SEED is a claim, insight, explanation, story turning point, or piece
of advice that likely has a PREMISE before it and a RESOLUTION after it. It is
the CENTER of a complete thought worth clipping.

{regions_text}

SCORING:
- Score interest RELATIVE TO THE REST OF THE VIDEO, not in isolation
- A seed connecting to a recurring theme scores higher
- A narrative turning point scores higher
- Prefer the strongest version when the speaker repeats an idea
- Avoid greetings, housekeeping, sponsor reads, and generic statements

RETURN JSON:
{{
  "seeds": [
    {{
      "segment_id": "S45",
      "text": "The exact sentence or phrase from the transcript",
      "rhetorical_type": "argument",
      "interest_score": 0.85,
      "reasoning": "Why this matters relative to the whole video",
      "likely_has_premise": true,
      "likely_has_resolution": true
    }}
  ]
}}

RHETORICAL TYPES: argument, teaching, story, advice, qa, comparison, insight

RULES:
- segment_id must be a real ID from the transcript (e.g. S45)
- text must be an EXACT phrase from that segment, not a paraphrase
- interest_score 0.0-1.0 calibrated across the whole video
- Return fewer seeds if the recording lacks {target_seeds} strong moments
- Quality is the primary criterion; temporal diversity is secondary
"""

        result = self._call_model(system, prompt)
        self.metrics["detection_calls"] += 1

        raw_seeds = result.get("seeds", [])
        print(f"      Model returned {len(raw_seeds)} candidates")
        return raw_seeds

    def _detect_chunked(
        self,
        chunks: List[List[Dict]],
        overview: Dict,
        target_seeds: int,
    ) -> List[Dict]:
        """Detect seeds across multiple transcript chunks."""
        per_chunk = max(3, math.ceil(1.5 * target_seeds / len(chunks)))
        all_raw: List[Dict] = []

        for i, chunk in enumerate(chunks, 1):
            chunk_formatted = self._format_compact_transcript(chunk)
            chunk_start = chunk[0]["start"]
            chunk_end = chunk[-1]["end"]
            print(f"      Detection chunk {i}/{len(chunks)} ({chunk_start:.0f}s-{chunk_end:.0f}s)...")

            raw = self._detect_with_context(chunk_formatted, overview, per_chunk)
            all_raw.extend(raw)
            self.metrics["chunks_analyzed"] += 1

        return all_raw

    # ------------------------------------------------------------------
    # Reranking (chunked paths only)
    # ------------------------------------------------------------------

    def _rerank(
        self,
        overview: Dict,
        candidates: List[Dict],
        target_seeds: int,
    ) -> List[Dict]:
        """Globally rerank candidates from multiple detection calls.

        Always runs for chunked paths because scores from separate calls are
        not reliably comparable, even when the pool is small enough to retain
        every candidate.
        """
        if not candidates:
            return candidates

        print(f"      Reranking {len(candidates)} candidates...")

        system = (
            "You are selecting the strongest thought seeds from a pool of "
            "candidates that were identified in separate sections of the same "
            "recording. Rank them relative to the whole video."
        )

        candidate_summaries = []
        for i, c in enumerate(candidates):
            candidate_summaries.append(
                f"ID:{i} | {c.get('rhetorical_type','?')} | "
                f"t={c['timestamp']:.1f}s | score={c.get('interest_score',0):.2f} | "
                f"\"{c['text'][:120]}\" | {c.get('reasoning','')[:80]}"
            )

        prompt = f"""RECORDING OVERVIEW:
{json.dumps(overview, ensure_ascii=False)}

CANDIDATE POOL ({len(candidates)} candidates):
{chr(10).join(candidate_summaries)}

Select the top {target_seeds} candidates that best represent the recording's
strongest moments. Return only existing candidate IDs.

RETURN JSON:
{{
  "selected": [
    {{
      "id": 0,
      "interest_score": 0.92,
      "reasoning": "Updated reasoning relative to all candidates"
    }}
  ]
}}

RULES:
- Select at most {target_seeds} candidates
- Recalibrate interest_score across the full pool (0.0-1.0)
- Prefer quality and diversity over clustering in one section
- Do NOT invent new candidates — only return IDs from the pool
"""

        try:
            result = self._call_model(system, prompt)
            self.metrics["rerank_calls"] += 1

            selected_ids = set()
            reranked = []
            for entry in result.get("selected", []):
                idx = entry.get("id")
                if not isinstance(idx, int) or idx < 0 or idx >= len(candidates):
                    continue
                if idx in selected_ids:
                    continue
                selected_ids.add(idx)

                seed = dict(candidates[idx])
                if isinstance(entry.get("interest_score"), (int, float)) and not isinstance(entry.get("interest_score"), bool):
                    seed["interest_score"] = max(0.0, min(1.0, float(entry["interest_score"])))
                if isinstance(entry.get("reasoning"), str) and entry["reasoning"]:
                    seed["reasoning"] = entry["reasoning"]
                reranked.append(seed)

            if reranked:
                print(f"      Reranked to {len(reranked)} seeds")
                return reranked[:target_seeds]
        except Exception as e:
            print(f"      Reranking failed ({e}), using score-based ordering")
            self.metrics["rerank_fallback_used"] = True

        # Fallback: deterministic sort by score then timestamp
        candidates.sort(key=lambda s: (-s.get("interest_score", 0), s.get("timestamp", 0)))
        return candidates[:target_seeds]

    # ------------------------------------------------------------------
    # Grounding, normalization, finalization
    # ------------------------------------------------------------------

    def _finalize(
        self,
        raw_seeds: List[Dict],
        segments: List[Dict],
        limit: int,
        *,
        assign_ids: bool = True,
    ) -> List[Dict]:
        """Ground, validate, deduplicate, and optionally assign IDs.

        When seeds will be reranked after finalization, pass assign_ids=False
        so IDs reflect the final order.
        """
        grounded = []
        for raw in raw_seeds:
            seed = self._ground_seed(raw, segments)
            if seed is not None:
                grounded.append(seed)
            else:
                self.metrics["invalid_seeds_rejected"] += 1

        unique = self._deduplicate_seeds(grounded)

        unique.sort(key=lambda s: (-s["interest_score"], s["timestamp"]))
        top = unique[:limit]

        if assign_ids:
            self._assign_seed_ids(top)

        return top

    def _ground_and_dedup(
        self,
        raw_seeds: List[Dict],
        segments: List[Dict],
    ) -> List[Dict]:
        """Ground and deduplicate without truncating.

        Used by chunked paths so all valid candidates reach the global reranker.
        """
        grounded = []
        for raw in raw_seeds:
            seed = self._ground_seed(raw, segments)
            if seed is not None:
                grounded.append(seed)
            else:
                self.metrics["invalid_seeds_rejected"] += 1
        return self._deduplicate_seeds(grounded)

    @staticmethod
    def _assign_seed_ids(seeds: List[Dict]) -> None:
        """Assign deterministic seed IDs based on current list order."""
        for i, seed in enumerate(seeds, 1):
            seed["seed_id"] = f"seed_{i:03d}"

    def _ground_seed(self, raw: Dict, segments: List[Dict]) -> Optional[Dict]:
        """Validate and ground a raw model-returned seed in the transcript."""
        if not isinstance(raw, dict):
            return None

        # Resolve segment ID. A present but malformed ID is a rejection.
        seg_id = raw.get("segment_id")
        has_seg_id = seg_id is not None and seg_id != ""
        seg_idx = self._parse_seg_id(seg_id) if has_seg_id else None
        if has_seg_id and seg_idx is None:
            # ID was supplied but doesn't match S<number> format — reject.
            return None
        raw_text = raw.get("text")
        if not isinstance(raw_text, str):
            return None
        text = raw_text.strip()

        if not text:
            return None

        # Try to find the exact text in the identified segment or neighbors
        matched_idx = self._find_text_in_segments(text, segments, seg_idx)
        if matched_idx is None:
            return None

        seg = segments[matched_idx]

        # Validate rhetorical type — reject unknown values
        rtype = raw.get("rhetorical_type")
        if rtype not in VALID_RHETORICAL_TYPES:
            return None

        # Validate interest score — reject bools, non-numeric, or out-of-range
        score = raw.get("interest_score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
            return None
        score = float(score)
        if score < 0.0 or score > 1.0:
            return None

        # Validate booleans strictly — reject string "false" etc.
        premise_val = raw.get("likely_has_premise")
        resolution_val = raw.get("likely_has_resolution")
        if not isinstance(premise_val, bool) or not isinstance(resolution_val, bool):
            return None

        # Extract context from neighboring segments
        ctx_before, ctx_after = self._extract_context(matched_idx, segments)

        return {
            "timestamp": seg["start"],
            "text": text,
            "rhetorical_type": rtype,
            "interest_score": score,
            "seed_id": "",
            "reasoning": str(raw.get("reasoning", "")),
            "likely_has_premise": premise_val,
            "likely_has_resolution": resolution_val,
            "context_before": ctx_before,
            "context_after": ctx_after,
        }

    def _find_text_in_segments(
        self,
        text: str,
        segments: List[Dict],
        hint_idx: Optional[int],
    ) -> Optional[int]:
        """Find which segment contains the exact text. Returns index or None.

        Priority order:
        1. The identified segment itself.
        2. The identified segment spanning into its neighbor.
        3. Global single-segment scan, only if the match is unique.
        """
        normalized = self._normalize_text(text)

        # 1. When a segment ID was supplied, match only against that segment
        #    and its immediate neighbors. Do not fall through to a global scan
        #    — an unknown or wrong ID must be rejected.
        if hint_idx is not None:
            list_pos = self._resolve_hint(hint_idx, segments)
            if list_pos is None:
                # The supplied segment ID does not exist in the transcript.
                return None

            # Exact match in the identified segment itself
            if normalized in self._normalize_text(segments[list_pos].get("text", "")):
                return list_pos

            # Spanning: identified segment + next
            if list_pos + 1 < len(segments):
                combined = (
                    self._normalize_text(segments[list_pos].get("text", ""))
                    + " "
                    + self._normalize_text(segments[list_pos + 1].get("text", ""))
                )
                if normalized in combined:
                    return list_pos

            # Spanning: previous + identified segment — return the earlier
            # segment so the timestamp reflects where the phrase begins.
            if list_pos > 0:
                combined = (
                    self._normalize_text(segments[list_pos - 1].get("text", ""))
                    + " "
                    + self._normalize_text(segments[list_pos].get("text", ""))
                )
                if normalized in combined:
                    return list_pos - 1

            # Text not found in or near the identified segment.
            return None

        # 2. No segment ID supplied — accept only if exactly one match.
        matches = []
        for i, seg in enumerate(segments):
            if normalized in self._normalize_text(seg.get("text", "")):
                matches.append(i)
        if len(matches) == 1:
            return matches[0]

        # No unique match found; reject.
        return None

    def _resolve_hint(self, hint_idx: int, segments: List[Dict]) -> Optional[int]:
        """Map an original segment _idx to its position in the segment list."""
        for pos, seg in enumerate(segments):
            if seg.get("_idx") == hint_idx:
                return pos
        # Fallback: treat as list position if in range
        if 0 <= hint_idx < len(segments):
            return hint_idx
        return None

    def _extract_context(self, idx: int, segments: List[Dict]) -> Tuple[str, str]:
        """Extract context before/after from neighboring segments."""
        before_parts = []
        for i in range(max(0, idx - 2), idx):
            before_parts.append(segments[i].get("text", "").strip())
        before = " ".join(before_parts)

        after_parts = []
        for i in range(idx + 1, min(len(segments), idx + 3)):
            after_parts.append(segments[i].get("text", "").strip())
        after = " ".join(after_parts)

        return before[:200], after[:200]

    # ------------------------------------------------------------------
    # Transcript formatting and chunking
    # ------------------------------------------------------------------

    def _format_compact_transcript(self, segments: List[Dict]) -> str:
        """Format segments with compact IDs: [S123|321.4] text..."""
        lines = []
        for seg in segments:
            idx = seg.get("_idx", seg.get("id", 0))
            start = seg["start"]
            text = seg.get("text", "").strip()
            if text:
                lines.append(f"[S{idx}|{start:.1f}] {text}")
        return "\n".join(lines)

    MIN_CHUNK_BUDGET = 2_000  # absolute floor for a usable chunk

    NEWLINE_TOKEN_COST = 1  # conservative cost for the \n between lines

    def _seg_line_tokens(self, seg: Dict) -> int:
        """Token cost of one formatted segment line plus its newline separator."""
        line = f"[S{seg.get('_idx', 0)}|{seg['start']:.1f}] {seg.get('text', '')}"
        return self._estimate_tokens(line) + self.NEWLINE_TOKEN_COST

    def _chunk_formatted_transcript(
        self,
        segments: List[Dict],
        token_budget: int,
    ) -> List[List[Dict]]:
        """Split segments into token-bounded chunks with boundary overlap.

        Guarantees:
        - The formatted text of every emitted chunk fits within token_budget.
        - Overlap segments reserve room for the triggering segment so the
          combined chunk never exceeds the budget.

        Raises ValueError if any single segment exceeds the budget. The
        transcript must be resegmented upstream before chunking.
        """
        if token_budget < self.MIN_CHUNK_BUDGET:
            raise ValueError(
                f"Chunk budget is too small ({token_budget} tokens). "
                f"The overview may be too large for the configured context capacity."
            )

        # Pre-compute per-segment token costs (including newline).
        # Reject any segment that alone exceeds the budget — the chunker
        # cannot split a single segment and must never emit an over-budget
        # chunk. The transcript must be resegmented upstream.
        seg_costs = []
        for s in segments:
            cost = self._seg_line_tokens(s)
            if cost > token_budget:
                raise ValueError(
                    f"Segment S{s.get('_idx', '?')} ({cost} tokens) exceeds the "
                    f"chunk budget ({token_budget} tokens). The transcript must "
                    f"be resegmented into smaller pieces."
                )
            seg_costs.append(cost)

        chunks: List[List[Dict]] = []
        current: List[Dict] = []
        current_tokens = 0

        for i, seg in enumerate(segments):
            cost = seg_costs[i]

            if current and current_tokens + cost > token_budget:
                chunks.append(current)

                # Build overlap: fit the most recent segments alongside the
                # incoming segment. Reserve cost for the new segment first.
                available = token_budget - cost
                overlap: List[Dict] = []
                overlap_tokens = 0
                for j in range(len(current) - 1, max(len(current) - CHUNK_OVERLAP_SEGMENTS - 1, -1), -1):
                    prev_cost = self._seg_line_tokens(current[j])
                    if overlap_tokens + prev_cost > available:
                        break
                    overlap.insert(0, current[j])
                    overlap_tokens += prev_cost

                current = list(overlap)
                current_tokens = overlap_tokens

            current.append(seg)
            current_tokens += cost

        if current:
            chunks.append(current)

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalize_segments(self, segments) -> List[Dict]:
        """Validate segments and add stable indices.

        Silently skips non-dict entries, segments with non-string text,
        None text, numeric text, or invalid time ranges.
        """
        if not isinstance(segments, list):
            return []
        valid = []
        for i, seg in enumerate(segments):
            if not isinstance(seg, dict):
                continue
            start = seg.get("start")
            end = seg.get("end")
            raw_text = seg.get("text")
            if not isinstance(raw_text, str):
                continue
            text = raw_text.strip()
            if (
                isinstance(start, (int, float))
                and not isinstance(start, bool)
                and isinstance(end, (int, float))
                and not isinstance(end, bool)
                and math.isfinite(start)
                and math.isfinite(end)
                and end > start
                and text
            ):
                valid.append({**seg, "_idx": i, "text": text})
        return valid

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count using tiktoken or a safe upper-bound fallback.

        The fallback uses UTF-8 byte length because a single Unicode character
        can encode into multiple tokens (e.g. emoji, rare scripts). Every token
        represents at least one input byte, so byte length is a true upper
        bound. This overestimates for ASCII but never underestimates for any
        input.
        """
        try:
            import tiktoken
            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))
        except Exception:
            return max(1, len(text.encode("utf-8")))

    @staticmethod
    def _parse_seg_id(seg_id) -> Optional[int]:
        """Parse a segment ID matching the exact S<n> grammar.

        Accepts: S0, S1, S999
        Rejects: non-string, S+1, S 1, S١, S01, S-1, S1\\n, BAD, empty
        """
        if not isinstance(seg_id, str):
            return None
        m = _SEGMENT_ID_RE.fullmatch(seg_id)
        return int(m.group(1)) if m else None

    @staticmethod
    def _normalize_text(text: str) -> str:
        return " ".join(text.lower().split())

    @classmethod
    def _valid_segment_range(cls, entry: Dict) -> bool:
        """Check that start/end segment IDs are present, well-formed, and ordered."""
        start = cls._parse_seg_id(entry.get("start_segment"))
        end = cls._parse_seg_id(entry.get("end_segment"))
        if start is None or end is None:
            return False
        return end >= start

    @staticmethod
    def _validate_overview(raw: Dict) -> Dict:
        """Ensure the overview has the expected structure and safe value types.

        Malformed entries are dropped. Numeric fields are coerced to float
        where possible or defaulted. Segment ranges require valid S<n> IDs
        with end >= start. Missing top-level keys default to empty lists so
        downstream code never crashes on a bad model response.
        """
        validated: Dict = {
            "summary": str(raw.get("summary", "")),
            "main_themes": [],
            "sections": [],
            "high_interest_regions": [],
            "low_interest_regions": [],
        }

        vr = ThoughtSeedDetector._valid_segment_range

        for theme in raw.get("main_themes") or []:
            if (
                isinstance(theme, dict)
                and isinstance(theme.get("name"), str)
                and vr(theme)
            ):
                theme = dict(theme)
                theme["importance"] = _safe_float(theme.get("importance"), 0.5)
                validated["main_themes"].append(theme)

        for section in raw.get("sections") or []:
            if (
                isinstance(section, dict)
                and isinstance(section.get("summary"), str)
                and vr(section)
            ):
                validated["sections"].append(section)

        for region in raw.get("high_interest_regions") or []:
            if (
                isinstance(region, dict)
                and isinstance(region.get("reason"), str)
                and vr(region)
            ):
                region = dict(region)
                region["priority"] = _safe_float(region.get("priority"), 0.5)
                validated["high_interest_regions"].append(region)

        for region in raw.get("low_interest_regions") or []:
            if (
                isinstance(region, dict)
                and isinstance(region.get("reason"), str)
                and vr(region)
            ):
                validated["low_interest_regions"].append(region)

        return validated

    def _format_region_guidance(self, overview: Dict) -> str:
        """Format overview regions as density guidance for the detection prompt."""
        regions = overview.get("high_interest_regions", [])
        if not regions:
            return "No specific region guidance available — analyze the full transcript evenly."

        lines = ["REGION GUIDANCE (from your overview):"]
        for r in regions:
            start = r.get("start_segment", "?")
            end = r.get("end_segment", "?")
            reason = r.get("reason", "")
            priority = r.get("priority", 0.5)
            lines.append(f"  - {start}-{end} (priority {priority:.1f}): {reason}")
        lines.append("These are guidance, not exclusion rules. Great seeds outside these regions are welcome.")
        return "\n".join(lines)

    def _call_model(
        self,
        system: str,
        prompt: str,
        use_overview: bool = False,
    ) -> Dict:
        """Call the model with structured JSON output and retry."""
        chat = self._overview_chat if use_overview else self._chat
        response = retry_with_backoff(
            lambda: chat.complete(
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                response_mode=ResponseMode.JSON,
            )
        )

        self.metrics["api_calls"] += 1
        self.metrics["tokens_used"] += response.usage.total_tokens
        if response.usage.estimated_cost_usd is not None:
            self.metrics["cost_usd"] += float(response.usage.estimated_cost_usd)

        return response.parsed

    # ------------------------------------------------------------------
    # Deduplication (retained from original)
    # ------------------------------------------------------------------

    def _deduplicate_seeds(self, seeds: List[Dict]) -> List[Dict]:
        """Remove duplicate seeds by time proximity and text similarity."""
        if len(seeds) <= 1:
            return seeds

        sorted_seeds = sorted(seeds, key=lambda s: s.get("timestamp", 0))
        unique: List[Dict] = []

        for seed in sorted_seeds:
            is_dup = False
            for existing in unique:
                time_diff = abs(seed.get("timestamp", 0) - existing.get("timestamp", 0))
                if time_diff < DEDUP_TIME_THRESHOLD:
                    sim = self._text_similarity(seed.get("text", ""), existing.get("text", ""))
                    if sim > DEDUP_TEXT_THRESHOLD:
                        is_dup = True
                        if seed.get("interest_score", 0) > existing.get("interest_score", 0):
                            unique.remove(existing)
                            unique.append(seed)
                        break
            if not is_dup:
                unique.append(seed)

        return unique

    @staticmethod
    def _text_similarity(text1: str, text2: str) -> float:
        """Jaccard word similarity."""
        if not text1 or not text2:
            return 0.0
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union) if union else 0.0
