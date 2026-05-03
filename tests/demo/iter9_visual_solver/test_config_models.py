"""Tests for config Pydantic models."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.fixtures.configs import (
    default_demo_config_dict,
    invalid_config_bad_rgb_tuple,
    invalid_config_missing_schema_version,
    invalid_config_negative_speed,
)


class ConfigModelsTests(unittest.TestCase):
    def test_default_config_fixture_is_structurally_complete(self):
        config = default_demo_config_dict()
        self.assertIn("schema_version", config)
        self.assertIn("window", config)
        self.assertIn("playback", config)
        self.assertIn("visuals", config)
        self.assertIn("status_panel", config)
        self.assertIn("input", config)

    def test_runtime_model_accepts_default_config(self):
        try:
            from demos.iter9_visual_solver.config.models import DemoConfig
        except ModuleNotFoundError:
            self.skipTest("DemoConfig is not implemented yet")
        model = DemoConfig.model_validate(default_demo_config_dict())
        self.assertEqual(model.schema_version, "iter9_visual_solver_demo_config.v1")
        self.assertTrue(model.window.resizable)
        self.assertTrue(model.window.fit_to_screen)
        self.assertTrue(model.window.center_window)

    def test_runtime_model_rejects_invalid_configs(self):
        try:
            from demos.iter9_visual_solver.config.models import DemoConfig
        except ModuleNotFoundError:
            self.skipTest("DemoConfig is not implemented yet")
        for invalid in [
            invalid_config_missing_schema_version(),
            invalid_config_bad_rgb_tuple(),
            invalid_config_negative_speed(),
        ]:
            with self.assertRaises(Exception):
                DemoConfig.model_validate(invalid)


if __name__ == "__main__":
    unittest.main()
