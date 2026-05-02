"""Tests for board surface rendering logic."""

from __future__ import annotations

import unittest

from demos.iter9_visual_solver.domain.board_state import BoardState
from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
from demos.iter9_visual_solver.rendering.color_palette import ColorPalette
from tests.demo.iter9_visual_solver.builders.grid_builder import GridBuilder
from tests.demo.iter9_visual_solver.fixtures.pygame_fakes import FakePygameModule, FakeSurface


class BoardSurfaceTests(unittest.TestCase):
    def test_board_surface_uses_grid_shape(self):
        try:
            from demos.iter9_visual_solver.rendering.board_surface import build_board_surface_model
        except ModuleNotFoundError:
            self.skipTest("build_board_surface_model is not implemented yet")
        grid = GridBuilder(height=3, width=5).build()
        model = build_board_surface_model(grid)
        self.assertEqual(model.width, 5)
        self.assertEqual(model.height, 3)

    def test_board_surface_maps_mine_and_safe_cells_to_configured_colors(self):
        from demos.iter9_visual_solver.rendering.board_surface import draw_board_state
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        surface = FakeSurface((10, 10))
        state = BoardState.empty(width=2, height=1)
        state.apply(PlaybackEvent(step=0, y=0, x=0, state="MINE", display="flag"))
        state.apply(PlaybackEvent(step=1, y=0, x=1, state="SAFE", display="reveal"))
        palette = ColorPalette(
            unseen_cell_rgb=(1, 1, 1),
            flagged_mine_rgb=(2, 2, 2),
            safe_cell_rgb=(3, 3, 3),
            unknown_cell_rgb=(4, 4, 4),
            background_rgb=(5, 5, 5),
        )
        draw_board_state(
            surface=surface,
            adapter=adapter,
            board_state=state,
            palette=palette,
            cell_px=2,
            show_safe_cells=True,
        )
        self.assertIn(((2, 2, 2), (0, 0, 2, 2)), surface.rect_calls)
        self.assertIn(((3, 3, 3), (2, 0, 2, 2)), surface.rect_calls)


if __name__ == "__main__":
    unittest.main()
