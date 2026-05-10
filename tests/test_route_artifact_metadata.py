import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from pipeline import (
    RepairRouteResult,
    RepairRoutingConfig,
    route_late_stage_failure,
    write_repair_route_artifacts,
)
from repair import Last100RepairResult, Phase2FullRepairResult
from solver import MINE, SAFE, UNKNOWN, SolveResult
from unittest import mock


class RouteArtifactMetadataTests(unittest.TestCase):
    def _write_decision_payload(self, route: RepairRouteResult) -> dict:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            result = write_repair_route_artifacts(str(out_dir), "300x370", route)
            return json.loads(Path(result["repair_route_decision"]).read_text(encoding="utf-8"))

    def test_route_artifacts_include_metadata_and_return_shape(self):
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td)
            route = RepairRouteResult(
                grid=np.zeros((2, 2), dtype=np.int8),
                sr=object(),
                selected_route="phase2_full_repair",
                route_result="solved",
                failure_taxonomy={"dominant_failure_class": "sealed_single_mesa"},
                visual_delta_summary={"visual_delta": 0.0},
                decision={"selected_route": "phase2_full_repair", "route_result": "solved"},
            )
            metadata = {
                "run_id": "20260426T000000Z_line_art_irl_11_v2_300w_seed11",
                "generated_at_utc": "2026-04-26T00:00:00.000Z",
                "source_image_project_relative_path": "assets/line_art_irl_11_v2.png",
                "source_image_sha256": "abc123",
                "metrics_path": "results/iter9/test/metrics_iter9_300x370.json",
            }
            result = write_repair_route_artifacts(
                str(out_dir),
                "300x370",
                route,
                artifact_metadata=metadata,
            )

            self.assertEqual(
                set(result.keys()),
                {"failure_taxonomy", "repair_route_decision", "visual_delta_summary"},
            )
            for key in ("failure_taxonomy", "repair_route_decision", "visual_delta_summary"):
                path = Path(result[key])
                self.assertTrue(path.exists())
                payload = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn("artifact_metadata", payload)
                self.assertEqual(payload["artifact_metadata"], metadata)
            decision_payload = json.loads(Path(result["repair_route_decision"]).read_text(encoding="utf-8"))
            self.assertIn("phase2_full_repair_hit_time_budget", decision_payload)
            self.assertIn("last100_repair_hit_time_budget", decision_payload)
            self.assertFalse(decision_payload["phase2_full_repair_hit_time_budget"], msg="route not invoked via phase2, so timeout flag must be False")
            self.assertFalse(decision_payload["last100_repair_hit_time_budget"], msg="route not invoked via last100, so timeout flag must be False")

    def test_repair_route_decision_timeout_fields_on_not_invoked_paths(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        target = grid.astype(np.float32)
        weights = np.ones((3, 3), dtype=np.float32)
        forbidden = np.zeros((3, 3), dtype=np.int8)

        cases = []

        already_solved_sr = SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))
        cases.append(
            route_late_stage_failure(
                grid,
                target,
                weights,
                forbidden,
                already_solved_sr,
                RepairRoutingConfig(),
            )
        )

        one_unknown_state = np.full((3, 3), SAFE, dtype=np.int8)
        one_unknown_state[1, 1] = UNKNOWN
        one_unknown_sr = SolveResult(n_unknown=1, state=one_unknown_state)
        cases.append(
            route_late_stage_failure(
                grid,
                target,
                weights,
                forbidden,
                one_unknown_sr,
                RepairRoutingConfig(enable_phase2=True, enable_last100=False),
            )
        )

        many_unknown_sr = SolveResult(n_unknown=9, state=np.full((3, 3), UNKNOWN, dtype=np.int8))
        cases.append(
            route_late_stage_failure(
                grid,
                target,
                weights,
                forbidden,
                many_unknown_sr,
                RepairRoutingConfig(enable_phase2=False, enable_last100=True, last100_unknown_threshold=1),
            )
        )

        for i, route in enumerate(cases):
            with self.subTest(case=i):
                payload = self._write_decision_payload(route)
                self.assertIn("phase2_full_repair_hit_time_budget", payload, msg=f"case {i}: phase2_full_repair_hit_time_budget missing from decision payload")
                self.assertIn("last100_repair_hit_time_budget", payload, msg=f"case {i}: last100_repair_hit_time_budget missing from decision payload")
                self.assertFalse(payload["phase2_full_repair_hit_time_budget"], msg=f"case {i}: phase2 was not run, timeout flag must be False")
                self.assertFalse(payload["last100_repair_hit_time_budget"], msg=f"case {i}: last100 was not run, timeout flag must be False")

    def test_repair_route_decision_timeout_fields_on_invoked_paths(self):
        target = np.zeros((3, 3), dtype=np.float32)
        weights = np.ones((3, 3), dtype=np.float32)
        forbidden = np.zeros((3, 3), dtype=np.int8)

        phase2_grid = np.ones((3, 3), dtype=np.int8)
        phase2_grid[1, 1] = 0
        phase2_state = np.full((3, 3), MINE, dtype=np.int8)
        phase2_state[1, 1] = UNKNOWN
        phase2_sr = SolveResult(n_unknown=1, state=phase2_state)
        phase2_result = Phase2FullRepairResult(
            grid=np.zeros((3, 3), dtype=np.int8),
            n_fixed=1,
            log=[{"visual_delta": 0.0}],
            phase2_full_repair_hit_time_budget=True,
        )
        with mock.patch("pipeline.run_phase2_full_repair", return_value=phase2_result):
            with mock.patch("pipeline.solve_board", return_value=SolveResult(n_unknown=0, state=np.full((3, 3), SAFE, dtype=np.int8))):
                route = route_late_stage_failure(
                    phase2_grid,
                    target,
                    weights,
                    forbidden,
                    phase2_sr,
                    RepairRoutingConfig(),
                )
        payload = self._write_decision_payload(route)
        self.assertTrue(payload["phase2_full_repair_hit_time_budget"], msg="phase2 was run with timeout=True, so phase2_full_repair_hit_time_budget must be True")
        self.assertFalse(payload["last100_repair_hit_time_budget"], msg="last100 was not run, so last100_repair_hit_time_budget must be False")

        last100_state = np.full((3, 3), SAFE, dtype=np.int8)
        last100_state[1, 1] = UNKNOWN
        last100_result = Last100RepairResult(
            grid=np.zeros((3, 3), dtype=np.int8),
            sr=SolveResult(n_unknown=0, state=last100_state),
            n_fixes=1,
            move_log=[{"visual_delta": 0.0}],
            stop_reason="timeout",
            last100_repair_hit_time_budget=True,
        )
        with mock.patch("pipeline.run_last100_repair", return_value=last100_result):
            route = route_late_stage_failure(
                np.zeros((3, 3), dtype=np.int8),
                target,
                weights,
                forbidden,
                SolveResult(n_unknown=1, state=last100_state),
                RepairRoutingConfig(enable_phase2=False),
            )
        payload = self._write_decision_payload(route)
        self.assertFalse(payload["phase2_full_repair_hit_time_budget"], msg="phase2 was not run, so phase2_full_repair_hit_time_budget must be False")
        self.assertTrue(payload["last100_repair_hit_time_budget"], msg="last100 was run with timeout=True, so last100_repair_hit_time_budget must be True")


if __name__ == "__main__":
    unittest.main()
