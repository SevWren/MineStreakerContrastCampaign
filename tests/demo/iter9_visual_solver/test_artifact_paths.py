"""Tests for artifact path resolution."""

from __future__ import annotations

import unittest


class ArtifactPathsTests(unittest.TestCase):
    def test_grid_latest_filename_contract(self):
        try:
            from demos.iter9_visual_solver.contracts.artifact_names import GRID_LATEST_FILENAME
        except ModuleNotFoundError:
            self.skipTest("artifact_names contract module is not implemented yet")
        self.assertEqual(GRID_LATEST_FILENAME, "grid_iter9_latest.npy")


if __name__ == "__main__":
    unittest.main()
