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

    def test_board_surface_can_skip_full_surface_clear_and_use_origin(self):
        from demos.iter9_visual_solver.rendering.board_surface import draw_board_state
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        surface = FakeSurface((20, 20))
        state = BoardState.empty(width=1, height=1)
        state.apply(PlaybackEvent(step=0, y=0, x=0, state="MINE", display="flag"))
        palette = ColorPalette((1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 5, 5))
        draw_board_state(
            surface=surface,
            adapter=adapter,
            board_state=state,
            palette=palette,
            cell_px=3,
            origin=(7, 8),
            clear_surface=False,
        )
        self.assertEqual(surface.fill_calls, [])
        self.assertIn(((2, 2, 2), (7, 8, 3, 3)), surface.rect_calls)

    def test_scaled_board_surface_draws_logical_grid_then_nearest_neighbor_blits(self):
        from demos.iter9_visual_solver.rendering.board_surface import draw_scaled_board_state
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter
        from demos.iter9_visual_solver.rendering.window_geometry import RectSpec

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        surface = FakeSurface((100, 100))
        state = BoardState.empty(width=2, height=1)
        state.apply(PlaybackEvent(step=0, y=0, x=1, state="MINE", display="flag"))
        palette = ColorPalette((1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 5, 5))
        draw_scaled_board_state(
            surface=surface,
            adapter=adapter,
            board_state=state,
            palette=palette,
            board_width=2,
            board_height=1,
            destination_rect=RectSpec(10, 20, 80, 40),
        )
        logical, size = fake.transform.scale_calls[-1]
        self.assertEqual(logical.get_size(), (2, 1))
        self.assertEqual(size, (80, 40))
        self.assertEqual(surface.blit_calls[-1][1], (10, 20))


if __name__ == "__main__":
    unittest.main()
