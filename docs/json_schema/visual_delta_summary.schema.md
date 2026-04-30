# JSON Output Schema Specification: `visual_delta_summary.json`

## Artifact name

`visual_delta_summary.json`

## Output filename/path pattern

Primary Iter9 path:

```text
results/iter9/<run_id>/visual_delta_summary.json
```

Iter9 image-sweep child path:

```text
<out_root>/<image_identity>_<board_width>x<board_height>_seed<seed>/visual_delta_summary.json
```

Normal benchmark child path:

```text
results/benchmark/<benchmark_run_id>/<board_width>x<board_height>_seed<seed>/visual_delta_summary.json
```

## Purpose

Stores the final route-level visual-delta summary selected by late-stage repair routing. This is a compact JSON artifact for the visual cost of a repair move or attempted move.

## Producing component

| Role | Component |
|---|---|
| Phase2 visual-delta fields | `repair.py::compute_repair_visual_delta(...)` and `repair.py::run_phase2_full_repair(...)` |
| Last100 move-log fields | `repair.py::run_last100_repair(...)` |
| Route selection of final summary | `pipeline.py::route_late_stage_failure(...)` |
| JSON file writer | `pipeline.py::write_repair_route_artifacts(...)` |

## Generation conditions

The file is written by `write_repair_route_artifacts(...)` whenever route artifacts are written.

The object shape is a union of three variants:

1. Empty/no-move variant: no repair move log exists, so route-level summary is `{}` before optional metadata injection.
2. Phase2 variant: last item from `phase2_log` when Phase2 solves the board.
3. Last100 variant: last item from `last100_log` when the Last100 route is selected.

## Top-level JSON structure

### Empty/no-move variant

```json
{
  "artifact_metadata": {
    "run_id": "20260429T204700Z_line_art_irl_11_v2_300w_seed42",
    "generated_at_utc": "2026-04-29T20:47:00.000Z",
    "source_image_project_relative_path": "assets/line_art_irl_11_v2.png",
    "source_image_sha256": "<sha256>",
    "metrics_path": "results/iter9/<run_id>/metrics_iter9_300x942.json"
  }
}
```

### Phase2 variant

```json
{
  "cluster_size": 3,
  "removed_mine": [41, 18],
  "removed_mines": [[41, 18]],
  "move_type": "single",
  "T_removed": 0.42,
  "delta_unk": 3,
  "repair_stage": "phase2_full",
  "cluster_id": 1,
  "cluster_kind": "sealed_multi_cell_cluster",
  "n_unknown_before": 3,
  "n_unknown_after": 0,
  "delta_unknown": 3,
  "mean_abs_error_before": 1.234,
  "mean_abs_error_after": 1.236,
  "visual_delta": 0.002,
  "accepted": true,
  "artifact_metadata": {
    "run_id": "20260429T204700Z_line_art_irl_11_v2_300w_seed42",
    "generated_at_utc": "2026-04-29T20:47:00.000Z",
    "source_image_project_relative_path": "assets/line_art_irl_11_v2.png",
    "source_image_sha256": "<sha256>",
    "metrics_path": "results/iter9/<run_id>/metrics_iter9_300x942.json"
  }
}
```

### Last100 variant

```json
{
  "iteration": 2,
  "component_id": 4,
  "component_size": 7,
  "move_type": "pair",
  "removed_mines": [[120, 44], [121, 45]],
  "pre_n_unknown": 7,
  "post_n_unknown": 2,
  "delta_unknown": 5,
  "delta_mean_abs_error": 0.0011,
  "delta_true_bg_err": 0.0024,
  "delta_hi_err": -0.0003,
  "accepted": true,
  "reject_reason": "",
  "artifact_metadata": {
    "run_id": "20260429T204700Z_line_art_irl_11_v2_300w_seed42",
    "generated_at_utc": "2026-04-29T20:47:00.000Z",
    "source_image_project_relative_path": "assets/line_art_irl_11_v2.png",
    "source_image_sha256": "<sha256>",
    "metrics_path": "results/iter9/<run_id>/metrics_iter9_300x942.json"
  }
}
```

## Required fields

Because this artifact is a union, required fields depend on the variant.

### Empty/no-move variant required fields

No variant-specific fields are required. The artifact may be `{}` if metadata is not supplied, or it may contain only `artifact_metadata`.

### Phase2 variant required fields

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `cluster_size` | integer | Yes | No | Size of repaired sealed cluster. |
| `removed_mine` | coordinate pair | Yes | No | Primary removed mine coordinate `[row, column]`. For pair moves this is the first selected mine. |
| `removed_mines` | array of coordinate pairs | Yes | No | One or two removed mine coordinates. |
| `move_type` | string enum | Yes | No | `single` or `pair`. |
| `T_removed` | number | Yes | No | Target-field value at `removed_mine`. |
| `delta_unk` | integer | Yes | No | Unknown-count reduction. Duplicate legacy spelling of `delta_unknown`. |
| `repair_stage` | string enum | Yes | No | Currently `phase2_full`. |
| `cluster_id` | integer | Yes | No | Cluster id from sealed-cluster detection. |
| `cluster_kind` | string enum | Yes | No | `sealed_single_mesa` or `sealed_multi_cell_cluster`. |
| `n_unknown_before` | integer | Yes | No | Unknown count before accepted repair move. |
| `n_unknown_after` | integer | Yes | No | Unknown count after accepted repair move. |
| `delta_unknown` | integer | Yes | No | Unknown-count reduction. |
| `mean_abs_error_before` | number | Yes | No | Mean absolute visual error before accepted repair move. |
| `mean_abs_error_after` | number | Yes | No | Mean absolute visual error after accepted repair move. |
| `visual_delta` | number | Yes | No | `mean_abs_error_after - mean_abs_error_before`; negative is visually better. |
| `accepted` | boolean | Yes | No | Always `true` for Phase2 log entries that are appended. |

### Last100 variant required fields

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `iteration` | integer | Yes | No | Outer Last100 iteration number, starting at `1`. |
| `component_id` | integer | Yes | No | Unknown connected-component id under consideration. |
| `component_size` | integer | Yes | No | Size of the component under consideration. |
| `move_type` | string enum | Yes | No | `single` or `pair`. |
| `removed_mines` | array of coordinate pairs | Yes | No | Candidate mines removed in this trial. |
| `pre_n_unknown` | integer | Yes | No | Unknown count before candidate move. |
| `post_n_unknown` | integer | Yes | No | Unknown count after candidate move. |
| `delta_unknown` | integer | Yes | No | `pre_n_unknown - post_n_unknown`. |
| `delta_mean_abs_error` | number or null | Yes | Yes | Mean absolute error delta; remains `null` when the candidate did not reduce unknowns. |
| `delta_true_bg_err` | number or null | Yes | Yes | True-background error delta; remains `null` when the candidate did not reduce unknowns. |
| `delta_hi_err` | number or null | Yes | Yes | High-target error delta; remains `null` when the candidate did not reduce unknowns. |
| `accepted` | boolean | Yes | No | Whether the candidate passed unknown-reduction and visual guardrails. |
| `reject_reason` | string | Yes | No | Empty string for accepted candidates; otherwise a reason string. |

## Optional fields

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `artifact_metadata` | object | No | No | Injected by `write_repair_route_artifacts(...)` when caller passes metadata. Current Iter9 and normal benchmark runs pass it. |

## Allowed values / enums

### `move_type`

```text
single
pair
```

### `repair_stage`

```text
phase2_full
```

### `cluster_kind`

```text
sealed_single_mesa
sealed_multi_cell_cluster
```

### Last100 `reject_reason`

```text
""
no_unknown_reduction
mean_abs_guardrail
true_bg_guardrail
hi_err_guardrail
```

## Array item definitions

### Coordinate pair

```json
[row, column]
```

| Index | Type | Description |
|---:|---:|---|
| `0` | integer | Row / y coordinate. |
| `1` | integer | Column / x coordinate. |

## Nullability rules

- Empty/no-move variant may contain no visual fields at all.
- Last100 `delta_mean_abs_error`, `delta_true_bg_err`, and `delta_hi_err` are nullable because they are initialized to `None` before visual guardrails run.
- Phase2 numeric fields are non-null when the Phase2 variant is present.
- `artifact_metadata.source_image_project_relative_path` may be `null` for images outside the project root.

## Example JSON output: rejected Last100 candidate

```json
{
  "iteration": 3,
  "component_id": 2,
  "component_size": 5,
  "move_type": "single",
  "removed_mines": [[88, 17]],
  "pre_n_unknown": 5,
  "post_n_unknown": 5,
  "delta_unknown": 0,
  "delta_mean_abs_error": null,
  "delta_true_bg_err": null,
  "delta_hi_err": null,
  "accepted": false,
  "reject_reason": "no_unknown_reduction",
  "artifact_metadata": {
    "run_id": "20260429T204700Z_line_art_irl_11_v2_300w_seed42",
    "generated_at_utc": "2026-04-29T20:47:00.000Z",
    "source_image_project_relative_path": "assets/line_art_irl_11_v2.png",
    "source_image_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
    "metrics_path": "results/iter9/20260429T204700Z_line_art_irl_11_v2_300w_seed42/metrics_iter9_300x942.json"
  }
}
```

## Notes about schema stability or inferred assumptions

- `visual_delta_summary.json` is the least stable of the four requested artifacts because its shape depends on the selected route and the repair log source.
- Current code stores `last100_log[-1]`, which is the last logged Last100 candidate, not necessarily the best or accepted candidate. Consumers should inspect `accepted` and `reject_reason` before treating it as a successful move summary.
- Phase2 appends only accepted moves, so `accepted` is currently always `true` for Phase2 variant entries.
- The empty/no-move variant occurs for `already_solved`, `needs_sa_or_adaptive_rerun`, and any repair route that produces no log entries.
