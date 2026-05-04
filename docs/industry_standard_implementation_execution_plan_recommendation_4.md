Industry-Standard Implementation & Execution Plan
Recommendation 4: Fully Specified Partial-Phase2 Route State

# Industry-Standard Implementation & Execution Plan

## Recommendation 4: Fully Specified Partial-Phase2 Route State

This plan is a **contract-first, test-first, schema-backed implementation plan**. It does **not** change Phase 2 search behavior. It changes how the existing route state is produced, persisted, copied, summarized, and explained.

The defect is confirmed: Phase 2 can mutate the grid and reduce unknowns, but the unresolved fallback currently reports `selected_route="needs_sa_or_adaptive_rerun"` and loses the partial Phase 2 route state. The report identifies this exact fallthrough failure and requires all route artifacts, metrics, summaries, and visual delta outputs to describe the same routed state.

This plan is implementation-ready because it includes the governance, consumer-impact, demo-doc, report-text, visual/overlay, serializer-equality, and syntax corrections required to close the previously identified blocker gaps. These corrections are part of the executable plan and are not optional follow-up work.

---

# 0. Current Code Anchors That Must Be Modified

| Area                       |                                                            File + exact current lines | Current problem                                                                                                                         |
| -------------------------- | ------------------------------------------------------------------------------------: | --------------------------------------------------------------------------------------------------------------------------------------- |
| Route result object        |                                                                   `pipeline.py:55-66` | `RepairRouteResult` lacks `route_outcome_detail`, `next_recommended_route`, and explicit phase count/state fields.                      |
| Route default decision     |                                                                   `pipeline.py:82-95` | Default `selected_route` is incorrectly initialized as `"needs_sa_or_adaptive_rerun"`.                                                  |
| Already-solved branch      |                                                                  `pipeline.py:97-107` | Does not emit `route_outcome_detail` or `next_recommended_route`.                                                                       |
| Phase 2 branch             |                                                                 `pipeline.py:109-142` | Sets `selected_route="phase2_full_repair"` only when solved; partial progress falls through.                                            |
| Last100 branch             |                                                                 `pipeline.py:144-177` | Does not emit complete Last100 route outcome detail or explicit counts.                                                                 |
| Final unresolved fallback  |                                                                 `pipeline.py:179-188` | Returns `selected_route="needs_sa_or_adaptive_rerun"` even after Phase 2 may have run.                                                  |
| Route artifact serializer  |                                                                 `pipeline.py:191-226` | Serializes whatever is in `decision`; writer must not infer missing route state.                                                        |
| Phase 2 result source      |                                                                   `repair.py:583-752` | Provides `grid`, `n_fixed`, `log`, and timeout flag; `pipeline.py` must translate these into route state.                               |
| Last100 result source      |                                                                   `repair.py:382-579` | Provides `grid`, `sr`, `n_fixes`, `move_log`, `stop_reason`, and timeout flag; `pipeline.py` must translate these into route state.     |
| Iter9 route invocation     |                                                                `run_iter9.py:782-807` | Correctly captures `grid_before_route`, calls routing, and assigns `grid=route.grid`; downstream fields must use the corrected `route`. |
| Iter9 artifact metadata    |                                                                `run_iter9.py:822-837` | Timeout metadata exists; add route-state metadata only after `route` is complete.                                                       |
| Iter9 render metrics       |                                                                `run_iter9.py:842-852` | Uses only `repair_route_selected`; must include four-field route model.                                                                 |
| Iter9 flat metrics         |                                                                `run_iter9.py:939-971` | Uses old `repair_reason`, `repair_route_selected`, `repair_route_result`, `phase2_fixes`, `last100_fixes`.                              |
| Iter9 nested route summary |                                                              `run_iter9.py:1074-1085` | Missing `route_outcome_detail`, `next_recommended_route`, and explicit phase fields.                                                    |
| Iter9 LLM summary          |                                                   `run_iter9.py:392-408`, `1136-1144` | Says run ended “through `<selected_route>`”; must include route result and next recommendation.                                         |
| Iter9 sweep fields         | `run_iter9.py:56-75`, `1189-1212`, `1236-1256`, `1269-1309`, `1391-1408`, `1500-1510` | Sweep rows only carry `repair_route_selected`; must carry four-field route state.                                                       |
| Benchmark route invocation |                                                            `run_benchmark.py:486-510` | Correctly captures route; downstream fields must use corrected route object.                                                            |
| Benchmark render metrics   |                                                            `run_benchmark.py:544-554` | Uses only `repair_route_selected`; must include four-field route model.                                                                 |
| Benchmark route summary    |                                                            `run_benchmark.py:634-645` | Missing `route_outcome_detail`, `next_recommended_route`, explicit phase counts.                                                        |
| Benchmark flat metrics     |                                                            `run_benchmark.py:668-701` | Uses old `repair_reason`, `repair_route_selected`, `repair_route_result`, `phase2_fixes`, `last100_fixes`.                              |
| Benchmark summary rows     |                                                            `run_benchmark.py:737-766` | Converts child metrics using old route fields.                                                                                          |
| Benchmark Markdown         |                                                            `run_benchmark.py:806-853` | Table column `route` displays `repair_route_selected` only.                                                                             |
| Benchmark CSV              |                                                            `run_benchmark.py:888-909` | CSV lacks new route-state columns.                                                                                                      |
| Benchmark regression       |                                              `run_benchmark.py:947-1004`, `1035-1055` | Regression output/checks use `repair_route_selected`.                                                                                   |
| Report text                |                                                                   `report.py:312-349` | Plain-English summaries read `repair_route_selected` only.                                                                              |
| Governance                 |                                                                   `AGENTS.md:276-320` | Regression-only stability and external-consumer documentation rules must be reconciled with route-state changes.                        |
| Consumer transition notes  |                                                                  `for_user_review.md` | Must document applicability, impact, transition notes, and validation evidence for public artifact field changes.                       |
| Demo artifact docs         |                                          `demo/docs/artifact_consumption_contract.md` | Consumes route artifacts and must not retain stale route-state semantics.                                                               |
| Docs/schema                |                                           `docs/json_schema/*.schema.md`, `README.md` | Current schema documents old or incomplete route semantics.                                                                             |

The report requires the durable contract to use the same four-field model everywhere: `selected_route`, `route_result`, `route_outcome_detail`, and `next_recommended_route`; it also states that `"needs_sa_or_adaptive_rerun"` belongs in `next_recommended_route`, not `selected_route`, after a repair route actually ran.

---

# 0.1 Governance Amendments Required Before Runtime Changes

Before changing runtime code, update `AGENTS.md` so the route-state implementation does not conflict with the existing benchmark contract.

Replace the current regression-only wording:

```md
`run_benchmark.py --regression-only` is a fixed-case mode and must preserve stable behavior.
When `--regression-only` is set, explicit normal-mode flags must remain rejected as currently implemented.
```

with:

```md
`run_benchmark.py --regression-only` is a fixed-case mode and must preserve stable case selection, validation gates, and explicit normal-mode flag rejection. Route-state field semantics may be corrected when required by an approved route-state contract, but regression-only outputs, checks, docs, and expected-route comparisons must be updated consistently in the same change.
When `--regression-only` is set, explicit normal-mode flags must remain rejected as currently implemented.
```

This preserves the fixed regression case behavior while allowing the required route-state semantic correction.

Also update `for_user_review.md` in the same change. It must document:

```text
applicability: Iter9 metrics, repair route decision artifacts, visual delta summary artifacts, repair overlays, image-sweep summaries, normal benchmark child metrics, normal benchmark summaries, benchmark_results.json, regression-only output, and report text.
impact: selected_route now means the invoked route; needs_sa_or_adaptive_rerun moves to next_recommended_route for unresolved follow-up work.
transition: repair_route_selected may remain only as an exact alias of selected_route in newly written artifacts; consumers must read next_recommended_route for follow-up strategy.
validation evidence: targeted tests, full test suite, help checks, image guard check, and the forensic rerun path.
```

Do not modify runtime code before these governance and transition-document updates are staged in the plan implementation branch.

---

# 0.1B Field Invariant Governance

**Read Before Implementation**: `docs/ROUTE_STATE_FIELD_INVARIANTS.md`

This plan introduces both `n_fixed` (direct counter) and `accepted_move_count` (defensive recount) fields. Before implementing any Phase2 or Last100 changes, you must read and understand the governance contract in `docs/ROUTE_STATE_FIELD_INVARIANTS.md`.

**Why Both Metrics?**

This document specifies:

1. **The Last100 Bug** (CRITICAL FIX):
   - Current code uses `len(last100_log)` which counts BOTH accepted and rejected moves
   - Last100 move_log contains rejected entries (guardrail violations)
   - This plan fixes it by defensive recount: `sum(1 for e in log if e["accepted"])`

2. **Defensive Verification for Phase2**:
   - Phase2 currently only logs accepted moves, so `sum(accepted)` equals `n_fixed`
   - But recount catches if Phase2 refactoring adds rejected-move logging

3. **Artifact Consistency Enforcement**:
   - Ensures metrics, visual_delta_summary, and repair_route_decision.json all report the same accepted count
   - Serializer guards validate the invariant before artifacts are written

**The Invariant**:

```python
accepted_move_count = sum(1 for e in repair_log if e["accepted"] == True)
                    == repair_result.n_fixed      (for Phase2)
                    == repair_result.n_fixes      (for Last100)
```

**Enforcement Happens At:**

- Serializer guard in `pipeline.py::write_repair_route_artifacts()` (rejects if violated)
- Test assertions in sections 2.1–2.2 (catch divergence early)
- Forensic rerun step 12.8 (validates cross-artifact equality)

**Required for ALL repair functions:** Any new repair function that modifies the grid must:

1. Return a counter field (`n_fixed`, `n_fixes`, or equivalent)
2. Log accepted moves with `"accepted": True`
3. Submit to the same invariant verification in `pipeline.py`

**For complete rationale**, read `docs/ROUTE_STATE_FIELD_INVARIANTS.md` now.

---

# 1. Target Route-State Contract

## 1.1 Required primary fields

Every route-state surface must expose:

```text
selected_route: str
route_result: str
route_outcome_detail: str
next_recommended_route: str | null
```

Required meanings:

```text
selected_route
  The route family actually selected and invoked.

route_result
  Final solved/unresolved result after all route attempts that contributed to route.grid and route.sr.

route_outcome_detail
  Precise outcome detail. Must be one of the values defined in Appendix D.

next_recommended_route
  The next strategy required after the selected route result.
  null when solved.
  "needs_sa_or_adaptive_rerun" when unresolved and no later route is available.
```

The report explicitly requires these fields and forbids overloading `selected_route` with both “route attempted” and “next action.”

## 1.2 State Transition Table

The following table defines the exact state transitions for all branches. Ambiguity in these mappings is a critical defect.

| Current State (Input) | Condition | `selected_route` | `route_result` | `route_outcome_detail` | `next_recommended_route` |
|---|---|---|---|---|---|
| Unresolved | Already Solved (`sr.n_unknown == 0`) | `already_solved` | `solved` | `already_solved_before_routing` | `None` |
| Unresolved | Phase 2 Invoked → Solved | `phase2_full_repair` | `solved` | `phase2_full_repair_solved` | `None` |
| Unresolved | Phase 2 Invoked → **Partial** (n < before) | `phase2_full_repair` | `unresolved_after_repair` | `phase2_full_repair_partial_progress_unresolved` | `last100_repair` (if enabled) OR `needs_sa_or_adaptive_rerun` |
| Unresolved | Phase 2 Invoked → **No-Op** (n == before) | `phase2_full_repair` | `unresolved_after_repair` | `phase2_full_repair_no_op` | `last100_repair` (if enabled) OR `needs_sa_or_adaptive_rerun` |
| Unresolved | Last100 Invoked → Solved | `last100_repair` | `solved` | `last100_repair_solved` | `None` |
| Unresolved | Last100 Invoked → Timeout | `last100_repair` | `unresolved_after_repair` | `last100_repair_timeout_unresolved` | `needs_sa_or_adaptive_rerun` |
| Unresolved | Last100 Invoked → Partial | `last100_repair` | `unresolved_after_repair` | `last100_repair_partial_progress_unresolved` | `needs_sa_or_adaptive_rerun` |
| Unresolved | No Route Invoked | `none` | `unresolved_after_repair` | `no_late_stage_route_invoked` | `needs_sa_or_adaptive_rerun` |

## 1.3 Formal Enum: `route_outcome_detail`

Free-text fields lead to parsing failures. The following values are the **only** allowed strings for `route_outcome_detail`. Any deviation indicates schema corruption:

- `already_solved_before_routing`
- `phase2_full_repair_solved`
- `phase2_full_repair_partial_progress_unresolved`
- `phase2_full_repair_no_op`
- `phase2_full_repair_no_accepted_moves`
- `last100_repair_solved`
- `last100_repair_timeout_unresolved`
- `last100_repair_partial_progress_unresolved`
- `last100_repair_no_accepted_moves`
- `no_late_stage_route_invoked`
- `unresolved_repair_error`

---

# 2. Phase 1: Contract Tests First

## 2.1 Update `tests/test_repair_route_decision.py`

Add or update tests before runtime changes.

Required assertions:

```text
No-route unresolved branch:
  selected_route == "none"
  route_result == "unresolved_after_repair"
  route_outcome_detail == "no_late_stage_route_invoked"
  next_recommended_route == "needs_sa_or_adaptive_rerun"

Already-solved branch:
  selected_route == "already_solved"
  route_result == "solved"
  route_outcome_detail == "already_solved_before_routing"
  next_recommended_route is None

Phase 2 solved branch:
  selected_route == "phase2_full_repair"
  route_result == "solved"
  route_outcome_detail == "phase2_full_repair_solved"
  next_recommended_route is None

Phase 2 partial branch:
  selected_route == "phase2_full_repair"
  route_result == "unresolved_after_repair"
  route_outcome_detail == "phase2_full_repair_partial_progress_unresolved"
  next_recommended_route == "needs_sa_or_adaptive_rerun"

Last100 solved branch:
  selected_route == "last100_repair"
  route_result == "solved"
  route_outcome_detail == "last100_repair_solved"
  next_recommended_route is None

Last100 unresolved branch:
  selected_route == "last100_repair"
  route_result == "unresolved_after_repair"
  route_outcome_detail in {
    "last100_repair_partial_progress_unresolved",
    "last100_repair_no_accepted_moves",
    "last100_repair_timeout_unresolved"
  }
  next_recommended_route == "needs_sa_or_adaptive_rerun"
```

The report specifically requires `tests/test_repair_route_decision.py` to assert every branch against this four-field model and to add a partial Phase 2 test.

---

## 2.2 Update artifact and transformer tests

Update these tests:

```text
tests/test_route_artifact_metadata.py
tests/test_benchmark_layout.py
tests/test_source_image_cli_contract.py
tests/test_iter9_image_sweep_contract.py
tests/test_report_explanations.py
```

Required test behavior:

```text
repair_route_decision.json contains:
  selected_route
  route_result
  route_outcome_detail
  next_recommended_route

metrics_iter9_*.json contains the same fields:
  top level
  repair_route_summary

benchmark_summary.json rows contain:
  selected_route
  route_result
  route_outcome_detail
  next_recommended_route

benchmark_summary.csv contains those headers.

benchmark_summary.md displays selected_route as the actual route.

iter9_image_sweep_summary.* rows contain those fields.

report text uses selected_route for performed route and next_recommended_route for next action.

artifact validation rejects stale route-state documents as schema-invalid:
  selected_route == "needs_sa_or_adaptive_rerun"
  and next_recommended_route is missing
  and route invocation is true or non-disambiguated
```

The report requires these consumer updates before runtime code changes.

---

# 3. Phase 2: Modify `pipeline.py` Route-State Producer

## 3.1 Extend `RepairRouteResult`

Modify `pipeline.py:55-66`.

Add these fields:

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

Also add a method:

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

This method must return exactly the fields shown above. It must not emit compatibility aliases such as `repair_route_selected`, `repair_route_result`, `phase2_fixes`, or `last100_fixes`; those aliases may be emitted only by metrics or summary transformers, and only when they are exact aliases of the canonical fields. `run_iter9.py` and `run_benchmark.py` must consume this method instead of recomputing route state from logs.

Reason: the report states that `RepairRouteResult` construction is a producer and every return from `route_late_stage_failure(...)` must populate `selected_route`, `route_result`, `route_outcome_detail`, `next_recommended_route`, `decision`, and phase count fields with consistent values.

---

## 3.1A Add `_build_route_result(...)` As The Only Construction Path

Add this helper in `pipeline.py` immediately below `RepairRouteResult`.

Every return from `route_late_stage_failure(...)` must go through this helper. Direct `RepairRouteResult(...)` construction inside `route_late_stage_failure(...)` is forbidden after this change.

```python
ROUTE_STATE_KEYS = {
    "selected_route",
    "route_result",
    "route_outcome_detail",
    "next_recommended_route",
    "solver_n_unknown_before",
    "solver_n_unknown_after",
    "phase2_full_repair_invoked",
    "phase2_full_repair_hit_time_budget",
    "phase2_full_repair_n_fixed",
    "phase2_full_repair_accepted_move_count",
    "phase2_full_repair_changed_grid",
    "phase2_full_repair_reduced_unknowns",
    "phase2_full_repair_solved",
    "phase2_solver_n_unknown_before",
    "phase2_solver_n_unknown_after",
    "last100_invoked",
    "last100_repair_hit_time_budget",
    "last100_n_fixes",
    "last100_accepted_move_count",
    "last100_solver_n_unknown_before",
    "last100_solver_n_unknown_after",
    "last100_stop_reason",
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

    # [AMENDMENT 2] Transactional Integrity: Verify sr.n_unknown matches decision BEFORE any commit
    sr_unknown = int(sr.n_unknown)
    decision_unknown = int(decision["solver_n_unknown_after"])
    if sr_unknown != decision_unknown:
        raise ValueError(
            "Route decision solver_n_unknown_after is stale: "
            f"decision={decision_unknown}, sr={sr_unknown}. "
            "Grid/sr was modified without updating decision."
        )

    # [AMENDMENT 2] Causal Consistency: Phase2 invoked must imply selected_route is phase2_full_repair
    if (
        bool(decision["phase2_full_repair_invoked"])
        and not bool(decision["last100_invoked"])
        and decision["selected_route"] != "phase2_full_repair"
    ):
        raise ValueError(
            "Phase 2 invoked but selected_route is not phase2_full_repair. "
            f"selected_route={decision['selected_route']!r}"
        )

    # [AMENDMENT 2] Logical Invariant: needs_sa_or_adaptive_rerun is only valid for next_recommended_route
    if decision["selected_route"] == "needs_sa_or_adaptive_rerun":
        raise ValueError(
            "needs_sa_or_adaptive_rerun is a next_recommended_route value, "
            "not a selected_route value. This indicates the route state was not updated after Phase 2."
        )

    route = RepairRouteResult(
        grid=grid.copy(),  # Deep copy for immutability
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

    # [AMENDMENT 2] Final Validation: Ensure dataclass and decision dict are perfectly synchronized
    for key, value in route.route_state_fields().items():
        if route.decision.get(key) != value:
            raise ValueError(
                f"Route decision disagrees with RepairRouteResult for {key}: "
                f"{route.decision.get(key)!r} != {value!r}"
            )

    return route

# [AMENDMENT 2] USAGE CONTRACT: This function MUST be used as the sole construction path.
# Any branch that modifies grid/sr must pass the MODIFIED copies (not originals) to this function.
# If validation fails, the caller must NOT persist grid/sr and must handle the exception.



---

## 3.2 Replace the default decision object

Modify `pipeline.py:82-95`.

Current default:

```python
"selected_route": "needs_sa_or_adaptive_rerun",
"solver_n_unknown_after": int(sr.n_unknown),
"route_result": "unresolved_after_repair",
```

Replace with:

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

The report requires the default state before any route runs to be `selected_route="none"`, `route_result="unresolved_after_repair"`, `route_outcome_detail="no_late_stage_route_invoked"`, and `next_recommended_route="needs_sa_or_adaptive_rerun"`.

---

## 3.2A Strict Write-Back Contract

Every route branch must obey this write-back contract:

```text
When a branch assigns a new current grid or solver result:

  grid = routed_grid
  sr = routed_sr

the same lexical block must update decision from that same routed state before any return or fallthrough can occur.
```

The source of truth for post-route unknown count is always the `sr` object that is returned on `RepairRouteResult.sr`. Therefore:

```python
decision["solver_n_unknown_after"] = int(sr.n_unknown)
```

must be written after every assignment that changes the current `sr`.

The source of truth for route outcome fields is the route outcome mapping chosen for the branch. The mapping must be written back immediately:

```python
decision.update({
    "route_result": route_result,
    "route_outcome_detail": route_outcome_detail,
    "next_recommended_route": next_recommended_route,
})
```

No route branch may keep `route_result`, `route_outcome_detail`, or `next_recommended_route` only as local variables after the outcome has been determined.

No route branch may return after assigning `grid`, `sr`, `routed_grid`, or `routed_sr` unless `_build_route_result(...)` can prove all of these are synchronized:

```text
RepairRouteResult.grid
RepairRouteResult.sr
RepairRouteResult.decision
RepairRouteResult.phase2_log
RepairRouteResult.last100_log
RepairRouteResult.visual_delta_summary
```

This contract is the direct guardrail for the original bug: Phase 2 produced a correct `sr.n_unknown == 31540`, but `decision["solver_n_unknown_after"]` stayed stale at `37285`.

---

## 3.3 Fix the already-solved branch

Modify `pipeline.py:97-107`.

Required output:

```python
decision.update({
    "selected_route": "already_solved",
    "route_result": "solved",
    "route_outcome_detail": "already_solved_before_routing",
    "next_recommended_route": None,
    "solver_n_unknown_after": 0,
})
```

Return `RepairRouteResult` with the same values.

No field in `decision` may disagree with the dataclass values.

---

## 3.4 Fix the Phase 2 branch

Modify `pipeline.py:109-142`.

### Required behavior when invoking Phase 2

Set the route family immediately before calling `run_phase2_full_repair(...)`:

```python
phase2_grid_before = grid.copy()
phase2_unknown_before = int(sr.n_unknown)

decision["selected_route"] = "phase2_full_repair"
decision["phase2_full_repair_invoked"] = True
decision["phase2_solver_n_unknown_before"] = phase2_unknown_before
```

The report requires `selected_route="phase2_full_repair"` immediately when Phase 2 is invoked, not only when it solves.

### Required translation from `Phase2FullRepairResult`

After Phase 2:

```python
routed_grid = phase2_result.grid
phase2_log = list(phase2_result.log)
routed_sr = solve_board(routed_grid, max_rounds=int(config.solve_max_rounds), mode="full")

# [AMENDMENT 4] Post-repair solve failure handling
if routed_sr is None or not getattr(routed_sr, "success", True):
    decision.update({
        "route_result": "unresolved_repair_error",
        "route_outcome_detail": "solver_failure_post_repair",
        "solver_n_unknown_after": phase2_unknown_before,  # Revert to pre-repair state
    })
    # Do NOT update grid/sr - preserve original pre-repair state
    return _build_route_result(
        grid=phase2_grid_before,
        sr=sr,
        failure_taxonomy=failure_taxonomy,
        decision=dict(decision),
        phase2_log=phase2_log,
        last100_log=[],
        visual_delta_summary={},
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

`repair.py::run_phase2_full_repair(...)` already supplies `grid`, `n_fixed`, `log`, and `phase2_full_repair_hit_time_budget`; the missing implementation is the `pipeline.py` translation into explicit route-state fields. `repair.py:583-752` is the current source for Phase 2 mutation and accepted-move logs.

### Required Phase 2 outcome mapping

**CRITICAL CLARIFICATION**: The `next_recommended_route` must reflect the *actual next action*, not a generic fallback. If `config.enable_last100` is `True`, the next route is `"last100_repair"`, **not** `"needs_sa_or_adaptive_rerun"`.

```python
# Determine next route based on config and progress
if phase2_solved:
    route_result = "solved"
    route_outcome_detail = "phase2_full_repair_solved"
    next_rec = None
elif phase2_unknown_after < phase2_unknown_before:  # Partial Progress (Reduced unknowns)
    route_result = "unresolved_after_repair"
    route_outcome_detail = "phase2_full_repair_partial_progress_unresolved"
    next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
elif phase2_unknown_after == phase2_unknown_before and phase2_changed_grid:  # No-Op (Grid changed, solver saw no improvement)
    route_result = "unresolved_after_repair"
    route_outcome_detail = "phase2_full_repair_no_op"
    next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
elif phase2_accepted_count == 0:  # No accepted moves
    route_result = "unresolved_after_repair"
    route_outcome_detail = "phase2_full_repair_no_accepted_moves"
    next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
else:  # Changed grid, but no solver improvement
    route_result = "unresolved_after_repair"
    route_outcome_detail = "phase2_full_repair_changed_grid_without_solver_progress"
    next_rec = "last100_repair" if config.enable_last100 else "needs_sa_or_adaptive_rerun"
```

Immediately after this mapping, write the outcome fields back into `decision`:

```python
decision.update({
    "route_result": route_result,
    "route_outcome_detail": route_outcome_detail,
    "next_recommended_route": next_rec,
})
```

The report requires exactly these Phase 2 values, including the partial-progress unresolved state.
The report requires exactly these Phase 2 values, including the partial-progress unresolved state.

**For Phase 2 SOLVED only**: return immediately with visual delta:

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
        grid=routed_grid,
        sr=routed_sr,
        failure_taxonomy=failure_taxonomy,
        decision=dict(decision),
        phase2_log=phase2_log,
        last100_log=[],
        visual_delta_summary=visual_delta_summary,
    )
```

**For Phase 2 partial/no-op/no_accepted (UNRESOLVED)**: Do NOT return. `decision` is updated, `grid` and `sr` are the Phase 2 results. Control flows to Last100 (if enabled) or the final return (Section 3.7).

---


## 3.7 Final Return via `_build_route_result`

Original `pipeline.py:179-188` returned `selected_route="needs_sa_or_adaptive_rerun"` unconditionally. Replace this entire final return with:

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

**Why this works**:

| Scenario | `selected_route` value before this return | How it was set |
|---|---|---|
| Already solved | `"already_solved"` | Early return in Section 3.3 |
| Phase 2 solved | `"phase2_full_repair"` | Section 3.4 (solved case) early return |
| Phase 2 partial/no-op/no_accepted | `"phase2_full_repair"` | Set at start of Phase 2 (Section 3.4) |
| Phase 2 error + Last100 not run | `"phase2_full_repair"` | Error return in Section 3.4 |
| Phase 2 partial + Last100 invoked | `"last100_repair"` | Set at start of Last100 (Section 3.6) |
| Last100 (any outcome) | `"last100_repair"` | Section 3.6 sets before return |
| No route invoked | `"none"` | Default from Section 3.2 |

`_build_route_result` validates all invariants (causal consistency, accepted count equality, etc.) so no additional checks are needed here.

**Important**: `_build_route_result` MUST be the ONLY return path from `route_late_stage_failure`. All other returns shown in Sections 3.4 and 3.6 also use `_build_route_result(...)`.

The original bug (`selected_route="needs_sa_or_adaptive_rerun"` after a route ran) is impossible because `decision["selected_route"]` is never set to that value after a route is invoked.
```

Actually, let's be simpler and clearer:

**Rule**: `_build_route_result` is the ONLY return point for the whole function. Every branch ends with `return _build_route_result(...)`.

In practice:
- Already-solved: returns `_build_route_result` (Section 3.3) ✓
- Phase 2 solved: returns `_build_route_result` (Section 3.4) ✓
- Phase 2 error: returns `_build_route_result` (Section 3.4 §solver_failure) ✓
- Last100 solved/error/partial: returns `_build_route_result` (Section 3.6) ✓
- No route invoked: falls through to final `return _build_route_result` (below) ✓
- Phase 2 partial progress + Last100 enabled: Last100 runs and returns (Section 3.6) ✓
- Phase 2 partial progress + Last100 NOT enabled: Last100 doesn't run, falls through to final `return _build_route_result` ✓

But wait - in the original code, Phase 2 partial progress (grid updated, not solved) continued to Last100 without returning. My Section 3.4 shows Phase 2 updating `decision` and computing visual delta, but NOT returning for partial progress. Let me re-check...

Looking at current Section 3.4: after the outcome mapping and `decision.update(...)`, I ADDED a return with visual delta. That would PREVENT Last100 from running! That's wrong.

I need to REMOVE that return from Phase 2 partial case. Phase 2 should only return immediately for:
- solved case (with visual delta)
- solver_failure_post_repair case

For partial/no-op/no_accepted_moves cases, Phase 2 should just update `decision`, `grid`, `sr`, `phase2_log` and let execution continue to Last100 (if enabled) or the final fallback.

Let me rewrite this cleanly.

---

## 3.6 Fix Last100 translation

Modify `pipeline.py:144-177`.

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
last100_unknown_after = int(routed_sr.n_unknown)
last100_accepted_count = sum(1 for e in last100_log if bool(e.get("accepted", False)))

# [AMENDMENT 4] Post-repair solve failure handling
if routed_sr is None or not getattr(routed_sr, "success", True):
    decision.update({
        "route_result": "unresolved_repair_error",
        "route_outcome_detail": "solver_failure_post_repair",
        "solver_n_unknown_after": last100_unknown_before,  # Revert to pre-repair state
    })
    # Do NOT update grid/sr - preserve original pre-repair state
    return _build_route_result(
        grid=last100_grid_before,
        sr=sr,
        failure_taxonomy=failure_taxonomy,
        decision=dict(decision),
        phase2_log=[],
        last100_log=last100_log,
        visual_delta_summary={},
    )

decision.update({
    "last100_repair_hit_time_budget": bool(last100_result.last100_repair_hit_time_budget),
    "last100_n_fixes": int(last100_result.n_fixes),
    "last100_accepted_move_count": int(last100_accepted_count),
    "last100_solver_n_unknown_after": last100_unknown_after,
    "last100_stop_reason": str(last100_result.stop_reason),
    "solver_n_unknown_after": last100_unknown_after,
})
```

Outcome mapping (preserving Phase 2 fields as phase-specific when Phase 2 ran first):

```python
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
```

Immediately after this mapping, write the outcome fields back into `decision`:

```python
decision.update({
    "route_result": route_result,
    "route_outcome_detail": route_outcome_detail,
    "next_recommended_route": next_rec,
})
```

### Last100 return via `_build_route_result`

```python
# Compute visual delta for this route phase
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
    grid=routed_grid,
    sr=routed_sr,
    failure_taxonomy=failure_taxonomy,
    decision=dict(decision),
    phase2_log=[],
    last100_log=last100_log,
    visual_delta_summary=visual_delta_summary,
)
```
---

# 4. Phase 3: Route-Wide Visual Delta Summary

## 4.1 Import route-wide visual delta calculation

Modify the import block in `pipeline.py:14-25`.

Add:

```python
compute_repair_visual_delta
```

from `repair.py`.

Reason: `repair.py::compute_repair_visual_delta(...)` already computes before/after visual delta. `pipeline.py` needs route-wide summaries instead of selecting only the last move log entry.

## 4.2 Build route-wide visual summary

For Phase 2:

```python
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
```

For Last100:

```python
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
```

The report requires `visual_delta_summary.json` to be route-wide and route-state-aware when Phase 2 changes the grid but does not solve.

For the forensic rerun, `visual_delta_summary.json` must also preserve the same grid-delta facts shown by the overlay:

```text
len(removed_mines) == 192
len(added_mines) == 0
changed_cells == 192
removed_mine_count == 192
added_mine_count == 0
solver_n_unknown_before == 37285
solver_n_unknown_after == 31540
visual_quality_improved == false
solver_progress_improved == true
```

If an intentional algorithmic change produces different counts, the new counts must agree across `visual_delta_summary.json`, the overlay, and metrics for the new run.

---

# 5. Phase 4: Serializer Hardening in `pipeline.py`

Modify `pipeline.py:191-226`.

## 5. Serializer Hardening and Error Handling

### 5.1 Serializer Rule with Invariant Validation

`write_repair_route_artifacts(...)` must only serialize already-complete state. The serializer is the **final enforcement point** for route-state invariants.

Required assertion before writing:

```python
required = {
    "selected_route",
    "route_result",
    "route_outcome_detail",
    "next_recommended_route",
    "solver_n_unknown_before",
    "solver_n_unknown_after",
}
missing = sorted(required - set(repair_route_decision))
if missing:
    raise ValueError(f"Incomplete repair route decision: missing {missing}")

route_state = route_result.route_state_fields()
for key, value in route_state.items():
    if repair_route_decision.get(key) != value:
        raise ValueError(
            f"Repair route decision disagrees with RepairRouteResult for {key}: "
            f"{repair_route_decision.get(key)!r} != {value!r}"
        )
```

### 5.2 Invariant Enforcement: Accepted Move Count

The serializer MUST validate the core invariant from `docs/ROUTE_STATE_FIELD_INVARIANTS.md`:

```python
# [AMENDMENT 4] Invariant Validation
if route_result.phase2_full_repair_invoked:
    phase2_accepted = sum(1 for e in route_result.phase2_log if e.get("accepted", False))
    if route_result.phase2_full_repair_accepted_move_count != phase2_accepted:
        raise RouteStateInvariantError(
            "phase2_full_repair_accepted_move_count",
            route_result.phase2_full_repair_accepted_move_count,
            phase2_accepted,
            {"context": "Phase 2 accepted count mismatch"}
        )
    if route_result.phase2_full_repair_n_fixed != phase2_accepted:
        raise RouteStateInvariantError(
            "phase2_full_repair_n_fixed",
            route_result.phase2_full_repair_n_fixed,
            phase2_accepted,
            {"context": "Phase 2 n_fixed does not match accepted count"}
        )

if route_result.last100_invoked:
    last100_accepted = sum(1 for e in route_result.last100_log if e.get("accepted", False))
    if route_result.last100_accepted_move_count != last100_accepted:
        raise RouteStateInvariantError(
            "last100_accepted_move_count",
            route_result.last100_accepted_move_count,
            last100_accepted,
            {"context": "Last100 accepted count mismatch"}
        )
    if route_result.last100_n_fixes != last100_accepted:
        raise RouteStateInvariantError(
            "last100_n_fixes",
            route_result.last100_n_fixes,
            last100_accepted,
            {"context": "Last100 n_fixes does not match accepted count"}
        )
```

Where `RouteStateInvariantError` is defined as:

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

**Effect**: If `accepted_move_count != n_fixed`, the artifact write is **aborted** with a `RouteStateInvariantError`. This prevents corrupt data from being persisted.

### 5.3 Post-Repair Solve Failure Handling

When `solve_board` is called on a modified grid after Phase 2 or Last100 (to compute `routed_sr`), it may fail or return an invalid result. The plan must handle this.

In the Phase 2 and Last100 outcome mapping code, after computing `routed_sr`:

```python
routed_sr = solve_board(routed_grid, max_rounds=int(config.solve_max_rounds), mode="full")
if routed_sr is None or not getattr(routed_sr, "success", True):
    # [AMENDMENT 4] Handle solver failure gracefully
    decision.update({
        "route_result": "unresolved_repair_error",
        "route_outcome_detail": "solver_failure_post_repair",
        "solver_n_unknown_after": int(sr.n_unknown),  # Revert to pre-repair state
    })
    # Do NOT update grid/sr - preserve original state
    return _build_route_result(
        grid=grid,  # Original grid, NOT routed_grid
        sr=sr,      # Original sr, NOT routed_sr
        failure_taxonomy=failure_taxonomy,
        decision=decision,
        phase2_log=phase2_log,
        last100_log=last100_log,
        visual_delta_summary=visual_delta_summary,
    )
```

**Rationale**: If the solver fails after Phase 2 has modified the grid, we must not lose the original state. The route is marked with `route_outcome_detail="solver_failure_post_repair"` and the original grid is preserved.

### 5.4 Remove primary-field `setdefault(...)`

Do not manufacture primary route-state fields in the serializer.

Allowed:

```python
artifact_metadata injection
```

Forbidden:

```python
repair_route_decision.setdefault("selected_route", ...)  # ❌ NEVER
repair_route_decision.setdefault("route_result", ...)    # ❌ NEVER
repair_route_decision.setdefault("route_outcome_detail", ...)  # ❌ NEVER
repair_route_decision.setdefault("next_recommended_route", ...)  # ❌ NEVER
```

The report explicitly says the writer must not be used to infer missing route state after the fact.

---

# 6. Phase 5: Update `run_iter9.py`

## 6.1 Add route fields to render metrics

Modify `run_iter9.py:842-852`.

Replace:

```python
"repair_route_selected": route.selected_route,
```

with:

```python
render_metrics = {
    **route.route_state_fields(),
    "repair_route_selected": route.selected_route,
    "repair_route_result": route.route_result,
}
```

The alias fields may remain only if:

```python
repair_route_selected == selected_route
repair_route_result == route_result
```

The report allows `repair_route_selected` only as an exact alias of `selected_route`.

---

## 6.2 Replace `repair_reason`

Modify `run_iter9.py:939`.

Current:

```python
"repair_reason": f"phase1={phase1_reason}+route={route.selected_route}",
```

Required:

```python
"repair_reason": (
    f"phase1={phase1_reason}"
    f"+selected_route={route.selected_route}"
    f"+route_result={route.route_result}"
    f"+route_outcome_detail={route.route_outcome_detail}"
    f"+next_recommended_route={route.next_recommended_route}"
),
```

The report requires `repair_reason` to stop embedding ambiguous route language and to be assembled from explicit terms.

---

## 6.3 Update flat metrics

Modify `run_iter9.py:960-971`.

Add:

```python
"selected_route": route.selected_route,
"route_result": route.route_result,
"route_outcome_detail": route.route_outcome_detail,
"next_recommended_route": route.next_recommended_route,

"phase2_full_repair_invoked": route.phase2_full_repair_invoked,
"phase2_full_repair_n_fixed": route.phase2_full_repair_n_fixed,
"phase2_full_repair_accepted_move_count": route.phase2_full_repair_accepted_move_count,
"phase2_full_repair_changed_grid": route.phase2_full_repair_changed_grid,
"phase2_full_repair_reduced_unknowns": route.phase2_full_repair_reduced_unknowns,
"phase2_full_repair_solved": route.phase2_full_repair_solved,
"phase2_solver_n_unknown_before": route.phase2_solver_n_unknown_before,
"phase2_solver_n_unknown_after": route.phase2_solver_n_unknown_after,

"last100_invoked": route.last100_invoked,
"last100_n_fixes": route.last100_n_fixes,
"last100_accepted_move_count": route.last100_accepted_move_count,
"last100_solver_n_unknown_before": route.last100_solver_n_unknown_before,
"last100_solver_n_unknown_after": route.last100_solver_n_unknown_after,
"last100_stop_reason": route.last100_stop_reason,
```

Replace old count aliases:

```python
"phase2_fixes": route.phase2_full_repair_accepted_move_count,
"last100_fixes": route.last100_n_fixes,
```

The report says top-level and nested metrics must carry explicit route-state fields and phase count fields, not infer them from logs.

---

## 6.4 Update nested `repair_route_summary`

Modify `run_iter9.py:1074-1085`.

Required nested summary:

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

The nested `phase2_fixes` and `last100_fixes` fields are explicit compatibility aliases. They must remain exact aliases of `phase2_full_repair_accepted_move_count` and `last100_n_fixes` until the documented schema transition removes them.

---

## 6.5 Update `_llm_review_summary(...)`

Modify `run_iter9.py:392-408` and the call at `run_iter9.py:1136-1144`.

Change function signature:

```python
def _llm_review_summary(
    source_cfg: SourceImageConfig,
    board_label: str,
    seed: int,
    selected_route: str,
    route_result: str,
    route_outcome_detail: str,
    next_recommended_route: str | None,
    n_unknown: int,
    artifact_inventory: dict,
    warnings: list[dict],
) -> dict:
```

Required sentence:

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

The report explicitly says the LLM review summary must not say the run ended “through `needs_sa_or_adaptive_rerun`” for partial Phase 2.

---

## 6.6 Update Iter9 image sweep

Modify these lines:

```text
run_iter9.py:56-75
run_iter9.py:1189-1212
run_iter9.py:1236-1256
run_iter9.py:1269-1309
run_iter9.py:1391-1408
run_iter9.py:1500-1510
```

Add fields to `IMAGE_SWEEP_SUMMARY_FIELDS`:

```python
"selected_route",
"route_result",
"route_outcome_detail",
"next_recommended_route",
"phase2_full_repair_invoked",
"phase2_full_repair_accepted_move_count",
"last100_invoked",
"last100_accepted_move_count",
```

For success rows, read directly from `metrics_doc`.

For failed rows, set all new route-state fields to `None`.

For skipped-existing rows:

```python
hydrated["selected_route"] = existing.get("selected_route")
hydrated["route_result"] = existing.get("route_result")
hydrated["route_outcome_detail"] = existing.get("route_outcome_detail")
hydrated["next_recommended_route"] = existing.get("next_recommended_route")
```

Do **not** synthesize `selected_route` from `repair_route_selected` if the new field is absent.

The report explicitly requires skipped-existing hydration to leave new fields null when the existing metrics file lacks the new schema.

---

# 7. Phase 6: Update `run_benchmark.py`

## 7.1 Update child render metrics

Modify `run_benchmark.py:544-554`.

Add:

```python
render_metrics = {
    **route.route_state_fields(),
    "repair_route_selected": route.selected_route,
    "repair_route_result": route.route_result,
}
```

---

## 7.2 Update `route_summary`

Modify `run_benchmark.py:634-645`.

Required:

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

---

## 7.3 Update flat metrics

Modify `run_benchmark.py:668-701`.

Same rule as Iter9:

```python
flat_metrics = {
    **route.route_state_fields(),
    "repair_route_selected": route.selected_route,
    "repair_route_result": route.route_result,
    "phase2_fixes": route.phase2_full_repair_accepted_move_count,
    "last100_fixes": route.last100_n_fixes,
}
```

Replace `repair_reason` at `run_benchmark.py:691` with the structured form:

```python
"repair_reason": (
    f"phase1={phase1_reason}"
    f"+selected_route={route.selected_route}"
    f"+route_result={route.route_result}"
    f"+route_outcome_detail={route.route_outcome_detail}"
    f"+next_recommended_route={route.next_recommended_route}"
),
```

---

## 7.4 Update benchmark summary rows

Modify `run_benchmark.py:737-766`.

Add row fields:

```python
"selected_route": metrics.get("selected_route"),
"route_result": metrics.get("route_result"),
"route_outcome_detail": metrics.get("route_outcome_detail"),
"next_recommended_route": metrics.get("next_recommended_route"),
"phase2_full_repair_invoked": metrics.get("phase2_full_repair_invoked"),
"phase2_full_repair_accepted_move_count": metrics.get("phase2_full_repair_accepted_move_count"),
"last100_invoked": metrics.get("last100_invoked"),
"last100_accepted_move_count": metrics.get("last100_accepted_move_count"),
```

Keep `repair_route_selected` only as an alias:

```python
"repair_route_selected": metrics.get("selected_route"),
"repair_route_result": metrics.get("route_result"),
```

The report requires benchmark summary rows to stop treating `repair_route_selected` as the complete route-state description.

---

## 7.5 Update benchmark Markdown

Modify `run_benchmark.py:840-851`.

Replace the child table header with:

```markdown
| board | seed | child_dir | n_unknown | coverage | solvable | selected_route | route_result | route_outcome_detail | next_recommended_route | phase2_accepted | last100_accepted | phase1_timeout | phase2_full_timeout | last100_timeout | visual_delta | total_time_s |
```

Rows must use:

```python
row["selected_route"]
row["route_result"]
row["route_outcome_detail"]
row["next_recommended_route"]
row["phase2_full_repair_accepted_move_count"]
row["last100_accepted_move_count"]
```

The current Markdown table has only a generic `route` column and displays `repair_route_selected`; that table shape is noncompliant under Recommendation 4.

---

## 7.6 Update benchmark CSV

Modify `run_benchmark.py:888-909`.

Add headers:

```python
"selected_route",
"route_result",
"route_outcome_detail",
"next_recommended_route",
"phase2_full_repair_invoked",
"phase2_full_repair_n_fixed",
"phase2_full_repair_accepted_move_count",
"last100_invoked",
"last100_n_fixes",
"last100_accepted_move_count",
```

Keep aliases only if they equal the canonical fields:

```python
"repair_route_selected",
"repair_route_result",
```

The report requires benchmark JSON rows, CSV rows, Markdown rows, and `benchmark_results.json` rows to agree on the four route-state fields.

---

## 7.7 Update regression-only output and checks

Modify `run_benchmark.py:947-1004` and `run_benchmark.py:1035-1055`.

Regression output must include:

```python
result = {
    **route.route_state_fields(),
    "repair_route_selected": route.selected_route,
    "repair_route_result": route.route_result,
    "phase2_fixes": route.phase2_full_repair_accepted_move_count,
    "last100_fixes": route.last100_n_fixes,
}
```

Change checks from:

```python
result["repair_route_selected"] != case["expected_route"]
```

to:

```python
result["selected_route"] != case["expected_route"]
```

Console output should print:

```python
route={result["selected_route"]}
route_result={result["route_result"]}
route_outcome_detail={result["route_outcome_detail"]}
```

The report requires regression checks to compare expected selected route against `selected_route`, not against a field that may contain a next recommendation.

---

# 8. Phase 7: Update `report.py`

Modify `report.py:312-349`.

## 8.1 Replace route lookup

Current:

```python
route = _coalesce(metrics.get("repair_route_selected"), "unknown repair route")
```

Required:

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

## 8.2 Required plain-English route text

For unresolved:

```python
f"The late-stage route used here was {selected_route}. "
f"It ended with route_result={route_result} and route_outcome_detail={route_outcome_detail}. "
f"The next recommended route is {next_recommended_route}."
```

If `route_contract_warning` is not `None`, append that warning to the plain-English route section. Do not silently fall back to `repair_route_selected` as the performed route.

For solved:

```python
f"The late-stage route used here was {selected_route}. "
f"It ended with route_result={route_result} and route_outcome_detail={route_outcome_detail}. "
f"No next route is required."
```

The report requires report text to read `selected_route` as the performed route and `next_recommended_route` as the next step.

---

# 9. Phase 8: Documentation and Schema Updates

Update these files:

```text
AGENTS.md
for_user_review.md
docs/json_schema/repair_route_decision.schema.md
docs/json_schema/metrics_iter9.schema.md
docs/json_schema/visual_delta_summary.schema.md
docs/json_schema/benchmark_summary.schema.md
docs/json_schema/JSON_OUTPUT_SCHEMA_INDEX.md
README.md
docs/DOCS_INDEX.md
demo/docs/artifact_consumption_contract.md
```

Required schema content:

```text
selected_route
route_result
route_outcome_detail
next_recommended_route
phase2_full_repair_invoked
phase2_full_repair_hit_time_budget
phase2_full_repair_n_fixed
phase2_full_repair_accepted_move_count
phase2_full_repair_changed_grid
phase2_full_repair_reduced_unknowns
phase2_full_repair_solved
phase2_solver_n_unknown_before
phase2_solver_n_unknown_after
last100_invoked
last100_repair_hit_time_budget
last100_n_fixes
last100_accepted_move_count
last100_solver_n_unknown_before
last100_solver_n_unknown_after
last100_stop_reason
solver_n_unknown_before
solver_n_unknown_after
```

Remove or rewrite any schema prose that says Phase 2 activity can be inferred from timeout fields or old metrics counts.

The report explicitly requires these schema updates and states that examples must not preserve old semantics where `selected_route` means “next recommendation.”

If any schema, README text, fixture prose, or generated example currently lists `needs_sa_or_adaptive_rerun` as an allowed or expected value for `selected_route`, move that value to `next_recommended_route` and rewrite the surrounding prose so `selected_route` names only an invoked route family or `"none"` before any late-stage route is invoked. `needs_sa_or_adaptive_rerun` may appear in `selected_route` documentation only as an explicitly invalid pre-correction example or stale-artifact warning.

`demo/docs/artifact_consumption_contract.md` must be read before editing and updated only where it consumes Iter9 route artifacts or route summaries. The demo docs must not retain stale `repair_route_selected` or `selected_route = "needs_sa_or_adaptive_rerun"` semantics for routed partial Phase 2 runs.

`for_user_review.md` must contain the external-consumer transition notes from Section 0.1 and must cite the validation evidence produced by this implementation.

---

# 10. Cross-Surface Invariants

After implementation, enforce these invariants in tests:

```text
repair_route_decision.json.selected_route
  == metrics_iter9_<board>.json.selected_route

repair_route_decision.json.route_result
  == metrics_iter9_<board>.json.route_result

repair_route_decision.json.route_outcome_detail
  == metrics_iter9_<board>.json.route_outcome_detail

repair_route_decision.json.next_recommended_route
  == metrics_iter9_<board>.json.next_recommended_route

repair_route_decision.json.solver_n_unknown_after
  == metrics_iter9_<board>.json.solver_summary.post_routing.n_unknown

repair_route_decision.json.solver_n_unknown_after
  == route.sr.n_unknown in the producer test fixture

metrics_iter9_<board>.json.repair_route_summary.selected_route
  == metrics_iter9_<board>.json.selected_route

metrics_iter9_<board>.json.repair_route_summary.route_result
  == metrics_iter9_<board>.json.route_result

metrics_iter9_<board>.json.repair_route_summary.route_outcome_detail
  == metrics_iter9_<board>.json.route_outcome_detail

metrics_iter9_<board>.json.repair_route_summary.next_recommended_route
  == metrics_iter9_<board>.json.next_recommended_route

metrics_iter9_<board>.json.repair_route_summary.phase2_fixes
  == repair_route_decision.json.phase2_full_repair_accepted_move_count

visual_delta_summary.json.accepted_move_count
  == repair_route_decision.json.phase2_full_repair_accepted_move_count
  when selected_route == "phase2_full_repair"
```

For benchmark:

```text
child metrics
child repair_route_decision.json
benchmark_summary.json rows
benchmark_summary.csv rows
benchmark_summary.md rows
benchmark_results.json rows
```

must agree on:

```text
selected_route
route_result
route_outcome_detail
next_recommended_route
```

Producer-level invariant tests must also assert:

```text
_build_route_result(...) raises ValueError when:
  decision["solver_n_unknown_after"] != int(sr.n_unknown)

_build_route_result(...) raises ValueError when:
  decision["selected_route"] == "needs_sa_or_adaptive_rerun"

_build_route_result(...) raises ValueError when:
  phase2_full_repair_invoked == true
  last100_invoked == false
  selected_route != "phase2_full_repair"

_build_route_result(...) raises ValueError when:
  any key returned by route.route_state_fields()
  disagrees with route.decision[key]

artifact-validator/schema tests reject stale route-state artifacts when:
  selected_route == "needs_sa_or_adaptive_rerun"
  and next_recommended_route is missing
  and route invocation is true or non-disambiguated
```

These invariants are required by the report.

---

# 11. Forensic Acceptance Criteria

For the known forensic rerun, if algorithm behavior remains unchanged, required values are:

```text
selected_route = "phase2_full_repair"
route_result = "unresolved_after_repair"
route_outcome_detail = "phase2_full_repair_partial_progress_unresolved"
next_recommended_route = "needs_sa_or_adaptive_rerun"
phase2_full_repair_invoked = true
phase2_full_repair_hit_time_budget = false
phase2_full_repair_n_fixed > 0
phase2_full_repair_accepted_move_count > 0
last100_invoked = false
solver_n_unknown_before = 37285
phase2_solver_n_unknown_before = 37285
phase2_solver_n_unknown_after = 31540
solver_n_unknown_after = 31540
visual_delta_summary.summary_scope = "route_phase"
visual_delta_summary.route_phase = "phase2_full_repair"
visual_delta_summary.solver_n_unknown_before = 37285
visual_delta_summary.solver_n_unknown_after = 31540
visual_delta_summary.mean_abs_error_before = 0.9614354968070984
visual_delta_summary.mean_abs_error_after = 0.9689586162567139
visual_delta_summary.visual_delta = 0.0075231194496154785
len(visual_delta_summary.removed_mines) = 192
len(visual_delta_summary.added_mines) = 0
visual_delta_summary.changed_cells = 192
visual_delta_summary.removed_mine_count = 192
visual_delta_summary.added_mine_count = 0
visual_delta_summary.visual_quality_improved = false
visual_delta_summary.solver_progress_improved = true
overlay_removed_mine_count = visual_delta_summary.removed_mine_count
overlay_added_mine_count = visual_delta_summary.added_mine_count
visual_delta_summary.accepted_move_count = repair_route_decision.phase2_full_repair_accepted_move_count
repair_route_summary.phase2_fixes = repair_route_decision.phase2_full_repair_accepted_move_count
```

The report defines these as the required forensic values for this run.

---

# 12. Execution Order

## Step 1: Classification search

Run:

```powershell
rg -n "repair_route_selected|selected_route|route_result|needs_sa_or_adaptive_rerun|phase2_fixes|last100_fixes|repair_route_decision|visual_delta_summary" -S .
```

Classify every hit as:

```text
producer
transformer
consumer
serializer
docs/schema
```

No hit may retain the old semantic meaning.

The report requires this exact search and classification step.

---

## Step 2: Add failing tests

Run targeted tests and confirm failures:

```powershell
python -m unittest tests.test_repair_route_decision
python -m unittest tests.test_route_artifact_metadata
python -m unittest tests.test_benchmark_layout
python -m unittest tests.test_source_image_cli_contract
python -m unittest tests.test_iter9_image_sweep_contract
python -m unittest tests.test_report_explanations
```

---

## Step 3: Implement `pipeline.py`

Implement:

```text
RepairRouteResult field expansion
route_state_fields()
_build_route_result()
strict write-back contract after every grid/sr mutation
default decision replacement
already-solved branch
Phase 2 translation
Phase 2 partial-progress return
Last100 translation
route-wide visual_delta_summary
serializer completeness guard
```

---

## Step 4: Implement `run_iter9.py`

Implement:

```text
render_metrics route-state fields
flat metrics route-state fields
repair_reason structured form
repair_route_summary route-state fields
_llm_review_summary route text
image sweep fields
skipped-existing hydration rule
failed-row null route fields
Markdown and CSV route-state headers
```

---

## Step 5: Implement `run_benchmark.py`

Implement:

```text
child render_metrics route-state fields
route_summary route-state fields
flat_metrics route-state fields
benchmark rows
benchmark CSV headers
benchmark Markdown headers
benchmark_results.json rows
regression-only records
regression route checks
console route output
```

---

## Step 6: Implement `report.py`

Implement:

```text
selected_route text
route_result text
route_outcome_detail text
next_recommended_route text
schema-incomplete warning when selected_route is missing
no fallback from repair_route_selected to selected_route
```

---

## Step 7: Update docs and schemas

Update `AGENTS.md`, `for_user_review.md`, all affected schema examples, README text, and demo artifact-consumption text.

No example may show:

```text
selected_route = "needs_sa_or_adaptive_rerun"
```

when any repair route ran.

---

## Step 8: Run validation

Targeted:

```powershell
python -m unittest tests.test_repair_route_decision
python -m unittest tests.test_route_artifact_metadata
python -m unittest tests.test_benchmark_layout
python -m unittest tests.test_source_image_cli_contract
python -m unittest tests.test_iter9_image_sweep_contract
python -m unittest tests.test_report_explanations
```

Documentation/governance verification:

```powershell
@'
from pathlib import Path
required = {
    "AGENTS.md": [
        "Route-state field semantics may be corrected",
        "regression-only outputs, checks, docs, and expected-route comparisons must be updated consistently",
    ],
    "for_user_review.md": [
        "applicability",
        "impact",
        "transition",
        "validation evidence",
    ],
    "demo/docs/artifact_consumption_contract.md": [
        "selected_route",
        "route_outcome_detail",
        "next_recommended_route",
    ],
}
for path, needles in required.items():
    text = Path(path).read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{path} missing {missing}")
'@ | python -
```

Full suite:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

Forensic rerun:

```powershell
python run_iter9.py --image assets/line_art_irl_14.png --run-tag Forensic-Run-RouteDecisionFix --seed 44 --board-w 300 --allow-noncanonical
```

The report requires this forensic rerun and acceptance check.

The rerun must produce a new result directory and must not overwrite:

`results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/`

Validation must assert that the rerun output directory path differs from the original forensic directory and that the original artifact timestamps remain unchanged.

After the forensic rerun, run a JSON/grid consistency probe that asserts:

```text
repair_route_decision.json.selected_route == metrics.selected_route
repair_route_decision.json.route_result == metrics.route_result
repair_route_decision.json.route_outcome_detail == metrics.route_outcome_detail
repair_route_decision.json.next_recommended_route == metrics.next_recommended_route
repair_route_decision.json.solver_n_unknown_after == metrics.solver_summary.post_routing.n_unknown
repair_route_decision.json.phase2_full_repair_n_fixed > 0
repair_route_decision.json.phase2_full_repair_accepted_move_count > 0
metrics.repair_route_summary.phase2_fixes == repair_route_decision.json.phase2_full_repair_accepted_move_count
visual_delta_summary.json.solver_n_unknown_after == repair_route_decision.json.solver_n_unknown_after
visual_delta_summary.json.accepted_move_count == repair_route_decision.json.phase2_full_repair_accepted_move_count
visual_delta_summary.json.mean_abs_error_before == metrics.visual_quality_summary.mean_abs_error_before_repair
visual_delta_summary.json.mean_abs_error_after == metrics.visual_quality_summary.mean_abs_error_after_repair
visual_delta_summary.json.visual_delta == metrics.visual_quality_summary.visual_delta
len(visual_delta_summary.json.removed_mines) == visual_delta_summary.json.removed_mine_count
len(visual_delta_summary.json.added_mines) == visual_delta_summary.json.added_mine_count
grid_iter9_latest.npy equals the board-specific final grid npy
```

---

# 13. Non-Goals

Do **not**:

```text
change Phase 2 search behavior
make visual error the Phase 2 acceptance criterion
reinterpret Phase 1 changes as route changes
label partial Phase 2 progress as solved
use phase2_full_repair_hit_time_budget=false to imply Phase 2 was not invoked
add legacy_repair_route_selected
preserve old selected_route semantics in any schema, fixture, row, summary, report, or README example
```

The report explicitly defines these non-goals.

---

# Appendix D: Route Outcome Detail Enumeration

The `route_outcome_detail` field must use exactly one of these values. No free-text variations are permitted.

| Value | Meaning |
|---|---|
| `already_solved_before_routing` | Board was solved before late-stage routing began |
| `phase2_full_repair_solved` | Phase 2 successfully solved the board |
| `phase2_full_repair_partial_progress_unresolved` | Phase 2 made progress (reduced unknowns) but did not solve |
| `phase2_full_repair_no_op` | Phase 2 invoked but made zero progress (no reduction in unknowns) |
| `phase2_full_repair_no_accepted_moves` | Phase 2 invoked but accepted zero moves |
| `last100_repair_solved` | Last100 successfully solved the board |
| `last100_repair_timeout_unresolved` | Last100 hit time budget and remains unresolved |
| `last100_repair_partial_progress_unresolved` | Last100 made progress but remains unresolved |
| `last100_repair_no_accepted_moves` | Last100 invoked but accepted zero moves |
| `no_late_stage_route_invoked` | No late-stage route was attempted |
| `unresolved_repair_error` | A solver failure or invariant violation occurred during repair |

Schema files must constrain this field to these enumerated values.

---

# Appendix E: Hardening Checklist for Implementation

This checklist must be completed before marking Recommendation 4 as implemented:

## Data Migration
- [ ] Script provided to backfill `route_outcome_detail` and `next_recommended_route` in existing artifacts
- [ ] Schema version field added to all route artifacts to distinguish old vs new format
- [ ] Legacy artifact loader handles missing fields with warnings (not errors)

## Invariant Enforcement
- [ ] `RouteStateInvariantError` exception class defined in `pipeline.py`
- [ ] Serializer guard validates `accepted_move_count == n_fixed` for Phase 2 and Last100
- [ ] Any invariant violation raises `RouteStateInvariantError` and aborts artifact write
- [ ] Tests verify invariant enforcement catches deliberate tampering

## Transactional Boundaries
- [ ] `_build_route_result` includes causal validation (Phase 2 invoked → selected_route is phase2_full_repair)
- [ ] `_build_route_result` rejects `selected_route == "needs_sa_or_adaptive_rerun"` after route invoked
- [ ] Phase 2 and Last100 branches use copy-on-write: validate BEFORE committing grid/sr changes
- [ ] Solver failure after grid modification reverts to original grid and marks error

## State Transitions
- [ ] No-route unresolved branch sets `selected_route="none"`
- [ ] Already-solved branch sets `route_outcome_detail="already_solved_before_routing"`
- [ ] Phase 2 partial progress sets `next_recommended_route` based on `config.enable_last100`
- [ ] Last100 partial progress sets `next_recommended_route="needs_sa_or_adaptive_rerun"`

## Documentation
- [ ] `for_user_review.md` lists all affected artifacts and field-level backward compatibility notes
- [ ] `demo/docs/artifact_consumption_contract.md` updated to use canonical field names
- [ ] Schema files updated with new required fields and `route_outcome_detail` enum
- [ ] Deprecation warning added for `repair_route_selected`, `phase2_fixes`, `last100_fixes`

## Testing
- [ ] Test for Phase 2 invocation with zero progress (`n_fixed == 0`)
- [ ] Test for Phase 2 partial progress with Last100 enabled (check `next_recommended_route`)
- [ ] Test for Last100 with rejected moves (verify `accepted_move_count != len(log)`)
- [ ] Test for invariant violation (tamper with counts, expect `RouteStateInvariantError`)
- [ ] Test for solver failure after Phase 2 (expect `route_outcome_detail="solver_failure_post_repair"`)
- [ ] Forensic rerun passes with corrected route state

## Logging and Observability
- [ ] Invariant violations log as ERROR with full context (grid hash, sr state, log entries)
- [ ] Solver failures after repair logged as WARNING with route context
- [ ] Deprecation warnings emitted when legacy fields are accessed

---

# Appendix F: Field Mapping Table

Canonical source of truth for all route-state fields:

| Field | Source | Notes |
|---|---|---|
| `selected_route` | `decision["selected_route"]` | Must match invoked route family |
| `route_result` | `decision["route_result"]` | `solved` or `unresolved_after_repair` |
| `route_outcome_detail` | `decision["route_outcome_detail"]` | Must be from Appendix D enum |
| `next_recommended_route` | `decision["next_recommended_route"]` | `None` or next route or `needs_sa_or_adaptive_rerun` |
| `solver_n_unknown_before` | `decision["solver_n_unknown_before"]` | Must equal initial `sr.n_unknown` |
| `solver_n_unknown_after` | `sr.n_unknown` | Must equal `decision["solver_n_unknown_after"]` |
| `phase2_full_repair_n_fixed` | `phase2_result.n_fixed` | Direct counter from `repair.py` |
| `phase2_full_repair_accepted_move_count` | `sum(1 for e in phase2_log if e["accepted"])` | Must equal `phase2_full_repair_n_fixed` |
| `last100_n_fixes` | `last100_result.n_fixes` | Direct counter from `repair.py` |
| `last100_accepted_move_count` | `sum(1 for e in last100_log if e["accepted"])` | Must equal `last100_n_fixes` |

