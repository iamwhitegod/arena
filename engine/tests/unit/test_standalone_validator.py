#!/usr/bin/env python3
"""
Unit Tests for arena.editorial.standalone_validator

Tests standalone validation logic using FakeChatModel.
"""

import unittest
import json
import sys
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from arena.editorial.thought_unit import ThoughtUnit, RhetoricalType, DependencyLevel
from arena.editorial.standalone_validator import StandaloneValidator
from arena.providers.base import ChatResponse, ProviderError, ProviderUsage
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


def make_standalone_response():
    """Helper to create a fake response for standalone content."""
    content = json.dumps({
        'is_standalone': True,
        'standalone_score': 0.95,
        'issues': [],
        'unresolved_references': [],
        'reasoning': 'Content is fully self-contained with clear context.',
        'confidence': 0.9,
    })
    return ChatResponse(
        content=content,
        parsed=json.loads(content),
        usage=ProviderUsage(
            input_tokens=250, output_tokens=50, total_tokens=300,
            estimated_cost_usd=Decimal("0.000165"),
        ),
    )


def make_needs_context_response():
    """Helper to create a fake response for content needing context."""
    content = json.dumps({
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
    return ChatResponse(
        content=content,
        parsed=json.loads(content),
        usage=ProviderUsage(
            input_tokens=280, output_tokens=70, total_tokens=350,
            estimated_cost_usd=Decimal("0.000198"),
        ),
    )


class TestStandaloneValidation(unittest.TestCase):
    """Test standalone validation logic."""

    def test_standalone_content_passes(self):
        """Content with no unresolved references should pass validation."""
        chat = FakeChatModel([make_standalone_response()])
        validator = StandaloneValidator(chat=chat)
        unit = make_thought_unit()
        result = validator.validate(unit)

        self.assertTrue(result['is_standalone'])
        self.assertGreater(result['standalone_score'], 0.8)
        self.assertEqual(len(result['issues']), 0)

    def test_context_dependent_content_fails(self):
        """Content with unresolved references should fail validation."""
        chat = FakeChatModel([make_needs_context_response()])
        validator = StandaloneValidator(chat=chat)
        unit = make_thought_unit(
            premise_text='He was talking about that idea earlier.',
            claim_text='And that is exactly why it matters.',
        )
        result = validator.validate(unit)

        self.assertFalse(result['is_standalone'])
        self.assertLess(result['standalone_score'], 0.5)
        self.assertGreater(len(result['issues']), 0)

    def test_metrics_tracked(self):
        """Metrics should track validated units and standalone counts."""
        chat = FakeChatModel([make_standalone_response()])
        validator = StandaloneValidator(chat=chat)
        unit = make_thought_unit()
        validator.validate(unit)

        self.assertEqual(validator.metrics['units_validated'], 1)
        self.assertEqual(validator.metrics['units_standalone'], 1)
        self.assertEqual(validator.metrics['units_need_context'], 0)

    def test_needs_context_metrics(self):
        """Needs-context results should increment the right counter."""
        chat = FakeChatModel([make_needs_context_response()])
        validator = StandaloneValidator(chat=chat)
        unit = make_thought_unit()
        validator.validate(unit)

        self.assertEqual(validator.metrics['units_validated'], 1)

    def test_api_error_returns_conservative_default(self):
        """API errors should return conservative defaults (assume not standalone)."""
        class FailingChat(FakeChatModel):
            def complete(self, *args, **kwargs):
                raise ProviderError("unavailable", code="unavailable", retryable=False)

        validator = StandaloneValidator(chat=FailingChat())
        unit = make_thought_unit()
        result = validator.validate(unit)

        self.assertFalse(result['is_standalone'])
        self.assertEqual(result['standalone_score'], 0.5)
        self.assertEqual(result['confidence'], 0.0)

    def test_api_error_does_not_crash(self):
        """API errors should be caught gracefully."""
        class FailingChat(FakeChatModel):
            def complete(self, *args, **kwargs):
                raise ConnectionError('Network error')

        validator = StandaloneValidator(chat=FailingChat())
        unit = make_thought_unit()

        # Should not raise
        result = validator.validate(unit)
        self.assertIn('issues', result)

    def test_uses_chat_model(self):
        """Validator should use the injected ChatModel."""
        chat = FakeChatModel([make_standalone_response()])
        validator = StandaloneValidator(chat=chat)
        unit = make_thought_unit(
            premise_text='First part.',
            claim_text='Second part.',
            resolution_text='Third part.',
        )
        validator.validate(unit)

        self.assertEqual(chat.call_count, 1)

    def test_multiple_validations_accumulate_metrics(self):
        """Multiple validations should accumulate metrics correctly."""
        responses = [make_standalone_response() for _ in range(3)]
        chat = FakeChatModel(responses)

        validator = StandaloneValidator(chat=chat)
        for _ in range(3):
            validator.validate(make_thought_unit())

        self.assertEqual(validator.metrics['units_validated'], 3)
        self.assertEqual(validator.metrics['units_standalone'], 3)

    def test_backward_compat_api_key(self):
        """api_key constructor path should still work."""
        validator = StandaloneValidator(api_key='sk-test')
        self.assertIsNotNone(validator._chat)


if __name__ == '__main__':
    unittest.main()
