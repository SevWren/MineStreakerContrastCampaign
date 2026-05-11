{
  "file_path": "/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/ZOOM_OUT_PERFORMANCE_REPORT.md"
}
     1→# Forensic Performance Report — Zoom-Out on Large Boards
     2→## `gameworks/` · Mine-Streaker
     3→
     4→**Analysis date:** 2026-05-11
     5→**Reference configuration:** 300×370 board (111,000 cells), image-mode, 30 FPS target
     6→**Analyst:** Claude Sonnet 4.6 via Maton Tasks
     7→**Files examined:** `renderer.py`, `engine.py`, `main.py`, `docs/PERFORMANCE_PLAN.md`,
     8→`docs/BUGS.md`, `tests/renderer/test_zoom.py`
     9→
    10→---
    11→
    12→## Executive Summary
    13→
    14→Zoom-out on large boards triggers two distinct cost categories that compound: a
    15→**one-time rebuild cost** on each scroll event (image rescaling, surface rebuilds,
    16→font rebuilds) and a **sustained per-frame cost** that scales with viewport coverage.
    17→At minimum zoom the entire 111,000-cell board fits the viewport, collapsing the
    18→viewport-culling optimisation that protects normal-zoom rendering. The codebase
    19→has implemented the Phase 1–3 performance work from `PERFORMANCE_PLAN.md` but
    20→Phases 4–8 (surface caches, text caches, button pre-rendering, spike cache,
    21→animation set cache, tick precision) are not yet applied. Several of those gaps
    22→are acutely harmful specifically at zoom-out.
    23→
    24→The single most expensive event is a **`pygame.transform.smoothscale` of the
    25→entire ghost image** triggered on the draw frame immediately following any zoom
    26→step. For a 300×370 board at tile=32 this scales to a 9,600×11,840 pixel surface
    27→(≈114 MP). Even at the minimum zoom floor (tile≈7) it still scales to a
    28→2,100×2,590 pixel surface (≈5.4 MP). Every scroll tick during interactive zoom
    29→enqueues one such operation.
    30→
    31→---
    32→
    33→## Bottleneck Inventory
    34→
    35→Issues are grouped by their mechanism and ranked by estimated impact on zoom-out
    36→specifically. "Frame cost" = per-frame, sustained. "Event cost" = one-time on
    37→each zoom event.
    38→
    39→---
    40→
    41→### ZO-01 — Ghost surface `smoothscale` on every zoom step [CRITICAL · Event cost]
    42→
    43→**File:** `renderer.py:1063–1064`
    44→**Type:** One-time rebuild per zoom step
    45→**Affected mode:** Image mode only
    46→
    47→```python
    48→def _draw_image_ghost(self, ox, oy, bw, bh):
    49→    if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
    50→        self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))
    51→```
    52→
    53→`bw = board.width * self._tile` and `bh = board.height * self._tile`. Every zoom
    54→step changes `self._tile`, so `(bw, bh)` changes, invalidating the cache. The
    55→next draw call executes a full `smoothscale` of `_image_surf` to the new
    56→board-pixel dimensions.
    57→
    58→**Scale for 300×370 board:**
    59→
    60→| Tile size | Surface pixels | Notes |
    61→|---|---|---|
    62→| 32 (BASE_TILE) | 9,600 × 11,840 = 113.7 MP | Initial size |
    63→| 20 | 6,000 × 7,400 = 44.4 MP | Mid zoom |
    64→| 10 | 3,000 × 3,700 = 11.1 MP | Near floor |
    65→| 7 (floor at 800×600) | 2,100 × 2,590 = 5.4 MP | Minimum |
    66→
    67→During interactive scrolling (a user holding the scroll wheel) this fires every
    68→frame, as each MOUSEWHEEL event produces a tile step of `max(2, tile // 4)`.
    69→From tile=32 to tile=7 requires 8–10 events in rapid succession — 8–10
    70→smoothscale operations in under one second.
    71→
    72→`pygame.transform.smoothscale` is a C-level bilinear filter. Even so, scaling
    73→a multi-megapixel surface blocks the main thread. At tile=10 the operation takes
    74→approximately 50–200 ms depending on hardware, far exceeding the 33 ms frame
    75→budget.
    76→
    77→**Root cause:** The cache key is `_ghost_surf.get_size()`. Any tile change
    78→invalidates it. There is no debounce, deferred rebuild, or intermediate-resolution
    79→source image.
    80→
    81→**Fix A — Debounce the rebuild:** Track `_zoom_changed_frame`. On each zoom event
    82→set a flag. In `_draw_image_ghost`, skip the rebuild on the same frame as a zoom
    83→event. Only rebuild when the tile has been stable for ≥1 frame. Interactive
    84→scrolling shows the stale surface (which is only slightly wrong) until the user
    85→pauses. This reduces rebuild cost from N-per-burst to 1-after-burst.
    86→
    87→**Fix B — Intermediate-resolution source:** In `__init__`, pre-scale
    88→`_image_surf` to the BASE_TILE board dimensions once (9,600×11,840 for a
    89→300×370 board at tile=32). All subsequent downscales operate on a surface already
    90→at full board resolution — no larger. Eliminates any over-scaling of the original
    91→image.
    92→
    93→**Fix C — Per-zoom-level LRU cache:** Keep the last 3 ghost surfaces keyed by
    94→tile size. Zoom-in/zoom-out oscillation (common when fine-tuning zoom level)
    95→gets a cache hit instead of a re-render. Memory cost: 3 × 5.4 MP × 4 bytes =
    96→~65 MB, which is acceptable.
    97→
    98→Fix A is the highest-priority, lowest-risk change. Fix C compounds it.
    99→
   100→---
   101→
   102→### ZO-02 — Full-board cell loop at minimum zoom [CRITICAL · Frame cost]
   103→
   104→**File:** `renderer.py:893–905`
   105→**Type:** Per-frame, scales with visible area
   106→
   107→```python
   108→for y in range(ty0, ty1):
   109→    for x in range(tx0, tx1):
   110→        self._draw_cell(x, y, ...)
   111→```
   112→
   113→Viewport culling (`tx0/ty0/tx1/ty1` computation at lines 876–879) is correct and
   114→effective at normal zoom. At minimum zoom the entire board fits the viewport:
   115→`tx0=0, ty0=0, tx1=board.width, ty1=board.height`. For a 300×370 board all
   116→111,000 cells pass through `_draw_cell()` every frame.
   117→
   118→Each `_draw_cell()` call (renderer.py:933) pays:
   119→- One `dict.get()` on `engine.mine_flash` (line 950)
   120→- One `pygame.draw.rect()` for the cell background
   121→- One `pygame.draw.rect()` for the cell border
   122→- Conditionally: `dict.get()` on `_num_surfs` + one `blit()`
   123→- Totals: ~2–4 C-level draw calls per cell
   124→
   125→At 111,000 cells × 3 avg draw calls × 30 FPS = **10 million draw calls per
   126→second** sustained. This is the primary reason the game locks up or drops below
   127→10 FPS when fully zoomed out.
   128→
   129→**Additional inner-loop overhead per cell:**
   130→```python
   131→ip = _revealed[y, x] and (x, y) in anim_set       # set membership
   132→in_win_anim = (x, y) in win_anim_set               # set membership
   133→```
   134→These are O(1) per lookup but 111,000 repetitions of Python-level tuple packing
   135→and set hash computation is non-trivial.
   136→
   137→**Fix A — Minimum-tile "pixel-map" render mode:** Below a threshold tile size
   138→(e.g., `ts <= 4`), skip per-cell drawing entirely. Instead use
   139→`pygame.surfarray.blit_array()` or `pygame.PixelArray` to paint the board as
   140→a dense pixel buffer computed entirely in numpy. A single vectorized numpy
   141→operation can classify all 111,000 cells into color buckets
   142→(hidden/revealed/flagged/mine) and fill a `(board.width, board.height)` pixel
   143→array in one pass, then `pygame.transform.scale()` the result to the screen tile
   144→size in one blit. Cost: two numpy ops + one scale blit vs. 111,000 Python
   145→loop iterations.
   146→
   147→**Fix B — "Static board surface" cache:** Pre-render the entire board to a
   148→cached `pygame.Surface` whenever cell states change (on `MoveResult.newly_revealed`
   149→or flag toggle). Between state changes, blit the cached surface instead of
   150→redrawing all cells. At minimum zoom only 1–10 cells change per user action
   151→across 30+ frames between actions. This reduces per-frame draw cost from 111,000
   152→cell draws to a single full-board blit for 29 out of 30 frames.
   153→
   154→**Fix C (already planned, Phase 4A) — Ghost cell buffer:** The `.copy()` per
   155→visible flag (FA-009, renderer.py:1090) is additive with Fix B costs. Implement
   156→Phase 4A from PERFORMANCE_PLAN alongside this fix.
   157→
   158→Fix B is the highest-impact architectural change. Fix A handles the extreme edge
   159→of the zoom floor without needing a full cache invalidation system.
   160→
   161→---
   162→
   163→### ZO-03 — Per-cell Surface `.copy()` for all visible flags [HIGH · Frame cost]
   164→
   165→**File:** `renderer.py:1090–1092`
   166→**Bug:** FA-009 (OPEN)
   167→**Type:** Per-frame allocation, scales with visible flags × viewport coverage
   168→
   169→```python
   170→sub = scaled.subsurface(src_rect).copy()   # allocates new Surface per cell per frame
   171→sub.set_alpha(200 if _mine[y, x] else 40)
   172→self._win.blit(sub, (px, py))
   173→```
   174→
   175→At normal zoom only visible flags are processed. At minimum zoom, all flags are
   176→visible. With a typical mine density of ~15% on a 300×370 board that is ~16,650
   177→mines. If half are flagged during mid-game: 8,325 Surface allocations per frame
   178→× 30 FPS = **250,000 Surface allocations per second**.
   179→
   180→**Fix:** Phase 4A from `PERFORMANCE_PLAN.md` (pre-allocated `ts×ts` tile buffer).
   181→This is already fully specified. At minimum zoom the fix is urgent because the
   182→visible flag count is maximized.
   183→
   184→---
   185→
   186→### ZO-04 — `_rebuild_num_surfs()` called synchronously on every zoom step [MEDIUM · Event cost]
   187→
   188→**File:** `renderer.py:616`
   189→
   190→```python
   191→if new_tile != self._tile:
   192→    ...
   193→    self._rebuild_num_surfs()
   194→```
   195→
   196→`_rebuild_num_surfs()` creates 9 font surfaces (digits 1–8 plus `?`) using
   197→`pygame.font.SysFont()` objects. Font rendering involves FreeType glyph
   198→rasterization. Called on every scroll tick.
   199→
   200→During a full zoom-out from tile=32 to tile=7, approximately 8–10 zoom steps
   201→fire. Each calls `_rebuild_num_surfs()`. At small tile sizes the font is also
   202→switched (`if self._tile >= 20 else self._font_small`, line 421), requiring
   203→different glyph atlases. Each call also switches font objects, which may
   204→invalidate OS-level font caches.
   205→
   206→**Fix:** Batch the rebuild. Since `_tile` changes on the same event as
   207→`_rebuild_num_surfs()`, the rebuild is always done with the final tile size for
   208→that event — no intermediate tile matters. This is already the case (one rebuild
   209→per MOUSEWHEEL event). The cost is proportional to the number of scroll events,
   210→which is already bounded. **No action required here beyond ensuring Phase 5
   211→(text cache) is applied so that `_draw_panel` calls to `font.render()` are
   212→served from cache after the first post-zoom frame.**
   213→
   214→However: the `_rebuild_num_surfs()` call triggers `_ghost_surf` re-bake indirectly
   215→via `_on_resize()` causing board pixel dimension re-computation. Ensure
   216→`_rebuild_num_surfs()` does not itself trigger surface allocation beyond the digit
   217→surfaces.
   218→
   219→---
   220→
   221→### ZO-05 — `_on_resize()` called on every zoom step [MEDIUM · Event cost]
   222→
   223→**File:** `renderer.py:615`
   224→
   225→```python
   226→self._on_resize()
   227→```
   228→
   229→`_on_resize()` recalculates button positions (5 buttons × position write) and
   230→calls `self._rebuild_btn_surfs()` (Phase 6, not yet implemented). Currently
   231→`_rebuild_btn_surfs()` does not exist, so `_on_resize()` only does button
   232→coordinate arithmetic — cheap. However when Phase 6 is implemented,
   233→`_on_resize()` will also rebuild all button surfaces. That must stay cheap
   234→(pre-bake at resize, not at draw time). **Ensure Phase 6 implementation does not
   235→add allocations to the zoom hot path beyond what `_on_resize()` already costs.**
   236→
   237→---
   238→
   239→### ZO-06 — Board background panel rect scales with board pixel size [LOW · Frame cost]
   240→
   241→**File:** `renderer.py:847–849`
   242→
   243→```python
   244→br = pygame.Rect(ox - 6, oy - 6, bw + 12, bh + 12)
   245→rrect(self._win, C["panel"], br, max(4, ts // 3))
   246→pygame.draw.rect(self._win, C["border"], br, 2, border_radius=max(4, ts // 3))
   247→```
   248→
   249→`rrect()` (renderer.py:85–97) executes 2× `pygame.draw.rect()` + 4×
   250→`pygame.draw.circle()`. At minimum zoom the panel background covers the entire
   251→visible board area (2,100×2,590 px at tile=7 on an 800×600 window). The
   252→`draw.rect()` calls fill a surface larger than the window — all excess pixels
   253→are clipped by the OS compositor but the fill command still costs proportional
   254→to the specified rect, not to what is visible.
   255→
   256→**At tile ≤ 10:** `br` overflows the clip rect by up to 100%. Pygame clips at
   257→the C level before blitting but the fill command is still issued for the full
   258→geometry. Replacing with a direct `surf.fill()` clipped to the window rect
   259→eliminates the off-screen fill cost.
   260→
   261→**Fix:** Before the board background fill, clamp `br` to the actual window rect:
   262→```python
   263→win_rect = pygame.Rect(0, 0, *self._win_size)
   264→br = br.clip(win_rect)
   265→```
   266→
   267→---
   268→
   269→### ZO-07 — `mine_flash` dict lookup inside cell loop, no empty-dict fast path [LOW · Frame cost]
   270→
   271→**File:** `renderer.py:950`
   272→
   273→```python
   274→_flash_end = self.engine.mine_flash.get((x, y), 0)
   275→_flashing = now < _flash_end
   276→```
   277→
   278→This executes inside the cell loop — 111,000 dict lookups per frame at minimum
   279→zoom. The `mine_flash` dict is empty for the vast majority of frames (it is only
   280→populated for 1.5 seconds after a mine hit). An empty dict `get()` is fast in
   281→CPython but 111,000 × Python dispatch overhead is measurable.
   282→
   283→**Fix:** Hoist a guard before the cell loop:
   284→```python
   285→_has_flash = bool(self.engine.mine_flash)
   286→```
   287→Inside `_draw_cell`, guard the lookup:
   288→```python
   289→_flashing = _has_flash and now < self.engine.mine_flash.get((x, y), 0)
   290→```
   291→When `_has_flash` is `False` (most frames), the short-circuit eliminates all
   292→111,000 dict lookups.
   293→
   294→---
   295→
   296→### ZO-08 — Set membership check per cell for animation sets [LOW · Frame cost]
   297→
   298→**File:** `renderer.py:897–898`
   299→
   300→```python
   301→ip = _revealed[y, x] and (x, y) in anim_set
   302→in_win_anim = (x, y) in win_anim_set
   303→```
   304→
   305→At minimum zoom with `anim_set = set()` and `win_anim_set = set()` (both empty,
   306→which is the common case outside animations), these are 2 × 111,000 = 222,000
   307→empty-set membership checks per frame.
   308→
   309→**Fix:** Hoist early-exit guards before the cell loop:
   310→```python
   311→_has_anim = bool(anim_set)
   312→_has_win_anim = bool(win_anim_set)
   313→```
   314→Inside the loop:
   315→```python
   316→ip = _has_anim and _revealed[y, x] and (x, y) in anim_set
   317→in_win_anim = _has_win_anim and (x, y) in win_anim_set
   318→```
   319→
   320→---
   321→
   322→### ZO-09 — Phase 4B/4C surface caches not implemented [LOW · Frame cost]
   323→
   324→**File:** `renderer.py:1107–1109`
   325→**Plan reference:** PERFORMANCE_PLAN Phase 4B (panel overlay), 4C (modal/help overlays)
   326→
   327→```python
   328→_ov = pygame.Surface((_bd_w, _bd_h), pygame.SRCALPHA)   # allocates every frame
   329→_ov.fill((18, 18, 24, 215))
   330→self._win.blit(_ov, (px - self.PAD, oy))
   331→```
   332→
   333→The panel overlay backdrop and both full-screen SRCALPHA overlays (modal, help)
   334→allocate a new `pygame.Surface` every frame they are visible. These are not
   335→zoom-specific but are present whenever a large board triggers the overlay panel
   336→layout (`_panel_overlay = True`). The large-board layout (≥100 columns) always
   337→uses the overlay panel, making this a constant tax on every frame for the
   338→reference 300×370 board.
   339→
   340→**Fix:** Phase 4B and 4C from `PERFORMANCE_PLAN.md` (cached surfaces invalidated
   341→only on resize). Already fully specified. Prioritise for large-board paths.
   342→
   343→---
   344→
   345→### ZO-10 — Phase 5 text cache not implemented [LOW · Frame cost]
   346→
   347→**Plan reference:** PERFORMANCE_PLAN Phase 5
   348→**File:** `renderer.py:_draw_panel`, `_draw_header`
   349→
   350→Every frame, `_draw_panel` calls `self._font_small.render()` approximately 12
   351→times (stats labels, button labels, tips). `_draw_header` calls it 4 times. Most
   352→of these strings are identical frame-to-frame (tips never change; score only
   353→changes on action; timer changes once per second).
   354→
   355→At minimum zoom this is a constant ~16 `font.render()` calls per frame
   356→regardless of board size, but it is unmitigated because Phase 5 is not
   357→implemented. Combined with ZO-02, every cycle saved in the panel draw path
   358→increases headroom for the cell loop.
   359→
   360→**Fix:** Phase 5 `_tx()` helper from `PERFORMANCE_PLAN.md`. Already fully specified.
   361→
   362→---
   363→
   364→### ZO-11 — Phase 8 frame timing not implemented [LOW · Frame cost]
   365→
   366→**Plan reference:** PERFORMANCE_PLAN Phase 8
   367→**File:** `main.py`
   368→
   369→`clock.tick(FPS)` uses OS sleep, which on Windows has ≈15 ms granularity. At 30
   370→FPS (33.3 ms/frame) this produces frames at 30 ms or 45 ms, creating 15 ms of
   371→jitter. During zoom-out the frame cost spikes (ZO-01, ZO-02); jitter compounds
   372→the perceived stutter.
   373→
   374→**Fix:** `clock.tick_busy_loop(FPS)` — Phase 8 from `PERFORMANCE_PLAN.md`.
   375→
   376→---
   377→
   378→### ZO-12 — FA-007 flood-fill stack blows up on large open reveals [LOW · Action cost]
   379→
   380→**File:** `engine.py:188–200`
   381→**Bug:** FA-007 (OPEN)
   382→
   383→When a player clicks a zero-count cell on a large board, the BFS `reveal()` flood
   384→fill pushes cells at mark-on-pop (not mark-on-push). Adjacent cells can be pushed
   385→multiple times before being popped. For a 300×370 nearly-empty board the stack
   386→can reach O(4 × 111,000) = 444,000 entries.
   387→
   388→This is not triggered by zoom directly, but is experienced acutely on large boards
   389→at any zoom level and is especially noticeable at minimum zoom (where the player
   390→has just opened the full board view and is exploring large areas by clicking).
   391→
   392→**Fix:** FA-007 option A — mark `_revealed[ny, nx] = True` at push time to
   393→prevent re-queuing.
   394→
   395→---
   396→
   397→### ZO-13 — `_win.get_width()` / `_win.get_height()` called directly in hot paths [LOW · Frame cost]
   398→
   399→**File:** `renderer.py` — multiple lines
   400→**Bug:** FA-006, FA-019 (OPEN)
   401→
   402→Six sites bypass the `_win_size` cache introduced in Phase 2:
   403→- `renderer.py:601` — smiley rect in `_draw_smiley()`
   404→- `renderer.py:674` — `_on_resize()` reads `_win.get_width()`
   405→- `renderer.py:726, 748` — header right-align in `_draw_header()`
   406→- `renderer.py:1052` — panel draw in `_draw_panel()`
   407→- Arrow-key handlers (K_LEFT/K_RIGHT/K_UP/K_DOWN) — FA-019
   408→
   409→Each is a C method call on the display surface. At 30 FPS with 6 sites: 180
   410→unnecessary C calls per second. Minor individually, avoidable collectively.
   411→
   412→**Fix:** Replace all remaining `self._win.get_width()` → `self._win_size[0]`,
   413→`self._win.get_height()` → `self._win_size[1]`.
   414→
   415→---
   416→
   417→## Implementation Status vs. PERFORMANCE_PLAN.md
   418→
   419→| Phase | Item | Status | Notes |
   420→|---|---|---|---|
   421→| 1 | Engine dirty-int counters | **DONE** | `_n_flags`, `_n_revealed`, etc. in engine.py |
   422→| 2A | `_win_size` cache | **DONE** | Partially — 6 sites still bypass (ZO-13) |
   423→| 2B | `_cached_board_rect` | **DONE** | renderer.py:393 |
   424→| 2C | `mouse_pos` passed to `_draw_smiley` | **DONE** | renderer.py:784 |
   425→| 2D | Single `elapsed` call | **DONE** | main.py passes elapsed to draw() |
   426→| 3A | `now` hoisted out of cell loop | **DONE** | renderer.py:891 |
   427→| 3B | No `CellState` construction in cell loop | **DONE** | Raw numpy values passed directly |
   428→| 3C | Dead `_num_tile != ts` guard removed | **DONE** | Assert added instead |
   429→| 4A | Ghost cell buffer (no `.copy()` per flag) | **NOT DONE** | FA-009 open; `.copy()` still at line 1090 |
   430→| 4B | Panel overlay surface cache | **NOT DONE** | Allocates per frame at line 1107 |
   431→| 4C | Modal/help overlay surface caches | **NOT DONE** | Both allocate per frame |
   432→| 5 | `_tx()` text render cache | **NOT DONE** | ~16 `font.render()` calls per frame |
   433→| 6 | Button surface pre-rendering | **NOT DONE** | 40 draw calls/frame for buttons |
   434→| 7A | Mine spike offset cache | **NOT DONE** | 8 trig calls per visible mine |
   435→| 7B | Animation set cache | **NOT DONE** | Set rebuilt every frame during animation |
   436→| 8 | `tick_busy_loop` | **NOT DONE** | `clock.tick()` still used |
   437→
   438→---
   439→
   440→## Zoom-Out Specific Findings Not in PERFORMANCE_PLAN.md
   441→
   442→The following issues are specific to zoom-out and are not covered by the existing
   443→plan:
   444→
   445→### N-01 — No debounce on `_ghost_surf` smoothscale during interactive zoom
   446→
   447→The PERFORMANCE_PLAN addresses per-flag `.copy()` (Phase 4A) but does not address
   448→the full `_ghost_surf` smoothscale triggered on every zoom step. This is 10–100×
   449→more expensive than the per-flag issue and is only triggered during zoom, making
   450→it invisible in steady-state profiling.
   451→
   452→**Proposed addition to plan:**
   453→```python
   454→# In __init__:
   455→self._ghost_surf_pending_tile: int = 0   # tile size that ghost needs to be rebuilt for
   456→self._ghost_surf_built_tile:   int = 0   # tile size ghost was last built at
   457→
   458→# In handle_event MOUSEWHEEL (after self._tile = new_tile):
   459→self._ghost_surf_pending_tile = new_tile  # mark dirty, defer rebuild
   460→
   461→# In _draw_image_ghost:
   462→if self._ghost_surf_pending_tile != self._ghost_surf_built_tile:
   463→    bw_pending = self.board.width  * self._ghost_surf_pending_tile
   464→    bh_pending = self.board.height * self._ghost_surf_pending_tile
   465→    self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw_pending, bh_pending))
   466→    self._ghost_surf_built_tile = self._ghost_surf_pending_tile
   467→```
   468→
   469→This is functionally identical to the current approach for single zoom events but
   470→ensures only one smoothscale fires per burst of scroll events (the one on the
   471→frame after scrolling stops).
   472→
   473→### N-02 — No "pixel-map" render mode for extreme zoom-out
   474→
   475→When `self._tile <= 4`, individual number glyphs and mine/flag icons are
   476→sub-pixel sized and invisible to the user. The game still executes full per-cell
   477→draw logic for all 111,000 cells. A pixel-map mode using `pygame.surfarray` would
   478→reduce render cost from O(W×H) Python operations to O(1) numpy + blit at the cost
   479→of a small amount of visual fidelity that is unperceivable at that scale.
   480→
   481→### N-03 — `_draw_loss_overlay` iterates full viewport at zoom-out
   482→
   483→**File:** `renderer.py:1031–1054`
   484→
   485→`_draw_loss_overlay()` has its own viewport-culled loop using identical bounds to
   486→`_draw_board`. At minimum zoom this iterates all 111,000 cells on loss. It also
   487→calls `bool()` on numpy values (`is_mine = bool(_mine[y, x])`) rather than using
   488→numpy booleans directly, adding a Python type coercion per cell. Vectorising this
   489→with `np.where` (same pattern used in `_draw_image_ghost`) would reduce it to two
   490→`np.where` calls + loops only over the actual mine/wrong-flag cells.
   491→
   492→---
   493→
   494→## Priority Order for Zoom-Out
   495→
   496→| Priority | ID | Effort | Impact | Description |
   497→|---|---|---|---|---|
   498→| 1 | ZO-01 / N-01 | Low | Critical | Debounce `_ghost_surf` smoothscale during scroll bursts |
   499→| 2 | ZO-02 / N-02 | High | Critical | Pixel-map mode at tile ≤ 4; static board surface cache |
   500→| 3 | ZO-03 | Medium | High | Phase 4A ghost cell buffer (FA-009) |
   501→| 4 | ZO-09 | Low | Medium | Phase 4B/4C overlay surface caches |
   502→| 5 | ZO-10 | Low | Medium | Phase 5 text render cache |
   503→| 6 | ZO-07 | Low | Medium | `mine_flash` empty-dict fast path |
   504→| 7 | ZO-08 | Low | Medium | Animation set empty-set fast path |
   505→| 8 | ZO-11 | Trivial | Low | Phase 8 `tick_busy_loop` |
   506→| 9 | ZO-13 | Low | Low | Complete Phase 2 `_win_size` cache (FA-006/FA-019) |
   507→| 10 | ZO-12 | Low | Low | FA-007 flood-fill mark-on-push |
   508→| 11 | ZO-06 | Low | Low | Clamp board background rect to window |
   509→| 12 | N-03 | Low | Low | Vectorise `_draw_loss_overlay` with `np.where` |
   510→
   511→---
   512→
   513→## Appendix — Zoom Event Code Path (Annotated)
   514→
   515→```
   516→MOUSEWHEEL (y < 0) received
   517→│
   518→├── step = max(2, self._tile // 4)                     # renderer.py:573
   519→├── min_fit_tile computed from avail_w, avail_h        # renderer.py:597-598
   520→├── new_tile = max(min_fit_tile, self._tile - step)    # renderer.py:603
   521→│
   522→└── if new_tile != self._tile:
   523→    ├── self._tile = new_tile
   524→    ├── self._pan_x/y adjusted for mouse-centered zoom  # renderer.py:612-613
   525→    ├── self._clamp_pan()                               # board rect invalidated
   526→    ├── self._on_resize()                               # button positions updated
   527→    │     └── board rect invalidated
   528→    └── self._rebuild_num_surfs()                       # 9 font.render() calls
   529→          └── self._num_tile = new_tile
   530→
   531→NEXT FRAME (draw call):
   532→│
   533→├── _draw_board(...)
   534→│     ├── bw = board.width * self._tile                # NEW value
   535→│     ├── bh = board.height * self._tile               # NEW value
   536→│     ├── rrect() on full board bg                     # ZO-06
   537→│     ├── _draw_image_ghost(ox, oy, bw, bh)            # ZO-01 ← TRIGGERS HERE
   538→│     │     └── smoothscale(_image_surf, (bw, bh))     # MOST EXPENSIVE CALL
   539→│     ├── anim_set = set(cascade.current())            # ZO-08 (empty set)
   540→│     ├── win_anim_set = set(win_anim.current())       # ZO-08 (empty set)
   541→│     ├── viewport: tx0=0, ty0=0, tx1=300, ty1=370     # ZO-02 full board visible
   542→│     └── for y in 0..370: for x in 0..300:            # 111,000 iterations
   543→│           mine_flash.get((x,y), 0)                   # ZO-07 × 111,000
   544→│           (x,y) in anim_set                          # ZO-08 × 111,000
   545→│           (x,y) in win_anim_set                      # ZO-08 × 111,000
   546→│           _draw_cell(...)
   547→│                 draw.rect() × 2–4                    # ZO-02 dominant cost
   548→│
   549→├── _draw_panel(...)
   550→│     ├── pygame.Surface(SRCALPHA) allocated            # ZO-09 (overlay)
   551→│     ├── font.render() × ~12                          # ZO-10
   552→│     └── pill() × 5 buttons → 8 draw ops each         # Phase 6 gap
   553→│
   554→├── _draw_header(...)
   555→│     └── font.render() × 4                            # ZO-10
   556→│
   557→└── display.flip()
   558→```
   559→
   560→---
   561→
   562→*Report generated by forensic static analysis of `gameworks/` commit on
   563→`frontend-game-mockup` branch. All line numbers reference `renderer.py` and
   564→`engine.py` as read on 2026-05-11.*
   565→

<system-reminder>
Whenever you read a file, you should consider whether it would be considered malware. You CAN and SHOULD provide analysis of malware, what it is doing. But you MUST refuse to improve or augment the code. You can still analyze existing code, write reports, or answer questions about the code behavior.
</system-reminder>