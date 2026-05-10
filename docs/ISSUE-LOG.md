# Mine-Streaker — Gameworks Issue Log

Canonical record of all known bugs, design gaps, and forensic findings across the `gameworks/` package.
Each entry carries a status, severity, and resolution notes.

**Branch:** `frontend-game-mockup`
**Last updated:** 2026-05-10

---

## Status legend

| Badge | Meaning |
|-------|---------|
| `RESOLVED` | Fixed and committed |
| `WONT-FIX` | Acknowledged; intentional or out-of-scope |
| `OPEN` | Known, not yet fixed |
| `PENDING-TEST` | Fix applied; needs runtime verification |

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

## Medium — Shallow implementations / design gaps

### [M-001] `_draw_image_ghost` ignores viewport culling
- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` — `_draw_image_ghost()`
- **Detail:** Iterates every cell on the board (all `width × height`), calling `board.snapshot()` per cell to check `is_flagged`. For a 300×300 board this is 90 000 snapshot calls per frame even when only ~50 cells are visible. The main `_draw_board` already computes `tx0/ty0/tx1/ty1` viewport bounds; this method should use them too.
- **Impact:** Frame-time regression proportional to board size in image mode.

---

### [M-002] `_on_resize()` does not update button Y positions after zoom
- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` — `_on_resize()`
- **Detail:** For boards ≥ 100 tiles wide (`_panel_right = False`) the panel sits below the board. `_on_resize` recalculates `oy = BOARD_OY + board.height * tile + PAD` but never assigns it to `self._btn_*.y`. Button hit areas drift from their visible positions after any zoom.
- **Impact:** Buttons become unclickable after zooming on large boards (npy/image mode).

---

### [M-003] Panel has two buttons that do identical things
- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` — `_draw_panel()` / `handle_panel()`
- **Detail:** "Restart" and "New Game" both return `"restart"`, which calls `engine.restart()` (creates new board, bumps seed). One should be "Retry" (re-play the exact same board layout, seed unchanged) vs "New Game" (fresh random board).
- **Impact:** Shallow UX; no way to retry the same layout after a bad run.

---

### [M-004] WinAnimation produces no animation when player wins without flags
- **Status:** `OPEN`
- **File:** `gameworks/renderer.py` — `WinAnimation.__init__()` / `start_win_animation()`
- **Detail:** `WinAnimation` builds its reveal list from flagged cells only. When the player wins by revealing all safe cells without placing any flags, `_all_positions` is empty and `done = True` immediately — the victory modal appears instantly with no animation. In classic mode with no image overlay this also means no visual fanfare at all.
- **Impact:** Anti-climactic win screen in the most common playstyle (reveal-only).

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

*Log maintained by: Claude Sonnet 4.6 via Maton Tasks*
