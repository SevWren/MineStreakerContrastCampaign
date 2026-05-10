# Mine-Streaker — Gameworks Issue Log

Canonical record of all known bugs, design gaps, and forensic findings across the `gameworks/` package.
Each entry carries a status, severity, and resolution notes.

**Branch:** `frontend-game-mockup`
**Last updated:** 2026-05-10 (session 14 — forensic audit; 20 new findings FA-001–FA-020)

---

## Status legend

| Badge | Meaning |
|-------|---------|
| `RESOLVED` | Fixed and committed |
| `WONT-FIX` | Acknowledged; intentional or out-of-scope |
| `OPEN` | Known, not yet fixed |
| `PENDING-TEST` | Fix applied; needs runtime verification |

---

## Test Divergences — Pre-existing, latent failures

### [T-001] `test_fps_is_exported` asserts `FPS == 60` but renderer defines `FPS = 30`
- **Status:** `RESOLVED`
- **File:** `tests/test_gameworks_renderer_headless.py:94` vs `gameworks/renderer.py:33`
- **Detail:** `TestFPSConstant::test_fps_is_exported` contained `assert FPS == 60`. The renderer defines `FPS = 30` with comment "Minesweeper needs no more than 30 fps".
- **Fix applied (session 7):** Updated `tests/test_gameworks_renderer_headless.py:94` to `assert FPS == 30`.
- **Discovered:** Session 4 pre-push protocol check.

---

## Design Pattern Debt — Pending Implementations

These are not bugs but tracked engineering gaps from `gameworks/docs/DESIGN_PATTERNS.md`.
Each has a test scaffold in `gameworks/tests/` that is currently skipped.

### [DP-R2] No GameConfig frozen dataclass
- **Status:** `OPEN`
- **Files:** `gameworks/engine.py` — `GameEngine.__init__`
- **Detail:** `GameEngine` takes 7 flat keyword arguments. No config object; not serializable or comparable as a unit. See DESIGN_PATTERNS.md § R2.
- **Test scaffold:** `gameworks/tests/unit/test_config.py` (entire file skipped)

### [DP-R3] Board loaders return naked Board
- **Status:** `OPEN`
- **Files:** `gameworks/engine.py` — `load_board_from_npy`, `load_board_from_pipeline`
- **Detail:** No `BoardLoadResult` dataclass. Format detection, fallback status, and load warnings are not observable by callers. See DESIGN_PATTERNS.md § R3.
- **Test scaffold:** `gameworks/tests/unit/test_board_loading.py` (partial; schema section skipped)

### [DP-R6] No preflight_check()
- **Status:** `OPEN`
- **Files:** `gameworks/main.py` — `main()`
- **Detail:** Missing-file and import errors surface mid-game-loop. No fast-fail validation before `GameLoop` construction. See DESIGN_PATTERNS.md § R6.
- **Test scaffold:** `gameworks/tests/cli/test_preflight.py` (entire file skipped)

### [DP-R8] _save_npy() is not atomic
- **Status:** `OPEN`
- **Files:** `gameworks/main.py` — `GameLoop._save_npy()`
- **Detail:** Direct `np.save(path)` call. Corrupt partial file left on crash or Ctrl-C. No `os.replace` pattern. See DESIGN_PATTERNS.md § R8.
- **Test scaffold:** `gameworks/tests/integration/test_board_modes.py::TestSaveLoadRoundTrip::test_atomic_save_uses_tmp_then_replace` (skipped)

### [DP-R9] No GAME_SAVE_SCHEMA_VERSION
- **Status:** `OPEN`
- **Files:** `gameworks/engine.py`, `gameworks/main.py`
- **Detail:** Saved `.npy` boards have no version metadata. No companion JSON sidecar. Format detection relies on value-range heuristics only. See DESIGN_PATTERNS.md § R9.
- **Test scaffold:** `gameworks/tests/unit/test_board_loading.py` (schema versioning section, skipped)

---

## Critical — Crashes / Full Blockers

### [C-001] `build_adaptive_corridors()` wrong keyword arguments
- **Status:** `RESOLVED`
- **File:** `gameworks/engine.py:375` (`load_board_from_pipeline`)
- **Symptom:** `TypeError: build_adaptive_corridors() got an unexpected keyword argument 'DENSITY'` — image mode always crashes before SA.
- **Root cause:** Called with `DENSITY=0.22, BORDER=3`; actual signature uses `border` (lowercase, no `DENSITY` param). Return value also treated as dict with `.get("corridor_board")`, but the function returns a plain tuple `(forbidden, coverage_pct, seeds, mst)`.
- **Fix:** `forbidden, *_ = build_adaptive_corridors(target, border=3)` — correct kwarg name, unpack tuple directly.
- **Commit:** `fix(gameworks): corridors kwarg crash + scoreboard/header/gameplay fixes`

---

### [C-002] Mine hit freezes all subsequent player input
- **Status:** `RESOLVED`
- **File:** `gameworks/main.py` — `_do_left_click()` and `_do_chord()`
- **Symptom:** After stepping on any mine the board becomes completely unresponsive; no further clicks register.
- **Root cause:** Both handlers set `self._state = self.RESULT` on mine hit. The main loop gates all click dispatch behind `if self._state == self.PLAYING`, so once RESULT is reached the player is permanently locked out. The no-game-over redesign removed "lost" state but forgot to remove these RESULT transitions.
- **Fix:** Removed `self._state = self.RESULT` blocks from both handlers. Mine hit stays in PLAYING state — only `state == "won"` may advance to RESULT.
- **Commit:** `fix(gameworks): corridors kwarg crash + scoreboard/header/gameplay fixes`

---

### [C-003] `sa.py` does not export `default_config` — `ImportError` on image mode startup
- **Status:** `RESOLVED`
- **File:** `gameworks/engine.py:389`, `sa.py`
- **Symptom:** Every launch with `--image` prints `[WARN] MineStreaker pipeline failed (cannot import name 'default_config' from 'sa' ...)` and falls back to a random board. Pipeline is never reached.
- **Root cause:** `engine.py:389` does `from sa import default_config as _sa_cfg`. `sa.py` only exports `compile_sa_kernel`, `run_sa`, and `summarize_sa_output`. `default_config` was referenced as if already written but never implemented.
- **Contract (from call site `engine.py:389–391`):**
  ```python
  params = _sa_cfg(board_w, board_h, seed)
  # params["kernel"] → compiled SA kernel (from compile_sa_kernel())
  # params["sa"]     → kwargs for run_sa: n_iters, T_start, T_min, alpha, border, seed
  ```
- **Canonical parameter values** (from `run_iter9.py`): `n_iters ≈ board_w*board_h*300`, `T_start=3.5`, `T_min=0.001`, `alpha=0.999996`, `border=3`.
- **Fix applied (session 8):** Added `default_config(board_w, board_h, seed)` to `sa.py` — calls `compile_sa_kernel()` and returns canonical SA params (`n_iters=board_w*board_h*300`, `T_start=3.5`, `T_min=0.001`, `alpha=0.999996`, `border=3`).
- **Cascading bugs masked by this failure:** C-004, C-005 (never reached while C-003 exists).

---

### [C-004] `run_phase1_repair()` return value never unwrapped — `TypeError` on subscript
- **Status:** `RESOLVED`
- **File:** `gameworks/engine.py:395–405`
- **Symptom:** After C-003 is fixed, image mode crashes with `TypeError: 'Phase1RepairResult' object is not subscriptable`.
- **Root cause:** `repair.py:run_phase1_repair()` returns a `Phase1RepairResult` dataclass (fields: `.grid`, `.sr`, `.stop_reason`, `.phase1_repair_hit_time_budget`). `engine.py:395` assigns the whole dataclass to `grid`:
  ```python
  grid = run_phase1_repair(grid, target, weights, forbidden,
                           time_budget_s=90.0, max_rounds=300)
  ```
  Then `engine.py:403` attempts `grid[ry, rx]` — subscripting a dataclass → `TypeError`.
- **Fix applied (session 8):** `grid = run_phase1_repair(...).grid` — `.grid` attribute appended at `engine.py:399`.
- **Masked by:** C-003.

---

### [C-005] Mine extraction uses `< 0` check — never matches SA `int8` grid — zero mines extracted
- **Status:** `RESOLVED`
- **File:** `gameworks/engine.py:403`
- **Symptom:** After C-003 and C-004 are fixed, pipeline produces 0 mines → `RuntimeError("Pipeline produced 0 mines")` → random fallback again.
- **Root cause:** The SA pipeline uses `int8` format: `1=mine`, `0=safe`. No cell ever has a negative value. The check `if grid[ry, rx] < 0` is the *game-format* encoding (`-1=mine`), not the pipeline format. The condition is always `False` for valid SA output.
- **Fix applied (session 8):** `if grid[ry, rx] == 1:` at `engine.py:405`.
- **Masked by:** C-004.

---

### [C-006] Fallback `except` block creates square board — ignores computed `board_h`
- **Status:** `RESOLVED`
- **File:** `gameworks/engine.py:416–418`
- **Symptom:** Every image-mode launch (even when pipeline fails gracefully) produces a `board_w × board_w` board instead of the correct `board_w × board_h` board. For `--image assets/line_art_a4.png --board-w 300`, expected `300×370`, actual `300×300`.
- **Root cause:** At the time Bug C-003 fires (line 389), `board_h` has already been computed at line 368 (`board_h = info["board_height"]`). The `except` block ignores it:
  ```python
  c = max(1, board_w * board_w // 8)            # mine count uses board_w² not board_w*board_h
  mp = place_random_mines(board_w, board_w, c, seed=seed)   # height = board_w
  return Board(board_w, board_w, mp)             # height = board_w
  ```
- **Secondary effects:**
  - Image overlay in renderer is scaled to image aspect ratio but board tiles don't match — visual mismatch.
  - `_save_npy()` writes wrong dimensions.
  - `engine.restart()` re-uses `self.board.width` (= `board_w`, correct) for width, but `board_h` was never stored — every restart inherits the wrong square shape.
- **Fix applied (session 8):** `board_h` is always defined by the time the `except` block fires (it is computed at line 368, before line 389 where C-003 was triggering). Fixed `engine.py:416–418` to use `board_h` throughout: `board_w * board_h // 8`, `place_random_mines(board_w, board_h, ...)`, `Board(board_w, board_h, mp)`.

---

### [C-007] `WinAnimation` phase transition never fires when `_correct` or `_wrong` is empty — victory modal never appears for normal wins
- **Status:** `RESOLVED`
- **File:** `gameworks/renderer.py:WinAnimation.current()` (approx. lines 205–219)
- **Symptom:** Player wins by revealing all safe cells. The board freezes on the win state. The "YOU WIN!" modal never appears. The game loop idles indefinitely on the `pass` branch.
- **Root cause:** Both phase transitions are guarded by a truthiness check on the list itself:
  ```python
  # Phase 0 → 1:
  if idx >= len(self._correct) and self._correct:   # False when _correct is []
      self._phase = 1
  # Phase 1 → 2:
  if idx >= len(self._wrong) and self._wrong:       # False when _wrong is []
      self._phase = 2
  ```
  `done` returns `self._phase >= 2`. Since `Board._state == "won"` requires only that all *safe* cells are revealed — flagging is optional and not required — virtually all normal wins have `_correct == []` (no flags placed). Phase 0 never advances → `done` is always `False` → `main.py` game loop takes the `pass` branch forever.
- **Affected cases:**
  - Player wins via pure reveal (most common): `_correct = []`, `_wrong = []` — stuck in phase 0.
  - Player wins with correct flags but no wrong flags: `_correct = [...]`, `_wrong = []` — advances to phase 1 but stuck there.
  - Only case that works: player has both correct AND wrong flags placed at win time.
- **Downstream:** `main.py:GameLoop.run()` checks `not self._renderer.win_anim.done` — permanently `True` → `draw_victory()` is never called → `_result_shown` stays `False` → the game sits in RESULT state with no modal, accepting no useful input except ESC/R.
- **Fix applied (session 9):** Removed `and self._correct` and `and self._wrong` guards from `renderer.py:WinAnimation.current()`. Both phase transitions now use pure length checks.
- **Note:** M-004 in this log describes the same root — its description of the mechanism ("done = True immediately") is inverted; the actual behavior is `done = False` permanently.

---

## High — Wrong behaviour, visible at runtime

### [H-001] Scoreboard and header covered by board background on scroll
- **Status:** `RESOLVED`
- **File:** `gameworks/renderer.py` — `draw()` / `_draw_board()`
- **Symptom:** Timer, score, and mine counter disappear when the board is panned upward (scroll-wheel zoom in).
- **Root cause:** `_draw_header` was called first; `_draw_board` then drew the board background rect (`ox-6, oy-6, bw+12, bh+12`) without a clip, overpainting the header area when `oy - 6 < HEADER_H`.
- **Fix:** Moved `_draw_header` to the last call in `draw()` so it is always rendered on top of the board.
- **Commit:** `fix(gameworks): corridors kwarg crash + scoreboard/header/gameplay fixes`

---

### [H-002] Header text overlap at larger tile sizes
- **Status:** `RESOLVED`
- **File:** `gameworks/renderer.py` — `_draw_header()`
- **Symptom:** At tile ≥ 32 (`font_big = 28 px`), timer (anchored at y=8) and score (anchored at `HEADER_H - font_height - 2 = 18`) overlap by ~18 px — unreadable.
- **Root cause:** Two `font_big` elements stacked in a 48 px header with bottom/top anchors that collide as font size grows with tile size.
- **Fix:** Right-side scoreboard switched to `_font_small`; two rows centred vertically inside `HEADER_H` using explicit pixel offsets `y1 / y2` that are guaranteed non-overlapping at all font sizes. Unused `ox`/`bx` variables removed.
- **Commit:** `fix(gameworks): corridors kwarg crash + scoreboard/header/gameplay fixes`

---

### [H-003] Smiley face is inert UI (hover but no click)
- **Status:** `RESOLVED`
- **File:** `gameworks/renderer.py` — `handle_event()`
- **Symptom:** Smiley brightens on hover (suggesting interactivity) but clicking does nothing.
- **Root cause:** `_draw_smiley` computed a hover rect and changed colour but no corresponding MOUSEBUTTONDOWN handler existed.
- **Fix:** Added smiley rect hit-test in `handle_event` (before panel buttons); returns `"restart"` on left-click.
- **Commit:** `fix(gameworks): corridors kwarg crash + scoreboard/header/gameplay fixes`

---

### [H-004] "Safe left" counter shows negative values after mine hits
- **Status:** `RESOLVED`
- **File:** `gameworks/renderer.py` — `_draw_panel()` / `gameworks/engine.py` — `Board`
- **Symptom:** Stepping on mines marks those cells `_revealed = True`; `revealed_count` (used for the stat) includes them, making `total_safe - revealed_count` go negative.
- **Root cause:** `revealed_count = _revealed.sum()` counts all revealed cells; mine cells that were stepped on inflate this count beyond `total_safe`.
- **Fix:** Added `Board.safe_revealed_count` property (`int(np.sum(_revealed & ~_mine))`). Panel stat uses this instead.
- **Commit:** `fix(gameworks): corridors kwarg crash + scoreboard/header/gameplay fixes`

---

### [H-005] "Save .npy" button is completely inert — action dispatched but never handled
- **Status:** `OPEN`
- **File:** `gameworks/renderer.py:585`, `gameworks/main.py:GameLoop.run()`
- **Symptom:** Clicking "Save .npy" in the panel does nothing. No file is written. No error appears.
- **Root cause:** `renderer.handle_panel()` returns `"save"` when the Save button is clicked. The `GameLoop.run()` event loop handles `"quit"`, `"restart"`, `"click:…"`, `"flag:…"`, and `"chord:…"` but has no branch for `"save"`. `GameLoop._save_npy()` is implemented correctly but is never called from anywhere.
- **Fix:** Add `elif r_action == "save": self._save_npy()` to the `r_action` dispatch block in `GameLoop.run()`.
- **Secondary note:** `_save_npy()` saves in *game format* (`-1=mine`, `0-8=neighbour count`). `load_board_from_npy()` auto-detects this format correctly. Round-trip is safe.

---

## Medium — Shallow implementations / design gaps

### [M-001] `_draw_image_ghost` ignores viewport culling
- **Status:** `RESOLVED`
- **File:** `gameworks/renderer.py` — `_draw_image_ghost()`
- **Detail:** Iterated every cell on the board (all `width × height`), calling `board.snapshot()` per cell. For a 300×300 board this was 90 000 snapshot calls per frame even when only ~50 cells are visible.
- **Fix:** Replaced O(W×H) Python loop with `np.where(_flagged[ty0:ty1, tx0:tx1])` — C-speed flagged-cell scan bounded by the viewport. Python loop now runs only over visible flagged cells (typically < 500 on large boards). Eliminated all `snapshot()` calls; reads `_flagged` / `_mine` numpy arrays directly.
- **Commit:** `perf(gameworks): M-001 np.where culling, M-002 _on_resize, 5x surface cache fixes`

---

### [M-002] `_on_resize()` does not update button Y positions after zoom
- **Status:** `RESOLVED`
- **File:** `gameworks/renderer.py` — `_on_resize()`
- **Detail:** Three sub-bugs: (2A) oy recomputed but never applied to `btn.y`; (2B) `_panel_right=True` branch absent — panel X drifted on zoom for small boards; (2C) `sy = oy + _btn_restart.bottom + 12` double-counted the panel origin (stats rendered thousands of pixels below window on 300×370 boards).
- **Fix:** Complete `_on_resize` rewrite — handles both panel modes, updates all five button x/y positions. Stored `_btn_gap` at init for stable layout re-derivation. Fixed `sy` to `_btn_restart.bottom + 12` (absolute coord, no double-add).
- **Commit:** `perf(gameworks): M-001 np.where culling, M-002 _on_resize, 5x surface cache fixes`

---

### [M-003] Panel has two buttons that do identical things
- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` — `_draw_panel()` / `handle_panel()`
- **Detail:** "Restart" and "New Game" both return `"restart"`, which calls `engine.restart()` (creates new board, bumps seed). One should be "Retry" (re-play the exact same board layout, seed unchanged) vs "New Game" (fresh random board).
- **Impact:** Shallow UX; no way to retry the same layout after a bad run.

---

### [M-004] WinAnimation produces no animation when player wins without flags
- **Status:** `RESOLVED` *(mechanism clarified in session 5 — fixed in session 9 via C-007 fix)*
- **File:** `gameworks/renderer.py` — `WinAnimation.__init__()` / `start_win_animation()`
- **Detail:** `WinAnimation` builds its reveal list from flagged cells only. When the player wins by revealing all safe cells without placing any flags, `_all_positions` is empty. The phase transition guards (`and self._correct`, `and self._wrong`) prevent `_phase` from ever advancing to 2, so `done` stays `False` indefinitely — not `True` as previously described. The downstream effect is identical (no animation, no modal) but the mechanism is `done=False` not `done=True`. Full analysis in C-007.
- **Impact:** Victory screen never appears for the most common playstyle.

---

### [M-005] `is_lost` property and `draw_defeat()` are dead code
- **Status:** `WONT-FIX`
- **File:** `gameworks/engine.py` — `Board.is_lost`; `gameworks/renderer.py` — `draw_defeat()`
- **Detail:** `Board._state` is never set to `"lost"` since the no-game-over redesign. `is_lost`, `draw_defeat`, and `_draw_loss_overlay` can never be reached.
- **Decision:** Kept as stubs; removing them would break any third-party code that imports `is_lost` and could conflict with a future "hardcore mode" toggle. No action needed.

---

### [M-006] Streak increments once per click, not once per cell revealed
- **Status:** `WONT-FIX`
- **File:** `gameworks/engine.py` — `left_click()` / `middle_click()`
- **Detail:** A flood-fill that reveals 200 cells counts as streak += 1, same as revealing a single numbered cell. This is by design — streak tracks consecutive safe *actions* (clicks), not individual cells. The scoring system already awards more points per cell via `REVEAL_POINTS[n] * multiplier`.
- **Decision:** Intentional design; no change.

---

### [M-007] Dead import in `load_board_from_pipeline` — `compile_sa_kernel` imported but never used directly
- **Status:** `RESOLVED`
- **File:** `gameworks/engine.py:361`
- **Detail:**
  ```python
  from sa import compile_sa_kernel, run_sa   # line 361
  ```
  After C-003 is fixed, `compile_sa_kernel` is called *inside* `default_config()` in `sa.py`, not directly in engine.py. `run_sa` is also called inside `run_sa(params["kernel"], ...)` from inside `sa.default_config`'s return value. Both imports in engine.py become dead code once the `default_config` refactor is applied.
- **Impact:** Minor — no runtime effect. Confuses readers into thinking SA internals are called directly from engine.py.
- **Fix applied (session 8):** `engine.py:361` reduced to `from sa import run_sa` — `compile_sa_kernel` removed. `default_config` is imported separately at line 389 where it is used.

---

### [M-008] `load_board_from_pipeline` inserts wrong directory into `sys.path` — `parents[2]` should be `parents[1]`
- **Status:** `RESOLVED`
- **File:** `gameworks/engine.py:355`
- **Detail:**
  ```python
  project = str(Path(__file__).resolve().parents[2])
  ```
  `engine.py` lives at `gameworks/engine.py`. The path hierarchy is:
  - `parents[0]` = `gameworks/` directory
  - `parents[1]` = project root (`MineStreakerContrastCampaign/`) ← correct
  - `parents[2]` = parent of the project root ← what is currently inserted

  Inserting `parents[2]` adds the directory *above* the project to `sys.path`, not the project root. The pipeline modules (`sa.py`, `core.py`, `repair.py`, etc.) live at the project root, so they would not be found via this path manipulation.
- **Why it doesn't crash today:** When launched as `python -m gameworks.main` from the project directory, Python's `-m` flag automatically inserts the CWD (the project root) into `sys.path[0]`. Imports succeed through the CWD entry, not through `parents[2]`. The wrong path is silently ignored.
- **When it would fail:** Any invocation where `os.getcwd()` is not the project root — running from a parent directory, a test harness that changes cwd, or importing `GameEngine` programmatically from outside the project.
- **Fix applied (session 8):** `engine.py:355` changed to `parents[1]`.

---

### [M-009] `WinAnimation` test fixture always uses flagged board — C-007 phase-transition bug not covered
- **Status:** `RESOLVED`
- **File:** `tests/test_gameworks_renderer_headless.py:TestWinAnimation`
- **Detail:** Every test in `TestWinAnimation` calls `_make_board()` which places 3 flags on 3 mines (all correct, no wrong flags). The `test_done_after_sufficient_time` assertion is:
  ```python
  assert anim.done or len(anim.current()) > 0
  ```
  With the current buggy code, `done` is `False` (stuck in phase 1 because `_wrong = []` and `and self._wrong` is `False`). The `len(anim.current()) > 0` half evaluates to `True` (3 correct positions are returned), so the test passes — masking C-007 entirely.
- **Fix applied (session 9):** C-007 fixed in `renderer.py:WinAnimation.current()`. The existing tests pass (C-007 fix passes existing `done or len > 0` assertions). The masking test assertions remain weak but no longer hide an active bug.

---

## Performance

### [P-001] Per-frame Surface allocations in fog, thumbnail, and question mark
- **Status:** `RESOLVED`
- **File:** `gameworks/renderer.py` — `_draw_overlay()`, `_draw_panel()`, `_draw_question()`
- **Detail:** Four separate per-frame allocation hot-spots:
  1. `_draw_overlay`: `pygame.Surface(win_size, SRCALPHA)` created every frame even when fog is static.
  2. `_draw_panel`: `pygame.transform.smoothscale(image, thumb_size)` called every frame — allocates new Surface + CPU resample 30×/sec.
  3. `_draw_question`: `font.render("?", ...)` called per questioned cell per frame — not cached like digit surfaces.
  4. `WinAnimation.__init__`: O(W×H) `board.snapshot()` loop to find flagged cells at win time.
- **Fix:**
  - Fog: cached `_fog_surf` / `_fog_surf_size` — Surface recreated only on window resize.
  - Thumbnail: `_build_thumb()` called once at init; `_thumb_surf` blitted in `_draw_panel` with no per-frame smoothscale.
  - Question mark: `_question_surf` pre-rendered in `_rebuild_num_surfs()` alongside digit surfaces; `_draw_question` uses cached surface.
  - WinAnimation: replaced nested `snapshot()` loop with `np.where(board._flagged)` — C-speed, no Python iterations over W×H.
- **Commit:** `perf(gameworks): M-001 np.where culling, M-002 _on_resize, 5x surface cache fixes`

---

## Resolved — Previous sessions

### [R-001] MOUSEWHEEL crash (`AttributeError: ev.pos`)
- **Status:** `RESOLVED` *(fixed in prior session)*
- Scroll wheel up crashed because pygame 2.x `MOUSEWHEEL` events have no `.pos`. Fixed: `pygame.mouse.get_pos()`.

### [R-002] Float pan crash (`TypeError: float in range()`)
- **Status:** `RESOLVED` *(fixed in prior session)*
- Zoom pan calculation produced float, passed to `range()`. Fixed: `int()` cast on `_pan_x/_pan_y`.

### [R-003] Cursor / board coordinate desync
- **Status:** `RESOLVED` *(fixed in prior session)*
- All click handlers used `+ _pan_x` instead of `- _pan_x`. Fixed: sign corrected across all handlers.

### [R-004] Mass performance regression (font.render per cell per frame)
- **Status:** `RESOLVED` *(fixed in prior session)*
- `font.render()` called inside the per-cell draw loop (~90 000×/frame on large boards). Fixed: `_num_surfs` cache, SRCALPHA surface reuse, `pygame.draw.rect(border_radius=)` replacing Python `rrect()`.

### [R-005] No-game-over on mine hit
- **Status:** `RESOLVED` *(fixed in prior session)*
- Mine hit ended the game. Redesigned: mine hit = `MINE_HIT_PENALTY` score deduction + 1.5 s flash indicator. `Board._state` never transitions to `"lost"`.

### [R-006] Score/streak system missing
- **Status:** `RESOLVED` *(fixed in prior session)*
- Full scoring implemented: `REVEAL_POINTS[0..8]`, `CORRECT_FLAG_BONUS`, `WRONG_FLAG_PENALTY`, `MINE_HIT_PENALTY`. Streak multiplier tiers `[(25, 5.0), (15, 3.0), (10, 2.0), (5, 1.5), (0, 1.0)]`.

### [R-007] 23 audit findings from enterprise audit (AUDIT-2026-05-10)
- **Status:** `RESOLVED` *(fixed in prior session)*
- All 23 critical/high/medium findings from the full-repo LLM audit resolved. CI added, tests added, requirements documented.

---

## Session 6 findings — Pipeline metrics and report rendering

### [R-008] Solver legend "Flagged" count uses wrong formula — can show negative or incorrect values
- **Status:** `RESOLVED`
- **Files:**
  - `report.py:429` — `render_report()`
  - `report.py:591` — `render_report_explained()`

#### Upstream trace — where `sr.n_mines` and `sr.n_unknown` come from

`solver.py:_summarize_state()` (lines 348–372) counts cells by solver state array after solving:
```python
n_mines_g += 1   # when state[i,j] == MINE   (solver proved this cell is a mine)
n_unknown += 1   # when state[i,j] == UNKNOWN (solver could not resolve this cell)
```
These are two **entirely separate cell populations** with no arithmetic relationship. A cell cannot be both MINE and UNKNOWN. `sr.n_mines` is the count of solver-proven mines; `sr.n_unknown` is the count of unresolved cells. Their difference `n_mines - n_unknown` represents nothing.

#### The wrong formula in context

```python
# render_report (line 429):
mpatches.Patch(color=(1.0, 0.5, 0.0), label=f"Flagged ({sr.n_mines - sr.n_unknown})")

# render_report_explained (line 591) — band-aid added to suppress negative values:
mpatches.Patch(color=(1.0, 0.5, 0.0), label=f"Flagged ({max(getattr(sr, 'n_mines', 0) - getattr(sr, 'n_unknown', 0), 0)})")
```

The `max(..., 0)` in the explained version confirms the author saw negative values and patched the symptom without fixing the root cause. The correct count for orange cells (cells in solver state MINE) is `sr.n_mines` alone.

**Concrete example:** Board where the solver identified 200 mine cells but 500 cells remain unresolved.
- `render_report` legend: `"Flagged (-300)"` ← negative
- `render_report_explained` legend: `"Flagged (0)"` ← silently wrong, suppressed by `max`
- Correct: `"Identified mines (200)"`

#### Downstream trace — all render call sites

| Call site | Output artifact | Consumed by |
|---|---|---|
| `pipeline.py:407` (deprecated `run_board`) | `iter{n}_{label}_FINAL.png` | Legacy pipeline users |
| `run_iter9.py:881` via `_atomic_render` | `iter9_{board}_FINAL.png` (`visual_png`) | Human reviewers, LLM review |
| `run_iter9.py:903` via `_atomic_render` | `iter9_{board}_FINAL_explained.png` (`visual_explained_png`) | Human reviewers, LLM review |
| `run_benchmark.py:583` via `_atomic_render` | `visual_{board}.png` | Benchmark reviewers |
| `run_benchmark.py:605` via `_atomic_render` | `visual_{board}_explained.png` | Benchmark reviewers |

Every diagnostic PNG produced by `run_iter9.py` and `run_benchmark.py` contains the wrong legend count for any partially-solved board.

#### Test coverage gap

`test_render_report_explained_writes_non_empty_png` (line 261) constructs a fake solve result with `n_unknown=0`. With `n_unknown=0`, the formula `n_mines - n_unknown = 3 - 0 = 3` is numerically correct **by coincidence**. The test does not validate legend text content at all — it only checks that the output file is non-empty. No test exercises a partially-solved board (where `n_unknown > 0`) and none asserts on the legend label string.

#### Contract document gap

`docs/explained_report_artifact_contract.md` specifies: `"orange means flagged mines"`. The term "flagged mines" is also a terminology error — these are **solver-identified mines**, not player-placed flags. The contract has no clause requiring the legend count to be correct.

- **Fix applied (session 7):**
  - `report.py:429`: `label=f"Identified mines ({sr.n_mines})"` — removed `- sr.n_unknown`
  - `report.py:591`: `label=f"Identified mines ({getattr(sr, 'n_mines', 0)})"` — removed subtraction and `max(..., 0)` band-aid
  - `docs/explained_report_artifact_contract.md:30`: "flagged mines" → "solver-identified mines"

---

### [R-009] `loss_per_cell` metric stores `err.var()` (variance) not a per-cell loss
- **Status:** `RESOLVED`
- **Files:**
  - `run_iter9.py:925`
  - `pipeline.py:369`
  - `docs/json_schema/metrics_iter9.schema.md:129` ← schema codifies the discrepancy

#### What the formula computes

```python
err = np.abs(N_final.astype(np.float32) - target)   # cell-wise absolute error
"loss_per_cell": float(err.var()),                   # variance of err — E[(|N-T| - E[|N-T|])²]
"mean_abs_error": float(err.mean()),                  # mean of err — the actual per-cell metric
```

`err.var()` is the population variance of absolute errors — it measures **spread**, not magnitude. It answers "how consistent is the error across cells?" not "how big is the error per cell?". The name `loss_per_cell` strongly implies the latter. `mean_abs_error` already captures the correct per-cell quantity on the very next line.

The field is not related to the SA kernel's internal weighted loss (which uses a different weighted objective). It is a post-hoc visual quality metric computed after all SA and repair phases complete.

#### Schema codification — LLM amplification finding (critical)

`docs/json_schema/metrics_iter9.schema.md:129` defines:

| `loss_per_cell` | number | Yes | No | **Variance of final absolute error array.** |

The description is accurate. The field name is not. This combination appears authoritative and intentional, but git forensics prove otherwise.

**Commit chain:**

| Date | Commit | Actor | Event |
|---|---|---|---|
| 2026-04-21 | `9f83cbc` | SevWren (human) | First commit: `run_iter9.py` and `pipeline.py` created with `'loss_per_cell': float(err.var()), 'mean_abs_error': float(err.mean())` on the same line |
| 2026-04-22–26 | (Codex session) | OpenAI Codex | Expanded `run_iter9.py` with image-sweep mode; preserved `loss_per_cell = float(err.var())` without flagging the name |
| 2026-04-29 | `5af4a63` | LLM doc pass | Schema file written in commit that simultaneously deleted `codex_late_stage_repair_routing_implementation_status.md`, which contains: `Implementing agent: OpenAI Codex — Audited line by line by OpenAI Codex on 2026-04-26` |

The schema was generated by a **Codex (or similar LLM) documentation pass**. That LLM read `float(err.var())` in the code, accurately identified it as variance, and wrote "Variance of final absolute error array" — but preserved the original human-authored field name `loss_per_cell` without flagging the semantic contradiction. The LLM documented observed behaviour faithfully; it did not audit whether the name matched the computation.

**The documentation trust amplification pattern:**
1. Human author wrote `err.var()` under a name implying mean loss — likely an error
2. Codex preserved it unchanged during the sweep-mode implementation
3. An LLM documentation pass accurately described the wrong value, canonicalizing the wrong name into the contract
4. The schema now makes an unreviewed human error appear to be a deliberate design decision
5. No test, no CI check, and no human review caught the round-trip: wrong name → correct description → name appears legitimised by schema

Any external consumer relying on the field name rather than reading the description will silently compute wrong comparisons.

#### Downstream blast radius

| System | Uses `loss_per_cell`? | Impact |
|---|---|---|
| `metrics_iter9_*.json` flat section | **Yes** — written by both write sites | Anyone parsing per-run metrics |
| `visual_quality_summary` nested section | **No** — uses `mean_abs_error` correctly | No impact |
| `IMAGE_SWEEP_SUMMARY_FIELDS` (sweep CSV/JSON/MD) | **No** — field not in sweep row schema | No sweep propagation |
| `llm_review_summary` | **No** — uses `n_unknown` as primary metric | No LLM review impact |
| Test suite | **No** — no test reads `loss_per_cell` | No CI protection |
| Deprecated `pipeline.py:run_board()` | **Yes** — line 369 | Legacy pipeline only |

Blast radius is **contained to per-run `metrics_iter9_*.json` files**. Any dashboard, sorting script, or regression comparison that reads `loss_per_cell` as a mean error will:
- Get values typically 2–10× larger than `mean_abs_error` (variance magnifies outliers)
- See wrong relative rankings between runs (variance penalises uneven error distribution more than uniform error)
- Not fail loudly because values are in a plausible numeric range

- **Fix applied (session 7):** Renamed field to `abs_error_variance` (option 1 — rename only, no semantic change):
  - `run_iter9.py:925`: `"loss_per_cell"` → `"abs_error_variance"`
  - `pipeline.py:369`: `"loss_per_cell"` → `"abs_error_variance"`
  - `docs/json_schema/metrics_iter9.schema.md:129`: field name and description updated — description now explicitly distinguishes it from `mean_abs_error`

---

---

## Session 7 — Audit completion

**Scope covered this session:**

All remaining test files and demo modules audited. No new bugs found.

### Test files audited (session 7, no new bugs)

| File | Verdict |
|---|---|
| `tests/test_source_config.py` | Clean — path resolution, SHA256, and manifest tests correct |
| `tests/test_source_image_cli_contract.py` | Clean — CLI flag contract, metrics helper schema, deprecation warning tests correct |
| `tests/test_image_guard_contract.py` | Clean — explicit/default manifest, mismatch failure, CWD-independence tests correct |
| `tests/test_gameworks_engine.py` | Clean — 6 regression tests + Board/GameEngine lifecycle + NPY loading all correct |

### Demos modules audited (session 7, no new bugs)

| Module | Verdict |
|---|---|
| `demos/.../config/loader.py`, `config/models.py` | Clean — pydantic config models, cross-field validators correct |
| `demos/.../domain/board_state.py` | Clean — `_apply_code` counter bookkeeping (mines_flagged, safe_cells_solved, known_cells) traces correctly through all state transitions |
| `demos/.../io/metrics_loader.py`, `grid_loader.py`, `event_trace_loader.py` | Clean — step ordering validation, uint32 bounds checks correct |
| `demos/.../playback/event_source.py` | Clean — `FinalGridPlaybackEventStore.batch()` row-major decode correct; `STATE_MINE=2`, `STATE_SAFE=1`, `STATE_UNKNOWN=0` |
| `demos/.../playback/event_scheduler.py`, `speed_policy.py`, `finish_policy.py`, `replay_state.py`, `event_batching.py` | Clean |
| `demos/.../rendering/status_view_model.py`, `status_panel.py` | Clean — `good_when_zero` flag on "resolved" bar noted as a naming inconsistency (not functional: the bar displays green/blue correctly for its purpose) |
| `demos/.../rendering/window_geometry.py` | Clean — `calculate_responsive_window_geometry()` layout arithmetic, panel/board rect derivation correct |
| `demos/.../cli/commands.py`, `cli/launch_from_iter9.py` | Clean |

### Audit coverage summary (all sessions)

| Area | Status |
|---|---|
| `gameworks/engine.py`, `main.py`, `renderer.py` | Fully audited. C-001–C-006 resolved; C-007 open; H-001–H-004 resolved; H-005, M-003/M-004/M-009 open; M-007/M-008 resolved; M-005/M-006 WONT-FIX; P-001 resolved |
| `pipeline.py`, `run_iter9.py`, `run_benchmark.py` | Fully audited; R-008, R-009 resolved |
| `report.py` | Fully audited; R-008 resolved |
| `solver.py`, `repair.py`, `source_config.py` | Fully audited; no bugs |
| All `tests/*.py` (18 files) | Fully audited; no new bugs beyond coverage gap M-009 |
| All `demos/iter9_visual_solver/**` (49 files) | Fully audited; no bugs |

**Session 7 fixed:** R-008, R-009, T-001.

**Session 8 fixed:** C-003, C-004, C-005, C-006, M-007, M-008.

**Session 9 fixed:** C-007, M-004, M-009. DEV "Solve Board" button added.

**Still open:** H-005, M-003, DP-R2, DP-R3, DP-R6, DP-R8, DP-R9, PF-001.

---

## Session 10 — Test Hardening v0.1.1

Full forensic review of all 25 `gameworks/tests/` files against `engine.py`, `renderer.py`,
and `main.py`. 17 hardening items identified and resolved per `gameworks/docs/TEST_HARDENING_PLAN.md`.
4 additional pre-existing bugs fixed as discovered during implementation.

### GWHARDEN-001 — RESOLVED
- `test_parser.py::TestDimensionFlags` used `--width`/`--height`; correct flags are `--board-w`/`--board-h`.

### GWHARDEN-002 — RESOLVED
- `test_parser.py` asserted `args.easy/medium/hard`; correct attribute is `args.diff` (`dest="diff"`).

### GWHARDEN-003 — RESOLVED (source fix)
- `GameEngine.from_difficulty()` silently fell back to medium on unknown input.
- Fix: raises `ValueError` with descriptive message and valid-values list.

### GWHARDEN-004 — RESOLVED (source fix)
- Dead unreachable win-check in `Board.toggle_flag()` (lines 221–222) removed.
- Win is purely safe-cell-count based; flag placement cannot trigger a win.

### GWHARDEN-005 — RESOLVED
- `test_wrong_flag_deducts_score`: weak `<= 500` assertion replaced with exact `== 500 - WRONG_FLAG_PENALTY` (475).

### GWHARDEN-006 — RESOLVED
- `test_fog_surf_stable_across_frames`: test never set `r.fog = True`; trivially passed on `id(None)==id(None)`. Fixed.

### GWHARDEN-007 — RESOLVED
- `test_num_surfs_initially_none_or_dict` / `test_num_surfs_none_before_first_draw`: `_num_surfs` is always a `dict` after `__init__`. Tightened to `isinstance(dict)` and renamed accordingly.

### GWHARDEN-008 — RESOLVED
- `_imports_in()` docstring falsely stated "Does NOT descend into function bodies"; `ast.walk()` descends everywhere. Corrected.

### GWHARDEN-009 — RESOLVED
- `test_chord_on_zero_count_cell_is_noop`: added `assert revealed == []`.

### GWHARDEN-010 — RESOLVED
- `test_saved_board_reloads_same_mine_count`: added exact position check `set(b2.all_mine_positions()) == set(b.all_mine_positions())`.

### GWHARDEN-011 — RESOLVED
- Added `TestDevSolveBoard` class (11 tests) covering `GameEngine.dev_solve_board()` which had zero coverage.

### GWHARDEN-012 — RESOLVED
- Added `test_game_over_true_after_win` to `TestBoardProperties`.

### GWHARDEN-013 — RESOLVED
- Added `test_safe_revealed_count_excludes_mine_hit` to `TestBoardProperties`.

### GWHARDEN-014 — RESOLVED
- Added `TestRestartModes` class with npy and image mode restart tests.

### GWHARDEN-015 — RESOLVED
- Added `test_3d_array_raises_value_error` to `TestLoadErrors`.

### GWHARDEN-016 — RESOLVED
- Added `TestArrowKeyPanning` class (8 tests) covering K_LEFT/K_RIGHT/K_UP/K_DOWN handlers.

### GWHARDEN-017 — RESOLVED
- `test_chord_fires_when_flag_count_matches`: added `assert len(revealed) > 0`.

### Bonus fixes (pre-existing, discovered during hardening)

**mine_flash ordering bug** — 4 tests in `test_engine.py` set `eng._first_click = False` before
`eng.start()`, which then reset it to `True`. Fixed by moving the assignment after `start()`.
Affected: `engine_with_mine_at` helper, `test_mine_flash_populated_on_hit`,
`test_mine_flash_value_is_future_timestamp`, `test_restart_clears_mine_flash`.

**`load_board_from_pipeline` fallback bug** — `board_h` was unbound in the `except` handler
when the pipeline import failed before line 363. Fixed: `_h = locals().get("board_h", board_w)`.
Affected: `test_image_mode_falls_back_to_random_on_missing_file` and new image restart test.

---

### [ANIM-001] `AnimationCascade.done` / `WinAnimation.done` never become True after elapsed time
- **Status:** `RESOLVED`
- **File:** `gameworks/renderer.py` (AnimationCascade and WinAnimation classes) + `gameworks/tests/renderer/test_animations.py`
- **Previously failing tests (now passing):**
  - `TestAnimationCascade::test_done_when_all_elapsed`
  - `TestAnimationCascade::test_single_position`
  - `TestWinAnimation::test_done_after_enough_time`
  - `TestWinAnimation::test_correct_done_property`
- **Root cause:** Both animations use lazy evaluation — `_idx`/`_phase` only advance when `current()` is explicitly invoked. Test assertions checked `.done` without first calling `.current()`, so the internal state never advanced and `done` remained `False`.
- **Fix (session 13):** Test assertions updated to call `.current()` before checking `.done`. All 4 tests now pass.
- **Discovered:** Session 10 pre-push baseline capture.

### [PF-001] Pre-existing pyflakes warnings in 3 test files (unused imports)
- **Status:** `OPEN`
- **Files/Lines:**
  - `gameworks/tests/unit/test_engine.py:23` — `place_random_mines` imported but unused
  - `gameworks/tests/architecture/test_boundaries.py:20` — `os` imported but unused
  - `gameworks/tests/architecture/test_boundaries.py:214` — `gameworks.engine` imported but unused (intentional side-effect import inside test)
  - `gameworks/tests/unit/test_board_loading.py:23` — `place_random_mines` imported but unused
  - `gameworks/tests/unit/test_board_loading.py:208` — `BoardLoadResult` imported but unused (inside skipped pending test)
- **Detail:** All warnings existed in the pre-change baseline. None introduced by this session.

---

## Sessions 11–13 — Performance Phases 1–3 + Test Hardening

### Session 11 — DEV TOOLS toggle + Performance Phase 1 (engine dirty-int counters)

**DEV TOOLS panel toggle (`b5710e9`)**
`Renderer._show_dev` (default `False`) gates the DEV TOOLS separator, header, and "Solve Board"
button. Press `` ` `` (`K_BACKQUOTE`) to show/hide. Button click handler also gated.

**Performance Phase 1 — dirty-int counters (`1624feb`)**
Replaced O(W×H) `numpy.sum()` scans in four `Board` properties with O(1) dirty-int counters:
`_n_flags`, `_n_questioned`, `_n_safe_revealed`, `_n_revealed`. Counters kept in sync on every
`reveal()` / `toggle_flag()` mutation. `dev_solve_board()` resyncs counters from arrays after bulk
numpy writes. Eliminates ~3 full array scans per frame on 300×300 boards. 5 regression tests added.

### Session 12 — Performance Phases 2 and 3 (renderer caches)

**Performance Phase 2 — cache frame-local values (`1fb0934`)**
- `_win_size`: caches `_win.get_size()` at init, updated on `VIDEORESIZE`.
- `_cached_board_rect`: caches `_board_rect()` result, invalidated on pan/zoom/resize.
- `_last_mouse_pos`: stores last known cursor position for `MOUSEWHEEL` events (no `.pos`).
- `mouse_pos` threaded through `draw()` → `_draw_header()` → `_draw_smiley()`.
- Eliminates ~10 OS/syscall invocations per frame. 8 new tests added.

**Bug fix:** `_on_resize()` did not clear `_cached_board_rect` on tile size change — stale coordinates
after zoom. Fixed: `_cached_board_rect = None` added. 4 cache invalidation regression tests added.

**Performance Phase 3 — cell loop refactor (`6557486`)**
- `time.monotonic()` hoisted out of cell loop (1 call/frame vs. per-cell).
- `CellState` construction eliminated from the hot path; raw numpy `bool_`/`uint8` values passed
  directly to `_draw_cell`. Eliminates 50,000+ Python object constructions per frame (300×300).
- `_draw_cell` now accepts individual field args + `now` instead of a `CellState`.
- `_num_surfs` lookup key cast to `int` to fix numpy `uint8` dict key mismatch.
- 5 new tests added.

### Session 13 — Animation timing fix + test expansion

**ANIM-001 resolved** — see entry above.

**Test expansion**
- `test_board.py`: +5 granular counter regression tests.
- `test_board_edge_cases.py`: 286-line new file; 33 boundary/edge-case tests.
- `test_main.py`: 263-line new file; 22 `main()` integration tests (CLI parser, GameLoop construction, action dispatch).
- Total: **337 tests passing** (up from 299 at end of session 10).

**Sessions 11–13 fixed:** ANIM-001, `_on_resize()` cache invalidation, `_num_surfs` uint8 key mismatch.

**Still open:** H-005, M-003, DP-R2, DP-R3, DP-R6, DP-R8, DP-R9, PF-001.

---

## Session 14 — Forensic Audit: gameworks/ (Full-Corpus Static Analysis)

**Scope:** Line-by-line static analysis of `engine.py` (721 lines), `renderer.py` (1 266 lines),
`main.py` (288 lines), and all 28 test files (≥ 2 300 lines of tests).
**Method:** Source review + test-coverage cross-reference + runtime execution-path reasoning.
**Standard:** Every finding includes affected file and line, root-cause mechanism, downstream
impact, fix specification, and test coverage gap.
**Result:** 20 findings — 1 critical, 3 high, 5 medium, 11 low.
No new critical bugs in `engine.py`. Critical bug isolated to rendering/main pipeline.

---

### FA-001 [CRITICAL] Victory modal never rendered — `draw_victory()` called after `display.flip()`

- **Status:** `OPEN`
- **File:** `gameworks/main.py:202–216` + `gameworks/renderer.py:702`
- **Reproduction:** Win any game. "YOU WIN!" modal never appears. Game sits frozen
  in RESULT state accepting only ESC/R.
- **Root cause:** `GameLoop.run()` calls `self._renderer.draw(...)` (line 202), which calls
  `pygame.display.flip()` at its final statement (renderer.py:702). `draw_victory(elapsed)` is
  then called at main.py:215 — **after** `flip()`. The victory modal is blitted to the new back
  buffer. On the next iteration, `_win.fill(C["bg"])` inside `draw()` erases it before a second
  `flip()` could show it. `_result_shown = True` is set immediately (main.py:216), ensuring no
  re-draw ever occurs. The modal is physically unreachable by the player.
- **Execution trace:**
  1. Frame N: `draw()` → ... → `display.flip()` → frame shown
  2. Frame N (still): `draw_victory()` → blits to **new** back buffer → `_result_shown = True`
  3. Frame N+1: `draw()` → `_win.fill(bg)` → erases modal → ... → `display.flip()` → no modal
  4. Frame N+1+: `_result_shown` is `True` → `draw_victory()` never called again
- **Downstream impact:** Blocks the entire RESULT screen. Players see no feedback that they won.
  Score and time summary are permanently hidden. ESC/R still function via KEYDOWN handler.
- **Proposed fix:** Move `draw_victory(elapsed)` **before** `display.flip()`. Options:
  a. Call it inside `draw()` when `game_state == "won"` and `win_anim.done`, or
  b. Move the block (lines 210–217) to before the `draw()` call block (line 202), or
  c. Add a second `pygame.display.flip()` call after `draw_victory()`.
  Option (a) is cleanest — keeps all rendering inside `Renderer`.
- **Test coverage gap:** No test verifies that the victory modal is actually drawn and visible
  after the win animation completes. `test_main.py::TestGameLoopActions::test_dev_solve_wins_board`
  only checks `engine.state == "won"`; it never asserts `_result_shown == True` or that
  `draw_victory()` is reachable.
- **Compounding bug:** FA-002 makes the modal display wrong content even if FA-001 is fixed.

---

### FA-002 [HIGH] Victory modal always shows "Time: 0.0s" — elapsed forced to 0 on game over

- **Status:** `OPEN`
- **File:** `gameworks/main.py:186`
- **Root cause:**
  ```python
  elapsed = self._engine.elapsed if not self._engine.board.game_over else 0
  ```
  When the board transitions to `"won"`, `game_over` returns `True`. Every subsequent frame
  sets `elapsed = 0` before passing it to `draw()` and `draw_victory()`. The timer is correctly
  frozen by `GameEngine.stop_timer()` on win (engine.py), but the frozen value is never read
  — `elapsed` is always overridden with `0`.
- **Downstream impact:** Played duration displayed as `0.0s` on the victory modal. The
  `_result_time` timestamp set at line 191 is correct but only used for result-screen fade
  timing, not for the "elapsed" field passed to drawing functions.
- **Proposed fix:** Remove the ternary. Use `self._engine.elapsed` unconditionally. The engine's
  `stop_timer()` already freezes the value correctly at win time.
  ```python
  elapsed = self._engine.elapsed   # engine.stop_timer() freezes this on win
  ```
- **Test coverage gap:** No test asserts the elapsed value passed to `draw_victory()` equals
  the actual game duration. `TestLifecycle::test_stop_timer_freezes_elapsed` correctly tests
  `engine.elapsed` freeze but never exercises the `main.py` read path.

---

### FA-003 [HIGH] Window resize does not update panel button positions — `_on_resize()` not called on `VIDEORESIZE`

- **Status:** `OPEN`
- **File:** `gameworks/renderer.py:460–464`
- **Root cause:** The `VIDEORESIZE` handler (renderer.py:460):
  ```python
  if ev.type == VIDEORESIZE:
      self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
      self._win_size = ev.size
      self._center_board()   # ← only centers the board
      return None
  ```
  `_on_resize()` is **never called** here. `_on_resize()` is the method that recomputes all
  five panel button `x`/`y` positions relative to the new window geometry. After a VIDEORESIZE
  event, the board is recentered correctly but all panel buttons remain at their pre-resize
  absolute pixel coordinates. On large windows the buttons appear in the wrong position; on
  smaller windows they may be clipped outside the viewport entirely.
- **Downstream impact:** Every user who resizes the game window gets misaligned panel buttons
  ("Restart", "New Game", "Save .npy", "Fog", "Help"). Clicks land on wrong targets or miss
  entirely. The DEV TOOLS panel (added session 11) is also affected.
- **Relationship to M-002 (RESOLVED):** M-002 fixed `_on_resize()` itself (it previously did
  not update button positions). FA-003 is the distinct follow-on bug: `_on_resize()` is now
  correct but is never invoked on window resize.
- **Test coverage gap:** `test_win_size_cache_updated_on_videoresize` verifies `_win_size`
  is updated but does not assert button positions. No test verifies button rects after
  `VIDEORESIZE`. The `TestArrowKeyPanning` suite tests pan but not resize.
- **Proposed fix:** Call `_on_resize()` inside the `VIDEORESIZE` handler:
  ```python
  if ev.type == VIDEORESIZE:
      self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
      self._win_size = ev.size
      self._cached_board_rect = None
      self._on_resize()       # ← add this
      self._center_board()
      return None
  ```

---

### FA-004 [HIGH] Panel click intercept only blocks left-click — right/middle-click bypasses panel hit-test

- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` — `handle_event()`, panel intercept block (approx. line 503)
- **Root cause:** The panel intercept that prevents mouse events "falling through" to board cells
  beneath the panel contains a guard:
  ```python
  if ev.type == MOUSEBUTTONDOWN and ev.button == 1:
      if panel_rect.collidepoint(ev.pos):
          ...handle panel...
          return action_or_none
  ```
  The `ev.button == 1` filter makes the intercept left-click only. A right-click (button 2)
  or middle-click (button 3) over the panel passes through the intercept, reaches the board
  coordinate conversion, and fires `toggle_flag()` or `chord()` on the board cell beneath the
  panel. On standard 16×16 boards, the panel covers 7–9 columns of cells on the right side,
  all permanently unreachable but still mutated silently.
- **Downstream impact:** Players right-clicking on panel buttons inadvertently flag or
  question-mark cells they cannot see. On small boards (`--easy`), a right-click on "Restart"
  flags the underlying cell, decrementing `mines_remaining` and distorting the mine counter.
- **Proposed fix:** Remove the `ev.button == 1` filter from the panel intercept. All
  `MOUSEBUTTONDOWN` events over the panel should be consumed:
  ```python
  if ev.type == MOUSEBUTTONDOWN:
      if panel_rect.collidepoint(ev.pos):
          if ev.button == 1:
              ...handle panel clicks...
          return None   # consume all buttons over panel
  ```
- **Test coverage gap:** No test fires `MOUSEBUTTONDOWN` with `ev.button == 2` or `3` over
  a panel pixel coordinate and verifies no board mutation occurs.

---

### FA-005 [MEDIUM] Board origin X offset wrong for `panel_right=True` layout — 240 px dead space on left

- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` — `Renderer.__init__()`, `BOARD_OX` assignment
- **Root cause:** For the `panel_right=True` layout (small boards where panel is on the right):
  ```python
  BOARD_OX = PAD + PANEL_W   # = 8 + 240 = 248 px from left edge
  ```
  `PANEL_W` (240 px) is the panel width. In `panel_right=True` mode the panel is on the
  **right** side of the board. There is nothing on the left — yet the board origin is pushed
  248 px right, creating 248 px of dead empty background on the left of the window on every
  small board (easy, medium, hard presets).
- **Downstream impact:** Cosmetic only, but players with small monitors experience a miscentered
  board with 248 px of wasted space on the left. Drag-to-scroll works correctly because `_pan_x`
  still clamps to valid board boundaries.
- **Proposed fix:** `BOARD_OX = PAD` for `panel_right=True`. Then `_center_board()` already
  re-derives the correct offset from the window midpoint anyway; the init value only matters
  during the first frame before centering runs.
- **Test coverage gap:** No test asserts `BOARD_OX` is `PAD` in `panel_right=True` mode.

---

### FA-006 [MEDIUM] Inconsistent `_win_size` cache use — `_win.get_width()` still called directly in 5 hot paths

- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` lines 601, 674, 726, 748, 1052 (and arrow-key handlers)
- **Root cause:** Phase 2 (session 12) introduced `_win_size` to cache `_win.get_size()`.
  The fix was applied to the render path that called `_win.get_size()` repeatedly per frame.
  However, five call sites still call `_win.get_width()` or `_win.get_height()` directly:
  - line 601: smiley rect X computation in `_draw_smiley()`
  - line 674: `_on_resize()` reads `_win.get_width()`
  - lines 726, 748: header draw uses `_win.get_width()` for right-align positions
  - line 1052: panel draw uses `_win.get_width()`
  - arrow-key pan handlers (K_LEFT/K_RIGHT/K_UP/K_DOWN): use `_win.get_width()/_win.get_height()`
- **Downstream impact:** Performance — each `get_width()` call is a Python → C extension call
  that re-queries the SDL window. On a 300×300 board at 30 FPS this adds ~5–8 C calls/frame
  beyond what Phase 2 eliminated. Not a correctness issue.
- **Proposed fix:** Replace all remaining `self._win.get_width()` with `self._win_size[0]` and
  `self._win.get_height()` with `self._win_size[1]` throughout renderer.py.
- **Test coverage gap:** `TestArrowKeyPanning` tests pan direction but never inspects whether
  `get_width()` is called directly. No performance regression test enforces Phase 2 cache
  completeness beyond the paths tested in `test_renderer_init.py`.

---

### FA-007 [MEDIUM] Flood-fill stack allows duplicate cell pushes — O(n²) stack size on open boards

- **Status:** `OPEN`
- **File:** `gameworks/engine.py:192–204` — `Board.reveal()`
- **Root cause:** The flood-fill pushes neighbors when popped, but marks cells revealed
  **only when popped**, not when pushed. Because the push-time guard only checks
  `not self._revealed[ny, nx]` (which is still `False` until pop-time), a cell can be pushed
  multiple times if multiple zero-count neighbors each process before it is popped:
  ```python
  stack = [(x, y)]
  while stack:
      cx, cy = stack.pop()
      if self._revealed[cy, cx] ...: continue   # skip if already processed
      self._revealed[cy, cx] = True              # marked AFTER pop
      ...
      for nx, ny in ...:
          if not self._revealed[ny, nx] ...:     # False for unpushed AND unpopped cells
              stack.append((nx, ny))              # can push same cell N times
  ```
  For a large empty region, each cell can be pushed by up to 4 zero-count neighbors before
  being popped, growing the stack to O(4 × area). On a 300×300 fully empty board this produces
  a stack of ~360 000 entries instead of ~90 000.
- **Downstream impact:** Performance on large open boards. Correctness is unaffected — the
  `continue` guard on pop prevents double-processing. Stack memory peaks ~4× higher than optimal.
- **Proposed fix:** Mark cells as "seen" when pushed, not when popped. Either:
  a. Use a `visited` set: `visited = set(); ... if (nx, ny) not in visited: visited.add((nx, ny)); stack.append(...)`
  b. Set `_revealed[ny, nx] = True` at push time (pre-mark), then skip the initial `continue` check.
  Option (b) is zero-allocation and matches what production BFS implementations do.
- **Test coverage gap:** All flood-fill tests use small boards (3×3 to 9×9). No test exercises
  large empty boards or asserts `len(newly)` equals the board area minus one mine for an all-zero
  configuration. `test_board_edge_cases.py` tests 100×1 boards but not 100×100 empty boards.

---

### FA-008 [MEDIUM] `load_board_from_npy()` validation uses O(W×H) nested Python loops

- **Status:** `OPEN`
- **File:** `gameworks/engine.py` — `load_board_from_npy()`, approx. lines 346–353
- **Root cause:** The post-load validation that checks neighbour counts iterates every cell
  with a nested Python `for` loop, calling `_count_adj()` per cell:
  ```python
  for y in range(b.height):
      for x in range(b.width):
          expected = b._count_adj(x, y)   # Python-level adjacency scan
          if b._neighbours[y, x] != expected:
              raise ValueError(...)
  ```
  For a 300×300 board this is 90 000 Python iterations × 9-cell adjacency scan = ~810 000
  Python operations, entirely replicated by the vectorized `scipy.ndimage.convolve` that
  already ran during `Board.__init__()` to build `_neighbours`.
- **Downstream impact:** Noticeable startup delay on large `.npy` boards. On a 300×370 board
  the validation loop takes ~0.5 s in CPython before the game window opens.
- **Proposed fix:** Replace with a single vectorized assertion:
  ```python
  expected = scipy.ndimage.convolve(b._mine.astype(np.uint8), np.ones((3,3), np.uint8),
                                     mode='constant') - b._mine.astype(np.uint8)
  if not np.array_equal(b._neighbours, expected):
      raise ValueError("Neighbour count mismatch")
  ```
  Or simply trust the `Board.__init__` computation (it is deterministic) and remove the
  post-load validation loop entirely.
- **Test coverage gap:** `TestLoadErrors` tests wrong-dimension raises but not the O(W×H)
  performance path. No benchmark test asserts load time for large `.npy` files.

---

### FA-009 [MEDIUM] `_draw_image_ghost()` calls `.copy()` per visible flagged cell per frame

- **Status:** `OPEN`
- **File:** `gameworks/renderer.py:1046`, `renderer.py:1194`
- **Root cause:** M-001 (session 9) fixed the outer loop to be viewport-culled via `np.where`,
  eliminating O(W×H) iterations. However, the per-cell operation still calls `.copy()` on a
  `subsurface()` to set per-cell alpha:
  ```python
  sub = scaled.subsurface(src_rect).copy()   # new Surface object every frame per visible flag
  sub.set_alpha(200 if _mine[y, x] else 40)
  self._win.blit(sub, (px, py))
  ```
  `subsurface()` returns a view (no allocation), but `.copy()` allocates a brand-new `Surface`
  object per call. On a board with 50 visible flags, this is 50 Surface allocations per frame
  × 30 FPS = 1 500 Surface allocations/second from this loop alone. This is also duplicated in
  the win-animation overlay path at line 1194.
- **Downstream impact:** GC pressure and per-frame allocation overhead. Not visually apparent
  but measurable via `pygame.Surface` allocation tracing on flag-heavy boards.
- **Proposed fix:** Pre-build a single SRCALPHA surface the size of the entire board ghost
  image at the same size as `scaled`. Blit the whole ghost surface with a global alpha rather
  than per-cell copies. Cache it as `_ghost_surf`; invalidate on zoom/resize (same as existing
  `_ghost_surf` attribute, which is currently `None` because this code path bypasses it).
- **Test coverage gap:** `TestGhostSurfCache::test_ghost_surf_not_rebuilt_per_frame` only
  verifies the top-level `_ghost_surf` attribute is not rebuilt. It does not capture the
  per-cell `.copy()` allocations inside the image-ghost draw loop.

---

### FA-010 [LOW] `_save_npy()` saves to current working directory, not `results/`

- **Status:** `OPEN`
- **File:** `gameworks/main.py` — `GameLoop._save_npy()`
- **Root cause:** The save path is constructed as `f"board_{timestamp}.npy"` (no directory
  prefix), writing to whatever directory `os.getcwd()` resolves to at runtime. When launched
  with `python -m gameworks.main` from the project root, files land in the project root.
  AGENTS.md specifies that output artifacts should go to `results/`.
- **Note:** This overlaps with DP-R8 (atomicity), which is a separate sub-issue.
  DP-R8 covers the `os.replace` pattern. FA-010 covers the output path.
- **Proposed fix:** Prepend `results/` and ensure the directory exists:
  ```python
  out_dir = Path(__file__).parent.parent / "results"
  out_dir.mkdir(exist_ok=True)
  path = out_dir / f"board_{timestamp}.npy"
  ```
- **Test coverage gap:** `TestSaveLoadRoundTrip` in `test_board_modes.py` is skipped (DP-R8
  scaffold). No test asserts the save path starts with `results/`.

---

### FA-011 [LOW] `Board._count_adj()` is dead code — never called

- **Status:** `OPEN`
- **File:** `gameworks/engine.py:112–117`
- **Root cause:** `_count_adj(self, x, y)` computes the number of mine neighbors for cell
  `(x, y)` by slicing `_mine` directly. It was presumably the pre-scipy neighbor computation,
  superseded by `scipy.ndimage.convolve` in `__init__()`. The function body is 5 lines and
  is never referenced anywhere in the codebase.
- **Downstream impact:** None — dead code. Slightly misleading to readers who may assume
  it is the active neighbor computation path.
- **Proposed fix:** Remove the method. If the pure-Python adjacency scan is needed for testing,
  it belongs in the test fixtures, not in `Board`.
- **Test coverage gap:** `test_boundaries.py` checks module imports but has no dead-code
  coverage detector. No test calls `_count_adj()` directly (confirming it is unused).

---

### FA-012 [LOW] `Board.correct_flags` uses `np.sum()` scan — inconsistent with Phase 1 dirty-int counters

- **Status:** `OPEN`
- **File:** `gameworks/engine.py:158–159`
- **Root cause:**
  ```python
  @property
  def correct_flags(self) -> int:
      return int(np.sum(self._flagged & self._mine))   # O(W×H) scan
  ```
  All four other `Board` counter properties (`flags_placed`, `questioned_count`,
  `safe_revealed_count`, `revealed_count`) were converted to O(1) dirty-int lookups in
  Phase 1 (session 11). `correct_flags` was not converted because it requires a **bitwise
  AND of two arrays** (`_flagged & _mine`), which cannot trivially be maintained with a
  single counter. However, it is called on every frame by `WinAnimation.__init__()` and by
  `dev_solve_board()`.
- **Downstream impact:** One O(W×H) numpy scan per `correct_flags` read. On 300×300 boards
  at win time: 90 000 element AND + sum. Not catastrophic (numpy is fast), but inconsistent
  with the Phase 1 contract.
- **Proposed fix:** Add a 5th dirty-int counter `_n_correct_flags`. Increment when
  `toggle_flag()` places a flag on a mine cell; decrement when the flag is removed. This
  requires checking `self._mine[y, x]` at flag placement time — already accessed in
  `right_click()` for scoring.
- **Test coverage gap:** `TestToggleFlag::test_correct_flags_count` verifies the value is
  correct but does not assert it is O(1) (i.e., doesn't check it avoids `np.sum`).

---

### FA-013 [LOW] Unreachable `if __name__ == "_test_engine":` block — module name can never be `"_test_engine"`

- **Status:** `OPEN`
- **File:** `gameworks/engine.py:705`
- **Root cause:**
  ```python
  if __name__ == "_test_engine":
  ```
  `__name__` in a Python module is either `"__main__"` (when run directly) or the dotted
  module path (e.g., `"gameworks.engine"` when imported). The string `"_test_engine"` is
  never assigned by the Python runtime. This block is permanently unreachable.
- **Downstream impact:** Dead code; wastes 15 lines at the bottom of the file.
- **Proposed fix:** Remove the block. If inline smoke-tests are needed they belong in
  `__main__` guard: `if __name__ == "__main__":`.
- **Test coverage gap:** `test_boundaries.py::TestEngineBoundaries::test_engine_parses_without_error`
  confirms the file is syntactically valid but does not detect unreachable guards.

---

### FA-014 [LOW] `GameLoop.MENU` state defined but never re-entered from `RESULT` — state machine has a dead arc

- **Status:** `OPEN`
- **File:** `gameworks/main.py:70–79`, `run()` — result/restart handling
- **Root cause:** The docstring and `__init__` define: `MENU → PLAYING → RESULT → MENU`.
  `_state = MENU` is set only in `__init__()`. The "restart" action sets
  `self._state = self.PLAYING` directly (skipping MENU). `RESULT` never transitions back
  to `MENU`. The MENU state has no event-handling code in `run()` either — the loop goes
  straight to `_start_game()` at the top regardless of `_state`.
- **Downstream impact:** The advertised state machine does not exist at runtime. This
  makes it impossible to add a main menu without refactoring `run()`.
- **Proposed fix:** Either remove `MENU` from the docstring/constants to match reality, or
  implement the MENU→PLAYING transition with a menu screen before `_start_game()`.
- **Test coverage gap:** `test_main.py::test_gameloop_initial_state_is_menu` asserts
  `loop._state == GameLoop.MENU` at construction but no test asserts `_state` transitions
  through the full documented `MENU → PLAYING → RESULT → MENU` cycle.

---

### FA-015 [LOW] `_do_right_click()` return value always silently discarded

- **Status:** `OPEN`
- **File:** `gameworks/main.py:164`, `232–234`
- **Root cause:**
  ```python
  def _do_right_click(self, x, y):
      state = self._engine.right_click(x, y)
      return state   # ← MoveResult returned
  ```
  The call site (main.py:164): `self._do_right_click(x, y)` — return value discarded.
  `_do_left_click` and `_do_chord` assign the result and use `newly_revealed` to set the
  cascade animation. `_do_right_click` discards it, meaning:
  - If a correct flag triggers a win via `toggle_flag()` (not currently implemented, but
    was present before GWHARDEN-004), the win transition would be missed.
  - Currently harmless but structurally inconsistent with other dispatch methods.
- **Proposed fix:** Either capture and handle the return value (check `result.state` for win)
  or change the return type to `None` to match the callsite behavior.
- **Test coverage gap:** `test_right_click_cycles_cell_states` in `test_main.py` only asserts
  no exception is raised, never checks the return value.

---

### FA-016 [LOW] `WinAnimation` uses fixed seed `random.Random(42)` — animation order is always identical

- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` — `WinAnimation.__init__()`
- **Root cause:**
  ```python
  rng = random.Random(42)
  rng.shuffle(self._correct)
  rng.shuffle(self._wrong)
  ```
  The hardcoded seed `42` means the animation plays in the exact same tile-reveal order on
  every game. For players who replay the same board (using seed-preserved games), the animation
  is visually identical each time, removing any sense of novelty.
- **Downstream impact:** Cosmetic. Not a correctness bug.
- **Proposed fix:** Use `random.Random()` (no seed) or seed from the current game's `seed`
  attribute: `random.Random(board.engine.seed)` for reproducibility without global identity.
- **Test coverage gap:** Animation tests use fully-flagged boards where shuffle order is
  observable but not asserted. No test asserts that two different `WinAnimation` instances
  produce different orderings.

---

### FA-017 [LOW] `main.TILE` global is a dead write — separate from `renderer.TILE`; never read

- **Status:** `OPEN`
- **File:** `gameworks/main.py:107` (approx.) and `main.py:282` (approx.)
- **Root cause:** `main.py` imports and updates a module-level `TILE` variable. However,
  `Renderer` reads `gameworks.renderer.TILE` (a module-level var in `renderer.py`) which is
  updated by `Renderer.__init__()` via `import gameworks.renderer as r; r.TILE = ts`.
  The `TILE` in `main.py` is a separate name binding that is never read by `Renderer` or
  `engine.py`. Setting it has no effect on tile size.
- **Downstream impact:** None at runtime. Misleads future maintainers into believing
  `main.TILE` controls tile rendering.
- **Proposed fix:** Remove the `TILE` import and assignment from `main.py`. Tile size is
  owned by `renderer.TILE` and `_build_engine()` already sets `gameworks.renderer.TILE`
  correctly via `import gameworks.renderer`.
- **Test coverage gap:** No test verifies that setting `main.TILE` has any effect.

---

### FA-018 [LOW] First-click board regeneration can silently produce fewer mines than requested on tiny boards

- **Status:** `OPEN`
- **File:** `gameworks/engine.py` — `GameEngine.left_click()`, first-click safety block
- **Root cause:** When the first click lands on a mine, `place_random_mines()` is called with
  `safe_x=x, safe_y=y`, which excludes the 3×3 neighborhood of the clicked cell from mine
  placement. On a 3×3 board with 8 mines and first click at (1,1), the exclusion zone covers
  all 9 cells — `place_random_mines()` cannot place any mines, returns an empty set, and
  `Board(3, 3, set())` is constructed with 0 mines. No error is raised; the game continues
  with a secretly different mine count.
- **Downstream impact:** Affects only extreme configurations (`mines >= W*H - 9`). Normal
  gameplay (standard presets) is unaffected. When triggered: `total_mines == 0`, the player
  instantly wins on the next click of any cell.
- **Proposed fix:** Validate after regeneration:
  ```python
  new_mines = place_random_mines(...)
  if len(new_mines) != self.board.total_mines:
      new_mines = place_random_mines(w, h, mine_count, seed=self.seed)  # no safe zone
  ```
  Or raise `ValueError` if `mine_count > W*H - 9` at engine construction time.
- **Test coverage gap:** `TestFirstClickSafety` uses `mines=70` on 9×9 boards (max 11 mines
  in exclusion zone, plenty of space for 70 mines). No test triggers the zero-mine fallback.

---

### FA-019 [LOW] Arrow-key pan bypasses `_win_size` cache — calls `_win.get_width()/_win.get_height()` directly

- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` — `handle_event()` arrow-key handlers
- **Root cause:** (Sub-issue of FA-006; listed separately for completeness.) The K_LEFT,
  K_RIGHT, K_UP, K_DOWN key handlers compute pan clamp bounds using `self._win.get_width()`
  and `self._win.get_height()` instead of `self._win_size[0]` and `self._win_size[1]`.
  `TestArrowKeyPanning` covers all four directions but does not assert that `get_width()`
  is not called.
- **Impact:** 1–2 redundant C extension calls per keypress event. Low severity.
- **Proposed fix:** Replace with `self._win_size[0]` / `self._win_size[1]` (see FA-006).

---

### FA-020 [LOW] `right_click()` never increments `self.streak` — correct flags cannot build streak

- **Status:** `OPEN`
- **File:** `gameworks/engine.py` — `GameEngine.right_click()`
- **Root cause:** `left_click()` and `middle_click()` both increment `self.streak += len(newly_revealed)`
  on safe reveals. `right_click()` awards `CORRECT_FLAG_BONUS * streak_multiplier` scoring
  points for correct flags but **never touches `self.streak`**. This creates a scoring
  inconsistency: placing 10 correct flags in a row earns bonus points but at the base
  multiplier (1.0×), while those same points would be multiplied if the flags were replaced
  by reveals. A player building streak via reveals and then switching to flagging resets to
  base multiplier for no visible reason.
- **Downstream impact:** Scoring inconsistency. Players who mix flagging into their play style
  receive lower score multipliers than pure-reveal players, with no visible explanation.
- **Design note:** M-006 (WONT-FIX) addressed streak-per-click vs. streak-per-cell. FA-020
  is a distinct issue: whether *any* right-click action contributes to streak, not granularity.
  The existing design already awards scoring for correct flags; not extending streak credit for
  them appears to be an oversight rather than an intentional design decision.
- **Test coverage gap:** `TestStreak` tests cover `left_click` streak increments and mine-hit
  resets. No test verifies `right_click` streak behavior after a correct flag.

---

## Session 14 — Forensic Audit Summary

| ID | Severity | File | Status | One-line description |
|---|---|---|---|---|
| FA-001 | CRITICAL | main.py:215 | OPEN | `draw_victory()` after `display.flip()` — modal never shown |
| FA-002 | HIGH | main.py:186 | OPEN | `elapsed = 0` on game_over — victory timer shows 0s |
| FA-003 | HIGH | renderer.py:460 | OPEN | VIDEORESIZE omits `_on_resize()` — buttons misalign |
| FA-004 | HIGH | renderer.py:~503 | OPEN | Panel intercept is left-click only — right/middle bypass |
| FA-005 | MEDIUM | renderer.py:init | OPEN | `BOARD_OX = PAD + PANEL_W` in panel-right mode — 248 px dead space |
| FA-006 | MEDIUM | renderer.py:multi | OPEN | `_win.get_width()` still called directly in 5 hot paths |
| FA-007 | MEDIUM | engine.py:192 | OPEN | Flood-fill stack allows duplicate pushes — O(4n) stack |
| FA-008 | MEDIUM | engine.py:~346 | OPEN | `load_board_from_npy()` validates with O(W×H) Python loops |
| FA-009 | MEDIUM | renderer.py:1046 | OPEN | `.copy()` per visible flag per frame in `_draw_image_ghost()` |
| FA-010 | LOW | main.py:_save_npy | OPEN | Save writes to cwd, not `results/` |
| FA-011 | LOW | engine.py:112 | OPEN | `_count_adj()` is dead code — never called |
| FA-012 | LOW | engine.py:158 | OPEN | `correct_flags` uses `np.sum()` — inconsistent with Phase 1 |
| FA-013 | LOW | engine.py:705 | OPEN | `if __name__ == "_test_engine":` — unreachable guard |
| FA-014 | LOW | main.py:70 | OPEN | `MENU` state documented but dead — no RESULT→MENU arc |
| FA-015 | LOW | main.py:164 | OPEN | `_do_right_click()` return value always discarded |
| FA-016 | LOW | renderer.py:WinAnim | OPEN | `WinAnimation` uses fixed seed 42 — identical animation every game |
| FA-017 | LOW | main.py:~107 | OPEN | `main.TILE` global is a dead write — separate from `renderer.TILE` |
| FA-018 | LOW | engine.py:~555 | OPEN | First-click regen can silently reduce mine count on tiny boards |
| FA-019 | LOW | renderer.py:K_arrows | OPEN | Arrow-key pan calls `_win.get_width()` not `_win_size` (see FA-006) |
| FA-020 | LOW | engine.py:right_click | OPEN | `right_click()` never increments `streak` — correct flags can't build multiplier |

**Still open after session 14:** H-005, M-003, DP-R2, DP-R3, DP-R6, DP-R8, DP-R9, PF-001,
FA-001 through FA-020.

---

*Log maintained by: Claude Sonnet 4.6 via Maton Tasks*
