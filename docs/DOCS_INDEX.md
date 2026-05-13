# Docs Index

This index defines active versus archived documentation paths for this repository snapshot.

## Active — Repository Governance

- `AGENTS.md` — Agent instruction priority and working guidelines for all AI agents in this repo
- `GEMINI.md` — Project context for Gemini agents: project overview, architecture, and conventions
- `for_user_review.md` — Policy document: when and how to log changes affecting external consumers

## Active — Pipeline / Reconstruction

- `docs/explained_report_artifact_contract.md`
- `docs/back_log.md`
- `docs/ROUTE_STATE_FIELD_INVARIANTS.md`
- `docs/example_commands_image_sweep_mode.md`
- `docs/json_schema/benchmark_summary.schema.md`
- `docs/json_schema/failure_taxonomy.schema.md`
- `docs/json_schema/JSON_OUTPUT_SCHEMA_INDEX.md`
- `docs/json_schema/metrics_iter9.schema.md`
- `docs/json_schema/repair_route_decision.schema.md`
- `docs/json_schema/visual_delta_summary.schema.md`
- `docs/DOCS_INDEX.md`


## Active — Gameworks Package

All gameworks documentation is self-contained under `gameworks/docs/`.
These are the canonical sources of truth for the game — read before modifying gameworks code.

| Document | Purpose |
|---|---|
| `gameworks/docs/INDEX.md` | Navigation index for all gameworks docs |
| `gameworks/docs/README.md` | Overview, installation, launch modes, controls |
| `gameworks/docs/ARCHITECTURE.md` | Module ownership, state machines, data flow |
| `gameworks/docs/API_REFERENCE.md` | Full public API for every class and function |
| `gameworks/docs/GAME_DESIGN.md` | Rules, scoring, streak tiers, board modes |
| `gameworks/docs/DEVELOPER_GUIDE.md` | Dev setup, testing, extension patterns |
| `gameworks/docs/CHANGELOG.md` | Version history |
| `gameworks/docs/DESIGN_PATTERNS.md` | Pipeline alignment audit; R2–R9 improvement recommendations |
| `gameworks/docs/BUGS.md` | All known bugs — flat register with severity, root cause, fix spec per entry |
| `gameworks/docs/PERFORMANCE_PLAN.md` | Performance remediation plan for P-01 through P-18 hot-path optimisations |
| `gameworks/docs/ZOOM_OUT_PERFORMANCE_REPORT.md` | Forensic analysis of 13 zoom-out bottlenecks; informs PERFORMANCE_PLAN Phases 4–8 |
| `gameworks/docs/REMEDIATION_PLAN_VERIFICATION.md` | Pre-execution readiness check; identifies Phase 7B WinAnimation._idx blocker |
| `gameworks/docs/FORENSIC_VISUAL_RECONSTRUCTION_ANALYSIS.md` | 9-gap spec for pixel-perfect image reconstruction on solved boards (unimplemented) |
| `gameworks/docs/TEST_GAP_ANALYSIS.md` | Test gap analysis: health by category, coverage table, and prioritised action plan |
| `gameworks/docs/TEST_HARDENING_PLAN.md` | Forensic test hardening plan — 25-file audit, 17 GWHARDEN hardening items |
| `gameworks/docs/gameplay_visual_improvement_ideas.md` | 9-gap analysis of solved board vs. source image with per-gap code sketches and prioritized implementation roadmap |

## Active — Gameworks Tests

`gameworks/tests/` is the package-local test suite (18 files, scaffolded 2026-05-10).

| Directory | Coverage |
|---|---|
| `gameworks/tests/unit/` | Board, GameEngine, scoring, mine placement, board loading, config (R2 pending) |
| `gameworks/tests/renderer/` | Renderer init, animations, surface cache, event handling |
| `gameworks/tests/architecture/` | AST-based import boundary enforcement |
| `gameworks/tests/cli/` | build_parser, preflight_check (R6 pending) |
| `gameworks/tests/integration/` | Board modes, save/load round-trip (R8 pending) |
| `gameworks/tests/fixtures/` | BoardFactory, EngineFactory shared helpers |

Pending tests (skipped; activate on R2/R3/R9 implementation):
- `gameworks/tests/unit/test_config.py` — R2 GameConfig
- `gameworks/tests/unit/test_board_loading.py` (partial) — R3 BoardLoadResult, R9 schema sidecar
- `gameworks/tests/cli/test_preflight.py` — R6 preflight_check (DP-R6 resolved; test un-skip pending)

Legacy root-level gameworks tests (regression guard):
- `tests/test_gameworks_engine.py`
- `tests/test_gameworks_renderer_headless.py`

## Active — Feature Specs (Pending Implementation)

- `docs/FEATURE_SAVE_RESUME_LOAD.md` — Full design spec and implementation checklist for Save/Resume/Load feature (branch: `feature/save-resume-load`). Supplementary docs required on implementation: `docs/SAVE_FORMAT_SPEC.md`, `docs/SCHEMA_MIGRATION.md`, `docs/SECURITY.md`.

## Archived (moved to `archives/`)

### archives/gameworks/ — Completed implementation specs
- `ARCH_FIX_FA010_DP-R8.md` — FA-010/DP-R8 fix spec (implemented)
- `BUG_REMEDIATION_PLAN.md` — 8-phase remediation for 30 bugs (all resolved)
- `CROSS_VERIFICATION_REPORT.md` — One-time consistency check across 4 performance docs
- `IMPLEMENTATION_TASK_PLAN.md` — Phase 0–8 execution guide (Phases 1–3 done; 4–8 in PERFORMANCE_PLAN)
- `PHASE_0_IMPLEMENTATION_SUMMARY.md` — WinAnimation._idx pre-impl summary (superseded by BACKLOG.md)
- `REMEDIATION_PLAN_VERIFICATION_DETAILED.md` — Detailed phase-by-phase readiness check (summary in REMEDIATION_PLAN_VERIFICATION.md)

### archives/pipeline/ — Completed Recommendation 4 implementation (2026-05-13)

Implemented: four-field route-state model · commit `ef7d5de` · branch `working-changes`
Active contract: `docs/json_schema/repair_route_decision.schema.md` + `AGENTS.md`

- `implementation_prompt_recommendation_4.md` — Primary execution prompt; hardening checklist (all 20 items checked)
- `industry_standard_implementation_execution_plan_recommendation_4.md` — Detailed plan; all code anchor rows resolved
- `industry_standard_implementation_execution_plan_recommendation_4_forensic_audit.md` — Pre-impl traceability audit; all blockers resolved
- `industry_standard_implementation_execution_plan_recommendation_4_forensic_review.md` — Pre-impl plan review; all 14 mandatory corrections applied
- `forensic_analysis_accepted_move_count_field_verification.md` — Accepted-move-count analysis; resolved via `RouteStateInvariantError`

### archives/pipeline/ — Superseded pipeline docs
- `ISSUE-LOG.md` — Superseded by gameworks/docs/BUGS.md; all OPEN items are now RESOLVED
- `M001-M002-analysis.md` — M-001/M-002 deep-dive (both resolved, code in repo)
- `PULL_REQUEST_DESCRIPTION.md` — PR for hardening-amendments-1-4 (not merged to codex/repair_budget_reporting)
- `HARDENING_SUMMARY.md` — Amendments 1–4 to recommendation_4.md (fully incorporated into plan doc)

### archives/llm-audits/ — Completed audit artifacts
- Full audit (34 files) — AUDIT-minestreaker-frontend-game-mockup-20260510: all critical/high findings resolved

### archives/deprecated/ — Dead specs, never-installed tooling
- `full_enterprise_grade_repository_audit_and_remediation_analysis_prompt.md` (×2, root + docs copy)
- `frontend_spec/` (11 files) — React/TypeScript spec for unbuilt web frontend
- `GAME_DESIGN.react.md` — Companion GDD to the React spec
- `PRE_PUSH_HOOK_IMPLEMENTATION.md` / `PRE_PUSH_HOOK_SUMMARY.md` — Hook never installed

### archives/ (pre-existing)
- `docs/archive/codex_late_stage_repair_routing_plan.md`
- `docs/archive/industry_standard_plan_remove_hardcoded_input_source_image.md`
- `docs/implement_clarified_source_image_runtime_contract.md`
- `docs/implement_clarified_source_image_runtime_contract_implementation_checklist.md`

## Review Later

- TODO: Consider consolidating duplicated pure helper functions only if tests stay green and behavior remains schema/path/signature neutral.

## Redirects

- `docs/codex_late_stage_repair_routing_plan.md` -> `docs/archive/codex_late_stage_repair_routing_plan.md`
- `docs/industry_standard_plan_remove_hardcoded_input_source_image.md` -> `docs/archive/industry_standard_plan_remove_hardcoded_input_source_image.md`
- `docs/implement_clarified_source_image_runtime_contract.md` -> `docs/archive/implement_clarified_source_image_runtime_contract.md`
- `docs/implement_clarified_source_image_runtime_contract_implementation_checklist.md` -> `docs/archive/implement_clarified_source_image_runtime_contract_implementation_checklist.md`
- `docs/implementation_prompt_recommendation_4.md` -> `archives/pipeline/implementation_prompt_recommendation_4.md`
- `docs/industry_standard_implementation_execution_plan_recommendation_4.md` -> `archives/pipeline/industry_standard_implementation_execution_plan_recommendation_4.md`
- `docs/industry_standard_implementation_execution_plan_recommendation_4_forensic_audit.md` -> `archives/pipeline/industry_standard_implementation_execution_plan_recommendation_4_forensic_audit.md`
- `docs/industry_standard_implementation_execution_plan_recommendation_4_forensic_review.md` -> `archives/pipeline/industry_standard_implementation_execution_plan_recommendation_4_forensic_review.md`
- `docs/forensic_analysis_accepted_move_count_field_verification.md` -> `archives/pipeline/forensic_analysis_accepted_move_count_field_verification.md`
