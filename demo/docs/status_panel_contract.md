# Iter9 Visual Solver Demo — Status Panel Contract

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Demo status/display architecture |
| Applies to | `domain/status_snapshot.py`, `rendering/status_text.py`, `rendering/status_panel.py` |
| Required before | status snapshot implementation, status text implementation, status panel rendering, GUI acceptance |
| Traceability IDs | DEMO-REQ-001, DEMO-REQ-002, DEMO-REQ-004, DEMO-REQ-005, DEMO-TEST-019, DEMO-TEST-020 |
| Change rule | Any status field addition/removal must update this contract, config schema/docs, status tests, acceptance criteria, and traceability matrix. |

---

## 1. Purpose

This contract defines the exact status values, status text lines, visibility rules, update behavior, and drawing boundaries for the Iter9 Visual Solver Demo status panel.

The status panel exists to make the non-interactive demo understandable while the board is solving visually.

---

## 2. Scope

This contract applies to:

```text
demos/iter9_visual_solver/domain/status_snapshot.py
demos/iter9_visual_solver/rendering/status_text.py
demos/iter9_visual_solver/rendering/status_panel.py
tests/demo/iter9_visual_solver/test_status_text.py
tests/demo/iter9_visual_solver/test_status_panel.py
```

This contract does not own:

```text
playback speed calculation
event scheduling
pygame window creation
artifact loading
config validation
```

---

## 3. Required Status Lines

The MVP status panel MUST support these lines:

```text
Source image: <source image name>
Board: <board_width> x <board_height>
Seed: <seed>
Total cells: <board_width * board_height>
Mines flagged: <mines_flagged> / <total_mines>
Safe cells solved: <safe_cells_solved> / <safe_cells>
Unknown remaining: <unknown_remaining>
Playback speed: <events_per_second> cells/sec
Elapsed time: <seconds>s
Finish: <running|complete|waiting|closed>
Replay source: <final_grid_replay|solver_trace>
```

The user-provided conceptual display block is supported, but placeholders MUST be replaced with actual values:

```text
Board: 300 x derived-height
```

is forbidden in runtime output.

Required final display form:

```text
Board: 300 x 942
```

or whatever the actual loaded grid dimensions are.

---

## 4. Data Ownership

## 4.1 `domain/status_snapshot.py`

Required API:

```python
from dataclasses import dataclass

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
    safe_cells: int
    unknown_remaining: int
    events_per_second: int
    elapsed_time_s: float
    finish_state: str
    replay_source: str
```

Optional future fields:

```text
current_step
total_events
percent_complete
fps_observed
```

Optional fields MUST NOT be displayed unless included in config/schema and tests.

## 4.2 `rendering/status_text.py`

Required API:

```python
def build_status_lines(
    snapshot: StatusSnapshot,
    visibility: StatusPanelVisibilityConfig,
) -> list[str]: ...
```

Required behavior:

- Converts snapshot values into strings.
- Applies visibility config.
- Does not draw fonts.
- Does not import pygame.
- Does not parse metrics JSON.
- Does not calculate playback speed.

## 4.3 `rendering/status_panel.py`

Required API:

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

- Draws already-built lines.
- Does not compute status values.
- Does not parse metrics.
- Does not own visibility decisions unless passed final lines.

---

## 5. Field Definitions

| Field | Type | Source | Runtime Owner | Display Rule |
|---|---|---|---|---|
| `source_image_name` | string | metrics/source image config | `io/metrics_loader.py` or demo input builder | show exact file name |
| `board_width` | integer | `BoardDimensions.from_grid()` | `domain/board_dimensions.py` | show as first number |
| `board_height` | integer | `BoardDimensions.from_grid()` | `domain/board_dimensions.py` | show as second number |
| `seed` | integer | metrics/run identity | `io/metrics_loader.py` or demo input builder | show decimal integer |
| `total_cells` | integer | board dimensions | `domain/board_dimensions.py` | width * height |
| `mines_flagged` | integer | replay state | `playback/replay_state.py` | current count |
| `total_mines` | integer | grid/event source | `playback/event_source.py` or replay init | denominator |
| `safe_cells_solved` | integer | replay state | `playback/replay_state.py` | current count |
| `safe_cells` | integer | total cells - total mines | replay init | denominator |
| `unknown_remaining` | integer | replay state | `playback/replay_state.py` | current unknown count |
| `events_per_second` | integer | speed policy | `playback/speed_policy.py` | append `cells/sec` |
| `elapsed_time_s` | number | pygame loop clock | `pygame_loop.py` | one decimal or integer seconds |
| `finish_state` | enum string | replay/finish policy | `playback/replay_state.py`, `finish_policy.py` | show simple word |
| `replay_source` | enum string | event source selector | `playback/event_source.py` | show source |

---

## 6. Visibility Config

The status panel MUST honor these config booleans:

```text
status_panel.show_source_image
status_panel.show_board_dimensions
status_panel.show_seed
status_panel.show_total_cells
status_panel.show_mines_flagged
status_panel.show_safe_cells_solved
status_panel.show_unknown_remaining
status_panel.show_playback_speed
status_panel.show_elapsed_time
status_panel.show_finish_message
```

If a field is hidden, `status_text.py` must omit the line entirely.

No hidden field may leave blank placeholder rows unless an explicit layout option exists.

Polished status panel additions:

- `status_view_model.py` owns grouping existing status facts into badge, metric
  cards, progress bars, legend items, and source-preview placeholder metadata.
- `status_panel.py` owns drawing, wrapping, and clipping only; it must not parse
  metrics, load images, calculate playback speed, or calculate finish policy.
- The original source-image preview slot is reserved in the bottom-right corner
  of the status panel. Geometry sizes it from available panel space and
  source-image aspect when metrics provide source dimensions. Until image
  loading/rendering is implemented, this slot draws a graceful placeholder with
  the source image name when available.
- Metric cards may carry structured label/value rows in addition to raw status
  lines. Wide panels render labels and right-aligned values in compact rows;
  narrow panels wrap safely without calculating status values in the renderer.
- Missing or unloadable source images must not fail the demo.
- `draw_status_panel(...)` remains available for raw-line compatibility, while
  `draw_status_panel_view_model(...)` draws the polished panel.

---

## 7. Required Formatting Rules

## 7.1 Board dimensions

```text
Board: <width> x <height>
```

Examples:

```text
Board: 300 x 942
Board: 300 x 10
Board: 10 x 300
```

Forbidden:

```text
Board: 300 x derived-height
Board: 300x942
Board: width=300 height=942
```

## 7.2 Total cells

```text
Total cells: 282600
```

Commas may be added only if tests expect them consistently. MVP default: no commas.

## 7.3 Mines flagged

```text
Mines flagged: 1250 / 1250
```

Denominator MUST be total mines, not total cells.

## 7.4 Safe cells solved

```text
Safe cells solved: 281350 / 281350
```

Denominator MUST be total safe cells.

## 7.5 Unknown remaining

```text
Unknown remaining: 0
```

## 7.6 Playback speed

```text
Playback speed: 12000 cells/sec
```

This display value MUST come from `speed_policy.py`, not from the pygame loop.

## 7.7 Finish message

Allowed finish states:

```text
running
complete
waiting
closing
closed
error
```

MVP display examples:

```text
Finish: running
Finish: complete - staying open
Finish: complete - closing in 3.0s
```

---

## 8. Update Behavior

The status snapshot MUST update when:

- playback starts
- event batch applies
- mines flagged count changes
- safe cells solved count changes
- unknown remaining changes
- playback completes
- finish policy state changes
- elapsed time changes

The status panel MAY redraw every frame.

The status text MUST NOT require every status value to change before redrawing.

---

## 9. Drawing Behavior

Status panel drawing MUST:

- fill panel background using configured/background palette.
- draw text lines top-to-bottom.
- use readable padding.
- avoid overlapping board area.
- avoid calculating text content.
- tolerate an empty list of lines.
- tolerate a panel narrower than ideal by clipping or wrapping according to implementation contract.

MVP recommended defaults:

```text
left padding: 12 px
top padding: 12 px
line spacing: 18–24 px
font size: 16 px or platform default equivalent
```

---

## 10. Error and Edge Behavior

| Case | Expected Behavior |
|---|---|
| missing source image name | show `Source image: unknown` or omit if hidden |
| seed missing | show `Seed: unknown` or omit if hidden |
| total mines unknown | use event source count or fail before playback if unavailable |
| total safe cells unknown | compute from total cells - total mines |
| unknown remaining below zero | bug; test must fail |
| mines flagged > total mines | bug; test must fail |
| safe solved > safe cells | bug; test must fail |
| panel width zero | no status panel drawn |
| empty line list | draw background only or no-op without error |

---

## 11. Forbidden Implementation Patterns

Forbidden in `status_text.py`:

```text
pygame
pygame.font
json.load
np.load
open(
Path(
calculate_events_per_second
```

Forbidden in `status_panel.py`:

```text
json.load
np.load
calculate_events_per_second
load_metrics
load_grid
```

Forbidden in status panel output:

```text
derived-height
<board_w * board_h>
<total_mines>
<safe_cells>
<n_unknown>
```

Placeholders MUST be resolved before display.

---

## 12. Required Tests

## 12.1 `test_status_text.py`

Required test cases:

- [ ] source image line formats correctly.
- [ ] board dimensions line uses actual grid-derived width and height.
- [ ] seed line formats correctly.
- [ ] total cells line formats correctly.
- [ ] mines flagged line uses current and total mine counts.
- [ ] safe cells solved line uses current and total safe counts.
- [ ] unknown remaining line formats correctly.
- [ ] playback speed line uses passed/calculated speed value.
- [ ] elapsed time line formats consistently.
- [ ] finish message changes after completion.
- [ ] hidden visibility fields are omitted.
- [ ] no placeholder strings appear.

## 12.2 `test_status_panel.py`

Required test cases:

- [ ] panel draws provided lines onto fake surface.
- [ ] panel uses injected fake font.
- [ ] panel handles empty lines.
- [ ] panel does not parse metrics.
- [ ] panel does not calculate status text.
- [ ] panel respects panel rectangle boundaries as defined by geometry.
- [ ] wide panels render structured metric label/value rows without wrapping common values.
- [ ] narrow panels still wrap or clip safely inside the panel.

## 12.3 Architecture tests

Required architecture assertions:

- [ ] `status_text.py` does not import pygame.
- [ ] `status_panel.py` does not import config loader or metrics loader.
- [ ] no status module calculates playback speed.

---

## 13. Acceptance Evidence

Required commands:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_status_text
python -m unittest tests.demo.iter9_visual_solver.test_status_panel
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
python -m unittest discover -s tests -p "test_*.py"
```

Manual evidence:

- [ ] screenshot showing status panel during playback.
- [ ] screenshot showing final complete state.
- [ ] final state screenshot contains no placeholders.

---

## 14. Completion Checklist

- [ ] `StatusSnapshot` exists.
- [ ] `build_status_lines()` exists.
- [ ] `draw_status_panel()` exists.
- [ ] All required status fields are represented.
- [ ] Visibility config is honored.
- [ ] No placeholder text is displayed.
- [ ] Status panel does not own playback/config/I/O logic.
- [ ] Unit tests and architecture tests pass.

---

## 15. Status View-Model Cache Rule

`status_view_model.py` may provide a factory that caches static view-model
parts such as legend items and card structure. Dynamic values from
`StatusSnapshot` must still update every frame.

Required behavior:

- [ ] cached static fields do not change playback counters.
- [ ] dynamic fields reflect the latest snapshot.
- [ ] status view-model code remains pygame-free.
- [ ] speed text remains owned by `status_text.py` and displays
      `Playback speed: <events_per_second> cells/sec`.
