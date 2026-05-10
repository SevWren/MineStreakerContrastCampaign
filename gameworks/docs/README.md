# Gameworks — Mine-Streaker Interactive Minesweeper

`gameworks` is the interactive Pygame-based Minesweeper front-end for the Mine-Streaker project.
It supports three board modes:

| Mode | Description |
|---|---|
| **Classic random** | Standard Minesweeper with randomly-placed mines |
| **Pipeline image** | Mine layout generated from a source image via the MineStreaker SA pipeline |
| **Load `.npy`** | Pre-built board loaded from a NumPy file (pipeline output or game save) |

The game introduces a **no-game-over** mechanic: stepping on a mine deducts score (a penalty) but does not end the game. Victory is achieved by revealing all safe cells.

---

## Requirements

| Dependency | Version |
|---|---|
| Python | 3.10 – 3.12 recommended (3.13+ requires extra steps — see `requirements.txt`) |
| pygame | >= 2.3 |
| numpy | >= 1.24, < 3 |
| scipy | >= 1.10 |

Install game dependencies:

```bash
pip install pygame numpy scipy
```

Or install all project dependencies at once:

```bash
pip install -r requirements.txt
```

---

## Launch Modes

All launch modes use the module entry point from the project root:

```bash
python -m gameworks.main [OPTIONS]
```

### Classic Random Board

```bash
# Easy  — 9×9, 10 mines
python -m gameworks.main --random --easy

# Medium — 16×16, 40 mines
python -m gameworks.main --random --medium

# Hard  — 30×16, 99 mines
python -m gameworks.main --random --hard
```

### Load a Pre-Built Pipeline Board

```bash
python -m gameworks.main --load results/iter9/<run_id>/grid_iter9_300x300.npy
```

### Image-Reveal Mode

Runs the MineStreaker SA pipeline at launch (slow; requires Numba warmup):

```bash
python -m gameworks.main --image assets/tessa_line_art_stiletto.png --board-w 300
```

### Custom Board Size

```bash
python -m gameworks.main --random --board-w 20 --board-h 20 --mines 50 --seed 7
```

---

## CLI Reference

| Flag | Default | Description |
|---|---|---|
| `--image PATH` | — | Source image; activates image-reveal mode |
| `--load PATH` | — | Load a saved mine grid (`.npy`) |
| `--random` | — | Classic random-mine board |
| `--easy` | — | Difficulty preset: 9×9, 10 mines |
| `--medium` | — | Difficulty preset: 16×16, 40 mines |
| `--hard` | — | Difficulty preset: 30×16, 99 mines |
| `--board-w N` | 300 | Board width in tiles |
| `--board-h N` | 370 | Board height in tiles |
| `--mines N` | 0 (auto) | Mine count (0 = width×height÷6) |
| `--seed N` | 42 | Random seed for reproducibility |
| `--tile N` | 32 | Tile size in pixels |

---

## Controls

| Input | Action |
|---|---|
| Left-click | Reveal tile |
| Right-click | Place / cycle flag → ? → clear |
| Middle-click | Chord (reveal all neighbours when flag count matches) |
| Ctrl + Left-click | Chord (alternative) |
| Scroll wheel | Zoom in / out (centered on cursor) |
| Mouse drag | Pan the board |
| Arrow keys | Pan the board |
| `R` | Restart game |
| `H` | Toggle help overlay |
| `F` | Toggle fog of war |
| `ESC` | Quit |

The smiley button in the header also triggers a restart.

---

## Window Layout

```
┌──────────────────────────────────────────────────┐
│  M:xxx   [ smiley ]   T:000  SCORE:  0           │  ← Header (HEADER_H px)
├──────────────────────────────────────────────────┤
│                              │ CONTROLS           │
│                              │ [Restart]          │
│         BOARD                │ [Help]             │
│       (scrollable,           │ [Toggle Fog]       │
│        zoomable)             │ [Save .npy]        │
│                              │ [New Game]         │
│                              │ Stats...           │
└──────────────────────────────────────────────────┘
```

For large boards (≥ 100 tiles wide), the side panel moves below the board and the tile size is auto-scaled to fit the screen.

---

## Running Tests

```bash
# With display
pytest tests/test_gameworks_engine.py -v

# Headless (CI / no display server)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/test_gameworks_engine.py -v
```

---

## See Also

- [ARCHITECTURE.md](ARCHITECTURE.md) — Module breakdown and system design
- [GAME_DESIGN.md](GAME_DESIGN.md) — Scoring, rules, and mechanics in depth
- [API_REFERENCE.md](API_REFERENCE.md) — Full public API
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — Dev setup and extension guide

---

*Gameworks v0.1.1*
