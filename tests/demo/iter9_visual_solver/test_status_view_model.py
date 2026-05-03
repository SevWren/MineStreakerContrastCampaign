"""Tests for polished status panel view models."""

from __future__ import annotations

import unittest
from pathlib import Path

from demos.iter9_visual_solver.rendering.color_palette import ColorPalette
from demos.iter9_visual_solver.rendering.status_view_model import build_status_panel_view_model
from tests.demo.iter9_visual_solver.builders.status_snapshot_builder import StatusSnapshotBuilder


class StatusViewModelTests(unittest.TestCase):
    def _palette(self) -> ColorPalette:
        return ColorPalette(
            unseen_cell_rgb=(1, 1, 1),
            flagged_mine_rgb=(2, 2, 2),
            safe_cell_rgb=(3, 3, 3),
            unknown_cell_rgb=(4, 4, 4),
            background_rgb=(5, 5, 5),
        )

    def test_view_model_reuses_existing_status_lines(self):
        snapshot = StatusSnapshotBuilder().build()
        view_model = build_status_panel_view_model(
            snapshot=snapshot,
            status_config=None,
            palette=self._palette(),
            show_safe_cells=True,
            show_unknown_cells=True,
        )
        self.assertTrue(any(line.startswith("Source image:") for line in view_model.raw_lines))

    def test_view_model_builds_solved_badge_for_complete_zero_unknown(self):
        snapshot = StatusSnapshotBuilder().with_unknowns(0).with_finish_state("complete - staying open").build()
        view_model = build_status_panel_view_model(
            snapshot=snapshot,
            status_config=None,
            palette=self._palette(),
            show_safe_cells=True,
            show_unknown_cells=True,
        )
        self.assertEqual(view_model.badge.label, "SOLVED")
        self.assertEqual(view_model.badge.state, "solved")

    def test_view_model_has_bottom_right_source_preview_placeholder_metadata(self):
        snapshot = StatusSnapshotBuilder().with_source_image("line_art_irl_11_v2.png").build()
        view_model = build_status_panel_view_model(
            snapshot=snapshot,
            status_config=None,
            palette=self._palette(),
            show_safe_cells=False,
            show_unknown_cells=True,
        )
        self.assertEqual(view_model.source_preview.label, "line_art_irl_11_v2.png")
        self.assertEqual(view_model.source_preview.state, "placeholder")

    def test_view_model_progress_ratios_are_clamped(self):
        snapshot = StatusSnapshotBuilder().with_flagged_mines(flagged=20, total_mines=10).build()
        view_model = build_status_panel_view_model(
            snapshot=snapshot,
            status_config=None,
            palette=self._palette(),
            show_safe_cells=False,
            show_unknown_cells=False,
        )
        self.assertLessEqual(max(progress.ratio for progress in view_model.progress_bars), 1.0)

    def test_status_view_model_does_not_import_pygame(self):
        source = Path("demos/iter9_visual_solver/rendering/status_view_model.py").read_text(encoding="utf-8")
        self.assertNotIn("pygame", source)


if __name__ == "__main__":
    unittest.main()
