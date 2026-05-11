{
  "file_path": "/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/PERFORMANCE_PLAN.md"
}
     1→# Performance Remediation Plan — P-01 through P-18
     2→## Mine-Streaker `gameworks/` — Industry-Standard Approach
     3→
     4→Forensic analysis date: 2026-05-10
     5→Board reference: 300×370 (111,000 cells) at 30 FPS target.
     6→
     7→---
     8→
     9→## Design Principles Applied
    10→
    11→1. **Compute once, reuse until invalid** — every value computed per-frame must have a defined invalidation trigger
    12→2. **Push allocations to init/resize, never to the draw path**
    13→3. **No Python-level per-cell loops for anything that can be moved outside**
    14→4. **Dirty flags and counters instead of array scans**
    15→5. **Each phase is independently testable and independently commit-able**
    16→
    17→---
    18→
    19→## Phase 1 — Engine Dirty-Int Counters
    20→**Fixes: P-06, P-07, P-08, P-23**
    21→**File: `gameworks/engine.py`**
    22→**Tests: `gameworks/tests/unit/test_board.py`**
    23→
    24→### Problem
    25→
    26→Four `Board` properties scan full numpy arrays (111,000 elements for a 300x370 board) every
    27→frame:
    28→- `revealed_count`      -> `self._revealed.sum()`
    29→- `safe_revealed_count` -> `np.sum(self._revealed & ~self._mine)` (creates temp array)
    30→- `flags_placed`        -> `self._flagged.sum()`
    31→- `questioned_count`    -> `self._questioned.sum()`
    32→
    33→`safe_revealed_count` is called from `_draw_panel` every frame.
    34→`flags_placed` is called via `mines_remaining` every frame in `_draw_header`.
    35→Together: 3+ full-array scans x 30 FPS = millions of element ops/second that never
    36→change between user actions.
    37→
    38→### Solution
    39→
    40→Add 4 int counters to `Board.__init__`, incremented/decremented atomically in
    41→`toggle_flag()` and `reveal()`. Properties return the counter.
    42→
    43→#### `Board.__init__` — add after existing array init
    44→
    45→```python
    46→# Dirty-int counters — updated atomically on every state mutation.
    47→# Eliminates full numpy array scans from the per-frame draw path.
    48→self._n_flags: int = 0
    49→self._n_questioned: int = 0
    50→self._n_safe_revealed: int = 0   # revealed non-mine cells only
    51→self._n_revealed: int = 0        # total revealed (includes mine-hit cells)
    52→```
    53→
    54→#### `Board.reveal()` — increment counters at both write sites
    55→
    56→**Pre-condition:** These increments assume `reveal()` returns `(False, [])` early
    57→when `_revealed[y, x]` is already True (i.e., re-revealing an already-revealed cell
    58→is a no-op). Verify this guard exists before implementing — if it is absent, a
    59→second click on a revealed cell would double-increment the counters and corrupt all
    60→derived values. Search for the guard at the top of `reveal()`:
    61→
    62→```python
    63→if self._revealed[y, x]:
    64→    return False, []
    65→```
    66→
    67→If not present, add it before adding the counter increments.
    68→
    69→```python
    70→# Mine-hit path (line ~177): after self._revealed[y, x] = True
    71→self._n_revealed += 1
    72→
    73→# BFS path (line ~188): after self._revealed[cy, cx] = True
    74→self._n_revealed += 1
    75→self._n_safe_revealed += 1
    76→```
    77→
    78→Win condition (line 195) — replace array scan with counter:
    79→
    80→```python
    81→# Before:
    82→if self.revealed_count == self.total_safe:
    83→# After:
    84→if self._n_safe_revealed == self.total_safe:
    85→```
    86→
    87→#### `Board.toggle_flag()` — increment/decrement at each transition
    88→
    89→```python
    90→# flag -> question transition (line ~208):
    91→self._n_flags -= 1
    92→self._n_questioned += 1
    93→
    94→# question -> hidden transition (line ~213):
    95→self._n_questioned -= 1
    96→
    97→# hidden -> flag transition (line ~219):
    98→self._n_flags += 1
    99→```
   100→
   101→#### Replace all 4 properties
   102→
   103→```python
   104→@property
   105→def revealed_count(self) -> int:
   106→    return self._n_revealed
   107→
   108→@property
   109→def safe_revealed_count(self) -> int:
   110→    return self._n_safe_revealed
   111→
   112→@property
   113→def flags_placed(self) -> int:
   114→    return self._n_flags
   115→
   116→@property
   117→def questioned_count(self) -> int:
   118→    return self._n_questioned
   119→```
   120→
   121→#### `dev_solve_board()` — resync counters after bulk numpy ops
   122→
   123→After `board._revealed[~board._mine] = True` etc.:
   124→
   125→```python
   126→board._n_safe_revealed = board.total_safe
   127→board._n_revealed      = int(board._revealed.sum())  # recount from array — mine-hit cells may also be revealed
   128→board._n_flags         = board.total_mines
   129→board._n_questioned    = 0
   130→```
   131→
   132→Why `_revealed.sum()` and not `total_safe`: the game continues after mine hits
   133→(no game-over). The user may have clicked mine cells before invoking dev_solve,
   134→leaving those cells revealed (`_revealed[y, x] = True`) but not safe. Setting
   135→`_n_revealed = total_safe` would undercount by the number of previously hit mines.
   136→Using `_revealed.sum()` is safe here — dev_solve is already in a bulk-numpy context;
   137→the single O(n) recount is a one-time cost on user action, not per-frame.
   138→
   139→### Tests to add in `gameworks/tests/unit/test_board.py`
   140→
   141→```
   142→test_flags_placed_counter_increments_on_flag
   143→test_flags_placed_counter_decrements_on_question
   144→test_flags_placed_counter_decrements_on_hidden
   145→test_safe_revealed_count_increments_per_safe_cell
   146→test_questioned_count_increments_and_decrements
   147→test_counters_match_array_state_after_flood_fill   <- validates counter == np.sum
   148→test_dev_solve_resyncs_all_counters
   149→```
   150→
   151→The `test_counters_match_array_state_after_flood_fill` test is the regression guard:
   152→after any sequence of actions, assert `board._n_flags == int(board._flagged.sum())` etc.
   153→This catches any future mutation that forgets to update the counter.
   154→
   155→---
   156→
   157→## Phase 2 — Frame-Local Value Hoisting
   158→**Fixes: P-15, P-17, P-18, P-21**
   159→**Files: `gameworks/renderer.py`, `gameworks/main.py`**
   160→**Tests: `gameworks/tests/renderer/test_renderer_init.py`**
   161→
   162→### 2A — Cache `_win.get_size()` (P-21)
   163→
   164→`get_size()` appears at 9 locations in renderer.py. It is a C method call but still
   165→unnecessary when called repeatedly within one frame.
   166→
   167→`__init__` — add after `set_mode`:
   168→
   169→```python
   170→self._win_size: Tuple[int, int] = self._win.get_size()
   171→```
   172→
   173→`handle_event` VIDEORESIZE handler — update cache:
   174→
   175→```python
   176→self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
   177→self._win_size = ev.size   # <- add this line
   178→```
   179→
   180→All call sites — replace `self._win.get_size()` with `self._win_size`:
   181→- `renderer.py:400`  `_center_board`
   182→- `renderer.py:520`  MOUSEMOTION handler
   183→- `renderer.py:629`  `_clamp_pan`
   184→- `renderer.py:685`  `_draw_overlay`
   185→- `renderer.py:806`  `_draw_board`
   186→- `renderer.py:948`  `_draw_loss_overlay`
   187→- `renderer.py:988`  `_draw_image_ghost`
   188→- `renderer.py:1158` `_draw_modal`
   189→- `renderer.py:1179` `_draw_help`
   190→
   191→### 2B — Cache `_board_rect()` (P-17)
   192→
   193→The board rect only changes when `_pan_x`, `_pan_y`, or `_tile` changes.
   194→Add a cache invalidated whenever those values change.
   195→
   196→`__init__` — add:
   197→
   198→```python
   199→self._cached_board_rect: Optional[pygame.Rect] = None
   200→```
   201→
   202→`_board_rect()` method — return cached:
   203→
   204→```python
   205→def _board_rect(self) -> pygame.Rect:
   206→    if self._cached_board_rect is None:
   207→        bw = self.board.width * self._tile
   208→        bh = self.board.height * self._tile
   209→        self._cached_board_rect = pygame.Rect(
   210→            self.BOARD_OX + self._pan_x,
   211→            self.BOARD_OY + self._pan_y,
   212→            bw, bh)
   213→    return self._cached_board_rect
   214→```
   215→
   216→Invalidation — add `self._cached_board_rect = None` after every mutation of
   217→`_pan_x`, `_pan_y`, `_tile`:
   218→- MOUSEMOTION handler (after clamping)
   219→- MOUSEWHEEL handler (after zoom)
   220→- `_clamp_pan()` (end of method)
   221→- `_on_resize()` (end of method)
   222→- `_center_board()` (end of method)
   223→
   224→### 2C — Eliminate redundant `get_pos()` in `_draw_smiley` (P-15)
   225→
   226→`renderer.py:749` — `_draw_smiley` calls `pygame.mouse.get_pos()` ignoring the
   227→`mouse_pos` already passed to `draw()`.
   228→
   229→`_draw_smiley` signature change:
   230→
   231→```python
   232→def _draw_smiley(self, x, y, w, h, state, mouse_pos):
   233→```
   234→
   235→`_draw_header` signature change:
   236→
   237→```python
   238→def _draw_header(self, elapsed, game_state, mouse_pos):
   239→```
   240→
   241→`_draw_smiley` body (line 749): replace `pygame.mouse.get_pos()` with `mouse_pos`.
   242→
   243→`draw()` call site — pass `mouse_pos` through:
   244→
   245→```python
   246→self._draw_header(elapsed, game_state, mouse_pos)
   247→```
   248→
   249→For the MOUSEWHEEL `get_pos()` at line 558, store `self._last_mouse_pos` and update
   250→at the top of each `draw()` call:
   251→
   252→```python
   253→# In __init__:
   254→self._last_mouse_pos: Tuple[int, int] = (0, 0)
   255→
   256→# In draw() first line:
   257→self._last_mouse_pos = mouse_pos
   258→
   259→# In MOUSEWHEEL handler (line 558):
   260→mx, my = self._last_mouse_pos   # was: pygame.mouse.get_pos()
   261→```
   262→
   263→### 2D — Single `elapsed` call per loop iteration (P-18)
   264→
   265→`main.py:186` already caches `elapsed` correctly and passes it to `draw()`.
   266→Verify no code path inside renderer calls `engine.elapsed` directly (which would
   267→re-invoke `time.time()`). Add an architecture test to enforce this.
   268→
   269→### Tests to add
   270→
   271→```
   272→test_win_size_cache_updated_on_videoresize
   273→test_board_rect_cache_invalidated_on_pan_change
   274→test_board_rect_cache_invalidated_on_zoom_change
   275→test_draw_smiley_uses_passed_mouse_pos          <- monkeypatch get_pos, verify not called
   276→test_renderer_does_not_call_engine_elapsed      <- inspect renderer source, assert 'engine.elapsed' absent
   277→```
   278→
   279→---
   280→
   281→## Phase 3 — Cell Loop Refactor
   282→**Fixes: P-01, P-02, P-03, P-20**
   283→**File: `gameworks/renderer.py`**
   284→**Tests: `gameworks/tests/renderer/test_surface_cache.py`, new `test_cell_draw.py`**
   285→
   286→This is the highest-impact single change for per-frame CPU. Every visible cell
   287→currently pays for: a `CellState` dataclass construction, 5 numpy->Python type
   288→coercions, and a `time.monotonic()` system call.
   289→
   290→### 3A — Hoist `time.monotonic()` out of the cell loop (P-01)
   291→
   292→In `_draw_board`, before the `for y in range(ty0, ty1):` loop at line 822:
   293→
   294→```python
   295→now = time.monotonic()   # hoist here, pass to _draw_cell
   296→```
   297→
   298→### 3B — Eliminate `CellState` construction and bool() coercions (P-02, P-03)
   299→
   300→New `_draw_cell` signature — accepts raw primitive values:
   301→
   302→```python
   303→def _draw_cell(self,
   304→               x: int, y: int,
   305→               is_mine,          # numpy bool_ — no bool() needed
   306→               is_revealed,      # numpy bool_
   307→               is_flagged,       # numpy bool_
   308→               is_questioned,    # numpy bool_
   309→               neighbour_mines,  # numpy uint8
   310→               pos: Tuple[int, int],
   311→               in_anim: bool,
   312→               is_pressed: bool,
   313→               fog: bool,
   314→               ts: int,
   315→               in_win_anim: bool,
   316→               now: float):      # hoisted monotonic time
   317→```
   318→
   319→In the cell loop body — remove `CellState(...)` construction entirely:
   320→
   321→```python
   322→for y in range(ty0, ty1):
   323→    for x in range(tx0, tx1):
   324→        px = ox + x * ts
   325→        py = oy + y * ts
   326→        ip = _revealed[y, x] and (x, y) in anim_set
   327→        in_win_anim = (x, y) in win_anim_set
   328→        self._draw_cell(
   329→            x, y,
   330→            _mine[y, x], _revealed[y, x], _flagged[y, x],
   331→            _questioned[y, x], _neighbours[y, x],
   332→            (px, py), ip, pressed == (x, y),
   333→            self.fog, ts, in_win_anim, now
   334→        )
   335→```
   336→
   337→Inside `_draw_cell` — remove time call, use passed `now`:
   338→
   339→```python
   340→# DELETE: _flash_end = self.engine.mine_flash.get((x, y), 0)
   341→# DELETE: _flashing = time.monotonic() < _flash_end
   342→# REPLACE with:
   343→_flashing = now < self.engine.mine_flash.get((x, y), 0)
   344→```
   345→
   346→Also remove:
   347→
   348→```python
   349→# DELETE: if ts is None: ts = self._tile    (ts always passed)
   350→# DELETE: pad = max(1, ts // 16)            (verify unused then remove)
   351→```
   352→
   353→Dict key cast — `neighbour_mines` is a numpy `uint8`. The `_num_surfs` dict was
   354→built with Python `int` keys via `range()`. A numpy `uint8` key does not match a
   355→Python `int` key in a dict lookup, so the lookup silently returns `None`:
   356→
   357→```python
   358→# BEFORE (silent None return — numpy uint8 never matches Python int key):
   359→num_surf = self._num_surfs.get(neighbour_mines)
   360→
   361→# AFTER:
   362→num_surf = self._num_surfs.get(int(neighbour_mines))
   363→```
   364→
   365→### 3C — Remove dead `_num_tile != ts` guard (P-20)
   366→
   367→`renderer.py:882` — this check can never be true mid-frame (surfs are rebuilt
   368→immediately after zoom before any draw call):
   369→
   370→```python
   371→# DELETE these two lines:
   372→if self._num_tile != ts:
   373→    self._rebuild_num_surfs()
   374→```
   375→
   376→Add a guard assertion in `_draw_cell()` instead, at the top of the method, so it
   377→fails loudly during development if the invariant is ever broken:
   378→
   379→```python
   380→assert self._num_tile == ts, (
   381→    f"_draw_cell: tile size mismatch — _num_tile={self._num_tile} != ts={ts}. "
   382→    "Call _rebuild_num_surfs() before drawing."
   383→)
   384→```
   385→
   386→### Tests to add in `gameworks/tests/renderer/test_cell_draw.py`
   387→
   388→```
   389→test_draw_completes_without_cellstate_construction   <- monkeypatch CellState
   390→test_draw_does_not_call_monotonic_in_cell_loop       <- monkeypatch, count calls == 1
   391→test_draw_cell_flashing_uses_passed_now
   392→test_draw_board_correct_cell_count_drawn             <- verify viewport culling
   393→```
   394→
   395→---
   396→
   397→## Phase 4 — Surface Allocation Caches
   398→**Fixes: P-04, P-05, P-09, P-10**
   399→**File: `gameworks/renderer.py`**
   400→**Tests: `gameworks/tests/renderer/test_surface_cache.py`**
   401→
   402→All four issues share the same root cause: SRCALPHA surface construction or `.copy()`
   403→on the per-frame hot path. The fix in every case is the established `_fog_surf`
   404→pattern already in the codebase.
   405→
   406→### 4A — Image ghost per-cell copy elimination (P-04, P-05)
   407→
   408→Problem: `subsurface().copy()` + `set_alpha()` per flagged cell per frame allocates
   409→a new Surface for each one.
   410→
   411→#### Memory constraint — why full-board alpha copies are NOT used
   412→
   413→The natural first instinct is to pre-bake two full-board alpha variants of `_ghost_surf`.
   414→**Do not do this.** `_ghost_surf` is scaled to `board.width * tile × board.height * tile`.
   415→For the reference board (300×370 at 32px tiles):
   416→
   417→```
   418→9600 × 11840 pixels × 4 bytes RGBA32 = ~431 MB per surface
   419→```
   420→
   421→Two copies plus the original = **~1.3 GB** of surface memory. This will OOM most
   422→consumer machines. The fix must operate at tile granularity, not board granularity.
   423→
   424→#### Fix (P-04 — ghost cells with alpha): reusable tile-sized buffer
   425→
   426→Pre-allocate a single `ts×ts` SRCALPHA surface once per tile size. Per cell: blit the
   427→ghost tile into the buffer, set_alpha, blit buffer to window. Same number of blit
   428→operations as before, zero allocations per cell.
   429→
   430→Memory cost: one surface at `ts×ts` = 32×32×4 = **4 KB** at the default tile size.
   431→
   432→`__init__` — add after existing `_ghost_surf`:
   433→
   434→```python
   435→self._ghost_cell_buf: Optional[pygame.Surface] = None  # ts×ts reuse buffer; no alloc per cell
   436→self._ghost_cell_buf_ts: int = 0
   437→```
   438→
   439→`_draw_image_ghost` — rebuild buffer only when tile size changes:
   440→
   441→```python
   442→ts = self._tile
   443→if self._ghost_cell_buf is None or self._ghost_cell_buf_ts != ts:
   444→    self._ghost_cell_buf = pygame.Surface((ts, ts), pygame.SRCALPHA)
   445→    self._ghost_cell_buf_ts = ts
   446→```
   447→
   448→Per-cell loop — replace `.copy().set_alpha()` with buffer reuse:
   449→
   450→```python
   451→for y, x in zip(ys, xs):
   452→    px = ox + int(x) * ts
   453→    py = oy + int(y) * ts
   454→    src_rect = pygame.Rect(int(x) * ts, int(y) * ts, ts, ts)
   455→    # Clear before blit — REQUIRED for images with any transparent pixels.
   456→    # SRCALPHA blit composites src OVER dest; alpha < 255 source pixels do NOT
   457→    # fully overwrite the previous cell's content. Omitting fill() produces
   458→    # ghost-on-ghost artifacts along anti-aliased edges.
   459→    self._ghost_cell_buf.fill((0, 0, 0, 0))
   460→    self._ghost_cell_buf.blit(self._ghost_surf, (0, 0), src_rect)
   461→    self._ghost_cell_buf.set_alpha(200 if _mine[y, x] else 40)
   462→    self._win.blit(self._ghost_cell_buf, (px, py))
   463→```
   464→
   465→Why `set_alpha()` works here: `_ghost_cell_buf` is SRCALPHA. `set_alpha()` applies a
   466→per-surface alpha multiplier on top of per-pixel alpha. The ghost surf tiles have
   467→per-pixel alpha 255 after the `fill()` + `blit()`, so the multiplier directly controls
   468→the final opacity.
   469→
   470→Why `fill((0,0,0,0))` does not undo the blit: `fill()` runs before `blit()`. The
   471→sequence is: clear → copy tile content in → set global alpha → blit to window.
   472→
   473→#### Fix (P-05 — win animation cells): direct subsurface blit
   474→
   475→Win animation uses alpha=255 (full opacity). A `subsurface()` is directly blittable —
   476→the `.copy()` was only ever needed to detach the surface before calling `set_alpha()`.
   477→At full opacity no alpha call is needed, so the copy is eliminated entirely.
   478→
   479→`_draw_win_animation_fx` — replace `.copy()`:
   480→
   481→```python
   482→for (x, y) in win_anim_set:
   483→    px = ox + x * ts
   484→    py = oy + y * ts
   485→    src_rect = pygame.Rect(x * ts, y * ts, ts, ts)
   486→    self._win.blit(self._ghost_surf.subsurface(src_rect), (px, py))  # no .copy()
   487→```
   488→
   489→### 4B — Panel overlay backdrop (P-09)
   490→
   491→Pattern: identical to `_fog_surf`.
   492→
   493→`__init__` — add:
   494→
   495→```python
   496→self._panel_overlay_surf: Optional[pygame.Surface] = None
   497→self._panel_overlay_surf_size: Tuple[int, int] = (0, 0)
   498→```
   499→
   500→`_draw_panel` — replace per-frame allocation:
   501→
   502→```python
   503→# BEFORE (allocates every frame):
   504→_ov = pygame.Surface((_bd_w, _bd_h), pygame.SRCALPHA)
   505→_ov.fill((18, 18, 24, 215))
   506→self._win.blit(_ov, (px - self.PAD, oy))
   507→
   508→# AFTER (cached):
   509→sz = (_bd_w, _bd_h)
   510→if self._panel_overlay_surf is None or self._panel_overlay_surf_size != sz:
   511→    self._panel_overlay_surf = pygame.Surface(sz, pygame.SRCALPHA)
   512→    self._panel_overlay_surf.fill((18, 18, 24, 215))
   513→    self._panel_overlay_surf_size = sz
   514→self._win.blit(self._panel_overlay_surf, (px - self.PAD, oy))
   515→```
   516→
   517→Invalidation triggers — the overlay size `(_bd_w, _bd_h)` depends on **both** window
   518→size and tile size:
   519→
   520→- Window resize: add `self._panel_overlay_surf = None` in the VIDEORESIZE handler.
   521→- Zoom: add `self._panel_overlay_surf = None` at the start of `_rebuild_num_surfs()`
   522→  (called after every MOUSEWHEEL zoom event). The board pixel dimensions change with
   523→  tile size, so the cached overlay would be the wrong size after a zoom.
   524→
   525→Note: `_modal_overlay_surf` and `_help_overlay_surf` (Phase 4C) use `_win_size`
   526→only — their size does not change with tile size — so resize-only invalidation is
   527→correct for those two.
   528→
   529→### 4C — Modal and help full-screen overlays (P-10)
   530→
   531→`__init__` — add:
   532→
   533→```python
   534→self._modal_overlay_surf: Optional[pygame.Surface] = None
   535→self._modal_overlay_surf_size: Tuple[int, int] = (0, 0)
   536→self._help_overlay_surf: Optional[pygame.Surface] = None
   537→self._help_overlay_surf_size: Tuple[int, int] = (0, 0)
   538→```
   539→
   540→`_draw_modal` — replace lines 1158-1160:
   541→
   542→```python
   543→sz = self._win_size
   544→if self._modal_overlay_surf is None or self._modal_overlay_surf_size != sz:
   545→    self._modal_overlay_surf = pygame.Surface(sz, pygame.SRCALPHA)
   546→    self._modal_overlay_surf.fill((0, 0, 0, 160))
   547→    self._modal_overlay_surf_size = sz
   548→self._win.blit(self._modal_overlay_surf, (0, 0))
   549→```
   550→
   551→Same pattern for `_draw_help` with `(0, 0, 0, 200)`.
   552→
   553→Invalidation trigger: window resize -> set both to `None` in VIDEORESIZE handler.
   554→
   555→### Tests to add in `gameworks/tests/renderer/test_surface_cache.py`
   556→
   557→```
   558→test_ghost_cell_buf_allocated_once_per_tile_size
   559→test_ghost_cell_buf_not_reallocated_across_frames   <- assert id() stable across 2 draw calls
   560→test_ghost_cell_buf_rebuilt_on_zoom_change
   561→test_win_anim_fx_blit_no_copy                       <- monkeypatch Surface.copy, assert 0 calls
   562→test_panel_overlay_surf_stable_across_frames
   563→test_panel_overlay_surf_rebuilt_on_resize
   564→test_modal_overlay_surf_stable_across_frames
   565→test_help_overlay_surf_stable_across_frames
   566→```
   567→
   568→The first three tests use `id()` comparison on `_ghost_cell_buf` to verify the same
   569→surface object is reused across frames and rebuilt on zoom, matching the pattern of
   570→the existing `test_fog_surf_stable_across_frames`.
   571→
   572→---
   573→
   574→## Phase 5 — Text/Font Surface Cache
   575→**Fixes: P-11, P-12, P-22**
   576→**File: `gameworks/renderer.py`**
   577→**Tests: `gameworks/tests/renderer/test_surface_cache.py`**
   578→
   579→### Design
   580→
   581→`font.render()` is one of the most expensive Pygame operations. The renderer calls it
   582→~20 times per frame for panel stats, tips, button labels, and header values. Most of
   583→these strings never change between frames — score only changes on action, timer changes
   584→every second, tips never change.
   585→
   586→The solution is a string-keyed render cache: a dict mapping
   587→`(text, font_id, color) -> Surface`. On a cache hit the surface is returned instantly
   588→(O(1) dict lookup). On a miss the surface is rendered and stored. The cache is
   589→self-managing: stale entries accumulate but are bounded — score is max 7 digits, timer
   590→is max 4 digits, so the cache stays small.
   591→
   592→### `__init__` — add:
   593→
   594→```python
   595→self._text_cache: dict = {}   # (text, font_id, color) -> pygame.Surface
   596→```
   597→
   598→### New helper method:
   599→
   600→```python
   601→def _tx(self, text: str, font: pygame.font.Font, color: tuple) -> pygame.Surface:
   602→    """Cached font.render(). Re-renders only when text or style changes."""
   603→    key = (text, id(font), color)
   604→    s = self._text_cache.get(key)
   605→    if s is None:
   606→        s = font.render(text, True, color)
   607→        self._text_cache[key] = s
   608→    return s
   609→```
   610→
   611→**`color` must always be a plain Python tuple** — e.g. `(255, 255, 255)` or
   612→`(r, g, b, a)`. Do not pass `pygame.Color` objects. A `pygame.Color(255, 255, 255)`
   613→and a tuple `(255, 255, 255)` produce different hash values and will never share a
   614→cache entry, causing every call with a Color object to be a miss and a re-render.
   615→All `C["..."]` palette values used in the renderer must be defined as tuples in the
   616→colour constants dict, not as `pygame.Color` instances.
   617→
   618→Cache invalidation on font rebuild — in `_rebuild_num_surfs()`, add:
   619→
   620→```python
   621→self._text_cache.clear()
   622→```
   623→
   624→Font objects are recreated when tile-based font sizes change. Clearing ensures no
   625→stale `id(font)` references remain.
   626→
   627→### Apply `_tx()` everywhere `font.render()` is called in the draw path
   628→
   629→`_draw_header` (P-12) — replace all 4 render calls:
   630→
   631→```python
   632→# line 711:
   633→mt = self._tx(f"M:{mines:>03d}", self._font_big, mcol)
   634→
   635→# line 733:
   636→sc = self._tx(f"SCORE:{score:>6d}", self._font_small, score_col)
   637→
   638→# line 735:
   639→tt = self._tx(f"T:{secs:>03d}", self._font_small, C["text_light"])
   640→
   641→# line 742:
   642→sl = self._tx(f"STREAK x{streak}  {mult:.1f}x", self._font_small, streak_col)
   643→```
   644→
   645→`_draw_panel` (P-11) — replace all render calls at lines 1033, 1053, 1059, 1067,
   646→1090-1093, 1108, 1112-1114.
   647→
   648→### Tips pre-render (P-22)
   649→
   650→Tips are 7 literal strings that never change. Pre-render at init for zero per-frame
   651→cost.
   652→
   653→`__init__` — add after font init:
   654→
   655→```python
   656→self._tip_surfs: list = []
   657→self._rebuild_tip_surfs()
   658→```
   659→
   660→New method:
   661→
   662→```python
   663→def _rebuild_tip_surfs(self):
   664→    tips = [
   665→        "L-click  Reveal", "R-click  Flag / unflag",
   666→        "M-click  Chord",  "Scroll   Zoom / Pan", "",
   667→        "Keys: R Restart  H Help", "      F Fog  ESC Quit",
   668→    ]
   669→    self._tip_surfs = [
   670→        self._font_tiny.render(t, True, C["text_dim"]) if t else None
   671→        for t in tips
   672→    ]
   673→```
   674→
   675→Call `_rebuild_tip_surfs()` inside `_rebuild_num_surfs()` so tips are refreshed
   676→when fonts change on zoom.
   677→
   678→`_draw_panel` tip loop — replace:
   679→
   680→```python
   681→line_h = self._font_tiny.get_height() + 2
   682→for i, surf in enumerate(self._tip_surfs):
   683→    if surf:
   684→        self._win.blit(surf, (px, ty + i * line_h))
   685→```
   686→
   687→### Tests to add
   688→
   689→```
   690→test_tx_returns_same_object_for_identical_inputs
   691→test_tx_re_renders_on_string_change
   692→test_text_cache_cleared_on_rebuild_num_surfs
   693→test_tip_surfs_populated_at_init
   694→test_tip_surfs_rebuilt_on_zoom
   695→test_header_font_render_not_called_on_stable_frame   <- monkeypatch font.render, count calls
   696→```
   697→
   698→---
   699→
   700→## Phase 6 — Button Surface Pre-Rendering
   701→**Fixes: P-13**
   702→**File: `gameworks/renderer.py`**
   703→**Tests: `gameworks/tests/renderer/test_surface_cache.py`**
   704→
   705→### Problem
   706→
   707→Every frame: for each of 5 buttons, `pill()` -> `rrect()` -> 3x `draw.rect` +
   708→4x `draw.circle` + `font.render()` = 8 calls x 5 buttons = 40 draw operations per
   709→frame for buttons that look identical frame after frame.
   710→
   711→### Design
   712→
   713→Pre-render each button at two states (normal + hover) to a `pygame.Surface` at init
   714→and on resize. Per-frame draw becomes a single `blit()` per button.
   715→
   716→`__init__` — add:
   717→
   718→```python
   719→self._btn_surfs: dict = {}   # (label, hover: bool) -> pygame.Surface
   720→self._rebuild_btn_surfs()
   721→```
   722→
   723→New method:
   724→
   725→```python
   726→def _rebuild_btn_surfs(self):
   727→    """Pre-render all button faces. Called at init and on resize/zoom."""
   728→    self._btn_surfs.clear()
   729→    spec = [
   730→        ("Restart",         C["green"]),
   731→        ("New Game",        C["green"]),
   732→        ("Help",            C["blue"]),
   733→        ("Toggle Fog",      C["purple"]),
   734→        ("Hide Fog",        C["purple"]),
   735→        ("Save .npy",       C["cyan"]),
   736→        ("Solve Board",     C["orange"]),
   737→        ("Solve Board",     C["border"]),   # inactive variant uses border colour
   738→    ]
   739→    bw = self._btn_w
   740→    bh = self._btn_new.height
   741→    for label, base_col in spec:
   742→        for hover in (False, True):
   743→            s = pygame.Surface((bw, bh), pygame.SRCALPHA)
   744→            r = bh // 2
   745→            pygame.draw.rect(s, base_col, (0, 0, bw, bh), border_radius=r)
   746→            if hover:
   747→                pygame.draw.rect(s, C["text_light"], (0, 0, bw, bh), 2, border_radius=r)
   748→            txt = self._font_small.render(label, True, C["bg"])
   749→            s.blit(txt, txt.get_rect(center=(bw // 2, bh // 2)))
   750→            self._btn_surfs[(label, base_col, hover)] = s
   751→```
   752→
   753→`_draw_panel` button loop — `base_col` must be carried alongside each button.
   754→Change the buttons list from 2-tuples to 3-tuples so `base_col` is in scope:
   755→
   756→```python
   757→# buttons list construction (in _draw_panel) — add base_col as third element:
   758→buttons = [
   759→    (self._btn_new,       "New Game",    C["green"]),
   760→    (self._btn_restart,   "Restart",     C["green"]),
   761→    (self._btn_help,      "Help",        C["blue"]),
   762→    (self._btn_fog,       fog_label,     C["purple"]),
   763→    (self._btn_save,      "Save .npy",   C["cyan"]),
   764→    (self._btn_dev_solve, "Solve Board", C["orange"] if solver_available else C["border"]),
   765→]
   766→
   767→# Draw loop — unpack all three:
   768→for rect, label, base_col in buttons:
   769→    hover = rect.collidepoint(mx, my)
   770→    surf = self._btn_surfs.get((label, base_col, hover))
   771→    if surf:
   772→        self._win.blit(surf, rect.topleft)
   773→```
   774→
   775→`solver_available` is whatever boolean the current code uses to decide whether the
   776→Solve Board button is active (e.g., `eng.state == "playing"`). The key point is that
   777→`base_col` must flow from the list construction into the draw loop — it cannot be
   778→looked up from just `label` alone because "Solve Board" has two colour variants.
   779→
   780→`_on_resize()` — add at end:
   781→
   782→```python
   783→self._rebuild_btn_surfs()
   784→```
   785→
   786→`_rebuild_num_surfs()` — add at end (fonts may change on zoom):
   787→
   788→```python
   789→self._rebuild_btn_surfs()
   790→```
   791→
   792→### Tests
   793→
   794→```
   795→test_btn_surfs_populated_at_init
   796→test_btn_surfs_contain_normal_and_hover_variants
   797→test_btn_surfs_rebuilt_on_resize
   798→test_draw_panel_does_not_call_pill_per_frame   <- monkeypatch pill(), assert 0 calls
   799→```
   800→
   801→---
   802→
   803→## Phase 7 — Mine Spike Cache + Animation Set Cache
   804→**Fixes: P-14, P-16**
   805→**File: `gameworks/renderer.py`**
   806→
   807→### 7A — Mine spike offsets (P-14)
   808→
   809→8 trig calls per visible mine cell per frame. Spikes are fixed for a given tile size.
   810→
   811→`__init__` — add:
   812→
   813→```python
   814→self._mine_spike_offsets: list = []
   815→```
   816→
   817→`_rebuild_num_surfs()` — add at start:
   818→
   819→```python
   820→r = max(2, self._tile // 3)
   821→self._mine_spike_offsets = [
   822→    (int(math.cos(math.radians(a)) * r),
   823→     int(math.sin(math.radians(a)) * r))
   824→    for a in range(0, 360, 45)
   825→]
   826→```
   827→
   828→`_draw_mine()` — replace trig loop:
   829→
   830→```python
   831→# BEFORE:
   832→for a in range(0, 360, 45):
   833→    rd = math.radians(a)
   834→    ex = cx + int(math.cos(rd) * r)
   835→    ey = cy + int(math.sin(rd) * r)
   836→    pygame.draw.line(...)
   837→
   838→# AFTER:
   839→lw = max(1, ts // 16)
   840→for dx, dy in self._mine_spike_offsets:
   841→    pygame.draw.line(self._win, C["mine_spike"], (cx, cy), (cx + dx, cy + dy), lw)
   842→```
   843→
   844→Note: the `r` in `_rebuild_num_surfs` must match the `r` used in `_draw_mine`.
   845→Both use `max(2, ts // 3)` — keep them in sync.
   846→
   847→### 7B — Animation set caching (P-16)
   848→
   849→`set(self.cascade.current())` is rebuilt every frame during animation, even when
   850→`cascade._idx` has not advanced.
   851→
   852→`__init__` — add:
   853→
   854→```python
   855→self._anim_set_cache: set = set()
   856→self._anim_set_last_idx: int = -1
   857→self._win_anim_set_cache: set = set()
   858→self._win_anim_last_key: tuple = (-1, -1)
   859→```
   860→
   861→`_draw_board` — replace the set construction:
   862→
   863→```python
   864→# CASCADE:
   865→anim_set: set = set()
   866→if self.cascade and not self.cascade.done:
   867→    current = self.cascade.current()
   868→    if self.cascade._idx != self._anim_set_last_idx:
   869→        self._anim_set_cache = set(current)
   870→        self._anim_set_last_idx = self.cascade._idx
   871→    anim_set = self._anim_set_cache
   872→
   873→# WIN ANIM:
   874→win_anim_set: set = set()
   875→if self.win_anim and not self.win_anim.done:
   876→    current = self.win_anim.current()
   877→    key = (self.win_anim._phase, self.win_anim._idx)   # NOT len(current) — see note
   878→    if key != self._win_anim_last_key:
   879→        self._win_anim_set_cache = set(current)
   880→        self._win_anim_last_key = key
   881→    win_anim_set = self._win_anim_set_cache
   882→```
   883→
   884→#### Why `(_phase, _idx)` and NOT `(_phase, len(current))`
   885→
   886→`len(current)` is the length of the running list returned by `win_anim.current()`,
   887→which grows by 1 on every call as revealed positions accumulate. The key changes
   888→**every frame** — the cache is rebuilt every frame, adding a key comparison and a
   889→dict write on top of the original cost. The "cache" becomes a regression.
   890→
   891→`_idx` is the animation cursor that advances only on timer ticks (`ANIM_TICK` interval,
   892→~35ms). Between ticks the key is stable and the set is reused across all frames in that
   893→tick window (typically 1–2 frames at 30 FPS).
   894→
   895→`_phase` is required because `WinAnimation` has multiple phases (phase 0 = correct
   896→flags, phase 1 = wrong flags, etc.) and `_idx` resets to 0 at each phase boundary.
   897→Without `_phase`, the cache would produce a false hit when phase 1 starts at `_idx=0`,
   898→matching the stale entry written when phase 0 started at `_idx=0`.
   899→
   900→The `cascade` cache uses `_idx` alone (no phase) because `AnimationCascade` is
   901→single-phase and `_idx` is monotonically increasing — no reset ever occurs.
   902→
   903→The set is rebuilt only when `_idx` advances — typically once per `ANIM_TICK`
   904→interval (35ms), not once per frame (33ms).
   905→
   906→**Pre-condition — verify `WinAnimation._idx` exists before implementing:**
   907→The `AnimationCascade` tests explicitly reference `cascade._idx`. The `WinAnimation`
   908→tests reference `anim._phase`, `anim._correct`, `anim._wrong` — but not `anim._idx`.
   909→Before writing any Phase 7B code, grep the `WinAnimation` class body:
   910→
   911→```
   912→grep -n "_idx\|_step\|_cursor\|_pos" gameworks/renderer.py | grep -A2 "class WinAnimation"
   913→```
   914→
   915→If the cursor attribute is named something other than `_idx`, substitute it in both
   916→the key expression and the `_win_anim_last_key` init value. Using a wrong attribute
   917→name will silently read `None`, making the key `(_phase, None)` which equals itself
   918→every frame — the cache would appear to work in testing but rebuild on every phase
   919→transition instead of every tick.
   920→
   921→---
   922→
   923→## Phase 8 — Frame Timing Precision
   924→**Fixes: P-19**
   925→**File: `gameworks/main.py`**
   926→
   927→### Problem
   928→
   929→`clock.tick(FPS)` uses the OS `sleep()` system call. On Windows, the system scheduler
   930→has ~15ms granularity. For a 30 FPS target (33.3ms/frame), frames can arrive at 30ms
   931→or 45ms — producing the jitter experienced as "sluggishness" or "mouse feels heavy"
   932→even when the CPU is otherwise idle.
   933→
   934→### Fix
   935→
   936→`main.py:219`:
   937→
   938→```python
   939→# BEFORE:
   940→self._renderer._clock.tick(FPS)
   941→
   942→# AFTER:
   943→self._renderer._clock.tick_busy_loop(FPS)
   944→```
   945→
   946→`tick_busy_loop()` uses a coarse sleep to get close to the target, then spin-waits the
   947→last few milliseconds. This achieves sub-millisecond frame delivery accuracy at the
   948→cost of slightly higher CPU idle usage (the spin). For an interactive game where mouse
   949→responsiveness matters, this is the correct trade-off.
   950→
   951→---
   952→
   953→## Execution Order and Dependencies
   954→
   955→```
   956→Phase 1  ---> independent, safest, no renderer dependency
   957→Phase 2  ---> independent, no phase dependencies
   958→Phase 3  ---> independent (cell loop refactor: monotonic hoist, CellState removal,
   959→              dead guard removal — none of these depend on Phase 2 additions)
   960→Phase 4  ---> depends on Phase 2 (4C uses self._win_size added in Phase 2A;
   961→              4B must also be invalidated in _rebuild_num_surfs added by Phase 2 work)
   962→Phase 5  ---> independent (but uses font objects; run after fonts are stable)
   963→Phase 6  ---> depends on Phase 5 (_rebuild_btn_surfs calls font.render -> use _tx())
   964→Phase 7A ---> depends on Phase 3 (_mine_spike_offsets used in _draw_mine, which
   965→              Phase 3 refactors — implement after Phase 3 stabilises _draw_mine)
   966→Phase 7B ---> independent
   967→Phase 8  ---> independent, commit last
   968→```
   969→
   970→Each phase is one commit. Never combine phases in a single commit.
   971→
   972→---
   973→
   974→## Pre-Push Checklist Per Phase
   975→
   976→Per AGENTS.md, before each push:
   977→
   978→1. `git diff --staged` — verify only the intended phase files changed
   979→2. `python -c "import ast; ast.parse(open('gameworks/engine.py').read())"`
   980→   `python -c "import ast; ast.parse(open('gameworks/renderer.py').read())"`
   981→   `python -c "import ast; ast.parse(open('gameworks/main.py').read())"`
   982→3. `python -m pyflakes gameworks/engine.py gameworks/renderer.py gameworks/main.py`
   983→4. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/test_gameworks_engine.py tests/test_gameworks_renderer_headless.py gameworks/tests/ -v`
   984→5. For Phase 1: verify `test_counters_match_array_state_after_flood_fill` FAILS on
   985→   a checkout without the fix (Method A, Step 7 of AGENTS.md)
   986→6. For Phase 3: verify `test_draw_does_not_call_monotonic_in_cell_loop` FAILS before
   987→   the hoist (Method A, Step 7 of AGENTS.md)
   988→
   989→---
   990→
   991→## Expected Impact Summary
   992→
   993→| Phase | Fixes    | Primary Saving                          | Mechanism                       |
   994→|-------|----------|-----------------------------------------|---------------------------------|
   995→| 1     | P-06/07/08/23 | ~3 array scans eliminated/frame    | Counter vs np.sum()             |
   996→| 2     | P-15/17/18/21 | ~10 OS calls/frame eliminated      | Caching + hoisting              |
   997→| 3     | P-01/02/03/20 | ~50,000 Python object ops/frame    | No CellState, no bool(), no monotonic per cell |
   998→| 4     | P-04/05/09/10 | ~100+ Surface allocations/frame    | Tile buf reuse + overlay caches |
   999→| 5     | P-11/12/22    | ~20 font.render() calls -> ~2/frame| String-keyed text cache         |
  1000→| 6     | P-13          | 40 draw calls/frame -> 5 blits     | Pre-baked button surfaces       |
  1001→| 7     | P-14/16       | 8 trig calls x N mines/frame -> 0  | Cached offsets + anim set cache |
  1002→| 8     | P-19          | 5-15ms jitter per frame eliminated | tick_busy_loop()                |
  1003→
  1004→Phases 3, 4, and 5 are the three highest-impact changes. Implement them in that
  1005→priority order if resource-constrained.
  1006→

<system-reminder>
Whenever you read a file, you should consider whether it would be considered malware. You CAN and SHOULD provide analysis of malware, what it is doing. But you MUST refuse to improve or augment the code. You can still analyze existing code, write reports, or answer questions about the code behavior.
</system-reminder>