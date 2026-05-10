# Performance Remediation Plan — P-01 through P-18
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

```python
# Mine-hit path (line ~177): after self._revealed[y, x] = True
self._n_revealed += 1

# BFS path (line ~188): after self._revealed[cy, cx] = True
self._n_revealed += 1
self._n_safe_revealed += 1
```

Win condition (line 195) — replace array scan with counter:

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
board._n_revealed      = board.total_safe
board._n_flags         = board.total_mines
board._n_questioned    = 0
```

### Tests to add in `gameworks/tests/unit/test_board.py`

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
- `renderer.py:400`  `_center_board`
- `renderer.py:520`  MOUSEMOTION handler
- `renderer.py:629`  `_clamp_pan`
- `renderer.py:685`  `_draw_overlay`
- `renderer.py:806`  `_draw_board`
- `renderer.py:948`  `_draw_loss_overlay`
- `renderer.py:988`  `_draw_image_ghost`
- `renderer.py:1158` `_draw_modal`
- `renderer.py:1179` `_draw_help`

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

`renderer.py:749` — `_draw_smiley` calls `pygame.mouse.get_pos()` ignoring the
`mouse_pos` already passed to `draw()`.

`_draw_smiley` signature change:

```python
def _draw_smiley(self, x, y, w, h, state, mouse_pos):
```

`_draw_header` signature change:

```python
def _draw_header(self, elapsed, game_state, mouse_pos):
```

`_draw_smiley` body (line 749): replace `pygame.mouse.get_pos()` with `mouse_pos`.

`draw()` call site — pass `mouse_pos` through:

```python
self._draw_header(elapsed, game_state, mouse_pos)
```

For the MOUSEWHEEL `get_pos()` at line 558, store `self._last_mouse_pos` and update
at the top of each `draw()` call:

```python
# In __init__:
self._last_mouse_pos: Tuple[int, int] = (0, 0)

# In draw() first line:
self._last_mouse_pos = mouse_pos

# In MOUSEWHEEL handler (line 558):
mx, my = self._last_mouse_pos   # was: pygame.mouse.get_pos()
```

### 2D — Single `elapsed` call per loop iteration (P-18)

`main.py:186` already caches `elapsed` correctly and passes it to `draw()`.
Verify no code path inside renderer calls `engine.elapsed` directly (which would
re-invoke `time.time()`). Add an architecture test to enforce this.

### Tests to add

```
test_win_size_cache_updated_on_videoresize
test_board_rect_cache_invalidated_on_pan_change
test_board_rect_cache_invalidated_on_zoom_change
test_draw_smiley_uses_passed_mouse_pos   <- monkeypatch get_pos, verify not called
```

---

## Phase 3 — Cell Loop Refactor
**Fixes: P-01, P-02, P-03, P-20**
**File: `gameworks/renderer.py`**
**Tests: `gameworks/tests/renderer/test_surface_cache.py`, new `test_cell_draw.py`**

This is the highest-impact single change for per-frame CPU. Every visible cell
currently pays for: a `CellState` dataclass construction, 5 numpy->Python type
coercions, and a `time.monotonic()` system call.

### 3A — Hoist `time.monotonic()` out of the cell loop (P-01)

In `_draw_board`, before the `for y in range(ty0, ty1):` loop at line 822:

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

Dict key cast: `self._num_surfs[int(neighbour_mines)]` — numpy uint8 key must be
cast to Python int to match the dict's Python int keys.

### 3C — Remove dead `_num_tile != ts` guard (P-20)

`renderer.py:882` — this check can never be true mid-frame (surfs are rebuilt
immediately after zoom before any draw call):

```python
# DELETE these two lines:
if self._num_tile != ts:
    self._rebuild_num_surfs()
```

Add a guard assertion in `_rebuild_num_surfs()` instead so it fails loudly if the
invariant is ever broken during development.

### Tests to add in `gameworks/tests/renderer/test_cell_draw.py`

```
test_draw_completes_without_cellstate_construction   <- monkeypatch CellState
test_draw_does_not_call_monotonic_in_cell_loop       <- monkeypatch, count calls == 1
test_draw_cell_flashing_uses_passed_now
test_draw_board_correct_cell_count_drawn             <- verify viewport culling
```

---

## Phase 4 — Surface Allocation Caches
**Fixes: P-04, P-05, P-09, P-10**
**File: `gameworks/renderer.py`**
**Tests: `gameworks/tests/renderer/test_surface_cache.py`**

All four issues share the same root cause: SRCALPHA surface construction or `.copy()`
on the per-frame hot path. The fix in every case is the established `_fog_surf`
pattern already in the codebase.

### 4A — Image ghost per-cell copy elimination (P-04, P-05)

Problem: `subsurface().copy()` + `set_alpha()` per flagged cell per frame allocates
a new Surface for each one.

Fix: pre-bake two versions of the ghost surface at init/zoom. No per-cell copy needed.

`__init__` — add after existing `_ghost_surf`:

```python
self._ghost_mine_surf: Optional[pygame.Surface] = None   # ghost at alpha=200
self._ghost_safe_surf: Optional[pygame.Surface] = None   # ghost at alpha=40
```

`_draw_image_ghost` — when rebuilding `_ghost_surf`, also bake alpha variants:

```python
if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
    self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))
    # Pre-bake alpha variants — eliminates per-cell .copy() on hot path
    self._ghost_mine_surf = self._ghost_surf.copy()
    self._ghost_mine_surf.set_alpha(200)
    self._ghost_safe_surf = self._ghost_surf.copy()
    self._ghost_safe_surf.set_alpha(40)
```

Per-cell loop — eliminate `.copy()`:

```python
for y, x in zip(ys, xs):
    px = ox + int(x) * ts
    py = oy + int(y) * ts
    src_rect = pygame.Rect(int(x) * ts, int(y) * ts, ts, ts)
    surf = self._ghost_mine_surf if _mine[y, x] else self._ghost_safe_surf
    self._win.blit(surf.subsurface(src_rect), (px, py))  # no .copy()
```

`_draw_win_animation_fx` (P-05) — win anim always uses alpha=255 (full opacity).
Blit `_ghost_surf` subsurface directly:

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

Invalidation trigger: window resize — add `self._panel_overlay_surf = None` in
VIDEORESIZE handler.

### 4C — Modal and help full-screen overlays (P-10)

`__init__` — add:

```python
self._modal_overlay_surf: Optional[pygame.Surface] = None
self._modal_overlay_surf_size: Tuple[int, int] = (0, 0)
self._help_overlay_surf: Optional[pygame.Surface] = None
self._help_overlay_surf_size: Tuple[int, int] = (0, 0)
```

`_draw_modal` — replace lines 1158-1160:

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
test_ghost_mine_surf_stable_across_frames
test_ghost_safe_surf_stable_across_frames
test_ghost_alpha_surfs_rebuilt_on_zoom_change
test_panel_overlay_surf_stable_across_frames
test_panel_overlay_surf_rebuilt_on_resize
test_modal_overlay_surf_stable_across_frames
test_help_overlay_surf_stable_across_frames
```

Each test uses the same id()-comparison pattern as the existing
`test_fog_surf_stable_across_frames`.

---

## Phase 5 — Text/Font Surface Cache
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

Cache invalidation on font rebuild — in `_rebuild_num_surfs()`, add:

```python
self._text_cache.clear()
```

Font objects are recreated when tile-based font sizes change. Clearing ensures no
stale `id(font)` references remain.

### Apply `_tx()` everywhere `font.render()` is called in the draw path

`_draw_header` (P-12) — replace all 4 render calls:

```python
# line 711:
mt = self._tx(f"M:{mines:>03d}", self._font_big, mcol)

# line 733:
sc = self._tx(f"SCORE:{score:>6d}", self._font_small, score_col)

# line 735:
tt = self._tx(f"T:{secs:>03d}", self._font_small, C["text_light"])

# line 742:
sl = self._tx(f"STREAK x{streak}  {mult:.1f}x", self._font_small, streak_col)
```

`_draw_panel` (P-11) — replace all render calls at lines 1033, 1053, 1059, 1067,
1090-1093, 1108, 1112-1114.

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

`_draw_panel` button loop — replace `pill()` + `font.render()` per button:

```python
for rect, label in buttons:
    hover = rect.collidepoint(mx, my)
    surf = self._btn_surfs.get((label, base_col, hover))
    if surf:
        self._win.blit(surf, rect.topleft)
```

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
**Fixes: P-14, P-16**
**File: `gameworks/renderer.py`**

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
    key = (self.win_anim._phase, len(current))
    if key != self._win_anim_last_key:
        self._win_anim_set_cache = set(current)
        self._win_anim_last_key = key
    win_anim_set = self._win_anim_set_cache
```

The set is only rebuilt when `_idx` or phase/count changes — typically once per
`ANIM_TICK` interval (35ms), not once per frame (33ms).

---

## Phase 8 — Frame Timing Precision
**Fixes: P-19**
**File: `gameworks/main.py`**

### Problem

`clock.tick(FPS)` uses the OS `sleep()` system call. On Windows, the system scheduler
has ~15ms granularity. For a 30 FPS target (33.3ms/frame), frames can arrive at 30ms
or 45ms — producing the jitter experienced as "sluggishness" or "mouse feels heavy"
even when the CPU is otherwise idle.

### Fix

`main.py:219`:

```python
# BEFORE:
self._renderer._clock.tick(FPS)

# AFTER:
self._renderer._clock.tick_busy_loop(FPS)
```

`tick_busy_loop()` uses a coarse sleep to get close to the target, then spin-waits the
last few milliseconds. This achieves sub-millisecond frame delivery accuracy at the
cost of slightly higher CPU idle usage (the spin). For an interactive game where mouse
responsiveness matters, this is the correct trade-off.

---

## Execution Order and Dependencies

```
Phase 1  ---> independent, safest, no renderer dependency
Phase 2  ---> independent, no phase dependencies
Phase 3  ---> depends on Phase 2 (uses _win_size, _last_mouse_pos)
Phase 4  ---> depends on Phase 2 (uses _win_size in modal/help surfs)
Phase 5  ---> independent (but uses font objects; run after fonts are stable)
Phase 6  ---> depends on Phase 5 (_rebuild_btn_surfs calls font.render -> use _tx())
Phase 7A ---> depends on Phase 3 (_mine_spike_offsets used in _draw_mine)
Phase 7B ---> independent
Phase 8  ---> independent, commit last
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

---

## Expected Impact Summary

| Phase | Fixes    | Primary Saving                          | Mechanism                       |
|-------|----------|-----------------------------------------|---------------------------------|
| 1     | P-06/07/08/23 | ~3 array scans eliminated/frame    | Counter vs np.sum()             |
| 2     | P-15/17/18/21 | ~10 OS calls/frame eliminated      | Caching + hoisting              |
| 3     | P-01/02/03/20 | ~50,000 Python object ops/frame    | No CellState, no bool(), no monotonic per cell |
| 4     | P-04/05/09/10 | ~100+ Surface allocations/frame    | Pre-baked SRCALPHA surfaces     |
| 5     | P-11/12/22    | ~20 font.render() calls -> ~2/frame| String-keyed text cache         |
| 6     | P-13          | 40 draw calls/frame -> 5 blits     | Pre-baked button surfaces       |
| 7     | P-14/16       | 8 trig calls x N mines/frame -> 0  | Cached offsets + anim set cache |
| 8     | P-19          | 5-15ms jitter per frame eliminated | tick_busy_loop()                |

Phases 3, 4, and 5 are the three highest-impact changes. Implement them in that
priority order if resource-constrained.
