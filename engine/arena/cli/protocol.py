"""Structured stdout protocol shared by the Python engine and Node CLI."""

import json
import re
import sys
from typing import Any


def emit(event_type: str, **payload: Any) -> None:
    sys.__stdout__.write(json.dumps({"type": event_type, **payload}) + "\n")
    sys.__stdout__.flush()


def progress(stage: str, percent: float, message: str) -> None:
    emit("progress", stage=stage, progress=max(0, min(100, percent)), message=message)


def result(data: dict[str, Any]) -> None:
    emit("result", data=data)


class PipelineEventStream:
    """Translate the legacy pipeline's useful milestones into protocol events.

    The pipeline still supports direct human-readable execution. Only the Node
    bridge wraps it with this stream, making stdout a machine-readable channel.
    """

    _stage_headers = {
        "Transcription": ("transcription", 5, "Preparing audio"),
        "Hybrid Analysis": ("analysis", 25, "Analyzing transcript and audio"),
        "Professional Editing": ("alignment", 65, "Refining clip boundaries"),
        "Clip Generation": ("generation", 80, "Generating clips"),
        "Platform Formatting": ("formatting", 90, "Formatting clips for the target platform"),
    }

    def __init__(self) -> None:
        self._buffer = ""

    def write(self, value: str) -> int:
        self._buffer += value
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._handle(line.strip())
        return len(value)

    def flush(self) -> None:
        if self._buffer.strip():
            self._handle(self._buffer.strip())
        self._buffer = ""
        sys.__stdout__.flush()

    def _handle(self, line: str) -> None:
        if not line:
            return
        if "❌" in line or line.lower().startswith("error:"):
            sys.stderr.write(line + "\n")
            sys.stderr.flush()
            return
        for label, (stage, percent, message) in self._stage_headers.items():
            if re.search(rf"\[\d+/\d+\].*{re.escape(label)}", line):
                progress(stage, percent, message)
                return
        milestones = (
            ("Using cached transcript", "transcription", 100, "Using cached transcript"),
            ("Transcription complete", "transcription", 100, "Transcription complete"),
            ("Analysis complete", "analysis", 100, "Analysis complete"),
            ("alignment complete", "alignment", 100, "Clip boundaries aligned"),
            ("Clip generation complete", "generation", 100, "Clip generation complete"),
            ("Formatted ", "formatting", 100, "Platform formatting complete"),
            ("Generating clip", "generation", 85, "Generating clips"),
        )
        for needle, stage, percent, message in milestones:
            if needle.lower() in line.lower():
                progress(stage, percent, message)
                return
