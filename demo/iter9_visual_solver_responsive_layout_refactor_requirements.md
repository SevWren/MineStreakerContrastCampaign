# Iter9 Visual Solver Demo — Responsive Layout Refactor Requirements

## Document Control

| Field | Value |
|---|---|
| Document status | Refactor requirements, not implementation code |
| Source basis | Current pasted config, latest layout analysis, `iter9_visual_solver_codebase.txt`, and `demo_documentation_files.txt` |
| Applies to | `demos/iter9_visual_solver/`, `tests/demo/iter9_visual_solver/`, `configs/demo/`, `demo/docs/` |
| Primary goal | Make the pygame GUI screen-aware, resize-aware, layout-recomputed, and horizontally centerable through `window.center_window` |
| Non-goal | Rewriting the Iter9 algorithm, solver, repair, SA, report generation, artifact generation, or base project root modules |
| Blocking validation command | `python -m unittest discover -s tests -p "test_*.py"` |

---

## 1. Required Interpretation of the User Request

The current visible problem is not the orange-on-black board policy. That behavior is expected from:

```json
"show_safe_cells": false,
"show_unknown_cells": false
```

The real refactor target is the layout system:

```text
fixed startup geometry
no live resize handling
status panel calculated once at startup
no runtime behavior for center_window
resizable flag without resize behavior
fit_to_screen disabled in the pasted active config
```

This refactor must make layout a runtime-owned system instead of a one-time startup calculation.

---

## 2. Non-Negotiable Scope Boundaries

## 2.1 Runtime source boundary

Allowed runtime package for this work:

```text
demos/iter9_visual_solver/
```

Allowed demo tests:

```text
tests/demo/iter9_visual_solver/
```

Allowed demo docs/config files:

```text
demo/docs/
configs/demo/iter9_visual_solver_demo.default.json
```

## 2.2 Forbidden base-project changes

Do not modify these files to solve GUI layout:

```text
core.py
sa.py
solver.py
corridors.py
repair.py
pipeline.py
report.py
board_sizing.py
source_config.py
run_benchmark.py
```

`run_iter9.py` may only remain a thin optional launch hook if demo integration already exists. It must not calculate layout, import pygame, or handle resize events.

## 2.3 Forbidden architectural shortcuts

Do not implement this by creating:

```text
demo_config.py
demo_visualizer.py
visual_solver_demo.py
iter9_visual_solver_demo.py
```

Do not put geometry math into:

```text
rendering/pygame_loop.py
rendering/status_panel.py
cli/commands.py
```

Do not put pygame imports outside:

```text
demos/iter9_visual_solver/rendering/
```

---

## 3. Current Code Problems That Must Be Removed

## 3.1 `window_geometry.py` is startup-only and scalar-only

Current behavior:

```text
calculate_window_geometry(...) returns board/window scalar dimensions.
It does not expose board_rect, status_panel_rect, content_rect, or placement.
It accepts screen_width/screen_height defaults but CLI does not pass real screen size.
When fit_to_screen is false, preferred_board_cell_px is used directly.
```

Required removal:

```text
Do not let pygame_loop reconstruct panel coordinates from scalar board_pixel_width.
Do not let CLI calculate geometry once and treat it as permanent.
Do not use default 1920x1080 as a hidden screen truth when pygame can report the actual display.
```

## 3.2 `pygame_adapter.py` sets `RESIZABLE` but owns no resize behavior

Current behavior:

```text
open_window(..., resizable=True) passes pygame.RESIZABLE into display.set_mode.
No adapter method reports current surface/window size.
No adapter method extracts resize-event dimensions.
No adapter method reopens/resizes the surface.
No adapter method performs center_window placement.
```

Required removal:

```text
Do not expose `resizable` as a cosmetic flag only.
Do not make pygame_loop inspect raw pygame event internals directly.
Do not make tests require a real pygame window for resize behavior.
```

## 3.3 `pygame_loop.py` ignores resize events

Current behavior:

```text
The loop polls events only for QUIT.
It draws with startup width, height, board_pixel_width, cell_px, and status_panel_width_px.
It never recomputes layout after the window changes size.
It hard-codes panel_rect as (board_pixel_width, 0, status_panel_width_px, height).
```

Required removal:

```text
Do not keep startup geometry as the only layout state.
Do not draw panel at y=0 unless geometry says y=0.
Do not ignore VIDEORESIZE / WINDOWSIZECHANGED events when resizable is true.
```

## 3.4 `status_panel.py` is fixed-position, fixed-spacing text drawing

Current behavior:

```text
x = 12
y = 12
line spacing = 20 px
no wrapping
no panel-aware measurement
no content clipping policy beyond surface behavior
no centered/balanced layout
```

Required removal:

```text
Do not let panel text depend on a hard-coded startup rectangle.
Do not draw text without considering actual current panel width.
Do not allow long values to silently draw outside the panel when wrapping is available.
```

## 3.5 `center_window` exists but is dead config

Current behavior:

```text
config/models.py defines window.center_window.
The CLI does not pass it into pygame_adapter.open_window.
pygame_adapter.open_window does not use it.
```

Required removal:

```text
Do not leave center_window as documentation-only config.
Do not interpret center_window inside CLI.
Do not implement center_window inside geometry math; it is window placement behavior owned by pygame_adapter.
```

---

## 4. Required Final Behavior

## 4.1 Startup behavior

At startup, the demo must:

```text
1. Load config.
2. Load grid.
3. Derive board dimensions from grid.shape.
4. Ask the rendering adapter for actual display bounds.
5. Calculate startup layout from board dimensions, display bounds, config, and requested status-panel width.
6. If window.center_window is true, place the entire pygame window horizontally centered on the active display before or during opening.
7. Open the pygame window with the calculated startup width and height.
8. Draw board and status panel from layout rectangles, not from ad hoc x/y formulas.
```

## 4.2 Runtime resize behavior

When `window.resizable` is true, the demo must:

```text
1. Detect window resize events from pygame.
2. Extract the new requested window width/height through pygame_adapter.
3. Recalculate current layout from the new window size.
4. Clamp the window size to the minimum legal layout if the requested size is too small.
5. Preserve replay_state and playback progress during resize.
6. Redraw board and status panel using the recalculated layout on the next frame.
7. Continue polling quit events during and after playback completion.
```

When `window.resizable` is false, the demo must:

```text
1. Not request pygame resizable mode.
2. Ignore resize events if the platform still emits them.
3. Continue using the startup layout.
```

## 4.3 Board scaling behavior

Board scaling must obey all of the following:

```text
cell_px is always an integer.
cell_px is never less than window.minimum_board_cell_px.
cell_px is never greater than window.preferred_board_cell_px unless a future config field explicitly permits upscaling.
board_width_cells and board_height_cells never change during GUI playback.
board aspect ratio is never distorted.
board cells are never stretched independently on X/Y axes.
```

## 4.4 Fit-to-screen behavior

The current pasted active config has:

```json
"fit_to_screen": false
```

The accepted config contract and model default expect:

```json
"fit_to_screen": true
```

Refactor requirement:

```text
Update configs/demo/iter9_visual_solver_demo.default.json so the default demo config sets window.fit_to_screen = true.
```

Runtime semantics:

| `fit_to_screen` | Startup behavior |
|---|---|
| `true` | Startup layout must shrink `cell_px` as needed so full GUI attempts to fit within `screen_size * max_screen_fraction`. |
| `false` | Startup layout may use `preferred_board_cell_px` even if the initial window exceeds screen budget. Resize handling must still work if the user resizes the window. |

No hidden override is allowed. If a user explicitly supplies `fit_to_screen=false`, the runtime must not pretend it is true.

## 4.5 `center_window` behavior

`window.center_window` must control placement of the entire OS-level pygame window rectangle, not the position of the board inside the window.

Required semantics:

| Field value | Required runtime behavior |
|---|---|
| `center_window: true` | Horizontally center the full window rectangle within the active display before or during opening. |
| `center_window: false` | Do not request custom horizontal centering; allow the OS/window manager default placement. |

Acceptance rule:

```text
When true, the window x-coordinate must be calculated as:

x = display_left_px + floor((display_width_px - window_width_px) / 2)
```

Clamp rule:

```text
x must be at least display_left_px.
If window_width_px > display_width_px, x = display_left_px.
```

Vertical placement is not part of this requirement unless a future config field defines it. Tests for this refactor must verify horizontal placement only.

---

## 5. Required Data Model Changes

## 5.1 Add `RectSpec`

File:

```text
demos/iter9_visual_solver/rendering/window_geometry.py
```

Required dataclass:

```python
@dataclass(frozen=True)
class RectSpec:
    x: int
    y: int
    width: int
    height: int
```

Required invariants:

```text
x >= 0
y >= 0
width >= 0
height >= 0
```

No pygame Rect dependency is allowed in this dataclass.

## 5.2 Replace scalar-only `WindowGeometry` with layout-aware geometry

Existing scalar fields must remain temporarily for compatibility until all callers are migrated.

Required final dataclass:

```python
@dataclass(frozen=True)
class WindowGeometry:
    board_width: int
    board_height: int
    total_cells: int
    cell_px: int

    window_rect: RectSpec
    content_rect: RectSpec
    board_rect: RectSpec
    status_panel_rect: RectSpec | None

    board_pixel_width: int
    board_pixel_height: int
    status_panel_width_px: int
    window_width: int
    window_height: int

    minimum_window_width: int
    minimum_window_height: int
    preferred_window_width: int
    preferred_window_height: int

    fits_screen: bool
    fits_window: bool
    scale_reason: str
```

Compatibility rule:

```text
Existing code that reads geometry.cell_px, geometry.board_pixel_width, geometry.status_panel_width_px, geometry.window_width, and geometry.window_height must continue working until the caller migration is complete.
```

## 5.3 Add `DisplayBounds`

File:

```text
demos/iter9_visual_solver/rendering/window_geometry.py
```

Required dataclass:

```python
@dataclass(frozen=True)
class DisplayBounds:
    x: int
    y: int
    width: int
    height: int
```

Purpose:

```text
Represent the current active display/work-area bounds used for fit-to-screen and center_window placement.
```

No pygame object dependency is allowed.

## 5.4 Add `WindowPlacement`

File:

```text
demos/iter9_visual_solver/rendering/window_geometry.py
```

Required dataclass:

```python
@dataclass(frozen=True)
class WindowPlacement:
    x: int | None
    y: int | None
    horizontally_centered: bool
```

Required semantics:

```text
x/y None means do not request custom placement.
horizontally_centered describes whether the requested x value came from center_window logic.
```

## 5.5 Add `LayoutRequest`

File:

```text
demos/iter9_visual_solver/rendering/window_geometry.py
```

Required dataclass:

```python
@dataclass(frozen=True)
class LayoutRequest:
    board_width: int
    board_height: int
    requested_window_width: int | None
    requested_window_height: int | None
    status_panel_width_px: int
    preferred_board_cell_px: int
    minimum_board_cell_px: int
    max_screen_fraction: float
    fit_to_screen: bool
    display_bounds: DisplayBounds
```

Purpose:

```text
One immutable input object for startup and resize layout calculation.
```

---

## 6. Required Geometry APIs

## 6.1 Startup geometry API

Keep `calculate_window_geometry(...)` available, but change it to produce the enriched geometry.

Required signature:

```python
def calculate_window_geometry(
    *,
    board_width: int,
    board_height: int,
    status_panel_width_px: int,
    preferred_board_cell_px: int,
    minimum_board_cell_px: int,
    max_screen_fraction: float,
    fit_to_screen: bool,
    screen_width: int | None = None,
    screen_height: int | None = None,
    display_bounds: DisplayBounds | None = None,
) -> WindowGeometry: ...
```

Rules:

```text
If display_bounds is supplied, use it.
If display_bounds is not supplied but screen_width/screen_height are supplied, construct DisplayBounds(0, 0, screen_width, screen_height).
If no display size is supplied, use the current compatibility default only in tests or legacy call paths; pygame runtime must pass real display bounds.
```

## 6.2 Resize geometry API

Add:

```python
def calculate_responsive_window_geometry(request: LayoutRequest) -> WindowGeometry: ...
```

Required behavior:

```text
requested_window_width/requested_window_height supplied -> calculate layout for that current window surface.
requested_window_width/requested_window_height None -> calculate startup layout from screen budget and preferred size.
```

## 6.3 Placement API

Add:

```python
def calculate_window_placement(
    *,
    window_width: int,
    window_height: int,
    display_bounds: DisplayBounds,
    center_window: bool,
) -> WindowPlacement: ...
```

Required behavior:

```text
center_window false -> WindowPlacement(x=None, y=None, horizontally_centered=False)
center_window true -> x = display_bounds.x + max(0, (display_bounds.width - window_width) // 2)
y may be None unless adapter implementation requires a y coordinate.
```

If the pygame/SDL backend requires a y-coordinate to apply x, adapter-level behavior must be documented and tested with fakes. Unit tests must assert the horizontal x value, not vertical centering.

---

## 7. Exact Geometry Calculation Requirements

## 7.1 Startup available screen budget

When `fit_to_screen=true`:

```text
allowed_screen_width_px  = floor(display_bounds.width  * max_screen_fraction)
allowed_screen_height_px = floor(display_bounds.height * max_screen_fraction)
```

When `fit_to_screen=false`:

```text
allowed_screen_width_px  = preferred_window_width
allowed_screen_height_px = preferred_window_height
```

## 7.2 Preferred window size

```text
preferred_board_width_px  = board_width  * preferred_board_cell_px
preferred_board_height_px = board_height * preferred_board_cell_px
preferred_window_width    = preferred_board_width_px + status_panel_width_px
preferred_window_height   = preferred_board_height_px
```

## 7.3 Minimum window size

```text
minimum_board_width_px  = board_width  * minimum_board_cell_px
minimum_board_height_px = board_height * minimum_board_cell_px
minimum_window_width    = minimum_board_width_px + status_panel_width_px
minimum_window_height   = minimum_board_height_px
```

Status panel width remains the configured width during this refactor. The refactor must not silently collapse or resize the status panel unless a future config contract explicitly permits it.

## 7.4 Cell size calculation

Available board width:

```text
available_board_width_px = max(1, available_window_width_px - status_panel_width_px)
```

Available board height:

```text
available_board_height_px = max(1, available_window_height_px)
```

Cell size candidate:

```text
candidate_cell_px = min(
    preferred_board_cell_px,
    floor(available_board_width_px / board_width),
    floor(available_board_height_px / board_height),
)
```

Effective cell size:

```text
cell_px = max(minimum_board_cell_px, candidate_cell_px)
```

Rules:

```text
If candidate_cell_px >= minimum_board_cell_px, fits_window = true.
If candidate_cell_px < minimum_board_cell_px, fits_window = false and cell_px = minimum_board_cell_px.
```

## 7.5 Rectangles

Board rectangle:

```text
board_rect.x = 0
board_rect.y = 0
board_rect.width = board_width * cell_px
board_rect.height = board_height * cell_px
```

Status panel rectangle when enabled:

```text
status_panel_rect.x = board_rect.width
status_panel_rect.y = 0
status_panel_rect.width = status_panel_width_px
status_panel_rect.height = max(board_rect.height, current_window_height)
```

Window rectangle:

```text
window_rect.x = 0
window_rect.y = 0
window_rect.width = board_rect.width + status_panel_width_px
window_rect.height = board_rect.height
```

If the user-resized window is larger than the content group, content centering inside the window is not in scope unless a future config field defines it. Extra surface area may remain background color.

## 7.6 No board cropping

Renderer must never intentionally crop the board as a layout strategy.

If the requested resize size is smaller than `minimum_window_width x minimum_window_height`, the runtime must:

```text
1. calculate geometry at minimum cell size.
2. mark fits_window = false.
3. request/clamp surface size back to at least the minimum window size when pygame backend supports it.
4. continue rendering without crashing.
```

## 7.7 `scale_reason` values

Use only these exact strings:

```text
preferred_cell_size_used
fit_to_screen_reduced_cell_size
resize_reduced_cell_size
minimum_cell_size_exceeds_screen_budget
minimum_cell_size_exceeds_window_size
```

No other string values are allowed without test and docs updates.

---

## 8. Required Pygame Adapter Refactor

File:

```text
demos/iter9_visual_solver/rendering/pygame_adapter.py
```

## 8.1 Required new adapter methods

Add these public methods:

```python
def get_display_bounds(self) -> DisplayBounds: ...

def open_window(
    self,
    *,
    width: int,
    height: int,
    title: str,
    resizable: bool = False,
    placement: WindowPlacement | None = None,
): ...

def resize_window(self, *, width: int, height: int, resizable: bool) -> object: ...

def get_surface_size(self, surface=None) -> tuple[int, int]: ...

def is_quit_event(self, event) -> bool: ...

def is_resize_event(self, event) -> bool: ...

def get_resize_event_size(self, event) -> tuple[int, int] | None: ...
```

## 8.2 Display bounds behavior

`get_display_bounds()` must prefer real pygame display information:

```text
1. initialize display subsystem if needed.
2. use pygame.display.get_desktop_sizes() if available.
3. otherwise use pygame.display.Info().current_w/current_h.
4. return DisplayBounds(x=0, y=0, width=w, height=h) unless platform-specific display origin is available.
```

If pygame cannot report a valid display size, return the existing compatibility fallback only through an explicit constant:

```python
FALLBACK_DISPLAY_BOUNDS = DisplayBounds(x=0, y=0, width=1920, height=1080)
```

The fallback must be covered by a test.

## 8.3 Open-window placement behavior

When `placement.x is not None`, the adapter must attempt to request that initial window x-position before opening the window.

Acceptable implementation options:

```text
SDL environment variable placement before pygame.display.set_mode.
Backend-specific placement call if pygame/backend supports it.
Fake adapter recording in tests.
```

Required guardrails:

```text
Do not place this logic in CLI.
Do not place this logic in window_geometry.py beyond calculating placement values.
Do not fail the demo if a platform ignores placement; log/record if a logging seam exists, otherwise continue.
```

## 8.4 Resize handling behavior

`resize_window(...)` must:

```text
1. call pygame.display.set_mode((width, height), flags) with RESIZABLE flag when resizable=true.
2. update adapter.surface.
3. return the new surface.
```

`get_surface_size(...)` must:

```text
1. prefer surface.get_size() when available.
2. fallback to adapter.surface.get_size().
3. return integer width/height.
```

## 8.5 Event helpers

`is_resize_event(event)` must identify both pygame resize event styles where supported:

```text
pygame.VIDEORESIZE
pygame.WINDOWSIZECHANGED
```

`get_resize_event_size(event)` must support:

```text
event.w / event.h
event.size tuple
current surface size fallback when event has no size fields
```

The loop must not compare raw event types directly except through adapter helper methods after this refactor.

---

## 9. Required Pygame Loop Refactor

File:

```text
demos/iter9_visual_solver/rendering/pygame_loop.py
```

## 9.1 Signature change

Preferred final signature:

```python
def run_pygame_loop(
    *,
    pygame_module=None,
    events=None,
    events_per_frame: int = 1,
    events_per_second: int = 0,
    board_width: int,
    board_height: int,
    source_image_name: str = "unknown",
    seed: int = 0,
    replay_source: str = "",
    finish_config=None,
    status_config=None,
    palette: ColorPalette | None = None,
    show_safe_cells: bool = False,
    show_unknown_cells: bool = True,
    geometry: WindowGeometry,
    display_bounds: DisplayBounds,
    window_config=None,
    target_fps: int = 60,
    title: str = "Mine-Streaker Iter9 Visual Solver Demo",
    resizable: bool = False,
    max_frames: int | None = None,
) -> PygameLoopResult: ...
```

Temporary compatibility path is allowed only during migration. The final implementation must stop passing these separate scalar geometry arguments from CLI:

```text
cell_px
board_pixel_width
status_panel_width_px
width
height
```

## 9.2 Startup sequence

The loop must perform or receive these prepared values:

```text
adapter = PygameAdapter(...)
display_bounds = adapter.get_display_bounds()
startup_geometry = calculate_window_geometry(..., display_bounds=display_bounds)
placement = calculate_window_placement(..., center_window=config.window.center_window)
surface = adapter.open_window(..., placement=placement)
current_geometry = startup_geometry
```

If CLI owns the first geometry calculation, then CLI must pass real display bounds from adapter. Preferred design is for a rendering-level launcher/helper to own adapter display query so CLI remains non-rendering orchestration.

## 9.3 Event handling loop

Replace current quit-only event loop with:

```python
for event in adapter.poll_events():
    if adapter.is_quit_event(event):
        return user_closed result

    if resizable and adapter.is_resize_event(event):
        size = adapter.get_resize_event_size(event)
        if size is not None:
            requested_width, requested_height = size
            current_geometry = calculate_responsive_window_geometry(...)
            if not current_geometry.fits_window:
                surface = adapter.resize_window(
                    width=current_geometry.minimum_window_width,
                    height=current_geometry.minimum_window_height,
                    resizable=resizable,
                )
            else:
                surface = adapter.resize_window(
                    width=requested_width,
                    height=requested_height,
                    resizable=resizable,
                )
```

Do not reset:

```text
scheduler
replay_state
events_applied
elapsed_time_s
finish_started_s
```

## 9.4 Per-frame draw order

The loop must draw in this order:

```text
1. fill entire surface with palette.background_rgb.
2. draw board state at current_geometry.board_rect.x/y.
3. draw status panel inside current_geometry.status_panel_rect if panel enabled.
4. flip display.
5. tick clock.
6. update elapsed time.
7. evaluate finish policy.
```

If future visual polish adds border/header/cards, those must use geometry rectangles, not ad hoc positions.

## 9.5 Finish behavior preservation

Resize refactor must not change finish behavior.

Required unchanged behavior:

```text
stay_open -> never auto-close after playback completion.
close_immediately -> auto-close when playback completes.
close_after_delay -> auto-close after configured delay.
OS close event -> exits cleanly in all modes.
```

## 9.6 Speed behavior preservation

Resize refactor must not change playback speed calculation.

The pygame loop must continue to consume:

```text
events_per_frame
events_per_second
```

It must not call:

```text
calculate_events_per_second
calculate_events_per_frame
```

inside `pygame_loop.py`.

---

## 10. Required Board Drawing Refactor

File:

```text
demos/iter9_visual_solver/rendering/board_surface.py
```

Current issue:

```text
draw_board_state(...) fills the entire surface every time.
```

Required change:

```python
def draw_board_state(
    *,
    surface,
    adapter,
    board_state: Any,
    palette: Any,
    cell_px: int,
    show_safe_cells: bool = False,
    show_unknown_cells: bool = True,
    origin: tuple[int, int] = (0, 0),
    clear_surface: bool = True,
) -> None: ...
```

Required behavior:

```text
clear_surface=True keeps existing standalone behavior.
clear_surface=False prevents board drawing from clearing status panel or extra window background.
pygame_loop must fill the whole surface once and then call draw_board_state(..., clear_surface=False).
```

Origin behavior:

```text
origin must come from current_geometry.board_rect.
The board renderer must not assume origin=(0, 0).
```

---

## 11. Required Status Panel Refactor

File:

```text
demos/iter9_visual_solver/rendering/status_panel.py
```

## 11.1 Panel rectangle ownership

`status_panel.py` must receive the actual current panel rectangle.

It must not calculate:

```text
panel x from board width
panel width from config
window height from startup values
```

## 11.2 Wrapping requirement

Text drawing must become panel-aware.

Required helper:

```python
def wrap_status_line(
    text: str,
    *,
    max_width_px: int,
    font,
) -> list[str]: ...
```

If the fake font cannot measure text width, tests may use deterministic character-count wrapping through a helper, but real pygame rendering must use font measurement when available.

## 11.3 Spacing requirement

Replace hard-coded `y += 20` with named constants:

```python
PANEL_PADDING_X = 12
PANEL_PADDING_Y = 12
LINE_GAP_PX = 4
SECTION_GAP_PX = 8
```

Line height must come from font when available:

```python
line_height = font.get_linesize() if available else 20
```

## 11.4 Clipping/overflow requirement

If status text exceeds panel height:

```text
Do not crash.
Do not draw outside current panel rect intentionally.
Draw only lines whose baseline/top lies inside panel_rect.
Stop drawing remaining lines after vertical space is exhausted.
```

No scrolling is required for MVP.

## 11.5 Existing status text preservation

`status_text.py` remains owner of what status lines say.

`status_panel.py` may wrap/draw lines only.

Do not change status values during layout refactor.

---

## 12. Required Status Text Preservation

File:

```text
demos/iter9_visual_solver/rendering/status_text.py
```

Do not change these prefixes without updating tests and docs:

```text
Source image:
Board:
Seed:
Total cells:
Mines flagged:
Safe cells solved:
Unknown remaining:
Playback speed:
Elapsed time:
Finish:
```

Do not silently add thousands separators during this refactor. That is polish work, not responsive-layout work.

---

## 13. Required CLI Refactor

File:

```text
demos/iter9_visual_solver/cli/commands.py
```

## 13.1 Remove startup-only scalar geometry wiring

Current CLI passes:

```text
cell_px
board_pixel_width
status_panel_width_px
width
height
```

Required final CLI behavior:

```text
Pass validated config, board dimensions, and initial geometry object or call a rendering-level launch helper that owns display query and geometry construction.
```

Preferred final wiring:

```python
run_pygame_loop(
    events=events,
    events_per_frame=events_per_frame,
    events_per_second=events_per_second,
    board_width=dims.width,
    board_height=dims.height,
    source_image_name=_source_image_name(metrics),
    seed=int(metrics.get("seed", 0)),
    replay_source=_source,
    finish_config=config.window.finish_behavior,
    status_config=config.status_panel,
    palette=palette,
    show_safe_cells=config.visuals.show_safe_cells,
    show_unknown_cells=config.visuals.show_unknown_cells,
    window_config=config.window,
    target_fps=config.playback.target_fps,
    title=config.window.title,
    resizable=config.window.resizable,
)
```

If the loop requires `geometry`, construct it through a rendering-level helper that already has real display bounds.

## 13.2 Do not query pygame from CLI

CLI must not directly import or instantiate pygame.

If display bounds are needed before opening the window, create a rendering helper such as:

```text
demos/iter9_visual_solver/rendering/window_runtime.py
```

with:

```python
def build_startup_window_context(...): ...
```

CLI may call this helper only if architecture tests allow it as rendering-owned behavior.

---

## 14. Required Config and Schema Changes

## 14.1 Default config file

File:

```text
configs/demo/iter9_visual_solver_demo.default.json
```

Required correction:

```json
"window": {
  "resizable": true,
  "fit_to_screen": true,
  "center_window": true
}
```

Reason:

```text
The pasted active config has fit_to_screen=false, which directly permits oversized windows. The accepted contract default and responsive demo goal require screen-aware behavior by default.
```

## 14.2 Config model

File:

```text
demos/iter9_visual_solver/config/models.py
```

Current model already exposes:

```text
window.resizable
window.max_screen_fraction
window.status_panel_width_px
window.minimum_board_cell_px
window.preferred_board_cell_px
window.fit_to_screen
window.center_window
```

Required model changes:

```text
No new config fields are required for this refactor.
Do not add center_content, center_horizontal, layout_mode, or panel_collapse fields unless a new contract is approved.
```

## 14.3 Schema and schema docs

Files:

```text
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md
```

Required actions:

```text
Verify schema reflects existing center_window and fit_to_screen fields.
Verify default examples set fit_to_screen=true.
Verify center_window runtime effect says horizontal window placement, not content layout.
```

If the schema already matches, do not churn it.

---

## 15. Required Documentation Updates

Update these docs:

```text
demo/docs/window_sizing_contract.md
demo/docs/pygame_rendering_contract.md
demo/docs/status_panel_contract.md
demo/docs/config_contract.md
demo/docs/testing_methodology.md
demo/docs/architecture_boundary_tests.md
demo/docs/traceability_matrix.md
demo/docs/completion_gate.md
demo/docs/acceptance_criteria.md
```

## 15.1 `window_sizing_contract.md`

Add requirements for:

```text
responsive resize geometry
DisplayBounds
LayoutRequest
WindowPlacement
fits_window
minimum_window_width / minimum_window_height
runtime recomputation on resize
center_window horizontal placement semantics
```

## 15.2 `pygame_rendering_contract.md`

Add requirements for:

```text
adapter resize event helpers
adapter display bounds query
adapter open-window placement
pygame loop recomputes layout on resize
pygame loop preserves replay state on resize
```

## 15.3 `status_panel_contract.md`

Add requirements for:

```text
panel-aware wrapping
current panel rectangle usage
font-based line height
safe overflow behavior
no hard-coded status-panel x/y ownership
```

## 15.4 `config_contract.md`

Add or correct:

```text
fit_to_screen default true
center_window runtime owner pygame_adapter.py
center_window controls horizontal OS-window placement
resizable controls both RESIZABLE flag and resize-event behavior
```

## 15.5 `completion_gate.md`

Add gates for:

```text
resize event test passes
center_window placement test passes
fit_to_screen default config is true
window geometry uses real display bounds in runtime
status panel uses current panel rect after resize
```

---

## 16. Required Test Changes

## 16.1 Geometry tests

File:

```text
tests/demo/iter9_visual_solver/test_window_geometry.py
```

Required tests:

```text
test_calculate_geometry_uses_grid_dimensions_as_truth
test_fit_to_screen_reduces_cell_px_to_fit_display_budget
test_fit_to_screen_false_uses_preferred_cell_px_at_startup
test_minimum_cell_size_reports_screen_budget_overflow
test_resize_geometry_reduces_cell_px_for_smaller_window
test_resize_geometry_never_goes_below_minimum_cell_px
test_resize_geometry_reports_window_overflow_when_too_small
test_status_panel_rect_recomputed_from_current_geometry
test_board_rect_preserves_aspect_ratio
test_calculate_window_placement_centers_x_when_enabled
test_calculate_window_placement_returns_none_when_disabled
```

## 16.2 Adapter tests

File:

```text
tests/demo/iter9_visual_solver/test_pygame_adapter_contract.py
```

Required tests:

```text
test_get_display_bounds_uses_desktop_sizes_when_available
test_get_display_bounds_falls_back_to_display_info
test_get_display_bounds_uses_explicit_fallback_when_display_invalid
test_open_window_records_or_applies_centered_placement
test_open_window_does_not_place_when_center_window_false
test_resize_window_reopens_surface_with_resizable_flag
test_get_surface_size_reads_surface_get_size
test_is_resize_event_detects_videoresize
test_is_resize_event_detects_window_size_changed
test_get_resize_event_size_reads_w_h
test_get_resize_event_size_reads_size_tuple
```

## 16.3 Pygame loop tests

File:

```text
tests/demo/iter9_visual_solver/test_pygame_loop_with_fakes.py
```

Required tests:

```text
test_loop_handles_quit_event_before_resize
test_loop_recomputes_geometry_on_resize_event
test_loop_preserves_replay_state_after_resize
test_loop_preserves_events_applied_after_resize
test_loop_draws_board_at_current_board_rect_after_resize
test_loop_draws_status_panel_at_current_panel_rect_after_resize
test_loop_clamps_surface_to_minimum_when_resize_too_small
test_loop_ignores_resize_when_resizable_false
test_loop_stay_open_still_waits_after_completion
test_loop_close_after_delay_still_closes_after_delay
test_loop_does_not_call_speed_policy
```

## 16.4 Status panel tests

File:

```text
tests/demo/iter9_visual_solver/test_status_panel.py
```

Required tests:

```text
test_draw_status_panel_uses_panel_rect_origin
test_draw_status_panel_wraps_long_lines_to_panel_width
test_draw_status_panel_uses_font_line_height_when_available
test_draw_status_panel_stops_when_panel_height_exhausted
test_draw_status_panel_does_not_calculate_status_values
test_draw_status_panel_keeps_existing_plain_line_behavior
```

## 16.5 Board surface tests

File:

```text
tests/demo/iter9_visual_solver/test_board_surface.py
```

Required tests:

```text
test_draw_board_state_default_clear_surface_preserves_existing_behavior
test_draw_board_state_clear_surface_false_does_not_fill_entire_surface
test_draw_board_state_uses_origin_from_geometry
test_draw_board_state_preserves_integer_cell_rects
```

## 16.6 Config/schema tests

Files:

```text
tests/demo/iter9_visual_solver/test_config_models.py
tests/demo/iter9_visual_solver/test_config_schema_contract.py
```

Required tests:

```text
test_default_config_fit_to_screen_true
test_default_config_center_window_true
test_center_window_is_boolean_and_extra_fields_forbidden
test_schema_default_example_matches_committed_default_config
test_config_model_default_fit_to_screen_matches_json_default
```

## 16.7 Architecture tests

File:

```text
tests/demo/iter9_visual_solver/test_architecture_boundaries.py
```

Required checks:

```text
pygame import isolation still passes.
CLI still does not draw pixels.
rendering still does not validate/load config.
playback still does not import rendering or pygame.
window_geometry still does not import pygame.
status_panel still does not load config or metrics.
```

---

## 17. Required Fake Pygame Enhancements

File:

```text
tests/demo/iter9_visual_solver/fixtures/pygame_fakes.py
```

Add fake support for:

```text
RESIZABLE flag recording
VIDEORESIZE constant
WINDOWSIZECHANGED constant
fake event queue with resize events
fake display.get_desktop_sizes()
fake display.Info()
fake display.set_mode() call recording
fake surface.get_size()
fake surface.fill(..., rect)
fake font.size(text) or equivalent measurement
fake font.get_linesize()
fake placement request recording if adapter uses env/application seam
```

Do not duplicate fake pygame classes inside individual test files.

---

## 18. Required File Ownership After Refactor

| Responsibility | Required owner |
|---|---|
| Board dimensions from grid | `domain/board_dimensions.py` |
| Startup and resize geometry math | `rendering/window_geometry.py` |
| Window placement calculation | `rendering/window_geometry.py` |
| Applying pygame window placement | `rendering/pygame_adapter.py` |
| Querying display size | `rendering/pygame_adapter.py` |
| Detecting pygame resize events | `rendering/pygame_adapter.py` |
| Reopening/resizing pygame surface | `rendering/pygame_adapter.py` |
| Event loop orchestration | `rendering/pygame_loop.py` |
| Board cell drawing | `rendering/board_surface.py` |
| Status text content | `rendering/status_text.py` |
| Status text drawing/wrapping | `rendering/status_panel.py` |
| Playback speed | `playback/speed_policy.py` |
| Finish behavior | `playback/finish_policy.py` |
| Config validation | `config/models.py` and `config/loader.py` |
| Artifact loading | `io/*_loader.py` |

---

## 19. Required Migration Sequence

Implement in this exact order:

```text
1. Add failing geometry tests for DisplayBounds, RectSpec, WindowPlacement, responsive layout, and center x placement.
2. Implement geometry dataclasses and pure geometry functions.
3. Add fake pygame display/resize/placement support.
4. Add adapter tests for display bounds, placement, resize events, and resize_window.
5. Implement adapter methods.
6. Add board_surface tests for clear_surface=False and origin behavior.
7. Implement board_surface clear_surface parameter.
8. Add status_panel tests for panel-aware wrapping and overflow.
9. Implement status_panel wrapping/dynamic line-height behavior.
10. Add pygame_loop fake resize tests.
11. Refactor pygame_loop to use current_geometry and adapter event helpers.
12. Refactor CLI wiring so scalar geometry values are not passed as independent layout truth.
13. Update default config so fit_to_screen=true.
14. Update docs and traceability.
15. Run targeted tests.
16. Run full unittest discovery.
17. Run manual demo on the latest Iter9 artifacts.
```

Do not combine steps 1–12 into a single large patch.

---

## 20. Required Validation Commands

After geometry changes:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_window_geometry
```

After adapter changes:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_pygame_adapter_contract
```

After board/status rendering changes:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_board_surface
python -m unittest tests.demo.iter9_visual_solver.test_status_panel
```

After loop integration:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
python -m unittest tests.demo.iter9_visual_solver.test_cli_commands
```

After config/schema updates:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_models
python -m unittest tests.demo.iter9_visual_solver.test_config_schema_contract
```

Final verification:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
python -m demos.iter9_visual_solver.cli.commands --help
```

---

## 21. Manual Acceptance Requirements

Run the GUI with a completed Iter9 run and the default demo config.

Manual reviewer must verify:

```text
Window opens within visible screen bounds when fit_to_screen=true.
Window is horizontally centered when center_window=true.
Window is not deliberately horizontally positioned when center_window=false.
Board is visible at startup.
Status panel is visible at startup.
Board uses actual grid dimensions.
Board aspect ratio is preserved.
Status text uses real values.
Window resize smaller causes board cell_px to shrink until minimum cell size.
Window resize larger does not exceed preferred_board_cell_px.
Status panel rectangle moves/reflows after resize.
Status text wraps/clips safely inside the panel.
Playback continues after resize.
Finish behavior still matches config.
OS close button exits cleanly.
No terminal traceback occurs.
```

Manual screenshot evidence required:

```text
1. startup screenshot
2. resized-smaller screenshot
3. resized-larger screenshot
4. completed stay_open screenshot
```

---

## 22. Blocking Failure Conditions

Any of these fail the refactor:

```text
fit_to_screen default config remains false.
center_window remains unused at runtime.
resizable true only sets a flag but does not handle resize events.
pygame_loop continues to poll only QUIT events.
pygame_loop continues to draw from startup-only board_pixel_width/height.
status_panel draws from hard-coded startup geometry after resize.
board_surface clears the whole surface after the loop has drawn panel/background.
cell_px becomes fractional.
board X/Y scale differs.
board dimensions change during resize.
playback restarts after resize.
events_applied resets after resize.
finish behavior changes.
pygame import leaks outside rendering/test seams.
CLI imports pygame or draws pixels.
config validation moves into rendering.
unit tests require a real pygame window.
```

---

## 23. Final Definition of Done

The refactor is complete only when all statements below are true:

```text
The default demo config is screen-aware by default: fit_to_screen=true.
window.center_window has a real runtime effect on horizontal OS-window placement.
window.resizable has a real runtime effect beyond setting pygame.RESIZABLE.
Startup geometry uses actual display bounds from the adapter.
Resize events cause layout recomputation.
Resize does not reset replay state.
Board rendering uses current_geometry.board_rect.
Status panel rendering uses current_geometry.status_panel_rect.
Status panel text wraps or clips inside the current panel.
Board aspect ratio remains correct under resize.
cell_px remains integer and within configured bounds.
Pygame loop remains an orchestration shell.
Geometry math remains pure and pygame-free.
Adapter owns pygame-specific event/window APIs.
All targeted tests pass.
Full unittest discovery passes.
Manual screenshots demonstrate startup, resize, and completed stay-open behavior.
```

---

## 24. Signoff Template

```text
Refactor branch:
Git commit:
Reviewer:
Date:
Default config path:
Grid artifact path:
Metrics artifact path:
Display bounds observed:
Startup window size:
Startup cell_px:
Startup centered x:
Resize-smaller window size:
Resize-smaller cell_px:
Resize-larger window size:
Resize-larger cell_px:
Final unknown remaining:
Finish behavior observed:
Targeted tests result:
Full unittest discovery result:
CLI smoke result:
Manual screenshot paths:
Approved exceptions:
Final decision: accepted / rejected
```
