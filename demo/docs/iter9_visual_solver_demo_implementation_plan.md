# Iter9 Visual Solver Demo - Generated Implementation Plan

## 0. Plan Status

| Field | Value |
|---|---|
| Plan status | Executed for standalone MVP runtime on 2026-05-02 |
| Generated on | 2026-05-02 |
| Demo documentation root | `demo/docs/` |
| Demo schema documentation root | `demo/docs/json_schemas/` |
| Runtime package target | `demos/iter9_visual_solver/` |
| Test package target | `tests/demo/iter9_visual_solver/` |
| Default config target | `configs/demo/iter9_visual_solver_demo.default.json` |
| Integration style | Additive demo package; optional thin `run_iter9.py` hook wired last |
| Current repository state observed | Demo docs, runtime package, default config, contract-strengthened tests, standalone CLI, pygame loop, and optional `run_iter9.py` flags are implemented |

This plan is generated from the dedicated demo documentation files under
`demo/docs/` plus the top-level demo planning file under `demo/`. The demo
documentation is its own package-level source of truth. Do not move the demo
contracts into the base repository documentation tree as part of this
implementation.

This is not a monolithic repository refactor. The visual solver demo is a
bounded additive feature. Existing root reconstruction modules remain stable
unless the final optional Iter9 launch hook phase explicitly touches
`run_iter9.py`.

---

## 1. Source Documents Analyzed

The following files are the source set for this implementation plan:

```text
demo/docs/iter9_visual_solver_demo_execution_plan.md
demo/docs/iter9_visual_solver_demo_implementation_plan.md
demo/iter9_visual_solver_demo_plan.md
demo/docs/acceptance_criteria.md
demo/docs/architecture_boundary_tests.md
demo/docs/architecture_decisions.md
demo/docs/artifact_consumption_contract.md
demo/docs/completion_gate.md
demo/docs/config_contract.md
demo/docs/finish_behavior_contract.md
demo/docs/playback_speed_contract.md
demo/docs/pygame_rendering_contract.md
demo/docs/runtime_package_contract.md
demo/docs/schema_docs_specs.md
demo/docs/source_modularity_standard.md
demo/docs/status_panel_contract.md
demo/docs/testing_methodology.md
demo/docs/traceability_matrix.md
demo/docs/window_sizing_contract.md
demo/docs/json_schemas/README.md
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md
demo/docs/json_schemas/solver_event_trace.schema.json
demo/docs/json_schemas/solver_event_trace.schema.md
```

The plan intentionally resolves the documentation-root ambiguity in favor of
the actual dedicated demo documentation tree:

```text
demo/docs/
demo/docs/json_schemas/
```

Contracts, tests, and helpers now use the demo-local documentation layout. New
demo docs must continue to use `demo/docs/` and `demo/docs/json_schemas/`.

---

## 2. Implementation Goal

Build a durable MVP visual solver demo that:

1. Launches from completed Iter9 artifacts.
2. Loads `grid_iter9_latest.npy`.
3. Loads `metrics_iter9_<board>.json`.
4. Optionally loads `solver_event_trace.jsonl` when present and enabled.
5. Falls back to deterministic final-grid replay when no solver trace exists
   and fallback is enabled.
6. Opens a pygame GUI window.
7. Derives board width and height from `grid.shape`.
8. Sizes the window from board dimensions and validated config.
9. Replays cell events at config-driven speed.
10. Applies event batches without dropping or duplicating events.
11. Displays status lines with real values.
12. Honors configured finish behavior.
13. Keeps pygame isolated behind rendering adapter/loop modules.
14. Keeps Pydantic isolated to config modules.
15. Keeps JSON Schema validation as test/tooling behavior for MVP.
16. Leaves existing Iter9 behavior unchanged when demo flags are omitted.

The MVP may show a final-grid replay rather than true chronological solver
trace replay. True trace emission can be added later as long as the optional
`solver_event_trace.jsonl` contract remains compatible.

---

## 3. Source-of-Truth Priority

Use this order when implementation details conflict:

1. User correction in this task: `demo/docs/` is the dedicated documentation
   root for the demo.
2. `demo/docs/json_schemas/*.schema.json` for machine-checkable JSON shape.
3. `demo/docs/*.md` contracts for runtime behavior and ownership boundaries.
4. `demo/iter9_visual_solver_demo_plan.md` for background sequencing and design
   rationale, after translating its documentation paths to `demo/docs/`.
5. Existing `tests/demo/iter9_visual_solver/` scaffold when it agrees with the
   demo contracts.
6. This implementation plan as the execution map.

If tests disagree with the dedicated demo documentation root, update tests to
match `demo/docs/`.

---

## 4. Current Live-State Assessment

Observed live state after this execution:

| Area | Observed state | Required action |
|---|---|---|
| Demo docs | Present under `demo/docs/` | Treat as canonical. |
| Demo schema files | Present under `demo/docs/json_schemas/` | Use as committed schema baseline. |
| Demo tests | Strengthened under `tests/demo/iter9_visual_solver/` | Keep architecture/schema/playback/rendering tests green. |
| Runtime package | Implemented under `demos/iter9_visual_solver/` | Keep new runtime work inside package boundaries. |
| Default config | Implemented under `configs/demo/` | Keep schema/default config drift tests green. |
| Optional Iter9 hook | Thin launch module and `run_iter9.py` flags are implemented | Keep hook pygame-free and delegation-only. |
| Existing root modules | Existing pipeline modules are present | Do not refactor for demo work. |

The demo has executable coverage for config/schema validation, artifact I/O,
domain models, playback policies, rendering seams, fake pygame loop behavior,
CLI surface, hook delegation, and architecture boundaries. The latest contract
continuation specifically verifies final-grid cell replay, ceil-based batching,
CLI-to-loop propagation of playback/status/finish/geometry inputs, board color
mapping, status wording, and finish behavior. Manual GUI validation still
requires an environment with `pygame` installed.

---

## 5. Non-Negotiable Boundaries

| Boundary | Rule |
|---|---|
| Demo documentation | Demo docs live under `demo/docs/`; schema docs live under `demo/docs/json_schemas/`. |
| Runtime source | Demo runtime code lives under `demos/iter9_visual_solver/`. |
| Tests | Demo tests live under `tests/demo/iter9_visual_solver/`. |
| Config file | Default config lives under `configs/demo/iter9_visual_solver_demo.default.json`. |
| Root scripts | Do not create root-level `demo_config.py`, `demo_visualizer.py`, `visual_solver_demo.py`, or `iter9_visual_solver_demo.py`. |
| Existing pipeline | Do not refactor existing root modules for demo work. |
| Pygame | Pygame imports are allowed only in pygame rendering adapter/loop modules and pygame-specific tests/fakes. |
| Pydantic | Pydantic imports are allowed only in `demos/iter9_visual_solver/config/` and config tests. |
| JSON Schema | `jsonschema` is test/tooling only for MVP; runtime config validation is Pydantic-driven. |
| Playback math | Speed, batching, scheduling, and finish policy live in `playback/`, not in pygame code. |
| Artifact loading | Artifact resolution and file reading live in `io/`, not in playback or rendering. |
| CLI | CLI orchestrates existing modules; it does not draw pixels or own business rules. |
| Iter9 hook | `run_iter9.py` gets only optional flags and a thin delegation call after standalone CLI works. |

---

## 6. Target Runtime Package

Create this package exactly, with side-effect-free `__init__.py` files:

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
    errors/
      __init__.py
      artifact_errors.py
      config_errors.py
      rendering_errors.py
      trace_errors.py
    io/
      __init__.py
      artifact_paths.py
      event_trace_loader.py
      event_trace_writer.py
      grid_loader.py
      json_reader.py
      metrics_loader.py
    playback/
      __init__.py
      event_batching.py
      event_scheduler.py
      event_source.py
      finish_policy.py
      replay_state.py
      speed_policy.py
    rendering/
      __init__.py
      board_surface.py
      color_palette.py
      pygame_adapter.py
      pygame_loop.py
      status_panel.py
      status_text.py
      window_geometry.py
```

Package ownership:

| Package | Owns | Must not own |
|---|---|---|
| `cli/` | argument parsing and orchestration | pygame drawing, artifact parsing internals, playback math |
| `config/` | Pydantic models, config loading, schema export | replay logic, rendering |
| `contracts/` | constants mirroring accepted docs | behavior, file I/O |
| `domain/` | plain data models and pure domain validation | filesystem, pygame, Pydantic |
| `errors/` | typed error classes | business logic |
| `io/` | artifact path resolution and loading | pygame drawing, speed policy |
| `playback/` | event selection, speed, batching, scheduling, replay, finish | file loading, pygame |
| `rendering/` | palette, geometry, board/status drawing, pygame adapter/loop | config validation, artifact loading |

---

## 7. Target Test Package

The existing scaffold already matches the intended location:

```text
tests/demo/iter9_visual_solver/
```

The complete target structure is:

```text
tests/demo/iter9_visual_solver/
  fixtures/
    __init__.py
    configs.py
    event_traces.py
    grids.py
    metrics.py
    pygame_fakes.py
    temp_runs.py
  builders/
    __init__.py
    config_builder.py
    event_trace_builder.py
    grid_builder.py
    metrics_builder.py
    status_snapshot_builder.py
  helpers/
    __init__.py
    assertions.py
    filesystem_assertions.py
    import_boundary_assertions.py
    pygame_assertions.py
    schema_assertions.py
  test_architecture_boundaries.py
  test_artifact_paths.py
  test_board_dimensions.py
  test_board_surface.py
  test_cli_args.py
  test_cli_commands.py
  test_color_palette.py
  test_config_loader.py
  test_config_models.py
  test_config_schema_contract.py
  test_event_batching.py
  test_event_scheduler.py
  test_event_source.py
  test_event_trace_loader.py
  test_event_trace_writer.py
  test_finish_policy.py
  test_grid_loader.py
  test_metrics_loader.py
  test_playback_event.py
  test_pygame_adapter_contract.py
  test_pygame_loop_with_fakes.py
  test_replay_state.py
  test_run_iter9_launch_hook.py
  test_source_file_modularity.py
  test_speed_policy.py
  test_status_panel.py
  test_status_text.py
  test_window_geometry.py
```

Tests should use shared fixtures/builders/helpers. Do not duplicate large
config dictionaries, grid literals, temporary run layouts, or pygame fakes
inside individual tests.

---

## 8. Phase 0 - Demo Documentation Path Normalization

### Purpose

Make the dedicated demo documentation root executable in tests and future code.
This is the first phase because current docs and scaffold tests contain stale
root-doc wording that conflicts with the actual demo-local tree.

### Files to update

Update only demo planning/docs/tests that reference the obsolete root-doc
layout. The canonical replacement is:

```text
demo/docs/
demo/docs/json_schemas/
```

Expected update areas:

```text
demo/iter9_visual_solver_demo_plan.md
demo/docs/acceptance_criteria.md
demo/docs/architecture_boundary_tests.md
demo/docs/architecture_decisions.md
demo/docs/completion_gate.md
demo/docs/config_contract.md
demo/docs/finish_behavior_contract.md
demo/docs/json_schemas/README.md
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md
demo/docs/json_schemas/solver_event_trace.schema.md
demo/docs/schema_docs_specs.md
demo/docs/testing_methodology.md
demo/docs/traceability_matrix.md
tests/demo/iter9_visual_solver/test_config_schema_contract.py
```

### Required behavior

- Demo docs remain under `demo/docs/`.
- Demo schemas remain under `demo/docs/json_schemas/`.
- Tests validate the schema files at the demo-local path.
- Architecture tests enforce the demo-local path.
- No root-level docs migration is performed.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_schema_contract
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
$oldForward = 'docs' + '/demo'
$oldWindows = 'docs' + '\demo'
rg -n $oldForward demo tests
rg -n $oldWindows demo tests
```

The final `rg` command must return no active-path references except inside
archived materials or explicit historical notes.

---

## 9. Phase 1 - Architecture Gates and Test Scaffold Hardening

### Purpose

Turn the existing scaffold into enforceable architecture fitness tests before
runtime modules are implemented.

### Implement or strengthen

```text
tests/demo/iter9_visual_solver/helpers/import_boundary_assertions.py
tests/demo/iter9_visual_solver/helpers/filesystem_assertions.py
tests/demo/iter9_visual_solver/test_architecture_boundaries.py
tests/demo/iter9_visual_solver/test_source_file_modularity.py
```

### Required test coverage

Architecture tests must enforce:

1. No forbidden root demo files.
2. Runtime package root exists once implementation starts.
3. Required runtime subpackages exist once implementation starts.
4. Pygame imports are rendering-only.
5. Pydantic imports are config-only.
6. `jsonschema` is absent from runtime modules.
7. Domain modules do not import pygame, Pydantic, filesystem loaders, or schema tooling.
8. Playback modules do not perform file I/O or rendering.
9. Rendering modules do not validate config or load raw artifacts.
10. I/O modules do not render.
11. CLI modules do not draw pixels or open pygame windows.
12. `run_iter9.py` does not import pygame.
13. Demo schema docs are located under `demo/docs/json_schemas/`.
14. Runtime/test line counts remain below smoke-alarm thresholds unless an approved exception exists.
15. Tests use shared fixtures/builders/helpers instead of repeated large setup.

### Implementation notes

- Use AST parsing for import-boundary tests.
- Normalize paths to POSIX style for Windows/Linux stability.
- Keep pre-runtime tests allowed to skip only when runtime source truly does
  not exist yet.
- Once `demos/iter9_visual_solver/` exists, missing required packages become
  blocking failures.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
python -m unittest tests.demo.iter9_visual_solver.test_source_file_modularity
```

---

## 10. Phase 2 - Executable Contracts and Default Config

### Purpose

Mirror the accepted Markdown/schema decisions in small runtime constants and a
committed default config.

### Create

```text
demos/__init__.py
demos/iter9_visual_solver/__init__.py
demos/iter9_visual_solver/contracts/__init__.py
demos/iter9_visual_solver/contracts/artifact_names.py
demos/iter9_visual_solver/contracts/defaults.py
demos/iter9_visual_solver/contracts/schema_versions.py
configs/demo/iter9_visual_solver_demo.default.json
```

### Required constants

```python
GRID_LATEST_FILENAME = "grid_iter9_latest.npy"
EVENT_TRACE_FILENAME = "solver_event_trace.jsonl"
METRICS_FILENAME_PREFIX = "metrics_iter9_"
METRICS_FILENAME_SUFFIX = ".json"

CONFIG_SCHEMA_VERSION = "iter9_visual_solver_demo_config.v1"
EVENT_TRACE_SCHEMA_VERSION = "iter9_visual_solver_event_trace.v1"

DEFAULT_CONFIG_PATH = Path("configs/demo/iter9_visual_solver_demo.default.json")
DEFAULT_FINISH_MODE = "stay_open"
DEFAULT_PLAYBACK_MODE = "mine_count_scaled"
```

### Default config contract

The committed default config must match
`demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json`:

- `schema_version`: `iter9_visual_solver_demo_config.v1`
- `window.finish_behavior.mode`: `stay_open`
- `window.finish_behavior.close_after_seconds`: `null`
- `playback.mode`: `mine_count_scaled`
- `playback.min_events_per_second`: `50`
- `playback.base_events_per_second`: `1000`
- `playback.mine_count_multiplier`: `0.08`
- `playback.max_events_per_second`: `12000`
- `playback.target_fps`: `60`
- `playback.batch_events_per_frame`: `true`
- `input.prefer_solver_event_trace`: `true`
- `input.allow_final_grid_replay_fallback`: `true`

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_schema_contract
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 11. Phase 3 - Config Models, Loader, and Schema Drift Tests

### Purpose

Make config validation executable before pygame can start.

### Create

```text
demos/iter9_visual_solver/config/__init__.py
demos/iter9_visual_solver/config/loader.py
demos/iter9_visual_solver/config/models.py
demos/iter9_visual_solver/config/schema_export.py
demos/iter9_visual_solver/config/validation_errors.py
demos/iter9_visual_solver/errors/__init__.py
demos/iter9_visual_solver/errors/config_errors.py
```

### Required models

```text
DemoConfig
WindowConfig
FinishBehaviorConfig
PlaybackConfig
VisualsConfig
StatusPanelConfig
InputConfig
```

### Required validation

- Unknown fields are rejected.
- `schema_version` must equal `iter9_visual_solver_demo_config.v1`.
- Finish mode must be `stay_open`, `close_immediately`, or `close_after_delay`.
- `close_after_seconds` may be `null` except `close_after_delay` requires a
  number greater than or equal to zero.
- Playback mode must be `mine_count_scaled`.
- Playback min/max rates must be positive and ordered.
- `base_events_per_second` and `mine_count_multiplier` must be non-negative.
- `target_fps` must be positive.
- `batch_events_per_frame` must be boolean.
- RGB values must contain exactly three integers in `0..255`.
- `preferred_board_cell_px >= minimum_board_cell_px`.

### Loader behavior

`load_demo_config(path: Path) -> DemoConfig` must:

- raise a typed not-found error for missing config files;
- raise a typed JSON error for malformed JSON;
- raise a typed validation error for Pydantic failures;
- include the config path in error messages;
- include field path information when available;
- never import or initialize pygame.

### Schema drift behavior

`schema_export.py` may expose generated Pydantic schema helpers for tests, but
runtime must not depend on `jsonschema`. Tests compare committed schema,
default config, invalid examples, and generated model fields enough to catch
drift.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_models
python -m unittest tests.demo.iter9_visual_solver.test_config_loader
python -m unittest tests.demo.iter9_visual_solver.test_config_schema_contract
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 12. Phase 4 - Pure Domain Layer

### Purpose

Create pygame-free, file-I/O-free domain objects used by I/O, playback, status,
and rendering.

### Create

```text
demos/iter9_visual_solver/domain/__init__.py
demos/iter9_visual_solver/domain/board_dimensions.py
demos/iter9_visual_solver/domain/board_state.py
demos/iter9_visual_solver/domain/demo_input.py
demos/iter9_visual_solver/domain/playback_event.py
demos/iter9_visual_solver/domain/status_snapshot.py
```

### Required behavior

`BoardDimensions`:

- derives `height = grid.shape[0]`;
- derives `width = grid.shape[1]`;
- derives `total_cells = width * height`;
- rejects non-2D grids;
- does not transpose or reinterpret the grid.

`PlaybackEvent`:

- requires `schema_version` or normalizes from loader-owned schema validation;
- uses zero-based `step`, `y`, and `x`;
- accepts `step >= 0`, `round >= 0`, `y >= 0`, `x >= 0`;
- accepts state values `SAFE`, `MINE`, and `UNKNOWN`;
- accepts display values `reveal`, `flag`, and `unknown`;
- enforces `MINE -> flag`, `SAFE -> reveal`, and `UNKNOWN -> unknown`.

`BoardState`:

- starts with all cells unseen/unknown for playback;
- applies normalized events by coordinate;
- exposes counts needed by status snapshots.

`DemoInput`:

- aggregates loaded grid, metrics, optional trace events, source paths, and
  board dimensions;
- remains a data object rather than an I/O loader.

`StatusSnapshot`:

- contains only already-derived display values;
- does not read metrics or config files.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_board_dimensions
python -m unittest tests.demo.iter9_visual_solver.test_playback_event
python -m unittest tests.demo.iter9_visual_solver.test_replay_state
python -m unittest tests.demo.iter9_visual_solver.test_status_text
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 13. Phase 5 - Artifact I/O

### Purpose

Load completed Iter9 run artifacts with typed errors, shape checks, and no
rendering/playback leakage.

### Create

```text
demos/iter9_visual_solver/errors/artifact_errors.py
demos/iter9_visual_solver/errors/trace_errors.py
demos/iter9_visual_solver/io/__init__.py
demos/iter9_visual_solver/io/artifact_paths.py
demos/iter9_visual_solver/io/event_trace_loader.py
demos/iter9_visual_solver/io/event_trace_writer.py
demos/iter9_visual_solver/io/grid_loader.py
demos/iter9_visual_solver/io/json_reader.py
demos/iter9_visual_solver/io/metrics_loader.py
```

### Artifact paths

The I/O layer owns:

```text
grid_iter9_latest.npy
metrics_iter9_<board>.json
solver_event_trace.jsonl
```

`artifact_paths.py` must provide:

```python
@dataclass(frozen=True)
class DemoArtifactPaths:
    run_dir: Path
    grid_path: Path
    metrics_path: Path
    event_trace_path: Path | None

def metrics_filename_for_board(board_label: str) -> str: ...
def resolve_artifact_paths(...) -> DemoArtifactPaths: ...
```

### Grid loader

`load_grid(path: Path) -> np.ndarray` must:

- use `np.load`;
- reject missing files;
- reject invalid NumPy files;
- reject non-2D arrays;
- preserve shape;
- avoid dtype conversion unless explicitly documented and tested.

### Metrics loader

`load_metrics(path: Path) -> dict` or a typed metrics data object must validate
the fields required by the status panel and demo orchestration:

- board label;
- seed;
- source image name or equivalent provenance field;
- unknown count when available;
- total mines or enough grid-derived data to calculate it;
- coverage/solvable fields when available for status/debug display.

Fallback behavior must be explicit when a metric field has changed across Iter9
artifact versions.

### Event trace loader/writer

`solver_event_trace.jsonl` is one JSON object per line. Loader rules:

- reject malformed JSON with line number;
- reject unknown schema version;
- reject missing required fields;
- reject invalid state/display pairings;
- reject negative coordinates;
- reject out-of-bounds coordinates after board dimensions are known;
- enforce monotonic or normalized step ordering;
- reject duplicate steps unless a contract update explicitly allows them;
- return normalized `PlaybackEvent` objects.

Writer rules:

- write JSONL atomically using a temp file and replace;
- emit rows that the loader can read back;
- include schema version on every row.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_artifact_paths
python -m unittest tests.demo.iter9_visual_solver.test_grid_loader
python -m unittest tests.demo.iter9_visual_solver.test_metrics_loader
python -m unittest tests.demo.iter9_visual_solver.test_event_trace_loader
python -m unittest tests.demo.iter9_visual_solver.test_event_trace_writer
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 14. Phase 6 - Playback Core Without Pygame

### Purpose

Implement replay behavior as a functional core that can be tested without GUI
dependencies.

### Create

```text
demos/iter9_visual_solver/playback/__init__.py
demos/iter9_visual_solver/playback/event_batching.py
demos/iter9_visual_solver/playback/event_scheduler.py
demos/iter9_visual_solver/playback/event_source.py
demos/iter9_visual_solver/playback/finish_policy.py
demos/iter9_visual_solver/playback/replay_state.py
demos/iter9_visual_solver/playback/speed_policy.py
```

### Speed policy

`speed_policy.py` owns:

```python
def calculate_events_per_second(playback_config: PlaybackConfig, *, total_mines: int) -> int: ...
```

Formula:

```text
calculated = base_events_per_second + total_mines * mine_count_multiplier
events_per_second = min(max_events_per_second, max(min_events_per_second, calculated))
```

Rules:

- return a deterministic integer;
- clamp to configured min/max;
- reject negative mine counts;
- do not use event timestamps;
- do not import pygame.

### Event source

`event_source.py` owns:

```python
def build_playback_events_from_final_grid(grid: np.ndarray) -> list[PlaybackEvent]: ...
def select_event_source(
    *,
    input_config: InputConfig,
    grid: np.ndarray,
    trace_events: list[PlaybackEvent] | None,
) -> tuple[list[PlaybackEvent], str]: ...
```

Rules:

- prefer solver trace when config allows and trace exists;
- use final-grid replay when fallback is enabled;
- fail clearly when trace is required and missing;
- final-grid replay generates deterministic mine-flag events;
- final-grid replay source label is `final_grid_replay`.

### Event batching

`event_batching.py` owns:

```python
def calculate_events_per_frame(
    *,
    events_per_second: int,
    target_fps: int,
    batch_events_per_frame: bool,
) -> int: ...
```

Rules:

- return `1` when batching is disabled;
- return at least `1` when batching is enabled;
- use a documented deterministic rounding policy;
- test slow, normal, and very fast playback rates.

### Scheduler and replay state

`EventScheduler`:

- returns ordered batches;
- never drops events;
- never duplicates events;
- reports completion accurately.

`ReplayState`:

- applies each event once;
- tracks mines flagged;
- tracks safe cells solved;
- tracks unknown remaining;
- exposes `StatusSnapshot`.

### Finish policy

Supported modes:

```text
stay_open
close_immediately
close_after_delay
```

Rules:

- `stay_open` never auto-closes;
- `close_immediately` closes as soon as playback completes;
- `close_after_delay` closes when elapsed after finish is greater than or equal
  to `close_after_seconds`;
- `close_after_seconds = 0` is valid and behaves like immediate close after
  playback completion.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_speed_policy
python -m unittest tests.demo.iter9_visual_solver.test_event_source
python -m unittest tests.demo.iter9_visual_solver.test_event_batching
python -m unittest tests.demo.iter9_visual_solver.test_event_scheduler
python -m unittest tests.demo.iter9_visual_solver.test_replay_state
python -m unittest tests.demo.iter9_visual_solver.test_finish_policy
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 15. Phase 7 - Rendering Helpers Without the Pygame Loop

### Purpose

Build renderable data, geometry, colors, and status text before opening a real
pygame window.

### Create

```text
demos/iter9_visual_solver/rendering/__init__.py
demos/iter9_visual_solver/rendering/board_surface.py
demos/iter9_visual_solver/rendering/color_palette.py
demos/iter9_visual_solver/rendering/status_panel.py
demos/iter9_visual_solver/rendering/status_text.py
demos/iter9_visual_solver/rendering/window_geometry.py
```

### Color palette

`color_palette.py` maps validated config RGB lists to immutable RGB values for:

- unseen cells;
- flagged mines;
- safe cells;
- unknown cells;
- background.

### Window geometry

`window_geometry.py` owns:

```python
def calculate_window_geometry(
    *,
    board_dimensions: BoardDimensions,
    window_config: WindowConfig,
    status_panel_visible: bool,
    screen_size: tuple[int, int],
) -> WindowGeometry: ...
```

Rules:

- use actual board dimensions;
- prefer configured cell size when possible;
- fit to screen when enabled;
- respect `max_screen_fraction`;
- include status panel width when visible;
- enforce minimum cell size;
- do not crop the board for MVP;
- fail clearly if a board cannot fit without violating minimum cell size.

### Board surface

`board_surface.py` converts board state to drawable cells/colors. It must not:

- load files;
- parse raw config;
- calculate playback speed;
- initialize pygame display.

### Status text

`status_text.py` owns formatting only. Required lines:

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

Rules:

- values come from `StatusSnapshot`;
- visibility comes from validated status-panel config;
- no placeholder strings such as `derived-height`;
- board line displays actual `width x height`.

### Status panel

`status_panel.py` draws already-formatted lines onto a supplied surface/adapter.
It must not calculate status values or read metrics.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_color_palette
python -m unittest tests.demo.iter9_visual_solver.test_window_geometry
python -m unittest tests.demo.iter9_visual_solver.test_board_surface
python -m unittest tests.demo.iter9_visual_solver.test_status_text
python -m unittest tests.demo.iter9_visual_solver.test_status_panel
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 16. Phase 8 - Pygame Adapter and Loop

### Purpose

Add the imperative pygame shell only after config, I/O, playback, geometry, and
status text are already tested.

### Create

```text
demos/iter9_visual_solver/rendering/pygame_adapter.py
demos/iter9_visual_solver/rendering/pygame_loop.py
```

### Adapter API

`pygame_adapter.py` should expose a small adapter that can be replaced by fakes:

```python
class PygameAdapter:
    def open_window(self, width: int, height: int, title: str): ...
    def poll_events(self): ...
    def tick(self, fps: int): ...
    def flip(self): ...
    def close(self): ...
```

The final API can be richer if tests require it, but it must remain a pygame
port, not a business-logic owner.

### Loop behavior

`pygame_loop.py` must:

1. accept already-loaded config-derived objects;
2. accept an event scheduler;
3. accept replay state;
4. accept board/status draw helpers;
5. accept an injectable pygame adapter for tests;
6. open one window;
7. poll OS/window events;
8. apply scheduled event batches;
9. draw board and status panel;
10. flip display;
11. tick target FPS;
12. honor finish policy;
13. exit cleanly on OS close event.

The loop must not:

- parse config files;
- call `np.load`;
- resolve artifact paths;
- calculate playback speed formula;
- decide trace-vs-final-grid source policy.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_pygame_adapter_contract
python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 17. Phase 9 - Standalone CLI

### Purpose

Create the primary launch surface before touching `run_iter9.py`.

### Create

```text
demos/iter9_visual_solver/cli/__init__.py
demos/iter9_visual_solver/cli/args.py
demos/iter9_visual_solver/cli/commands.py
```

### CLI arguments

Required MVP arguments:

```text
--grid
--metrics
--config
```

Optional arguments:

```text
--event-trace
```

Optional ergonomic argument, if implemented without duplicating I/O logic:

```text
--run-dir
```

`--run-dir` must delegate to `io/artifact_paths.py`.

### CLI orchestration sequence

`commands.py` owns this sequence only:

1. parse args;
2. load config;
3. load grid;
4. load metrics;
5. load optional event trace;
6. derive board dimensions;
7. build `DemoInput`;
8. select playback events;
9. calculate total mines;
10. calculate events per second;
11. calculate events per frame;
12. build scheduler;
13. build replay state;
14. calculate window geometry;
15. build status snapshot/text inputs;
16. launch pygame loop;
17. return a process code.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_cli_args
python -m unittest tests.demo.iter9_visual_solver.test_cli_commands
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 18. Phase 10 - Optional Thin `run_iter9.py` Hook

### Purpose

Allow `run_iter9.py` to launch the demo after a successful Iter9 run without
making the base pipeline own demo behavior.

### Create

```text
demos/iter9_visual_solver/cli/launch_from_iter9.py
```

### Modify

```text
run_iter9.py
```

### Add flags

```text
--demo-gui
--demo-config
```

### Hook API

```python
def run_demo_from_completed_iter9_run(
    *,
    grid_path: Path,
    metrics_path: Path,
    config_path: Path,
    event_trace_path: Path | None = None,
) -> int: ...
```

### Hook rules

- `run_iter9.py` must not import pygame.
- `run_iter9.py` must not parse demo config.
- `run_iter9.py` must not calculate playback speed.
- The hook runs only after Iter9 artifacts are successfully written.
- The hook receives exact completed artifact paths.
- Omitting `--demo-gui` preserves existing behavior.
- `--demo-config` is only meaningful when `--demo-gui` is enabled, unless a
  clear validation rule is added.

### Acceptance commands

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_run_iter9_launch_hook
python run_iter9.py --help
python run_benchmark.py --help
python -m unittest discover -s tests -p "test_*.py"
```

---

## 19. Phase 11 - Manual Demo Validation

### Purpose

Prove the GUI behavior with a completed Iter9 run.

### Generate or locate a run

Use an existing completed run if available. Otherwise generate a validation run:

```powershell
python run_iter9.py --image assets/line_art_irl_11_v2.png --board-w 300 --seed 11 --allow-noncanonical --run-tag "demo_manual_validation"
```

### Standalone demo command

```powershell
python -m demos.iter9_visual_solver.cli.commands --grid results/iter9/<run_id>/grid_iter9_latest.npy --metrics results/iter9/<run_id>/metrics_iter9_<board>.json --config configs/demo/iter9_visual_solver_demo.default.json
```

If a trace file exists:

```powershell
python -m demos.iter9_visual_solver.cli.commands --grid results/iter9/<run_id>/grid_iter9_latest.npy --metrics results/iter9/<run_id>/metrics_iter9_<board>.json --event-trace results/iter9/<run_id>/solver_event_trace.jsonl --config configs/demo/iter9_visual_solver_demo.default.json
```

### Optional hook command

```powershell
python run_iter9.py --image assets/line_art_irl_11_v2.png --board-w 300 --seed 11 --allow-noncanonical --run-tag "demo_hook_validation" --demo-gui --demo-config configs/demo/iter9_visual_solver_demo.default.json
```

### Manual pass criteria

- Window opens.
- Board aspect ratio matches `grid.shape`.
- Status panel shows source image, board dimensions, seed, total cells, mines
  flagged, safe solved, unknown remaining, playback speed, elapsed time, and
  finish state.
- No placeholder text appears.
- Mines or cell states animate over time.
- Playback speed visibly uses config-derived batching.
- Playback completes without event loss/duplication.
- Final board state matches loaded final grid.
- Configured finish behavior is honored.
- OS close event exits cleanly.
- Omitting `--demo-gui` keeps normal Iter9 behavior.

---

## 20. Cross-Contract Traceability

| Requirement | Source contract(s) | Runtime owner | Required test evidence |
|---|---|---|---|
| Use actual grid dimensions | `window_sizing_contract.md`, `acceptance_criteria.md` | `domain/board_dimensions.py`, `rendering/window_geometry.py` | `test_board_dimensions.py`, `test_window_geometry.py` |
| Config-driven speed | `playback_speed_contract.md`, `config_contract.md` | `playback/speed_policy.py` | `test_speed_policy.py` |
| No hardcoded speed in loop | `source_modularity_standard.md`, `pygame_rendering_contract.md` | `playback/`, `rendering/pygame_loop.py` | `test_architecture_boundaries.py` |
| Configurable finish behavior | `finish_behavior_contract.md` | `playback/finish_policy.py` | `test_finish_policy.py` |
| Final-grid replay MVP | `artifact_consumption_contract.md`, `architecture_decisions.md` | `io/grid_loader.py`, `playback/event_source.py` | `test_grid_loader.py`, `test_event_source.py` |
| Solver trace compatibility | `artifact_consumption_contract.md`, `solver_event_trace.schema.*` | `io/event_trace_loader.py`, `domain/playback_event.py` | `test_event_trace_loader.py`, `test_event_trace_writer.py` |
| Dedicated demo schema docs | `schema_docs_specs.md`, user correction | docs/tests only | `test_config_schema_contract.py`, architecture docs path tests |
| Runtime package isolation | `runtime_package_contract.md` | `demos/iter9_visual_solver/` | `test_architecture_boundaries.py` |
| Pygame isolation | `pygame_rendering_contract.md` | `rendering/pygame_adapter.py`, `rendering/pygame_loop.py` | `test_architecture_boundaries.py`, `test_pygame_loop_with_fakes.py` |
| Pydantic isolation | `config_contract.md` | `config/` | `test_architecture_boundaries.py` |
| Status panel real values | `status_panel_contract.md` | `domain/status_snapshot.py`, `rendering/status_text.py`, `rendering/status_panel.py` | `test_status_text.py`, `test_status_panel.py` |
| Thin optional Iter9 hook | `runtime_package_contract.md`, `acceptance_criteria.md` | `cli/launch_from_iter9.py`, `run_iter9.py` | `test_run_iter9_launch_hook.py`, CLI smoke |

---

## 21. Required Dependencies

| Dependency | Use | Boundary |
|---|---|---|
| `numpy` | Grid loading and board arrays | `io/`, `domain/`, playback/render data |
| `pydantic>=2` | Runtime config validation | `config/` only |
| `jsonschema` | Schema tests and schema artifact validation | tests/tools only |
| `pygame` import | GUI adapter and event loop | pygame rendering modules only |

Install command:

```powershell
python -m pip install numpy pydantic jsonschema pygame
```

On Python 3.14, if the `pygame` package attempts a source build instead of
installing a wheel, install `pygame-ce`; it provides the same `pygame` import
used by the runtime:

```powershell
python -m pip install pygame-ce
```

Dependency smoke:

```powershell
python -c "import numpy, pydantic, jsonschema, pygame; print('demo deps ok')"
```

Do not add new runtime dependencies without updating `architecture_decisions.md`
and the relevant contract/test docs.

---

## 22. Risk Register

| Risk | Impact | Mitigation | Gate |
|---|---|---|---|
| Demo docs path drift persists | Tests look in the wrong place or future agents move docs incorrectly | Phase 0 path normalization | schema and architecture tests |
| Pygame leaks into domain/playback/config | Runtime becomes hard to test | Import boundary tests before GUI work | `test_architecture_boundaries.py` |
| Pydantic leaks outside config | Validation rules spread across layers | Import boundary tests | `test_architecture_boundaries.py` |
| JSON Schema used at runtime | Runtime dependency and ownership drift | Keep `jsonschema` in tests/tools only | config/schema tests |
| Final-grid replay order feels arbitrary | Demo looks less solver-like | Deterministic ordering and source label | `test_event_source.py` |
| Large boards overload GUI | Slow or unusable demo | Configurable batching and screen-fit geometry | `test_event_batching.py`, `test_window_geometry.py` |
| Status panel shows placeholders | Demo looks fake | Snapshot/text tests require real values | `test_status_text.py` |
| `run_iter9.py` hook changes existing behavior | Pipeline regression | Hook last and verify omitted-flag behavior | `test_run_iter9_launch_hook.py` |
| LLM creates blob files | Maintenance failure | Source modularity tests and one-responsibility modules | `test_source_file_modularity.py` |

---

## 23. Definition of Ready for a Coding Slice

A slice is ready only when:

- the source contract is named;
- target files are listed;
- forbidden files are listed;
- the owning package is clear;
- the import boundary is known;
- tests exist or will be created first;
- shared fixture/builder/helper needs are identified;
- the exact verification command is known;
- the slice can complete without unrelated root-module changes.

---

## 24. Definition of Done for a Coding Slice

A slice is done only when:

- target tests pass;
- architecture boundary tests pass;
- no forbidden root demo files were created;
- no production module mixes ownership layers;
- error messages include path/field/line information where applicable;
- public APIs match the runtime package contract;
- demo docs or traceability are updated if behavior changed;
- existing non-demo behavior remains unchanged unless explicitly planned.

---

## 25. Final Automated Completion Gate

Before claiming implementation complete:

```powershell
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

Then run at least one standalone manual GUI validation and, if the hook is
implemented, one hook-based manual GUI validation.

Current automated evidence from 2026-05-02:

```text
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py" -> 56 tests passed.
python -m unittest discover -s tests -p "test_*.py" -> 160 tests passed.
python -m compileall -q demos tests/demo tests/__init__.py run_iter9.py -> passed.
python run_iter9.py --help -> passed.
python run_benchmark.py --help -> passed.
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical -> passed.
python -m demos.iter9_visual_solver.cli.commands --help -> passed.
headless standalone pygame launch smoke with temp/demo_contract_smoke -> passed.
headless hook launch smoke with temp/demo_contract_smoke -> passed.
git diff --check over demo/runtime/test surfaces -> passed with line-ending warnings only.
```

Manual GUI review with a human-visible window remains the last non-automated
acceptance item before final demo signoff.

---

## 26. Recommended Checkpoint Sequence

Use focused commits or checkpoints:

```text
1. demo-docs: normalize demo documentation paths
2. demo-tests: harden visual solver architecture and schema gates
3. demo-contracts: add runtime package skeleton and contract constants
4. demo-config: add pydantic config models and default config
5. demo-domain: add board dimensions, events, state, input, and snapshots
6. demo-io: add artifact, grid, metrics, and trace loaders
7. demo-playback: add speed, batching, source, scheduler, replay, and finish policy
8. demo-rendering: add palette, geometry, board, and status helpers
9. demo-pygame: add pygame adapter and fake-tested loop
10. demo-cli: add standalone visual solver demo launcher
11. iter9-hook: add optional thin demo launch hook
12. demo-acceptance: record validation evidence
```

---

## 27. LLM Work-Package Template

Use this shape for each implementation request:

```text
Implement only <slice name> for the Iter9 Visual Solver Demo.

Dedicated demo docs SSOT:
- demo/docs/<contract file>.md
- demo/docs/json_schemas/<schema file> if relevant

Files allowed to edit:
- <exact files>

Files forbidden to edit:
- run_iter9.py unless this is Phase 10
- existing root pipeline modules
- unrelated demo modules

Required tests:
- <exact tests>

Required behavior:
- <specific contract bullets>

Forbidden implementation patterns:
- <boundary bullets>

Run before reporting done:
- python -m unittest <target test>
- python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries

Return:
- changed files
- test results
- any contract ambiguity found
```

---

## 28. Final Implementation Judgment

The correct implementation sequence is:

```text
demo-local docs path normalization
-> architecture gates and scaffold hardening
-> executable constants and default config
-> config models
-> pure domain
-> artifact I/O
-> pygame-free playback
-> rendering helpers
-> pygame adapter and loop
-> standalone CLI
-> optional Iter9 hook
-> manual acceptance evidence
```

This order keeps the visual solver demo a dedicated, modular subproject rather
than a monolithic repository refactor. It also keeps the final GUI work small:
by the time pygame is introduced, artifact loading, config validation, board
dimensions, playback speed, batching, replay state, finish behavior, and status
text are already tested.
