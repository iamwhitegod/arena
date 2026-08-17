"""
JSON extraction, validation, and grammar utilities for provider adapters.

Local models often wrap JSON in markdown fences, preamble text, or trailing
commentary.  The extraction cascade handles all common patterns.  The
validation function enforces depth, size, and finiteness limits shared by
every adapter that parses model output.
"""

import json
import math
import re
from typing import Optional

from .base import ProviderResponseError

# ---------------------------------------------------------------------------
# Validation limits (shared by all adapters)
# ---------------------------------------------------------------------------
MAX_JSON_DEPTH = 20
MAX_JSON_NODES = 10_000
MAX_JSON_COLLECTION_SIZE = 1_000
MAX_JSON_STRING_LENGTH = 1_000_000

# ---------------------------------------------------------------------------
# JSON object validation
# ---------------------------------------------------------------------------


def validate_json_object(value: object) -> dict:
    """Enforce depth, size, and finiteness limits on a parsed JSON object.

    Raises ProviderResponseError for violations.  Returns the dict unchanged
    when valid.
    """
    if not isinstance(value, dict):
        raise ProviderResponseError("Model returned a non-object JSON response")

    nodes = 0
    stack: list[tuple[object, int]] = [(value, 0)]
    while stack:
        current, depth = stack.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            raise ProviderResponseError("Model returned an oversized JSON response")
        if isinstance(current, dict):
            if len(current) > MAX_JSON_COLLECTION_SIZE:
                raise ProviderResponseError("Model returned an oversized JSON object")
            for key, nested in current.items():
                if not isinstance(key, str) or len(key) > 1_000:
                    raise ProviderResponseError("Model returned an invalid JSON object")
                stack.append((nested, depth + 1))
        elif isinstance(current, list):
            if len(current) > MAX_JSON_COLLECTION_SIZE:
                raise ProviderResponseError("Model returned an oversized JSON array")
            stack.extend((nested, depth + 1) for nested in current)
        elif isinstance(current, str):
            if len(current) > MAX_JSON_STRING_LENGTH:
                raise ProviderResponseError("Model returned an oversized JSON string")
        elif isinstance(current, float) and not math.isfinite(current):
            raise ProviderResponseError("Model returned a non-finite JSON number")
        elif current is not None and not isinstance(current, (str, bool, int, float)):
            raise ProviderResponseError("Model returned an unsupported JSON value")
    return value


# ---------------------------------------------------------------------------
# JSON extraction cascade
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(
    r"```(?:json)?\s*\n(.*?)\n\s*```", re.DOTALL,
)


def _extract_braces(text: str) -> Optional[str]:
    """Find the outermost ``{...}`` by brace-depth scanning.

    Tracks JSON string state so that braces inside quoted strings
    (including escaped quotes) do not affect the depth count.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            if in_string:
                escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_json(text: str) -> dict:
    """Extract and validate a JSON object from possibly-decorated model output.

    Cascade:
    1. ``json.loads(text)`` directly.
    2. Extract from a markdown ````` ```json ... ``` ````` fence.
    3. Scan for the outermost ``{...}`` by brace depth.
    4. Raise ``ProviderResponseError(retryable=True)``.

    The extracted dict is validated for depth, size, and finiteness before
    being returned.
    """
    # 1. Direct parse
    try:
        return validate_json_object(json.loads(text))
    except (json.JSONDecodeError, ValueError):
        pass

    # 2. Markdown fence
    match = _FENCE_RE.search(text)
    if match:
        try:
            return validate_json_object(json.loads(match.group(1)))
        except (json.JSONDecodeError, ValueError):
            pass

    # 3. Brace-depth scan
    candidate = _extract_braces(text)
    if candidate:
        try:
            return validate_json_object(json.loads(candidate))
        except (json.JSONDecodeError, ValueError):
            pass

    raise ProviderResponseError(
        "Model returned unparseable JSON",
        code="response_error",
        retryable=True,
    )


def recover_truncated_object_array(text: str) -> Optional[dict]:
    """Recover fully closed objects from a length-truncated top-level array.

    This intentionally supports only ``{"key": [{...}, ...]}`` responses.
    The unfinished item and all trailing text are discarded, then the rebuilt
    document goes through the same bounded JSON validation as normal output.
    """
    object_start = text.find("{")
    array_start = text.find("[", object_start + 1)
    if object_start < 0 or array_start < 0:
        return None

    stack: list[str] = []
    in_string = False
    escape = False
    last_complete_item: Optional[int] = None
    pairs = {"}": "{", "]": "["}

    for index in range(object_start, len(text)):
        char = text[index]
        if escape:
            escape = False
            continue
        if char == "\\" and in_string:
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char in "{[":
            stack.append(char)
            continue
        if char in "}]":
            if not stack or stack[-1] != pairs[char]:
                return None
            stack.pop()
            if char == "}" and stack == ["{", "["]:
                last_complete_item = index

    if last_complete_item is None:
        return None

    candidate = text[object_start : last_complete_item + 1] + "]}"
    try:
        return validate_json_object(json.loads(candidate))
    except (json.JSONDecodeError, ValueError, ProviderResponseError):
        return None


# ---------------------------------------------------------------------------
# GBNF grammar generation for llama.cpp
# ---------------------------------------------------------------------------

# Minimal GBNF that accepts any JSON object.
_GENERIC_JSON_OBJECT_GRAMMAR = r"""
root   ::= "{" ws members "}" ws
members ::= pair ("," ws pair)*
pair   ::= string ":" ws value
value  ::= string | number | "true" | "false" | "null" | object | array
object ::= "{" ws (pair ("," ws pair)*)? "}" ws
array  ::= "[" ws (value ("," ws value)*)? "]" ws
string ::= "\"" ([^"\\] | "\\" .)* "\""
number ::= "-"? ("0" | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [+-]? [0-9]+)?
ws     ::= [ \t\n]*
""".strip()

_COMPACT_SEEDS_SCHEMA_ID = "arena://schemas/compact-seeds-v1"
_COMPACT_SEEDS_GRAMMAR = r'''
root ::= "{" ws "\"seeds\"" ws ":" ws "[" ws seeds? "]" ws "}" ws
seeds ::= seed ("," ws seed)*
seed ::= "{" ws "\"segment_id\"" ws ":" ws segment-id "," ws "\"text\"" ws ":" ws short-string "," ws "\"rhetorical_type\"" ws ":" ws rhetorical-type "," ws "\"interest_score\"" ws ":" ws score "}" ws
segment-id ::= "\"S" ("0" | [1-9] [0-9]{0,5}) "\""
short-string ::= "\"" string-char{1,180} "\""
string-char ::= [^"\\] | "\\" ["\\/bfnrt]
rhetorical-type ::= "\"argument\"" | "\"teaching\"" | "\"story\"" | "\"advice\"" | "\"qa\"" | "\"comparison\"" | "\"insight\""
score ::= "0" ("." [0-9]{1,3})? | "1" ("." "0"{1,3})?
ws ::= [ \t\n]{0,4}
'''.strip()


def build_gbnf_grammar(json_schema: Optional[dict] = None) -> Optional[str]:
    """Convert a JSON Schema to a GBNF grammar string for llama.cpp.

    Returns the generic JSON-object grammar when no schema is provided.
    Returns ``None`` for schemas too complex for GBNF translation (the
    caller should fall back to free-form generation + ``extract_json``).
    """
    if json_schema is None:
        return _GENERIC_JSON_OBJECT_GRAMMAR

    if json_schema.get("$id") == _COMPACT_SEEDS_SCHEMA_ID:
        return _COMPACT_SEEDS_GRAMMAR

    # For now, only handle the common Arena pattern: a flat object with
    # string/number/boolean/array properties.  Complex schemas (anyOf,
    # nested $ref, etc.) return None so the caller uses extract_json.
    properties = json_schema.get("properties")
    if not isinstance(properties, dict) or not properties:
        return _GENERIC_JSON_OBJECT_GRAMMAR

    if any(
        key in json_schema
        for key in ("anyOf", "oneOf", "allOf", "$ref", "if", "then")
    ):
        return None

    # For flat schemas with only simple types, use the generic grammar.
    # A schema-specific positional grammar would be more restrictive but
    # the escaping complexity isn't worth it for Phase 2.  The generic
    # grammar plus post-hoc domain validation in the editorial modules
    # is sufficient.
    for prop_schema in properties.values():
        prop_type = prop_schema.get("type", "string")
        if _schema_type_to_gbnf(prop_type) is None:
            return None
    return _GENERIC_JSON_OBJECT_GRAMMAR


def _schema_type_to_gbnf(schema_type: str) -> Optional[str]:
    mapping = {
        "string": "string",
        "number": "number",
        "integer": "number",
        "boolean": '("true" | "false")',
    }
    return mapping.get(schema_type)
