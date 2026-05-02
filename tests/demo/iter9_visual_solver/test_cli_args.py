"""Tests for demo CLI args."""

from __future__ import annotations

import unittest


class CliArgsTests(unittest.TestCase):
    def test_cli_accepts_grid_metrics_and_config_args(self):
        try:
            from demos.iter9_visual_solver.cli.args import parse_args
        except ModuleNotFoundError:
            self.skipTest("parse_args is not implemented yet")
        args = parse_args(["--grid", "grid.npy", "--metrics", "metrics.json", "--config", "config.json"])
        self.assertEqual(args.grid, "grid.npy")


if __name__ == "__main__":
    unittest.main()
