# Mine-Streaker — Gameworks Issue Log

Canonical record of all known bugs, design gaps, and forensic findings across the `gameworks/` package.
Each entry carries a status, severity, and resolution notes.

**Branch:** `frontend-game-mockup`
**Last updated:** 2026-05-10 (session 9 — C-007/M-009 fixed; DEV solve feature added)

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

**Still open:** H-005, M-003, DP-R2, DP-R3, DP-R6, DP-R8, DP-R9.

*Log maintained by: Claude Sonnet 4.6 via Maton Tasks*
