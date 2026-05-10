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
        self.assertEqual(result["changed_cells"], 1)
        self.assertEqual(result["removed_mines"], [[0, 1]])

    def test_added_mines_are_reported(self):
        before = np.zeros((2, 2), dtype=np.int8)
        after = np.array([[1, 0], [0, 0]], dtype=np.int8)
        target = np.zeros((2, 2), dtype=np.float32)
        result = compute_repair_visual_delta(before, after, target)
        self.assertEqual(result["added_mines"], [[0, 0]])

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
        for key in ("changed_cells", "removed_mines", "added_mines"):
            self.assertIn(key, result, msg=f"Missing key: {key}")


if __name__ == "__main__":
    unittest.main()
