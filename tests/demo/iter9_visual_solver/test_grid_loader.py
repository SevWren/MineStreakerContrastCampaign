"""Tests for grid loader."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.builders.grid_builder import GridBuilder
from tests.demo.iter9_visual_solver.fixtures.temp_runs import make_temp_iter9_run_dir


class GridLoaderTests(unittest.TestCase):
    def test_load_grid_reads_npy_grid(self):
        try:
            from demos.iter9_visual_solver.io.grid_loader import load_grid
        except ModuleNotFoundError:
            self.skipTest("load_grid is not implemented yet")
        grid = GridBuilder(height=3, width=4).with_mines([(0, 0), (2, 3)]).build()
        with make_temp_iter9_run_dir() as run:
            path = run.write_grid_artifact(grid)
            loaded = load_grid(path)
        self.assertEqual(loaded.shape, (3, 4))


if __name__ == "__main__":
    unittest.main()
