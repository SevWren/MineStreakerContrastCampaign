# Codex Implementation Plan: Late-Stage Repair Routing + Failure Taxonomy

**Project:** Mine-Streaker / Minesweeper Image Reconstruction  
**Target implementation:** Production repair-routing architecture based on the `line_art_irl_9.png` repair-only campaign findings  
**Primary entry point:** `run_iter9.py`  
**Explicitly out of scope:** `run_contrast_preprocessing_study.py`

---

## 1. Purpose

Implement a production-quality late-stage repair routing layer so the pipeline no longer treats unresolved cells as a generic failure.

The current strategic target is to change the post-solver flow from:

```text
solve → repair attempt → measure
```

to:

```text
solve → classify unresolved failure type → choose targeted repair route → measure → emit visual/logical repair evidence
```

The implementation must make the campaign lesson part of the active codebase:

- `solver.py` explains **why** the board remains stuck.
- `pipeline.py` chooses **what repair route to run next**.
- `repair.py` applies **the smallest targeted repair** and logs exact cause/effect.
- `report.py` renders **visual proof of the repair effect**.
- `run_iter9.py` uses the routed repair path in the main experiment flow.
- `run_benchmark.py` locks the campaign lesson as a regression gate.

---

## 2. Evidence-Based Codebase Facts

The repository contains the active runtime modules required for this implementation:

```text
board_sizing.py
core.py
corridors.py
list_unignored_files.py
pipeline.py
repair.py
report.py
run_benchmark.py
run_iter9.py
run_repair_only_from_grid.py
sa.py
solver.py
AGENTS.md
```

The campaign result directory also exists and contains the repair-only campaign artifacts for:

```text
line_art_robustness_campaign_2_line_art_irl_9_repair_only_last100
```

with per-variant run directories for:

```text
baseline_recheck
phase2_extended_only
last100_only
phase2_extended_then_last100
```

The codebase already contains the key building blocks:

- `solver.py` already has a `SolveResult` structure with solver state and unresolved-cell metrics.
- `repair.py` already has full Phase 2 sealed-cluster repair behavior.
- `run_iter9.py` already imports full Phase 2 repair but still uses the narrower MESA-only repair path in the main flow.
- `pipeline.py` is the correct location for route selection, but it currently does not express the campaign’s late-stage routing lesson.

---

## 3. Non-Negotiable Implementation Constraints

### 3.1 Preserve Existing Behavior

Do not remove or rename existing public functions unless the implementation provides a backward-compatible wrapper.

Existing behavior that must remain callable:

```text
solve_board()
run_phase1_repair()
run_phase2_mesa_repair()
run_phase2_full_repair()
run_sa()
render_report()
```

### 3.2 Preserve Existing Artifacts

Do not rename or remove existing generated artifacts:

```text
metrics_<board>.json
grid_<board>.npy
visual_<board>.png
repair_move_log.jsonl
attempt_meta.json
command_signature
log.txt
```

### 3.3 Do Not Add New Production Dependencies

Use the current dependency family already present in the project:

```text
numpy
scipy
numba
Pillow
matplotlib
```

Use standard-library `unittest` for new tests unless the repository already has another active test framework.

### 3.4 Do Not Silently Run Expensive Fallbacks

The new router must **not** silently rerun SA or adaptive fallback.

If targeted repair does not resolve the board, return a structured decision:

```json
{
  "selected_route": "needs_sa_or_adaptive_rerun",
  "route_result": "unresolved_after_repair",
  "sa_rerun_invoked": false
}
```

### 3.5 Treat Deprecated Study Script As Out Of Scope

Do not modify:

```text
run_contrast_preprocessing_study.py
```

unless changes elsewhere create a direct import, syntax, or compatibility failure.

---

## 4. Required Files To Modify

```text
solver.py
repair.py
pipeline.py
run_iter9.py
report.py
run_benchmark.py
core.py
corridors.py
sa.py
list_unignored_files.py
AGENTS.md
```

---

## 5. Explicitly Out Of Scope

```text
run_contrast_preprocessing_study.py
```

Reason:

`run_contrast_preprocessing_study.py` is a deprecated / one-time contrast-preprocessing study script. It is not part of the active repair-routing architecture. Do not add route fields, summary columns, or tests that depend on it.

---

# Phase 1: Add Solver Failure Taxonomy

## File

```text
solver.py
```

## Objective

Make `solver.py` expose a structured diagnosis of unresolved cells after `solve_board()`.

## Add Dataclass

Add near `SolveResult`:

```python
from dataclasses import dataclass, field

@dataclass
class UnresolvedCluster:
    cluster_id: int
    size: int
    kind: str
    has_safe_neighbor: bool
    external_mine_count: int
    candidate_repair: str
    cells: list[tuple[int, int]] = field(default_factory=list)
    external_mines: list[tuple[int, int]] = field(default_factory=list)
```

## Add Function

```python
def classify_unresolved_clusters(grid: np.ndarray, sr: SolveResult) -> dict:
    """
    Classify remaining UNKNOWN cells after solve_board().

    Categories:
    - no_unknowns
    - sealed_single_mesa
    - sealed_multi_cell_cluster
    - frontier_adjacent_unknown
    - ordinary_ambiguous_unknown
    """
```

## Required Classification Rules

| Condition | `kind` | `candidate_repair` |
|---|---|---|
| `sr.n_unknown == 0` | `no_unknowns` | `none` |
| Unknown cluster size is `1`, has no adjacent `SAFE`, and has external mines | `sealed_single_mesa` | `phase2_full_repair` |
| Unknown cluster size is `>1`, has no adjacent `SAFE`, and has external mines | `sealed_multi_cell_cluster` | `phase2_full_repair` |
| Unknown cluster has adjacent `SAFE` cells | `frontier_adjacent_unknown` | `last100_or_standard_repair` |
| Unknown cluster has no external mines and no adjacent `SAFE` cells | `ordinary_ambiguous_unknown` | `manual_or_future_solver_analysis` |

## Required Return Shape

```python
{
    "n_unknown": int,
    "unknown_cluster_count": int,
    "sealed_single_mesa_count": int,
    "sealed_multi_cell_cluster_count": int,
    "frontier_adjacent_unknown_count": int,
    "ordinary_ambiguous_unknown_count": int,
    "sealed_cluster_count": int,
    "dominant_failure_class": str,
    "recommended_route": str,
    "clusters": list[dict],
}
```

## Required Error Shape

If `sr.state is None`, return:

```python
{
    "n_unknown": sr.n_unknown,
    "unknown_cluster_count": 0,
    "sealed_single_mesa_count": 0,
    "sealed_multi_cell_cluster_count": 0,
    "frontier_adjacent_unknown_count": 0,
    "ordinary_ambiguous_unknown_count": 0,
    "sealed_cluster_count": 0,
    "dominant_failure_class": "unclassified_missing_solver_state",
    "recommended_route": "rerun_solver_full",
    "clusters": []
}
```

## Acceptance Criteria

- Does not mutate `grid`.
- Does not mutate `sr.state`.
- Does not call `solve_board()`.
- Handles `sr.n_unknown == 0`.
- Handles `sr.state is None`.
- Output is JSON-serializable.

---

# Phase 2: Add Sealed-Cluster Detection And Repair Visual Delta

## File

```text
repair.py
```

## Objective

Separate repair detection from repair mutation, and make each accepted repair move auditable.

## Add Function: `find_sealed_unknown_clusters`

```python
def find_sealed_unknown_clusters(grid: np.ndarray, sr, forbidden: np.ndarray) -> list[dict]:
    """
    Return sealed UNKNOWN clusters without mutating the grid.
    Uses sr.state as authoritative solver state.
    """
```

## Required Cluster Record

```python
{
    "cluster_id": int,
    "cluster_size": int,
    "cells": list[tuple[int, int]],
    "has_safe_neighbor": bool,
    "external_mines": list[tuple[int, int]],
    "external_mine_count": int,
    "cluster_kind": "sealed_single_mesa" | "sealed_multi_cell_cluster"
}
```

## Refactor `run_phase2_full_repair`

Keep the existing public signature and return type:

```python
grid, n_fixed, log = run_phase2_full_repair(...)
```

Required changes:

1. Use `find_sealed_unknown_clusters()` for cluster detection.
2. Preserve all existing safety caps and time-budget behavior.
3. Preserve current return type.
4. Preserve legacy log fields.
5. Add new structured log fields.

## Add Function: `compute_repair_visual_delta`

```python
def compute_repair_visual_delta(
    before_grid: np.ndarray,
    after_grid: np.ndarray,
    target: np.ndarray,
) -> dict:
    """
    Compare visual cost before and after a repair move using |N - T| mean absolute error.
    """
```

## Required Return Shape

```python
{
    "mean_abs_error_before": float,
    "mean_abs_error_after": float,
    "visual_delta": float,
    "changed_cells": int,
    "removed_mines": list[tuple[int, int]],
    "added_mines": list[tuple[int, int]]
}
```

## Extend Phase 2 Log Entries

Preserve existing keys such as:

```text
cluster_size
removed_mine
removed_mines
move_type
T_removed
delta_unk
```

Add:

```python
{
    "repair_stage": "phase2_full",
    "cluster_id": int,
    "cluster_kind": str,
    "n_unknown_before": int,
    "n_unknown_after": int,
    "delta_unknown": int,
    "mean_abs_error_before": float,
    "mean_abs_error_after": float,
    "visual_delta": float,
    "accepted": True
}
```

## Acceptance Criteria

- `run_phase2_full_repair()` remains backward compatible.
- `delta_unk` remains present.
- `delta_unknown` is added.
- `forbidden == 1` cells remain mine-free after accepted moves.
- All new log records are JSON-serializable.

---

# Phase 3: Add Repair Route Contract

## File

```text
pipeline.py
```

## Objective

Make `pipeline.py` own the decision of which late-stage repair route to run.

## Add Dataclass: `RepairRoutingConfig`

```python
@dataclass
class RepairRoutingConfig:
    phase2_budget_s: float = 360.0
    last100_budget_s: float = 300.0
    last100_unknown_threshold: int = 100
    solve_max_rounds: int = 300
    trial_max_rounds: int = 60
    enable_phase2: bool = True
    enable_last100: bool = True
    enable_sa_rerun: bool = False
```

## Add Dataclass: `RepairRouteResult`

```python
@dataclass
class RepairRouteResult:
    grid: np.ndarray
    sr: object
    selected_route: str
    route_result: str
    failure_taxonomy: dict
    phase2_log: list
    last100_log: list
    visual_delta_summary: dict
    decision: dict
```

## Add Function: `route_late_stage_failure`

```python
def route_late_stage_failure(
    grid: np.ndarray,
    target: np.ndarray,
    weights: np.ndarray,
    forbidden: np.ndarray,
    sr,
    config: RepairRoutingConfig,
) -> RepairRouteResult:
    """
    Choose the cheapest next intervention based on unresolved-cell diagnosis.
    """
```

## Required Route Order

### Route 1: Already Solved

If `sr.n_unknown == 0`:

```text
selected_route = "already_solved"
route_result = "solved"
```

No repair function is called.

### Route 2: Phase 2 Full Repair

If taxonomy reports sealed clusters and Phase 2 is enabled:

```text
selected_route = "phase2_full_repair"
```

Call:

```python
run_phase2_full_repair(...)
```

Then rerun:

```python
solve_board(..., mode="full")
```

If final `n_unknown == 0`:

```text
route_result = "solved"
```

### Route 3: Last-100 Repair

If unknown count is at or below `last100_unknown_threshold` and Last-100 is enabled:

```text
selected_route = "last100_repair"
```

Use existing Last-100 behavior.

If the current Last-100 logic only exists inside `run_repair_only_from_grid.py`, extract the existing behavior into `repair.py` as:

```python
def run_last100_repair(...):
    ...
```

Do not invent unrelated Last-100 behavior.

### Route 4: Unresolved

If no targeted route resolves the board:

```text
selected_route = "needs_sa_or_adaptive_rerun"
route_result = "unresolved_after_repair"
sa_rerun_invoked = false
```

## Add Function: `write_repair_route_artifacts`

```python
def write_repair_route_artifacts(
    out_dir: str,
    board_label: str,
    route_result: RepairRouteResult,
) -> dict:
    """
    Write failure_taxonomy.json, repair_route_decision.json, visual_delta_summary.json.
    Return artifact paths.
    """
```

## Acceptance Criteria

- `route_late_stage_failure()` is importable from `run_iter9.py`.
- No SA rerun is called inside the router.
- The route always returns structured output.
- The route decision is JSON-serializable.
- Artifact writer creates:
  - `failure_taxonomy.json`
  - `repair_route_decision.json`
  - `visual_delta_summary.json`

---

# Phase 4: Update Main Iteration Flow

## File

```text
run_iter9.py
```

## Objective

Replace direct MESA-only repair in the main path with late-stage repair routing.

## Required Change

Replace the active main-path call to:

```python
run_phase2_mesa_repair(...)
```

with:

```python
route_late_stage_failure(...)
```

## Required New Flow

```python
print("  Late-stage repair routing:", flush=True)

routing_config = RepairRoutingConfig(
    phase2_budget_s=360.0,
    last100_budget_s=300.0,
    last100_unknown_threshold=100,
    solve_max_rounds=300,
    trial_max_rounds=60,
    enable_phase2=True,
    enable_last100=True,
    enable_sa_rerun=False,
)

route = route_late_stage_failure(
    grid=grid,
    target=target_eval,
    weights=w_zone,
    forbidden=forbidden,
    sr=sr_p1,
    config=routing_config,
)

grid = route.grid
grid[forbidden == 1] = 0
assert_board_valid(grid, forbidden, "post-late-stage-routing")
sr_p2 = route.sr
```

## Add Metrics

Add these metrics while preserving all existing metrics:

```python
"repair_route_selected": route.selected_route,
"repair_route_result": route.route_result,
"dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
"sealed_cluster_count": route.failure_taxonomy.get("sealed_cluster_count"),
"sealed_single_mesa_count": route.failure_taxonomy.get("sealed_single_mesa_count"),
"sealed_multi_cell_cluster_count": route.failure_taxonomy.get("sealed_multi_cell_cluster_count"),
"phase2_fixes": len(route.phase2_log),
"last100_fixes": len(route.last100_log),
"visual_delta": route.visual_delta_summary.get("visual_delta"),
"phase2": "full_cluster_repair",
```

## Write Route Artifacts

After metrics are written:

```python
route_artifacts = write_repair_route_artifacts(
    OUT_DIR,
    f"{BW}x{BH}",
    route,
)
```

Add paths to metrics:

```python
"failure_taxonomy_path": route_artifacts["failure_taxonomy"],
"repair_route_decision_path": route_artifacts["repair_route_decision"],
"visual_delta_summary_path": route_artifacts["visual_delta_summary"],
```

## Acceptance Criteria

- Terminal output uses `Late-stage repair routing`.
- Main path no longer directly calls `run_phase2_mesa_repair()`.
- `run_phase2_mesa_repair()` remains available for compatibility.
- Metrics include route fields.
- Route JSON artifacts are written under `results/iter9`.

---

# Phase 5: Add Repair Overlay Rendering

## File

```text
report.py
```

## Objective

Generate a visual artifact showing what repair changed.

## Add Function

```python
def render_repair_overlay(
    target: np.ndarray,
    grid_before: np.ndarray,
    grid_after: np.ndarray,
    sr_before,
    sr_after,
    repair_log: list,
    save_path: str,
    dpi: int = 120,
) -> None:
    """
    Render repair cause/effect overlay.

    Panels:
    1. Target image
    2. Before repair UNKNOWN cells
    3. After repair UNKNOWN cells
    4. Removed mines overlay
    5. Error delta |N_after - T| - |N_before - T|
    6. Text summary of route and repair counts
    """
```

## Output Artifact

```text
repair_overlay_<board>.png
```

Example:

```text
results/iter9/repair_overlay_300x942.png
```

## Acceptance Criteria

- Works with empty `repair_log`.
- Works when `sr_before.state is None`.
- Works when `sr_after.state is None`.
- Uses non-interactive matplotlib backend.
- Does not alter `render_report()` behavior.

---

# Phase 6: Add Sealed-Cluster Risk Diagnostics

## File

```text
core.py
```

## Objective

Add a pre-solver diagnostic that estimates saturation / sealing risk.

## Add Function

```python
def compute_sealed_cluster_risk_map(
    target: np.ndarray,
    grid: np.ndarray | None = None,
    high_target_threshold: float = 5.5,
    dense_neighbor_threshold: int = 5,
) -> dict:
    """
    Estimate regions likely to create solver-inaccessible clusters.
    """
```

## Required Output

```python
{
    "sat_risk_cells": int,
    "high_target_dense_components": int,
    "predicted_sealed_cluster_risk": "none" | "low" | "medium" | "high",
    "high_target_threshold": float,
    "dense_neighbor_threshold": int
}
```

## Acceptance Criteria

- Works with only `target`.
- If `grid` is supplied, include optional mine-density overlap stats.
- Does not change existing target generation.
- Does not add a new dependency.

---

# Phase 7: Add Corridor Access Diagnostics

## File

```text
corridors.py
```

## Objective

Measure whether unresolved clusters are isolated from corridor routes.

## Add Function

```python
def analyze_corridor_access_to_unknowns(forbidden: np.ndarray, sr) -> dict:
    """
    Measure whether unresolved clusters are near corridor paths.
    """
```

## Required Output

```python
{
    "unknown_cells": int,
    "unknown_clusters_touching_corridor": int,
    "mean_distance_unknown_to_corridor": float | None,
    "sealed_clusters_isolated_from_corridor": int
}
```

## Acceptance Criteria

- Uses `sr.state == UNKNOWN` for unknown cells.
- Uses `forbidden == 1` as the corridor mask.
- If no unknown cells exist, returns zero counts and `None` for mean distance.
- Does not mutate `forbidden`.
- Does not mutate `sr.state`.
- Output is JSON-serializable.

---

# Phase 8: Add SA Output Diagnostics

## File

```text
sa.py
```

## Objective

Add diagnostics about SA output without changing SA behavior.

## Add Function

```python
def summarize_sa_output(
    grid: np.ndarray,
    target: np.ndarray,
    forbidden: np.ndarray,
) -> dict:
    """
    Return density, local mine-density risk, target saturation overlap,
    and corridor compliance.
    """
```

## Required Output

```python
{
    "mine_density": float,
    "forbidden_mine_count": int,
    "forbidden_violation": bool,
    "high_target_mine_overlap_count": int,
    "high_target_mine_overlap_pct": float
}
```

## Acceptance Criteria

- Do not modify `_sa_kernel`.
- Do not change `run_sa()` return type.
- Do not add routing behavior to `sa.py`.
- Output is JSON-serializable.

---

# Phase 9: Add Regression Gates

## File

```text
run_benchmark.py
```

## Objective

Lock the campaign finding as a regression case.

## Add Regression Case

```python
REGRESSION_CASES = [
    {
        "name": "line_art_irl_9_phase2_full_repair",
        "image_name": "line_art_irl_9.png",
        "board": "300x942",
        "seeds": [11, 22, 33],
        "expected_baseline_unknowns": [89, 20, 37],
        "expected_final_unknown": 0,
        "expected_route": "phase2_full_repair",
    }
]
```

## Add Result Fields

```text
repair_route_selected
repair_route_result
dominant_failure_class
sealed_cluster_count
phase2_fixes
last100_fixes
visual_delta
```

## Required Gate

A regression row passes only when:

```text
repair_route_selected == "phase2_full_repair"
n_unknown == 0
coverage >= 0.9999
solvable is True
last100_fixes == 0
```

## Acceptance Criteria

- Existing benchmark summary still prints.
- New regression result is written into benchmark output JSON.
- Benchmark fails loudly if the known case no longer routes through Phase 2 full repair.

---

# Phase 10: Keep Deprecated Contrast Study Out Of Scope

## File

```text
run_contrast_preprocessing_study.py
```

## Decision

Do not modify this file.

## Reason

This file is treated as deprecated / one-time study infrastructure. It is not required for:

- unresolved-cell failure taxonomy
- Phase 2 full repair routing
- Last-100 fallback routing
- repair route artifacts
- repair overlay reporting
- Iteration 9 routing behavior
- benchmark regression gates

## Required Codex Behavior

Codex must not edit this file unless a direct compile/import issue is caused by changes elsewhere.

## Acceptance Criteria

- `run_contrast_preprocessing_study.py` remains unchanged.
- No new routing logic is added to it.
- No new summary columns are added to it.
- No new tests depend on it.

---

# Phase 11: Improve Digest File Listing Reliability

## File

```text
list_unignored_files.py
```

## Objective

Make future repository digests more reliable.

## Add Function

```python
def collect_git_tracked_and_unignored_files(root: Path) -> list[Path]:
    """
    Prefer git ls-files / git check-ignore when available.
    Fall back to current pattern matcher otherwise.
    """
```

## Required Behavior

1. If Git is available and `root` is inside a Git repository:
   - use `git ls-files` for tracked files
   - include untracked but not ignored files if the current script already includes them
2. If Git is unavailable:
   - use existing pattern-based collection logic
3. Do not include generated binary result artifacts by default unless explicitly requested.

## Acceptance Criteria

- Existing script behavior remains available.
- New Git-native path is deterministic.
- Output file order is stable.
- Fallback mode still works outside a Git repository.

---

# Phase 12: Update Agent Instructions

## File

```text
AGENTS.md
```

## Add Section

```markdown
## Late-Stage Repair Routing Contract

When modifying solver/repair/pipeline behavior:

- `solver.py` owns unresolved-cell classification.
- `pipeline.py` owns repair route selection.
- `repair.py` owns grid mutation and repair move logs.
- `report.py` owns visual proof artifacts.
- `sa.py` must not contain repair routing logic.
- Existing metrics fields must not be removed.
- New artifacts must be written under `results/`.
- Generated root-level ad-hoc files are forbidden.
- Deprecated study scripts must not be modified unless required for direct compatibility.
```

## Acceptance Criteria

- AGENTS.md explains the ownership boundaries.
- AGENTS.md explicitly says `sa.py` must not own routing.
- AGENTS.md prevents generated root-level clutter.

---

# 6. Required New Artifacts

Every routed production run should be able to write:

```text
metrics_<board>.json
grid_<board>.npy
visual_<board>.png
repair_move_log.jsonl
repair_overlay_<board>.png
failure_taxonomy.json
repair_route_decision.json
visual_delta_summary.json
```

---

## 6.1 `failure_taxonomy.json`

Required schema:

```json
{
  "n_unknown": 37,
  "unknown_cluster_count": 9,
  "sealed_single_mesa_count": 0,
  "sealed_multi_cell_cluster_count": 9,
  "frontier_adjacent_unknown_count": 0,
  "ordinary_ambiguous_unknown_count": 0,
  "sealed_cluster_count": 9,
  "dominant_failure_class": "sealed_multi_cell_cluster",
  "recommended_route": "phase2_full_repair",
  "clusters": []
}
```

---

## 6.2 `repair_route_decision.json`

Required schema:

```json
{
  "solver_n_unknown_before": 37,
  "dominant_failure_class": "sealed_multi_cell_cluster",
  "recommended_route": "phase2_full_repair",
  "selected_route": "phase2_full_repair",
  "phase2_budget_s": 360.0,
  "last100_budget_s": 300.0,
  "last100_invoked": false,
  "sa_rerun_invoked": false,
  "solver_n_unknown_after": 0,
  "route_result": "solved"
}
```

---

## 6.3 `visual_delta_summary.json`

Required schema:

```json
{
  "mean_abs_error_before": 1.1692,
  "mean_abs_error_after": 1.1694,
  "visual_delta": 0.0002,
  "changed_cells": 1,
  "removed_mines": [[617, 176]],
  "added_mines": []
}
```

---

# 7. Test Plan

## 7.1 Add Test Directory

```text
tests/
```

## 7.2 Add Test Files

```text
tests/test_solver_failure_taxonomy.py
tests/test_repair_visual_delta.py
tests/test_repair_route_decision.py
tests/test_digest_file_listing.py
```

---

## 7.3 `tests/test_solver_failure_taxonomy.py`

Required tests:

1. **No unknowns**
   - Fake or build `SolveResult` with `n_unknown = 0`.
   - Assert `dominant_failure_class == "no_unknowns"`.

2. **Missing solver state**
   - `sr.state is None`.
   - Assert `dominant_failure_class == "unclassified_missing_solver_state"`.

3. **Sealed single MESA**
   - Synthetic small board with one unknown safe cell enclosed by mines.
   - Assert `sealed_single_mesa_count == 1`.

4. **Sealed multi-cell cluster**
   - Synthetic small board with connected unknown cells and no adjacent safe state.
   - Assert `sealed_multi_cell_cluster_count >= 1`.

5. **Frontier-adjacent unknown**
   - Unknown cell adjacent to `SAFE`.
   - Assert `frontier_adjacent_unknown_count >= 1`.

---

## 7.4 `tests/test_repair_visual_delta.py`

Required tests:

1. Removing one mine produces JSON-serializable visual delta.
2. `changed_cells` equals count of differing cells.
3. `removed_mines` is populated when a mine is removed.
4. `added_mines` is populated when a mine is added.

---

## 7.5 `tests/test_repair_route_decision.py`

Required tests:

1. `sr.n_unknown == 0` routes to `already_solved`.
2. Sealed cluster taxonomy routes to `phase2_full_repair`.
3. If Phase 2 is disabled and unknown count is under threshold, the router reaches Last-100 path if implemented.
4. If unresolved after available repairs, router returns `needs_sa_or_adaptive_rerun` without running SA.

---

## 7.6 `tests/test_digest_file_listing.py`

Required tests:

1. Git-native file collection returns stable sorted results.
2. Fallback file collection works outside a Git repository.
3. Generated binary result artifacts are excluded unless explicitly requested.

---

# 8. Required Validation Commands

Run from repository root:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python assets/image_guard.py --path assets/input_source_image.png
python run_iter9.py
python run_benchmark.py
```

If `run_benchmark.py` is too expensive for a normal local loop, add a lightweight regression mode rather than skipping regression validation.

Example acceptable CLI addition:

```powershell
python run_benchmark.py --regression-only
```

Do not add this flag unless it is fully implemented and documented.

---

# 9. Definition Of Done

The implementation is complete only when every item below is true.

## 9.1 Code Behavior

- `solver.py` exposes `UnresolvedCluster`.
- `solver.py` exposes `classify_unresolved_clusters()`.
- `repair.py` exposes `find_sealed_unknown_clusters()`.
- `repair.py` exposes `compute_repair_visual_delta()`.
- `pipeline.py` exposes:
  - `RepairRoutingConfig`
  - `RepairRouteResult`
  - `route_late_stage_failure()`
  - `write_repair_route_artifacts()`
- `run_iter9.py` uses `route_late_stage_failure()` in the main repair path.
- `run_iter9.py` no longer directly calls `run_phase2_mesa_repair()` in the main repair path.
- `report.py` exposes `render_repair_overlay()`.
- `core.py` exposes `compute_sealed_cluster_risk_map()`.
- `corridors.py` exposes `analyze_corridor_access_to_unknowns()`.
- `sa.py` exposes `summarize_sa_output()`.
- `list_unignored_files.py` exposes `collect_git_tracked_and_unignored_files()`.

## 9.2 Artifact Behavior

A routed `run_iter9.py` execution writes:

```text
failure_taxonomy.json
repair_route_decision.json
visual_delta_summary.json
repair_overlay_<board>.png
```

## 9.3 Metrics Behavior

`metrics_<board>.json` includes:

```text
repair_route_selected
repair_route_result
dominant_failure_class
sealed_cluster_count
sealed_single_mesa_count
sealed_multi_cell_cluster_count
phase2_fixes
last100_fixes
visual_delta
failure_taxonomy_path
repair_route_decision_path
visual_delta_summary_path
```

## 9.4 Backward Compatibility

Existing metrics fields remain:

```text
coverage
solvable
mine_accuracy
n_unknown
repair_reason
total_time_s
sat_risk
phase2
gate_aspect_ratio_within_0_5pct
```

## 9.5 Deprecated Study Script

```text
run_contrast_preprocessing_study.py
```

remains unchanged unless required to fix a direct compatibility failure caused by the routing implementation.

## 9.6 Test Behavior

These commands complete successfully:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python assets/image_guard.py --path assets/input_source_image.png
python run_iter9.py
```

## 9.7 Review Behavior

Run Codex review after implementation.

Required review focus:

- No unrelated refactors.
- No generated root-level clutter.
- No route logic inside `sa.py`.
- No edits to `run_contrast_preprocessing_study.py`.
- Route artifacts are written under `results/`.
- Existing public function signatures remain compatible.

---

# 10. Codex Execution Prompt

Paste the following into the OpenAI Codex app:

```markdown
Implement the late-stage repair routing architecture described below.

Repository context:
- This is a Python research codebase for Minesweeper-board reconstruction.
- Root runtime modules include `core.py`, `sa.py`, `solver.py`, `corridors.py`, `repair.py`, `report.py`, and `pipeline.py`.
- Main entry scripts include `run_iter9.py`, `run_benchmark.py`, and `run_repair_only_from_grid.py`.
- Generated artifacts belong under `results/`.
- Obey `AGENTS.md`.

Goal:
Change the post-solver flow from:
`solve → repair attempt → measure`

to:
`solve → classify unresolved failure type → choose targeted repair route → measure → emit visual/logical repair evidence`

Required changes:

1. In `solver.py`
   - Add `UnresolvedCluster`.
   - Add `classify_unresolved_clusters(grid, sr) -> dict`.
   - Classify:
     - `no_unknowns`
     - `sealed_single_mesa`
     - `sealed_multi_cell_cluster`
     - `frontier_adjacent_unknown`
     - `ordinary_ambiguous_unknown`
   - Return summary counts, dominant failure class, recommended route, and clusters.

2. In `repair.py`
   - Add `find_sealed_unknown_clusters(grid, sr, forbidden) -> list[dict]`.
   - Refactor `run_phase2_full_repair()` to use that detection helper while preserving its public signature and return type.
   - Add `compute_repair_visual_delta(before_grid, after_grid, target) -> dict`.
   - Extend Phase 2 log entries with:
     - `repair_stage`
     - `cluster_id`
     - `cluster_kind`
     - `n_unknown_before`
     - `n_unknown_after`
     - `delta_unknown`
     - `mean_abs_error_before`
     - `mean_abs_error_after`
     - `visual_delta`
     - `accepted`
   - Preserve legacy keys including `cluster_size`, `removed_mine`, `removed_mines`, `move_type`, `T_removed`, and `delta_unk`.

3. In `pipeline.py`
   - Add `RepairRoutingConfig`.
   - Add `RepairRouteResult`.
   - Add `route_late_stage_failure(grid, target, weights, forbidden, sr, config)`.
   - Add `write_repair_route_artifacts(out_dir, board_label, route_result)`.
   - Route order:
     1. already solved
     2. Phase 2 full repair for sealed clusters
     3. Last-100 repair if implemented and unknown count is at or below threshold
     4. structured unresolved result requiring future SA/adaptive rerun
   - Do not silently run SA from the router.

4. In `run_iter9.py`
   - Replace the direct `run_phase2_mesa_repair()` main-path call with `route_late_stage_failure()`.
   - Print `Late-stage repair routing`.
   - Add route fields to metrics.
   - Write route artifacts under `results/iter9`.
   - Keep existing metrics fields.

5. In `report.py`
   - Add `render_repair_overlay(...)`.
   - Render target, before unknowns, after unknowns, removed mines, error delta, and text summary.
   - Do not alter `render_report()` behavior.

6. In `core.py`
   - Add `compute_sealed_cluster_risk_map(target, grid=None, high_target_threshold=5.5, dense_neighbor_threshold=5)`.

7. In `corridors.py`
   - Add `analyze_corridor_access_to_unknowns(forbidden, sr)`.

8. In `sa.py`
   - Add `summarize_sa_output(grid, target, forbidden)`.
   - Do not modify `_sa_kernel`.
   - Do not change `run_sa()` return type.
   - Do not add routing logic to `sa.py`.

9. In `run_benchmark.py`
   - Add regression fields for repair route, dominant failure class, sealed cluster count, Phase 2 fixes, Last-100 fixes, and visual delta.
   - Add a known regression case for `line_art_irl_9.png`, board `300x942`, seeds `[11, 22, 33]`, expected final `n_unknown = 0`, expected route `phase2_full_repair`.

10. Do not modify `run_contrast_preprocessing_study.py`.
    - Treat it as deprecated / one-time study infrastructure.
    - It is out of scope unless changes elsewhere create a direct import, syntax, or compatibility failure.
    - Do not add repair routing fields to it.
    - Do not add summary columns to it.
    - Do not add tests that depend on it.

11. In `list_unignored_files.py`
    - Add a Git-native collection path using `git ls-files` / `git check-ignore` where available.
    - Keep the current fallback behavior.

12. In `AGENTS.md`
    - Add a late-stage repair routing contract:
      - `solver.py` owns unresolved-cell classification.
      - `pipeline.py` owns repair route selection.
      - `repair.py` owns grid mutation and repair move logs.
      - `report.py` owns visual proof artifacts.
      - `sa.py` must not contain repair routing logic.
      - Existing metrics fields must not be removed.
      - New artifacts must be written under `results/`.
      - Deprecated study scripts must not be modified unless required for direct compatibility.

Testing:
- Add standard-library `unittest` tests under `tests/`.
- Run:
  `python -m unittest discover -s tests -p "test_*.py"`
  `python assets/image_guard.py --path assets/input_source_image.png`
  `python run_iter9.py`

Do not remove existing public functions.
Do not rename existing artifacts.
Do not add new production dependencies.
Do not perform unrelated refactors.
Do not modify `run_contrast_preprocessing_study.py` unless required for direct compatibility.
```

---

# 11. Codex Workflow

1. Open the repository in the Codex app.
2. Start this work in a separate worktree.
3. Paste the Codex execution prompt.
4. Let Codex edit the files.
5. Run the validation commands.
6. Use Codex review.
7. Inspect the diff manually.
8. Commit only after:
   - route artifacts exist,
   - tests pass,
   - `run_iter9.py` writes route metrics,
   - `run_contrast_preprocessing_study.py` remains unchanged,
   - no unrelated refactors are present.

---

# 12. Final Architectural Target

After implementation, the codebase ownership should be:

```text
board_sizing.py
  decides board dimensions safely

core.py
  builds target image, weights, number fields, and pre-solver risk signals

corridors.py
  builds mine-free corridors and analyzes corridor access to unresolved cells

sa.py
  optimizes mine grids and reports SA output diagnostics

solver.py
  solves the board and classifies unresolved failure type

repair.py
  applies targeted repairs and logs exact local cause/effect

pipeline.py
  chooses route: already solved → Phase 2 full repair → Last-100 → unresolved fallback decision

run_iter9.py
  active experiment entry point using the routed repair architecture

run_benchmark.py
  regression gate for known failure families

report.py
  renders visual proof, including repair overlays

list_unignored_files.py
  produces reliable future repository digests

AGENTS.md
  documents ownership boundaries for future Codex/LLM work

run_contrast_preprocessing_study.py
  deprecated / one-time study script; unchanged
```

The core implementation principle is:

```text
The solver explains why the board is stuck.
The pipeline chooses the next repair route.
The repair module changes the grid.
The report module proves what changed.
The benchmark locks the behavior so it does not regress.
```
