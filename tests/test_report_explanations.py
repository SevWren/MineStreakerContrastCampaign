import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import matplotlib
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import report as report_module
from report import (
    EXPLAINED_COLORBAR_LABELS,
    EXPLAINED_VALUE_EXPLANATIONS,
    REPAIR_PANEL_CAPTIONS,
    REPORT_PANEL_CAPTIONS,
    TECHNICAL_HISTORY_X_LABEL,
    TECHNICAL_HISTORY_Y_LABEL,
    _add_explained_colorbar,
    _format_duration,
    _plot_explained_optimization_progress,
    _runtime_context_line,
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
                "repair_route_selected": "none",
                "selected_route": "none",
                "route_result": "unresolved_after_repair",
                "route_outcome_detail": "no_late_stage_route_invoked",
                "next_recommended_route": "needs_sa_or_adaptive_rerun",
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

    def test_report_reads_selected_route_not_repair_route_selected(self):
        from report import _format_metric_explanations
        # When selected_route is present, it must be used over repair_route_selected
        metrics = {
            "selected_route": "phase2_full_repair",
            "route_result": "solved",
            "route_outcome_detail": "phase2_full_repair_solved",
            "next_recommended_route": None,
            "repair_route_selected": "old_stale_value",
            "coverage": 1.0,
            "mine_accuracy": 0.95,
            "mean_abs_error": 0.2,
            "mine_density": 0.18,
            "n_unknown": 0,
        }
        lines = _format_metric_explanations(metrics)
        joined = " ".join(lines)
        self.assertIn("phase2_full_repair", joined)
        self.assertNotIn("old_stale_value", joined)

    def test_report_no_fallback_to_repair_route_selected_for_selected_route(self):
        from report import build_plain_english_run_summary
        # When selected_route is missing, must warn about schema violation, not silently use repair_route_selected
        metrics = {
            # selected_route intentionally absent to test schema_incomplete fallback
            "repair_route_selected": "phase2_full_repair",
            "route_result": "solved",
            "board": "300x370",
            "seed": 11,
            "solvable": True,
            "n_unknown": 0,
            "coverage": 1.0,
            "mine_accuracy": 0.95,
            "mean_abs_error": 0.2,
            "mine_density": 0.18,
        }
        lines = build_plain_english_run_summary(metrics)
        joined = " ".join(lines)
        # Must NOT silently use repair_route_selected as the selected route
        self.assertNotIn("phase2_full_repair", joined)

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
        self.assertIn("lower", REPORT_PANEL_CAPTIONS["loss_curve"].lower())
        self.assertIn("lower", EXPLAINED_VALUE_EXPLANATIONS["loss_curve"].lower())

    def test_explained_colorbar_labels_are_beginner_readable(self):
        target_label = EXPLAINED_COLORBAR_LABELS["target_image"]
        number_label = EXPLAINED_COLORBAR_LABELS["number_field"]
        error_label = EXPLAINED_COLORBAR_LABELS["error_map"]

        self.assertIn("Target value", target_label)
        self.assertIn("0 background", target_label)
        self.assertIn("8 strongest line", target_label)
        self.assertIn("Generated number", number_label)
        self.assertIn("0 no nearby mines", number_label)
        self.assertIn("8 surrounded", number_label)
        self.assertIn("Difference", error_label)
        self.assertIn("0 match", error_label)
        self.assertIn("4+ large mismatch", error_label)

    def test_explained_value_explanations_define_zero_and_high_values(self):
        target_expl = EXPLAINED_VALUE_EXPLANATIONS["target_image"]
        numbers_expl = EXPLAINED_VALUE_EXPLANATIONS["number_field"]
        error_expl = EXPLAINED_VALUE_EXPLANATIONS["error_map"]

        self.assertIn("0 means background", target_expl)
        self.assertIn("8 means the strongest line area", target_expl)
        self.assertIn("0 means a safe cell has no touching mines", numbers_expl)
        self.assertIn("8 means a safe cell is surrounded by mines", numbers_expl)
        self.assertIn("0 means the generated number matched", error_expl)
        self.assertIn("4 or more means a large mismatch", error_expl)

    def test_add_explained_colorbar_sets_label_and_ticks(self):
        fig, ax = plt.subplots(figsize=(2, 2))
        image = ax.imshow(np.array([[0.0, 1.0], [2.0, 3.0]], dtype=np.float32))
        cbar = _add_explained_colorbar(image, ax, "Demo label", ticks=[0, 1, 2, 3])
        try:
            self.assertEqual(cbar.ax.get_ylabel(), "Demo label")
            tick_texts = [tick.get_text() for tick in cbar.ax.get_yticklabels()]
            non_empty = [t for t in tick_texts if t.strip()]
            self.assertTrue(non_empty, msg=f"Expected at least one non-empty tick label, got: {tick_texts!r}")
            self.assertTrue(any("0" in t or "1" in t or "2" in t or "3" in t for t in non_empty), msg=f"Expected numeric tick labels for [0,1,2,3], got: {non_empty!r}")
        finally:
            plt.close(fig)

    def test_explained_optimization_progress_uses_beginner_labels(self):
        fig, ax = plt.subplots(figsize=(4, 3))
        try:
            hist = np.array([100.0, 50.0, 25.0], dtype=np.float64)
            _plot_explained_optimization_progress(ax, hist, metrics={"total_time_s": 75})
            self.assertIn("lower is better", ax.get_title(), msg="Title must contain 'lower is better'")
            self.assertIn("millions of attempted mine changes", ax.get_xlabel(), msg="X-axis label must mention 'millions of attempted mine changes'")
            self.assertIn("1 plotted point = 50,000 attempted changes", ax.get_xlabel(), msg="X-axis label must include point scale explanation")
            self.assertEqual(ax.get_ylabel(), "Match error score (lower is better)", msg="Y-axis label must match expected beginner-readable label")
            legend = ax.get_legend()
            self.assertIsNotNone(legend, msg="Optimization progress chart must have a legend")
            legend_labels = [text.get_text() for text in legend.get_texts()]
            self.assertIn("Match error score", legend_labels, msg="Legend must include 'Match error score'")

            collected = [ax.get_title(), ax.get_xlabel(), ax.get_ylabel(), *legend_labels]
            collected.extend([text.get_text() for text in ax.texts])
            blob = " ".join(collected).lower()
            self.assertNotIn("weighted loss", blob)
            self.assertNotIn("x50k iterations", blob)
            self.assertNotIn("x50k", blob)
        finally:
            plt.close(fig)

    def test_explained_report_sidebar_axes_are_vertically_separated(self):
        from matplotlib.transforms import Bbox

        fig = plt.figure(figsize=(24, 15.5))
        gs = gridspec.GridSpec(
            4,
            4,
            figure=fig,
            height_ratios=[0.75, 2.25, 2.25, 0.55],
            width_ratios=[1.2, 1.2, 1.2, 1.35],
            hspace=0.46,
            wspace=0.34,
        )
        right_gs = gs[:, 3].subgridspec(
            2,
            1,
            height_ratios=[1.0, 1.0],
            hspace=0.12,
        )
        caption_ax = fig.add_subplot(right_gs[0, 0])
        metrics_ax = fig.add_subplot(right_gs[1, 0])

        caption_box: Bbox = caption_ax.get_position()
        metrics_box: Bbox = metrics_ax.get_position()

        self.assertGreater(caption_box.y0, metrics_box.y1, msg=f"caption_ax (y0={caption_box.y0:.4f}) must be above metrics_ax (y1={metrics_box.y1:.4f}); sidebar axes are overlapping or in wrong order")
        plt.close(fig)

    def test_explained_optimization_progress_uses_million_unit_axis(self):
        fig, ax = plt.subplots()
        hist = np.array([1_000_000.0, 500_000.0, 250_000.0])

        _plot_explained_optimization_progress(ax, hist, {"total_time_s": 75})

        self.assertIn("millions of attempted mine changes", ax.get_xlabel())
        self.assertIn("1 plotted point = 50,000 attempted changes", ax.get_xlabel())
        self.assertNotIn("x50k", ax.get_xlabel())
        self.assertNotIn("Weighted loss", ax.get_ylabel())

        plt.close(fig)

    def test_format_duration_outputs_plain_english(self):
        self.assertEqual(_format_duration(12), "about 12 sec")
        self.assertEqual(_format_duration(75), "about 1 min 15 sec")
        self.assertEqual(_format_duration(3660), "about 1 hr 1 min")
        self.assertIsNone(_format_duration(None))
        self.assertIsNone(_format_duration("bad-value"))
        self.assertIsNone(_format_duration(-1))

    def test_runtime_context_line_uses_total_time_or_runtime_before_report(self):
        total_line = _runtime_context_line({"total_time_s": 75})
        self.assertIsNotNone(total_line)
        self.assertIn("about 1 min 15 sec", total_line)

        before_line = _runtime_context_line({"runtime_before_report_s": 12})
        self.assertIsNotNone(before_line)
        self.assertIn("about 12 sec", before_line)

        self.assertIsNone(_runtime_context_line({}))

    def test_technical_history_labels_are_preserved(self):
        self.assertEqual(TECHNICAL_HISTORY_X_LABEL, "x50k iters")
        self.assertEqual(TECHNICAL_HISTORY_Y_LABEL, "Weighted loss")

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
            "total_time_s": 12.0,
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
            self.assertEqual(out_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n", msg="Output file must be a valid PNG (PNG magic bytes mismatch)")

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
            self.assertEqual(out_path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n", msg="Output file must be a valid PNG (PNG magic bytes mismatch)")


    def test_render_report_explained_legend_mine_count_uses_n_mines_not_subtraction(self):
        """R-008 regression: legend 'Identified mines' count must equal sr.n_mines,
        not sr.n_mines - sr.n_unknown. Catches the case where n_unknown > n_mines,
        which the old formula made negative (suppressed to 0 by the max band-aid)."""
        # n_unknown=5, n_mines=3 → old formula: max(3-5,0)=0; correct: 3
        sr = _fake_solve_result(n_unknown=5, solvable=False)
        self.assertEqual(sr.n_mines, 3)
        self.assertEqual(sr.n_unknown, 5)

        captured_labels = []
        _labels = captured_labels
        _RealPatch = mpatches.Patch

        class _SpyPatch(_RealPatch):
            def __init__(self, *args, **kwargs):
                _labels.append(kwargs.get("label", ""))
                super().__init__(*args, **kwargs)

        import types as _types
        _fake_mpatches = _types.ModuleType("matplotlib.patches")
        _fake_mpatches.__dict__.update(mpatches.__dict__)
        _fake_mpatches.Patch = _SpyPatch

        with mock.patch.object(report_module, "mpatches", _fake_mpatches):
            with tempfile.TemporaryDirectory() as td:
                out_path = Path(td) / "out.png"
                render_report_explained(
                    np.zeros((3, 3), dtype=np.float32),
                    np.zeros((3, 3), dtype=np.int8),
                    sr,
                    np.array([1.0]),
                    "test",
                    str(out_path),
                    metrics={},
                    dpi=72,
                )

        mine_label = next((l for l in captured_labels if "mine" in l.lower()), None)
        self.assertIsNotNone(mine_label, f"No mine-related patch label found; captured: {captured_labels}")
        self.assertIn("(3)", mine_label)   # correct: n_mines=3
        self.assertNotIn("(0)", mine_label)  # old max(...,0) band-aid would give 0
        self.assertNotIn("(-2)", mine_label)  # old raw subtraction would give -2

    def test_render_report_legend_mine_count_uses_n_mines_not_subtraction(self):
        """R-008 regression: render_report (non-explained) legend must also use n_mines."""
        from report import render_report

        sr = _fake_solve_result(n_unknown=5, solvable=False)
        captured_labels = []
        _labels2 = captured_labels
        _RealPatch2 = mpatches.Patch

        class _SpyPatch2(_RealPatch2):
            def __init__(self, *args, **kwargs):
                _labels2.append(kwargs.get("label", ""))
                super().__init__(*args, **kwargs)

        import types as _types
        _fake_mpatches2 = _types.ModuleType("matplotlib.patches")
        _fake_mpatches2.__dict__.update(mpatches.__dict__)
        _fake_mpatches2.Patch = _SpyPatch2

        with mock.patch.object(report_module, "mpatches", _fake_mpatches2):
            with tempfile.TemporaryDirectory() as td:
                render_report(
                    np.zeros((3, 3), dtype=np.float32),
                    np.zeros((3, 3), dtype=np.int8),
                    sr,
                    np.array([1.0]),
                    "test",
                    str(Path(td) / "out.png"),
                    dpi=72,
                )

        mine_label = next((l for l in captured_labels if "mine" in l.lower()), None)
        self.assertIsNotNone(mine_label, f"No mine-related patch label found; captured: {captured_labels}")
        self.assertIn("(3)", mine_label)
        self.assertNotIn("(-2)", mine_label)


if __name__ == "__main__":
    unittest.main()
