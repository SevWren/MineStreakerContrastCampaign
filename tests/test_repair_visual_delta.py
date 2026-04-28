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


if __name__ == "__main__":
    unittest.main()
