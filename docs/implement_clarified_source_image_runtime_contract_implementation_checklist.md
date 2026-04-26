# Source Image Runtime Contract â€” Implementation Checklist

**Companion to:** `Implement Clarified Source Image Runtime Contract`  
**Purpose:** Track implementation progress, verification evidence, skipped work, and final readiness for the source-image runtime contract refactor.

---

## Checklist Status Legend

| Status | Meaning |
|---|---|
| `[ ]` | Not started |
| `[~]` | In progress / partially implemented |
| `[x]` | Complete and verified |
| `[!]` | Blocked / requires decision or fix |
| `[D]` | Deferred intentionally |
| `[N/A]` | Not applicable after implementation review |

---

## Implementation Goals

- [x] Remove hard-coded runtime dependence on `assets/input_source_image.png` for normal runs.
- [x] Preserve backward-compatible default behavior for `python run_iter9.py`.
- [x] Preserve stable fixed-case behavior for `python run_benchmark.py --regression-only`.
- [x] Preserve established artifact filenames inside run-specific directories.
- [x] Move image identity into directory names and provenance fields, not expanded filenames.
- [x] Make image validation import-safe.
- [x] Make metrics JSON provenance-rich and LLM-review friendly.
- [x] Make normal benchmark outputs hierarchical by benchmark run root and board/seed child directories.
- [x] Keep all runs non-interactive and non-destructive.

## Authoritative Verification Snapshot (2026-04-26)

This section is the authoritative current-state refresh. The detailed per-line checklist below is retained as the original execution scaffold.

- Verification date: 2026-04-26 15:12:01 (America/Chicago, UTC-05:00)
- Branch: `codex/pipe_line_late_stage_repair_routing`
- Commit at verification start: `6378a6a3b90dde829a44a8c698db8d8d78422037`
- Fresh verification commands executed in this refresh:
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
- Fresh artifact evidence:
  - `results/iter9/20260426T200242Z_input_source_image_300w_seed42/`
  - `results/iter9/20260426T200320Z_line_art_irl_11_v2_300w_seed42/`
  - `results/benchmark/20260426T200455Z_line_art_irl_11_v2_benchmark/`
  - `results/tmp_regression_contract_check_20260426T2012/`
- Benchmark summary files verified present at benchmark root:
  - `benchmark_summary.json`
  - `benchmark_summary.csv`
  - `benchmark_summary.md`
- Runtime quality note:
  - Contract implementation verified. One normal benchmark child run remains unresolved (`420x311_seed22`, route `needs_sa_or_adaptive_rerun`, `n_unknown=130`); this is a quality/performance outcome, not a contract-interface break.

---

# Phase 0 â€” Pre-Implementation Baseline

## 0.1 Confirm starting state

- [x] Confirm `run_iter9.py` currently hard-codes or depends on `assets/input_source_image.png` in normal runtime logic.
- [x] Confirm `run_benchmark.py` currently hard-codes or depends on `assets/input_source_image.png` in normal runtime logic.
- [x] Confirm `run_iter9.py` performs image validation only after implementation, not at import time.
- [x] Confirm `run_benchmark.py` performs image validation only after implementation, not at import time.
- [x] Confirm existing Iter9 artifact filenames before refactor.
- [x] Confirm existing benchmark regression-only filenames before refactor.
- [x] Confirm current repair-routing tests pass before refactor.

## 0.2 Record baseline evidence

| Evidence Item | Path / Command | Status | Notes |
|---|---|---|---|
| Current branch | `git branch --show-current` | [x] | `codex/pipe_line_late_stage_repair_routing` |
| Current commit | `git rev-parse HEAD` | [x] | `6378a6a3b90dde829a44a8c698db8d8d78422037` |
| Dirty state | `git status --short` | [x] | Dirty worktree preserved; no unrelated files reverted. |
| Unit tests baseline | `python -m unittest discover -s tests -p "test_*.py"` | [x] | Passes after implementation updates (35 tests). |
| Existing strict image guard | `python assets/image_guard.py --path assets/input_source_image.png` | [x] | Passes in strict default-manifest mode. |
| Existing regression-only benchmark | `python run_benchmark.py --regression-only` | [x] | Passes route/coverage/unknown gates on fixed case. |

---

# Phase 1 â€” Add `source_config.py`

## 1.1 Create filesystem-only source identity module

- [x] Add new file: `source_config.py`.
- [x] Add `SourceImageConfig` dataclass.
- [x] Add exact fields:
  - [x] `command_arg`
  - [x] `absolute_path`
  - [x] `project_relative_path`
  - [x] `name`
  - [x] `stem`
  - [x] `sha256`
  - [x] `size_bytes`
  - [x] `allow_noncanonical`
  - [x] `manifest_path`
- [x] Add `to_metrics_dict()`.
- [x] Ensure `to_metrics_dict()` returns exactly:
  - [x] `command_arg`
  - [x] `project_relative_path`
  - [x] `absolute_path`
  - [x] `name`
  - [x] `stem`
  - [x] `sha256`
  - [x] `size_bytes`
  - [x] `allow_noncanonical`
  - [x] `manifest_path`
- [x] Ensure all serialized paths use forward slashes on Windows.

## 1.2 Add source identity helpers

- [x] Add `compute_file_sha256(path: Path) -> str`.
- [x] Add `project_relative_or_none(path: Path, project_root: Path) -> str | None`.
- [x] Add `resolve_source_image_config(image_path, project_root=None, allow_noncanonical=False, manifest_path=None) -> SourceImageConfig`.
- [x] Ensure `resolve_source_image_config()` validates path existence.
- [x] Ensure `resolve_source_image_config()` validates path is a file, not a directory.
- [x] Ensure `resolve_source_image_config()` records file size.
- [x] Ensure `resolve_source_image_config()` records SHA-256 hash.
- [x] Ensure `resolve_source_image_config()` records project-relative path when inside repo.
- [x] Ensure `resolve_source_image_config()` records `project_relative_path = None` when outside repo.

## 1.3 Enforce ownership boundary

- [x] Confirm `source_config.py` does **not** import Pillow.
- [x] Confirm `source_config.py` does **not** import NumPy.
- [x] Confirm `source_config.py` does **not** parse manifests.
- [x] Confirm `source_config.py` does **not** compute pixel statistics.
- [x] Confirm `source_config.py` does **not** perform canonical validation.
- [x] Confirm `source_config.py` does **not** inspect environment policy flags.
- [x] Confirm `source_config.py` does **not** perform git metadata lookup.

## 1.4 Phase 1 verification

- [x] Add tests in `tests/test_source_config.py` for absolute paths.
- [x] Add tests in `tests/test_source_config.py` for project-relative paths.
- [x] Add tests in `tests/test_source_config.py` for out-of-repo paths.
- [x] Add tests in `tests/test_source_config.py` for SHA-256 hashing.
- [x] Add tests in `tests/test_source_config.py` for size capture.
- [x] Add tests in `tests/test_source_config.py` for forward-slash path formatting.
- [x] Run `python -m unittest tests.test_source_config`.

---

# Phase 2 â€” Refactor `assets/image_guard.py`

## 2.1 Preserve public compatibility

- [x] Keep `DEFAULT_IMG_PATH` public.
- [x] Keep `ALLOW_NONCANONICAL_ENV` public.
- [x] Keep `verify_source_image()` public.
- [x] Keep `get_canonical_record()` public.
- [x] Keep `compute_image_hashes()` public.
- [x] Preserve legacy behavior when `return_details=False`.
- [x] Ensure existing callers continue working unchanged.

## 2.2 Replace inline stale canonical metadata

- [x] Stop using inline stale canonical metadata as default-image authority.
- [x] Load `assets/SOURCE_IMAGE_HASH.json` at validation time for default image.
- [x] Normalize `assets/SOURCE_IMAGE_HASH.json` into internal comparison schema.
- [x] Compare normalized manifest values to live `assets/input_source_image.png`.
- [x] Fail clearly if manifest is stale or mismatched.
- [x] Do not rewrite the manifest automatically.
- [x] Do not weaken strict mode on mismatch.

## 2.3 Support manifest schemas

- [x] Support existing nested `SOURCE_IMAGE_HASH.json` schema.
- [x] Support flat explicit-manifest schema.
- [x] Normalize both schemas into one internal comparison shape.

## 2.4 Extend `verify_source_image()` API

- [x] Add `allow_noncanonical: bool | None = None`.
- [x] Add `manifest_path: str | None = None`.
- [x] Add `return_details: bool = False`.
- [x] When `return_details=True`, return exact JSON-safe shape:
  - [x] `ok`
  - [x] `path`
  - [x] `absolute_path`
  - [x] `manifest_path`
  - [x] `canonical_match`
  - [x] `noncanonical_allowed`
  - [x] `validation_mode`
  - [x] `warnings`
  - [x] `computed`
  - [x] `expected`

## 2.5 Warning records and validation modes

- [x] Warning records have exact fields:
  - [x] `code`
  - [x] `severity`
  - [x] `message`
- [x] Support warning code `DEFAULT_MANIFEST_USED`.
- [x] Support warning code `MANIFEST_NOT_SUPPLIED`.
- [x] Support warning code `NONCANONICAL_SOURCE_ALLOWED`.
- [x] `validation_mode` can be `default_manifest`.
- [x] `validation_mode` can be `explicit_manifest`.
- [x] `validation_mode` can be `noncanonical_allowed`.

## 2.6 Validation precedence

- [x] Explicit manifest wins when `manifest_path` is supplied.
- [x] Default manifest applies for default image when no explicit manifest is supplied.
- [x] Noncanonical mode applies only for non-default images without applicable manifest.
- [x] Default image strict manifest validation wins even if `--allow-noncanonical` is supplied.

## 2.7 Computed / expected comparison keys

- [x] Normalize `computed.file_size`.
- [x] Normalize `computed.file_sha256`.
- [x] Normalize `computed.pixel_sha256`.
- [x] Normalize `computed.pixel_shape`.
- [x] Normalize `computed.pixel_dtype`.
- [x] Normalize `computed.pixel_mean`.
- [x] Normalize `computed.pixel_std`.
- [x] Normalize `computed.pixel_min`.
- [x] Normalize `computed.pixel_max`.
- [x] Normalize matching `expected.*` keys for manifest modes.
- [x] Set `expected = None` in noncanonical mode.

## 2.8 Phase 2 verification

- [x] Test default manifest success with live `assets/SOURCE_IMAGE_HASH.json`.
- [x] Test explicit flat manifest success.
- [x] Test custom image failure without manifest/noncanonical.
- [x] Test structured warnings.
- [x] Test exact `return_details=True` schema.
- [x] Test mismatch failure when default manifest and live image disagree.
- [x] Run `python assets/image_guard.py --path assets/input_source_image.png`.
- [x] Run `python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical`.

---

# Phase 3 â€” Refactor `run_iter9.py`

## 3.1 Remove import-time validation and globals

- [x] Remove all import-time `verify_source_image()` calls.
- [x] Replace runtime dependence on module-level `IMG`.
- [x] Replace runtime dependence on module-level `BOARD_W`.
- [x] Replace runtime dependence on module-level `SEED`.
- [x] Replace runtime dependence on module-level `OUT_DIR`.
- [x] Keep `DEFAULT_IMAGE = "assets/input_source_image.png"` only as argparse default.

## 3.2 Add CLI contract

- [x] Add `--image` default `assets/input_source_image.png`.
- [x] Add `--out-dir` default `None`.
- [x] Add `--board-w` default `300`.
- [x] Add `--seed` default `42`.
- [x] Add `--allow-noncanonical`.
- [x] Add `--image-manifest`.
- [x] Add `--run-tag` default empty string.
- [x] Ensure `python run_iter9.py --help` exits without image validation.

## 3.3 Implement run ID and output directory policy

- [x] `--out-dir` means exact final Iter9 run directory.
- [x] Omitted `--out-dir` derives `results/iter9/<run_id>/`.
- [x] Run ID format: `YYYYMMDDTHHMMSSZ_<image_stem>_<board_width>w_seed<seed>`.
- [x] Append sanitized run tag when present.
- [x] Use `os.makedirs(..., exist_ok=True)`.
- [x] Do not delete existing files.
- [x] Allow atomic overwrite only for files this run writes.

## 3.4 Implement run-tag sanitization

- [x] Replace spaces with `_`.
- [x] Replace every non `[A-Za-z0-9_-]` character with `_`.
- [x] Collapse any run of `[_-]+` to a single `_`.
- [x] Trim leading and trailing `_` or `-`.
- [x] Truncate to 64 characters.
- [x] Trim separators again after truncation.
- [x] Omit tag entirely if sanitized result is empty.
- [x] Add tests for normal tag.
- [x] Add tests for punctuation-heavy tag.
- [x] Add tests for empty-after-sanitize tag.
- [x] Add tests for over-64-character tag.

## 3.5 Use resolved source image everywhere

- [x] Use resolved source image in board sizing.
- [x] Use resolved source image in full-resolution image load.
- [x] Use resolved source image in coarse image load.
- [x] Use resolved source image in all source-image metadata.
- [x] Do not copy over `assets/input_source_image.png`.
- [x] Do not require image renaming.

## 3.6 Preserve Iter9 artifact filenames

- [x] Preserve `metrics_iter9_<board>.json`.
- [x] Preserve `grid_iter9_<board>.npy`.
- [x] Preserve `grid_iter9_latest.npy`.
- [x] Preserve `iter9_<board>_FINAL.png`.
- [x] Preserve `repair_overlay_<board>.png`.
- [x] Preserve `failure_taxonomy.json`.
- [x] Preserve `repair_route_decision.json`.
- [x] Preserve `visual_delta_summary.json`.

## 3.7 Add `build_metrics_document(...)`

- [x] Add pure helper `build_metrics_document(...) -> dict`.
- [x] Ensure helper can be unit-tested without running SA.
- [x] Add `schema_version` block.
- [x] Add `run_identity` block.
- [x] Add `run_timing` block.
- [x] Add `project_identity` block.
- [x] Add `command_invocation` block.
- [x] Add `source_image` block.
- [x] Add `source_image_analysis` block.
- [x] Add `effective_config` block.
- [x] Add `board_sizing` block.
- [x] Add `preprocessing_config` block.
- [x] Add `target_field_stats` block.
- [x] Add `weight_config` block.
- [x] Add `corridor_config` block.
- [x] Add `sa_config` block.
- [x] Add `repair_config` block.
- [x] Add `solver_summary` block.
- [x] Add `repair_route_summary` block.
- [x] Add `visual_quality_summary` block.
- [x] Add `runtime_phase_timing_s` block.
- [x] Add `environment` block.
- [x] Add `artifact_inventory` block.
- [x] Add `validation_gates` block.
- [x] Add `warnings_and_exceptions` block.
- [x] Add `llm_review_summary` block.
- [x] Preserve all existing flat metrics keys as additive compatibility fields.
- [x] Preserve current repair-routing flat metrics keys.
- [x] Preserve current board-quality flat metrics keys.

## 3.8 Atomic writes

- [x] Use temp-write plus `os.replace` for metrics JSON.
- [x] Use temp-write plus `os.replace` for NPY files.
- [x] Use temp-write plus `os.replace` for route JSON artifacts where applicable.
- [x] Use temp path plus replace for rendered PNG where practical.

## 3.9 Phase 3 verification

- [x] `python run_iter9.py --help` passes without validation.
- [x] Importing `run_iter9.py` does not validate image.
- [x] `python run_iter9.py` works with default image in strict mode or fails clearly if default manifest is stale.
- [x] `python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical` writes to run-specific directory.
- [x] Metrics JSON contains all required provenance blocks.
- [x] Metrics JSON preserves existing flat metrics keys.
- [x] Artifact inventory points to preserved Iter9 filenames.

---

# Phase 4 â€” Extend `pipeline.write_repair_route_artifacts()`

## 4.1 Add optional linked metadata

- [x] Extend `write_repair_route_artifacts()` with optional metadata argument.
- [x] Preserve current return shape unchanged.
- [x] Inject `artifact_metadata` into `failure_taxonomy.json`.
- [x] Inject `artifact_metadata` into `repair_route_decision.json`.
- [x] Inject `artifact_metadata` into `visual_delta_summary.json`.

## 4.2 Required metadata fields

- [x] Add `run_id`.
- [x] Add `generated_at_utc`.
- [x] Add `source_image_project_relative_path`.
- [x] Add `source_image_sha256`.
- [x] Add `metrics_path`.
- [x] Use project-relative forward-slash `metrics_path` when possible.
- [x] Use forward-slash absolute `metrics_path` when project-relative path is unavailable.
- [x] Allow `source_image_project_relative_path = None` for out-of-repo images.

## 4.3 Phase 4 verification

- [x] Add tests asserting all three route JSONs contain `artifact_metadata`.
- [x] Add tests asserting required metadata keys are present.
- [x] Add tests asserting existing return shape is unchanged.
- [x] Confirm route artifact paths are still emitted correctly by Iter9.

---

# Phase 5 â€” Refactor `run_benchmark.py`

## 5.1 Remove import-time validation

- [x] Remove all import-time `verify_source_image()` calls.
- [x] Keep `DEFAULT_IMAGE = "assets/input_source_image.png"` only as normal-mode argparse default.
- [x] Ensure `python run_benchmark.py --help` exits without image validation.
- [x] Ensure importing `run_benchmark.py` does not validate image.

## 5.2 Add CLI contract

- [x] Add `--image`.
- [x] Add `--widths` with `nargs +`.
- [x] Add `--seeds` with `nargs +`.
- [x] Add `--out-dir`.
- [x] Add `--allow-noncanonical`.
- [x] Add `--image-manifest`.
- [x] Add `--regression-only`.
- [x] Add `--include-regressions`.

## 5.3 Regression-only conflict handling

- [x] Detect explicitly supplied incompatible flags using raw `sys.argv`.
- [x] Detect `--image`.
- [x] Detect `--image=value` form.
- [x] Detect `--widths`.
- [x] Detect `--widths=value` form.
- [x] Detect `--seeds`.
- [x] Detect `--seeds=value` form.
- [x] Detect `--allow-noncanonical`.
- [x] Detect `--image-manifest`.
- [x] Detect `--image-manifest=value` form.
- [x] Detect `--include-regressions`.
- [x] Allow `--out-dir` with `--regression-only`.
- [x] Use `argparse.ArgumentParser.error(...)` for conflicts.
- [x] Error message names incompatible flags found.
- [x] Preserve fixed `REGRESSION_CASES` behavior.
- [x] Preserve current regression route gates.
- [x] Preserve current regression unknown-count gates.
- [x] Preserve stable regression-only default filenames.

## 5.4 Normal benchmark output layout

- [x] `--out-dir` means benchmark-run root.
- [x] Omitted `--out-dir` derives `results/benchmark/<benchmark_run_id>/`.
- [x] Benchmark run ID format: `YYYYMMDDTHHMMSSZ_<image_stem>_benchmark`.
- [x] Create one child directory per board/seed.
- [x] Child directory name format: `<board_width>x<board_height>_seed<seed>/`.
- [x] Do not write normal benchmark artifacts flat at benchmark root.

## 5.5 Preserve child artifact filenames

- [x] Preserve `metrics_<board>.json`.
- [x] Preserve `grid_<board>.npy`.
- [x] Preserve `visual_<board>.png`.
- [x] Preserve `repair_overlay_<board>.png`.
- [x] Preserve `failure_taxonomy.json`.
- [x] Preserve `repair_route_decision.json`.
- [x] Preserve `visual_delta_summary.json`.

## 5.6 Change `run_single()` behavior

- [x] Change normal-mode `run_single()` to write full child-run artifact set.
- [x] Keep returned row data for summary generation.
- [x] Pass resolved source-image config into each child run.
- [x] Pass image validation details into each child run.
- [x] Resolve and validate normal-mode source image only once per benchmark run.

## 5.7 Benchmark child metrics

- [x] Child metrics reuse provenance-rich structured metrics contract where practical.
- [x] Add `benchmark_mode`.
- [x] Add `benchmark_run_id`.
- [x] Add `child_run_dir`.
- [x] Include nested `source_image` from `SourceImageConfig.to_metrics_dict()`.

## 5.8 Benchmark root summaries

- [x] Emit `benchmark_summary.json`.
- [x] Emit `benchmark_summary.csv`.
- [x] Emit `benchmark_summary.md`.
- [x] Optionally emit compatibility `benchmark_results.json`.
- [x] `benchmark_summary.json` includes benchmark-run metadata.
- [x] `benchmark_summary.json` includes per-child rows.
- [x] `benchmark_summary.json` includes per-board aggregates.
- [x] `benchmark_summary.csv` includes one row per child run.
- [x] CSV includes `board`.
- [x] CSV includes `seed`.
- [x] CSV includes `child_dir`.
- [x] CSV includes `n_unknown`.
- [x] CSV includes `coverage`.
- [x] CSV includes `solvable`.
- [x] CSV includes `repair_route_selected`.
- [x] CSV includes `repair_route_result`.
- [x] CSV includes `phase2_fixes`.
- [x] CSV includes `last100_fixes`.
- [x] CSV includes `visual_delta`.
- [x] CSV includes `total_time_s`.
- [x] CSV includes source-image identity columns.
- [x] Markdown includes benchmark-run provenance.
- [x] Markdown includes aggregate board medians.
- [x] Markdown includes readable per-child results table.

## 5.9 Phase 5 verification

- [x] `python run_benchmark.py --help` passes without validation.
- [x] Importing `run_benchmark.py` does not validate image.
- [x] `python run_benchmark.py --regression-only` keeps stable regression behavior.
- [x] `python run_benchmark.py --regression-only --out-dir results/tmp_regression` is accepted.
- [x] `python run_benchmark.py --regression-only --image assets/line_art_irl_11_v2.png` fails fast.
- [x] `python run_benchmark.py --regression-only --image=assets/line_art_irl_11_v2.png` fails fast.
- [x] Normal benchmark explicit-image run writes benchmark root.
- [x] Normal benchmark explicit-image run writes per-board/per-seed child directories.
- [x] Normal benchmark explicit-image run writes required summary files.
- [x] Normal benchmark child metrics include source-image provenance.

---

# Phase 6 â€” Documentation Updates

## 6.1 README.md

- [x] Remove or replace guidance that teaches overwrite workflows for `assets/input_source_image.png`.
- [x] Add explicit-image Iter9 example using `assets/line_art_irl_11_v2.png`.
- [x] Add explicit-image benchmark example using `assets/line_art_irl_11_v2.png`.
- [x] Explain `--allow-noncanonical` for custom images.
- [x] Explain manifest validation.
- [x] Explain where source-image provenance appears in metrics.
- [x] Keep short note that `run_iter9.py` defaults to `assets/input_source_image.png` only when `--image` is omitted.

## 6.2 AGENTS.md

- [x] Add Source Image Runtime Contract.
- [x] Require explicit CLI image handling for entry scripts.
- [x] Forbid import-time image validation.
- [x] Require provenance-rich metrics.
- [x] Require image identity in directories and metrics, not expanded filenames.
- [x] Document fixed-image exceptions only for regression cases.

## 6.3 Phase 6 verification

- [x] README examples do not instruct users to overwrite `assets/input_source_image.png`.
- [x] AGENTS.md contract prevents reintroducing hard-coded normal runtime image globals.
- [x] Documentation examples match implemented CLI flags.

---

# Phase 7 â€” Test Suite Completion

## 7.1 Required test files

- [x] Add or update `tests/test_source_config.py`.
- [x] Add or update `tests/test_source_image_cli_contract.py`.
- [x] Add or update image-guard tests.
- [x] Add or update metrics-document tests.
- [x] Add or update benchmark-layout tests.
- [x] Add or update route-artifact metadata tests.
- [x] Keep existing repair-routing tests green.

## 7.2 Full unit test command

- [x] Run `python -m unittest discover -s tests -p "test_*.py"`.
- [x] Record result.
- [x] Fix all failures.

---

# Phase 8 â€” Acceptance Commands

Run all commands from the repository root.

| Command | Status | Evidence / Notes |
|---|---|---|
| `python -m unittest discover -s tests -p "test_*.py"` | [x] | Pass (35 tests). |
| `python run_iter9.py --help` | [x] | Help renders with new CLI flags; no validation side effects. |
| `python run_benchmark.py --help` | [x] | Help renders with normal/regression contract flags. |
| `python assets/image_guard.py --path assets/input_source_image.png` | [x] | Strict default-manifest validation passes. |
| `python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical` | [x] | Passes with structured noncanonical warnings. |
| `python run_iter9.py` | [x] | Pass; writes `results/iter9/20260426T200242Z_input_source_image_300w_seed42/`. |
| `python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical` | [x] | Pass; writes `results/iter9/20260426T200320Z_line_art_irl_11_v2_300w_seed42/`. |
| `python run_benchmark.py --regression-only` | [x] | Pass; fixed `line_art_irl_9.png` route-aware regression validates. |
| `python run_benchmark.py --image assets/line_art_irl_11_v2.png --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical` | [x] | Pass; writes `results/benchmark/20260426T200455Z_line_art_irl_11_v2_benchmark/` with required summary files and child dirs. |

---

# Phase 9 â€” Final Grep Check

## 9.1 Search command

- [x] Run repository search for:

```text
assets/input_source_image.png
```

Suggested command:

```powershell
Select-String -Path *.py,*.md,assets\*.py,tests\*.py -Pattern "assets/input_source_image.png" -Recurse
```

Alternative Git command:

```powershell
git grep "assets/input_source_image.png"
```

## 9.2 Allowed remaining occurrences

Each remaining occurrence must be one of:

- [x] argparse default.
- [x] README backward-compatibility note.
- [x] AGENTS backward-compatibility note.
- [x] default manifest validation path.
- [x] test fixture for backward compatibility.
- [x] fixed regression or default-image test expectation.
- [~] Residual non-runtime historical references remain in archived/deprecated docs and plan history files.

## 9.3 Forbidden remaining occurrences

- [x] No normal runtime path implicitly depends on `assets/input_source_image.png`.
- [x] No normal experiment path requires copying over `assets/input_source_image.png`.
- [x] No normal benchmark path requires the default image unless `--image` is omitted.

---

# Final Implementation Matrix

| Area | Required Result | Status | Evidence |
|---|---|---|---|
| `source_config.py` | Filesystem-only source identity module exists | [x] | Dataclass + helpers + forward-slash serializer + tests. |
| `assets/image_guard.py` | Manifest-driven structured validation | [x] | Default/explicit/noncanonical modes + structured warning/details schema. |
| `run_iter9.py` | CLI-driven, import-safe, provenance-rich | [x] | Parse-first validate-second + structured metrics + route artifact metadata + `repair_overlay_path`. |
| `pipeline.py` | Route artifacts include linked metadata | [x] | `artifact_metadata` injected into all three route JSON artifacts. |
| `run_benchmark.py` | Normal mode uses benchmark root + child run dirs | [x] | Per-run child directories + preserved filenames + benchmark summaries + regression-only guardrails. |
| `README.md` | No overwrite workflow; explicit-image docs | [x] | Added source image runtime contract and explicit command examples. |
| `AGENTS.md` | Source Image Runtime Contract added | [x] | Added contract rules + deprecated-study out-of-scope note retained. |
| Tests | New and existing tests pass | [x] | `python -m unittest discover -s tests -p "test_*.py"` passes (35). |
| Acceptance commands | All required commands run | [x] | All listed commands executed successfully in this implementation pass. |
| Final grep check | No hidden hard-coded normal runtime dependency | [~] | Runtime paths comply; historical/archive docs still mention legacy path. |

---

# Final Completion Statement

Complete this section only after implementation and validation.

```text
Implementation completed on: 2026-04-26

Summary of completed changes:
- Added `source_config.py` with `SourceImageConfig`, SHA-256 helpers, project-relative resolution, and JSON-safe path serialization.
- Refactored `assets/image_guard.py` to manifest-driven validation with strict default-manifest behavior, explicit manifest mode, noncanonical mode, and structured detail payloads/warnings.
- Refactored `run_iter9.py` to parse-first/validate-second, CLI source image contract, run-tag sanitization, atomic writes, and provenance-rich structured metrics while preserving flat compatibility metrics and repair route artifacts.
- Extended `pipeline.write_repair_route_artifacts(...)` with additive `artifact_metadata`.
- Rebuilt `run_benchmark.py` with:
  - import-safe behavior,
  - raw-argv conflict detection for `--regression-only`,
  - fixed regression-only compatibility,
  - normal benchmark root + per-board/per-seed child directories,
  - preserved child artifact filenames,
  - required benchmark root summaries (`benchmark_summary.json/.csv/.md`) plus compatibility `benchmark_results.json`.
- Updated `README.md` and `AGENTS.md` with Source Image Runtime Contract guidance.
- Added tests:
  - `tests/test_source_config.py`
  - `tests/test_source_image_cli_contract.py`
  - `tests/test_image_guard_contract.py`
  - `tests/test_benchmark_layout.py`
  - `tests/test_route_artifact_metadata.py`

Tests run:
- python -m unittest discover -s tests -p "test_*.py"
- python run_iter9.py --help
- python run_benchmark.py --help
- python assets/image_guard.py --path assets/input_source_image.png
- python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
- python run_iter9.py
- python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical
- python run_benchmark.py --regression-only
- python run_benchmark.py --regression-only --out-dir results/tmp_regression_contract_check_20260426T2012
- python run_benchmark.py --regression-only --image assets/line_art_irl_11_v2.png  (expected fail-fast)
- python run_benchmark.py --image assets/line_art_irl_11_v2.png --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical
- git grep "assets/input_source_image.png"

Artifacts generated:
- Iter9 run directories:
  - `results/iter9/20260426T200242Z_input_source_image_300w_seed42/`
  - `results/iter9/20260426T200320Z_line_art_irl_11_v2_300w_seed42/`
- Benchmark run root:
  - `results/benchmark/20260426T200455Z_line_art_irl_11_v2_benchmark/`
- Regression-only out-dir check:
  - `results/tmp_regression_contract_check_20260426T2012/`
- Benchmark summary files:
  - `benchmark_summary.json`
  - `benchmark_summary.csv`
  - `benchmark_summary.md`

Known remaining issues:
- Historical/archive/deprecated docs still contain legacy `assets/input_source_image.png` references; runtime entry paths now comply with the source-image contract.
- Benchmark quality remains non-uniform on one full benchmark child run (`420x311_seed22`, unresolved via `needs_sa_or_adaptive_rerun`), which is a model-quality issue and not a contract-interface break.

Final reviewer:
- Codex (GPT-5)

Ready for commit:
- yes (pending user review/acceptance of quality outcomes)
```

