# JSON Output Schema Specification: Benchmark Root Summaries

## Artifact names

Normal benchmark mode writes these root-level summary artifacts under one benchmark run root:

```text
results/benchmark/<benchmark_run_id>/benchmark_summary.json
results/benchmark/<benchmark_run_id>/benchmark_summary.csv
results/benchmark/<benchmark_run_id>/benchmark_summary.md
results/benchmark/<benchmark_run_id>/benchmark_results.json
```

## Purpose

Benchmark root summaries provide a run-level index across benchmark child directories. They preserve row-level child metrics, source-image provenance, and per-board aggregate health checks without changing child artifact filenames.

## Producing component

| Role | Component |
|---|---|
| Row extraction | `run_benchmark.py::_rows_from_child_metrics(...)` |
| Board aggregates | `run_benchmark.py::_board_aggregates(...)` |
| JSON/CSV/Markdown writers | `run_benchmark.py::write_normal_benchmark_summaries(...)` |

## Summary JSON structure

`benchmark_summary.json` is an object:

```json
{
  "benchmark_mode": "normal",
  "benchmark_run_id": "20260429T204700Z_line_art_irl_11_v2_benchmark",
  "generated_at_utc": "2026-04-29T20:47:00.000Z",
  "benchmark_root": "results/benchmark/<benchmark_run_id>",
  "widths": [300],
  "seeds": [11],
  "source_image": {},
  "source_image_validation": {},
  "rows": [],
  "board_aggregates": []
}
```

## Row fields

The same row shape is used by:

- `benchmark_summary.json.rows`
- `benchmark_summary.csv`
- `benchmark_results.json`
- the child-run table in `benchmark_summary.md`

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `board` | string | Yes | No | Board label, for example `300x942`. |
| `seed` | integer | Yes | No | Child run seed. |
| `child_dir` | string | Yes | No | Child run directory path. |
| `n_unknown` | integer | Yes | No | Final unknown-cell count. |
| `coverage` | number | Yes | No | Final solver coverage. |
| `solvable` | boolean | Yes | No | Final solvability flag. |
| `repair_route_selected` | string | Yes | No | Selected late-stage route. |
| `repair_route_result` | string | Yes | No | Route result. |
| `phase2_fixes` | integer | Yes | No | Length of Phase2 repair log. |
| `last100_fixes` | integer | Yes | No | Length of Last100 repair log. |
| `phase1_repair_hit_time_budget` | boolean | Yes | No | Phase1 timeout boolean copied from child metrics. |
| `phase2_full_repair_hit_time_budget` | boolean | Yes | No | Phase2 full repair timeout boolean copied from child metrics. |
| `last100_repair_hit_time_budget` | boolean | Yes | No | Last100 repair timeout boolean copied from child metrics. |
| `visual_delta` | number | Yes | Yes | Route visual delta, or `null` when unavailable. |
| `total_time_s` | number | Yes | No | Child run wall-clock duration. |
| `source_image_name` | string | Yes | Yes | Source image filename. |
| `source_image_stem` | string | Yes | Yes | Source image stem. |
| `source_image_project_relative_path` | string | Yes | Yes | Source image path relative to project root. |
| `source_image_sha256` | string | Yes | Yes | Source image SHA-256. |

## Board aggregate fields

`benchmark_summary.json.board_aggregates` and the aggregate table in `benchmark_summary.md` include:

| Field | Type | Required | Nullable | Description |
|---|---:|---:|---:|---|
| `board` | string | Yes | No | Board label. |
| `runs` | integer | Yes | No | Number of child rows for the board. |
| `median_n_unknown` | number | Yes | No | Median final unknown count. |
| `median_coverage` | number | Yes | No | Median final coverage. |
| `median_visual_delta` | number | Yes | No | Median visual delta, treating missing values as `0.0`. |
| `median_total_time_s` | number | Yes | No | Median child run duration. |
| `all_solved` | boolean | Yes | No | True when every row is solvable with zero unknowns. |
| `phase1_repair_timeout_count` | integer | Yes | No | Count of rows where Phase1 reached its time budget. |
| `phase2_full_repair_timeout_count` | integer | Yes | No | Count of rows where Phase2 full repair reached its time budget. |
| `last100_repair_timeout_count` | integer | Yes | No | Count of rows where Last100 repair reached its time budget. |
| `any_repair_timeout` | boolean | Yes | No | True when any repair timeout boolean is true for any row in the board group. |

## CSV and Markdown notes

`benchmark_summary.csv` uses the row fields above as headers in the same order emitted by `write_normal_benchmark_summaries(...)`.

`benchmark_summary.md` contains:

- a board aggregate table with timeout counts and `any_repair_timeout`
- a child-run table with all three row-level timeout booleans

## Compatibility JSON

`benchmark_results.json` remains a compatibility artifact containing only the `rows` list. It now carries the same row-level timeout booleans as `benchmark_summary.json.rows`.
