import unittest

import numpy as np

from solver import MINE, SAFE, UNKNOWN, SolveResult, classify_unresolved_clusters


class SolverFailureTaxonomyTests(unittest.TestCase):
    def test_no_unknowns(self):
        sr = SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))
        result = classify_unresolved_clusters(np.zeros((3, 3), dtype=np.int8), sr)
        self.assertEqual(result["dominant_failure_class"], "no_unknowns")

    def test_missing_solver_state(self):
        sr = SolveResult(n_unknown=5, state=None)
        result = classify_unresolved_clusters(np.zeros((3, 3), dtype=np.int8), sr)
        self.assertEqual(result["dominant_failure_class"], "unclassified_missing_solver_state")

    def test_sealed_single_mesa(self):
        grid = np.ones((3, 3), dtype=np.int8)
        grid[1, 1] = 0
        state = np.full((3, 3), MINE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        result = classify_unresolved_clusters(grid, sr)
        self.assertEqual(result["sealed_single_mesa_count"], 1)

    def test_sealed_multi_cell_cluster(self):
        grid = np.ones((4, 4), dtype=np.int8)
        grid[1:3, 1:3] = 0
        state = np.full((4, 4), MINE, dtype=np.int8)
        state[1:3, 1:3] = UNKNOWN
        sr = SolveResult(n_unknown=4, state=state)
        result = classify_unresolved_clusters(grid, sr)
        self.assertGreaterEqual(result["sealed_multi_cell_cluster_count"], 1)

    def test_frontier_adjacent_unknown(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        state = np.full((3, 3), SAFE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        result = classify_unresolved_clusters(grid, sr)
        self.assertGreaterEqual(result["frontier_adjacent_unknown_count"], 1)


if __name__ == "__main__":
    unittest.main()
