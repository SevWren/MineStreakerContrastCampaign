# Docs Index

This index defines active versus archived documentation paths for this repository snapshot.

## Active — Pipeline / Reconstruction

- `docs/explained_report_artifact_contract.md`
- `docs/back_log.md`
- `docs/ISSUE-LOG.md`
- `docs/ROUTE_STATE_FIELD_INVARIANTS.md`
- `docs/M001-M002-analysis.md`
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
| `gameworks/docs/BUGS.md` | All open bugs — flat register with severity, root cause, fix spec per entry |

## Active — Gameworks Tests

`gameworks/tests/` is the package-local test suite (22 files, scaffolded 2026-05-10).

| Directory | Coverage |
|---|---|
| `gameworks/tests/unit/` | Board, GameEngine, scoring, mine placement, board loading, config (R2 pending) |
| `gameworks/tests/renderer/` | Renderer init, animations, surface cache, event handling |
| `gameworks/tests/architecture/` | AST-based import boundary enforcement |
| `gameworks/tests/cli/` | build_parser, preflight_check (R6 pending) |
| `gameworks/tests/integration/` | Board modes, save/load round-trip (R8 pending) |
| `gameworks/tests/fixtures/` | BoardFactory, EngineFactory shared helpers |

Pending tests (skipped; activate on R2/R3/R6/R8/R9 implementation):
- `gameworks/tests/unit/test_config.py` — R2 GameConfig
- `gameworks/tests/unit/test_board_loading.py` (partial) — R3 BoardLoadResult, R9 schema sidecar
- `gameworks/tests/cli/test_preflight.py` — R6 preflight_check
- `gameworks/tests/integration/test_board_modes.py::test_atomic_save` — R8 atomic save

Legacy root-level gameworks tests (regression guard):
- `tests/test_gameworks_engine.py`
- `tests/test_gameworks_renderer_headless.py`

## Archived
- `docs/archive/codex_late_stage_repair_routing_plan.md`
- `docs/archive/industry_standard_plan_remove_hardcoded_input_source_image.md`
- `docs/implement_clarified_source_image_runtime_contract.md`
- `docs/implement_clarified_source_image_runtime_contract_implementation_checklist.md`
  Note: `docs/archive` exists in `.gitignore`, assume files still exist unless stated otherwise.

## Review Later

- TODO: Consider consolidating duplicated pure helper functions only if tests stay green and behavior remains schema/path/signature neutral.

## Redirects

- `docs/codex_late_stage_repair_routing_plan.md` -> `docs/archive/codex_late_stage_repair_routing_plan.md`
- `docs/industry_standard_plan_remove_hardcoded_input_source_image.md` -> `docs/archive/industry_standard_plan_remove_hardcoded_input_source_image.md`
- `docs/implement_clarified_source_image_runtime_contract.md` -> `docs/archive/implement_clarified_source_image_runtime_contract.md`
- `docs/implement_clarified_source_image_runtime_contract_implementation_checklist.md` -> `docs/archive/implement_clarified_source_image_runtime_contract_implementation_checklist.md`
