"""Boundary tests for untrusted editorial model output."""

import unittest

from arena.editorial.premise_detector import PremiseDetector
from arena.editorial.resolution_detector import ResolutionDetector
from arena.providers.base import ChatResponse
from arena.providers.fake import FakeChatModel


class TestEditorialOutputValidation(unittest.TestCase):

    def test_premise_index_must_be_a_strict_integer(self):
        context = {
            "before_segments": [{"start": 0.0, "end": 1.0, "text": "setup"}],
        }
        for invalid in (True, "0", 1.5, None):
            with self.subTest(value=invalid):
                response = ChatResponse(
                    content="{}",
                    parsed={"premise_start_index": invalid, "confidence": 0.9},
                )
                detector = PremiseDetector(chat=FakeChatModel([response]))
                self.assertIsNone(
                    detector._analyze_premise("claim", "argument", context)
                )

    def test_resolution_requires_a_strict_boolean(self):
        context = {
            "after_segments": [{"start": 1.0, "end": 2.0, "text": "ending"}],
        }
        for invalid in ("false", 0, 1, None):
            with self.subTest(value=invalid):
                response = ChatResponse(
                    content="{}",
                    parsed={
                        "resolution_end_index": 0,
                        "is_complete": invalid,
                        "confidence": 0.9,
                    },
                )
                detector = ResolutionDetector(chat=FakeChatModel([response]))
                self.assertIsNone(
                    detector._analyze_resolution("claim", "argument", context)
                )

    def test_resolution_text_fields_are_bounded(self):
        context = {
            "after_segments": [{"start": 1.0, "end": 2.0, "text": "ending"}],
        }
        response = ChatResponse(
            content="{}",
            parsed={
                "resolution_end_index": 0,
                "is_complete": True,
                "completion_type": "x" * 1_000,
                "reasoning": "r" * 20_000,
                "confidence": 0.9,
            },
        )
        detector = ResolutionDetector(chat=FakeChatModel([response]))

        result = detector._analyze_resolution("claim", "argument", context)

        self.assertEqual(len(result["completion_type"]), 100)
        self.assertEqual(len(result["reasoning"]), 10_000)
