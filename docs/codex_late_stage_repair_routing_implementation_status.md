# Late-Stage Repair Routing Implementation Status

## Purpose

This document is the implementation-status companion to the late-stage repair routing plan.

Use this file to track what the implementing LLM or agent has actually changed, tested, skipped, or blocked while implementing the late-stage solver failure taxonomy and repair-routing architecture.

```text
Plan document = what should be built
Status ledger = what has actually been changed, tested, skipped, or blocked
```

---

## Current Status

| Field | Value |
|---|---|
| Overall status | Not started |
| Last updated | YYYY-MM-DD |
| Active branch/worktree |  |
| Implementing agent | OpenAI Codex |
| Source plan | `docs/late_stage_repair_routing_plan.md` |
| Current phase |  |
| Blocking issues | None recorded |
| Review status | Not reviewed |

---

## Status Legend

| Status | Meaning |
|---|---|
| Not started | No implementation work has been done for this item. |
| In progress | The file or phase has partial changes. |
| Complete | The planned change has been implemented and verified. |
| Blocked | Work cannot continue until an issue is resolved. |
| Deferred | Intentionally postponed. |
| Protected | File is intentionally left unchanged. |
| Not applicable | Item does not apply after implementation review. |

---

# File Implementation Matrix

| File | Required Change | Status | Evidence | Notes |
|---|---|---|---|---|
| `solver.py` | Add unresolved-cell taxonomy and `classify_unresolved_clusters()` | Not started |  |  |
| `repair.py` | Add sealed-cluster detection helper, visual delta helper, and richer repair logs | Not started |  |  |
| `pipeline.py` | Add routing config/result objects, route function, and route artifact writer | Not started |  |  |
| `run_iter9.py` | Replace direct MESA repair path with late-stage repair router | Not started |  |  |
| `report.py` | Add repair overlay renderer | Not started |  |  |
| `run_benchmark.py` | Add repair-route regression gate for known failure family | Not started |  |  |
| `core.py` | Add sealed-cluster risk-map diagnostic helper | Not started |  |  |
| `corridors.py` | Add corridor-access diagnostic helper | Not started |  |  |
| `sa.py` | Add SA output summary helper only; no routing logic | Not started |  |  |
| `list_unignored_files.py` | Add Git-native file collection path with existing fallback preserved | Not started |  |  |
| `AGENTS.md` | Add late-stage repair routing contract | Not started |  |  |
| `run_contrast_preprocessing_study.py` | Out of scope; must remain unchanged unless direct compatibility failure occurs | Protected | No diff expected | Deprecated / one-time study script |

---

# Phase Checklist

## Phase 1: Solver Failure Taxonomy

### Target File

`solver.py`

### Required Changes

- [ ] Add `UnresolvedCluster` dataclass.
- [ ] Add `classify_unresolved_clusters(grid, sr) -> dict`.
- [ ] Detect `sr.n_unknown == 0`.
- [ ] Handle missing `sr.state`.
- [ ] Classify `sealed_single_mesa`.
- [ ] Classify `sealed_multi_cell_cluster`.
- [ ] Classify `frontier_adjacent_unknown`.
- [ ] Classify `ordinary_ambiguous_unknown`.
- [ ] Return JSON-serializable dictionary.
- [ ] Do not mutate `grid`.
- [ ] Do not mutate `sr.state`.
- [ ] Do not call `solve_board()` inside classifier.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 2: Repair Detection And Visual Delta

### Target File

`repair.py`

### Required Changes

- [ ] Add `find_sealed_unknown_clusters(grid, sr, forbidden) -> list[dict]`.
- [ ] Refactor `run_phase2_full_repair()` to use the detection helper.
- [ ] Preserve `run_phase2_full_repair()` public signature.
- [ ] Preserve `run_phase2_full_repair()` return shape.
- [ ] Preserve legacy repair log keys:
  - [ ] `cluster_size`
  - [ ] `removed_mine`
  - [ ] `removed_mines`
  - [ ] `move_type`
  - [ ] `T_removed`
  - [ ] `delta_unk`
- [ ] Add new repair log keys:
  - [ ] `repair_stage`
  - [ ] `cluster_id`
  - [ ] `cluster_kind`
  - [ ] `n_unknown_before`
  - [ ] `n_unknown_after`
  - [ ] `delta_unknown`
  - [ ] `mean_abs_error_before`
  - [ ] `mean_abs_error_after`
  - [ ] `visual_delta`
  - [ ] `accepted`
- [ ] Add `compute_repair_visual_delta(before_grid, after_grid, target) -> dict`.
- [ ] Ensure forbidden cells remain mine-free after repair.
- [ ] Ensure new helper outputs are JSON-serializable.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 3: Repair Routing Contract

### Target File

`pipeline.py`

### Required Changes

- [ ] Add `RepairRoutingConfig`.
- [ ] Add `RepairRouteResult`.
- [ ] Add `route_late_stage_failure(grid, target, weights, forbidden, sr, config)`.
- [ ] Add `write_repair_route_artifacts(out_dir, board_label, route_result)`.
- [ ] Route `already_solved` when `sr.n_unknown == 0`.
- [ ] Call `classify_unresolved_clusters()`.
- [ ] Route sealed clusters to `run_phase2_full_repair()`.
- [ ] Rerun solver after Phase 2.
- [ ] Route to Last-100 only when available and threshold condition is met.
- [ ] Do not silently run SA or adaptive reruns.
- [ ] Return structured unresolved result when repair cannot solve the board.
- [ ] Write `failure_taxonomy.json`.
- [ ] Write `repair_route_decision.json`.
- [ ] Write `visual_delta_summary.json`.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 4: Iteration 9 Entry Point Uses Router

### Target File

`run_iter9.py`

### Required Changes

- [ ] Replace direct main-path `run_phase2_mesa_repair()` call.
- [ ] Use `route_late_stage_failure()`.
- [ ] Print `Late-stage repair routing`.
- [ ] Keep board validity assertion after routing.
- [ ] Add route fields to metrics:
  - [ ] `repair_route_selected`
  - [ ] `repair_route_result`
  - [ ] `dominant_failure_class`
  - [ ] `sealed_cluster_count`
  - [ ] `sealed_single_mesa_count`
  - [ ] `sealed_multi_cell_cluster_count`
  - [ ] `phase2_fixes`
  - [ ] `last100_fixes`
  - [ ] `visual_delta`
  - [ ] `failure_taxonomy_path`
  - [ ] `repair_route_decision_path`
  - [ ] `visual_delta_summary_path`
- [ ] Preserve existing metrics fields.
- [ ] Write route artifacts under `results/iter9`.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 5: Repair Overlay Rendering

### Target File

`report.py`

### Required Changes

- [ ] Add `render_repair_overlay(...)`.
- [ ] Render target image.
- [ ] Render before-repair unknown cells.
- [ ] Render after-repair unknown cells.
- [ ] Render removed mines.
- [ ] Render added mines if present.
- [ ] Render error delta.
- [ ] Render text summary.
- [ ] Work when `repair_log` is empty.
- [ ] Work when `sr_before.state` is missing.
- [ ] Work when `sr_after.state` is missing.
- [ ] Do not alter `render_report()` behavior.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 6: Core Risk Diagnostics

### Target File

`core.py`

### Required Changes

- [ ] Add `compute_sealed_cluster_risk_map(target, grid=None, high_target_threshold=5.5, dense_neighbor_threshold=5)`.
- [ ] Return `sat_risk_cells`.
- [ ] Return `high_target_dense_components`.
- [ ] Return `predicted_sealed_cluster_risk`.
- [ ] Return configured thresholds.
- [ ] Include optional mine-density stats when `grid` is supplied.
- [ ] Do not change target generation behavior.
- [ ] Do not add new dependencies.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 7: Corridor Access Diagnostics

### Target File

`corridors.py`

### Required Changes

- [ ] Add `analyze_corridor_access_to_unknowns(forbidden, sr) -> dict`.
- [ ] Use `sr.state` as solver-state source.
- [ ] Use `forbidden == 1` as corridor mask.
- [ ] Return `unknown_cells`.
- [ ] Return `unknown_clusters_touching_corridor`.
- [ ] Return `mean_distance_unknown_to_corridor`.
- [ ] Return `sealed_clusters_isolated_from_corridor`.
- [ ] Tolerate no unknown cells.
- [ ] Tolerate missing `sr.state`.
- [ ] Do not mutate inputs.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 8: SA Output Diagnostics Only

### Target File

`sa.py`

### Required Changes

- [ ] Add `summarize_sa_output(grid, target, forbidden) -> dict`.
- [ ] Return `mine_density`.
- [ ] Return `forbidden_mine_count`.
- [ ] Return `forbidden_violation`.
- [ ] Return `high_target_mine_overlap_count`.
- [ ] Return `high_target_mine_overlap_pct`.
- [ ] Do not modify `_sa_kernel`.
- [ ] Do not change `run_sa()` return type.
- [ ] Do not add repair routing logic to `sa.py`.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 9: Benchmark Regression Gate

### Target File

`run_benchmark.py`

### Required Changes

- [ ] Add regression case for `line_art_irl_9.png`.
- [ ] Use board `300x942`.
- [ ] Use seeds `[11, 22, 33]`.
- [ ] Expected final `n_unknown = 0`.
- [ ] Expected route `phase2_full_repair`.
- [ ] Add route fields to per-run result:
  - [ ] `repair_route_selected`
  - [ ] `repair_route_result`
  - [ ] `dominant_failure_class`
  - [ ] `sealed_cluster_count`
  - [ ] `phase2_fixes`
  - [ ] `last100_fixes`
  - [ ] `visual_delta`
- [ ] Fail loudly if known regression no longer routes through Phase 2 full repair.
- [ ] Preserve existing benchmark summary output.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 10: Deprecated Contrast Study Script Remains Out Of Scope

### Target File

`run_contrast_preprocessing_study.py`

### Required Decision

Do not modify this file as part of this implementation.

### Required Checks

- [ ] File remains unchanged.
- [ ] No route fields added.
- [ ] No tests depend on this file.
- [ ] Only modify if required to fix a direct import, syntax, or compatibility failure caused by routing implementation.

### Status

Protected

### Evidence

```text
Expected evidence: no diff for run_contrast_preprocessing_study.py.
```

### Notes

```text
This file is treated as a deprecated / one-time study script.
```

---

## Phase 11: Digest File Listing Reliability

### Target File

`list_unignored_files.py`

### Required Changes

- [ ] Add `collect_git_tracked_and_unignored_files(root: Path) -> list[Path]`.
- [ ] Prefer `git ls-files` when Git is available.
- [ ] Use `git check-ignore` where applicable for untracked files.
- [ ] Preserve existing fallback behavior.
- [ ] Preserve stable output ordering.
- [ ] Avoid including generated binary result artifacts by default unless explicitly requested.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

## Phase 12: Repository Agent Contract

### Target File

`AGENTS.md`

### Required Changes

- [ ] Add late-stage repair routing contract.
- [ ] State that `solver.py` owns unresolved-cell classification.
- [ ] State that `pipeline.py` owns repair route selection.
- [ ] State that `repair.py` owns grid mutation and repair move logs.
- [ ] State that `report.py` owns visual proof artifacts.
- [ ] State that `sa.py` must not contain repair routing logic.
- [ ] State that existing metrics fields must not be removed.
- [ ] State that new artifacts must be written under `results/`.
- [ ] State that generated root-level ad-hoc files are forbidden.

### Status

Not started

### Evidence

```text

```

### Notes

```text

```

---

# Decision Log

| Date | Decision | Reason | Files Affected |
|---|---|---|---|
| YYYY-MM-DD | Treat `run_contrast_preprocessing_study.py` as out of scope | Deprecated / one-time contrast study script | None |
| YYYY-MM-DD |  |  |  |

---

# Test Status

| Test Command | Status | Result / Error |
|---|---|---|
| `python -m unittest discover -s tests -p "test_*.py"` | Not run |  |
| `python assets/image_guard.py --path assets/input_source_image.png` | Not run |  |
| `python run_iter9.py` | Not run |  |
| `python run_benchmark.py` | Not run |  |

---

# Unit Test Implementation Status

| Test File | Purpose | Status | Notes |
|---|---|---|---|
| `tests/test_solver_failure_taxonomy.py` | Validate unresolved-cluster classifier | Not started |  |
| `tests/test_repair_visual_delta.py` | Validate repair visual delta helper | Not started |  |
| `tests/test_repair_route_decision.py` | Validate routing decisions | Not started |  |
| `tests/test_digest_file_listing.py` | Validate Git-native and fallback file collection | Not started |  |

---

# Required Artifact Status

| Artifact | Expected Location | Status | Notes |
|---|---|---|---|
| `failure_taxonomy.json` | `results/iter9/` | Missing |  |
| `repair_route_decision.json` | `results/iter9/` | Missing |  |
| `visual_delta_summary.json` | `results/iter9/` | Missing |  |
| `repair_overlay_<board>.png` | `results/iter9/` | Missing |  |

---

# Required Metrics Status

| Metrics Field | Status | Notes |
|---|---|---|
| `repair_route_selected` | Missing |  |
| `repair_route_result` | Missing |  |
| `dominant_failure_class` | Missing |  |
| `sealed_cluster_count` | Missing |  |
| `sealed_single_mesa_count` | Missing |  |
| `sealed_multi_cell_cluster_count` | Missing |  |
| `phase2_fixes` | Missing |  |
| `last100_fixes` | Missing |  |
| `visual_delta` | Missing |  |
| `failure_taxonomy_path` | Missing |  |
| `repair_route_decision_path` | Missing |  |
| `visual_delta_summary_path` | Missing |  |

---

# Backward Compatibility Status

| Existing Behavior / Field | Status | Notes |
|---|---|---|
| `solve_board()` return shape preserved | Not verified |  |
| `SolveResult` existing fields preserved | Not verified |  |
| `run_phase1_repair()` callable | Not verified |  |
| `run_phase2_mesa_repair()` callable | Not verified |  |
| `run_phase2_full_repair()` callable | Not verified |  |
| Existing metrics field `coverage` preserved | Not verified |  |
| Existing metrics field `solvable` preserved | Not verified |  |
| Existing metrics field `mine_accuracy` preserved | Not verified |  |
| Existing metrics field `n_unknown` preserved | Not verified |  |
| Existing metrics field `repair_reason` preserved | Not verified |  |
| Existing metrics field `total_time_s` preserved | Not verified |  |
| Existing metrics field `sat_risk` preserved | Not verified |  |
| Existing metrics field `gate_aspect_ratio_within_0_5pct` preserved | Not verified |  |

---

# Open Issues

| ID | Issue | Severity | Blocking? | Next Action |
|---|---|---|---|---|
| RR-001 |  | High / Medium / Low | Yes / No |  |

---

# Implementation Notes By Agent

Use this section for Codex or another implementing agent to record concrete observations during implementation.

## Notes

```text

```

---

# Final Verification Checklist

- [ ] `solver.py` owns unresolved-cell classification.
- [ ] `pipeline.py` owns repair route selection.
- [ ] `repair.py` owns grid mutation and repair move logs.
- [ ] `report.py` owns visual proof artifacts.
- [ ] `sa.py` does not contain repair routing logic.
- [ ] `run_contrast_preprocessing_study.py` remains unchanged unless required by direct compatibility failure.
- [ ] Existing metrics fields are preserved.
- [ ] New route metrics are present.
- [ ] Required route artifacts are generated.
- [ ] Required unit tests exist.
- [ ] Unit tests pass.
- [ ] `assets/image_guard.py` check passes.
- [ ] `run_iter9.py` completes.
- [ ] `run_benchmark.py` completes or fails only on intentional regression gate.
- [ ] Codex review completed.
- [ ] Diff inspected by user.
- [ ] Final commit prepared.

---

# Final Completion Statement

Complete this section only after implementation and verification.

```text
Implementation completed on: YYYY-MM-DD

Summary of completed changes:

Tests run:

Artifacts generated:

Known remaining issues:

Final reviewer:
```
