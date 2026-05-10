# Gameworks — Game Design Document

## Overview

Mine-Streaker Minesweeper is a variant of classic Minesweeper with two key departures from the traditional rules:

1. **No game-over on mine hit.** Stepping on a mine applies a score penalty and the game continues. Victory is achieved solely by revealing all safe cells.
2. **Image-reveal mode.** Mine positions are generated from a source image via a simulated-annealing pipeline. Correctly flagging mines progressively reveals the source image.

---

## Win / Loss Conditions

| Condition | Result |
|---|---|
| All safe cells revealed | Win — victory modal displayed |
| Mine hit | Score penalty; game **continues** |
| Flag placed on safe cell | Score penalty; flag can be removed |

There is no lose state. Players can hit as many mines as they wish — the game ends only when every non-mine cell has been revealed.

---

## Board Modes

### Classic Random

Standard Minesweeper. Mines placed uniformly at random excluding the first-click cell and its 3×3 neighbourhood (guaranteed safe first click).

Default mine count: `max(1, width × height ÷ 6)` when `--mines 0` (the default).

### Difficulty Presets

| Preset | Width | Height | Mines | Mine Density |
|---|---|---|---|---|
| Easy | 9 | 9 | 10 | ~12% |
| Medium | 16 | 16 | 40 | ~16% |
| Hard | 30 | 16 | 99 | ~21% |

### Image-Reveal Mode

Mine positions are derived from a source image by the MineStreaker SA (simulated annealing) pipeline. Darker regions of the image correspond to higher mine density. Correctly-flagged mines are rendered as translucent image tiles, progressively revealing the picture as flags are placed.

### Pre-built Board (`.npy` Load)

Loads a board from a NumPy file. Supports both pipeline-format (`0`/`1`) and game-save format (`-1`/`0–8`). Useful for reproducible testing and sharing specific boards.

---

## Core Mechanics

### Reveal (Left Click)

- Clicking a hidden, unflagged cell reveals it.
- If the revealed cell has zero adjacent mines, a flood-fill expands the reveal to all connected zero-count cells and their numbered borders.
- If the cell is a mine, a score penalty is applied (see Scoring) and the cell is marked revealed. The game continues.
- The first click is always safe. If the clicked cell would be a mine, the board is regenerated with the click position (and its 3×3 neighbourhood) excluded.

### Flag Cycle (Right Click)

Right-clicking a hidden cell cycles through three states:

```
hidden → flag (🚩) → question (?) → hidden
```

- Placing a flag on a mine: score bonus.
- Placing a flag on a safe cell: score penalty (reversed if the flag is removed).
- Removing a correct flag (cycling to `?`): score bonus reversed.
- Revealed cells cannot be flagged.

### Chord (Middle Click or Ctrl + Left Click)

Chording reveals all unflagged neighbours of a revealed number-cell when the number of adjacent flags equals the cell's mine count. If any flagged neighbour is wrong (a safe cell was flagged), those unrevealed cells are revealed as mines and a penalty applies.

Chording is a no-op when:
- The cell is unrevealed.
- The cell has 0 adjacent mines.
- The number of adjacent flags does not match the cell's number.

### Flood-Fill Semantics

Flood-fill expands only to cells that are:
- Not revealed
- Not flagged
- Not mines

Mines act as flood-fill barriers. The expansion stops at numbered cells (they are added to the newly-revealed set but do not propagate further).

---

## Scoring System

### Base Points

Points are awarded for each cell revealed (per `REVEAL_POINTS` indexed by neighbour count):

| Neighbour count | Points |
|---|---|
| 0 (empty) | 1 |
| 1 | 5 |
| 2 | 10 |
| 3 | 20 |
| 4 | 35 |
| 5 | 55 |
| 6 | 80 |
| 7 | 110 |
| 8 | 150 |

Higher-numbered cells are worth more because they require more deductive reasoning to safely reveal.

### Flag Scoring

| Action | Score Change |
|---|---|
| Flag placed on a mine | +50 × streak_multiplier |
| Flag placed on a safe cell | −25 |
| Correct flag reversed (→ question) | −50 (reversal of bonus) |
| Wrong flag reversed (→ question) | +25 (reversal of penalty) |

### Mine Hit Penalty

Each mine hit deducts **250 points** (floored at 0). The streak counter resets to 0.

### Streak Multiplier

The streak counter increments by 1 after each successful reveal action (left-click or chord that does not hit a mine). Mine hits and flag actions reset the streak to 0.

| Streak | Multiplier |
|---|---|
| 0–4 | 1.0× |
| 5–9 | 1.5× |
| 10–14 | 2.0× |
| 15–24 | 3.0× |
| 25+ | 5.0× |

The multiplier applies to all reveal points and correct-flag bonuses.

### Score Floor

The score cannot go below zero: `score = max(0, score - penalty)`.

---

## Visual Feedback

### Mine Flash

When a mine is hit, the cell background flashes red for **1.5 seconds**. This is implemented via `GameEngine.mine_flash`, a `dict` mapping `(x, y)` to an expiry timestamp (monotonic clock). The renderer reads this dict and applies the flash without any engine-side timer logic.

### Cascade Animation

When cells are revealed (including flood-fill results), they animate open one-by-one at `ANIM_TICK` (0.035 s/tile). The `AnimationCascade` object is created by `GameLoop` from the `MoveResult.newly_revealed` list.

### Win Animation

On victory, the `WinAnimation` object progressively reveals flagged cells in the order: correct flags (shuffled), then wrong flags (shuffled). In image mode, each revealed flag shows the corresponding pixel strip of the source image at full opacity.

After the animation completes, the victory modal is displayed.

### Fog of War

The fog toggle (`F` key or panel button) overlays a semi-transparent dark mask over the entire window, with the board area punched out. This is a cosmetic feature.

### Smiley State

The header smiley button reflects game state:
- `playing` — yellow with neutral expression
- `won` — green with smile
- `lost` — red with frown (defined but not currently triggered)

---

## HUD Layout

### Header Bar

```
[ M:xxx ]   [ smiley (restart) ]   [ T:000   SCORE: 000000 ]
                                   [ STREAK x15   3.0×      ]
```

- **M:** mines remaining (total mines − flags placed; can go negative with over-flagging).
- **Smiley:** clickable restart button; face reflects game state.
- **T:** elapsed time in seconds.
- **SCORE:** current score; turns yellow when streak multiplier > 1×.
- **STREAK:** shown only when streak ≥ 5.

### Side Panel / Bottom Panel

| Element | Description |
|---|---|
| Restart / New Game buttons | Trigger game restart |
| Help button | Toggle help overlay |
| Toggle Fog button | Toggle fog of war |
| Save .npy button | Save current board grid |
| Stats block | Board size, mine count, safe cells left, flags placed, time |
| Tips block | Keyboard/mouse reference |
| Mode badge | "Mode: Image-Reveal" or "Mode: Classic" |
| Image thumbnail | Small preview of the source image (image mode only) |

---

## First-Click Safety

On the very first left-click of a game:
- The game timer starts.
- If the clicked cell contains a mine, the board is regenerated: mines are re-placed with `seed+1`, excluding the click cell and its entire 3×3 neighbourhood.
- This guarantees the first reveal is always safe.

First-click safety does not apply to chording or subsequent clicks.

---

## Panning and Zooming

For boards larger than the display, the board is pannable via:
- Mouse drag (left-button hold + move)
- Scroll wheel (zoom, centered on cursor position)
- Arrow keys

Pan is clamped so the board never moves more than one viewport-width off screen.

Zoom updates the tile size incrementally (`step = max(2, tile // 4)`) and adjusts pan to keep the point under the cursor fixed in screen space.

---

## Board Sizing and Auto-Scale

For boards with ≥ 100 tiles on either axis, the tile size is auto-computed at `Renderer.__init__`:

```
scale_w = (TARGET_SCREEN_W - PANEL_W - 2*PAD) / board_width
scale_h = (TARGET_SCREEN_H - HEADER_H - 2*PAD) / board_height
tile_size = max(MIN_TILE_SIZE, int(min(scale_w, scale_h)))
```

`MIN_TILE_SIZE` = 10 px, `TARGET_SCREEN_W` = 1400 px, `TARGET_SCREEN_H` = 850 px.

---

*Gameworks v0.1.1*
