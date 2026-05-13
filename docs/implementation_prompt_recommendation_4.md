# Execution Prompt: Implement Recommendation 4 — Fully Specified Partial-Phase2 Route State

## What This Implements

Phase 2 can mutate the grid and reduce unknowns, but the current unresolved fallback in `pipeline.py` reports `selected_route="needs_sa_or_adaptive_rerun"` and loses all partial Phase 2 route state. This implementation fixes the producer, all transformers, all serializers, all consumers, all schemas, and all tests so every surface describes the same routed state using a four-field model: `selected_route`, `route_result`, `route_outcome_detail`, `next_recommended_route`.

**This does not change Phase 2 search behavior. It only changes how existing route state is produced, persisted, copied, summarized, and explained.**

---

## Non-Goals — Do Not Do Any of These

- Change Phase 2 search behavior
- Make visual error the Phase 2 acceptance criterion
- Reinterpret Phase 1 changes as route changes
- Label partial Phase 2 progress as solved
- Use `phase2_full_repair_hit_time_budget=false` to imply Phase 2 was not invoked
- Add `legacy_repair_route_selected`
- Preserve old `selected_route` semantics in any schema, fixture, row, summary, report, or README example

---

## Current Code State (Starting Conditions)

| File | Lines | Current broken state |
|---|---|---|
| `pipeline.py` | 55–66 | `RepairRouteResult` lacks `route_outcome_detail`, `next_recommended_route`, and all phase count/state fields |
| `pipeline.py` | 82–95 | Default `selected_route` initialized as `"needs_sa_or_adaptive_rerun"` |
| `pipeline.py` | 97–107 | Already-solved branch emits no `route_outcome_detail` or `next_recommended_route` |
| `pipeline.py` | 109–142 | Sets `selected_route="phase2_full_repair"` only when solved; partial progress falls through |
| `pipeline.py` | 144–177 | No complete Last100 route outcome detail or explicit counts |
| `pipeline.py` | 179–188 | Returns `selected_route="needs_sa_or_adaptive_rerun"` even after Phase 2 ran |
| `pipeline.py` | 191–226 | Uses `setdefault(...)` to fill missing fields; must not infer route state |
| `run_iter9.py` | 842–852 | Uses only `repair_route_selected`; no four-field model |
| `run_iter9.py` | 939–971 | Uses old `repair_reason`, `repair_route_selected`, `repair_route_result`, `phase2_fixes`, `last100_fixes` |
| `run_iter9.py` | 1074–1085 | Missing `route_outcome_detail`, `next_recommended_route`, explicit phase fields |
| `run_iter9.py` | 392–408, 1136–1144 | LLM summary says run ended "through `needs_sa_or_adaptive_rerun`" |
| `run_iter9.py` | 56–75, 1189–1212, 1236–1256, 1269–1309, 1391–1408, 1500–1510 | Sweep rows carry `repair_route_selected` only |
| `run_benchmark.py` | 544–554 | Uses only `repair_route_selected` |
| `run_benchmark.py` | 634–645 | Missing `route_outcome_detail`, `next_recommended_route`, phase counts |
| `run_benchmark.py` | 668–701 | Uses old field names |
| `run_benchmark.py` | 737–766 | Converts using old route fields |
| `run_benchmark.py` | 806–853 | Markdown table shows `repair_route_selected` only |
| `run_benchmark.py` | 888–909 | CSV lacks new route-state columns |
| `run_benchmark.py` | 947–1004, 1035–1055 | Regression checks use `repair_route_selected` |
| `report.py` | 312–349 | Reads `repair_route_selected` only |

---

## Accepted-Move-Count Invariant (Read Before Writing Any Code)

For every repair route invocation the following must always hold:

```python
accepted_move_count = sum(1 for e in repair_log if e["accepted"] == True)
                    == repair_result.n_fixed    # for Phase2
                    == repair_result.n_fixes    # for Last100
```

**Why this matters:**
- `repair.py::run_last100_repair()` appends log entries for BOTH accepted moves (`"accepted": True`) and rejected moves (`"accepted": False`). Current code uses `len(last100_log)` which overcounts. This is a confirmed bug.
- Phase2 currently only logs accepted moves so `len(phase2_log) == n_fixed` today, but the defensive recount catches any future refactor that adds rejected-move logging.
- All three artifact consumers — `repair_route_decision.json`, `metrics_iter9_*.json`, `visual_delta_summary.json` — must report the same accepted count.

**Enforcement points:**
1. Serializer guard in `pipeline.py::write_repair_route_artifacts()` — raises `RouteStateInvariantError` and aborts artifact write if invariant is violated
2. Test assertions in Step 1
3. Forensic rerun probe in Step 7

---

## Four-Field Route-State Contract

Every route-state surface must expose exactly these four primary fields:

```text
selected_route         — The route family actually invoked ("none", "already_solved",
                         "phase2_full_repair", "last100_repair")
route_result           — "solved" or "unresolved_after_repair"
route_outcome_detail   — Precise outcome; must be one of the 11 enum values below
next_recommended_route — null when solved; "needs_sa_or_adaptive_rerun" when unresolved
                         and no further route is available; "last100_repair" when
                         Phase 2 is unresolved and config.enable_last100 is True
```

`"needs_sa_or_adaptive_rerun"` is valid ONLY in `next_recommended_route`. It must NEVER appear in `selected_route`.

### State Transition Table

| Condition | `selected_route` | `route_result` | `route_outcome_detail` | `next_recommended_route` |
|---|---|---|---|---|
| Already solved (`sr.n_unknown == 0`) | `already_solved` | `solved` | `already_solved_before_routing` | `None` |
| Phase 2 invoked → solved | `phase2_full_repair` | `solved` | `phase2_full_repair_solved` | `None` |
| Phase 2 invoked → partial (n < before) | `phase2_full_repair` | `unresolved_after_repair` | `phase2_full_repair_partial_progress_unresolved` | `"last100_repair"` if enabled, else `"needs_sa_or_adaptive_rerun"` |
| Phase 2 invoked → no-op (n == before, grid changed) | `phase2_full_repair` | `unresolved_after_repair` | `phase2_full_repair_no_op` | `"last100_repair"` if enabled, else `"needs_sa_or_adaptive_rerun"` |
| Phase 2 invoked → no accepted moves | `phase2_full_repair` | `unresolved_after_repair` | `phase2_full_repair_no_accepted_moves` | `"last100_repair"` if enabled, else `"needs_sa_or_adaptive_rerun"` |
| Last100 invoked → solved | `last100_repair` | `solved` | `last100_repair_solved` | `None` |
| Last100 invoked → timeout | `last100_repair` | `unresolved_after_repair` | `last100_repair_timeout_unresolved` | `"needs_sa_or_adaptive_rerun"` |
| Last100 invoked → partial | `last100_repair` | `unresolved_after_repair` | `last100_repair_partial_progress_unresolved` | `"needs_sa_or_adaptive_rerun"` |
| No route invoked | `none` | `unresolved_after_repair` | `no_late_stage_route_invoked` | `"needs_sa_or_adaptive_rerun"` |

### `route_outcome_detail` Enum — Only These 11 Values Are Permitted

```
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

---

## Execution Order

### Step 0 — Governance (Before Any Code Changes)

**0a. Amend `AGENTS.md`** — find the regression-only clause and replace it.

Find:
```
`run_benchmark.py --regression-only` is a fixed-case mode and must preserve stable behavior.
When `--regression-only` is set, explicit normal-mode flags must remain rejected as currently implemented.
```

Replace with:
```
`run_benchmark.py --regression-only` is a fixed-case mode and must preserve stable case selection, validation gates, and explicit normal-mode flag rejection. Route-state field semantics may be corrected when required by an approved route-state contract, but regression-only outputs, checks, docs, and expected-route comparisons must be updated consistently in the same change.
When `--regression-only` is set, explicit normal-mode flags must remain rejected as currently implemented.
```

**0b. Populate `for_user_review.md`** — add this content:

```
applicability: Iter9 metrics, repair route decision artifacts, visual delta summary artifacts,
  repair overlays, image-sweep summaries, normal benchmark child metrics, normal benchmark
  summaries, benchmark_results.json, regression-only output, and report text.
impact: selected_route now means the invoked route; needs_sa_or_adaptive_rerun moves to
  next_recommended_route for unresolved follow-up work.
transition: repair_route_selected may remain only as an exact alias of selected_route in
  newly written artifacts; consumers must read next_recommended_route for follow-up strategy.
validation evidence: targeted tests, full test suite, help checks, image guard check, and
  the forensic rerun path.
```

---

### Step 1 — Add Failing Tests First

Update each test file so the assertions below exist and FAIL before any production code changes. Run each file to confirm failure before proceeding.

```bash
python -m unittest tests.test_repair_route_decision
python -m unittest tests.test_route_artifact_metadata
python -m unittest tests.test_benchmark_layout
python -m unittest tests.test_source_image_cli_contract
python -m unittest tests.test_iter9_image_sweep_contract
python -m unittest tests.test_report_explanations
```

**`tests/test_repair_route_decision.py`** — assert all six branches against the four-field model:

```text
No-route unresolved:
  selected_route == "none"
  route_result == "unresolved_after_repair"
  route_outcome_detail == "no_late_stage_route_invoked"
  next_recommended_route == "needs_sa_or_adaptive_rerun"

Already-solved:
  selected_route == "already_solved"
  route_result == "solved"
  route_outcome_detail == "already_solved_before_routing"
  next_recommended_route is None

Phase 2 solved:
  selected_route == "phase2_full_repair"
  route_result == "solved"
  route_outcome_detail == "phase2_full_repair_solved"
  next_recommended_route is None

Phase 2 partial (new test — currently missing):
  selected_route == "phase2_full_repair"
  route_result == "unresolved_after_repair"
  route_outcome_detail == "phase2_full_repair_partial_progress_unresolved"
  next_recommended_route == "needs_sa_or_adaptive_rerun"

Last100 solved:
  selected_route == "last100_repair"
  route_result == "solved"
  route_outcome_detail == "last100_repair_solved"
  next_recommended_route is None

Last100 unresolved:
  selected_route == "last100_repair"
  route_result == "unresolved_after_repair"
  route_outcome_detail in {
    "last100_repair_partial_progress_unresolved",
    "last100_repair_no_accepted_moves",
    "last100_repair_timeout_unresolved"
  }
  next_recommended_route == "needs_sa_or_adaptive_rerun"
```

**`tests/test_route_artifact_metadata.py`** — assert `repair_route_decision.json` contains all four primary fields: `selected_route`, `route_result`, `route_outcome_detail`, `next_recommended_route`.

**`tests/test_benchmark_layout.py`** — assert `phase2_fixes == phase2_full_repair_accepted_move_count` in child metrics; assert benchmark summary rows contain all four fields.

**`tests/test_source_image_cli_contract.py`** — assert new route-state fields propagate through CLI output.

**`tests/test_iter9_image_sweep_contract.py`** — assert sweep rows contain all four fields; assert skipped-existing rows do not synthesize `selected_route` from `repair_route_selected`.

**`tests/test_report_explanations.py`** — assert report reads `selected_route` for performed route and `next_recommended_route` for next action; assert no fallback to `repair_route_selected`.

Also add producer-level invariant tests asserting `_build_route_result(...)` raises `ValueError` when:
- `decision["solver_n_unknown_after"] != int(sr.n_unknown)`
- `decision["selected_route"] == "needs_sa_or_adaptive_rerun"`
- `phase2_full_repair_invoked == True` and `last100_invoked == False` and `selected_route != "phase2_full_repair"`
- Any key from `route.route_state_fields()` disagrees with `route.decision[key]`

Also add an artifact-validator test asserting stale artifacts are rejected when `selected_route == "needs_sa_or_adaptive_rerun"` and `next_recommended_route` is missing and route invocation is non-disambiguated.

---

### Step 2 — Implement `pipeline.py`

Work through these sub-steps in order.

#### 2a. Define `RouteStateInvariantError` above `RepairRouteResult`

```python
class RouteStateInvariantError(RuntimeError):
    """Raised when accepted_move_count != n_fixed, indicating log corruption or bug."""
    def __init__(self, field, expected, actual, context):
        self.field = field
        self.expected = expected
        self.actual = actual
        self.context = context
        super().__init__(
            f"Invariant failed: {field} expected {expected}, got {actual}. Context: {context}"
        )
```

#### 2b. Expand `RepairRouteResult` — modify `pipeline.py:55-66`

Add these fields to the dataclass:

```python
route_outcome_detail: str
next_recommended_route: str | None

solver_n_unknown_before: int = 0
solver_n_unknown_after: int = 0

phase2_full_repair_invoked: bool = False
phase2_full_repair_n_fixed: int = 0
phase2_full_repair_accepted_move_count: int = 0
phase2_full_repair_changed_grid: bool = False
phase2_full_repair_reduced_unknowns: bool = False
phase2_full_repair_solved: bool = False
phase2_solver_n_unknown_before: int | None = None
phase2_solver_n_unknown_after: int | None = None

last100_invoked: bool = False
last100_n_fixes: int = 0
last100_accepted_move_count: int = 0
last100_solver_n_unknown_before: int | None = None
last100_solver_n_unknown_after: int | None = None
last100_stop_reason: str | None = None
```

Add this method to the dataclass:

```python
def route_state_fields(self) -> dict:
    return {
        "selected_route": self.selected_route,
        "route_result": self.route_result,
        "route_outcome_detail": self.route_outcome_detail,
        "next_recommended_route": self.next_recommended_route,
        "solver_n_unknown_before": int(self.solver_n_unknown_before),
        "solver_n_unknown_after": int(self.solver_n_unknown_after),
        "phase2_full_repair_invoked": bool(self.phase2_full_repair_invoked),
        "phase2_full_repair_hit_time_budget": bool(self.phase2_full_repair_hit_time_budget),
        "phase2_full_repair_n_fixed": int(self.phase2_full_repair_n_fixed),
        "phase2_full_repair_accepted_move_count": int(self.phase2_full_repair_accepted_move_count),
        "phase2_full_repair_changed_grid": bool(self.phase2_full_repair_changed_grid),
        "phase2_full_repair_reduced_unknowns": bool(self.phase2_full_repair_reduced_unknowns),
        "phase2_full_repair_solved": bool(self.phase2_full_repair_solved),
        "phase2_solver_n_unknown_before": self.phase2_solver_n_unknown_before,
        "phase2_solver_n_unknown_after": self.phase2_solver_n_unknown_after,
        "last100_invoked": bool(self.last100_invoked),
        "last100_repair_hit_time_budget": bool(self.last100_repair_hit_time_budget),
        "last100_n_fixes": int(self.last100_n_fixes),
        "last100_accepted_move_count": int(self.last100_accepted_move_count),
        "last100_solver_n_unknown_before": self.last100_solver_n_unknown_before,
        "last100_solver_n_unknown_after": self.last100_solver_n_unknown_after,
        "last100_stop_reason": self.last100_stop_reason,
    }
```

This method must not emit compatibility aliases (`repair_route_selected`, `phase2_fixes`, etc.). Those are emitted only by transformers.

#### 2c. Add `ROUTE_STATE_KEYS` and `_build_route_result(...)` immediately below `RepairRouteResult`

`_build_route_result` is the **only** permitted construction path for `RepairRouteResult` inside `route_late_stage_failure`. Direct `RepairRouteResult(...)` construction inside that function is forbidden after this change.

```python
ROUTE_STATE_KEYS = {
    "selected_route", "route_result", "route_outcome_detail", "next_recommended_route",
    "solver_n_unknown_before", "solver_n_unknown_after",
    "phase2_full_repair_invoked", "phase2_full_repair_hit_time_budget",
    "phase2_full_repair_n_fixed", "phase2_full_repair_accepted_move_count",
    "phase2_full_repair_changed_grid", "phase2_full_repair_reduced_unknowns",
    "phase2_full_repair_solved", "phase2_solver_n_unknown_before", "phase2_solver_n_unknown_after",
    "last100_invoked", "last100_repair_hit_time_budget",
    "last100_n_fixes", "last100_accepted_move_count",
    "last100_solver_n_unknown_before", "last100_solver_n_unknown_after", "last100_stop_reason",
}


def _build_route_result(
    *,
    grid: np.ndarray,
    sr,
    failure_taxonomy: dict,
    decision: dict,
    phase2_log: list | None = None,
    last100_log: list | None = None,
    visual_delta_summary: dict | None = None,
) -> RepairRouteResult:
    missing = sorted(ROUTE_STATE_KEYS - set(decision))
    if missing:
        raise ValueError(f"Incomplete route decision before result construction: {missing}")

    sr_unknown = int(sr.n_unknown)
    decision_unknown = int(decision["solver_n_unknown_after"])
    if sr_unknown != decision_unknown:
        raise ValueError(
            "Route decision solver_n_unknown_after is stale: "
            f"decision={decision_unknown}, sr={sr_unknown}. "
            "Grid/sr was modified without updating decision."
        )

    if (
        bool(decision["phase2_full_repair_invoked"])
        and not bool(decision["last100_invoked"])
        and decision["selected_route"] != "phase2_full_repair"
    ):
        raise ValueError(
            "Phase 2 invoked but selected_route is not phase2_full_repair. "
            f"selected_route={decision['selected_route']!r}"
        )

    if decision["selected_route"] == "needs_sa_or_adaptive_rerun":
        raise ValueError(
            "needs_sa_or_adaptive_rerun is a next_recommended_route value, "
            "not a selected_route value. This indicates the route state was not updated after Phase 2."
        )

    route = RepairRouteResult(
        grid=grid.copy(),
        sr=sr,
        selected_route=decision["selected_route"],
        route_result=decision["route_result"],
        route_outcome_detail=decision["route_outcome_detail"],
        next_recommended_route=decision["next_recommended_route"],
        solver_n_unknown_before=int(decision["solver_n_unknown_before"]),
        solver_n_unknown_after=decision_unknown,
        failure_taxonomy=dict(failure_taxonomy),
        phase2_full_repair_invoked=bool(decision["phase2_full_repair_invoked"]),
        phase2_full_repair_hit_time_budget=bool(decision["phase2_full_repair_hit_time_budget"]),
        phase2_full_repair_n_fixed=int(decision["phase2_full_repair_n_fixed"]),
        phase2_full_repair_accepted_move_count=int(decision["phase2_full_repair_accepted_move_count"]),
        phase2_full_repair_changed_grid=bool(decision["phase2_full_repair_changed_grid"]),
        phase2_full_repair_reduced_unknowns=bool(decision["phase2_full_repair_reduced_unknowns"]),
        phase2_full_repair_solved=bool(decision["phase2_full_repair_solved"]),
        phase2_solver_n_unknown_before=decision["phase2_solver_n_unknown_before"],
        phase2_solver_n_unknown_after=decision["phase2_solver_n_unknown_after"],
        last100_invoked=bool(decision["last100_invoked"]),
        last100_repair_hit_time_budget=bool(decision["last100_repair_hit_time_budget"]),
        last100_n_fixes=int(decision["last100_n_fixes"]),
        last100_accepted_move_count=int(decision["last100_accepted_move_count"]),
        last100_solver_n_unknown_before=decision["last100_solver_n_unknown_before"],
        last100_solver_n_unknown_after=decision["last100_solver_n_unknown_after"],
        last100_stop_reason=decision["last100_stop_reason"],
        phase2_log=list(phase2_log or []),
        last100_log=list(last100_log or []),
        visual_delta_summary=dict(visual_delta_summary or {}),
        decision=dict(decision),
    )

    for key, value in route.route_state_fields().items():
        if route.decision.get(key) != value:
            raise ValueError(
                f"Route decision disagrees with RepairRouteResult for {key}: "
                f"{route.decision.get(key)!r} != {value!r}"
            )

    return route
```

#### 2d. Replace the default `decision` dict — modify `pipeline.py:82-95`

Replace the entire current `decision = { ... }` initializer with:

```python
decision = {
    "solver_n_unknown_before": int(sr.n_unknown),
    "solver_n_unknown_after": int(sr.n_unknown),
    "dominant_failure_class": failure_taxonomy.get("dominant_failure_class"),
    "recommended_route": failure_taxonomy.get("recommended_route"),

    "selected_route": "none",
    "route_result": "unresolved_after_repair",
    "route_outcome_detail": "no_late_stage_route_invoked",
    "next_recommended_route": "needs_sa_or_adaptive_rerun",

    "phase2_budget_s": float(config.phase2_budget_s),
    "last100_budget_s": float(config.last100_budget_s),

    "phase2_full_repair_invoked": False,
    "phase2_full_repair_hit_time_budget": False,
    "phase2_full_repair_n_fixed": 0,
    "phase2_full_repair_accepted_move_count": 0,
    "phase2_full_repair_changed_grid": False,
    "phase2_full_repair_reduced_unknowns": False,
    "phase2_full_repair_solved": False,
    "phase2_solver_n_unknown_before": None,
    "phase2_solver_n_unknown_after": None,

    "last100_invoked": False,
    "last100_repair_hit_time_budget": False,
    "last100_n_fixes": 0,
    "last100_accepted_move_count": 0,
    "last100_solver_n_unknown_before": None,
    "last100_solver_n_unknown_after": None,
    "last100_stop_reason": None,

    "sa_rerun_invoked": False,
}
```

Also declare these variables so they are in scope for the final return:

```python
phase2_log = []
last100_log = []
visual_delta_summary = {}
```

#### 2e. Fix already-solved branch — modify `pipeline.py:97-107`

```python
decision.update({
    "selected_route": "already_solved",
    "route_result": "solved",
    "route_outcome_detail": "already_solved_before_routing",
    "next_recommended_route": None,
    "solver_n_unknown_after": 0,
})
return _build_route_result(
    grid=grid, sr=sr, failure_taxonomy=failure_taxonomy, decision=dict(decision),
)
```

#### 2f. Fix Phase 2 branch — modify `pipeline.py:109-142`

**Write-back rule**: Every assignment of `grid = routed_grid` or `sr = routed_sr` must be followed immediately by `decision["solver_n_unknown_after"] = int(sr.n_unknown)` and the full outcome mapping before any return or fallthrough.

Set route family **before** calling `run_phase2_full_repair`:

```python
phase2_grid_before = grid.copy()
phase2_unknown_before = int(sr.n_unknown)
decision["selected_route"] = "phase2_full_repair"
decision["phase2_full_repair_invoked"] = True
decision["phase2_solver_n_unknown_before"] = phase2_unknown_before
```

After Phase 2 returns, translate results:

```python
routed_grid = phase2_result.grid
phase2_log = list(phase2_result.log)
routed_sr = solve_board(routed_grid, max_rounds=int(config.solve_max_rounds), mode="full")

if routed_sr is None or not getattr(routed_sr, "success", True):
    decision.update({
        "route_result": "unresolved_repair_error",
        "route_outcome_detail": "solver_failure_post_repair",
        "solver_n_unknown_after": phase2_unknown_before,
    })
    return _build_route_result(
        grid=phase2_grid_before, sr=sr, failure_taxonomy=failure_taxonomy,
        decision=dict(decision), phase2_log=phase2_log, last100_log=[],
    )

phase2_unknown_after = int(routed_sr.n_unknown)
phase2_accepted_count = sum(1 for e in phase2_log if bool(e.get("accepted", False)))
phase2_changed_grid = bool(np.any(routed_grid != phase2_grid_before))
phase2_reduced_unknowns = phase2_unknown_after < phase2_unknown_before
phase2_solved = phase2_unknown_after == 0

decision.update({
    "phase2_full_repair_hit_time_budget": bool(phase2_result.phase2_full_repair_hit_time_budget),
    "phase2_full_repair_n_fixed": int(phase2_result.n_fixed),
    "phase2_full_repair_accepted_move_count": int(phase2_accepted_count),
    "phase2_full_repair_changed_grid": phase2_changed_grid,
    "phase2_full_repair_reduced_unknowns": phase2_reduced_unknowns,
    "phase2_full_repair_solved": phase2_solved,
    "phase2_solver_n_unknown_after": phase2_unknown_after,
    "solver_n_unknown_after": phase2_unknown_after,
})
```

Outcome mapping — `next_rec` depends on `config.enable_last100`:

```python
if phase2_solved:
    route_result = "solved"
    route_outcome_detail = "phase2_full_repair_solved"
    next_rec = None
elif phase2_unknown_after < phase2_unknown_before:
    route_result = "unresolved_after_repair"
    route_outcome_detail = "phase2_full_repair_partial_progress_unresolved"
    next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
elif phase2_unknown_after == phase2_unknown_before and phase2_changed_grid:
    route_result = "unresolved_after_repair"
    route_outcome_detail = "phase2_full_repair_no_op"
    next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
elif phase2_accepted_count == 0:
    route_result = "unresolved_after_repair"
    route_outcome_detail = "phase2_full_repair_no_accepted_moves"
    next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
else:
    route_result = "unresolved_after_repair"
    route_outcome_detail = "phase2_full_repair_changed_grid_without_solver_progress"
    next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"

decision.update({
    "route_result": route_result,
    "route_outcome_detail": route_outcome_detail,
    "next_recommended_route": next_rec,
})
```

**If Phase 2 solved**: return immediately with route-wide visual delta:

```python
if phase2_solved:
    phase2_visual_delta = compute_repair_visual_delta(phase2_grid_before, routed_grid, target)
    visual_delta_summary = {
        **phase2_visual_delta,
        "summary_scope": "route_phase",
        "route_phase": "phase2_full_repair",
        "selected_route": decision["selected_route"],
        "route_result": decision["route_result"],
        "route_outcome_detail": decision["route_outcome_detail"],
        "next_recommended_route": decision["next_recommended_route"],
        "solver_n_unknown_before": phase2_unknown_before,
        "solver_n_unknown_after": phase2_unknown_after,
        "accepted_move_count": phase2_accepted_count,
        "n_fixed": int(phase2_result.n_fixed),
        "removed_mine_count": int(np.sum((phase2_grid_before == 1) & (routed_grid == 0))),
        "added_mine_count": int(np.sum((phase2_grid_before == 0) & (routed_grid == 1))),
        "visual_quality_improved": bool(phase2_visual_delta["visual_delta"] < 0),
        "solver_progress_improved": bool(phase2_unknown_after < phase2_unknown_before),
    }
    return _build_route_result(
        grid=routed_grid, sr=routed_sr, failure_taxonomy=failure_taxonomy,
        decision=dict(decision), phase2_log=phase2_log, last100_log=[],
        visual_delta_summary=visual_delta_summary,
    )
```

**If Phase 2 unresolved**: do NOT return. Update `grid`, `sr`, and `visual_delta_summary`; fall through to Last100:

```python
else:
    grid = routed_grid
    sr = routed_sr
    visual_delta_summary = compute_repair_visual_delta(phase2_grid_before, routed_grid, target)
    visual_delta_summary.update({
        "summary_scope": "route_phase",
        "route_phase": "phase2_full_repair",
        "selected_route": decision["selected_route"],
        "route_result": decision["route_result"],
        "route_outcome_detail": decision["route_outcome_detail"],
        "next_recommended_route": decision["next_recommended_route"],
        "solver_n_unknown_before": phase2_unknown_before,
        "solver_n_unknown_after": phase2_unknown_after,
        "accepted_move_count": phase2_accepted_count,
        "n_fixed": int(phase2_result.n_fixed),
        "removed_mine_count": int(np.sum((phase2_grid_before == 1) & (routed_grid == 0))),
        "added_mine_count": int(np.sum((phase2_grid_before == 0) & (routed_grid == 1))),
        "visual_quality_improved": bool(visual_delta_summary["visual_delta"] < 0),
        "solver_progress_improved": bool(phase2_unknown_after < phase2_unknown_before),
    })
```

#### 2g. Fix Last100 branch — modify `pipeline.py:144-177`

Before invoking Last100:

```python
last100_grid_before = grid.copy()
last100_unknown_before = int(sr.n_unknown)
decision["selected_route"] = "last100_repair"
decision["last100_invoked"] = True
decision["last100_solver_n_unknown_before"] = last100_unknown_before
```

After Last100:

```python
routed_grid = last100_result.grid
routed_sr = last100_result.sr
last100_log = last100_result.move_log
last100_unknown_after = int(routed_sr.n_unknown)
last100_accepted_count = sum(1 for e in last100_log if bool(e.get("accepted", False)))

if routed_sr is None or not getattr(routed_sr, "success", True):
    decision.update({
        "route_result": "unresolved_repair_error",
        "route_outcome_detail": "solver_failure_post_repair",
        "solver_n_unknown_after": last100_unknown_before,
    })
    return _build_route_result(
        grid=last100_grid_before, sr=sr, failure_taxonomy=failure_taxonomy,
        decision=dict(decision), phase2_log=phase2_log, last100_log=last100_log,
    )

decision.update({
    "last100_repair_hit_time_budget": bool(last100_result.last100_repair_hit_time_budget),
    "last100_n_fixes": int(last100_result.n_fixes),
    "last100_accepted_move_count": int(last100_accepted_count),
    "last100_solver_n_unknown_after": last100_unknown_after,
    "last100_stop_reason": str(last100_result.stop_reason),
    "solver_n_unknown_after": last100_unknown_after,
})

if last100_unknown_after == 0:
    route_result = "solved"
    route_outcome_detail = "last100_repair_solved"
    next_rec = None
elif bool(last100_result.last100_repair_hit_time_budget):
    route_result = "unresolved_after_repair"
    route_outcome_detail = "last100_repair_timeout_unresolved"
    next_rec = "needs_sa_or_adaptive_rerun"
elif last100_accepted_count > 0 and last100_unknown_after < last100_unknown_before:
    route_result = "unresolved_after_repair"
    route_outcome_detail = "last100_repair_partial_progress_unresolved"
    next_rec = "needs_sa_or_adaptive_rerun"
else:
    route_result = "unresolved_after_repair"
    route_outcome_detail = "last100_repair_no_accepted_moves"
    next_rec = "needs_sa_or_adaptive_rerun"

decision.update({
    "route_result": route_result,
    "route_outcome_detail": route_outcome_detail,
    "next_recommended_route": next_rec,
})

last100_visual_delta = compute_repair_visual_delta(last100_grid_before, routed_grid, target)
visual_delta_summary = {
    **last100_visual_delta,
    "summary_scope": "route_phase",
    "route_phase": "last100_repair",
    "selected_route": decision["selected_route"],
    "route_result": decision["route_result"],
    "route_outcome_detail": decision["route_outcome_detail"],
    "next_recommended_route": decision["next_recommended_route"],
    "solver_n_unknown_before": last100_unknown_before,
    "solver_n_unknown_after": last100_unknown_after,
    "accepted_move_count": last100_accepted_count,
    "n_fixed": int(last100_result.n_fixes),
    "removed_mine_count": int(np.sum((last100_grid_before == 1) & (routed_grid == 0))),
    "added_mine_count": int(np.sum((last100_grid_before == 0) & (routed_grid == 1))),
    "visual_quality_improved": bool(last100_visual_delta["visual_delta"] < 0),
    "solver_progress_improved": bool(last100_unknown_after < last100_unknown_before),
}

return _build_route_result(
    grid=routed_grid, sr=routed_sr, failure_taxonomy=failure_taxonomy,
    decision=dict(decision), phase2_log=phase2_log, last100_log=last100_log,
    visual_delta_summary=visual_delta_summary,
)
```

#### 2h. Replace final fallback — modify `pipeline.py:179-188`

Replace the entire unconditional `return RepairRouteResult(selected_route="needs_sa_or_adaptive_rerun", ...)` with:

```python
return _build_route_result(
    grid=grid,
    sr=sr,
    failure_taxonomy=failure_taxonomy,
    phase2_log=phase2_log,
    last100_log=last100_log,
    visual_delta_summary=visual_delta_summary,
    decision=decision,
)
```

By this point `decision["selected_route"]` is guaranteed to be `"none"` (no route ran) or `"phase2_full_repair"` (Phase 2 ran unresolved). `"needs_sa_or_adaptive_rerun"` is never assigned to `decision["selected_route"]`.

#### 2i. Update `write_repair_route_artifacts` — modify `pipeline.py:191-226`

**Remove** all `setdefault(...)` lines for primary route-state fields — forbidden.

**Add** before writing any file:

```python
# Completeness guard
required = {
    "selected_route", "route_result", "route_outcome_detail", "next_recommended_route",
    "solver_n_unknown_before", "solver_n_unknown_after",
}
missing = sorted(required - set(repair_route_decision))
if missing:
    raise ValueError(f"Incomplete repair route decision: missing {missing}")

# Dataclass-to-decision sync guard
route_state = route_result.route_state_fields()
for key, value in route_state.items():
    if repair_route_decision.get(key) != value:
        raise ValueError(
            f"Repair route decision disagrees with RepairRouteResult for {key}: "
            f"{repair_route_decision.get(key)!r} != {value!r}"
        )

# Invariant: accepted_move_count == n_fixed
if route_result.phase2_full_repair_invoked:
    phase2_accepted = sum(1 for e in route_result.phase2_log if e.get("accepted", False))
    if route_result.phase2_full_repair_accepted_move_count != phase2_accepted:
        raise RouteStateInvariantError(
            "phase2_full_repair_accepted_move_count",
            route_result.phase2_full_repair_accepted_move_count,
            phase2_accepted,
            {"context": "Phase 2 accepted count mismatch"},
        )
    if route_result.phase2_full_repair_n_fixed != phase2_accepted:
        raise RouteStateInvariantError(
            "phase2_full_repair_n_fixed",
            route_result.phase2_full_repair_n_fixed,
            phase2_accepted,
            {"context": "Phase 2 n_fixed does not match accepted count"},
        )

if route_result.last100_invoked:
    last100_accepted = sum(1 for e in route_result.last100_log if e.get("accepted", False))
    if route_result.last100_accepted_move_count != last100_accepted:
        raise RouteStateInvariantError(
            "last100_accepted_move_count",
            route_result.last100_accepted_move_count,
            last100_accepted,
            {"context": "Last100 accepted count mismatch"},
        )
    if route_result.last100_n_fixes != last100_accepted:
        raise RouteStateInvariantError(
            "last100_n_fixes",
            route_result.last100_n_fixes,
            last100_accepted,
            {"context": "Last100 n_fixes does not match accepted count"},
        )
```

---

### Step 3 — Implement `run_iter9.py`

**3.1** Render metrics — `run_iter9.py:842-852`:
```python
render_metrics = {
    **route.route_state_fields(),
    "repair_route_selected": route.selected_route,   # exact alias only
    "repair_route_result": route.route_result,        # exact alias only
}
```

**3.2** `repair_reason` — `run_iter9.py:939`:
```python
"repair_reason": (
    f"phase1={phase1_reason}"
    f"+selected_route={route.selected_route}"
    f"+route_result={route.route_result}"
    f"+route_outcome_detail={route.route_outcome_detail}"
    f"+next_recommended_route={route.next_recommended_route}"
),
```

**3.3** Flat metrics — `run_iter9.py:960-971` — add all fields from `route.route_state_fields()` and replace the old count aliases:
```python
"phase2_fixes": route.phase2_full_repair_accepted_move_count,  # replaces len(route.phase2_log)
"last100_fixes": route.last100_n_fixes,                         # replaces len(route.last100_log)
```

**3.4** Nested `repair_route_summary` — `run_iter9.py:1074-1085`:
```python
repair_route_summary = {
    **route.route_state_fields(),
    "repair_route_selected": route.selected_route,
    "repair_route_result": route.route_result,
    "phase2_fixes": route.phase2_full_repair_accepted_move_count,
    "last100_fixes": route.last100_n_fixes,
    "dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
    "sealed_cluster_count": int(route.failure_taxonomy.get("sealed_cluster_count", 0) or 0),
    "phase1_repair_hit_time_budget": phase1_repair_hit_time_budget,
    "phase2_full_repair_hit_time_budget": bool(route.phase2_full_repair_hit_time_budget),
    "last100_repair_hit_time_budget": bool(route.last100_repair_hit_time_budget),
    "sa_rerun_invoked": bool(route.decision.get("sa_rerun_invoked", False)),
}
```

**3.5** `_llm_review_summary` — `run_iter9.py:392-408` and call at `1136-1144`:

Update signature to accept `selected_route`, `route_result`, `route_outcome_detail`, `next_recommended_route`. Update `one_sentence_result`:
```python
next_text = (
    f" Next recommended route: {next_recommended_route}."
    if next_recommended_route is not None
    else " No next route is required."
)
one_sentence_result = (
    f"The run used {source_cfg.command_arg} at {board_label} with seed {seed} "
    f"and ended after selected_route={selected_route} "
    f"with route_result={route_result} "
    f"and route_outcome_detail={route_outcome_detail}."
    f"{next_text}"
)
```

**3.6** Image sweep — `run_iter9.py:56-75` and all sweep builder lines:

Add to `IMAGE_SWEEP_SUMMARY_FIELDS`:
```python
"selected_route", "route_result", "route_outcome_detail", "next_recommended_route",
"phase2_full_repair_invoked", "phase2_full_repair_accepted_move_count",
"last100_invoked", "last100_accepted_move_count",
```

For failed rows: set all new fields to `None`.

For skipped-existing rows: use `existing.get("selected_route")` — do NOT synthesize from `repair_route_selected`.

---

### Step 4 — Implement `run_benchmark.py`

**4.1** Child render metrics — `run_benchmark.py:544-554`:
```python
render_metrics = {
    **route.route_state_fields(),
    "repair_route_selected": route.selected_route,
    "repair_route_result": route.route_result,
}
```

**4.2** `route_summary` — `run_benchmark.py:634-645`:
```python
route_summary = {
    **route.route_state_fields(),
    "repair_route_selected": route.selected_route,
    "repair_route_result": route.route_result,
    "dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
    "sealed_cluster_count": int(route.failure_taxonomy.get("sealed_cluster_count", 0) or 0),
    "phase1_repair_hit_time_budget": phase1_repair_hit_time_budget,
    "phase2_full_repair_hit_time_budget": bool(route.phase2_full_repair_hit_time_budget),
    "last100_repair_hit_time_budget": bool(route.last100_repair_hit_time_budget),
    "sa_rerun_invoked": bool(route.decision.get("sa_rerun_invoked", False)),
}
```

**4.3** Flat metrics — `run_benchmark.py:668-701` — same pattern as Iter9; structured `repair_reason` at line 691:
```python
"repair_reason": (
    f"phase1={phase1_reason}"
    f"+selected_route={route.selected_route}"
    f"+route_result={route.route_result}"
    f"+route_outcome_detail={route.route_outcome_detail}"
    f"+next_recommended_route={route.next_recommended_route}"
),
```

**4.4** Summary rows — `run_benchmark.py:737-766`:
```python
"selected_route": metrics.get("selected_route"),
"route_result": metrics.get("route_result"),
"route_outcome_detail": metrics.get("route_outcome_detail"),
"next_recommended_route": metrics.get("next_recommended_route"),
"phase2_full_repair_invoked": metrics.get("phase2_full_repair_invoked"),
"phase2_full_repair_accepted_move_count": metrics.get("phase2_full_repair_accepted_move_count"),
"last100_invoked": metrics.get("last100_invoked"),
"last100_accepted_move_count": metrics.get("last100_accepted_move_count"),
"repair_route_selected": metrics.get("selected_route"),   # exact alias
"repair_route_result": metrics.get("route_result"),        # exact alias
```

**4.5** Markdown table header — `run_benchmark.py:840-851`:
```markdown
| board | seed | child_dir | n_unknown | coverage | solvable | selected_route | route_result | route_outcome_detail | next_recommended_route | phase2_accepted | last100_accepted | phase1_timeout | phase2_full_timeout | last100_timeout | visual_delta | total_time_s |
```
Rows use `row["selected_route"]`, `row["route_result"]`, `row["route_outcome_detail"]`, `row["next_recommended_route"]`, `row["phase2_full_repair_accepted_move_count"]`, `row["last100_accepted_move_count"]`.

**4.6** CSV headers — `run_benchmark.py:888-909` — add:
```python
"selected_route", "route_result", "route_outcome_detail", "next_recommended_route",
"phase2_full_repair_invoked", "phase2_full_repair_n_fixed",
"phase2_full_repair_accepted_move_count", "last100_invoked",
"last100_n_fixes", "last100_accepted_move_count",
"repair_route_selected",   # exact alias
"repair_route_result",     # exact alias
```

**4.7** Regression-only — `run_benchmark.py:947-1004` and `1035-1055`:
```python
result = {
    **route.route_state_fields(),
    "repair_route_selected": route.selected_route,
    "repair_route_result": route.route_result,
    "phase2_fixes": route.phase2_full_repair_accepted_move_count,
    "last100_fixes": route.last100_n_fixes,
}
```
Change comparison from `result["repair_route_selected"] != case["expected_route"]` to `result["selected_route"] != case["expected_route"]`.

Console output: print `route={result["selected_route"]}`, `route_result={result["route_result"]}`, `route_outcome_detail={result["route_outcome_detail"]}`.

---

### Step 5 — Implement `report.py` — modify `report.py:312-349`

Replace:
```python
route = _coalesce(metrics.get("repair_route_selected"), "unknown repair route")
```

With:
```python
selected_route = metrics.get("selected_route")
route_result = metrics.get("route_result")
route_outcome_detail = _coalesce(metrics.get("route_outcome_detail"), "unknown detail")
next_recommended_route = metrics.get("next_recommended_route")
route_contract_warning = None

if selected_route is None:
    selected_route = "schema_incomplete_missing_selected_route"
    route_contract_warning = (
        "This metrics document predates or violates the route-state contract; "
        "repair_route_selected was not used as the performed route."
    )

if route_result is None:
    route_result = "schema_incomplete_missing_route_result"
```

Plain-English route text for unresolved:
```python
f"The late-stage route used here was {selected_route}. "
f"It ended with route_result={route_result} and route_outcome_detail={route_outcome_detail}. "
f"The next recommended route is {next_recommended_route}."
```

Plain-English route text for solved:
```python
f"The late-stage route used here was {selected_route}. "
f"It ended with route_result={route_result} and route_outcome_detail={route_outcome_detail}. "
f"No next route is required."
```

If `route_contract_warning` is not `None`, append it. Do not silently fall back to `repair_route_selected`.

---

### Step 6 — Update Documentation and Schemas

Update every file below. For schemas: remove `needs_sa_or_adaptive_rerun` from `selected_route` enum and move it to `next_recommended_route` only. Add all new required fields. Add the `route_outcome_detail` 11-value enum. No example may show `selected_route = "needs_sa_or_adaptive_rerun"` when any repair route ran.

Files to update:
```
AGENTS.md                                          (Step 0 already done)
for_user_review.md                                 (Step 0 already done)
docs/json_schema/repair_route_decision.schema.md
docs/json_schema/metrics_iter9.schema.md
docs/json_schema/visual_delta_summary.schema.md
docs/json_schema/benchmark_summary.schema.md
docs/json_schema/JSON_OUTPUT_SCHEMA_INDEX.md
README.md
docs/DOCS_INDEX.md
demo/docs/artifact_consumption_contract.md
```

New required fields to add to all applicable schemas:
```
selected_route, route_result, route_outcome_detail, next_recommended_route,
solver_n_unknown_before, solver_n_unknown_after,
phase2_full_repair_invoked, phase2_full_repair_hit_time_budget,
phase2_full_repair_n_fixed, phase2_full_repair_accepted_move_count,
phase2_full_repair_changed_grid, phase2_full_repair_reduced_unknowns, phase2_full_repair_solved,
phase2_solver_n_unknown_before, phase2_solver_n_unknown_after,
last100_invoked, last100_repair_hit_time_budget,
last100_n_fixes, last100_accepted_move_count,
last100_solver_n_unknown_before, last100_solver_n_unknown_after, last100_stop_reason
```

For `visual_delta_summary.schema.md`: add route-wide variant shape with `summary_scope`, `route_phase`, `accepted_move_count`, `n_fixed`, `removed_mine_count`, `added_mine_count`, `visual_quality_improved`, `solver_progress_improved`.

For `metrics_iter9.schema.md`: update `repair_route_summary.phase2_fixes` description — it is now a compatibility alias of `phase2_full_repair_accepted_move_count`, not a log length.

---

### Step 7 — Validate

**Classification search** — run first and classify every hit:
```bash
grep -rn "repair_route_selected\|selected_route\|route_result\|needs_sa_or_adaptive_rerun\|phase2_fixes\|last100_fixes\|repair_route_decision\|visual_delta_summary" .
```
Every hit must be classified as `producer`, `transformer`, `consumer`, `serializer`, or `docs/schema`. No hit may retain the old semantic meaning.

**Targeted tests — all six must pass:**
```bash
python -m unittest tests.test_repair_route_decision
python -m unittest tests.test_route_artifact_metadata
python -m unittest tests.test_benchmark_layout
python -m unittest tests.test_source_image_cli_contract
python -m unittest tests.test_iter9_image_sweep_contract
python -m unittest tests.test_report_explanations
```

**Documentation governance check:**
```python
from pathlib import Path
required = {
    "AGENTS.md": [
        "Route-state field semantics may be corrected",
        "regression-only outputs, checks, docs, and expected-route comparisons must be updated consistently",
    ],
    "for_user_review.md": ["applicability", "impact", "transition", "validation evidence"],
    "demo/docs/artifact_consumption_contract.md": [
        "selected_route", "route_outcome_detail", "next_recommended_route",
    ],
}
for path, needles in required.items():
    text = Path(path).read_text(encoding="utf-8")
    missing = [n for n in needles if n not in text]
    if missing:
        raise SystemExit(f"{path} missing {missing}")
```

**Full suite:**
```bash
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

**Forensic rerun** — must create a NEW directory, must NOT overwrite `results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/`:
```bash
python run_iter9.py --image assets/line_art_irl_14.png --run-tag Forensic-Run-RouteDecisionFix --seed 44 --board-w 300 --allow-noncanonical
```

---

## Forensic Acceptance Criteria

After the forensic rerun, read the output artifacts and assert every value below exactly:

```
selected_route                                    == "phase2_full_repair"
route_result                                      == "unresolved_after_repair"
route_outcome_detail                              == "phase2_full_repair_partial_progress_unresolved"
next_recommended_route                            == "needs_sa_or_adaptive_rerun"
phase2_full_repair_invoked                        == true
phase2_full_repair_hit_time_budget                == false
phase2_full_repair_n_fixed                        > 0
phase2_full_repair_accepted_move_count            > 0
last100_invoked                                   == false
solver_n_unknown_before                           == 37285
phase2_solver_n_unknown_before                    == 37285
phase2_solver_n_unknown_after                     == 31540
solver_n_unknown_after                            == 31540
visual_delta_summary.summary_scope                == "route_phase"
visual_delta_summary.route_phase                  == "phase2_full_repair"
visual_delta_summary.solver_n_unknown_before      == 37285
visual_delta_summary.solver_n_unknown_after       == 31540
visual_delta_summary.mean_abs_error_before        == 0.9614354968070984
visual_delta_summary.mean_abs_error_after         == 0.9689586162567139
visual_delta_summary.visual_delta                 == 0.0075231194496154785
len(visual_delta_summary.removed_mines)           == 192
len(visual_delta_summary.added_mines)             == 0
visual_delta_summary.changed_cells                == 192
visual_delta_summary.removed_mine_count           == 192
visual_delta_summary.added_mine_count             == 0
visual_delta_summary.visual_quality_improved      == false
visual_delta_summary.solver_progress_improved     == true
```

Cross-artifact equality — all must hold:
```
repair_route_decision.json.selected_route          == metrics.selected_route
repair_route_decision.json.route_result            == metrics.route_result
repair_route_decision.json.route_outcome_detail    == metrics.route_outcome_detail
repair_route_decision.json.next_recommended_route  == metrics.next_recommended_route
repair_route_decision.json.solver_n_unknown_after  == metrics.solver_summary.post_routing.n_unknown
repair_route_decision.json.phase2_full_repair_n_fixed > 0
repair_route_decision.json.phase2_full_repair_accepted_move_count > 0
metrics.repair_route_summary.phase2_fixes          == repair_route_decision.json.phase2_full_repair_accepted_move_count
visual_delta_summary.json.solver_n_unknown_after   == repair_route_decision.json.solver_n_unknown_after
visual_delta_summary.json.accepted_move_count      == repair_route_decision.json.phase2_full_repair_accepted_move_count
visual_delta_summary.json.mean_abs_error_before    == metrics.visual_quality_summary.mean_abs_error_before_repair
visual_delta_summary.json.mean_abs_error_after     == metrics.visual_quality_summary.mean_abs_error_after_repair
visual_delta_summary.json.visual_delta             == metrics.visual_quality_summary.visual_delta
len(visual_delta_summary.json.removed_mines)       == visual_delta_summary.json.removed_mine_count
len(visual_delta_summary.json.added_mines)         == visual_delta_summary.json.added_mine_count
grid_iter9_latest.npy                              byte-equal to grid_iter9_<board>.npy
```

---

## Hardening Checklist — Must Be Complete Before Marking as Done

- [ ] `RouteStateInvariantError` defined in `pipeline.py`
- [ ] Serializer guard validates `accepted_move_count == n_fixed` for Phase 2 and Last100
- [ ] Any invariant violation raises `RouteStateInvariantError` and aborts artifact write
- [ ] `_build_route_result` rejects `selected_route == "needs_sa_or_adaptive_rerun"`
- [ ] `_build_route_result` rejects stale `decision["solver_n_unknown_after"]`
- [ ] `_build_route_result` rejects Phase 2 invoked without `selected_route == "phase2_full_repair"`
- [ ] No-route unresolved branch sets `selected_route = "none"`
- [ ] Phase 2 partial sets `next_recommended_route` from `config.enable_last100`
- [ ] Last100 partial sets `next_recommended_route = "needs_sa_or_adaptive_rerun"`
- [ ] Test for Phase 2 zero progress (`n_fixed == 0`)
- [ ] Test for Phase 2 partial with Last100 enabled
- [ ] Test for Last100 with rejected moves (`accepted_move_count != len(log)`)
- [ ] Test for invariant violation (deliberate tampering → `RouteStateInvariantError`)
- [ ] Test for solver failure after Phase 2 (`route_outcome_detail == "solver_failure_post_repair"`)
- [ ] `for_user_review.md` contains all four required fields
- [ ] `demo/docs/artifact_consumption_contract.md` updated
- [ ] All schemas updated with new fields and `route_outcome_detail` enum
- [ ] No schema example shows `selected_route = "needs_sa_or_adaptive_rerun"` when a route ran
- [ ] Forensic rerun creates a new directory and does not overwrite the original
- [ ] All forensic acceptance criteria pass exactly
