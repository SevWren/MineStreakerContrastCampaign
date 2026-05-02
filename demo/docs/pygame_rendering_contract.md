# Iter9 Visual Solver Demo — pygame Rendering Contract

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Demo rendering architecture |
| Applies to | `demos/iter9_visual_solver/rendering/` |
| Required before | pygame adapter, pygame loop, board surface, status panel, rendering tests |
| Traceability IDs | DEMO-REQ-010, DEMO-REQ-011, DEMO-REQ-012, DEMO-TEST-020, DEMO-TEST-021 |
| Change rule | Any pygame rendering behavior change must update this file, architecture boundary tests, testing methodology, acceptance criteria, and traceability matrix. |

---

## 1. Purpose

This contract defines how pygame is allowed to be used in the Iter9 Visual Solver Demo.

The rendering layer is the only runtime layer allowed to import pygame. pygame is an adapter and display mechanism, not the owner of config validation, artifact loading, board sizing, playback speed, or event-source selection.

---

## 2. Scope

This contract applies to:

```text
demos/iter9_visual_solver/rendering/color_palette.py
demos/iter9_visual_solver/rendering/window_geometry.py
demos/iter9_visual_solver/rendering/board_surface.py
demos/iter9_visual_solver/rendering/status_text.py
demos/iter9_visual_solver/rendering/status_panel.py
demos/iter9_visual_solver/rendering/pygame_adapter.py
demos/iter9_visual_solver/rendering/pygame_loop.py
tests/demo/iter9_visual_solver/test_color_palette.py
tests/demo/iter9_visual_solver/test_window_geometry.py
tests/demo/iter9_visual_solver/test_board_surface.py
tests/demo/iter9_visual_solver/test_status_text.py
tests/demo/iter9_visual_solver/test_status_panel.py
tests/demo/iter9_visual_solver/test_pygame_adapter_contract.py
tests/demo/iter9_visual_solver/test_pygame_loop_with_fakes.py
```

---

## 3. Rendering Ownership Boundaries

| Module | Owns | Must Not Own |
|---|---|---|
| `color_palette.py` | color tuple conversion from validated config | Pydantic validation, pygame window creation |
| `window_geometry.py` | pure geometry calculation | pygame imports, config loading |
| `board_surface.py` | mapping board state/events to visual cells/surface data | event scheduling, file loading, speed policy |
| `status_text.py` | converting `StatusSnapshot` to lines of text | font rendering, metrics loading |
| `status_panel.py` | drawing already-built text lines onto a surface | status calculation, metrics parsing |
| `pygame_adapter.py` | pygame init/display/event/clock seam | playback logic, config validation |
| `pygame_loop.py` | frame-loop orchestration | artifact loading, Pydantic validation, speed formula |

---

## 4. Allowed pygame Import Paths

Runtime pygame imports are allowed only under:

```text
demos/iter9_visual_solver/rendering/pygame_adapter.py
demos/iter9_visual_solver/rendering/pygame_loop.py
demos/iter9_visual_solver/rendering/status_panel.py
demos/iter9_visual_solver/rendering/board_surface.py
```

`color_palette.py`, `window_geometry.py`, and `status_text.py` SHOULD remain pygame-free unless a later ADR explicitly allows otherwise.

Test pygame/fake paths:

```text
tests/demo/iter9_visual_solver/fixtures/pygame_fakes.py
tests/demo/iter9_visual_solver/helpers/pygame_assertions.py
tests/demo/iter9_visual_solver/test_pygame_adapter_contract.py
tests/demo/iter9_visual_solver/test_pygame_loop_with_fakes.py
```

Forbidden pygame import paths:

```text
demos/iter9_visual_solver/config/
demos/iter9_visual_solver/contracts/
demos/iter9_visual_solver/domain/
demos/iter9_visual_solver/io/
demos/iter9_visual_solver/playback/
demos/iter9_visual_solver/cli/
run_iter9.py
run_benchmark.py
```

---

## 5. Required Rendering Flow

The runtime flow MUST follow this order:

```text
validated config
+ loaded grid
+ loaded metrics
+ normalized playback events
    ↓
BoardDimensions
    ↓
WindowGeometry
    ↓
ColorPalette
    ↓
ReplayState / StatusSnapshot
    ↓
StatusText lines
    ↓
BoardSurface + StatusPanel drawing
    ↓
PygameAdapter / PygameLoop
```

The renderer MUST NOT reverse this flow by having pygame modules load config or parse artifacts.

---

## 6. Required Public APIs

## 6.1 `rendering/color_palette.py`

```python
@dataclass(frozen=True)
class ColorPalette:
    unseen_cell_rgb: tuple[int, int, int]
    flagged_mine_rgb: tuple[int, int, int]
    safe_cell_rgb: tuple[int, int, int]
    unknown_cell_rgb: tuple[int, int, int]
    background_rgb: tuple[int, int, int]

    @classmethod
    def from_config(cls, visuals: VisualsConfig) -> "ColorPalette": ...
```

Required behavior:

- Converts lists from config into immutable tuples.
- Does not validate raw config shape; config layer already owns that.
- Does not import pygame.

## 6.2 `rendering/board_surface.py`

Expected APIs:

```python
def build_board_surface_model(board_state: BoardState, palette: ColorPalette) -> BoardSurfaceModel: ...

def apply_event_to_surface_model(
    surface_model: BoardSurfaceModel,
    event: PlaybackEvent,
    palette: ColorPalette,
) -> None: ...
```

If pygame-specific surface drawing is included:

```python
def draw_board_surface(surface, surface_model: BoardSurfaceModel, geometry: WindowGeometry) -> None: ...
```

Required behavior:

- Mines flagged during playback use `flagged_mine_rgb`.
- Safe cells use `safe_cell_rgb` only if `show_safe_cells = true`.
- Unknown cells use `unknown_cell_rgb` only if `show_unknown_cells = true`.
- Unseen cells use `unseen_cell_rgb`.
- Board model dimensions must match board dimensions.

## 6.3 `rendering/status_panel.py`

Expected API:

```python
def draw_status_panel(
    surface,
    lines: list[str],
    *,
    panel_rect: RectSpec,
    palette: ColorPalette,
    font,
) -> None: ...
```

Required behavior:

- Draws provided lines.
- Does not calculate status values.
- Does not load metrics.
- Handles empty line list.
- Uses injected/fake font in tests.

## 6.4 `rendering/pygame_adapter.py`

Required API:

```python
class PygameAdapter:
    def __init__(self, pygame_module=None): ...

    def initialize(self) -> None: ...
    def open_window(self, *, width: int, height: int, title: str, resizable: bool): ...
    def create_clock(self): ...
    def poll_events(self) -> list: ...
    def tick(self, fps: int) -> int: ...
    def flip(self) -> None: ...
    def close(self) -> None: ...
```

Required behavior:

- Supports dependency injection of a fake pygame module.
- Does not import or load config.
- Does not calculate playback speed.
- Does not load artifacts.
- Does not own event scheduling.

## 6.5 `rendering/pygame_loop.py`

Required API:

```python
def run_pygame_loop(
    *,
    adapter: PygameAdapter,
    geometry: WindowGeometry,
    palette: ColorPalette,
    scheduler: EventScheduler,
    replay_state: ReplayState,
    finish_config: FinishBehaviorConfig,
    target_fps: int,
    status_line_builder: Callable[[StatusSnapshot], list[str]],
) -> DemoRunResult: ...
```

Allowed alternate API:

```python
def run_pygame_loop(..., pygame_module=None, max_frames: int | None = None) -> DemoRunResult: ...
```

`max_frames` is allowed only as a test seam.

---

## 7. Loop Behavior Contract

The pygame loop MUST:

1. Initialize pygame through the adapter.
2. Open a window using precomputed geometry.
3. Poll pygame events.
4. Exit on user close/QUIT event.
5. Request the next batch of playback events from scheduler.
6. Apply events to replay state and board visual model.
7. Build status lines from status snapshot.
8. Draw board and status panel.
9. Flip display.
10. Tick clock using configured target FPS.
11. Detect playback completion.
12. Apply finish policy.
13. Return a structured result.

The pygame loop MUST NOT:

```text
load config JSON
validate Pydantic models
load .npy grid
load metrics JSON
calculate board dimensions from source image
calculate events-per-second formula
select event source
write event traces
write artifacts
```

---

## 8. Frame Rate and Playback Separation

`target_fps` controls the pygame tick rate.

`events_per_second` controls playback speed.

These are separate concepts.

The pygame loop may call:

```text
scheduler.next_batch()
```

but it MUST NOT calculate:

```text
base_events_per_second + total_mines * mine_count_multiplier
```

That formula belongs only in:

```text
playback/speed_policy.py
```

---

## 9. Finish Behavior

Finish behavior is owned by:

```text
playback/finish_policy.py
```

The pygame loop may ask:

```python
should_auto_close(finish_config, elapsed_after_finish_s)
```

The pygame loop MUST support:

```text
stay_open
close_immediately
close_after_delay
```

Default expected behavior:

```text
stay_open
```

---

## 10. Testing Contract

## 10.1 No real window for unit tests

Unit tests MUST use fakes.

Required fake classes:

```text
FakePygameModule
FakeDisplay
FakeSurface
FakeClock
FakeEventQueue
FakeFont
```

## 10.2 Required tests

### `test_pygame_adapter_contract.py`

- [ ] adapter initializes injected pygame module.
- [ ] adapter opens requested window size.
- [ ] adapter sets caption.
- [ ] adapter polls events through fake queue.
- [ ] adapter ticks clock through fake clock.
- [ ] adapter closes pygame cleanly.

### `test_pygame_loop_with_fakes.py`

- [ ] loop runs with fake pygame module.
- [ ] loop applies at least one event batch.
- [ ] loop draws at least one frame.
- [ ] loop exits on fake QUIT event.
- [ ] loop honors `stay_open` with test `max_frames` seam.
- [ ] loop honors `close_immediately`.
- [ ] loop honors `close_after_delay`.
- [ ] loop does not require real display.

### `test_board_surface.py`

- [ ] mine events map to configured flag color.
- [ ] safe events map according to `show_safe_cells`.
- [ ] unknown events map according to `show_unknown_cells`.
- [ ] unseen cells remain configured unseen color.
- [ ] model dimensions match board dimensions.

### `test_status_panel.py`

- [ ] panel draws supplied lines.
- [ ] panel does not calculate text.
- [ ] panel handles no status lines.
- [ ] panel uses fake font/surface.

### `test_architecture_boundaries.py`

- [ ] pygame imports are rendering-only.
- [ ] rendering does not validate config.
- [ ] CLI does not draw pixels.
- [ ] run_iter9 does not import pygame.

---

## 11. Manual Visual Smoke Criteria

A manual smoke run passes when:

- [ ] pygame window opens.
- [ ] board area is visible.
- [ ] status panel is visible when configured.
- [ ] mines/flags appear progressively during playback.
- [ ] playback speed visibly changes when config speed changes.
- [ ] final board remains open under `stay_open`.
- [ ] GUI can close through OS window close button.
- [ ] no traceback appears in terminal.

---

## 12. Failure Conditions

The implementation fails this contract if:

- pygame is imported outside allowed paths.
- A real pygame window opens during unit tests.
- pygame loop parses config.
- pygame loop loads grid or metrics.
- pygame loop owns speed formula.
- geometry is calculated inside pygame loop instead of `window_geometry.py`.
- status panel parses metrics.
- playback completion always auto-closes despite config.
- board display dimensions are hardcoded.

---

## 13. Completion Checklist

- [ ] pygame adapter exists.
- [ ] pygame loop exists.
- [ ] board surface drawing/model exists.
- [ ] status panel drawing exists.
- [ ] renderer consumes validated config values only.
- [ ] rendering tests use fakes.
- [ ] architecture tests enforce pygame isolation.
- [ ] manual smoke criteria are documented.
