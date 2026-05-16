"""Shared JSON Schema assertions."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def assert_json_schema_valid(testcase, schema: dict) -> None:
    try:
        import jsonschema
    except ImportError as exc:
        raise unittest.SkipTest("jsonschema is not installed") from exc
    jsonschema.Draft202012Validator.check_schema(schema)


def assert_json_validates(testcase, instance: dict, schema: dict) -> None:
    import jsonschema
    jsonschema.Draft202012Validator(schema).validate(instance)


def assert_json_rejected(testcase, instance: dict, schema: dict, expected_message_fragment: str | None = None) -> None:
    import jsonschema
    with testcase.assertRaises(jsonschema.ValidationError) as ctx:
        jsonschema.Draft202012Validator(schema).validate(instance)
    if expected_message_fragment:
        testcase.assertIn(expected_message_fragment, str(ctx.exception))
