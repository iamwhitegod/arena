"""Compact-model editorial path avoids cloud-scale per-seed inference."""

from arena.editorial.adapter import FourLayerAdapter
from arena.editorial.thought_unit import (
    DependencyLevel,
    RhetoricalType,
    ThoughtUnit,
)
from arena.editorial.thought_unit_constructor import ThoughtUnitConstructor
from arena.providers.fake import FakeChatModel


def test_compact_constructor_uses_grounded_deterministic_boundaries():
    chat = FakeChatModel(context_window_tokens=4_096, max_output_tokens=512)
    constructor = ThoughtUnitConstructor(chat=chat, verbose=False)
    segments = [
        {"start": float(index * 5), "end": float((index + 1) * 5),
         "text": f"Transcript sentence number {index} with enough context."}
        for index in range(20)
    ]
    seeds = [{
        "timestamp": 25.0,
        "text": "Transcript sentence number 5",
        "rhetorical_type": "insight",
        "interest_score": 0.9,
    }]

    units = constructor.construct_from_seeds(seeds, segments)

    assert chat.call_count == 0
    assert len(units) == 1
    assert 30.0 <= units[0].duration <= 60.0
    assert "sentence number 2" in units[0].premise_text
    assert "sentence number 8" in units[0].resolution_text


def test_compact_scoring_is_deterministic_and_model_free():
    unit = ThoughtUnit(
        premise_start=0.0,
        claim_peak=10.0,
        resolution_end=35.0,
        premise_text="A sufficiently clear premise introduces the topic.",
        claim_text="This is a strong and complete central claim.",
        resolution_text="The explanation resolves the claim with enough context.",
        rhetorical_type=RhetoricalType.INSIGHT,
        dependency_level=DependencyLevel.NEEDS_CONTEXT,
        claim_strength=9.0,
    )

    validations, scores = FourLayerAdapter._score_compact_units([unit])

    assert validations[0]["is_standalone"] is True
    assert scores[0]["completeness_score"] >= 0.85
    assert unit.dependency_level is DependencyLevel.STANDALONE
    assert unit.has_unresolved_refs is False
