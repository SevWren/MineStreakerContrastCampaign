"""Tests for board surface rendering logic."""

from __future__ import annotations

import unittest

import numpy as np

from demos.iter9_visual_solver.domain.board_state import BoardState
from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
from demos.iter9_visual_solver.playback.event_source import STATE_MINE, STATE_SAFE, TypedPlaybackEventStore
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

    def test_cached_board_surface_creates_logical_surface_once_and_draws_batch_cells(self):
        from demos.iter9_visual_solver.rendering.board_surface import CachedBoardSurfaceRenderer
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        palette = ColorPalette((1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 5, 5))
        store = TypedPlaybackEventStore(
            steps=np.array([0, 1], dtype=np.uint32),
            y=np.array([0, 0], dtype=np.uint32),
            x=np.array([0, 1], dtype=np.uint32),
            state_codes=np.array([STATE_MINE, STATE_SAFE], dtype=np.uint8),
            board_width=2,
            board_height=1,
        )
        renderer = CachedBoardSurfaceRenderer(
            board_width=2,
            board_height=1,
            adapter=adapter,
            palette=palette,
            show_safe_cells=True,
        )
        renderer.apply_batch(store.batch(0, 2))
        self.assertEqual(renderer.logical_surface.get_size(), (2, 1))
        self.assertEqual(fake.draw.rect_calls[-2][2], (0, 0, 1, 1))
        self.assertEqual(fake.draw.rect_calls[-1][2], (1, 0, 1, 1))

    def test_cached_board_surface_reuses_logical_surface_across_scaled_draws(self):
        from demos.iter9_visual_solver.rendering.board_surface import CachedBoardSurfaceRenderer
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter
        from demos.iter9_visual_solver.rendering.window_geometry import RectSpec

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        palette = ColorPalette((1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 5, 5))
        renderer = CachedBoardSurfaceRenderer(board_width=2, board_height=1, adapter=adapter, palette=palette)
        logical = renderer.logical_surface
        surface = FakeSurface((100, 100))
        renderer.draw_scaled(surface=surface, destination_rect=RectSpec(0, 0, 20, 10))
        renderer.draw_scaled(surface=surface, destination_rect=RectSpec(0, 0, 40, 20))
        self.assertIs(fake.transform.scale_calls[0][0], logical)
        self.assertIs(fake.transform.scale_calls[1][0], logical)
        self.assertEqual(len(surface.blit_calls), 2)


if __name__ == "__main__":
    unittest.main()
