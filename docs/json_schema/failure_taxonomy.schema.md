# JSON Output Schema Specification: `failure_taxonomy.json`

## Artifact name

`failure_taxonomy.json`

## Output filename/path pattern

Primary Iter9 path:

```text
results/iter9/<run_id>/failure_taxonomy.json
```

Iter9 image-sweep child path:

```text
<out_root>/<image_identity>_<board_width>x<board_height>_seed<seed>/failure_taxonomy.json
```

Normal benchmark child path:

```text
results/benchmark/<benchmark_run_id>/<board_width>x<board_height>_seed<seed>/failure_taxonomy.json
```

## Purpose

Captures a solver-facing diagnosis of remaining unresolved cells after Phase 1 repair and before/while late-stage route selection. It classifies unknown cells into connected clusters and recommends the next repair route.

## Producing component

| Role | Component |
|---|---|
| Taxonomy dictionary builder | `solver.py::classify_unresolved_clusters(grid, sr)` |
| Route object creation | `pipeline.py::route_late_stage_failure(...)` |
| JSON file writer | `pipeline.py::write_repair_route_artifacts(...)` |
| Iter9 caller | `run_iter9.py::run_iter9_single(...)` |
| Benchmark caller | `run_benchmark.py::run_normal_child(...)` |

## Generation conditions

The file is written when a run reaches late-stage routing and calls `write_repair_route_artifacts(...)`.

It is written even when no unknown cells remain; in that case `dominant_failure_class` is `"no_unknowns"` and `clusters` is an empty array.

The file is not produced if execution fails before late-stage routing artifact writing.

## Top-level JSON structure

```json
{
  "n_unknown": 0,
  "unknown_cluster_count": 0,
  "sealed_single_mesa_count": 0,
  "sealed_multi_cell_cluster_count": 0,
  "frontier_adjacent_unknown_count": 0,
  "ordinary_ambiguous_unknown_count": 0,
  "sealed_cluster_count": 0,
  "dominant_failure_class": "no_unknowns",
  "recommended_route": "none",
  "clusters": [],
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

The following fields are always returned by `classify_unresolved_clusters(...)`:

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `n_unknown` | integer | Yes | No | Count of solver cells still in `UNKNOWN` state. |
| `unknown_cluster_count` | integer | Yes | No | Number of connected components among unknown cells. |
| `sealed_single_mesa_count` | integer | Yes | No | Number of one-cell sealed unknown clusters. |
| `sealed_multi_cell_cluster_count` | integer | Yes | No | Number of multi-cell sealed unknown clusters. |
| `frontier_adjacent_unknown_count` | integer | Yes | No | Number of unknown clusters adjacent to at least one solver-safe cell. |
| `ordinary_ambiguous_unknown_count` | integer | Yes | No | Number of unknown clusters without safe-neighbor access and without external mine enclosure. |
| `sealed_cluster_count` | integer | Yes | No | Sum of `sealed_single_mesa_count` and `sealed_multi_cell_cluster_count`. |
| `dominant_failure_class` | string | Yes | No | Highest-priority / most frequent failure class. See enum below. |
| `recommended_route` | string | Yes | No | Suggested next repair route. See enum below. |
| `clusters` | array of objects | Yes | No | One object per unknown connected component. Empty when `n_unknown == 0` or solver state is missing. |

## Optional fields

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `artifact_metadata` | object | No | No | Injected by `write_repair_route_artifacts(...)` when caller passes metadata. Current Iter9 and normal benchmark runs pass it. |

## Allowed values / enums

### `dominant_failure_class`

```text
unclassified_missing_solver_state
no_unknowns
sealed_multi_cell_cluster
sealed_single_mesa
frontier_adjacent_unknown
ordinary_ambiguous_unknown
```

### `recommended_route`

```text
rerun_solver_full
none
phase2_full_repair
last100_or_standard_repair
manual_or_future_solver_analysis
```

### `clusters[].kind`

```text
sealed_single_mesa
sealed_multi_cell_cluster
frontier_adjacent_unknown
ordinary_ambiguous_unknown
```

### `clusters[].candidate_repair`

```text
phase2_full_repair
last100_or_standard_repair
manual_or_future_solver_analysis
```

## Nested object definitions

### `clusters[]`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `cluster_id` | integer | Yes | No | Connected-component label assigned by `scipy.ndimage.label`, starting at `1`. |
| `size` | integer | Yes | No | Number of unknown cells in the cluster. |
| `kind` | string enum | Yes | No | Cluster classification. |
| `has_safe_neighbor` | boolean | Yes | No | Whether any cell in the cluster touches a solver-safe cell. |
| `external_mine_count` | integer | Yes | No | Count of adjacent grid mines outside the cluster. |
| `candidate_repair` | string enum | Yes | No | Repair family suggested for this cluster. |
| `cells` | array of coordinate pairs | Yes | No | Unknown cell coordinates in `[row, column]` form. |
| `external_mines` | array of coordinate pairs | Yes | No | Adjacent external mine coordinates in `[row, column]` form. |

### Coordinate pair

```json
[row, column]
```

| Index | Type | Description |
|---:|---:|---|
| `0` | integer | Row / y coordinate. |
| `1` | integer | Column / x coordinate. |

### `artifact_metadata`

| Field | Type | Required when object exists | Nullable | Description |
|---|---:|---:|---:|---|
| `run_id` | string | Yes | No | Iter9 run id or benchmark child run id. |
| `generated_at_utc` | string | Yes | No | UTC timestamp in ISO-like `...Z` format. |
| `source_image_project_relative_path` | string | Yes | Yes | Source image path relative to project root. May be `null` for non-project paths. |
| `source_image_sha256` | string | Yes | No | SHA-256 hash of source image. |
| `metrics_path` | string | Yes | No | Relative or absolute path to the metrics JSON for the same run. |

## Nullability rules

- Core taxonomy fields are not nullable.
- `clusters` is always an array; it may be empty.
- `cells` and `external_mines` are always arrays; either may be empty depending on cluster kind.
- `artifact_metadata.source_image_project_relative_path` may be `null` if the source image is outside the project root.
- `artifact_metadata` itself is optional because the writer accepts `artifact_metadata=None`.

## Example JSON output

```json
{
  "n_unknown": 3,
  "unknown_cluster_count": 1,
  "sealed_single_mesa_count": 0,
  "sealed_multi_cell_cluster_count": 1,
  "frontier_adjacent_unknown_count": 0,
  "ordinary_ambiguous_unknown_count": 0,
  "sealed_cluster_count": 1,
  "dominant_failure_class": "sealed_multi_cell_cluster",
  "recommended_route": "phase2_full_repair",
  "clusters": [
    {
      "cluster_id": 1,
      "size": 3,
      "kind": "sealed_multi_cell_cluster",
      "has_safe_neighbor": false,
      "external_mine_count": 5,
      "candidate_repair": "phase2_full_repair",
      "cells": [[42, 18], [42, 19], [43, 18]],
      "external_mines": [[41, 17], [41, 18], [41, 19], [42, 17], [43, 17]]
    }
  ],
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

- The taxonomy schema is relatively stable because all core keys are constructed in a single function, `solver.py::classify_unresolved_clusters(...)`.
- The `clusters[].cells` array can be large because every unresolved cell coordinate is serialized.
- The code does not cap `clusters[].external_mines` in the taxonomy artifact.
- `artifact_metadata` is writer-level metadata, not taxonomy-level diagnosis.
- `dominant_failure_class` uses a count-based `max(...)` with tie preferences for sealed clusters, so consumers should not assume it is simply the first cluster kind encountered.
