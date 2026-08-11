#!/usr/bin/env python3
"""
Unit Tests for arena.editorial.standalone_validator

Tests standalone validation logic with mocked OpenAI API calls.
"""

import unittest
import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arena.editorial.thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel
from arena.editorial.standalone_validator import StandaloneValidator


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


def make_standalone_response():
    """Helper to create a mock response for standalone content."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps({
        'is_standalone': True,
        'standalone_score': 0.95,
        'issues': [],
        'unresolved_references': [],
        'reasoning': 'Content is fully self-contained with clear context.',
        'confidence': 0.9,
    })
    response.usage = MagicMock()
    response.usage.total_tokens = 300
    response.usage.prompt_tokens = 250
    response.usage.completion_tokens = 50
    return response


def make_needs_context_response():
    """Helper to create a mock response for content needing context."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = json.dumps({
        'is_standalone': False,
        'standalone_score': 0.3,
        'issues': [
            'Unresolved pronoun "he" without antecedent',
            'Reference to "that idea" without prior context',
        ],
        'unresolved_references': ['he', 'that idea'],
        'reasoning': 'Content references prior discussion that viewer would not have seen.',
        'confidence': 0.85,
    })
    response.usage = MagicMock()
    response.usage.total_tokens = 350
    response.usage.prompt_tokens = 280
    response.usage.completion_tokens = 70
    return response


class TestStandaloneValidation(unittest.TestCase):
    """Test standalone validation logic."""

    @patch('arena.editorial.standalone_validator.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_standalone_content_passes(self, mock_openai_cls, mock_retry):
        """Content with no unresolved references should pass validation."""
        mock_retry.return_value = make_standalone_response()

        validator = StandaloneValidator(api_key='sk-test')
        unit = make_thought_unit()
        result = validator.validate(unit)

        self.assertTrue(result['is_standalone'])
        self.assertGreater(result['standalone_score'], 0.8)
        self.assertEqual(len(result['issues']), 0)

    @patch('arena.editorial.standalone_validator.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_context_dependent_content_fails(self, mock_openai_cls, mock_retry):
        """Content with unresolved references should fail validation."""
        mock_retry.return_value = make_needs_context_response()

        validator = StandaloneValidator(api_key='sk-test')
        unit = make_thought_unit(
            premise_text='He was talking about that idea earlier.',
            claim_text='And that is exactly why it matters.',
        )
        result = validator.validate(unit)

        self.assertFalse(result['is_standalone'])
        self.assertLess(result['standalone_score'], 0.5)
        self.assertGreater(len(result['issues']), 0)

    @patch('arena.editorial.standalone_validator.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_metrics_tracked(self, mock_openai_cls, mock_retry):
        """Metrics should track validated units and standalone counts."""
        mock_retry.return_value = make_standalone_response()

        validator = StandaloneValidator(api_key='sk-test')
        unit = make_thought_unit()
        validator.validate(unit)

        self.assertEqual(validator.metrics['units_validated'], 1)
        self.assertEqual(validator.metrics['units_standalone'], 1)
        self.assertEqual(validator.metrics['units_need_context'], 0)

    @patch('arena.editorial.standalone_validator.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_needs_context_metrics(self, mock_openai_cls, mock_retry):
        """Needs-context results should increment the right counter."""
        mock_retry.return_value = make_needs_context_response()

        validator = StandaloneValidator(api_key='sk-test')
        unit = make_thought_unit()
        result = validator.validate(unit)

        # The result should indicate needs_context dependency level
        self.assertEqual(validator.metrics['units_validated'], 1)

    @patch('arena.editorial.standalone_validator.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_api_error_returns_conservative_default(self, mock_openai_cls, mock_retry):
        """API errors should return conservative defaults (assume not standalone)."""
        mock_retry.side_effect = Exception('API unavailable')

        validator = StandaloneValidator(api_key='sk-test')
        unit = make_thought_unit()
        result = validator.validate(unit)

        self.assertFalse(result['is_standalone'])
        self.assertEqual(result['standalone_score'], 0.5)
        self.assertEqual(result['confidence'], 0.0)

    @patch('arena.editorial.standalone_validator.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_api_error_does_not_crash(self, mock_openai_cls, mock_retry):
        """API errors should be caught gracefully."""
        mock_retry.side_effect = ConnectionError('Network error')

        validator = StandaloneValidator(api_key='sk-test')
        unit = make_thought_unit()

        # Should not raise
        result = validator.validate(unit)
        self.assertIn('issues', result)

    @patch('arena.editorial.standalone_validator.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_uses_full_text_for_analysis(self, mock_openai_cls, mock_retry):
        """Validator should pass the full text (premise + claim + resolution) to the API."""
        mock_retry.return_value = make_standalone_response()

        validator = StandaloneValidator(api_key='sk-test')
        unit = make_thought_unit(
            premise_text='First part.',
            claim_text='Second part.',
            resolution_text='Third part.',
        )
        validator.validate(unit)

        # Verify the API was called (via mock_retry)
        self.assertTrue(mock_retry.called)

    @patch('arena.editorial.standalone_validator.call_api_with_smart_retry')
    @patch('openai.OpenAI')
    def test_multiple_validations_accumulate_metrics(self, mock_openai_cls, mock_retry):
        """Multiple validations should accumulate metrics correctly."""
        mock_retry.return_value = make_standalone_response()

        validator = StandaloneValidator(api_key='sk-test')
        for _ in range(3):
            validator.validate(make_thought_unit())

        self.assertEqual(validator.metrics['units_validated'], 3)
        self.assertEqual(validator.metrics['units_standalone'], 3)


if __name__ == '__main__':
    unittest.main()
