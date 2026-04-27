import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from report import (
    REPAIR_PANEL_CAPTIONS,
    REPORT_PANEL_CAPTIONS,
    build_plain_english_repair_summary,
    build_plain_english_run_summary,
    render_repair_overlay_explained,
    render_report_explained,
)


def _fake_solve_result(*, n_unknown: int, solvable: bool) -> SimpleNamespace:
    state = np.array(
        [
            [1, 2, 0],
            [1, 1, 2],
            [0, 1, 2],
        ],
        dtype=np.int8,
    )
    return SimpleNamespace(
        coverage=1.0 if n_unknown == 0 else 0.78,
        solvable=solvable,
        mine_accuracy=0.94,
        n_revealed=5,
        n_safe=6,
        n_mines=3,
        n_unknown=n_unknown,
        state=state,
        rounds=12,
    )


class ReportExplanationTests(unittest.TestCase):
    def test_run_summary_describes_solved_board_in_plain_english(self):
        lines = build_plain_english_run_summary(
            {
                "board": "300x370",
                "seed": 11,
                "source_image": {"name": "line_art_irl_11_v2.png"},
                "repair_route_selected": "phase2_full_repair",
                "solvable": True,
                "n_unknown": 0,
                "coverage": 1.0,
                "mine_accuracy": 0.95,
                "mean_abs_error": 0.22,
                "mine_density": 0.18,
            }
        )
        joined = " ".join(lines).lower()
        self.assertIn("finished completely solved", joined)
        self.assertIn("300x370", joined)
        self.assertIn("seed 11", joined)
        self.assertNotIn("coverage:", joined)
        self.assertNotIn("mean_abs_error", joined)
        self.assertNotIn("mine_density", joined)

    def test_run_summary_describes_unsolved_board(self):
        lines = build_plain_english_run_summary(
            {
                "board": "300x370",
                "seed": 11,
                "repair_route_selected": "needs_sa_or_adaptive_rerun",
                "solvable": False,
                "n_unknown": 42,
                "coverage": 0.91,
                "mine_accuracy": 0.82,
                "mean_abs_error": 0.63,
                "mine_density": 0.20,
            }
        )
        joined = " ".join(lines).lower()
        self.assertIn("42 unresolved cells", joined)
        self.assertIn("did not finish fully solved", joined)

    def test_repair_summary_reports_exact_counts(self):
        lines = build_plain_english_repair_summary(
            before_unknown=12,
            after_unknown=0,
            removed_mines=3,
            added_mines=1,
            solved_after=True,
        )
        joined = " ".join(lines).lower()
        self.assertIn("12 unresolved cells", joined)
        self.assertIn("0 unresolved cells", joined)
        self.assertIn("removed 3 mines", joined)
        self.assertIn("added 1 mine", joined)
        self.assertIn("fully solved", joined)

    def test_caption_dictionaries_are_complete(self):
        expected_report = {
            "target_image",
            "mine_grid",
            "number_field",
            "error_map",
            "solver_result",
            "loss_curve",
            "distribution",
            "metrics",
        }
        expected_repair = {
            "target_image",
            "before_unknown",
            "after_unknown",
            "mine_changes",
            "error_delta",
            "repair_summary",
        }
        self.assertEqual(expected_report, set(REPORT_PANEL_CAPTIONS.keys()))
        self.assertEqual(expected_repair, set(REPAIR_PANEL_CAPTIONS.keys()))
        for caption in list(REPORT_PANEL_CAPTIONS.values()) + list(REPAIR_PANEL_CAPTIONS.values()):
            self.assertTrue(isinstance(caption, str) and caption.strip())

    def test_render_report_explained_writes_non_empty_png(self):
        target = np.array([[0.0, 1.0, 2.0], [2.0, 3.0, 4.0], [4.0, 5.0, 6.0]], dtype=np.float32)
        grid = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.int8)
        sr = _fake_solve_result(n_unknown=0, solvable=True)
        history = np.array([50.0, 25.0, 12.0], dtype=np.float64)
        metrics = {
            "run_id": "demo_run_id_with_extra_context_for_wrapping",
            "board": "300x370",
            "seed": 11,
            "source_image": {
                "name": "very_long_source_image_name_for_wrapped_caption_testing.png",
            },
            "repair_route_selected": "phase2_full_repair",
            "coverage": 1.0,
            "solvable": True,
            "mine_accuracy": 0.95,
            "n_unknown": 0,
            "mean_abs_error": 0.21,
            "mine_density": 0.18,
        }
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "report_explained.png"
            render_report_explained(
                target,
                grid,
                sr,
                history,
                "Mine-Streaker explained final report with a deliberately long title for wrapping checks",
                str(out_path),
                metrics=metrics,
                dpi=90,
            )
            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)

    def test_render_repair_overlay_explained_writes_non_empty_png(self):
        target = np.array([[0.0, 1.0, 2.0], [2.0, 3.0, 4.0], [4.0, 5.0, 6.0]], dtype=np.float32)
        grid_before = np.array([[0, 1, 0], [1, 0, 1], [0, 1, 0]], dtype=np.int8)
        grid_after = np.array([[0, 0, 0], [1, 0, 1], [0, 1, 0]], dtype=np.int8)
        sr_before = _fake_solve_result(n_unknown=2, solvable=False)
        sr_after = _fake_solve_result(n_unknown=0, solvable=True)
        repair_log = [{"move_type": "single", "delta_unknown": 2}]
        metrics = {
            "run_id": "demo_repair_run_with_wrapped_context",
            "board": "300x370",
            "seed": 11,
            "source_image": {
                "name": "very_long_source_image_name_for_wrapped_caption_testing.png",
            },
            "before_unknown": 2,
            "after_unknown": 0,
            "removed_mines": 1,
            "added_mines": 0,
            "solved_after": True,
        }
        with tempfile.TemporaryDirectory() as td:
            out_path = Path(td) / "repair_overlay_explained.png"
            render_repair_overlay_explained(
                target,
                grid_before,
                grid_after,
                sr_before,
                sr_after,
                repair_log,
                str(out_path),
                metrics=metrics,
                dpi=90,
            )
            self.assertTrue(out_path.exists())
            self.assertGreater(out_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
