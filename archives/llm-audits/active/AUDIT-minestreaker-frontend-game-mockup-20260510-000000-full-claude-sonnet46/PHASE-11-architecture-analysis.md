# PHASE 11 — Architecture Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. Subsystem Boundary Analysis

### 1.1 Pipeline Boundary (run_iter9.py + modules)
**Quality**: HIGH

The pipeline has well-defined ownership boundaries (documented in README Contributor Rules):
- `solver.py`: unresolved-cell classification only
- `pipeline.py`: route selection and route artifacts
- `repair.py`: repair mutations and move logs
- `report.py`: visual proof artifacts
- `sa.py`: optimization kernel only

These boundaries are enforced by convention and tested by `tests/demo/iter9_visual_solver/test_architecture_boundaries.py`. The demo package enforces import boundaries formally.

### 1.2 gameworks/ Boundary (POOR)
The gameworks package has **no enforced boundaries**:
- `engine.py` directly imports from pipeline modules at runtime (violating the notion of engine as pure game logic)
- `renderer.py` writes to `global TILE` (module-level side effect)
- `main.py` imports `AnimationCascade` inside action handlers instead of at module level

### 1.3 demos/iter9_visual_solver/ Boundary (EXCELLENT)
The demo package is the most architecturally mature subsystem:
- Strict layered architecture: cli → config → domain → playback → rendering
- Enforced by `test_architecture_boundaries.py`
- No upward imports (rendering never imports from cli, etc.)
- Artifact-based coupling to pipeline: reads JSON/NPY files, no import dependency

## 2. Layering Violations

| Violation | Files | Severity |
|---|---|---|
| `engine.py` imports from pipeline at runtime | `gameworks/engine.py` → `sa.py`, `repair.py`, `corridors.py`, `core.py` | MEDIUM |
| `renderer.py` writes module-level global | `renderer.py` → `global TILE` | LOW |
| `main.py` inline imports in action handlers | `main.py` → `gameworks.renderer.AnimationCascade` in `_do_left_click` | LOW |

## 3. God Object Analysis

### Board — Borderline God Object
`Board` has 15 methods/properties for: initialization, mine checking, reveal, flag, chord, snapshot, win/loss query, mine position query. This is manageable but could be split:
- `BoardQuery`: read-only properties (is_won, is_lost, snapshot, mines_remaining, etc.)
- `BoardMutator`: reveal, toggle_flag, chord

For now, the current design is acceptable given the narrow domain.

### Renderer — God Object
`Renderer` (1041 LOC) handles: window management, event handling, board drawing, HUD drawing, panel drawing, help overlay, victory/defeat overlays, animations, image ghost, panning/zooming. This is a classic god object.

**Recommended decomposition**:
```
Renderer (coordinator)
├── WindowManager (window sizing, pan/zoom)
├── BoardLayer (cell drawing, viewport culling)
├── HUDLayer (header, smiley, timer)
├── PanelView (buttons, stats, tips)
├── OverlayLayer (help, victory, defeat, fog)
└── AnimationSystem (cascade, win animation)
```

## 4. Architectural Drift

### Planned vs Implemented
| GAME_DESIGN.md Specification | Current Implementation Status |
|---|---|
| React 18 + TypeScript + Canvas 2D | Not implemented — Pygame only |
| 7-state game state machine | 3-state machine (MENU/PLAYING/RESULT) |
| Scoring system (5 components) | Not implemented |
| Hint engine (solver-driven) | Not implemented |
| Undo engine (action stack) | Not implemented |
| Difficulty system (4 tiers) | 3 difficulty presets (no Expert) |
| Leaderboard | Not implemented |
| Image ghost overlay (toggleable) | Implemented ✓ |
| First-click safety | Implemented ✓ |
| Chording | Implemented ✓ |
| Win/loss conditions | Partially correct (win condition missing flag check) |

### frontend_spec/ vs gameworks/
The `docs/frontend_spec/` describes a complete TypeScript/React implementation. `gameworks/` is a Python/Pygame implementation. These are **completely different technology stacks** with overlapping conceptual design. The relationship is:
- frontend_spec = aspirational target (web port)
- gameworks = current implementation (desktop prototype)

This is architecturally valid only if it's intentional and documented.

## 5. Scalability Risks

### Per-Cell Render Calls
At BASE_TILE=32, a 300×370 board requires rendering ~111,000 cells. With viewport culling, only ~1000-2000 visible cells are drawn per frame (depending on window size). This is acceptable at 32px tiles.

At MIN_TILE_SIZE=10, the viewport shows more cells: up to 10,000+ visible cells per frame. At 60fps, this requires 600,000 draw calls/second. PyGame primitive drawing is not batched — this will cause performance issues.

### Pipeline Blocking Game Thread
`load_board_from_pipeline()` runs the full SA + repair pipeline synchronously in the game's main thread. On a 300×370 board, this takes 2-5 minutes. Pygame's event loop is completely blocked during this time (no window refresh, no input).

**Required architectural fix**: Move pipeline execution to a background thread or subprocess, with a loading screen.

## 6. Modularity Quality

| Subsystem | Modularity Score | Notes |
|---|---|---|
| pipeline modules | HIGH | Clear ownership, enforced boundaries |
| demos/iter9_visual_solver | EXCELLENT | Strict layering, full test coverage |
| gameworks/engine.py | MEDIUM | Pure logic ✓, but couples to pipeline |
| gameworks/renderer.py | LOW | God object, global mutation, no abstraction |
| gameworks/main.py | MEDIUM | Small but has double-dispatch bug |

## 7. Target Architecture Proposal

### Short Term (fix critical bugs)
```
gameworks/
├── engine.py      [add .state property]
├── renderer.py    [fix fog, btn_w, ghost perf]
├── main.py        [fix FPS, double dispatch, Optional import]
└── __init__.py
```

### Medium Term (decompose Renderer)
```
gameworks/
├── engine/
│   ├── board.py           [Board class]
│   ├── game_engine.py     [GameEngine]
│   └── mine_placement.py  [place_random_mines, load_board_from_*]
├── rendering/
│   ├── renderer.py        [thin coordinator]
│   ├── board_layer.py     [cell drawing]
│   ├── hud_layer.py       [header/timer/smiley]
│   ├── panel_view.py      [buttons/stats]
│   └── overlay_layer.py   [modal/help/fog]
├── input/
│   └── event_handler.py   [unified event → action mapping]
└── main.py                [CLI + game loop]
```

### Long Term (web port per frontend_spec/)
Implement the React 18 + TypeScript + Canvas 2D frontend as specified in `docs/frontend_spec/`. This requires:
1. FastAPI backend wrapping the Python pipeline
2. WebSocket or REST API for board generation
3. React frontend implementing the GameController + Renderer spec
