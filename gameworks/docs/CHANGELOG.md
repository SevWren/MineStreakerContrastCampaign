# Gameworks — Changelog

All notable changes to the `gameworks` package are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Version numbers follow [Semantic Versioning](https://semver.org/).

---

## [0.1.0] — 2026-05-10

### Added

**Core engine (`engine.py`)**
- `Board` class: pure-logic Minesweeper board backed by NumPy arrays
  - Flood-fill reveal with scipy-accelerated neighbour-count precomputation
  - Flag cycle: hidden → flag → question → hidden
  - Chording support (middle-click semantics)
  - Win detection on full safe-cell reveal
- `GameEngine` class: lifecycle, player actions, scoring, streak system
  - Three board modes: `random`, `image`, `npy`
  - `from_difficulty()` class method: `easy` / `medium` / `hard` presets
  - First-click safety: board regenerated if first click would hit a mine
  - Mine-hit-as-penalty mechanic: game continues after mine hits (no game-over state)
  - Score system: `REVEAL_POINTS` indexed by neighbour count, streak multiplier tiers
  - `mine_flash` dict for renderer-driven flash feedback
- `MoveResult` dataclass: structured return type for all player actions
- `CellState` frozen dataclass: immutable cell snapshot for renderer consumption
- `place_random_mines()`: safe-zone-aware random mine placement
- `load_board_from_npy()`: auto-detecting loader for pipeline-format and game-save-format `.npy` files
- `load_board_from_pipeline()`: image → Board via MineStreaker SA pipeline, with random fallback

**Renderer (`renderer.py`)**
- `Renderer` class: full Pygame-based rendering
  - Auto-scaling tile size for boards ≥ 100 tiles on either axis
  - Dual layout: side panel (small boards) or bottom panel (large boards)
  - Viewport-culled tile drawing for 300×370+ boards
  - Pre-rendered digit surface cache (`_num_surfs`) — no per-frame `font.render()`
  - Reusable SRCALPHA surfaces for animations, hover highlight, fog overlay
  - Image ghost overlay: source image visible through flagged mine tiles
  - Scroll-wheel zoom centered on cursor; mouse-drag and arrow-key panning
  - Pan clamping; board centering on init
  - Header HUD: mine counter, smiley button, timer, score, streak/multiplier
  - Side/bottom panel: control buttons, stats, tips, mode badge, image thumbnail
  - Fog-of-war toggle
  - Help overlay
  - Victory and defeat modals
  - `handle_event()` returns action strings (decoupled from engine)
- `AnimationCascade`: timed wave reveal animation for newly-revealed cells
- `WinAnimation`: progressive flag-reveal animation with correct-first ordering
- Helper drawing utilities: `rrect`, `rrect_outline`, `pill`
- Dark modern color palette (`C` dict)

**Entry point (`main.py`)**
- `GameLoop` state machine: `MENU → PLAYING → RESULT → MENU`
- `build_parser()`: full CLI with `--image`, `--load`, `--random`, difficulty flags, board dimensions, tile size, seed
- `GameLoop._save_npy()`: save current board to timestamped `.npy`

**Package**
- `gameworks/__init__.py` with `__version__ = "0.1.0"` and module docstring

**Documentation** (`gameworks/docs/`)
- `INDEX.md`, `README.md`, `ARCHITECTURE.md`, `API_REFERENCE.md`, `GAME_DESIGN.md`, `DEVELOPER_GUIDE.md`, `CHANGELOG.md`

---

## Upcoming / Known Gaps

The following areas are noted as shallow or not yet implemented at v0.1.0:

- **Persistent high score / leaderboard** — score is not saved between sessions.
- **Difficulty selection UI** — difficulty can only be set via CLI; no in-game menu.
- **Save/load game state** — `Save .npy` saves the mine grid only; cell reveal/flag state is not persisted.
- **Sound effects** — no audio; the pygame mixer is not initialised.
- **Mobile / touch input** — designed for desktop mouse/keyboard only.
- **Settings screen** — tile size, seed, board dimensions require CLI restart.
- **Lose state rendering** — `draw_defeat()` is defined but never called; mine hits are penalties only.
- **Accessibility** — no colour-blind mode; colours are hardcoded in the `C` palette.

---

*Gameworks v0.1.0*
