# Forensic Audit: Recommendation 4 Traceability And Completeness

Audited plan:

`docs/industry_standard_implementation_execution_plan_recommendation_4.md`

Primary source report:

`results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/forensic_route_decision_recommendations_report.md`

Run artifacts audited:

- `results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/repair_route_decision.json`
- `results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/metrics_iter9_300x538.json`
- `results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/visual_delta_summary.json`
- `results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/grid_iter9_300x538.npy`
- `results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/grid_iter9_latest.npy`
- `results/iter9/20260503T185252Z_line_art_irl_14_300w_seed44_Forensic_Run/repair_overlay_300x538.png`

## Audit Method

This audit compared the implementation plan against:

- the required route-state contract in the forensic report,
- the actual inconsistent run artifacts,
- live route producer code in `pipeline.py`,
- live repair log producers in `repair.py`,
- live Iter9 and benchmark transformer/serializer surfaces,
- live report text consumers,
- live schema docs, README references, demo artifact-consumption docs, tests, and repository instructions.

The audit treats a plan item as complete only if it gives an implementer enough information to change all relevant producers, transformers, consumers, serializers, docs, schemas, and validation gates without making additional semantic decisions.

Implementation-ready status is now achieved for the audited plan when implemented with the mandatory amendments encoded in `docs/industry_standard_implementation_execution_plan_recommendation_4.md`. The previous audit blockers are retained below as traceability evidence, and each one is closed by an explicit source-plan requirement.

## Artifact Baseline

The audited artifacts establish the following baseline:

| Surface | Observed value |
|---|---|
| `repair_route_decision.json.solver_n_unknown_before` | `37285` |
| `repair_route_decision.json.solver_n_unknown_after` | `37285` |
| `repair_route_decision.json.selected_route` | `"needs_sa_or_adaptive_rerun"` |
| `metrics_iter9_300x538.json.n_unknown` | `31540` |
| `metrics_iter9_300x538.json.solver_summary.post_routing.n_unknown` | `31540` |
| `metrics_iter9_300x538.json.repair_route_selected` | `"needs_sa_or_adaptive_rerun"` |
| `metrics_iter9_300x538.json.phase2_fixes` | `0` |
| `visual_delta_summary.json` | only `artifact_metadata` |
| `grid_iter9_300x538.npy` vs `grid_iter9_latest.npy` | equal final grids |

The plan must resolve all of these, not only rename the route field.

## Requirement Traceability

| Requirement from source report | Plan coverage | Audit result |
|---|---|---|
| `selected_route` must mean the invoked route, not the next recommendation. | Sections 1.1, 3.4, 3.5, 11, and 14. | Pass. |
| Partial Phase 2 unresolved state must be explicit. | Sections 3.4, 3.5, and 11. | Pass. |
| `next_recommended_route` must carry `needs_sa_or_adaptive_rerun` for unresolved next work. | Sections 1.1, 3.4, 3.5, and 11. | Pass. |
| Route decision defaults must not initialize `selected_route` as `needs_sa_or_adaptive_rerun`. | Section 3.2. | Pass. |
| Phase 2 invocation state and counts must be explicit. | Sections 3.1, 3.4, 3.5, 6, 7, and 9. | Pass. |
| `RepairRouteResult` and `decision` must not disagree. | Sections 3.1, 3.3, 3.4, 3.5, and 5. | Pass. |
| Every `grid` or `sr` mutation must write back to `decision` before return or fallthrough. | Section 3.2A. | Pass. |
| Route result construction must synchronize `grid`, `sr`, `decision`, logs, and visual summary in one controlled place. | Section 3.1A. | Pass. |
| Serializer must not manufacture route-state primary fields. | Section 5. | Pass. |
| Iter9 metrics and summaries must use the four-field route model. | Sections 6.1 through 6.6. | Pass. |
| Benchmark child metrics and root summaries must use the four-field route model. | Sections 0.1 and 7.1 through 7.7. | Pass with required `AGENTS.md` amendment. |
| `visual_delta_summary.json` must be route-wide and not empty for partial Phase 2 grid changes. | Sections 4, 11, and 14. | Pass. |
| Forensic rerun must create a new results directory and must not overwrite the original forensic run directory. | Section 12 Step 8 forensic rerun guard. | Pass. |
| Forensic acceptance must assert `phase2_full_repair_n_fixed > 0` and `phase2_full_repair_accepted_move_count > 0`. | Sections 11 and 12 Step 8 JSON/grid probe. | Pass. |
| Nested `repair_route_summary.phase2_fixes` must remain an exact alias of `phase2_full_repair_accepted_move_count` during transition. | Sections 6.4, 10, and 12 Step 8 probe. | Pass. |
| Artifact validation must reject stale route-state artifacts as schema-invalid when selected-route semantics are ambiguous. | Sections 2.2 and 10 invariant tests. | Pass. |
| Overlay consistency must include route-phase accepted-count equality through `visual_delta_summary.accepted_move_count` and `repair_route_decision.phase2_full_repair_accepted_move_count`. | Sections 10, 11, and 12 Step 8 probe. | Pass. |
| Plain-English report text must not preserve old route semantics. | Sections 8 and 12 Step 6. | Pass. |
| Docs and schemas must not preserve old `selected_route` semantics. | Sections 9, 12 Step 7, and 13. | Pass. |
| Cross-surface invariants must be tested. | Section 10. | Pass. |
| Forensic rerun must prove corrected values. | Sections 11 and 12 Step 8. | Pass. |

All "Pass" results in the table above for invariant, forensic, and consistency assertions are governed by the contract defined in `docs/ROUTE_STATE_FIELD_INVARIANTS.md`.

## Producer Audit

The plan correctly identifies `pipeline.py::route_late_stage_failure(...)` as the route-state producer and `repair.py` as the repair mutation/log source.

Current producer facts:

- `RepairRouteResult` currently has `selected_route`, `route_result`, `failure_taxonomy`, timeout booleans, logs, `visual_delta_summary`, and `decision`, but no `route_outcome_detail` or `next_recommended_route`.
- The current default decision sets `selected_route = "needs_sa_or_adaptive_rerun"` before any route attempt.
- Phase 2 currently updates `grid` and `sr` on partial unresolved progress but does not update `decision["solver_n_unknown_after"]`, `phase2_log`, or `visual_delta_summary` in the final fallback return.

Plan assessment:

- The plan's producer changes are complete for the identified route-state discrepancy.
- The helper `route_state_fields()` is now specified as an exact canonical dictionary shape, not a descriptive placeholder.
- The plan now requires a strict write-back contract: any branch that assigns a new current `grid` or `sr` must immediately update `decision["solver_n_unknown_after"]`, `route_result`, `route_outcome_detail`, and `next_recommended_route` from the same routed state.
- The plan now requires `_build_route_result(...)` as the single synchronization boundary for `grid`, `sr`, `decision`, route logs, and `visual_delta_summary`.
- The plan now explicitly requires serializer-side dataclass-to-decision equality checks, preventing `route_state_fields()` drift from serialized JSON.

## Transformer Audit

The plan correctly identifies these transformer surfaces:

- Iter9 render metrics.
- Iter9 flat metrics.
- Iter9 nested `repair_route_summary`.
- Iter9 LLM review summary.
- Iter9 image-sweep summaries.
- Benchmark child metrics.
- Benchmark root rows, CSV, Markdown, and compatibility JSON.
- Regression-only benchmark records.
- Plain-English report text.

Plan assessment:

- The plan is comprehensive for root runtime transformers.
- The plan now forbids `report.py` from coalescing old `repair_route_selected` into the performed-route text.
- The plan now pairs benchmark regression changes with an explicit `AGENTS.md` governance amendment.

## Consumer Audit

The plan names these consumer test files:

- `tests/test_repair_route_decision.py`
- `tests/test_route_artifact_metadata.py`
- `tests/test_benchmark_layout.py`
- `tests/test_source_image_cli_contract.py`
- `tests/test_iter9_image_sweep_contract.py`
- `tests/test_report_explanations.py`

Live route-field search also shows stale route semantics in:

- `docs/json_schema/repair_route_decision.schema.md`
- `docs/json_schema/metrics_iter9.schema.md`
- `docs/json_schema/visual_delta_summary.schema.md`
- `docs/json_schema/benchmark_summary.schema.md`
- `docs/json_schema/JSON_OUTPUT_SCHEMA_INDEX.md`
- `README.md`
- `demo/docs/artifact_consumption_contract.md`
- `for_user_review.md`

Plan assessment:

- The plan requires a classification search and says every hit must be classified.
- The explicit update list now includes both `demo/docs/artifact_consumption_contract.md` and `for_user_review.md`, eliminating the audit-significant omissions.

## Serializer Audit

The plan correctly identifies:

- `pipeline.py::write_repair_route_artifacts(...)` for route artifacts.
- `run_iter9.py::_atomic_save_json(...)` for Iter9 metrics.
- Iter9 image-sweep JSON/CSV/Markdown writers.
- Normal benchmark child metrics.
- Normal benchmark root JSON/CSV/Markdown and `benchmark_results.json`.
- Regression-only outputs.
- Report overlay renderers.

Plan assessment:

- The serializer rule forbidding primary-field `setdefault(...)` is correct.
- The serializer guard now validates agreement between `RepairRouteResult.route_state_fields()` and `RepairRouteResult.decision` before writing, not only field presence.

## Docs And Schema Audit

Root schema coverage in the plan is strong:

- `repair_route_decision.schema.md`
- `metrics_iter9.schema.md`
- `visual_delta_summary.schema.md`
- `benchmark_summary.schema.md`
- `JSON_OUTPUT_SCHEMA_INDEX.md`
- `README.md`
- `DOCS_INDEX.md`

All required documentation surfaces are now covered:

- `for_user_review.md`, required by `AGENTS.md` for external-consumer-impacting metrics changes.
- `demo/docs/artifact_consumption_contract.md`, found by live route-artifact search and relevant to route artifact consumption.

The schema section now explicitly requires stale enum/prose that permits `needs_sa_or_adaptive_rerun` as a selected route to be removed or rewritten. Live schema evidence showed this stale meaning in `docs/json_schema/repair_route_decision.schema.md` and `docs/json_schema/metrics_iter9.schema.md`; the source plan now requires that value to move to `next_recommended_route` and forbids retaining it as a valid performed-route value.

## Visual Delta And Overlay Audit

The plan correctly switches from last-move visual summaries to route-wide summaries using `compute_repair_visual_delta(...)`.

However, the original discrepancy involved:

- `visual_delta_summary.json` being effectively empty.
- overlay before/after unknown counts showing `37285 -> 31540`.
- overlay removed/added counts showing `-192 / +0`.
- final metrics visual quality showing visual MAE worsened despite solver progress.

The plan's acceptance criteria now force those facts to agree across `visual_delta_summary.json`, metrics, grids, and overlays. `compute_repair_visual_delta(...)` returns `removed_mines`, `added_mines`, and `changed_cells`, and the plan now requires tests or forensic acceptance checks for those fields.

Plan requirement now present:

The forensic acceptance criteria must assert route-wide visual summary and overlay agreement:

- `visual_delta_summary.summary_scope == "route_phase"`.
- `visual_delta_summary.route_phase == "phase2_full_repair"`.
- `visual_delta_summary.solver_n_unknown_before == 37285`.
- `visual_delta_summary.solver_n_unknown_after == 31540`.
- `visual_delta_summary.mean_abs_error_before == 0.9614354968070984`.
- `visual_delta_summary.mean_abs_error_after == 0.9689586162567139`.
- `visual_delta_summary.visual_delta == 0.0075231194496154785`.
- `len(visual_delta_summary.removed_mines) == 192`.
- `len(visual_delta_summary.added_mines) == 0`.
- `visual_delta_summary.changed_cells == 192`.
- overlay removed/added count agrees with the visual summary when no later route changes occur.

## Validation Audit

The plan includes targeted and full validation:

- route decision tests,
- route artifact metadata tests,
- benchmark layout tests,
- source-image CLI contract tests,
- image sweep tests,
- report explanation tests,
- full unittest discovery,
- CLI help checks,
- image guard check,
- forensic rerun.

Required validation now includes:

- explicit `AGENTS.md` contract update verification,
- PowerShell-native documentation/governance verification syntax,
- producer invariant tests for stale `decision["solver_n_unknown_after"]`,
- producer invariant tests for invalid `selected_route == "needs_sa_or_adaptive_rerun"`,
- producer invariant tests for Phase 2 invoked without Last100 and non-Phase2 selected route,
- `for_user_review.md` content verification,
- demo artifact-consumption doc verification,
- visual summary and overlay removed/added count agreement,
- explicit `phase2_full_repair_n_fixed > 0` and `phase2_full_repair_accepted_move_count > 0` forensic assertions,
- explicit `repair_route_summary.phase2_fixes == phase2_full_repair_accepted_move_count` equality checks,
- explicit `visual_delta_summary.accepted_move_count == phase2_full_repair_accepted_move_count` equality checks,
- explicit non-overwrite forensic rerun directory/timestamp guard,
- explicit schema-invalid rejection tests for stale `selected_route = needs_sa_or_adaptive_rerun` artifacts,
- explicit route-phase accepted-count equality via `visual_delta_summary.accepted_move_count == phase2_full_repair_accepted_move_count`,
- dataclass-to-decision route-state equality before serialization,
- syntax validation of code snippets if the plan is meant to be copy-implementable.

## Completeness Determination

The plan is now implementation-ready. It resolves the main route-state semantic bug and the full forensic discrepancy, including governance, external-consumer transition notes, demo artifact docs, report text semantics, serializer equality, visual/overlay agreement, grid equality, and validation requirements.

## Resolved Blocker List

1. Resolved: the plan now reconciles regression-only route-state changes with `AGENTS.md` through a required governance amendment.
2. Resolved: the plan now requires `for_user_review.md` consumer-impact and transition notes.
3. Resolved: the plan now forbids old-alias performed-route fallback in `report.py`.
4. Resolved: the plan now includes `demo/docs/artifact_consumption_contract.md` in the docs update surface.
5. Resolved: the plan now requires visual delta, overlay, removed/added mine count, changed-cell, and grid equality checks.
6. Resolved: the plan now requires serializer dataclass-to-decision route-state equality checks.
7. Resolved: the plan now requires `_build_route_result(...)` as the controlled route-result construction boundary.
8. Resolved: the plan now requires immediate write-back from every mutated `grid`/`sr` state into `decision`.
9. Resolved: the plan now corrects syntactically incomplete snippets into complete dictionary or validation examples.
10. Resolved: the plan now requires forensic reruns to use a new output directory and explicitly forbids overwriting the original forensic run directory.
11. Resolved: the plan now requires explicit forensic checks for `phase2_full_repair_n_fixed > 0` and `phase2_full_repair_accepted_move_count > 0`.
12. Resolved: the plan now encodes and validates the nested `repair_route_summary.phase2_fixes` compatibility-equality path.
13. Resolved: the plan now requires schema-invalid rejection tests for stale ambiguous route-state artifacts.
14. Resolved: the plan now requires route-phase accepted-count equality through canonical artifact fields.
