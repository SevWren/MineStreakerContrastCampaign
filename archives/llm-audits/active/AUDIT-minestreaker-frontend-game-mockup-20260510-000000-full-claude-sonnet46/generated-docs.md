# Generated Documentation
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## README.md Addition: Gameworks Section

Add after "## Quick Start":

```markdown
## Playing the Minesweeper Game

### Run the game (classic random board)
```powershell
python -m gameworks.main --random --medium
```

### Run with easy/hard presets
```powershell
python -m gameworks.main --easy
python -m gameworks.main --hard
```

### Run with a custom board (image-reconstruction mode)
```powershell
python -m gameworks.main --image assets/line_art_irl_11_v2.png
```
Note: Image mode requires the MineStreaker pipeline to generate the board.
First run may take 2-5 minutes for SA optimization and repair.

### Load a previously saved board
```powershell
python -m gameworks.main --load board_20260510_142300_300x370.npy
```

### Controls
| Input | Action |
|---|---|
| Left click | Reveal cell |
| Right click | Place/cycle flag (hidden → flag → ? → hidden) |
| Middle click / Ctrl+click | Chord reveal |
| Scroll wheel | Zoom in/out |
| Mouse drag | Pan board |
| Arrow keys | Pan board |
| R | Restart |
| H | Toggle help |
| F | Toggle fog of war |
| ESC | Quit |

### CLI Options
```
--random       Classic random board (default)
--image PATH   Image-reconstruction mode
--load PATH    Load saved .npy board
--easy         9×9, 10 mines
--medium       16×16, 40 mines (default)
--hard         30×16, 99 mines
--board-w N    Board width in tiles (default: 300)
--board-h N    Board height in tiles (default: 370)
--mines N      Mine count (0 = auto)
--seed N       Random seed (default: 42)
--tile N       Tile size in pixels (default: 32)
```
```

## docs/adr/001-pygame-implementation.md

```markdown
# ADR-001: Pygame Desktop Implementation for gameworks/

**Date**: 2026-05
**Status**: Accepted
**Context**: The `docs/frontend_spec/` describes a React 18 + TypeScript + Canvas 2D web frontend.
The `gameworks/` directory implements a Pygame desktop game instead.

**Decision**: Implement the Minesweeper game as a Pygame desktop application for initial
prototype, deferring the React/TypeScript web implementation to a future phase.

**Rationale**:
- Pygame shares the Python ecosystem with the pipeline (no additional runtime)
- Pygame allows rapid prototyping without a web bundler/toolchain
- The pipeline already runs on desktop — Pygame allows direct integration
- The React spec can still be implemented as a web port at any time

**Consequences**:
- The frontend spec (`docs/frontend_spec/`) remains as a spec for the future web port
- The pygame implementation covers the core gameplay loop
- Sound, leaderboard, and scoring features from the spec are deferred
- The game cannot run in a browser in this form
```
