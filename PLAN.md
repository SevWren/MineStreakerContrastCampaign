## Iter9 Image Sweep Implementation Plan (Contract-Locked)

### Summary
- Implement Iter9 image sweep in `run_iter9.py` with no algorithmic behavior drift.
- Modify only:
  - `run_iter9.py`
  - `README.md`
  - `AGENTS.md`
  - `tests/test_iter9_image_sweep_contract.py`
- Preserve artifact filename contract and all forbidden-file boundaries.

### Authoritative Sources
- Authoritative implementation sources, in precedence order:
  1. `iter9_image_sweep_traceability_matrix.md`
  2. `iter9_image_sweep_contract.md`
  3. `iter9_image_sweep_test_plan.md`
  4. `README.md` and `AGENTS.md` only for insertion locations and user-facing wording
- If any validation-command conflict exists, `iter9_image_sweep_traceability_matrix.md` wins.

### Phase 0: Scope Lock, Baseline Capture, And Guardrail Setup
Goal:
Prove the implementation starts from a known state and cannot drift outside the approved files.

Allowed files:
- run_iter9.py
- README.md
- AGENTS.md
- tests/test_iter9_image_sweep_contract.py

Forbidden files:
- run_benchmark.py
- source_config.py
- assets/image_guard.py
- board_sizing.py
- core.py
- corridors.py
- pipeline.py
- repair.py
- report.py
- sa.py
- solver.py
- list_unignored_files.py
- all existing tests except tests/test_iter9_image_sweep_contract.py

Required actions:
1. Run `git diff --name-only`.
2. Confirm the working tree starts clean or record existing unrelated diffs.
3. Run baseline single-image validation before implementation:
   `python run_iter9.py --image assets/line_art_irl_11_v2.png --seed 11 --allow-noncanonical --out-dir results/iter9_parity_before`
4. Save the baseline metrics path:
   `results/iter9_parity_before/metrics_iter9_<board>.json`
5. Record baseline values:
   - board
   - seed
   - source_image.sha256
   - n_unknown
   - coverage
   - solvable
   - mean_abs_error
   - artifact_inventory keys
6. Do not modify any forbidden file during this phase.

Phase 0 completion gate:
- Baseline metrics JSON exists.
- Baseline artifact filenames match the existing Iter9 filename contract.
- `git diff --name-only` contains no forbidden file.

### Phase 1: CLI Contract, Discovery Helpers, And Path Helpers
Goal:
Add only the non-runtime helper surface needed for image-sweep mode.

Required `run_iter9.py` changes:
1. Add standard-library imports:
   - `csv`
   - `hashlib`
2. Change ArgumentParser construction to:
   `argparse.ArgumentParser(description="Run Iter9 reconstruction pipeline.", allow_abbrev=False)`
3. Add CLI flags:
   - `--image-dir`
   - `--image-glob`
   - `--recursive`
   - `--out-root`
   - `--continue-on-error`
   - `--skip-existing`
   - `--max-images`
4. Add `_explicit_flag_present(raw_argv, flag)`.
5. Add `parse_args(raw_argv)` validation:
   - sweep-only flags require `--image-dir`
   - `--out-dir` cannot be used with `--image-dir`
   - explicit `--image` cannot be used with `--image-dir`
   - explicit `--image-manifest` cannot be used with `--image-dir`
   - `--max-images` must be `>= 1`
   - abbreviated long flags must be rejected
6. Add discovery/path helpers:
   - `discover_source_images(...)`
   - `_sanitize_path_token(...)`
   - `_path_hash_token(...)`
   - `_colliding_sanitized_stem_tokens(...)`
   - `build_image_sweep_child_out_dir(...)`
   - `_build_image_sweep_batch_id(...)`
   - `_md_table_cell(...)`
7. Add summary constants and atomic writers:
   - `IMAGE_SWEEP_SUMMARY_FIELDS`
   - `_atomic_save_text(...)`
   - `_atomic_save_csv(...)`

Phase 1 completion gate:
- `python run_iter9.py --help` shows every new sweep flag.
- Each invalid CLI command listed in the plan fails nonzero.
- Discovery helper tests pass with fake PNG files.
- Child directory collision tests pass.
- No real simulated annealing runs in Phase 1 tests.

### Phase 2: Single-Run Extraction And Main Control-Flow Split
Goal:
Extract one deterministic single-run execution unit and route both modes through contract-compliant entry flow.

Required `run_iter9.py` changes:
1. Introduce `run_iter9_single(...)` with required contract signature.
2. Move existing single-image runtime body into `run_iter9_single(...)` without changing algorithm order.
3. Enforce single-run boundary:
   - no `parse_args`
   - no `resolve_source_image_config`
   - no `verify_source_image`
   - no `compile_sa_kernel` / `ensure_solver_warmed`
   - no batch discovery/loop/summary writes
4. Ensure first filesystem action is `out_dir_path.mkdir(parents=True, exist_ok=True)`.
5. Use command provenance:
   - `{"entry_point":"run_iter9.py","argv":["run_iter9.py", *raw_argv]}`
6. Update `build_metrics_document(...)` to accept optional `batch_context` and include it only when non-None.
7. Change `main` to `main(argv: list[str] | None = None)` and split mode flow:
   - single-image mode resolves/validates image, warms once, calls `run_iter9_single(..., batch_context=None)`, returns `0`
   - image-sweep mode dispatches to `run_iter9_image_sweep(...)`

Metrics schema correction:
- Ensure `build_metrics_document(...)` includes top-level `source_image_validation`.
- Single-image metrics must include `source_image_validation`.
- Sweep child metrics must include `source_image_validation` and `batch_context`.
- This correction is allowed because it is confined to `run_iter9.py` and aligns README with metrics behavior.

Phase 2 completion gate:
- Existing single-image behavior remains functionally equivalent.
- Single-image metrics include `source_image_validation` and omit `batch_context`.
- Sweep child metrics include both `source_image_validation` and `batch_context`.
- Command invocation in single-run metrics uses raw argv prefix contract exactly.

### Phase 3: Batch Runner, Row Helpers, Summary Writer, And Sweep Execution
Goal:
Add full image-sweep orchestration with deterministic ordering, failure summaries, and schema-locked outputs.

Required batch preflight order:
1. Resolve `image_dir_path` before building `batch_id`:
   `image_dir_path = Path(args.image_dir).expanduser().resolve()`
2. Use `image_dir_path` for:
   - `_build_image_sweep_batch_id(image_dir=image_dir_path, ...)`
   - `discover_source_images(image_dir_path, ...)`
   - `batch_context["image_dir"]`
   - warmup failure row `image_path`
3. Build `batch_id` from `image_dir_path`, `args.image_glob`, `args.board_w`, `args.seed`, and `args.run_tag`.
4. Resolve `out_root` using this exact rule:
   - If `args.out_root` is supplied:
     `out_root = Path(args.out_root).expanduser().resolve()`
   - If `args.out_root` is not supplied:
     `out_root = (project_root / RESULTS_ROOT / batch_id).resolve()`
5. Create `out_root` before discovery:
   `out_root.mkdir(parents=True, exist_ok=True)`
6. Start discovery try/except.
7. Discover images.
8. Compute colliding stem tokens.
9. Batch warmup once.

Implementation note:
- Discovery-failure summaries must always be written under `out_root`. Therefore `out_root` must be resolved and created before calling `discover_source_images(...)`.

Required per-image execution order:
1. per-image resolve
2. per-image validate with `halt_on_failure=False`
3. derive board size
4. build full board label
5. build child directory
6. build expected metrics path
7. skip-existing decision
8. build `batch_context`
9. call `run_iter9_single`
10. append row

Required additions:
1. Implement `run_iter9_image_sweep(...)` with fail-fast/continue-on-error/skip-existing semantics.
2. Add row helpers:
   - `_image_sweep_success_row(...)`
   - `_image_sweep_failure_row(...)`
   - `_image_sweep_skipped_existing_row(...)`
3. Add `write_iter9_image_sweep_summaries(...)`:
   - JSON/CSV/Markdown outputs
   - atomic write helpers only
   - row normalization through exact `IMAGE_SWEEP_SUMMARY_FIELDS` projection
4. Ensure discovery failure and warmup failure both write summaries then return `1`.
5. Re-raise `KeyboardInterrupt`.
6. Preserve child artifact filenames exactly.

Batch-level failure row rules:

Discovery failure row must be built with these exact values:
- `batch_index = 0`
- `image_path = str(Path(args.image_dir).expanduser())`
- `image_name = None`
- `image_stem = None`
- `source_image_sha256 = None`
- `status = "failed"`
- `child_run_dir = None`
- `metrics_path = None`
- `best_artifact_to_open_first = None`
- `board = None`
- `seed = int(args.seed)`
- `n_unknown = None`
- `coverage = None`
- `solvable = None`
- `mean_abs_error = None`
- `repair_route_selected = None`
- `error_type = type(error).__name__`
- `error_message = str(error)`

Warmup failure row must be built with these exact values:
- `batch_index = 0`
- `image_path = _relative_or_absolute(image_dir_path, project_root)`
- `image_name = None`
- `image_stem = None`
- `source_image_sha256 = None`
- `status = "failed"`
- `child_run_dir = None`
- `metrics_path = None`
- `best_artifact_to_open_first = None`
- `board = None`
- `seed = int(args.seed)`
- `n_unknown = None`
- `coverage = None`
- `solvable = None`
- `mean_abs_error = None`
- `repair_route_selected = None`
- `error_type = type(error).__name__`
- `error_message = str(error)`

Both rows must be normalized through `IMAGE_SWEEP_SUMMARY_FIELDS` before JSON, CSV, or Markdown output.

Phase 3 completion gate:
- Sweep runner returns `0` only when no child failed.
- Discovery/warmup/validation/runtime failures produce summary rows and required counts.
- Summary JSON and CSV row schemas match exact locked field order.
- Sweep child metrics include full `batch_context` key set.

### Phase 4: Contract Tests And Documentation Updates
Goal:
Finish all automated contract coverage and add user-facing docs without changing runtime behavior.

Required test file:
- `tests/test_iter9_image_sweep_contract.py`

Required test coverage:
1. Help exposes all image-sweep flags.
2. Abbreviated long flags are rejected.
3. Sweep-only flags fail without `--image-dir`.
4. `--image-dir` rejects explicit `--image`.
5. `--image-dir` rejects `--image-manifest`.
6. `--image-dir` rejects `--out-dir`.
7. `--max-images 0` fails.
8. Discovery returns sorted top-level matches.
9. Recursive discovery includes nested matches.
10. `max_images` applies after sorting.
11. Missing image directory fails.
12. File instead of directory fails.
13. Empty match set fails.
14. Child output directory includes full board label.
15. Sanitized stem collisions include SHA and path hash.
16. Case-insensitive stem collisions are detected.
17. Same stem and same SHA still produce distinct child directories.
18. `build_metrics_document(...)` includes `batch_context` only when supplied.
18A. `build_metrics_document(...)` includes `source_image_validation` at top level.
19. Markdown table cells escape pipes and newlines.
20. Batch runner calls `run_iter9_single` once per attempted image.
21. Validation failure writes failed row and summary.
22. Fail-fast stops after first runtime failure and writes summaries.
23. Continue-on-error attempts all images.
24. Skip-existing prevents `run_iter9_single` call.
25. Summary writer emits JSON, CSV, and Markdown.
26. `batch_context` passed to `run_iter9_single` has the exact required key set.
27. `run_iter9_single` receives exact `raw_argv`.
28. `command_invocation` uses `["run_iter9.py", *raw_argv]`.
29. Summary Markdown escapes row cells.
30. `IMAGE_SWEEP_SUMMARY_FIELDS` exact order is locked.
31. Summary writer accepts `image_dir` as `str` and stores `images_discovered`.
32. Success, failure, and skipped row helpers return exact field set and mappings.
33. skip-existing metrics path uses derived full board label.
34. Discovery failure writes summary, returns `1`, and verifies exact batch-level failure row fields.
35. Warmup failure writes summary, returns `1`, and verifies exact batch-level failure row fields.
36. Command invocation uses exact raw argv prefix.
37. Source-config resolution failure writes failed row in fail-fast mode.
38. Source-config resolution failure with `--continue-on-error` attempts remaining images.
39. Default `out_root` uses `results/iter9/<batch_id>` when `--out-root` is omitted.

Required exact tests to add:

```python
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
```

```python
# Add to discovery-failure test assertions
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

self.assertEqual(row["batch_index"], 0)
self.assertEqual(row["image_path"], str(Path(missing_image_dir).expanduser()))
self.assertEqual(row["status"], "failed")
self.assertEqual(row["seed"], 11)
self.assertEqual(row["error_type"], "FileNotFoundError")

for field in expected_null_fields:
    self.assertIsNone(row[field], msg=field)
```

```python
# Add to warmup-failure test assertions
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

self.assertEqual(row["batch_index"], 0)
self.assertIn("images", row["image_path"])
self.assertEqual(row["status"], "failed")
self.assertEqual(row["seed"], 11)
self.assertEqual(row["error_type"], "RuntimeError")
self.assertEqual(row["error_message"], "warmup-boom")

for field in expected_null_fields:
    self.assertIsNone(row[field], msg=field)
```

```python
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
            raw_argv=["--image-dir", image_dir.as_posix()],
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
```

```python
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
            raw_argv=["--image-dir", image_dir.as_posix(), "--continue-on-error"],
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
```

```python
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
            project_root=PROJECT_ROOT,
        )

        batch_context = single_mock.call_args.kwargs["batch_context"]

    self.assertEqual(rc, 0)
    self.assertIn(
        "results/iter9/",
        batch_context["batch_out_root"].replace("\\", "/"),
    )
    self.assertIn("_300w_seed11", batch_context["batch_id"])
```

Required documentation updates:
1. `README.md`:
   - Insert image-sweep usage section immediately after the explained PNG paragraph.
   - Insert before `## Beginner Workflow`.
2. `AGENTS.md`:
   - Insert image-sweep contract section immediately after `## Source Image Runtime Contract`.
   - Do not remove or rewrite existing source-image runtime bullets.

Phase 4 completion gate:
- `tests/test_iter9_image_sweep_contract.py` exists.
- Full unittest discovery passes.
- README contains image-sweep section at required insertion point.
- AGENTS contains image-sweep contract section at required insertion point.
- No test runs real simulated annealing.
- Automated tests confirm `build_metrics_document(...)` emits top-level `source_image_validation`.
- Discovery failure test verifies exact batch-level failure row field values.
- Warmup failure test verifies exact batch-level failure row field values.
- Source-config resolution failure is tested in both fail-fast and `--continue-on-error` modes.
- Automated tests confirm default sweep output root is `results/iter9/<batch_id>` when `--out-root` is omitted.

### Phase 5: Verification, Traceability Inspection, And Completion Signoff
Goal:
Prove the implementation satisfies contract, test plan, traceability matrix, and manual validation gates.

Required commands:
1. Run all tests:  
   `python -m unittest discover -s tests -p "test_*.py"`
2. Confirm help output:  
   `python run_iter9.py --help`
3. Validate source image:  
   `python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical`
4. Run single-image smoke:  
   `python run_iter9.py --image assets/line_art_irl_11_v2.png --seed 11 --allow-noncanonical --out-dir results/iter9_manual_single_validation`
5. Run post-implementation parity validation:  
   `python run_iter9.py --image assets/line_art_irl_11_v2.png --seed 11 --allow-noncanonical --out-dir results/iter9_parity_after`
6. Compare baseline parity metrics against post-implementation parity metrics:  
   `python -c "import glob,json; before_paths=sorted(glob.glob('results/iter9_parity_before/metrics_iter9_*.json')); after_paths=sorted(glob.glob('results/iter9_parity_after/metrics_iter9_*.json')); assert before_paths, 'Missing baseline parity metrics in results/iter9_parity_before'; assert after_paths, 'Missing post-implementation parity metrics in results/iter9_parity_after'; before=json.load(open(before_paths[0],encoding='utf-8')); after=json.load(open(after_paths[0],encoding='utf-8')); keys=['board','seed','n_unknown','coverage','solvable','mean_abs_error']; [(_ for _ in ()).throw(AssertionError(f'Parity mismatch for {k}: before={before.get(k)!r}, after={after.get(k)!r}')) for k in keys if before.get(k)!=after.get(k)]; assert before.get('source_image',{}).get('sha256')==after.get('source_image',{}).get('sha256'), 'Parity mismatch for source_image.sha256'; assert set(before.get('artifact_inventory',{}).keys())==set(after.get('artifact_inventory',{}).keys()), 'Parity mismatch for artifact_inventory keys'; print('OK parity preserved:', before_paths[0], '->', after_paths[0])"`
7. Run sweep smoke:  
   `python run_iter9.py --image-dir assets --image-glob "*.png" --seed 11 --allow-noncanonical --out-root results/iter9_manual_explained_validation --max-images 2`
8. Run sweep smoke without `--out-root` to verify default batch output root:  
   `python run_iter9.py --image-dir assets --image-glob "*.png" --seed 11 --allow-noncanonical --max-images 1`  
   Expected behavior:
   - Command exits `0` when selected image succeeds.
   - Batch output is written under `results/iter9/<batch_id>/`.
   - `iter9_image_sweep_summary.json` exists under that batch root.
9. Run invalid CLI checks and confirm each exits nonzero:
   - `python run_iter9.py --out-root results/x`
   - `python run_iter9.py --image-glob "*.jpg"`
   - `python run_iter9.py --recursive`
   - `python run_iter9.py --continue-on-error`
   - `python run_iter9.py --skip-existing`
   - `python run_iter9.py --max-images 2`
   - `python run_iter9.py --image-dir assets --out-dir results/x`
   - `python run_iter9.py --image-dir assets --image assets/foo.png`
   - `python run_iter9.py --image-dir assets --image=assets/foo.png`
   - `python run_iter9.py --image-dir assets --image-manifest assets/SOURCE_IMAGE_HASH.json`
   - `python run_iter9.py --image-dir assets --max-images 0`
   - `python run_iter9.py --image-g "*.jpg"`
   - `python run_iter9.py --rec`
   - `python run_iter9.py --image-dir assets --image-man x.json`
10. Inspect single-image and sweep child metrics:
   - Confirm `source_image_validation` exists at top level.
   - Confirm `batch_context` is absent from single-image metrics.
   - Confirm `batch_context` exists only in sweep child metrics.
11. Inspect sweep summary JSON:
   - Confirm root keys: `schema_version`, `batch_identity`, `batch_timing`, `images_discovered`, `rows_recorded`, `runs_attempted`, `runs_succeeded`, `runs_failed`, `runs_skipped`, `rows`.
12. Inspect sweep summary CSV:
   - Confirm header equals `IMAGE_SWEEP_SUMMARY_FIELDS` exactly.
13. Inspect one sweep child metrics JSON:
   - Confirm `batch_context` key set equals required contract key set.
14. Inspect Markdown summary:
   - Confirm table is readable.
   - Confirm pipes/newlines in row values are escaped.
15. Inspect changed files:  
   `git diff --name-only`

Phase 5 completion gate:
- All automated tests pass.
- All invalid CLI commands fail nonzero.
- Single-image smoke succeeds.
- Sweep smoke succeeds.
- Summary JSON, CSV, and Markdown exist.
- CSV and JSON row schemas match `IMAGE_SWEEP_SUMMARY_FIELDS`.
- README and AGENTS contain required sections.
- `git diff --name-only` lists only:
  - `run_iter9.py`
  - `README.md`
  - `AGENTS.md`
  - `tests/test_iter9_image_sweep_contract.py`
- Baseline parity and post-implementation parity match for `board`, `seed`, `source_image.sha256`, `n_unknown`, `coverage`, `solvable`, `mean_abs_error`, and `artifact_inventory` keys.
- Post-implementation parity comparison passes against `results/iter9_parity_before`.
- `build_metrics_document(...)` has automated test coverage for top-level `source_image_validation`.
- Default image-sweep `out_root` behavior is specified and tested by running sweep mode without `--out-root`.
- Discovery failure rows and warmup failure rows use the exact batch-level failure field values.
- Source-config resolution failure writes a failed row and does not call `verify_source_image(...)`, `derive_board_from_width(...)`, or `run_iter9_single(...)`.
- Phase 5 parity comparison command is PowerShell-safe and does not use Bash heredoc syntax.
- `image_dir_path` is resolved once before `batch_id` construction and reused for `batch_id`, discovery, `batch_context`, and warmup failure row `image_path`.
- Discovery failure rows are verified against exact batch-level failure row values.
- Warmup failure rows are verified against exact batch-level failure row values.
- Source-config resolution failure is verified in both fail-fast and `--continue-on-error` modes.
- Default image-sweep `out_root` behavior is covered by automated test and manual no-`--out-root` smoke command.
