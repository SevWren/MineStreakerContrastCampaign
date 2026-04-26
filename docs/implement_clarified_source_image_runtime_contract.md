# Implement Clarified Source Image Runtime Contract

## Summary
- Remove the hard-coded runtime dependency on `assets/input_source_image.png` for normal runs while preserving backward-compatible defaults for `python run_iter9.py` and stable fixed-case behavior for `python run_benchmark.py --regression-only`.
- Keep established per-run artifact filenames unchanged. Image identity moves into directory names and provenance fields, not expanded filenames.
- Make validation import-safe, metrics provenance-rich, benchmark normal-mode output hierarchical, and all runs non-interactive and non-destructive.

## Verification Refresh (2026-04-26)
- Verified implementation state with a fresh execution pass on 2026-04-26 (America/Chicago).
- Commands executed in this refresh:
  - `python -m unittest discover -s tests -p "test_*.py"` (pass, 35 tests)
  - `python run_iter9.py --help` (pass)
  - `python run_benchmark.py --help` (pass)
  - `python assets/image_guard.py --path assets/input_source_image.png` (pass)
  - `python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical` (pass)
  - `python run_iter9.py` (pass)
  - `python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical` (pass)
  - `python run_benchmark.py --regression-only` (pass)
  - `python run_benchmark.py --regression-only --out-dir results/tmp_regression_contract_check_20260426T2012` (pass)
  - `python run_benchmark.py --regression-only --image assets/line_art_irl_11_v2.png` (expected fail-fast, pass-by-contract)
  - `python run_benchmark.py --image assets/line_art_irl_11_v2.png --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical` (pass)
  - `git grep "assets/input_source_image.png"` (reviewed)
- Fresh artifact evidence from this verification:
  - Iter9 default strict run: `results/iter9/20260426T200242Z_input_source_image_300w_seed42/`
  - Iter9 explicit-image run: `results/iter9/20260426T200320Z_line_art_irl_11_v2_300w_seed42/`
  - Benchmark run root: `results/benchmark/20260426T200455Z_line_art_irl_11_v2_benchmark/`
  - Regression-only custom out-dir check: `results/tmp_regression_contract_check_20260426T2012/`
  - Benchmark summaries present: `benchmark_summary.json`, `benchmark_summary.csv`, `benchmark_summary.md`
- Current quality-state note:
  - The source-image runtime contract implementation is functioning, but one normal benchmark child run remains unresolved (`420x311_seed22`, route `needs_sa_or_adaptive_rerun`, `n_unknown=130`), which is a model-quality/regression outcome, not a contract-interface failure.

## Key Changes
### 1. Add `source_config.py` as a filesystem-only identity module
- Add `SourceImageConfig` with these exact fields: `command_arg`, `absolute_path`, `project_relative_path`, `name`, `stem`, `sha256`, `size_bytes`, `allow_noncanonical`, `manifest_path`.
- Add `to_metrics_dict()` returning exactly: `command_arg`, `project_relative_path`, `absolute_path`, `name`, `stem`, `sha256`, `size_bytes`, `allow_noncanonical`, `manifest_path`.
- All serialized paths must use forward slashes on Windows.
- Add `compute_file_sha256(path: Path) -> str`, `project_relative_or_none(path: Path, project_root: Path) -> str | None`, and `resolve_source_image_config(image_path, project_root=None, allow_noncanonical=False, manifest_path=None) -> SourceImageConfig`.
- `source_config.py` must remain filesystem-only. It may do path resolution, existence/type checks, file-size reads, and SHA-256 hashing. It must not use Pillow, NumPy, manifest parsing, pixel-stat inspection, canonical validation, or runtime environment policy.

### 2. Refactor `assets/image_guard.py` into structured manifest-based validation
- Keep `DEFAULT_IMG_PATH`, `ALLOW_NONCANONICAL_ENV`, `verify_source_image()`, `get_canonical_record()`, and `compute_image_hashes()` public and backward-compatible.
- Stop using inline stale canonical metadata as the default-image authority. Load and normalize `assets/SOURCE_IMAGE_HASH.json` at validation time for the default image.
- Do not assume `assets/SOURCE_IMAGE_HASH.json` is correct. The validator must compare normalized manifest data to the live `assets/input_source_image.png` and fail clearly if the manifest is stale or mismatched. It must not rewrite the manifest or silently weaken strict mode.
- Support both the current nested `SOURCE_IMAGE_HASH.json` schema and the flat explicit-manifest schema from the plan by normalizing both into one internal comparison shape.
- Extend `verify_source_image()` to accept `allow_noncanonical: bool | None = None`, `manifest_path: str | None = None`, and `return_details: bool = False`.
- If `return_details=False`, preserve legacy behavior exactly.
- If `return_details=True`, return this exact JSON-safe shape:
```python
{
    "ok": bool,
    "path": str,
    "absolute_path": str,
    "manifest_path": str | None,
    "canonical_match": bool | None,
    "noncanonical_allowed": bool,
    "validation_mode": "default_manifest" | "explicit_manifest" | "noncanonical_allowed",
    "warnings": list[dict],
    "computed": dict,
    "expected": dict | None,
}
```
- Warning records must have exact shape:
```python
{
    "code": str,
    "severity": "info" | "warning" | "error",
    "message": str,
}
```
- Required warning codes are `DEFAULT_MANIFEST_USED`, `MANIFEST_NOT_SUPPLIED`, and `NONCANONICAL_SOURCE_ALLOWED`.
- Validation precedence is fixed: explicit manifest first, default manifest second for the default image, noncanonical mode last for non-default images without a manifest.
- For the default image, strict default-manifest validation wins even if `--allow-noncanonical` is passed.
- Normalize `computed` and `expected` to `file_size`, `file_sha256`, `pixel_sha256`, `pixel_shape`, `pixel_dtype`, `pixel_mean`, `pixel_std`, `pixel_min`, and `pixel_max`. In noncanonical mode, `expected` is `None`.

### 3. Refactor `run_iter9.py` to parse first, validate second, and emit provenance-rich metrics
- Remove all import-time image validation.
- Replace module-level runtime dependence on `IMG`, `BOARD_W`, `SEED`, and `OUT_DIR` with parsed arguments. Keep `DEFAULT_IMAGE = "assets/input_source_image.png"` only as the argparse default.
- Add CLI flags `--image`, `--out-dir`, `--board-w`, `--seed`, `--allow-noncanonical`, `--image-manifest`, and `--run-tag`.
- `--out-dir` means the exact final Iter9 run directory when supplied.
- When `--out-dir` is omitted, derive `results/iter9/<run_id>/` where `run_id = YYYYMMDDTHHMMSSZ_<image_stem>_<board_width>w_seed<seed>` and append sanitized `run_tag` if present.
- Define `--run-tag` sanitization exactly:
  - replace spaces with `_`
  - replace every non `[A-Za-z0-9_-]` character with `_`
  - collapse any run of separator characters `[_-]+` to a single `_`
  - trim leading and trailing `_` or `-`
  - truncate to 64 characters
  - trim separators again after truncation
  - omit the tag entirely if the sanitized result is empty
- Use the resolved source image everywhere currently using `IMG`, including board sizing and coarse/fine image loads.
- Preserve established Iter9 filenames inside the run directory:
  - `metrics_iter9_<board>.json`
  - `grid_iter9_<board>.npy`
  - `grid_iter9_latest.npy`
  - `iter9_<board>_FINAL.png`
  - `repair_overlay_<board>.png`
  - `failure_taxonomy.json`
  - `repair_route_decision.json`
  - `visual_delta_summary.json`
- Add a pure helper `build_metrics_document(...) -> dict` so unit tests can validate provenance blocks without running SA.
- `build_metrics_document()` must emit these required blocks: `schema_version`, `run_identity`, `run_timing`, `project_identity`, `command_invocation`, `source_image`, `source_image_analysis`, `effective_config`, `board_sizing`, `preprocessing_config`, `target_field_stats`, `weight_config`, `corridor_config`, `sa_config`, `repair_config`, `solver_summary`, `repair_route_summary`, `visual_quality_summary`, `runtime_phase_timing_s`, `environment`, `artifact_inventory`, `validation_gates`, `warnings_and_exceptions`, and `llm_review_summary`.
- Preserve all existing flat metrics keys as additive compatibility fields, especially repair-routing metrics and current quality metrics.
- Record current run ID and UTC timestamps in metrics for every run.
- Output-directory behavior is fixed:
  - do not delete existing files
  - allow atomic overwrite only for files this run writes
  - keep runs non-interactive
  - use `os.makedirs(..., exist_ok=True)` for directories
- For JSON, NPY, and new summary artifacts, use temp-write plus `os.replace`. For rendered PNG outputs, write to a temp path and replace atomically where practical so reruns do not leave partial files.

### 4. Extend `pipeline.write_repair_route_artifacts()` with linked artifact metadata
- Add an optional metadata input while preserving the current return shape.
- Inject `artifact_metadata` into `failure_taxonomy.json`, `repair_route_decision.json`, and `visual_delta_summary.json`.
- `artifact_metadata` must include `run_id`, `generated_at_utc`, `source_image_project_relative_path`, `source_image_sha256`, and `metrics_path`.
- Use project-relative forward-slash `metrics_path` when possible. If the image is outside the repo, allow `source_image_project_relative_path = null`.

### 5. Refactor `run_benchmark.py` into normal-mode run roots plus per-board/seed child directories
- Remove all import-time image validation.
- Keep `DEFAULT_IMAGE = "assets/input_source_image.png"` only as the normal-mode argparse default.
- Add CLI flags `--image`, `--widths`, `--seeds`, `--out-dir`, `--allow-noncanonical`, `--image-manifest`, `--regression-only`, and `--include-regressions`.
- `--regression-only` must fail fast if explicitly mixed with incompatible normal-mode flags. Detect explicit user-supplied incompatible flags by inspecting raw `sys.argv`, not only parsed values, so defaults are not mistaken for user input.
- The incompatible explicit flags are `--image`, `--widths`, `--seeds`, `--allow-noncanonical`, `--image-manifest`, and `--include-regressions`.
- `--out-dir` remains allowed with `--regression-only`.
- Detection must catch both `--flag value` and `--flag=value` forms.
- The failure must occur immediately after parse validation using `argparse.ArgumentParser.error(...)` with a clear message naming the incompatible flags found.
- `--regression-only` must keep using fixed `REGRESSION_CASES`, stable default filenames, current route gates, and current unknown-count gates.
- In normal benchmark mode, `--out-dir` means the benchmark-run root. When omitted, derive `results/benchmark/<benchmark_run_id>/` where `benchmark_run_id = YYYYMMDDTHHMMSSZ_<image_stem>_benchmark`.
- Inside the benchmark-run root, create one child directory per board/seed named exactly `<board_width>x<board_height>_seed<seed>/`.
- Normal benchmark artifacts must not be written flat at the benchmark root.
- Each child directory must preserve benchmark-compatible filenames:
  - `metrics_<board>.json`
  - `grid_<board>.npy`
  - `visual_<board>.png`
  - `repair_overlay_<board>.png`
  - `failure_taxonomy.json`
  - `repair_route_decision.json`
  - `visual_delta_summary.json`
- Implement normal-mode child runs by changing `run_single()` so it writes a full child-run artifact set instead of returning only a row dict.
- Normal benchmark child `metrics_<board>.json` should reuse the same provenance-rich structured metrics contract as Iter9 where practical, plus benchmark context fields such as `benchmark_mode`, `benchmark_run_id`, and `child_run_dir`.
- Normal benchmark mode must emit required benchmark-root summary files:
  - `benchmark_summary.json`
  - `benchmark_summary.csv`
  - `benchmark_summary.md`
- `benchmark_results.json` may remain as a compatibility list-of-row output in addition to the required summary files.
- `benchmark_summary.json` must include benchmark-run metadata, per-child rows, and per-board aggregates.
- `benchmark_summary.csv` must contain one row per child run with at least `board`, `seed`, `child_dir`, `n_unknown`, `coverage`, `solvable`, `repair_route_selected`, `repair_route_result`, `phase2_fixes`, `last100_fixes`, `visual_delta`, `total_time_s`, and source-image identity columns.
- `benchmark_summary.md` must contain benchmark-run provenance, aggregate board medians, and a readable per-child results table.
- In normal mode, resolve and validate the source image once at the benchmark-run level and pass the resolved config plus validation details into child runs.
- Child rows and benchmark summaries must include nested `source_image` provenance using `SourceImageConfig.to_metrics_dict()`.
- Regression-only default output layout remains compatible and separate from the new normal-mode directory layout.

### 6. Update `README.md` and `AGENTS.md`
- Update `README.md` to stop teaching overwrite workflows for `assets/input_source_image.png`.
- Replace beginner commands with explicit-image examples using `assets/line_art_irl_11_v2.png` and `--allow-noncanonical`.
- Keep a short backward-compatible note that `run_iter9.py` defaults to `assets/input_source_image.png` only when `--image` is omitted.
- Explain manifest validation, noncanonical mode, and where source-image provenance appears in metrics.
- Update `AGENTS.md` with a Source Image Runtime Contract requiring explicit CLI image handling, no import-time validation, provenance-rich metrics, image identity in directories and metrics rather than filenames, and fixed-image exceptions only for regression cases.

## Test Plan
- Add `tests/test_source_config.py` covering absolute paths, project-relative paths, out-of-repo paths, SHA-256 hashing, size capture, and `to_metrics_dict()` forward-slash formatting.
- Add `tests/test_source_image_cli_contract.py` covering:
  - `run_iter9.py --help`
  - `run_benchmark.py --help`
  - default `--image` values
  - no import-time validation by patching `assets.image_guard.verify_source_image` and importing/reloading both modules
  - fail-fast rejection when `--regression-only` is mixed with explicitly supplied incompatible normal-mode flags by raw `sys.argv`
  - acceptance of `--regression-only` with `--out-dir`
  - `--run-tag` sanitization cases, including empty-after-sanitize behavior
- Add image-guard tests covering:
  - default manifest success using the live `assets/SOURCE_IMAGE_HASH.json`
  - explicit flat manifest success
  - custom image failure without manifest/noncanonical
  - structured warnings and exact `return_details=True` schema
  - mismatch failure when default manifest and live image disagree
- Add tests for `build_metrics_document()` asserting all required provenance blocks exist without running SA and that current flat repair-routing fields are still present.
- Add tests for benchmark normal-mode layout helpers asserting benchmark-root path derivation, child-directory naming, summary-file naming, preserved child artifact filenames, and non-destructive existing-directory behavior.
- Add tests for route artifact metadata asserting all three route JSONs contain `artifact_metadata` with required keys.
- Keep existing repair-routing tests green.

## Final Acceptance Commands
- `python -m unittest discover -s tests -p "test_*.py"`
- `python run_iter9.py --help`
- `python run_benchmark.py --help`
- `python assets/image_guard.py --path assets/input_source_image.png`
- `python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical`
- `python run_iter9.py`
- `python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical`
- `python run_benchmark.py --regression-only`
- `python run_benchmark.py --image assets/line_art_irl_11_v2.png --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical`

## Assumptions and Defaults
- The implementation must verify, not assume, that `assets/SOURCE_IMAGE_HASH.json` matches the live default image before using it as the strict default manifest source of truth.
- `run_iter9.py --out-dir` is the exact run directory. `run_benchmark.py --out-dir` is the benchmark-run root that still contains required board/seed child directories.
- Established artifact filenames are preserved inside directories. Image identity belongs in directory names and provenance fields, not expanded filenames.
- Regression-only output layout stays compatible by default and is intentionally not migrated in this implementation.
