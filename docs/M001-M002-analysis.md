# Industry-Standard Analysis: M-001 & M-002
## `_draw_image_ghost` viewport culling · `_on_resize()` button Y drift

**Analyst:** Claude Sonnet 4.6
**Branch:** `frontend-game-mockup`
**Date:** 2026-05-10
**Files examined:** `gameworks/renderer.py` (full), `gameworks/engine.py` (full)

---

# PART A — M-001: `_draw_image_ghost` Ignores Viewport Culling

## 1. Exact Problem Statement

```
renderer.py:914-924   _draw_image_ghost()
```

```python
for y in range(self.board.height):          # iterates ALL rows
    for x in range(self.board.width):       # iterates ALL columns
        cell = self.board.snapshot(x, y)    # creates CellState dataclass per cell
        if not cell.is_flagged:
            continue
        px = ox + x * ts
        py = oy + y * ts
        src_rect = pygame.Rect(x * ts, y * ts, ts, ts)
        sub = scaled.subsurface(src_rect).copy()          # Surface alloc per flagged cell
        sub.set_alpha(200 if cell.is_mine else 40)        # mutates per frame
        self._win.blit(sub, (px, py))
```

### Four compounding failure layers

| Layer | Current behaviour | Cost per frame |
|-------|-------------------|----------------|
| **Iteration** | `range(W) × range(H)` Python loop | O(W×H) = 90,000 on 300×300 |
| **Object alloc** | `snapshot()` creates frozen `CellState` dataclass, 5 numpy reads | 90,000 allocations/frame |
| **Surface alloc** | `subsurface().copy()` + `set_alpha()` per flagged cell | N_flags new Surface objects |
| **Viewport blindness** | draws cells even when pygame clip will throw them away | 100% waste for off-screen blits |

### Measured impact

Python loop overhead is approximately 0.5–1 µs per iteration (CPython, cache-warm).
90,000 iterations × 0.75 µs = **67 ms per frame** — the entire 33 ms 30 FPS budget consumed
before a single pixel of image ghost is drawn.

At 30 FPS: **2,700,000 `snapshot()` calls per second** from this method alone.
For a typical game with ~20 flags: the loop examines 89,980 non-flagged cells uselessly.
Useful work fraction: 20 / 90,000 = **0.022 %**.

### Context: what the rest of `_draw_board` already does correctly

`_draw_board` (lines 736–739) computes viewport culling bounds immediately after calling
`_draw_image_ghost`:

```python
tx0 = max(0, (-self._pan_x) // ts - 1)
ty0 = max(0, (-self._pan_y) // ts - 1)
tx1 = min(self.board.width, (win_w - ox) // ts + 2)
ty1 = min(self.board.height, (win_h - oy) // ts + 2)
```

These bounds are local to `_draw_board`. They are NOT passed into `_draw_image_ghost`.
`_draw_image_ghost` is called at line 718, before `tx0/ty0/tx1/ty1` are computed (line 736).
The board clip rect IS set before `_draw_image_ghost` (lines 712–714), so off-screen blits
are discarded by pygame at the C level — but Python-level allocation and iteration still run.

### Additional note: `_draw_image_ghost` is also called from `_draw_win_animation_fx`

`_draw_win_animation_fx` (lines 1021–1043) uses a similar per-cell pattern on `win_anim_set`
(a set of coordinates already bounded). It is NOT affected by this bug.

---

## 2. Constraints and Invariants

Before evaluating solutions, these facts are fixed:

1. `_ghost_surf` (full board pixel size) is already cached — rebuilds only when `(bw, bh)` changes.
   Calling `smoothscale` per frame is not the problem; this cache works correctly.

2. Two alpha values are required: `200` for flagged mines, `40` for flagged non-mines.
   Any solution must respect this distinction.

3. The board clip rect is set before this method is called — `self._win.set_clip(clip_rect)`.
   Blits outside the visible board area will be clipped by pygame regardless.

4. `self.board._flagged`, `self.board._mine` are numpy `bool` arrays of shape `(H, W)`.
   Direct indexed access is O(1). `np.where()` is O(H×W) but C-speed (~1 µs for 300×300).

5. At `MIN_TILE_SIZE = 10`, a 300×300 board produces `_ghost_surf` of 3000×3000 px = 36 MB.
   At `BASE_TILE = 32`, a 9×9 board → 288×288 = 332 KB. Both are within reason.

6. The number of flagged cells at any one time: typically 0–200 for a 300×300 board
   (total_mines = ~4794 for the Tessa board; a player might flag 50–300 during gameplay).

---

## 3. The Five Solutions

---

### Solution 1 — Viewport Culling + Direct Array Access

**Philosophy:** Minimal change. Mirror exactly what `_draw_board` does. Eliminate the two worst
problems (full iteration + `snapshot()` allocations) without changing architecture.

**Complexity:** Low | **Risk:** Very low | **Implementation delta:** ~10 lines changed

#### Approach

Recompute the same `tx0/ty0/tx1/ty1` bounds inside `_draw_image_ghost` (or receive them as
parameters from `_draw_board`). Replace `board.snapshot()` with direct array reads.

```python
def _draw_image_ghost(self, ox, oy, bw, bh):
    if not self._image_surf:
        return

    if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
        self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))

    scaled = self._ghost_surf
    ts     = self._tile
    _flagged = self.board._flagged
    _mine    = self.board._mine

    # Recompute viewport bounds (same formula as _draw_board:736-739)
    win_w, win_h = self._win.get_size()
    tx0 = max(0, (-self._pan_x) // ts - 1)
    ty0 = max(0, (-self._pan_y) // ts - 1)
    tx1 = min(self.board.width,  (win_w - ox) // ts + 2)
    ty1 = min(self.board.height, (win_h - oy) // ts + 2)

    for y in range(ty0, ty1):
        for x in range(tx0, tx1):
            if not _flagged[y, x]:
                continue
            px = ox + x * ts
            py = oy + y * ts
            src_rect = pygame.Rect(x * ts, y * ts, ts, ts)
            sub = scaled.subsurface(src_rect).copy()
            sub.set_alpha(200 if _mine[y, x] else 40)
            self._win.blit(sub, (px, py))
```

#### Performance profile

| Scenario | Before | After |
|----------|--------|-------|
| 300×300 board, scrolled to show ~1000 tiles | 90,000 iters | ~1,000 iters |
| 300×300 board at min zoom (all tiles visible) | 90,000 iters | ~90,000 iters |
| 9×9 board (small) | 81 iters | 81 iters (no change) |

Worst case (all tiles visible, fully zoomed out): no improvement. This is acceptable because at
`MIN_TILE_SIZE=10` with a 300×300 board, each tile is 10×10 px — the viewport shows the entire
board. But typical gameplay involves zooming into a region, where this solution provides 10–100×
speedup.

#### Edge cases

- `ts == 0`: Cannot happen; `MIN_TILE_SIZE = 10`. No guard needed.
- `tx1 <= tx0` or `ty1 <= ty0`: When the viewport is entirely outside the board — loop body
  never executes. Correct.
- Pan values out of bounds: `_clamp_pan()` always runs before any draw. Safe.
- 0 flags in viewport: fast-skip within loop, no surface allocations. Correct.
- The `-1` / `+2` slack in bounds formula matches `_draw_board` exactly — no off-by-one.

#### Why this is Solution 1 and not higher

The `subsurface().copy() + set_alpha()` allocation pattern remains. For 200 visible flagged
cells, that's 200 Surface allocations per frame × 30 FPS = 6,000/sec. Acceptable for typical
flag counts but not optimal. More critically, it still iterates ALL visible tiles (not just
flagged ones), which is wasteful when the viewport contains 1,000 tiles but only 10 are flagged.

---

### Solution 2 — NumPy Sparse Flagged Index: O(N_flags) Iteration

**Philosophy:** Replace the nested Python loop entirely with a single vectorized numpy scan,
then iterate only the flagged cells by coordinate. This is the natural use of numpy: batch
finding, not per-element Python logic.

**Complexity:** Low | **Risk:** Very low | **Implementation delta:** ~8 lines changed

#### Approach

`np.where(array)` returns a tuple of index arrays `(row_indices, col_indices)` for all `True`
elements, executing a single C-speed pass over the array. For `board._flagged` (300×300 bool):
this takes approximately 1–2 µs and returns typically 0–300 coordinate pairs.

```python
def _draw_image_ghost(self, ox, oy, bw, bh):
    if not self._image_surf:
        return

    if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
        self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))

    scaled   = self._ghost_surf
    ts       = self._tile
    _flagged = self.board._flagged
    _mine    = self.board._mine

    # One vectorized pass — returns only flagged cell coordinates
    flag_ys, flag_xs = np.where(_flagged)          # ~1-2 µs for 300×300

    # Optional: filter to viewport (saves blits for off-screen flags)
    win_w, win_h = self._win.get_size()
    tx0 = max(0, (-self._pan_x) // ts - 1)
    ty0 = max(0, (-self._pan_y) // ts - 1)
    tx1 = min(self.board.width,  (win_w - ox) // ts + 2)
    ty1 = min(self.board.height, (win_h - oy) // ts + 2)

    for fy, fx in zip(flag_ys, flag_xs):
        if not (tx0 <= fx < tx1 and ty0 <= fy < ty1):
            continue                               # skip off-screen flags
        px = ox + fx * ts
        py = oy + fy * ts
        src_rect = pygame.Rect(int(fx) * ts, int(fy) * ts, ts, ts)
        sub = scaled.subsurface(src_rect).copy()
        sub.set_alpha(200 if _mine[int(fy), int(fx)] else 40)
        self._win.blit(sub, (px, py))
```

#### Performance profile

| Scenario | Before | After |
|----------|--------|-------|
| 300×300, 20 flags | 90,000 Python iters | 1 numpy pass (2µs) + 20 Python iters |
| 300×300, 300 flags | 90,000 Python iters | 1 numpy pass + 300 Python iters |
| 9×9, 5 flags | 81 iters | 1 numpy pass + 5 iters |
| 0 flags | 90,000 iters (skip all) | 1 numpy pass + 0 iters |

For any realistic flag count this is a strict improvement. The 90,000-iteration loop is
completely eliminated regardless of viewport size.

#### Edge cases

- `np.where` on 0 flags: returns `(array([]), array([]))`. `zip` of two empty arrays produces
  an empty iterator. Loop body never executes. Correct.
- `flag_ys`, `flag_xs` are numpy `int64` arrays. `int(fx)` cast needed for `Rect()` and
  array indexing, since pygame Rect expects Python int, not numpy int64.
- `np.where` returns row-major order (y first, x second), matching `(H, W)` array layout. ✓
- Viewport filter: the `if not (tx0 <= fx < tx1 ...)` check is Python int comparison, O(1).
  For very large flag counts (>1000), could use a vectorized numpy filter instead:
  ```python
  vp_mask = ((flag_xs >= tx0) & (flag_xs < tx1) &
             (flag_ys >= ty0) & (flag_ys < ty1))
  flag_ys, flag_xs = flag_ys[vp_mask], flag_xs[vp_mask]
  ```
  This replaces the in-loop check with a single O(N_flags) numpy filter before the loop.

#### Why this is Solution 2 and not higher

Surface allocation per flagged cell remains. For 300 flags × 30 FPS = 9,000 Surface objects/sec.
This is still measurable GC pressure. The nested Python loop is eliminated, which is the dominant
cost at low flag counts. However, for high flag counts (late-game, many flags placed), the
surface allocation becomes the bottleneck.

---

### Solution 3 — Dirty-Tracked Pre-Composited Ghost Overlay

**Philosophy:** Invest computation at the moment flags change (once per flag action) instead
of every frame (30× per second). Separate the "what changed" event from the "render" event.
Per-frame draw becomes a single `blit()` call.

**Complexity:** Medium | **Risk:** Low | **Implementation delta:** ~40 lines added/changed

#### Approach

Maintain a persistent `_ghost_overlay_surf` (SRCALPHA, same dimensions as `_ghost_surf`).
Track a generation counter (or flag sum) to detect when the overlay needs rebuild.
On rebuild: iterate flagged cells (Solution 2 pattern), blit tile subsurfaces with correct
alpha into the persistent surface. On each draw frame: blit the surface.

```python
# Added to __init__:
self._ghost_overlay_surf: Optional[pygame.Surface] = None
self._ghost_overlay_bw:   int = 0     # last bw at which overlay was built
self._ghost_overlay_bh:   int = 0
self._ghost_flag_gen:     int = -1    # detected flag-state generation

def _rebuild_ghost_overlay(self, bw, bh):
    """Rebuild the full-board ghost overlay. Called only when flags change or tile changes."""
    if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
        self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))

    surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
    surf.fill((0, 0, 0, 0))   # fully transparent baseline

    scaled   = self._ghost_surf
    ts       = self._tile
    _flagged = self.board._flagged
    _mine    = self.board._mine
    flag_ys, flag_xs = np.where(_flagged)

    for fy, fx in zip(flag_ys, flag_xs):
        src_rect = pygame.Rect(int(fx) * ts, int(fy) * ts, ts, ts)
        sub = scaled.subsurface(src_rect).copy()
        sub.set_alpha(200 if _mine[int(fy), int(fx)] else 40)
        surf.blit(sub, (int(fx) * ts, int(fy) * ts))

    self._ghost_overlay_surf = surf
    self._ghost_overlay_bw   = bw
    self._ghost_overlay_bh   = bh
    self._ghost_flag_gen     = int(self.board._flagged.sum())

def _draw_image_ghost(self, ox, oy, bw, bh):
    if not self._image_surf:
        return

    # Detect if overlay needs rebuild
    current_gen = int(self.board._flagged.sum())
    needs_rebuild = (
        self._ghost_overlay_surf is None
        or self._ghost_overlay_bw != bw
        or self._ghost_overlay_bh != bh
        or self._ghost_flag_gen   != current_gen
    )

    if needs_rebuild:
        self._rebuild_ghost_overlay(bw, bh)

    # Per-frame cost: one blit
    self._win.blit(self._ghost_overlay_surf, (ox, oy))
```

#### Performance profile

| Event | Cost |
|-------|------|
| Frame (no flag change) | 1 surface blit ~= 1 µs |
| Frame (flag just changed) | 1 rebuild (O(N_flags) iters) + 1 blit |
| Zoom (tile changed) | 1 full rebuild (bw/bh changed) |
| 30 FPS steady state | ~30 µs total vs ~2,000,000 µs before |

#### Generation counter analysis

`int(self.board._flagged.sum())` counts the number of True cells in a (H,W) bool array.
For 300×300: numpy vectorized sum = ~2 µs. Called every frame.

**False-negative risk:** Can two simultaneous flag changes (one added, one removed) produce
the same sum? Yes: unflag at (0,0) and flag at (1,1) → sum unchanged → overlay not rebuilt.
But this is structurally impossible in the current engine: one action = one `right_click()` =
one `toggle_flag()` = one cell state change. The renderer draws between each action.

**Robust alternative:** Store `self._ghost_flag_hash: bytes` using
`self.board._flagged.tobytes()` (computes a hash-comparable bytes object). Or store
`self._prev_flagged: np.ndarray` and use `np.array_equal(self.board._flagged, self._prev_flagged)`.
The sum is sufficient for the current single-action-per-frame design; use `tobytes()` if
multi-action batch processing is ever added.

#### Edge cases

- `_ghost_overlay_surf` built at different `bw/bh` than current: `_ghost_overlay_bw != bw`
  triggers a full rebuild. Zoom always rebuilds. ✓
- Board restart (new `Board` object): `self.board` reference changes. The flag array is all
  zeros → `sum = 0`. If previous sum was also 0 (no flags placed before restart), rebuild
  NOT triggered → stale overlay. Fix: track `id(self.board)` as a generation component:
  `self._ghost_board_id` compared on each call.
- 0 flags: `_ghost_overlay_surf` is fully transparent. One transparent blit per frame.
  Cost = 1 blit. No visible effect. Correct.
- Full board flagged (theoretical max): rebuild iterates all cells once. Same cost as Solution 2.
- `blit(self._ghost_overlay_surf, (ox, oy))`: `ox = BOARD_OX + _pan_x`. The overlay is
  board-pixel-size, positioned at the board origin including pan. The active clip rect
  (set in `_draw_board` before this call) ensures nothing draws outside the board. ✓
- Memory: `bw × bh × 4 bytes`. At tile=10, 300×300: 3000×3000×4 = 36 MB. Acceptable.
  At BASE_TILE=32, 9×9: 288×288×4 = 332 KB. Trivial.

#### Why this is Solution 3 and not higher

The generation counter check (`_flagged.sum()`) costs ~2 µs/frame even when nothing changed.
The rebuild still uses `subsurface().copy() + set_alpha()` surface allocations per flagged cell
(same as Solution 2), so rebuilds are not free. The overlay surface is `(bw × bh)` — for the
largest board at max tile size this is 36 MB (manageable but notable). Solution 4 eliminates
the per-flag surface allocations during rebuild.

---

### Solution 4 — Incremental Dirty-Rectangle Update (Classic Game Dev Pattern)

**Philosophy:** Only update the pixel region that actually changed. Flag a cell → update exactly
that cell's tile rect in the overlay. No full rebuild. Per-frame: one blit. Per-flag-action:
one tile-sized blit into the overlay.

This is the industry-standard "dirty rect" pattern from all pre-GPU 2D game engines (SDL 1.x,
DirectDraw, Amiga blitter). It decouples render frequency from state-change frequency.

**Complexity:** Medium | **Risk:** Low-Medium | **Implementation delta:** ~50 lines

#### Approach

The renderer already has the infrastructure for event-driven updates (`cascade`, `win_anim`).
Add a flag-change notification path:

**Engine side:** `MoveResult.flagged` already returns the new cell state string (`"flag"`,
`"question"`, `"hidden"`). `MoveResult` does NOT return the (x, y) coordinates, but
`main.py:_do_right_click` has them. Add them to `MoveResult`:

```python
# engine.py: MoveResult — add flag_pos field
class MoveResult:
    __slots__ = (..., "flag_pos")
    def __init__(self, ..., flag_pos: Optional[Tuple[int,int]] = None):
        ...
        self.flag_pos = flag_pos  # (x,y) of flag action, or None
```

Or — keep the engine untouched. In `main.py._do_right_click(x, y)`:
```python
def _do_right_click(self, x, y):
    state = self._engine.right_click(x, y)
    self._renderer.notify_flag_changed(x, y)   # <-- add this
    return state
```

**Renderer side:** `notify_flag_changed(x, y)` updates only the (x,y) tile in the overlay:

```python
def notify_flag_changed(self, x: int, y: int):
    """Update the single tile at (x,y) in the ghost overlay. O(1) per flag action."""
    if not self._image_surf or self._ghost_overlay_surf is None:
        self._ghost_flag_dirty_all = True   # fallback: full rebuild next frame
        return

    ts       = self._tile
    _flagged = self.board._flagged
    _mine    = self.board._mine
    bw, bh   = self._ghost_overlay_surf.get_size()

    # Clear the tile region in the overlay (make it transparent)
    tile_rect = pygame.Rect(x * ts, y * ts, ts, ts)
    self._ghost_overlay_surf.fill((0, 0, 0, 0), tile_rect)

    # If now flagged: blit the image tile with correct alpha
    if _flagged[y, x] and self._ghost_surf:
        src_rect = pygame.Rect(x * ts, y * ts, ts, ts)
        sub = self._ghost_surf.subsurface(src_rect).copy()
        sub.set_alpha(200 if _mine[y, x] else 40)
        self._ghost_overlay_surf.blit(sub, tile_rect.topleft)
```

`_draw_image_ghost` reduces to:
```python
def _draw_image_ghost(self, ox, oy, bw, bh):
    if not self._image_surf:
        return

    if (self._ghost_overlay_surf is None
            or self._ghost_overlay_surf.get_size() != (bw, bh)
            or getattr(self, '_ghost_flag_dirty_all', True)):
        self._rebuild_ghost_overlay(bw, bh)
        self._ghost_flag_dirty_all = False

    self._win.blit(self._ghost_overlay_surf, (ox, oy))
```

#### Performance profile

| Event | Cost |
|-------|------|
| Frame (steady state) | 1 blit, ~1 µs |
| Flag placed / removed | 1 tile-clear + 1 subsurface copy + 1 blit = ~5 µs |
| Zoom | Full rebuild: O(N_flags) iters |
| Board restart | Full rebuild (dirty_all=True) |

This is the asymptotically optimal solution: O(1) per frame, O(1) per flag action.

#### Edge cases

- **`notify_flag_changed` called before overlay is initialized:** `self._ghost_overlay_surf is None`
  → sets `_ghost_flag_dirty_all = True` → `_draw_image_ghost` triggers full rebuild next frame. ✓
- **Fog mode:** When fog is enabled, flagged cells are drawn as hidden tiles (`_draw_cell`
  handles this at line 807: `pygame.draw.rect(self._win, C["tile_hidden"], ...)` skipping the
  flag visual). The ghost overlay is still maintained correctly in the background. When fog is
  toggled off, it shows immediately. ✓
- **Chord revealing a flagged cell:** Chording can reveal cells. A flagged cell can't be revealed
  (engine guards this at `reveal()` line 168: `if self._revealed[y, x] or self._flagged[y, x]:`).
  So a flagged cell is never simultaneously revealed — no conflicting state. ✓
- **Win animation:** `_draw_win_animation_fx` draws on top of cells after `_draw_image_ghost`
  runs. The ghost overlay is drawn first, then win animation overlays it. Ordering preserved. ✓
- **`_ghost_surf` not yet built (first frame):** `_draw_image_ghost` rebuilds `_ghost_surf` as
  before. `notify_flag_changed` checks `self._ghost_surf` before using it. First frame always
  triggers a full rebuild. ✓
- **Question mark state:** `toggle_flag` cycles hidden→flag→question→hidden. In "question" state,
  `_flagged[y,x] = False`, `_questioned[y,x] = True`. `notify_flag_changed` checks `_flagged`
  — finds False → clears tile, doesn't redraw image. Ghost image hidden for questioned cells. ✓
- **Multiple rapid flag changes** (e.g., scripted/test input): Each change triggers one tile
  update. No race condition — Python is single-threaded, pygame events are processed serially.

#### Why this is Solution 4 and not higher

Requires coupling: `main.py` must call `self._renderer.notify_flag_changed(x, y)` after every
`right_click`. This is a cross-module dependency that violates the "renderer is a passive
observer of engine state" invariant. Solutions 3 and 5 are self-contained within the renderer.
Also, `subsurface().copy() + set_alpha()` per tile still happens on each flag action — this could
be eliminated by Solution 5's pre-baked alpha approach.

---

### Solution 5 — Dual Pre-Baked Alpha Layers + Per-Frame Stencil Blit (Maximum Long-Term Elegance)

**Philosophy:** Pre-compute everything that doesn't change at flag-time (the mine map and the
image pixels). Represent the flag state as a minimal boolean "stencil" that gates which pixels
show through. Per-frame render = 1 masked blit. Per-flag-action = 1 tile update to the stencil.
Never create per-frame Surface objects.

This is the classic "layer compositing" approach used in game engines (Photoshop layer modes,
video compositing, shader-based rendering).

**Complexity:** High | **Risk:** Medium | **Implementation delta:** ~80 lines + numpy pixel ops

#### Approach

**At init / tile-change (one-time cost):**

Pre-bake two board-sized SRCALPHA surfaces from `_ghost_surf`:

```
_ghost_mine_layer:  SRCALPHA surface, board-pixel size
    → image pixels at mine positions,   alpha = 200
    → transparent (alpha = 0) everywhere else

_ghost_safe_layer:  SRCALPHA surface, board-pixel size
    → image pixels at safe positions,   alpha = 40
    → transparent (alpha = 0) everywhere else
```

These depend only on `_mine` (static for a given board) and `_ghost_surf` (static until tile
changes). Built ONCE at init and on tile-size change.

Construction using numpy pixel array manipulation:

```python
def _build_ghost_layers(self, bw, bh):
    """Build static per-layer surfaces from ghost image and mine map.
    Called once at init and on tile size change only."""
    if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
        self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))

    ts = self._tile
    H, W = self.board.height, self.board.width
    _mine = self.board._mine      # (H, W) bool array

    # Start with the scaled ghost image copied to two surfaces
    mine_layer = self._ghost_surf.copy().convert_alpha()
    safe_layer = self._ghost_surf.copy().convert_alpha()

    # Use pygame.surfarray to set alpha per-pixel without Python loop
    # surfarray gives a (W, H) view: note transposed axes in pygame surfarray
    mine_alpha = pygame.surfarray.pixels_alpha(mine_layer)   # shape (bw, bh), writable
    safe_alpha = pygame.surfarray.pixels_alpha(safe_layer)

    # For each tile (col x, row y): set alpha = 200/40 where mine/safe, 0 elsewhere
    # Build alpha mask arrays of shape (bw, bh) using tile-expanded mine map
    import numpy as np
    # Expand mine map to pixel resolution via repeat
    mine_px = np.repeat(np.repeat(_mine.astype(np.uint8) * 200, ts, axis=0), ts, axis=1)
    # mine_px shape: (H*ts, W*ts) = (bh, bw) — need to transpose for surfarray (bw, bh)
    mine_alpha[:, :] = mine_px.T
    safe_px  = np.repeat(np.repeat((~_mine).astype(np.uint8) * 40, ts, axis=0), ts, axis=1)
    safe_alpha[:, :] = safe_px.T

    del mine_alpha  # release surfarray lock
    del safe_alpha

    self._ghost_mine_layer = mine_layer
    self._ghost_safe_layer = safe_layer
```

**At flag-change (per-action cost):**

Maintain a stencil surface (SRCALPHA, board-pixel size) where each tile is either "white"
(flagged — reveal image) or "black" (hidden). Update only the changed tile.

```python
def notify_flag_changed(self, x: int, y: int):
    ts = self._tile
    tile_rect = pygame.Rect(x * ts, y * ts, ts, ts)
    if self.board._flagged[y, x]:
        self._ghost_stencil.fill((255, 255, 255, 255), tile_rect)  # reveal
    else:
        self._ghost_stencil.fill((0, 0, 0, 255), tile_rect)        # hide
```

**Per-frame render:**

```python
def _draw_image_ghost(self, ox, oy, bw, bh):
    if not self._image_surf:
        return
    # Apply stencil to both pre-baked layers and blit to window
    # BLEND_RGBA_MULT: result_alpha = layer_alpha * stencil_alpha / 255
    # White stencil (255) → reveals layer at its preset alpha (200 or 40)
    # Black stencil (0)   → multiplies alpha to 0 → fully transparent

    mine_frame = self._ghost_mine_layer.copy()
    mine_frame.blit(self._ghost_stencil, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    self._win.blit(mine_frame, (ox, oy))

    safe_frame = self._ghost_safe_layer.copy()
    safe_frame.blit(self._ghost_stencil, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
    self._win.blit(safe_frame, (ox, oy))
```

**Optimization:** Eliminate the `.copy()` per frame by pre-applying the stencil into a
persistent `_ghost_composite_surf` that is only rebuilt when the stencil changes. Combined with
Solution 4's dirty-rect approach: `notify_flag_changed` updates the stencil tile AND the
composite. Per-frame: 1 blit. No allocations.

#### Performance profile

| Event | Cost |
|-------|------|
| Frame (steady state) | 2 blits (or 1 if fully composited), 0 allocations |
| Flag placed / removed | 1 `surface.fill()` on stencil tile = ~1 µs |
| Init / tile change | 1 `smoothscale` + 2 surfarray writes, ~100 ms for 300×300 at tile=10 |

#### Edge cases

- `np.repeat(..., ts, axis=0)` for tile expansion: produces pixel-resolution mine map. For
  300×300 at tile=10: shape = (3000, 3000). Memory: 9 MB per array. Two temporary arrays =
  18 MB extra during build. Released immediately.
- `pygame.surfarray.pixels_alpha` returns a 2D view of alpha channel, shape `(width, height)`.
  Note: pygame surfarray uses `(x, y)` ordering = `(W, H)` = transposed from numpy `(H, W)`.
  The `.T` transpose corrects this.
- `del mine_alpha` releases the surfarray lock on the surface. MUST be called before any other
  pygame operations on the surface.
- Board restart: new `Board` has new `_mine` array → `_ghost_mine_layer` and `_ghost_safe_layer`
  must be rebuilt. Track `id(self.board)` as a rebuild trigger.
- `.copy()` per frame in the naive version: 2 full board-sized Surface copies per frame.
  At 300×300 at tile=10: 2 × 36 MB copies = expensive. The optimization (pre-composited
  `_ghost_composite_surf` updated only on stencil change) eliminates this.
- If `notify_flag_changed` is not implemented (main.py not updated), can fall back to Solution 3's
  generation-counter dirty check.
- `BLEND_RGBA_MULT`: available in pygame >= 1.8. The project uses pygame >= 2.3. ✓

#### Why this is Solution 5 (highest architectural integrity)

Most complex to implement, requires surfarray pixel manipulation and coordination between
main.py notification and renderer. Pre-bake cost at tile=10 for 300×300 board is ~100ms
(one-time, at start or zoom). Not appropriate as a "quick fix" but is the architecturally
cleanest long-term design — the only solution with zero per-frame Python work and zero
per-flag-action Surface allocations.

---

## 4. Comparative Matrix — M-001

| Criterion | Sol 1 · Viewport | Sol 2 · np.where | Sol 3 · Dirty Cache | Sol 4 · Dirty Rect | Sol 5 · Layer Stencil |
|-----------|:----------------:|:----------------:|:-------------------:|:-----------------:|:---------------------:|
| Per-frame Python iters | O(viewport) | O(N_flags) | 0 | 0 | 0 |
| Surface allocs / frame | O(vis_flags) | O(vis_flags) | 0 | 0 | 0 (after composite) |
| Steady-state frame cost | ~1–5 µs | ~2 µs + iters | ~1 µs blit | ~1 µs blit | ~2 µs blits |
| Impl. complexity | Low | Low | Medium | Med-High | High |
| Coupling to main.py | None | None | None | Yes (notify) | Yes (notify) |
| Handles zoom correctly | ✓ | ✓ | ✓ (bw/bh guard) | ✓ (dirty_all) | ✓ (rebuild layers) |
| Handles restart correctly | ✓ | ✓ | Need board ID | Need board ID | Need board ID |
| Extra memory | 0 | 0 | bw×bh×4 | bw×bh×4 | 3×bw×bh×4 |
| Risk of regression | Very low | Very low | Low | Low-Med | Medium |

### Recommendation

**Immediate fix:** Solution 2 (np.where sparse iteration). 5 lines changed, zero architectural
risk, eliminates 99.97% of the wasteful iteration. Add viewport filter for the edge case where
all cells are visible.

**Long-term target:** Solution 3 (dirty-tracked overlay) built on top of Solution 2's rebuild
logic. Zero per-frame iteration, self-contained in the renderer, no main.py coupling.

**Final state (if performance budget allows):** Solution 4 or 5 for O(1) per flag action.
Implement only after benchmarking confirms Solution 3 is insufficient at extreme flag counts.

---
---

# PART B — M-002: `_on_resize()` Does Not Update Button Y Positions After Zoom

## 1. Exact Problem Statement

Three distinct bugs, all in `renderer.py`:

### Bug 2A — `not _panel_right`: `oy` computed but never applied (line 591)

```python
def _on_resize(self):
    if not self._panel_right:
        bx = self.PAD
        oy = int(self.BOARD_OY + self.board.height * self._tile + self.PAD)  # computed
        self._btn_new.x = bx      # x updated
        self._btn_help.x = bx
        self._btn_fog.x = bx
        self._btn_save.x = bx
        self._btn_restart.x = bx
        # *** oy is NEVER applied to any .y attribute ***
```

**Impact:** For large boards (≥100 tiles wide, `_panel_right = False`), button y positions are
frozen at their `__init__` values. After zooming in from tile=10 to tile=12 on a 300-tall board:
- Init y (tile=10): `oy = 60 + 3000 + 12 = 3072`
- Post-zoom y (tile=12): `oy = 60 + 3600 + 12 = 3672` — 600px below init
- Buttons still at y=3072 — visually overlapping the board after zoom in
- `_draw_panel` draws "CONTROLS" label correctly at y=3672, but buttons at y=3072 — drift visible
- `handle_panel` uses `self._btn_*.y` → buttons respond to wrong screen region

### Bug 2B — `_panel_right = True`: entire `_on_resize` branch not entered (line 589)

```python
def _on_resize(self):
    if not self._panel_right:   # <-- this is False for small boards; body never runs
        ...
    # Nothing for _panel_right = True case
```

For small boards (`_panel_right = True`), the panel sits to the RIGHT of the board. When zoom
changes `self._tile`, the board pixel width changes, shifting the panel x:

```
panel x = board.width * self._tile + self.BOARD_OX + self.PAD
```

Example — Easy board (9 tiles wide), zoom from tile=32 to tile=22:
- Init `px = 9×32 + (12+240) + 12 = 288 + 264 = 552`
- Post-zoom `px = 9×22 + 264 = 198 + 264 = 462`
- Button x frozen at 552; panel visually draws at 462 — **90 px visual/hittest desync**

For this case, button y is `BOARD_OY = 60` (a constant — does NOT change with zoom). So only
x is wrong.

### Bug 2C — `sy` formula double-counts panel origin (line 963)

```python
sy = oy + self._btn_restart.bottom + 12
```

`self._btn_restart.bottom` is an ABSOLUTE window y coordinate (not a relative offset).
`oy` is also an absolute window y coordinate. Adding them double-counts the panel origin.

At `_panel_right = True`, Easy board, init (tile=32):
- `oy = BOARD_OY = 60`
- `_btn_restart = Rect(552, 60 + (29+5)*4, btn_w, 29) = Rect(552, 196, btn_w, 29)`
- `_btn_restart.bottom = 225`
- `sy = 60 + 225 + 12 = 297` — stats drawn 60 px below correct position (237)

At `_panel_right = False`, large board, init (tile=10):
- `oy = 3072`
- `_btn_restart.bottom = 3232`
- `sy = 3072 + 3232 + 12 = 6316` — STATS NEVER VISIBLE (window height < 1000 px)
- Stats are completely inaccessible for large boards regardless of zoom

### Confirmed: `_on_resize` is called by MOUSEWHEEL only

Looking at `handle_event`:
- Line 520: MOUSEWHEEL → `self._clamp_pan()` → `self._on_resize()` → `self._rebuild_num_surfs()`
- Line 416: VIDEORESIZE → `self._win = ...set_mode(ev.size...)` → `self._center_board()`
  — does NOT call `_on_resize()`. For VIDEORESIZE, tile doesn't change → button positions
  don't need updating → this omission is benign.

### Also: `btn_h` is not updated on zoom

At init (line 318): `btn_h = max(28, font_base + 10)` where `font_base = max(9, tile * 3 // 5)`.
After zoom: `self._tile` changes → `font_base` changes → `btn_h` should change. But `btn_h` is
a local variable; buttons keep their original height. In practice: at tile=10, `btn_h=28`; at
tile=32, `btn_h=29`. Difference is 1 px — negligible, not worth special-casing.

---

## 2. Constraints and Invariants

1. `self._panel_right: bool` — set in `__init__` based on `board.width < 100`. NEVER changes
   after init (zoom doesn't change board dimensions in tiles, only pixel rendering). ✓
2. `self.BOARD_OX`, `self.BOARD_OY`, `self.PAD`, `self.PANEL_W` — all set in `__init__`,
   never modified. ✓
3. `self._tile` — modified by MOUSEWHEEL handler, is the only source of button drift.
4. `self._btn_w = self.PANEL_W - 2 * self.PAD` — constant. ✓
5. `_draw_panel` (lines 927-1016) recomputes `px` and `oy` dynamically each call — the
   "CONTROLS" title and stats/tips text DRAW at correct positions already. Only the button
   RECTS and the `sy` formula are wrong.
6. `handle_panel` (lines 546-567) uses stored rects exclusively for hit testing.
7. Any solution must maintain both drawing and hit-testing in sync.

---

## 3. The Five Solutions

---

### Solution 1 — Complete `_on_resize()` Symmetrically

**Philosophy:** Fix the existing approach by filling its gaps. `_on_resize()` was designed to
update button positions; it's just incomplete. Complete it to be a mirror of `__init__` layout
logic. Fix `sy` formula as a bonus.

**Complexity:** Very low | **Risk:** Very low | **Delta:** ~15 lines changed

#### Approach

```python
def _on_resize(self):
    """Recompute ALL button positions after tile-size change. Symmetric with __init__ layout."""
    btn_h = self._btn_new.height   # height doesn't significantly change with zoom
    gap   = max(4, btn_h // 5)

    if self._panel_right:
        # Panel is to the RIGHT of the board — only x changes with tile
        px = self.board.width * self._tile + self.BOARD_OX + self.PAD
        oy = self.BOARD_OY                     # constant — does not change with zoom
    else:
        # Panel is BELOW the board — only y changes with tile
        px = self.PAD                          # constant
        oy = int(self.BOARD_OY + self.board.height * self._tile + self.PAD)

    for i, btn in enumerate([self._btn_new, self._btn_help,
                              self._btn_fog, self._btn_save, self._btn_restart]):
        btn.x = px
        btn.y = oy + (btn_h + gap) * i
```

Fix `sy` formula in `_draw_panel` (line 963):
```python
# Before (buggy):
sy = oy + self._btn_restart.bottom + 12
# After (correct):
sy = self._btn_restart.bottom + 12
```

#### Edge cases

- `btn_h` from `self._btn_new.height`: at init, `btn_h = max(28, font_base + 10)`. Font is
  rebuilt on zoom (`_rebuild_num_surfs` is called). BUT `self._font_small` and related are NOT
  rebuilt on zoom — fonts are built once at init. So `btn_h` doesn't change with zoom in
  practice (it's based on `tile * 3 // 5`, which barely changes: tile=10→btn_h=28,
  tile=32→btn_h=29). Using stored `self._btn_new.height` (28 or 29) is correct.
- `gap = max(4, btn_h // 5)` must match `__init__` formula. With `btn_h=28`: `gap=5`. ✓
- `oy + (btn_h + gap) * 0` = `oy` for first button — same as `pygame.Rect(px, oy, ...)`. ✓
- Very large board, tile zoomed to max (BASE_TILE=32): `oy = 60 + 300*32 + 12 = 9672`.
  Window height is capped at screen height (~900px). Buttons at y=9672 are off-screen.
  This is a display problem (panel below board at max zoom on large board), not a sync bug —
  the panel was always going to be off-screen at that zoom level. Out of scope for this fix.
- After `_on_resize()`, `_draw_panel` line 963 uses the now-correct `self._btn_restart.bottom`.
  With the `sy` fix (`sy = self._btn_restart.bottom + 12` instead of `oy + ...`), stats draw
  correctly. Both fixes must be applied together.

#### Why this is Solution 1 and not higher

"Complete the existing approach" is the minimum viable fix. It works but perpetuates the
architectural flaw: button positions are scattered across three places (`__init__`, `_on_resize`,
`_draw_panel`). Any future change to layout (add a button, change spacing) requires updating
all three sites. Solutions 2–5 address this root cause.

---

### Solution 2 — Lazy Layout via `_panel_origin()` + `_layout_buttons()` Helpers

**Philosophy:** Extract the layout math into one canonical helper. `__init__` and `_on_resize`
both call the same helper. Single source of truth for all position calculations.

**Complexity:** Low | **Risk:** Very low | **Delta:** ~25 lines, pure refactor

#### Approach

```python
def _panel_origin(self) -> Tuple[int, int]:
    """Returns (px, oy) — the top-left anchor of the control panel."""
    if self._panel_right:
        return (self.board.width * self._tile + self.BOARD_OX + self.PAD,
                self.BOARD_OY)
    else:
        return (self.PAD,
                int(self.BOARD_OY + self.board.height * self._tile + self.PAD))

def _layout_buttons(self):
    """Recompute and apply all button positions. Call from __init__ and _on_resize."""
    px, oy = self._panel_origin()
    btn_h  = max(28, max(9, self._tile * 3 // 5) + 10)
    gap    = max(4, btn_h // 5)
    btns   = [self._btn_new, self._btn_help, self._btn_fog,
              self._btn_save, self._btn_restart]
    for i, btn in enumerate(btns):
        btn.update(px, oy + (btn_h + gap) * i, self._btn_w, btn_h)
```

> `pygame.Rect.update(x, y, w, h)` modifies the rect in-place. ✓

```python
def __init__(self, ...):
    ...
    self._btn_new     = pygame.Rect(0, 0, 0, 0)   # placeholder
    self._btn_help    = pygame.Rect(0, 0, 0, 0)
    self._btn_fog     = pygame.Rect(0, 0, 0, 0)
    self._btn_save    = pygame.Rect(0, 0, 0, 0)
    self._btn_restart = pygame.Rect(0, 0, 0, 0)
    self._layout_buttons()   # fills in real positions

def _on_resize(self):
    self._layout_buttons()   # one call, always correct
```

Fix `sy` in `_draw_panel`:
```python
sy = self._btn_restart.bottom + 12   # absolute y, no double-count
```

#### Edge cases

- `btn_h = max(28, max(9, self._tile * 3 // 5) + 10)` — this is the exact `__init__` formula.
  At tile=10: `btn_h=28`. At tile=32: `btn_h=29`. At tile=15: `btn_h=max(28, 9+10)=28`. ✓
- `pygame.Rect.update()` — modifies x, y, w, h atomically. No intermediate inconsistent state.
- `_layout_buttons()` called during `__init__` after `self._btn_w` is set — must preserve
  init order. `self._btn_w = self.PANEL_W - 2 * self.PAD` at line 316; `_layout_buttons`
  must come after. ✓
- `_panel_origin()` is callable at any time (accesses only `self._tile`, `self.board.width`,
  `self.board.height` — all always-valid attributes).

#### Why this is Solution 2 and not higher

Still mutates 5 stored `pygame.Rect` objects. If `_layout_buttons()` is ever called while
`handle_panel` is mid-iteration (impossible in single-threaded Python, but worth noting), there
could be a momentary inconsistency. The stored-rect approach fundamentally requires keeping two
things in sync: the render-time position and the hittest-time position. Solutions 3–5 eliminate
this duality.

---

### Solution 3 — Compute-on-Demand: Live Rects, No Storage

**Philosophy:** Eliminate stored button positions entirely. Compute the rect for each button
freshly whenever needed — both for drawing and for hit testing. Stale state cannot exist if
there is no stored state.

**Complexity:** Low-Medium | **Risk:** Low | **Delta:** ~30 lines, some interface change

#### Approach

Define a single method that returns the button rects in order, computed fresh from current
`self._tile` and `self.board` dimensions:

```python
def _button_rects(self) -> List[pygame.Rect]:
    """Return all 5 button Rects, freshly computed. Never stale."""
    px, oy = self._panel_origin()         # same helper as Solution 2
    btn_h  = max(28, max(9, self._tile * 3 // 5) + 10)
    gap    = max(4, btn_h // 5)
    w      = self._btn_w
    return [
        pygame.Rect(px, oy + (btn_h + gap) * i, w, btn_h)
        for i in range(5)
    ]
```

`_draw_panel`:
```python
btns = self._button_rects()
buttons = [
    (btns[0], "Restart"),
    (btns[1], "Help"),
    (btns[2], "Hide Fog" if self.fog else "Toggle Fog"),
    (btns[3], "Save .npy"),
    (btns[4], "New Game"),
]
for rect, label in buttons:
    hover = rect.collidepoint(mx, my)
    ...
    pill(win, base_col, rect)
    ...
    win.blit(ts, ts.get_rect(center=rect.center))

# Stats anchor — use btn_h and gap directly, not .bottom
sy = btns[4].bottom + 12
```

`handle_panel`:
```python
def handle_panel(self, pos) -> Optional[str]:
    btns = self._button_rects()
    actions = ["restart", None, None, "save", "restart"]   # None → handled inline
    for i, btn in enumerate(btns):
        if btn.collidepoint(pos):
            if i == 1:   # Help
                self.help_visible = not self.help_visible
                return None
            if i == 2:   # Fog
                self.fog = not self.fog
                return None
            return actions[i]
    return None
```

`_on_resize`: deleted or made a no-op. (Or kept for future use with `pass`.)

The 5 `self._btn_*` attributes: kept as stubs for backwards compatibility OR removed if nothing
external references them. The test `test_f005a_btn_w_stored_on_self` checks `"self._btn_w" in src`
only — `_btn_w` is a separate attribute (still needed for thumbnail positioning) and is unaffected.

#### Edge cases

- **Performance:** `_button_rects()` creates 5 `pygame.Rect` objects per call. Called twice per
  frame (once in `_draw_panel`, once in `handle_panel` if a click occurred). 5 Rect() * 2 *
  30 FPS = 300 Rect allocations/sec. Each `pygame.Rect` allocation is ~100 ns. Total: 30 µs/sec
  = completely negligible.
- **`_btn_w` still needed:** Line 1016 uses `self._btn_w` for thumbnail positioning:
  `(px + (self._btn_w - thumb_w - 4) // 2, oy - thumb_h - 14)`. Keep `self._btn_w` as is. ✓
- **No stored `self._btn_*` Rects:** Any external test or code accessing `self._btn_new`
  directly would fail. The existing test `test_f005a_btn_w_stored_on_self` only checks `_btn_w`
  (not `_btn_new`). Safe to remove stored button rects. ✓
- **`_on_resize()` called from MOUSEWHEEL handler:** With Solution 3, `_on_resize` is a no-op
  — no harm in calling it. Remove it or leave it as `pass`.
- **Panel thumbnails still use `oy` from `_draw_panel`'s local variable:** `_draw_panel`
  computes `oy` dynamically → thumbnail at `(px, oy - thumb_h - 14)` remains correct. ✓
- **Fog button label changes at runtime:** "Hide Fog" vs "Toggle Fog". The label list is rebuilt
  every call to `_draw_panel` already — this is unchanged. ✓

#### Why this is Solution 3 and not higher

Creates new `pygame.Rect` objects every frame. While negligible in cost, it contradicts the
existing pattern of pre-allocated objects (`_anim_surf`, `_hover_surf`, `_num_surfs`). Also,
removing `self._btn_*` attributes is a breaking change if any external code or test accesses
them (currently safe; future risk). Solution 4 preserves the attribute interface while
eliminating stale state.

---

### Solution 4 — Layout Manager: `ControlPanel` Class Encapsulation

**Philosophy:** The root cause of all three bugs (2A, 2B, 2C) is that panel geometry is spread
across `__init__`, `_on_resize`, `_draw_panel`, and `handle_panel` — four sites that must be
kept in sync. Encapsulate the panel into a cohesive object with internal layout state,
consistent with industry-standard GUI component patterns (Qt QWidget, Android ViewGroup,
web CSS layout engine).

**Complexity:** Medium-High | **Risk:** Medium (refactor) | **Delta:** ~120 lines, new class

#### Approach

```python
class ControlPanel:
    """
    Encapsulates the control panel: layout, drawing, and hit testing.
    All geometry is computed from a single `layout()` call triggered by tile change.
    """

    LABELS = ["Restart", "Help", "Toggle Fog", "Save .npy", "New Game"]
    ACTIONS = ["restart", "_toggle_help", "_toggle_fog", "save", "restart"]

    def __init__(self, board: Board, tile: int, panel_right: bool,
                 board_ox: int, board_oy: int, panel_w: int, pad: int):
        self._board      = board
        self._tile       = tile
        self._panel_right = panel_right
        self._board_ox   = board_ox
        self._board_oy   = board_oy
        self._panel_w    = panel_w
        self._pad        = pad
        self._btn_w      = panel_w - 2 * pad

        self._rects: List[pygame.Rect] = []
        self._px    = 0
        self._oy    = 0
        self._btn_h = 28
        self._gap   = 5
        self._dirty = True

    def notify_resize(self, tile: int):
        """Called when tile size changes. Marks layout dirty."""
        self._tile  = tile
        self._dirty = True

    def layout(self):
        """Recompute all rects. Called lazily on first draw/hittest after dirty."""
        if not self._dirty:
            return
        if self._panel_right:
            self._px = self._board.width * self._tile + self._board_ox + self._pad
            self._oy = self._board_oy
        else:
            self._px = self._pad
            self._oy = int(self._board_oy + self._board.height * self._tile + self._pad)

        self._btn_h = max(28, max(9, self._tile * 3 // 5) + 10)
        self._gap   = max(4, self._btn_h // 5)
        self._rects = [
            pygame.Rect(self._px, self._oy + (self._btn_h + self._gap) * i,
                        self._btn_w, self._btn_h)
            for i in range(len(self.LABELS))
        ]
        self._dirty = False

    @property
    def stats_y(self) -> int:
        self.layout()
        return self._rects[-1].bottom + 12

    @property
    def origin(self) -> Tuple[int, int]:
        self.layout()
        return (self._px, self._oy)

    def draw(self, surface: pygame.Surface, mouse_pos: Tuple[int,int],
             fog: bool, fonts: dict):
        self.layout()
        ...

    def hit_test(self, pos: Tuple[int,int]) -> Optional[str]:
        self.layout()
        for rect, action in zip(self._rects, self.ACTIONS):
            if rect.collidepoint(pos):
                return action
        return None
```

`Renderer.__init__` replaces the 5 `_btn_*` Rect attributes with:
```python
self._panel = ControlPanel(
    board=self.board, tile=self._tile,
    panel_right=self._panel_right,
    board_ox=self.BOARD_OX, board_oy=self.BOARD_OY,
    panel_w=self.PANEL_W, pad=self.PAD
)
```

`_on_resize`:
```python
def _on_resize(self):
    self._panel.notify_resize(self._tile)
```

`_draw_panel` → `self._panel.draw(self._win, mouse_pos, self.fog, fonts=...)`
`handle_panel` → `return self._panel.hit_test(pos)`

#### Edge cases

- **Lazy layout:** `layout()` is called on first `draw()` or `hit_test()` after `notify_resize()`.
  The window draw and event handling happen in the correct order: events → (handle_panel calls
  hit_test → triggers layout if dirty) → draw (also triggers layout). Since layout is idempotent,
  calling it twice in the same frame is safe.
- **`_board.width`, `_board.height` used inside `layout()`:** These are board attributes that
  change only on restart (when a new `Board` is assigned to `engine.board`). The renderer's
  `self.board` reference is updated on restart:
  `self.board = engine.board` — but `ControlPanel._board` still points to the old Board.
  Fix: `notify_board_change(new_board)` method. Or: pass `board` as a callable / live reference.
  Alternatively, use `self._renderer.board` in `layout()` instead of a stored reference.
- **Fog label change:** "Toggle Fog" ↔ "Hide Fog". Currently handled in `_draw_panel`
  dynamically. In `ControlPanel.draw()`, must accept `fog: bool` parameter to update label.
- **Backwards compatibility:** `self._btn_new`, `self._btn_w` etc. are no longer attributes.
  `test_f005a_btn_w_stored_on_self` checks `"self._btn_w" in src` — `_btn_w` moves into
  `ControlPanel` as `self._panel._btn_w`. Test must be updated OR `_btn_w` kept as a passthrough
  property: `@property def _btn_w(self): return self._panel._btn_w`.

#### Why this is Solution 4 and not higher

The largest refactor of the five. Touches `__init__`, `_on_resize`, `_draw_panel`, `handle_panel`,
and requires a new class. Carries medium risk of introducing regressions during the refactor.
Architecturally superior but over-engineered for a 5-button panel. Solution 5 offers similar
correctness guarantees with less code.

---

### Solution 5 — Property-Based Dynamic Rects: Correct By Construction

**Philosophy:** Make it impossible for button positions to be stale by making them computed
properties that always derive from current `self._tile` and `self.board`. Remove the concept of
"stored button position" from the renderer's state space. A position that is never stored can
never be stale.

This is the "derived state" principle from functional programming and reactive UI frameworks
(React's render-from-props model, SwiftUI's computed body).

**Complexity:** Medium | **Risk:** Low | **Delta:** ~35 lines, property additions

#### Approach

```python
@property
def _panel_px(self) -> int:
    """Panel x origin. Always correct."""
    if self._panel_right:
        return self.board.width * self._tile + self.BOARD_OX + self.PAD
    return self.PAD

@property
def _panel_oy(self) -> int:
    """Panel y origin. Always correct."""
    if self._panel_right:
        return self.BOARD_OY
    return int(self.BOARD_OY + self.board.height * self._tile + self.PAD)

@property
def _panel_btn_h(self) -> int:
    return max(28, max(9, self._tile * 3 // 5) + 10)

@property
def _panel_gap(self) -> int:
    return max(4, self._panel_btn_h // 5)

def _panel_btn_rect(self, index: int) -> pygame.Rect:
    """Return Rect for button[index], always computed fresh."""
    return pygame.Rect(
        self._panel_px,
        self._panel_oy + (self._panel_btn_h + self._panel_gap) * index,
        self._btn_w,        # _btn_w = PANEL_W - 2*PAD: constant, keep as attribute
        self._panel_btn_h
    )
```

`_draw_panel` replaces the `buttons` list construction:
```python
def _draw_panel(self, mouse_pos, game_state, elapsed):
    px = self._panel_px      # property call
    oy = self._panel_oy      # property call
    ...
    buttons = [
        (self._panel_btn_rect(0), "Restart"),
        (self._panel_btn_rect(1), "Help"),
        (self._panel_btn_rect(2), "Hide Fog" if self.fog else "Toggle Fog"),
        (self._panel_btn_rect(3), "Save .npy"),
        (self._panel_btn_rect(4), "New Game"),
    ]
    ...
    sy = self._panel_btn_rect(4).bottom + 12   # correct: absolute y, no double-count
```

`handle_panel`:
```python
def handle_panel(self, pos) -> Optional[str]:
    if self._panel_btn_rect(0).collidepoint(pos): return "restart"
    if self._panel_btn_rect(1).collidepoint(pos):
        self.help_visible = not self.help_visible; return None
    if self._panel_btn_rect(2).collidepoint(pos):
        self.fog = not self.fog; return None
    if self._panel_btn_rect(3).collidepoint(pos): return "save"
    if self._panel_btn_rect(4).collidepoint(pos): return "restart"
    return None
```

`_on_resize`: no-op (or deleted). Tile change takes effect automatically via properties.
Stored `self._btn_new`, ..., `self._btn_restart` Rects: removed.

#### Handling `_btn_w` attribute (used for thumbnail, line 1016)

`self._btn_w = self.PANEL_W - 2 * self.PAD` does NOT depend on `self._tile`. Keep as attribute.
`_panel_btn_rect` uses `self._btn_w` directly. ✓

#### Edge cases

- **Per-frame Rect allocation:** `_panel_btn_rect(i)` creates one `pygame.Rect` per call.
  `_draw_panel` calls it 5 times; `handle_panel` calls it up to 5 times on each click event.
  At 30 FPS with no clicks: 5 × 30 = 150 Rect allocs/sec. Trivially cheap (~15 µs/sec).
- **Property calls vs attribute reads:** Each property call runs `if self._panel_right: ...` —
  1 branch + 2 multiplications. Cost: ~100 ns per call. Called ~10× per frame = 1 µs/frame.
  Within noise.
- **`self._btn_w` for thumbnail at line 1016:** `self._panel_px + (self._btn_w - thumb_w - 4) // 2`
  — `_panel_px` is a property call (always correct), `_btn_w` is an attribute (constant). ✓
- **Test `test_f005a_btn_w_stored_on_self`:** Checks `"self._btn_w" in src` of `Renderer.__init__`.
  `self._btn_w = ...` is still assigned in `__init__` (line 316). Test continues to pass. ✓
- **`_on_resize` is still called by MOUSEWHEEL handler:** With properties, it's a pure no-op.
  Leave it as `pass` rather than removing it (prevents AttributeError if future code calls it).
- **Board restart:** `self.board` attribute on Renderer is updated by the main loop after each
  restart (`self._renderer.cascade = ...` etc., but actually: looking at `main.py:_start_game`:
  `self._renderer = Renderer(eng, image_path=image_path)` — a NEW renderer is created on
  restart. `self.board` is always fresh. ✓
- **`_panel_oy` when board zoomed to max (large board):** At tile=32, 300×300 board:
  `_panel_oy = 60 + 300*32 + 12 = 9672`. Window is capped at screen height (~900px). Buttons
  and panel are off-screen. This is a display/UX issue (panel too far below for large boards at
  max zoom) but not a sync bug. Both drawing and hit-testing consistently use the same computed
  value — they agree even if both are off-screen. Correct.
- **`_btn_w` if ever `PANEL_W` needed to change:** Currently constant. If future feature
  changes `PANEL_W` dynamically, `_btn_w` should also become a property. For now: leave as
  attribute.

---

## 4. Comparative Matrix — M-002

| Criterion | Sol 1 · Complete _on_resize | Sol 2 · _layout_buttons helper | Sol 3 · Compute-on-demand | Sol 4 · ControlPanel class | Sol 5 · Properties |
|-----------|:---------------------------:|:------------------------------:|:-------------------------:|:--------------------------:|:-----------------:|
| Fixes Bug 2A (not-panel-right y) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Fixes Bug 2B (panel-right x) | ✓ | ✓ | ✓ | ✓ | ✓ |
| Fixes Bug 2C (sy double-count) | ✓ (separate) | ✓ (separate) | ✓ (inherent) | ✓ (inherent) | ✓ (inherent) |
| Single source of layout truth | No (3 sites) | Yes (_layout_buttons) | Yes (_button_rects) | Yes (ControlPanel.layout) | Yes (properties) |
| Can position become stale? | Yes (if _on_resize not called) | Yes (if _layout_buttons not called) | Never | Never (lazy) | Never (derived) |
| Preserved attribute interface | ✓ | ✓ | Needs update | Needs update | Needs update |
| Impl. complexity | Very low | Low | Medium | High | Medium |
| Test compatibility | ✓ | ✓ | Need test update | Need test update | ✓ |
| Removes _on_resize need | No | No | Yes | Yes | Yes |

### Recommendation

**Immediate fix:** Solution 1 (complete `_on_resize`) + fix `sy` formula. Minimum code change,
zero regression risk. Apply both parts together — they fix distinct bugs but share the same root.

**Long-term target:** Solution 5 (property-based dynamic rects). Eliminates the stale-state
class of bugs permanently, requires no `_on_resize` maintenance, and has no meaningful
performance cost. The refactor is bounded (35 lines, no new classes) and carries low risk.

**Only if panel grows significantly** (pagination, scrollable buttons, resizable width): upgrade
to Solution 4 (ControlPanel class). The complexity is justified only if the panel becomes a
first-class UI component with its own state, events, and lifecycle.

---

## 5. Implementation Order Recommendation

For both issues, the following phased approach balances risk and benefit:

| Phase | Action | Fixes |
|-------|--------|-------|
| **Now** | M-001: Solution 2 (np.where sparse iteration) | 99.97% of iteration waste |
| **Now** | M-002: Solution 1 (complete _on_resize + fix sy) | All 3 sub-bugs |
| **Next** | M-001: Solution 3 (dirty-tracked overlay) built on S2 | Zero per-frame iteration |
| **Later** | M-002: Solution 5 (properties) | Permanent stale-state prevention |
| **If needed** | M-001: Solution 4/5 (incremental + stencil) | O(1) per flag action |
| **If needed** | M-002: Solution 4 (ControlPanel) | Full panel abstraction |

---

*Analysis by: Claude Sonnet 4.6 via Maton Tasks · 2026-05-10*
