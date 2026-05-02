# Iter9 Visual Solver Demo — Industry Standard Execution Plan

## 0. Execution Plan Status

| Field | Value |
|---|---|
| Plan status | Executed for standalone MVP runtime on 2026-05-02 |
| Execution style | Test-first, contract-first, small work packages |
| Primary output | Working demo code under `demos/iter9_visual_solver/` |
| Secondary output | Passing architecture, unit, schema, CLI smoke, and pygame launch-smoke gates |
| Optimized for | LLM-assisted development with strict sequencing and verification |

This execution plan converted the implementation plan into exact coding work
packages. The standalone runtime package, default config, schema/config tests,
architecture gates, playback core, rendering seams, and CLI surface have been
implemented. The optional `run_iter9.py` flag integration is wired through a
thin launch seam and does not import pygame from `run_iter9.py`.

### 0.1 Execution Evidence

Validated on 2026-05-02:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_run_iter9_launch_hook
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
python -m unittest discover -s tests -p "test_*.py"
python -m compileall -q demos tests/demo tests/__init__.py run_iter9.py
python -c "import pygame; print('pygame import ok', pygame.version.ver)"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
python -m demos.iter9_visual_solver.cli.commands --help
$env:SDL_VIDEODRIVER='dummy'; python -m demos.iter9_visual_solver.cli.commands --grid temp/demo_contract_smoke/grid_iter9_latest.npy --metrics temp/demo_contract_smoke/metrics_iter9_3x2.json --config temp/demo_contract_smoke/demo_close_immediately.json
$env:SDL_VIDEODRIVER='dummy'; @'
from pathlib import Path
from demos.iter9_visual_solver.cli.launch_from_iter9 import run_demo_from_completed_iter9_run
raise SystemExit(run_demo_from_completed_iter9_run(
    grid_path=Path('temp/demo_contract_smoke/grid_iter9_latest.npy'),
    metrics_path=Path('temp/demo_contract_smoke/metrics_iter9_3x2.json'),
    config_path=Path('temp/demo_contract_smoke/demo_close_immediately.json'),
))
'@ | python -
git diff --check -- .gitignore demo tests/demo demos configs tests/__init__.py run_iter9.py
```

Results:

```text
run_iter9 hook delegation test: 3 tests passed.
Demo test suite: 60 tests passed.
Full repository unittest discovery: 164 tests passed.
Compileall gate: passed.
Entrypoint help commands: passed.
Image guard smoke: passed.
Demo CLI help: passed.
pygame import: passed with pygame-ce 2.5.7 providing the pygame module.
Headless standalone pygame launch smoke: passed against temp/demo_contract_smoke artifacts.
Headless hook launch smoke: passed against temp/demo_contract_smoke artifacts.
Headless prompted wrapper smoke: passed against results/iter9/line_art_a2_w300_demo_s42.
Whitespace/diff check: passed with line-ending warnings only for AGENTS.md and run_iter9.py.
```

The package name `pygame` did not provide a Python 3.14 wheel in this
environment and attempted a failing source build. `pygame-ce` was installed
instead; it provides the `pygame` import used by the runtime. Unit coverage uses
fake pygame seams, and the standalone CLI plus hook seam were smoke-tested with
real pygame initialization against tiny `temp/demo_contract_smoke` artifacts.

The latest continuation strengthened contract adherence beyond module
existence checks:

- final-grid replay now emits deterministic row-major cell events for both mine
  and safe cells so replay/status counters can complete;
- event batching uses ceiling division and the CLI passes `events_per_frame`
  into the pygame loop instead of losing the calculated value;
- the pygame loop applies scheduler batches, updates replay/status state,
  renders board/status surfaces, honors finish behavior, and returns structured
  exit evidence;
- the standalone CLI now passes grid dimensions, source image name, seed,
  replay source, finish config, status config, color palette, geometry, and
  playback speed into the rendering loop;
- tests now cover CLI-to-loop wiring, fake pygame finish behavior, board color
  mapping, status wording, batching, and final-grid event generation.

---

## 1. Global Execution Rules

### 1.1 Work one slice at a time

Do not ask the coding agent to implement multiple layers at once. A valid task modifies one bounded group, such as:

```text
contracts constants only
config models only
grid loader only
speed policy only
window geometry only
pygame loop with fakes only
```

### 1.2 Tests before or with code

For every runtime module:

1. Create or update the test first.
2. Implement only enough code to pass the test.
3. Run the exact slice test.
4. Run architecture tests.
5. Commit or checkpoint.

### 1.3 No cross-layer shortcuts

Forbidden shortcuts:

- Calculating speed inside `pygame_loop.py`.
- Loading `.npy` files inside rendering modules.
- Parsing config inside playback or rendering modules.
- Importing pygame in domain/playback/io/config modules.
- Importing Pydantic in domain/io/playback/rendering modules.
- Modifying `run_iter9.py` before standalone CLI works.

### 1.4 Use stable commands after every slice

Minimum per-slice verification:

```powershell
python -m unittest tests.demo.iter9_visual_solver.<target_test_module>
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

After every milestone:

```powershell
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
```

After integration changes:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
```

---

## 2. Pre-Coding Setup

### Task 0.1 — Create a clean branch

**Action:**

```powershell
git checkout -b demo/iter9-visual-solver
```

**Done when:**

- Branch exists.
- Working tree starts from a known state.

---

### Task 0.2 — Install required demo dependencies

**Action:**

```powershell
python -m pip install numpy pydantic jsonschema pygame
```

On Python 3.14, if the `pygame` package attempts a source build instead of
installing a wheel, install the compatible provider:

```powershell
python -m pip install pygame-ce
```

**Done when:**

```powershell
python -c "import numpy, pydantic, jsonschema, pygame; print('demo deps ok')"
```

---

### Task 0.3 — Baseline existing behavior

**Action:**

```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
```

**Done when:**

- Existing tests pass or known pre-existing failures are documented before demo changes.
- Help commands still work.

---

## 3. Milestone 1 — Test Infrastructure and Architecture Gates

### Task 1.1 — Create demo test package skeleton

**Create:**

```text
tests/demo/__init__.py
tests/demo/iter9_visual_solver/__init__.py
tests/demo/iter9_visual_solver/fixtures/__init__.py
tests/demo/iter9_visual_solver/builders/__init__.py
tests/demo/iter9_visual_solver/helpers/__init__.py
```

**Acceptance command:**

```powershell
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
```

---

### Task 1.2 — Add shared test fixtures

**Create:**

```text
tests/demo/iter9_visual_solver/fixtures/configs.py
tests/demo/iter9_visual_solver/fixtures/grids.py
tests/demo/iter9_visual_solver/fixtures/metrics.py
tests/demo/iter9_visual_solver/fixtures/event_traces.py
tests/demo/iter9_visual_solver/fixtures/temp_runs.py
tests/demo/iter9_visual_solver/fixtures/pygame_fakes.py
```

**Required fixture content:**

- Minimal valid config dictionary.
- Small grid arrays such as `2x2`, `3x3`, and non-square grids.
- Minimal metrics dictionary with source image, seed, board, and solver counts.
- Valid and invalid event trace rows.
- Temp run directory builder that writes grid and metrics files.
- Pygame fake adapter with event queue, draw-call log, tick log, and close flag.

**Acceptance command:**

```powershell
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
```

---

### Task 1.3 — Add shared builders

**Create:**

```text
tests/demo/iter9_visual_solver/builders/config_builder.py
tests/demo/iter9_visual_solver/builders/grid_builder.py
tests/demo/iter9_visual_solver/builders/metrics_builder.py
tests/demo/iter9_visual_solver/builders/event_trace_builder.py
tests/demo/iter9_visual_solver/builders/status_snapshot_builder.py
```

**Required builder behavior:**

- Defaults produce valid objects/dicts.
- Each builder has `with_*` methods for targeted overrides.
- Builders avoid copy-pasted setup in test files.

**Acceptance command:**

```powershell
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
```

---

### Task 1.4 — Add shared test helpers

**Create:**

```text
tests/demo/iter9_visual_solver/helpers/assertions.py
tests/demo/iter9_visual_solver/helpers/schema_assertions.py
tests/demo/iter9_visual_solver/helpers/filesystem_assertions.py
tests/demo/iter9_visual_solver/helpers/import_boundary_assertions.py
tests/demo/iter9_visual_solver/helpers/pygame_assertions.py
```

**Required helper behavior:**

- Assert exact status lines.
- Assert schema accepts/rejects examples.
- Assert no forbidden files exist.
- Parse Python imports with `ast`.
- Assert fake pygame adapter calls.

---

### Task 1.5 — Implement architecture boundary tests

**Create:**

```text
tests/demo/iter9_visual_solver/test_architecture_boundaries.py
tests/demo/iter9_visual_solver/test_source_file_modularity.py
```

**Test requirements:**

- No forbidden root demo files.
- Runtime package exists once implementation starts.
- Pygame import isolation.
- Pydantic import isolation.
- jsonschema excluded from runtime modules.
- Domain purity.
- Playback isolation from pygame and file I/O.
- Rendering does not validate config or load raw artifacts.
- CLI does not draw pixels.
- `run_iter9.py` hook does not import pygame.
- Demo schema docs are not mixed into base schema docs.
- Tests use fixtures/builders/helpers.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
python -m unittest tests.demo.iter9_visual_solver.test_source_file_modularity
```

---

## 4. Milestone 2 — Runtime Package Skeleton and Executable Contracts

### Task 2.1 — Create runtime package skeleton

**Create:**

```text
demos/__init__.py
demos/iter9_visual_solver/__init__.py
demos/iter9_visual_solver/cli/__init__.py
demos/iter9_visual_solver/config/__init__.py
demos/iter9_visual_solver/contracts/__init__.py
demos/iter9_visual_solver/domain/__init__.py
demos/iter9_visual_solver/io/__init__.py
demos/iter9_visual_solver/playback/__init__.py
demos/iter9_visual_solver/rendering/__init__.py
demos/iter9_visual_solver/errors/__init__.py
```

**Rule:**

All `__init__.py` files must be side-effect free.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

### Task 2.2 — Implement contract constants

**Create:**

```text
demos/iter9_visual_solver/contracts/artifact_names.py
demos/iter9_visual_solver/contracts/schema_versions.py
demos/iter9_visual_solver/contracts/defaults.py
```

**Expected constants:**

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

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_artifact_paths
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 5. Milestone 3 — Config Models and Config Loading

### Task 3.1 — Implement typed config errors

**Create:**

```text
demos/iter9_visual_solver/config/validation_errors.py
demos/iter9_visual_solver/errors/config_errors.py
```

**Expected exceptions:**

```python
class DemoConfigError(Exception): ...
class DemoConfigFileNotFoundError(DemoConfigError): ...
class DemoConfigJsonError(DemoConfigError): ...
class DemoConfigValidationError(DemoConfigError): ...
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_loader
```

---

### Task 3.2 — Implement Pydantic config models

**Create:**

```text
demos/iter9_visual_solver/config/models.py
```

**Required models:**

```text
DemoConfig
WindowConfig
FinishBehaviorConfig
PlaybackConfig
VisualsConfig
StatusPanelConfig
InputConfig
```

**Required validation:**

- `schema_version` equals `iter9_visual_solver_demo_config.v1`.
- `window.finish_behavior.mode` is one of `stay_open`, `close_immediately`, `close_after_delay`.
- `window.finish_behavior.close_after_seconds >= 0`.
- `playback.mode` is `mine_count_scaled`.
- playback numeric rates are positive and ordered correctly.
- `playback.batch_events_per_frame` is boolean.
- RGB values are arrays/tuples of three integers from `0` to `255`.
- Unknown fields are rejected.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_models
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

### Task 3.3 — Implement config loader

**Create:**

```text
demos/iter9_visual_solver/config/loader.py
```

**API:**

```python
def load_demo_config(path: Path) -> DemoConfig: ...
```

**Behavior:**

- Missing file raises `DemoConfigFileNotFoundError`.
- Malformed JSON raises `DemoConfigJsonError`.
- Pydantic validation failures raise `DemoConfigValidationError`.
- Error text includes the config path and field path when available.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_loader
```

---

### Task 3.4 — Add default config file

**Create:**

```text
configs/demo/iter9_visual_solver_demo.default.json
```

**Required default behavior:**

- finish mode: `stay_open`
- playback mode: `mine_count_scaled`
- status panel enabled by default
- final-grid replay fallback enabled by default
- solver event trace preferred when present

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_loader
```

---

### Task 3.5 — Implement config schema export/drift tests

**Create:**

```text
demos/iter9_visual_solver/config/schema_export.py
```

**API:**

```python
def build_config_json_schema() -> dict: ...
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_schema_contract
```

---

## 6. Milestone 4 — Domain Layer

### Task 4.1 — Implement board dimensions

**Create:**

```text
demos/iter9_visual_solver/domain/board_dimensions.py
```

**API:**

```python
@dataclass(frozen=True)
class BoardDimensions:
    width: int
    height: int
    total_cells: int

    @classmethod
    def from_grid(cls, grid: np.ndarray) -> "BoardDimensions": ...
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_board_dimensions
```

---

### Task 4.2 — Implement playback event model

**Create:**

```text
demos/iter9_visual_solver/domain/playback_event.py
```

**API:**

```python
@dataclass(frozen=True)
class PlaybackEvent:
    event_id: str
    step: int
    round: int
    y: int
    x: int
    state: str
    display: str
    source: str | None = None
    confidence: float | None = None
    reason: str | None = None
```

**Rules:**

- `step >= 0`.
- `y >= 0`, `x >= 0`.
- `state` in `SAFE`, `MINE`, `UNKNOWN`.
- `display` in `reveal`, `flag`, `unknown`.
- `state=MINE` pairs with `display=flag`.
- `state=SAFE` pairs with `display=reveal`.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_playback_event
```

---

### Task 4.3 — Implement board state, demo input, and status snapshot

**Create:**

```text
demos/iter9_visual_solver/domain/board_state.py
demos/iter9_visual_solver/domain/demo_input.py
demos/iter9_visual_solver/domain/status_snapshot.py
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_replay_state
python -m unittest tests.demo.iter9_visual_solver.test_status_text
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 7. Milestone 5 — Artifact I/O

### Task 5.1 — Implement artifact and trace errors

**Create:**

```text
demos/iter9_visual_solver/errors/artifact_errors.py
demos/iter9_visual_solver/errors/trace_errors.py
```

**Expected behavior:**

- Errors include path.
- Trace errors include line number and field path when applicable.

---

### Task 5.2 — Implement JSON reader

**Create:**

```text
demos/iter9_visual_solver/io/json_reader.py
```

**API:**

```python
def read_json_object(path: Path) -> dict: ...
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_metrics_loader
```

---

### Task 5.3 — Implement artifact paths

**Create:**

```text
demos/iter9_visual_solver/io/artifact_paths.py
```

**API:**

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

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_artifact_paths
```

---

### Task 5.4 — Implement grid loader

**Create:**

```text
demos/iter9_visual_solver/io/grid_loader.py
```

**API:**

```python
def load_grid(path: Path) -> np.ndarray: ...
```

**Rules:**

- Use `np.load`.
- Reject missing/invalid files.
- Reject non-2D arrays.
- Preserve shape and dtype unless explicit conversion is documented.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_grid_loader
```

---

### Task 5.5 — Implement metrics loader

**Create:**

```text
demos/iter9_visual_solver/io/metrics_loader.py
```

**Required fields for MVP display:**

```text
board
seed
source_image.name or image_name
n_unknown
mine_density or total mine count derivable from grid
coverage
solvable
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_metrics_loader
```

---

### Task 5.6 — Implement event trace loader/writer

**Create:**

```text
demos/iter9_visual_solver/io/event_trace_loader.py
demos/iter9_visual_solver/io/event_trace_writer.py
```

**Rules:**

- JSONL one object per line.
- Validate required event fields.
- Preserve order.
- Reject invalid schema versions.
- Reject state/display mismatch.
- Writer emits rows that loader can read back.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_event_trace_loader
python -m unittest tests.demo.iter9_visual_solver.test_event_trace_writer
```

---

## 8. Milestone 6 — Playback Core

### Task 6.1 — Implement speed policy

**Create:**

```text
demos/iter9_visual_solver/playback/speed_policy.py
```

**API:**

```python
def calculate_events_per_second(playback_config: PlaybackConfig, *, total_mines: int) -> int: ...
```

**Formula:**

```text
base_events_per_second + total_mines * mine_count_multiplier
```

Then clamp to min/max.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_speed_policy
```

---

### Task 6.2 — Implement event source selection

**Create:**

```text
demos/iter9_visual_solver/playback/event_source.py
```

**APIs:**

```python
def build_playback_events_from_final_grid(grid: np.ndarray) -> list[PlaybackEvent]: ...
def select_event_source(*, input_config: InputConfig, grid: np.ndarray, trace_events: list[PlaybackEvent] | None) -> tuple[list[PlaybackEvent], str]: ...
```

**Rules:**

- Prefer trace when enabled and trace is present.
- Use final-grid replay when fallback enabled.
- Reject missing trace if trace is required and fallback disabled.
- Final-grid replay should generate deterministic mine-flag events.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_event_source
```

---

### Task 6.3 — Implement event batching

**Create:**

```text
demos/iter9_visual_solver/playback/event_batching.py
```

**API:**

```python
def calculate_events_per_frame(*, events_per_second: int, target_fps: int, batch_events_per_frame: bool) -> int: ...
```

**Rules:**

- If batching disabled, return `1`.
- If batching enabled, return at least `1`.
- Use deterministic rounding policy and test edge cases.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_event_batching
```

---

### Task 6.4 — Implement event scheduler

**Create:**

```text
demos/iter9_visual_solver/playback/event_scheduler.py
```

**Expected API:**

```python
class EventScheduler:
    def next_batch(self) -> list[PlaybackEvent]: ...
    @property
    def finished(self) -> bool: ...
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_event_scheduler
```

---

### Task 6.5 — Implement replay state

**Create:**

```text
demos/iter9_visual_solver/playback/replay_state.py
```

**Expected API:**

```python
class ReplayState:
    def apply(self, event: PlaybackEvent) -> None: ...
    def snapshot(self) -> StatusSnapshot: ...
```

**Rules:**

- Apply each event once.
- Track mines flagged, safe cells solved, unknown remaining.
- Final state after all final-grid events equals grid mine positions.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_replay_state
```

---

### Task 6.6 — Implement finish policy

**Create:**

```text
demos/iter9_visual_solver/playback/finish_policy.py
```

**API:**

```python
def should_auto_close(finish_config: FinishBehaviorConfig, elapsed_after_finish_s: float) -> bool: ...
```

**Rules:**

- `stay_open` never auto-closes.
- `close_immediately` auto-closes immediately.
- `close_after_delay` auto-closes when elapsed is greater than or equal to `close_after_seconds`.
- `close_after_seconds = 0` is valid and means close as soon as playback is finished.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_finish_policy
```

---

## 9. Milestone 7 — Rendering Helpers

### Task 7.1 — Implement color palette

**Create:**

```text
demos/iter9_visual_solver/rendering/color_palette.py
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_color_palette
```

---

### Task 7.2 — Implement window geometry

**Create:**

```text
demos/iter9_visual_solver/rendering/window_geometry.py
```

**Rules:**

- Use board width/height from `BoardDimensions`.
- Respect preferred cell size when screen allows.
- Respect minimum cell size.
- Respect `max_screen_fraction`.
- Include status panel width when status panel is visible.
- Do not crop board for MVP.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_window_geometry
```

---

### Task 7.3 — Implement board surface model/drawing helper

**Create:**

```text
demos/iter9_visual_solver/rendering/board_surface.py
```

**Rules:**

- Convert board state to drawable cell rectangles/colors.
- Do not load files.
- Do not calculate playback speed.
- Do not parse config.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_board_surface
```

---

### Task 7.4 — Implement status text formatting

**Create:**

```text
demos/iter9_visual_solver/rendering/status_text.py
```

**API:**

```python
def build_status_lines(snapshot: StatusSnapshot) -> list[str]: ...
```

**Required visible lines:**

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

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_status_text
```

---

### Task 7.5 — Implement status panel drawing helper

**Create:**

```text
demos/iter9_visual_solver/rendering/status_panel.py
```

**Rules:**

- Accept already-formatted status lines.
- Draw onto supplied surface/adapter abstraction.
- Do not calculate status values.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_status_panel
```

---

## 10. Milestone 8 — Pygame Adapter and Loop

### Task 8.1 — Implement pygame adapter

**Create:**

```text
demos/iter9_visual_solver/rendering/pygame_adapter.py
```

**Expected API:**

```python
class PygameAdapter:
    def open_window(self, width: int, height: int, title: str): ...
    def poll_events(self): ...
    def tick(self, fps: int): ...
    def flip(self): ...
    def close(self): ...
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_pygame_adapter_contract
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

### Task 8.2 — Implement pygame loop with fake adapter tests

**Create:**

```text
demos/iter9_visual_solver/rendering/pygame_loop.py
```

**Rules:**

- Use injected adapter in tests.
- Apply scheduler batches.
- Draw board and status.
- Honor finish policy.
- Exit on OS close event.
- Do not parse config.
- Do not load artifacts.
- Do not calculate speed formula.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 11. Milestone 9 — Standalone CLI

### Task 9.1 — Implement CLI args

**Create:**

```text
demos/iter9_visual_solver/cli/args.py
```

**API:**

```python
def build_parser() -> argparse.ArgumentParser: ...
def parse_args(argv: list[str] | None = None) -> argparse.Namespace: ...
```

**Required args:**

```text
--grid
--metrics
--config
```

**Optional args:**

```text
--event-trace
```

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_cli_args
```

---

### Task 9.2 — Implement CLI orchestration

**Create:**

```text
demos/iter9_visual_solver/cli/commands.py
```

**API:**

```python
def main(argv: list[str] | None = None) -> int: ...
```

**Orchestration sequence:**

1. Parse CLI args.
2. Load config.
3. Load grid.
4. Load metrics.
5. Load event trace if supplied.
6. Derive board dimensions.
7. Build or select playback events.
8. Calculate speed and batching.
9. Build replay state and scheduler.
10. Calculate window geometry.
11. Launch pygame loop.
12. Return process code.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_cli_commands
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

---

## 12. Milestone 10 — Optional `run_iter9.py` Hook

### Task 10.1 — Implement launch-from-Iter9 seam

**Create:**

```text
demos/iter9_visual_solver/cli/launch_from_iter9.py
```

**API:**

```python
def run_demo_from_completed_iter9_run(
    *,
    grid_path: Path,
    metrics_path: Path,
    config_path: Path,
    event_trace_path: Path | None = None,
) -> int: ...
```

**Rules:**

- No pygame imports at module import time.
- No artifact discovery beyond paths passed in.
- Delegate to CLI/orchestration code.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_run_iter9_launch_hook
```

---

### Task 10.2 — Add thin optional flags to `run_iter9.py`

**Modify:**

```text
run_iter9.py
```

**Add:**

```text
--demo-gui
--demo-config
```

**Rules:**

- When `--demo-gui` is omitted, existing behavior is unchanged.
- `run_iter9.py` must not import pygame.
- Hook runs only after artifacts are successfully written.
- Hook passes exact completed grid/metrics/config paths.

**Acceptance command:**

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_run_iter9_launch_hook
python run_iter9.py --help
python run_benchmark.py --help
python -m unittest discover -s tests -p "test_*.py"
```

---

## 13. Milestone 11 — Manual Demo Validation

### Task 11.1 — Generate or locate a completed Iter9 run

Use an existing completed run if available. Otherwise run a small validated run.

**Preferred manual command:**

```powershell
python run_iter9.py --image assets/line_art_irl_11_v2.png --board-w 300 --seed 11 --allow-noncanonical --run-tag "demo_manual_validation"
```

---

### Task 11.2 — Launch standalone demo CLI

**Command:**

```powershell
python -m demos.iter9_visual_solver.cli.commands --grid results/iter9/<run_id>/grid_iter9_latest.npy --metrics results/iter9/<run_id>/metrics_iter9_<board>.json --config configs/demo/iter9_visual_solver_demo.default.json
```

**Prompted wrapper command:**

```powershell
.\demo\run_iter9_visual_solver_demo_prompted.ps1
```

The prompted wrapper asks for a completed results directory, a playback speed
modifier such as `50x`, `100x`, `150x`, `200x`, or `300x`, and whether the demo
should automatically close when playback finishes. It writes the generated
config under `temp/` and delegates to the standalone demo CLI with explicit
artifact paths.

**Pass checklist:**

- Window opens.
- Board appears with correct aspect ratio.
- Status panel shows source image, board dimensions, seed, total cells, mines flagged, safe solved, unknown remaining, playback speed, elapsed time, finish state.
- No placeholder text appears.
- Mines reveal/flag over time.
- Playback completes without dropping events.
- Final board state matches final grid.
- Configured finish behavior is honored.
- OS window close exits cleanly.

---

### Task 11.3 — Launch from optional `run_iter9.py` hook

**Command:**

```powershell
python run_iter9.py --image assets/line_art_irl_11_v2.png --board-w 300 --seed 11 --allow-noncanonical --run-tag "demo_hook_validation" --demo-gui --demo-config configs/demo/iter9_visual_solver_demo.default.json
```

**Pass checklist:**

- Existing Iter9 artifacts are written.
- Demo launches only after successful artifact write.
- Omitting `--demo-gui` reverts to normal behavior.

---

## 14. Commit / Checkpoint Sequence

Use focused commits or checkpoints. Suggested commit sequence:

```text
1. demo-tests: add visual solver test support and architecture gates
2. demo-contracts: add executable demo contract constants
3. demo-config: add pydantic config models and default config
4. demo-domain: add board dimensions, playback events, and snapshots
5. demo-io: add artifact, grid, metrics, and trace loaders
6. demo-playback: add speed, batching, event source, scheduler, replay, finish policy
7. demo-rendering: add palette, window geometry, board/status rendering helpers
8. demo-pygame: add pygame adapter and loop with fake-adapter tests
9. demo-cli: add standalone visual solver demo launcher
10. iter9-hook: add optional thin demo launch hook
11. demo-acceptance: add manual validation notes and final gate evidence
```

---

## 15. LLM Work-Package Prompt Template

Use this template for each coding slice:

```text
Implement only <module/test slice> for the Iter9 Visual Solver Demo.

Source-of-truth contract:
- <contract doc section>

Files allowed to edit:
- <exact files>

Files forbidden to edit:
- run_iter9.py unless this is the hook phase
- existing root pipeline modules
- unrelated demo modules

Required tests to create/update:
- <test file>

Required behavior:
- <specific bullets>

Forbidden implementation patterns:
- <boundary bullets>

Run these commands before reporting done:
- python -m unittest <target test module>
- python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries

Return:
- changed files
- test results
- any contract ambiguity found
```

---

## 16. Final Execution Gate

Before claiming the demo is complete, run:

```powershell
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

Then complete one standalone manual GUI run and one optional hook GUI run.

The demo is not complete until automated gates and manual GUI evidence both pass.
