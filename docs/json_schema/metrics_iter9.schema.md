# JSON Output Schema Specification: `metrics_iter9_<board>.json`

## Artifact name

`metrics_iter9_<board>.json`

Example:

```text
metrics_iter9_300x942.json
```

## Output filename/path pattern

Primary Iter9 single-run path:

```text
results/iter9/<run_id>/metrics_iter9_<board_width>x<board_height>.json
```

Iter9 image-sweep child path:

```text
<out_root>/<image_identity>_<board_width>x<board_height>_seed<seed>/metrics_iter9_<board_width>x<board_height>.json
```

## Purpose

Main structured execution-result document for an Iter9 run. It combines flat run metrics, source-image provenance, configuration, solver/repair summaries, visual quality metrics, artifact inventory, validation gates, environment details, warnings, and a short LLM-review summary.

## Producing component

| Role | Component |
|---|---|
| Filename construction | `run_iter9.py::run_iter9_single(...)` |
| Route artifact metadata used by metrics links | `run_iter9.py::run_iter9_single(...)` |
| Flat metrics dictionary | `run_iter9.py::run_iter9_single(...)` |
| Nested metrics sections | `run_iter9.py::run_iter9_single(...)` |
| Final document assembly | `run_iter9.py::build_metrics_document(...)` |
| JSON writer | `run_iter9.py::_atomic_save_json(...)` |

## Generation conditions

The file is written near the end of a successful `run_iter9_single(...)` execution, after:

1. Source image validation.
2. Board sizing.
3. Image loading and target preprocessing.
4. Corridor construction.
5. Coarse/fine/refine simulated annealing.
6. Solver run.
7. Phase 1 repair.
8. Late-stage routing.
9. Route artifact writing.
10. Final PNG and overlay rendering.
11. Grid `.npy` writing.

If the run fails before the final metrics write step, this metrics artifact is not written.

## Top-level JSON structure

The top-level object contains:

1. Flat metrics fields.
2. Nested provenance/configuration/result sections inserted by `build_metrics_document(...)`.
3. Optional `batch_context` only for successful Iter9 image-sweep child runs.

```json
{
  "label": "300x942",
  "board": "300x942",
  "cells": 282600,
  "loss_per_cell": 1.52,
  "mean_abs_error": 0.91,
  "hi_err": 1.1,
  "true_bg_err": 0.2,
  "trans_bg_err": 0.8,
  "bg_err": 0.3,
  "pct_within_1": 76.4,
  "pct_within_2": 91.2,
  "mine_density": 0.22,
  "corridor_pct": 4.8,
  "coverage": 1.0,
  "solvable": true,
  "mine_accuracy": 1.0,
  "n_unknown": 0,
  "repair_reason": "phase1=converged+route=already_solved",
  "total_time_s": 123.45,
  "seed": 42,
  "iter": 9,
  "schema_version": "metrics.v2.source_image_runtime_contract",
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
  "source_image_validation": {}
}
```

## Required top-level flat fields

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `label` | string | Yes | No | Board label: `<board_width>x<board_height>`. |
| `board` | string | Yes | No | Same board label as `label`. |
| `cells` | integer | Yes | No | `board_width * board_height`. |
| `loss_per_cell` | number | Yes | No | Variance of final absolute error array. |
| `mean_abs_error` | number | Yes | No | Mean absolute difference between final neighbor counts and target field. |
| `hi_err` | number | Yes | No | Mean absolute error in high-target region. Falls back to `0.0` if mask empty. |
| `true_bg_err` | number | Yes | No | Mean absolute error in true-background region. Falls back to `0.0` if mask empty. |
| `trans_bg_err` | number | Yes | No | Mean absolute error in transition-background region. Falls back to `0.0` if mask empty. |
| `bg_err` | number | Yes | No | Mean absolute error in all background cells. Falls back to `0.0` if mask empty. |
| `pct_within_1` | number | Yes | No | Percentage of cells with absolute error `<= 1.0`. |
| `pct_within_2` | number | Yes | No | Percentage of cells with absolute error `<= 2.0`. |
| `mine_density` | number | Yes | No | Fraction of grid cells containing mines. |
| `corridor_pct` | number | Yes | No | Percentage of cells reserved as mine-free corridors. |
| `coverage` | number | Yes | No | Solver coverage ratio after final route. |
| `solvable` | boolean | Yes | No | Final solver solvability flag. |
| `mine_accuracy` | number | Yes | No | Final solver mine-flag accuracy. |
| `n_unknown` | integer | Yes | No | Final unknown-cell count. |
| `repair_reason` | string | Yes | No | Combined Phase1 stop reason and selected route. |
| `total_time_s` | number | Yes | No | Total wall-clock run time in seconds. |
| `seed` | integer | Yes | No | Random seed supplied to Iter9. |
| `iter` | integer | Yes | No | Fixed value `9` for Iter9. |
| `bp_true` | number | Yes | No | True-background weight parameter. |
| `bp_trans` | number | Yes | No | Transition-background weight parameter. |
| `hi_boost` | number | Yes | No | High-target boost parameter. |
| `uf_factor` | number | Yes | No | Underfill factor. |
| `seal_thr` | number | Yes | No | Sealing-prevention density threshold. |
| `seal_str` | number | Yes | No | Sealing-prevention strength. |
| `pw_knee` | number | Yes | No | Piecewise target compression knee. |
| `pw_T_max` | number | Yes | No | Piecewise target compression maximum. |
| `sat_risk` | integer | Yes | No | Count of saturation-risk cells. |
| `preprocessing` | string enum | Yes | No | Current value: `piecewise_T_compression`. |
| `phase2` | string enum | Yes | No | Current value: `full_cluster_repair`. |
| `source_width` | integer | Yes | No | Source image width in pixels. |
| `source_height` | integer | Yes | No | Source image height in pixels. |
| `source_ratio` | number | Yes | No | Source image aspect ratio. |
| `board_ratio` | number | Yes | No | Generated board aspect ratio. |
| `aspect_ratio_relative_error` | number | Yes | No | Relative aspect-ratio error. |
| `gate_aspect_ratio_within_0_5pct` | boolean | Yes | No | Board/source aspect-ratio validation gate. |
| `repair_route_selected` | string enum | Yes | No | Selected late-stage route. |
| `repair_route_result` | string enum | Yes | No | Selected route result. |
| `dominant_failure_class` | string | Yes | Yes | From `failure_taxonomy`. Nullable only if taxonomy key missing unexpectedly. |
| `sealed_cluster_count` | integer | Yes | Yes | From `failure_taxonomy`. Nullable only if taxonomy key missing unexpectedly. |
| `sealed_single_mesa_count` | integer | Yes | Yes | From `failure_taxonomy`. Nullable only if taxonomy key missing unexpectedly. |
| `sealed_multi_cell_cluster_count` | integer | Yes | Yes | From `failure_taxonomy`. Nullable only if taxonomy key missing unexpectedly. |
| `phase2_fixes` | integer | Yes | No | Length of `route.phase2_log`. |
| `last100_fixes` | integer | Yes | No | Length of `route.last100_log`. Note this is log-entry count, not necessarily accepted-fix count. |
| `visual_delta` | number | Yes | Yes | From route visual summary; may be `null` if no summary field exists. |
| `failure_taxonomy_path` | string | Yes | No | Path to `failure_taxonomy.json`. |
| `repair_route_decision_path` | string | Yes | No | Path to `repair_route_decision.json`. |
| `visual_delta_summary_path` | string | Yes | No | Path to `visual_delta_summary.json`. |
| `repair_overlay_path` | string | Yes | No | Path to technical repair overlay PNG. |

## Required nested sections

The following fields are always inserted by `build_metrics_document(...)`.

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `schema_version` | string | Yes | No | Current value: `metrics.v2.source_image_runtime_contract`. |
| `run_identity` | object | Yes | No | Identity of this run. |
| `run_timing` | object | Yes | No | Start, finish, and duration. |
| `project_identity` | object | Yes | No | Project root and Git metadata. |
| `command_invocation` | object | Yes | No | Runtime entry point and CLI args. |
| `source_image` | object | Yes | No | Source-image provenance from `SourceImageConfig.to_metrics_dict()`. |
| `source_image_analysis` | object | Yes | No | Direct image analysis summary. |
| `effective_config` | object | Yes | No | Effective runtime config. |
| `board_sizing` | object | Yes | No | Board sizing output from `derive_board_from_width(...)`. |
| `preprocessing_config` | object | Yes | No | Image preprocessing settings. |
| `target_field_stats` | object | Yes | No | Target-field statistics. |
| `weight_config` | object | Yes | No | Weight-generation settings. |
| `corridor_config` | object | Yes | No | Corridor-generation settings. |
| `sa_config` | object | Yes | No | Simulated annealing schedule. |
| `repair_config` | object | Yes | No | Repair/routing budgets and solver trial settings. |
| `solver_summary` | object | Yes | No | Solver summaries after major stages. |
| `repair_route_summary` | object | Yes | No | Compact route summary. |
| `visual_quality_summary` | object | Yes | No | Before/after repair visual quality metrics. |
| `runtime_phase_timing_s` | object | Yes | No | Phase timing in seconds. |
| `environment` | object | Yes | No | Runtime environment package/platform summary. |
| `artifact_inventory` | object | Yes | No | Paths to all run artifacts. |
| `validation_gates` | object | Yes | No | Boolean validation gates. |
| `warnings_and_exceptions` | array of objects | Yes | No | Validation/runtime warnings copied from image validation. |
| `llm_review_summary` | object | Yes | No | Human-readable summary and recommended artifacts to open. |
| `source_image_validation` | object | Yes | No | Detailed payload from `verify_source_image(..., return_details=True)`. |

## Optional top-level fields

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `batch_context` | object | No | No | Present only for successful Iter9 image-sweep child runs. Omitted for normal single-image runs. |

## Nested object definitions

### `run_identity`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `run_id` | string | Yes | No | Generated as `<UTC>_<image_stem>_<board_w>w_seed<seed>[_tag]`. |
| `entry_point` | string enum | Yes | No | `run_iter9.py`. |
| `output_dir` | string | Yes | No | Relative or absolute output directory path. |
| `board_width` | integer | Yes | No | Board width. |
| `board_height` | integer | Yes | No | Board height derived from source aspect ratio. |
| `seed` | integer | Yes | No | Random seed. |

### `run_timing`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `started_at_utc` | string | Yes | No | UTC timestamp. |
| `finished_at_utc` | string | Yes | No | UTC timestamp. |
| `duration_wall_s` | number | Yes | No | Total wall-clock duration. |

### `project_identity`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `project_root` | string | Yes | No | Project root path. |
| `project_root_name` | string | Yes | No | Project directory name. |
| `git_commit` | string | Yes | Yes | Current Git commit, or `null` if unavailable. |
| `git_branch` | string | Yes | Yes | Current Git branch, or `null` if unavailable. |
| `git_dirty` | boolean | Yes | No | Whether `git status --porcelain` returned content. |

### `command_invocation`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `entry_point` | string enum | Yes | No | `run_iter9.py`. |
| `argv` | array of strings | Yes | No | Runtime argument vector with `run_iter9.py` prepended. |

### `source_image`

`source_image` is returned by `SourceImageConfig.to_metrics_dict()`. The supplied snapshot references `source_config.py` but does not include that file, so this object is documented from visible attribute usage and repository contract notes.

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `command_arg` | string | Inferred yes | No | Original CLI image argument. |
| `project_relative_path` | string | Inferred yes | Yes | Path relative to project root, or `null` for outside-project images. |
| `absolute_path` | string | Inferred yes | No | Absolute source image path. |
| `name` | string | Inferred yes | No | Image filename. |
| `stem` | string | Inferred yes | No | Image filename stem. |
| `sha256` | string | Inferred yes | No | Source image SHA-256. |
| `size_bytes` | integer | Inferred yes | No | Source image file size in bytes. |
| `allow_noncanonical` | boolean | Inferred yes | No | Whether noncanonical image use was allowed. |
| `manifest_path` | string | Inferred yes | Yes | Manifest path or `null`. |

### `source_image_analysis`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `width_px` | integer | Yes | No | Pixel width. |
| `height_px` | integer | Yes | No | Pixel height. |
| `aspect_ratio` | number | Yes | No | `width_px / height_px`. |
| `mode` | string | Yes | No | PIL image mode. |
| `has_alpha` | boolean | Yes | No | Whether image mode contains alpha channel. |
| `mean_luma` | number | Yes | No | Mean luma value. |
| `std_luma` | number | Yes | No | Standard deviation of luma. |

### `effective_config`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `board_width` | integer | Yes | No | Effective board width. |
| `board_height` | integer | Yes | No | Effective board height. |
| `seed` | integer | Yes | No | Effective seed. |
| `density` | number | Yes | No | Initial mine density. |
| `border` | integer | Yes | No | Border/corridor safety margin. |
| `invert` | boolean | Yes | No | Image inversion flag. |
| `piecewise_compression_enabled` | boolean | Yes | No | Whether piecewise target compression is enabled. |
| `pw_knee` | number | Yes | No | Piecewise compression knee. |
| `pw_t_max` | number | Yes | No | Piecewise compression max. |
| `out_dir` | string | Yes | No | Output directory path. |

### `board_sizing`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `source_width` | integer | Yes | No | Source image width. |
| `source_height` | integer | Yes | No | Source image height. |
| `source_ratio` | number | Yes | No | Source aspect ratio. |
| `board_width` | integer | Yes | No | Requested/effective board width. |
| `board_height` | integer | Yes | No | Derived board height. |
| `board_ratio` | number | Yes | No | Board aspect ratio. |
| `aspect_ratio_relative_error` | number | Yes | No | Relative aspect-ratio error. |
| `aspect_ratio_tolerance` | number | Yes | No | Allowed relative error. |
| `gate_aspect_ratio_within_tolerance` | boolean | Yes | No | Aspect-ratio gate result. |
| `width_policy_min` | integer | Yes | No | Minimum accepted board width. |

### `preprocessing_config`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `loader` | string enum | Yes | No | `load_image_smart`. |
| `invert` | boolean | Yes | No | Image inversion flag. |
| `piecewise_compression_enabled` | boolean | Yes | No | Whether target compression is enabled. |
| `pw_knee` | number | Yes | No | Piecewise compression knee. |
| `pw_t_max` | number | Yes | No | Piecewise compression max. |

### `target_field_stats`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `min` | number | Yes | No | Minimum target value. |
| `max` | number | Yes | No | Maximum target value. |
| `mean` | number | Yes | No | Mean target value. |
| `std` | number | Yes | No | Standard deviation. |
| `pct_t_ge_6` | number | Yes | No | Percent of target values `>= 6.0`. |
| `pct_t_ge_7` | number | Yes | No | Percent of target values `>= 7.0`. |
| `pct_t_le_1` | number | Yes | No | Percent of target values `<= 1.0`. |

### `weight_config`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `method` | string enum | Yes | No | `compute_zone_aware_weights`. |
| `bp_true` | number | Yes | No | True-background penalty/weight. |
| `bp_trans` | number | Yes | No | Transition-background weight. |
| `hi_boost` | number | Yes | No | High-target boost. |
| `hi_threshold` | number | Yes | No | High-target threshold. |
| `underfill_factor` | number | Yes | No | Underfill refinement factor. |

### `corridor_config`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `method` | string enum | Yes | No | `build_adaptive_corridors`. |
| `border` | integer | Yes | No | Border size. |
| `corridor_pct` | number | Yes | No | Percent of cells reserved as corridors. |

### `sa_config`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `density` | number | Yes | No | Initial mine density. |
| `coarse_iters` | integer | Yes | No | Coarse SA iterations. |
| `fine_iters` | integer | Yes | No | Fine SA iterations. |
| `refine_iters` | array of integers | Yes | No | Iterations for refinement passes. |
| `T_coarse` | number | Yes | No | Coarse starting temperature. |
| `T_fine` | number | Yes | No | Fine starting temperature. |
| `T_refine` | array of numbers | Yes | No | Refinement temperatures. |
| `T_min` | number | Yes | No | Minimum temperature. |
| `alpha_coarse` | number | Yes | No | Coarse cooling factor. |
| `alpha_fine` | number | Yes | No | Fine cooling factor. |
| `alpha_refine` | array of numbers | Yes | No | Refinement cooling factors. |

### `repair_config`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `phase1_budget_s` | number | Yes | No | Actual Phase1 time budget, capped at 120 seconds. |
| `phase2_budget_s` | number | Yes | No | Phase2 route budget. |
| `last100_budget_s` | number | Yes | No | Last100 route budget. |
| `last100_unknown_threshold` | integer | Yes | No | Unknown-count threshold for Last100 route. |
| `solve_max_rounds` | integer | Yes | No | Full solver max rounds. |
| `trial_max_rounds` | integer | Yes | No | Trial solver max rounds. |

### `solver_summary`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `post_sa` | object | Yes | No | Solver state after SA. |
| `post_phase1` | object | Yes | No | Solver state after Phase1 repair. |
| `post_routing` | object | Yes | No | Solver state after late-stage route. |

Each `solver_summary` child object has:

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `coverage` | number | Yes | No | Solver coverage ratio. |
| `n_unknown` | integer | Yes | No | Unknown-cell count. |
| `solvable` | boolean | Yes | No | Solver solvability flag. |

### `repair_route_summary`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `selected_route` | string enum | Yes | No | Same as `repair_route_selected`. |
| `route_result` | string enum | Yes | No | Same as `repair_route_result`. |
| `dominant_failure_class` | string | Yes | Yes | Dominant failure class. |
| `sealed_cluster_count` | integer | Yes | No | Sealed-cluster count coerced to integer fallback `0`. |
| `phase2_fixes` | integer | Yes | No | Length of Phase2 log. |
| `last100_fixes` | integer | Yes | No | Length of Last100 log. |
| `sa_rerun_invoked` | boolean | Yes | No | Current code emits `false`. |

### `visual_quality_summary`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `mean_abs_error_before_repair` | number | Yes | No | MAE before late-stage route. |
| `mean_abs_error_after_repair` | number | Yes | No | MAE after late-stage route. |
| `visual_delta` | number | Yes | No | Route visual delta, with fallback to `after - before`. |
| `pct_within_1` | number | Yes | No | Percent cells within absolute error `<= 1.0`. |
| `pct_within_2` | number | Yes | No | Percent cells within absolute error `<= 2.0`. |
| `hi_err` | number | Yes | No | High-target error. |
| `true_bg_err` | number | Yes | No | True-background error. |

### `runtime_phase_timing_s`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `warmup` | number | Yes | No | Kernel/solver warmup seconds. |
| `image_load_and_preprocess` | number | Yes | No | Image loading and target preprocessing seconds. |
| `corridor_build` | number | Yes | No | Corridor build seconds. |
| `coarse_sa` | number | Yes | No | Coarse simulated annealing seconds. |
| `fine_sa` | number | Yes | No | Fine simulated annealing seconds. |
| `refine_sa_total` | number | Yes | No | All refinement passes total seconds. |
| `phase1_repair` | number | Yes | No | Phase1 repair seconds. |
| `late_stage_routing` | number | Yes | No | Route selection / late-stage repair seconds. |
| `render_and_write` | number | Yes | No | Report rendering and output write seconds. |
| `total` | number | Yes | No | Total run duration. |

### `environment`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `os` | string | Yes | No | Platform descriptor. |
| `python_version` | string | Yes | No | Python version. |
| `python_bits` | integer | Yes | No | 64 or 32. |
| `cpu_count` | integer | Yes | Yes | CPU count; Python can return `None`. |
| `numba_num_threads` | null | Yes | Yes | Currently always `null` in this code. |
| `numpy_version` | string | Yes | No | NumPy version. |
| `scipy_version` | string | Yes | No | SciPy version. |
| `pillow_version` | string | Yes | No | Pillow version. |
| `matplotlib_version` | string | Yes | No | Matplotlib version. |

### `artifact_inventory`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `metrics_json` | string | Yes | No | This metrics JSON path. |
| `grid_npy` | string | Yes | No | Final grid `.npy` path. |
| `grid_latest_npy` | string | Yes | No | Latest grid `.npy` path. |
| `visual_png` | string | Yes | No | Technical final PNG. |
| `visual_explained_png` | string | Yes | No | Explained final PNG. |
| `repair_overlay_png` | string | Yes | No | Technical repair overlay PNG. |
| `repair_overlay_explained_png` | string | Yes | No | Explained repair overlay PNG. |
| `failure_taxonomy_json` | string | Yes | No | Failure taxonomy JSON path. |
| `repair_route_decision_json` | string | Yes | No | Repair route decision JSON path. |
| `visual_delta_summary_json` | string | Yes | No | Visual delta summary JSON path. |

### `validation_gates`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `board_valid` | boolean | Yes | No | `assert_board_valid(...)` passed. |
| `forbidden_cells_mine_free` | boolean | Yes | No | Final grid has no mines in forbidden cells. |
| `aspect_ratio_within_tolerance` | boolean | Yes | No | Board/source ratio gate. |
| `n_unknown_zero` | boolean | Yes | No | Whether final unknown count is zero. |
| `coverage_at_least_9999` | boolean | Yes | No | Whether final coverage is at least `0.9999`. |
| `solvable_true` | boolean | Yes | No | Whether final solver result is solvable. |
| `source_image_validated` | boolean | Yes | No | Source image validation `ok`. |
| `canonical_image_match` | boolean | Yes | Yes | Source image canonical-match flag; may be `null` depending on validation payload. |
| `noncanonical_allowed` | boolean | Yes | No | Whether noncanonical image input was allowed. |

### `llm_review_summary`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `one_sentence_result` | string | Yes | No | Short result sentence. |
| `main_success` | string | Yes | No | Human-readable success summary. |
| `main_risk` | string | Yes | No | Warning-derived risk summary or default no-risk text. |
| `best_artifact_to_open_first` | string | Yes | Yes | Usually explained final visual path. |
| `best_artifact_to_open_second` | string | Yes | Yes | Usually technical final visual path. |
| `best_repair_artifact_to_open_first` | string | Yes | Yes | Usually explained repair overlay path. |
| `best_repair_artifact_to_open_second` | string | Yes | Yes | Usually technical repair overlay path. |
| `best_metric_to_check_first` | string | Yes | No | Current value: `n_unknown`. |
| `next_recommended_check` | string | Yes | No | Human-readable suggested next review step. |

### `source_image_validation`

`source_image_validation` is the structured image-validation result embedded into the metrics document.

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `ok` | boolean | Yes | No | Overall validation success flag. |
| `path` | string | Yes | No | Original image path argument supplied for validation. |
| `absolute_path` | string | Yes | No | Resolved absolute image path. |
| `manifest_path` | string | Yes | Yes | Manifest path used for validation, or `null` when no manifest was used. |
| `canonical_match` | boolean | Yes | Yes | Whether computed image stats match the expected manifest values; `null` when no expected manifest exists. |
| `noncanonical_allowed` | boolean | Yes | No | Whether noncanonical source-image use was allowed. |
| `validation_mode` | string enum | Yes | No | Validation branch used. See enum below. |
| `warnings` | array of warning objects | Yes | No | Structured warnings emitted by validation. Empty when no warnings were emitted. |
| `computed` | object | Yes | No | File and pixel statistics computed from the image. May be `{}` when the path is missing or not a file. |
| `expected` | object | Yes | Yes | Expected file and pixel statistics from a manifest, or `null` when no manifest was used. |

#### `source_image_validation.validation_mode`

```text
default_manifest
explicit_manifest
noncanonical_allowed
```

#### `source_image_validation.warnings[]`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `code` | string enum | Yes | No | Warning code. Known values are listed below. |
| `severity` | string enum | Yes | No | Warning severity. Known values are `info` and `warning`. |
| `message` | string | Yes | No | Human-readable warning message. |

Known `warnings[].code` values:

```text
DEFAULT_MANIFEST_USED
MANIFEST_NOT_SUPPLIED
NONCANONICAL_SOURCE_ALLOWED
```

#### `source_image_validation.computed`

| Field | Type | Required when object is populated | Nullable | Description |
|---|---:|---:|---:|---|
| `file_size` | integer | Yes | No | Image file size in bytes. |
| `file_sha256` | string | Yes | No | SHA-256 hash of raw file bytes. |
| `pixel_sha256` | string | Yes | No | SHA-256 hash of the loaded pixel buffer. |
| `pixel_shape` | array of integers | Yes | No | Loaded image array shape. Common forms are `[height, width]` or `[height, width, channels]`. |
| `pixel_dtype` | string | Yes | No | Loaded NumPy dtype string, usually `uint8`. |
| `pixel_mean` | number | Yes | No | Mean pixel value. |
| `pixel_std` | number | Yes | No | Pixel standard deviation. |
| `pixel_min` | integer | Yes | No | Minimum pixel value. |
| `pixel_max` | integer | Yes | No | Maximum pixel value. |

#### `source_image_validation.expected`

When non-null, `expected` has the same normalized fields as `computed` except that it is loaded from the manifest rather than computed from the current file.

| Field | Type | Required when object exists | Nullable | Description |
|---|---:|---:|---:|---|
| `file_size` | integer | Yes | No | Expected file size in bytes. |
| `file_sha256` | string | Yes | No | Expected SHA-256 hash of raw file bytes. |
| `pixel_sha256` | string | Yes | No | Expected SHA-256 hash of the pixel buffer. |
| `pixel_shape` | array of integers | Yes | No | Expected image array shape. |
| `pixel_dtype` | string | Yes | No | Expected NumPy dtype string. |
| `pixel_mean` | number | Yes | No | Expected mean pixel value. |
| `pixel_std` | number | Yes | No | Expected pixel standard deviation. |
| `pixel_min` | integer | Yes | No | Expected minimum pixel value. |
| `pixel_max` | integer | Yes | No | Expected maximum pixel value. |

### `warnings_and_exceptions[]`

This array is populated from `source_image_validation.warnings`.

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `code` | string | Yes | No | Structured warning code. |
| `severity` | string | Yes | No | Warning severity. |
| `message` | string | Yes | No | Human-readable warning message used by `llm_review_summary.main_risk` when present. |

### `batch_context` optional object

Present only in Iter9 image-sweep child metrics.

| Field | Type | Required when object exists | Nullable | Description |
|---|---:|---:|---:|---|
| `schema_version` | string | Yes | No | `iter9_image_sweep_context.v1`. |
| `batch_mode` | string enum | Yes | No | `iter9_image_sweep`. |
| `batch_id` | string | Yes | No | Sweep batch id. |
| `batch_index` | integer | Yes | No | One-based image index within sweep. |
| `batch_total` | integer | Yes | No | Total images discovered. |
| `images_discovered` | integer | Yes | No | Total images discovered. |
| `image_dir` | string | Yes | No | Source image directory. |
| `image_glob` | string | Yes | No | Glob used to select images. |
| `recursive` | boolean | Yes | No | Whether recursive discovery was enabled. |
| `batch_out_root` | string | Yes | No | Sweep output root. |
| `child_run_dir` | string | Yes | No | This child output directory. |
| `continue_on_error` | boolean | Yes | No | Sweep continue-on-error flag. |
| `skip_existing` | boolean | Yes | No | Sweep skip-existing flag. |
| `max_images` | integer or null | Yes | Yes | Image limit if supplied, otherwise `null`. |
| `batch_warmup_s` | number | Yes | No | Shared sweep warmup seconds. |
| `child_warmup_s` | number | Yes | No | Child warmup seconds, currently `0.0` in sweep reuse mode. |

## Allowed values / enums

### `preprocessing`

```text
piecewise_T_compression
```

### `phase2`

```text
full_cluster_repair
```

### `repair_route_selected` / `repair_route_summary.selected_route`

```text
already_solved
phase2_full_repair
last100_repair
needs_sa_or_adaptive_rerun
```

### `repair_route_result` / `repair_route_summary.route_result`

```text
solved
unresolved_after_repair
```

### `dominant_failure_class`

```text
unclassified_missing_solver_state
no_unknowns
sealed_multi_cell_cluster
sealed_single_mesa
frontier_adjacent_unknown
ordinary_ambiguous_unknown
```

## Nullability rules

- `visual_delta` at the flat top level can be `null` because it is pulled directly from `route.visual_delta_summary.get("visual_delta")`.
- `visual_quality_summary.visual_delta` is non-null because the code supplies a fallback calculation.
- Git fields `git_commit` and `git_branch` may be `null` if Git commands fail.
- `environment.cpu_count` may be `null` if Python returns `None`.
- `environment.numba_num_threads` is explicitly `null` in current code.
- `source_image.project_relative_path`, `source_image.manifest_path`, and `source_image_validation.canonical_match` may be `null` depending on external modules and source path context.
- `batch_context.max_images` may be `null`.

## Example JSON output

```json
{
  "label": "300x942",
  "board": "300x942",
  "cells": 282600,
  "loss_per_cell": 1.52,
  "mean_abs_error": 0.91,
  "hi_err": 1.10,
  "true_bg_err": 0.20,
  "trans_bg_err": 0.80,
  "bg_err": 0.30,
  "pct_within_1": 76.4,
  "pct_within_2": 91.2,
  "mine_density": 0.2201,
  "corridor_pct": 4.8,
  "coverage": 1.0,
  "solvable": true,
  "mine_accuracy": 1.0,
  "n_unknown": 0,
  "repair_reason": "phase1=converged+route=already_solved",
  "total_time_s": 123.45,
  "seed": 42,
  "iter": 9,
  "bp_true": 8.0,
  "bp_trans": 1.0,
  "hi_boost": 18.0,
  "uf_factor": 1.8,
  "seal_thr": 0.6,
  "seal_str": 20.0,
  "pw_knee": 4.0,
  "pw_T_max": 6.0,
  "sat_risk": 12,
  "preprocessing": "piecewise_T_compression",
  "phase2": "full_cluster_repair",
  "source_width": 900,
  "source_height": 2826,
  "source_ratio": 0.31847,
  "board_ratio": 0.31847,
  "aspect_ratio_relative_error": 0.00001,
  "gate_aspect_ratio_within_0_5pct": true,
  "repair_route_selected": "already_solved",
  "repair_route_result": "solved",
  "dominant_failure_class": "no_unknowns",
  "sealed_cluster_count": 0,
  "sealed_single_mesa_count": 0,
  "sealed_multi_cell_cluster_count": 0,
  "phase2_fixes": 0,
  "last100_fixes": 0,
  "visual_delta": null,
  "failure_taxonomy_path": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/failure_taxonomy.json",
  "repair_route_decision_path": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/repair_route_decision.json",
  "visual_delta_summary_path": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/visual_delta_summary.json",
  "repair_overlay_path": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/repair_overlay_300x942.png",
  "schema_version": "metrics.v2.source_image_runtime_contract",
  "run_identity": {
    "run_id": "20260429T204700Z_line_art_irl_11_v2_300w_seed42",
    "entry_point": "run_iter9.py",
    "output_dir": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42",
    "board_width": 300,
    "board_height": 942,
    "seed": 42
  },
  "run_timing": {
    "started_at_utc": "2026-04-29T20:47:00.000Z",
    "finished_at_utc": "2026-04-29T20:49:03.450Z",
    "duration_wall_s": 123.45
  },
  "project_identity": {
    "project_root": "/repo/Minesweeper",
    "project_root_name": "Minesweeper",
    "git_commit": null,
    "git_branch": null,
    "git_dirty": false
  },
  "command_invocation": {
    "entry_point": "run_iter9.py",
    "argv": ["run_iter9.py", "--image", "assets/line_art_irl_11_v2.png", "--allow-noncanonical"]
  },
  "source_image": {
    "command_arg": "assets/line_art_irl_11_v2.png",
    "project_relative_path": "assets/line_art_irl_11_v2.png",
    "absolute_path": "/repo/Minesweeper/assets/line_art_irl_11_v2.png",
    "name": "line_art_irl_11_v2.png",
    "stem": "line_art_irl_11_v2",
    "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "size_bytes": 123456,
    "allow_noncanonical": true,
    "manifest_path": null
  },
  "source_image_analysis": {
    "width_px": 900,
    "height_px": 2826,
    "aspect_ratio": 0.31847,
    "mode": "RGB",
    "has_alpha": false,
    "mean_luma": 241.3,
    "std_luma": 42.1
  },
  "effective_config": {
    "board_width": 300,
    "board_height": 942,
    "seed": 42,
    "density": 0.22,
    "border": 3,
    "invert": true,
    "piecewise_compression_enabled": true,
    "pw_knee": 4.0,
    "pw_t_max": 6.0,
    "out_dir": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42"
  },
  "board_sizing": {
    "source_width": 900,
    "source_height": 2826,
    "source_ratio": 0.31847,
    "board_width": 300,
    "board_height": 942,
    "board_ratio": 0.31847,
    "aspect_ratio_relative_error": 0.00001,
    "aspect_ratio_tolerance": 0.005,
    "gate_aspect_ratio_within_tolerance": true,
    "width_policy_min": 50
  },
  "preprocessing_config": {
    "loader": "load_image_smart",
    "invert": true,
    "piecewise_compression_enabled": true,
    "pw_knee": 4.0,
    "pw_t_max": 6.0
  },
  "target_field_stats": {
    "min": 0.0,
    "max": 8.0,
    "mean": 1.2,
    "std": 1.8,
    "pct_t_ge_6": 2.5,
    "pct_t_ge_7": 1.0,
    "pct_t_le_1": 71.0
  },
  "weight_config": {
    "method": "compute_zone_aware_weights",
    "bp_true": 8.0,
    "bp_trans": 1.0,
    "hi_boost": 18.0,
    "hi_threshold": 3.0,
    "underfill_factor": 1.8
  },
  "corridor_config": {
    "method": "build_adaptive_corridors",
    "border": 3,
    "corridor_pct": 4.8
  },
  "sa_config": {
    "density": 0.22,
    "coarse_iters": 2000000,
    "fine_iters": 8000000,
    "refine_iters": [2000000, 2000000, 4000000],
    "T_coarse": 12.5,
    "T_fine": 3.5,
    "T_refine": [2.25, 1.7, 1.4],
    "T_min": 0.001,
    "alpha_coarse": 0.99998,
    "alpha_fine": 0.999996,
    "alpha_refine": [0.999997, 0.999997, 0.999998]
  },
  "repair_config": {
    "phase1_budget_s": 120.0,
    "phase2_budget_s": 360.0,
    "last100_budget_s": 300.0,
    "last100_unknown_threshold": 100,
    "solve_max_rounds": 300,
    "trial_max_rounds": 60
  },
  "solver_summary": {
    "post_sa": {"coverage": 0.93, "n_unknown": 1320, "solvable": false},
    "post_phase1": {"coverage": 1.0, "n_unknown": 0, "solvable": true},
    "post_routing": {"coverage": 1.0, "n_unknown": 0, "solvable": true}
  },
  "repair_route_summary": {
    "selected_route": "already_solved",
    "route_result": "solved",
    "dominant_failure_class": "no_unknowns",
    "sealed_cluster_count": 0,
    "phase2_fixes": 0,
    "last100_fixes": 0,
    "sa_rerun_invoked": false
  },
  "visual_quality_summary": {
    "mean_abs_error_before_repair": 0.91,
    "mean_abs_error_after_repair": 0.91,
    "visual_delta": 0.0,
    "pct_within_1": 76.4,
    "pct_within_2": 91.2,
    "hi_err": 1.1,
    "true_bg_err": 0.2
  },
  "runtime_phase_timing_s": {
    "warmup": 1.1,
    "image_load_and_preprocess": 0.4,
    "corridor_build": 0.7,
    "coarse_sa": 15.0,
    "fine_sa": 52.0,
    "refine_sa_total": 41.0,
    "phase1_repair": 9.0,
    "late_stage_routing": 0.1,
    "render_and_write": 4.1,
    "total": 123.45
  },
  "environment": {
    "os": "Windows-10-10.0.19045-SP0",
    "python_version": "3.11.8",
    "python_bits": 64,
    "cpu_count": 12,
    "numba_num_threads": null,
    "numpy_version": "1.26.4",
    "scipy_version": "1.12.0",
    "pillow_version": "10.2.0",
    "matplotlib_version": "3.8.2"
  },
  "artifact_inventory": {
    "metrics_json": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/metrics_iter9_300x942.json",
    "grid_npy": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/grid_iter9_300x942.npy",
    "grid_latest_npy": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/grid_iter9_latest.npy",
    "visual_png": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/iter9_300x942_FINAL.png",
    "visual_explained_png": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/iter9_300x942_FINAL_explained.png",
    "repair_overlay_png": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/repair_overlay_300x942.png",
    "repair_overlay_explained_png": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/repair_overlay_300x942_explained.png",
    "failure_taxonomy_json": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/failure_taxonomy.json",
    "repair_route_decision_json": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/repair_route_decision.json",
    "visual_delta_summary_json": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/visual_delta_summary.json"
  },
  "validation_gates": {
    "board_valid": true,
    "forbidden_cells_mine_free": true,
    "aspect_ratio_within_tolerance": true,
    "n_unknown_zero": true,
    "coverage_at_least_9999": true,
    "solvable_true": true,
    "source_image_validated": true,
    "canonical_image_match": false,
    "noncanonical_allowed": true
  },
  "warnings_and_exceptions": [],
  "llm_review_summary": {
    "one_sentence_result": "The run used assets/line_art_irl_11_v2.png at 300x942 with seed 42 and ended with n_unknown=0 through already_solved.",
    "main_success": "The routed repair pipeline completed and produced final artifacts.",
    "main_risk": "No critical risks detected.",
    "best_artifact_to_open_first": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/iter9_300x942_FINAL_explained.png",
    "best_artifact_to_open_second": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/iter9_300x942_FINAL.png",
    "best_repair_artifact_to_open_first": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/repair_overlay_300x942_explained.png",
    "best_repair_artifact_to_open_second": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/repair_overlay_300x942.png",
    "best_metric_to_check_first": "n_unknown",
    "next_recommended_check": "Start with the explained final visual, then use the technical reports for detailed audit."
  },
  "source_image_validation": {
    "ok": true,
    "canonical_match": false,
    "noncanonical_allowed": true,
    "warnings": []
  }
}
```

## Notes about schema stability or inferred assumptions

- `metrics_iter9_<board>.json` has the strongest schema surface but also the widest dependency surface because it embeds outputs from source configuration, image validation, solver, repair route, environment, and artifact inventory.
- `schema_version` is fixed in code as `metrics.v2.source_image_runtime_contract`.
- The `source_image` payload is partially inferred because `source_config.py` was not present in the supplied snapshot. The `source_image_validation` payload is documented from the supplied image-validation module.
- The code preserves flat legacy metrics while adding nested sections. Downstream consumers should prefer nested sections for new integrations and keep flat fields for backward compatibility.
- `last100_fixes` is named like a count of fixes but is implemented as `len(route.last100_log)`, which counts logged candidate attempts in the current code path.
