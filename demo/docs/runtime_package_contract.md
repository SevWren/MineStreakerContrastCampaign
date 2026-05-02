# Iter9 Visual Solver Demo — Runtime Package Contract

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Demo architecture |
| Applies to | `demos/iter9_visual_solver/` |
| Required before | Any demo runtime source module |
| Traceability IDs | DEMO-REQ-009, DEMO-REQ-010, DEMO-REQ-013, DEMO-REQ-014 |
| Change rule | New package areas or ownership changes require updating this file, `architecture_decisions.md`, `architecture_boundary_tests.md`, and `traceability_matrix.md`. |

---

## 1. Purpose

This contract defines the runtime package structure, module ownership boundaries, public API expectations, allowed imports, forbidden imports, test ownership, and completion criteria for the Iter9 Visual Solver Demo.

The goal is to make the demo additive and modular without refactoring the existing base project.

---

## 2. Scope

This contract applies to:

```text
demos/iter9_visual_solver/
tests/demo/iter9_visual_solver/
run_iter9.py demo hook only
```

This contract does not authorize a whole-project package refactor.

Existing root modules remain root modules unless a separate approved architecture plan says otherwise.

---

## 3. Runtime Root

All demo runtime code MUST live under:

```text
demos/iter9_visual_solver/
```

Forbidden root files:

```text
demo_config.py
demo_visualizer.py
visual_solver_demo.py
iter9_visual_solver_demo.py
```

---

## 4. Required Package Layout

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
      prompted_launcher.py

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

## 5. `__init__.py` Rules

Each `__init__.py` MUST be minimal.

Allowed:

```python
"""Package docstring."""
```

Allowed only if explicitly needed:

```python
__all__ = [...]
```

Forbidden:

- Importing pygame.
- Loading config.
- Loading artifacts.
- Starting playback.
- Creating windows.
- Exporting broad wildcard APIs.
- Performing filesystem I/O.

Rationale: package imports must be safe and side-effect free.

---

## 6. Package Ownership Matrix

| Package | Owns | Must Not Own | Required Test Coverage |
|---|---|---|---|
| `cli/` | CLI args, command orchestration, thin launch wrappers, prompted launcher delegation | pygame drawing, config validation rules, pixel loops, playback math | `test_cli_args.py`, `test_cli_commands.py`, `test_run_iter9_launch_hook.py`, `test_prompted_launcher.py` |
| `config/` | Pydantic models, config loading, schema export, validation errors | rendering, replay state, artifact parsing, pygame | `test_config_models.py`, `test_config_loader.py`, `test_config_schema_contract.py` |
| `contracts/` | executable constants mirroring accepted docs | runtime behavior, pygame, file loading | `test_artifact_paths.py`, architecture tests |
| `domain/` | pure data models and pure domain calculations | pygame, pydantic, file I/O, JSON loading | `test_board_dimensions.py`, `test_playback_event.py` |
| `io/` | artifact path resolution, grid/metrics/trace/JSON loading/writing | rendering, playback policy math, pygame | `test_artifact_paths.py`, `test_grid_loader.py`, `test_metrics_loader.py`, `test_event_trace_loader.py`, `test_event_trace_writer.py` |
| `playback/` | speed policy, batching, scheduling, replay state, finish policy | pygame, file parsing, config loading | `test_speed_policy.py`, `test_event_batching.py`, `test_event_scheduler.py`, `test_replay_state.py`, `test_finish_policy.py` |
| `rendering/` | color palette, window geometry, board surface, status text/panel, pygame adapter/loop | Pydantic validation, JSON schema validation, raw config loading, artifact parsing | `test_color_palette.py`, `test_window_geometry.py`, `test_board_surface.py`, `test_status_text.py`, `test_status_panel.py`, `test_pygame_adapter_contract.py`, `test_pygame_loop_with_fakes.py` |
| `errors/` | typed exceptions and message helpers | business logic, pygame, config loading | error tests or usage tests |

---

## 7. Module-by-Module Contract

## 7.1 `cli/args.py`

### Purpose

Parse standalone demo CLI arguments.

### Public API

```python
def build_parser() -> argparse.ArgumentParser: ...
def parse_args(argv: list[str] | None = None) -> argparse.Namespace: ...
```

### Required Arguments

```text
--grid
--metrics
--config
```

### Optional Arguments

```text
--event-trace
```

if event trace replay is implemented.

### Forbidden

- pygame imports
- loading grid files
- loading metrics JSON
- calculating playback speed
- drawing GUI

### Tests

```text
test_cli_args.py
```

---

## 7.2 `cli/commands.py`

### Purpose

Standalone command orchestration.

### Public API

```python
def main(argv: list[str] | None = None) -> int: ...
```

### Responsibilities

- Parse args.
- Call config loader.
- Call artifact loaders.
- Build demo input.
- Call high-level pygame loop/orchestrator.

### Forbidden

- Direct pixel drawing.
- Direct pygame display creation.
- Pydantic model definitions.
- Playback speed formula implementation.

### Tests

```text
test_cli_commands.py
```

---

## 7.3 `cli/launch_from_iter9.py`

### Purpose

Thin integration seam called after `run_iter9.py` completes artifact generation.

### Public API

```python
def run_demo_from_completed_iter9_run(
    *,
    grid_path: Path,
    metrics_path: Path,
    config_path: Path,
    event_trace_path: Path | None = None,
) -> int: ...
```

### Forbidden

- pygame imports at module import time.
- Config model definitions.
- Playback math.
- Artifact discovery beyond paths passed in.

### Tests

```text
test_run_iter9_launch_hook.py
```

---

## 7.3.1 `cli/prompted_launcher.py`

### Purpose

Interactive wrapper for launching the demo from a completed Iter9 run directory.

### Public API

```python
def parse_speed_modifier(value: str) -> float: ...
def parse_yes_no(value: str) -> bool: ...
def build_prompted_config_dict(default_config: dict, *, speed_modifier: float, auto_close: bool) -> dict: ...
def build_demo_argv(*, artifacts: DemoArtifactPaths, config_path: Path) -> list[str]: ...
def prompted_main(...) -> int: ...
```

### Required Prompts

```text
completed results/run directory
playback speed modifier such as 50x, 100x, 150x, 200x, or 300x
auto-close on completion, Y/N
```

### Required Behavior

- Resolve `grid_iter9_latest.npy` and `metrics_iter9_<board>.json` through
  `io/artifact_paths.py`.
- Include `solver_event_trace.jsonl` when present.
- Generate a temporary config under `temp/` by copying the default config and
  applying the requested speed modifier and finish behavior.
- Delegate to `cli/commands.py` with explicit `--grid`, `--metrics`,
  `--config`, and optional `--event-trace` arguments.

### Forbidden

- pygame imports.
- Direct pygame display creation.
- Pixel drawing.
- Reimplementing artifact loading.
- Reimplementing the playback speed formula from `speed_policy.py`.

### Tests

```text
test_prompted_launcher.py
```

---

## 7.4 `config/models.py`

### Purpose

Define Pydantic v2 models for demo config.

### Expected Public Models

```python
class DemoConfig(BaseModel): ...
class WindowConfig(BaseModel): ...
class FinishBehaviorConfig(BaseModel): ...
class PlaybackConfig(BaseModel): ...
class VisualsConfig(BaseModel): ...
class StatusPanelConfig(BaseModel): ...
class InputConfig(BaseModel): ...
```

### Forbidden

- pygame imports
- artifact loading
- runtime playback state
- rendering logic

### Tests

```text
test_config_models.py
```

---

## 7.5 `config/loader.py`

### Purpose

Load config JSON file and return a typed `DemoConfig`.

### Public API

```python
def load_demo_config(path: Path) -> DemoConfig: ...
```

### Required Behavior

- Missing file raises typed config error.
- Malformed JSON raises typed config error.
- Invalid fields raise typed config validation error.
- Errors include path and field path where applicable.

### Forbidden

- pygame imports
- playback start
- artifact loading unrelated to config

### Tests

```text
test_config_loader.py
```

---

## 7.6 `config/schema_export.py`

### Purpose

Support schema generation/checking from Pydantic models if the project chooses to generate schema snapshots.

### Public API

```python
def build_config_json_schema() -> dict: ...
```

### Forbidden

- Writing schema files unless explicitly called by a dedicated command/test.
- pygame imports.
- runtime playback.

### Tests

```text
test_config_schema_contract.py
```

---

## 7.7 `config/validation_errors.py`

### Purpose

Define config-specific exceptions and error formatting.

### Expected Exceptions

```python
class DemoConfigError(Exception): ...
class DemoConfigFileNotFoundError(DemoConfigError): ...
class DemoConfigJsonError(DemoConfigError): ...
class DemoConfigValidationError(DemoConfigError): ...
```

### Tests

Covered through:

```text
test_config_loader.py
test_config_models.py
```

---

## 7.8 `contracts/artifact_names.py`

### Purpose

Executable constants for artifact filenames and patterns.

### Expected Constants

```python
GRID_LATEST_FILENAME = "grid_iter9_latest.npy"
EVENT_TRACE_FILENAME = "solver_event_trace.jsonl"
METRICS_FILENAME_PREFIX = "metrics_iter9_"
METRICS_FILENAME_SUFFIX = ".json"
```

### Forbidden

- filesystem scanning
- JSON loading
- pygame imports

### Tests

```text
test_artifact_paths.py
```

---

## 7.9 `contracts/schema_versions.py`

### Purpose

Executable constants for schema version strings.

### Expected Constants

```python
CONFIG_SCHEMA_VERSION = "iter9_visual_solver_demo_config.v1"
EVENT_TRACE_SCHEMA_VERSION = "iter9_visual_solver_event_trace.v1"
```

### Tests

```text
test_config_models.py
test_event_trace_loader.py
```

---

## 7.10 `contracts/defaults.py`

### Purpose

Executable constants for runtime defaults that mirror config/schema docs.

### Expected Constants

```python
DEFAULT_CONFIG_PATH = Path("configs/demo/iter9_visual_solver_demo.default.json")
DEFAULT_FINISH_MODE = "stay_open"
DEFAULT_PLAYBACK_MODE = "mine_count_scaled"
```

### Forbidden

- importing Pydantic
- importing pygame
- reading files

---

## 7.11 `domain/board_dimensions.py`

### Purpose

Pure board dimension model derived from grid shape.

### Public API

```python
@dataclass(frozen=True)
class BoardDimensions:
    width: int
    height: int
    total_cells: int

    @classmethod
    def from_grid(cls, grid: np.ndarray) -> "BoardDimensions": ...
```

### Required Behavior

- `height` is `grid.shape[0]`.
- `width` is `grid.shape[1]`.
- `total_cells = width * height`.
- Reject non-2D grids.

### Forbidden

- pygame
- pathlib/file I/O
- Pydantic

### Tests

```text
test_board_dimensions.py
```

---

## 7.12 `domain/board_state.py`

### Purpose

Represent in-memory board display state independent of pygame.

### Expected API

```python
@dataclass
class BoardState:
    dimensions: BoardDimensions
    ...
```

### Forbidden

- pygame surfaces
- artifact loading

### Tests

```text
test_replay_state.py
test_board_surface.py
```

---

## 7.13 `domain/playback_event.py`

### Purpose

Typed playback event model.

### Expected API

```python
@dataclass(frozen=True)
class PlaybackEvent:
    step: int
    y: int
    x: int
    state: str
    display: str
    source: str | None = None
```

### Valid States

```text
SAFE
MINE
UNKNOWN
```

### Valid Displays

```text
flag
reveal
unknown
```

### Tests

```text
test_playback_event.py
test_event_trace_loader.py
```

---

## 7.14 `domain/demo_input.py`

### Purpose

Aggregate validated demo inputs after config and artifact loading.

### Expected API

```python
@dataclass(frozen=True)
class DemoInput:
    config: DemoConfig
    grid: np.ndarray
    metrics: dict
    board_dimensions: BoardDimensions
    events: list[PlaybackEvent]
    replay_source: str
    artifact_paths: DemoArtifactPaths
```

### Forbidden

- loading files
- pygame

---

## 7.15 `domain/status_snapshot.py`

### Purpose

Represent status panel values without formatting or drawing.

### Expected API

```python
@dataclass(frozen=True)
class StatusSnapshot:
    source_image_name: str
    board_width: int
    board_height: int
    seed: int
    total_cells: int
    mines_flagged: int
    total_mines: int
    safe_cells_solved: int
    unknown_remaining: int
    playback_speed: int
    finish_state: str
```

### Tests

```text
test_status_text.py
test_replay_state.py
```

---

## 7.16 `io/artifact_paths.py`

### Purpose

Resolve and validate artifact paths.

### Public API

```python
@dataclass(frozen=True)
class DemoArtifactPaths:
    run_dir: Path
    grid_path: Path
    metrics_path: Path
    event_trace_path: Path | None

def metrics_filename_for_board(board_label: str) -> str: ...
def resolve_artifact_paths(
    *,
    run_dir: Path,
    board_label: str | None = None,
    grid_path: Path | None = None,
    metrics_path: Path | None = None,
    event_trace_path: Path | None = None,
) -> DemoArtifactPaths: ...
```

### Forbidden

- pygame
- playback math
- reading artifact contents

### Tests

```text
test_artifact_paths.py
```

---

## 7.17 `io/grid_loader.py`

### Purpose

Load `.npy` grid artifact.

### Public API

```python
def load_grid(path: Path) -> np.ndarray: ...
```

### Required Behavior

- Missing file raises artifact error.
- Invalid `.npy` raises artifact error.
- Non-2D grid rejected.
- Shape preserved.

### Forbidden

- pygame
- window sizing
- playback event generation

### Tests

```text
test_grid_loader.py
```

---

## 7.18 `io/metrics_loader.py`

### Purpose

Load metrics JSON artifact.

### Public API

```python
def load_metrics(path: Path) -> dict: ...
```

### Required Behavior

- Missing file raises artifact error.
- Malformed JSON raises artifact error.
- Required fields validated according to artifact contract.

### Forbidden

- status text formatting
- playback speed
- pygame

### Tests

```text
test_metrics_loader.py
```

---

## 7.19 `io/event_trace_loader.py`

### Purpose

Load solver event trace JSONL.

### Public API

```python
def load_event_trace(path: Path) -> list[PlaybackEvent]: ...
```

### Required Behavior

- One JSON object per line.
- Convert rows to `PlaybackEvent`.
- Reject invalid state/display/missing fields.
- Preserve order.

### Tests

```text
test_event_trace_loader.py
```

---

## 7.20 `io/event_trace_writer.py`

### Purpose

Write solver event trace JSONL.

### Public API

```python
def write_event_trace(events: Iterable[PlaybackEvent], path: Path) -> None: ...
```

### Tests

```text
test_event_trace_writer.py
```

---

## 7.21 `io/json_reader.py`

### Purpose

Centralize JSON file reading and JSON parse errors.

### Public API

```python
def read_json_object(path: Path) -> dict: ...
```

### Forbidden

- config-specific validation
- pygame
- playback

---

## 7.22 `playback/speed_policy.py`

### Purpose

Calculate events per second from validated config.

### Public API

```python
def calculate_events_per_second(
    playback_config: PlaybackConfig,
    *,
    total_mines: int,
) -> int: ...
```

### Formula

```text
base_events_per_second + total_mines * mine_count_multiplier
```

then clamp to min/max.

### Forbidden

- pygame
- file I/O
- config loading

### Tests

```text
test_speed_policy.py
```

---

## 7.23 `playback/event_source.py`

### Purpose

Choose final-grid replay or solver trace replay.

### Public API

```python
def build_playback_events_from_final_grid(grid: np.ndarray) -> list[PlaybackEvent]: ...
def select_event_source(
    *,
    input_config: InputConfig,
    grid: np.ndarray,
    trace_events: list[PlaybackEvent] | None,
) -> tuple[list[PlaybackEvent], str]: ...
```

### Tests

```text
test_event_trace_loader.py
test_event_source.py
test_replay_state.py
```

---

## 7.24 `playback/event_batching.py`

### Purpose

Convert speed, FPS, and the validated `playback.batch_events_per_frame` boolean into frame batch sizes.

### Public API

```python
def calculate_events_per_frame(
    *,
    events_per_second: int,
    target_fps: int,
    batch_events_per_frame: bool,
) -> int: ...
```

### Tests

```text
test_event_batching.py
```

---

## 7.25 `playback/event_scheduler.py`

### Purpose

Return ordered event batches.

### Expected API

```python
class EventScheduler:
    def next_batch(self) -> list[PlaybackEvent]: ...
    @property
    def finished(self) -> bool: ...
```

### Tests

```text
test_event_scheduler.py
```

---

## 7.26 `playback/replay_state.py`

### Purpose

Track applied events and status counters.

### Expected API

```python
class ReplayState:
    def apply(event: PlaybackEvent) -> None: ...
    def snapshot() -> StatusSnapshot: ...
```

### Tests

```text
test_replay_state.py
```

---

## 7.27 `playback/finish_policy.py`

### Purpose

Determine whether GUI should auto-close after playback finishes.

### Public API

```python
def should_auto_close(finish_config: FinishBehaviorConfig, elapsed_after_finish_s: float) -> bool: ...
```

### Tests

```text
test_finish_policy.py
```

---

## 7.28 `rendering/color_palette.py`

### Purpose

Convert validated visual config to color values.

### Expected API

```python
@dataclass(frozen=True)
class ColorPalette:
    ...
    @classmethod
    def from_config(cls, visuals: VisualsConfig) -> "ColorPalette": ...
```

### Tests

```text
test_color_palette.py
```

---

## 7.29 `rendering/window_geometry.py`

### Purpose

Calculate display/window dimensions without opening pygame.

### Public API

```python
def calculate_window_geometry(
    *,
    board_width: int,
    board_height: int,
    status_panel_width_px: int,
    preferred_board_cell_px: int,
    minimum_board_cell_px: int,
    max_screen_fraction: float,
    screen_width_px: int | None = None,
    screen_height_px: int | None = None,
) -> WindowGeometry: ...
```

### Tests

```text
test_window_geometry.py
```

---

## 7.30 `rendering/board_surface.py`

### Purpose

Map board state/events to drawable board surface data.

### Forbidden

- config loading
- metrics loading
- playback speed calculation

### Tests

```text
test_board_surface.py
```

---

## 7.31 `rendering/status_text.py`

### Purpose

Format `StatusSnapshot` into display lines.

### Public API

```python
def build_status_lines(snapshot: StatusSnapshot) -> list[str]: ...
```

### Tests

```text
test_status_text.py
```

---

## 7.32 `rendering/status_panel.py`

### Purpose

Draw provided status lines onto a surface.

### Forbidden

- metrics parsing
- status calculation
- playback policy math

### Tests

```text
test_status_panel.py
```

---

## 7.33 `rendering/pygame_adapter.py`

### Purpose

Wrap pygame primitives for injection and fake testing.

### Expected API

```python
class PygameAdapter:
    def open_window(self, width: int, height: int, title: str): ...
    def poll_events(self): ...
    def tick(self, fps: int): ...
    def flip(self): ...
    def close(self): ...
```

### Tests

```text
test_pygame_adapter_contract.py
```

---

## 7.34 `rendering/pygame_loop.py`

### Purpose

Imperative shell that runs the demo frame loop.

### Required Behavior

- Uses injected adapter or pygame module.
- Applies scheduled event batches.
- Draws board/status using rendering helpers.
- Honors finish policy.
- Exits on close event.

### Forbidden

- config validation
- artifact loading
- playback speed formula
- metrics parsing

### Tests

```text
test_pygame_loop_with_fakes.py
test_architecture_boundaries.py
```

---

## 8. Import Boundary Matrix

| Package | Allowed Imports | Forbidden Imports |
|---|---|---|
| `cli/` | argparse, pathlib, high-level demo APIs | pygame, pydantic model definitions, pixel loops |
| `config/` | pydantic, json, pathlib, config errors | pygame, rendering, playback state |
| `contracts/` | constants, pathlib for default paths if needed | pygame, pydantic, runtime modules |
| `domain/` | dataclasses, enum, typing, NumPy only if needed | pygame, pydantic, pathlib/file I/O |
| `io/` | json, pathlib, NumPy, domain models | pygame, rendering modules, playback policy math |
| `playback/` | domain models, config models/types | pygame, pathlib/file I/O, json loading |
| `rendering/` | pygame, NumPy, domain snapshots/events, playback state values | pydantic, jsonschema, raw config loader |
| `errors/` | stdlib only | pygame, pydantic unless config-specific error module explicitly needs it |

---

## 9. Test Ownership Matrix

| Runtime Module | Primary Test File |
|---|---|
| `cli/args.py` | `test_cli_args.py` |
| `cli/commands.py` | `test_cli_commands.py` |
| `cli/launch_from_iter9.py` | `test_run_iter9_launch_hook.py` |
| `cli/prompted_launcher.py` | `test_prompted_launcher.py` |
| `config/models.py` | `test_config_models.py` |
| `config/loader.py` | `test_config_loader.py` |
| `config/schema_export.py` | `test_config_schema_contract.py` |
| `contracts/artifact_names.py` | `test_artifact_paths.py` |
| `contracts/schema_versions.py` | `test_config_models.py`, `test_event_trace_loader.py` |
| `domain/board_dimensions.py` | `test_board_dimensions.py` |
| `domain/playback_event.py` | `test_playback_event.py` |
| `io/artifact_paths.py` | `test_artifact_paths.py` |
| `io/grid_loader.py` | `test_grid_loader.py` |
| `io/metrics_loader.py` | `test_metrics_loader.py` |
| `io/event_trace_loader.py` | `test_event_trace_loader.py` |
| `io/event_trace_writer.py` | `test_event_trace_writer.py` |
| `playback/speed_policy.py` | `test_speed_policy.py` |
| `playback/event_batching.py` | `test_event_batching.py` |
| `playback/event_scheduler.py` | `test_event_scheduler.py` |
| `playback/replay_state.py` | `test_replay_state.py` |
| `playback/finish_policy.py` | `test_finish_policy.py` |
| `rendering/color_palette.py` | `test_color_palette.py` |
| `rendering/window_geometry.py` | `test_window_geometry.py` |
| `rendering/board_surface.py` | `test_board_surface.py` |
| `rendering/status_text.py` | `test_status_text.py` |
| `rendering/status_panel.py` | `test_status_panel.py` |
| `rendering/pygame_adapter.py` | `test_pygame_adapter_contract.py` |
| `rendering/pygame_loop.py` | `test_pygame_loop_with_fakes.py` |

---

## 10. Completion Checklist

- [ ] Runtime package exists under `demos/iter9_visual_solver/`.
- [ ] No forbidden root demo files exist.
- [ ] All required package directories exist.
- [ ] `__init__.py` files are side-effect free.
- [ ] Every required runtime module has a contract.
- [ ] Every runtime module has a primary test file.
- [ ] Import boundary tests pass.
- [ ] `run_iter9.py` hook is thin and optional.
- [ ] Existing base project root modules are not refactored by demo work.
