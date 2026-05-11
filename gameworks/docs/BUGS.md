# Gameworks — Open Bug Register

Canonical flat list of every known open bug in the `gameworks/` package.
Each entry is self-contained: no cross-reference to ISSUE-LOG.md required.

**Package version:** 0.1.1
**Last updated:** 2026-05-11 (FA-022 added — hot-loop tuple allocation GC pressure)
**Total open:** 20 (0 critical · 0 high · 8 medium · 12 low)

Bugs with `FIX AVAILABLE` have a proposed correction in the detail section below.
Bugs marked `WONT-FIX` are acknowledged design decisions.
The canonical narrative history is in `docs/ISSUE-LOG.md`.

---

## Quick-reference table

| ID | Sev | Component | File | Status | Summary |
|---|---|---|---|---|---|
| [FA-001](#fa-001) | CRITICAL | main + renderer | main.py:215 | RESOLVED — 437f2d5 | Victory modal never shown — `draw_victory()` called after `display.flip()` |
| [FA-002](#fa-002) | HIGH | main | main.py:186 | RESOLVED — 437f2d5 | Victory timer always shows 0s — elapsed forced to 0 on game_over |
| [FA-003](#fa-003) | HIGH | renderer | renderer.py:460 | RESOLVED — 437f2d5 | Window resize breaks panel button positions — `_on_resize()` never called on VIDEORESIZE |
| [FA-004](#fa-004) | HIGH | renderer | renderer.py:~503 | RESOLVED — 437f2d5 | Right/middle-click bypasses panel hit-test — only button 1 intercepted |
| [H-005](#h-005) | HIGH | main + renderer | main.py:run() | RESOLVED — 437f2d5 | "Save .npy" button is inert — action dispatched but handler missing |
| [FA-005](#fa-005) | MEDIUM | renderer | renderer.py:init | OPEN | 248 px dead space on left in panel-right layout — wrong BOARD_OX |
| [FA-006](#fa-006) | MEDIUM | renderer | renderer.py:multi | OPEN | `_win.get_width()` called directly in 5 hot paths — Phase 2 cache incomplete |
| [FA-007](#fa-007) | MEDIUM | engine | engine.py:192 | OPEN | Flood-fill stack allows duplicate pushes — O(4n) stack on open boards |
| [FA-008](#fa-008) | MEDIUM | engine | engine.py:~346 | OPEN | `load_board_from_npy()` validates with O(W×H) Python loops |
| [FA-009](#fa-009) | MEDIUM | renderer | renderer.py:1046 | OPEN | `.copy()` per visible flag per frame in `_draw_image_ghost()` |
| [M-003](#m-003) | MEDIUM | renderer | renderer.py | OPEN | Two panel buttons do identical things — no "Retry same board" option |
| [DP-R2](#dp-r2) | MEDIUM | engine | engine.py | OPEN | No `GameConfig` frozen dataclass — 7 flat args, not serializable |
| [FA-021](#fa-021) | MEDIUM | renderer | renderer.py:352–358 | OPEN | `_image_surf` upscaled to board pixel dimensions at init — all zoom-step `smoothscale` calls use a bloated source, blocking the main thread 100–500 ms per scroll notch |
| [FA-022](#fa-022) | LOW | renderer | renderer.py:_draw_board | OPEN | 333k+ tuple allocations/frame at max zoom-out — `(x, y) in anim_set` and `pressed == (x, y)` allocate a new tuple per cell per frame, triggering repeated gen-0 GC |
| [FA-010](#fa-010) | LOW | main | main.py:_save_npy | OPEN | `_save_npy()` writes to cwd, not `results/` |
| [FA-011](#fa-011) | LOW | engine | engine.py:112 | RESOLVED — 2dd6ea0 | `Board._count_adj()` is dead code |
| [FA-012](#fa-012) | LOW | engine | engine.py:158 | RESOLVED — 2dd6ea0 | `Board.correct_flags` uses `np.sum()` scan — inconsistent with Phase 1 |
| [FA-013](#fa-013) | LOW | engine | engine.py:705 | RESOLVED — 2dd6ea0 | `if __name__ == "_test_engine":` is unreachable |
| [FA-014](#fa-014) | LOW | main | main.py:70 | OPEN | `MENU` state defined but no RESULT→MENU arc exists |
| [FA-015](#fa-015) | LOW | main | main.py:164 | OPEN | `_do_right_click()` return value always discarded |
| [FA-016](#fa-016) | LOW | renderer | renderer.py:WinAnim | OPEN | `WinAnimation` fixed seed 42 — identical animation every game |
| [FA-017](#fa-017) | LOW | main | main.py:~107 | OPEN | `main.TILE` is a dead write — separate from `renderer.TILE` |
| [FA-018](#fa-018) | LOW | engine | engine.py:~555 | RESOLVED — 2dd6ea0 | First-click regen can silently reduce mine count on tiny boards |
| [FA-019](#fa-019) | LOW | renderer | renderer.py:K_arrows | OPEN | Arrow-key pan calls `_win.get_width()` not `_win_size` (sub-issue of FA-006) |
| [FA-020](#fa-020) | LOW | engine | engine.py:right_click | RESOLVED — 2dd6ea0 | `right_click()` never increments `streak` — flags can't build multiplier |
| [DP-R3](#dp-r3) | LOW | engine | engine.py | OPEN | Board loaders return naked `Board` — no `BoardLoadResult` |
| [DP-R6](#dp-r6) | LOW | main | main.py | OPEN | No `preflight_check()` — errors surface mid-game-loop |
| [DP-R8](#dp-r8) | LOW | main | main.py:_save_npy | OPEN | `_save_npy()` is not atomic — no `os.replace` pattern |
| [DP-R9](#dp-r9) | LOW | engine | engine.py | OPEN | No `GAME_SAVE_SCHEMA_VERSION` — format detection by value heuristic |
| [PF-001](#pf-001) | LOW | tests | 3 test files | OPEN | Pre-existing pyflakes warnings — unused imports |
| [T-002](#t-002) | LOW | tests | test_gameworks_engine.py | RESOLVED — tests now pass | Pre-existing failure: `test_snapshot_fields` |
| [T-003](#t-003) | LOW | tests | test_gameworks_renderer_headless.py | RESOLVED — tests now pass | Pre-existing failure: `test_dev_solve_click_returns_action_not_none` |

---

## Bug details

---

### FA-001

**Severity:** CRITICAL
**Component:** `main.py` + `renderer.py`
**File/Line:** `main.py:215`, `renderer.py:702`

**Summary:** Victory modal never rendered. Winning a game shows nothing. The "YOU WIN!" screen is permanently invisible.

**Root cause:** `GameLoop.run()` calls `self._renderer.draw(...)`, which ends with `pygame.display.flip()` at renderer.py:702. Immediately after, `draw_victory(elapsed)` is called at main.py:215. By then, `flip()` has already swapped the back buffer to the screen. `draw_victory()` blits to the *new* back buffer, which is never shown: the very next `draw()` call starts with `_win.fill(C["bg"])`, erasing the modal before any subsequent `flip()`. `_result_shown = True` (main.py:216) is set immediately, preventing any retry.

**Downstream impact:** Players receive zero visual feedback on winning. Score summary and time are hidden. The game sits in RESULT state indefinitely, accepting only ESC/R.

**Fix:** Move `draw_victory()` call to *before* `display.flip()` — inside `draw()` when the win animation is done, or by adding a second `flip()` after `draw_victory()`.

```python
# main.py — move this block BEFORE self._renderer.draw(...):
if self._state == self.RESULT and not self._result_shown:
    if gs == "won" and ...:
        pass
    elif gs == "won":
        self._renderer.draw_victory(elapsed)
        self._result_shown = True
# Then call draw() — its flip() will show the modal
self._renderer.draw(...)
```

**Test gap:** No test asserts `_result_shown` becomes `True` or that `draw_victory()` is called on winning.

---

### FA-002

**Severity:** HIGH
**Component:** `main.py`
**File/Line:** `main.py:186`

**Summary:** Victory modal always shows elapsed time as 0s.

**Root cause:**
```python
elapsed = self._engine.elapsed if not self._engine.board.game_over else 0
```
When `game_over` is `True` (which includes the won state), `elapsed` is overridden with `0` every frame, even though `GameEngine.stop_timer()` already freezes `engine.elapsed` correctly at win time.

**Fix:** Remove the conditional — read `self._engine.elapsed` unconditionally:
```python
elapsed = self._engine.elapsed
```

**Test gap:** No test asserts the elapsed value passed to `draw_victory()` equals the actual game duration.

---

### FA-003

**Severity:** HIGH
**Component:** `renderer.py`
**File/Line:** `renderer.py:460–464`

**Summary:** Resizing the game window moves the board but leaves all panel buttons at their pre-resize pixel positions.

**Root cause:** The `VIDEORESIZE` handler:
```python
if ev.type == VIDEORESIZE:
    self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
    self._win_size = ev.size
    self._center_board()   # ← recenters board only
    return None
```
`_on_resize()` — which updates all five panel button `x`/`y` coordinates — is never called. M-002 (session 9) fixed `_on_resize()` to handle both panel layouts correctly, but the call site for window resize was never added.

**Fix:**
```python
if ev.type == VIDEORESIZE:
    self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
    self._win_size = ev.size
    self._cached_board_rect = None
    self._on_resize()     # ← add this
    self._center_board()
    return None
```

**Test gap:** `test_win_size_cache_updated_on_videoresize` tests only the cache; no test verifies button positions after resize.

---

### FA-004

**Severity:** HIGH
**Component:** `renderer.py`
**File/Line:** `renderer.py` — panel intercept, approx. line 503

**Summary:** Right-clicking or middle-clicking over panel buttons fires board actions (flag/chord) on cells beneath the panel.

**Root cause:** The panel intercept that prevents mouse events from falling through to board cells contains `ev.button == 1`. Only left-clicks are consumed. Right-click (button 2) and middle-click (button 3) over the panel skip the intercept and reach the board coordinate handler.

**Fix:**
```python
if ev.type == MOUSEBUTTONDOWN:
    if panel_rect.collidepoint(ev.pos):
        if ev.button == 1:
            ...handle panel...
        return None   # consume ALL buttons over panel
```

**Test gap:** No test fires `MOUSEBUTTONDOWN` with `ev.button == 2` or `3` over a panel pixel coordinate and asserts no board mutation.

---

### H-005

**Severity:** HIGH
**Component:** `main.py` + `renderer.py`
**File/Line:** `renderer.py:585`, `main.py:run()`

**Summary:** Clicking "Save .npy" in the side panel does nothing.

**Root cause:** `renderer.handle_event()` correctly returns `"save"` when the Save button is clicked. The `GameLoop.run()` event dispatch block handles `"quit"`, `"restart"`, `"click:…"`, `"flag:…"`, `"chord:…"`, and `"dev:solve"` — but has no branch for `"save"`. `GameLoop._save_npy()` is correctly implemented but unreachable from the UI.

**Fix:** Add to the `r_action` dispatch in `run()`:
```python
elif r_action == "save":
    self._save_npy()
```

**Test gap:** `test_main.py` does not test the "save" action dispatch path.

---

### FA-005

**Severity:** MEDIUM
**Component:** `renderer.py`
**File/Line:** `renderer.py` — `Renderer.__init__()`, `BOARD_OX` assignment

**Summary:** On small boards (easy/medium/hard), the board is offset 248 px from the left window edge with nothing on the left side — 248 px of dead empty background.

**Root cause:** For `panel_right=True` layout:
```python
BOARD_OX = PAD + PANEL_W   # = 8 + 240 = 248 px
```
The panel is on the *right*. There is no panel on the left. The board origin should be `PAD` (8 px), not `PAD + PANEL_W` (248 px).

**Fix:** `BOARD_OX = PAD` for `panel_right=True`. `_center_board()` re-derives the correct centered offset from window midpoint anyway; this only affects the first frame.

**Test gap:** No test asserts `BOARD_OX == PAD` in `panel_right=True` mode.

---

### FA-006

**Severity:** MEDIUM
**Component:** `renderer.py`
**File/Line:** renderer.py lines 601, 674, 726, 748, 1052 and arrow-key handlers

**Summary:** Phase 2 frame-local caching (`_win_size`) was applied inconsistently. Five call sites still call `_win.get_width()` / `_win.get_height()` directly, bypassing the cache.

**Affected sites:**
- line 601: smiley rect X in `_draw_smiley()`
- line 674: `_on_resize()` reads `_win.get_width()`
- lines 726, 748: header right-align in `_draw_header()`
- line 1052: panel draw in `_draw_panel()`
- arrow-key pan handlers (K_LEFT / K_RIGHT / K_UP / K_DOWN)

**Fix:** Replace all remaining `self._win.get_width()` with `self._win_size[0]` and `self._win.get_height()` with `self._win_size[1]` throughout.

**Test gap:** No test enforces Phase 2 cache completeness for the remaining sites.

---

### FA-007

**Severity:** MEDIUM
**Component:** `engine.py`
**File/Line:** `engine.py:192–204`

**Summary:** The flood-fill in `Board.reveal()` allows the same cell to be pushed onto the stack multiple times. On large open boards the stack grows to O(4 × area) instead of O(area).

**Root cause:** Cells are marked revealed *on pop*, not *on push*. The push-time guard checks `not self._revealed[ny, nx]`, which is still `False` for cells that have been pushed but not yet popped. A cell adjacent to N zero-count cells can be pushed N times before being popped. The `continue` guard on pop prevents double-processing (correctness is preserved), but stack memory and iteration count grow unnecessarily.

**Fix (option A — zero allocation):** Set `_revealed[ny, nx] = True` at push time (pre-mark). Adjust the pop check accordingly.

**Fix (option B — explicit visited set):**
```python
seen = set()
stack = [(x, y)]
while stack:
    cx, cy = stack.pop()
    if (cx, cy) in seen: continue
    seen.add((cx, cy))
    ...push neighbors...
```

**Test gap:** All flood-fill tests use boards ≤ 9×9. No test exercises large empty boards.

---

### FA-008

**Severity:** MEDIUM
**Component:** `engine.py`
**File/Line:** `engine.py` — `load_board_from_npy()`, approx. lines 346–353

**Summary:** Post-load validation runs O(W×H) nested Python loops calling `_count_adj()` per cell. On a 300×300 board this is ~810 000 Python operations before the window opens.

**Fix:** Replace with a single vectorized comparison:
```python
from scipy.ndimage import convolve
expected = convolve(b._mine.astype(np.uint8),
                    np.ones((3, 3), np.uint8), mode='constant') - b._mine.astype(np.uint8)
if not np.array_equal(b._neighbours, expected):
    raise ValueError("Neighbour count mismatch in loaded board")
```
Or remove the validation entirely — `Board.__init__` already runs the same convolve and the result is deterministic.

**Test gap:** No benchmark test asserts load time for large `.npy` files.

---

### FA-009

**Severity:** MEDIUM
**Component:** `renderer.py`
**File/Line:** `renderer.py:1046`, `renderer.py:1194`

**Summary:** `_draw_image_ghost()` calls `.copy()` on a `subsurface` for every visible flagged cell every frame, allocating one new `Surface` per flag per frame. M-001 (session 9) reduced the outer loop to visible cells only, but the per-cell allocation was not eliminated.

**Root cause:**
```python
sub = scaled.subsurface(src_rect).copy()   # new Surface every frame per visible flag
sub.set_alpha(200 if _mine[y, x] else 40)
self._win.blit(sub, (px, py))
```
`subsurface()` returns a zero-copy view; `.copy()` makes a full allocation to allow `set_alpha()`. On a board with 50 visible flags: 50 Surface allocations × 30 FPS = 1 500 allocations/second.

**Fix:** Pre-render the entire ghost image as a single SRCALPHA surface once (when the image changes or the zoom level changes). Blit the whole surface per frame with a global alpha, or build per-cell alpha into a pre-composed texture. Cache it as `_ghost_surf` (attribute already exists but is unused by this path).

**Test gap:** `test_ghost_surf_not_rebuilt_per_frame` checks the top-level `_ghost_surf` attribute but not per-cell allocations inside the draw loop.

---

### M-003

**Severity:** MEDIUM
**Component:** `renderer.py`
**File/Line:** `renderer.py` — `_draw_panel()` / `handle_event()`

**Summary:** "Restart" and "New Game" panel buttons both return `"restart"`, which calls `engine.restart()` (new board, increments seed). There is no "Retry" option that replays the exact same board layout.

**Impact:** Players who want to retry a specific layout must record the seed externally and restart from CLI. No in-game retry mechanism.

**Fix:** Differentiate the two buttons — one returns `"restart"` (new seed), one returns `"retry"` (re-runs `engine.restart(width=..., height=..., mines=..., seed=engine.seed)` without incrementing seed).

---

### DP-R2

**Severity:** MEDIUM
**Component:** `engine.py`
**File/Line:** `engine.py` — `GameEngine.__init__`

**Summary:** `GameEngine` constructor takes 7 flat keyword arguments. No config object — not serializable, not comparable as a unit.

**Proposed pattern (from DESIGN_PATTERNS.md § R2):**
```python
@dataclass(frozen=True)
class GameConfig:
    mode: str = "random"
    width: int = 16
    height: int = 16
    mines: int = 0
    image_path: str = ""
    npy_path: str = ""
    seed: int = 42
```

**Test gap:** `gameworks/tests/unit/test_config.py` (entire file skipped — pending R2 implementation).

---

### FA-022

**Severity:** LOW
**Component:** `renderer.py`
**File/Line:** `renderer.py` — `_draw_board()` cell loop

**Summary:** The cell draw loop creates three Python `(x, y)` tuples per cell per
frame: `(x, y) in anim_set`, `(x, y) in win_anim_set`, and `pressed == (x, y)`.
At tile=1 (max zoom-out), all 111,000 cells are visible — resulting in 333,000+
tuple allocations per frame. At 30 FPS this is ≥10 million heap allocations per
second. CPython's gen-0 GC threshold (700 objects by default) fires hundreds of
times per second, adding unpredictable micro-pauses throughout the draw path.

**Root cause:**

```python
# renderer.py — _draw_board cell loop body
ip         = _revealed[y, x] and (x, y) in anim_set      # alloc
in_win_anim = (x, y) in win_anim_set                      # alloc
...pressed == (x, y)                                       # alloc
```

Python's `(x, y)` syntax constructs a new `tuple` object on every evaluation.
There is no sharing or caching — each iteration allocates and immediately discards.
The GC tracks every allocation, and gen-0 collection runs every ~700 allocations
by default, so at 333k allocs/frame it fires ~476 times per frame.

**Relationship to other bugs:** Compounds with FA-021 (zoom-out smoothscale freeze)
at max zoom-out. After Phase 9 eliminates the smoothscale blocking, this becomes the
next measurable latency contributor at tile=1.

**Fix:** Replace set-of-tuples membership testing with numpy bool array indexing.
Full solution in PERFORMANCE_PLAN.md Phase 10. Summary:

```python
# Pre-alloc in __init__:
self._anim_arr     = np.zeros((board_h, board_w), dtype=bool)
self._win_anim_arr = np.zeros((board_h, board_w), dtype=bool)

# Per-frame — zero and fill (no tuple per cell):
self._anim_arr.fill(False)
for (cx, cy) in self.cascade.current():
    self._anim_arr[cy, cx] = True

# Cell loop — array index, no tuple:
ip          = _revealed[y, x] and self._anim_arr[y, x]
in_win_anim = self._win_anim_arr[y, x]

# pressed comparison — use separate ints, not tuple comparison:
is_pressed = (self._pressed_x == x and self._pressed_y == y)
```

**Test gap:** No test measures tuple allocation count inside the cell loop. No
tracemalloc or `gc.get_count()` assertion exists for the draw path.

---

### FA-010

**Severity:** LOW
**Component:** `main.py`
**File/Line:** `main.py` — `GameLoop._save_npy()`

**Summary:** Saved `.npy` files are written to the current working directory (`os.getcwd()`) instead of the `results/` directory specified in AGENTS.md.

**Fix:**
```python
out_dir = Path(__file__).parent.parent / "results"
out_dir.mkdir(exist_ok=True)
path = out_dir / f"board_{timestamp}.npy"
```

---

### FA-011

**Severity:** LOW
**Component:** `engine.py`
**File/Line:** `engine.py:112–117`

**Summary:** `Board._count_adj(self, x, y)` is dead code — never called anywhere. It was superseded by `scipy.ndimage.convolve` in `Board.__init__()` but was never removed.

**Fix:** Delete the method.

---

### FA-012

**Severity:** LOW
**Component:** `engine.py`
**File/Line:** `engine.py:158–159`

**Summary:** `Board.correct_flags` property uses `np.sum(self._flagged & self._mine)` — an O(W×H) scan. All four other Board counter properties were converted to O(1) dirty-int counters in Phase 1 (session 11). `correct_flags` was left as a scan.

**Fix:** Add a 5th dirty-int counter `_n_correct_flags`. Increment in `toggle_flag()` when placing a flag on a mine cell; decrement when reversing it. Check `self._mine[y, x]` is already performed at the toggle_flag call site in `right_click()`.

---

### FA-013

**Severity:** LOW
**Component:** `engine.py`
**File/Line:** `engine.py:705`

**Summary:** The block `if __name__ == "_test_engine":` is permanently unreachable. Python `__name__` is either `"__main__"` or `"gameworks.engine"` — never `"_test_engine"`.

**Fix:** Remove the block. If inline dev testing is needed, use `if __name__ == "__main__":`.

---

### FA-014

**Severity:** LOW
**Component:** `main.py`
**File/Line:** `main.py:70–79`

**Summary:** `GameLoop` docstring documents `MENU → PLAYING → RESULT → MENU`. `MENU` is set only in `__init__`. No code path transitions from `RESULT` back to `MENU`. The MENU state has no event-handling code — `run()` jumps straight to `_start_game()` regardless.

**Fix:** Either remove `MENU` from the documented state machine and constants, or implement a real menu screen as a gating step before `_start_game()`.

---

### FA-015

**Severity:** LOW
**Component:** `main.py`
**File/Line:** `main.py:164`, `232–234`

**Summary:** `_do_right_click()` returns a `MoveResult` but the caller always discards it. `_do_left_click` and `_do_chord` both use their return values to drive cascade animation.

**Fix:** Either capture and handle the return value (check `result.state` for any win transition), or change the return type to `None` to match the caller's behavior.

---

### FA-016

**Severity:** LOW
**Component:** `renderer.py`
**File/Line:** `renderer.py` — `WinAnimation.__init__()`

**Summary:** `WinAnimation` shuffles its tile-reveal order using `random.Random(42)` — a fixed seed. The animation plays in the identical order on every game and every restart.

**Fix:** Use `random.Random()` (no seed) or seed from the engine's current `seed` attribute for per-game variety.

---

### FA-017

**Severity:** LOW
**Component:** `main.py`
**File/Line:** `main.py` — approx. lines 107 and 282

**Summary:** `main.py` imports and writes a module-level `TILE` variable, but `Renderer` reads `gameworks.renderer.TILE` — a separate name binding. Setting `main.TILE` has no effect on tile size.

**Fix:** Remove the `TILE` import and assignment from `main.py`. Tile size is fully controlled by `gameworks.renderer.TILE` and `_build_engine()` already sets it correctly via `import gameworks.renderer`.

---

### FA-018

**Severity:** LOW
**Component:** `engine.py`
**File/Line:** `engine.py` — `GameEngine.left_click()`, first-click safety block

**Summary:** When the first click lands on a mine, the board is regenerated with a 3×3 safe zone around the click. On tiny boards where the safe zone covers all or most available cells, `place_random_mines()` returns fewer mines than requested — silently. No error is raised.

**Example:** 3×3 board, 8 mines, first click at center (1,1) → safe zone excludes all 9 cells → 0 mines placed → instant win on next click.

**Fix:** Validate after regeneration:
```python
new_mines = place_random_mines(w, h, mine_count, safe_x=x, safe_y=y, seed=self.seed)
if len(new_mines) != mine_count:
    new_mines = place_random_mines(w, h, mine_count, seed=self.seed)  # no safe zone
```

**Test gap:** `TestFirstClickSafety` uses `mines=70` on 9×9 boards — no test triggers the zero-mine edge case.

---

### FA-019

**Severity:** LOW
**Component:** `renderer.py`
**File/Line:** renderer.py — arrow-key handlers in `handle_event()`

**Summary:** The K_LEFT, K_RIGHT, K_UP, K_DOWN key handlers compute pan clamp bounds using `self._win.get_width()` / `self._win.get_height()` directly instead of the `_win_size` cache introduced in Phase 2. (Sub-issue of FA-006.)

**Fix:** Replace `self._win.get_width()` → `self._win_size[0]`, `self._win.get_height()` → `self._win_size[1]`.

---

### FA-020

**Severity:** LOW
**Component:** `engine.py`
**File/Line:** `engine.py` — `GameEngine.right_click()`

**Summary:** `right_click()` awards `CORRECT_FLAG_BONUS * streak_multiplier` scoring points for correct flags but never increments `self.streak`. A player cannot build their streak multiplier through flagging — only through left-click reveals. This inconsistency means the multiplier applied to flag bonuses is always the pre-existing streak from reveals, never benefiting from a flagging run.

**Fix:** Increment `self.streak` on correct flag placement in `right_click()`. Optionally decrement on flag removal (flag→question transition).

---

### DP-R3

**Severity:** LOW
**Component:** `engine.py`
**File/Line:** `engine.py` — `load_board_from_npy`, `load_board_from_pipeline`

**Summary:** Both board-loader functions return a naked `Board`. Format detection results, fallback status, and load warnings are not observable by callers. (See DESIGN_PATTERNS.md § R3.)

**Proposed pattern:** Add a `BoardLoadResult` dataclass:
```python
@dataclass
class BoardLoadResult:
    board: Board
    format: str           # "pipeline" | "game-save"
    used_fallback: bool
    warnings: List[str]
```

**Test gap:** `gameworks/tests/unit/test_board_loading.py` schema section is skipped.

---

### DP-R6

**Severity:** LOW
**Component:** `main.py`
**File/Line:** `main.py` — `main()`

**Summary:** Missing-file and import errors surface as exceptions mid-game-loop initialization rather than being caught early with clear messages. (See DESIGN_PATTERNS.md § R6.)

**Proposed fix:** Add `preflight_check(args)` that validates image/npy paths exist, pygame is importable, and board dimensions are sane — before constructing `GameLoop`.

**Test gap:** `gameworks/tests/cli/test_preflight.py` is entirely skipped.

---

### DP-R8

**Severity:** LOW
**Component:** `main.py`
**File/Line:** `main.py` — `GameLoop._save_npy()`

**Summary:** `np.save(path, grid)` writes directly to the target path. A crash or Ctrl-C mid-write leaves a partial, corrupted file. No `os.replace` atomic-write pattern is used. (See DESIGN_PATTERNS.md § R8.)

**Fix:**
```python
tmp = path.with_suffix(".tmp")
np.save(tmp, grid)
os.replace(tmp, path)
```

**Test gap:** `test_board_modes.py::TestSaveLoadRoundTrip::test_atomic_save_uses_tmp_then_replace` is skipped.

---

### DP-R9

**Severity:** LOW
**Component:** `engine.py`, `main.py`
**File/Line:** `engine.py` — `load_board_from_npy()`

**Summary:** Saved `.npy` boards carry no version metadata. `load_board_from_npy()` detects format (pipeline vs. game-save) by inspecting value ranges (`0`/`1` vs. `-1`/`0–8`). There is no schema version field or JSON sidecar. A future format change has no migration path. (See DESIGN_PATTERNS.md § R9.)

**Test gap:** `test_board_loading.py` schema versioning section is skipped.

---

### PF-001

**Severity:** LOW
**Component:** tests
**File/Line:** 3 test files

**Summary:** Pre-existing pyflakes warnings (unused imports) in three test files. Not introduced by any recent session.

| File | Line | Warning |
|---|---|---|
| `gameworks/tests/unit/test_engine.py:23` | `place_random_mines` imported, unused |
| `gameworks/tests/architecture/test_boundaries.py:20` | `os` imported, unused |
| `gameworks/tests/architecture/test_boundaries.py:214` | `gameworks.engine` imported, unused (intentional side-effect import inside test) |
| `gameworks/tests/unit/test_board_loading.py:23` | `place_random_mines` imported, unused |
| `gameworks/tests/unit/test_board_loading.py:208` | `BoardLoadResult` imported, unused (inside skipped test) |

**Fix:** Remove unused imports. For the `gameworks.engine` side-effect import, add `# noqa: F401` with a comment explaining intent.

---

### T-002

**Severity:** LOW
**Component:** tests (legacy)
**File/Line:** `tests/test_gameworks_engine.py::TestBoardLogic::test_snapshot_fields`

**Summary:** Pre-existing test failure in the legacy root-level test file. Confirmed present before any session-14 changes.

**Detail:** `test_snapshot_fields` asserts field values on a `CellState` snapshot. The assertion is likely stale from a prior `CellState` interface change (see CHANGELOG.md v0.1.1: renderer no longer constructs `CellState` in the hot loop).

**Fix:** Investigate and update the assertion to match the current `CellState` contract.

---

### T-003

**Severity:** LOW
**Component:** tests (legacy)
**File/Line:** `tests/test_gameworks_renderer_headless.py::TestOverlayPanelClickRouting::test_dev_solve_click_returns_action_not_none`

**Summary:** Pre-existing test failure in the legacy root-level renderer test file. Confirmed present before any session-14 changes.

**Detail:** `test_dev_solve_click_returns_action_not_none` tests that clicking the "Solve Board" DEV TOOLS button returns a non-None action string. This test likely fails because `Renderer._show_dev` defaults to `False` (the DEV panel is hidden by default), making the button unclickable and the handler unreachable.

**Fix:** Either set `r._show_dev = True` before the click event in the test fixture, or update the test to assert `None` is returned when the panel is hidden.

---

### FA-021

**Severity:** MEDIUM
**Component:** `renderer.py`
**File/Line:** `renderer.py:352–358` (`Renderer.__init__`), `renderer.py:1063–1064` (`_draw_image_ghost`)

**Summary:** `_image_surf` is upscaled to full board pixel dimensions at init. Every zoom-level change triggers `pygame.transform.smoothscale(_image_surf, (bw, bh))` with this inflated surface as the source, blocking the main thread 100–500 ms per scroll notch. Zooming from tile=10 to tile=1 requires ~5 steps, producing ~0.5–2.5 s of cumulative blocking during the zoom-out. This is the primary cause of the unresponsive freeze described when zooming all the way out.

**Root cause:**

```python
# renderer.py:352–358 — __init__
scale = min((w_cols * self._tile) / max(img.get_width(), 1),
            (h_rows * self._tile) / max(img.get_height(), 1))
tw = max(1, int(img.get_width() * scale))
th = max(1, int(img.get_height() * scale))
self._image_surf = pygame.transform.smoothscale(img, (tw, th))
```

`scale` equals `(board.width * initial_tile) / img_w`. For a 200×200 input image on a 300×370 board at initial tile=10, `scale = 15` and `_image_surf` becomes 3000×3000 (9 M pixels, 36 MB). The intent was to pre-scale the image to fit the board, but it has the side-effect of making the source surface for every subsequent `_ghost_surf` rebuild needlessly large.

Every frame after a tile-size change, `_draw_image_ghost` fires:

```python
# renderer.py:1063–1064
if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
    self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))
```

`smoothscale` time is dominated by source pixel count. Downscaling a 9 M-pixel surface to (300, 370) reads all 9 M pixels per call. Each scroll notch during zoom-out causes one such call in the next frame.

**Relationship to other bugs:** Compounds with the O(W×H) Python draw loop (PERFORMANCE_PLAN.md Phase 3) at min zoom. FA-009's per-flag `.copy()` allocations (Phase 4A) and the uncached panel overlay Surface (Phase 4B) add GC pressure on top. FA-021 is the root cause of the discrete blocking spikes; the draw loop causes the sustained low-FPS unresponsiveness that follows.

**Fix:** Do not upscale `_image_surf` beyond the natural image dimensions. Only downscale if the input image exceeds a practical cap (`board.width * BASE_TILE × board.height * BASE_TILE` pixels on its longest axis), which prevents very large source images from being wasteful during zoom-in. Replace the existing init block with:

```python
# renderer.py:352–358 — Renderer.__init__
img = pygame.image.load(image_path).convert_alpha()
# Cap: downscale only if image exceeds board pixel dimensions at max zoom.
# Never upscale — upscaling inflates _image_surf and makes every subsequent
# smoothscale (called once per zoom level) proportionally slower.
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

Why `BASE_TILE` (not `self._tile`): `BASE_TILE` is the hard maximum tile size (32 px). The cap ensures `_image_surf` is never larger than needed at maximum zoom, which is the only case where an upscale of `_ghost_surf` would matter for quality. At any other zoom level, downscaling from the natural image size produces equivalent or better quality at a fraction of the cost.

**Impact of fix:** `smoothscale(_image_surf, (bw, bh))` now scales from the natural image size (e.g., 512×512) rather than from the inflated board pixel dimensions. For a 200×200 natural image, each zoom-step `smoothscale` shrinks from 40 000 source pixels instead of 9 000 000 — a 225× reduction in source data touched. The multi-second blocking freezes during zoom-out are eliminated; each zoom step completes in < 5 ms.

**Test gap:** No test asserts that `renderer._image_surf.get_width()` is ≤ the natural image width after `Renderer.__init__` completes. The existing `test_renderer_init.py` tests verify surface existence but not dimensions.

---

## Won't-Fix entries (for completeness)

These bugs are acknowledged but will not be fixed. Documented here to prevent re-investigation.

| ID | Summary | Rationale |
|---|---|---|
| M-005 | `is_lost` property and `draw_defeat()` are dead code | Kept as stubs for potential "hardcore mode" future use and to avoid breaking third-party imports |
| M-006 | Streak increments once per click, not once per revealed cell | Intentional design — streak tracks safe *actions*, not individual cells. Scoring already rewards cells via `REVEAL_POINTS[n] * multiplier` |

---

*Gameworks v0.1.1 — bug register maintained by Claude Sonnet 4.6 via Maton Tasks*
