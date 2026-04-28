import unittest
from unittest import mock

import numpy as np

from pipeline import RepairRoutingConfig, route_late_stage_failure
from solver import MINE, SAFE, UNKNOWN, SolveResult


class RepairRouteDecisionTests(unittest.TestCase):
    def test_already_solved_route(self):
        grid = np.zeros((2, 2), dtype=np.int8)
        sr = SolveResult(n_unknown=0, state=np.full((2, 2), SAFE, dtype=np.int8))
        route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((2, 2), dtype=np.float32), np.zeros((2, 2), dtype=np.int8), sr, RepairRoutingConfig())
        self.assertEqual(route.selected_route, "already_solved")

    def test_sealed_cluster_routes_to_phase2(self):
        grid = np.ones((3, 3), dtype=np.int8)
        grid[1, 1] = 0
        state = np.full((3, 3), MINE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        with mock.patch("pipeline.run_phase2_full_repair", return_value=(grid.copy(), 1, [{"visual_delta": 0.0}])):
            with mock.patch("pipeline.solve_board", return_value=SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))):
                route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((3, 3), dtype=np.float32), np.zeros((3, 3), dtype=np.int8), sr, RepairRoutingConfig())
        self.assertEqual(route.selected_route, "phase2_full_repair")

    def test_last100_route_when_phase2_disabled(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        state = np.full((3, 3), SAFE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        with mock.patch("pipeline.run_last100_repair", return_value=(grid.copy(), SolveResult(n_unknown=0, state=state), 1, [{"visual_delta": 0.0}], "solved")):
            route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((3, 3), dtype=np.float32), np.zeros((3, 3), dtype=np.int8), sr, RepairRoutingConfig(enable_phase2=False))
        self.assertEqual(route.selected_route, "last100_repair")

    def test_unresolved_route_does_not_run_sa(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        state = np.full((3, 3), UNKNOWN, dtype=np.int8)
        sr = SolveResult(n_unknown=9, state=state)
        with mock.patch("pipeline.run_phase2_full_repair") as phase2_mock:
            with mock.patch("pipeline.run_last100_repair") as last100_mock:
                route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((3, 3), dtype=np.float32), np.zeros((3, 3), dtype=np.int8), sr, RepairRoutingConfig(enable_phase2=False, enable_last100=False))
        phase2_mock.assert_not_called()
        last100_mock.assert_not_called()
        self.assertEqual(route.selected_route, "needs_sa_or_adaptive_rerun")


if __name__ == "__main__":
    unittest.main()
