"""Tests for JSON extraction, validation, and grammar utilities."""

import unittest

from arena.providers.base import ProviderResponseError
from arena.providers.json_utils import (
    build_gbnf_grammar,
    extract_json,
    recover_truncated_object_array,
    validate_json_object,
)


class TestValidateJsonObject(unittest.TestCase):

    def test_valid_flat_object(self):
        obj = {"key": "value", "num": 42}
        self.assertEqual(validate_json_object(obj), obj)

    def test_rejects_non_dict(self):
        with self.assertRaises(ProviderResponseError):
            validate_json_object([1, 2, 3])

    def test_rejects_non_finite_float(self):
        with self.assertRaises(ProviderResponseError):
            validate_json_object({"x": float("nan")})

    def test_rejects_deeply_nested(self):
        obj = {"a": {}}
        current = obj["a"]
        for _ in range(25):
            current["nested"] = {}
            current = current["nested"]
        with self.assertRaises(ProviderResponseError):
            validate_json_object(obj)


class TestExtractJson(unittest.TestCase):

    def test_clean_json(self):
        result = extract_json('{"key": "value"}')
        self.assertEqual(result, {"key": "value"})

    def test_json_in_markdown_fence(self):
        text = 'Here is the result:\n```json\n{"score": 0.9}\n```\nDone.'
        result = extract_json(text)
        self.assertEqual(result, {"score": 0.9})

    def test_json_with_preamble(self):
        text = 'Sure! Here is the JSON:\n{"answer": true}\nHope that helps!'
        result = extract_json(text)
        self.assertEqual(result, {"answer": True})

    def test_invalid_text_raises(self):
        with self.assertRaises(ProviderResponseError):
            extract_json("no json here at all")

    def test_empty_string_raises(self):
        with self.assertRaises(ProviderResponseError):
            extract_json("")

    def test_nested_braces(self):
        text = 'Result: {"outer": {"inner": 1}}'
        result = extract_json(text)
        self.assertEqual(result, {"outer": {"inner": 1}})

    def test_braces_inside_string_values(self):
        text = 'prefix {"text": "}"} suffix'
        result = extract_json(text)
        self.assertEqual(result, {"text": "}"})


class TestBuildGbnfGrammar(unittest.TestCase):

    def test_no_schema_returns_generic(self):
        grammar = build_gbnf_grammar(None)
        self.assertIsNotNone(grammar)
        self.assertIn("root", grammar)

    def test_simple_schema_returns_grammar(self):
        schema = {
            "properties": {
                "name": {"type": "string"},
                "score": {"type": "number"},
            }
        }
        grammar = build_gbnf_grammar(schema)
        self.assertIsNotNone(grammar)

    def test_complex_schema_with_properties_returns_none(self):
        schema = {
            "anyOf": [
                {"type": "string"},
                {"type": "number"},
            ],
            "properties": {
                "name": {"type": "string"},
            },
        }
        result = build_gbnf_grammar(schema)
        self.assertIsNone(result)

    def test_compact_seed_schema_uses_bounded_string_grammar(self):
        grammar = build_gbnf_grammar({
            "$id": "arena://schemas/compact-seeds-v1",
            "properties": {"seeds": {"type": "array"}},
        })
        self.assertIsNotNone(grammar)
        self.assertIn("string-char{1,180}", grammar)
        self.assertIn("rhetorical-type", grammar)


class TestRecoverTruncatedObjectArray(unittest.TestCase):

    def test_keeps_only_fully_closed_array_objects(self):
        result = recover_truncated_object_array(
            '{"seeds":[{"text":"one"},{"text":"two"},{"text":"unfinished'
        )
        self.assertEqual(
            result,
            {"seeds": [{"text": "one"}, {"text": "two"}]},
        )

    def test_handles_braces_inside_strings(self):
        result = recover_truncated_object_array(
            '{"seeds":[{"text":"a } brace"},{"text":"unfinished'
        )
        self.assertEqual(result, {"seeds": [{"text": "a } brace"}]})

    def test_rejects_prefix_without_complete_item(self):
        self.assertIsNone(
            recover_truncated_object_array('{"seeds":[{"text":"unfinished')
        )

    def test_unsupported_property_type_returns_none(self):
        schema = {
            "properties": {
                "data": {"type": "object"},
            }
        }
        result = build_gbnf_grammar(schema)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
