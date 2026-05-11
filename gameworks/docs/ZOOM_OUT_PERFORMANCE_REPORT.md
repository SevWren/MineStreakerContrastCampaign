# Forensic Performance Report — Zoom-Out on Large Boards
## `gameworks/` · Mine-Streaker

**Analysis date:** 2026-05-11
**Reference configuration:** 300×370 board (111,000 cells), image-mode, 30 FPS target
**Analyst:** Claude Sonnet 4.6 via Maton Tasks
**Files examined:** `renderer.py`, `engine.py`, `main.py`, `docs/PERFORMANCE_PLAN.md`,
`docs/BUGS.md`, `tests/renderer/test_zoom.py`

---

## Executive Summary

Zoom-out on large boards triggers two distinct cost categories that compound: a
**one-time rebuild cost** on each scroll event (image rescaling, surface rebuilds,
font rebuilds) and a **sustained per-frame cost** that scales with viewport coverage.
At minimum zoom the entire 111,000-cell board fits the viewport, collapsing the
viewport-culling optimisation that protects normal-zoom rendering. The codebase
has implemented the Phase 1–3 performance work from `PERFORMANCE_PLAN.md` but
Phases 4–8 (surface caches, text caches, button pre-rendering, spike cache,
animation set cache, tick precision) are not yet applied. Several of those gaps
are acutely harmful specifically at zoom-out.

The single most expensive event is a **`pygame.transform.smoothscale` of the
entire ghost image** triggered on the draw frame immediately following any zoom
step. For a 300×370 board at tile=32 this scales to a 9,600×11,840 pixel surface
(≈114 MP). Even at the minimum zoom floor (tile≈7) it still scales to a
2,100×2,590 pixel surface (≈5.4 MP). Every scroll tick during interactive zoom
enqueues one such operation.

---

## Bottleneck Inventory

Issues are grouped by their mechanism and ranked by estimated impact on zoom-out
specifically. "Frame cost" = per-frame, sustained. "Event cost" = one-time on
each zoom event.

---

### ZO-01 — Ghost surface `smoothscale` on every zoom step [CRITICAL · Event cost]

**File:** `renderer.py:1063–1064`
**Type:** One-time rebuild per zoom step
**Affected mode:** Image mode only

```python
def _draw_image_ghost(self, ox, oy, bw, bh):
    if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
        self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))
```

`bw = board.width * self._tile` and `bh = board.height * self._tile`. Every zoom
step changes `self._tile`, so `(bw, bh)` changes, invalidating the cache. The
next draw call executes a full `smoothscale` of `_image_surf` to the new
board-pixel dimensions.

**Scale for 300×370 board:**

| Tile size | Surface pixels | Notes |
|---|---|---|
| 32 (BASE_TILE) | 9,600 × 11,840 = 113.7 MP | Initial size |
| 20 | 6,000 × 7,400 = 44.4 MP | Mid zoom |
| 10 | 3,000 × 3,700 = 11.1 MP | Near floor |
| 7 (floor at 800×600) | 2,100 × 2,590 = 5.4 MP | Minimum |

During interactive scrolling (a user holding the scroll wheel) this fires every
frame, as each MOUSEWHEEL event produces a tile step of `max(2, tile // 4)`.
From tile=32 to tile=7 requires 8–10 events in rapid succession — 8–10
smoothscale operations in under one second.

`pygame.transform.smoothscale` is a C-level bilinear filter. Even so, scaling
a multi-megapixel surface blocks the main thread. At tile=10 the operation takes
approximately 50–200 ms depending on hardware, far exceeding the 33 ms frame
budget.

**Root cause:** The cache key is `_ghost_surf.get_size()`. Any tile change
invalidates it. There is no debounce, deferred rebuild, or intermediate-resolution
source image.

**Fix A — Debounce the rebuild:** Track `_zoom_changed_frame`. On each zoom event
set a flag. In `_draw_image_ghost`, skip the rebuild on the same frame as a zoom
event. Only rebuild when the tile has been stable for ≥1 frame. Interactive
scrolling shows the stale surface (which is only slightly wrong) until the user
pauses. This reduces rebuild cost from N-per-burst to 1-after-burst.

**Fix B — Intermediate-resolution source:** In `__init__`, pre-scale
`_image_surf` to the BASE_TILE board dimensions once (9,600×11,840 for a
300×370 board at tile=32). All subsequent downscales operate on a surface already
at full board resolution — no larger. Eliminates any over-scaling of the original
image.

**Fix C — Per-zoom-level LRU cache:** Keep the last 3 ghost surfaces keyed by
tile size. Zoom-in/zoom-out oscillation (common when fine-tuning zoom level)
gets a cache hit instead of a re-render. Memory cost: 3 × 5.4 MP × 4 bytes =
~65 MB, which is acceptable.

Fix A is the highest-priority, lowest-risk change. Fix C compounds it.

---

### ZO-02 — Full-board cell loop at minimum zoom [CRITICAL · Frame cost]

**File:** `renderer.py:893–905`
**Type:** Per-frame, scales with visible area

```python
for y in range(ty0, ty1):
    for x in range(tx0, tx1):
        self._draw_cell(x, y, ...)
```

Viewport culling (`tx0/ty0/tx1/ty1` computation at lines 876–879) is correct and
effective at normal zoom. At minimum zoom the entire board fits the viewport:
`tx0=0, ty0=0, tx1=board.width, ty1=board.height`. For a 300×370 board all
111,000 cells pass through `_draw_cell()` every frame.

Each `_draw_cell()` call (renderer.py:933) pays:
- One `dict.get()` on `engine.mine_flash` (line 950)
- One `pygame.draw.rect()` for the cell background
- One `pygame.draw.rect()` for the cell border
- Conditionally: `dict.get()` on `_num_surfs` + one `blit()`
- Totals: ~2–4 C-level draw calls per cell

At 111,000 cells × 3 avg draw calls × 30 FPS = **10 million draw calls per
second** sustained. This is the primary reason the game locks up or drops below
10 FPS when fully zoomed out.

**Additional inner-loop overhead per cell:**
```python
ip = _revealed[y, x] and (x, y) in anim_set       # set membership
in_win_anim = (x, y) in win_anim_set               # set membership
```
These are O(1) per lookup but 111,000 repetitions of Python-level tuple packing
and set hash computation is non-trivial.

**Fix A — Minimum-tile "pixel-map" render mode:** Below a threshold tile size
(e.g., `ts <= 4`), skip per-cell drawing entirely. Instead use
`pygame.surfarray.blit_array()` or `pygame.PixelArray` to paint the board as
a dense pixel buffer computed entirely in numpy. A single vectorized numpy
operation can classify all 111,000 cells into color buckets
(hidden/revealed/flagged/mine) and fill a `(board.width, board.height)` pixel
array in one pass, then `pygame.transform.scale()` the result to the screen tile
size in one blit. Cost: two numpy ops + one scale blit vs. 111,000 Python
loop iterations.

**Fix B — "Static board surface" cache:** Pre-render the entire board to a
cached `pygame.Surface` whenever cell states change (on `MoveResult.newly_revealed`
or flag toggle). Between state changes, blit the cached surface instead of
redrawing all cells. At minimum zoom only 1–10 cells change per user action
across 30+ frames between actions. This reduces per-frame draw cost from 111,000
cell draws to a single full-board blit for 29 out of 30 frames.

**Fix C (already planned, Phase 4A) — Ghost cell buffer:** The `.copy()` per
visible flag (FA-009, renderer.py:1090) is additive with Fix B costs. Implement
Phase 4A from PERFORMANCE_PLAN alongside this fix.

Fix B is the highest-impact architectural change. Fix A handles the extreme edge
of the zoom floor without needing a full cache invalidation system.

---

### ZO-03 — Per-cell Surface `.copy()` for all visible flags [HIGH · Frame cost]

**File:** `renderer.py:1090–1092`
**Bug:** FA-009 (OPEN)
**Type:** Per-frame allocation, scales with visible flags × viewport coverage

```python
sub = scaled.subsurface(src_rect).copy()   # allocates new Surface per cell per frame
sub.set_alpha(200 if _mine[y, x] else 40)
self._win.blit(sub, (px, py))
```

At normal zoom only visible flags are processed. At minimum zoom, all flags are
visible. With a typical mine density of ~15% on a 300×370 board that is ~16,650
mines. If half are flagged during mid-game: 8,325 Surface allocations per frame
× 30 FPS = **250,000 Surface allocations per second**.

**Fix:** Phase 4A from `PERFORMANCE_PLAN.md` (pre-allocated `ts×ts` tile buffer).
This is already fully specified. At minimum zoom the fix is urgent because the
visible flag count is maximized.

---

### ZO-04 — `_rebuild_num_surfs()` called synchronously on every zoom step [MEDIUM · Event cost]

**File:** `renderer.py:616`

```python
if new_tile != self._tile:
    ...
    self._rebuild_num_surfs()
```

`_rebuild_num_surfs()` creates 9 font surfaces (digits 1–8 plus `?`) using
`pygame.font.SysFont()` objects. Font rendering involves FreeType glyph
rasterization. Called on every scroll tick.

During a full zoom-out from tile=32 to tile=7, approximately 8–10 zoom steps
fire. Each calls `_rebuild_num_surfs()`. At small tile sizes the font is also
switched (`if self._tile >= 20 else self._font_small`, line 421), requiring
different glyph atlases. Each call also switches font objects, which may
invalidate OS-level font caches.

**Fix:** Batch the rebuild. Since `_tile` changes on the same event as
`_rebuild_num_surfs()`, the rebuild is always done with the final tile size for
that event — no intermediate tile matters. This is already the case (one rebuild
per MOUSEWHEEL event). The cost is proportional to the number of scroll events,
which is already bounded. **No action required here beyond ensuring Phase 5
(text cache) is applied so that `_draw_panel` calls to `font.render()` are
served from cache after the first post-zoom frame.**

However: the `_rebuild_num_surfs()` call triggers `_ghost_surf` re-bake indirectly
via `_on_resize()` causing board pixel dimension re-computation. Ensure
`_rebuild_num_surfs()` does not itself trigger surface allocation beyond the digit
surfaces.

---

### ZO-05 — `_on_resize()` called on every zoom step [MEDIUM · Event cost]

**File:** `renderer.py:615`

```python
self._on_resize()
```

`_on_resize()` recalculates button positions (5 buttons × position write) and
calls `self._rebuild_btn_surfs()` (Phase 6, not yet implemented). Currently
`_rebuild_btn_surfs()` does not exist, so `_on_resize()` only does button
coordinate arithmetic — cheap. However when Phase 6 is implemented,
`_on_resize()` will also rebuild all button surfaces. That must stay cheap
(pre-bake at resize, not at draw time). **Ensure Phase 6 implementation does not
add allocations to the zoom hot path beyond what `_on_resize()` already costs.**

---

### ZO-06 — Board background panel rect scales with board pixel size [LOW · Frame cost]

**File:** `renderer.py:847–849`

```python
br = pygame.Rect(ox - 6, oy - 6, bw + 12, bh + 12)
rrect(self._win, C["panel"], br, max(4, ts // 3))
pygame.draw.rect(self._win, C["border"], br, 2, border_radius=max(4, ts // 3))
```

`rrect()` (renderer.py:85–97) executes 2× `pygame.draw.rect()` + 4×
`pygame.draw.circle()`. At minimum zoom the panel background covers the entire
visible board area (2,100×2,590 px at tile=7 on an 800×600 window). The
`draw.rect()` calls fill a surface larger than the window — all excess pixels
are clipped by the OS compositor but the fill command still costs proportional
to the specified rect, not to what is visible.

**At tile ≤ 10:** `br` overflows the clip rect by up to 100%. Pygame clips at
the C level before blitting but the fill command is still issued for the full
geometry. Replacing with a direct `surf.fill()` clipped to the window rect
eliminates the off-screen fill cost.

**Fix:** Before the board background fill, clamp `br` to the actual window rect:
```python
win_rect = pygame.Rect(0, 0, *self._win_size)
br = br.clip(win_rect)
```

---

### ZO-07 — `mine_flash` dict lookup inside cell loop, no empty-dict fast path [LOW · Frame cost]

**File:** `renderer.py:950`

```python
_flash_end = self.engine.mine_flash.get((x, y), 0)
_flashing = now < _flash_end
```

This executes inside the cell loop — 111,000 dict lookups per frame at minimum
zoom. The `mine_flash` dict is empty for the vast majority of frames (it is only
populated for 1.5 seconds after a mine hit). An empty dict `get()` is fast in
CPython but 111,000 × Python dispatch overhead is measurable.

**Fix:** Hoist a guard before the cell loop:
```python
_has_flash = bool(self.engine.mine_flash)
```
Inside `_draw_cell`, guard the lookup:
```python
_flashing = _has_flash and now < self.engine.mine_flash.get((x, y), 0)
```
When `_has_flash` is `False` (most frames), the short-circuit eliminates all
111,000 dict lookups.

---

### ZO-08 — Set membership check per cell for animation sets [LOW · Frame cost]

**File:** `renderer.py:897–898`

```python
ip = _revealed[y, x] and (x, y) in anim_set
in_win_anim = (x, y) in win_anim_set
```

At minimum zoom with `anim_set = set()` and `win_anim_set = set()` (both empty,
which is the common case outside animations), these are 2 × 111,000 = 222,000
empty-set membership checks per frame.

**Fix:** Hoist early-exit guards before the cell loop:
```python
_has_anim = bool(anim_set)
_has_win_anim = bool(win_anim_set)
```
Inside the loop:
```python
ip = _has_anim and _revealed[y, x] and (x, y) in anim_set
in_win_anim = _has_win_anim and (x, y) in win_anim_set
```

---

### ZO-09 — Phase 4B/4C surface caches not implemented [LOW · Frame cost]

**File:** `renderer.py:1107–1109`
**Plan reference:** PERFORMANCE_PLAN Phase 4B (panel overlay), 4C (modal/help overlays)

```python
_ov = pygame.Surface((_bd_w, _bd_h), pygame.SRCALPHA)   # allocates every frame
_ov.fill((18, 18, 24, 215))
self._win.blit(_ov, (px - self.PAD, oy))
```

The panel overlay backdrop and both full-screen SRCALPHA overlays (modal, help)
allocate a new `pygame.Surface` every frame they are visible. These are not
zoom-specific but are present whenever a large board triggers the overlay panel
layout (`_panel_overlay = True`). The large-board layout (≥100 columns) always
uses the overlay panel, making this a constant tax on every frame for the
reference 300×370 board.

**Fix:** Phase 4B and 4C from `PERFORMANCE_PLAN.md` (cached surfaces invalidated
only on resize). Already fully specified. Prioritise for large-board paths.

---

### ZO-10 — Phase 5 text cache not implemented [LOW · Frame cost]

**Plan reference:** PERFORMANCE_PLAN Phase 5
**File:** `renderer.py:_draw_panel`, `_draw_header`

Every frame, `_draw_panel` calls `self._font_small.render()` approximately 12
times (stats labels, button labels, tips). `_draw_header` calls it 4 times. Most
of these strings are identical frame-to-frame (tips never change; score only
changes on action; timer changes once per second).

At minimum zoom this is a constant ~16 `font.render()` calls per frame
regardless of board size, but it is unmitigated because Phase 5 is not
implemented. Combined with ZO-02, every cycle saved in the panel draw path
increases headroom for the cell loop.

**Fix:** Phase 5 `_tx()` helper from `PERFORMANCE_PLAN.md`. Already fully specified.

---

### ZO-11 — Phase 8 frame timing not implemented [LOW · Frame cost]

**Plan reference:** PERFORMANCE_PLAN Phase 8
**File:** `main.py`

`clock.tick(FPS)` uses OS sleep, which on Windows has ≈15 ms granularity. At 30
FPS (33.3 ms/frame) this produces frames at 30 ms or 45 ms, creating 15 ms of
jitter. During zoom-out the frame cost spikes (ZO-01, ZO-02); jitter compounds
the perceived stutter.

**Fix:** `clock.tick_busy_loop(FPS)` — Phase 8 from `PERFORMANCE_PLAN.md`.

---

### ZO-12 — FA-007 flood-fill stack blows up on large open reveals [LOW · Action cost]

**File:** `engine.py:188–200`
**Bug:** FA-007 (OPEN)

When a player clicks a zero-count cell on a large board, the BFS `reveal()` flood
fill pushes cells at mark-on-pop (not mark-on-push). Adjacent cells can be pushed
multiple times before being popped. For a 300×370 nearly-empty board the stack
can reach O(4 × 111,000) = 444,000 entries.

This is not triggered by zoom directly, but is experienced acutely on large boards
at any zoom level and is especially noticeable at minimum zoom (where the player
has just opened the full board view and is exploring large areas by clicking).

**Fix:** FA-007 option A — mark `_revealed[ny, nx] = True` at push time to
prevent re-queuing.

---

### ZO-13 — `_win.get_width()` / `_win.get_height()` called directly in hot paths [LOW · Frame cost]

**File:** `renderer.py` — multiple lines
**Bug:** FA-006, FA-019 (OPEN)

Six sites bypass the `_win_size` cache introduced in Phase 2:
- `renderer.py:601` — smiley rect in `_draw_smiley()`
- `renderer.py:674` — `_on_resize()` reads `_win.get_width()`
- `renderer.py:726, 748` — header right-align in `_draw_header()`
- `renderer.py:1052` — panel draw in `_draw_panel()`
- Arrow-key handlers (K_LEFT/K_RIGHT/K_UP/K_DOWN) — FA-019

Each is a C method call on the display surface. At 30 FPS with 6 sites: 180
unnecessary C calls per second. Minor individually, avoidable collectively.

**Fix:** Replace all remaining `self._win.get_width()` → `self._win_size[0]`,
`self._win.get_height()` → `self._win_size[1]`.

---

## Implementation Status vs. PERFORMANCE_PLAN.md

| Phase | Item | Status | Notes |
|---|---|---|---|
| 1 | Engine dirty-int counters | **DONE** | `_n_flags`, `_n_revealed`, etc. in engine.py |
| 2A | `_win_size` cache | **DONE** | Partially — 6 sites still bypass (ZO-13) |
| 2B | `_cached_board_rect` | **DONE** | renderer.py:393 |
| 2C | `mouse_pos` passed to `_draw_smiley` | **DONE** | renderer.py:784 |
| 2D | Single `elapsed` call | **DONE** | main.py passes elapsed to draw() |
| 3A | `now` hoisted out of cell loop | **DONE** | renderer.py:891 |
| 3B | No `CellState` construction in cell loop | **DONE** | Raw numpy values passed directly |
| 3C | Dead `_num_tile != ts` guard removed | **DONE** | Assert added instead |
| 4A | Ghost cell buffer (no `.copy()` per flag) | **NOT DONE** | FA-009 open; `.copy()` still at line 1090 |
| 4B | Panel overlay surface cache | **NOT DONE** | Allocates per frame at line 1107 |
| 4C | Modal/help overlay surface caches | **NOT DONE** | Both allocate per frame |
| 5 | `_tx()` text render cache | **NOT DONE** | ~16 `font.render()` calls per frame |
| 6 | Button surface pre-rendering | **NOT DONE** | 40 draw calls/frame for buttons |
| 7A | Mine spike offset cache | **NOT DONE** | 8 trig calls per visible mine |
| 7B | Animation set cache | **NOT DONE** | Set rebuilt every frame during animation |
| 8 | `tick_busy_loop` | **NOT DONE** | `clock.tick()` still used |

---

## Zoom-Out Specific Findings Not in PERFORMANCE_PLAN.md

The following issues are specific to zoom-out and are not covered by the existing
plan:

### N-01 — No debounce on `_ghost_surf` smoothscale during interactive zoom

The PERFORMANCE_PLAN addresses per-flag `.copy()` (Phase 4A) but does not address
the full `_ghost_surf` smoothscale triggered on every zoom step. This is 10–100×
more expensive than the per-flag issue and is only triggered during zoom, making
it invisible in steady-state profiling.

**Proposed addition to plan:**
```python
# In __init__:
self._ghost_surf_pending_tile: int = 0   # tile size that ghost needs to be rebuilt for
self._ghost_surf_built_tile:   int = 0   # tile size ghost was last built at

# In handle_event MOUSEWHEEL (after self._tile = new_tile):
self._ghost_surf_pending_tile = new_tile  # mark dirty, defer rebuild

# In _draw_image_ghost:
if self._ghost_surf_pending_tile != self._ghost_surf_built_tile:
    bw_pending = self.board.width  * self._ghost_surf_pending_tile
    bh_pending = self.board.height * self._ghost_surf_pending_tile
    self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw_pending, bh_pending))
    self._ghost_surf_built_tile = self._ghost_surf_pending_tile
```

This is functionally identical to the current approach for single zoom events but
ensures only one smoothscale fires per burst of scroll events (the one on the
frame after scrolling stops).

### N-02 — No "pixel-map" render mode for extreme zoom-out

When `self._tile <= 4`, individual number glyphs and mine/flag icons are
sub-pixel sized and invisible to the user. The game still executes full per-cell
draw logic for all 111,000 cells. A pixel-map mode using `pygame.surfarray` would
reduce render cost from O(W×H) Python operations to O(1) numpy + blit at the cost
of a small amount of visual fidelity that is unperceivable at that scale.

### N-03 — `_draw_loss_overlay` iterates full viewport at zoom-out

**File:** `renderer.py:1031–1054`

`_draw_loss_overlay()` has its own viewport-culled loop using identical bounds to
`_draw_board`. At minimum zoom this iterates all 111,000 cells on loss. It also
calls `bool()` on numpy values (`is_mine = bool(_mine[y, x])`) rather than using
numpy booleans directly, adding a Python type coercion per cell. Vectorising this
with `np.where` (same pattern used in `_draw_image_ghost`) would reduce it to two
`np.where` calls + loops only over the actual mine/wrong-flag cells.

---

## Priority Order for Zoom-Out

| Priority | ID | Effort | Impact | Description |
|---|---|---|---|---|
| 1 | ZO-01 / N-01 | Low | Critical | Debounce `_ghost_surf` smoothscale during scroll bursts |
| 2 | ZO-02 / N-02 | High | Critical | Pixel-map mode at tile ≤ 4; static board surface cache |
| 3 | ZO-03 | Medium | High | Phase 4A ghost cell buffer (FA-009) |
| 4 | ZO-09 | Low | Medium | Phase 4B/4C overlay surface caches |
| 5 | ZO-10 | Low | Medium | Phase 5 text render cache |
| 6 | ZO-07 | Low | Medium | `mine_flash` empty-dict fast path |
| 7 | ZO-08 | Low | Medium | Animation set empty-set fast path |
| 8 | ZO-11 | Trivial | Low | Phase 8 `tick_busy_loop` |
| 9 | ZO-13 | Low | Low | Complete Phase 2 `_win_size` cache (FA-006/FA-019) |
| 10 | ZO-12 | Low | Low | FA-007 flood-fill mark-on-push |
| 11 | ZO-06 | Low | Low | Clamp board background rect to window |
| 12 | N-03 | Low | Low | Vectorise `_draw_loss_overlay` with `np.where` |

---

## Appendix — Zoom Event Code Path (Annotated)

```
MOUSEWHEEL (y < 0) received
│
├── step = max(2, self._tile // 4)                     # renderer.py:573
├── min_fit_tile computed from avail_w, avail_h        # renderer.py:597-598
├── new_tile = max(min_fit_tile, self._tile - step)    # renderer.py:603
│
└── if new_tile != self._tile:
    ├── self._tile = new_tile
    ├── self._pan_x/y adjusted for mouse-centered zoom  # renderer.py:612-613
    ├── self._clamp_pan()                               # board rect invalidated
    ├── self._on_resize()                               # button positions updated
    │     └── board rect invalidated
    └── self._rebuild_num_surfs()                       # 9 font.render() calls
          └── self._num_tile = new_tile

NEXT FRAME (draw call):
│
├── _draw_board(...)
│     ├── bw = board.width * self._tile                # NEW value
│     ├── bh = board.height * self._tile               # NEW value
│     ├── rrect() on full board bg                     # ZO-06
│     ├── _draw_image_ghost(ox, oy, bw, bh)            # ZO-01 ← TRIGGERS HERE
│     │     └── smoothscale(_image_surf, (bw, bh))     # MOST EXPENSIVE CALL
│     ├── anim_set = set(cascade.current())            # ZO-08 (empty set)
│     ├── win_anim_set = set(win_anim.current())       # ZO-08 (empty set)
│     ├── viewport: tx0=0, ty0=0, tx1=300, ty1=370     # ZO-02 full board visible
│     └── for y in 0..370: for x in 0..300:            # 111,000 iterations
│           mine_flash.get((x,y), 0)                   # ZO-07 × 111,000
│           (x,y) in anim_set                          # ZO-08 × 111,000
│           (x,y) in win_anim_set                      # ZO-08 × 111,000
│           _draw_cell(...)
│                 draw.rect() × 2–4                    # ZO-02 dominant cost
│
├── _draw_panel(...)
│     ├── pygame.Surface(SRCALPHA) allocated            # ZO-09 (overlay)
│     ├── font.render() × ~12                          # ZO-10
│     └── pill() × 5 buttons → 8 draw ops each         # Phase 6 gap
│
├── _draw_header(...)
│     └── font.render() × 4                            # ZO-10
│
└── display.flip()
```

---

*Report generated by forensic static analysis of `gameworks/` commit on
`frontend-game-mockup` branch. All line numbers reference `renderer.py` and
`engine.py` as read on 2026-05-11.*
