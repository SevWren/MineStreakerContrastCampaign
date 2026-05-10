# Gameworks — Changelog

All notable changes to the `gameworks` package are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Version numbers follow [Semantic Versioning](https://semver.org/).

---

## [0.1.1] — 2026-05-10

### Added

**DEV TOOLS panel toggle**
- `Renderer._show_dev` flag (default `False`) gates all DEV TOOLS rendering and click handling.
- Press `` ` `` (backtick / `K_BACKQUOTE`) to toggle the DEV TOOLS separator, header, and "Solve Board" button on/off.
- The "Solve Board" button is unclickable while the panel is hidden.

**Performance — Phase 1: dirty-int counters in `Board` (P-06, P-07, P-08, P-23)**
- Added four `int` counters to `Board.__init__`: `_n_flags`, `_n_questioned`, `_n_safe_revealed`, `_n_revealed`.
- Counters are incremented/decremented atomically in `reveal()` and `toggle_flag()`.
- Properties `flags_placed`, `questioned_count`, `safe_revealed_count`, and `revealed_count` now return cached ints instead of calling `numpy.sum()` on full arrays — eliminating ~3 full array scans per frame at 30 FPS on 300×300 boards.
- `GameEngine.dev_solve_board()` resyncs counters from arrays after bulk numpy operations.

**Performance — Phase 2: cache frame-local values in `Renderer` (P-15, P-17, P-18, P-21)**
- `_win_size` attribute caches `_win.get_size()` at init; invalidated on `VIDEORESIZE`.
- `_cached_board_rect` caches `_board_rect()` result; invalidated on pan, zoom, or resize.
- `_last_mouse_pos` attribute stores last known mouse position for `MOUSEWHEEL` events (which lack `.pos`).
- `mouse_pos` passed through `draw()` → `_draw_header()` → `_draw_smiley()` to eliminate a redundant `pygame.mouse.get_pos()` call per frame.
- Eliminates ~10 OS/syscall invocations per frame.

**Performance — Phase 3: cell loop refactor in `Renderer` (P-01, P-02, P-03, P-20)**
- `time.monotonic()` hoisted before the cell loop (1 call/frame instead of per-cell).
- `CellState` dataclass construction eliminated from the hot cell loop; raw numpy `bool_`/`uint8` values passed directly to `_draw_cell`.
- `_draw_cell` signature updated to accept individual field values instead of a `CellState` object:
  `_draw_cell(x, y, is_mine, is_revealed, is_flagged, is_questioned, neighbour_mines, pos, in_anim, is_pressed, fog, ts, in_win_anim, now)`
- `_num_surfs` lookup key cast from numpy `uint8` to Python `int` to fix dict key type mismatch.
- Eliminates 50,000+ Python object constructions per frame on 300×300 boards.

**Test suite expansion**
- `test_board.py`: +5 regression tests validating dirty-int counters match array state.
- `test_board_edge_cases.py`: 286-line new file — 1×1/2×2/100×1/1×100 boards, all-mines, no-mines, corner/edge operations, neighbour count boundaries, repeat operations, win condition edge cases, random mine placement validation.
- `test_cell_draw.py`: 5 tests validating cell loop draw behaviour and Phase 3 invariants.
- `test_renderer_init.py`: +12 tests for cache existence, init state, cache invalidation on VIDEORESIZE/pan/zoom.
- `gameworks/tests/integration/test_main.py`: 263-line new file — 22 integration tests covering CLI parser, `GameLoop` construction, `main()` entry point, and `GameLoop` action dispatch.
- Total gameworks test count: **337 passing**.

### Fixed

- **ANIM-001: `AnimationCascade.done` / `WinAnimation.done` never became `True` after elapsed time.** Root cause: animation phase transitions use lazy evaluation — `_idx`/`_phase` only advance when `current()` is explicitly invoked. Fixed test assertions to call `.current()` before checking `.done`. All 4 animation timing tests now pass.
- **`_on_resize()` cache invalidation bug:** `_cached_board_rect` was not cleared after tile size changes, causing stale board rect coordinates after zoom. Fixed: `_cached_board_rect = None` added to `_on_resize()`.

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
