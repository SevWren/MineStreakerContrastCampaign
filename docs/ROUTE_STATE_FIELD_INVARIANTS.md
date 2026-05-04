# Route-State Field Invariant Contract

This document specifies the mathematical and semantic invariants that all 
route-state artifacts must maintain. These invariants are ENFORCED by serializer 
guards (Section 5 of Recommendation 4) and validation tests (Section 2 of Recommendation 4).

**Governance Status**: Required reading before implementing Recommendation 4.  
**Reference**: AGENTS.md § Route-State Field Invariants  
**Implementation Plan**: docs/industry_standard_implementation_execution_plan_recommendation_4.md

---

## Accepted Move Count Invariant

### Definition

For every repair route invocation (Phase2 or Last100), the accepted move count 
must be independently computable from both:

1. **Direct Counter**: the repair result object's counter (`n_fixed` or `n_fixes`)
2. **Defensive Recount**: log inspection counting only entries with `"accepted": True`

Both must always be equal:

```python
accepted_move_count = sum(1 for e in repair_log if e["accepted"] == True)
                    == repair_result.n_fixed      (for Phase2)
                    == repair_result.n_fixes      (for Last100)
```

### Why This Invariant Exists: Three Reasons

#### 1. The Last100 Log-Mixing Bug (Critical Fix)

**Current Problem** (repair.py as of analysis date):

`repair.py::run_last100_repair()` appends entries to `move_log` for both:
- **REJECTED moves** (guardrail violations): appended at line 485 with `"accepted": False`
- **ACCEPTED moves** (passes all checks): appended at line 509 with `"accepted": True`

**Current Code Bug** (run_iter9.py:966, run_benchmark.py:639):

```python
"phase2_fixes": len(route.last100_log)  # ← WRONG for Last100
```

**Impact**:
- Counts BOTH accepted AND rejected entries
- Inflates last100 fixes metric, obscuring actual accepted moves
- Hides guardrail rejection activity
- Metrics artifact becomes misleading

**This Plan's Fix**:

Defensive recount recovers the correct value:

```python
last100_accepted_count = sum(1 for e in last100_log if e["accepted"] == True)
                       == last100_result.n_fixes  # invariant
```

Serializer guards (Section 5) validate this invariant before writing artifacts.

#### 2. Phase2 Defensive Verification (Robustness)

**Current Behavior** (repair.py:583-752):

Phase2 logs ONLY accepted moves:
- Line 712: `n_fixed += 1` (when `best_mine is not None`, i.e., accepted)
- Line 722: `log.append({...,'accepted': True,...})`

**Mathematical Property**:
```
sum(1 for e in phase2_log if e["accepted"]) == n_fixed  (always true today)
len(phase2_log) == n_fixed  (always true today)
```

**Why Still Introduce Defensive Recount**?

1. **Catch Accidental Changes**: If Phase2 refactoring ever adds rejected-move logging, 
   the invariant check catches it early (defensive programming)

2. **Enforce Consistency**: Provides an explicit, testable correlation between grid 
   mutations (`n_fixed`) and logged moves, not just log length

3. **Parity with Last100**: Both repair functions use the same validation pattern, 
   reducing cognitive load and bug surface

**Example Scenario Where Invariant Catches a Bug**:

Imagine a future refactor adds:
```python
trial = grid.copy()
trial[my, mx] = 0
sr_t = solve_board(trial, ...)
if sr_t.n_unknown > sr.n_unknown:  # Rejects improvement
    log.append({'accepted': False, 'reason': 'no_progress'})  # New behavior
```

Without the invariant check:
- `n_fixed` stays at 22
- `len(log)` becomes 30 (includes rejections)
- Metrics silently diverge, breaking artifact consistency

With the invariant enforced by tests:
- Test assertion fails: `sum(accepted) == n_fixed` fails
- Developer catches the issue **before** it propagates to prod artifacts

#### 3. Artifact Consistency Enforcement

The invariant ensures all downstream artifacts report the same accepted count:

```
repair.py (counter)
  ↓
pipeline.py (decision dict decision["phase2_full_repair_accepted_move_count"])
  ↓
├─ repair_route_decision.json (top-level field)
├─ metrics_iter9_*.json (nested in repair_route_summary.phase2_fixes)
└─ visual_delta_summary.json ("accepted_move_count" field)
```

If any artifact computes this differently, the invariant-check tests catch it.

---

## Field Mapping and Computation

### Phase2

| Field | Source | Computation | Must Equal |
|-------|--------|-------------|-----------|
| `phase2_full_repair_n_fixed` | `phase2_result.n_fixed` | Direct counter | Direct counter (no recomputation) |
| `phase2_full_repair_accepted_move_count` | `phase2_log` | `sum(1 for e in log if e["accepted"])` | `n_fixed` |

**Where Used**:
- `repair_route_decision.json`
- `metrics_iter9_*.json.repair_route_summary.phase2_fixes` (as compatibility alias)
- `visual_delta_summary.json.accepted_move_count`

### Last100

| Field | Source | Computation | Must Equal |
|-------|--------|-------------|-----------|
| `last100_n_fixes` | `last100_result.n_fixes` | Direct counter | Direct counter (no recomputation) |
| `last100_accepted_move_count` | `last100_log` | `sum(1 for e in log if e["accepted"])` | `n_fixes` |

**Where Used**:
- `repair_route_decision.json`
- `metrics_iter9_*.json.repair_route_summary.last100_fixes` (as compatibility alias)
- `visual_delta_summary.json.accepted_move_count`

---

## Enforcement Points

### 1. Serializer Guard (pipeline.py::write_repair_route_artifacts)

**When**: Immediately before writing `repair_route_decision.json`

**What**:
```python
# Validate dataclass-to-decision route-state equality
route_state = route.route_state_fields()

# Phase2 invariant
if route.phase2_full_repair_invoked:
    phase2_accepted = sum(1 for e in route.phase2_log if e.get("accepted"))
    assert route.phase2_full_repair_accepted_move_count == phase2_accepted, \
        f"Phase2 accepted count mismatch: dataclass={route.phase2_full_repair_accepted_move_count} != log_recount={phase2_accepted}"
    assert route.phase2_full_repair_n_fixed == phase2_accepted, \
        f"Phase2 n_fixed mismatch with accepted count: n_fixed={route.phase2_full_repair_n_fixed} != accepted={phase2_accepted}"

# Last100 invariant
if route.last100_invoked:
    last100_accepted = sum(1 for e in route.last100_log if e.get("accepted"))
    assert route.last100_accepted_move_count == last100_accepted, \
        f"Last100 accepted count mismatch: dataclass={route.last100_accepted_move_count} != log_recount={last100_accepted}"
    assert route.last100_n_fixes == last100_accepted, \
        f"Last100 n_fixes mismatch with accepted count: n_fixes={route.last100_n_fixes} != accepted={last100_accepted}"

# Write decision dict
decision_dict = route_state_fields() | route.decision  # merged
atomic_save_json(decision_dict, artifact_path)
```

**Effect**: Rejects any artifact write if invariant is violated; prevents stale or malformed artifacts.

### 2. Metrics Unit Tests (tests/test_repair_route_decision.py)

**Required Assertions** (Section 2.1 of Recommendation 4):

For each branch (already-solved, phase2-partial, phase2-solved, last100-partial, last100-solved):

```python
def test_phase2_partial_progress_route():
    # Arrange
    phase2_result = Phase2FullRepairResult(
        grid=..., n_fixed=1, log=[{..., 'accepted': True}], timeout=False
    )
    
    # Act
    route = route_late_stage_failure(grid, target, weights, forbidden, sr, config)
    
    # Assert - Invariant check
    assert route.phase2_full_repair_n_fixed == 1
    assert route.phase2_full_repair_accepted_move_count == 1
    assert route.phase2_full_repair_accepted_move_count == route.phase2_full_repair_n_fixed
```

### 3. Cross-Artifact Validation (forensic rerun step 12.8)

**Forensic acceptance criteria** (Section 12 of Recommendation 4):

For the unchanged forensic rerun (`line_art_irl_14.png`, seed 44):

```python
# Read artifacts
decision = json.load(open('repair_route_decision.json'))
metrics = json.load(open('metrics_iter9_300x538.json'))
visual_delta = json.load(open('visual_delta_summary.json'))

# Assert invariants
assert decision['phase2_full_repair_accepted_move_count'] == 192, \
    f"Expected 192 accepted Phase2 moves, got {decision['phase2_full_repair_accepted_move_count']}"

assert decision['phase2_full_repair_n_fixed'] == 192, \
    f"Expected n_fixed=192, got {decision['phase2_full_repair_n_fixed']}"

# Cross-artifact equality
assert visual_delta['accepted_move_count'] == decision['phase2_full_repair_accepted_move_count'], \
    f"Visual delta and decision mismatch: {visual_delta['accepted_move_count']} != {decision['phase2_full_repair_accepted_move_count']}"

assert metrics['repair_route_summary']['phase2_fixes'] == decision['phase2_full_repair_accepted_move_count'], \
    f"Metrics and decision mismatch: {metrics['repair_route_summary']['phase2_fixes']} != {decision['phase2_full_repair_accepted_move_count']}"
```

### 4. Schema Validation (docs/json_schema/)

**Required Schema Updates**:

- `repair_route_decision.schema.md`: 
  - Add `phase2_full_repair_accepted_move_count: integer` (required)
  - Add `last100_accepted_move_count: integer` (required)
  - Document invariant: both must be present and equal to corresponding n_fixed/n_fixes

- `visual_delta_summary.schema.md`:
  - Add `accepted_move_count: integer` (required)
  - Document: must equal `repair_route_decision.json.phase2_full_repair_accepted_move_count` when phase2 is final route

- `metrics_iter9.schema.md`:
  - Update `repair_route_summary.phase2_fixes` documentation to state it is computed from `repair_route_decision.json.phase2_full_repair_accepted_move_count`

---

## Test Coverage Requirements

From Section 2.2 of Recommendation 4:

| Test File | Test Case | Assertion |
|-----------|-----------|-----------|
| `tests/test_repair_route_decision.py` | Phase2 partial | `phase2_accepted == n_fixed` |
| `tests/test_repair_route_decision.py` | Last100 unresolved | `last100_accepted == n_fixes` |
| `tests/test_route_artifact_metadata.py` | Serializer guard | Accept only if invariant holds |
| `tests/test_benchmark_layout.py` | Child metrics conversion | `phase2_fixes == phase2_full_repair_accepted_move_count` |
| Forensic rerun (step 12.8) | Cross-artifact equality | All three artifacts report same accepted count |

---

## Migration Path

### Phase 1: New Field Introduction (Recommendation 4)

1. Add `phase2_full_repair_accepted_move_count` and `last100_accepted_move_count` to `RepairRouteResult`
2. Compute recount in pipeline.py
3. Add serializer guard (mandatory enforcement)
4. Add test assertions
5. Write metrics and visual_delta with new fields

### Phase 2: Backward Compatibility (Future)

Once all artifacts use the new fields:
- Old `repair_route_selected` and `phase2_fixes` may be removed
- Transition documented in `for_user_review.md`

### Phase 3: Schema Normalization (Future)

- Schemas require both `n_fixed` and `accepted_move_count`
- Validation tools reject old artifacts missing recount field
- Consumers must use new fields exclusively

---

## Rationale for Dual Metrics

**Q: Why not just use `n_fixed` directly?**

A: Because:
1. **Last100 bug is real**: The current code using `len(move_log)` is wrong
2. **Defensive verification is valuable**: Catches Phase2 refactors early
3. **Artifact consistency requires it**: All three downstream consumers (metrics, visual_delta, repair_route_decision) must compute the same value
4. **Test-driven enforcement**: The dual computation makes the invariant explicit and testable

**Q: Doesn't this add overhead?**

A: Minimal:
- Recount is O(n) where n = number of log entries (typically 1-20 per route)
- Done once at serialization time
- Catches bugs that would otherwise propagate to prod artifacts

**Q: What if a future repair function uses a different pattern?**

A: This contract defines the pattern. Any new repair function must:
1. Return a counter (`n_fixed` or equivalent)
2. Log accepted moves with `"accepted": True`
3. Submit to the same invariant verification in pipeline.py

If a new function has a different pattern, it requires explicit contract amendment and board review.

---

## Related Documentation

- **Implementation Plan**: docs/industry_standard_implementation_execution_plan_recommendation_4.md (Sections 3.1, 3.4, 3.5, 4.2)
- **Governance**: AGENTS.md § Route-State Field Invariants, § Late-Stage Repair Routing Ownership
- **Transition Notes**: for_user_review.md (applicability, impact, migration guidance)
- **Demo Artifacts**: demo/docs/artifact_consumption_contract.md (must reflect new field contract)

---

## Summary

This invariant contract ensures that repair-route artifacts are internally consistent, that the Last100 bug is fixed, and that future repairs follow the same defensive-verification pattern. Enforcement is mandatory at serialization time and verified by comprehensive test coverage.

**Before implementing Recommendation 4, read this document.**  
**After implementing, verify the forensic rerun passes all invariant checks at Section 12.8.**
