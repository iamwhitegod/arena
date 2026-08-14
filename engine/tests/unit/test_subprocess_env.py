"""Security tests for media subprocess environment isolation."""

import ast
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from arena.providers.subprocess_env import scrubbed_env


class TestScrubbedEnvironment(unittest.TestCase):

    def test_uses_allowlist_instead_of_provider_credential_denylist(self):
        source = {
            "PATH": "/usr/bin",
            "HOME": "/tmp/test-home",
            "LANG": "en_US.UTF-8",
            "OPENAI_API_KEY": "openai-secret",
            "MISTRAL_API_KEY": "mistral-secret",
            "AWS_SECRET_ACCESS_KEY": "aws-secret",
            "SESSION_TOKEN": "session-secret",
            "HTTPS_PROXY": "https://user:password@example.test",
        }
        with patch.dict(os.environ, source, clear=True):
            env = scrubbed_env()

        self.assertEqual(env["PATH"], "/usr/bin")
        self.assertEqual(env["HOME"], "/tmp/test-home")
        self.assertNotIn("OPENAI_API_KEY", env)
        self.assertNotIn("MISTRAL_API_KEY", env)
        self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
        self.assertNotIn("SESSION_TOKEN", env)
        self.assertNotIn("HTTPS_PROXY", env)

    def test_extra_environment_cannot_reintroduce_secrets(self):
        with self.assertRaisesRegex(ValueError, "sensitive"):
            scrubbed_env({"SERVICE_TOKEN": "secret"})

    def test_extra_environment_must_also_be_allowlisted(self):
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            scrubbed_env({"UNRELATED_DATA": "value"})


class TestMediaSubprocessCalls(unittest.TestCase):

    def test_every_engine_subprocess_run_supplies_an_environment(self):
        engine_root = Path(__file__).resolve().parents[2]
        files = list((engine_root / "arena").rglob("*.py"))
        files.append(engine_root / "arena_process.py")
        violations = []

        for path in files:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                if not (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "subprocess"
                    and node.func.attr in {"run", "Popen"}
                ):
                    continue
                if not any(keyword.arg == "env" for keyword in node.keywords):
                    violations.append(f"{path.relative_to(engine_root)}:{node.lineno}")

        self.assertEqual(violations, [], "Subprocesses missing explicit env:\n" + "\n".join(violations))


if __name__ == "__main__":
    unittest.main()
