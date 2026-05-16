"""Tests for board dimension domain behavior."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.fixtures.grids import wide_300x10_grid


class BoardDimensionsTests(unittest.TestCase):
    def test_board_dimensions_come_from_grid_shape(self):
        try:
            from demos.iter9_visual_solver.domain.board_dimensions import BoardDimensions
        except ModuleNotFoundError:
            self.skipTest("BoardDimensions is not implemented yet")
        grid = wide_300x10_grid()
        dims = BoardDimensions.from_grid(grid)
        self.assertEqual(dims.width, 300)
        self.assertEqual(dims.height, 10)


if __name__ == "__main__":
    unittest.main()
