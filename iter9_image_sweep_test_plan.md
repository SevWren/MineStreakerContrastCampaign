# Iter9 Image Sweep Test Plan

## 1. Test Plan Purpose

This document defines the complete test plan for native Iter9 image-sweep mode in `run_iter9.py`.

All tests in this document belong in:

```text
tests/test_iter9_image_sweep_contract.py
```

The test file must use `unittest`.

No test in `tests/test_iter9_image_sweep_contract.py` may run real simulated annealing.

## 2. Test File Required Imports

`tests/test_iter9_image_sweep_contract.py` must start with exactly these imports:

```python
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import run_iter9
from source_config import SourceImageConfig
```

## 3. Test File Required Constants

Add this constant below the imports:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[1]
```

## 4. Test File Required Helper Functions

### 4.1 Source Config Helper

Add this helper below `PROJECT_ROOT`:

```python
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
```

### 4.2 Temporary PNG Helper

Add this helper:

```python
def write_fake_png(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"not-a-real-png-but-valid-for-discovery-tests")
    return path
```

Discovery tests use fake PNG filenames and do not decode image contents.

### 4.3 Minimal Metrics Keyword Helper

Add this helper:

```python
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
```

### 4.4 Successful Metrics Document Helper

Add this helper:

```python
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
        "run_identity": {"output_dir": child_dir},
        "artifact_inventory": {"metrics_json": f"{child_dir}/metrics_iter9_{board}.json"},
        "llm_review_summary": {
            "best_artifact_to_open_first": f"{child_dir}/iter9_{board}_FINAL_explained.png"
        },
    }
```

### 4.5 Sweep Args Helper

Add this helper:

```python
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
```

### 4.6 Common Batch Mock Setup Helper

Add this helper:

```python
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
```

## 5. Test Class

Add this class:

```python
class Iter9ImageSweepContractTests(unittest.TestCase):
    ...
```

All tests below must be methods on `Iter9ImageSweepContractTests`.

## 6. Required Tests

### Test 1: Help Exposes All Batch Flags

Name:

```python
test_help_exposes_all_image_sweep_flags
```

Implementation:

```python
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
        self.assertIn(flag, completed.stdout)
```

Expected result:

```text
return code is 0
stdout contains every sweep flag
```

Forbidden behavior:

```text
test must not import image files
test must not run SA
```

### Test 2: Parser Rejects Abbreviated Long Flags

Name:

```python
test_argparse_rejects_abbreviated_long_flags
```

Implementation:

```python
def test_argparse_rejects_abbreviated_long_flags(self):
    for raw in [
        ["--image-g", "*.jpg"],
        ["--rec"],
        ["--image-dir", "assets", "--image-man", "x.json"],
    ]:
        with self.subTest(raw=raw):
            with self.assertRaises(SystemExit):
                run_iter9.parse_args(raw)
```

Expected result:

```text
every abbreviated command raises SystemExit
```

Forbidden behavior:

```text
argparse must not accept abbreviated long options
```

### Test 3: Discovery Direct Matches Are Sorted

Name:

```python
test_discovery_direct_matches_are_sorted
```

Implementation:

```python
def test_discovery_direct_matches_are_sorted(self):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_fake_png(root / "b.png")
        write_fake_png(root / "a.png")
        (root / "note.txt").write_text("ignore", encoding="utf-8")
        write_fake_png(root / "nested" / "c.png")

        result = run_iter9.discover_source_images(root, "*.png", recursive=False)

    self.assertEqual([path.name for path in result], ["a.png", "b.png"])
```

Expected result:

```text
only top-level .png files are returned
returned order is a.png then b.png
```

Forbidden behavior:

```text
nested/c.png must not be returned when recursive is False
note.txt must not be returned
```

### Test 4: Discovery Recursive Includes Nested Matches

Name:

```python
test_discovery_recursive_includes_nested_matches
```

Implementation:

```python
def test_discovery_recursive_includes_nested_matches(self):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_fake_png(root / "b.png")
        write_fake_png(root / "a.png")
        (root / "note.txt").write_text("ignore", encoding="utf-8")
        write_fake_png(root / "nested" / "c.png")

        result = run_iter9.discover_source_images(root, "*.png", recursive=True)

    self.assertEqual(sorted(path.name for path in result), ["a.png", "b.png", "c.png"])
```

Expected result:

```text
recursive discovery includes nested/c.png
note.txt is excluded
```

### Test 5: Discovery Applies Max Images After Sorting

Name:

```python
test_discovery_applies_max_images_after_sorting
```

Implementation:

```python
def test_discovery_applies_max_images_after_sorting(self):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        write_fake_png(root / "c.png")
        write_fake_png(root / "a.png")
        write_fake_png(root / "b.png")

        result = run_iter9.discover_source_images(root, "*.png", recursive=False, max_images=2)

    self.assertEqual([path.name for path in result], ["a.png", "b.png"])
```

Expected result:

```text
sorting happens before max_images truncation
```

### Test 6: Discovery Missing Directory Fails

Name:

```python
test_discovery_missing_directory_fails
```

Implementation:

```python
def test_discovery_missing_directory_fails(self):
    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "missing"
        with self.assertRaises(FileNotFoundError):
            run_iter9.discover_source_images(missing, "*.png")
```

Expected result:

```text
FileNotFoundError is raised
```

### Test 7: Discovery File Instead Of Directory Fails

Name:

```python
test_discovery_file_instead_of_directory_fails
```

Implementation:

```python
def test_discovery_file_instead_of_directory_fails(self):
    with tempfile.TemporaryDirectory() as td:
        file_path = Path(td) / "not_dir.png"
        write_fake_png(file_path)
        with self.assertRaises(NotADirectoryError):
            run_iter9.discover_source_images(file_path, "*.png")
```

Expected result:

```text
NotADirectoryError is raised
```

### Test 8: Discovery Empty Match Fails

Name:

```python
test_discovery_empty_match_fails
```

Implementation:

```python
def test_discovery_empty_match_fails(self):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "note.txt").write_text("ignore", encoding="utf-8")
        with self.assertRaises(ValueError):
            run_iter9.discover_source_images(root, "*.png")
```

Expected result:

```text
ValueError is raised
```

### Test 9: Image Dir Plus Explicit Image Fails

Name:

```python
test_image_dir_plus_explicit_image_fails
```

Implementation:

```python
def test_image_dir_plus_explicit_image_fails(self):
    for raw in [
        ["--image-dir", "assets", "--image", "assets/foo.png"],
        ["--image-dir", "assets", "--image=assets/foo.png"],
    ]:
        with self.subTest(raw=raw):
            with self.assertRaises(SystemExit):
                run_iter9.parse_args(raw)
```

Expected result:

```text
both explicit --image forms fail
```

### Test 10: Image Dir Plus Out Dir Fails

Name:

```python
test_image_dir_plus_out_dir_fails
```

Implementation:

```python
def test_image_dir_plus_out_dir_fails(self):
    with self.assertRaises(SystemExit):
        run_iter9.parse_args(["--image-dir", "assets", "--out-dir", "results/x"])
```

Expected result:

```text
SystemExit is raised
```

### Test 11: Sweep Only Flags Without Image Dir Fail

Name:

```python
test_sweep_only_flags_without_image_dir_fail
```

Implementation:

```python
def test_sweep_only_flags_without_image_dir_fail(self):
    invalid_commands = [
        ["--out-root", "results/x"],
        ["--image-glob", "*.jpg"],
        ["--recursive"],
        ["--continue-on-error"],
        ["--skip-existing"],
        ["--max-images", "2"],
    ]
    for raw in invalid_commands:
        with self.subTest(raw=raw):
            with self.assertRaises(SystemExit):
                run_iter9.parse_args(raw)
```

Expected result:

```text
every sweep-only flag fails when --image-dir is absent
```

### Test 12: Image Dir Plus Image Manifest Fails

Name:

```python
test_image_dir_plus_image_manifest_fails
```

Implementation:

```python
def test_image_dir_plus_image_manifest_fails(self):
    with self.assertRaises(SystemExit):
        run_iter9.parse_args(
            ["--image-dir", "assets", "--image-manifest", "assets/SOURCE_IMAGE_HASH.json"]
        )
```

Expected result:

```text
SystemExit is raised
```

### Test 13: Max Images Zero Fails

Name:

```python
test_max_images_zero_fails
```

Implementation:

```python
def test_max_images_zero_fails(self):
    with self.assertRaises(SystemExit):
        run_iter9.parse_args(["--image-dir", "assets", "--max-images", "0"])
```

Expected result:

```text
SystemExit is raised
```

### Test 14: Child Output Directory Includes Full Board Label

Name:

```python
test_child_output_directory_includes_full_board_label
```

Implementation:

```python
def test_child_output_directory_includes_full_board_label(self):
    with tempfile.TemporaryDirectory() as td:
        sample_path = write_fake_png(Path(td) / "sample.png")
        source_cfg = make_source_cfg(sample_path)
        child = run_iter9.build_image_sweep_child_out_dir(
            Path("results/root"),
            source_cfg=source_cfg,
            board_label="300x370",
            seed=11,
            colliding_stem_tokens=set(),
        )

    self.assertEqual(child.name, "sample_300x370_seed11")
```

Expected result:

```text
child directory name includes stem, full board label, and seed
```

### Test 15: Sanitized Stem Collisions Include SHA And Path Hash

Name:

```python
test_sanitized_stem_collisions_include_sha_and_path_hash
```

Implementation:

```python
def test_sanitized_stem_collisions_include_sha_and_path_hash(self):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path_a = write_fake_png(root / "a b.png")
        path_b = write_fake_png(root / "a_b.png")
        cfg_a = make_source_cfg(path_a, sha="a" * 64)
        cfg_b = make_source_cfg(path_b, sha="b" * 64)

        collisions = run_iter9._colliding_sanitized_stem_tokens([path_a, path_b])
        child_a = run_iter9.build_image_sweep_child_out_dir(
            Path("results/root"),
            source_cfg=cfg_a,
            board_label="300x370",
            seed=11,
            colliding_stem_tokens=collisions,
        )
        child_b = run_iter9.build_image_sweep_child_out_dir(
            Path("results/root"),
            source_cfg=cfg_b,
            board_label="300x370",
            seed=11,
            colliding_stem_tokens=collisions,
        )

    self.assertIn("a_b", collisions)
    self.assertNotEqual(child_a.name, child_b.name)
    self.assertIn(cfg_a.sha256[:12], child_a.name)
    self.assertIn(cfg_b.sha256[:12], child_b.name)
    self.assertIn("300x370_seed11", child_a.name)
    self.assertIn("300x370_seed11", child_b.name)
```

Expected result:

```text
a b.png and a_b.png are collision-protected after sanitization
```

### Test 16: Case Insensitive Stem Collisions Are Detected

Name:

```python
test_case_insensitive_stem_collisions_are_detected
```

Implementation:

```python
def test_case_insensitive_stem_collisions_are_detected(self):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path_a = write_fake_png(root / "Cat.png")
        path_b = write_fake_png(root / "cat.png")

        collisions = run_iter9._colliding_sanitized_stem_tokens([path_a, path_b])

    self.assertIn("cat", collisions)
```

Expected result:

```text
casefolded Cat/cat collision is detected
```

### Test 17: Same Stem Same SHA Duplicate Produces Distinct Child Directories

Name:

```python
test_same_stem_same_sha_duplicate_produces_distinct_child_directories
```

Implementation:

```python
def test_same_stem_same_sha_duplicate_produces_distinct_child_directories(self):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        path_a = write_fake_png(root / "one" / "sample.png")
        path_b = write_fake_png(root / "two" / "sample.png")
        same_sha = "c" * 64
        cfg_a = make_source_cfg(path_a, sha=same_sha)
        cfg_b = make_source_cfg(path_b, sha=same_sha)

        collisions = run_iter9._colliding_sanitized_stem_tokens([path_a, path_b])
        child_a = run_iter9.build_image_sweep_child_out_dir(
            Path("results/root"),
            source_cfg=cfg_a,
            board_label="300x370",
            seed=11,
            colliding_stem_tokens=collisions,
        )
        child_b = run_iter9.build_image_sweep_child_out_dir(
            Path("results/root"),
            source_cfg=cfg_b,
            board_label="300x370",
            seed=11,
            colliding_stem_tokens=collisions,
        )

    self.assertNotEqual(child_a.name, child_b.name)
    self.assertIn(same_sha[:12], child_a.name)
    self.assertIn(same_sha[:12], child_b.name)
```

Expected result:

```text
path hash separates same stem and same SHA files
```

### Test 18: Metrics Document Includes Optional Batch Context

Name:

```python
test_build_metrics_document_includes_optional_batch_context
```

Implementation:

```python
def test_build_metrics_document_includes_optional_batch_context(self):
    doc = run_iter9.build_metrics_document(
        {"board": "300x370", "seed": 11},
        **make_minimal_metrics_doc_kwargs(),
        batch_context={"batch_mode": "iter9_image_sweep", "batch_index": 1},
    )
    self.assertEqual(doc["batch_context"]["batch_mode"], "iter9_image_sweep")

    doc_without_batch = run_iter9.build_metrics_document(
        {"board": "300x370", "seed": 11},
        **make_minimal_metrics_doc_kwargs(),
    )
    self.assertNotIn("batch_context", doc_without_batch)
```

Expected result:

```text
batch_context appears only when supplied
```

### Test 19: Markdown Table Cell Escapes Pipes And Newlines

Name:

```python
test_md_table_cell_escapes_pipes_and_newlines
```

Implementation:

```python
def test_md_table_cell_escapes_pipes_and_newlines(self):
    value = "a|b\nc\rd"
    self.assertEqual(run_iter9._md_table_cell(value), "a\\|b c d")
    self.assertEqual(run_iter9._md_table_cell(None), "")
```

Expected result:

```text
pipe is escaped
newline is replaced by space
carriage return is replaced by space
None becomes empty string
```

### Test 20: Batch Runner Calls Single Run Once Per Image

Name:

```python
test_batch_runner_calls_single_run_once_per_image
```

Required decorators:

```python
@mock.patch("run_iter9.run_iter9_single")
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
@mock.patch("run_iter9.derive_board_from_width")
@mock.patch("run_iter9.verify_source_image")
@mock.patch("run_iter9.resolve_source_image_config")
```

Implementation body:

```python
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
            write_fake_png(image_dir / "c.png"),
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
        rc = run_iter9.run_iter9_image_sweep(args, raw_argv=["--image-dir", image_dir.as_posix()], project_root=PROJECT_ROOT)

    self.assertEqual(rc, 0)
    self.assertEqual(single_mock.call_count, 3)
```

Expected result:

```text
run_iter9_single is called exactly three times
return code is 0
```

### Test 21: Validation Failure Writes Failed Row And Summary

Name:

```python
test_validation_failure_writes_failed_row_and_summary
```

Required decorators:

```python
@mock.patch("run_iter9.run_iter9_single")
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
@mock.patch("run_iter9.derive_board_from_width")
@mock.patch("run_iter9.verify_source_image")
@mock.patch("run_iter9.resolve_source_image_config")
```

Implementation body:

```python
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
        resolve_mock.return_value = make_source_cfg(image_path)
        verify_mock.return_value = {
            "ok": False,
            "canonical_match": False,
            "noncanonical_allowed": True,
            "warnings": [{"message": "bad image"}],
        }
        sizing_mock.return_value = {"board_width": 300, "board_height": 370}
        compile_mock.return_value = object()
        warm_mock.return_value = None

        args = make_sweep_args(image_dir, out_root)
        rc = run_iter9.run_iter9_image_sweep(args, raw_argv=["--image-dir", image_dir.as_posix()], project_root=PROJECT_ROOT)
        summary_path = out_root / "iter9_image_sweep_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    self.assertEqual(rc, 1)
    single_mock.assert_not_called()
    self.assertTrue(summary_path.exists())
    self.assertEqual(summary["rows"][0]["status"], "failed")
    self.assertEqual(summary["rows"][0]["error_type"], "ValueError")
```

Expected result:

```text
validation failure is recorded as failed row
run_iter9_single is not called
summary JSON exists
return code is 1
```

### Test 22: Fail Fast Stops After First Runtime Failure And Writes Summaries

Name:

```python
test_fail_fast_stops_after_first_runtime_failure_and_writes_summaries
```

Required decorators:

```python
@mock.patch("run_iter9.run_iter9_single")
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
@mock.patch("run_iter9.derive_board_from_width")
@mock.patch("run_iter9.verify_source_image")
@mock.patch("run_iter9.resolve_source_image_config")
```

Implementation requirements:

```text
create a.png, b.png, c.png
configure successful mocks
set run_iter9_single.side_effect to [success_doc_for_a, RuntimeError("boom"), success_doc_for_c]
run without --continue-on-error
assert return code 1
assert run_iter9_single.call_count == 2
assert summary JSON exists
assert statuses are ["succeeded", "failed"]
```

Exact status assertion:

```python
self.assertEqual([row["status"] for row in summary["rows"]], ["succeeded", "failed"])
```

### Test 23: Continue On Error Attempts All Images

Name:

```python
test_continue_on_error_attempts_all_images
```

Required decorators:

```python
@mock.patch("run_iter9.run_iter9_single")
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
@mock.patch("run_iter9.derive_board_from_width")
@mock.patch("run_iter9.verify_source_image")
@mock.patch("run_iter9.resolve_source_image_config")
```

Implementation requirements:

```text
create a.png, b.png, c.png
configure successful mocks
set run_iter9_single.side_effect to [success_doc_for_a, RuntimeError("boom"), success_doc_for_c]
run with --continue-on-error
assert return code 1
assert run_iter9_single.call_count == 3
assert summary row statuses are ["succeeded", "failed", "succeeded"]
```

Exact status assertion:

```python
self.assertEqual([row["status"] for row in summary["rows"]], ["succeeded", "failed", "succeeded"])
```

### Test 24: Skip Existing Prevents Single Run Call

Name:

```python
test_skip_existing_prevents_single_run_call
```

Required decorators:

```python
@mock.patch("run_iter9.run_iter9_single")
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
@mock.patch("run_iter9.derive_board_from_width")
@mock.patch("run_iter9.verify_source_image")
@mock.patch("run_iter9.resolve_source_image_config")
```

Implementation requirements:

```text
create one image sample.png
resolve source config for sample.png
derive board as 300x370
compute child_out_dir using build_image_sweep_child_out_dir(...)
create expected_metrics parent directory with expected_metrics.parent.mkdir(parents=True, exist_ok=True)
write expected metrics file before calling run_iter9_image_sweep(...)
run with --skip-existing
assert return code 0
assert run_iter9_single is not called
assert summary row status is skipped_existing
```

Expected metrics path:

```python
expected_metrics = child_out_dir / "metrics_iter9_300x370.json"
```

### Test 25: Summaries Write JSON CSV And Markdown

Name:

```python
test_summaries_write_json_csv_and_markdown
```

Implementation requirements:

```text
run a mocked successful sweep with one image
assert these files exist:
out_root / "iter9_image_sweep_summary.json"
out_root / "iter9_image_sweep_summary.csv"
out_root / "iter9_image_sweep_summary.md"
assert JSON contains images_discovered
assert JSON contains rows_recorded
assert JSON contains runs_attempted
assert JSON contains runs_succeeded
assert JSON contains runs_failed
assert JSON contains runs_skipped
assert JSON contains batch_timing.batch_warmup_s
```

Exact JSON assertions:

```python
self.assertIn("images_discovered", summary)
self.assertIn("rows_recorded", summary)
self.assertIn("runs_attempted", summary)
self.assertIn("runs_succeeded", summary)
self.assertIn("runs_failed", summary)
self.assertIn("runs_skipped", summary)
self.assertIn("batch_warmup_s", summary["batch_timing"])
```

### Test 26: Batch Context Passed To Single Run Is Complete

Name:

```python
test_batch_context_passed_to_single_run_is_complete
```

Required decorators:

```python
@mock.patch("run_iter9.run_iter9_single")
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
@mock.patch("run_iter9.derive_board_from_width")
@mock.patch("run_iter9.verify_source_image")
@mock.patch("run_iter9.resolve_source_image_config")
```

Implementation requirements:

```text
run mocked sweep with one image
read single_mock.call_args.kwargs["batch_context"]
assert exact key set equals required batch_context key set
assert child_warmup_s == 0.0
assert batch_mode == "iter9_image_sweep"
assert schema_version == "iter9_image_sweep_context.v1"
```

Required key assertion:

```python
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
```

### Test 27: Single Run Receives Exact Raw Argv

Name:

```python
test_single_run_receives_exact_raw_argv
```

Required decorators:

```python
@mock.patch("run_iter9.run_iter9_single")
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
@mock.patch("run_iter9.derive_board_from_width")
@mock.patch("run_iter9.verify_source_image")
@mock.patch("run_iter9.resolve_source_image_config")
```

Implementation requirements:

```text
raw_argv = ["--image-dir", <image_dir>, "--seed", "11", "--allow-noncanonical"]
call run_iter9_image_sweep(..., raw_argv=raw_argv, ...)
assert single_mock.call_args.kwargs["raw_argv"] == raw_argv
```

Exact assertion:

```python
self.assertEqual(single_mock.call_args.kwargs["raw_argv"], raw_argv)
```

### Test 28: Command Invocation Builder Uses Raw Argv

Name:

```python
test_command_invocation_uses_raw_argv
```

Implementation method:

```text
This test must not run the full Iter9 pipeline.
Test the command invocation construction through a small helper if implemented, or through a mocked single-run extraction seam.
The asserted value must be exactly ["run_iter9.py", *raw_argv].
```

Required assertion:

```python
self.assertEqual(command_invocation["argv"], ["run_iter9.py", *raw_argv])
```

Forbidden behavior:

```text
The asserted value must not use sys.argv from the unittest runner.
```

### Test 29: Summary Markdown Escapes Table Cells

Name:

```python
test_summary_markdown_escapes_table_cells
```

Implementation requirements:

```text
call write_iter9_image_sweep_summaries(...) with one failed row where:
image_path contains |
error_message contains | and newline
read iter9_image_sweep_summary.md
assert unescaped raw pipe/newline content is absent from the row
assert escaped pipe sequence \| is present
```

Exact row input fragment:

```python
rows = [
    {
        "batch_index": 1,
        "image_path": "bad|image.png",
        "image_name": "bad|image.png",
        "image_stem": "bad|image",
        "source_image_sha256": None,
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
        "error_message": "bad|error\nnext",
    }
]
```

Required assertions:

```python
self.assertIn("bad\\|image.png", markdown)
self.assertIn("bad\\|error next", markdown)
```

### Test 30: IMAGE_SWEEP_SUMMARY_FIELDS Exact Order

Name:

```python
test_image_sweep_summary_fields_exact_order
```

Implementation:

```python
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
        "error_type",
        "error_message",
    ]
    self.assertEqual(run_iter9.IMAGE_SWEEP_SUMMARY_FIELDS, expected_fields)
```

Expected result:

```text
IMAGE_SWEEP_SUMMARY_FIELDS matches the exact locked field order
```

### Test 31: Summary Writer Accepts image_dir String And Stores images_discovered

Name:

```python
test_summary_writer_accepts_image_dir_string_and_stores_images_discovered
```

Implementation:

```python
def test_summary_writer_accepts_image_dir_string_and_stores_images_discovered(self):
    with tempfile.TemporaryDirectory() as td:
        out_root = Path(td) / "out"
        out_root.mkdir(parents=True, exist_ok=True)

        result = run_iter9.write_iter9_image_sweep_summaries(
            out_root=out_root,
            batch_id="20260428T000000Z_assets_png_300w_seed11",
            image_dir="assets",
            image_glob="*.png",
            recursive=False,
            board_w=300,
            seed=11,
            started_at_utc="2026-04-28T00:00:00.000Z",
            finished_at_utc="2026-04-28T00:01:00.000Z",
            duration_wall_s=60.0,
            batch_warmup_s=3.5,
            rows=[],
            images_discovered=5,
        )

        summary_path = out_root / "iter9_image_sweep_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    self.assertEqual(summary["images_discovered"], 5)
    self.assertEqual(summary["batch_identity"]["image_dir"], "assets")
    self.assertIsInstance(summary["batch_identity"]["image_dir"], str)
```

Expected result:

```text
image_dir is stored as a plain string, not a Path
images_discovered reflects the argument value, not row count
```

### Test 32: Success Failure Skipped Row Helpers Return Exact Field Set And Mapping

Name:

```python
test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping
```

Implementation:

```python
def test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping(self):
    expected_keys = set(run_iter9.IMAGE_SWEEP_SUMMARY_FIELDS)

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        img_path = write_fake_png(root / "sample.png")
        source_cfg = make_source_cfg(img_path)
        child_dir = root / "child"
        metrics_path = child_dir / "metrics_iter9_300x370.json"

        metrics_doc = make_success_metrics_doc("sample", board="300x370", seed=11)

        success_row = run_iter9._image_sweep_success_row(
            batch_index=1,
            source_cfg=source_cfg,
            child_run_dir=child_dir,
            metrics_doc=metrics_doc,
            project_root=root,
        )
        self.assertEqual(set(success_row.keys()), expected_keys)
        self.assertEqual(success_row["status"], "succeeded")
        self.assertIsNone(success_row["error_type"])
        self.assertIsNone(success_row["error_message"])

        failure_row = run_iter9._image_sweep_failure_row(
            batch_index=2,
            image_path=img_path,
            source_cfg=source_cfg,
            child_run_dir=None,
            board_label=None,
            seed=11,
            error=RuntimeError("test-error"),
            project_root=root,
        )
        self.assertEqual(set(failure_row.keys()), expected_keys)
        self.assertEqual(failure_row["status"], "failed")
        self.assertEqual(failure_row["error_type"], "RuntimeError")
        self.assertEqual(failure_row["error_message"], "test-error")

        skipped_row = run_iter9._image_sweep_skipped_existing_row(
            batch_index=3,
            source_cfg=source_cfg,
            child_run_dir=child_dir,
            metrics_path=metrics_path,
            board_label="300x370",
            seed=11,
            project_root=root,
        )
        self.assertEqual(set(skipped_row.keys()), expected_keys)
        self.assertEqual(skipped_row["status"], "skipped_existing")
        self.assertIsNone(skipped_row["error_type"])
        self.assertIsNone(skipped_row["error_message"])
```

Expected result:

```text
all three row helpers return exactly IMAGE_SWEEP_SUMMARY_FIELDS keys
success row sets error_type and error_message to None
failure row sets error_type to exception class name and error_message to str(error)
skipped row sets error_type and error_message to None
```

### Test 33: Skip Existing Metrics Path Uses Derived Full Board Label

Name:

```python
test_skip_existing_metrics_path_uses_derived_full_board_label
```

Required decorators:

```python
@mock.patch("run_iter9.run_iter9_single")
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
@mock.patch("run_iter9.derive_board_from_width")
@mock.patch("run_iter9.verify_source_image")
@mock.patch("run_iter9.resolve_source_image_config")
```

Implementation requirements:

```text
create one image sample.png
configure mocks with board_width=420, board_height=510
compute expected child_out_dir using build_image_sweep_child_out_dir(..., board_label="420x510", ...)
write expected metrics file at child_out_dir / "metrics_iter9_420x510.json" before the sweep
run with --skip-existing and --board-w 420
assert return code 0
assert run_iter9_single is not called
assert summary row status is skipped_existing
assert the metrics_path in the row matches the 420x510 label
```

Exact assertions:

```python
self.assertEqual(rc, 0)
single_mock.assert_not_called()
self.assertEqual(summary["rows"][0]["status"], "skipped_existing")
self.assertIn("420x510", summary["rows"][0].get("metrics_path", ""))
```

Expected result:

```text
skip-existing decision uses the derived board label, not a placeholder
420x510 board label appears in the skipped row metrics_path
```

### Test 34: Discovery Failure Writes Failure Summary And Returns 1

Name:

```python
test_discovery_failure_writes_failure_summary_and_returns_1
```

Required decorators:

```python
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
```

Implementation:

```python
def test_discovery_failure_writes_failure_summary_and_returns_1(
    self,
    compile_mock,
    warm_mock,
):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        missing_image_dir = root / "does_not_exist"
        out_root = root / "out"
        out_root.mkdir(parents=True, exist_ok=True)

        compile_mock.return_value = object()
        warm_mock.return_value = None

        raw_argv = ["--image-dir", missing_image_dir.as_posix(), "--allow-noncanonical", "--out-root", out_root.as_posix()]
        args = run_iter9.parse_args(raw_argv)
        rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)

        summary_path = out_root / "iter9_image_sweep_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    self.assertEqual(rc, 1)
    self.assertTrue(summary_path.exists())
    self.assertEqual(summary["images_discovered"], 0)
    self.assertEqual(summary["runs_failed"], 1)
    self.assertEqual(summary["runs_succeeded"], 0)
    self.assertEqual(summary["rows"][0]["status"], "failed")
```

Expected result:

```text
discovery failure writes summary JSON before returning 1
images_discovered is 0
runs_failed is 1
first row status is failed
```

Forbidden behavior:

```text
discovery failure must not silently exit without writing summary files
```

### Test 35: Warmup Failure Writes Failure Summary And Returns 1

Name:

```python
test_warmup_failure_writes_failure_summary_and_returns_1
```

Required decorators:

```python
@mock.patch("run_iter9.ensure_solver_warmed")
@mock.patch("run_iter9.compile_sa_kernel")
```

Implementation:

```python
def test_warmup_failure_writes_failure_summary_and_returns_1(
    self,
    compile_mock,
    warm_mock,
):
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        image_dir = root / "images"
        out_root = root / "out"
        write_fake_png(image_dir / "sample.png")

        compile_mock.side_effect = RuntimeError("warmup-boom")
        warm_mock.return_value = None

        raw_argv = ["--image-dir", image_dir.as_posix(), "--allow-noncanonical", "--out-root", out_root.as_posix()]
        args = run_iter9.parse_args(raw_argv)
        rc = run_iter9.run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=PROJECT_ROOT)

        summary_path = out_root / "iter9_image_sweep_summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

    self.assertEqual(rc, 1)
    self.assertTrue(summary_path.exists())
    self.assertEqual(summary["runs_failed"], 1)
    self.assertEqual(summary["runs_succeeded"], 0)
    self.assertEqual(summary["rows"][0]["status"], "failed")
```

Expected result:

```text
warmup failure writes summary JSON before returning 1
runs_failed is 1
first row status is failed
```

Forbidden behavior:

```text
warmup failure must not silently exit without writing summary files
```

### Test 36: Command Invocation Uses Exact Raw Argv Prefix

Name:

```python
test_command_invocation_uses_exact_raw_argv_prefix
```

Implementation method:

```text
This test locks the exact deterministic assertion target for command invocation provenance.
The asserted argv value must be exactly ["run_iter9.py", *raw_argv].
The test must not depend on sys.argv from the unittest runner.
The test must be verifiable without running the full Iter9 SA pipeline.
Use a mocked single-run seam to capture the command_invocation block written inside run_iter9_single(...).
```

Required assertion:

```python
self.assertEqual(command_invocation["argv"], ["run_iter9.py", *raw_argv])
self.assertEqual(command_invocation["entry_point"], "run_iter9.py")
```

Forbidden behavior:

```text
sys.argv from the test runner must not appear in the asserted value.
The argv list must not be hardcoded; it must be constructed from the raw_argv argument.
```

## 7. Required Test Command

After implementation, run:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

The command must exit with status `0`.

## 8. Global Forbidden Test Behaviors

The test file must not:

```text
run real simulated annealing
decode fake PNG files in discovery-only tests
modify files outside a TemporaryDirectory except through subprocess --help
depend on ambient sys.argv
use pytest fixtures
use tmp_path
use monkeypatch
require network access
require GPU access
write generated artifacts into repository root
```

## 9. Completion Gate For The Test Plan

The test plan is complete only when:

```text
all parser mode rules are tested
abbreviated argparse flags are tested
discovery success and failure paths are tested
child directory collision paths are tested
batch_context presence and exact keys are tested
summary JSON/CSV/Markdown creation is tested
Markdown table escaping is tested
validation failure summary behavior is tested
discovery failure summary behavior is tested (test 34)
warmup failure summary behavior is tested (test 35)
fail-fast behavior is tested
continue-on-error behavior is tested
skip-existing behavior is tested
skip-existing uses derived full board label before skip decision (test 33)
IMAGE_SWEEP_SUMMARY_FIELDS exact order is tested (test 30)
image_dir string persistence in summary writer is tested (test 31)
row helper exact field set and mapping is tested (test 32)
command_invocation exact raw_argv prefix is tested (test 36)
raw_argv propagation is tested
no test runs real SA
the full unittest discovery command passes
```
