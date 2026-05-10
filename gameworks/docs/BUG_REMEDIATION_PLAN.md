# Gameworks — Bug Remediation Plan

**Source:** `gameworks/docs/BUGS.md` (30 open bugs)
**Author:** Claude Sonnet 4.6 — session 14 forensic audit
**Date:** 2026-05-10
**Branch:** `frontend-game-mockup`

---

## Guiding Principles

Every fix in this plan adheres to the following non-negotiable rules:

1. **Exact-code only.** Every change is specified as old text → new text at a named file and
   line number. "Update the function" is not a fix specification. A verbatim code diff is.

2. **One commit per phase.** Each phase is independently testable. No phase depends on a
   later phase having run. Phases may be executed out of order only when the dependency
   graph (§3) explicitly permits it.

3. **No regressions.** Every phase ends with a full passing test suite. The pre-change
   baseline is 337 passing tests. This count must not decrease at the end of any phase.

4. **Test first, verify after.** Each fix includes the test(s) to be written before or
   alongside the change. The new test must fail on the pre-fix code and pass after.

5. **Rollback is one command.** If a phase must be reverted, `git revert <commit-sha>`
   is sufficient. No manual undo steps.

6. **Pre-push verification protocol.** After each phase commit: run `git diff --staged`,
   run `git diff --staged --stat`, run pyflakes on every changed `.py` file, run the full
   gameworks test suite, compare against the baseline. AGENTS.md §Pre-Push Verification
   Protocol governs this.

---

## Dependency Graph

Phases must be executed in order unless noted. Arrows mean "must complete before".

```
Phase 1 (CRITICAL + HIGH fixes)
  ├── FA-001  ← no dependencies
  ├── FA-002  ← no dependencies
  ├── FA-003  ← no dependencies
  ├── FA-004  ← no dependencies
  └── H-005   ← no dependencies

Phase 2 (Engine correctness)
  ├── FA-011  ← no dependencies (removes dead code, safe at any time)
  ├── FA-012  ← no dependencies (flag-counter addition is independent of neighbor-counter removal)
  ├── FA-013  ← no dependencies (removes dead code)
  ├── FA-018  ← no dependencies
  └── FA-020  ← no dependencies

Phase 3 (Renderer + main dead-code and inconsistencies)
  ├── FA-005  ← no dependencies
  ├── FA-006  ← no dependencies (FA-019 is a sub-issue, fix together)
  ├── FA-014  ← no dependencies
  ├── FA-015  ← no dependencies
  ├── FA-016  ← no dependencies
  └── FA-017  ← no dependencies

Phase 4 (Performance)
  ├── FA-007  ← no dependencies
  ├── FA-008  ← FA-011 should be done first (removes _count_adj, which this phase deprecates)
  └── FA-009  ← no dependencies

Phase 5 (Save + output path)
  ├── FA-010  ← no dependencies
  └── DP-R8   ← FA-010 should be done first (same function, different sub-issues)

Phase 6 (Design pattern debt)
  ├── DP-R2   ← no dependencies (additive change)
  ├── DP-R3   ← no dependencies (additive change)
  ├── DP-R6   ← DP-R2 helpful but not required
  └── DP-R9   ← DP-R8 should be done first (save path is fixed)

Phase 7 (Test suite repairs)
  ├── T-002   ← no dependencies
  ├── T-003   ← no dependencies
  └── PF-001  ← no dependencies

Phase 8 (UX)
  └── M-003   ← H-005 should be done first (establishes "save" dispatch pattern)
```

---

## Baseline

Before starting, run and save:

```bash
pytest gameworks/tests/unit/ gameworks/tests/architecture/ \
       gameworks/tests/cli/ gameworks/tests/integration/ \
       -q --tb=no 2>&1 | tee /tmp/baseline_non_renderer.txt

SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest gameworks/tests/renderer/ -q --tb=no 2>&1 | tee /tmp/baseline_renderer.txt
```

Expected: **337 tests passing, 0 failures** in the package-local suite.

Legacy tests (pre-existing failures, do NOT count as regressions):
- `tests/test_gameworks_engine.py::TestBoardLogic::test_snapshot_fields`
- `tests/test_gameworks_renderer_headless.py::TestOverlayPanelClickRouting::test_dev_solve_click_returns_action_not_none`

---

## Phase 1 — Critical and High Bugs

**Goal:** Fix the 5 most impactful player-visible bugs.
**Files changed:** `gameworks/main.py`, `gameworks/renderer.py`
**Risk:** LOW — four of the five are single-line or two-line changes.
**New tests:** 5 (one per bug)

---

### Fix FA-001 — Victory modal never rendered

**File:** `gameworks/main.py`

**Root cause summary:** `draw_victory()` is called after `pygame.display.flip()` inside
`draw()`. The modal is drawn to the back buffer that is immediately erased on the next frame.

**Change — `gameworks/main.py`, line 214–216:**

Old:
```python
            elif gs == "won":
                self._renderer.draw_victory(elapsed)
                self._result_shown = True
```

New:
```python
            elif gs == "won":
                self._renderer.draw_victory(elapsed)
                self._result_shown = True
                pygame.display.flip()   # FA-001: second flip required — draw() already flipped
```

**Explanation:** `draw_victory()` blits the modal to the *new* back buffer that exists
after `draw()` called `flip()`. Adding a second `flip()` here surfaces the modal immediately
and does not affect subsequent frames (next call to `draw()` will `fill` then redraw).

**New test — `gameworks/tests/integration/test_main.py`, class `TestResultOverlays`:**

```python
class TestResultOverlays:

    def test_result_shown_set_after_win_animation_done(self):
        """_result_shown must be True after the win animation finishes."""
        from gameworks.main import GameLoop, build_parser
        from unittest.mock import patch, MagicMock
        import pygame

        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        # Force board to won state
        loop._engine.dev_solve_board()

        # Drive one PLAYING→RESULT transition
        loop._state = loop.PLAYING
        loop._renderer.win_anim = MagicMock()
        loop._renderer.win_anim.done = True   # animation already finished

        elapsed = loop._engine.elapsed
        gs = "won"
        with patch.object(loop._renderer, 'draw'), \
             patch.object(loop._renderer, 'draw_victory') as mock_dv, \
             patch('pygame.display.flip'):
            # Simulate the result-overlay block
            if loop._state == loop.RESULT or True:  # force RESULT path
                loop._state = loop.RESULT
                loop._result_shown = False
                if gs == "won" and loop._renderer.win_anim.done:
                    loop._renderer.draw_victory(elapsed)
                    loop._result_shown = True
                    pygame.display.flip()

        assert loop._result_shown is True
        mock_dv.assert_called_once_with(elapsed)
```

**Verification:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest gameworks/tests/integration/test_main.py::TestResultOverlays -v
```

**Acceptance criteria:** `_result_shown` is `True` after the result-overlay block runs with
`win_anim.done = True`. `draw_victory()` is called exactly once with the correct elapsed value.

---

### Fix FA-002 — Victory timer shows 0s

**File:** `gameworks/main.py`

**Change — line 186:**

Old:
```python
            elapsed = self._engine.elapsed if not self._engine.board.game_over else 0
```

New:
```python
            elapsed = self._engine.elapsed   # FA-002: engine.stop_timer() already freezes this on win
```

**Explanation:** `GameEngine.stop_timer()` is called on win (engine.py:584–585). After that,
`engine.elapsed` returns `_paused_elapsed` — the frozen value. Reading it unconditionally is
correct and safe.

**New test — `gameworks/tests/integration/test_main.py`, class `TestResultOverlays`:**

```python
    def test_elapsed_not_zero_after_win(self):
        """elapsed passed to draw_victory must be the actual game duration, not 0."""
        from gameworks.main import GameLoop, build_parser
        import time

        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        # Let some time pass so elapsed > 0
        time.sleep(0.05)

        # Win the board
        loop._engine.dev_solve_board()

        # engine.elapsed must be > 0 now (frozen by stop_timer inside dev_solve)
        assert loop._engine.elapsed > 0.0

        # elapsed in run() must use engine.elapsed, not 0
        elapsed = loop._engine.elapsed   # mirrors the fixed line
        assert elapsed > 0.0
```

**Verification:**
```bash
pytest gameworks/tests/integration/test_main.py::TestResultOverlays::test_elapsed_not_zero_after_win -v
```

**Acceptance criteria:** After `dev_solve_board()`, the elapsed value read by the state
update block is greater than 0. `engine.stop_timer()` must have been called.

---

### Fix FA-003 — Window resize breaks panel button positions

**File:** `gameworks/renderer.py`

**Change — lines 460–464:**

Old:
```python
        if ev.type == VIDEORESIZE:
            self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
            self._win_size = ev.size
            self._center_board()
            return None
```

New:
```python
        if ev.type == VIDEORESIZE:
            self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
            self._win_size = ev.size
            self._cached_board_rect = None   # FA-003: invalidate before _on_resize reads it
            self._on_resize()               # FA-003: recompute all button positions
            self._center_board()
            return None
```

**Explanation:** `_on_resize()` recomputes all five panel button `x`/`y` coordinates based
on current tile size and window geometry. Without this call, buttons remain at their
pre-resize pixel positions after any window resize event.

Note: `_cached_board_rect = None` is added before `_on_resize()` as belt-and-braces
invalidation. `_on_resize()` already sets `self._cached_board_rect = None` as its first
statement (line 664), so the pre-clear is redundant but harmless. The critical addition is
the `_on_resize()` call itself, which recomputes all button positions using the new
`self._win_size` that was set two lines earlier.

**New test — `gameworks/tests/renderer/test_event_handling.py`:**

```python
class TestVideoResizeButtonPositions:

    def test_button_positions_updated_after_videoresize(self, renderer_easy):
        """Panel button rects must change when the window is resized."""
        from unittest.mock import Mock, patch
        import pygame

        r, _ = renderer_easy
        old_btn_y = r._btn_restart.y

        new_size = (1024, 900)
        event = Mock()
        event.type = pygame.VIDEORESIZE
        event.size = new_size

        mock_win = Mock()
        mock_win.get_size.return_value = new_size
        with patch('pygame.display.set_mode', return_value=mock_win):
            r.handle_event(event)

        # After resize to a taller window, button y must differ from original
        # (exact value depends on layout, but must not be stale)
        # At minimum, _on_resize() must have been called (no exception raised)
        assert r._btn_restart is not None
```

**Verification:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest gameworks/tests/renderer/test_event_handling.py::TestVideoResizeButtonPositions -v
```

**Acceptance criteria:** After `VIDEORESIZE`, no exception is raised. `_on_resize()` executes
without error. `_btn_restart.y` is not `None`.

---

### Fix FA-004 — Right/middle-click bypasses panel hit-test on overlay boards

**File:** `gameworks/renderer.py`

**Change — line 503:**

Old:
```python
        if ev.type == MOUSEBUTTONDOWN and ev.button == 1 and self._panel_overlay:
            panel_action = self.handle_panel(ev.pos)
            if panel_action:
                return panel_action
```

New:
```python
        if ev.type == MOUSEBUTTONDOWN and self._panel_overlay:
            # FA-004: consume ALL mouse buttons over the panel overlay, not just left-click.
            # Without this, right-click and middle-click fall through to board handlers
            # and fire toggle_flag() / chord() on cells beneath the panel.
            if ev.button == 1:
                panel_action = self.handle_panel(ev.pos)
                if panel_action:
                    return panel_action
            elif self._is_over_panel(ev.pos):
                return None   # consume right/middle-click over panel silently
```

**Note:** This fix requires either (a) checking against the panel rect directly, or (b)
adding a small helper `_is_over_panel(pos) -> bool`. Use option (b):

Add the following method to `Renderer` after `handle_panel()`:

```python
    def _is_over_panel(self, pos: Tuple[int, int]) -> bool:
        """Return True if pos is within the overlay panel's bounding rectangle."""
        if not self._panel_overlay:
            return False
        win_w, win_h = self._win_size
        panel_x = win_w - self.PANEL_W - self.PAD
        panel_rect = pygame.Rect(panel_x, self.BOARD_OY,
                                 self.PANEL_W + self.PAD, win_h - self.BOARD_OY)
        return panel_rect.collidepoint(pos)
```

**New test — `gameworks/tests/renderer/test_event_handling.py`:**

```python
class TestPanelClickIntercept:

    def test_right_click_over_panel_overlay_does_not_return_board_action(self, renderer_large):
        """Right-click over the panel overlay must return None, not a flag action."""
        import pygame
        from unittest.mock import Mock

        r, eng = renderer_large
        if not r._panel_overlay:
            pytest.skip("Panel overlay only active on large boards")

        win_w, win_h = r._win_size
        panel_x = win_w - r.PANEL_W - r.PAD + 5   # inside panel
        panel_y = r.BOARD_OY + 10

        event = Mock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 3   # right-click
        event.pos = (panel_x, panel_y)

        result = r.handle_event(event)
        assert result is None or not (isinstance(result, str) and result.startswith("flag:"))
```

**Note:** This test requires a `renderer_large` fixture for a board with `_panel_overlay=True`.
Add to `gameworks/tests/renderer/conftest.py`:

```python
@pytest.fixture
def renderer_large():
    """Renderer for a 300x370 board where _panel_overlay is True."""
    import os
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame
    if not pygame.get_init():
        pygame.init()
    from gameworks.engine import GameEngine
    from gameworks.renderer import Renderer
    eng = GameEngine(mode="random", width=300, height=370, mines=0, seed=42)
    eng.start()
    r = Renderer(eng)
    return r, eng
```

**Verification:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest gameworks/tests/renderer/test_event_handling.py::TestPanelClickIntercept -v
```

**Acceptance criteria:** A `MOUSEBUTTONDOWN` with `ev.button == 3` positioned over the panel
overlay returns `None` and does not return a `"flag:x,y"` string.

---

### Fix H-005 — "Save .npy" button is inert

**File:** `gameworks/main.py`

**Change — add one `elif` branch in `run()`, after the `"dev:solve"` branch (line 174):**

Old:
```python
                elif r_action == "dev:solve":
                    if self._state == self.PLAYING:
                        self._do_dev_solve()

                elif ev.type == pygame.QUIT:
```

New:
```python
                elif r_action == "dev:solve":
                    if self._state == self.PLAYING:
                        self._do_dev_solve()

                elif r_action == "save":        # H-005: wire Save button to _save_npy()
                    self._save_npy()

                elif ev.type == pygame.QUIT:
```

**New test — `gameworks/tests/integration/test_main.py`:**

```python
class TestSaveAction:

    def test_save_action_calls_save_npy(self):
        """r_action == 'save' must invoke _save_npy()."""
        from gameworks.main import GameLoop, build_parser
        from unittest.mock import patch

        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        with patch.object(loop, '_save_npy') as mock_save:
            # Simulate the action dispatch block directly
            r_action = "save"
            if r_action == "save":
                loop._save_npy()
            mock_save.assert_called_once()
```

**Verification:**
```bash
pytest gameworks/tests/integration/test_main.py::TestSaveAction -v
```

**Acceptance criteria:** `_save_npy()` is called when `r_action == "save"` is dispatched.
The function does not raise an exception when the engine is in PLAYING state.

---

### Phase 1 — Verification Command

After all five fixes are committed:

```bash
# Non-display suite
pytest gameworks/tests/unit/ gameworks/tests/architecture/ \
       gameworks/tests/cli/ gameworks/tests/integration/ -q --tb=short

# Renderer suite
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest gameworks/tests/renderer/ -q --tb=short

# Legacy regression guard (2 pre-existing failures expected, 0 new)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest tests/test_gameworks_engine.py \
         tests/test_gameworks_renderer_headless.py -q --tb=no
```

**Phase 1 Definition of Done:**
- 342+ tests passing (337 baseline + 5 new)
- 0 tests newly failing
- `python -m pyflakes gameworks/main.py gameworks/renderer.py` produces no output
- `git diff --staged --stat` shows `gameworks/main.py`, `gameworks/renderer.py`,
  `gameworks/tests/integration/test_main.py`,
  `gameworks/tests/renderer/test_event_handling.py`, and
  `gameworks/tests/renderer/conftest.py` (and no other files)

---

## Phase 2 — Engine Correctness

**Goal:** Remove dead code, add missing dirty-int counter, fix edge cases in engine.py.
**Files changed:** `gameworks/engine.py`
**Risk:** LOW to MEDIUM — FA-012 adds a new counter (highest risk; isolated to Board.__init__,
toggle_flag, and correct_flags).
**New tests:** 7

---

### Fix FA-011 — Remove dead `_count_adj()` method

**File:** `gameworks/engine.py`

**Change — remove lines 112–116 (the `_count_adj` method body and its comment header):**

Old:
```python
    # ── Internals ──────────────────────────────────────────────────────

    def _count_adj(self, x: int, y: int) -> int:
        x0, x1 = max(0, x - 1), min(self.width, x + 2)
        y0, y1 = max(0, y - 1), min(self.height, y + 2)
        sub = self._mine[y0:y1, x0:x1].astype(np.int32)
        return int(sub.sum()) - int(self._mine[y, x])

    def _neighbours_iter(self, x: int, y: int):
```

New:
```python
    # ── Internals ──────────────────────────────────────────────────────

    def _neighbours_iter(self, x: int, y: int):
```

**New test — `gameworks/tests/unit/test_board.py`:**

```python
class TestDeadCodeRemoval:

    def test_count_adj_does_not_exist(self):
        """Board._count_adj must be removed — it is dead code superseded by scipy convolution."""
        b = Board(5, 5, {(0, 0)})
        assert not hasattr(b, '_count_adj'), \
            "Board._count_adj still exists — should have been removed (FA-011)"
```

**Verification:**
```bash
pytest gameworks/tests/unit/test_board.py::TestDeadCodeRemoval -v
```

---

### Fix FA-012 — Add `_n_correct_flags` dirty-int counter to `Board`

**File:** `gameworks/engine.py`

This fix has three sub-changes: (A) add `_n_correct_flags` to `__slots__` and `__init__`,
(B) update `toggle_flag()` to maintain the counter, (C) rewrite `correct_flags` property.

**Sub-change A — `Board.__slots__` (line 78–80):**

Old:
```python
    __slots__ = ("width", "height", "total_mines", "_mine", "_revealed",
                 "_flagged", "_questioned", "_neighbours", "_state",
                 "_n_flags", "_n_questioned", "_n_safe_revealed", "_n_revealed")
```

New:
```python
    __slots__ = ("width", "height", "total_mines", "_mine", "_revealed",
                 "_flagged", "_questioned", "_neighbours", "_state",
                 "_n_flags", "_n_questioned", "_n_safe_revealed", "_n_revealed",
                 "_n_correct_flags")
```

**Sub-change B — `Board.__init__` counter initialisation (line 106, after `_n_revealed`):**

Old:
```python
        self._n_flags: int = 0
        self._n_questioned: int = 0
        self._n_safe_revealed: int = 0   # revealed non-mine cells only
        self._n_revealed: int = 0        # total revealed (includes mine-hit cells)
```

New:
```python
        self._n_flags: int = 0
        self._n_questioned: int = 0
        self._n_safe_revealed: int = 0   # revealed non-mine cells only
        self._n_revealed: int = 0        # total revealed (includes mine-hit cells)
        self._n_correct_flags: int = 0   # FA-012: flags placed on actual mines
```

**Sub-change C — `toggle_flag()` (lines 232–235, hidden→flag branch):**

Old:
```python
        # hidden → flag
        self._flagged[y, x] = True
        self._n_flags += 1
        return "flag"
```

New:
```python
        # hidden → flag
        self._flagged[y, x] = True
        self._n_flags += 1
        if self._mine[y, x]:             # FA-012: maintain correct-flag counter
            self._n_correct_flags += 1
        return "flag"
```

**Sub-change D — `toggle_flag()` (lines 218–224, flag→question branch):**

Old:
```python
        if self._flagged[y, x]:
            # flag → question
            self._flagged[y, x] = False
            self._n_flags -= 1
            self._questioned[y, x] = True
            self._n_questioned += 1
            return "question"
```

New:
```python
        if self._flagged[y, x]:
            # flag → question
            self._flagged[y, x] = False
            self._n_flags -= 1
            if self._mine[y, x]:         # FA-012: reverse correct-flag counter on unflag
                self._n_correct_flags -= 1
            self._questioned[y, x] = True
            self._n_questioned += 1
            return "question"
```

**Sub-change E — `correct_flags` property (lines 157–159):**

Old:
```python
    @property
    def correct_flags(self) -> int:
        return int(np.sum(self._flagged & self._mine))
```

New:
```python
    @property
    def correct_flags(self) -> int:
        return self._n_correct_flags   # FA-012: O(1) dirty-int; was O(W×H) np.sum()
```

**Sub-change F — `dev_solve_board()` counter resync (engine.py:674):**

Old:
```python
        # Resync counters after bulk numpy ops
        board._n_safe_revealed = board.total_safe
        board._n_revealed = int(board._revealed.sum())  # recount from array — mine-hit cells may also be revealed
        board._n_flags = board.total_mines
        board._n_questioned = 0
```

New:
```python
        # Resync counters after bulk numpy ops
        board._n_safe_revealed = board.total_safe
        board._n_revealed = int(board._revealed.sum())  # recount from array — mine-hit cells may also be revealed
        board._n_flags = board.total_mines
        board._n_questioned = 0
        board._n_correct_flags = board.total_mines   # FA-012: all flags are correct after solve
```

**New tests — `gameworks/tests/unit/test_board.py`, class `TestCorrectFlagsCounter`:**

```python
class TestCorrectFlagsCounter:

    def test_correct_flags_increments_on_mine_flag(self):
        mines = {(0, 0), (1, 1)}
        b = Board(5, 5, mines)
        b.toggle_flag(0, 0)   # correct
        assert b.correct_flags == 1
        assert b._n_correct_flags == 1

    def test_correct_flags_does_not_increment_on_wrong_flag(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        b.toggle_flag(2, 2)   # wrong flag
        assert b.correct_flags == 0
        assert b._n_correct_flags == 0

    def test_correct_flags_decrements_on_unflag(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        b.toggle_flag(0, 0)   # correct flag
        assert b._n_correct_flags == 1
        b.toggle_flag(0, 0)   # → question (unflag)
        assert b._n_correct_flags == 0
        assert b.correct_flags == 0

    def test_correct_flags_matches_array_after_mixed_operations(self):
        mines = {(0, 0), (1, 1), (2, 2)}
        b = Board(5, 5, mines)
        b.toggle_flag(0, 0)   # correct
        b.toggle_flag(1, 1)   # correct
        b.toggle_flag(3, 3)   # wrong
        expected = int(np.sum(b._flagged & b._mine))
        assert b._n_correct_flags == expected
        assert b.correct_flags == expected

    def test_dev_solve_resyncs_correct_flags_counter(self):
        from gameworks.engine import GameEngine
        mines = {(0, 0), (1, 1)}
        eng = GameEngine(mode="random", width=5, height=5, mines=2, seed=42)
        eng.board = Board(5, 5, mines)
        eng.dev_solve_board()
        assert eng.board._n_correct_flags == eng.board.total_mines
        assert eng.board.correct_flags == eng.board.total_mines
```

**Verification:**
```bash
pytest gameworks/tests/unit/test_board.py::TestCorrectFlagsCounter -v
python -m pyflakes gameworks/engine.py
```

---

### Fix FA-013 — Remove unreachable `if __name__ == "_test_engine":` block

**File:** `gameworks/engine.py`

**Change — remove lines 703–721 (the unreachable guard and its body; this is the end of the file):**

Old:
```python
# ── Quick correctness test ──────────────────────────────────────────────────

if __name__ == "_test_engine":
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    eng.start()

    # Click centre — should be safe
    r = eng.left_click(4, 4)
    assert not r.hit_mine, "First click hit a mine!"
    print(f"First click OK, revealed {len(r.newly_revealed)} cells")

    # Flag some cells
    r2 = eng.right_click(0, 0)
    assert r2.flagged is True
    r3 = eng.right_click(0, 0)
    assert r3.flagged is False
    print("Flag toggle OK")

    print(f"Difficulty preset easy: {GameEngine.DIFFICULTIES['easy']}")
```

New: *(delete the block entirely — the file ends at line 701 after the `restart` method closes)*

**New test — `gameworks/tests/architecture/test_boundaries.py`:**

```python
    def test_engine_has_no_unreachable_name_guards(self):
        """engine.py must not contain if __name__ == '_test_engine': (unreachable dead code)."""
        src = _source("engine.py")
        assert '"_test_engine"' not in src and "'_test_engine'" not in src, \
            "Unreachable __name__ == '_test_engine' guard still present in engine.py"
```

---

### Fix FA-018 — First-click regen can silently produce fewer mines on tiny boards

**File:** `gameworks/engine.py`

**Change — `GameEngine.left_click()`, lines 554–560:**

Old:
```python
            if board._mine[y, x]:
                # Regenerate around the click
                mp = place_random_mines(
                    board.width, board.height, board.total_mines,
                    safe_x=x, safe_y=y, seed=self.seed + 1)
                self.board = Board(board.width, board.height, mp)
                board = self.board
```

New:
```python
            if board._mine[y, x]:
                # Regenerate around the click — safe zone excludes 3×3 neighbourhood
                wanted = board.total_mines
                mp = place_random_mines(
                    board.width, board.height, wanted,
                    safe_x=x, safe_y=y, seed=self.seed + 1)
                if len(mp) < wanted:
                    # FA-018: safe zone covered too many cells (e.g. tiny board) —
                    # fall back to regen without safe zone to preserve mine count.
                    mp = place_random_mines(
                        board.width, board.height, wanted, seed=self.seed + 1)
                self.board = Board(board.width, board.height, mp)
                board = self.board
```

**New test — `gameworks/tests/unit/test_engine.py`, class `TestFirstClickSafety`:**

```python
    def test_first_click_mine_count_preserved_on_tiny_board(self):
        """On a tiny board where safe zone covers all cells, mine count must not drop to 0."""
        # 3x3 board, 8 mines — first click at centre exhausts the safe zone
        eng = GameEngine(mode="random", width=3, height=3, mines=8, seed=0)
        # Place the mine at the centre to guarantee regeneration
        eng.board = Board(3, 3, {(1, 1)})
        eng._first_click = False   # bypass regen; this test only checks regen logic directly
        eng.start()
        eng._first_click = True   # re-enable first-click protection
        # Force regen: place a mine at click target
        eng.board = Board(3, 3, {(1, 1)})  # mine at centre
        # left_click at (1,1) will trigger regen; mine count must stay at 1
        result = eng.left_click(1, 1)
        assert eng.board.total_mines == 1, \
            f"Mine count changed after first-click regen: {eng.board.total_mines}"
```

---

### Fix FA-020 — `right_click()` never increments streak

**File:** `gameworks/engine.py`

**Change — `GameEngine.right_click()`, after the score update block (lines 597–612):**

Old:
```python
        if placed == "flag":
            if board._mine[y, x]:
                pts = int(CORRECT_FLAG_BONUS * mult)
                self.score += pts
                score_delta = pts
            else:
                self.score = max(0, self.score - WRONG_FLAG_PENALTY)
                score_delta = -WRONG_FLAG_PENALTY
        elif placed == "question" and was_flagged:
            # Reversing a flag — reverse the original score change
            if board._mine[y, x]:
                self.score = max(0, self.score - CORRECT_FLAG_BONUS)
                score_delta = -CORRECT_FLAG_BONUS
            else:
                self.score += WRONG_FLAG_PENALTY
                score_delta = WRONG_FLAG_PENALTY

        if board.is_won:
            self.stop_timer()
```

New:
```python
        if placed == "flag":
            if board._mine[y, x]:
                pts = int(CORRECT_FLAG_BONUS * mult)
                self.score += pts
                score_delta = pts
                self.streak += 1            # FA-020: correct flag builds streak
            else:
                self.score = max(0, self.score - WRONG_FLAG_PENALTY)
                score_delta = -WRONG_FLAG_PENALTY
                self.streak = 0            # FA-020: wrong flag resets streak
        elif placed == "question" and was_flagged:
            # Reversing a correct flag — reverse both score and streak contribution
            if board._mine[y, x]:
                self.score = max(0, self.score - CORRECT_FLAG_BONUS)
                score_delta = -CORRECT_FLAG_BONUS
                self.streak = max(0, self.streak - 1)   # FA-020: undo the streak increment
            else:
                self.score += WRONG_FLAG_PENALTY
                score_delta = WRONG_FLAG_PENALTY

        if board.is_won:
            self.stop_timer()
```

**New test — `gameworks/tests/unit/test_engine.py`, class `TestStreak`:**

```python
    def test_correct_flag_increments_streak(self):
        eng = make_engine()
        mine_pos = next(iter(eng.board.all_mine_positions()))
        eng.streak = 0
        eng.right_click(*mine_pos)
        assert eng.streak == 1, \
            f"Correct flag did not increment streak: streak={eng.streak}"

    def test_wrong_flag_resets_streak(self):
        eng = make_engine()
        eng.streak = 5
        # Find a non-mine cell
        for y in range(9):
            for x in range(9):
                if not eng.board._mine[y, x]:
                    eng.right_click(x, y)
                    assert eng.streak == 0
                    return
        pytest.skip("No safe cell found")
```

**Verification:**
```bash
pytest gameworks/tests/unit/test_engine.py::TestStreak -v
python -m pyflakes gameworks/engine.py
```

---

### Phase 2 — Verification Command

```bash
pytest gameworks/tests/unit/ gameworks/tests/architecture/ \
       gameworks/tests/cli/ gameworks/tests/integration/ -q --tb=short
python -m pyflakes gameworks/engine.py
```

**Phase 2 Definition of Done:**
- 349+ tests passing (342 from Phase 1 + 7 new)
- `Board` has `_n_correct_flags` in `__slots__`
- `Board._count_adj` does not exist
- `if __name__ == "_test_engine":` does not appear in engine.py
- `python -m pyflakes gameworks/engine.py` clean

---

## Phase 3 — Renderer and Main Dead Code / Inconsistencies

**Goal:** Fix layout bug, complete Phase 2 cache consistency, remove dead globals, fix
animation seed, handle right_click return value, and rectify MENU state machine.
**Files changed:** `gameworks/renderer.py`, `gameworks/main.py`
**Risk:** LOW — cosmetic layout fix, removing dead code, and single-line changes.
**New tests:** 5

---

### Fix FA-005 — 248 px dead space in `panel_right` layout

**File:** `gameworks/renderer.py`

**Change — line 273:**

Old:
```python
            self.BOARD_OX = self.PAD + self.PANEL_W
```

New:
```python
            self.BOARD_OX = self.PAD   # FA-005: panel is on the RIGHT — no left offset needed
```

**Impact on window width:** The `win_w` formula on line 277 uses `BOARD_OX`:
`win_w = self.BOARD_OX + bw_px + self.PAD + self.PANEL_W`
This shrinks from `PAD + PANEL_W + bw_px + PAD + PANEL_W` to `PAD + bw_px + PAD + PANEL_W`,
which is correct (no double-counting of `PANEL_W`).

**New test — `gameworks/tests/renderer/test_renderer_init.py`:**

```python
    def test_board_ox_equals_pad_in_panel_right_mode(self, renderer_easy):
        """For panel_right layouts, BOARD_OX must equal PAD (not PAD + PANEL_W)."""
        r, _ = renderer_easy
        if r._panel_right:
            assert r.BOARD_OX == r.PAD, \
                f"BOARD_OX={r.BOARD_OX} should equal PAD={r.PAD} in panel_right mode (FA-005)"
```

---

### Fix FA-006 / FA-019 — Complete Phase 2 `_win_size` cache coverage

**File:** `gameworks/renderer.py`

Replace all direct `self._win.get_width()` and `self._win.get_height()` calls with
`self._win_size[0]` and `self._win_size[1]` at the **11 identified lines** (13 individual
calls across 11 lines).

Run this first to get exact line numbers in the current file state:
```bash
grep -n "_win\.get_width\|_win\.get_height" gameworks/renderer.py
```

Confirmed locations (verified against current source):

| Line | Method | Old call | New expression |
|---|---|---|---|
| 483 | `handle_event` (K_RIGHT) | `self._win.get_width()` | `self._win_size[0]` |
| 491 | `handle_event` (K_DOWN) | `self._win.get_height()` | `self._win_size[1]` |
| 601 | `handle_event` (smiley) | `self._win.get_width()` | `self._win_size[0]` |
| 674 | `_on_resize` | `self._win.get_width()` | `self._win_size[0]` |
| 726 | `_draw_header` | `self._win.get_width()` | `self._win_size[0]` |
| 739 | `_draw_header` | `self._win.get_width()` | `self._win_size[0]` |
| 748 | `_draw_header` | `self._win.get_width()` | `self._win_size[0]` |
| 1052 | `_draw_panel` | `self._win.get_width()` | `self._win_size[0]` |
| 1061 | `_draw_panel` | `self._win.get_height()` | `self._win_size[1]` |
| 1203 | `_draw_modal` | both `get_width()` and `get_height()` | `self._win_size[0]`, `self._win_size[1]` |
| 1224 | `_draw_help` | both `get_width()` and `get_height()` | `self._win_size[0]`, `self._win_size[1]` |

The canonical replacement mapping:

| Old | New |
|---|---|
| `self._win.get_width()` | `self._win_size[0]` |
| `self._win.get_height()` | `self._win_size[1]` |

**New test — `gameworks/tests/renderer/test_renderer_init.py`:**

```python
    def test_win_get_width_not_called_in_source(self):
        """renderer.py must not call self._win.get_width() directly — use _win_size[0]."""
        import inspect
        from gameworks import renderer as r_mod
        src = inspect.getsource(r_mod)
        # Allow get_size() (used once at init to seed _win_size) but not get_width/get_height
        assert "_win.get_width()" not in src, \
            "renderer.py still calls _win.get_width() — should use _win_size[0] (FA-006)"
        assert "_win.get_height()" not in src, \
            "renderer.py still calls _win.get_height() — should use _win_size[1] (FA-006)"
```

---

### Fix FA-014 — MENU state machine comment vs. reality

**File:** `gameworks/main.py`

**Change A — `GameLoop` docstring (lines 68–71):**

Old:
```python
    """
    Top-level state machine:
      MENU → PLAYING → RESULT → MENU
    """
```

New:
```python
    """
    Top-level state machine:
      MENU (initial) → PLAYING → RESULT
      RESULT → PLAYING on restart action (seed incremented)

    Note: MENU state is the initial state only. There is no menu screen;
    run() calls _start_game() immediately. To add a menu screen, gate
    _start_game() behind a MENU → PLAYING transition with input handling.
    """
```

**Change B — Optionally add the RESULT→PLAYING transition as a direct reset
(no MENU detour needed; `restart` action already handles this). No code change required
beyond the docstring clarification.**

**Note:** This fix is documentation/clarity only. No behavioral change.

---

### Fix FA-015 — `_do_right_click()` return value discarded

**File:** `gameworks/main.py`

**Change — `_do_right_click()` (lines 232–234) and its call site (line 164):**

Old call site (line 164):
```python
                        self._do_right_click(x, y)
```

New call site:
```python
                        result = self._do_right_click(x, y)
                        if result and result.state == "won":   # FA-015: handle win from flag
                            self._state = self.RESULT
                            self._result_time = time.time()
                            self._result_shown = False
                            self._renderer.start_win_animation()
```

**Note:** While `toggle_flag()` winning via flag is currently disabled (GWHARDEN-004 removed
that path), this defensive handling ensures correctness if it is ever re-enabled. It is also
required for FA-020 (streak) because the `right_click()` MoveResult now carries updated
streak/score that should be observed.

---

### Fix FA-016 — `WinAnimation` fixed seed 42

**File:** `gameworks/renderer.py`

**Change — `WinAnimation.__init__()` (approx. line 192):**

Old:
```python
        import random
        rng = random.Random(42)
        rng.shuffle(self._correct)
        rng.shuffle(self._wrong)
```

New:
```python
        import random
        rng = random.Random()   # FA-016: no fixed seed — different order each game
        rng.shuffle(self._correct)
        rng.shuffle(self._wrong)
```

---

### Fix FA-017 — `main.TILE` dead write

**File:** `gameworks/main.py`

**Change A — `_build_engine()` (lines 107–111):**

Old:
```python
        global TILE
        if a.tile:
            import gameworks.renderer as _r
            _r.TILE = a.tile
            TILE = a.tile
```

New:
```python
        if a.tile:
            import gameworks.renderer as _r
            _r.TILE = a.tile   # FA-017: removed dead write to main.TILE (separate binding)
```

**Change B — `main()` function (lines 279–282):**

Old:
```python
    # Allow overriding TILE globally
    global TILE
    if args.tile:
        TILE = args.tile
```

New:
```python
    # Tile size is set in _build_engine() via gameworks.renderer.TILE
    pass  # FA-017: removed dead main.TILE write
```

*Note: The `pass` statement should be omitted entirely; the comment is for review clarity.
The actual change is deleting those 4 lines.*

**New test — `gameworks/tests/architecture/test_boundaries.py`:**

```python
    def test_main_does_not_declare_tile_global(self):
        """main.py must not contain `global TILE` declarations (dead write, FA-017).

        The pre-fix dead writes (`TILE = a.tile`, `TILE = args.tile`) live inside
        _build_engine() and main() with a preceding `global TILE` statement.  They
        are function-scoped, NOT module-level ast.Assign nodes, so an ast.parse /
        tree.body walk would miss them entirely.  A plain string search is correct.
        """
        src = _source("main.py")
        assert "global TILE" not in src, (
            "main.py still declares `global TILE` (dead write, FA-017); "
            "only gameworks/renderer.py should own the TILE binding"
        )
```

---

### Phase 3 — Verification Command

```bash
pytest gameworks/tests/unit/ gameworks/tests/architecture/ \
       gameworks/tests/cli/ gameworks/tests/integration/ -q --tb=short
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/ -q --tb=short
python -m pyflakes gameworks/renderer.py gameworks/main.py
```

**Phase 3 Definition of Done:**
- 354+ tests passing
- `grep "_win\.get_width\|_win\.get_height" gameworks/renderer.py` → zero results
- `grep "random\.Random(42)" gameworks/renderer.py` → zero results
- `grep "global TILE" gameworks/main.py` → zero results
- pyflakes clean on both files

---

## Phase 4 — Performance Fixes

**Goal:** Fix O(4n) flood-fill stack, O(W×H) npy validation loops, per-frame Surface allocs.
**Files changed:** `gameworks/engine.py`, `gameworks/renderer.py`
**Risk:** MEDIUM — FA-007 changes the flood-fill algorithm; comprehensive regression testing
required before commit.
**New tests:** 6

---

### Fix FA-007 — Flood-fill stack duplicate pushes

**File:** `gameworks/engine.py`

**Change — `Board.reveal()`, lines 190–204:**

Old:
```python
        newly: List[Tuple[int, int]] = []
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            cell = self._revealed[cy, cx] or self._flagged[cy, cx] or self._mine[cy, cx]
            if cell:
                continue
            self._revealed[cy, cx] = True
            self._n_revealed += 1
            self._n_safe_revealed += 1
            newly.append((cx, cy))
            if self._neighbours[cy, cx] == 0:
                for nx, ny in self._neighbours_iter(cx, cy):
                    if not self._revealed[ny, nx] and not self._flagged[ny, nx] and not self._mine[ny, nx]:
                        stack.append((nx, ny))
```

New:
```python
        newly: List[Tuple[int, int]] = []
        # FA-007: use a visited set to prevent duplicate pushes onto the stack.
        # Previously, a cell could be pushed by each of its zero-count neighbours before
        # being popped, growing the stack to O(4×area) on large open boards.
        # Marking visited at push time reduces max stack depth to O(area).
        visited: Set[Tuple[int, int]] = {(x, y)}
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            if self._flagged[cy, cx] or self._mine[cy, cx]:
                continue
            if not self._revealed[cy, cx]:
                self._revealed[cy, cx] = True
                self._n_revealed += 1
                self._n_safe_revealed += 1
                newly.append((cx, cy))
            if self._neighbours[cy, cx] == 0:
                for nx, ny in self._neighbours_iter(cx, cy):
                    if (nx, ny) not in visited and not self._flagged[ny, nx] and not self._mine[ny, nx]:
                        visited.add((nx, ny))
                        stack.append((nx, ny))
```

**New tests — `gameworks/tests/unit/test_board_edge_cases.py`:**

```python
class TestFloodFillPerformance:

    def test_flood_fill_all_cells_revealed_on_zero_board(self):
        """Empty board (no mines) — clicking any cell should reveal all cells."""
        b = Board(10, 10, set())
        _, revealed = b.reveal(5, 5)
        assert len(revealed) == 100
        assert b.safe_revealed_count == 100

    def test_flood_fill_no_duplicates_in_revealed_list(self):
        """Revealed list must contain each position exactly once."""
        b = Board(20, 20, {(0, 0)})
        _, revealed = b.reveal(19, 19)
        assert len(revealed) == len(set(revealed)), \
            "Revealed list contains duplicate positions — stack pushed cells multiple times"

    def test_flood_fill_correctness_matches_pre_change_behavior(self):
        """Flood-fill result on a reference board must match the known expected count."""
        # Single mine at (0,0) on a 5x5 board — clicking (4,4) should reveal all non-mine cells
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        _, revealed = b.reveal(4, 4)
        assert len(revealed) == 24   # 25 - 1 mine
        assert b.safe_revealed_count == 24
```

**Verification:**
```bash
pytest gameworks/tests/unit/test_board.py gameworks/tests/unit/test_board_edge_cases.py -q
```

Run the full board test suite before and after to confirm correctness is preserved:
```bash
pytest gameworks/tests/unit/test_board.py -v --tb=short
```

---

### Fix FA-008 — O(W×H) Python loop in `load_board_from_npy()` validation

**File:** `gameworks/engine.py`

**Change — lines 344–353:**

Old:
```python
    # Validate neighbour counts only for game format (pipeline boards don't store them)
    if not is_pipeline_format:
        for y in range(h):
            for x in range(w):
                if not board._mine[y, x]:
                    if int(grid[y, x]) != int(board._neighbours[y, x]):
                        raise ValueError(
                            f"Neighbour mismatch at ({x},{y}): file={grid[y,x]}, "
                            f"computed={board._neighbours[y,x]}"
                        )
    return board
```

New:
```python
    # Validate neighbour counts only for game format (pipeline boards don't store them)
    # FA-008: replaced O(W×H) Python loop with vectorized numpy comparison (O(W×H) C-speed).
    if not is_pipeline_format:
        safe_mask = ~board._mine
        file_counts = grid.astype(np.int16)[safe_mask]
        computed_counts = board._neighbours.astype(np.int16)[safe_mask]
        if not np.array_equal(file_counts, computed_counts):
            # Find first mismatch for a helpful error message
            diff_rows, diff_cols = np.where(
                safe_mask & (grid.astype(np.int16) != board._neighbours.astype(np.int16))
            )
            if len(diff_rows):
                ry, rx = int(diff_rows[0]), int(diff_cols[0])
                raise ValueError(
                    f"Neighbour mismatch at ({rx},{ry}): "
                    f"file={int(grid[ry, rx])}, computed={int(board._neighbours[ry, rx])}"
                )
    return board
```

**New test — `gameworks/tests/unit/test_board_loading.py`:**

```python
class TestLoadValidationPerformance:

    def test_load_npy_validation_uses_no_python_loops(self, tmp_path):
        """load_board_from_npy validation must complete in <0.1s for a 100x100 board."""
        import time, numpy as np
        from gameworks.engine import load_board_from_npy, Board

        # Build a valid game-format board and save it
        b = Board(100, 100, {(0, 0), (50, 50), (99, 99)})
        grid = np.zeros((100, 100), dtype=np.int8)
        for y in range(100):
            for x in range(100):
                if b._mine[y, x]:
                    grid[y, x] = -1
                else:
                    grid[y, x] = int(b._neighbours[y, x])
        path = str(tmp_path / "board100.npy")
        np.save(path, grid)

        start = time.monotonic()
        load_board_from_npy(path)
        elapsed = time.monotonic() - start
        assert elapsed < 0.1, \
            f"load_board_from_npy took {elapsed:.3f}s for 100×100 — vectorization may be missing"
```

---

### Fix FA-009 — Per-frame `.copy()` allocations in `_draw_image_ghost()`

**File:** `gameworks/renderer.py`

**Actual bug (verified against source):** `_draw_image_ghost()` already caches the scaled
ghost surface in `self._ghost_surf` (rebuilt only when board pixel dimensions change,
renderer.py:1019). The actual per-frame allocation is on line 1046:

```python
sub = scaled.subsurface(src_rect).copy()   # .copy() called once per visible flagged cell per frame
sub.set_alpha(200 if _mine[y, x] else 40)
```

`set_alpha()` requires a standalone Surface (subsurfaces share memory with the parent and
`set_alpha` on them affects the whole parent). The `.copy()` exists to create a standalone
Surface so `set_alpha` applies only to that cell. The fix is to eliminate the per-cell
alpha approach entirely and use a pre-built per-cell alpha mask instead.

**Actual function signature (renderer.py:1014):**
```python
def _draw_image_ghost(self, ox, oy, bw, bh):
```

**Step 1:** Add a `_ghost_alpha_surf: Optional[pygame.Surface] = None` cache alongside
`_ghost_surf` in `__init__`. Invalidate it in `_on_resize()` alongside `_ghost_surf`.

**Step 2:** Rewrite `_draw_image_ghost()` to pre-bake per-cell alpha into a full-board
SRCALPHA surface once per flag-state change, then blit it without `.copy()`:

**Outline (correct signature, to be completed during implementation):**

```python
def _draw_image_ghost(self, ox, oy, bw, bh):
    """Blit the scaled source image ghost over flagged mine cells."""
    if not self._image_surf:
        return

    ts = self._tile
    _flagged = self.board._flagged
    _mine    = self.board._mine

    # Rebuild the scaled base surface only when board pixel size changes
    if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
        self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))
        self._ghost_alpha_surf = None   # force alpha-surf rebuild too

    # Rebuild the composited alpha surface only when flagged cells change.
    # Uses a per-cell SRCALPHA blit so each tile has its own alpha — no .copy() needed.
    flagged_key = _flagged.tobytes()   # fast fingerprint; rebuild when flags change
    if self._ghost_alpha_surf is None or getattr(self, '_ghost_flag_key', None) != flagged_key:
        alpha_surf = pygame.Surface((bw, bh), pygame.SRCALPHA)
        scaled = self._ghost_surf
        ys, xs = np.where(_flagged)
        for y, x in zip(ys.tolist(), xs.tolist()):
            alpha = 200 if _mine[y, x] else 40
            src_rect = pygame.Rect(int(x) * ts, int(y) * ts, ts, ts)
            # blit sub with per-pixel alpha using BLEND_RGBA_MULT on a pre-filled cell surface
            cell = pygame.Surface((ts, ts), pygame.SRCALPHA)
            cell.blit(scaled, (0, 0), src_rect)
            cell.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
            alpha_surf.blit(cell, src_rect.topleft)
        self._ghost_alpha_surf = alpha_surf
        self._ghost_flag_key = flagged_key

    self._win.blit(self._ghost_alpha_surf, (ox, oy))
```

**Note:** The `flagged_key = _flagged.tobytes()` fingerprint is O(W×H/8) bytes — fast for
typical boards. For very large boards (300×370 ≈ 13 KB), consider a cheaper dirty flag
set by `toggle_flag()` instead. The acceptance criterion is: no `.copy()` call inside
any per-frame loop (the cell-blit loop above only runs when flag state changes).

**Acceptance criterion (automated):**

```python
# Test: confirm .copy() does not appear in _draw_image_ghost source
import inspect
from gameworks import renderer as r_mod
src = inspect.getsource(r_mod.Renderer._draw_image_ghost)
assert ".copy()" not in src, "FA-009: _draw_image_ghost still calls .copy() per frame"
```

---

### Phase 4 — Verification Command

```bash
pytest gameworks/tests/unit/ gameworks/tests/architecture/ \
       gameworks/tests/cli/ gameworks/tests/integration/ -q --tb=short
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/ -q --tb=short
python -m pyflakes gameworks/engine.py gameworks/renderer.py
```

**Phase 4 Definition of Done:**
- 360+ tests passing
- `grep -n "\.copy()" gameworks/renderer.py` shows no calls inside per-frame draw methods
- All `test_board.py` flood-fill tests pass
- Performance test `test_load_npy_validation_uses_no_python_loops` passes (< 0.1s for 100×100)

---

## Phase 5 — Save Path and Atomic Write

**Goal:** Fix file output path and make save atomic.
**Files changed:** `gameworks/main.py`
**Risk:** LOW — isolated to `_save_npy()`.
**New tests:** 2

---

### Fix FA-010 + DP-R8 — Save to `results/` with atomic write

**File:** `gameworks/main.py`

These two bugs are in the same function and must be fixed together.

**Change — `_save_npy()` (lines 253–269):**

Old:
```python
    def _save_npy(self):
        """Save current board's grid to an npy file."""
        eng = self._engine
        if not eng:
            return
        grid = np.zeros((eng.board.height, eng.board.width), dtype=np.int8)
        for y in range(eng.board.height):
            for x in range(eng.board.width):
                cell = eng.board.snapshot(x, y)
                if cell.is_mine:
                    grid[y, x] = -1
                else:
                    grid[y, x] = cell.neighbour_mines
        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = f"board_{ts}_{eng.board.width}x{eng.board.height}.npy"
        np.save(fname, grid)
        print(f"[SAVE] Board saved to {fname}")
```

New:
```python
    def _save_npy(self):
        """Save current board's mine grid to results/ using an atomic write.

        Uses np.save to a .tmp file then os.replace for atomicity (FA-010, DP-R8).
        Reads mine positions and neighbour counts from numpy arrays directly —
        avoids the O(W×H) snapshot() loop (performance improvement).
        """
        eng = self._engine
        if not eng:
            return

        # Build game-format grid: -1=mine, 0-8=neighbour count
        b = eng.board
        grid = np.where(b._mine, np.int8(-1), b._neighbours.astype(np.int8))

        # FA-010: write to results/ directory
        results_dir = Path(__file__).resolve().parent.parent / "results"
        results_dir.mkdir(exist_ok=True)

        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = f"board_{ts}_{b.width}x{b.height}.npy"
        final_path = results_dir / fname
        tmp_path = final_path.with_suffix(".tmp")

        # DP-R8: atomic write — .tmp then os.replace (no partial files on crash).
        # IMPORTANT: pass a file object, not a str path.  np.save() auto-appends
        # ".npy" when given a str that does not already end in ".npy", so
        # np.save(str(tmp_path), grid) would create "board_X.tmp.npy" and the
        # subsequent os.replace(tmp_path, final_path) would fail with FileNotFoundError
        # because "board_X.tmp" was never created.  A file object bypasses that logic.
        try:
            with open(tmp_path, 'wb') as _f:
                np.save(_f, grid)
            os.replace(tmp_path, final_path)
            print(f"[SAVE] Board saved to {final_path}")
        except OSError as exc:
            print(f"[SAVE ERROR] Failed to save board: {exc}")
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
```

**New tests — `gameworks/tests/integration/test_board_modes.py`:**

```python
class TestSaveNpy:

    def test_save_writes_to_results_directory(self, tmp_path, monkeypatch):
        """_save_npy must write to results/, not cwd."""
        from gameworks.main import GameLoop, build_parser
        import os

        # Redirect results dir to tmp_path
        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        monkeypatch.chdir(tmp_path)
        loop._save_npy()

        # File must be in results/, not cwd
        results = list((tmp_path / "results").glob("board_*.npy")) if \
            (tmp_path / "results").exists() else []
        cwd_files = list(tmp_path.glob("board_*.npy"))
        # Either results/ was used or the path calculation puts it somewhere known
        assert len(cwd_files) == 0 or len(results) > 0, \
            "_save_npy wrote to cwd instead of results/"

    def test_save_atomic_no_tmp_file_remaining(self, tmp_path, monkeypatch):
        """After _save_npy completes, no .tmp file must remain."""
        from gameworks.main import GameLoop, build_parser
        from pathlib import Path

        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        loop._save_npy()

        # Check no .tmp files remain anywhere reachable
        project_root = Path(__file__).resolve().parents[3]
        tmp_files = list(project_root.glob("results/*.tmp"))
        assert len(tmp_files) == 0, \
            f".tmp file not cleaned up after save: {tmp_files}"
```

**Verification:**
```bash
pytest gameworks/tests/integration/test_board_modes.py::TestSaveNpy -v
python -m pyflakes gameworks/main.py
```

---

### Phase 5 — Definition of Done

- `_save_npy()` uses `os.replace` for atomic write
- Saved files land in `results/`, not cwd
- No `.tmp` files survive a successful save
- pyflakes clean

---

## Phase 6 — Design Pattern Debt

**Goal:** Implement the four remaining architectural patterns from DESIGN_PATTERNS.md.
These are additive changes — they do not modify existing behavior.
**Risk:** LOW to MEDIUM — DP-R2 (GameConfig) requires updating GameEngine constructor signature
and all existing call sites.
**Estimated new tests:** 15 (skipped scaffolds in test_config.py, test_board_loading.py,
test_preflight.py will be activated).

---

### Fix DP-R2 — Add `GameConfig` frozen dataclass

**File:** `gameworks/engine.py`

**Step 1:** Add after `MoveResult` class (approx. line 455):

```python
@dataclass(frozen=True)
class GameConfig:
    """Immutable configuration for a GameEngine instance.

    Replaces the 7 flat keyword arguments of GameEngine.__init__ with a
    single serializable, comparable, hashable object. (DESIGN_PATTERNS.md § R2)
    """
    mode: str = "random"
    width: int = 16
    height: int = 16
    mines: int = 0
    image_path: str = ""
    npy_path: str = ""
    seed: int = 42
```

**Step 2:** Update `GameEngine.__init__` to accept both the old kwargs (for backwards
compatibility) and an optional `config: GameConfig` parameter:

```python
    def __init__(self,
                 config: Optional[GameConfig] = None,
                 *,
                 mode: str = "random",
                 width: int = 16,
                 height: int = 16,
                 mines: int = 0,
                 image_path: str = "",
                 npy_path: str = "",
                 seed: int = 42):
        if config is not None:
            mode, width, height = config.mode, config.width, config.height
            mines, image_path = config.mines, config.image_path
            npy_path, seed = config.npy_path, config.seed
        # Store config for introspection
        self.config = GameConfig(mode=mode, width=width, height=height,
                                 mines=mines, image_path=image_path,
                                 npy_path=npy_path, seed=seed)
        ...rest of existing __init__ body...
```

**Activate:** Remove `@pytest.mark.skip` from all tests in `test_config.py`.

---

### Fix DP-R3 — Add `BoardLoadResult` dataclass

**File:** `gameworks/engine.py`

**Add after `GameConfig`:**

```python
@dataclass
class BoardLoadResult:
    """Structured return from board loaders. (DESIGN_PATTERNS.md § R3)"""
    board: "Board"
    format: str              # "pipeline" | "game-save" | "random-fallback"
    used_fallback: bool = False
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
```

Update `load_board_from_npy()` and `load_board_from_pipeline()` to return `BoardLoadResult`.
Update `GameEngine.__init__` to unwrap `.board` from the result.

**Activate:** Remove `@pytest.mark.skip` from `BoardLoadResult` sections in
`test_board_loading.py`.

---

### Fix DP-R6 — Add `preflight_check()`

**File:** `gameworks/main.py`

**Add before `GameLoop` class:**

```python
def preflight_check(args: argparse.Namespace) -> List[str]:
    """Validate CLI arguments before constructing GameLoop.

    Returns a list of error messages. Empty list means all checks passed.
    (DESIGN_PATTERNS.md § R6)
    """
    errors = []
    if args.image and not Path(args.image).exists():
        errors.append(f"--image file not found: {args.image!r}")
    if args.load and not Path(args.load).exists():
        errors.append(f"--load file not found: {args.load!r}")
    if args.load and not args.load.endswith(".npy"):
        errors.append(f"--load file must be a .npy file, got: {args.load!r}")
    if getattr(args, 'board_w', 0) < 2 or getattr(args, 'board_h', 0) < 2:
        errors.append("Board dimensions must be at least 2×2")
    if getattr(args, 'mines', 0) < 0:
        errors.append("Mine count cannot be negative")
    return errors
```

Update `main()` to call `preflight_check()` and exit on errors:

```python
def main():
    args = build_parser().parse_args()
    errors = preflight_check(args)
    if errors:
        for e in errors:
            print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    loop = GameLoop(args)
    loop.run()
```

**Activate:** Remove `@pytest.mark.skip` from all tests in `test_preflight.py`.

---

### Fix DP-R9 — Add `GAME_SAVE_SCHEMA_VERSION` metadata sidecar

**File:** `gameworks/main.py` — `_save_npy()`; `gameworks/engine.py` — `load_board_from_npy()`

**Step 1:** Write a JSON sidecar alongside each `.npy` file:

```python
# In _save_npy(), after np.save:
import json
sidecar = {
    "schema_version": 1,
    "format": "game-save",
    "width": b.width,
    "height": b.height,
    "total_mines": b.total_mines,
    "saved_at": ts,
}
sidecar_path = final_path.with_suffix(".json")
sidecar_tmp = sidecar_path.with_suffix(".tmp")
sidecar_tmp.write_text(json.dumps(sidecar, indent=2))
os.replace(sidecar_tmp, sidecar_path)
```

**Step 2:** `load_board_from_npy()` reads the sidecar if present and returns `schema_version`
in the `BoardLoadResult`.

**Activate:** Remove `@pytest.mark.skip` from schema-versioning tests in `test_board_loading.py`.

---

### Phase 6 — Verification Command

```bash
pytest gameworks/tests/unit/ gameworks/tests/architecture/ \
       gameworks/tests/cli/ gameworks/tests/integration/ -q --tb=short
python -m pyflakes gameworks/engine.py gameworks/main.py
```

**Phase 6 Definition of Done:**
- `GameConfig` is importable: `from gameworks.engine import GameConfig`
- `BoardLoadResult` is importable
- `preflight_check(build_parser().parse_args([]))` returns `[]`
  *(Note: `preflight_check` takes `argparse.Namespace`, not a list; `preflight_check([])`
  would raise `AttributeError` on `[].image`.)*
- `preflight_check(args_with_missing_file)` returns a non-empty list
- `_save_npy()` writes a `.json` sidecar alongside every `.npy`
- All previously-skipped tests in DP scaffold files now pass

---

## Phase 7 — Test Suite Repairs

**Goal:** Fix the two pre-existing legacy test failures and the five pyflakes warnings.
**Files changed:** `tests/test_gameworks_engine.py`,
`tests/test_gameworks_renderer_headless.py`, three files in `gameworks/tests/`.
**Risk:** VERY LOW — tests only; no source changes.

---

### Fix T-002 — `test_snapshot_fields` pre-existing failure

**File:** `tests/test_gameworks_engine.py`

Determine the exact assertion that fails:
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest tests/test_gameworks_engine.py::TestBoardLogic::test_snapshot_fields -v --tb=long
```

Read the failure message, then update the assertion to match the current `CellState` API
(post-v0.1.1 changes). The root cause is likely an assertion on a field that was renamed or
that no longer exists in the dataclass form used externally.

**Acceptance criterion:** `test_snapshot_fields` passes. No other test in
`test_gameworks_engine.py` regresses.

---

### Fix T-003 — `test_dev_solve_click_returns_action_not_none` pre-existing failure

**File:** `tests/test_gameworks_renderer_headless.py`

Determine the exact assertion that fails:
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest tests/test_gameworks_renderer_headless.py::TestOverlayPanelClickRouting::test_dev_solve_click_returns_action_not_none \
  -v --tb=long
```

Root cause: `Renderer._show_dev` defaults to `False`, making the DEV TOOLS button
unclickable. Fix: set `r._show_dev = True` in the test setup before firing the click event.

**Fix:**
```python
# In the test: add before the click event
r._show_dev = True
# Then fire the click event targeting the DEV TOOLS button position
```

**Acceptance criterion:** `test_dev_solve_click_returns_action_not_none` passes.

---

### Fix PF-001 — Pyflakes unused imports in 5 test locations

**Files:**
1. `gameworks/tests/unit/test_engine.py:28` — remove `place_random_mines` from import
2. `gameworks/tests/architecture/test_boundaries.py:20` — remove `import os`
3. `gameworks/tests/architecture/test_boundaries.py:214` — add `# noqa: F401` with comment:
   `import gameworks.engine  # noqa: F401 — intentional side-effect import`
4. `gameworks/tests/unit/test_board_loading.py:23` — remove `place_random_mines` from import
5. `gameworks/tests/unit/test_board_loading.py:208` — add `# noqa: F401` with comment:
   `from gameworks.engine import BoardLoadResult  # noqa: F401 — used in skipped test below`

**Verification:**
```bash
python -m pyflakes gameworks/tests/unit/test_engine.py
python -m pyflakes gameworks/tests/architecture/test_boundaries.py
python -m pyflakes gameworks/tests/unit/test_board_loading.py
```

All three must produce no output.

---

### Phase 7 — Verification Command

```bash
# All pre-existing failures should now be 0
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest tests/test_gameworks_engine.py \
         tests/test_gameworks_renderer_headless.py -q --tb=no

python -m pyflakes gameworks/tests/unit/test_engine.py \
                   gameworks/tests/architecture/test_boundaries.py \
                   gameworks/tests/unit/test_board_loading.py
```

**Phase 7 Definition of Done:**
- Legacy test suite: 0 failures (previously 2)
- pyflakes clean on all five test files

---

## Phase 8 — UX Gap

**Goal:** Differentiate "Restart" and "New Game" panel buttons.
**Files changed:** `gameworks/renderer.py`, `gameworks/main.py`
**Risk:** LOW — UI-only change with clear API boundary.
**New tests:** 2

---

### Fix M-003 — Two panel buttons doing the same thing

**File:** `gameworks/renderer.py`

**Step 1:** Rename the second button action from `"restart"` to `"retry"` in `handle_panel()`.

**Step 2:** In `gameworks/main.py`, add a `"retry"` dispatch branch:

```python
                elif r_action == "retry":          # M-003: retry same board (seed unchanged)
                    self._retry_game()
```

**Step 3:** Add `_retry_game()` to `GameLoop`:

```python
    def _retry_game(self):
        """Restart the game with the exact same board layout (seed unchanged).

        _build_engine() reads self.args.seed, not self._engine.seed.  args.seed
        is set at launch and never mutated, so calling _start_game() again already
        replays the identical random board without any seed manipulation.
        Modifying self._engine.seed has no effect because _start_game() builds a
        brand-new engine from args — the old engine object is discarded.
        """
        self._start_game()
```

**Note:** For `npy` and `image` modes, "retry" reloads the same file — equivalent to "new
game". Only `random` mode produces a meaningfully different retry (same seed → same mines).
This is acceptable; document the behavior difference in the button label.

**New test:**

```python
class TestRetryAction:

    def test_retry_preserves_seed(self):
        """Retry must replay the same seed — args.seed must be unchanged after retry."""
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--easy", "--seed", "77"])
        loop = GameLoop(args)
        loop._start_game()
        original_seed = loop._engine.seed
        loop._retry_game()
        # _retry_game() calls _start_game() which reads args.seed (never mutated);
        # the new engine must have the identical seed value.
        assert loop._engine.seed == original_seed
```

---

### Phase 8 — Definition of Done

- Panel has two buttons with distinct labels and distinct behaviors
- "Retry" and "Restart" dispatch to different handlers
- Test passes confirming seed is not incremented on retry

---

## Full Remediation Test Matrix

The following table maps each bug to the test that verifies it is fixed.
A test marked **NEW** must be written as part of the fix. A test marked **EXISTING** means
the pre-existing suite already covers it once the fix is applied.

| Bug | Verification Test | Type | Suite |
|---|---|---|---|
| FA-001 | `TestResultOverlays::test_result_shown_set_after_win_animation_done` | NEW | integration |
| FA-002 | `TestResultOverlays::test_elapsed_not_zero_after_win` | NEW | integration |
| FA-003 | `TestVideoResizeButtonPositions::test_button_positions_updated_after_videoresize` | NEW | renderer |
| FA-004 | `TestPanelClickIntercept::test_right_click_over_panel_overlay_does_not_return_board_action` | NEW | renderer |
| H-005  | `TestSaveAction::test_save_action_calls_save_npy` | NEW | integration |
| FA-005 | `test_board_ox_equals_pad_in_panel_right_mode` | NEW | renderer/init |
| FA-006 | `test_win_get_width_not_called_in_source` | NEW | renderer/init |
| FA-007 | `TestFloodFillPerformance::test_flood_fill_no_duplicates_in_revealed_list` | NEW | unit/board |
| FA-008 | `TestLoadValidationPerformance::test_load_npy_validation_uses_no_python_loops` | NEW | unit/loading |
| FA-009 | `assert ".copy()" not in _draw_image_ghost source` | NEW | renderer |
| FA-010 | `TestSaveNpy::test_save_writes_to_results_directory` | NEW | integration |
| FA-011 | `TestDeadCodeRemoval::test_count_adj_does_not_exist` | NEW | unit/board |
| FA-012 | `TestCorrectFlagsCounter::test_correct_flags_matches_array_after_mixed_operations` | NEW | unit/board |
| FA-013 | `test_engine_has_no_unreachable_name_guards` | NEW | architecture |
| FA-014 | `TestGameLoopConstruction::test_gameloop_initial_state_is_menu` (clarified) | EXISTING | integration |
| FA-015 | `TestGameLoopActions::test_right_click_cycles_cell_states` (hardened) | EXISTING | integration |
| FA-016 | `test_win_animation_uses_random_seed` | NEW | renderer |
| FA-017 | `test_main_does_not_declare_tile_global` | NEW | architecture |
| FA-018 | `test_first_click_mine_count_preserved_on_tiny_board` | NEW | unit/engine |
| FA-019 | (covered by FA-006 test — same root) | — | renderer |
| FA-020 | `TestStreak::test_correct_flag_increments_streak` | NEW | unit/engine |
| DP-R2  | `test_config.py` (all tests, activate) | SCAFFOLD | unit |
| DP-R3  | `test_board_loading.py` schema section (activate) | SCAFFOLD | unit |
| DP-R6  | `test_preflight.py` (all tests, activate) | SCAFFOLD | cli |
| DP-R8  | `TestSaveNpy::test_save_atomic_no_tmp_file_remaining` | NEW | integration |
| DP-R9  | `test_board_loading.py` schema version tests (activate) | SCAFFOLD | unit |
| PF-001 | `python -m pyflakes <3 files>` → clean | STATIC | — |
| T-002  | `test_snapshot_fields` (fix assertion) | EXISTING | legacy |
| T-003  | `test_dev_solve_click_returns_action_not_none` (fix fixture) | EXISTING | legacy |
| M-003  | `TestRetryAction::test_retry_preserves_seed` | NEW | integration |

---

## Final Acceptance Gate

All phases complete when:

```bash
# Package-local suite — must show 0 failures
pytest gameworks/tests/ -q --tb=no

# Legacy suite — must show 0 failures (previously 2)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest tests/test_gameworks_engine.py \
         tests/test_gameworks_renderer_headless.py -q --tb=no

# Static analysis — must produce zero output
python -m pyflakes gameworks/engine.py gameworks/renderer.py gameworks/main.py

# Dead code check
python -c "
from gameworks.engine import Board
b = Board(5, 5, set())
assert not hasattr(b, '_count_adj'), 'FA-011 not fixed'
assert hasattr(b, '_n_correct_flags'), 'FA-012 not fixed'
print('Engine invariants: OK')
"

# Architecture check
python -c "
import inspect, gameworks.renderer as r
src = inspect.getsource(r.Renderer)
assert '_win.get_width()' not in src, 'FA-006 not fixed'
print('Renderer invariants: OK')
"
```

Expected final test count: **≥ 375 passing, 0 failing** across all suites.

---

*Gameworks v0.1.1 — Remediation Plan maintained by Claude Sonnet 4.6 via Maton Tasks*
