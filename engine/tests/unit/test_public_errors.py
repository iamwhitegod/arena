"""Tests for safe public CLI error formatting."""

import re
import unittest

from arena.cli.public_errors import format_public_error
from arena.providers.base import ProviderError


class TestPublicErrors(unittest.TestCase):

    def test_non_provider_error_never_exposes_native_message(self):
        native = RuntimeError(
            "sk-canary-secret /Users/private/video.mp4 \x1b]52;c;clipboard\x07"
        )

        rendered = format_public_error(native, "Processing failed")

        self.assertIn("internal_error", rendered)
        self.assertNotIn("canary", rendered)
        self.assertNotIn("/Users/private", rendered)
        self.assertNotIn("\x1b", rendered)

    def test_provider_error_has_safe_metadata_and_redaction(self):
        error = ProviderError(
            "Provider failed with token=sk-canary-secret-value",
            code="rate_limit",
            retryable=True,
        )

        rendered = format_public_error(error)

        self.assertIn("rate_limit", rendered)
        self.assertIn("retryable=true", rendered)
        self.assertIn("[redacted]", rendered)
        self.assertNotIn("canary", rendered)
        self.assertRegex(rendered, re.compile(r"ref=[0-9a-f]{12}"))
