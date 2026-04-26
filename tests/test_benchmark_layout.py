import tempfile
import unittest
from pathlib import Path

from run_benchmark import (
    _child_dir_name,
    _normal_benchmark_root,
    benchmark_child_artifact_filenames,
    parse_args,
    write_normal_benchmark_summaries,
)
from source_config import resolve_source_image_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class BenchmarkLayoutTests(unittest.TestCase):
    def test_child_directory_naming(self):
        self.assertEqual(_child_dir_name(300, 370, 11), "300x370_seed11")

    def test_preserved_child_artifact_filenames(self):
        names = benchmark_child_artifact_filenames("300x370")
        self.assertEqual(names["metrics"], "metrics_300x370.json")
        self.assertEqual(names["grid"], "grid_300x370.npy")
        self.assertEqual(names["visual"], "visual_300x370.png")
        self.assertEqual(names["overlay"], "repair_overlay_300x370.png")
        self.assertEqual(names["failure_taxonomy"], "failure_taxonomy.json")
        self.assertEqual(names["repair_route_decision"], "repair_route_decision.json")
        self.assertEqual(names["visual_delta_summary"], "visual_delta_summary.json")

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
