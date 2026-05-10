import unittest

import numpy as np

from repair import (
    Last100RepairResult,
    Phase1RepairResult,
    Phase2FullRepairResult,
    Phase2MesaRepairResult,
    run_last100_repair,
    run_phase1_repair,
    run_phase2_full_repair,
    run_phase2_mesa_repair,
)


class RepairResultDataclassTests(unittest.TestCase):
    def test_phase1_zero_budget_sets_timeout_boolean(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        target = np.zeros((3, 3), dtype=np.float32)
        forbidden = np.zeros((3, 3), dtype=np.int8)

        result = run_phase1_repair(
            grid,
            target,
            np.ones((3, 3), dtype=np.float32),
            forbidden,
            time_budget_s=0.0,
            max_rounds=1,
            verbose=False,
            parallel_eval=False,
        )

        self.assertIsInstance(result, Phase1RepairResult)
        self.assertTrue(result.phase1_repair_hit_time_budget)
        self.assertTrue(result.stop_reason.startswith("timeout"), msg=f"Expected stop_reason to start with 'timeout', got {result.stop_reason!r}")
        with self.assertRaises(TypeError):
            tuple(result)

    def test_phase2_full_zero_budget_sets_timeout_boolean(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        target = np.zeros((3, 3), dtype=np.float32)
        forbidden = np.zeros((3, 3), dtype=np.int8)

        result = run_phase2_full_repair(
            grid,
            target,
            forbidden,
            verbose=False,
            time_budget_s=0.0,
            solve_max_rounds=1,
            trial_max_rounds=1,
        )

        self.assertIsInstance(result, Phase2FullRepairResult)
        self.assertTrue(result.phase2_full_repair_hit_time_budget)
        with self.assertRaises(TypeError):
            tuple(result)

    def test_last100_zero_budget_sets_timeout_boolean(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        target = np.zeros((3, 3), dtype=np.float32)
        forbidden = np.zeros((3, 3), dtype=np.int8)

        result = run_last100_repair(
            grid,
            target,
            target,
            forbidden,
            budget_s=0.0,
            solve_max_rounds=1,
            trial_max_rounds=1,
            verbose=False,
        )

        self.assertIsInstance(result, Last100RepairResult)
        self.assertTrue(result.last100_repair_hit_time_budget)
        self.assertEqual(result.stop_reason, "timeout")
        with self.assertRaises(TypeError):
            tuple(result)

    def test_phase1_adequate_budget_does_not_set_timeout_boolean(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        target = np.zeros((3, 3), dtype=np.float32)
        forbidden = np.zeros((3, 3), dtype=np.int8)

        result = run_phase1_repair(
            grid,
            target,
            np.ones((3, 3), dtype=np.float32),
            forbidden,
            time_budget_s=60.0,
            max_rounds=1,
            verbose=False,
            parallel_eval=False,
        )

        self.assertIsInstance(result, Phase1RepairResult, msg="Expected run_phase1_repair to return Phase1RepairResult")
        self.assertFalse(
            result.phase1_repair_hit_time_budget,
            msg="Ample budget should not set phase1_repair_hit_time_budget=True",
        )

    def test_phase2_full_adequate_budget_does_not_set_timeout_boolean(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        target = np.zeros((3, 3), dtype=np.float32)
        forbidden = np.zeros((3, 3), dtype=np.int8)

        result = run_phase2_full_repair(
            grid,
            target,
            forbidden,
            verbose=False,
            time_budget_s=60.0,
            solve_max_rounds=1,
            trial_max_rounds=1,
        )

        self.assertIsInstance(result, Phase2FullRepairResult, msg="Expected run_phase2_full_repair to return Phase2FullRepairResult")
        self.assertFalse(
            result.phase2_full_repair_hit_time_budget,
            msg="Ample budget should not set phase2_full_repair_hit_time_budget=True",
        )

    def test_last100_adequate_budget_does_not_set_timeout_boolean(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        target = np.zeros((3, 3), dtype=np.float32)
        forbidden = np.zeros((3, 3), dtype=np.int8)

        result = run_last100_repair(
            grid,
            target,
            target,
            forbidden,
            budget_s=60.0,
            solve_max_rounds=1,
            trial_max_rounds=1,
            verbose=False,
        )

        self.assertIsInstance(result, Last100RepairResult, msg="Expected run_last100_repair to return Last100RepairResult")
        self.assertFalse(
            result.last100_repair_hit_time_budget,
            msg="Ample budget should not set last100_repair_hit_time_budget=True",
        )

    def test_phase2_mesa_returns_result_object_without_timeout_field(self):
        grid = np.zeros((3, 3), dtype=np.int8)
        target = np.zeros((3, 3), dtype=np.float32)
        forbidden = np.zeros((3, 3), dtype=np.int8)

        result = run_phase2_mesa_repair(grid, target, forbidden, verbose=False)

        self.assertIsInstance(result, Phase2MesaRepairResult, msg="Expected run_phase2_mesa_repair to return Phase2MesaRepairResult")
        self.assertFalse(hasattr(result, "phase2_mesa_repair_hit_time_budget"), msg="Phase2MesaRepairResult must not have 'phase2_mesa_repair_hit_time_budget'")
        self.assertFalse(hasattr(result, "phase2_full_repair_hit_time_budget"), msg="Phase2MesaRepairResult must not have 'phase2_full_repair_hit_time_budget'")
        with self.assertRaises(TypeError):
            tuple(result)


if __name__ == "__main__":
    unittest.main()
