# Iter9 Visual Solver Demo Plan

## Current Status

This document is the corrected consolidated plan for the Iter9 Visual Solver Demo.

The major correction in this version is sequencing:

```text
Do not create executable contract code before the human contracts exist.
```

The correct order is:

```text
contract discovery
→ human contract documents
→ contract review and traceability
→ schema documentation/specification
→ test infrastructure and architecture gates
→ executable contract constants and implementation code
```

This plan assumes LLM AI-driven development, so the first priority is to create guardrails that stop the LLM from inventing architecture, mixing responsibilities, or creating large source/test files.

---

# 1. Demo Purpose

The demo visually presents an Iter9 result as a solver-style playback.

The user runs an Iter9 command for a source image, board width, and seed. After the Iter9 pipeline completes, a pygame GUI opens and animates the board so it looks like the computer is placing flags and solving cells at high speed.

The final screen should show a completed flag pattern that visually represents the source image.

Example status panel content:

```text
Source image: line_art_irl_11_v2.png
Board: 300 x 942
Seed: 11
Total cells: <board_w * board_h>
Mines flagged: 0 / <total_mines>
Safe cells solved: 0 / <safe_cells>
Unknown remaining: <n_unknown>
Playback speed: <calculated_events_per_second> cells/sec
```

---

# 2. Locked Product Decisions

## 2.1 GUI library

Chosen:

```text
pygame
numpy
```

Reason: the demo is a fast 2D pixel/surface animation, not a form-heavy desktop application. The board is a NumPy grid, and pygame is appropriate for fast pixel animation.

## 2.2 Config and schema tools

Chosen:

```text
pydantic v2
jsonschema
```

Use Pydantic v2 for runtime config models, defaults, type validation, range validation, clear validation errors, and schema generation support.

Use jsonschema for tests that validate default config against committed schema, bad configs fail, and schema files are valid JSON Schema documents.

## 2.3 Dynamic board size

Incorrect display:

```text
Board: 300 x derived-height
```

Correct display:

```text
Board: 300 x 942
```

Implementation anchor:

```python
board_h, board_w = grid.shape
```

The GUI window size must be derived from the actual grid dimensions, not from hardcoded width/height assumptions.

## 2.4 Config-driven playback speed

Incorrect display:

```text
Playback speed: 50+ cells/sec
```

Correct display:

```text
Playback speed: <calculated_events_per_second> cells/sec
```

Recommended formula:

```text
calculated_events_per_second =
  base_events_per_second
  + total_mines * mine_count_multiplier
```

Then clamp:

```text
events_per_second =
  min(max_events_per_second,
      max(min_events_per_second, calculated_events_per_second))
```

This allows playback to scale as board/mine count grows.

## 2.5 Configurable finish behavior

Correct MVP behavior:

```text
No required user controls for MVP.
The demo starts automatically.
When playback finishes, the window behavior is controlled by config.
```

Valid finish modes:

```text
stay_open
close_immediately
close_after_delay
```

Default:

```text
stay_open
```

---

# 3. Non-Negotiable Architecture Rule

Do **not** create short-term root files like:

```text
demo_config.py
demo_visualizer.py
```

Do **not** “split later.”

The demo must be implemented as a durable, modular runtime package from day one.

---

# 4. Correct First-Step Rule

## 4.1 Human contracts come before code contracts

Do **not** create these first:

```text
demos/iter9_visual_solver/contracts/artifact_names.py
demos/iter9_visual_solver/contracts/schema_versions.py
demos/iter9_visual_solver/contracts/defaults.py
```

Those files are executable mirrors of decisions. They cannot be responsibly written before the contract documents exist.

Correct rule:

```text
Contract documentation comes before contract code.
Contract code is the executable mirror of already-written contracts.
```

## 4.2 Two meanings of “contract”

Human contracts come first:

```text
Markdown contracts
requirements
acceptance criteria
schema documentation
testing methodology
source modularity standard
traceability matrix
```

Code contracts come later:

```text
artifact_names.py
schema_versions.py
defaults.py
Pydantic models
JSON Schema files
architecture tests
```

---

# 5. Correct LLM-Driven Phase Sequence

## Phase -2: Contract Discovery

Status: completed by the dedicated demo contract set under `demo/docs/`.

Purpose: surface unknowns before source code exists. The accepted demo docs
now answer:

```text
1. What existing Iter9 artifacts does the demo read?
2. Which artifacts are required for MVP?
3. Which artifacts are optional?
4. What does the demo display?
5. What is the exact playback-speed formula?
6. What does “finish” mean?
7. What happens when config is invalid?
8. What happens when grid and metrics disagree?
9. What behavior is forbidden?
10. What source-code folders own which responsibilities?
11. What tests must exist before implementation begins?
12. Which decisions are still unresolved?
```

No pygame code. No runtime package code. No contract constants code belong in
the discovery phase.

## Phase -1: Human Contract Authoring

Only after discovery, write the actual contract docs. In the current dedicated
demo documentation package, those docs are:

```text
demo/docs/iter9_visual_solver_demo_execution_plan.md
demo/docs/iter9_visual_solver_demo_implementation_plan.md
demo/docs/runtime_package_contract.md
demo/docs/artifact_consumption_contract.md
demo/docs/config_contract.md
demo/docs/playback_speed_contract.md
demo/docs/window_sizing_contract.md
demo/docs/finish_behavior_contract.md
demo/docs/pygame_rendering_contract.md
demo/docs/status_panel_contract.md
demo/docs/testing_methodology.md
demo/docs/source_modularity_standard.md
demo/docs/acceptance_criteria.md
demo/docs/completion_gate.md
demo/docs/traceability_matrix.md
demo/docs/architecture_boundary_tests.md
demo/docs/architecture_decisions.md
demo/docs/schema_docs_specs.md
```

At this stage, the contracts are still written in English/Markdown. No executable constants yet.

## Phase 0: Contract Review and Traceability

Before coding, review the docs for contradictions.

Example checks:

```text
Does config_contract.md define a field that schema docs do not mention?
Does playback_speed_contract.md depend on a config field that does not exist?
Does window_sizing_contract.md define screen behavior clearly?
Does artifact_consumption_contract.md name the exact files the demo reads?
Does testing_methodology.md define fixtures/builders/helpers before tests are written?
Does traceability_matrix.md map each requirement to planned source modules and tests?
```

This is a hard pause in LLM-driven development.

## Phase 1: JSON Schema Specs and Schema Documentation

Create schema files and painstaking schema docs in the demo docs area:

```text
demo/docs/json_schemas/README.md
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md
demo/docs/json_schemas/solver_event_trace.schema.json
demo/docs/json_schemas/solver_event_trace.schema.md
```

The Markdown schema docs must include for every field:

```text
field name
field type
required or optional
default value
valid range or allowed enum
runtime effect
owning runtime module
example valid value
example invalid value
validation failure expectation
migration/versioning note when applicable
```

## Phase 2: Test Infrastructure and Architecture Gates

Create shared test support before production implementation:

```text
tests/demo/iter9_visual_solver/
  fixtures/
    __init__.py
    configs.py
    grids.py
    metrics.py
    event_traces.py
    temp_runs.py
    pygame_fakes.py

  builders/
    __init__.py
    config_builder.py
    grid_builder.py
    metrics_builder.py
    event_trace_builder.py
    status_snapshot_builder.py

  helpers/
    __init__.py
    assertions.py
    schema_assertions.py
    filesystem_assertions.py
    import_boundary_assertions.py
    pygame_assertions.py
```

Then create architecture gate tests:

```text
tests/demo/iter9_visual_solver/test_architecture_boundaries.py
tests/demo/iter9_visual_solver/test_source_file_modularity.py
```

Reason: for AI-driven development, architecture tests and shared test support prevent the LLM from producing blobs, duplicated setup, and layer violations.

## Phase 3: Executable Contract Constants and Config Models

Only now create executable contract code:

```text
demos/iter9_visual_solver/contracts/
  __init__.py
  artifact_names.py
  schema_versions.py
  defaults.py
```

These files must directly mirror the already-approved Markdown contracts.

Then create config code:

```text
demos/iter9_visual_solver/config/
  __init__.py
  models.py
  loader.py
  schema_export.py
  validation_errors.py
```

Tests:

```text
tests/demo/iter9_visual_solver/test_config_models.py
tests/demo/iter9_visual_solver/test_config_loader.py
tests/demo/iter9_visual_solver/test_config_schema_contract.py
```

## Phase 4: Domain and I/O Foundation

Create domain modules:

```text
demos/iter9_visual_solver/domain/
  __init__.py
  board_dimensions.py
  board_state.py
  playback_event.py
  demo_input.py
  status_snapshot.py
```

Create I/O modules:

```text
demos/iter9_visual_solver/io/
  __init__.py
  artifact_paths.py
  grid_loader.py
  metrics_loader.py
  event_trace_loader.py
  event_trace_writer.py
  json_reader.py
```

## Phase 5: Playback Logic

Create playback modules:

```text
demos/iter9_visual_solver/playback/
  __init__.py
  speed_policy.py
  event_source.py
  event_batching.py
  event_scheduler.py
  replay_state.py
  finish_policy.py
```

Playback speed, batching, finish behavior, and replay state must work without pygame.

## Phase 6: Rendering Helpers Before pygame Loop

Create rendering-helper modules:

```text
demos/iter9_visual_solver/rendering/
  __init__.py
  color_palette.py
  window_geometry.py
  board_surface.py
  status_text.py
  status_panel.py
```

These are rendering-adjacent but mostly testable without a real pygame window.

## Phase 7: pygame Adapter and Loop

Create pygame-specific modules:

```text
demos/iter9_visual_solver/rendering/pygame_adapter.py
demos/iter9_visual_solver/rendering/pygame_loop.py
```

This is the first place pygame should appear. By this point, config, loading, playback, window sizing, and status text are already tested.

## Phase 8: CLI

Create CLI modules:

```text
demos/iter9_visual_solver/cli/
  __init__.py
  args.py
  commands.py
  launch_from_iter9.py
```

CLI should orchestrate already-tested modules. It should not contain business logic.

## Phase 9: Thin `run_iter9.py` Hook

Modify last:

```text
run_iter9.py
```

Add only:

```text
--demo-gui
--demo-config
```

and call:

```text
demos.iter9_visual_solver.cli.launch_from_iter9
```

The existing pipeline should be touched only after the standalone demo runner works.

---

# 6. Runtime Package Layout

Correct long-term runtime structure:

```text
demos/
  __init__.py

  iter9_visual_solver/
    __init__.py

    cli/
      __init__.py
      args.py
      commands.py
      launch_from_iter9.py

    config/
      __init__.py
      models.py
      loader.py
      schema_export.py
      validation_errors.py

    contracts/
      __init__.py
      artifact_names.py
      schema_versions.py
      defaults.py

    domain/
      __init__.py
      board_dimensions.py
      board_state.py
      playback_event.py
      demo_input.py
      status_snapshot.py

    io/
      __init__.py
      artifact_paths.py
      grid_loader.py
      metrics_loader.py
      event_trace_loader.py
      event_trace_writer.py
      json_reader.py

    playback/
      __init__.py
      speed_policy.py
      event_source.py
      event_batching.py
      event_scheduler.py
      replay_state.py
      finish_policy.py

    rendering/
      __init__.py
      color_palette.py
      window_geometry.py
      board_surface.py
      status_text.py
      status_panel.py
      pygame_adapter.py
      pygame_loop.py

    errors/
      __init__.py
      config_errors.py
      artifact_errors.py
      trace_errors.py
      rendering_errors.py
```

---

# 7. Runtime Package Ownership Boundaries

| Package area | Owns | Must not own |
|---|---|---|
| `cli/` | command arguments and launch orchestration | pygame drawing, schema internals, pixel loops |
| `config/` | Pydantic models, config loading, validation, schema export | board replay logic, pygame rendering |
| `contracts/` | artifact names, schema versions, defaults/constants | runtime behavior |
| `domain/` | plain data models and pure domain objects | file I/O, pygame, pydantic |
| `io/` | loading grids, metrics, event traces, JSON reading/writing | playback math, pygame |
| `playback/` | speed policy, event batching, replay state, finish behavior | pygame drawing, file parsing |
| `rendering/` | pygame surfaces, window geometry, board/status drawing | config parsing, schema validation |
| `errors/` | typed error classes/messages | business logic |

---

# 8. Correct Documentation Layout

All demo documentation belongs under:

```text
demo/docs/
```

All demo JSON Schema specifications and detailed Markdown schema documentation belong under:

```text
demo/docs/json_schemas/
```

Correct documentation layout:

```text
demo/
  iter9_visual_solver_demo_plan.md
  docs/
    iter9_visual_solver_demo_execution_plan.md
    iter9_visual_solver_demo_implementation_plan.md
    architecture_decisions.md
    acceptance_criteria.md
    runtime_package_contract.md
    artifact_consumption_contract.md
    pygame_rendering_contract.md
    config_contract.md
    playback_speed_contract.md
    window_sizing_contract.md
    finish_behavior_contract.md
    status_panel_contract.md
    testing_methodology.md
    source_modularity_standard.md
    traceability_matrix.md
    completion_gate.md
    architecture_boundary_tests.md
    schema_docs_specs.md
    json_schemas/
      README.md
      iter9_visual_solver_demo_config.schema.json
      iter9_visual_solver_demo_config.schema.md
      solver_event_trace.schema.json
      solver_event_trace.schema.md
```

Do not place demo schema docs in:

```text
docs/json_schema/
schemas/
```

Do not mix base project documentation and demo documentation in the same folder.

---

# 9. Config File Location

Correct location:

```text
configs/
  demo/
    iter9_visual_solver_demo.default.json
```

Incorrect:

```text
configs/iter9_visual_solver_demo.default.json
```

---

# 10. Default Config Draft

```json
{
  "schema_version": "iter9_visual_solver_demo_config.v1",
  "window": {
    "title": "Mine-Streaker Iter9 Visual Solver Demo",
    "resizable": false,
    "max_screen_fraction": 0.92,
    "status_panel_width_px": 360,
    "minimum_board_cell_px": 1,
    "preferred_board_cell_px": 2,
    "fit_to_screen": true,
    "center_window": true,
    "finish_behavior": {
      "mode": "stay_open",
      "close_after_seconds": null
    }
  },
  "playback": {
    "mode": "mine_count_scaled",
    "min_events_per_second": 50,
    "base_events_per_second": 1000,
    "mine_count_multiplier": 0.08,
    "max_events_per_second": 12000,
    "target_fps": 60,
    "batch_events_per_frame": true
  },
  "visuals": {
    "unseen_cell_rgb": [18, 18, 18],
    "flagged_mine_rgb": [255, 80, 40],
    "safe_cell_rgb": [95, 95, 95],
    "unknown_cell_rgb": [60, 100, 230],
    "background_rgb": [10, 10, 10],
    "show_safe_cells": false,
    "show_unknown_cells": true
  },
  "status_panel": {
    "show_source_image": true,
    "show_board_dimensions": true,
    "show_seed": true,
    "show_total_cells": true,
    "show_mines_flagged": true,
    "show_safe_cells_solved": true,
    "show_unknown_remaining": true,
    "show_playback_speed": true,
    "show_elapsed_time": true,
    "show_finish_message": true
  },
  "input": {
    "prefer_solver_event_trace": true,
    "allow_final_grid_replay_fallback": true
  }
}
```

---

# 11. MVP Behavior

MVP may replay from final grid artifacts:

```text
grid_iter9_latest.npy
metrics_iter9_<board>.json
```

MVP builds replay events from final grid mine positions:

```text
MINE flag event for each final mine cell
```

Version 2 adds actual solver event trace support:

```text
solver_event_trace.jsonl
```

---

# 12. Solver Event Trace Contract

Future trace artifact:

```text
solver_event_trace.jsonl
```

Each line should be one JSON object.

Example:

```json
{"step": 1, "round": 0, "y": 42, "x": 118, "state": "MINE", "display": "flag"}
{"step": 2, "round": 0, "y": 42, "x": 119, "state": "SAFE", "display": "reveal"}
```

Required conceptual fields:

```text
step
round
y
x
state
display
```

Valid states:

```text
SAFE
MINE
UNKNOWN
```

Valid displays:

```text
flag
reveal
unknown
```

The complete schema belongs in:

```text
demo/docs/json_schemas/solver_event_trace.schema.json
```

The complete schema documentation belongs in:

```text
demo/docs/json_schemas/solver_event_trace.schema.md
```

---

# 13. Design Methods That Produce Smaller Files

This section replaces vague “keep files small” language with concrete methods that create smaller files as a side effect.

The goal is not merely to keep files under a numeric limit. The goal is to create structural pressure that prevents large files from forming.

## 13.1 Change-axis decomposition

Split files by reason they would change.

A file is wrong when two unrelated future changes would modify it.

Bad file:

```text
pygame_renderer.py
```

If this file owns:

```text
window size
colors
status text
event playback
pygame draw calls
finish behavior
```

then it has too many change axes.

Correct split:

```text
rendering/window_geometry.py      changes when screen sizing rules change
rendering/color_palette.py        changes when colors/theme change
rendering/status_layout.py        changes when panel text/layout changes
rendering/board_surface.py        changes when board pixel drawing changes
rendering/pygame_loop.py          changes when pygame event-loop behavior changes
playback/finish_policy.py         changes when close/stay-open rules change
```

## 13.2 One-abstraction-level-per-file

A source file must operate at one conceptual level only.

Allowed levels:

```text
Level 1: CLI orchestration
Level 2: use-case orchestration
Level 3: domain policy / calculation
Level 4: I/O adapter
Level 5: rendering adapter
Level 6: data model / contract
```

A file cannot mix levels.

## 13.3 Functional-core / imperative-shell split

Put pure logic in small testable functions. Keep side effects at the edge.

Functional-core files:

```text
playback/speed_policy.py
playback/event_batching.py
rendering/window_geometry.py
rendering/status_text.py
domain/board_dimensions.py
```

Imperative-shell files:

```text
io/grid_loader.py
io/metrics_loader.py
rendering/pygame_loop.py
cli/commands.py
```

## 13.4 Policy object extraction

Any configurable rule becomes a policy module, not inline logic.

Policies in this demo:

```text
playback speed policy
finish behavior policy
window sizing policy
event ordering policy
fallback input policy
status visibility policy
color palette policy
```

Each policy gets one model/config input, one calculation module, and one test file.

## 13.5 Port-adapter boundaries

Separate what the demo needs from how pygame provides it.

Pygame adapter owns pygame primitives.

Pygame-specific code cannot infect playback, config, loading, or domain modules.

## 13.6 Schema-first config contracts

Every config field must be defined in:

```text
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md
demos/iter9_visual_solver/config/models.py
```

Each field must identify its owning runtime module.

Example:

```text
playback.mine_count_multiplier

Owner:
  playback/speed_policy.py

Not owner:
  rendering/pygame_loop.py
  cli/commands.py
```

## 13.7 Event model separation

Separate concerns:

```text
domain/playback_event.py       data model
io/event_trace_loader.py       reads jsonl
io/event_trace_writer.py       writes jsonl
playback/event_source.py       chooses final-grid replay vs trace replay
playback/event_scheduler.py    determines which events happen this frame
rendering/board_surface.py     draws events
```

## 13.8 Renderer / view-model separation

The status panel should not read metrics directly.

Use:

```text
domain/status_snapshot.py
rendering/status_text.py
rendering/status_panel.py
```

## 13.9 Fixture-builder-helper testing architecture

Tests must not duplicate setup.

Use three separate test support concepts:

```text
fixtures = ready-made common objects
builders = controlled variation objects
helpers = reusable assertions/actions
```

## 13.10 Architecture fitness tests

Required files:

```text
tests/demo/iter9_visual_solver/test_architecture_boundaries.py
tests/demo/iter9_visual_solver/test_source_file_modularity.py
```

Enforced rules:

```text
pygame imports only allowed in rendering/ and pygame fake tests
pydantic imports only allowed in config/
jsonschema imports only allowed in schema contract tests
io/ modules must not import pygame
playback/ modules must not import pygame
domain/ modules must not import pygame, pydantic, or pathlib
rendering/ modules must not import pydantic
config/ modules must not import pygame
cli/ modules may orchestrate but not contain pixel drawing logic
```

## 13.11 Responsibility budget method

Each file gets a responsibility budget.

Review a file when it has more than:

```text
1 primary responsibility
3 public functions
3 imported internal package areas
1 side-effect category
```

## 13.12 Public API budget method

Each module should expose a small public API.

Target:

```text
1–3 public functions/classes per source file
```

If a file needs 6–10 public functions, it is probably multiple files.

## 13.13 Growth trigger refactor rules

Split a file immediately when:

```text
1. A new import belongs to a different architecture layer.
2. A second config section is consumed by the same file.
3. A function needs both pygame objects and domain calculations.
4. A test requires unrelated fixtures.
5. A function name contains "and."
6. A module section header becomes necessary to separate unrelated areas.
7. A helper function is only there to support another responsibility.
8. A new feature would require editing more than one conceptual section of a file.
9. A file's test file needs more than one builder type.
10. The file needs both happy-path and error-path fixtures from different domains.
```

---

# 14. File Size Methodology

The line count is a smoke alarm, not the architecture.

Target ranges:

```text
0–150 lines:
  Ideal for focused modules.

150–300 lines:
  Acceptable for a substantial single-responsibility module.

300–400 lines:
  Requires review. Confirm there is still exactly one responsibility.

400–500 lines:
  Must have a documented reason to remain together.

500+ lines:
  Treated as an architecture failure unless the file is generated, data-only, or an explicitly approved exception.
```

This is not a static-only hard cap. The primary controls are architecture boundaries, import-boundary tests, responsibility budgets, policy extraction, and fixture-builder-helper testing.

---

# 15. Test Package Layout

Correct test structure:

```text
tests/
  demo/
    __init__.py

    iter9_visual_solver/
      __init__.py

      fixtures/
        __init__.py
        configs.py
        grids.py
        metrics.py
        event_traces.py
        temp_runs.py
        pygame_fakes.py

      builders/
        __init__.py
        config_builder.py
        grid_builder.py
        metrics_builder.py
        event_trace_builder.py
        status_snapshot_builder.py

      helpers/
        __init__.py
        assertions.py
        schema_assertions.py
        filesystem_assertions.py
        import_boundary_assertions.py
        pygame_assertions.py

      test_config_models.py
      test_config_loader.py
      test_config_schema_contract.py
      test_artifact_paths.py
      test_grid_loader.py
      test_metrics_loader.py
      test_event_trace_loader.py
      test_event_trace_writer.py
      test_board_dimensions.py
      test_playback_event.py
      test_speed_policy.py
      test_event_batching.py
      test_event_scheduler.py
      test_replay_state.py
      test_finish_policy.py
      test_color_palette.py
      test_window_geometry.py
      test_board_surface.py
      test_status_text.py
      test_status_panel.py
      test_pygame_adapter_contract.py
      test_pygame_loop_with_fakes.py
      test_cli_args.py
      test_cli_commands.py
      test_run_iter9_launch_hook.py
      test_architecture_boundaries.py
      test_source_file_modularity.py
```

---

# 16. Shared Fixture Files

## 16.1 `fixtures/grids.py`

Owns reusable grid fixtures.

Examples:

```text
tiny_2x2_grid()
wide_300x10_grid()
tall_10x300_grid()
line_art_like_grid()
empty_grid(height, width)
checker_mine_grid(height, width)
```

## 16.2 `fixtures/metrics.py`

Owns reusable metrics documents.

Examples:

```text
minimal_iter9_metrics(board="300x942", seed=11)
metrics_with_source_image(name="line_art_irl_11_v2.png")
metrics_with_unknowns(n_unknown=25)
metrics_with_artifact_inventory(...)
```

## 16.3 `fixtures/configs.py`

Owns valid and invalid config fixtures.

Examples:

```text
default_demo_config_dict()
config_with_finish_mode("stay_open")
config_with_playback_multiplier(0.08)
invalid_config_missing_schema_version()
invalid_config_bad_rgb_tuple()
invalid_config_negative_speed()
```

## 16.4 `fixtures/event_traces.py`

Owns solver-event trace examples.

Examples:

```text
valid_flag_only_trace()
valid_safe_and_mine_trace()
trace_with_duplicate_cell()
trace_with_out_of_bounds_cell()
trace_with_unknown_state()
```

## 16.5 `fixtures/pygame_fakes.py`

Owns fake pygame seams.

Examples:

```text
FakeClock
FakeSurface
FakeFont
FakeEventQueue
FakePygameModule
```

## 16.6 `fixtures/temp_runs.py`

Owns temporary Iter9 run folder creation.

Examples:

```text
make_temp_iter9_run_dir()
write_grid_artifact()
write_metrics_artifact()
write_event_trace_artifact()
write_demo_config()
```

---

# 17. Shared Helper Files

## 17.1 `helpers/assertions.py`

Owns semantic assertions.

Examples:

```text
assert_status_snapshot_matches_metrics(...)
assert_event_sequence_is_monotonic(...)
assert_replay_finished(...)
assert_board_dimensions(...)
```

## 17.2 `helpers/schema_assertions.py`

Owns schema validation assertions.

Examples:

```text
assert_json_schema_valid(schema)
assert_json_validates(instance, schema)
assert_json_rejected(instance, schema, expected_message_fragment)
```

## 17.3 `helpers/filesystem_assertions.py`

Owns file/path assertions.

Examples:

```text
assert_file_exists(path)
assert_no_root_ad_hoc_files(project_root)
assert_only_expected_files_written(root, expected_relative_paths)
```

## 17.4 `helpers/pygame_assertions.py`

Owns rendering-specific assertions.

Examples:

```text
assert_surface_size(surface, width, height)
assert_pixel_rgb(surface, x, y, rgb)
assert_window_geometry_fits_screen(...)
```

## 17.5 `helpers/import_boundary_assertions.py`

Owns modularity/import-boundary assertions.

Examples:

```text
assert_module_does_not_import(module_path, forbidden_import)
assert_package_imports_without_pygame_window()
assert_no_runtime_module_imports_tests()
```

---

# 18. Builder Files

Builders allow controlled variation. Fixtures give ready-made objects. Helpers provide reusable assertions.

## 18.1 `builders/config_builder.py`

Example API:

```python
config = (
    DemoConfigBuilder()
    .with_finish_mode("stay_open")
    .with_base_events_per_second(1000)
    .with_mine_count_multiplier(0.08)
    .build_dict()
)
```

## 18.2 `builders/grid_builder.py`

Example API:

```python
grid = (
    GridBuilder(height=6, width=8)
    .with_mines([(0, 0), (3, 4)])
    .build()
)
```

## 18.3 `builders/event_trace_builder.py`

Example API:

```python
trace = (
    EventTraceBuilder(board_height=6, board_width=8)
    .flag(0, 0)
    .safe(1, 1)
    .flag(3, 4)
    .build_jsonl()
)
```

## 18.4 `builders/metrics_builder.py`

Example API:

```python
metrics = (
    MetricsBuilder()
    .with_source_image("line_art_irl_11_v2.png")
    .with_board("300x942")
    .with_seed(11)
    .with_unknown_count(0)
    .build_dict()
)
```

## 18.5 `builders/status_snapshot_builder.py`

Example API:

```python
snapshot = (
    StatusSnapshotBuilder()
    .with_board(width=300, height=942)
    .with_playback_speed(8500)
    .with_flagged_mines(1200, total_mines=4000)
    .build()
)
```

---

# 19. LLM Task Sequencing Standard

For AI-driven coding, each task should follow this sequence:

```text
1. Write or update the contract doc.
2. Write or update schema docs/spec if relevant.
3. Write or update fixtures/builders/helpers.
4. Write failing tests.
5. Implement the smallest source module.
6. Run targeted tests.
7. Run architecture boundary tests.
8. Run full unittest discovery.
9. Update traceability matrix.
```

Good LLM task:

```text
Implement only demos/iter9_visual_solver/playback/speed_policy.py and its tests.
Do not touch pygame.
Do not touch run_iter9.py.
Do not touch config loader except typed model imports if required.
```

Bad LLM task:

```text
Implement the demo.
```

That is too vague and will produce a blob.

---

# 20. Highest-Value First Coding Targets After Contracts Exist

After Phase -2, Phase -1, Phase 0, and Phase 1 docs/schema work are complete, the first coding targets should be:

## 20.1 Architecture gate tests

```text
test_architecture_boundaries.py
test_source_file_modularity.py
```

## 20.2 Test support builders/fixtures/helpers

```text
fixtures/configs.py
builders/config_builder.py
helpers/schema_assertions.py
helpers/import_boundary_assertions.py
```

## 20.3 Executable contract constants

```text
contracts/artifact_names.py
contracts/schema_versions.py
contracts/defaults.py
```

Because, at this point, the contracts already exist and these files mirror them.

## 20.4 Config models

```text
config/models.py
config/loader.py
```

## 20.5 Playback speed policy

```text
playback/speed_policy.py
```

## 20.6 Window geometry

```text
domain/board_dimensions.py
rendering/window_geometry.py
```

## 20.7 Finish policy

```text
playback/finish_policy.py
```

## 20.8 Artifact loaders

```text
io/grid_loader.py
io/metrics_loader.py
```

## 20.9 Event source / replay state

```text
playback/event_source.py
playback/replay_state.py
```

## 20.10 Board surface and status text

```text
rendering/board_surface.py
rendering/status_text.py
```

## 20.11 pygame loop

```text
rendering/pygame_adapter.py
rendering/pygame_loop.py
```

## 20.12 `run_iter9.py` hook

```text
run_iter9.py
```

This is last because the core pipeline should remain untouched until the standalone demo runner works.

---

# 21. Completion Gate

The demo is not execution-ready unless all of this is true:

```text
Contract discovery document exists.
Human-readable contract docs exist.
Contracts have passed contradiction review.
Traceability matrix maps requirements to docs, modules, and tests.
JSON schema specs live under demo/docs/json_schemas/.
Painstaking schema Markdown lives under demo/docs/json_schemas/.
Runtime code is under demos/iter9_visual_solver/.
Tests are under tests/demo/iter9_visual_solver/.
Shared fixtures exist under tests/demo/iter9_visual_solver/fixtures/.
Shared helpers exist under tests/demo/iter9_visual_solver/helpers/.
Builders exist under tests/demo/iter9_visual_solver/builders/.
Default config lives under configs/demo/.
No root-level demo_config.py exists.
No root-level demo_visualizer.py exists.
No pygame import exists outside rendering modules except pygame fakes/tests.
No Pydantic import exists outside config/schema modules.
Playback speed is tested independently from pygame.
Window sizing is tested independently from pygame.
Finish behavior is tested independently from pygame.
Pygame loop is tested with fakes first.
Line count is enforced as a smoke alarm, not as the primary architecture rule.
The full test command passes:
  python -m unittest discover -s tests -p "test_*.py"
```

---

# 22. Final Architecture Judgment

The corrected design is:

```text
Contract discovery first.
Human contract docs second.
Executable contract code only after docs are accepted.
Modular package first.
Fixture/helper/builder testing architecture first.
pygame rendering isolated.
Config/schema isolated.
Playback logic isolated.
Window sizing isolated.
Finish behavior isolated.
No short-term root scripts.
No "split later."
No static-only 500-line rule.
```

The implementation should proceed only after the contract documents and JSON schema documents are written in the correct demo documentation area.
