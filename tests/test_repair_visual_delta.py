import json
import unittest

import numpy as np

from repair import compute_repair_visual_delta


class RepairVisualDeltaTests(unittest.TestCase):
    def test_visual_delta_is_json_serializable(self):
        before = np.array([[0, 1], [0, 0]], dtype=np.int8)
        after = np.array([[0, 0], [0, 0]], dtype=np.int8)
        target = np.zeros((2, 2), dtype=np.float32)
        result = compute_repair_visual_delta(before, after, target)
        json.dumps(result)
        self.assertEqual(result["changed_cells"], 1, msg="Expected 1 changed cell when one mine was removed")
        self.assertEqual(result["removed_mines"], [[0, 1]], msg="Expected removed_mines=[[0,1]] for mine at (0,1)")

    def test_added_mines_are_reported(self):
        before = np.zeros((2, 2), dtype=np.int8)
        after = np.array([[1, 0], [0, 0]], dtype=np.int8)
        target = np.zeros((2, 2), dtype=np.float32)
        result = compute_repair_visual_delta(before, after, target)
        self.assertEqual(result["added_mines"], [[0, 0]], msg="Expected added_mines=[[0,0]] for mine added at (0,0)")
        self.assertEqual(result["changed_cells"], 1, msg="Expected 1 changed cell when one mine was added")
        self.assertEqual(result["removed_mines"], [], msg="Expected removed_mines=[] when no mines were removed")

    def test_no_changes_yields_zero_delta(self):
        grid = np.array([[0, 1], [0, 0]], dtype=np.int8)
        target = np.zeros((2, 2), dtype=np.float32)
        result = compute_repair_visual_delta(grid, grid, target)
        self.assertEqual(result["changed_cells"], 0)
        self.assertEqual(result["removed_mines"], [])
        self.assertEqual(result["added_mines"], [])

    def test_result_is_json_serializable_with_all_expected_keys(self):
        before = np.array([[0, 1], [1, 0]], dtype=np.int8)
        after = np.array([[1, 0], [0, 1]], dtype=np.int8)
        target = np.zeros((2, 2), dtype=np.float32)
        result = compute_repair_visual_delta(before, after, target)
        import json as _json
        _json.dumps(result)
        self.assertEqual(
            set(result.keys()),
            {"changed_cells", "removed_mines", "added_mines", "mean_abs_error_before", "mean_abs_error_after", "visual_delta"},
            msg=f"Expected exact keys {{changed_cells, removed_mines, added_mines, mean_abs_error_before, mean_abs_error_after, visual_delta}}, got {set(result.keys())}",
        )


if __name__ == "__main__":
    unittest.main()
