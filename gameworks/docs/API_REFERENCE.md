# Gameworks — API Reference

This document covers the full public API of the `gameworks` package.
Internal/private members (prefixed `_`) are excluded unless noted where they are intentionally read by the renderer.

---

## Table of Contents

1. [Package](#package)
2. [engine.py](#enginepy)
   - [CellState](#cellstate)
   - [Board](#board)
   - [MoveResult](#moveresult)
   - [GameEngine](#gameengine)
   - [Module-Level Functions](#module-level-functions)
3. [renderer.py](#rendererpy)
   - [AnimationCascade](#animationcascade)
   - [WinAnimation](#winanimation)
   - [Renderer](#renderer)
   - [Module-Level Helpers](#module-level-helpers)
4. [main.py](#mainpy)
   - [GameLoop](#gameloop)
   - [build_parser](#build_parser)
   - [main](#main)
5. [Constants Reference](#constants-reference)

---

## Package

### `gameworks.__version__`

```python
__version__: str = "0.1.3"
```

Package version string.

---

## engine.py

### `CellState`

```python
@dataclass(frozen=True)
class CellState:
    is_mine:        bool = False
    is_revealed:    bool = False
    is_flagged:     bool = False
    is_questioned:  bool = False
    neighbour_mines: int = 0
```

Immutable snapshot of a single cell. Produced by `Board.snapshot()`. All fields are read-only (frozen dataclass).

> **Note (v0.1.1):** The renderer's hot cell loop no longer constructs `CellState` objects. Raw numpy `bool_`/`uint8` values are passed directly to `_draw_cell`. `CellState` is still used by `snapshot()` and may be used by callers outside the render loop.

| Field | Type | Description |
|---|---|---|
| `is_mine` | bool | Cell contains a mine |
| `is_revealed` | bool | Cell has been revealed by the player |
| `is_flagged` | bool | Cell has been flagged |
| `is_questioned` | bool | Cell is in the `?` state (post-flag cycle) |
| `neighbour_mines` | int | Count of adjacent mines (0–8); always 0 for mines |

---

### `Board`

Pure-logic Minesweeper board. All coordinate arguments use `(x, y)` == `(col, row)`. Internal NumPy arrays index `[row, col]`.

#### Constructor

```python
Board(width: int, height: int, mine_positions: Set[Tuple[int, int]])
```

| Parameter | Type | Description |
|---|---|---|
| `width` | int | Number of columns |
| `height` | int | Number of rows |
| `mine_positions` | Set[Tuple[int,int]] | Set of `(x, y)` mine coordinates |

Neighbour counts are pre-computed at construction via `scipy.ndimage.convolve`.

#### Read-Only Properties

| Property | Type | Description |
|---|---|---|
| `width` | int | Board width in tiles |
| `height` | int | Board height in tiles |
| `total_mines` | int | Total number of mines |
| `total_safe` | int | `width * height - total_mines` |
| `revealed_count` | int | Total revealed cells (includes mine-hit cells) — O(1) dirty-int counter |
| `safe_revealed_count` | int | Revealed non-mine cells only — O(1) dirty-int counter |
| `flags_placed` | int | Number of flagged cells — O(1) dirty-int counter |
| `questioned_count` | int | Number of `?`-marked cells — O(1) dirty-int counter |
| `mines_remaining` | int | `total_mines - flags_placed` (may be negative) |
| `correct_flags` | int | Flags placed on actual mines |
| `is_won` | bool | `True` when `_state == "won"` |
| `is_lost` | bool | `True` when `_state == "lost"` (unused in current play) |
| `game_over` | bool | `True` when `_state in ("won", "lost")` |

#### Methods

```python
def reveal(self, x: int, y: int) -> Tuple[bool, List[Tuple[int, int]]]
```

Reveal cell `(x, y)`. Returns `(hit_mine, newly_revealed_positions)`.

- If the cell is already revealed or flagged, returns `(False, [])`.
- If the cell is a mine: marks it revealed, returns `(True, [(x, y)])`. Game continues (no state transition to "lost").
- If the cell is safe: flood-fills all connected zero-count cells. Returns `(False, [(x0,y0), ...])`.
- Sets `_state = "won"` when `revealed_count == total_safe`.

```python
def toggle_flag(self, x: int, y: int) -> str
```

Cycle the cell's marker state. Returns the new state string.

| Current State | Next State | Return value |
|---|---|---|
| hidden | flag | `"flag"` |
| flag | question | `"question"` |
| question | hidden | `"hidden"` |
| revealed | (no-op) | `"hidden"` |

Sets `_state = "won"` if all safe cells are now also correctly covered after flagging.

```python
def snapshot(self, x: int, y: int) -> CellState
```

Return an immutable `CellState` for cell `(x, y)`.

```python
def chord(self, x: int, y: int) -> Tuple[bool, List[Tuple[int, int]]]
```

Chord action: if the number of flags adjacent to `(x, y)` equals its `neighbour_mines` count, reveals all unflagged neighbours. Returns `(hit_mine, newly_revealed)`. No-op if `(x, y)` is unrevealed or has zero neighbours.

```python
def all_mine_positions(self) -> List[Tuple[int, int]]
```

Returns `[(x, y), ...]` for every mine on the board.

```python
def wrong_flag_positions(self) -> List[Tuple[int, int]]
```

Returns `[(x, y), ...]` for every flag placed on a non-mine cell.

---

### `MoveResult`

```python
class MoveResult:
    success:        bool
    hit_mine:       bool
    newly_revealed: List[Tuple[int, int]]
    flagged:        str | bool   # flag state string from toggle_flag, or False
    state:          str          # board._state after the action
    score_delta:    int          # net score change (can be negative)
    streak:         int          # streak count after the action
    penalty:        int          # > 0 only when mine was hit
```

Returned by all `GameEngine` player-action methods. `__slots__` are used; no inheritance.

| Field | Type | Description |
|---|---|---|
| `success` | bool | Always `True` in current implementation |
| `hit_mine` | bool | `True` if a mine was hit this action |
| `newly_revealed` | list | Cells newly revealed this action (used to drive `AnimationCascade`) |
| `flagged` | str\|bool | Result of `toggle_flag` (`"flag"`, `"question"`, `"hidden"`) or `False` for non-flag actions |
| `state` | str | Board state after action: `"playing"` or `"won"` |
| `score_delta` | int | Score change this action (negative for penalties) |
| `streak` | int | Streak count after this action |
| `penalty` | int | `MINE_HIT_PENALTY` value when `hit_mine` is `True`, else 0 |

---

### `GameEngine`

Ties `Board` state to player input. Manages scoring, streak, timer, and first-click safety.

#### Constructor

```python
GameEngine(
    mode:       str = "random",   # "random" | "image" | "npy"
    width:      int = 16,
    height:     int = 16,
    mines:      int = 0,          # 0 = auto (width*height // 6)
    image_path: str = "",         # required when mode="image"
    npy_path:   str = "",         # required when mode="npy"
    seed:       int = 42,
)
```

| Parameter | Type | Description |
|---|---|---|
| `mode` | str | `"random"` — random mines; `"image"` — pipeline from image; `"npy"` — load file |
| `width` | int | Board width (random mode only) |
| `height` | int | Board height (random mode only) |
| `mines` | int | Mine count; `0` = `max(1, width*height // 6)` |
| `image_path` | str | Source image path (image mode only) |
| `npy_path` | str | Path to `.npy` board file (npy mode only) |
| `seed` | int | Random seed |

#### Class Method

```python
@classmethod
def from_difficulty(cls, diff: str, seed: int = 42) -> GameEngine
```

Create a `GameEngine` from a named difficulty preset.

| `diff` | Width | Height | Mines |
|---|---|---|---|
| `"easy"` | 9 | 9 | 10 |
| `"medium"` | 16 | 16 | 40 |
| `"hard"` | 30 | 16 | 99 |

#### Public Attributes

| Attribute | Type | Description |
|---|---|---|
| `board` | Board | The current board (may be replaced on first-click safety regeneration) |
| `mode` | str | Board mode: `"random"`, `"image"`, or `"npy"` |
| `seed` | int | Current random seed (incremented on restart) |
| `image_path` | str | Source image path (image mode) |
| `npy_path` | str | `.npy` file path (npy mode) |
| `score` | int | Current score (non-negative) |
| `streak` | int | Consecutive safe-action streak counter |
| `mine_flash` | dict | `{(x, y): expiry_time}` — cells flashing after mine hit; read by renderer |

#### Properties

| Property | Type | Description |
|---|---|---|
| `elapsed` | float | Seconds since game start; frozen when game is over |
| `state` | str | `board._state`: `"playing"` or `"won"` |
| `streak_multiplier` | float | Score multiplier from current streak (see scoring tiers) |

#### Methods

```python
def start(self) -> None
```

Initialize the timer. Call once after constructing the engine, before the game loop.

```python
def stop_timer(self) -> None
```

Freeze `elapsed`. Called automatically on win.

```python
def left_click(self, x: int, y: int) -> MoveResult
```

Reveal cell `(x, y)`. First click is always safe (board regenerated if needed). Mine hit applies `MINE_HIT_PENALTY` and resets streak; safe reveal awards `REVEAL_POINTS[n] * streak_multiplier`.

```python
def right_click(self, x: int, y: int) -> MoveResult
```

Cycle flag state at `(x, y)`. Correct flag awards `CORRECT_FLAG_BONUS * multiplier`; wrong flag deducts `WRONG_FLAG_PENALTY`. Reversing a correct flag (flag→question) reverses the bonus.

```python
def middle_click(self, x: int, y: int) -> MoveResult
```

Chord action at `(x, y)`. Reveals unflagged neighbours if flag count matches the cell's number. Scoring same as `left_click`.

```python
def restart(
    self,
    width:  int | None = None,
    height: int | None = None,
    mines:  int | None = None,
) -> None
```

Reset the engine in-place. Increments `seed`. Reuses the same mode (random/image/npy). Optional `width`/`height`/`mines` override board dimensions.

```python
def dev_solve_board(self) -> MoveResult
```

**DEV tool only.** Instantly reveals all safe cells and flags all mines via direct numpy array writes. Resyncs the four dirty-int counters (`_n_flags`, `_n_questioned`, `_n_safe_revealed`, `_n_revealed`) from array state after the bulk operation. Returns a `MoveResult` reflecting the solved state. Intended for development and testing; should not be called during normal gameplay.

---

### Module-Level Functions

```python
def place_random_mines(
    width:  int,
    height: int,
    count:  int,
    safe_x: int = -1,
    safe_y: int = -1,
    seed:   Optional[int] = None,
) -> Set[Tuple[int, int]]
```

Place `count` mines randomly. If `safe_x`/`safe_y` are valid coordinates, the cell and its 3×3 neighbourhood are excluded from mine placement.

```python
def load_board_from_npy(path: str) -> Board
```

Load a `Board` from a `.npy` file. Auto-detects pipeline format (`0`/`1`) vs game-save format (`-1`/`0–8`). Raises `ValueError` for wrong dimensions or neighbour-count mismatches.

```python
def load_board_from_pipeline(
    image_path: str,
    board_w:    int = 30,
    seed:       int = 42,
) -> Board
```

Run the MineStreaker SA pipeline to produce a `Board` from an image. Falls back to a random board if the pipeline imports fail.

---

## renderer.py

### `AnimationCascade`

Animates a set of newly-revealed tiles one-by-one over time.

```python
class AnimationCascade:
    def __init__(
        self,
        positions: List[Tuple[int, int]],
        speed:     float = ANIM_TICK,   # 0.035 s per tile
    )
```

| Property / Method | Description |
|---|---|
| `done: bool` | `True` when all positions have been shown |
| `current() -> List[Tuple[int,int]]` | Tiles visible so far (expands each frame) |
| `finished_after() -> float` | Estimated seconds until animation completes |

---

### `WinAnimation`

Animates the win sequence: flagged cells reveal progressively, showing the source image beneath.

```python
class WinAnimation:
    def __init__(
        self,
        board: Board,
        speed: float = 0.025,   # seconds per tile
    )
```

Correct flags animate first (in shuffled order), then wrong flags.

| Property / Method | Description |
|---|---|
| `done: bool` | `True` when all flagged cells have been revealed |
| `correct_done: bool` | `True` when the correct-flags phase is complete |
| `current() -> List[Tuple[int,int]]` | Flagged cells revealed so far |
| `finished_after() -> float` | Estimated total animation duration in seconds |

---

### `Renderer`

Owns the Pygame window and all rendering resources.

#### Constructor

```python
Renderer(
    engine:     GameEngine,
    image_path: Optional[str] = None,
)
```

Initializes Pygame, creates the window, auto-scales tile size for large boards, loads the image overlay if `image_path` is provided.

**Auto-scaling rule:** Boards with ≥ 100 tiles on either axis scale down from `BASE_TILE` (32 px) toward `MIN_TILE_SIZE` (10 px) so the board fits within `TARGET_SCREEN_W × TARGET_SCREEN_H` (1400 × 850 px).

#### Public Attributes

| Attribute | Type | Description |
|---|---|---|
| `engine` | GameEngine | Reference to the game engine |
| `board` | Board | Reference to `engine.board` |
| `help_visible` | bool | Whether the help overlay is shown |
| `fog` | bool | Whether fog-of-war is active |
| `cascade` | AnimationCascade \| None | Active reveal animation |
| `win_anim` | WinAnimation \| None | Active win animation |
| `pressed_cell` | Tuple[int,int] \| None | Cell under mouse button (for press visual) |
| `_show_dev` | bool | Whether the DEV TOOLS panel section is visible; toggled by `` ` `` (`K_BACKQUOTE`) |

#### Methods

```python
def handle_event(self, ev: pygame.event.Event) -> Optional[str]
```

Translate a Pygame event into an action string. Returns one of:

| Return value | Meaning |
|---|---|
| `"quit"` | Close the window |
| `"restart"` | Start a new game |
| `"save"` | Save board to `.npy` |
| `"click:x,y"` | Left-click reveal at `(x, y)` |
| `"flag:x,y"` | Right-click flag cycle at `(x, y)` |
| `"chord:x,y"` | Middle-click / Ctrl+click chord at `(x, y)` |
| `"dev:solve"` | DEV TOOLS "Solve Board" button clicked (only emitted when `_show_dev` is `True`) |
| `None` | No action (internal state updated, e.g. pan/zoom) |

```python
def draw(
    self,
    mouse_pos:    Tuple[int, int] = (0, 0),
    game_state:   str = "waiting",
    elapsed:      float = 0.0,
    cascade_done: bool = True,
) -> None
```

Render one frame. Call every tick of the game loop.

```python
def start_win_animation(self) -> None
```

Begin the win animation. Call once when `engine.state` transitions to `"won"`.

```python
def draw_victory(self, elapsed: float) -> None
```

Draw the victory modal overlay. Called after the win animation completes.

```python
def draw_defeat(self) -> None
```

Draw the defeat modal overlay. (Defined for API completeness; not called in current game flow as game never ends on mine hit.)

---

### Module-Level Helpers

```python
def rrect(surf: pygame.Surface, color, rect: Tuple[int,int,int,int], r: int = 4) -> None
```

Draw a filled rounded rectangle.

```python
def rrect_outline(surf: pygame.Surface, color, rect: Tuple[int,int,int,int], width: int = 1, r: int = 4) -> None
```

Draw a rounded-rectangle outline using polyline arcs.

```python
def pill(surf: pygame.Surface, color, rect: Tuple[int,int,int,int]) -> None
```

Draw a filled pill-shaped button (radius = height ÷ 2).

---

## main.py

### `GameLoop`

```python
class GameLoop:
    MENU    = "menu"
    PLAYING = "playing"
    RESULT  = "result"

    def __init__(self, args: argparse.Namespace)
    def run(self) -> None
```

Top-level state machine. `run()` blocks until the player quits. On return, `pygame.quit()` has been called.

Internal methods (not part of the public API but documented for contributors):

| Method | Description |
|---|---|
| `_build_engine() -> GameEngine` | Construct engine from CLI args |
| `_start_game() -> None` | Build engine + renderer, enter PLAYING state |
| `_do_left_click(x, y) -> None` | Delegate to `engine.left_click`; set cascade |
| `_do_right_click(x, y) -> MoveResult` | Delegate to `engine.right_click` |
| `_do_chord(x, y) -> None` | Delegate to `engine.middle_click`; set cascade |
| `_save_npy() -> None` | Save current board grid to timestamped `.npy` |

---

### `build_parser`

```python
def build_parser() -> argparse.ArgumentParser
```

Returns the configured argument parser for the `minesweeper` CLI. See [README.md](README.md) for the full flag reference.

---

### `main`

```python
def main() -> None
```

CLI entry point. Parses arguments, creates `GameLoop`, calls `run()`.

---

## Constants Reference

### Scoring Constants (`engine.py`)

| Constant | Value | Description |
|---|---|---|
| `REVEAL_POINTS` | `[1, 5, 10, 20, 35, 55, 80, 110, 150]` | Points per revealed cell, indexed by neighbour count (0–8) |
| `CORRECT_FLAG_BONUS` | `50` | Points for correctly flagging a mine |
| `WRONG_FLAG_PENALTY` | `25` | Points deducted for flagging a safe cell |
| `MINE_HIT_PENALTY` | `250` | Points deducted per mine stepped on |

### Streak Tiers (`engine.py`)

| Consecutive safe actions | Multiplier |
|---|---|
| 25+ | 5.0× |
| 15–24 | 3.0× |
| 10–14 | 2.0× |
| 5–9 | 1.5× |
| 0–4 | 1.0× (base) |

### Renderer Constants (`renderer.py`)

| Constant | Value | Description |
|---|---|---|
| `BASE_TILE` | `32` | Default tile size in pixels |
| `MIN_TILE_SIZE` | `10` | Minimum tile size after auto-scaling |
| `ANIM_TICK` | `0.035` | Seconds per tile in cascade animation |
| `FPS` | `30` | Target frames per second |
| `TARGET_SCREEN_W` | `1400` | Preferred window width |
| `TARGET_SCREEN_H` | `850` | Preferred window height |
| `PANEL_W` | `240` | Side panel width in pixels |
| `PANEL_H` | `520` | Side panel height in pixels |
| `PAD` | `12` | General padding in pixels |
| `HEADER_H` | `48` | Header bar height in pixels |
| `NUM_COLS` | list of `pygame.Surface` | Pre-rendered number surfaces indexed 1–8 (index 0 is `None`) |
| `TILE` | `32` (mutable) | Module-level current tile size; updated by `Renderer.__init__` |

---

*Gameworks v0.1.1*
