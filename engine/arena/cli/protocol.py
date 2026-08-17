"""Structured stdout protocol shared by the Python engine and Node CLI."""

import json
import re
import sys
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from typing import Any, Iterator, TextIO


def emit(event_type: str, **payload: Any) -> None:
    sys.__stdout__.write(json.dumps({"type": event_type, **payload}) + "\n")
    sys.__stdout__.flush()


def progress(stage: str, percent: float | None, message: str) -> None:
    value = None if percent is None else max(0, min(100, percent))
    emit("progress", stage=stage, progress=value, message=message)


def result(data: dict[str, Any]) -> None:
    emit("result", data=data)


class PipelineEventStream:
    """Translate the legacy pipeline's useful milestones into protocol events.

    The pipeline still supports direct human-readable execution. Only the Node
    bridge wraps it with this stream, making stdout a machine-readable channel.
    """

    _ansi_escape = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
    _stage_headers = {
        "Transcription": ("transcription", "Preparing audio"),
        "Hybrid Analysis": ("analysis", "Initializing analyzers"),
        "Professional Editing": ("alignment", "Preparing clip alignment"),
        "Clip Generation": ("generation", "Preparing clip generation"),
        "Platform Formatting": ("formatting", "Preparing platform formatting"),
    }

    def __init__(self) -> None:
        self._buffer = ""
        self._current_stage: str | None = None
        self._last_progress: dict[str, int] = {}
        self._last_message: dict[str, str] = {}
        self._last_mode: dict[str, str] = {}
        self._transcription_chunks: int | None = None
        # Capture the original diagnostic stream before redirect_stderr is used.
        self._diagnostic_output = sys.stderr

    def diagnostics(self) -> "PipelineDiagnosticStream":
        """Return a stream that parses tqdm updates and preserves diagnostics."""
        return PipelineDiagnosticStream(self, self._diagnostic_output)

    @contextmanager
    def capture(self) -> Iterator[None]:
        """Capture legacy output and always flush pending protocol events."""
        diagnostic_stream = self.diagnostics()
        try:
            with redirect_stdout(self), redirect_stderr(diagnostic_stream):
                yield
        finally:
            self.flush()
            diagnostic_stream.flush()

    def write(self, value: str) -> int:
        self._buffer += value
        parts = re.split(r"[\r\n]", self._buffer)
        self._buffer = parts.pop()
        for line in parts:
            self._handle(line)
        return len(value)

    def flush(self) -> None:
        if self._buffer.strip():
            self._handle(self._buffer)
        self._buffer = ""
        sys.__stdout__.flush()

    def _publish(self, stage: str, percent: float, message: str) -> None:
        """Publish a monotonic, de-duplicated stage-local progress event."""
        rounded_percent = max(0, min(100, int(percent + 0.5)))
        rounded_percent = max(self._last_progress.get(stage, 0), rounded_percent)
        if (
            self._last_progress.get(stage) == rounded_percent
            and self._last_message.get(stage) == message
            and self._last_mode.get(stage) == "determinate"
        ):
            return

        self._last_progress[stage] = rounded_percent
        self._last_message[stage] = message
        self._last_mode[stage] = "determinate"
        progress(stage, rounded_percent, message)

    def _publish_indeterminate(self, stage: str, message: str) -> None:
        """Publish an honest waiting state when the operation exposes no percent."""
        if (
            self._last_mode.get(stage) == "indeterminate"
            and self._last_message.get(stage) == message
        ):
            return

        self._last_message[stage] = message
        self._last_mode[stage] = "indeterminate"
        progress(stage, None, message)

    @staticmethod
    def _scaled_progress(raw_percent: float, start: int, end: int) -> int:
        scaled = start + (max(0, min(100, raw_percent)) / 100) * (end - start)
        return int(scaled + 0.5)

    def _handle_tqdm(self, line: str) -> bool:
        match = re.search(
            r"(Transcribing|Initializing|Generating clips|Thumbnails):\s*(\d{1,3})%",
            line,
            re.IGNORECASE,
        )
        if not match:
            return False

        label = match.group(1).lower()
        raw_percent = int(match.group(2))
        if label == "transcribing":
            if raw_percent >= 100:
                self._publish("transcription", 95, "Finalizing transcription")
            elif raw_percent == 0:
                self._publish("transcription", 30, "Preparing transcription")
            else:
                self._publish_indeterminate("transcription", "Transcribing audio")
        elif label == "initializing":
            self._publish(
                "analysis",
                self._scaled_progress(raw_percent, 2, 10),
                "Initializing analyzers",
            )
        elif label == "generating clips":
            self._publish(
                "generation",
                self._scaled_progress(raw_percent, 10, 75),
                "Generating clips",
            )
        else:
            self._publish(
                "generation",
                self._scaled_progress(raw_percent, 75, 95),
                "Generating thumbnails",
            )
        return True

    def _handle_counted_item(self, line: str) -> bool:
        match = re.search(r"\[(\d+)/(\d+)\]", line)
        if not match or self._current_stage not in {"generation", "formatting"}:
            return False

        current, total = (int(value) for value in match.groups())
        if total <= 0:
            return False

        if self._current_stage == "generation":
            self._publish(
                "generation",
                self._scaled_progress((current / total) * 100, 10, 75),
                f"Generated clip {current} of {total}",
            )
        else:
            self._publish(
                "formatting",
                self._scaled_progress((current / total) * 100, 10, 95),
                f"Formatted clip {current} of {total}",
            )
        return True

    def _handle_transcription(self, line: str) -> bool:
        milestones = (
            ("Enhancing audio quality", 5, "Extracting audio"),
            ("Applying noise reduction", 10, "Enhancing audio"),
            ("Using cached enhanced audio", 25, "Using cached enhanced audio"),
            ("Audio enhanced and cached", 25, "Audio enhancement complete"),
            ("Audio enhancement failed", 25, "Using original audio"),
            ("Audio file is", 30, "Checking transcription limits"),
            ("Chunking audio", 35, "Preparing audio chunks"),
        )
        for needle, percent, message in milestones:
            if needle.lower() in line.lower():
                self._publish("transcription", percent, message)
                return True

        if "transcribing video" in line.lower() or "transcribing audio" in line.lower():
            self._publish_indeterminate("transcription", "Transcribing audio")
            return True

        split_match = re.search(
            r"Splitting .* into (?:approximately )?(\d+) chunks?",
            line,
            re.IGNORECASE,
        )
        if split_match:
            self._transcription_chunks = int(split_match.group(1))
            self._publish(
                "transcription",
                40,
                f"Prepared {self._transcription_chunks} audio chunk(s)",
            )
            return True

        chunk_match = re.search(
            r"Transcribing chunk (\d+)(?:/(\d+))?",
            line,
            re.IGNORECASE,
        )
        if chunk_match:
            current = int(chunk_match.group(1))
            explicit_total = chunk_match.group(2)
            total = int(explicit_total) if explicit_total else self._transcription_chunks
            total = max(total or current, current, 1)
            percent = 40 + ((current - 1) / total) * 50
            self._publish(
                "transcription",
                percent,
                f"Transcribing chunk {current} of {total}",
            )
            self._publish_indeterminate(
                "transcription",
                f"Transcribing chunk {current} of {total}",
            )
            return True

        if re.search(r"Transcription complete \(\d+ chunks? merged\)", line, re.IGNORECASE):
            self._publish("transcription", 95, "Merging transcript chunks")
            return True
        if "Using cached transcript".lower() in line.lower():
            self._publish("transcription", 100, "Using cached transcript")
            return True
        if "Transcription complete".lower() in line.lower():
            self._publish("transcription", 100, "Transcription complete")
            return True
        return False

    def _handle_analysis(self, line: str) -> bool:
        milestones = (
            ("Loading inference models", 2, "Loading local inference models", True),
            ("Initializing analyzers", 2, "Initializing analyzers", False),
            ("Running hybrid analysis", 10, "Starting hybrid analysis", False),
            ("Analyzing transcript content", 15, "Analyzing transcript with AI", True),
            ("Week 1: Detecting Thought Seeds", 20, "Detecting thought seeds", False),
            ("Generating content overview", 22, "Generating content overview", True),
            ("Overview complete", 25, "Content overview complete", False),
            ("Detecting seeds", 28, "Detecting thought seeds", True),
            ("Detected ", 35, "Thought seed detection complete", False),
            ("Week 2: Constructing ThoughtUnits", 40, "Constructing thought units", True),
            ("Constructed ", 55, "Thought unit construction complete", False),
            ("Week 3: Completeness Validation", 60, "Validating completeness", False),
            ("Running standalone validation", 62, "Validating standalone context", True),
            ("Standalone validation:", 68, "Standalone validation complete", False),
            ("Running completeness scoring", 70, "Scoring completeness", True),
            ("Average completeness", 78, "Completeness scoring complete", False),
            ("Week 4: Deduplication", 80, "Deduplicating candidates", True),
            ("Clustering:", 88, "Candidate clustering complete", False),
            ("Selected top ", 92, "Selecting final candidates", False),
            ("Analyzing audio energy", 94, "Analyzing audio energy", True),
            ("Computing hybrid scores", 97, "Computing hybrid scores", False),
            ("Analysis complete", 100, "Analysis complete", False),
        )
        for needle, percent, message, indeterminate in milestones:
            if needle.lower() in line.lower():
                self._publish("analysis", percent, message)
                if indeterminate:
                    self._publish_indeterminate("analysis", message)
                return True
        return False

    def _handle_alignment(self, line: str) -> bool:
        milestones = (
            ("Aligning clips to sentence boundaries", 10, "Aligning clip boundaries", True),
            ("Found ", 25, "Sentence boundaries detected", False),
            ("Detecting scene changes", 35, "Detecting scene changes", True),
            ("Aligned ", 90, "Clip boundaries aligned", False),
            ("Professional Editing Report", 95, "Saving alignment results", False),
            ("Alignment failed", 100, "Using original clip boundaries", False),
        )
        for needle, percent, message, indeterminate in milestones:
            if needle.lower() in line.lower():
                self._publish("alignment", percent, message)
                if indeterminate:
                    self._publish_indeterminate("alignment", message)
                return True
        return False

    def _handle_generation(self, line: str) -> bool:
        milestones = (
            ("Using enhanced audio for clips", 5, "Preparing enhanced clip audio"),
            ("Video Info:", 8, "Inspecting source video"),
            ("Generating thumbnails and metadata", 75, "Generating thumbnails"),
            ("Clip generation complete", 100, "Clip generation complete"),
        )
        for needle, percent, message in milestones:
            if needle.lower() in line.lower():
                self._publish("generation", percent, message)
                return True

        match = re.search(r"Generating (\d+) clips", line, re.IGNORECASE)
        if match:
            self._publish("generation", 10, f"Generating {match.group(1)} clips")
            return True
        return False

    def _handle_formatting(self, line: str) -> bool:
        if line.lower().startswith("target:"):
            self._publish("formatting", 5, "Loading platform specification")
            return True
        if line.lower().startswith("output:"):
            self._publish("formatting", 10, "Preparing formatted output")
            return True
        if "formatted " in line.lower():
            self._publish("formatting", 100, "Platform formatting complete")
            return True
        if "Platform formatting failed" in line:
            self._publish("formatting", 100, "Platform formatting skipped")
            return True
        return False

    def _handle(self, line: str) -> bool:
        line = self._ansi_escape.sub("", line).strip()
        if not line:
            return True
        for label, (stage, message) in self._stage_headers.items():
            if re.search(rf"\[\d+/\d+\].*{re.escape(label)}", line):
                self._current_stage = stage
                self._publish(stage, 1, message)
                return True

        if self._handle_tqdm(line) or self._handle_counted_item(line):
            return True
        if self._current_stage == "transcription" and self._handle_transcription(line):
            return True
        if self._current_stage == "analysis" and self._handle_analysis(line):
            return True
        if self._current_stage == "alignment" and self._handle_alignment(line):
            return True
        if self._current_stage == "generation" and self._handle_generation(line):
            return True
        if self._current_stage == "formatting" and self._handle_formatting(line):
            return True

        if "❌" in line or line.lower().startswith("error:"):
            self._diagnostic_output.write(line + "\n")
            self._diagnostic_output.flush()
            return True
        return False


class PipelineDiagnosticStream:
    """Parse carriage-return progress output while preserving real stderr."""

    def __init__(self, event_stream: PipelineEventStream, output: TextIO) -> None:
        self._event_stream = event_stream
        self._output = output
        self._buffer = ""

    def write(self, value: str) -> int:
        self._buffer += value
        parts = re.split(r"[\r\n]", self._buffer)
        self._buffer = parts.pop()
        for line in parts:
            self._handle(line)
        return len(value)

    def _handle(self, line: str) -> None:
        if line and not self._event_stream._handle(line):
            self._output.write(line + "\n")
            self._output.flush()

    def flush(self) -> None:
        if self._buffer:
            self._handle(self._buffer)
        self._buffer = ""
        self._output.flush()
