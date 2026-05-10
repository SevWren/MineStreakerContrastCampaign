# Gameworks — Architecture

## Overview

`gameworks` is structured as a strict **two-layer system**: a pure-logic engine and a Pygame renderer. They communicate through a single shared reference to the `GameEngine` object. No rendering code is in the engine; no logic is in the renderer.

```
┌──────────────────────────────────────────────────────┐
│                    main.py                           │
│             GameLoop (state machine)                 │
│   MENU → PLAYING → RESULT → MENU                     │
│                                                      │
│   builds GameEngine  ←──────────────────────────┐   │
│   builds Renderer(engine)                        │   │
│   dispatches events → engine.left/right/middle   │   │
│   feeds results → renderer.cascade / win_anim    │   │
└──────────┬───────────────────────┬───────────────┘   │
           │                       │                   │
           ▼                       ▼                   │
┌──────────────────┐   ┌───────────────────────────┐  │
│   engine.py      │   │      renderer.py           │  │
│                  │   │                            │  │
│  Board           │   │  Renderer                  │  │
│  GameEngine      │◄──│    .engine  (ref)          │  │
│  MoveResult      │   │    .board   (ref)          │  │
│  CellState       │   │  AnimationCascade          │  │
│  place_random_   │   │  WinAnimation              │  │
│    mines()       │   │  helper fns (rrect, pill…) │  │
│  load_board_     │   └───────────────────────────┘  │
│    from_npy()    │                                   │
│  load_board_     │                                   │
│    from_pipeline │                                   │
└──────────────────┘                                   │
```

---

## Module Responsibilities

### `engine.py` — Pure Game Logic

No Pygame imports. No I/O beyond NumPy file loading. Fully testable in headless environments.

**Responsibilities:**
- Board construction and mine placement (`Board`, `place_random_mines`)
- Cell state management: revealed / flagged / questioned / mine
- Flood-fill reveal and chording logic
- Win detection
- Scoring: points, streak multiplier, penalties
- Board loading from `.npy` files (two formats) and from the SA pipeline
- `GameEngine`: lifecycle (start, restart, stop_timer), player actions, difficulty presets

**Key design choice:** Mine hits are score penalties — the game does **not** end on a mine hit. The `Board._state` can only transition to `"won"`, never `"lost"` via normal play (the `"lost"` code path exists but is unused in the current design).

---

### `renderer.py` — Pygame Rendering

No game-logic decisions. Reads engine/board state; never mutates it.

**Responsibilities:**
- Window creation and auto-scaling for large boards
- Per-frame drawing: tiles, HUD header, side panel, overlays
- Clipped, viewport-culled rendering for large boards (only visible tiles drawn)
- Pre-rendered caches to avoid per-frame `font.render()` calls
- Input event handling: translates raw Pygame events into action strings (`"click:x,y"`, `"flag:x,y"`, `"chord:x,y"`, `"restart"`, `"quit"`, `"save"`)
- Animation subsystems: `AnimationCascade` (reveal wave), `WinAnimation` (flag reveal sequence)
- Image ghost overlay (source image visible through correctly-flagged mine tiles)
- Fog-of-war toggle
- Modal overlays: victory, help

**Key design choice:** The renderer returns action strings from `handle_event()` instead of calling engine methods directly. `GameLoop` (in `main.py`) is the dispatcher.

---

### `main.py` — Entry Point and Game Loop

**Responsibilities:**
- CLI argument parsing (`build_parser`)
- `GameLoop` state machine: `MENU → PLAYING → RESULT → MENU`
- Constructing `GameEngine` from CLI args
- Constructing `Renderer` from the engine
- Dispatching renderer action strings to engine methods
- Passing `MoveResult.newly_revealed` lists to `AnimationCascade`
- Triggering win animation on state transition to `"won"`

---

## Class Relationships

```
GameLoop
 ├── _engine: GameEngine
 │    └── board: Board
 │         ├── _mine:       ndarray(H, W, bool)
 │         ├── _revealed:   ndarray(H, W, bool)
 │         ├── _flagged:    ndarray(H, W, bool)
 │         ├── _questioned: ndarray(H, W, bool)
 │         └── _neighbours: ndarray(H, W, uint8)
 └── _renderer: Renderer
      ├── engine: GameEngine  (shared ref)
      ├── board:  Board       (shared ref)
      ├── cascade:    AnimationCascade | None
      └── win_anim:   WinAnimation | None
```

---

## State Machines

### GameLoop States (`main.py`)

```
         ┌─────────────────────────────┐
         │                             │
         ▼                             │  restart / new game
       MENU ──► PLAYING ──► RESULT ────┘
                  │
                  │  engine.state == "won"
                  ▼
                RESULT
```

- `MENU`: transient; immediately calls `_start_game()` on first `run()`.
- `PLAYING`: normal gameplay. Handles left/right/chord clicks.
- `RESULT`: win screen. Displays victory modal after win animation completes.
- Transition back to `PLAYING` on restart.

### Board States (`engine.py → Board._state`)

```
  "playing" ──► "won"    (all safe cells revealed)
```

Note: `"lost"` is defined in the code for API completeness but is never set during normal play. Mine hits are penalties, not terminal events.

### Flag Cycle (`Board.toggle_flag`)

```
  hidden ──► flag ──► question ──► hidden ──► ...
```

---

## Data Flow: Left Click

```
User left-clicks (x, y)
        │
        ▼
Renderer.handle_event(ev)
  └─► returns "click:x,y"
        │
        ▼
GameLoop._do_left_click(x, y)
  │
  ├─► GameEngine.left_click(x, y)
  │     ├─► [first click] regenerate board if (x,y) is a mine
  │     ├─► Board.reveal(x, y)
  │     │     ├─► flood-fill reveal for zero-count cells
  │     │     └─► returns (hit_mine, newly_revealed)
  │     ├─► score += REVEAL_POINTS[n] * streak_multiplier  (or apply MINE_HIT_PENALTY)
  │     └─► returns MoveResult
  │
  └─► if MoveResult.newly_revealed:
        Renderer.cascade = AnimationCascade(newly_revealed)
```

---

## Rendering Pipeline (per frame)

```
Renderer.draw(mouse_pos, game_state, elapsed, cascade_done)
  │
  ├── _win.fill(bg)
  ├── _draw_board(mouse_pos, game_state, cascade_done)
  │     ├── draw board background + border
  │     ├── set clip rect to board area
  │     ├── _draw_image_ghost()          [if image mode]
  │     ├── for each visible tile (viewport-culled):
  │     │     _draw_cell(x, y, CellState, pos, in_anim, is_pressed, fog, ts, in_win_anim)
  │     ├── _draw_loss_overlay()         [if game_state == "lost"]
  │     └── _draw_win_animation_fx()     [if game_state == "won" and win_anim running]
  ├── _draw_overlay()                    [fog of war]
  ├── _draw_panel(mouse_pos, game_state, elapsed)
  ├── _draw_header(elapsed, game_state)
  └── display.flip()
```

---

## Performance Considerations

| Concern | Solution |
|---|---|
| Large boards (300×370 = 111,000 cells) | Viewport culling: only cells within the visible window rect are drawn |
| Per-frame font.render() for digits | Pre-rendered `_num_surfs` cache; rebuilt only on tile size change |
| Per-frame image rescaling | `_ghost_surf` and `_thumb_surf` cached; rebuilt only on board size change |
| Per-frame SRCALPHA surface allocation | `_anim_surf`, `_hover_surf`, `_fog_surf` reused across frames |
| Neighbour count computation at board construction | scipy.ndimage.convolve; O(H×W) vs O(H×W×9) naive loop |
| Mine/flag position queries during rendering | numpy.where on array slices; no Python-level per-cell loop |

---

## Board Loading Formats

Two `.npy` encodings are supported; auto-detected at load time:

| Format | Encoding | Producer |
|---|---|---|
| Pipeline format | `int8`: `1` = mine, `0` = safe | `run_iter9.py` pipeline output |
| Game save format | `int8`: `-1` = mine, `0–8` = neighbour count | `GameLoop._save_npy()` |

Detection: if `grid.min() >= 0` and `grid.max() <= 1`, pipeline format is assumed.

---

## Dependency Boundaries

```
main.py     imports  engine.py, renderer.py
renderer.py imports  engine.py (Board, CellState, GameEngine, MoveResult)
engine.py   imports  numpy, scipy (NO pygame)
```

The engine has zero knowledge of the renderer. This allows the engine to be tested in headless environments without a display server.

---

## See Also

- [API_REFERENCE.md](API_REFERENCE.md) — Detailed class and method signatures
- [GAME_DESIGN.md](GAME_DESIGN.md) — Scoring model and game rules
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — How to run tests and extend the package
