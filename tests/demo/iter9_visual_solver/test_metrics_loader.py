"""Tests for metrics loader."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.builders.metrics_builder import MetricsBuilder
from tests.demo.iter9_visual_solver.fixtures.temp_runs import make_temp_iter9_run_dir


class MetricsLoaderTests(unittest.TestCase):
    def test_load_metrics_reads_json_document(self):
        try:
            from demos.iter9_visual_solver.io.metrics_loader import load_metrics
        except ModuleNotFoundError:
            self.skipTest("load_metrics is not implemented yet")
        metrics = MetricsBuilder().with_board("300x942").with_seed(11).build_dict()
        with make_temp_iter9_run_dir() as run:
            path = run.write_metrics_artifact(metrics)
            loaded = load_metrics(path)
        self.assertEqual(loaded["board"], "300x942")


if __name__ == "__main__":
    unittest.main()
