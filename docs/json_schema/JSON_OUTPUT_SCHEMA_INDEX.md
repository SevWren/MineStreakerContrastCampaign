# JSON Output Schema Index

Generated for the attached Mine-Streaker / Minesweeper Python codebase snapshot.

## Covered JSON result artifacts

| Artifact | Documentation file | Primary output pattern | Primary producer |
|---|---|---|---|
| `failure_taxonomy.json` | [`failure_taxonomy.schema.md`](failure_taxonomy.schema.md) | `results/iter9/<run_id>/failure_taxonomy.json` | `solver.py::classify_unresolved_clusters(...)` via `pipeline.py::write_repair_route_artifacts(...)` |
| `metrics_iter9_<board>.json` | [`metrics_iter9.schema.md`](metrics_iter9.schema.md) | `results/iter9/<run_id>/metrics_iter9_<board_width>x<board_height>.json` | `run_iter9.py::run_iter9_single(...)` via `run_iter9.py::build_metrics_document(...)` |
| `repair_route_decision.json` | [`repair_route_decision.schema.md`](repair_route_decision.schema.md) | `results/iter9/<run_id>/repair_route_decision.json` | `pipeline.py::route_late_stage_failure(...)` via `pipeline.py::write_repair_route_artifacts(...)` |
| `visual_delta_summary.json` | [`visual_delta_summary.schema.md`](visual_delta_summary.schema.md) | `results/iter9/<run_id>/visual_delta_summary.json` | `repair.py::run_phase2_full_repair(...)` or `repair.py::run_last100_repair(...)` via `pipeline.py::write_repair_route_artifacts(...)` |
| Benchmark root summaries | [`benchmark_summary.schema.md`](benchmark_summary.schema.md) | `results/benchmark/<benchmark_run_id>/benchmark_summary.*` and `benchmark_results.json` | `run_benchmark.py::write_normal_benchmark_summaries(...)` |

## Additional path patterns found

The same route artifacts (`failure_taxonomy.json`, `repair_route_decision.json`, and `visual_delta_summary.json`) are also written by normal benchmark child runs:

```text
results/benchmark/<benchmark_run_id>/<board_width>x<board_height>_seed<seed>/failure_taxonomy.json
results/benchmark/<benchmark_run_id>/<board_width>x<board_height>_seed<seed>/repair_route_decision.json
results/benchmark/<benchmark_run_id>/<board_width>x<board_height>_seed<seed>/visual_delta_summary.json
```

`metrics_iter9_<board>.json` is specific to Iter9 single-image runs and Iter9 image-sweep child runs.

Normal benchmark root summary artifacts are:

```text
results/benchmark/<benchmark_run_id>/benchmark_summary.json
results/benchmark/<benchmark_run_id>/benchmark_summary.csv
results/benchmark/<benchmark_run_id>/benchmark_summary.md
results/benchmark/<benchmark_run_id>/benchmark_results.json
```



## Important schema notes

1. The codebase writes these files directly with `json.dump(..., indent=2)` and does not define formal JSON Schema files.
2. The schemas in this documentation are inferred from the Python dictionaries written to disk.
3. The route artifacts support an optional `artifact_metadata` object. Current `run_iter9.py` and normal `run_benchmark.py` calls provide it, but `pipeline.py::write_repair_route_artifacts(...)` accepts `artifact_metadata=None`, so downstream consumers should treat it as optional.
4. `source_config.py` was not present in the supplied code snapshot, so the `source_image` object is documented from visible runtime usage and repository contract notes. The `source_image_validation` object is documented from the supplied image-validation module.
