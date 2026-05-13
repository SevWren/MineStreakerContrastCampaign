# Forensic Review: Recommendation 4 Implementation Plan

---

## IMPLEMENTATION STATUS: COMPLETE

**This was a pre-implementation plan review.** The plan is now fully implemented.

**Implemented:** 2026-05-13 · Commit `ef7d5de` · Branch `working-changes`

> The "Evidence Snapshot" below documents the BROKEN artifact values that prompted this work.
> All 14 mandatory corrections listed in this review have been applied.
> See `implementation_prompt_recommendation_4.md` for the full completion record.

---

Reviewed plan:

`docs/industry_standard_implementation_execution_plan_recommendation_4.md`

Primary source report:

`results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/forensic_route_decision_recommendations_report.md`

Forensic run directory:

`results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/`

## Review Verdict

Implementation-ready status is now achieved for the reviewed plan when implemented with the mandatory amendments in `docs/industry_standard_implementation_execution_plan_recommendation_4.md`.

The plan captures the central architectural fix: `selected_route` must mean the actual invoked route, while `next_recommended_route` carries `needs_sa_or_adaptive_rerun` when the board remains unresolved. The previous blocker-level gaps are resolved by explicit plan requirements for governance, external-consumer notes, report text behavior, demo artifact-consumption docs, visual/overlay acceptance checks, serializer equality checks, and syntactically complete code snippets.

## Implementation-Ready Resolution Summary

The reviewed implementation plan now includes these mandatory corrections:

1. `AGENTS.md` must be amended before runtime changes so regression-only fixed-case behavior remains stable while route-state output/check semantics may be corrected consistently.
2. `for_user_review.md` must document applicability, impact, transition notes, alias rules, and validation evidence for external consumers.
3. `report.py` must not fall back from missing `selected_route` to old `repair_route_selected`; stale artifacts must render a schema-incomplete warning instead.
4. `demo/docs/artifact_consumption_contract.md` must be read and updated where it consumes Iter9 route artifacts or route summaries.
5. The forensic rerun must prove visual delta, overlay, removed/added mine counts, grid equality, and route-state fields all agree.
6. `write_repair_route_artifacts(...)` must validate dataclass-to-decision route-state equality before serialization.
7. `_build_route_result(...)` must be the only `RepairRouteResult` construction path inside `route_late_stage_failure(...)`.
8. Every branch that mutates `grid` or `sr` must write `decision["solver_n_unknown_after"]` and route outcome fields from that same routed state before returning or falling through.
9. All implementation snippets that were previously fragmentary are now represented as complete dictionary fragments or explicit validation snippets.
10. The forensic rerun must produce a new result directory and must not overwrite `results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/`.
11. Forensic acceptance and consistency probes must assert `phase2_full_repair_n_fixed > 0` and `phase2_full_repair_accepted_move_count > 0` (governed by the contract in `docs/ROUTE_STATE_FIELD_INVARIANTS.md`).
12. Nested `repair_route_summary.phase2_fixes` must be retained as an explicit compatibility alias and must equal `phase2_full_repair_accepted_move_count` in acceptance checks.
13. Artifact-validator/schema tests must reject stale ambiguous route-state artifacts, including `selected_route = "needs_sa_or_adaptive_rerun"` without `next_recommended_route` under invoked or non-disambiguated route conditions.
14. Route-phase accepted-count fields must explicitly agree through canonical artifacts: `visual_delta_summary.accepted_move_count == repair_route_decision.phase2_full_repair_accepted_move_count` when Phase 2 is the final applied route.

## Evidence Snapshot

The original run artifacts still show the inconsistency the plan is supposed to resolve:

- `repair_route_decision.json` reports `solver_n_unknown_before = 37285`, `solver_n_unknown_after = 37285`, and `selected_route = "needs_sa_or_adaptive_rerun"`.
- `metrics_iter9_300x538.json` reports final `n_unknown = 31540`, `solver_summary.post_routing.n_unknown = 31540`, `repair_route_selected = "needs_sa_or_adaptive_rerun"`, and `phase2_fixes = 0`.
- `visual_delta_summary.json` contains only `artifact_metadata`.
- `grid_iter9_300x538.npy` and `grid_iter9_latest.npy` are byte-level equivalent NumPy contents for the final routed grid.
- The forensic report requires the corrected partial Phase 2 state to be `selected_route = "phase2_full_repair"`, `route_result = "unresolved_after_repair"`, `route_outcome_detail = "phase2_full_repair_partial_progress_unresolved"`, and `next_recommended_route = "needs_sa_or_adaptive_rerun"`.

## What The Plan Gets Right

The plan correctly identifies the central live-code defect:

- `pipeline.py:82-95` initializes `selected_route` as `needs_sa_or_adaptive_rerun` and initializes `solver_n_unknown_after` from the pre-route solver result.
- `pipeline.py:109-142` can run Phase 2 and assign the improved `routed_grid` and `routed_sr`.
- `pipeline.py:179-188` then returns `RepairRouteResult(selected_route="needs_sa_or_adaptive_rerun")` on unresolved fallback, even when Phase 2 ran and improved the grid.

The plan correctly requires:

- `selected_route = "phase2_full_repair"` immediately when Phase 2 is invoked.
- `solver_n_unknown_after` to be refreshed after the Phase 2 full solve.
- `decision` to be written back immediately after every grid or solver-result mutation.
- `_build_route_result(...)` to synchronize `grid`, `sr`, `decision`, logs, and visual delta summary before any route result can be returned.
- `route_outcome_detail` and `next_recommended_route` to become first-class route-state fields.
- Iter9 metrics, benchmark metrics, benchmark summaries, sweep summaries, report text, and schema docs to stop treating `repair_route_selected` as a complete route-state description.
- `visual_delta_summary.json` to become route-wide and route-state-aware instead of using only the final move log entry or an empty object.

## Findings

### R4-REV-001: Resolved `AGENTS.md` Regression-Only Contract Conflict

Previous severity: Blocker

Resolution status: Resolved by mandatory plan amendment.

Original concern:

The plan requires regression-only output and checks to change from `repair_route_selected` to `selected_route` in `run_benchmark.py:947-1004` and `run_benchmark.py:1035-1055`. That is necessary for the new route-state model, but it conflicted with the current repository instruction that `run_benchmark.py --regression-only` is a fixed-case mode and must preserve stable behavior.

Evidence:

- Current plan Section 7.7: regression-only output must include `route.route_state_fields()` and checks must compare `result["selected_route"]` to the expected route.
- `AGENTS.md:276-277`: regression-only is a fixed-case mode and must preserve stable behavior while rejecting explicit normal-mode flags.

Previous impact:

An implementer following the older plan could either obey the new route-state model or obey the existing benchmark contract, but the older plan did not tell them how to reconcile the two. That created a policy-level ambiguity before implementation began.

Implemented plan correction:

The plan now requires an explicit amendment to the Benchmark Layout Contract in `AGENTS.md`. The amended rule preserves fixed case selection and normal-mode flag rejection while allowing route-state field semantics and regression expected-route comparisons to be updated consistently under the approved route-state contract.

### R4-REV-002: Resolved External-Consumer Transition Documentation Gap

Previous severity: Blocker

Resolution status: Resolved by mandatory plan amendment.

Original concern:

The plan changes broad metrics and summary surfaces, including Iter9 flat metrics, nested route summaries, benchmark rows, benchmark CSV/Markdown, sweep summaries, and report text. The repository instruction requires applicability, impact, and transition notes in `for_user_review.md` when a change may affect external consumers.

Evidence:

- Current plan Sections 6.1 through 6.4: Iter9 render metrics, flat metrics, and nested route summaries change.
- Current plan Sections 7.1 through 7.7: benchmark child metrics, rows, Markdown, CSV, and regression records change.
- Previous plan Section 9: documentation update list omitted `for_user_review.md`.
- `AGENTS.md:319-320`: external-consumer-affecting changes require applicability, impact, and transition notes in `for_user_review.md`.
- `for_user_review.md:1-3`: currently contains only the repo rule text, not the required impact and transition notes.

Previous impact:

The older plan said "No Backward-Compatibility Shim" while still changing public artifact fields. Without a transition document, external consumers would have no authoritative note describing which fields changed, which aliases remain exact aliases, and how to migrate from old artifacts.

Implemented plan correction:

The plan now adds `for_user_review.md` to the required documentation updates. It must document affected artifacts, old-to-new field semantics, alias rules, external impact, migration guidance, and validation evidence.

### R4-REV-003: Resolved Report Text Old-Alias Fallback Violation

Previous severity: Blocker

Resolution status: Resolved by mandatory plan amendment.

Original concern:

The older plan forbade preserving old selected-route semantics, but it also instructed `report.py` to fall back from `selected_route` to `repair_route_selected`. That would have allowed old artifacts with `repair_route_selected = "needs_sa_or_adaptive_rerun"` to be rendered as though `needs_sa_or_adaptive_rerun` were the performed route.

Evidence:

- Source report lines `188-203`: no backward-compatibility shim; `repair_route_selected` may remain only if it exactly matches `selected_route`; `needs_sa_or_adaptive_rerun` belongs only in `next_recommended_route` after a route ran.
- Source report lines `490-494`: plain-English route text must read `selected_route` as the performed route and `next_recommended_route` as the next step.
- Previous plan lines `982-997`: `report.py` would have used `_coalesce(metrics.get("selected_route"), metrics.get("repair_route_selected"), "unknown route")`.
- Previous plan Section 8 / Step 6 text: the implementation step permitted old-alias read tolerance for route text.

Previous impact:

That would have kept the old ambiguity alive in rendered reports. The review target explicitly says no artifact, summary, report, benchmark row, sweep row, fixture, schema prose, or README example should preserve the old ambiguous meaning.

Implemented plan correction:

The plan now requires `report.py` to use `selected_route` only for the performed route. If `selected_route` is absent, the report text must state that the metrics document is pre-route-state-contract or schema-incomplete; it must not silently reinterpret `repair_route_selected` as the performed route. Exact aliases are acceptable only for new writes where `repair_route_selected == selected_route`.

### R4-REV-004: Resolved Demo Artifact-Consumption Documentation Omission

Previous severity: Blocker

Resolution status: Resolved by mandatory plan amendment.

Original concern:

The older plan required a classification search and said no route-field hit may retain old semantics, but its documentation update list omitted demo artifact-consumption docs. The live search surface includes `demo/docs/artifact_consumption_contract.md`, which names `repair_route_decision.json`, `visual_delta_summary.json`, and `repair_route_summary`.

Evidence:

- Previous plan Section 9: documentation update list included root schema docs, README, and `docs/DOCS_INDEX.md`, but not `demo/docs/artifact_consumption_contract.md`.
- Current plan Step 1: classification search must classify every route-field hit and no hit may retain old semantics.
- Live search evidence found `demo/docs/artifact_consumption_contract.md` references to `repair_route_decision.json`, `visual_delta_summary.json`, and `repair_route_summary`.
- `AGENTS.md:34-37`: when demo docs are touched, relevant `demo/docs/` files must be read and kept aligned.

Previous impact:

The demo docs could have remained stale even while the runtime artifact contract changed. That would have violated the plan's own classification-search rule and risked an internal documentation contradiction for any demo consumer of Iter9 metrics or route artifacts.

Implemented plan correction:

The plan now adds `demo/docs/artifact_consumption_contract.md` to the explicit documentation update surface, with the instruction to read relevant `demo/docs/` contracts first and update only the route-artifact consumption semantics affected by the base artifact contract change.

### R4-REV-005: Resolved Visual/Overlay Consistency Acceptance Gap

Previous severity: Blocker

Resolution status: Resolved by mandatory plan amendment.

Original concern:

The original problem includes `visual_delta_summary.json`, final routed grids, and the repair overlay. The older plan created a route-wide visual summary, but its acceptance criteria did not explicitly require `visual_delta_summary.json` to preserve the removed/added mine facts that make the overlay discrepancy visible.

Evidence:

- Source report lines `30-37`: final metrics and overlay show before unknown `37285`, after unknown `31540`, removed mines `192`, added mines `0`.
- Source report lines `607-620`: the final artifact family must preserve that Phase 2 accepted route changes, removed mines, improved solver progress, remained unresolved, and worsened visual MAE slightly.
- Current plan Section 4.2: route-wide visual summary includes `compute_repair_visual_delta(...)`, route state, unknown counts, accepted move count, and `n_fixed`.
- `repair.py:290-312`: `compute_repair_visual_delta(...)` returns `changed_cells`, `removed_mines`, and `added_mines` lists.
- Previous plan Section 11: forensic acceptance criteria omitted checks for removed-mine count, added-mine count, changed-cell count, visual before/after values, and overlay count agreement.

Previous impact:

The implementation could have passed the older plan while still failing to prove that `visual_delta_summary.json`, route metrics, and the overlay were describing the same grid delta. That was below the required coverage for the original five-artifact consistency problem.

Implemented plan correction:

The plan now adds acceptance checks requiring:

- `len(visual_delta_summary.removed_mines) == 192` for the unchanged forensic rerun.
- `len(visual_delta_summary.added_mines) == 0`.
- `visual_delta_summary.changed_cells == 192`.
- `visual_delta_summary.mean_abs_error_before == 0.9614354968070984`.
- `visual_delta_summary.mean_abs_error_after == 0.9689586162567139`.
- `visual_delta_summary.visual_delta == 0.0075231194496154785`.
- `visual_delta_summary.mean_abs_error_before`, `mean_abs_error_after`, and `visual_delta` match route-wide visual quality values for the same before/after grids.
- Overlay removed/added mine counts agree with the route-wide visual delta summary when no later route changes occur.

### R4-REV-006: Resolved Syntax-Level Ambiguities In Code Snippets

Previous severity: Blocker

Resolution status: Resolved by mandatory plan amendment.

Original concern:

Several snippets were written as if they were implementation guidance but were syntactically incomplete.

Evidence:

- Previous plan Section 7.1: `**route.route_state_fields()` appeared in a code block without a comma or surrounding dictionary context.
- Previous plan Section 7.7: regression output snippet contained `**route.route_state_fields()` without closing syntactic context.

Previous impact:

For a plan that is supposed to be decision-complete and unambiguous, those snippets could have caused divergent implementation choices. One implementer might have treated them as pseudocode; another might have pasted or adapted them incorrectly.

Implemented plan correction:

The plan now converts these snippets into valid dictionary examples and explicit validation snippets with surrounding context, commas, and alias assignments where needed.

## Review Conclusion

The plan is implementation-ready after the mandatory amendments now encoded in `docs/industry_standard_implementation_execution_plan_recommendation_4.md`. The prior blocker findings are retained as forensic evidence, but each has a concrete resolution path and no remaining semantic decision is left to the implementer.

## Resolved Blocker List

1. Resolved: the plan now requires an `AGENTS.md` regression-only wording amendment before runtime changes.
2. Resolved: the plan now requires `for_user_review.md` applicability, impact, transition, alias, and validation notes.
3. Resolved: the plan now forbids `report.py` from using `repair_route_selected` as a fallback performed-route value.
4. Resolved: the plan now includes `demo/docs/artifact_consumption_contract.md` in the explicit docs update surface.
5. Resolved: the plan now requires visual delta, overlay, removed/added mine count, changed-cell, and grid equality acceptance checks.
6. Resolved: the plan now requires `_build_route_result(...)` as the single route-result construction and synchronization boundary.
7. Resolved: the plan now requires immediate decision write-back after every route grid/solver-result mutation.
8. Resolved: the plan now replaces syntactically incomplete snippets with complete dictionary or validation examples.
9. Resolved: the plan now requires forensic reruns to create a new result directory and explicitly forbids overwriting the original forensic run directory.
10. Resolved: the plan now requires explicit forensic checks for `phase2_full_repair_n_fixed > 0` and `phase2_full_repair_accepted_move_count > 0`.
11. Resolved: the plan now requires nested `repair_route_summary.phase2_fixes` compatibility-equality checks.
12. Resolved: the plan now requires schema-invalid rejection tests for stale ambiguous route-state artifacts.
13. Resolved: the plan now requires explicit route-phase accepted-count equality through canonical artifact fields.
