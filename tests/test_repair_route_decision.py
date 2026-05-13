import unittest
from unittest import mock

import numpy as np

from pipeline import RepairRoutingConfig, route_late_stage_failure
from repair import Last100RepairResult, Phase2FullRepairResult
from solver import MINE, SAFE, UNKNOWN, SolveResult


def _make_grid(shape=(3, 3)):
    return np.zeros(shape, dtype=np.int8)

def _make_target(shape=(3, 3)):
    return np.zeros(shape, dtype=np.float32)

def _make_weights(shape=(3, 3)):
    return np.ones(shape, dtype=np.float32)

def _make_forbidden(shape=(3, 3)):
    return np.zeros(shape, dtype=np.int8)


class RepairRouteDecisionTests(unittest.TestCase):
    def test_already_solved_route(self):
        grid = np.zeros((2, 2), dtype=np.int8)
        sr = SolveResult(n_unknown=0, state=np.full((2, 2), SAFE, dtype=np.int8))
        route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((2, 2), dtype=np.float32), np.zeros((2, 2), dtype=np.int8), sr, RepairRoutingConfig())
        self.assertEqual(route.selected_route, "already_solved", msg="Zero unknowns should route to already_solved")

    def test_already_solved_four_field_model(self):
        grid = _make_grid()
        sr = SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))
        route = route_late_stage_failure(grid, _make_target(), _make_weights(), _make_forbidden(), sr, RepairRoutingConfig())
        self.assertEqual(route.selected_route, "already_solved")
        self.assertEqual(route.route_result, "solved")
        self.assertEqual(route.route_outcome_detail, "already_solved_before_routing")
        self.assertIsNone(route.next_recommended_route)

    def test_no_route_unresolved_four_field_model(self):
        grid = _make_grid()
        state = np.full((3, 3), UNKNOWN, dtype=np.int8)
        sr = SolveResult(n_unknown=9, state=state)
        with mock.patch("pipeline.run_phase2_full_repair") as p2_mock:
            with mock.patch("pipeline.run_last100_repair") as l100_mock:
                route = route_late_stage_failure(
                    grid, _make_target(), _make_weights(), _make_forbidden(), sr,
                    RepairRoutingConfig(enable_phase2=False, enable_last100=False),
                )
        p2_mock.assert_not_called()
        l100_mock.assert_not_called()
        self.assertEqual(route.selected_route, "none")
        self.assertEqual(route.route_result, "unresolved_after_repair")
        self.assertEqual(route.route_outcome_detail, "no_late_stage_route_invoked")
        self.assertEqual(route.next_recommended_route, "needs_sa_or_adaptive_rerun")

    def test_phase2_solved_four_field_model(self):
        grid = np.ones((3, 3), dtype=np.int8)
        grid[1, 1] = 0
        state = np.full((3, 3), MINE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        phase2_result = Phase2FullRepairResult(
            grid=grid.copy(),
            n_fixed=1,
            log=[{"accepted": True}],
            phase2_full_repair_hit_time_budget=False,
        )
        solved_sr = SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))
        with mock.patch("pipeline.run_phase2_full_repair", return_value=phase2_result):
            with mock.patch("pipeline.solve_board", return_value=solved_sr):
                route = route_late_stage_failure(
                    grid, _make_target(), _make_weights(), _make_forbidden(), sr, RepairRoutingConfig()
                )
        self.assertEqual(route.selected_route, "phase2_full_repair")
        self.assertEqual(route.route_result, "solved")
        self.assertEqual(route.route_outcome_detail, "phase2_full_repair_solved")
        self.assertIsNone(route.next_recommended_route)

    def test_phase2_partial_progress_four_field_model(self):
        grid = np.ones((3, 3), dtype=np.int8)
        grid[1, 1] = 0
        state = np.full((3, 3), MINE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=5, state=state)
        phase2_result = Phase2FullRepairResult(
            grid=grid.copy(),
            n_fixed=2,
            log=[{"accepted": True}, {"accepted": True}],
            phase2_full_repair_hit_time_budget=False,
        )
        # partial — n_unknown reduced from 5 to 3 but not zero
        partial_sr = SolveResult(n_unknown=3, state=np.full((3, 3), UNKNOWN, dtype=np.int8))
        with mock.patch("pipeline.run_phase2_full_repair", return_value=phase2_result):
            with mock.patch("pipeline.solve_board", return_value=partial_sr):
                route = route_late_stage_failure(
                    grid, _make_target(), _make_weights(), _make_forbidden(), sr,
                    RepairRoutingConfig(enable_last100=False),
                )
        self.assertEqual(route.selected_route, "phase2_full_repair")
        self.assertEqual(route.route_result, "unresolved_after_repair")
        self.assertEqual(route.route_outcome_detail, "phase2_full_repair_partial_progress_unresolved")
        self.assertEqual(route.next_recommended_route, "needs_sa_or_adaptive_rerun")

    def test_last100_solved_four_field_model(self):
        grid = _make_grid()
        state = np.full((3, 3), SAFE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        last100_result = Last100RepairResult(
            grid=grid.copy(),
            sr=SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8)),
            n_fixes=1,
            move_log=[{"accepted": True}],
            stop_reason="solved",
            last100_repair_hit_time_budget=False,
        )
        with mock.patch("pipeline.run_last100_repair", return_value=last100_result):
            route = route_late_stage_failure(
                grid, _make_target(), _make_weights(), _make_forbidden(), sr,
                RepairRoutingConfig(enable_phase2=False),
            )
        self.assertEqual(route.selected_route, "last100_repair")
        self.assertEqual(route.route_result, "solved")
        self.assertEqual(route.route_outcome_detail, "last100_repair_solved")
        self.assertIsNone(route.next_recommended_route)

    def test_last100_unresolved_four_field_model(self):
        grid = _make_grid()
        state = np.full((3, 3), SAFE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        last100_result = Last100RepairResult(
            grid=grid.copy(),
            sr=SolveResult(n_unknown=1, state=state),
            n_fixes=0,
            move_log=[{"accepted": False}],
            stop_reason="no_effect",
            last100_repair_hit_time_budget=False,
        )
        with mock.patch("pipeline.run_last100_repair", return_value=last100_result):
            route = route_late_stage_failure(
                grid, _make_target(), _make_weights(), _make_forbidden(), sr,
                RepairRoutingConfig(enable_phase2=False),
            )
        self.assertEqual(route.selected_route, "last100_repair")
        self.assertEqual(route.route_result, "unresolved_after_repair")
        self.assertIn(route.route_outcome_detail, {
            "last100_repair_partial_progress_unresolved",
            "last100_repair_no_accepted_moves",
            "last100_repair_timeout_unresolved",
        })
        self.assertEqual(route.next_recommended_route, "needs_sa_or_adaptive_rerun")

    def test_sealed_cluster_routes_to_phase2(self):
        grid = np.ones((3, 3), dtype=np.int8)
        grid[1, 1] = 0
        state = np.full((3, 3), MINE, dtype=np.int8)
        state[1, 1] = UNKNOWN
        sr = SolveResult(n_unknown=1, state=state)
        phase2_result = Phase2FullRepairResult(
            grid=grid.copy(),
            n_fixed=1,
            log=[{"accepted": True}],
            phase2_full_repair_hit_time_budget=True,
        )
        with mock.patch("pipeline.run_phase2_full_repair", return_value=phase2_result):
            with mock.patch("pipeline.solve_board", return_value=SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))) as solve_mock:
                route = route_late_stage_failure(grid, grid.astype(np.float32), np.ones((3, 3), dtype=np.float32), np.zeros((3, 3), dtype=np.int8), sr, RepairRoutingConfig())
        solve_mock.assert_called_once()
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
            move_log=[{"accepted": True}],
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
        # Post-fix: selected_route must be "none", not "needs_sa_or_adaptive_rerun"
        self.assertNotEqual(route.selected_route, "needs_sa_or_adaptive_rerun",
                            msg="needs_sa_or_adaptive_rerun must never appear in selected_route")
        self.assertEqual(route.selected_route, "none",
                         msg="All repairs disabled should yield selected_route='none'")
        self.assertFalse(route.phase2_full_repair_hit_time_budget, msg="phase2 was not run, so its timeout flag must be False")
        self.assertFalse(route.last100_repair_hit_time_budget, msg="last100 was not run, so its timeout flag must be False")

    # ── Producer-level invariant tests ────────────────────────────────────

    def test_build_route_result_rejects_needs_sa_as_selected_route(self):
        from pipeline import _build_route_result
        grid = _make_grid()
        sr = SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))
        decision = {
            "selected_route": "needs_sa_or_adaptive_rerun",
            "route_result": "unresolved_after_repair",
            "route_outcome_detail": "no_late_stage_route_invoked",
            "next_recommended_route": "needs_sa_or_adaptive_rerun",
            "solver_n_unknown_before": 0,
            "solver_n_unknown_after": 0,
            "phase2_full_repair_invoked": False,
            "phase2_full_repair_hit_time_budget": False,
            "phase2_full_repair_n_fixed": 0,
            "phase2_full_repair_accepted_move_count": 0,
            "phase2_full_repair_changed_grid": False,
            "phase2_full_repair_reduced_unknowns": False,
            "phase2_full_repair_solved": False,
            "phase2_solver_n_unknown_before": None,
            "phase2_solver_n_unknown_after": None,
            "last100_invoked": False,
            "last100_repair_hit_time_budget": False,
            "last100_n_fixes": 0,
            "last100_accepted_move_count": 0,
            "last100_solver_n_unknown_before": None,
            "last100_solver_n_unknown_after": None,
            "last100_stop_reason": None,
        }
        with self.assertRaises(ValueError, msg="_build_route_result must reject selected_route='needs_sa_or_adaptive_rerun'"):
            _build_route_result(
                grid=grid,
                sr=sr,
                failure_taxonomy={},
                decision=decision,
            )

    def test_build_route_result_rejects_stale_solver_n_unknown_after(self):
        from pipeline import _build_route_result
        grid = _make_grid()
        sr = SolveResult(n_unknown=5, state=np.full((3, 3), UNKNOWN, dtype=np.int8))
        decision = {
            "selected_route": "none",
            "route_result": "unresolved_after_repair",
            "route_outcome_detail": "no_late_stage_route_invoked",
            "next_recommended_route": "needs_sa_or_adaptive_rerun",
            "solver_n_unknown_before": 5,
            "solver_n_unknown_after": 99,  # stale — does not match sr.n_unknown=5
            "phase2_full_repair_invoked": False,
            "phase2_full_repair_hit_time_budget": False,
            "phase2_full_repair_n_fixed": 0,
            "phase2_full_repair_accepted_move_count": 0,
            "phase2_full_repair_changed_grid": False,
            "phase2_full_repair_reduced_unknowns": False,
            "phase2_full_repair_solved": False,
            "phase2_solver_n_unknown_before": None,
            "phase2_solver_n_unknown_after": None,
            "last100_invoked": False,
            "last100_repair_hit_time_budget": False,
            "last100_n_fixes": 0,
            "last100_accepted_move_count": 0,
            "last100_solver_n_unknown_before": None,
            "last100_solver_n_unknown_after": None,
            "last100_stop_reason": None,
        }
        with self.assertRaises(ValueError, msg="_build_route_result must reject stale solver_n_unknown_after"):
            _build_route_result(
                grid=grid,
                sr=sr,
                failure_taxonomy={},
                decision=decision,
            )

    def test_build_route_result_rejects_phase2_invoked_without_matching_selected_route(self):
        from pipeline import _build_route_result
        grid = _make_grid()
        sr = SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))
        decision = {
            "selected_route": "none",  # wrong — phase2 invoked but selected_route is not phase2_full_repair
            "route_result": "unresolved_after_repair",
            "route_outcome_detail": "no_late_stage_route_invoked",
            "next_recommended_route": "needs_sa_or_adaptive_rerun",
            "solver_n_unknown_before": 0,
            "solver_n_unknown_after": 0,
            "phase2_full_repair_invoked": True,  # invoked
            "phase2_full_repair_hit_time_budget": False,
            "phase2_full_repair_n_fixed": 0,
            "phase2_full_repair_accepted_move_count": 0,
            "phase2_full_repair_changed_grid": False,
            "phase2_full_repair_reduced_unknowns": False,
            "phase2_full_repair_solved": False,
            "phase2_solver_n_unknown_before": None,
            "phase2_solver_n_unknown_after": None,
            "last100_invoked": False,
            "last100_repair_hit_time_budget": False,
            "last100_n_fixes": 0,
            "last100_accepted_move_count": 0,
            "last100_solver_n_unknown_before": None,
            "last100_solver_n_unknown_after": None,
            "last100_stop_reason": None,
        }
        with self.assertRaises(ValueError, msg="_build_route_result must reject phase2 invoked without phase2_full_repair selected_route"):
            _build_route_result(
                grid=grid,
                sr=sr,
                failure_taxonomy={},
                decision=decision,
            )

    def test_route_state_fields_agrees_with_decision(self):
        from pipeline import _build_route_result
        grid = _make_grid()
        sr = SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))
        decision = {
            "selected_route": "already_solved",
            "route_result": "solved",
            "route_outcome_detail": "already_solved_before_routing",
            "next_recommended_route": None,
            "solver_n_unknown_before": 0,
            "solver_n_unknown_after": 0,
            "phase2_full_repair_invoked": False,
            "phase2_full_repair_hit_time_budget": False,
            "phase2_full_repair_n_fixed": 0,
            "phase2_full_repair_accepted_move_count": 0,
            "phase2_full_repair_changed_grid": False,
            "phase2_full_repair_reduced_unknowns": False,
            "phase2_full_repair_solved": False,
            "phase2_solver_n_unknown_before": None,
            "phase2_solver_n_unknown_after": None,
            "last100_invoked": False,
            "last100_repair_hit_time_budget": False,
            "last100_n_fixes": 0,
            "last100_accepted_move_count": 0,
            "last100_solver_n_unknown_before": None,
            "last100_solver_n_unknown_after": None,
            "last100_stop_reason": None,
        }
        route = _build_route_result(grid=grid, sr=sr, failure_taxonomy={}, decision=decision)
        fields = route.route_state_fields()
        for key, value in fields.items():
            self.assertEqual(route.decision.get(key), value,
                             msg=f"route_state_fields disagrees with decision for {key}")


if __name__ == "__main__":
    unittest.main()
