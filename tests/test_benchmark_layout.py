import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import report
import run_benchmark
from pipeline import RepairRouteResult
from run_benchmark import (
    _board_aggregates,
    _build_child_metrics_document,
    _child_dir_name,
    _normal_benchmark_root,
    _rows_from_child_metrics,
    benchmark_child_artifact_filenames,
    parse_args,
    write_normal_benchmark_summaries,
)
from solver import SAFE, SolveResult
from source_config import resolve_source_image_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BenchmarkLayoutTests(unittest.TestCase):
    def test_benchmark_uses_shared_explained_report_renderer(self):
        self.assertIs(run_benchmark.render_report_explained, report.render_report_explained,
                      msg="run_benchmark.render_report_explained is not report.render_report_explained")
        self.assertIs(run_benchmark.render_repair_overlay_explained, report.render_repair_overlay_explained,
                      msg="run_benchmark.render_repair_overlay_explained is not report.render_repair_overlay_explained")

    def test_child_directory_naming(self):
        self.assertEqual(_child_dir_name(300, 370, 11), "300x370_seed11")
        # seed=0 zero-padding contract
        self.assertEqual(_child_dir_name(300, 370, 0), "300x370_seed0")
        # single-digit dimensions
        self.assertEqual(_child_dir_name(9, 9, 1), "9x9_seed1")
        # large seed — no truncation
        result = _child_dir_name(300, 370, 999999)
        self.assertIn("999999", result)

    def test_preserved_child_artifact_filenames(self):
        names = benchmark_child_artifact_filenames("300x370")
        self.assertEqual(set(names.keys()), {
            "metrics", "grid", "visual", "visual_explained",
            "overlay", "overlay_explained",
            "failure_taxonomy", "repair_route_decision", "visual_delta_summary",
        })
        self.assertEqual(names["metrics"], "metrics_300x370.json", msg="metrics filename mismatch")
        self.assertEqual(names["grid"], "grid_300x370.npy", msg="grid filename mismatch")
        self.assertEqual(names["visual"], "visual_300x370.png", msg="visual filename mismatch")
        self.assertEqual(names["visual_explained"], "visual_300x370_explained.png", msg="visual_explained filename mismatch")
        self.assertEqual(names["overlay"], "repair_overlay_300x370.png", msg="overlay filename mismatch")
        self.assertEqual(names["overlay_explained"], "repair_overlay_300x370_explained.png", msg="overlay_explained filename mismatch")
        self.assertEqual(names["failure_taxonomy"], "failure_taxonomy.json", msg="failure_taxonomy filename mismatch")
        self.assertEqual(names["repair_route_decision"], "repair_route_decision.json", msg="repair_route_decision filename mismatch")
        self.assertEqual(names["visual_delta_summary"], "visual_delta_summary.json", msg="visual_delta_summary filename mismatch")

    def test_child_metrics_document_includes_explained_artifacts_and_review_hints(self):
        flat_metrics = {
            "corridor_pct": 0.1,
            "phase1_budget_s": 12.0,
            "mean_abs_error": 0.25,
            "visual_delta": -0.1,
            "pct_within_1": 98.0,
            "n_unknown": 0,
            "coverage": 1.0,
            "solvable": True,
            "repair_route_selected": "phase2_full_repair",
            "phase1_repair_hit_time_budget": False,
            "phase2_full_repair_hit_time_budget": True,
            "last100_repair_hit_time_budget": False,
            "solver_summary": {},
        }
        doc = _build_child_metrics_document(
            flat_metrics,
            run_identity={
                "benchmark_run_id": "20260427T000000Z_demo_benchmark",
                "board_width": 300,
                "board_height": 370,
                "seed": 11,
                "child_run_dir": "results/benchmark/demo/300x370_seed11",
                "board": "300x370",
            },
            run_timing={},
            source_image={"name": "line_art_irl_11_v2.png"},
            source_image_validation={"ok": True, "canonical_match": None, "noncanonical_allowed": True, "warnings": []},
            board_sizing={},
            target_stats={},
            route_summary={
                "phase1_repair_hit_time_budget": False,
                "phase2_full_repair_hit_time_budget": True,
                "last100_repair_hit_time_budget": False,
            },
            artifact_inventory={
                "visual_png": "results/benchmark/demo/300x370_seed11/visual_300x370.png",
                "visual_explained_png": "results/benchmark/demo/300x370_seed11/visual_300x370_explained.png",
                "repair_overlay_png": "results/benchmark/demo/300x370_seed11/repair_overlay_300x370.png",
                "repair_overlay_explained_png": "results/benchmark/demo/300x370_seed11/repair_overlay_300x370_explained.png",
            },
            phase_timing={},
        )
        self.assertIn("visual_explained_png", doc["artifact_inventory"], msg="visual_explained_png missing from artifact_inventory")
        self.assertIn("repair_overlay_explained_png", doc["artifact_inventory"], msg="repair_overlay_explained_png missing from artifact_inventory")
        self.assertIn("best_artifact_to_open_first", doc["llm_review_summary"], msg="best_artifact_to_open_first missing from llm_review_summary")
        self.assertIn("best_artifact_to_open_second", doc["llm_review_summary"], msg="best_artifact_to_open_second missing from llm_review_summary")
        self.assertIn("best_repair_artifact_to_open_first", doc["llm_review_summary"], msg="best_repair_artifact_to_open_first missing from llm_review_summary")
        self.assertIn("best_repair_artifact_to_open_second", doc["llm_review_summary"], msg="best_repair_artifact_to_open_second missing from llm_review_summary")
        for field in (
            "phase1_repair_hit_time_budget",
            "phase2_full_repair_hit_time_budget",
            "last100_repair_hit_time_budget",
        ):
            self.assertIn(field, doc, msg=f"{field} missing from doc")
            self.assertIn(field, doc["repair_route_summary"], msg=f"{field} missing from doc['repair_route_summary']")
        # Assert the specific boolean values from the input
        self.assertFalse(doc["phase1_repair_hit_time_budget"], msg="phase1_repair_hit_time_budget should be False")
        self.assertTrue(doc["phase2_full_repair_hit_time_budget"], msg="phase2_full_repair_hit_time_budget should be True (set in input)")
        self.assertFalse(doc["last100_repair_hit_time_budget"], msg="last100_repair_hit_time_budget should be False")

    def test_rows_and_board_aggregates_include_repair_timeout_fields(self):
        metrics_docs = [
            {
                "board": "300x370",
                "seed": 11,
                "child_run_dir": "300x370_seed11",
                "n_unknown": 0,
                "coverage": 1.0,
                "solvable": True,
                "repair_route_selected": "phase2_full_repair",
                "repair_route_result": "solved",
                "phase2_fixes": 1,
                "last100_fixes": 0,
                "phase1_repair_hit_time_budget": True,
                "phase2_full_repair_hit_time_budget": False,
                "last100_repair_hit_time_budget": True,
                "visual_delta": 0.0,
                "total_time_s": 12.3,
                "source_image": {"name": "line.png", "stem": "line", "sha256": "abc"},
            }
        ]

        rows = _rows_from_child_metrics(metrics_docs)
        row = rows[0]
        self.assertTrue(row["phase1_repair_hit_time_budget"])
        self.assertFalse(row["phase2_full_repair_hit_time_budget"])
        self.assertTrue(row["last100_repair_hit_time_budget"])

        aggregates = _board_aggregates(rows)
        aggregate = aggregates[0]
        self.assertEqual(aggregate["phase1_repair_timeout_count"], 1)
        self.assertEqual(aggregate["phase2_full_repair_timeout_count"], 0)
        self.assertEqual(aggregate["last100_repair_timeout_count"], 1)
        self.assertTrue(aggregate["any_repair_timeout"], msg="any_repair_timeout should be True when at least one timeout occurred")

    def test_normal_root_derivation_default_and_out_dir(self):
        cfg = resolve_source_image_config("assets/line_art_irl_11_v2.png", project_root=PROJECT_ROOT)
        args_default = parse_args([], raw_argv=["run_benchmark.py"])
        root_default, run_id = _normal_benchmark_root(args_default, PROJECT_ROOT, cfg)
        expected_base = (PROJECT_ROOT / "results/benchmark").resolve().as_posix()
        self.assertTrue(
            root_default.as_posix().startswith(expected_base),
            msg=f"Expected path inside 'results/benchmark', got {root_default.as_posix()}",
        )
        self.assertIn(f"{cfg.stem}_benchmark", run_id)

        args_out = parse_args(["--out-dir", "results/custom_root"], raw_argv=["run_benchmark.py", "--out-dir", "results/custom_root"])
        root_out, _ = _normal_benchmark_root(args_out, PROJECT_ROOT, cfg)
        self.assertEqual(root_out, (PROJECT_ROOT / "results/custom_root").resolve())

    def test_summary_files_written_and_existing_files_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "benchmark_root"
            root.mkdir(parents=True, exist_ok=True)
            sentinel = root / "keep.txt"
            sentinel.write_text("keep", encoding="utf-8")

            source_cfg = resolve_source_image_config("assets/line_art_irl_11_v2.png", project_root=PROJECT_ROOT)
            rows = [
                {
                    "board": "300x370",
                    "seed": 11,
                    "child_dir": "300x370_seed11",
                    "n_unknown": 0,
                    "coverage": 1.0,
                    "solvable": True,
                    "repair_route_selected": "phase2_full_repair",
                    "repair_route_result": "solved",
                    "phase2_fixes": 2,
                    "last100_fixes": 0,
                    "phase1_repair_hit_time_budget": True,
                    "phase2_full_repair_hit_time_budget": False,
                    "last100_repair_hit_time_budget": True,
                    "visual_delta": 0.0,
                    "total_time_s": 12.3,
                    "source_image_name": source_cfg.name,
                    "source_image_stem": source_cfg.stem,
                    "source_image_project_relative_path": source_cfg.project_relative_path,
                    "source_image_sha256": source_cfg.sha256,
                }
            ]
            paths = write_normal_benchmark_summaries(
                benchmark_root=root,
                benchmark_run_id="20260426T000000Z_line_art_irl_11_v2_benchmark",
                source_cfg=source_cfg,
                source_validation={"ok": True, "warnings": []},
                rows=rows,
                widths=[300],
                seeds=[11],
            )
            self.assertTrue((root / "benchmark_summary.json").exists(), msg="benchmark_summary.json not written")
            self.assertTrue((root / "benchmark_summary.csv").exists(), msg="benchmark_summary.csv not written")
            self.assertTrue((root / "benchmark_summary.md").exists(), msg="benchmark_summary.md not written")
            self.assertTrue((root / "benchmark_results.json").exists(), msg="benchmark_results.json not written")
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep", msg="Pre-existing file was overwritten")
            self.assertIn("benchmark_summary_json", paths, msg="paths dict missing benchmark_summary_json key")
            summary = json.loads((root / "benchmark_summary.json").read_text(encoding="utf-8"))
            row = summary["rows"][0]
            self.assertTrue(row["phase1_repair_hit_time_budget"], msg="row phase1_repair_hit_time_budget should be True")
            self.assertFalse(row["phase2_full_repair_hit_time_budget"], msg="row phase2_full_repair_hit_time_budget should be False")
            self.assertTrue(row["last100_repair_hit_time_budget"], msg="row last100_repair_hit_time_budget should be True")
            aggregate = summary["board_aggregates"][0]
            self.assertEqual(aggregate["phase1_repair_timeout_count"], 1, msg="phase1_repair_timeout_count should be 1")
            self.assertEqual(aggregate["phase2_full_repair_timeout_count"], 0, msg="phase2_full_repair_timeout_count should be 0")
            self.assertEqual(aggregate["last100_repair_timeout_count"], 1, msg="last100_repair_timeout_count should be 1")
            self.assertTrue(aggregate["any_repair_timeout"], msg="any_repair_timeout should be True when at least one timeout occurred")
            compatibility = json.loads((root / "benchmark_results.json").read_text(encoding="utf-8"))
            self.assertIn("phase1_repair_hit_time_budget", compatibility[0], msg="compatibility row missing phase1_repair_hit_time_budget")
            with (root / "benchmark_summary.csv").open("r", encoding="utf-8", newline="") as handle:
                csv_rows = list(csv.DictReader(handle))
            for field in (
                "phase1_repair_hit_time_budget",
                "phase2_full_repair_hit_time_budget",
                "last100_repair_hit_time_budget",
            ):
                self.assertIn(field, csv_rows[0], msg=f"CSV row missing field: {field}")
            md_text = (root / "benchmark_summary.md").read_text(encoding="utf-8")
            self.assertIn("phase1_timeouts", md_text, msg="md missing 'phase1_timeouts'")
            self.assertIn("phase1_timeout", md_text, msg="md missing 'phase1_timeout'")

    def test_regression_result_includes_route_timeout_booleans(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_name = "fake.png"
            board_w = 2
            board_h = 2
            seed = 11
            baseline_dir = root / f"{image_name}_s{seed}"
            baseline_dir.mkdir(parents=True)
            grid = np.zeros((board_h, board_w), dtype=np.int8)
            np.save(baseline_dir / f"grid_{board_w}x{board_h}.npy", grid)
            (baseline_dir / f"metrics_{board_w}x{board_h}.json").write_text(
                json.dumps({"n_unknown": 1, "repair_reason": "baseline"}),
                encoding="utf-8",
            )
            route = RepairRouteResult(
                grid=grid,
                sr=SolveResult(
                    coverage=1.0,
                    solvable=True,
                    mine_accuracy=1.0,
                    n_unknown=0,
                    state=np.full((board_h, board_w), SAFE, dtype=np.int8),
                ),
                selected_route="phase2_full_repair",
                route_result="solved",
                route_outcome_detail="phase2_full_repair_solved",
                next_recommended_route=None,
                failure_taxonomy={"dominant_failure_class": "sealed_single_mesa", "sealed_cluster_count": 1},
                phase2_full_repair_hit_time_budget=True,
                last100_repair_hit_time_budget=False,
                phase2_full_repair_invoked=True,
                phase2_full_repair_n_fixed=1,
                phase2_full_repair_accepted_move_count=1,
                phase2_full_repair_solved=True,
                phase2_log=[{"accepted": True}],
                visual_delta_summary={"visual_delta": 0.0},
                decision={
                    "selected_route": "phase2_full_repair",
                    "route_result": "solved",
                    "route_outcome_detail": "phase2_full_repair_solved",
                    "next_recommended_route": None,
                    "solver_n_unknown_before": 0,
                    "solver_n_unknown_after": 0,
                    "phase2_full_repair_invoked": True,
                    "phase2_full_repair_hit_time_budget": True,
                    "phase2_full_repair_n_fixed": 1,
                    "phase2_full_repair_accepted_move_count": 1,
                    "phase2_full_repair_changed_grid": False,
                    "phase2_full_repair_reduced_unknowns": False,
                    "phase2_full_repair_solved": True,
                    "phase2_solver_n_unknown_before": 0,
                    "phase2_solver_n_unknown_after": 0,
                    "last100_invoked": False,
                    "last100_repair_hit_time_budget": False,
                    "last100_n_fixes": 0,
                    "last100_accepted_move_count": 0,
                    "last100_solver_n_unknown_before": None,
                    "last100_solver_n_unknown_after": None,
                    "last100_stop_reason": None,
                },
            )
            case = {
                "image_path": "fake.png",
                "image_name": image_name,
                "board_w": board_w,
                "board_h": board_h,
                "baseline_root": root.as_posix(),
            }

            with mock.patch("run_benchmark.load_image_smart", return_value=np.zeros((board_h, board_w), dtype=np.float32)):
                with mock.patch("run_benchmark.apply_piecewise_T_compression", return_value=np.zeros((board_h, board_w), dtype=np.float32)):
                    with mock.patch("run_benchmark.compute_zone_aware_weights", return_value=np.ones((board_h, board_w), dtype=np.float32)):
                        with mock.patch("run_benchmark.build_adaptive_corridors", return_value=(np.zeros((board_h, board_w), dtype=np.int8), 0.0, [], None)):
                            with mock.patch("run_benchmark.assert_board_valid"):
                                with mock.patch("run_benchmark.solve_board", return_value=route.sr):
                                    with mock.patch("run_benchmark.route_late_stage_failure", return_value=route):
                                        result = run_benchmark.run_regression_from_baseline(case, seed)

        self.assertFalse(result["phase1_repair_hit_time_budget"], msg="phase1_repair_hit_time_budget should be False (not set in route)")
        self.assertTrue(result["phase2_full_repair_hit_time_budget"], msg="phase2_full_repair_hit_time_budget should be True (set in route)")
        self.assertFalse(result["last100_repair_hit_time_budget"], msg="last100_repair_hit_time_budget should be False (not set in route)")

    def test_child_metrics_phase2_fixes_equals_accepted_move_count(self):
        flat_metrics = {
            "corridor_pct": 0.1,
            "phase1_budget_s": 12.0,
            "mean_abs_error": 0.25,
            "visual_delta": -0.1,
            "pct_within_1": 98.0,
            "n_unknown": 0,
            "coverage": 1.0,
            "solvable": True,
            "repair_route_selected": "phase2_full_repair",
            "phase2_fixes": 3,
            "phase2_full_repair_accepted_move_count": 3,
            "phase1_repair_hit_time_budget": False,
            "phase2_full_repair_hit_time_budget": False,
            "last100_repair_hit_time_budget": False,
            "solver_summary": {},
        }
        doc = _build_child_metrics_document(
            flat_metrics,
            run_identity={"benchmark_run_id": "x", "board_width": 300, "board_height": 370, "seed": 11, "child_run_dir": "x", "board": "300x370"},
            run_timing={},
            source_image={"name": "x.png"},
            source_image_validation={"ok": True, "canonical_match": None, "noncanonical_allowed": True, "warnings": []},
            board_sizing={},
            target_stats={},
            route_summary={
                "selected_route": "phase2_full_repair",
                "route_result": "solved",
                "route_outcome_detail": "phase2_full_repair_solved",
                "next_recommended_route": None,
                "phase2_fixes": 3,
                "phase2_full_repair_accepted_move_count": 3,
                "phase1_repair_hit_time_budget": False,
                "phase2_full_repair_hit_time_budget": False,
                "last100_repair_hit_time_budget": False,
            },
            artifact_inventory={},
            phase_timing={},
        )
        self.assertEqual(
            doc.get("phase2_fixes"),
            doc.get("phase2_full_repair_accepted_move_count"),
            msg="phase2_fixes must equal phase2_full_repair_accepted_move_count in child metrics",
        )

    def test_benchmark_summary_rows_contain_four_route_fields(self):
        rows = [
            {
                "board": "300x370",
                "seed": 11,
                "child_dir": "300x370_seed11",
                "n_unknown": 0,
                "coverage": 1.0,
                "solvable": True,
                "selected_route": "phase2_full_repair",
                "route_result": "solved",
                "route_outcome_detail": "phase2_full_repair_solved",
                "next_recommended_route": None,
                "repair_route_selected": "phase2_full_repair",
                "repair_route_result": "solved",
                "phase2_fixes": 1,
                "last100_fixes": 0,
                "phase2_full_repair_accepted_move_count": 1,
                "last100_accepted_move_count": 0,
                "phase1_repair_hit_time_budget": False,
                "phase2_full_repair_hit_time_budget": False,
                "last100_repair_hit_time_budget": False,
                "visual_delta": 0.0,
                "total_time_s": 12.3,
                "source_image_name": "x.png",
                "source_image_stem": "x",
                "source_image_project_relative_path": None,
                "source_image_sha256": "abc",
            }
        ]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "benchmark_root"
            root.mkdir(parents=True, exist_ok=True)
            source_cfg = resolve_source_image_config("assets/line_art_irl_11_v2.png", project_root=PROJECT_ROOT)
            paths = write_normal_benchmark_summaries(
                benchmark_root=root,
                benchmark_run_id="test_run_id",
                source_cfg=source_cfg,
                source_validation={"ok": True, "warnings": []},
                rows=rows,
                widths=[300],
                seeds=[11],
            )
            summary = json.loads((root / "benchmark_summary.json").read_text(encoding="utf-8"))
            row = summary["rows"][0]
            for field in ("selected_route", "route_result", "route_outcome_detail", "next_recommended_route"):
                self.assertIn(field, row, msg=f"benchmark summary row missing field: {field}")


if __name__ == "__main__":
    unittest.main()
