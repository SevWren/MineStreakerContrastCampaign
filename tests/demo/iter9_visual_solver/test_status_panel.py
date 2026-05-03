"""Tests for status panel drawing seam."""

from __future__ import annotations

import unittest

from demos.iter9_visual_solver.rendering.color_palette import ColorPalette
from demos.iter9_visual_solver.rendering.status_view_model import build_status_panel_view_model
from demos.iter9_visual_solver.rendering.window_geometry import RectSpec
from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter
from tests.demo.iter9_visual_solver.builders.status_snapshot_builder import StatusSnapshotBuilder
from tests.demo.iter9_visual_solver.fixtures.pygame_fakes import FakePygameModule, FakeSurface


class StatusPanelTests(unittest.TestCase):
    def test_status_panel_draws_lines_to_surface(self):
        try:
            from demos.iter9_visual_solver.rendering.status_panel import draw_status_panel
        except ModuleNotFoundError:
            self.skipTest("draw_status_panel is not implemented yet")
        surface = FakeSurface((360, 600))
        draw_status_panel(surface, ["Board: 300 x 942"])
        self.assertTrue(surface.fill_calls or surface.blit_calls)

    def test_status_panel_wraps_long_lines_to_panel_width(self):
        from demos.iter9_visual_solver.rendering.status_panel import wrap_status_line

        fake = FakePygameModule()
        font = fake.font.SysFont(None, 16)
        lines = wrap_status_line("Source image: a very long filename that should wrap", max_width_px=80, font=font)
        self.assertGreater(len(lines), 1)

    def test_status_panel_view_model_draws_badge_progress_and_preview_placeholder(self):
        from demos.iter9_visual_solver.rendering.status_panel import draw_status_panel_view_model

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        surface = FakeSurface((360, 600))
        palette = ColorPalette((1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 5, 5))
        snapshot = StatusSnapshotBuilder().with_source_image("source.png").build()
        view_model = build_status_panel_view_model(
            snapshot=snapshot,
            status_config=None,
            palette=palette,
            show_safe_cells=True,
            show_unknown_cells=True,
        )
        font = adapter.create_font()
        draw_status_panel_view_model(
            surface,
            view_model,
            adapter=adapter,
            panel_rect=RectSpec(0, 0, 360, 600),
            palette=palette,
            font=font,
            source_preview_rect=RectSpec(188, 468, 160, 120),
        )
        self.assertIn("Source preview", font.rendered_text)
        self.assertIn("source.png", font.rendered_text)

    def test_status_panel_wide_mode_renders_metric_label_and_value_separately(self):
        from demos.iter9_visual_solver.rendering.status_panel import draw_status_panel_view_model

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        surface = FakeSurface((560, 600))
        palette = ColorPalette((1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 5, 5))
        snapshot = StatusSnapshotBuilder().with_board(800, 800).build()
        view_model = build_status_panel_view_model(
            snapshot=snapshot,
            status_config=None,
            palette=palette,
            show_safe_cells=True,
            show_unknown_cells=True,
        )
        font = adapter.create_font()
        draw_status_panel_view_model(
            surface,
            view_model,
            adapter=adapter,
            panel_rect=RectSpec(0, 0, 560, 600),
            palette=palette,
            font=font,
        )
        self.assertIn("Total cells:", font.rendered_text)
        self.assertIn("640000", font.rendered_text)
        self.assertNotIn("Total cells: 640000", font.rendered_text)


if __name__ == "__main__":
    unittest.main()
