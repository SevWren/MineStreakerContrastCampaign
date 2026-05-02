"""Tests for committed demo config schema."""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.demo.iter9_visual_solver.fixtures.configs import default_demo_config_dict
from tests.demo.iter9_visual_solver.helpers.schema_assertions import (
    assert_json_schema_valid,
    assert_json_validates,
    load_json,
)


class ConfigSchemaContractTests(unittest.TestCase):
    def test_config_schema_exists_under_demo_json_schemas(self):
        schema_path = Path("demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json")
        self.assertTrue(schema_path.is_file(), f"Missing schema: {schema_path}")

    def test_default_config_validates_against_schema(self):
        schema_path = Path("demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json")
        if not schema_path.is_file():
            self.skipTest("Config schema file is not present yet")
        schema = load_json(schema_path)
        assert_json_schema_valid(self, schema)
        assert_json_validates(self, default_demo_config_dict(), schema)

    def test_committed_default_config_validates_against_schema(self):
        schema_path = Path("demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json")
        config_path = Path("configs/demo/iter9_visual_solver_demo.default.json")
        self.assertTrue(schema_path.is_file(), f"Missing schema: {schema_path}")
        self.assertTrue(config_path.is_file(), f"Missing default config: {config_path}")
        assert_json_validates(self, load_json(config_path), load_json(schema_path))


if __name__ == "__main__":
    unittest.main()
