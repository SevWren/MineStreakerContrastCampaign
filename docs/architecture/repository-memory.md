# Repository Memory
## Last Updated: 2026-05-10 (Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46)

## Architectural Assumptions

1. The repository has two independent systems: (1) the SA pipeline for image→board generation and (2) the gameworks Pygame game that can consume pipeline output.

2. `gameworks/engine.py::load_board_from_pipeline()` uses dynamic runtime imports to avoid hard-coupling the game to the pipeline. This design is intentional but creates a sys.path manipulation pattern.

3. The demo package (`demos/iter9_visual_solver/`) is SEPARATE from the game (`gameworks/`). The demo plays back solver event traces; the game is an interactive Minesweeper. These serve different purposes.

4. `run_iter9.py` is the canonical pipeline entrypoint. `run_benchmark.py` runs matrices of runs. Neither directly invokes `gameworks/`.

## Subsystem Explanations

### gameworks/
Pygame-based interactive Minesweeper with three board modes:
- `random`: classic mine placement with numpy RNG
- `npy`: load pre-computed layout from file
- `image`: invoke MineStreaker pipeline (CURRENTLY BROKEN)

### demos/iter9_visual_solver/
Standalone demo that reads pipeline output artifacts and replays the solver decision sequence visually. Has ~30 tests. NOT the game.

### Pipeline (run_iter9.py + modules)
SA-based image reconstruction pipeline. Produces .npy boards + visual reports. Mature and well-tested.

## Gameplay Invariants

1. Coordinates are always (x, y) == (col, row) in the public API
2. Internal numpy arrays index as [row, col] == [y, x]
3. First click is always safe — board regenerates if needed (seed+1)
4. Mine = -1 in .npy format; safe cells = neighbour count
5. Win condition: revealed_count == total_safe (NOTE: should also require correct_flags == total_mines per design spec — this is a known gap)

## State Ownership Rules

- `Board._state` is the authoritative game state string: "playing" | "won" | "lost"
- `GameEngine` delegates all game logic to `Board`
- `Renderer` is read-only with respect to game state (never modifies Board)
- `GameLoop` is the only entity that calls GameEngine action methods

## Known Technical Debt

1. **5 critical runtime crashes** in gameworks/ (as of 2026-05-10 audit) — see findings.json
2. **Zero test coverage** for gameworks/ package
3. **No requirements.txt** — environment not reproducible
4. **frontend_spec/ not implemented** — React/TS spec exists but pygame is the actual implementation
5. **SA constants as module globals** in run_iter9.py — 30+ constants without config file
6. **Renderer god object** — 1041 LOC covering window, input, rendering, animations, HUD

## Unresolved Architectural Risks

1. Pipeline blocking game thread (image mode pipeline runs synchronously, blocks pygame for minutes)
2. Stale board reference in Renderer after first-click mine regeneration
3. MoveResult.flagged type mismatch (bool annotated, str actual)
4. win condition missing correct-flag check per design spec

## Historical Design Decisions

- Branch name `frontend-game-mockup` indicates this is a prototype/mockup phase
- `docs/frontend_spec/` represents the aspirational React web frontend — not yet implemented
- Pygame was chosen for rapid prototyping within the Python ecosystem
- The SA pipeline constants have been iteratively tuned — commented-out alternatives in run_iter9.py represent historical tuning history, not active alternatives

## Known Constraints

- Numba JIT requires first-run compilation (10-30 seconds) — unavoidable
- pygame requires a display server (SDL2) — headless testing needs SDL_VIDEODRIVER=dummy
- Board sizes of 300×370 are normal for this project (derived from image aspect ratios)
- The min_width in board_sizing.py was changed from 300 to 50 for testing flexibility
