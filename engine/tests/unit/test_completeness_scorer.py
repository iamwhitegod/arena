#!/usr/bin/env python3
"""
Unit Tests for arena.editorial.completeness_scorer

Tests completeness scoring logic using FakeChatModel.
"""

import unittest
import json
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arena.editorial.thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel
from arena.editorial.completeness_scorer import CompletenessScorer
from arena.providers.base import ChatResponse, ProviderUsage
from arena.providers.fake import FakeChatModel


def make_thought_unit(**kwargs):
    """Helper to create a ThoughtUnit with defaults."""
    defaults = {
        'premise_start': 10.0,
        'claim_peak': 25.0,
        'resolution_end': 40.0,
        'premise_text': 'People often think success comes from talent alone.',
        'claim_text': 'But the research shows that deliberate practice is the primary driver of expertise.',
        'resolution_text': 'So the real question is not whether you have talent, but whether you are willing to put in the work.',
        'rhetorical_type': RhetoricalType.ARGUMENT,
        'dependency_level': DependencyLevel.STANDALONE,
    }
    defaults.update(kwargs)
    return ThoughtUnit(**defaults)


def make_score_response(premise=8.0, claim=7.5, resolution=7.0):
    """Helper to create a fake ChatResponse with scoring JSON."""
    content = json.dumps({
        'premise_clarity': premise,
        'claim_strength': claim,
        'resolution_closure': resolution,
        'reasoning': {
            'premise': 'Clear setup',
            'claim': 'Strong insight',
            'resolution': 'Good closure',
        },
        'suggestions': ['Minor polish needed'],
    })
    return ChatResponse(
        content=content,
        parsed=json.loads(content),
        usage=ProviderUsage(
            input_tokens=400,
            output_tokens=100,
            total_tokens=500,
            estimated_cost_usd=Decimal("0.000285"),
        ),
    )


class TestCompletenessScoring(unittest.TestCase):
    """Test completeness score calculation logic."""

    def test_high_scores_meet_production_standard(self):
        """Scores with all components >= 8.0 and avg >= 0.85 should meet production."""
        chat = FakeChatModel([make_score_response(premise=9.0, claim=8.5, resolution=8.0)])
        scorer = CompletenessScorer(chat=chat)
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertTrue(result['meets_production_standard'])
        self.assertAlmostEqual(result['completeness_score'], (9.0 + 8.5 + 8.0) / 30.0, places=2)

    def test_low_scores_fail_production_standard(self):
        """Scores with any component < 8.0 should fail production."""
        chat = FakeChatModel([make_score_response(premise=8.0, claim=4.0, resolution=7.0)])
        scorer = CompletenessScorer(chat=chat)
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertFalse(result['meets_production_standard'])

    def test_completeness_formula(self):
        """Completeness = (premise + claim + resolution) / 30."""
        chat = FakeChatModel([make_score_response(premise=6.0, claim=6.0, resolution=6.0)])
        scorer = CompletenessScorer(chat=chat)
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertAlmostEqual(result['completeness_score'], 18.0 / 30.0, places=4)

    def test_metrics_tracked(self):
        """Metrics should track API calls and scores."""
        chat = FakeChatModel([make_score_response(premise=7.0, claim=7.0, resolution=7.0)])
        scorer = CompletenessScorer(chat=chat)
        unit = make_thought_unit()
        scorer.score(unit)

        self.assertEqual(scorer.metrics['api_calls'], 1)
        self.assertEqual(scorer.metrics['units_scored'], 1)
        self.assertGreater(scorer.metrics['tokens_used'], 0)
        self.assertGreater(scorer.metrics['cost_usd'], 0)

    def test_api_error_returns_conservative_defaults(self):
        """API errors should return conservative defaults, not crash."""
        from arena.providers.base import ProviderError

        class FailingChat(FakeChatModel):
            def complete(self, *args, **kwargs):
                raise ProviderError("rate limit", code="rate_limit", retryable=False)

        scorer = CompletenessScorer(chat=FailingChat())
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertEqual(result['premise_clarity'], 5.0)
        self.assertEqual(result['claim_strength'], 5.0)
        self.assertEqual(result['resolution_closure'], 5.0)
        self.assertEqual(result['completeness_score'], 0.5)
        self.assertFalse(result['meets_production_standard'])

    def test_missing_fields_use_defaults(self):
        """Missing fields in JSON response should use 5.0 default."""
        content = json.dumps({'premise_clarity': 9.0})
        chat = FakeChatModel([ChatResponse(
            content=content,
            parsed=json.loads(content),
            usage=ProviderUsage(input_tokens=80, output_tokens=20, total_tokens=100,
                                estimated_cost_usd=Decimal("0.000060")),
        )])

        scorer = CompletenessScorer(chat=chat)
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertEqual(result['premise_clarity'], 9.0)
        self.assertEqual(result['claim_strength'], 5.0)  # default
        self.assertEqual(result['resolution_closure'], 5.0)  # default

    def test_score_batch(self):
        """score_batch should score all units and return list."""
        responses = [make_score_response(premise=7.0, claim=7.0, resolution=7.0) for _ in range(3)]
        chat = FakeChatModel(responses)

        scorer = CompletenessScorer(chat=chat)
        units = [make_thought_unit() for _ in range(3)]
        scores = scorer.score_batch(units, verbose=False)

        self.assertEqual(len(scores), 3)
        self.assertEqual(scorer.metrics['units_scored'], 3)

    def test_update_thought_units(self):
        """update_thought_units should write scores back to ThoughtUnit objects."""
        scorer = CompletenessScorer(chat=FakeChatModel())
        unit = make_thought_unit()
        scores = [{
            'premise_clarity': 8.0,
            'claim_strength': 9.0,
            'resolution_closure': 7.5,
            'completeness_score': 0.82,
            'reasoning': {'premise': 'good'},
            'suggestions': [],
            'meets_production_standard': True,
        }]

        updated = scorer.update_thought_units([unit], scores)

        self.assertEqual(updated[0].premise_clarity, 8.0)
        self.assertEqual(updated[0].claim_strength, 9.0)
        self.assertEqual(updated[0].resolution_closure, 7.5)
        self.assertEqual(updated[0].completeness_score, 0.82)

    def test_production_requires_all_components_above_threshold(self):
        """Even if average is >= 0.85, all components must be >= 8.0."""
        chat = FakeChatModel([make_score_response(premise=9.5, claim=9.5, resolution=7.5)])
        scorer = CompletenessScorer(chat=chat)
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertFalse(result['meets_production_standard'])

    def test_backward_compat_api_key(self):
        """api_key constructor path should still work."""
        scorer = CompletenessScorer(api_key='sk-test')
        self.assertIsNotNone(scorer._chat)


if __name__ == '__main__':
    unittest.main()
