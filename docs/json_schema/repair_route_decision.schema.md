# JSON Output Schema Specification: `repair_route_decision.json`

## Artifact name

`repair_route_decision.json`

## Output filename/path pattern

Primary Iter9 path:

```text
results/iter9/<run_id>/repair_route_decision.json
```

Iter9 image-sweep child path:

```text
<out_root>/<image_identity>_<board_width>x<board_height>_seed<seed>/repair_route_decision.json
```

Normal benchmark child path:

```text
results/benchmark/<benchmark_run_id>/<board_width>x<board_height>_seed<seed>/repair_route_decision.json
```

## Purpose

Records the route selected by late-stage repair routing, including the solver unknown count before and after routing and which repair branch was invoked.

## Producing component

| Role | Component |
|---|---|
| Decision object builder | `pipeline.py::route_late_stage_failure(...)` |
| JSON file writer | `pipeline.py::write_repair_route_artifacts(...)` |
| Iter9 caller and metadata source | `run_iter9.py::run_iter9_single(...)` |
| Benchmark caller and metadata source | `run_benchmark.py::run_normal_child(...)` |

## Generation conditions

This artifact is written when a run reaches late-stage routing and calls `write_repair_route_artifacts(...)`.

It is written for already-solved boards, phase2 repair attempts, last100 repair attempts, and unresolved boards requiring a future SA/adaptive rerun.

## Top-level JSON structure

```json
{
  "solver_n_unknown_before": 0,
  "dominant_failure_class": "no_unknowns",
  "recommended_route": "none",
  "selected_route": "already_solved",
  "phase2_budget_s": 360.0,
  "last100_budget_s": 300.0,
  "phase2_full_repair_hit_time_budget": false,
  "last100_repair_hit_time_budget": false,
  "last100_invoked": false,
  "sa_rerun_invoked": false,
  "solver_n_unknown_after": 0,
  "route_result": "solved",
  "artifact_metadata": {
    "run_id": "20260429T204700Z_line_art_irl_11_v2_300w_seed42",
    "generated_at_utc": "2026-04-29T20:47:00.000Z",
    "source_image_project_relative_path": "assets/line_art_irl_11_v2.png",
    "source_image_sha256": "<sha256>",
    "metrics_path": "results/iter9/<run_id>/metrics_iter9_300x942.json",
    "phase1_repair_hit_time_budget": false,
    "phase2_full_repair_hit_time_budget": false,
    "last100_repair_hit_time_budget": false
  }
}
```

## Required fields

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `selected_route` | string enum | Yes | No | Route family actually invoked. Never `needs_sa_or_adaptive_rerun`. |
| `route_result` | string enum | Yes | No | Route outcome summary. |
| `route_outcome_detail` | string enum | Yes | No | Precise outcome; one of 11 permitted values. |
| `next_recommended_route` | string or null | Yes | Yes | `null` when solved; `"needs_sa_or_adaptive_rerun"` or `"last100_repair"` when unresolved. |
| `solver_n_unknown_before` | integer | Yes | No | Unknown-cell count passed into route selection. |
| `solver_n_unknown_after` | integer | Yes | No | Unknown-cell count after selected route attempt. |
| `dominant_failure_class` | string | Yes | Yes | Copied from `failure_taxonomy.dominant_failure_class`. |
| `recommended_route` | string | Yes | Yes | Copied from `failure_taxonomy.recommended_route`. |
| `phase2_budget_s` | number | Yes | No | Configured Phase2 budget in seconds. |
| `last100_budget_s` | number | Yes | No | Configured Last100 budget in seconds. |
| `phase2_full_repair_invoked` | boolean | Yes | No | Whether Phase2 full repair was invoked. |
| `phase2_full_repair_hit_time_budget` | boolean | Yes | No | Set by Phase2 when it reaches its `time_budget_s`; default `false` when not invoked. |
| `phase2_full_repair_n_fixed` | integer | Yes | No | Number of cells fixed by Phase2 (accepted move count). |
| `phase2_full_repair_accepted_move_count` | integer | Yes | No | Number of accepted Phase2 moves (equals `phase2_full_repair_n_fixed`). |
| `phase2_full_repair_changed_grid` | boolean | Yes | No | Whether Phase2 mutated the grid. |
| `phase2_full_repair_reduced_unknowns` | boolean | Yes | No | Whether Phase2 reduced the unknown count. |
| `phase2_full_repair_solved` | boolean | Yes | No | Whether Phase2 fully solved the board. |
| `phase2_solver_n_unknown_before` | integer or null | Yes | Yes | Unknown count before Phase2 ran; `null` if Phase2 not invoked. |
| `phase2_solver_n_unknown_after` | integer or null | Yes | Yes | Unknown count after Phase2 ran; `null` if Phase2 not invoked. |
| `last100_invoked` | boolean | Yes | No | Whether the Last100 repair branch was invoked. |
| `last100_repair_hit_time_budget` | boolean | Yes | No | Set by Last100 when it reaches its `budget_s`; default `false` when not invoked. |
| `last100_n_fixes` | integer | Yes | No | Number of cells fixed by Last100 (accepted move count). |
| `last100_accepted_move_count` | integer | Yes | No | Number of accepted Last100 moves (equals `last100_n_fixes`). |
| `last100_solver_n_unknown_before` | integer or null | Yes | Yes | Unknown count before Last100 ran; `null` if not invoked. |
| `last100_solver_n_unknown_after` | integer or null | Yes | Yes | Unknown count after Last100 ran; `null` if not invoked. |
| `last100_stop_reason` | string or null | Yes | Yes | Stop reason from Last100; `null` if not invoked. |
| `sa_rerun_invoked` | boolean | Yes | No | Reserved flag; currently always `false`. |

## Optional fields

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `artifact_metadata` | object | No | No | Injected by `write_repair_route_artifacts(...)` when caller passes metadata. |

## Allowed values / enums

### `selected_route`

`"needs_sa_or_adaptive_rerun"` is **not** a valid `selected_route` value. It is only valid in `next_recommended_route`.

```text
none
already_solved
phase2_full_repair
last100_repair
```

### `route_result`

```text
solved
unresolved_after_repair
unresolved_repair_error
```

### `route_outcome_detail`

```text
already_solved_before_routing
phase2_full_repair_solved
phase2_full_repair_partial_progress_unresolved
phase2_full_repair_no_op
phase2_full_repair_no_accepted_moves
last100_repair_solved
last100_repair_timeout_unresolved
last100_repair_partial_progress_unresolved
last100_repair_no_accepted_moves
no_late_stage_route_invoked
unresolved_repair_error
```

### `next_recommended_route`

```text
null                        (when route_result == "solved")
needs_sa_or_adaptive_rerun  (when unresolved and no further route available)
last100_repair              (when Phase2 unresolved and config.enable_last100 is True)
```

### `recommended_route`

```text
rerun_solver_full
none
phase2_full_repair
last100_or_standard_repair
manual_or_future_solver_analysis
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

### `last100_stop_reason`

Observed values from `repair.py::run_last100_repair(...)`:

```text
no_effect
timeout
solved
last100_not_applicable
no_unknown_components
no_accepted_move
```

## Route-specific field behavior

| Route | Trigger in current code | Field changes |
|---|---|---|
| `already_solved` | `sr.n_unknown == 0` before routing | `route_result = "solved"`; `solver_n_unknown_after` remains `0`; timeout booleans remain `false`; `last100_invoked = false`. |
| `phase2_full_repair` | `sealed_cluster_count > 0`, Phase2 enabled, and Phase2 fully solves the board | `route_result = "solved"`; `solver_n_unknown_after = 0`; `phase2_full_repair_hit_time_budget` is copied from Phase2; `last100_invoked = false`. |
| `last100_repair` | Last100 enabled and current unknown count is less than or equal to configured threshold after any Phase2 attempt | `last100_invoked = true`; `last100_stop_reason` added; timeout booleans are copied from their phases; `route_result` is `"solved"` if final unknown count is `0`, otherwise `"unresolved_after_repair"`. |
| `none` | No repair branch was invoked (Phase2 and Last100 both disabled or not triggered) | `selected_route = "none"`, `route_result = "unresolved_after_repair"`, `route_outcome_detail = "no_late_stage_route_invoked"`, `next_recommended_route = "needs_sa_or_adaptive_rerun"`. |

## Nested object definitions

### `artifact_metadata`

| Field | Type | Required when object exists | Nullable | Description |
|---|---:|---:|---:|---|
| `run_id` | string | Yes | No | Iter9 run id or benchmark child run id. |
| `generated_at_utc` | string | Yes | No | UTC timestamp in ISO-like `...Z` format. |
| `source_image_project_relative_path` | string | Yes | Yes | Source image path relative to project root. May be `null` for non-project paths. |
| `source_image_sha256` | string | Yes | No | SHA-256 hash of source image. |
| `metrics_path` | string | Yes | No | Relative or absolute path to the metrics JSON for the same run. |
| `phase1_repair_hit_time_budget` | boolean | No | No | Current Iter9 and benchmark metadata include the Phase1 repair timeout boolean. |
| `phase2_full_repair_hit_time_budget` | boolean | No | No | Current Iter9 and benchmark metadata include the Phase2 full repair timeout boolean. |
| `last100_repair_hit_time_budget` | boolean | No | No | Current Iter9 and benchmark metadata include the Last100 repair timeout boolean. |

## Nullability rules

- `dominant_failure_class` and `recommended_route` are assigned with `.get(...)`, so they are technically nullable if the taxonomy object is malformed. With the current `solver.py` taxonomy builder, both are always non-null strings.
- `artifact_metadata.source_image_project_relative_path` may be `null` for images outside the project root.
- `last100_stop_reason` is absent unless Last100 repair is invoked.

## Example JSON output

```json
{
  "solver_n_unknown_before": 14,
  "dominant_failure_class": "sealed_multi_cell_cluster",
  "recommended_route": "phase2_full_repair",
  "selected_route": "last100_repair",
  "phase2_budget_s": 360.0,
  "last100_budget_s": 300.0,
  "phase2_full_repair_hit_time_budget": false,
  "last100_repair_hit_time_budget": false,
  "last100_invoked": true,
  "sa_rerun_invoked": false,
  "solver_n_unknown_after": 2,
  "route_result": "unresolved_after_repair",
  "last100_stop_reason": "no_accepted_move",
  "artifact_metadata": {
    "run_id": "20260429T204700Z_line_art_irl_11_v2_300w_seed42",
    "generated_at_utc": "2026-04-29T20:47:00.000Z",
    "source_image_project_relative_path": "assets/line_art_irl_11_v2.png",
    "source_image_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "metrics_path": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/metrics_iter9_300x942.json",
    "phase1_repair_hit_time_budget": false,
    "phase2_full_repair_hit_time_budget": false,
    "last100_repair_hit_time_budget": false
  }
}
```

## Notes about schema stability or inferred assumptions

- This artifact is route-level state, not a full repair log. Detailed repair attempts are only represented indirectly through `visual_delta_summary.json` and rendered repair overlays.
- `sa_rerun_invoked` is currently always `false` because `enable_sa_rerun=False` is passed and no code branch mutates the field.
- If Phase2 is attempted but does not solve the board, the current decision object does not record a separate `phase2_invoked` boolean. Consumers can still read `phase2_full_repair_hit_time_budget`; activity count remains available from metrics fields like `phase2_fixes`.
