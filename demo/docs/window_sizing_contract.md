# Iter9 Visual Solver Demo — Window Sizing Contract

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Demo rendering/domain architecture |
| Applies to | `demos/iter9_visual_solver/domain/board_dimensions.py`, `demos/iter9_visual_solver/rendering/window_geometry.py` |
| Required before | `test_board_dimensions.py`, `test_window_geometry.py`, `pygame_rendering_contract.md`, GUI MVP implementation |
| Traceability IDs | DEMO-REQ-001, DEMO-REQ-008, DEMO-REQ-010, DEMO-TEST-001, DEMO-TEST-018 |
| Change rule | Any window sizing behavior change must update this file, config schema docs, config contract, test methodology, architecture boundary tests, and traceability matrix. |

---

## 1. Purpose

This contract defines how the Iter9 Visual Solver Demo derives board dimensions, board display dimensions, status-panel dimensions, and final pygame window dimensions.

The most important rule is:

```text
The GUI size is derived from the actual board/grid dimensions and validated config.
The GUI must not depend on a static board height or static board width.
```

The demo may be launched from an Iter9 run that originally used a requested board width such as `300`, but the GUI itself must use the loaded grid shape as the source of truth.

---

## 2. Scope

This contract applies to:

```text
demos/iter9_visual_solver/domain/board_dimensions.py
demos/iter9_visual_solver/rendering/window_geometry.py
demos/iter9_visual_solver/rendering/pygame_adapter.py
demos/iter9_visual_solver/rendering/pygame_loop.py
tests/demo/iter9_visual_solver/test_board_dimensions.py
tests/demo/iter9_visual_solver/test_window_geometry.py
```

This contract does not own:

```text
source image aspect-ratio derivation in board_sizing.py
grid file loading in io/grid_loader.py
status text formatting in rendering/status_text.py
pygame loop behavior in rendering/pygame_loop.py
```

---

## 3. Definitions

| Term | Meaning |
|---|---|
| Source image board width | The requested width passed to Iter9, such as `--board-w 300`. |
| Derived board height | The height originally computed by the Iter9 pipeline from source image aspect ratio. |
| Loaded grid shape | The actual shape of the loaded `.npy` grid artifact. This is authoritative for the demo GUI. |
| Board width | `grid.shape[1]`. |
| Board height | `grid.shape[0]`. |
| Total cells | `board_width * board_height`. |
| Cell pixel size | Compatibility integer derived from board scale; it is not the visual scaling authority during responsive resize. |
| Board viewport | The allotted pixel rectangle for the Minesweeper board visualization. |
| Board draw rect | The aspect-fit rectangle inside the board viewport where the scaled board is blitted. |
| Board scale | Floating screen pixels per logical board cell. This may be below 1.0 on small windows or above 1.0 on large/maximized windows. |
| Status panel | The optional side panel showing source image, board size, seed, cell counts, and playback status. |
| Window geometry | The complete pygame window width/height and all child rectangles. |

---

## 4. Ownership

## 4.1 Owner modules

| Responsibility | Owner Module |
|---|---|
| Extract board width/height from grid shape | `domain/board_dimensions.py` |
| Validate board dimension invariants | `domain/board_dimensions.py` |
| Calculate cell pixel size | `rendering/window_geometry.py` |
| Calculate board viewport size | `rendering/window_geometry.py` |
| Calculate status-panel rectangle | `rendering/window_geometry.py` |
| Calculate total window size | `rendering/window_geometry.py` |
| Apply pygame window size | `rendering/pygame_adapter.py` |

## 4.2 Explicit non-owner modules

| Module | Must Not Own |
|---|---|
| `io/grid_loader.py` | window size, cell pixel size, status panel geometry |
| `io/metrics_loader.py` | board dimensions as GUI truth, window geometry |
| `playback/speed_policy.py` | window geometry |
| `playback/event_scheduler.py` | window geometry |
| `rendering/pygame_loop.py` | sizing formula details |
| `rendering/status_panel.py` | status panel width calculation |
| `cli/commands.py` | window size calculation |
| `run_iter9.py` | demo window size calculation |

---

## 5. Source of Truth Rules

## 5.1 Board dimensions

The demo board dimensions MUST come from the loaded grid:

```python
board_height = grid.shape[0]
board_width = grid.shape[1]
```

The demo MUST NOT use:

```text
a hardcoded height
a hardcoded width
the literal string "derived-height"
metrics board label as the primary source of GUI dimensions
source image dimensions as the primary source of GUI dimensions
```

Metrics may be used for display/provenance cross-checking, but not as the primary GUI shape authority.

## 5.2 Grid/metrics mismatch

If metrics say `300x942` but grid shape is `(941, 300)`, the implementation MUST follow an explicit mismatch policy.

Required policy:

```text
1. grid.shape remains authoritative for GUI dimensions.
2. mismatch is recorded as warning or typed input validation error according to artifact consumption contract.
3. status panel may show both grid-derived board and metrics board only if explicitly configured.
```

MVP recommended behavior:

```text
Raise a typed DemoInputValidationError for mismatch unless the artifact contract explicitly allows warning-only mode.
```

---

## 6. Required Public API

## 6.1 `domain/board_dimensions.py`

Required API:

```python
from dataclasses import dataclass
import numpy as np

@dataclass(frozen=True)
class BoardDimensions:
    width: int
    height: int
    total_cells: int
    label: str

    @classmethod
    def from_grid(cls, grid: np.ndarray) -> "BoardDimensions": ...
```

Required behavior:

| Case | Expected Result |
|---|---|
| grid shape `(942, 300)` | width `300`, height `942`, total cells `282600`, label `300x942` |
| grid shape `(10, 300)` | width `300`, height `10`, total cells `3000`, label `300x10` |
| non-2D grid | reject with typed domain/input error |
| zero-sized dimension | reject |
| `None` grid | reject |

Forbidden behavior:

```text
opening files
importing pygame
importing Pydantic
reading metrics JSON
looking at source image path
```

---

## 6.2 `rendering/window_geometry.py`

Required API:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class RectSpec:
    x: int
    y: int
    width: int
    height: int

@dataclass(frozen=True)
class WindowGeometry:
    board_width_cells: int
    board_height_cells: int
    total_cells: int
    cell_px: int
    board_rect: RectSpec
    status_panel_rect: RectSpec | None
    window_width_px: int
    window_height_px: int
    scale_reason: str
    fits_screen: bool

def calculate_window_geometry(
    *,
    board_width_cells: int,
    board_height_cells: int,
    status_panel_width_px: int,
    preferred_board_cell_px: int,
    minimum_board_cell_px: int,
    max_screen_fraction: float,
    fit_to_screen: bool,
    screen_width_px: int | None = None,
    screen_height_px: int | None = None,
) -> WindowGeometry: ...
```

Responsive layout additions:

- `RectSpec` is the pygame-free rectangle value type for window, content,
  header, board, status-panel, divider, and source-preview rectangles.
- `DisplayBounds` represents active display bounds for screen budgets and
  horizontal placement.
- `LayoutRequest` is the immutable input for startup and resize geometry.
- `WindowPlacement` carries optional OS-window placement. `center_window=true`
  horizontally centers the full window rectangle, not board content.
- `calculate_responsive_window_geometry(...)` recalculates layout for resize
  events while preserving board aspect ratio and exposing
  `board_viewport_rect`, `board_draw_rect`, and floating `board_scale`.
- For user-requested larger window sizes, including maximize, responsive
  geometry preserves the requested surface width/height instead of shrinking
  the pygame window back to the board content size. The board is aspect-fit and
  visually scaled inside its viewport; it is not capped by integer cell size.
- `WindowGeometry` must keep scalar compatibility fields while exposing rects,
  fit flags, minimum/preferred window sizes, and a bottom-right
  `source_preview_rect` inside the status panel when space allows.

---

## 7. Geometry Calculation Rules

## 7.1 Base board viewport

```text
base_board_width_px  = board_width_cells  * preferred_board_cell_px
base_board_height_px = board_height_cells * preferred_board_cell_px
```

## 7.2 Status panel

If `status_panel_width_px > 0`:

```text
window_width_px = board_width_px + status_panel_width_px
window_height_px = max(board_height_px, minimum_status_panel_height_px)
```

During resize/maximize handling, the configured width is treated as the
minimum/preferred width. The responsive width is:

```text
panel_width = min(max(status_panel_width_px, int(window_width * 0.28)), min(560, window_width // 2))
```

The panel docks to the right edge of the requested window surface, leaving a
gutter and divider between panel and board viewport.

If `status_panel_width_px == 0`:

```text
window_width_px = board_width_px
status_panel_rect = None
```

## 7.3 Screen fitting

When `fit_to_screen = true`, geometry MUST fit within:

```text
allowed_screen_width  = floor(screen_width_px  * max_screen_fraction)
allowed_screen_height = floor(screen_height_px * max_screen_fraction)
```

If the preferred visual scale does not fit, reduce `board_scale` until the
board draw rect fits the allotted viewport. `cell_px` remains a compatibility
integer only.

## 7.4 Minimum cell size

If the full window cannot fit even at `minimum_board_cell_px`, then:

```text
cell_px = minimum_board_cell_px
fits_screen = false
scale_reason = "minimum_cell_size_exceeds_screen_budget"
```

The implementation MUST NOT distort board aspect ratio.

## 7.5 No board cropping for MVP

MVP MUST NOT crop the board.

If the board cannot fit at the minimum cell size, the window geometry must report `fits_screen = false`; the pygame adapter may still open the minimum-size window, but cropping/scrolling/panning is out of MVP scope.

---

## 8. Config Fields Consumed

| Config Field | Owner | Runtime Effect |
|---|---|---|
| `window.status_panel_width_px` | `window_geometry.py` | Adds horizontal panel width. |
| `window.minimum_board_cell_px` | `window_geometry.py` | Lower bound for cell size. |
| `window.preferred_board_cell_px` | `window_geometry.py` | Starting/ideal cell size. |
| `window.max_screen_fraction` | `window_geometry.py` | Limits window size relative to screen. |
| `window.fit_to_screen` | `window_geometry.py` | Enables dynamic shrink-to-fit behavior. |
| `window.resizable` | `pygame_adapter.py` | Applies pygame resizable flag. |
| `window.title` | `pygame_adapter.py` | Sets pygame window caption. |
| `window.center_window` | `pygame_adapter.py` | Optional platform/window placement behavior. |

---

## 9. Required Error Behavior

| Invalid Condition | Required Error |
|---|---|
| non-2D grid | typed domain/input validation error |
| grid width <= 0 | typed domain/input validation error |
| grid height <= 0 | typed domain/input validation error |
| preferred cell px < minimum cell px | config validation error before geometry function |
| max screen fraction outside contract range | config validation error before geometry function |
| status panel width < 0 | config validation error before geometry function |
| screen width/height <= 0 when supplied | geometry validation error |

Error messages MUST include:

```text
field or argument name
invalid value
expected rule
```

---

## 10. Forbidden Implementation Patterns

Forbidden in `window_geometry.py`:

```text
pygame.display.set_mode
pygame.Surface
pygame.draw
json.load
np.load
Pydantic BaseModel
open(
Path(
```

Forbidden in `pygame_loop.py`:

```text
manual window sizing formula
hardcoded board dimensions
hardcoded status panel width
```

Forbidden anywhere:

```text
Board: 300 x derived-height
hardcoded derived height
static GUI dimensions disconnected from grid shape
```

---

## 11. Required Tests

## 11.1 `test_board_dimensions.py`

Required test cases:

- [ ] `BoardDimensions.from_grid()` uses `grid.shape`.
- [ ] Height comes from `shape[0]`.
- [ ] Width comes from `shape[1]`.
- [ ] Total cells equals width times height.
- [ ] Label formats as `<width>x<height>`.
- [ ] Non-2D grid is rejected.
- [ ] Zero-height grid is rejected.
- [ ] Zero-width grid is rejected.
- [ ] No pygame import is needed.

## 11.2 `test_window_geometry.py`

Required test cases:

- [ ] Preferred cell size is used when it fits.
- [ ] Cell size shrinks when preferred size exceeds screen budget.
- [ ] Cell size does not shrink below minimum.
- [ ] Status panel width is included in total window width.
- [ ] Status panel rect is `None` when width is zero.
- [ ] Tall board and wide board both calculate correctly.
- [ ] Window dimensions are derived from board dimensions.
- [ ] Board aspect ratio is not distorted.
- [ ] Maximized windows produce `board_scale > 1.0` when space allows.
- [ ] Smaller resize produces `board_scale < 1.0` without changing board dimensions.
- [ ] Source preview aspect-fits using source-image dimensions when provided.
- [ ] `fits_screen` false case is represented explicitly.
- [ ] No pygame window is opened in geometry tests.

## 11.3 Architecture tests

Required architecture boundary assertions:

- [ ] `window_geometry.py` does not import pygame.
- [ ] `board_dimensions.py` does not import pygame, Pydantic, pathlib, JSON, or file I/O.
- [ ] `pygame_loop.py` does not own sizing formula details.

---

## 12. Acceptance Evidence

A change satisfies this contract only when:

```text
python -m unittest tests.demo.iter9_visual_solver.test_board_dimensions
python -m unittest tests.demo.iter9_visual_solver.test_window_geometry
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
```

pass, and the full suite passes:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

---

## 13. Completion Checklist

- [ ] Board dimensions are derived from loaded grid shape.
- [ ] Window geometry is pure and pygame-free.
- [ ] Screen fitting is config-driven.
- [ ] Status panel width is config-driven.
- [ ] Geometry reports failure-to-fit explicitly.
- [ ] No static `300 x derived-height` placeholder exists.
- [ ] Tests cover wide, tall, and line-art-like board shapes.
- [ ] Architecture tests enforce boundaries.
