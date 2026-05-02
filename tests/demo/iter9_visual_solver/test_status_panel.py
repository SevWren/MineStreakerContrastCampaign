"""Tests for status panel drawing seam."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.fixtures.pygame_fakes import FakeSurface


class StatusPanelTests(unittest.TestCase):
    def test_status_panel_draws_lines_to_surface(self):
        try:
            from demos.iter9_visual_solver.rendering.status_panel import draw_status_panel
        except ModuleNotFoundError:
            self.skipTest("draw_status_panel is not implemented yet")
        surface = FakeSurface((360, 600))
        draw_status_panel(surface, ["Board: 300 x 942"])
        self.assertTrue(surface.fill_calls or surface.blit_calls)


if __name__ == "__main__":
    unittest.main()
