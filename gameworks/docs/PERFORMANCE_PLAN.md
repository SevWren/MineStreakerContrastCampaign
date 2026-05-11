# Performance Remediation Plan — P-01 through P-25
## Mine-Streaker `gameworks/` — Industry-Standard Approach

Forensic analysis date: 2026-05-10
Board reference: 300×370 (111,000 cells) at 30 FPS target.

---

## Design Principles Applied

1. **Compute once, reuse until invalid** — every value computed per-frame must have a defined invalidation trigger
2. **Push allocations to init/resize, never to the draw path**
3. **No Python-level per-cell loops for anything that can be moved outside**
4. **Dirty flags and counters instead of array scans**
5. **Each phase is independently testable and independently commit-able**

---

## Phase 1 — Engine Dirty-Int Counters
**Status: IMPLEMENTED**
**Fixes: P-06, P-07, P-08, P-23**
**File: `gameworks/engine.py`**
**Tests: `gameworks/tests/unit/test_board.py`**

### Problem

Four `Board` properties scan full numpy arrays (111,000 elements for a 300x370 board) every
frame:
- `revealed_count`      -> `self._revealed.sum()`
- `safe_revealed_count` -> `np.sum(self._revealed & ~self._mine)` (creates temp array)
- `flags_placed`        -> `self._flagged.sum()`
- `questioned_count`    -> `self._questioned.sum()`

`safe_revealed_count` is called from `_draw_panel` every frame.
`flags_placed` is called via `mines_remaining` every frame in `_draw_header`.
Together: 3+ full-array scans x 30 FPS = millions of element ops/second that never
change between user actions.

### Solution

Add 4 int counters to `Board.__init__`, incremented/decremented atomically in
`toggle_flag()` and `reveal()`. Properties return the counter.

#### `Board.__init__` — add after existing array init

```python
# Dirty-int counters — updated atomically on every state mutation.
# Eliminates full numpy array scans from the per-frame draw path.
self._n_flags: int = 0
self._n_questioned: int = 0
self._n_safe_revealed: int = 0   # revealed non-mine cells only
self._n_revealed: int = 0        # total revealed (includes mine-hit cells)
```

#### `Board.reveal()` — increment counters at both write sites

**Pre-condition:** These increments assume `reveal()` returns `(False, [])` early
when `_revealed[y, x]` is already True (i.e., re-revealing an already-revealed cell
is a no-op). Verify this guard exists before implementing — if it is absent, a
second click on a revealed cell would double-increment the counters and corrupt all
derived values. Search for the guard at the top of `reveal()`:

```python
if self._revealed[y, x]:
    return False, []
```

If not present, add it before adding the counter increments.

```python
# Mine-hit path (line ~177): after self._revealed[y, x] = True
self._n_revealed += 1

# BFS path (line ~188): after self._revealed[cy, cx] = True
self._n_revealed += 1
self._n_safe_revealed += 1
```

Win condition (line ~195) — replace array scan with counter:

```python
# Before:
if self.revealed_count == self.total_safe:
# After:
if self._n_safe_revealed == self.total_safe:
```

#### `Board.toggle_flag()` — increment/decrement at each transition

```python
# flag -> question transition (line ~208):
self._n_flags -= 1
self._n_questioned += 1

# question -> hidden transition (line ~213):
self._n_questioned -= 1

# hidden -> flag transition (line ~219):
self._n_flags += 1
```

#### Replace all 4 properties

```python
@property
def revealed_count(self) -> int:
    return self._n_revealed

@property
def safe_revealed_count(self) -> int:
    return self._n_safe_revealed

@property
def flags_placed(self) -> int:
    return self._n_flags

@property
def questioned_count(self) -> int:
    return self._n_questioned
```

#### `dev_solve_board()` — resync counters after bulk numpy ops

After `board._revealed[~board._mine] = True` etc.:

```python
board._n_safe_revealed = board.total_safe
board._n_revealed      = int(board._revealed.sum())  # recount from array — mine-hit cells may also be revealed
board._n_flags         = board.total_mines
board._n_questioned    = 0
```

Why `_revealed.sum()` and not `total_safe`: the game continues after mine hits
(no game-over). The user may have clicked mine cells before invoking dev_solve,
leaving those cells revealed (`_revealed[y, x] = True`) but not safe. Setting
`_n_revealed = total_safe` would undercount by the number of previously hit mines.
Using `_revealed.sum()` is safe here — dev_solve is already in a bulk-numpy context;
the single O(n) recount is a one-time cost on user action, not per-frame.

### Tests — `gameworks/tests/unit/test_board.py`
*(Phase 1 is IMPLEMENTED; these tests should exist. If any are missing, add them.)*

```
test_flags_placed_counter_increments_on_flag
test_flags_placed_counter_decrements_on_question
test_flags_placed_counter_decrements_on_hidden
test_safe_revealed_count_increments_per_safe_cell
test_questioned_count_increments_and_decrements
test_counters_match_array_state_after_flood_fill   <- validates counter == np.sum
test_dev_solve_resyncs_all_counters
```

The `test_counters_match_array_state_after_flood_fill` test is the regression guard:
after any sequence of actions, assert `board._n_flags == int(board._flagged.sum())` etc.
This catches any future mutation that forgets to update the counter.

---

## Phase 2 — Frame-Local Value Hoisting
**Status: IMPLEMENTED** *(partially — 5 sites remain; tracked in FA-006)*
**Fixes: P-15, P-17, P-18, P-21**
**Files: `gameworks/renderer.py`, `gameworks/main.py`**
**Tests: `gameworks/tests/renderer/test_renderer_init.py`**

### 2A — Cache `_win.get_size()` (P-21)

`get_size()` appears at 9 locations in renderer.py. It is a C method call but still
unnecessary when called repeatedly within one frame.

`__init__` — add after `set_mode`:

```python
self._win_size: Tuple[int, int] = self._win.get_size()
```

`handle_event` VIDEORESIZE handler — update cache:

```python
self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
self._win_size = ev.size   # <- add this line
```

All call sites — replace `self._win.get_size()` with `self._win_size`:
- `_center_board()` — reads `get_size()` to compute centering origin
- MOUSEMOTION handler — reads `get_size()` to compute pan clamp bounds
- `_clamp_pan()` — reads `get_size()` to clamp `_pan_x` / `_pan_y`
- `_draw_overlay()` — reads `get_size()` for full-window surface sizing
- `_draw_board()` — reads `get_size()` for visible-tile viewport culling
- `_draw_loss_overlay()` — reads `get_size()` for full-window surface sizing
- `_draw_image_ghost()` — reads `get_size()` for board-pixel blit region
- `_draw_modal()` — reads `get_size()` for modal overlay sizing
- `_draw_help()` — reads `get_size()` for help overlay sizing

**Note:** Line numbers in renderer.py are not pinned here because the file changes
with each phase commit. Search by method name, not line number, when implementing.

### 2B — Cache `_board_rect()` (P-17)

The board rect only changes when `_pan_x`, `_pan_y`, or `_tile` changes.
Add a cache invalidated whenever those values change.

`__init__` — add:

```python
self._cached_board_rect: Optional[pygame.Rect] = None
```

`_board_rect()` method — return cached:

```python
def _board_rect(self) -> pygame.Rect:
    if self._cached_board_rect is None:
        bw = self.board.width * self._tile
        bh = self.board.height * self._tile
        self._cached_board_rect = pygame.Rect(
            self.BOARD_OX + self._pan_x,
            self.BOARD_OY + self._pan_y,
            bw, bh)
    return self._cached_board_rect
```

Invalidation — add `self._cached_board_rect = None` after every mutation of
`_pan_x`, `_pan_y`, `_tile`:
- MOUSEMOTION handler (after clamping)
- MOUSEWHEEL handler (after zoom)
- `_clamp_pan()` (end of method)
- `_on_resize()` (end of method)
- `_center_board()` (end of method)

### 2C — Eliminate redundant `get_pos()` in `_draw_smiley` (P-15)

`_draw_smiley` — calls `pygame.mouse.get_pos()` ignoring the
`mouse_pos` already passed to `draw()`.

`_draw_smiley` signature change:

```python
def _draw_smiley(self, x, y, w, h, state, mouse_pos):
```

`_draw_header` signature change:

```python
def _draw_header(self, elapsed, game_state, mouse_pos):
```

`_draw_smiley` body — replace the `pygame.mouse.get_pos()` call with `mouse_pos`.
Search for the single `get_pos()` call inside `_draw_smiley`; it is the only one
in that method.

`draw()` call site — pass `mouse_pos` through:

```python
self._draw_header(elapsed, game_state, mouse_pos)
```

For the `MOUSEWHEEL` handler's `get_pos()` call (inside `handle_event`, in the
`ev.type == pygame.MOUSEBUTTONDOWN` / `MOUSEWHEEL` branch), store
`self._last_mouse_pos` and update at the top of each `draw()` call:

```python
# In __init__:
self._last_mouse_pos: Tuple[int, int] = (0, 0)

# In draw() first line:
self._last_mouse_pos = mouse_pos

# In handle_event() MOUSEWHEEL branch:
mx, my = self._last_mouse_pos   # was: pygame.mouse.get_pos()
```

### 2D — Single `elapsed` call per loop iteration (P-18)

`GameLoop.run()` already caches `elapsed` at the top of each loop iteration and
passes it to `draw()`. Verify no code path inside renderer calls `engine.elapsed`
directly (which would re-invoke `time.time()`). Add an architecture test to enforce
this.

### Tests — `gameworks/tests/renderer/test_renderer_init.py`
*(Phase 2 is IMPLEMENTED; these tests should exist. If any are missing, add them.)*

```
test_win_size_cache_updated_on_videoresize
test_board_rect_cache_invalidated_on_pan_change
test_board_rect_cache_invalidated_on_zoom_change
test_draw_smiley_uses_passed_mouse_pos          <- monkeypatch get_pos, verify not called
test_renderer_does_not_call_engine_elapsed      <- inspect renderer source, assert 'engine.elapsed' absent
```

---

## Phase 3 — Cell Loop Refactor
**Status: IMPLEMENTED**
**Fixes: P-01, P-02, P-03, P-20**
**File: `gameworks/renderer.py`**
**Tests: `gameworks/tests/renderer/test_surface_cache.py`, new `test_cell_draw.py`**

This is the highest-impact single change for per-frame CPU. Every visible cell
currently pays for: a `CellState` dataclass construction, 5 numpy->Python type
coercions, and a `time.monotonic()` system call.

### 3A — Hoist `time.monotonic()` out of the cell loop (P-01)

In `_draw_board`, immediately before the outer `for y in range(ty0, ty1):` loop
(the viewport-culled cell iteration loop, not the board-rect setup above it):

```python
now = time.monotonic()   # hoist here, pass to _draw_cell
```

### 3B — Eliminate `CellState` construction and bool() coercions (P-02, P-03)

New `_draw_cell` signature — accepts raw primitive values:

```python
def _draw_cell(self,
               x: int, y: int,
               is_mine,          # numpy bool_ — no bool() needed
               is_revealed,      # numpy bool_
               is_flagged,       # numpy bool_
               is_questioned,    # numpy bool_
               neighbour_mines,  # numpy uint8
               pos: Tuple[int, int],
               in_anim: bool,
               is_pressed: bool,
               fog: bool,
               ts: int,
               in_win_anim: bool,
               now: float):      # hoisted monotonic time
```

In the cell loop body — remove `CellState(...)` construction entirely:

```python
for y in range(ty0, ty1):
    for x in range(tx0, tx1):
        px = ox + x * ts
        py = oy + y * ts
        ip = _revealed[y, x] and (x, y) in anim_set
        in_win_anim = (x, y) in win_anim_set
        self._draw_cell(
            x, y,
            _mine[y, x], _revealed[y, x], _flagged[y, x],
            _questioned[y, x], _neighbours[y, x],
            (px, py), ip, pressed == (x, y),
            self.fog, ts, in_win_anim, now
        )
```

Inside `_draw_cell` — remove time call, use passed `now`:

```python
# DELETE: _flash_end = self.engine.mine_flash.get((x, y), 0)
# DELETE: _flashing = time.monotonic() < _flash_end
# REPLACE with:
_flashing = now < self.engine.mine_flash.get((x, y), 0)
```

Also remove:

```python
# DELETE: if ts is None: ts = self._tile    (ts always passed)
# DELETE: pad = max(1, ts // 16)            (verify unused then remove)
```

Dict key cast — `neighbour_mines` is a numpy `uint8`. The `_num_surfs` dict was
built with Python `int` keys via `range()`. A numpy `uint8` key does not match a
Python `int` key in a dict lookup, so the lookup silently returns `None`:

```python
# BEFORE (silent None return — numpy uint8 never matches Python int key):
num_surf = self._num_surfs.get(neighbour_mines)

# AFTER:
num_surf = self._num_surfs.get(int(neighbour_mines))
```

**Note:** The `(x, y) in anim_set` and `(x, y) in win_anim_set` lookups in the
cell loop above are an intermediate state. Phase 10 supersedes them with numpy
bool array indexing (`anim_arr[y, x]`, `win_arr[y, x]`), eliminating the per-cell
tuple allocations entirely. Implement Phase 3 as written here; Phase 10 will
replace those two lines.

### 3C — Remove dead `_num_tile != ts` guard (P-20)

Search inside both `_draw_board` and `_draw_cell` — there is a guard that checks
`self._num_tile != ts` and calls `self._rebuild_num_surfs()` if true.
Delete it from whichever method it appears in (it will be in one or the other,
not both). This check can never be true mid-frame (surfs are rebuilt immediately
after zoom before any draw call):

```python
# DELETE these two lines:
if self._num_tile != ts:
    self._rebuild_num_surfs()
```

Add a guard assertion in `_draw_cell()` instead, at the top of the method, so it
fails loudly during development if the invariant is ever broken:

```python
assert self._num_tile == ts, (
    f"_draw_cell: tile size mismatch — _num_tile={self._num_tile} != ts={ts}. "
    "Call _rebuild_num_surfs() before drawing."
)
```

### Tests — `gameworks/tests/renderer/test_cell_draw.py`
*(Phase 3 is IMPLEMENTED; these tests should exist. If any are missing, add them.)*

```
test_draw_completes_without_cellstate_construction   <- monkeypatch CellState
test_draw_does_not_call_monotonic_in_cell_loop       <- monkeypatch, count calls == 1
test_draw_cell_flashing_uses_passed_now
test_draw_board_correct_cell_count_drawn             <- verify viewport culling
```

---

## Phase 4 — Surface Allocation Caches
**Status: PENDING**
**Fixes: P-04, P-05, P-09, P-10**
**File: `gameworks/renderer.py`**
**Tests: `gameworks/tests/renderer/test_surface_cache.py`**

All four issues share the same root cause: SRCALPHA surface construction or `.copy()`
on the per-frame hot path. The fix in every case is the established `_fog_surf`
pattern already in the codebase.

### 4A — Image ghost per-cell copy elimination (P-04, P-05)

Problem: `subsurface().copy()` + `set_alpha()` per flagged cell per frame allocates
a new Surface for each one.

#### Memory constraint — why full-board alpha copies are NOT used

The natural first instinct is to pre-bake two full-board alpha variants of `_ghost_surf`.
**Do not do this.** `_ghost_surf` is scaled to `board.width * tile × board.height * tile`.
For the reference board (300×370 at 32px tiles):

```
9600 × 11840 pixels × 4 bytes RGBA32 = ~431 MB per surface
```

Two copies plus the original = **~1.3 GB** of surface memory. This will OOM most
consumer machines. The fix must operate at tile granularity, not board granularity.

#### Fix (P-04 — ghost cells with alpha): reusable tile-sized buffer

Pre-allocate a single `ts×ts` SRCALPHA surface once per tile size. Per cell: blit the
ghost tile into the buffer, set_alpha, blit buffer to window. Same number of blit
operations as before, zero allocations per cell.

Memory cost: one surface at `ts×ts` = 32×32×4 = **4 KB** at the default tile size.

`__init__` — add after existing `_ghost_surf`:

```python
self._ghost_cell_buf: Optional[pygame.Surface] = None  # ts×ts reuse buffer; no alloc per cell
self._ghost_cell_buf_ts: int = 0
```

`_draw_image_ghost` — rebuild buffer only when tile size changes:

```python
ts = self._tile
if self._ghost_cell_buf is None or self._ghost_cell_buf_ts != ts:
    self._ghost_cell_buf = pygame.Surface((ts, ts), pygame.SRCALPHA)
    self._ghost_cell_buf_ts = ts
```

Per-cell loop — replace `.copy().set_alpha()` with buffer reuse:

```python
for y, x in zip(ys, xs):
    px = ox + int(x) * ts
    py = oy + int(y) * ts
    src_rect = pygame.Rect(int(x) * ts, int(y) * ts, ts, ts)
    # Clear before blit — REQUIRED for images with any transparent pixels.
    # SRCALPHA blit composites src OVER dest; alpha < 255 source pixels do NOT
    # fully overwrite the previous cell's content. Omitting fill() produces
    # ghost-on-ghost artifacts along anti-aliased edges.
    self._ghost_cell_buf.fill((0, 0, 0, 0))
    self._ghost_cell_buf.blit(self._ghost_surf, (0, 0), src_rect)
    self._ghost_cell_buf.set_alpha(200 if _mine[y, x] else 40)
    self._win.blit(self._ghost_cell_buf, (px, py))
```

Why `set_alpha()` works here: `_ghost_cell_buf` is SRCALPHA. `set_alpha()` applies a
per-surface alpha multiplier on top of per-pixel alpha. The ghost surf tiles have
per-pixel alpha 255 after the `fill()` + `blit()`, so the multiplier directly controls
the final opacity.

Why `fill((0,0,0,0))` does not undo the blit: `fill()` runs before `blit()`. The
sequence is: clear → copy tile content in → set global alpha → blit to window.

#### Fix (P-05 — win animation cells): direct subsurface blit

Win animation uses alpha=255 (full opacity). A `subsurface()` is directly blittable —
the `.copy()` was only ever needed to detach the surface before calling `set_alpha()`.
At full opacity no alpha call is needed, so the copy is eliminated entirely.

`_draw_win_animation_fx` — replace `.copy()`:

```python
for (x, y) in win_anim_set:
    px = ox + x * ts
    py = oy + y * ts
    src_rect = pygame.Rect(x * ts, y * ts, ts, ts)
    self._win.blit(self._ghost_surf.subsurface(src_rect), (px, py))  # no .copy()
```

### 4B — Panel overlay backdrop (P-09)

Pattern: identical to `_fog_surf`.

`__init__` — add:

```python
self._panel_overlay_surf: Optional[pygame.Surface] = None
self._panel_overlay_surf_size: Tuple[int, int] = (0, 0)
```

`_draw_panel` — replace per-frame allocation:

```python
# BEFORE (allocates every frame):
_ov = pygame.Surface((_bd_w, _bd_h), pygame.SRCALPHA)
_ov.fill((18, 18, 24, 215))
self._win.blit(_ov, (px - self.PAD, oy))

# AFTER (cached):
sz = (_bd_w, _bd_h)
if self._panel_overlay_surf is None or self._panel_overlay_surf_size != sz:
    self._panel_overlay_surf = pygame.Surface(sz, pygame.SRCALPHA)
    self._panel_overlay_surf.fill((18, 18, 24, 215))
    self._panel_overlay_surf_size = sz
self._win.blit(self._panel_overlay_surf, (px - self.PAD, oy))
```

Invalidation triggers — the overlay size `(_bd_w, _bd_h)` depends on **window size
only**, not on tile size:

- `_bd_w = PANEL_W + PAD*2` — both `PANEL_W` and `PAD` are module-level constants;
  tile size has no effect on panel width.
- `_bd_h = win_h - BOARD_OY` — `win_h` is the window height; `BOARD_OY` is a
  constant header offset. Tile size has no effect on panel height.

Therefore: **one invalidation site only:**
- Window resize: add `self._panel_overlay_surf = None` in the VIDEORESIZE handler.

**Do NOT add zoom invalidation** (`_rebuild_num_surfs()` call site). Adding it would
force a Surface realloc on every zoom notch for an overlay whose size has not changed —
the opposite of the intent. This is a common mistake because the board pixel rect does
change on zoom, but the *panel* overlay occupies a fixed column next to the board, not
the board itself.

Note: `_modal_overlay_surf` and `_help_overlay_surf` (Phase 4C) are also window-size
only — consistent with the same analysis. Resize-only invalidation is correct for all
three panel/modal/help overlays.

### 4C — Modal and help full-screen overlays (P-10)

`__init__` — add:

```python
self._modal_overlay_surf: Optional[pygame.Surface] = None
self._modal_overlay_surf_size: Tuple[int, int] = (0, 0)
self._help_overlay_surf: Optional[pygame.Surface] = None
self._help_overlay_surf_size: Tuple[int, int] = (0, 0)
```

`_draw_modal` — replace the block that allocates a full-window SRCALPHA Surface and
fills it at the top of the method body (the `pygame.Surface(..., pygame.SRCALPHA)`
/ `.fill((0, 0, 0, 160))` / `.blit(...)` sequence):

```python
sz = self._win_size
if self._modal_overlay_surf is None or self._modal_overlay_surf_size != sz:
    self._modal_overlay_surf = pygame.Surface(sz, pygame.SRCALPHA)
    self._modal_overlay_surf.fill((0, 0, 0, 160))
    self._modal_overlay_surf_size = sz
self._win.blit(self._modal_overlay_surf, (0, 0))
```

Same pattern for `_draw_help` with `(0, 0, 0, 200)`.

Invalidation trigger: window resize -> set both to `None` in VIDEORESIZE handler.

### Tests to add in `gameworks/tests/renderer/test_surface_cache.py`

```
test_ghost_cell_buf_allocated_once_per_tile_size
test_ghost_cell_buf_not_reallocated_across_frames   <- assert id() stable across 2 draw calls
test_ghost_cell_buf_rebuilt_on_zoom_change
test_win_anim_fx_blit_no_copy                       <- monkeypatch Surface.copy, assert 0 calls
test_panel_overlay_surf_stable_across_frames
test_panel_overlay_surf_rebuilt_on_resize
test_modal_overlay_surf_stable_across_frames
test_modal_overlay_surf_rebuilt_on_resize
test_help_overlay_surf_stable_across_frames
test_help_overlay_surf_rebuilt_on_resize
```

The first three tests use `id()` comparison on `_ghost_cell_buf` to verify the same
surface object is reused across frames and rebuilt on zoom, matching the pattern of
the existing `test_fog_surf_stable_across_frames`.

---

## Phase 5 — Text/Font Surface Cache
**Status: PENDING**
**Fixes: P-11, P-12, P-22**
**File: `gameworks/renderer.py`**
**Tests: `gameworks/tests/renderer/test_surface_cache.py`**

### Design

`font.render()` is one of the most expensive Pygame operations. The renderer calls it
~20 times per frame for panel stats, tips, button labels, and header values. Most of
these strings never change between frames — score only changes on action, timer changes
every second, tips never change.

The solution is a string-keyed render cache: a dict mapping
`(text, font_id, color) -> Surface`. On a cache hit the surface is returned instantly
(O(1) dict lookup). On a miss the surface is rendered and stored. The cache is
self-managing: stale entries accumulate but are bounded — score is max 7 digits, timer
is max 4 digits, so the cache stays small.

### `__init__` — add:

```python
self._text_cache: dict = {}   # (text, font_id, color) -> pygame.Surface
```

### New helper method:

```python
def _tx(self, text: str, font: pygame.font.Font, color: tuple) -> pygame.Surface:
    """Cached font.render(). Re-renders only when text or style changes."""
    key = (text, id(font), color)
    s = self._text_cache.get(key)
    if s is None:
        s = font.render(text, True, color)
        self._text_cache[key] = s
    return s
```

**`color` must always be a plain Python tuple** — e.g. `(255, 255, 255)` or
`(r, g, b, a)`. Do not pass `pygame.Color` objects. A `pygame.Color(255, 255, 255)`
and a tuple `(255, 255, 255)` produce different hash values and will never share a
cache entry, causing every call with a Color object to be a miss and a re-render.
All `C["..."]` palette values used in the renderer must be defined as tuples in the
colour constants dict, not as `pygame.Color` instances.

Cache invalidation on font rebuild — in `_rebuild_num_surfs()`, add:

```python
self._text_cache.clear()
```

Font objects are recreated when tile-based font sizes change. Clearing ensures no
stale `id(font)` references remain.

### Apply `_tx()` everywhere `font.render()` is called in the draw path

`_draw_header` (P-12) — replace all 4 `font.render()` calls inside the method body.
Search for `font.render(` inside `_draw_header`; there are exactly 4 calls covering
the mine count, score, elapsed time, and streak/multiplier strings:

```python
mt = self._tx(f"M:{mines:>03d}", self._font_big, mcol)
sc = self._tx(f"SCORE:{score:>6d}", self._font_small, score_col)
tt = self._tx(f"T:{secs:>03d}", self._font_small, C["text_light"])
sl = self._tx(f"STREAK x{streak}  {mult:.1f}x", self._font_small, streak_col)
```

**Note:** Line numbers are intentionally omitted — the method will shift with each
prior-phase commit. Search by method name and string content.

`_draw_panel` (P-11) — replace all `font.render()` calls in the method body.
Search for every `font.render(` inside `_draw_panel` and apply `_tx()`.
Affected strings include: safe count, mine count, score, label strings, and
stat line values. Do not use line numbers — the method spans a large block and
will shift with each phase commit; search by method scope instead.

**Note:** Line numbers are intentionally omitted here. Use
`grep -n "font.render" gameworks/renderer.py` to locate all remaining
call sites at implementation time.

### Tips pre-render (P-22)

Tips are 7 literal strings that never change. Pre-render at init for zero per-frame
cost.

`__init__` — add after font init:

```python
self._tip_surfs: list = []
self._rebuild_tip_surfs()
```

New method:

```python
def _rebuild_tip_surfs(self):
    tips = [
        "L-click  Reveal", "R-click  Flag / unflag",
        "M-click  Chord",  "Scroll   Zoom / Pan", "",
        "Keys: R Restart  H Help", "      F Fog  ESC Quit",
    ]
    self._tip_surfs = [
        self._font_tiny.render(t, True, C["text_dim"]) if t else None
        for t in tips
    ]
```

**Why `font.render()` directly and not `_tx()` here:** `_rebuild_tip_surfs()` is
called only at init and on zoom (inside `_rebuild_num_surfs()`), never per-frame.
The rendered surfaces are stored in `_tip_surfs` and blitted directly in the draw
loop — the per-frame path already avoids `font.render()`. Using `_tx()` here would
add an unnecessary dict write to `_text_cache` for strings that will never be
requested through the cache path. Do not change this call to `_tx()`.

Call `_rebuild_tip_surfs()` inside `_rebuild_num_surfs()` so tips are refreshed
when fonts change on zoom.

`_draw_panel` tip loop — replace:

```python
line_h = self._font_tiny.get_height() + 2
for i, surf in enumerate(self._tip_surfs):
    if surf:
        self._win.blit(surf, (px, ty + i * line_h))
```

### Tests to add

```
test_tx_returns_same_object_for_identical_inputs
test_tx_re_renders_on_string_change
test_text_cache_cleared_on_rebuild_num_surfs
test_tip_surfs_populated_at_init
test_tip_surfs_rebuilt_on_zoom
test_header_font_render_not_called_on_stable_frame   <- monkeypatch font.render, count calls
```

---

## Phase 6 — Button Surface Pre-Rendering
**Status: PENDING**
**Fixes: P-13**
**File: `gameworks/renderer.py`**
**Tests: `gameworks/tests/renderer/test_surface_cache.py`**

### Problem

Every frame: for each of 5 buttons, `pill()` -> `rrect()` -> 3x `draw.rect` +
4x `draw.circle` + `font.render()` = 8 calls x 5 buttons = 40 draw operations per
frame for buttons that look identical frame after frame.

### Design

Pre-render each button at two states (normal + hover) to a `pygame.Surface` at init
and on resize. Per-frame draw becomes a single `blit()` per button.

`__init__` — add:

```python
self._btn_surfs: dict = {}   # (label, hover: bool) -> pygame.Surface
self._rebuild_btn_surfs()
```

New method:

```python
def _rebuild_btn_surfs(self):
    """Pre-render all button faces. Called at init and on resize/zoom."""
    self._btn_surfs.clear()
    spec = [
        ("Restart",         C["green"]),
        ("New Game",        C["green"]),
        ("Help",            C["blue"]),
        ("Toggle Fog",      C["purple"]),
        ("Hide Fog",        C["purple"]),
        ("Save .npy",       C["cyan"]),
        ("Solve Board",     C["orange"]),
        ("Solve Board",     C["border"]),   # inactive variant uses border colour
    ]
    bw = self._btn_w
    bh = self._btn_new.height
    for label, base_col in spec:
        for hover in (False, True):
            s = pygame.Surface((bw, bh), pygame.SRCALPHA)
            r = bh // 2
            pygame.draw.rect(s, base_col, (0, 0, bw, bh), border_radius=r)
            if hover:
                pygame.draw.rect(s, C["text_light"], (0, 0, bw, bh), 2, border_radius=r)
            txt = self._font_small.render(label, True, C["bg"])
            s.blit(txt, txt.get_rect(center=(bw // 2, bh // 2)))
            self._btn_surfs[(label, base_col, hover)] = s
```

**Why `font.render()` directly and not `_tx()` here:** `_rebuild_btn_surfs()` is
called only at init and on resize/zoom (inside `_rebuild_num_surfs()` and
`_on_resize()`), never per-frame. The rendered surfaces are stored in `_btn_surfs`
and blitted directly in the draw loop — the per-frame path already avoids
`font.render()`. Using `_tx()` here would add unnecessary dict writes to
`_text_cache` for label strings that will never be requested through the cache
path. Do not change these calls to `_tx()`.

`_draw_panel` button loop — `base_col` must be carried alongside each button.
Change the buttons list from 2-tuples to 3-tuples so `base_col` is in scope:

```python
# buttons list construction (in _draw_panel) — add base_col as third element:
buttons = [
    (self._btn_new,       "New Game",    C["green"]),
    (self._btn_restart,   "Restart",     C["green"]),
    (self._btn_help,      "Help",        C["blue"]),
    (self._btn_fog,       fog_label,     C["purple"]),
    (self._btn_save,      "Save .npy",   C["cyan"]),
    (self._btn_dev_solve, "Solve Board", C["orange"] if solver_available else C["border"]),
]

# Draw loop — unpack all three:
for rect, label, base_col in buttons:
    hover = rect.collidepoint(mx, my)
    surf = self._btn_surfs.get((label, base_col, hover))
    if surf:
        self._win.blit(surf, rect.topleft)
```

`solver_available` is whatever boolean the current code uses to decide whether the
Solve Board button is active (e.g., `eng.state == "playing"`). The key point is that
`base_col` must flow from the list construction into the draw loop — it cannot be
looked up from just `label` alone because "Solve Board" has two colour variants.

`_on_resize()` — add at end:

```python
self._rebuild_btn_surfs()
```

`_rebuild_num_surfs()` — add at end (fonts may change on zoom):

```python
self._rebuild_btn_surfs()
```

### Tests

```
test_btn_surfs_populated_at_init
test_btn_surfs_contain_normal_and_hover_variants
test_btn_surfs_rebuilt_on_resize
test_draw_panel_does_not_call_pill_per_frame   <- monkeypatch pill(), assert 0 calls
```

---

## Phase 7 — Mine Spike Cache + Animation Set Cache
**Status: PENDING**
**Fixes: P-14, P-16**
**File: `gameworks/renderer.py`**
**Tests: `gameworks/tests/renderer/test_surface_cache.py`**

### 7A — Mine spike offsets (P-14)

8 trig calls per visible mine cell per frame. Spikes are fixed for a given tile size.

`__init__` — add:

```python
self._mine_spike_offsets: list = []
```

`_rebuild_num_surfs()` — add at start:

```python
r = max(2, self._tile // 3)
self._mine_spike_offsets = [
    (int(math.cos(math.radians(a)) * r),
     int(math.sin(math.radians(a)) * r))
    for a in range(0, 360, 45)
]
```

`_draw_mine()` — replace trig loop:

```python
# BEFORE:
for a in range(0, 360, 45):
    rd = math.radians(a)
    ex = cx + int(math.cos(rd) * r)
    ey = cy + int(math.sin(rd) * r)
    pygame.draw.line(...)

# AFTER:
lw = max(1, ts // 16)
for dx, dy in self._mine_spike_offsets:
    pygame.draw.line(self._win, C["mine_spike"], (cx, cy), (cx + dx, cy + dy), lw)
```

Note: the `r` in `_rebuild_num_surfs` must match the `r` used in `_draw_mine`.
Both use `max(2, ts // 3)` — keep them in sync.

### 7B — Animation set caching (P-16)

`set(self.cascade.current())` is rebuilt every frame during animation, even when
`cascade._idx` has not advanced.

**Pre-condition — verify and if necessary add `WinAnimation._idx` before writing any code:**

The `AnimationCascade` tests explicitly reference `cascade._idx`. The `WinAnimation`
tests reference `anim._phase`, `anim._correct`, `anim._wrong` — but not `anim._idx`.

**Step 1 — Grep for the actual cursor attribute name:**

```
awk '/class WinAnimation/,/^class [A-Z]/' gameworks/renderer.py | grep -n "_idx\|_step\|_cursor"
```

This extracts the `WinAnimation` class body and searches within it for cursor-like
attributes. The pipe structure matters: `awk` first isolates the class, then `grep`
searches only those lines. The previous form (`grep … | grep -A2 "class WinAnimation"`)
was incorrect — the first grep emits attribute lines, none of which contain the string
"class WinAnimation", so the second grep always returns empty output.

**Step 2 — Branch on the result:**

- **If `_idx` is found**: substitute it directly in the key expression and in
  `_win_anim_last_key = (-1, -1)`. Proceed to implement Phase 7B.

- **If the cursor is named something else** (e.g. `_step`, `_cursor`): substitute
  that name everywhere `_idx` appears in the code below, and update
  `_win_anim_last_key` to match.

- **If no cursor attribute exists at all**: `WinAnimation` increments progress via
  a local variable inside `current()` only. In this case:
  1. Add `self._idx: int = 0` to `WinAnimation.__init__`.
  2. Increment `self._idx` at the same point where the local counter currently
     advances (typically inside the `if time.monotonic() >= self._next_tick:` block
     in `current()`).
  3. Then implement Phase 7B using `self._idx`.
  **This step must be its own atomic commit before the Phase 7B commit.**

Using a wrong or absent attribute silently reads `None`, producing key
`(_phase, None)` which is stable every frame — the cache would appear to work in
testing but skip all invalidation, freezing the animation set at the first-frame
snapshot for the entire animation run.

#### Fix

`__init__` — add:

```python
self._anim_set_cache: set = set()
self._anim_set_last_idx: int = -1
self._win_anim_set_cache: set = set()
self._win_anim_last_key: tuple = (-1, -1)
```

`_draw_board` — replace the set construction:

```python
# CASCADE:
anim_set: set = set()
if self.cascade and not self.cascade.done:
    current = self.cascade.current()
    if self.cascade._idx != self._anim_set_last_idx:
        self._anim_set_cache = set(current)
        self._anim_set_last_idx = self.cascade._idx
    anim_set = self._anim_set_cache

# WIN ANIM:
win_anim_set: set = set()
if self.win_anim and not self.win_anim.done:
    current = self.win_anim.current()
    key = (self.win_anim._phase, self.win_anim._idx)   # NOT len(current) — see note
    if key != self._win_anim_last_key:
        self._win_anim_set_cache = set(current)
        self._win_anim_last_key = key
    win_anim_set = self._win_anim_set_cache
```

#### Why `(_phase, _idx)` and NOT `(_phase, len(current))`

`len(current)` is the length of the running list returned by `win_anim.current()`,
which grows by 1 on every call as revealed positions accumulate. The key changes
**every frame** — the cache is rebuilt every frame, adding a key comparison and a
dict write on top of the original cost. The "cache" becomes a regression.

`_idx` is the animation cursor that advances only on timer ticks (`ANIM_TICK` interval,
~35ms). Between ticks the key is stable and the set is reused across all frames in that
tick window (typically 1–2 frames at 30 FPS).

`_phase` is required because `WinAnimation` has multiple phases (phase 0 = correct
flags, phase 1 = wrong flags, etc.) and `_idx` resets to 0 at each phase boundary.
Without `_phase`, the cache would produce a false hit when phase 1 starts at `_idx=0`,
matching the stale entry written when phase 0 started at `_idx=0`.

The `cascade` cache uses `_idx` alone (no phase) because `AnimationCascade` is
single-phase and `_idx` is monotonically increasing — no reset ever occurs.

The set is rebuilt only when `_idx` advances — typically once per `ANIM_TICK`
interval (35ms), not once per frame (33ms).

### Tests to add in `gameworks/tests/renderer/test_surface_cache.py`

```
test_mine_spike_offsets_populated_at_init
    # Assert len(renderer._mine_spike_offsets) == 8 after __init__

test_mine_spike_offsets_rebuilt_on_zoom
    # Change self._tile, call _rebuild_num_surfs(), assert offsets recomputed
    # (verify r = max(2, new_tile // 3) is reflected in first offset value)

test_mine_spike_offsets_contain_8_tuples_of_ints
    # Assert all elements are 2-tuples of Python int (not float from trig)

test_anim_set_cache_stable_between_idx_ticks
    # Advance cascade to _idx=N; call _draw_board twice without advancing _idx
    # Assert id(renderer._anim_set_cache) is stable (same object both calls)

test_anim_set_cache_rebuilt_on_idx_advance
    # Assert id(renderer._anim_set_cache) changes when cascade._idx increments

test_win_anim_set_cache_stable_within_phase
    # Same as anim_set test but for win_anim: stable key → same cache object

test_win_anim_set_cache_invalidated_on_phase_change
    # Simulate phase boundary (_phase increments, _idx resets to 0)
    # Assert cache is rebuilt despite _idx returning to 0
```

The `test_win_anim_set_cache_invalidated_on_phase_change` test is the regression
guard for the `(_phase, _idx)` vs `_idx`-only key decision: it must **fail** if the
key is changed to use `_idx` alone, and **pass** with the correct `(_phase, _idx)` key.

---

## Phase 8 — Frame Timing Precision
**Status: PENDING**
**Fixes: P-19**
**File: `gameworks/main.py`**

### Problem

`clock.tick(FPS)` uses the OS `sleep()` system call. On Windows, the system scheduler
has ~15ms granularity. For a 30 FPS target (33.3ms/frame), frames can arrive at 30ms
or 45ms — producing the jitter experienced as "sluggishness" or "mouse feels heavy"
even when the CPU is otherwise idle.

On Linux and macOS, the kernel uses `clock_nanosleep` with sub-millisecond precision.
`clock.tick()` already achieves accurate frame pacing on these platforms. Switching
to `tick_busy_loop()` unconditionally on Linux/macOS wastes CPU in a spin with zero
perceptible benefit.

### Fix

Locate the `self._renderer._clock.tick(FPS)` call in `main.py` (inside `GameLoop.run()`).
Replace with a platform-conditional:

```python
import sys   # add at top of main.py if not already present

# In GameLoop.run(), replace the tick call:
if sys.platform == "win32":
    self._renderer._clock.tick_busy_loop(FPS)
else:
    self._renderer._clock.tick(FPS)
```

`tick_busy_loop()` uses a coarse sleep to get close to the target, then spin-waits the
last few milliseconds. On Windows this eliminates 5–15ms frame jitter at the cost of
slightly higher CPU idle usage. On Linux/macOS, the standard `tick()` is already
accurate and the busy-loop spin buys nothing.

**Scope:** This fix benefits Windows users only. Do not apply unconditionally.

---

## Phase 9 — Image Source Surface Cap
**Status: PENDING**
**Fixes: P-24 (FA-021)**
**File: `gameworks/renderer.py`**
**Tests: `gameworks/tests/renderer/test_renderer_init.py`**

### Problem

`Renderer.__init__` upscales `_image_surf` to fit the full board pixel area at the
initial tile size:

```python
scale = min((w_cols * self._tile) / max(img.get_width(), 1),
            (h_rows * self._tile) / max(img.get_height(), 1))
tw = max(1, int(img.get_width() * scale))
th = max(1, int(img.get_height() * scale))
self._image_surf = pygame.transform.smoothscale(img, (tw, th))
```

For a 200×200 image on a 300×370 board (initial tile=10), `scale = 15` and
`_image_surf` is stored at 3000×3000 (9 M pixels, ~36 MB). Every subsequent zoom-level
change triggers:

```python
# _draw_image_ghost — fires once per zoom step in the next frame
self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))
```

`pygame.transform.smoothscale` time is dominated by source pixel count. Downscaling a
9 M-pixel source to the minimum-zoom board size (e.g., 300×370 = 111 k pixels) reads
all 9 M source pixels per call. Zooming from tile=10 to tile=1 requires ~5 scroll
steps → 5 blocking `smoothscale` calls in successive frames → 500 ms–2.5 s of main
thread blocking during the zoom-out sequence.

The invariant broken by the current code: `_image_surf` is stored at a size that
grows with the initial tile value, not with the natural image resolution. A smaller
input image produces a *larger* `_image_surf` (upscaled further to fill the board),
making zoom-out strictly slower for users who supply small source images.

### Solution

Store `_image_surf` at the natural image dimensions. Only downscale if the input
image exceeds the board pixel area at maximum zoom (`board.width * BASE_TILE ×
board.height * BASE_TILE`), which caps memory use for very high-resolution inputs.
Never upscale.

#### `Renderer.__init__` — replace the image-scaling block in `__init__`

Search for the block that computes `scale`, `tw`, `th` and calls
`pygame.transform.smoothscale(img, (tw, th))` to assign `self._image_surf`.
It is the only `smoothscale` call in `__init__`.

```python
# BEFORE (upscales to board pixel dimensions at initial tile):
scale = min((w_cols * self._tile) / max(img.get_width(), 1),
            (h_rows * self._tile) / max(img.get_height(), 1))
tw = max(1, int(img.get_width() * scale))
th = max(1, int(img.get_height() * scale))
self._image_surf = pygame.transform.smoothscale(img, (tw, th))

# AFTER (never upscale; downscale only if input exceeds max-zoom board pixel area):
max_w = w_cols * BASE_TILE
max_h = h_rows * BASE_TILE
if img.get_width() > max_w or img.get_height() > max_h:
    cap_scale = min(max_w / max(img.get_width(), 1),
                    max_h / max(img.get_height(), 1))
    cw = max(1, int(img.get_width() * cap_scale))
    ch = max(1, int(img.get_height() * cap_scale))
    self._image_surf = pygame.transform.smoothscale(img, (cw, ch))
else:
    self._image_surf = img  # keep at natural resolution
```

Why `BASE_TILE` (not `self._tile`): `BASE_TILE = 32` is the hard maximum tile size.
The cap ensures `_image_surf` never exceeds the pixel area needed at maximum zoom.
At all other zoom levels, scaling from the natural image size is equivalent or better
quality and always faster because the source pixel count is lower.

Why not `self._tile`: using the *initial* tile as the cap (the original behaviour)
ties surface size to a runtime variable. On a large board where `auto_tile = 10`,
`_image_surf` grows to `board.width * 10` wide — 10× the `BASE_TILE = 1` minimum
but still many times the natural image width. The bug is repeatable for any board
where `auto_tile > 1` and the source image is smaller than the board pixel area.

#### Impact on `_draw_image_ghost` — no change required

The `_ghost_surf` rebuild condition (`self._ghost_surf.get_size() != (bw, bh)`) and
the subsequent `smoothscale(_image_surf, (bw, bh))` call are unchanged. With a
small `_image_surf` (natural resolution), each zoom-step `smoothscale` now reads
`img_w × img_h` source pixels instead of `board_w * initial_tile × board_h *
initial_tile`. For the 200×200 example: 40 000 vs 9 000 000 source pixels — a 225×
reduction.

**Zoom-out direction:** `smoothscale` time is dominated by source pixel count when
downscaling (reads all source pixels, writes fewer dest pixels). For a 512×512 source
scaled to (300, 370): ~262 k source pixels at ~2 ns/px ≈ < 1 ms. The blocking spikes
during zoom-out are eliminated.

**Zoom-in direction:** `smoothscale` time when upscaling is dominated by destination
pixel count (must compute all dest pixels). At tile=32 (max zoom): `smoothscale(512×512,
(9600, 11840))` writes 113 M destination pixels ≈ 200–250 ms. This is an existing
limitation of the SDL smoothscale algorithm and is not introduced by this fix — the
current code avoids this cost by storing `_image_surf` at the inflated size, paying
the cost once at init instead of at zoom-in time. Phase 9 trades that init cost for a
per-zoom-in cost at max tile. The zoom-in case is significantly less common in gameplay
than zoom-out; if it proves problematic, pre-rendering `_ghost_surf` eagerly at init
for the max-zoom level (one `smoothscale` at startup, never repeated during play) is a
follow-on optimisation outside this phase's scope.

#### Impact on `_build_thumb` — no change required

`_build_thumb` calls `pygame.transform.smoothscale(self._image_surf, (thumb_w,
thumb_h))` once at init. With a smaller `_image_surf`, this call becomes faster.
The visual result is identical — `_image_surf` was never used at its inflated size
directly; it was always further scaled by `_build_thumb` and `_ghost_surf`.

#### Memory delta

"Before" sizes reflect the current code's `_image_surf = smoothscale(img, (board_w *
initial_tile, board_h * initial_tile))`.  For a 300×370 board at initial tile=10 the
board pixel area is 3000×3700; the current code always produces an `_image_surf` of
roughly that size regardless of the natural image dimensions.

| Scenario | Before (current) | After (fix) | Direction |
|---|---|---|---|
| 200×200 image, 300×370 board, tile=10 | ≈ 3000×3000 × 4 B ≈ 36 MB | 200×200 × 4 B = 160 KB | ✓ 225× smaller |
| 512×512 image, 300×370 board, tile=10 | ≈ 3000×3000 × 4 B ≈ 36 MB | 512×512 × 4 B ≈ 1 MB | ✓ 36× smaller |
| 2048×2048 image, 300×370 board, tile=10 | ≈ 2998×2998 × 4 B ≈ 36 MB | 2048×2048 × 4 B ≈ 16 MB | ✓ 2.2× smaller |
| 4096×4096 image, 300×370 board, tile=10 | ≈ 2998×2998 × 4 B ≈ 36 MB | 4096×4096 × 4 B ≈ 67 MB | ⚠ slight regression |

The regression in row 4 is expected and acceptable: for a 4096×4096 image on a 300×370
board, `max_w = 9600 > 4096`, so the cap does not trigger and `_image_surf = img` is
stored at its natural 67 MB.  The current code accidentally downscales such images to
fit the board pixel area at the initial tile (≈36 MB) — a lossy pre-process that
reduces quality for zoom-in.  The fix avoids that lossy pre-step at the cost of
slightly higher memory for very large inputs.  For images larger than the board's
max-zoom pixel area (`board.width * BASE_TILE × board.height * BASE_TILE`), the cap
triggers and the fix produces a smaller surface than the current code.  If memory
pressure for very large input images is a concern, a secondary cap at an absolute pixel
budget (e.g., 2048² = 4 MP) may be added as a follow-on.

**Pre-condition:** `BASE_TILE` must be importable at the `Renderer.__init__` call site.
It is already defined as a module-level constant (`BASE_TILE = 32`) in `renderer.py`,
so no import changes are required.

### Tests to add in `gameworks/tests/renderer/test_renderer_init.py`

```
test_image_surf_not_upscaled_beyond_natural_size
    # Assert _image_surf.get_width() <= natural_img_w
    # Assert _image_surf.get_height() <= natural_img_h
    # Inject a 16×16 PNG; verify _image_surf dimensions are (16, 16)

test_image_surf_clamped_for_oversized_input
    # Inject a synthetic surface larger than BASE_TILE * board_w
    # Assert _image_surf.get_width() <= board_w * BASE_TILE

test_ghost_surf_rebuild_time_bounded_after_fix
    # Patch pygame.transform.smoothscale to record call args
    # Inject a 32×32 image, trigger a tile change, assert smoothscale
    # was called with a source no larger than 32×32 (not board pixel dims)

test_image_surf_unchanged_for_natural_size_input
    # Inject a 64×64 image on a 16×16 board (BASE_TILE=32 → max_w=512, max_h=512)
    # Assert _image_surf.get_size() == (64, 64)
    # — verifies the else branch is taken and dimensions are preserved.
    # NOTE: do NOT assert object identity (renderer._image_surf is img).
    # img is a local inside a try/except in __init__; the test harness has no
    # reference to it, and convert_alpha() may or may not return the same object.
    # Dimension equality is the correct and portable assertion here.
```

The regression guard is `test_image_surf_not_upscaled_beyond_natural_size`. It must
**fail** on the current codebase (source image = 16×16, `_image_surf` = 3000×3000 on
a 300-wide board at tile=10) and **pass** after the fix.

---

## Phase 10 — Hot-Loop Tuple Allocation Reduction
**Status: PENDING**
**Fixes: P-25 (FA-022)**
**File: `gameworks/renderer.py`**
**Tests: `gameworks/tests/renderer/test_cell_draw.py`**

### Problem

The cell draw loop currently creates Python tuple objects on every cell iteration:

```python
ip = _revealed[y, x] and (x, y) in anim_set          # tuple allocated per cell
in_win_anim = (x, y) in win_anim_set                  # tuple allocated per cell
...pressed == (x, y)                                   # tuple allocated per cell
```

At tile=1 (maximum zoom-out), the visible area is the full 300×370 = 111,000 cells.
Three tuple allocations per cell = **333,000 tuples per frame** at 30 FPS =
10 million tuple allocations per second. CPython's allocator is fast but not free:
at 2–5 ns per small object allocation, this accounts for ~0.67–1.67 ms/frame of
pure allocation overhead — measurable but not dominant at tile=1 where the draw
loop itself is the bottleneck.

The allocator overhead is the dominant cost. CPython's cyclic GC tracks tuples
only when they contain other tracked objects (e.g., dicts, lists, class instances).
A `(int, int)` tuple contains only immutable scalars and is either never tracked or
rapidly untracked via `_PyObject_GC_UNTRACK` shortly after creation. GC collection
pauses from these tuples specifically are minimal and not the right justification for
this fix.

The correct framing: each allocation invokes `pymalloc` or the small-object
free-list, increments and then decrements refcounts, and writes a pointer that
the allocator must zero on free. At 333k/frame these per-object costs accumulate
to ~0.67–1.67ms of pure allocator overhead — measurable and additive with the
draw-loop cost at tile=1.

### Solution

#### 10A — Replace set membership with flat arrays

Convert `anim_set` and `win_anim_set` from `set` of tuples to 2D numpy `bool` arrays.
Membership becomes an array index (O(1), zero allocation) instead of a hash lookup
on a heap-allocated tuple key.

`_draw_board` — replace set construction (this is the intermediate step; 10B below
eliminates the per-frame `np.zeros` allocation):

```python
# CASCADE:
anim_arr = np.zeros((board_h, board_w), dtype=bool)
if self.cascade and not self.cascade.done:
    for (cx, cy) in self.cascade.current():
        anim_arr[cy, cx] = True

# WIN ANIM:
win_arr = np.zeros((board_h, board_w), dtype=bool)
if self.win_anim and not self.win_anim.done:
    for (cx, cy) in self.win_anim.current():
        win_arr[cy, cx] = True
```

Cell loop — replace set lookups and tuple comparisons:

```python
ip         = _revealed[y, x] and anim_arr[y, x]   # no tuple
in_win_anim = win_arr[y, x]                         # no tuple
is_pressed = (pressed is not None
              and pressed[0] == x and pressed[1] == y)  # no (x,y) tuple vs tuple
```

Where `pressed` is stored as a 2-tuple `(px, py)` already (from the MOUSEBUTTONDOWN
event), but the comparison is restructured to avoid allocating a new `(x, y)` on the
right-hand side. Alternatively, maintain `_pressed_x` and `_pressed_y` as separate
`int` attributes on the renderer to eliminate the tuple entirely.

#### 10B — Pre-allocate reusable bool arrays in `__init__`

Rather than allocating two `(board_h × board_w)` bool arrays every frame, allocate
once at init (and on board size change) and zero them in-place with `fill(False)`:

```python
# __init__ — after engine / board is set:
h, w = self.board.height, self.board.width
self._anim_arr     = np.zeros((h, w), dtype=bool)
self._win_anim_arr = np.zeros((h, w), dtype=bool)
```

`_draw_board` — per-frame:

```python
self._anim_arr.fill(False)
if self.cascade and not self.cascade.done:
    for (cx, cy) in self.cascade.current():
        self._anim_arr[cy, cx] = True

self._win_anim_arr.fill(False)
if self.win_anim and not self.win_anim.done:
    for (cx, cy) in self.win_anim.current():
        self._win_anim_arr[cy, cx] = True
```

Memory cost: one array = 300 × 370 × 1 byte = 111,000 bytes ≈ **108 KB** (numpy
stores bool as 1 byte/element). Two arrays = 222,000 bytes ≈ **216 KB** total —
negligible.

**Interaction with Phase 7B:** Phase 7B's set-caching approach becomes unnecessary
if Phase 10A is implemented (the set is replaced with an array). Implement Phase 10
before or instead of Phase 7B. If Phase 7B is already committed, Phase 10 supersedes
it for the win_anim path; the `_anim_set_cache` for cascade can likewise be removed.

### Tests to add in `gameworks/tests/renderer/test_cell_draw.py`

```
test_anim_arr_preallocated_at_init
    # Assert renderer._anim_arr.shape == (board_h, board_w)
    # Assert renderer._win_anim_arr.shape == (board_h, board_w)

test_anim_arr_zero_when_no_cascade
    # Assert _anim_arr.sum() == 0 when cascade is None

test_anim_arr_set_for_cascade_cells
    # Set a cascade with known cells, call one draw frame
    # Assert _anim_arr[cy, cx] == True for each cascade cell

test_cell_loop_zero_tuple_allocations
    # Monkeypatch tuple.__new__ or use tracemalloc to count tuple allocations
    # during _draw_board; assert count < N for a reasonable bound
    # (Pragmatic: assert delta_objects from tracemalloc < 1000 for 10x10 board)

test_pressed_comparison_no_tuple
    # Assert _draw_cell is called with is_pressed bool, not compared via (x,y) tuple
```

---

## Execution Order and Dependencies

```
Phase 1  ---> independent, safest, no renderer dependency
Phase 2  ---> independent, no phase dependencies
Phase 3  ---> independent (cell loop refactor: monotonic hoist, CellState removal,
              dead guard removal — none of these depend on Phase 2 additions)
Phase 4  ---> depends on Phase 2 (4C uses self._win_size added in Phase 2A;
              4B must only be invalidated on resize — no zoom invalidation needed)
Phase 5  ---> independent (but uses font objects; run after fonts are stable)
Phase 6  ---> depends on Phase 5 (both phases add calls to _rebuild_num_surfs();
              commit Phase 5 first to avoid merge conflicts in that method)
Phase 7A ---> depends on Phase 3 (_mine_spike_offsets used in _draw_mine, which
              Phase 3 refactors — implement after Phase 3 stabilises _draw_mine)
Phase 7B ---> superseded by Phase 10 if Phase 10 is implemented; otherwise independent
Phase 8  ---> independent (suggested last among Phases 1–8; Phases 9 and 10 are
              also independent and may be committed in any order relative to Phase 8)
Phase 9  ---> independent; only touches __init__ image-load block; no interaction
              with any other phase. Implement first if zoom-out freeze is the
              priority — it is a self-contained 10-line change.
Phase 10 ---> depends on Phase 3 (requires the refactored cell loop from 3B to
              replace set lookups with array indexing cleanly); supersedes Phase 7B
              for the animation set caching problem.
```

Each phase is one commit. Never combine phases in a single commit.

---

## Pre-Push Checklist Per Phase

Per AGENTS.md, before each push:

1. `git diff --staged` — verify only the intended phase files changed
2. `python -c "import ast; ast.parse(open('gameworks/engine.py').read())"`
   `python -c "import ast; ast.parse(open('gameworks/renderer.py').read())"`
   `python -c "import ast; ast.parse(open('gameworks/main.py').read())"`
3. `python -m pyflakes gameworks/engine.py gameworks/renderer.py gameworks/main.py`
4. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/test_gameworks_engine.py tests/test_gameworks_renderer_headless.py gameworks/tests/ -v`
5. For Phase 1: verify `test_counters_match_array_state_after_flood_fill` FAILS on
   a checkout without the fix (Method A, Step 7 of AGENTS.md)
6. For Phase 3: verify `test_draw_does_not_call_monotonic_in_cell_loop` FAILS before
   the hoist (Method A, Step 7 of AGENTS.md)
7. For Phase 9: verify `test_image_surf_not_upscaled_beyond_natural_size` FAILS on
   a checkout without the fix (inject a 16×16 image on a 300×370 board at tile=10;
   assert `_image_surf.get_width() <= 16` — this must fail before the fix since the
   current code stores it at ≈ 3000 wide) (Method A, Step 7 of AGENTS.md)
8. For Phase 10: verify `test_cell_loop_zero_tuple_allocations` FAILS on the
   pre-fix code (tracemalloc shows >333k tuple allocations on a full-board draw
   at tile=1) and PASSES after the numpy-array replacement (Method A, Step 7 of AGENTS.md)

---

## Expected Impact Summary

| Phase | Fixes    | Primary Saving                          | Mechanism                       |
|-------|----------|-----------------------------------------|---------------------------------|
| 1     | P-06/07/08/23 | ~3 array scans eliminated/frame    | Counter vs np.sum()             |
| 2     | P-15/17/18/21 | ~10 OS calls/frame eliminated      | Caching + hoisting              |
| 3     | P-01/02/03/20 | ~50,000 Python object ops/frame    | No CellState, no bool(), no monotonic per cell |
| 4     | P-04/05/09/10 | ~100+ Surface allocations/frame    | Tile buf reuse + overlay caches |
| 5     | P-11/12/22    | ~20 font.render() calls -> ~2/frame| String-keyed text cache         |
| 6     | P-13          | 40 draw calls/frame -> 5 blits     | Pre-baked button surfaces       |
| 7     | P-14/16       | 8 trig calls x N mines/frame -> 0  | Cached offsets + anim set cache |
| 8     | P-19          | 5-15ms jitter eliminated (Windows) | tick_busy_loop() on win32 only  |
| 9     | P-24 (FA-021) | 100–500 ms blocking spike per zoom step eliminated | Store _image_surf at natural size, not board pixel dims |
| 10    | P-25 (FA-022) | 333k+ tuple allocs/frame -> 0 at max zoom-out | numpy bool arrays replace set-of-tuples |

Phases 3, 4, and 5 are the three highest-impact changes. Implement them in that
priority order if resource-constrained.

---

## Acceptance Criteria

Each phase must meet **all** of the following targets on the reference board
(300×370, 111,000 cells) before its commit is considered done.

**Benchmark infrastructure prerequisite:** Performance measurements use
`pytest-benchmark`. Install it before running any `--benchmark-*` flags:

```
pip install pytest-benchmark
```

Verify installation: `pytest --co -q gameworks/tests/ | grep benchmark` should
list at least one benchmark. If `pytest-benchmark` is absent, `--benchmark-only`
silently collects zero tests — measurements will appear to pass vacuously.

Measure with `SDL_VIDEODRIVER=dummy` headless benchmarks (`pytest --benchmark-only`)
unless otherwise noted.

### Per-Phase Gate Tests

| Phase | Pass Condition |
|-------|----------------|
| 1     | `test_counters_match_array_state_after_flood_fill` PASSES; `board.flags_placed` never calls `np.sum` (verified by monkeypatching) |
| 2     | `test_win_size_cache_updated_on_videoresize` and `test_board_rect_cache_invalidated_on_zoom_change` PASS |
| 3     | `test_draw_does_not_call_monotonic_in_cell_loop` PASSES; `test_draw_completes_without_cellstate_construction` PASSES |
| 4     | `test_ghost_cell_buf_not_reallocated_across_frames` and `test_panel_overlay_surf_stable_across_frames` PASS |
| 5     | `test_tx_returns_same_object_for_identical_inputs` PASSES; `test_header_font_render_not_called_on_stable_frame` PASSES with 0 render calls on frame 2+ |
| 6     | `test_draw_panel_does_not_call_pill_per_frame` PASSES with 0 pill() calls |
| 7     | `test_win_anim_set_cache_invalidated_on_phase_change` PASSES |
| 8     | `sys.platform == "win32"` gate is present; no unconditional `tick_busy_loop` calls |
| 9     | `test_image_surf_not_upscaled_beyond_natural_size` FAILS on pre-fix checkout and PASSES after fix |
| 10    | `test_anim_arr_preallocated_at_init` PASSES; tracemalloc delta < 1,000 tuple objects per 10×10 board draw frame |

### System-Level FPS Targets

Measured with `--random --board-w 300 --board-h 370` at the given tile size,
averaged over 100 frames after warmup, on a mid-tier laptop CPU (Intel i5-class,
4 cores, no GPU acceleration):

| Zoom level | Tile size | Target (post all phases) | Baseline (current) |
|------------|-----------|--------------------------|---------------------|
| Max out    | 1 px      | ≥ 28 FPS                 | 3–5 FPS             |
| Mid        | 8 px      | ≥ 30 FPS                 | 20–25 FPS           |
| Default    | 10 px     | 30 FPS (locked)          | 30 FPS              |
| Max in     | 32 px     | 30 FPS (locked)          | 30 FPS              |

### Zoom-Step Latency Target

With Phase 9 applied, a single zoom step (one MOUSEWHEEL tick) must not block the
main thread for more than **16 ms** (one frame budget at 60 FPS) for any image
≤ 2048×2048 pixels on the reference board. Measured by patching
`pygame.transform.smoothscale` with a `time.perf_counter()` wrapper in the headless
test suite.

### Memory Budget

After all phases are applied, peak RSS during a full gameplay session (random board,
300×370, image mode with a 512×512 input, zoom from tile=32 to tile=1 and back)
must not exceed **300 MB**. Measured with `tracemalloc` or `/usr/bin/time -v`.

### Non-Regression Gate

The full test suite must pass before and after every phase commit:

```
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v --tb=short
```

Zero new failures permitted. Any pre-existing skipped tests must remain skipped (not
newly failing).
