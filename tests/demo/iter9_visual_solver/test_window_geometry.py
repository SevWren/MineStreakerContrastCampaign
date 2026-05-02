"""Tests for window geometry calculation."""

from __future__ import annotations

import unittest


class WindowGeometryTests(unittest.TestCase):
    def test_window_geometry_uses_grid_dimensions(self):
        try:
            from demos.iter9_visual_solver.rendering.window_geometry import calculate_window_geometry
        except ModuleNotFoundError:
            self.skipTest("calculate_window_geometry is not implemented yet")
        geometry = calculate_window_geometry(board_width=300, board_height=942, status_panel_width_px=360)
        self.assertEqual(geometry.board_width, 300)
        self.assertEqual(geometry.board_height, 942)


if __name__ == "__main__":
    unittest.main()
