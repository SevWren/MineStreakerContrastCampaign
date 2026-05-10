import unittest
from unittest import mock

import numpy as np

from pipeline import RepairRoutingConfig, route_late_stage_failure
from repair import Last100RepairResult, Phase2FullRepairResult
from solver import MINE, SAFE, UNKNOWN, SolveResult


class RepairRouteDecisionTests(unittest.TestCase):
    def test_already_solved_route(self):
        grid = np.zeros((2, 2), dtype=np.int8)
        sr = SolveResult(n_unknown=0, state=np.full((2, 2), SAFE, dtype=np.int8))
        route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((2, 2), dtype=np.float32), np.zeros((2, 2), dtype=np.int8), sr, RepairRoutingConfig())
        self.assertEqual(route.selected_route, "already_solved", msg="Zero unknowns should route to already_solved")

    def test_sealed_cluster_routes_to_phase2(self):
        grid = np.ones((3, 3), dtype=np.int8)
        grid[1, 1] = 0
        state = np.full((3, 3), MINE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        phase2_result = Phase2FullRepairResult(
            grid=grid.copy(),
            n_fixed=1,
            log=[{"visual_delta": 0.0}],
            phase2_full_repair_hit_time_budget=True,
        )
        with mock.patch("pipeline.run_phase2_full_repair", return_value=phase2_result):
            with mock.patch("pipeline.solve_board", return_value=SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))):
                route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((3, 3), dtype=np.float32), np.zeros((3, 3), dtype=np.int8), sr, RepairRoutingConfig())
        self.assertEqual(route.selected_route, "phase2_full_repair", msg="Sealed cluster should route to phase2_full_repair")
        self.assertTrue(route.phase2_full_repair_hit_time_budget, msg="phase2_full_repair_hit_time_budget should reflect the repair result")
        self.assertTrue(route.decision["phase2_full_repair_hit_time_budget"], msg="decision dict must mirror route.phase2_full_repair_hit_time_budget")
        self.assertFalse(route.last100_repair_hit_time_budget, msg="last100 was not run, so its timeout flag must be False")

    def test_last100_route_when_phase2_disabled(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        state = np.full((3, 3), SAFE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        last100_result = Last100RepairResult(
            grid=grid.copy(),
            sr=SolveResult(n_unknown=0, state=state),
            n_fixes=1,
            move_log=[{"visual_delta": 0.0}],
            stop_reason="solved",
            last100_repair_hit_time_budget=True,
        )
        with mock.patch("pipeline.run_last100_repair", return_value=last100_result):
            route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((3, 3), dtype=np.float32), np.zeros((3, 3), dtype=np.int8), sr, RepairRoutingConfig(enable_phase2=False))
        self.assertEqual(route.selected_route, "last100_repair", msg="Should fall through to last100 when phase2 is disabled")
        self.assertTrue(route.last100_repair_hit_time_budget, msg="last100_repair_hit_time_budget should reflect the repair result")
        self.assertTrue(route.decision["last100_repair_hit_time_budget"], msg="decision dict must mirror route.last100_repair_hit_time_budget")
        self.assertFalse(route.phase2_full_repair_hit_time_budget, msg="phase2 was not run, so its timeout flag must be False")

    def test_unresolved_route_does_not_run_sa(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        state = np.full((3, 3), UNKNOWN, dtype=np.int8)
        sr = SolveResult(n_unknown=9, state=state)
        with mock.patch("pipeline.run_phase2_full_repair") as phase2_mock:
            with mock.patch("pipeline.run_last100_repair") as last100_mock:
                route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((3, 3), dtype=np.float32), np.zeros((3, 3), dtype=np.int8), sr, RepairRoutingConfig(enable_phase2=False, enable_last100=False))
        phase2_mock.assert_not_called()
        last100_mock.assert_not_called()
        self.assertEqual(route.selected_route, "needs_sa_or_adaptive_rerun", msg="All repairs disabled should yield needs_sa_or_adaptive_rerun")
        self.assertFalse(route.phase2_full_repair_hit_time_budget, msg="phase2 was not run, so its timeout flag must be False")
        self.assertFalse(route.last100_repair_hit_time_budget, msg="last100 was not run, so its timeout flag must be False")


if __name__ == "__main__":
    unittest.main()
