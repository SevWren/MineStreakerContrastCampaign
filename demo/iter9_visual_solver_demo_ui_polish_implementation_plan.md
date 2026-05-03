# Iter9 Visual Solver Demo UI Polish — Codebase-Grounded Implementation Plan

## Document Control

| Field | Value |
|---|---|
| Document status | Rewritten implementation plan grounded in `iter9_visual_solver_codebase.txt` and `demo_documentation_files.txt` |
| Applies to | `demos/iter9_visual_solver/` runtime package, `tests/demo/iter9_visual_solver/`, `demo/docs/`, `configs/demo/` |
| Primary implementation goal | Improve the pygame demo interface polish without violating existing demo contracts, architecture boundaries, or Iter9 artifact contracts |
| Non-negotiable scope boundary | Do **not** refactor base Iter9 algorithm/runtime modules as part of this UI polish work |
| Primary validation command | `python -m unittest discover -s tests -p "test_*.py"` |
| Existing CLI smoke commands | `python run_iter9.py --help`, `python run_benchmark.py --help`, `python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical` |

---

## 1. Exact Objective

Rewrite the current plain pygame demo interface into a polished, professional technical demo while preserving the existing architecture contract.

The final interface must still display the same factual runtime information required by the accepted demo documentation:

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

The polish work must add visual structure around those facts:

```text
in-app header strip
completion badge
metric cards
progress bars
legend
board border
board/status divider
cleaner panel spacing
optional cursor-hide seam if added through config/docs/tests
```

The work must **not** change solver output, artifact generation, replay event semantics, grid loading semantics, speed calculation semantics, or finish behavior semantics.

---

## 2. Grounded Current-State Inventory

The uploaded codebase already contains the durable demo runtime package and these files:

```text
demos/iter9_visual_solver/cli/commands.py
demos/iter9_visual_solver/config/models.py
demos/iter9_visual_solver/domain/status_snapshot.py
demos/iter9_visual_solver/playback/replay_state.py
demos/iter9_visual_solver/rendering/board_surface.py
demos/iter9_visual_solver/rendering/color_palette.py
demos/iter9_visual_solver/rendering/pygame_adapter.py
demos/iter9_visual_solver/rendering/pygame_loop.py
demos/iter9_visual_solver/rendering/status_panel.py
demos/iter9_visual_solver/rendering/status_text.py
demos/iter9_visual_solver/rendering/window_geometry.py
```

The current implementation path is:

```text
cli/commands.py
  -> load_demo_config(...)
  -> load_grid(...)
  -> load_metrics(...)
  -> BoardDimensions.from_grid(grid)
  -> load_event_trace(...) when supplied
  -> select_event_source(...)
  -> calculate_events_per_second(...)
  -> calculate_events_per_frame(...)
  -> calculate_window_geometry(...)
  -> ColorPalette.from_config(...)
  -> run_pygame_loop(...)
```

The current renderer is intentionally simple:

```text
status_text.py builds plain string lines.
status_panel.py draws those lines top-to-bottom with fixed x/y padding and fixed 20 px spacing.
board_surface.py draws cell rectangles and currently fills the whole surface background.
pygame_loop.py draws board state, then status text, then flips the display.
window_geometry.py returns scalar sizes only; it does not expose header, board, panel, border, or divider rectangles.
pygame_adapter.py exposes window open, event polling, ticking, flip, font creation, rectangle drawing, and close.
```

The current docs require:

```text
pygame imports only under rendering-approved seams.
status_panel.py draws already-built text and must not parse metrics or calculate status.
status_text.py converts StatusSnapshot values into display text.
window_geometry.py owns pure geometry calculation.
playback/speed_policy.py owns speed calculation.
playback/finish_policy.py owns finish behavior.
pygame_loop.py owns frame-loop orchestration only.
```

Therefore, polish must be implemented as rendering/view-model work, not as new business logic inside `pygame_loop.py`.

---

## 3. Scope Lock

## 3.1 In Scope

| Area | In scope change |
|---|---|
| Header strip | Add an in-window title/source/board/seed header derived from already-loaded values. |
| Completion badge | Add a visual badge derived from `StatusSnapshot.unknown_remaining` and `finish_state`. |
| Metric cards | Render the existing required status facts as grouped cards. |
| Progress bars | Render mines flagged, safe solved, and unknown remaining using already-computed counters. |
| Legend | Render color legend using existing `ColorPalette`. |
| Board border | Draw a non-invasive border around the board rectangle. |
| Divider | Draw a thin divider between board and status panel. |
| Layout model | Add pure layout/view-model dataclasses so `status_panel.py` does not calculate status. |
| Tests | Add/modify unit tests with fakes; do not require a real pygame window. |
| Docs | Update only docs needed to describe new rendering/view-model behavior and completion gates. |

## 3.2 Out of Scope

| Item | Reason |
|---|---|
| Source-image thumbnail | Current runtime input does not load a source image artifact. Adding it would require artifact/config contract changes and image I/O ownership decisions. |
| Pause/resume controls | Current MVP explicitly requires no user controls. |
| Timeline scrubber | Non-goal for MVP and would add input-state complexity. |
| True solver chronological replay | Current MVP supports final-grid replay fallback; chronological trace is a future feature. |
| Modifying SA/solver/repair/pipeline | UI polish must not alter generation logic. |
| Changing artifact names | Demo consumes `grid_iter9_latest.npy` and `metrics_iter9_<board>.json`; names stay unchanged. |
| Adding web UI framework | Accepted rendering stack is pygame. |
| Adding broad theme system | This plan uses existing palette/config and small rendering constants only. |

## 3.3 Explicit Forbidden Changes

Do not edit these files for UI polish unless a separate implementation issue proves a blocking integration defect:

```text
core.py
sa.py
solver.py
corridors.py
repair.py
pipeline.py
board_sizing.py
source_config.py
run_benchmark.py
assets/image_guard.py
```

Do not add these root files:

```text
demo_config.py
demo_visualizer.py
visual_solver_demo.py
iter9_visual_solver_demo.py
```

Do not import pygame in:

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

## 4. Target Visual Design

## 4.1 Final Window Composition

The final pygame window must have this layout:

```text
┌──────────────────────────────────────────────────────────────────────────┐
│ Mine-Streaker Iter9 Visual Solver Demo | source | board | seed | status │  <- header strip
├──────────────────────────────────────────────┬───────────────────────────┤
│                                              │ Completion badge           │
│                                              │                           │
│            board render area                 │ Metric cards              │
│            orange mine line art              │                           │
│                                              │ Progress bars             │
│                                              │                           │
│                                              │ Legend                    │
└──────────────────────────────────────────────┴───────────────────────────┘
```

## 4.2 Required Visual Elements

| Element | Required behavior | Owner |
|---|---|---|
| Header strip | Draws `window.title`, source image, board dimensions, seed, replay source if available. | `rendering/window_chrome.py` or `rendering/status_panel.py` through a passed view model |
| Completion badge | Shows `SOLVED` only when `unknown_remaining == 0` and playback is complete; otherwise shows `RUNNING`. | `rendering/status_view_model.py` builds, `status_panel.py` draws |
| Mine progress bar | Numerator = `mines_flagged`, denominator = `total_mines`. | view model + panel drawing |
| Safe progress bar | Numerator = `safe_cells_solved`, denominator = `safe_cells`. | view model + panel drawing |
| Unknown bar | Numerator = remaining unknown cells; denominator = `total_cells`; display must make zero unknown visually good. | view model + panel drawing |
| Metric cards | Group required status values into stable sections; no placeholders. | view model + panel drawing |
| Legend | Draws configured color swatches for flagged mine, safe cell if enabled, unknown if enabled, unseen/background. | view model + panel drawing |
| Board border | Draw a 1 px border around actual board viewport only. | `rendering/window_chrome.py` or `board_surface.py` helper |
| Divider | Draw a 1 px vertical divider between board and status panel. | `rendering/window_chrome.py` or panel helper |

## 4.3 Text Rules

The accepted status contract currently says numeric values are shown without commas by default. This plan must preserve that unless tests and docs are intentionally updated.

Therefore:

```text
Default line text remains:
Total cells: 115800
Mines flagged: 6715 / 6715
Safe cells solved: 109085 / 109085
```

A polish implementation may use alignment and spacing, but it must not silently change existing text formatting in `build_status_lines(...)`.

If thousands separators are desired later, they must be added through an explicit contract update and tests must consistently expect commas.

---

## 5. Architecture Design

## 5.1 New Pure View-Model Layer

Add a new rendering pure helper file:

```text
demos/iter9_visual_solver/rendering/status_view_model.py
```

This file must not import pygame, Pydantic, jsonschema, pathlib, json, os, sys, numpy, or artifact loaders.

Required contents:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

@dataclass(frozen=True)
class ProgressSpec:
    key: str
    label: str
    current: int
    total: int
    ratio: float
    value_text: str
    good_when_zero: bool = False

@dataclass(frozen=True)
class MetricCardSpec:
    key: str
    title: str
    lines: tuple[str, ...]

@dataclass(frozen=True)
class LegendItemSpec:
    label: str
    rgb: tuple[int, int, int]

@dataclass(frozen=True)
class CompletionBadgeSpec:
    label: str
    detail: str
    state: str

@dataclass(frozen=True)
class StatusPanelViewModel:
    header_text: str
    badge: CompletionBadgeSpec
    cards: tuple[MetricCardSpec, ...]
    progress_bars: tuple[ProgressSpec, ...]
    legend_items: tuple[LegendItemSpec, ...]
    raw_lines: tuple[str, ...]
```

Required public function:

```python
def build_status_panel_view_model(
    *,
    snapshot: StatusSnapshot | dict,
    status_config: StatusPanelConfig | dict | None,
    palette: ColorPalette,
    show_safe_cells: bool,
    show_unknown_cells: bool,
) -> StatusPanelViewModel: ...
```

This function owns grouping and display model construction only.

It must call or reuse `build_status_lines(...)` so legacy line formatting stays testable and consistent.

## 5.2 Existing `status_text.py` Compatibility Rule

Keep this public function stable:

```python
def build_status_lines(snapshot: Any, status_config: Any | None = None) -> list[str]: ...
```

Do not remove or rename it.

Do not change these exact default line prefixes:

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

Add tests before changing any string content.

## 5.3 Existing `status_panel.py` Backward-Compatible Expansion

Keep this existing public function:

```python
def draw_status_panel(surface, lines: list[str], *, panel_rect=None, background_rgb=(10, 10, 10), text_rgb=(230, 230, 230), font=None) -> None: ...
```

Add a second function for polished rendering:

```python
def draw_status_panel_view_model(
    surface,
    view_model: StatusPanelViewModel,
    *,
    adapter,
    panel_rect,
    palette: ColorPalette,
    font,
    text_rgb: tuple[int, int, int] = (230, 230, 230),
) -> None: ...
```

`draw_status_panel_view_model(...)` must draw only data from `StatusPanelViewModel`.

It must not parse metrics, inspect raw grid arrays, calculate playback speed, calculate finish policy, or load files.

## 5.4 Window Chrome Drawing

Add this file:

```text
demos/iter9_visual_solver/rendering/window_chrome.py
```

It must be pygame-free. It may use the adapter object supplied by `pygame_loop.py`.

Required APIs:

```python
def draw_header_strip(
    surface,
    *,
    adapter,
    header_rect,
    text: str,
    background_rgb: tuple[int, int, int],
    text_rgb: tuple[int, int, int],
    font,
) -> None: ...

def draw_board_border(
    surface,
    *,
    adapter,
    board_rect,
    border_rgb: tuple[int, int, int],
) -> None: ...

def draw_vertical_divider(
    surface,
    *,
    adapter,
    divider_rect,
    divider_rgb: tuple[int, int, int],
) -> None: ...
```

These functions may draw rectangles and text only. They must not know anything about replay events.

## 5.5 Adapter Additions

Update:

```text
demos/iter9_visual_solver/rendering/pygame_adapter.py
```

Add these methods:

```python
def draw_line(self, surface, color, start_pos, end_pos, width: int = 1) -> None: ...

def draw_rect(
    self,
    surface,
    color,
    rect,
    *,
    width: int = 0,
    border_radius: int = 0,
) -> None: ...

def blit_text(self, surface, font, text: str, color, position) -> None: ...

def set_mouse_visible(self, visible: bool) -> None: ...
```

Backward compatibility rule:

```python
adapter.draw_rect(surface, color, rect)
```

must continue to work exactly as before.

If the injected fake pygame object does not support line, border radius, or mouse visibility, the adapter method must degrade without crashing. Fakes should record the attempted call.

## 5.6 Geometry Enrichment

Update:

```text
demos/iter9_visual_solver/rendering/window_geometry.py
```

Current `WindowGeometry` fields must remain available because `cli/commands.py` uses:

```text
geometry.cell_px
geometry.board_pixel_width
geometry.status_panel_width_px
geometry.window_width
geometry.window_height
```

Add these dataclasses while preserving the scalar fields:

```python
@dataclass(frozen=True)
class RectSpec:
    x: int
    y: int
    width: int
    height: int

@dataclass(frozen=True)
class WindowGeometry:
    board_width: int
    board_height: int
    cell_px: int
    board_pixel_width: int
    board_pixel_height: int
    status_panel_width_px: int
    window_width: int
    window_height: int
    header_rect: RectSpec
    board_rect: RectSpec
    status_panel_rect: RectSpec | None
    divider_rect: RectSpec | None
    scale_reason: str
    fits_screen: bool
```

Use constants inside `window_geometry.py`:

```python
DEFAULT_HEADER_HEIGHT_PX = 34
DEFAULT_DIVIDER_WIDTH_PX = 1
```

Do not add config fields for header height in Phase 1.

Required geometry formula:

```text
available_width_px = floor(screen_width * max_screen_fraction)
available_height_px = floor(screen_height * max_screen_fraction)
header_height_px = 34
candidate_cell_px = preferred_board_cell_px

if fit_to_screen:
    max_board_width_px = available_width_px - status_panel_width_px
    max_board_height_px = available_height_px - header_height_px
    candidate_cell_px = min(
        preferred_board_cell_px,
        floor(max_board_width_px / board_width),
        floor(max_board_height_px / board_height),
    )

cell_px = max(minimum_board_cell_px, candidate_cell_px)
board_pixel_width = board_width * cell_px
board_pixel_height = board_height * cell_px
window_width = board_pixel_width + status_panel_width_px
window_height = header_height_px + board_pixel_height
header_rect = RectSpec(0, 0, window_width, header_height_px)
board_rect = RectSpec(0, header_height_px, board_pixel_width, board_pixel_height)
status_panel_rect = None if status_panel_width_px == 0 else RectSpec(board_pixel_width, header_height_px, status_panel_width_px, board_pixel_height)
divider_rect = None if status_panel_width_px == 0 else RectSpec(board_pixel_width, header_height_px, 1, board_pixel_height)
fits_screen = window_width <= available_width_px and window_height <= available_height_px
scale_reason = one of:
  "preferred_cell_size_used"
  "fit_to_screen_reduced_cell_size"
  "minimum_cell_size_exceeds_screen_budget"
```

No board cropping is allowed.

## 5.7 Board Drawing Adjustment

Update:

```text
demos/iter9_visual_solver/rendering/board_surface.py
```

Current `draw_board_state(...)` fills the entire surface. That makes header/status composition fragile.

Add a parameter:

```python
def draw_board_state(..., clear_surface: bool = True) -> None: ...
```

Behavior:

```text
clear_surface=True  -> existing behavior: fill full surface with background.
clear_surface=False -> do not fill full surface; draw only changed/visible cells at origin.
```

`pygame_loop.py` must use `clear_surface=False` after the loop has filled the complete window background and drawn the header area.

Do not change cell-state color rules.

## 5.8 Pygame Loop Composition

Update:

```text
demos/iter9_visual_solver/rendering/pygame_loop.py
```

The frame draw order must become:

```text
1. Poll close events.
2. Apply next scheduler batch if playback is not finished.
3. Update finish timestamp/finish state.
4. Fill full window background.
5. Draw header strip.
6. Draw board state at geometry.board_rect origin.
7. Draw board border.
8. Draw divider if status panel exists.
9. Build status snapshot.
10. Build status panel view model.
11. Draw polished status panel view model.
12. Flip display.
13. Tick target FPS.
14. Apply finish policy.
15. Return structured result when closed/finished/test limit.
```

`pygame_loop.py` must not calculate events/sec.

`pygame_loop.py` must not inspect metrics.

`pygame_loop.py` may call:

```python
build_status_panel_view_model(...)
draw_status_panel_view_model(...)
draw_header_strip(...)
draw_board_border(...)
draw_vertical_divider(...)
```

## 5.9 CLI Command Wiring

Update:

```text
demos/iter9_visual_solver/cli/commands.py
```

Pass the enriched geometry object into `run_pygame_loop(...)` if the loop signature is updated.

Preferred signature change:

```python
run_pygame_loop(
    *,
    events=events,
    events_per_frame=events_per_frame,
    events_per_second=events_per_second,
    geometry=geometry,
    source_image_name=_source_image_name(metrics),
    seed=int(metrics.get("seed", 0)),
    replay_source=_source,
    finish_config=config.window.finish_behavior,
    status_config=config.status_panel,
    palette=palette,
    show_safe_cells=config.visuals.show_safe_cells,
    show_unknown_cells=config.visuals.show_unknown_cells,
    target_fps=config.playback.target_fps,
    title=config.window.title,
    resizable=config.window.resizable,
)
```

Temporary compatibility is allowed only if tests still cover both forms. The final preferred state is one `geometry` object, not ten scalar layout arguments.

---

## 6. Exact Visual Calculations

## 6.1 Completion Badge

Input:

```text
snapshot.unknown_remaining
snapshot.finish_state
```

Rules:

| Condition | Badge label | Detail | State |
|---|---|---|---|
| `unknown_remaining == 0` and `finish_state` starts with `complete` | `SOLVED` | `0 unknown cells` | `solved` |
| `finish_state == "running"` | `RUNNING` | `<unknown_remaining> unknown remaining` | `running` |
| otherwise | `IN REVIEW` | `<unknown_remaining> unknown remaining` | `warning` |

The badge must not use solver truth outside the snapshot.

## 6.2 Progress Bar Ratio

Function:

```python
def _safe_ratio(current: int, total: int) -> float:
    if total <= 0:
        return 1.0
    return min(1.0, max(0.0, current / total))
```

Mines:

```text
current = mines_flagged
total = total_mines
ratio = current / total
```

Safe cells:

```text
current = safe_cells_solved
total = safe_cells
ratio = current / total
```

Unknown remaining:

```text
current = total_cells - unknown_remaining
total = total_cells
ratio = current / total
label = "Resolved cells"
```

Do **not** render an “unknown remaining” progress bar where a full bar means many unknown cells. That is visually backwards. Use “Resolved cells” so a full bar means progress.

## 6.3 Metric Card Grouping

Build cards in this exact order:

```text
1. Run
   Source image: <source_image_name>
   Board: <width> x <height>
   Seed: <seed>

2. Cells
   Total cells: <total_cells>
   Mines flagged: <mines_flagged> / <total_mines>
   Safe cells solved: <safe_cells_solved> / <safe_cells>
   Unknown remaining: <unknown_remaining>

3. Playback
   Playback speed: <events_per_second> cells/sec
   Elapsed time: <elapsed_seconds>.2fs
   Finish: <finish_state>

4. Replay
   Source: <replay_source or final_grid_replay/unknown>
```

Honor the existing status-panel visibility booleans. Hidden values must not appear in cards or raw lines.

## 6.4 Legend Items

Always include:

```text
Flagged mine / image stroke -> palette.flagged_mine_rgb
Background -> palette.background_rgb
```

Include only when configured:

```text
Safe cell -> palette.safe_cell_rgb, when show_safe_cells=True
Unknown cell -> palette.unknown_cell_rgb, when show_unknown_cells=True
```

---

## 7. Phase-by-Phase Implementation Plan

## Phase 0 — Baseline Snapshot and No-Change Verification

### Purpose

Prove the current runtime and tests are known before UI polish changes.

### Required commands

```powershell
python -m unittest discover -s tests -p "test_*.py"
python -m unittest tests.demo.iter9_visual_solver.test_status_text
python -m unittest tests.demo.iter9_visual_solver.test_status_panel
python -m unittest tests.demo.iter9_visual_solver.test_window_geometry
python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

### Guardrails

- If baseline tests fail, record exact failing tests before modifying UI code.
- Do not use UI polish changes to hide unrelated failures.
- Do not open a real pygame window during unit tests.

### Exit criteria

```text
Baseline command results captured.
Current status line output captured.
Current geometry output for board 300 x 386 captured.
```

---

## Phase 1 — Geometry Enrichment

### Files to modify

```text
demos/iter9_visual_solver/rendering/window_geometry.py
tests/demo/iter9_visual_solver/test_window_geometry.py
```

### Implementation steps

1. Add `RectSpec` dataclass.
2. Add enriched fields to `WindowGeometry` without removing existing scalar fields.
3. Add header/divider constants.
4. Modify `calculate_window_geometry(...)` to reserve header height before board y origin.
5. Preserve aspect ratio by keeping integer `cell_px` and never changing `board_width` or `board_height`.
6. Add `fits_screen` and `scale_reason`.
7. Update tests for:
   - board 300 x 386, preferred cell 2, status panel 360, header 34.
   - status panel disabled width 0.
   - fit-to-screen reduction.
   - minimum cell exceeds screen budget.

### Required tests

```text
test_geometry_exposes_header_board_panel_and_divider_rects
test_geometry_preserves_existing_scalar_fields
test_geometry_offsets_board_below_header
test_geometry_status_panel_none_when_width_zero
test_geometry_fit_to_screen_accounts_for_header_height
test_geometry_reports_minimum_cell_size_exceeds_screen_budget
```

### Blocking failures

- Board y origin remains `0` after header is enabled.
- Window height does not include header height.
- `cell_px` becomes fractional.
- Board aspect ratio is distorted.
- Existing `geometry.cell_px`, `geometry.window_width`, or `geometry.window_height` access breaks.

---

## Phase 2 — Status View Model

### Files to add

```text
demos/iter9_visual_solver/rendering/status_view_model.py
tests/demo/iter9_visual_solver/test_status_view_model.py
```

### Files to preserve

```text
demos/iter9_visual_solver/rendering/status_text.py
```

### Implementation steps

1. Add `ProgressSpec`, `MetricCardSpec`, `LegendItemSpec`, `CompletionBadgeSpec`, and `StatusPanelViewModel`.
2. Add `build_status_panel_view_model(...)`.
3. Reuse `build_status_lines(...)` inside the view model builder.
4. Ensure status visibility booleans hide values in both raw lines and cards.
5. Ensure the “Resolved cells” bar treats zero unknowns as complete.
6. Ensure badge shows `SOLVED` only for complete + zero unknown.
7. Ensure no config validation occurs in this file.

### Required tests

```text
test_view_model_uses_existing_status_lines
test_view_model_builds_solved_badge_when_complete_and_zero_unknown
test_view_model_builds_running_badge_during_playback
test_view_model_progress_ratios_are_clamped
test_view_model_resolved_cells_bar_full_when_unknown_zero
test_view_model_honors_status_visibility_flags
test_view_model_legend_uses_palette_colors
test_status_view_model_does_not_import_pygame
```

### Blocking failures

- View model parses metrics directly.
- View model reads grid arrays.
- View model calculates events/sec.
- View model ignores status visibility flags.
- Zero unknown visually maps to an empty/negative progress state.

---

## Phase 3 — Adapter Primitive Expansion

### Files to modify

```text
demos/iter9_visual_solver/rendering/pygame_adapter.py
tests/demo/iter9_visual_solver/test_pygame_adapter_contract.py
tests/demo/iter9_visual_solver/fixtures/pygame_fakes.py
```

### Implementation steps

1. Extend `draw_rect(...)` to accept optional `width` and `border_radius` keyword arguments.
2. Add `draw_line(...)`.
3. Add `blit_text(...)`.
4. Add `set_mouse_visible(...)` but do not call it by default unless config/docs/tests are updated.
5. Update pygame fakes to record:
   - drawn rectangles
   - drawn lines
   - rendered text
   - blits
   - mouse visibility requests
6. Keep current no-real-window behavior in unit tests.

### Required tests

```text
test_draw_rect_backwards_compatible_signature
test_draw_rect_records_width_and_border_radius_with_fake
test_draw_line_uses_fake_draw_line_when_available
test_blit_text_renders_and_blits_with_fake_font
test_set_mouse_visible_degrades_when_fake_has_no_mouse
```

### Blocking failures

- Existing call `adapter.draw_rect(surface, color, rect)` fails.
- Unit tests require real pygame.
- Adapter starts owning playback logic or config validation.

---

## Phase 4 — Status Panel Polished Drawing

### Files to modify

```text
demos/iter9_visual_solver/rendering/status_panel.py
tests/demo/iter9_visual_solver/test_status_panel.py
```

### Files to use

```text
demos/iter9_visual_solver/rendering/status_view_model.py
```

### Implementation steps

1. Keep existing `draw_status_panel(...)` unchanged for raw line drawing.
2. Add `draw_status_panel_view_model(...)`.
3. Draw panel background inside `panel_rect` only.
4. Draw completion badge at top of panel.
5. Draw metric cards below badge.
6. Draw progress bars below metric cards.
7. Draw legend at bottom or after progress bars, depending on available height.
8. Clip by natural surface behavior when panel is too small; do not calculate hidden values in drawing code.
9. Do not parse metric card text.
10. Do not inspect `StatusSnapshot` directly.

### Recommended drawing constants

```python
PANEL_PADDING_X = 12
PANEL_PADDING_Y = 12
CARD_PADDING_X = 10
CARD_PADDING_Y = 8
CARD_GAP_Y = 8
PROGRESS_BAR_HEIGHT = 8
LEGEND_SWATCH_SIZE = 10
BADGE_HEIGHT = 34
TEXT_LINE_SPACING = 20
BORDER_WIDTH = 1
```

These constants may live in `status_panel.py` because they are presentation constants, not runtime policy.

### Required tests

```text
test_draw_status_panel_existing_lines_still_work
test_draw_status_panel_view_model_draws_badge
test_draw_status_panel_view_model_draws_cards
test_draw_status_panel_view_model_draws_progress_bars
test_draw_status_panel_view_model_draws_legend_items
test_draw_status_panel_view_model_does_not_require_metrics
test_draw_status_panel_view_model_handles_empty_cards_and_bars
```

### Blocking failures

- Drawing code calls `build_status_lines(...)` itself.
- Drawing code calculates mines/safe/unknown counters.
- Drawing code uses hardcoded demo data.
- Drawing code overlaps board area by ignoring `panel_rect.x`.

---

## Phase 5 — Window Chrome Drawing

### Files to add

```text
demos/iter9_visual_solver/rendering/window_chrome.py
tests/demo/iter9_visual_solver/test_window_chrome.py
```

### Implementation steps

1. Implement `draw_header_strip(...)`.
2. Implement `draw_board_border(...)`.
3. Implement `draw_vertical_divider(...)`.
4. Use adapter methods only; do not import pygame directly.
5. Do not parse status snapshot or metrics in chrome drawing.
6. Accept already-built text for the header.

### Header text source

Header text must come from the status view model:

```text
<Mine-Streaker Iter9 Visual Solver Demo> | Source: <source> | Board: <w> x <h> | Seed: <seed>
```

If a value is hidden by status config, omit that fragment from the header.

### Required tests

```text
test_draw_header_strip_fills_header_rect
test_draw_header_strip_blits_given_text
test_draw_board_border_draws_four_edges_or_border_rect
test_draw_vertical_divider_draws_divider_rect
test_window_chrome_does_not_import_pygame
```

### Blocking failures

- Window chrome reads metrics JSON.
- Header text contains placeholders.
- Board border is drawn around the whole window instead of board rect.
- Divider is drawn when status panel is disabled.

---

## Phase 6 — Pygame Loop Integration

### Files to modify

```text
demos/iter9_visual_solver/rendering/pygame_loop.py
demos/iter9_visual_solver/cli/commands.py
tests/demo/iter9_visual_solver/test_pygame_loop_with_fakes.py
tests/demo/iter9_visual_solver/test_cli_commands.py
```

### Implementation steps

1. Update `run_pygame_loop(...)` to accept `geometry: WindowGeometry`.
2. Keep a temporary scalar compatibility path only if required by existing tests; remove it after tests are updated.
3. Fill full window background once per frame before drawing elements.
4. Call `draw_header_strip(...)` with `geometry.header_rect`.
5. Call `draw_board_state(...)` with:

```python
origin=(geometry.board_rect.x, geometry.board_rect.y)
clear_surface=False
cell_px=geometry.cell_px
```

6. Call `draw_board_border(...)` with `geometry.board_rect`.
7. Call `draw_vertical_divider(...)` only when `geometry.divider_rect is not None`.
8. Build snapshot from `ReplayState`.
9. Build `StatusPanelViewModel` from snapshot.
10. Call `draw_status_panel_view_model(...)` when `geometry.status_panel_rect is not None`.
11. Preserve existing event polling and quit behavior.
12. Preserve finish-policy behavior.
13. Preserve `max_frames` test seam.

### Required tests

```text
test_loop_draws_header_before_flip
test_loop_draws_board_at_geometry_board_origin
test_loop_draws_status_panel_with_view_model
test_loop_draws_divider_when_status_panel_exists
test_loop_omits_divider_when_status_panel_width_zero
test_loop_preserves_quit_event_exit
test_loop_preserves_stay_open_finish_behavior
test_loop_does_not_calculate_speed_formula
```

### Blocking failures

- `pygame_loop.py` imports `load_demo_config`, `load_grid`, or `load_metrics`.
- `pygame_loop.py` contains `base_events_per_second + total_mines` or `mine_count_multiplier`.
- `pygame_loop.py` draws board at y=0 after header is enabled.
- `pygame_loop.py` stops polling events after playback completes.

---

## Phase 7 — Config, Schema, and Docs Decision

### Default decision for this plan

Do **not** add config fields in Phase 1–6.

Reason:

```text
The existing accepted config already controls window title, panel width, colors, safe/unknown visibility, playback, and finish behavior. The proposed polish can be implemented using those existing values plus rendering constants.
```

### Docs that must be updated

```text
demo/docs/pygame_rendering_contract.md
demo/docs/status_panel_contract.md
demo/docs/window_sizing_contract.md
demo/docs/testing_methodology.md
demo/docs/completion_gate.md
demo/docs/traceability_matrix.md
```

### Required doc changes

1. Add `status_view_model.py` and `window_chrome.py` to rendering ownership sections.
2. Add tests:

```text
test_status_view_model.py
test_window_chrome.py
```

3. Add completion gates for:

```text
header strip renders
completion badge renders
progress bars reflect snapshot counters
legend uses ColorPalette
board border uses board rect
status divider uses divider rect
```

4. Document that Phase 1 polish uses existing config values and fixed rendering constants.

### Explicit schema rule

Because no new config fields are added, this plan must not modify:

```text
configs/demo/iter9_visual_solver_demo.default.json
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md
```

If a future implementer wants configurable header height, card padding, rounded corners, cursor hiding, or number separators, that work must be a separate config/schema change.

---

## Phase 8 — Manual Demo Review

### Manual command

Use a completed Iter9 run directory containing:

```text
grid_iter9_latest.npy
metrics_iter9_<board>.json
```

Launch through the standalone command path:

```powershell
python -m demos.iter9_visual_solver.cli.commands --grid <run_dir>\grid_iter9_latest.npy --metrics <run_dir>\metrics_iter9_<board>.json --config configs/demo/iter9_visual_solver_demo.default.json
```

### Manual visual checklist

The screenshot must show:

```text
Header strip visible.
Board starts below header, not behind it.
Cat/line-art render remains undistorted.
Board border encloses the rendered board only.
Divider separates board from panel.
Completion badge is visible in the panel.
Metric cards are visible and readable.
Progress bars are visible and use correct ratios.
Legend is visible and matches configured colors.
Status text values match the underlying counters.
Finish state remains open under stay_open.
OS close button exits cleanly.
No terminal traceback appears.
```

### Manual arithmetic checks

For the screenshot case shown previously:

```text
Board: 300 x 386
Total cells: 115800
Mines flagged: 6715 / 6715
Safe cells solved: 109085 / 109085
Unknown remaining: 0
```

The reviewer must verify:

```text
300 * 386 = 115800
6715 + 109085 = 115800
unknown_remaining = 0 means SOLVED badge
```

---

## 8. Required Test Matrix

| Test file | New / modified | Required purpose |
|---|---|---|
| `test_window_geometry.py` | modified | Header/rect geometry, fit-to-screen, scalar compatibility. |
| `test_status_text.py` | modified only if needed | Existing raw status lines remain stable. |
| `test_status_view_model.py` | new | Badge, cards, progress, legend, visibility flags. |
| `test_status_panel.py` | modified | Existing plain lines plus polished view-model drawing. |
| `test_window_chrome.py` | new | Header, border, divider drawing through adapter/fakes. |
| `test_pygame_adapter_contract.py` | modified | New primitive methods and backwards-compatible `draw_rect`. |
| `test_pygame_loop_with_fakes.py` | modified | Composed draw order and finish behavior with new UI. |
| `test_cli_commands.py` | modified | Command passes enriched geometry into loop. |
| `test_architecture_boundaries.py` | modified if allowlists reference exact files | New rendering modules remain inside allowed rendering boundary. |
| `test_source_file_modularity.py` | modified if pattern lists require it | New files stay under responsibility and size limits. |

---

## 9. Acceptance Gates for This UI Polish Work

## 9.1 Blocking gates

| Gate ID | Requirement | Verification |
|---|---|---|
| UIP-GATE-001 | Existing raw status lines still render without placeholders. | `test_status_text.py` |
| UIP-GATE-002 | Geometry exposes header, board, status, and divider rects. | `test_window_geometry.py` |
| UIP-GATE-003 | Board origin accounts for header height. | `test_pygame_loop_with_fakes.py` |
| UIP-GATE-004 | Status panel drawing does not calculate metrics. | `test_status_panel.py` + architecture scan |
| UIP-GATE-005 | Status view model produces correct SOLVED badge. | `test_status_view_model.py` |
| UIP-GATE-006 | Progress bars use correct denominators. | `test_status_view_model.py` |
| UIP-GATE-007 | Legend uses `ColorPalette`. | `test_status_view_model.py` / `test_status_panel.py` |
| UIP-GATE-008 | Pygame adapter still supports old `draw_rect` call. | `test_pygame_adapter_contract.py` |
| UIP-GATE-009 | pygame loop does not calculate speed formula. | architecture/source modularity test |
| UIP-GATE-010 | No pygame imports outside rendering-approved paths. | architecture test |
| UIP-GATE-011 | Full unittest discovery passes. | `python -m unittest discover -s tests -p "test_*.py"` |
| UIP-GATE-012 | Existing Iter9 CLI smoke commands pass. | smoke commands |

## 9.2 Manual gates

| Gate ID | Requirement | Evidence |
|---|---|---|
| UIP-MANUAL-001 | Header/card/progress/badge/legend visible in screenshot. | final screenshot path |
| UIP-MANUAL-002 | Board line art is not cropped or distorted. | final screenshot path |
| UIP-MANUAL-003 | `stay_open` leaves the final board inspectable. | reviewer note |
| UIP-MANUAL-004 | OS close exits cleanly. | reviewer note |

---

## 10. Implementation Guardrails for LLM Coding Agents

## 10.1 File ownership guardrails

Do not place status grouping logic in `status_panel.py`.

Do not place drawing logic in `status_text.py`.

Do not place geometry logic in `pygame_loop.py`.

Do not place playback speed math in `pygame_loop.py`.

Do not place config model changes in rendering modules.

Do not place artifact path discovery in rendering or playback modules.

## 10.2 Dependency guardrails

Allowed new imports by file:

| File | Allowed new imports |
|---|---|
| `status_view_model.py` | `dataclasses`, `typing`, existing `status_text`, `ColorPalette` type if safe |
| `window_chrome.py` | `typing` only if needed |
| `status_panel.py` | existing rendering model types only; no pygame import required |
| `pygame_adapter.py` | no new third-party imports; keep lazy pygame import through `importlib` |
| `pygame_loop.py` | new rendering helpers only |
| `window_geometry.py` | `dataclasses`, `math` if needed |

Forbidden new imports anywhere in polish work:

```text
jsonschema
PIL
Pillow
cv2
numpy in rendering/status_panel.py
pygame in non-rendering packages
matplotlib
network libraries
```

## 10.3 Naming guardrails

Use exact names:

```text
StatusPanelViewModel
MetricCardSpec
ProgressSpec
LegendItemSpec
CompletionBadgeSpec
RectSpec
WindowGeometry
build_status_panel_view_model
draw_status_panel_view_model
draw_header_strip
draw_board_border
draw_vertical_divider
```

Do not invent near-duplicate names such as:

```text
StatusCardThing
DashboardModel
PrettyPanel
ChromeRendererGod
```

## 10.4 Error guardrails

No polish function should raise for missing optional visual space. If a panel is too narrow or too short, draw as much as possible and let clipping happen naturally. Validation belongs in config and geometry, not in drawing.

Use typed existing errors only if a caller passes impossible programmatic values. For example:

```text
negative board dimensions -> geometry/domain error
negative progress totals -> clamp in view model unless impossible contract violation
missing font -> allow no text blit, but keep rect drawing in fake tests
```

---

## 11. Exact Patch Sequence

Apply patches in this exact order:

```text
1. Add/modify tests for window geometry expected rects.
2. Implement enriched geometry while preserving scalar fields.
3. Add status_view_model tests.
4. Implement status_view_model.py.
5. Extend pygame fakes and adapter tests.
6. Extend pygame_adapter.py.
7. Add status_panel polished drawing tests.
8. Implement draw_status_panel_view_model(...).
9. Add window_chrome tests.
10. Implement window_chrome.py.
11. Add/modify board_surface tests for clear_surface=False and origin handling.
12. Update board_surface.py.
13. Modify pygame_loop tests for composed draw order.
14. Update pygame_loop.py.
15. Update cli command tests.
16. Update cli/commands.py.
17. Update docs and traceability rows.
18. Run targeted tests.
19. Run full unittest discovery.
20. Run CLI smoke commands.
21. Run manual demo and capture screenshot evidence.
```

Do not batch all changes into one giant patch.

---

## 12. Targeted Validation Commands

Run after Phase 1:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_window_geometry
```

Run after Phase 2:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_status_text
python -m unittest tests.demo.iter9_visual_solver.test_status_view_model
```

Run after Phase 3:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_pygame_adapter_contract
```

Run after Phase 4:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_status_panel
```

Run after Phase 5:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_window_chrome
```

Run after Phase 6:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
python -m unittest tests.demo.iter9_visual_solver.test_cli_commands
```

Run final verification:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

---

## 13. Documentation Update Checklist

Update these docs only after source/tests are clear:

```text
demo/docs/pygame_rendering_contract.md
demo/docs/status_panel_contract.md
demo/docs/window_sizing_contract.md
demo/docs/testing_methodology.md
demo/docs/completion_gate.md
demo/docs/traceability_matrix.md
```

Required doc additions:

```text
status_view_model.py ownership
window_chrome.py ownership
header strip behavior
completion badge behavior
progress bar denominator rules
legend behavior
board border/divider behavior
new tests and gates
manual screenshot checklist
```

Do not update config schema docs unless config fields are added.

Do not update base project docs unless they already mention the visual demo and become inaccurate.

---

## 14. Rollback Plan

If polish integration causes regressions:

1. Revert `pygame_loop.py` to call existing `draw_status_panel(...)` with raw `build_status_lines(...)`.
2. Keep `status_view_model.py` and tests only if they pass and are unused.
3. Keep `window_geometry.py` scalar fields intact.
4. Disable header/chrome drawing by not calling `window_chrome.py` functions.
5. Do not alter artifact loaders or playback policy to compensate.

Rollback must preserve:

```text
config loading
final-grid replay
speed policy
finish policy
raw status line display
OS window close behavior
```

---

## 15. Final Signoff Template

```text
Implementation date:
Reviewer:
Git commit:
Changed runtime files:
Changed test files:
Changed docs:
Targeted test results:
Full unittest discovery result:
CLI smoke result:
Manual command:
Input run directory:
Config path:
Screenshot path during playback:
Screenshot path after completion:
Observed board dimensions:
Observed mines flagged:
Observed safe cells solved:
Observed unknown remaining:
Observed finish behavior:
Known approved exceptions:
Final decision: accepted / rejected
```

---

## 16. Final Completion Definition

The UI polish implementation is complete only when all of the following are true:

```text
Status lines still show all required real values.
Header strip renders without covering the board.
Board render area remains aspect-correct and unclipped.
Status panel renders badge, cards, progress bars, and legend.
Progress bars use correct denominators.
Zero unknown cells produces a solved visual state.
Pygame imports remain inside allowed rendering paths.
Rendering does not load artifacts or validate config.
Pygame loop does not calculate playback speed.
Existing finish behavior still honors stay_open, close_immediately, and close_after_delay.
All targeted demo tests pass.
Full unittest discovery passes.
Existing Iter9 CLI smoke commands pass.
Manual screenshot evidence confirms the polished interface.
```
