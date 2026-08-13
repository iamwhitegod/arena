#!/usr/bin/env python3
"""
Unit Tests for arena.editorial.completeness_scorer

Tests completeness scoring logic with mocked OpenAI API calls.
"""

import unittest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arena.editorial.thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel
from arena.editorial.completeness_scorer import CompletenessScorer


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


def make_mock_response(premise=8.0, claim=7.5, resolution=7.0):
    """Helper to create a mock OpenAI API response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps({
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
    response.usage = MagicMock()
    response.usage.total_tokens = 500
    response.usage.prompt_tokens = 400
    response.usage.completion_tokens = 100
    return response


class TestCompletenessScoring(unittest.TestCase):
    """Test completeness score calculation logic."""

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_high_scores_meet_production_standard(self, mock_openai_cls, mock_retry):
        """Scores with all components >= 8.0 and avg >= 0.85 should meet production."""
        mock_retry.return_value = make_mock_response(premise=9.0, claim=8.5, resolution=8.0)

        scorer = CompletenessScorer(api_key='sk-test')
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertTrue(result['meets_production_standard'])
        self.assertAlmostEqual(result['completeness_score'], (9.0 + 8.5 + 8.0) / 30.0, places=2)

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_low_scores_fail_production_standard(self, mock_openai_cls, mock_retry):
        """Scores with any component < 8.0 should fail production."""
        mock_retry.return_value = make_mock_response(premise=8.0, claim=4.0, resolution=7.0)

        scorer = CompletenessScorer(api_key='sk-test')
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertFalse(result['meets_production_standard'])

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_completeness_formula(self, mock_openai_cls, mock_retry):
        """Completeness = (premise + claim + resolution) / 30."""
        mock_retry.return_value = make_mock_response(premise=6.0, claim=6.0, resolution=6.0)

        scorer = CompletenessScorer(api_key='sk-test')
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertAlmostEqual(result['completeness_score'], 18.0 / 30.0, places=4)

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_metrics_tracked(self, mock_openai_cls, mock_retry):
        """Metrics should track API calls and scores."""
        mock_retry.return_value = make_mock_response(premise=7.0, claim=7.0, resolution=7.0)

        scorer = CompletenessScorer(api_key='sk-test')
        unit = make_thought_unit()
        scorer.score(unit)

        self.assertEqual(scorer.metrics['api_calls'], 1)
        self.assertEqual(scorer.metrics['units_scored'], 1)
        self.assertGreater(scorer.metrics['tokens_used'], 0)
        self.assertGreater(scorer.metrics['cost_usd'], 0)

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_malformed_response_returns_defaults(self, mock_openai_cls, mock_retry):
        """Malformed JSON response should return safe defaults."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = 'not valid json'
        response.usage = MagicMock()
        response.usage.total_tokens = 100
        response.usage.prompt_tokens = 80
        response.usage.completion_tokens = 20
        mock_retry.return_value = response

        scorer = CompletenessScorer(api_key='sk-test')
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertEqual(result['premise_clarity'], 5.0)
        self.assertEqual(result['completeness_score'], 0.5)
        self.assertFalse(result['meets_production_standard'])

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_api_error_returns_conservative_defaults(self, mock_openai_cls, mock_retry):
        """API errors should return conservative defaults, not crash."""
        mock_retry.side_effect = Exception('API rate limit exceeded')

        scorer = CompletenessScorer(api_key='sk-test')
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertEqual(result['premise_clarity'], 5.0)
        self.assertEqual(result['claim_strength'], 5.0)
        self.assertEqual(result['resolution_closure'], 5.0)
        self.assertEqual(result['completeness_score'], 0.5)
        self.assertFalse(result['meets_production_standard'])

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_missing_fields_use_defaults(self, mock_openai_cls, mock_retry):
        """Missing fields in JSON response should use 5.0 default."""
        response = MagicMock()
        response.choices = [MagicMock()]
        response.choices[0].message.content = json.dumps({
            'premise_clarity': 9.0,
            # claim_strength and resolution_closure missing
        })
        response.usage = MagicMock()
        response.usage.total_tokens = 100
        response.usage.prompt_tokens = 80
        response.usage.completion_tokens = 20
        mock_retry.return_value = response

        scorer = CompletenessScorer(api_key='sk-test')
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertEqual(result['premise_clarity'], 9.0)
        self.assertEqual(result['claim_strength'], 5.0)  # default
        self.assertEqual(result['resolution_closure'], 5.0)  # default

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_score_batch(self, mock_openai_cls, mock_retry):
        """score_batch should score all units and return list."""
        mock_retry.return_value = make_mock_response(premise=7.0, claim=7.0, resolution=7.0)

        scorer = CompletenessScorer(api_key='sk-test')
        units = [make_thought_unit() for _ in range(3)]
        scores = scorer.score_batch(units, verbose=False)

        self.assertEqual(len(scores), 3)
        self.assertEqual(scorer.metrics['units_scored'], 3)

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_update_thought_units(self, mock_openai_cls, mock_retry):
        """update_thought_units should write scores back to ThoughtUnit objects."""
        scorer = CompletenessScorer(api_key='sk-test')
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

    @patch('arena.editorial.completeness_scorer.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_production_requires_all_components_above_threshold(self, mock_openai_cls, mock_retry):
        """Even if average is >= 0.85, all components must be >= 8.0."""
        mock_retry.return_value = make_mock_response(premise=9.5, claim=9.5, resolution=7.5)

        scorer = CompletenessScorer(api_key='sk-test')
        unit = make_thought_unit()
        result = scorer.score(unit)

        self.assertFalse(result['meets_production_standard'])


if __name__ == '__main__':
    unittest.main()
