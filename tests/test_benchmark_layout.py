import tempfile
import unittest
from pathlib import Path

import report
import run_benchmark
from run_benchmark import (
    _build_child_metrics_document,
    _child_dir_name,
    _normal_benchmark_root,
    benchmark_child_artifact_filenames,
    parse_args,
    write_normal_benchmark_summaries,
)
from source_config import resolve_source_image_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BenchmarkLayoutTests(unittest.TestCase):
    def test_benchmark_uses_shared_explained_report_renderer(self):
        self.assertIs(run_benchmark.render_report_explained, report.render_report_explained)
        self.assertIs(run_benchmark.render_repair_overlay_explained, report.render_repair_overlay_explained)

    def test_child_directory_naming(self):
        self.assertEqual(_child_dir_name(300, 370, 11), "300x370_seed11")

    def test_preserved_child_artifact_filenames(self):
        names = benchmark_child_artifact_filenames("300x370")
        self.assertEqual(names["metrics"], "metrics_300x370.json")
        self.assertEqual(names["grid"], "grid_300x370.npy")
        self.assertEqual(names["visual"], "visual_300x370.png")
        self.assertEqual(names["visual_explained"], "visual_300x370_explained.png")
        self.assertEqual(names["overlay"], "repair_overlay_300x370.png")
        self.assertEqual(names["overlay_explained"], "repair_overlay_300x370_explained.png")
        self.assertEqual(names["failure_taxonomy"], "failure_taxonomy.json")
        self.assertEqual(names["repair_route_decision"], "repair_route_decision.json")
        self.assertEqual(names["visual_delta_summary"], "visual_delta_summary.json")

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
            route_summary={},
            artifact_inventory={
                "visual_png": "results/benchmark/demo/300x370_seed11/visual_300x370.png",
                "visual_explained_png": "results/benchmark/demo/300x370_seed11/visual_300x370_explained.png",
                "repair_overlay_png": "results/benchmark/demo/300x370_seed11/repair_overlay_300x370.png",
                "repair_overlay_explained_png": "results/benchmark/demo/300x370_seed11/repair_overlay_300x370_explained.png",
            },
            phase_timing={},
        )
        self.assertIn("visual_explained_png", doc["artifact_inventory"])
        self.assertIn("repair_overlay_explained_png", doc["artifact_inventory"])
        self.assertIn("best_artifact_to_open_first", doc["llm_review_summary"])
        self.assertIn("best_artifact_to_open_second", doc["llm_review_summary"])
        self.assertIn("best_repair_artifact_to_open_first", doc["llm_review_summary"])
        self.assertIn("best_repair_artifact_to_open_second", doc["llm_review_summary"])

    def test_normal_root_derivation_default_and_out_dir(self):
        cfg = resolve_source_image_config("assets/line_art_irl_11_v2.png", project_root=PROJECT_ROOT)
        args_default = parse_args([], raw_argv=["run_benchmark.py"])
        root_default, run_id = _normal_benchmark_root(args_default, PROJECT_ROOT, cfg)
        self.assertIn("results/benchmark", root_default.as_posix())
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
            self.assertTrue((root / "benchmark_summary.json").exists())
            self.assertTrue((root / "benchmark_summary.csv").exists())
            self.assertTrue((root / "benchmark_summary.md").exists())
            self.assertTrue((root / "benchmark_results.json").exists())
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "keep")
            self.assertIn("benchmark_summary_json", paths)


if __name__ == "__main__":
    unittest.main()
