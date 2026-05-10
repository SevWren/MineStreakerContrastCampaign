# Gameworks — Developer Guide

## Prerequisites

| Tool | Version |
|---|---|
| Python | 3.10 – 3.12 recommended |
| pip | latest |
| git | any recent version |

Python 3.13+ is not yet supported by pygame pre-built wheels on all platforms. See `requirements.txt` for a workaround.

---

## Environment Setup

```bash
# Clone the repository (frontend-game-mockup branch)
git clone --branch frontend-game-mockup \
    https://github.com/SevWren/MineStreakerContrastCampaign.git
cd MineStreakerContrastCampaign

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate          # Linux / macOS
# .venv\Scripts\Activate.ps1       # Windows PowerShell

# Install all dependencies
pip install -r requirements.txt
```

Minimum game-only install (no pipeline or benchmarking):

```bash
pip install pygame numpy scipy pytest
```

---

## Running the Game

```bash
# From the project root:
python -m gameworks.main --random --easy
python -m gameworks.main --random --medium
python -m gameworks.main --random --hard
```

See [README.md](README.md) for all launch modes and CLI flags.

---

## Running Tests

### Gameworks Engine Tests

```bash
# With a display
pytest gameworks/tests/ -v

# Headless (CI, no display server) — Linux / macOS
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v

# Headless — Windows (cmd)
set SDL_VIDEODRIVER=dummy && set SDL_AUDIODRIVER=dummy && pytest gameworks/tests/ -v
```

### Full Test Suite

```bash
# Linux / macOS
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m pytest gameworks/tests/ -q

# Windows (cmd)
set SDL_VIDEODRIVER=dummy && set SDL_AUDIODRIVER=dummy && python -m pytest gameworks/tests/ -q
```

The engine tests do not require Pygame or a display and cover:
- `Board.reveal` (safe reveal, mine hit, flood-fill)
- `Board.toggle_flag` (cycle, win-on-flag)
- `Board.chord`
- `GameEngine.left_click` (first-click safety, scoring)
- `GameEngine.right_click` (correct/wrong flag scoring)
- `GameEngine.from_difficulty` presets
- `load_board_from_npy` (pipeline format + game-save format)

---

## Project Structure (gameworks-relevant)

```
MineStreakerContrastCampaign/
├── gameworks/
│   ├── __init__.py      Version string
│   ├── engine.py        Pure logic (Board, GameEngine, scoring)
│   ├── renderer.py      Pygame rendering
│   ├── main.py          CLI entry + GameLoop
│   └── docs/            ← All gameworks documentation
├── tests/
│   └── test_gameworks_engine.py
└── requirements.txt
```

---

## Module Boundaries

Follow these rules when making changes:

| Module | Can import | Must NOT import |
|---|---|---|
| `engine.py` | `numpy`, `scipy`, stdlib | `pygame`, `renderer`, `main` |
| `renderer.py` | `engine`, `pygame`, `numpy`, stdlib | `main`, pipeline modules |
| `main.py` | `engine`, `renderer`, stdlib | pipeline modules (except inside `_build_engine`) |

The engine must remain headless and testable without a display server.

---

## Adding a New Board Mode

1. Add a new `mode` string (e.g. `"csv"`) to `GameEngine.__init__`.
2. Add a corresponding loader function in `engine.py` (pattern: `load_board_from_csv(path) -> Board`).
3. Add a CLI flag in `main.py → build_parser()`.
4. Handle the new mode in `GameLoop._build_engine()`.
5. Handle it in `GameEngine.restart()` if the board should be reloadable.
6. Add tests in `tests/test_gameworks_engine.py`.

---

## Adding a New Scoring Rule

All scoring constants are at the top of `engine.py`:

```python
REVEAL_POINTS      = [1, 5, 10, 20, 35, 55, 80, 110, 150]
CORRECT_FLAG_BONUS = 50
WRONG_FLAG_PENALTY = 25
MINE_HIT_PENALTY   = 250
STREAK_TIERS       = [(25, 5.0), (15, 3.0), (10, 2.0), (5, 1.5), (0, 1.0)]
```

To modify scoring:
- Edit the constants directly; they are not exposed in settings files.
- Update `GAME_DESIGN.md` to reflect the change.
- The streak multiplier lookup is in `GameEngine.streak_multiplier` (property); add tiers there.

---

## Adding a New Animation

Animations follow the `AnimationCascade` / `WinAnimation` pattern:

1. Create a class in `renderer.py` with:
   - `done: bool` property
   - `current() -> List[Tuple[int,int]]` method
2. Store an instance on `Renderer` (e.g. `self.my_anim: Optional[MyAnim] = None`).
3. In `Renderer.draw()`, read `my_anim.current()` and draw the effect.
4. Set the instance from `GameLoop` in `main.py` when the triggering event occurs.

---

## Renderer Caching Pattern

To avoid per-frame allocations, the renderer caches Pygame surfaces and rebuilds them only when inputs change:

| Cache | Invalidation condition |
|---|---|
| `_num_surfs` | Tile size changes |
| `_ghost_surf` | Board pixel dimensions change (zoom/resize) |
| `_fog_surf` | Window size changes |
| `_anim_surf` | Tile size changes |
| `_hover_surf` | Tile size changes |
| `_thumb_surf` | Built once at init; never rebuilt |

When adding a new cached surface, follow this pattern:

```python
if self._my_surf is None or self._my_surf.get_size() != expected_size:
    self._my_surf = pygame.Surface(expected_size, pygame.SRCALPHA)
    # ... populate ...
self._win.blit(self._my_surf, dest)
```

---

## Headless Testing Tips

The engine has zero Pygame dependencies, so engine unit tests run without a display:

```python
import pytest
from gameworks.engine import Board, GameEngine, place_random_mines

def test_first_click_safe():
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    eng.start()
    result = eng.left_click(4, 4)
    assert not result.hit_mine
```

For renderer tests that require Pygame, set environment variables before importing:

```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
```

---

## Common Issues

### `pygame.error: No available video device`

Run with headless drivers:
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy python -m gameworks.main --random --easy
```

### `ImportError: numba` when using `--image`

Image mode requires `numba` (for the SA pipeline). Install it:
```bash
pip install numba
```

### Board appears tiny on a large monitor

Pass a larger tile size:
```bash
python -m gameworks.main --random --medium --tile 48
```

### `.npy` file raises `ValueError: Neighbour mismatch`

The file is in game-save format but has incorrect neighbour counts (likely corrupted). Use a pipeline-format `.npy` instead, or re-generate the board.

---

## Code Style

- Follow PEP 8. Line length ≤ 100 characters.
- Use `from __future__ import annotations` for forward references.
- Type hints on all public methods and functions.
- Coordinate convention: `(x, y)` == `(col, row)` everywhere in the public API. Internal NumPy arrays index `[row, col]` (i.e. `[y, x]`).
- Constants in `UPPER_SNAKE_CASE` at module top-level.
- Private members prefixed `_`.

---

## Releasing a New Version

1. Update `gameworks/__init__.py`:
   ```python
   __version__ = "0.2.0"
   ```
2. Add a section to `gameworks/docs/CHANGELOG.md`.
3. Run the full test suite.
4. Commit with message: `chore: bump gameworks to v0.2.0`.

---

*Gameworks v0.1.1*
