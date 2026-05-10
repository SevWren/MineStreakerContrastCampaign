import importlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SourceImageCliContractTests(unittest.TestCase):
    def test_run_iter9_help_exposes_contract_flags(self):
        proc = subprocess.run(
            [sys.executable, "run_iter9.py", "--help"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        for flag in ["--image", "--out-dir", "--board-w", "--seed", "--allow-noncanonical", "--image-manifest", "--run-tag"]:
            with self.subTest(flag=flag):
                self.assertIn(flag, proc.stdout)

    def test_run_benchmark_help_exposes_contract_flags(self):
        proc = subprocess.run(
            [sys.executable, "run_benchmark.py", "--help"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr)
        for flag in [
            "--image",
            "--widths",
            "--seeds",
            "--out-dir",
            "--allow-noncanonical",
            "--image-manifest",
            "--regression-only",
            "--include-regressions",
        ]:
            with self.subTest(flag=flag):
                self.assertIn(flag, proc.stdout)

    def test_default_image_values(self):
        run_iter9 = importlib.import_module("run_iter9")
        run_benchmark = importlib.import_module("run_benchmark")
        iter9_args = run_iter9.parse_args([])
        bench_args = run_benchmark.parse_args([], raw_argv=["run_benchmark.py"])
        self.assertEqual(iter9_args.image, "assets/input_source_image.png")
        self.assertEqual(bench_args.image, "assets/input_source_image.png")

    def test_no_import_time_validation_in_entrypoints(self):
        for module_name in ("run_iter9", "run_benchmark"):
            with self.subTest(module=module_name):
                with mock.patch("assets.image_guard.verify_source_image", side_effect=RuntimeError("should not be called")) as guard:
                    sys.modules.pop(module_name, None)
                    module = importlib.import_module(module_name)
                    importlib.reload(module)
                    self.assertFalse(guard.called)

    def test_regression_only_rejects_explicit_normal_mode_flags(self):
        run_benchmark = importlib.import_module("run_benchmark")
        with self.assertRaises(SystemExit):
            run_benchmark.parse_args(
                ["--regression-only", "--image", "assets/line_art_irl_11_v2.png"],
                raw_argv=["run_benchmark.py", "--regression-only", "--image", "assets/line_art_irl_11_v2.png"],
            )
        with self.assertRaises(SystemExit):
            run_benchmark.parse_args(
                ["--regression-only", "--image=assets/line_art_irl_11_v2.png"],
                raw_argv=["run_benchmark.py", "--regression-only", "--image=assets/line_art_irl_11_v2.png"],
            )
        with self.assertRaises(SystemExit):
            run_benchmark.parse_args(
                ["--regression-only", "--widths=300"],
                raw_argv=["run_benchmark.py", "--regression-only", "--widths=300"],
            )
        with self.assertRaises(SystemExit):
            run_benchmark.parse_args(
                ["--regression-only", "--include-regressions"],
                raw_argv=["run_benchmark.py", "--regression-only", "--include-regressions"],
            )

    def test_regression_only_allows_out_dir(self):
        run_benchmark = importlib.import_module("run_benchmark")
        args = run_benchmark.parse_args(
            ["--regression-only", "--out-dir", "results/tmp_regression"],
            raw_argv=["run_benchmark.py", "--regression-only", "--out-dir", "results/tmp_regression"],
        )
        self.assertTrue(args.regression_only)
        self.assertEqual(args.out_dir, "results/tmp_regression")

    def test_run_tag_sanitization_contract(self):
        run_iter9 = importlib.import_module("run_iter9")
        sanitize = run_iter9.sanitize_run_tag
        self.assertEqual(sanitize("alpha beta"), "alpha_beta", msg="spaces should be replaced with underscores")
        self.assertEqual(sanitize("A--B__C"), "A_B_C", msg="multiple dashes/underscores should be collapsed")
        self.assertEqual(sanitize("___---"), "", msg="all separators should produce empty string")
        self.assertLessEqual(len(sanitize("a" * 200)), 64, msg="sanitized tag must be at most 64 characters")
        self.assertEqual(sanitize("  !! a  $$ b -- "), "a_b", msg="special chars and surrounding separators should be stripped")
        self.assertEqual(sanitize(""), "", msg="empty string input should produce empty string")

    def test_metrics_helper_blocks_exist_and_flat_keys_preserved(self):
        run_iter9 = importlib.import_module("run_iter9")
        flat = {
            "repair_route_selected": "phase2_full_repair",
            "repair_route_result": "solved",
            "visual_delta": 0.0,
            "coverage": 1.0,
            "n_unknown": 0,
        }
        doc = run_iter9.build_metrics_document(
            flat,
            run_identity={},
            run_timing={},
            project_identity={},
            command_invocation={},
            source_image={},
            source_image_analysis={},
            effective_config={},
            board_sizing={},
            preprocessing_config={},
            target_field_stats={},
            weight_config={},
            corridor_config={},
            sa_config={},
            repair_config={},
            solver_summary={},
            repair_route_summary={},
            visual_quality_summary={},
            runtime_phase_timing_s={},
            environment={},
            artifact_inventory={
                "visual_png": "results/iter9/example/iter9_300x370_FINAL.png",
                "visual_explained_png": "results/iter9/example/iter9_300x370_FINAL_explained.png",
                "repair_overlay_png": "results/iter9/example/repair_overlay_300x370.png",
                "repair_overlay_explained_png": "results/iter9/example/repair_overlay_300x370_explained.png",
            },
            validation_gates={},
            warnings_and_exceptions=[],
            llm_review_summary={
                "best_artifact_to_open_first": "results/iter9/example/iter9_300x370_FINAL_explained.png",
                "best_artifact_to_open_second": "results/iter9/example/iter9_300x370_FINAL.png",
                "best_repair_artifact_to_open_first": "results/iter9/example/repair_overlay_300x370_explained.png",
                "best_repair_artifact_to_open_second": "results/iter9/example/repair_overlay_300x370.png",
            },
            source_image_validation={"ok": True, "validation_mode": "default_manifest"},
        )
        required = [
            "schema_version",
            "run_identity",
            "run_timing",
            "project_identity",
            "command_invocation",
            "source_image",
            "source_image_analysis",
            "effective_config",
            "board_sizing",
            "preprocessing_config",
            "target_field_stats",
            "weight_config",
            "corridor_config",
            "sa_config",
            "repair_config",
            "solver_summary",
            "repair_route_summary",
            "visual_quality_summary",
            "runtime_phase_timing_s",
            "environment",
            "artifact_inventory",
            "validation_gates",
            "warnings_and_exceptions",
            "llm_review_summary",
        ]
        for key in required:
            with self.subTest(key=key):
                self.assertIn(key, doc)
        self.assertEqual(doc["repair_route_selected"], "phase2_full_repair")
        self.assertIn("repair_route_result", doc)
        self.assertIn("visual_delta", doc)
        self.assertIn("source_image_validation", doc)
        self.assertTrue(doc["source_image_validation"]["ok"])
        self.assertIn("visual_explained_png", doc["artifact_inventory"])
        self.assertIn("repair_overlay_explained_png", doc["artifact_inventory"])
        self.assertIn("best_artifact_to_open_first", doc["llm_review_summary"])
        self.assertIn("best_artifact_to_open_second", doc["llm_review_summary"])
        self.assertIn("best_repair_artifact_to_open_first", doc["llm_review_summary"])
        self.assertIn("best_repair_artifact_to_open_second", doc["llm_review_summary"])

    def test_pipeline_run_board_is_present_and_deprecated(self):
        pipeline = importlib.import_module("pipeline")
        self.assertTrue(hasattr(pipeline, "run_board"))
        self.assertIn("deprecated", (pipeline.run_board.__doc__ or "").lower(), msg="run_board.__doc__ must mention 'deprecated'")
        with mock.patch("assets.image_guard.verify_source_image", side_effect=RuntimeError("stop")):
            with self.assertWarnsRegex(DeprecationWarning, "deprecated"):
                with self.assertRaisesRegex(RuntimeError, "stop"):
                    pipeline.run_board(
                        board_w=10,
                        board_h=10,
                        label="deprecation-test",
                        sa_fn=None,
                        img_path="assets/input_source_image.png",
                        out_dir=str(PROJECT_ROOT / "results" / "tmp_deprecation_test"),
                        verbose=False,
                    )

    def test_removed_legacy_visual_report_script_is_absent(self):
        legacy_script = PROJECT_ROOT / "run_iris3d_visual_report.py"
        self.assertFalse(legacy_script.exists(), msg=f"Legacy script {legacy_script} must have been removed")

    def test_abs_error_variance_replaces_loss_per_cell_in_metrics_write_sites(self):
        """R-009 regression: both metrics write sites must use abs_error_variance,
        not the old misleading name loss_per_cell."""
        for fname in ("run_iter9.py", "pipeline.py"):
            source = (PROJECT_ROOT / fname).read_text(encoding="utf-8")
            self.assertIn(
                "abs_error_variance", source,
                f"{fname} must contain abs_error_variance",
            )
            self.assertNotIn(
                '"loss_per_cell"', source,
                f"{fname} must not contain the old field name loss_per_cell",
            )


if __name__ == "__main__":
    unittest.main()
