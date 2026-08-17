import io
import sys

from arena.cli import protocol


def collect_progress(monkeypatch):
    events = []
    monkeypatch.setattr(
        protocol,
        "progress",
        lambda stage, percent, message: events.append((stage, percent, message)),
    )
    return events


def test_pipeline_stream_emits_stage_local_transcription_progress(monkeypatch):
    events = collect_progress(monkeypatch)
    stream = protocol.PipelineEventStream()

    stream.write("[1/4] 📝 Transcription\n")
    stream.write("🎧 Enhancing audio quality...\n")
    stream.write("   Applying noise reduction and volume normalization...\n")
    stream.write("✓ Audio enhanced and cached\n")
    stream.write("⚠️  Audio file is 47.7MB (limit: 25MB)\n")
    stream.write("   Chunking audio into smaller segments...\n")
    stream.write("   Splitting 20.0 minutes into 2 chunks...\n")
    stream.write("   Transcribing chunk 1/2 (0.0-10.0 min)...\n")
    stream.write("   Transcribing chunk 2/2 (10.0-20.0 min)...\n")
    stream.write("   ✓ Transcription complete (2 chunks merged)\n")
    stream.write("✓ Transcription complete\n")

    assert [event[1] for event in events] == [
        1, 5, 10, 25, 30, 35, 40, 40, None, 65, None, 95, 100
    ]
    assert events[-1] == ("transcription", 100, "Transcription complete")


def test_pipeline_stream_parses_carriage_return_tqdm_updates(monkeypatch):
    events = collect_progress(monkeypatch)
    stream = protocol.PipelineEventStream()
    diagnostics = stream.diagnostics()

    stream.write("[4/4] ✂️  Video Clip Generation\n")
    diagnostics.write("✂️  Generating clips:   0%|          | 0/4\r")
    diagnostics.write("✂️  Generating clips:  50%|█████     | 2/4\r")
    diagnostics.write("✂️  Generating clips: 100%|██████████| 4/4\n")

    assert [event[1] for event in events] == [1, 10, 43, 75]
    assert events[-1] == ("generation", 75, "Generating clips")


def test_pipeline_stream_uses_real_item_counts(monkeypatch):
    events = collect_progress(monkeypatch)
    stream = protocol.PipelineEventStream()

    stream.write("[5/5] 📐 Platform Formatting (tiktok)\n")
    stream.write("Target: TikTok (1080x1920, 9:16)\n")
    stream.write("Output: /tmp/formatted\n")
    stream.write("  [1/4] ✅ clip-1.mp4\n")
    stream.write("  [2/4] ✅ clip-2.mp4\n")
    stream.write("  [4/4] ✅ clip-4.mp4\n")
    stream.write("✓ Formatted 4/4 clips for TikTok\n")

    assert [event[1] for event in events] == [1, 5, 10, 31, 53, 95, 100]


def test_pipeline_stream_never_regresses_progress(monkeypatch):
    events = collect_progress(monkeypatch)
    stream = protocol.PipelineEventStream()

    stream.write("[2/4] 🧠 Hybrid Analysis (AI + Energy)\n")
    stream.write("[3/4] 🎯 Week 3: Completeness Validation & Scoring\n")
    stream.write("[2/4] 🏗️ Week 2: Constructing ThoughtUnits\n")

    assert [event[1] for event in events] == [1, 60, 60, None]


def test_diagnostic_stream_preserves_non_progress_output(monkeypatch):
    collect_progress(monkeypatch)
    stream = protocol.PipelineEventStream()
    output = io.StringIO()
    diagnostics = protocol.PipelineDiagnosticStream(stream, output)

    diagnostics.write("UserWarning: possible clipped samples\n")

    assert output.getvalue() == "UserWarning: possible clipped samples\n"


def test_capture_reads_stdout_and_carriage_return_stderr(monkeypatch):
    events = collect_progress(monkeypatch)
    diagnostics = io.StringIO()
    monkeypatch.setattr(sys, "stderr", diagnostics)
    stream = protocol.PipelineEventStream()

    with stream.capture():
        print("[1/4] 📝 Transcription")
        sys.stderr.write("🎤 Transcribing:  20%|██        | 00:08\r")

    assert [event[1] for event in events] == [1, None]
    assert events[-1] == ("transcription", None, "Transcribing audio")
    assert diagnostics.getvalue() == ""


def test_pipeline_stream_marks_opaque_analysis_calls_indeterminate(monkeypatch):
    events = collect_progress(monkeypatch)
    stream = protocol.PipelineEventStream()

    stream.write("[2/4] 🧠 Hybrid Analysis (AI + Energy)\n")
    stream.write("🧠 Analyzing transcript content with AI...\n")
    stream.write("[1/4] 🌱 Week 1: Detecting Thought Seeds\n")
    stream.write("      Generating content overview...\n")
    stream.write("      Overview complete\n")

    assert [event[1] for event in events] == [1, 15, None, 20, 22, None, 25]


def test_pipeline_stream_marks_local_model_loading_indeterminate(monkeypatch):
    events = collect_progress(monkeypatch)
    stream = protocol.PipelineEventStream()

    stream.write("[2/4] 🧠 Hybrid Analysis (AI + Energy)\n")
    stream.write("🔧 Loading inference models...\n")

    assert events == [
        ("analysis", 1, "Initializing analyzers"),
        ("analysis", 2, "Loading local inference models"),
        ("analysis", None, "Loading local inference models"),
    ]
