"""Tests for window geometry calculation."""

from __future__ import annotations

import unittest

from demos.iter9_visual_solver.rendering.window_geometry import (
    DisplayBounds,
    LayoutRequest,
    RectSpec,
    calculate_responsive_window_geometry,
    calculate_window_geometry,
    calculate_window_placement,
)


class WindowGeometryTests(unittest.TestCase):
    def test_window_geometry_uses_grid_dimensions(self):
        geometry = calculate_window_geometry(board_width=300, board_height=942, status_panel_width_px=360)
        self.assertEqual(geometry.board_width, 300)
        self.assertEqual(geometry.board_height, 942)

    def test_fit_to_screen_reduces_cell_px_to_fit_display_budget(self):
        geometry = calculate_window_geometry(
            board_width=300,
            board_height=300,
            status_panel_width_px=360,
            preferred_board_cell_px=4,
            minimum_board_cell_px=1,
            max_screen_fraction=0.92,
            display_bounds=DisplayBounds(0, 0, 1280, 720),
            fit_to_screen=True,
        )
        self.assertLess(geometry.cell_px, 4)
        self.assertTrue(geometry.fits_screen)
        self.assertIsInstance(geometry.board_rect, RectSpec)

    def test_fit_to_screen_false_uses_preferred_cell_px_at_startup(self):
        geometry = calculate_window_geometry(
            board_width=300,
            board_height=942,
            status_panel_width_px=360,
            preferred_board_cell_px=2,
            minimum_board_cell_px=1,
            display_bounds=DisplayBounds(0, 0, 640, 480),
            fit_to_screen=False,
        )
        self.assertEqual(geometry.cell_px, 2)

    def test_resize_geometry_reports_window_overflow_when_too_small(self):
        geometry = calculate_responsive_window_geometry(
            LayoutRequest(
                board_width=300,
                board_height=942,
                requested_window_width=100,
                requested_window_height=100,
                status_panel_width_px=360,
                preferred_board_cell_px=2,
                minimum_board_cell_px=1,
                max_screen_fraction=0.92,
                fit_to_screen=True,
                display_bounds=DisplayBounds(0, 0, 1280, 720),
            )
        )
        self.assertFalse(geometry.fits_window)
        self.assertEqual(geometry.cell_px, 1)

    def test_resize_geometry_preserves_larger_requested_window_size(self):
        geometry = calculate_responsive_window_geometry(
            LayoutRequest(
                board_width=800,
                board_height=800,
                requested_window_width=1920,
                requested_window_height=1080,
                status_panel_width_px=360,
                preferred_board_cell_px=2,
                minimum_board_cell_px=1,
                max_screen_fraction=0.92,
                fit_to_screen=True,
                display_bounds=DisplayBounds(0, 0, 1920, 1080),
            )
        )
        self.assertEqual(geometry.window_width, 1920, msg="window_width must equal the requested_window_width=1920")
        self.assertEqual(geometry.window_height, 1080, msg="window_height must equal the requested_window_height=1080")
        self.assertGreater(geometry.board_scale, 1.0, msg="board_scale must be > 1.0 when window is larger than the logical board")
        self.assertGreater(geometry.board_draw_rect.width, 800, msg="board_draw_rect.width must exceed logical board width 800 when scaled up")
        self.assertEqual(geometry.status_panel_rect.width, 537, msg="status_panel_rect.width must be 537 for window_width=1920 and board scaled to fill")
        self.assertEqual(geometry.status_panel_rect.x, 1367, msg="status_panel_rect.x must be 1367 (= 1920 - 537 - margin)")
        self.assertEqual(geometry.header_rect.width, 1920, msg="header_rect.width must span the full window width 1920")
        self.assertLess(geometry.board_draw_rect.x + geometry.board_draw_rect.width, geometry.status_panel_rect.x, msg="board draw rect must not overlap the status panel")

    def test_smaller_resize_scales_board_down_without_distortion(self):
        geometry = calculate_responsive_window_geometry(
            LayoutRequest(
                board_width=800,
                board_height=800,
                requested_window_width=500,
                requested_window_height=420,
                status_panel_width_px=360,
                preferred_board_cell_px=2,
                minimum_board_cell_px=1,
                max_screen_fraction=1.0,
                fit_to_screen=True,
                display_bounds=DisplayBounds(0, 0, 1920, 1080),
            )
        )
        self.assertLess(geometry.board_scale, 1.0)
        self.assertEqual(geometry.board_draw_rect.width, geometry.board_draw_rect.height)
        self.assertEqual(geometry.window_width, 500)
        self.assertEqual(geometry.window_height, 420)

    def test_source_preview_preserves_source_aspect_ratio(self):
        geometry = calculate_responsive_window_geometry(
            LayoutRequest(
                board_width=100,
                board_height=100,
                requested_window_width=1280,
                requested_window_height=720,
                status_panel_width_px=360,
                preferred_board_cell_px=2,
                minimum_board_cell_px=1,
                max_screen_fraction=1.0,
                fit_to_screen=True,
                display_bounds=DisplayBounds(0, 0, 1280, 720),
                source_image_width_px=1600,
                source_image_height_px=900,
            )
        )
        preview = geometry.source_preview_rect
        self.assertIsNotNone(preview)
        self.assertAlmostEqual(preview.width / preview.height, 16 / 9, delta=0.02)
        panel = geometry.status_panel_rect
        self.assertGreaterEqual(preview.x, panel.x, msg="preview.x must be >= panel.x (preview inside status panel)")
        self.assertGreaterEqual(preview.y, panel.y, msg="preview.y must be >= panel.y (preview inside status panel)")
        self.assertLessEqual(preview.x + preview.width, panel.x + panel.width, msg="preview right edge must not exceed panel right edge")
        self.assertLessEqual(preview.y + preview.height, panel.y + panel.height, msg="preview bottom edge must not exceed panel bottom edge")

    def test_status_panel_and_source_preview_rects_are_inside_geometry(self):
        geometry = calculate_window_geometry(board_width=10, board_height=20, status_panel_width_px=360)
        self.assertIsNotNone(geometry.status_panel_rect)
        self.assertIsNotNone(geometry.source_preview_rect)
        preview = geometry.source_preview_rect
        panel = geometry.status_panel_rect
        self.assertGreaterEqual(preview.x, panel.x, msg="preview.x must be >= panel.x")
        self.assertGreaterEqual(preview.y, panel.y, msg="preview.y must be >= panel.y")
        self.assertLessEqual(preview.x + preview.width, panel.x + panel.width, msg="preview right edge must be <= panel right edge")
        self.assertLessEqual(preview.y + preview.height, panel.y + panel.height, msg="preview bottom edge must be <= panel bottom edge")

    def test_calculate_window_placement_centers_x_when_enabled(self):
        placement = calculate_window_placement(
            window_width=400,
            window_height=200,
            display_bounds=DisplayBounds(10, 0, 1000, 800),
            center_window=True,
        )
        self.assertEqual(placement.x, 310, msg="x must be (display_x=10) + (display_width=1000 - window_width=400) // 2 = 310")
        self.assertTrue(placement.horizontally_centered)

    def test_calculate_window_placement_returns_none_when_disabled(self):
        placement = calculate_window_placement(
            window_width=400,
            window_height=200,
            display_bounds=DisplayBounds(10, 0, 1000, 800),
            center_window=False,
        )
        self.assertIsNone(placement.x)
        self.assertFalse(placement.horizontally_centered)


if __name__ == "__main__":
    unittest.main()
