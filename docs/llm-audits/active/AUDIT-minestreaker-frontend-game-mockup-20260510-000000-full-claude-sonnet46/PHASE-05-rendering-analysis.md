# PHASE 05 — Rendering Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. Render Loop

```
GameLoop.run()
    └── while running:
         └── renderer.draw(mouse_pos, game_state, elapsed, cascade_done)
              ├── self._win.fill(C["bg"])              [full screen clear]
              ├── _draw_header(elapsed, game_state)     [HUD bar]
              ├── _draw_board(mouse_pos, ...)           [all visible cells]
              │    ├── _draw_image_ghost()              [if image loaded — PER FLAGGED CELL]
              │    ├── cell loop (viewport-culled)      [_draw_cell per visible tile]
              │    ├── _draw_loss_overlay()             [if lost — NO culling]
              │    └── _draw_win_animation_fx()         [if won and animating]
              ├── _draw_overlay()                       [fog — BROKEN]
              ├── _draw_panel()                         [side/bottom panel]
              └── pygame.display.flip()                 [present]
```

## 2. Render/Update Coupling

### Good Separation
- `Renderer.draw()` only reads state — it never calls engine methods
- `handle_event()` returns action strings; game logic is in main.py action dispatchers
- `AnimationCascade` and `WinAnimation` are pure time-based — no game state mutation

### Coupling Problems
- `Renderer` stores `self.board = engine.board` at init time — stale after board regeneration (PHASE-04 §3.1)
- `Renderer._clock` is owned by Renderer but ticked by `GameLoop.run()` — clock ownership ambiguous
- `global TILE` mutation: `Renderer.__init__` writes to module-level `TILE` variable

## 3. Viewport Culling

### Board Draw — Has Culling ✓
```python
tx0 = max(0, (-self._pan_x) // ts - 1)
ty0 = max(0, (-self._pan_y) // ts - 1)
tx1 = min(self.board.width, (win_w - ox) // ts + 2)
ty1 = min(self.board.height, (win_h - oy) // ts + 2)
```
Correct: only draws tiles visible in the current viewport. Critical for 300×370 boards.

### Loss Overlay — NO Culling ✗
`_draw_loss_overlay()` iterates `range(self.board.height) × range(self.board.width)` — all cells regardless of viewport. On 300×370: 111,000 iterations per frame.

### Image Ghost — No Viewport Culling ✗
`_draw_image_ghost()` iterates all cells checking `cell.is_flagged` — no viewport restriction.

## 4. Texture and Surface Lifecycle

### Pre-Computed Surfaces
- `self._image_surf` — loaded once at init, scaled once ✓
- `self._icon` — created once at init ✓
- Fonts — created once at init ✓

### Per-Frame Surface Creation (PROBLEMS)
- `_draw_image_ghost()`: `pygame.Surface((ts, ts), pygame.SRCALPHA)` × n_flagged_cells × 60fps
- `_draw_win_animation_fx()`: `pygame.transform.smoothscale(self._image_surf, (bw, bh))` × 60fps (rescales the full board-sized image every frame during win animation)
- `_draw_board()` cursor highlight: `pygame.Surface((ts, ts), pygame.SRCALPHA)` × 1 per frame ← acceptable
- `_draw_board()` cell border in anim: `pygame.Surface((ts, ts), pygame.SRCALPHA)` × n_anim_cells ← minor issue

## 5. Batching Opportunities

### Current State: No Batching
Every cell is drawn individually with individual `pygame.draw.rect()` and `pygame.draw.circle()` calls. No surface batching, sprite groups, or surface composition layers.

### Opportunities
1. **Cell layer**: Pre-render all hidden tiles to a single "grid background" surface. Only re-render changed cells.
2. **Number layer**: Cache rendered number surfaces by (number, color) pair — 8 possible combinations.
3. **Mine/Flag sprites**: Pre-render mine and flag sprites at each tile size (on resize/zoom).
4. **Ghost layer**: Cache per `(flag_state, image_pixel)` or full ghost composite.

## 6. Animation Systems

### AnimationCascade
- Time-based: `elapsed / ANIM_TICK` determines how many cells are "revealed so far"
- `ANIM_TICK = 0.035` seconds → ~28 cells/second reveal rate
- Clean implementation — no issues

### WinAnimation
- Two-phase: correct flags first, then wrong flags
- Uses `random.Random(42).shuffle()` for ordering — deterministic but uses Python stdlib random, not numpy
- Phase transition tracked by `self._phase` counter
- Clean implementation — no issues

### Missing: No Easing / Lerp
Animations are linear (linear time → linear cell count). No ease-in/ease-out. Per GAME_DESIGN.md §8 (animation easing), smooth easing is specified but not implemented.

## 7. UI Rendering Analysis

### Header
- Mine counter: font-rendered emoji `💣` — may not render on all systems without emoji font
- Timer: `⏱` emoji — same concern
- Smiley button: drawn with pygame primitives — correct

### Panel
- 5 buttons with hover detection — correct
- Stats text — correct
- Tips text — correct
- Thumbnail: references undefined `btn_w` (CRITICAL BUG) — crashes when image loaded

### Help Overlay
- Rendered as full-screen alpha overlay with centered modal
- Clean implementation
- **Issue**: Large modal (580×520) — may exceed screen height on small displays

### Victory/Defeat Modal
- `draw_victory()` and `draw_defeat()` call `_draw_modal()` directly — not integrated into main render loop
- Called from `GameLoop.run()` outside of `renderer.draw()` — second blit per frame when RESULT state

## 8. Zoom / Pan

### Zoom
- Scroll wheel zooms toward mouse position — correct centering math
- Zoom range: `MIN_TILE_SIZE=10` to `BASE_TILE=32`
- `_on_resize()` only updates bottom-panel button positions — not right-panel positions

### Pan
- Mouse drag for panning — implemented correctly
- `_clamp_pan()` prevents excessive pan — correct
- Arrow keys for panning — correct
- **Issue**: Initial pan centers board but `_center_board()` sets `_pan_x = max(0, ...)` — never negative, meaning centered boards always start at (0,0) offset in top-left, not truly centered for boards smaller than window

## 9. Screen Resolution Handling

- `pygame.display.Info()` called in `__init__` to cap window size
- Window is `RESIZABLE`
- `VIDEORESIZE` event triggers re-center — correct
- `_on_resize()` recalculates button positions for zoom
- **Issue**: On resize, panel buttons only reposition for non-right-panel layout
