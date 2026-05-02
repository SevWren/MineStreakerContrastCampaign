# Iter9 Visual Solver Demo — Acceptance Criteria

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Demo QA/release gate |
| Applies to | Full Iter9 Visual Solver Demo MVP |
| Required before | Implementation signoff, manual demo review, final completion gate |
| Traceability IDs | DEMO-REQ-001 through DEMO-REQ-014 |
| Change rule | Any acceptance criterion change must update `completion_gate.md`, `traceability_matrix.md`, relevant contracts, and tests. |

---

## 1. Purpose

This document defines the exact acceptance criteria for the Iter9 Visual Solver Demo MVP.

The demo is accepted only when source, tests, docs, schemas, and manual GUI behavior satisfy the criteria below.

---

## 2. MVP Acceptance Statement

The MVP is accepted when:

```text
Running the Iter9 demo GUI against a valid completed Iter9 run opens a pygame window, derives board size from the loaded grid, visually replays cell solving/flagging at config-driven speed, updates a status panel with real values, honors configurable finish behavior, and leaves the existing Iter9 pipeline behavior unchanged when demo flags are not used.
```

---

## 3. Required User-Facing Behavior

## 3.1 Launch behavior

The demo MUST be launchable from one or both supported paths:

```text
Standalone demo CLI
Optional run_iter9.py --demo-gui hook
```

If integrated into `run_iter9.py`, the hook MUST be optional and thin.

Existing command behavior MUST remain unchanged when demo flags are omitted.

## 3.2 GUI behavior

The demo MUST:

- open a pygame GUI window.
- display the board visualization.
- display status panel when configured.
- start automatically.
- require no user controls for MVP.
- stop automatically when playback completes.
- honor `stay_open`, `close_immediately`, and `close_after_delay`.
- allow normal OS window close event.
- not auto-close by default.

## 3.3 Board sizing behavior

The demo MUST:

- load board dimensions from `grid.shape`.
- show actual board dimensions in status text.
- avoid hardcoded board height.
- avoid static GUI dimensions.
- size the GUI from board dimensions and config.
- support `300 x derived-height` concept by replacing `derived-height` with the actual height.

## 3.4 Playback behavior

The demo MUST:

- use config-driven playback speed.
- support at least `50+ cells/sec` as a capability target, while displaying the calculated numeric speed rather than the literal text `50+`.
- support dynamic speed scaling as mine count grows.
- avoid hardcoded playback speed in pygame loop.
- apply event batches without dropping or duplicating events.
- visually flag mines over time.
- finish with final board state fully represented.

## 3.5 Status behavior

The demo MUST show real values for:

```text
Source image
Board dimensions
Seed
Total cells
Mines flagged
Safe cells solved
Unknown remaining
Playback speed
Elapsed time
Finish state
```

No placeholder values may appear in the running GUI.

---

## 4. Required Runtime Artifacts

The demo MUST consume a valid completed Iter9 run containing at least:

```text
grid_iter9_latest.npy
metrics_iter9_<board>.json
```

Optional/future:

```text
solver_event_trace.jsonl
```

If `solver_event_trace.jsonl` is absent and fallback is enabled, MVP MUST support final-grid replay.

---

## 5. Required Documentation Acceptance

The following docs MUST exist and be internally consistent:

```text
demo/docs/iter9_visual_solver_demo_execution_plan.md
demo/docs/iter9_visual_solver_demo_implementation_plan.md
demo/docs/traceability_matrix.md
demo/docs/source_modularity_standard.md
demo/docs/testing_methodology.md
demo/docs/architecture_decisions.md
demo/docs/runtime_package_contract.md
demo/docs/artifact_consumption_contract.md
demo/docs/config_contract.md
demo/docs/schema_docs_specs.md
demo/docs/playback_speed_contract.md
demo/docs/finish_behavior_contract.md
demo/docs/window_sizing_contract.md
demo/docs/pygame_rendering_contract.md
demo/docs/status_panel_contract.md
demo/docs/acceptance_criteria.md
demo/docs/completion_gate.md
demo/docs/architecture_boundary_tests.md
```

All demo schema docs MUST live under:

```text
demo/docs/json_schemas/
```

---

## 6. Required Schema Acceptance

The following files MUST exist:

```text
demo/docs/json_schemas/README.md
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md
demo/docs/json_schemas/solver_event_trace.schema.json
demo/docs/json_schemas/solver_event_trace.schema.md
configs/demo/iter9_visual_solver_demo.default.json
```

Required schema checks:

- [ ] Config schema is valid Draft 2020-12.
- [ ] Default config validates against schema.
- [ ] Invalid config examples fail.
- [ ] Event trace row schema is valid Draft 2020-12.
- [ ] Valid event trace rows pass.
- [ ] Invalid event trace rows fail.
- [ ] Unknown fields are rejected unless explicitly allowed by contract.

---

## 7. Required Source Layout Acceptance

Demo runtime code MUST live under:

```text
demos/iter9_visual_solver/
```

Required package areas:

```text
cli/
config/
contracts/
domain/
io/
playback/
rendering/
errors/
```

Forbidden root files:

```text
demo_config.py
demo_visualizer.py
visual_solver_demo.py
iter9_visual_solver_demo.py
```

Existing base project root modules MUST NOT be refactored as part of the demo unless a separate EXPLICIT USER CONFIRMED accepted architecture plan exists.

---

## 8. Required Test Acceptance

The following test package MUST exist:

```text
tests/demo/iter9_visual_solver/
```

Required test categories:

```text
config tests
schema tests
artifact path tests
grid/metrics/trace I/O tests
domain tests
playback policy tests
rendering pure tests
pygame fake tests
CLI/hook tests
architecture boundary tests
source modularity tests
```

Required command:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Acceptance requires:

```text
0 failures
0 errors
no unexpected skips for implemented demo modules
```

Before implementation is complete, scaffold tests may skip missing runtime modules. At completion, skips for implemented required modules are not acceptable unless documented as approved exceptions.

---

## 9. Required Architecture Acceptance

Architecture tests MUST enforce:

- pygame imports are rendering-only.
- Pydantic imports are config-only.
- jsonschema imports are test/schema-helper only.
- domain modules are pure.
- playback modules do not perform file I/O or rendering.
- I/O modules do not render.
- CLI does not draw pixels.
- `run_iter9.py` does not import pygame.
- no root ad hoc demo files exist.
- file-size smoke alarms pass.
- repeated test setup is centralized in fixtures/builders/helpers.

---

## 10. Required Manual Demo Scenario

## 10.1 Scenario identity

Baseline manual scenario:

```text
Source image: assets/line_art_irl_11_v2.png
Board width: 300
Seed: 11
Input artifacts: completed Iter9 run output
```

The actual board height MUST be derived from the loaded grid shape.

## 10.2 Manual execution evidence

Reviewer must record:

```text
date
git commit
command used
config path
run artifact directory
screenshot during playback
screenshot after completion
observed finish behavior
any exceptions/warnings
```

## 10.3 Manual pass criteria

- [ ] GUI opens.
- [ ] Board appears.
- [ ] Status panel appears.
- [ ] Board line shows actual dimensions.
- [ ] Playback starts automatically.
- [ ] Mine flags/visual cells appear progressively.
- [ ] Playback speed is visibly non-static when config changes.
- [ ] Final board visually represents source image.
- [ ] Final state remains open under default `stay_open`.
- [ ] OS close button exits cleanly.
- [ ] No terminal traceback occurs.

---

## 11. Required CLI Smoke Acceptance

Minimum existing CLI smoke commands:

```powershell
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

Optional demo CLI smoke command once implemented:

```powershell
python -m demos.iter9_visual_solver.cli.commands --help
```

If `run_iter9.py` receives demo flags:

```powershell
python run_iter9.py --help
```

must list the demo flags without breaking existing flags.

---

## 12. Required Config Acceptance

Default config MUST satisfy:

- [ ] `window.finish_behavior.mode` default is `stay_open`.
- [ ] playback mode is config-driven.
- [ ] `mine_count_multiplier` exists.
- [ ] `max_events_per_second` exists.
- [ ] `target_fps` exists.
- [ ] `status_panel_width_px` exists.
- [ ] RGB colors are valid arrays of three integers from 0 to 255.
- [ ] invalid config fails before pygame starts.

---

## 13. Performance Acceptance

MVP minimum:

```text
At least 50 cells/sec effective visual playback.
```

Config-driven speed must support higher rates for large boards.

The pygame loop MUST remain responsive to close events during playback.

Performance failures include:

- GUI freezes until final state.
- close event is ignored for multiple seconds.
- playback speed config has no effect.
- event batches drop/duplicate events.
- status panel stops updating.

---

## 14. Non-Goals for MVP

The following are not required for MVP acceptance:

```text
user playback controls
pause/resume button
scrubbing timeline
zoom/pan controls
true solver chronological event trace if not yet instrumented
packaged executable
cross-platform installer
advanced accessibility themes
```

Non-goals MUST NOT be implemented by creating architecture debt in MVP files.

---

## 15. Blocking Failure Conditions

Any of the following blocks acceptance:

- pygame import outside allowed rendering/test paths.
- config validation occurs inside rendering.
- board dimensions do not come from grid shape.
- GUI uses hardcoded board height.
- `derived-height` appears in runtime output.
- playback speed is hardcoded in pygame loop.
- finish behavior ignores config.
- default finish behavior auto-closes.
- tests require real pygame window.
- demo docs or schemas are placed in base project schema folders.
- root `demo_visualizer.py` or `demo_config.py` exists.
- existing Iter9 tests fail because of demo changes.

---

## 16. Acceptance Signoff Template

```text
Acceptance date:
Reviewer:
Git commit:
Demo command:
Config path:
Input run directory:
Board dimensions observed:
Playback speed observed:
Finish behavior observed:
Unit test command result:
CLI smoke command result:
Manual screenshot path during playback:
Manual screenshot path after completion:
Known approved exceptions:
Final decision: accepted / rejected
```

---

## 17. Completion Checklist

- [ ] Required docs exist.
- [ ] Required schemas/config exist.
- [ ] Required runtime package exists.
- [ ] Required test package exists.
- [ ] Full unittest discovery passes.
- [ ] Existing Iter9 CLI smoke commands pass.
- [ ] Demo GUI manual scenario passes.
- [ ] Acceptance signoff template is completed.
