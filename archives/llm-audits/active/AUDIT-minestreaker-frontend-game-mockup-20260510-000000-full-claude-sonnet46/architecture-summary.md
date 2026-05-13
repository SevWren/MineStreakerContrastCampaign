# Architecture Summary
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. System Overview

MineStreakerContrastCampaign is a **dual-system repository**:

1. **Research Pipeline** (`run_iter9.py` + modules): SA-based image-to-Minesweeper-board reconstruction
2. **Gameworks Package** (`gameworks/`): Interactive Pygame Minesweeper game that can use pipeline output

These two systems share no common module except `gameworks/engine.py::load_board_from_pipeline()` which dynamically imports the pipeline at runtime.

## 2. Gameworks Architecture

```
                    CLI Args
                        │
                    gameworks/main.py
                   ┌────┴────┐
                   │         │
              GameLoop   build_parser()
                   │
         ┌─────────┼──────────┐
         │         │          │
     GameEngine  Renderer   events
    (engine.py) (renderer.py)
         │         │
      Board      pygame
      (logic)   (display)
```

### 2.1 GameEngine (`gameworks/engine.py`)
- Owns `Board` instance
- Manages timers, first-click safety, difficulty presets
- Supports three board creation modes:
  - `"random"` — pure random mine placement
  - `"npy"` — load pre-computed board from `.npy` file
  - `"image"` — dynamically invoke MineStreaker pipeline (BROKEN — see findings)
- Exposes `left_click`, `right_click`, `middle_click`, `restart`
- Has **no `.state` property** (critical gap)

### 2.2 Board (`gameworks/engine.py`)
- Pure numpy-backed Minesweeper board
- Internal state: `_mine`, `_revealed`, `_flagged`, `_questioned` (H×W numpy arrays)
- Exposed via `snapshot(x, y) → CellState` (immutable dataclass)
- State machine: `"playing"` → `"won"` | `"lost"`

### 2.3 Renderer (`gameworks/renderer.py`)
- Initializes Pygame window on construction
- Auto-scales tile size for boards ≥ 100 cells on either axis
- Panel placement: right side (small boards) or bottom (large boards)
- Supports: panning, scroll-wheel zoom, fog-of-war toggle, image ghost overlay
- Animations: `AnimationCascade` (reveal), `WinAnimation` (flag reveal)
- `draw()` → calls 5 sub-draw methods → `pygame.display.flip()`

### 2.4 GameLoop (`gameworks/main.py`)
- Three states: `MENU → PLAYING → RESULT → MENU`
- Delegates all input to `Renderer.handle_event()` first
- **CRITICAL BUG**: also calls `Renderer.handle_panel()` directly for MOUSEBUTTONDOWN,
  causing double processing of panel clicks

## 3. Pipeline Architecture (Research System)

```
Image File
    │
board_sizing.py → aspect ratio → (board_w, board_h)
    │
core.py → load_image_smart() → target float32[H,W]
    │
core.py → compute_zone_aware_weights() → weights float32[H,W]
    │
corridors.py → build_adaptive_corridors() → forbidden int8[H,W]
    │
sa.py → compile_sa_kernel() → JIT kernel
    │
sa.py → run_sa() × N stages → grid int8[H,W]
    │
solver.py → solve_board() → SolveResult
    │
repair.py → run_phase1_repair() → repaired grid
    │
pipeline.py → route_late_stage_failure() → route decision
    │
report.py → render_report() → PNG artifacts
    │
run_iter9.py → write metrics JSON, NPY, artifacts
```

## 4. Architectural Gaps

| Gap | Description | Risk |
|---|---|---|
| No `.state` property on GameEngine | `main.py` references `self._engine.state` but GameEngine has no such attribute; only `Board._state` | CRITICAL — NameError at runtime |
| FPS undefined in main.py | `FPS` constant from renderer.py is referenced but not imported | CRITICAL — NameError at runtime |
| compile_sa_kernel() signature mismatch | Called with 3 args, defined with 0 | CRITICAL — TypeError in image mode |
| run_phase1_repair() signature mismatch | _RouteCfg object passed as time_budget_s float | CRITICAL — TypeError in image mode |
| btn_w undefined in _draw_panel | Local variable from __init__ used in method | HIGH — NameError when image loaded |
| Double panel event processing | handle_event AND handle_panel called for same click | HIGH — duplicate game restart/save |
| Wrong attribute name fog | `_draw_overlay` checks `self._fog` but attribute is `self.fog` | HIGH — fog feature never works |
| No test coverage for gameworks/ | All 4 game files have 0 unit tests | HIGH — regressions undetectable |
| Pipeline .npy format incompatibility | `load_board_from_npy()` checks `grid < 0`; pipeline boards use `1=mine` (never negative) | CRITICAL — all 3 committed boards load with 0 mines |
| ~~Missing source image for 2 of 3 boards~~ | ~~`line_art_irl_18v2` not in assets/~~ | **RESOLVED** commit 09e17c1 — `assets/line_art_irl_18v2.png` committed |
