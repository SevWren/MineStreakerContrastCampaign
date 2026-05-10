# Repository Memory
## Last Updated: 2026-05-10 (Session 5 — design pattern scaffold + test suite)

## Architectural Assumptions

1. The repository has two independent systems: (1) the SA pipeline for image→board
   generation and (2) the gameworks Pygame game that can consume pipeline output.

2. `gameworks/engine.py::load_board_from_pipeline()` uses dynamic runtime imports to
   avoid hard-coupling the game to the pipeline. This design is intentional but creates
   a sys.path manipulation pattern.

3. The demo package (`demos/iter9_visual_solver/`) is SEPARATE from the game
   (`gameworks/`). The demo plays back solver event traces; the game is an interactive
   Minesweeper. These serve different purposes.

4. `run_iter9.py` is the canonical pipeline entrypoint. `run_benchmark.py` runs
   matrices of runs. Neither directly invokes `gameworks/`.

5. `gameworks/docs/` is the self-contained documentation tree for the game package.
   Do not use root `docs/` for gameworks-specific contracts or API docs.

6. `gameworks/tests/` is the package-local test suite. Root `tests/` contains legacy
   regression guards and pipeline tests; both suites must stay green.

---

## Subsystem Explanations

### gameworks/
Pygame-based interactive Minesweeper with three board modes:
- `random`: classic mine placement with numpy RNG
- `npy`: load pre-computed layout from file
- `image`: invoke MineStreaker pipeline via `load_board_from_pipeline()`
  (corridors crash C-001 was resolved; end-to-end image mode requires `numba`)

Documentation: `gameworks/docs/` (8 documents — see `gameworks/docs/INDEX.md`)
Test suite: `gameworks/tests/` (22 files — see `docs/DOCS_INDEX.md`)
Design pattern debt: `gameworks/docs/DESIGN_PATTERNS.md` (R2–R9 recommendations)

### demos/iter9_visual_solver/
Standalone demo that reads pipeline output artifacts and replays the solver decision
sequence visually. Has ~30 tests. NOT the game.

### Pipeline (run_iter9.py + modules)
SA-based image reconstruction pipeline. Produces .npy boards + visual reports.
Mature and well-tested. Key contracts in `docs/`, `demo/docs/`.

---

## Gameplay Invariants

1. Coordinates are always `(x, y)` == `(col, row)` in the public API.
2. Internal numpy arrays index as `[row, col]` == `[y, x]`.
3. First click is always safe — board regenerates if needed (seed+1).
4. Pipeline `.npy` format: `0`=safe, `1`=mine. Game-save format: `-1`=mine, `0–8`=neighbour count.
5. Win condition: `safe_revealed_count == total_safe`. Flags are not required for victory.
6. Mine hit is a score penalty only. `Board._state` is NEVER set to `"lost"`.

---

## State Ownership Rules

- `Board._state` is the authoritative game state string: `"playing"` | `"won"` (never `"lost"`)
- `GameEngine` delegates all board logic to `Board`; manages scoring, streak, timer
- `Renderer` is read-only with respect to game state — never modifies `Board`
- `GameLoop` is the only entity that calls `GameEngine` action methods

---

## Known Technical Debt

1. **R2 — No GameConfig frozen dataclass.** `GameEngine` takes 7 flat constructor args.
   Config cannot be serialized or compared as a unit. Tracked: `DESIGN_PATTERNS.md § R2`.
   Test scaffold: `gameworks/tests/unit/test_config.py` (skipped pending implementation).

2. **R3 — Board loaders return naked Board.** `load_board_from_npy` and
   `load_board_from_pipeline` return `Board` directly. Format detection, fallback status,
   and warnings are not observable. Tracked: `DESIGN_PATTERNS.md § R3`.
   Test scaffold: `gameworks/tests/unit/test_board_loading.py` (partial).

3. **R6 — No preflight_check().** Missing-file and bad-import errors surface mid-game-loop
   rather than at startup with a clean error message. Tracked: `DESIGN_PATTERNS.md § R6`.
   Test scaffold: `gameworks/tests/cli/test_preflight.py` (skipped).

4. **R8 — _save_npy() is not atomic.** Direct `np.save(path)` leaves corrupt partial files
   on crash/Ctrl-C. Tracked: `DESIGN_PATTERNS.md § R8`.
   Test scaffold: `gameworks/tests/integration/test_board_modes.py::test_atomic_save` (skipped).

5. **R9 — No GAME_SAVE_SCHEMA_VERSION.** Saved `.npy` boards have no version metadata.
   Loader relies on value-range heuristics; no forward-compatible schema gate.
   Tracked: `DESIGN_PATTERNS.md § R9`.
   Test scaffold: `gameworks/tests/unit/test_board_loading.py` (schema section, skipped).

6. **M-003 — Duplicate Restart/New Game buttons.** Both panel buttons return `"restart"`.
   No way to retry the same board. Tracked: `docs/ISSUE-LOG.md § M-003`.

7. **M-004 — WinAnimation empty on flag-free win.** No visual fanfare when player wins
   without placing flags (most common playstyle). Tracked: `docs/ISSUE-LOG.md § M-004`.

8. **T-001 — FPS constant mismatch.** `tests/test_gameworks_renderer_headless.py:94`
   asserts `FPS == 60` but `renderer.py` defines `FPS = 30`.
   Tracked: `docs/ISSUE-LOG.md § T-001`.

9. **30+ SA constants as module globals** in `run_iter9.py` — pipeline-only concern.
   Tracked: `docs/back_log.md`.

10. **Renderer god object** — `renderer.py` is ~1000 LOC covering window, input,
    rendering, animations, HUD. Single-responsibility violation; tracked for future split.

---

## Unresolved Architectural Risks

1. **Pipeline blocking game thread.** Image mode invokes the SA pipeline synchronously
   in the main thread, potentially blocking pygame for minutes on large boards.
   No background thread or progress indicator implemented.

2. **Stale board reference in Renderer after first-click mine regeneration.**
   When the first-click safety check regenerates the board, `Renderer.board` may hold
   the old reference. Renderer should always read `engine.board` dynamically.

3. **MoveResult.flagged type annotation mismatch.** Annotated as `str | bool`; in practice
   it is a string (`"flag"`, `"question"`, `"hidden"`) or `False`. Consumers must handle both.

---

## Historical Design Decisions

- Branch name `frontend-game-mockup` indicates this was originally a prototype/mockup phase.
- `docs/frontend_spec/` represents the aspirational React web frontend — NOT implemented.
  Treat as dormant reference material only.
- Pygame was chosen for rapid prototyping within the Python ecosystem.
- The no-game-over mine-hit design is intentional — mine hits are score penalties only.
- The SA pipeline constants in `run_iter9.py` have been iteratively tuned across 9 versions;
  commented-out alternatives represent historical tuning history, not dead code.

---

## Known Constraints

- Numba JIT requires first-run compilation (10–30 seconds) — unavoidable.
- pygame requires a display server (SDL2) — headless testing needs `SDL_VIDEODRIVER=dummy`.
- Board sizes of 300×370 are normal for this project (derived from image aspect ratios).
- The min_width in `board_sizing.py` was changed from 300 to 50 for testing flexibility.
- `requirements.txt` exists at repo root with full dependency list.
