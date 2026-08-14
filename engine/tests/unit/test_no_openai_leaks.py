"""Guard test: openai imports only exist under arena/providers/.

This ensures the provider abstraction is not bypassed. The only
acceptable openai imports outside providers/ are in docstring examples.
"""

import ast
import os
import unittest
from pathlib import Path


class TestNoOpenAILeaks(unittest.TestCase):

    def test_openai_only_in_providers(self):
        """All 'from openai import' or 'import openai' must be under arena/providers/."""
        arena_root = Path(__file__).parent.parent.parent / "arena"
        providers_dir = arena_root / "providers"
        violations = []

        for py_file in arena_root.rglob("*.py"):
            # Skip providers/ — that's where OpenAI imports belong
            try:
                py_file.relative_to(providers_dir)
                continue
            except ValueError:
                pass

            content = py_file.read_text(encoding="utf-8")

            # Parse the AST to find real imports (not docstrings/comments)
            try:
                tree = ast.parse(content)
            except SyntaxError:
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name == "openai" or alias.name.startswith("openai."):
                            violations.append(
                                f"{py_file.relative_to(arena_root)}:{node.lineno}: import {alias.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module and (node.module == "openai" or node.module.startswith("openai.")):
                        names = ", ".join(a.name for a in node.names)
                        violations.append(
                            f"{py_file.relative_to(arena_root)}:{node.lineno}: from {node.module} import {names}"
                        )

        if violations:
            msg = "OpenAI imports found outside arena/providers/:\n" + "\n".join(f"  {v}" for v in violations)
            self.fail(msg)


if __name__ == "__main__":
    unittest.main()
