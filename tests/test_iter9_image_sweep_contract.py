from __future__ import annotations
import argparse
import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_iter9
from source_config import SourceImageConfig


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def make_source_cfg(path: Path, *, sha: str | None = None) -> SourceImageConfig:
    digest = sha or ("a" * 64)
    return SourceImageConfig(
        command_arg=path.as_posix(),
        absolute_path=path.resolve(),
        project_relative_path=None,
        name=path.name,
        stem=path.stem,
        sha256=digest,
        size_bytes=int(path.stat().st_size) if path.exists() else 1,
        allow_noncanonical=True,
        manifest_path=None,
    )


def write_fake_png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not-a-real-png-but-valid-for-discovery-tests")
    return path


def make_minimal_metrics_doc_kwargs() -> dict:
    return {
        "run_identity": {},
        "run_timing": {},
        "project_identity": {},
        "command_invocation": {},
        "source_image": {},
        "source_image_analysis": {},
        "effective_config": {},
        "board_sizing": {},
        "preprocessing_config": {},
        "target_field_stats": {},
        "weight_config": {},
        "corridor_config": {},
        "sa_config": {},
        "repair_config": {},
        "solver_summary": {},
        "repair_route_summary": {},
        "visual_quality_summary": {},
        "runtime_phase_timing_s": {},
        "environment": {},
        "artifact_inventory": {},
        "validation_gates": {},
        "warnings_and_exceptions": [],
        "llm_review_summary": {},
        "source_image_validation": {},
    }


def make_success_metrics_doc(image_stem: str, *, board: str = "300x370", seed: int = 11) -> dict:
    child_dir = f"results/out/{image_stem}_{board}_seed{seed}"
    return {
        "board": board,
        "seed": int(seed),
        "n_unknown": 0,
        "coverage": 1.0,
        "solvable": True,
        "mean_abs_error": 0.1,
        "repair_route_selected": "already_solved",
        "selected_route": "already_solved",
        "route_result": "solved",
        "route_outcome_detail": "already_solved_before_routing",
        "next_recommended_route": None,
        "phase1_repair_hit_time_budget": False,
        "phase2_full_repair_hit_time_budget": False,
        "last100_repair_hit_time_budget": False,
        "repair_route_summary": {
            "selected_route": "already_solved",
            "route_result": "solved",
            "route_outcome_detail": "already_solved_before_routing",
            "next_recommended_route": None,
            "phase1_repair_hit_time_budget": False,
            "phase2_full_repair_hit_time_budget": False,
            "last100_repair_hit_time_budget": False,
        },
        "run_identity": {"output_dir": child_dir},
        "artifact_inventory": {"metrics_json": f"{child_dir}/metrics_iter9_{board}.json"},
        "llm_review_summary": {
            "best_artifact_to_open_first": f"{child_dir}/iter9_{board}_FINAL_explained.png"
        },
    }


def make_sweep_args(image_dir: Path, out_root: Path, *extra: str) -> argparse.Namespace:
    raw = [
        "--image-dir",
        image_dir.as_posix(),
        "--image-glob",
        "*.png",
        "--seed",
        "11",
        "--allow-noncanonical",
        "--out-root",
        out_root.as_posix(),
        *extra,
    ]
    return run_iter9.parse_args(raw)


def configure_successful_batch_mocks(
    *,
    resolve_mock,
    verify_mock,
    sizing_mock,
    compile_mock,
    warm_mock,
    single_mock,
    image_paths: list[Path],
) -> None:
    source_cfgs = [make_source_cfg(path, sha=f"{index + 1:064x}") for index, path in enumerate(image_paths)]
    resolve_mock.side_effect = source_cfgs
    verify_mock.return_value = {
        "ok": True,
        "canonical_match": False,
        "noncanonical_allowed": True,
        "warnings": [],
    }
    sizing_mock.return_value = {
        "board_width": 300,
        "board_height": 370,
        "gate_aspect_ratio_within_tolerance": True,
    }
    compile_mock.return_value = object()
    warm_mock.return_value = None
    single_mock.side_effect = [
        make_success_metrics_doc(source_cfg.stem, board="300x370", seed=11)
        for source_cfg in source_cfgs
    ]


def make_sweep_raw_argv(image_dir: Path, out_root: Path, *extra: str) -> list[str]:
    return [
        "--image-dir",
        image_dir.as_posix(),
        "--image-glob",
        "*.png",
        "--seed",
        "11",
        "--allow-noncanonical",
        "--out-root",
        out_root.as_posix(),
        *extra,
    ]


class Iter9ImageSweepContractTests(unittest.TestCase):
    def test_help_exposes_all_image_sweep_flags(self):
        completed = subprocess.run(
            [sys.executable, "run_iter9.py", "--help"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, msg=completed.stderr)
        for flag in [
            "--image-dir",
            "--image-glob",
            "--recursive",
            "--out-root",
            "--continue-on-error",
            "--skip-existing",
            "--max-images",
        ]:
            with self.subTest(flag=flag):
                self.assertIn(flag, completed.stdout)

    def test_argparse_rejects_abbreviated_long_flags(self):
        bad_argv = [
            ["--image-g", "*.png"],
            ["--rec"],
            ["--image-dir", "assets", "--image-man", "x.json"],
        ]
        for argv in bad_argv:
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    run_iter9.parse_args(argv)

    def test_discovery_direct_matches_are_sorted(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            write_fake_png(image_dir / "zeta.png")
            write_fake_png(image_dir / "alpha.png")
            write_fake_png(image_dir / "m.png")
            write_fake_png(image_dir / "nested" / "nested.png")
            write_fake_png(image_dir / "a.jpg")

            discovered = run_iter9.discover_source_images(image_dir, "*.png", recursive=False, max_images=None)
            names = [path.name for path in discovered]

        self.assertEqual(names, ["alpha.png", "m.png", "zeta.png"])
        self.assertNotIn("nested.png", names, msg="nested/nested.png must be excluded when recursive=False")
        self.assertNotIn("a.jpg", names, msg="a.jpg must be excluded when glob is *.png")

    def test_discovery_recursive_includes_nested_matches(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            write_fake_png(image_dir / "top.png")
            write_fake_png(image_dir / "nested" / "a.png")
            write_fake_png(image_dir / "nested" / "deeper" / "b.png")

            discovered = run_iter9.discover_source_images(image_dir, "*.png", recursive=True, max_images=None)

        self.assertEqual([path.name for path in discovered], ["a.png", "b.png", "top.png"])

    def test_discovery_applies_max_images_after_sorting(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            write_fake_png(image_dir / "c.png")
            write_fake_png(image_dir / "a.png")
            write_fake_png(image_dir / "b.png")

            discovered = run_iter9.discover_source_images(image_dir, "*.png", recursive=False, max_images=2)

        self.assertEqual([path.name for path in discovered], ["a.png", "b.png"])

    def test_discovery_missing_directory_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing = root / "missing"
            with self.assertRaises(FileNotFoundError):
                run_iter9.discover_source_images(missing, "*.png")

    def test_discovery_file_instead_of_directory_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            file_path = write_fake_png(root / "not_a_dir.png")
            with self.assertRaises(NotADirectoryError):
                run_iter9.discover_source_images(file_path, "*.png")

    def test_discovery_empty_match_fails(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            image_dir.mkdir(parents=True, exist_ok=True)
            write_fake_png(image_dir / "a.jpg")
            with self.assertRaises(ValueError):
                run_iter9.discover_source_images(image_dir, "*.png")

    def test_image_dir_plus_explicit_image_fails(self):
        invalid = [
            ["--image-dir", "assets", "--image", "assets/foo.png"],
            ["--image-dir", "assets", "--image=assets/foo.png"],
        ]
        for argv in invalid:
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    run_iter9.parse_args(argv)

    def test_image_dir_plus_out_dir_fails(self):
        with self.assertRaises(SystemExit):
            run_iter9.parse_args(["--image-dir", "assets", "--out-dir", "results/x"])

    def test_sweep_only_flags_without_image_dir_fail(self):
        invalid = [
            ["--out-root", "results/x"],
            ["--image-glob", "*.jpg"],
            ["--recursive"],
            ["--continue-on-error"],
            ["--skip-existing"],
            ["--max-images", "2"],
        ]
        for argv in invalid:
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    run_iter9.parse_args(argv)

    def test_image_dir_plus_image_manifest_fails(self):
        invalid = [
            ["--image-dir", "assets", "--image-manifest", "assets/SOURCE_IMAGE_HASH.json"],
            ["--image-dir", "assets", "--image-manifest=assets/SOURCE_IMAGE_HASH.json"],
        ]
        for argv in invalid:
            with self.subTest(argv=argv):
                with self.assertRaises(SystemExit):
                    run_iter9.parse_args(argv)

    def test_max_images_zero_fails(self):
        with self.assertRaises(SystemExit):
            run_iter9.parse_args(["--image-dir", "assets", "--max-images", "0"])

    def test_child_output_directory_includes_full_board_label(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source_cfg = make_source_cfg(write_fake_png(root / "images" / "sample.png"))
            child = run_iter9.build_image_sweep_child_out_dir(
                root / "out",
                source_cfg=source_cfg,
                board_label="420x510",
                seed=11,
                colliding_stem_tokens=set(),
            )
        self.assertIn("420x510_seed11", child.name)
        self.assertTrue(child.name.startswith("sample_420x510_seed11"))

    def test_sanitized_stem_collisions_include_sha_and_path_hash(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path_a = write_fake_png(root / "images" / "A B.png")
            path_b = write_fake_png(root / "images" / "A-B.png")
            cfg_a = make_source_cfg(path_a, sha="1" * 64)
            cfg_b = make_source_cfg(path_b, sha="2" * 64)
            collisions = run_iter9._colliding_sanitized_stem_tokens([path_a, path_b])
            out_root = root / "out"

            child_a = run_iter9.build_image_sweep_child_out_dir(
                out_root,
                source_cfg=cfg_a,
                board_label="300x370",
                seed=11,
                colliding_stem_tokens=collisions,
            )
            child_b = run_iter9.build_image_sweep_child_out_dir(
                out_root,
                source_cfg=cfg_b,
                board_label="300x370",
                seed=11,
                colliding_stem_tokens=collisions,
            )

        self.assertIn(cfg_a.sha256[:12], child_a.name)
        self.assertIn(cfg_b.sha256[:12], child_b.name)
        self.assertIn(run_iter9._path_hash_token(cfg_a.absolute_path), child_a.name)
        self.assertIn(run_iter9._path_hash_token(cfg_b.absolute_path), child_b.name)
        self.assertNotEqual(child_a.name, child_b.name)

    def test_case_insensitive_stem_collisions_are_detected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path_a = write_fake_png(root / "images" / "Alpha.png")
            path_b = write_fake_png(root / "images" / "alpha.png")
            collisions = run_iter9._colliding_sanitized_stem_tokens([path_a, path_b])
        self.assertIn("alpha", collisions)

    def test_same_stem_same_sha_duplicate_produces_distinct_child_directories(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path_a = write_fake_png(root / "images" / "dup" / "same.png")
            path_b = write_fake_png(root / "images" / "other" / "same.png")
            cfg_a = make_source_cfg(path_a, sha="3" * 64)
            cfg_b = make_source_cfg(path_b, sha="3" * 64)
            collisions = run_iter9._colliding_sanitized_stem_tokens([path_a, path_b])

            child_a = run_iter9.build_image_sweep_child_out_dir(
                root / "out",
                source_cfg=cfg_a,
                board_label="300x370",
                seed=11,
                colliding_stem_tokens=collisions,
            )
            child_b = run_iter9.build_image_sweep_child_out_dir(
                root / "out",
                source_cfg=cfg_b,
                board_label="300x370",
                seed=11,
                colliding_stem_tokens=collisions,
            )

        self.assertNotEqual(child_a.name, child_b.name)

    def test_build_metrics_document_includes_optional_batch_context(self):
        kwargs = make_minimal_metrics_doc_kwargs()
        doc = run_iter9.build_metrics_document(
            {"board": "300x370", "seed": 11},
            **kwargs,
            batch_context={"batch_mode": "iter9_image_sweep", "batch_index": 1},
        )
        self.assertEqual(doc["batch_context"]["batch_mode"], "iter9_image_sweep")
        doc_without_batch = run_iter9.build_metrics_document({"board": "300x370"}, **kwargs)
        self.assertNotIn("batch_context", doc_without_batch)

    def test_build_metrics_document_includes_source_image_validation(self):
        kwargs = make_minimal_metrics_doc_kwargs()
        kwargs["source_image_validation"] = {
            "ok": True,
            "canonical_match": False,
            "noncanonical_allowed": True,
            "warnings": [],
        }

        doc = run_iter9.build_metrics_document(
            {"board": "300x370", "seed": 11},
            **kwargs,
        )

        self.assertIn("source_image_validation", doc)
        self.assertEqual(
            doc["source_image_validation"],
            {
                "ok": True,
                "canonical_match": False,
                "noncanonical_allowed": True,
                "warnings": [],
            },
        )

    def test_build_metrics_document_includes_repair_timeout_fields(self):
        kwargs = make_minimal_metrics_doc_kwargs()
        kwargs["repair_route_summary"] = {
            "phase1_repair_hit_time_budget": True,
            "phase2_full_repair_hit_time_budget": False,
            "last100_repair_hit_time_budget": True,
        }
        doc = run_iter9.build_metrics_document(
            {
                "board": "300x370",
                "seed": 11,
                "phase1_repair_hit_time_budget": True,
                "phase2_full_repair_hit_time_budget": False,
                "last100_repair_hit_time_budget": True,
            },
            **kwargs,
        )

        for field in (
            "phase1_repair_hit_time_budget",
            "phase2_full_repair_hit_time_budget",
            "last100_repair_hit_time_budget",
        ):
            self.assertIn(field, doc)
            self.assertIn(field, doc["repair_route_summary"])

    def test_sweep_success_child_metrics_include_repair_timeout_fields(self):
        metrics_doc = make_success_metrics_doc("sample")
        for field in (
            "phase1_repair_hit_time_budget",
            "phase2_full_repair_hit_time_budget",
            "last100_repair_hit_time_budget",
        ):
            self.assertIn(field, metrics_doc)
            self.assertIn(field, metrics_doc["repair_route_summary"])

    def test_md_table_cell_escapes_pipes_and_newlines(self):
        escaped = run_iter9._md_table_cell("a|b\r\nc\\d")
        self.assertEqual(escaped, "a\\|b  c\\\\d")

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_batch_runner_calls_single_run_once_per_image(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            image_paths = [
                write_fake_png(image_dir / "a.png"),
                write_fake_png(image_dir / "b.png"),
            ]
            configure_successful_batch_mocks(
                resolve_mock=resolve_mock,
                verify_mock=verify_mock,
                sizing_mock=sizing_mock,
                compile_mock=compile_mock,
                warm_mock=warm_mock,
                single_mock=single_mock,
                image_paths=image_paths,
            )

            args = make_sweep_args(image_dir, out_root)
            raw_argv = make_sweep_raw_argv(image_dir, out_root)
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)
            summary_path = out_root / "iter9_image_sweep_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        self.assertEqual(single_mock.call_count, 2, msg="run_iter9_single must be called once per image (2 images → 2 calls)")
        self.assertEqual(compile_mock.call_count, 1, msg="compile_sa_kernel must be called exactly once (shared across images)")
        self.assertEqual(warm_mock.call_count, 1, msg="ensure_solver_warmed must be called exactly once")
        self.assertEqual([row["status"] for row in summary["rows"]], ["succeeded", "succeeded"], msg="Both images should have status='succeeded'")

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_validation_failure_writes_failed_row_and_summary(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            image_path = write_fake_png(image_dir / "bad.png")
            source_cfg = make_source_cfg(image_path)

            resolve_mock.return_value = source_cfg
            verify_mock.return_value = {
                "ok": False,
                "canonical_match": False,
                "noncanonical_allowed": True,
                "warnings": [],
            }
            sizing_mock.return_value = {
                "board_width": 300,
                "board_height": 370,
                "gate_aspect_ratio_within_tolerance": True,
            }
            compile_mock.return_value = object()
            warm_mock.return_value = None

            args = make_sweep_args(image_dir, out_root)
            raw_argv = make_sweep_raw_argv(image_dir, out_root)
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)
            summary_path = out_root / "iter9_image_sweep_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 1)
        single_mock.assert_not_called()
        self.assertEqual(summary["rows"][0]["status"], "failed")
        self.assertEqual(summary["rows"][0]["error_type"], "ValueError")
        self.assertIn("Source image validation failed:", summary["rows"][0]["error_message"])

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_fail_fast_stops_after_first_runtime_failure_and_writes_summaries(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            image_paths = [
                write_fake_png(image_dir / "a.png"),
                write_fake_png(image_dir / "b.png"),
            ]
            source_cfgs = [make_source_cfg(path, sha=f"{index + 1:064x}") for index, path in enumerate(image_paths)]

            resolve_mock.side_effect = source_cfgs
            verify_mock.return_value = {
                "ok": True,
                "canonical_match": False,
                "noncanonical_allowed": True,
                "warnings": [],
            }
            sizing_mock.return_value = {
                "board_width": 300,
                "board_height": 370,
                "gate_aspect_ratio_within_tolerance": True,
            }
            compile_mock.return_value = object()
            warm_mock.return_value = None
            single_mock.side_effect = [RuntimeError("boom"), make_success_metrics_doc("b", board="300x370", seed=11)]

            args = make_sweep_args(image_dir, out_root)
            raw_argv = make_sweep_raw_argv(image_dir, out_root)
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)
            summary = json.loads((out_root / "iter9_image_sweep_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 1)
        self.assertEqual(single_mock.call_count, 1, msg="fail-fast should stop after first failure; single_run should be called only once")
        self.assertEqual([row["status"] for row in summary["rows"]], ["failed"], msg="summary should contain exactly one failed row")
        self.assertEqual(summary["runs_attempted"], 1, msg="runs_attempted should be 1 (only the failed run)")
        self.assertEqual(summary["runs_failed"], 1, msg="runs_failed should be 1")

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_continue_on_error_attempts_all_images(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            image_paths = [
                write_fake_png(image_dir / "a.png"),
                write_fake_png(image_dir / "b.png"),
                write_fake_png(image_dir / "c.png"),
            ]
            source_cfgs = [make_source_cfg(path, sha=f"{index + 1:064x}") for index, path in enumerate(image_paths)]

            resolve_mock.side_effect = source_cfgs
            verify_mock.return_value = {
                "ok": True,
                "canonical_match": False,
                "noncanonical_allowed": True,
                "warnings": [],
            }
            sizing_mock.return_value = {
                "board_width": 300,
                "board_height": 370,
                "gate_aspect_ratio_within_tolerance": True,
            }
            compile_mock.return_value = object()
            warm_mock.return_value = None
            single_mock.side_effect = [
                make_success_metrics_doc("a", board="300x370", seed=11),
                RuntimeError("boom"),
                make_success_metrics_doc("c", board="300x370", seed=11),
            ]

            args = make_sweep_args(image_dir, out_root, "--continue-on-error")
            raw_argv = make_sweep_raw_argv(image_dir, out_root, "--continue-on-error")
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)
            summary = json.loads((out_root / "iter9_image_sweep_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 1)
        self.assertEqual(single_mock.call_count, 3)
        self.assertEqual([row["status"] for row in summary["rows"]], ["succeeded", "failed", "succeeded"])

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_skip_existing_prevents_single_run_call(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            image_path = write_fake_png(image_dir / "sample.png")
            source_cfg = make_source_cfg(image_path)

            resolve_mock.return_value = source_cfg
            verify_mock.return_value = {
                "ok": True,
                "canonical_match": False,
                "noncanonical_allowed": True,
                "warnings": [],
            }
            sizing_mock.return_value = {
                "board_width": 420,
                "board_height": 510,
                "gate_aspect_ratio_within_tolerance": True,
            }
            compile_mock.return_value = object()
            warm_mock.return_value = None

            collisions = run_iter9._colliding_sanitized_stem_tokens([image_path])
            child_dir = run_iter9.build_image_sweep_child_out_dir(
                out_root,
                source_cfg=source_cfg,
                board_label="420x510",
                seed=11,
                colliding_stem_tokens=collisions,
            )
            child_dir.mkdir(parents=True, exist_ok=True)
            expected_metrics = child_dir / "metrics_iter9_420x510.json"
            expected_metrics.write_text(
                json.dumps(
                    {
                        "n_unknown": 0,
                        "coverage": 1.0,
                        "solvable": True,
                        "mean_abs_error": 0.2,
                        "repair_route_selected": "already_solved",
                        "llm_review_summary": {"best_artifact_to_open_first": "artifact.png"},
                    }
                ),
                encoding="utf-8",
            )

            args = make_sweep_args(image_dir, out_root, "--skip-existing")
            raw_argv = make_sweep_raw_argv(image_dir, out_root, "--skip-existing")
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)
            summary = json.loads((out_root / "iter9_image_sweep_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        single_mock.assert_not_called()
        self.assertEqual(summary["rows"][0]["status"], "skipped_existing")
        self.assertIn("metrics_path", summary["rows"][0], msg="skipped_existing row must contain 'metrics_path' key")
        self.assertIn("420x510", summary["rows"][0]["metrics_path"], msg="metrics_path must include the board label '420x510'")

    def test_summaries_write_json_csv_and_markdown(self):
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td) / "out"
            rows = [
                {
                    "batch_index": 1,
                    "image_path": "a.png",
                    "image_name": "a.png",
                    "image_stem": "a",
                    "source_image_sha256": "1" * 64,
                    "status": "succeeded",
                    "child_run_dir": "results/out/a",
                    "metrics_path": "results/out/a/metrics_iter9_300x370.json",
                    "best_artifact_to_open_first": "results/out/a/iter9_300x370_FINAL_explained.png",
                    "board": "300x370",
                    "seed": 11,
                    "n_unknown": 0,
                    "coverage": 1.0,
                    "solvable": True,
                    "mean_abs_error": 0.1,
                    "repair_route_selected": "already_solved",
                    "error_type": None,
                    "error_message": None,
                },
                {
                    "batch_index": 2,
                    "image_path": "b.png",
                    "image_name": "b.png",
                    "image_stem": "b",
                    "source_image_sha256": "2" * 64,
                    "status": "failed",
                    "child_run_dir": None,
                    "metrics_path": None,
                    "best_artifact_to_open_first": None,
                    "board": None,
                    "seed": 11,
                    "n_unknown": None,
                    "coverage": None,
                    "solvable": None,
                    "mean_abs_error": None,
                    "repair_route_selected": None,
                    "error_type": "RuntimeError",
                    "error_message": "bad|line\nbreak",
                },
                {
                    "batch_index": 3,
                    "image_path": "c.png",
                    "image_name": "c.png",
                    "image_stem": "c",
                    "source_image_sha256": "3" * 64,
                    "status": "skipped_existing",
                    "child_run_dir": "results/out/c",
                    "metrics_path": "results/out/c/metrics_iter9_300x370.json",
                    "best_artifact_to_open_first": None,
                    "board": "300x370",
                    "seed": 11,
                    "n_unknown": None,
                    "coverage": None,
                    "solvable": None,
                    "mean_abs_error": None,
                    "repair_route_selected": None,
                    "error_type": None,
                    "error_message": None,
                },
            ]
            run_iter9.write_iter9_image_sweep_summaries(
                out_root=out_root,
                batch_id="batch123",
                image_dir="assets",
                image_glob="*.png",
                recursive=False,
                board_w=300,
                seed=11,
                started_at_utc="2026-01-01T00:00:00.000Z",
                finished_at_utc="2026-01-01T00:01:00.000Z",
                duration_wall_s=60.0,
                batch_warmup_s=1.0,
                rows=rows,
                images_discovered=3,
            )

            summary_json = out_root / "iter9_image_sweep_summary.json"
            summary_csv = out_root / "iter9_image_sweep_summary.csv"
            summary_md = out_root / "iter9_image_sweep_summary.md"
            summary_json_exists = summary_json.exists()
            summary_csv_exists = summary_csv.exists()
            summary_md_exists = summary_md.exists()
            summary = json.loads(summary_json.read_text(encoding="utf-8"))
            csv_text = summary_csv.read_text(encoding="utf-8")
            csv_rows_parsed = list(csv.reader(io.StringIO(csv_text)))
            csv_header = csv_rows_parsed[0]
            md_text = summary_md.read_text(encoding="utf-8")

        self.assertTrue(summary_json_exists)
        self.assertTrue(summary_csv_exists)
        self.assertTrue(summary_md_exists)
        self.assertEqual(summary["schema_version"], "iter9_image_sweep.v1")
        self.assertEqual(summary["images_discovered"], 3)
        self.assertEqual(summary["runs_attempted"], 2)
        self.assertEqual(summary["runs_succeeded"], 1)
        self.assertEqual(summary["runs_failed"], 1)
        self.assertEqual(summary["runs_skipped"], 1)
        self.assertEqual(csv_header, run_iter9.IMAGE_SWEEP_SUMMARY_FIELDS)
        self.assertIn("\\|", md_text)

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_batch_context_passed_to_single_run_is_complete(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            image_paths = [write_fake_png(image_dir / "one.png")]
            configure_successful_batch_mocks(
                resolve_mock=resolve_mock,
                verify_mock=verify_mock,
                sizing_mock=sizing_mock,
                compile_mock=compile_mock,
                warm_mock=warm_mock,
                single_mock=single_mock,
                image_paths=image_paths,
            )

            args = make_sweep_args(image_dir, out_root)
            raw_argv = make_sweep_raw_argv(image_dir, out_root)
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)
            batch_context = single_mock.call_args.kwargs["batch_context"]

        self.assertEqual(rc, 0)
        self.assertEqual(single_mock.call_args.kwargs["warmup_s"], 0.0)
        self.assertEqual(
            set(batch_context),
            {
                "schema_version",
                "batch_mode",
                "batch_id",
                "batch_index",
                "batch_total",
                "images_discovered",
                "image_dir",
                "image_glob",
                "recursive",
                "batch_out_root",
                "child_run_dir",
                "continue_on_error",
                "skip_existing",
                "max_images",
                "batch_warmup_s",
                "child_warmup_s",
            },
        )
        self.assertEqual(batch_context["schema_version"], "iter9_image_sweep_context.v1")
        self.assertEqual(batch_context["batch_mode"], "iter9_image_sweep")
        self.assertEqual(batch_context["child_warmup_s"], 0.0)

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_single_run_receives_exact_raw_argv(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            image_paths = [write_fake_png(image_dir / "one.png")]
            configure_successful_batch_mocks(
                resolve_mock=resolve_mock,
                verify_mock=verify_mock,
                sizing_mock=sizing_mock,
                compile_mock=compile_mock,
                warm_mock=warm_mock,
                single_mock=single_mock,
                image_paths=image_paths,
            )

            raw_argv = make_sweep_raw_argv(image_dir, out_root, "--continue-on-error")
            args = run_iter9.parse_args(raw_argv)
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)

        self.assertEqual(rc, 0)
        self.assertEqual(single_mock.call_args.kwargs["raw_argv"], raw_argv)

    def test_command_invocation_uses_raw_argv(self):
        raw_argv = ["--image", "assets/input_source_image.png", "--seed", "11", "--allow-noncanonical"]
        kwargs = make_minimal_metrics_doc_kwargs()
        kwargs["command_invocation"] = {"argv": ["run_iter9.py", *[str(arg) for arg in raw_argv]]}
        doc = run_iter9.build_metrics_document({}, **kwargs)
        self.assertEqual(doc["command_invocation"]["argv"][0], "run_iter9.py", msg="argv must start with 'run_iter9.py'")
        self.assertEqual(doc["command_invocation"]["argv"][1:], [str(a) for a in raw_argv], msg="argv[1:] must match the raw_argv values")

    def test_summary_markdown_escapes_table_cells(self):
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td) / "out"
            run_iter9.write_iter9_image_sweep_summaries(
                out_root=out_root,
                batch_id="batch123",
                image_dir="assets",
                image_glob="*.png",
                recursive=False,
                board_w=300,
                seed=11,
                started_at_utc="2026-01-01T00:00:00.000Z",
                finished_at_utc="2026-01-01T00:01:00.000Z",
                duration_wall_s=60.0,
                batch_warmup_s=1.0,
                rows=[
                    {
                        "batch_index": 1,
                        "status": "failed",
                        "image_path": "a|b\nc",
                        "board": "300x370",
                        "seed": 11,
                        "n_unknown": None,
                        "coverage": None,
                        "solvable": None,
                        "repair_route_selected": None,
                        "best_artifact_to_open_first": "x|y",
                        "error_message": "bad\nline|pipe",
                    }
                ],
                images_discovered=1,
            )
            md_text = (out_root / "iter9_image_sweep_summary.md").read_text(encoding="utf-8")

        self.assertIn("a\\|b c", md_text)
        self.assertIn("x\\|y", md_text)
        self.assertIn("bad line\\|pipe", md_text)

    def test_image_sweep_summary_fields_exact_order(self):
        expected_fields = [
            "batch_index",
            "image_path",
            "image_name",
            "image_stem",
            "source_image_sha256",
            "status",
            "child_run_dir",
            "metrics_path",
            "best_artifact_to_open_first",
            "board",
            "seed",
            "n_unknown",
            "coverage",
            "solvable",
            "mean_abs_error",
            "repair_route_selected",
            "selected_route",
            "route_result",
            "route_outcome_detail",
            "next_recommended_route",
            "error_type",
            "error_message",
        ]
        self.assertEqual(run_iter9.IMAGE_SWEEP_SUMMARY_FIELDS, expected_fields, msg="IMAGE_SWEEP_SUMMARY_FIELDS must match the exact expected field order")

    def test_sweep_success_row_contains_four_route_state_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_path = write_fake_png(root / "images" / "sample.png")
            source_cfg = make_source_cfg(image_path, sha="9" * 64)
            child_dir = root / "out" / "child"
            child_dir.mkdir(parents=True, exist_ok=True)
            metrics_doc = make_success_metrics_doc("sample")
            row = run_iter9._image_sweep_success_row(
                batch_index=1,
                source_cfg=source_cfg,
                child_run_dir=child_dir,
                metrics_doc=metrics_doc,
                project_root=root,
            )
        for field in ("selected_route", "route_result", "route_outcome_detail", "next_recommended_route"):
            self.assertIn(field, row, msg=f"success row missing field: {field}")
        self.assertEqual(row["selected_route"], "already_solved")
        self.assertEqual(row["route_result"], "solved")

    def test_sweep_failure_row_four_route_fields_are_none(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_path = write_fake_png(root / "images" / "bad.png")
            source_cfg = make_source_cfg(image_path)
            row = run_iter9._image_sweep_failure_row(
                batch_index=1,
                image_path=image_path,
                source_cfg=source_cfg,
                child_run_dir=None,
                board_label="300x370",
                seed=11,
                error=RuntimeError("boom"),
                project_root=root,
            )
        for field in ("selected_route", "route_result", "route_outcome_detail", "next_recommended_route"):
            self.assertIn(field, row, msg=f"failure row missing field: {field}")
            self.assertIsNone(row[field], msg=f"failure row {field} must be None")

    def test_skipped_existing_row_uses_selected_route_not_synthesized(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_path = write_fake_png(root / "images" / "sample.png")
            source_cfg = make_source_cfg(image_path, sha="9" * 64)
            child_dir = root / "out" / "child"
            child_dir.mkdir(parents=True, exist_ok=True)
            metrics_path = child_dir / "metrics_iter9_300x370.json"
            metrics_path.write_text(
                json.dumps({
                    "n_unknown": 0,
                    "coverage": 1.0,
                    "solvable": True,
                    "mean_abs_error": 0.1,
                    "repair_route_selected": "phase2_full_repair",
                    "selected_route": "phase2_full_repair",
                    "route_result": "solved",
                    "route_outcome_detail": "phase2_full_repair_solved",
                    "next_recommended_route": None,
                    "llm_review_summary": {"best_artifact_to_open_first": "artifact.png"},
                }),
                encoding="utf-8",
            )
            row = run_iter9._image_sweep_skipped_existing_row(
                batch_index=1,
                source_cfg=source_cfg,
                child_run_dir=child_dir,
                metrics_path=metrics_path,
                board_label="300x370",
                seed=11,
                project_root=root,
            )
        # Must read selected_route directly, not synthesize from repair_route_selected
        self.assertEqual(row["selected_route"], "phase2_full_repair")
        self.assertEqual(row["route_result"], "solved")
        self.assertEqual(row["route_outcome_detail"], "phase2_full_repair_solved")

    def test_summary_writer_accepts_image_dir_string_and_stores_images_discovered(self):
        with tempfile.TemporaryDirectory() as td:
            out_root = Path(td) / "out"
            out_root.mkdir(parents=True, exist_ok=True)
            run_iter9.write_iter9_image_sweep_summaries(
                out_root=out_root,
                batch_id="batch123",
                image_dir="assets",
                image_glob="*.png",
                recursive=False,
                board_w=300,
                seed=11,
                started_at_utc="2026-01-01T00:00:00.000Z",
                finished_at_utc="2026-01-01T00:00:01.000Z",
                duration_wall_s=1.0,
                batch_warmup_s=0.5,
                rows=[],
                images_discovered=5,
            )
            summary_path = out_root / "iter9_image_sweep_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(summary["images_discovered"], 5)
        self.assertEqual(summary["batch_identity"]["image_dir"], "assets")
        self.assertIsInstance(summary["batch_identity"]["image_dir"], str)

    def test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            project_root = root
            image_path = write_fake_png(root / "images" / "sample.png")
            source_cfg = make_source_cfg(image_path, sha="9" * 64)
            child_dir = root / "out" / "child"
            child_dir.mkdir(parents=True, exist_ok=True)
            metrics_path = child_dir / "metrics_iter9_300x370.json"
            metrics_path.write_text(
                json.dumps(
                    {
                        "n_unknown": 2,
                        "coverage": 0.9,
                        "solvable": False,
                        "mean_abs_error": 0.3,
                        "repair_route_selected": "phase2_full_repair",
                        "llm_review_summary": {"best_artifact_to_open_first": "first.png"},
                    }
                ),
                encoding="utf-8",
            )

            success_row = run_iter9._image_sweep_success_row(
                batch_index=1,
                source_cfg=source_cfg,
                child_run_dir=child_dir,
                metrics_doc=make_success_metrics_doc("sample", board="300x370", seed=11),
                project_root=project_root,
            )
            failure_row = run_iter9._image_sweep_failure_row(
                batch_index=2,
                image_path=image_path,
                source_cfg=source_cfg,
                child_run_dir=None,
                board_label="300x370",
                seed=11,
                error=RuntimeError("boom"),
                project_root=project_root,
            )
            skipped_row = run_iter9._image_sweep_skipped_existing_row(
                batch_index=3,
                source_cfg=source_cfg,
                child_run_dir=child_dir,
                metrics_path=metrics_path,
                board_label="300x370",
                seed=11,
                project_root=project_root,
            )

        expected_keys = set(run_iter9.IMAGE_SWEEP_SUMMARY_FIELDS)
        self.assertEqual(set(success_row), expected_keys)
        self.assertEqual(set(failure_row), expected_keys)
        self.assertEqual(set(skipped_row), expected_keys)

        self.assertEqual(success_row["status"], "succeeded")
        self.assertIsNone(success_row["error_type"])
        self.assertIsNone(success_row["error_message"])
        self.assertEqual(success_row["n_unknown"], 0)

        self.assertEqual(failure_row["status"], "failed")
        self.assertEqual(failure_row["error_type"], "RuntimeError")
        self.assertEqual(failure_row["error_message"], "boom")

        self.assertEqual(skipped_row["status"], "skipped_existing")
        self.assertIsNone(skipped_row["error_type"])
        self.assertIsNone(skipped_row["error_message"])
        self.assertIn("metrics_iter9_300x370.json", skipped_row["metrics_path"])

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_skip_existing_metrics_path_uses_derived_full_board_label(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            image_path = write_fake_png(image_dir / "sample.png")
            source_cfg = make_source_cfg(image_path)

            resolve_mock.return_value = source_cfg
            verify_mock.return_value = {
                "ok": True,
                "canonical_match": False,
                "noncanonical_allowed": True,
                "warnings": [],
            }
            sizing_mock.return_value = {
                "board_width": 420,
                "board_height": 510,
                "gate_aspect_ratio_within_tolerance": True,
            }
            compile_mock.return_value = object()
            warm_mock.return_value = None

            collisions = run_iter9._colliding_sanitized_stem_tokens([image_path])
            child_dir = run_iter9.build_image_sweep_child_out_dir(
                out_root,
                source_cfg=source_cfg,
                board_label="420x510",
                seed=11,
                colliding_stem_tokens=collisions,
            )
            child_dir.mkdir(parents=True, exist_ok=True)
            expected_metrics = child_dir / "metrics_iter9_420x510.json"
            expected_metrics.write_text("{}", encoding="utf-8")

            args = make_sweep_args(image_dir, out_root, "--skip-existing")
            raw_argv = make_sweep_raw_argv(image_dir, out_root, "--skip-existing")
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)
            summary = json.loads((out_root / "iter9_image_sweep_summary.json").read_text(encoding="utf-8"))

        self.assertEqual(rc, 0)
        single_mock.assert_not_called()
        self.assertIn("420x510", summary["rows"][0]["metrics_path"])

    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    def test_discovery_failure_writes_failure_summary_and_returns_1(
        self,
        compile_mock,
        warm_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            missing_image_dir = root / "missing_images"
            out_root = root / "out"
            out_root.mkdir(parents=True, exist_ok=True)

            compile_mock.return_value = object()
            warm_mock.return_value = None

            raw_argv = [
                "--image-dir",
                missing_image_dir.as_posix(),
                "--seed",
                "11",
                "--allow-noncanonical",
                "--out-root",
                out_root.as_posix(),
            ]
            args = run_iter9.parse_args(raw_argv)
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)
            summary_path = out_root / "iter9_image_sweep_summary.json"
            summary_exists = summary_path.exists()
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        expected_null_fields = [
            "image_name",
            "image_stem",
            "source_image_sha256",
            "child_run_dir",
            "metrics_path",
            "best_artifact_to_open_first",
            "board",
            "n_unknown",
            "coverage",
            "solvable",
            "mean_abs_error",
            "repair_route_selected",
        ]

        row = summary["rows"][0]

        self.assertEqual(rc, 1)
        self.assertTrue(summary_exists)
        self.assertEqual(summary["images_discovered"], 0)
        self.assertEqual(summary["runs_attempted"], 0)
        self.assertEqual(summary["runs_failed"], 1)
        self.assertEqual(summary["runs_succeeded"], 0)
        self.assertEqual(summary["runs_skipped"], 0)
        self.assertEqual(row["batch_index"], 0)
        self.assertEqual(row["image_path"], str(Path(missing_image_dir).expanduser()))
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["seed"], 11)
        self.assertEqual(row["error_type"], "FileNotFoundError")

        for field in expected_null_fields:
            self.assertIsNone(row[field], msg=field)

    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    def test_warmup_failure_writes_failure_summary_and_returns_1(
        self,
        compile_mock,
        warm_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            write_fake_png(image_dir / "a.png")

            compile_mock.side_effect = RuntimeError("warmup-boom")
            warm_mock.return_value = None

            raw_argv = make_sweep_raw_argv(image_dir, out_root)
            args = run_iter9.parse_args(raw_argv)
            rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)
            summary_path = out_root / "iter9_image_sweep_summary.json"
            summary_exists = summary_path.exists()
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        expected_null_fields = [
            "image_name",
            "image_stem",
            "source_image_sha256",
            "child_run_dir",
            "metrics_path",
            "best_artifact_to_open_first",
            "board",
            "n_unknown",
            "coverage",
            "solvable",
            "mean_abs_error",
            "repair_route_selected",
        ]

        row = summary["rows"][0]

        self.assertEqual(rc, 1)
        self.assertTrue(summary_exists)
        self.assertEqual(summary["runs_attempted"], 0)
        self.assertEqual(summary["runs_failed"], 1)
        self.assertEqual(summary["runs_succeeded"], 0)
        self.assertEqual(row["batch_index"], 0)
        self.assertIn("images", row["image_path"])
        self.assertEqual(row["status"], "failed")
        self.assertEqual(row["seed"], 11)
        self.assertEqual(row["error_type"], "RuntimeError")
        self.assertEqual(row["error_message"], "warmup-boom")

        for field in expected_null_fields:
            self.assertIsNone(row[field], msg=field)

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_source_config_resolution_failure_writes_failed_row(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"
            write_fake_png(image_dir / "bad.png")

            resolve_mock.side_effect = RuntimeError("resolve-boom")
            compile_mock.return_value = object()
            warm_mock.return_value = None

            args = make_sweep_args(image_dir, out_root)
            rc = run_iter9.run_iter9_image_sweep(
                args,
                raw_argv=["--image-dir", image_dir.as_posix(), "--out-root", out_root.as_posix()],
                project_root=PROJECT_ROOT,
            )

            summary_path = out_root / "iter9_image_sweep_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 1)
        single_mock.assert_not_called()
        verify_mock.assert_not_called()
        sizing_mock.assert_not_called()
        self.assertEqual(summary["rows"][0]["status"], "failed")
        self.assertEqual(summary["rows"][0]["error_type"], "RuntimeError")
        self.assertEqual(summary["rows"][0]["error_message"], "resolve-boom")

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_source_config_resolution_failure_continue_on_error_attempts_remaining_images(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            out_root = root / "out"

            write_fake_png(image_dir / "bad.png")
            good_path = write_fake_png(image_dir / "good.png")
            good_cfg = make_source_cfg(good_path, sha="2" * 64)

            resolve_mock.side_effect = [
                RuntimeError("resolve-boom"),
                good_cfg,
            ]
            verify_mock.return_value = {
                "ok": True,
                "canonical_match": False,
                "noncanonical_allowed": True,
                "warnings": [],
            }
            sizing_mock.return_value = {
                "board_width": 300,
                "board_height": 370,
                "gate_aspect_ratio_within_tolerance": True,
            }
            compile_mock.return_value = object()
            warm_mock.return_value = None
            single_mock.return_value = make_success_metrics_doc(
                "good",
                board="300x370",
                seed=11,
            )

            args = make_sweep_args(image_dir, out_root, "--continue-on-error")
            rc = run_iter9.run_iter9_image_sweep(
                args,
                raw_argv=["--image-dir", image_dir.as_posix(), "--continue-on-error", "--out-root", out_root.as_posix()],
                project_root=PROJECT_ROOT,
            )

            summary_path = out_root / "iter9_image_sweep_summary.json"
            summary = json.loads(summary_path.read_text(encoding="utf-8"))

        self.assertEqual(rc, 1)
        self.assertEqual(resolve_mock.call_count, 2)
        self.assertEqual(single_mock.call_count, 1)
        self.assertEqual(
            [row["status"] for row in summary["rows"]],
            ["failed", "succeeded"],
        )

    @mock.patch("run_iter9.run_iter9_single")
    @mock.patch("run_iter9.ensure_solver_warmed")
    @mock.patch("run_iter9.compile_sa_kernel")
    @mock.patch("run_iter9.derive_board_from_width")
    @mock.patch("run_iter9.verify_source_image")
    @mock.patch("run_iter9.resolve_source_image_config")
    def test_default_out_root_uses_results_iter9_batch_id(
        self,
        resolve_mock,
        verify_mock,
        sizing_mock,
        compile_mock,
        warm_mock,
        single_mock,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            image_dir = root / "images"
            image_path = write_fake_png(image_dir / "sample.png")
            source_cfg = make_source_cfg(image_path)

            resolve_mock.return_value = source_cfg
            verify_mock.return_value = {
                "ok": True,
                "canonical_match": False,
                "noncanonical_allowed": True,
                "warnings": [],
            }
            sizing_mock.return_value = {
                "board_width": 300,
                "board_height": 370,
                "gate_aspect_ratio_within_tolerance": True,
            }
            compile_mock.return_value = object()
            warm_mock.return_value = None
            single_mock.return_value = make_success_metrics_doc(
                "sample",
                board="300x370",
                seed=11,
            )

            raw_argv = [
                "--image-dir",
                image_dir.as_posix(),
                "--image-glob",
                "*.png",
                "--seed",
                "11",
                "--allow-noncanonical",
            ]
            args = run_iter9.parse_args(raw_argv)

            rc = run_iter9.run_iter9_image_sweep(
                args,
                raw_argv=raw_argv,
                project_root=root,
            )

            batch_context = single_mock.call_args.kwargs["batch_context"]

        self.assertEqual(rc, 0)
        self.assertIn(
            "results/iter9/",
            batch_context["batch_out_root"].replace("\\", "/"),
        )
        self.assertIn("_300w_seed11", batch_context["batch_id"])

    def test_command_invocation_uses_exact_raw_argv_prefix(self):
        raw_argv = ["--image", "assets/input_source_image.png", "--out-dir", "results/x"]
        kwargs = make_minimal_metrics_doc_kwargs()
        kwargs["command_invocation"] = {"argv": ["run_iter9.py", *[str(arg) for arg in raw_argv]]}
        doc = run_iter9.build_metrics_document({}, **kwargs)
        self.assertEqual(doc["command_invocation"]["argv"][:1], ["run_iter9.py"], msg="argv prefix must be 'run_iter9.py'")
        self.assertEqual(doc["command_invocation"]["argv"][1:], list(raw_argv), msg="argv tail must match raw_argv exactly")


if __name__ == "__main__":
    unittest.main()
