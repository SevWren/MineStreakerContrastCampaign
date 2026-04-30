# Repair Result Dataclass Migration With Timeout Persistence And Summary Propagation

## Summary

Migrate repair-related tuple returns to named result dataclasses, set timeout booleans inside the repair phases that own the time-budget checks, and propagate those booleans through all persisted runtime artifacts, benchmark root summaries, docs, and tests.

Final persisted timeout fields:

```json
{
  "phase1_repair_hit_time_budget": false,
  "phase2_full_repair_hit_time_budget": false,
  "last100_repair_hit_time_budget": false
}
```

---

## Repair API Changes

- In `repair.py`, add result dataclasses for:
  - `_eval_removal(...)`
  - `run_phase1_repair(...)`
  - `run_phase2_mesa_repair(...)`
  - `run_phase2_full_repair(...)`
  - `run_last100_repair(...)`

- Replace all repair tuple returns with dataclass instances.

- Update repair-internal callers to use named fields instead of tuple indexes or tuple unpacking.

- Add an `_EvalRemovalResult` dataclass with fields equivalent to:
  - `coverage`
  - `trial_grid`

- Update `_eval_removal(...)` callers inside `run_phase1_repair(...)` to use:
  - `.coverage`
  - `.trial_grid`

- Add `Phase1RepairResult` for `run_phase1_repair(...)`.

- Set `phase1_repair_hit_time_budget = True` inside `run_phase1_repair(...)` at every branch where:

```python
elapsed >= time_budget_s
```

- Add `Phase2MesaRepairResult` for legacy `run_phase2_mesa_repair(...)`.

- Keep `run_phase2_mesa_repair(...)` timeout-free because it has no time-budget parameter.

- Do not add a fake timeout field to `Phase2MesaRepairResult`.

- Add `Phase2FullRepairResult` for `run_phase2_full_repair(...)`.

- Set `phase2_full_repair_hit_time_budget = True` inside `run_phase2_full_repair(...)` at every branch where the phase reaches `time_budget_s`.

- Add `Last100RepairResult` for `run_last100_repair(...)`.

- Set `last100_repair_hit_time_budget = True` inside `run_last100_repair(...)` at every branch where the phase reaches `budget_s`.

- Preserve the semantic meaning of existing stop reasons.

- Do not preserve tuple-compatible adapters for the migrated repair APIs.

---

## Pipeline Updates

- In `pipeline.py::route_late_stage_failure(...)`, initialize the `decision` dictionary with:

```python
"phase2_full_repair_hit_time_budget": False,
"last100_repair_hit_time_budget": False,
```

- This ensures `repair_route_decision.json` always contains both fields, even when Phase 2 and Last100 routes are not invoked.

- Update `pipeline.py::route_late_stage_failure(...)` Phase 2 and Last100 call sites to consume result-object fields instead of tuple unpacking.

- For Phase 2 full repair:
  - assign `routed_grid` from `phase2_result.grid`
  - assign `phase2_log` from `phase2_result.log`
  - assign `decision["phase2_full_repair_hit_time_budget"]` from `phase2_result.phase2_full_repair_hit_time_budget`
  - propagate the same timeout boolean into `RepairRouteResult`

- For Last100 repair:
  - assign `routed_grid` from `last100_result.grid`
  - assign `routed_sr` from `last100_result.sr`
  - assign `last100_log` from `last100_result.move_log`
  - assign `stop_reason` from `last100_result.stop_reason`
  - assign `decision["last100_repair_hit_time_budget"]` from `last100_result.last100_repair_hit_time_budget`
  - propagate the same timeout boolean into `RepairRouteResult`

- Extend `RepairRouteResult` with explicit fields:

```python
phase2_full_repair_hit_time_budget: bool = False
last100_repair_hit_time_budget: bool = False
```

- Update deprecated `pipeline.py::run_board(...)` so its `run_phase1_repair(...)` call consumes `Phase1RepairResult` fields instead of tuple unpacking.

---

## Runtime And Artifact Propagation

### `run_iter9.py`

- In `run_iter9.py`, persist all three timeout booleans in:
  - top-level flat metrics
  - `repair_route_summary`
  - route artifact metadata, if route artifact metadata includes route-status fields

- Fields:

```text
phase1_repair_hit_time_budget
phase2_full_repair_hit_time_budget
last100_repair_hit_time_budget
```

- Replace the Phase 1 repair tuple-unpacking call site with `Phase1RepairResult` field access.

- Ensure final Iter9 metrics contain all three timeout booleans even when Phase 2 or Last100 repair is not invoked.

---

### `run_benchmark.py`

- In `run_benchmark.py`, persist all three booleans in:
  - normal child flat metrics
  - child `route_summary`
  - route artifact metadata, if route artifact metadata includes route-status fields
  - regression result dictionaries

- Fields:

```text
phase1_repair_hit_time_budget
phase2_full_repair_hit_time_budget
last100_repair_hit_time_budget
```

- Replace the Phase 1 repair tuple-unpacking call site with `Phase1RepairResult` field access.

- Update `run_benchmark.py::_rows_from_child_metrics(...)` so root summary rows carry all three timeout booleans from child metrics.

- Update `benchmark_summary.json`, `benchmark_results.json`, `benchmark_summary.csv`, and `benchmark_summary.md` to include row-level timeout fields:

```text
phase1_repair_hit_time_budget
phase2_full_repair_hit_time_budget
last100_repair_hit_time_budget
```

- Update `run_benchmark.py::_board_aggregates(...)` and the Markdown aggregate table to include:

```text
per-board Phase 1 timeout counts
per-board Phase 2 full repair timeout counts
per-board Last100 timeout counts
any_repair_timeout
```

- Ensure benchmark summary output remains backward-compatible in file names and locations:
  - `benchmark_summary.json`
  - `benchmark_summary.csv`
  - `benchmark_summary.md`
  - `benchmark_results.json`

---

## Tests

- Update `tests/test_repair_route_decision.py` mocks to return result dataclasses instead of tuples.

- Expand `tests/test_route_artifact_metadata.py` to assert `repair_route_decision.json` always includes:

```text
phase2_full_repair_hit_time_budget
last100_repair_hit_time_budget
```

- `tests/test_route_artifact_metadata.py` must cover invoked and not-invoked route paths, including:
  - already solved
  - Phase 2 disabled
  - Last100 disabled
  - no route selected

- Add Iter9 single-run metrics-shape assertions that top-level metrics and `repair_route_summary` include:

```text
phase1_repair_hit_time_budget
phase2_full_repair_hit_time_budget
last100_repair_hit_time_budget
```

- If `tests/test_iter9_image_sweep_contract.py` validates child metrics shape, add assertions that sweep child metrics include all three repair timeout booleans:

```text
phase1_repair_hit_time_budget
phase2_full_repair_hit_time_budget
last100_repair_hit_time_budget
```

- Expand `tests/test_benchmark_layout.py` so all of the following include the timeout fields:
  - summary rows
  - JSON summaries
  - CSV headers
  - Markdown child-run tables
  - compatibility `benchmark_results.json`
  - board aggregates
  - Markdown aggregate table

- Add benchmark aggregate assertions for:
  - per-board Phase 1 timeout counts
  - per-board Phase 2 full repair timeout counts
  - per-board Last100 timeout counts
  - `any_repair_timeout`

- Add regression-result assertions that benchmark regression result dictionaries carry Phase 2 and Last100 route timeout booleans.

- Add focused timeout tests for:
  - `run_phase1_repair(...)`
  - `run_phase2_full_repair(...)`
  - `run_last100_repair(...)`

- Use zero-budget or tiny-budget execution for timeout tests.

- Add a result-object test for `run_phase2_mesa_repair(...)` proving its tuple return was removed without adding a fake timeout field.

---

## Docs And Audit Trail

- Update `docs/json_schema/repair_route_decision.schema.md` so Phase 2 and Last100 timeout booleans are required top-level fields.

- Update `docs/json_schema/metrics_iter9.schema.md` so all three timeout booleans are required flat fields and appear in examples.

- Add or update benchmark summary schema documentation for:
  - root summary JSON
  - CSV
  - Markdown
  - compatibility JSON

- Update `docs/json_schema/JSON_OUTPUT_SCHEMA_INDEX.md` if new benchmark summary schema docs are added.

- Update `README.md` benchmark artifact notes to mention that benchmark root summaries expose repair timeout booleans.

- Update `docs/DOCS_INDEX.md` so any new or materially updated schema docs are discoverable.

- Before editing `PATCH_SUMMARY.md`, verify that the file already exists.

- If `PATCH_SUMMARY.md` does not exist, do not create a new root-level summary file unless repo convention confirms it is allowed.

- If `PATCH_SUMMARY.md` does not exist, place the audit/update notes in an existing approved documentation file instead.

- If `PATCH_SUMMARY.md` exists, update it in completed tense with:
  - dataclass migration
  - timeout propagation
  - benchmark summary propagation
  - tuple-return audit
  - validation results

- Add a concrete tuple-return audit note listing non-repair tuple returns intentionally left unchanged:
  - `corridors.py::build_adaptive_corridors(...)`
  - `sa.py::_sa_kernel(...)`
  - `sa.py::run_sa(...)`
  - `solver.py::_numba_solve(...)`
  - `solver.py::_summarize_state(...)`
  - `report.py::_mine_change_overlay(...)`
  - `run_benchmark.py::_normal_benchmark_root(...)`

---

## Validation

- Run syntax validation:

```powershell
python -m py_compile repair.py pipeline.py run_iter9.py run_benchmark.py
```

- Run the unit suite:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

- Do not run expensive full Iter9 or benchmark jobs unless explicitly requested after implementation.

---

## Assumptions

- No tuple-compatible adapter will be preserved for migrated repair APIs.

- Non-repair tuple returns remain unchanged and are documented as intentionally out of scope.

- Benchmark root summaries are first-class persisted contract artifacts.

- Timeout booleans are authoritative only when set inside the phase that owns the budget check.

- Phase 2 Mesa repair remains timeout-free because it does not own a runtime budget parameter.
