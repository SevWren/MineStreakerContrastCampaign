# Iter9 Visual Solver Demo — Traceability Matrix

## Purpose
Maps requirements to contracts, modules, tests, fixtures/builders/helpers, and completion evidence so LLM-driven development cannot implement untracked behavior.

## ID formats
- Requirement: `DEMO-REQ-###`
- Contract: `DEMO-CONTRACT-###`
- Test: `DEMO-TEST-###`

## Matrix
| Requirement ID | Requirement | Contract | Runtime owner | Required tests | Test support | Completion evidence |
|---|---|---|---|---|---|---|
| DEMO-REQ-001 | GUI uses actual `grid.shape`, not static width/height | `window_sizing_contract.md` | `domain/board_dimensions.py`, `rendering/window_geometry.py` | `test_board_dimensions.py`, `test_window_geometry.py` | `GridBuilder`, `fixtures/grids.py` | status shows `Board: W x H` |
| DEMO-REQ-002 | Playback speed is config-driven and mine-count scaled | `playback_speed_contract.md`, `config_contract.md` | `playback/speed_policy.py`, `playback/event_batching.py`, `playback/event_scheduler.py`, `playback/replay_state.py`, `cli/commands.py`, `rendering/status_text.py` | `test_speed_policy.py`, `test_event_batching.py`, `test_event_scheduler.py`, `test_replay_state.py`, `test_status_text.py`, `test_cli_commands.py` | `DemoConfigBuilder` | min/base/multiplier/max, batching, scheduler, replay counters, status text, and CLI wiring tests pass |
| DEMO-REQ-003 | Playback speed is not hardcoded in pygame loop | `source_modularity_standard.md`, `playback_speed_contract.md` | `playback/speed_policy.py`, `rendering/pygame_loop.py` | `test_pygame_loop_with_fakes.py`, `test_architecture_boundaries.py` | `import_boundary_assertions.py` | no pygame-loop speed formula ownership |
| DEMO-REQ-003A | GUI layout is responsive, resize-aware, centerable, and scales board regions from the live surface | `window_sizing_contract.md`, `pygame_rendering_contract.md`, `config_contract.md` | `rendering/window_geometry.py`, `rendering/pygame_adapter.py`, `rendering/pygame_loop.py`, `rendering/board_surface.py` | `test_window_geometry.py`, `test_pygame_adapter_contract.py`, `test_pygame_loop_with_fakes.py`, `test_board_surface.py`, `test_config_models.py` | `pygame_fakes.py` | resize, maximize, scaled-board, display bounds, and center placement tests pass |
| DEMO-REQ-003B | Polished status panel uses dynamic width, structured metric rows, and an aspect-fit bottom-right source preview slot | `status_panel_contract.md`, `pygame_rendering_contract.md`, `window_sizing_contract.md` | `rendering/status_view_model.py`, `rendering/status_panel.py`, `rendering/window_geometry.py`, `cli/commands.py` | `test_status_view_model.py`, `test_status_panel.py`, `test_window_geometry.py`, `test_window_chrome.py`, `test_cli_commands.py` | `StatusSnapshotBuilder`, `pygame_fakes.py` | placeholder preview, aspect-fit geometry, wide-row rendering, and chrome tests pass |
| DEMO-REQ-004 | Finish behavior is configurable | `finish_behavior_contract.md` | `playback/finish_policy.py` | `test_finish_policy.py` | `DemoConfigBuilder` | all finish modes tested |
| DEMO-REQ-005 | Default finish behavior is `stay_open` | `finish_behavior_contract.md` | `config/models.py` | `test_config_models.py` | `fixtures/configs.py` | default config validates |
| DEMO-REQ-006 | MVP replays from final grid artifacts | `artifact_consumption_contract.md` | `io/grid_loader.py`, `playback/event_source.py` | `test_grid_loader.py`, `test_event_source.py` | `temp_runs.py`, `GridBuilder` | final-grid events produced |
| DEMO-REQ-007 | Solver trace replay is future-compatible | `artifact_consumption_contract.md`, `schema_docs_specs.md`, `json_schemas/solver_event_trace.schema.md` | `domain/playback_event.py`, `io/event_trace_loader.py` | `test_event_trace_loader.py` | `EventTraceBuilder` | trace rows normalize to events |
| DEMO-REQ-008 | Config schema/spec docs live under `demo/docs/json_schemas/` | `schema_docs_specs.md` | docs only | `test_config_schema_contract.py` | `schema_assertions.py` | schema files found/validated |
| DEMO-REQ-009 | Runtime code lives under `demos/iter9_visual_solver/` | `runtime_package_contract.md` | package layout | `test_architecture_boundaries.py` | `filesystem_assertions.py` | no root demo files |
| DEMO-REQ-010 | pygame is isolated to rendering | `pygame_rendering_contract.md` | `rendering/` | `test_architecture_boundaries.py` | `import_boundary_assertions.py` | import test passes |
| DEMO-REQ-011 | Pydantic is isolated to config | `config_contract.md` | `config/` | `test_architecture_boundaries.py` | `import_boundary_assertions.py` | import test passes |
| DEMO-REQ-012 | Tests use fixtures/builders/helpers | `testing_methodology.md` | tests | `test_source_file_modularity.py` | all test support dirs | no large duplicate setup |
| DEMO-REQ-013 | `run_iter9.py` hook is thin and optional | `runtime_package_contract.md`, `acceptance_criteria.md` | `run_iter9.py`, `cli/launch_from_iter9.py` | `test_run_iter9_launch_hook.py` | CLI fakes | existing behavior unchanged |
| DEMO-REQ-014 | Prompted wrapper launches from a completed results directory with speed and finish prompts | `runtime_package_contract.md`, `artifact_consumption_contract.md`, `config_contract.md` | `cli/prompted_launcher.py`, `demo/run_iter9_visual_solver_demo_prompted.ps1` | `test_prompted_launcher.py` | `TempIter9Run`, `DemoConfigBuilder` | wrapper delegates with resolved artifacts and generated config |
| DEMO-REQ-015 | Large-board playback avoids per-cell object materialization and full-board redraws | `playback_speed_contract.md`, `artifact_consumption_contract.md`, `pygame_rendering_contract.md`, `runtime_package_contract.md`, `architecture_decisions.md` | `playback/event_source.py`, `io/event_trace_loader.py`, `playback/event_scheduler.py`, `domain/board_state.py`, `playback/replay_state.py`, `rendering/board_surface.py`, `rendering/pygame_loop.py`, `rendering/status_view_model.py` | `test_event_source.py`, `test_event_trace_loader.py`, `test_event_scheduler.py`, `test_replay_state.py`, `test_board_surface.py`, `test_pygame_loop_with_fakes.py`, `test_status_view_model.py`, `test_architecture_boundaries.py` | `GridBuilder`, `EventTraceBuilder`, `pygame_fakes.py`, `StatusSnapshotBuilder` | typed/lazy event-store, streaming trace, dirty-surface, resize-reuse, and counter snapshot tests pass |

## Review checklist
- [ ] Every requirement has a contract.
- [ ] Every requirement has an owner module.
- [ ] Every requirement has tests.
- [ ] Every test maps back to a requirement.
- [ ] Every source module maps to a requirement.
- [ ] Every JSON field maps to a runtime owner.
- [ ] Every completion-gate item maps to a requirement.
