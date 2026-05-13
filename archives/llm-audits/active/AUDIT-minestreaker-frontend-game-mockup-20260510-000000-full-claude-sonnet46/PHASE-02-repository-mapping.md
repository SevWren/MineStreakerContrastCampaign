# PHASE 02 — Repository Mapping
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. Runtime Lifecycle

### 1.1 Game Startup Lifecycle

```
python -m gameworks.main [args]
    │
    └── main()
         ├── build_parser().parse_args()
         ├── GameLoop(args)
         └── GameLoop.run()
              ├── _start_game()
              │    ├── _build_engine()     → GameEngine construction
              │    ├── engine.start()      → timer init
              │    └── Renderer(engine)    → pygame.init() + window
              │
              └── while running:
                   ├── pygame.event.get()
                   │    └── renderer.handle_event(ev) [returns action string]
                   │         └── [also calls] renderer.handle_panel(ev.pos)  ← BUG: double
                   │
                   ├── engine.state  ← BUG: attribute doesn't exist
                   │
                   ├── renderer.draw(...)
                   │
                   └── renderer._clock.tick(FPS)  ← BUG: FPS undefined
```

### 1.2 Pipeline Startup Lifecycle

```
python run_iter9.py --image assets/... --board-w 300 --seed 42
    │
    ├── resolve_source_image_config()
    ├── verify_source_image()
    ├── derive_board_from_width()
    ├── load_image_smart()
    ├── compute_zone_aware_weights()
    ├── build_adaptive_corridors()
    ├── compile_sa_kernel()      ← Numba JIT warmup
    ├── run_sa() × 5 stages
    ├── solve_board()
    ├── run_phase1_repair()
    ├── route_late_stage_failure()
    └── render artifacts → results/iter9/<run_id>/
```

## 2. Gameplay Loop

```
GameLoop.run()
    │
    ├── [MENU state]
    │    └── _start_game() → PLAYING
    │
    ├── [PLAYING state]
    │    ├── left_click(x,y)
    │    │    └── engine.left_click(x,y) → MoveResult
    │    │         ├── board.reveal(x,y)
    │    │         │    └── flood-fill if neighbour_mines == 0
    │    │         ├── [first click] regenerate if mine
    │    │         └── [hit mine] reveal all mines + stop timer
    │    │
    │    ├── right_click(x,y)
    │    │    └── board.toggle_flag(x,y) → cycle hidden→flag→?→hidden
    │    │
    │    ├── middle_click(x,y) [chord]
    │    │    └── board.chord(x,y)
    │    │         └── if flags == number: reveal all unflagged neighbours
    │    │
    │    └── [win condition] revealed_count == total_safe → "won"
    │
    └── [RESULT state]
         ├── [won] start_win_animation() → WinAnimation
         └── [lost] draw_defeat() → modal
```

## 3. State Mutation Flow

### 3.1 Board State Transitions
```
Initial: _state = "playing"
    │
    ├── reveal(x,y) where (x,y) is mine → _state = "lost"
    ├── chord → mine revealed → _state = "lost"
    └── revealed_count == total_safe → _state = "won"
```

### 3.2 GameLoop State Machine
```
MENU → _start_game() → PLAYING
PLAYING → [engine.state == "won"] → RESULT [r_action = "win"]
PLAYING → [engine.state == "lost"] → RESULT [r_action = "lost"]
RESULT → [key R / restart button] → MENU → PLAYING
```

## 4. Event Flow

```
pygame.event.get()
    │
    ├── QUIT → running = False
    ├── KEYDOWN
    │    ├── K_ESCAPE → "quit"
    │    ├── K_r → "restart"
    │    ├── K_h → toggle help_visible
    │    ├── K_f → toggle fog
    │    └── K_LEFT/RIGHT/UP/DOWN → pan adjustment
    │
    ├── MOUSEBUTTONDOWN (button=1)
    │    ├── on board → start drag + record pressed_cell
    │    └── on panel → handle_panel() [also called from main.py — DOUBLE]
    │
    ├── MOUSEBUTTONUP (button=1) → click detection (if no drag)
    ├── MOUSEMOTION → pan update
    ├── MOUSEWHEEL → zoom
    ├── MOUSEBUTTONDOWN (button=3) → flag:x,y
    ├── MOUSEBUTTONDOWN (button=2) → chord:x,y
    └── VIDEORESIZE → re-center board
```

## 5. Save/Load Flow

### 5.1 Save (`.npy`)
- `GameLoop._save_npy()` triggered by "save" panel button
- Iterates all cells, writes mine=-1 / neighbour_count to float32 grid
- Saves to CWD with timestamp filename (no configurable path)

### 5.2 Load (`.npy`)
- CLI: `--load <path>`
- `_build_engine()` calls `load_board_from_npy(a.load)`
- Creates GameEngine with dummy random mode, then replaces board
- Validates neighbour counts against computed values

### 5.3 Image Mode (Pipeline Load)
- CLI: `--image <path>`
- `load_board_from_pipeline()` in engine.py
- **BROKEN** due to compile_sa_kernel() and run_phase1_repair() signature mismatches
- Falls back to random board on ANY exception (silently)

## 6. Asset Pipeline

```
Source image (PNG/JPEG)
    │
    └── gameworks/renderer.py::Renderer.__init__()
         ├── pygame.image.load(image_path).convert_alpha()
         ├── pygame.transform.smoothscale() to fit board dimensions
         └── stored as self._image_surf
              │
              └── Used in:
                   ├── _draw_image_ghost() — per-flagged-cell blit (PER-FRAME)
                   ├── _draw_win_animation_fx() — per-animated-cell blit
                   └── _draw_panel() — thumbnail preview
```
