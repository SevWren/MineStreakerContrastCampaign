"""Tests for status text formatting."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.builders.status_snapshot_builder import StatusSnapshotBuilder


class StatusTextTests(unittest.TestCase):
    def test_status_text_shows_actual_board_dimensions(self):
        try:
            from demos.iter9_visual_solver.rendering.status_text import build_status_lines
        except ModuleNotFoundError:
            self.skipTest("build_status_lines is not implemented yet")
        snapshot = StatusSnapshotBuilder().with_board(width=300, height=942).build()
        lines = build_status_lines(snapshot)
        self.assertTrue(any("Board: 300 x 942" in line for line in lines))

    def test_status_text_uses_real_speed_and_finish_wording(self):
        from demos.iter9_visual_solver.rendering.status_text import build_status_lines

        snapshot = (
            StatusSnapshotBuilder()
            .with_playback_speed(12000)
            .with_flagged_mines(flagged=10, total_mines=10)
            .build()
        )
        lines = build_status_lines(snapshot)
        self.assertIn("Playback speed: 12000 cells/sec", lines, msg="Expected a line 'Playback speed: 12000 cells/sec' in status lines")
        self.assertIn("Finish: running", lines, msg="Expected a line 'Finish: running' in status lines when playback is in progress")
        self.assertFalse(any("<" in line or ">" in line for line in lines))


if __name__ == "__main__":
    unittest.main()
