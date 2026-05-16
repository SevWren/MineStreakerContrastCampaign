"""Tests for demo config loader."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.fixtures.configs import default_demo_config_dict
from tests.demo.iter9_visual_solver.fixtures.temp_runs import make_temp_iter9_run_dir


class ConfigLoaderTests(unittest.TestCase):
    def test_load_demo_config_reads_json_file(self):
        try:
            from demos.iter9_visual_solver.config.loader import load_demo_config
        except ModuleNotFoundError:
            self.skipTest("load_demo_config is not implemented yet")
        with make_temp_iter9_run_dir() as run:
            config_path = run.write_demo_config(default_demo_config_dict())
            config = load_demo_config(config_path)
        self.assertEqual(config.schema_version, "iter9_visual_solver_demo_config.v1")
        self.assertTrue(config.window.resizable, msg="config.window.resizable should be True per default config")


if __name__ == "__main__":
    unittest.main()
