# Gameworks Test Suite Hardening — Execution & Implementation Plan

**Document ID:** GWHARDEN-PLAN-001
**Version:** 1.0.0
**Date:** 2026-05-10
**Status:** APPROVED — Ready for implementation
**Scope:** `gameworks/tests/` and `gameworks/engine.py` (source bug fixes only)
**Branch target:** `frontend-game-mockup`

---

## Table of Contents

1. [Revision History](#1-revision-history)
2. [Executive Summary](#2-executive-summary)
3. [Binding Design Decisions](#3-binding-design-decisions)
4. [Pre-Implementation Checklist](#4-pre-implementation-checklist)
5. [Issue Register](#5-issue-register)
6. [Phase Plan Overview](#6-phase-plan-overview)
7. [Implementation Specifications — Phase 1 (P0 Critical)](#7-implementation-specifications--phase-1-p0-critical)
8. [Implementation Specifications — Phase 2 (P1 Source Logic)](#8-implementation-specifications--phase-2-p1-source-logic)
9. [Implementation Specifications — Phase 3 (P2 Assertion Hardening)](#9-implementation-specifications--phase-3-p2-assertion-hardening)
10. [Implementation Specifications — Phase 4 (P3 Coverage Expansion)](#10-implementation-specifications--phase-4-p3-coverage-expansion)
11. [Verification Matrix](#11-verification-matrix)
12. [CI Configuration Requirements](#12-ci-configuration-requirements)
13. [Regression Protection Rules](#13-regression-protection-rules)
14. [Out-of-Scope (Explicit)](#14-out-of-scope-explicit)
15. [Definition of Done](#15-definition-of-done)

---

## 1. Revision History

| Version | Date | Author | Change |
|---------|------|--------|--------|
| 1.0.0 | 2026-05-10 | Forensic Review | Initial plan from full test/source audit |

---

## 2. Executive Summary

A forensic review of all 25 test files in `gameworks/tests/` against their corresponding
source modules (`engine.py`, `renderer.py`, `main.py`) identified **17 hardening items**
across 4 severity classes:

| Class | Count | Consequence if unaddressed |
|-------|-------|---------------------------|
| P0 — Critical (CI Blocker) | 3 | `pytest` exits non-zero; no merge possible |
| P1 — Source Logic Bug | 1 | Silent wrong behavior in production; invalid inputs pass |
| P2 — Weak/Incorrect Test | 6 | Tests pass while not actually catching the defect they claim |
| P3 — Missing Coverage | 7 | Entire code paths have zero test protection |

**Total affected files:** 7 test files, 1 source file (`engine.py`)
**Total new lines of test code:** approximately 180
**Total source lines changed:** 8 (4 removed, 4 replaced)
**No new source features are introduced.** This plan hardens existing behavior only.

---

## 3. Binding Design Decisions

Two issues require an explicit design decision before any code is written.
These decisions are recorded here and are **final for this plan**.
Any deviation requires a new plan version.

---

### Decision D-001: `GameEngine.from_difficulty()` behavior on unknown difficulty string

**Issue:** `GWHARDEN-003`
**Question:** When an unrecognized difficulty string is passed to `from_difficulty()`,
should the source raise an exception (fix source) or silently return a medium board
(fix test to match)?

**Evidence:**

Current source at `engine.py:523–525`:
```python
@classmethod
def from_difficulty(cls, diff: str, seed: int = 42) -> "GameEngine":
    w, h, m = cls.DIFFICULTIES.get(diff, cls.DIFFICULTIES["medium"])
    return cls(mode="random", width=w, height=h, mines=m, seed=seed)
```

Current test at `tests/unit/test_engine.py:339–341`:
```python
def test_invalid_difficulty_raises(self):
    with pytest.raises((KeyError, ValueError)):
        GameEngine.from_difficulty("impossible")
```

`ARCHITECTURE.md` states: *"difficulty presets: Easy / Medium / Hard"* — a closed enum.
`DEVELOPER_GUIDE.md` documents only three valid difficulties.
No document anywhere specifies or endorses a silent fallback.

**Decision: Fix the source. `from_difficulty()` must raise `ValueError` on unknown input.**

Rationale:
1. The test documents the intended contract. Tests are the executable specification.
2. Silent fallback to a different difficulty than requested violates the principle of least
   surprise. A caller passing `"impossible"` would receive a 16×16 board with zero warning,
   making debugging extremely difficult.
3. `DIFFICULTIES` is a closed dictionary of three known values. Any string outside that
   set is a programming error and must be surfaced immediately.
4. `ValueError` is the correct Python exception type for invalid argument values.

---

### Decision D-002: `Board.toggle_flag()` win-check at line 221

**Issue:** `GWHARDEN-004`
**Question:** The win-check inside `toggle_flag()` is unreachable. Should it be removed,
or corrected to implement a "win when all mines are flagged" rule?

**Evidence:**

Current source at `engine.py:200–224`:
```python
def toggle_flag(self, x: int, y: int) -> str:
    ...
    # hidden → flag
    self._flagged[y, x] = True

    if self.revealed_count == self.total_safe:   # ← line 221
        self._state = "won"

    return "flag"
```

`revealed_count` returns `int(self._revealed.sum())`.
`total_safe` returns `self.width * self.height - self.total_mines`.
Placing a flag does not call `self._revealed` anywhere. Therefore `revealed_count` cannot
increase inside `toggle_flag()`. The condition `self.revealed_count == self.total_safe` can
only be True if all safe cells were already revealed *before* this flag was placed, which
would have already transitioned to `"won"` during the preceding `reveal()` call. The check
is structurally unreachable.

`ARCHITECTURE.md` states explicitly:
> *"Win detection: all safe cells revealed"*
> *"Board States: `playing` → `won` (all safe cells revealed)"*

`tests/unit/test_board.py:189–196` confirms:
```python
def test_win_does_not_require_flagging_mines(self):
    """Win is purely safe-cell count — no flags needed."""
```

There is no documented game rule that grants a win through flag placement.

**Decision: Remove the dead win-check from `toggle_flag()` entirely.**

Rationale:
1. The check is provably unreachable. No input sequence can cause it to fire.
2. `ARCHITECTURE.md` and `GAME_DESIGN.md` both define win as reveal-count-only.
3. Implementing a "win-on-flag" rule is explicitly out of scope for this plan. If that
   rule is desired in future, it must be added through a new design document and a
   separate PR, not by correcting this dead code in place.
4. Removing dead code reduces cognitive overhead for future readers.

---

## 4. Pre-Implementation Checklist

The following steps must be completed **before any code change is committed**.
Each step has a binary pass/fail outcome and must be documented by the implementor.

### Step 1: Capture the Baseline Test Run

Run the complete test suite from the repo root and save the output:

```bash
cd /path/to/MineStreakerContrastCampaign
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest gameworks/tests/ -v --tb=short \
  --ignore=gameworks/tests/renderer \
  2>&1 | tee gameworks/docs/baseline_test_run.txt
```

Run renderer tests separately (requires dummy SDL):
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest gameworks/tests/renderer/ -v --tb=short \
  2>&1 | tee -a gameworks/docs/baseline_test_run.txt
```

Record the following from the output in a comment on the first PR:
- Total tests collected
- Total passed
- Total failed
- Total errors
- Total skipped
- Total xfailed/xpassed

This baseline is the reference. No previously-passing test may regress.

### Step 2: Confirm Python and Package Versions

```bash
python --version
python -m pytest --version
python -c "import pygame; print(pygame.__version__)"
python -c "import numpy; print(numpy.__version__)"
```

Record output. This plan was authored against Python 3.10–3.12 and the package
versions in `requirements.txt`. Tests involving `time.sleep` may be sensitive to
slow CI machines — this is acceptable and noted per-ticket.

### Step 3: Confirm All Skipped Tests Remain Skipped

The following test files/classes are permanently skipped because they test features
not yet implemented (R2, R3, R6, R8, R9 from `DESIGN_PATTERNS.md`). Verify they are
still skipped with `pytest.mark.skip` and not accidentally run:

- `tests/unit/test_config.py` — `pytestmark = pytest.mark.skip` (R2)
- `tests/cli/test_preflight.py` — `pytestmark = pytest.mark.skip` (R6)
- `tests/unit/test_board_loading.py::TestBoardLoadResult` — all methods `@pytest.mark.skip` (R3)
- `tests/unit/test_board_loading.py::TestSchemaVersioning` — all methods `@pytest.mark.skip` (R9)
- `tests/integration/test_board_modes.py::TestSaveLoadRoundTrip::test_atomic_save_uses_tmp_then_replace` — `@pytest.mark.skip` (R8)

**None of these files are touched by this plan.** Their skip status must not change.

### Step 4: Verify Branch and Working Tree State

```bash
git status           # must show clean working tree
git branch           # must be on frontend-game-mockup
git log --oneline -5 # confirm ancestry
```

### Step 5: Confirm No Pre-existing Uncommitted Changes in Scope

The following files will be modified by this plan. None of them may have uncommitted
changes before work begins:

**Source files:**
- `gameworks/engine.py`

**Test files:**
- `gameworks/tests/unit/test_board.py`
- `gameworks/tests/unit/test_engine.py`
- `gameworks/tests/unit/test_board_loading.py`
- `gameworks/tests/integration/test_board_modes.py`
- `gameworks/tests/cli/test_parser.py`
- `gameworks/tests/architecture/test_boundaries.py`
- `gameworks/tests/renderer/test_event_handling.py`
- `gameworks/tests/renderer/test_renderer_init.py`
- `gameworks/tests/renderer/test_surface_cache.py`

---

## 5. Issue Register

| ID | Phase | Priority | Category | File(s) | Lines | Summary |
|----|-------|----------|----------|---------|-------|---------|
| GWHARDEN-001 | 1 | P0 | Test Bug | `test_parser.py` | 74–84 | `--width`/`--height` flags do not exist in parser |
| GWHARDEN-002 | 1 | P0 | Test Bug | `test_parser.py` | 56–66, 110–114 | `args.easy/medium/hard` attributes do not exist |
| GWHARDEN-003 | 1 | P0 | Source Bug | `engine.py`, `test_engine.py` | 523–525, 339–341 | `from_difficulty()` silently falls back instead of raising |
| GWHARDEN-004 | 2 | P1 | Source Bug | `engine.py` | 221–222 | Dead win-check in `toggle_flag()` is unreachable |
| GWHARDEN-005 | 3 | P2 | Weak Assertion | `test_engine.py` | 191–201 | `score <= 500` allows no penalty to be applied |
| GWHARDEN-006 | 3 | P2 | Incorrect Test | `test_surface_cache.py` | 73–79 | Fog cache test never enables fog; trivially passes |
| GWHARDEN-007 | 3 | P2 | Incorrect Expectation | `test_renderer_init.py`, `test_surface_cache.py` | 110–112, 27–30 | `_num_surfs` is always a dict after `__init__`; None branch is unreachable |
| GWHARDEN-008 | 3 | P2 | Doc/Design | `test_boundaries.py` | 41–56 | `_imports_in` docstring falsely claims it does not descend into function bodies |
| GWHARDEN-009 | 3 | P2 | Weak Assertion | `test_board.py` | 284–290 | `chord` noop test does not assert `revealed == []` |
| GWHARDEN-010 | 3 | P2 | Weak Assertion | `test_board_modes.py` | 119–130 | Save/load round-trip verifies mine count only, not positions |
| GWHARDEN-011 | 4 | P3 | Missing Coverage | `test_engine.py` | — | `GameEngine.dev_solve_board()` has zero test coverage |
| GWHARDEN-012 | 4 | P3 | Missing Coverage | `test_board.py` | — | `Board.game_over` True state (post-win) never tested |
| GWHARDEN-013 | 4 | P3 | Missing Coverage | `test_board.py` | — | `safe_revealed_count` mine-exclusion semantics never tested |
| GWHARDEN-014 | 4 | P3 | Missing Coverage | `test_engine.py` | — | `restart()` for npy and image modes never tested |
| GWHARDEN-015 | 4 | P3 | Missing Coverage | `test_board_loading.py` | — | 3-dimensional array input to `load_board_from_npy` never tested |
| GWHARDEN-016 | 4 | P3 | Missing Coverage | `test_event_handling.py` | — | Arrow-key pan events not tested |
| GWHARDEN-017 | 4 | P3 | Missing Coverage | `test_board.py` | 292–298 | `chord()` success path does not verify any cells were actually revealed |

---

## 6. Phase Plan Overview

```
Phase 1 — P0 Critical (unblock CI)
  GWHARDEN-001  GWHARDEN-002  GWHARDEN-003
  Can be implemented in parallel. Must merge before Phase 3 and 4.
  GWHARDEN-003 is the only ticket that modifies engine.py in this phase.

Phase 2 — P1 Source Logic (no CI dependency, can run in parallel with Phase 1)
  GWHARDEN-004
  Modifies engine.py. Must not be merged in the same PR as GWHARDEN-003
  to keep each change reviewable in isolation.

Phase 3 — P2 Assertion Hardening (depends on Phase 1 being merged)
  GWHARDEN-005  GWHARDEN-006  GWHARDEN-007
  GWHARDEN-008  GWHARDEN-009  GWHARDEN-010
  All test-only changes. No source changes. Can be grouped into
  one PR per affected test file or one omnibus PR — implementor's choice.
  GWHARDEN-005 requires GWHARDEN-003 to already be merged (the source
  now raises on invalid difficulty; import list must include WRONG_FLAG_PENALTY).

Phase 4 — P3 Coverage Expansion (no ordering dependency; independent of Phases 1–3)
  GWHARDEN-011  GWHARDEN-012  GWHARDEN-013  GWHARDEN-014
  GWHARDEN-015  GWHARDEN-016  GWHARDEN-017
  All new test code only. No source changes. Can be implemented
  in parallel once the baseline has been captured (Step 1 above).
```

**Merge order constraint summary:**
- Phase 1 before Phase 3 (GWHARDEN-005 reads WRONG_FLAG_PENALTY which needs engine.py stable)
- Phase 2 is independent but must not be merged with Phase 1 in the same commit
- Phase 4 is fully independent and can be merged in any order

---

## 7. Implementation Specifications — Phase 1 (P0 Critical)

---

### GWHARDEN-001

**Title:** Fix `test_parser.py` — `--width` and `--height` do not exist; correct flags are `--board-w` and `--board-h`

**Priority:** P0
**Category:** Test Bug
**File:** `gameworks/tests/cli/test_parser.py`
**Lines affected:** 73–84

**Root Cause:**

`build_parser()` in `main.py:55–56` defines the width and height flags as:
```python
p.add_argument("--board-w", type=int, default=300, help="Board width  (tiles)")
p.add_argument("--board-h", type=int, default=370, help="Board height (tiles)")
```

Argparse converts hyphenated long options to underscore attributes: `--board-w` → `args.board_w`,
`--board-h` → `args.board_h`. The tests use `--width` and `--height` which argparse does not
recognize and will reject with `SystemExit(2)`.

**Current code at `test_parser.py:73–84` (WRONG):**
```python
class TestDimensionFlags:

    def test_width_flag(self):
        args = parse("--random", "--width", "20")
        assert args.width == 20

    def test_height_flag(self):
        args = parse("--random", "--height", "15")
        assert args.height == 15
```

**Required change — replace those two test methods with:**
```python
class TestDimensionFlags:

    def test_board_w_flag(self):
        args = parse("--board-w", "20")
        assert args.board_w == 20

    def test_board_h_flag(self):
        args = parse("--board-h", "15")
        assert args.board_h == 15
```

Note: `--random` is removed from these calls because `--board-w` and `--board-h` are
not mode-restricted flags. The parser allows them standalone.

**Acceptance Criteria:**
- `test_board_w_flag` passes: `parse("--board-w", "20").board_w == 20`
- `test_board_h_flag` passes: `parse("--board-h", "15").board_h == 15`
- `pytest tests/cli/test_parser.py -v` exits 0
- No other tests in `test_parser.py` regress

**Risk:** None. Test-only change. No behavior change to source.

**Dependencies:** None.

---

### GWHARDEN-002

**Title:** Fix `test_parser.py` — `args.easy`, `args.medium`, `args.hard` do not exist; correct attribute is `args.diff`

**Priority:** P0
**Category:** Test Bug
**File:** `gameworks/tests/cli/test_parser.py`
**Lines affected:** 56–66, 110–114

**Root Cause:**

`build_parser()` in `main.py:51–53` defines difficulty flags with a shared destination:
```python
diff = p.add_mutually_exclusive_group()
diff.add_argument("--easy",   action="store_const", const="easy",   dest="diff")
diff.add_argument("--medium", action="store_const", const="medium", dest="diff")
diff.add_argument("--hard",   action="store_const", const="hard",   dest="diff")
```

When `dest="diff"` is specified, argparse writes to `args.diff` only. The attributes
`args.easy`, `args.medium`, and `args.hard` are never created. Accessing them raises
`AttributeError`.

After `parse_args(["--easy"])`: `args.diff == "easy"`
After `parse_args(["--medium"])`: `args.diff == "medium"`
After `parse_args(["--hard"])`: `args.diff == "hard"`
After `parse_args([])`: `args.diff is None`

**Current code at `test_parser.py:53–66` (WRONG):**
```python
class TestDifficultyFlags:

    def test_easy_flag_exists(self):
        args = parse("--random", "--easy")
        assert args.easy is True

    def test_medium_flag_exists(self):
        args = parse("--random", "--medium")
        assert args.medium is True

    def test_hard_flag_exists(self):
        args = parse("--random", "--hard")
        assert args.hard is True
```

**Current code at `test_parser.py:107–114` (WRONG):**
```python
class TestDefaults:

    def test_easy_medium_hard_default_false(self):
        args = parse("--random")
        assert args.easy is False
        assert args.medium is False
        assert args.hard is False
```

**Required change — replace `TestDifficultyFlags` with:**
```python
class TestDifficultyFlags:

    def test_easy_sets_diff(self):
        args = parse("--random", "--easy")
        assert args.diff == "easy"

    def test_medium_sets_diff(self):
        args = parse("--random", "--medium")
        assert args.diff == "medium"

    def test_hard_sets_diff(self):
        args = parse("--random", "--hard")
        assert args.diff == "hard"
```

**Required change — replace `test_easy_medium_hard_default_false` with:**
```python
    def test_diff_default_none(self):
        """No difficulty flag supplied — args.diff must be None (auto-computed by engine)."""
        args = parse("--random")
        assert args.diff is None
```

**Acceptance Criteria:**
- `test_easy_sets_diff`: `parse("--random", "--easy").diff == "easy"` — passes
- `test_medium_sets_diff`: `parse("--random", "--medium").diff == "medium"` — passes
- `test_hard_sets_diff`: `parse("--random", "--hard").diff == "hard"` — passes
- `test_diff_default_none`: `parse("--random").diff is None` — passes
- `test_easy_and_hard_mutually_exclusive` still passes (uses `pytest.raises(SystemExit)`)
- `test_easy_and_medium_mutually_exclusive` still passes
- `pytest tests/cli/test_parser.py -v` exits 0

**Risk:** None. Test-only change.

**Dependencies:** None.

---

### GWHARDEN-003

**Title:** Fix `engine.py` — `from_difficulty()` must raise `ValueError` on unknown difficulty string

**Priority:** P0
**Category:** Source Bug
**Files:**
- `gameworks/engine.py` lines 522–525 (source fix)
- `gameworks/tests/unit/test_engine.py` lines 339–341 (test was correct; verify it passes)

**Root Cause:**

`from_difficulty()` uses `.get()` with a default, silently returning a medium board
for any unknown input string:
```python
w, h, m = cls.DIFFICULTIES.get(diff, cls.DIFFICULTIES["medium"])
```

The test expects `ValueError` or `KeyError` to be raised. The test is correct per
Decision D-001.

**Current code at `engine.py:522–525` (WRONG):**
```python
@classmethod
def from_difficulty(cls, diff: str, seed: int = 42) -> "GameEngine":
    w, h, m = cls.DIFFICULTIES.get(diff, cls.DIFFICULTIES["medium"])
    return cls(mode="random", width=w, height=h, mines=m, seed=seed)
```

**Required change — replace with:**
```python
@classmethod
def from_difficulty(cls, diff: str, seed: int = 42) -> "GameEngine":
    if diff not in cls.DIFFICULTIES:
        raise ValueError(
            f"Unknown difficulty {diff!r}. "
            f"Valid values: {list(cls.DIFFICULTIES)}"
        )
    w, h, m = cls.DIFFICULTIES[diff]
    return cls(mode="random", width=w, height=h, mines=m, seed=seed)
```

**Existing test at `test_engine.py:339–341` (CORRECT — no change needed):**
```python
def test_invalid_difficulty_raises(self):
    with pytest.raises((KeyError, ValueError)):
        GameEngine.from_difficulty("impossible")
```

This test passes once the source is fixed. No change is required to the test itself.

**Additional verification:** Confirm the three valid paths still work. These existing
tests must remain passing:
- `test_easy_preset`: `from_difficulty("easy")` → 9×9, 10 mines
- `test_medium_preset`: `from_difficulty("medium")` → 16×16, 40 mines
- `test_hard_preset`: `from_difficulty("hard")` → 30×16, 99 mines

**Acceptance Criteria:**
- `GameEngine.from_difficulty("impossible")` raises `ValueError`
- `GameEngine.from_difficulty("easy")` returns board with `width=9, height=9, total_mines=10`
- `GameEngine.from_difficulty("medium")` returns board with `width=16, height=16, total_mines=40`
- `GameEngine.from_difficulty("hard")` returns board with `width=30, height=16, total_mines=99`
- `pytest tests/unit/test_engine.py::TestFromDifficulty -v` all pass

**Risk:** Low. The only callers of `from_difficulty()` in the codebase are
`GameLoop._build_engine()` in `main.py:103–104` and the test suite. In `_build_engine()`,
the `diff` value comes from `args.diff` which is restricted by the mutually exclusive
argparse group to `"easy"`, `"medium"`, `"hard"`, or `None`. When `args.diff is None`,
`_build_engine()` does not call `from_difficulty()` at all (the `if getattr(a, 'diff', None):`
guard on line 102 prevents it). Therefore no valid runtime path passes an unknown value
to `from_difficulty()`.

**Dependencies:** Should be merged in a separate PR from GWHARDEN-004 (both touch `engine.py`).

---

## 8. Implementation Specifications — Phase 2 (P1 Source Logic)

---

### GWHARDEN-004

**Title:** Remove dead win-check from `Board.toggle_flag()`

**Priority:** P1
**Category:** Source Bug (dead code)
**File:** `gameworks/engine.py`
**Lines affected:** 221–222

**Root Cause:**

`toggle_flag()` contains a win-check that is structurally unreachable per Decision D-002.

**Current code at `engine.py:200–224` (showing only `hidden → flag` branch):**
```python
    # hidden → flag
    self._flagged[y, x] = True

    if self.revealed_count == self.total_safe:
        self._state = "won"

    return "flag"
```

**Required change — remove the dead check entirely:**
```python
    # hidden → flag
    self._flagged[y, x] = True
    return "flag"
```

The full `toggle_flag` method after the change:
```python
def toggle_flag(self, x: int, y: int) -> str:
    """Right-click cycle: hidden → flag → ? → hidden.
    Returns new state: 'hidden' | 'flag' | 'question'.
    """
    if self._revealed[y, x]:
        return "hidden"

    if self._flagged[y, x]:
        # flag → question
        self._flagged[y, x] = False
        self._questioned[y, x] = True
        return "question"

    if self._questioned[y, x]:
        # question → hidden
        self._questioned[y, x] = False
        return "hidden"

    # hidden → flag
    self._flagged[y, x] = True
    return "flag"
```

**Existing tests that verify `toggle_flag` remains correct (must all pass unchanged):**
- `TestToggleFlag::test_hidden_to_flag`
- `TestToggleFlag::test_flag_to_question`
- `TestToggleFlag::test_question_to_hidden`
- `TestToggleFlag::test_revealed_cell_toggle_is_noop`
- `TestToggleFlag::test_flags_placed_counter_increments`
- `TestToggleFlag::test_flags_placed_counter_decrements_on_cycle`
- `TestToggleFlag::test_mines_remaining_decrements_with_flag`
- `TestToggleFlag::test_correct_flags_count`
- `TestToggleFlag::test_wrong_flag_positions`

**Acceptance Criteria:**
- All 9 existing `TestToggleFlag` tests pass
- `Board._state` is never set to `"won"` through `toggle_flag()` (win only via `reveal()`)
- `pytest tests/unit/test_board.py::TestToggleFlag -v` exits 0
- `pytest tests/unit/test_board.py -v` exits 0 (no regressions in the broader board suite)

**Risk:** None. The removed code is provably unreachable. Win detection via `reveal()` is
unaffected. Existing tests already verify all toggle_flag behaviors.

**Dependencies:** Do not merge in the same PR as GWHARDEN-003.

---

## 9. Implementation Specifications — Phase 3 (P2 Assertion Hardening)

---

### GWHARDEN-005

**Title:** Strengthen `test_wrong_flag_deducts_score` — use exact score value, not `<= 500`

**Priority:** P2
**Category:** Weak Assertion
**File:** `gameworks/tests/unit/test_engine.py`
**Lines affected:** 191–201

**Root Cause:**

The assertion `assert eng.score <= 500` passes even if no penalty is applied
(score == 500), because it does not enforce that the score actually decreased.

**Current code at `test_engine.py:191–201` (WRONG):**
```python
def test_wrong_flag_deducts_score(self):
    eng = make_engine()
    eng.score = 500
    # Flag a non-mine cell — find one
    for y in range(9):
        for x in range(9):
            if not eng.board._mine[y, x]:
                eng.right_click(x, y)
                assert eng.score <= 500
                return
    pytest.skip("No safe cell found")
```

**Required change:**

Step 1 — Add `WRONG_FLAG_PENALTY` to the import at the top of `test_engine.py`.

Current import at `test_engine.py:23`:
```python
from gameworks.engine import Board, GameEngine, MoveResult, place_random_mines
```

Replace with:
```python
from gameworks.engine import (
    Board, GameEngine, MoveResult, place_random_mines,
    WRONG_FLAG_PENALTY,
)
```

Step 2 — Replace the test method:
```python
def test_wrong_flag_deducts_score(self):
    """Flagging a non-mine cell must deduct exactly WRONG_FLAG_PENALTY from score."""
    eng = make_engine()
    eng.score = 500
    for y in range(9):
        for x in range(9):
            if not eng.board._mine[y, x]:
                eng.right_click(x, y)
                assert eng.score == 500 - WRONG_FLAG_PENALTY
                return
    pytest.skip("No safe cell found")
```

**Acceptance Criteria:**
- Test passes when `eng.score` is reduced by exactly `WRONG_FLAG_PENALTY` (25 points)
- Test fails if patched to make `right_click` apply no penalty (catches regression)
- `WRONG_FLAG_PENALTY` is 25 per `engine.py:39` — expected final score is `475`

**Risk:** None. Test-only change. Import addition does not affect runtime behavior.

**Dependencies:** GWHARDEN-003 must be merged first (stabilises `engine.py` imports).

---

### GWHARDEN-006

**Title:** Fix `test_fog_surf_stable_across_frames` — enable fog before drawing

**Priority:** P2
**Category:** Incorrect Test (trivially passes without exercising the code path)
**File:** `gameworks/tests/renderer/test_surface_cache.py`
**Lines affected:** 73–79

**Root Cause:**

`_draw_overlay()` in `renderer.py:682–697` returns immediately if `self.fog is False`.
The test never sets `r.fog = True`, so `_fog_surf` is never allocated. Both before and
after draws, `r._fog_surf` is `None`. The assertion `id(None) == id(None)` is trivially
`True` and proves nothing about cache stability.

**Current code at `test_surface_cache.py:73–79` (WRONG):**
```python
def test_fog_surf_stable_across_frames(self, renderer_easy):
    r, _ = renderer_easy
    r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
    surf1 = id(r._fog_surf)
    r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
    surf2 = id(r._fog_surf)
    assert surf1 == surf2, "Fog surface must not be recreated between identical frames"
```

**Required change:**
```python
def test_fog_surf_stable_across_frames(self, renderer_easy):
    """Fog surface must be allocated on first fog draw and reused on subsequent frames."""
    r, _ = renderer_easy
    r.fog = True   # enable fog so _draw_overlay() actually allocates _fog_surf
    r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
    assert r._fog_surf is not None, "_fog_surf must be allocated after first fog draw"
    surf1 = id(r._fog_surf)
    r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
    surf2 = id(r._fog_surf)
    assert surf1 == surf2, "Fog surface must not be recreated between identical frames"
```

**Acceptance Criteria:**
- `r._fog_surf is not None` after first fog-enabled draw
- `id(r._fog_surf)` is identical across two consecutive draws with same window size
- Test fails if `_draw_overlay()` is patched to allocate a new Surface every call

**Risk:** Low. This adds `r.fog = True` which causes fog rendering during the test draw
call. The renderer does not mutate engine/board state, so no side-effects on other state.

**Dependencies:** None.

---

### GWHARDEN-007

**Title:** Fix incorrect `None` expectation for `_num_surfs` in renderer init and surface cache tests

**Priority:** P2
**Category:** Incorrect Expectation
**Files:**
- `gameworks/tests/renderer/test_renderer_init.py` lines 110–112
- `gameworks/tests/renderer/test_surface_cache.py` lines 27–30

**Root Cause:**

`Renderer.__init__` at `renderer.py:391` calls `self._rebuild_num_surfs()` unconditionally.
After construction, `_num_surfs` is always a non-empty `dict`. The `None` branch in both
tests is structurally unreachable and creates a false impression that `_num_surfs` can be
`None` after init.

`renderer.py:374–375, 391` (relevant init lines):
```python
self._num_surfs: dict = {}
...
self._rebuild_num_surfs()   # always called in __init__
```

**Current code at `test_renderer_init.py:110–112` (WRONG):**
```python
def test_num_surfs_initially_none_or_dict(self, renderer_easy):
    r, _ = renderer_easy
    assert r._num_surfs is None or isinstance(r._num_surfs, dict)
```

**Required change for `test_renderer_init.py`:**
```python
def test_num_surfs_populated_after_init(self, renderer_easy):
    """_rebuild_num_surfs() is called in __init__; cache must be a non-empty dict."""
    r, _ = renderer_easy
    assert isinstance(r._num_surfs, dict)
    assert len(r._num_surfs) > 0
```

**Current code at `test_surface_cache.py:27–30` (WRONG — name and assertion both incorrect):**
```python
def test_num_surfs_none_before_first_draw(self, renderer_easy):
    """Number digit cache must be None until first draw populates it."""
    r, _ = renderer_easy
    assert r._num_surfs is None or isinstance(r._num_surfs, dict)
```

**Required change for `test_surface_cache.py`:**
```python
def test_num_surfs_populated_before_first_draw(self, renderer_easy):
    """_rebuild_num_surfs() is called in __init__; cache is populated before first draw."""
    r, _ = renderer_easy
    assert isinstance(r._num_surfs, dict)
    assert len(r._num_surfs) > 0
```

**Acceptance Criteria:**
- Both renamed tests pass with exact dict assertions
- Tests fail if `_rebuild_num_surfs()` is removed from `__init__`
- `pytest tests/renderer/test_renderer_init.py -v` exits 0
- `pytest tests/renderer/test_surface_cache.py -v` exits 0

**Risk:** None. Test-only changes.

**Dependencies:** None.

---

### GWHARDEN-008

**Title:** Correct `_imports_in()` docstring — it does descend into function bodies

**Priority:** P2
**Category:** Documentation/Design
**File:** `gameworks/tests/architecture/test_boundaries.py`
**Lines affected:** 41–56

**Root Cause:**

The docstring at line 46 states *"Does NOT descend into function bodies"*, but `ast.walk()`
traverses every node in the AST, including nodes inside function bodies, class bodies,
lambdas, and comprehensions. Any `import` statement inside a function — such as the
pipeline imports inside `engine.py:load_board_from_pipeline()` — will be found by this
helper.

This is significant because the test boundary checks for `engine.py` do not check for
pipeline module imports, and if they did, `_imports_in` would return false positives for
imports that appear inside guarded function bodies. The docstring is misleading and would
cause a future engineer to add an incorrect test guard.

Note: `TestMainBoundaries.test_main_does_not_import_pipeline_at_top_level` correctly uses
`tree.body` (top-level only) instead of `ast.walk()`. That test is correct and is NOT
changed by this ticket.

**Current code at `test_boundaries.py:41–56`:**
```python
def _imports_in(source: str) -> List[str]:
    """
    Return a flat list of all top-level module names imported in the source.
    Handles: import X, from X import Y, from X.Y import Z.
    Does NOT descend into function bodies (catches top-level and class-level imports).
    """
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module.split(".")[0])
    return names
```

**Required change — correct the docstring only; do not change the logic:**
```python
def _imports_in(source: str) -> List[str]:
    """
    Return a flat list of all module names imported anywhere in the source.
    Handles: import X, from X import Y, from X.Y import Z.
    Uses ast.walk() which descends into ALL scopes including function bodies,
    class bodies, and nested blocks. Use tree.body iteration instead if you
    need top-level-only imports (see TestMainBoundaries).
    """
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module.split(".")[0])
    return names
```

**Acceptance Criteria:**
- Docstring accurately describes the function's actual behavior
- No logic changes; all existing boundary tests pass unchanged
- `pytest tests/architecture/test_boundaries.py -v` exits 0

**Risk:** None. Documentation-only change. Zero impact on test outcomes.

**Dependencies:** None.

---

### GWHARDEN-009

**Title:** Add `assert revealed == []` to `test_chord_on_zero_count_cell_is_noop`

**Priority:** P2
**Category:** Weak Assertion
**File:** `gameworks/tests/unit/test_board.py`
**Lines affected:** 284–290

**Root Cause:**

`chord()` returns a tuple `(hit_mine: bool, newly_revealed: List)`. The test asserts
`not hit` but does not assert that the revealed list is empty. A buggy chord that
incorrectly reveals cells would pass this test.

**Current code at `test_board.py:284–290` (INCOMPLETE):**
```python
def test_chord_on_zero_count_cell_is_noop(self):
    """Chord on a revealed cell with 0 neighbours is a no-op."""
    mines = {(0, 0)}
    b = Board(9, 9, mines)
    b.reveal(8, 8)   # far corner, should be 0-count and flood-filled
    hit, revealed = b.chord(8, 8)
    assert not hit
```

**Required change:**
```python
def test_chord_on_zero_count_cell_is_noop(self):
    """Chord on a revealed cell with 0 neighbours is a no-op: no hit, no reveals."""
    mines = {(0, 0)}
    b = Board(9, 9, mines)
    b.reveal(8, 8)   # far corner, flood-fills most of the board; (8,8) has 0 neighbours
    hit, revealed = b.chord(8, 8)
    assert not hit
    assert revealed == []
```

**Acceptance Criteria:**
- Test passes on correct implementation (chord on zero-count cell returns `(False, [])`)
- Test fails if `chord()` is patched to return non-empty `revealed` on a zero-count cell
- `pytest tests/unit/test_board.py::TestChord -v` exits 0

**Risk:** None. Adding one assertion to an existing test.

**Dependencies:** None.

---

### GWHARDEN-010

**Title:** Strengthen `test_saved_board_reloads_same_mine_count` — verify exact positions, not just count

**Priority:** P2
**Category:** Weak Assertion
**File:** `gameworks/tests/integration/test_board_modes.py`
**Lines affected:** 119–130

**Root Cause:**

The test saves `b._mine.astype(np.int8)` and reloads it, asserting only
`b2.total_mines == b.total_mines`. A loader that places the correct number of mines
in wrong positions would pass this test.

**Current code at `test_board_modes.py:119–130`:**
```python
def test_saved_board_reloads_same_mine_count(self):
    from gameworks.engine import load_board_from_npy
    mines = place_random_mines(9, 9, 10, seed=42)
    b = Board(9, 9, mines)
    f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
    np.save(f.name, b._mine.astype(np.int8))
    f.close()
    try:
        b2 = load_board_from_npy(f.name)
        assert b2.total_mines == b.total_mines
    finally:
        os.unlink(f.name)
```

**Required change — add a second test for exact positions (do not modify the existing test):**

Add the following method inside `TestSaveLoadRoundTrip` immediately after the existing test:

```python
def test_saved_board_reloads_exact_mine_positions(self):
    """Mine positions after load must exactly match the original board, not just the count."""
    from gameworks.engine import load_board_from_npy
    mines = place_random_mines(9, 9, 10, seed=42)
    b = Board(9, 9, mines)
    f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
    np.save(f.name, b._mine.astype(np.int8))
    f.close()
    try:
        b2 = load_board_from_npy(f.name)
        assert set(b2.all_mine_positions()) == set(b.all_mine_positions())
    finally:
        os.unlink(f.name)
```

**Acceptance Criteria:**
- New test passes on correct implementation
- New test fails if `load_board_from_npy` places mines at different positions than saved
- Existing `test_saved_board_reloads_same_mine_count` is unchanged and still passes
- `pytest tests/integration/test_board_modes.py::TestSaveLoadRoundTrip -v` exits 0

**Risk:** None. Adding a new test method only.

**Dependencies:** None.

---

## 10. Implementation Specifications — Phase 4 (P3 Coverage Expansion)

---

### GWHARDEN-011

**Title:** Add full test coverage for `GameEngine.dev_solve_board()`

**Priority:** P3
**Category:** Missing Coverage
**File:** `gameworks/tests/unit/test_engine.py`
**Target source:** `gameworks/engine.py:633–657`

**Root Cause:**

`dev_solve_board()` has zero tests. It modifies board state atomically and transitions
to `"won"`. The method:
1. Returns `MoveResult(success=False)` if `board.game_over` is already True
2. Sets `board._revealed[~board._mine] = True` (reveals all safe cells)
3. Sets `board._flagged[:] = board._mine` (flags exactly the mines)
4. Sets `board._questioned[:] = False` (clears all question marks)
5. Sets `board._state = "won"`
6. Calls `self.stop_timer()`
7. Returns `MoveResult(success=True, state="won", score_delta=0, streak=self.streak)`

**Required change — add class `TestDevSolveBoard` at the end of `test_engine.py`:**

```python
# ---------------------------------------------------------------------------
# dev_solve_board()
# ---------------------------------------------------------------------------

class TestDevSolveBoard:

    def _make_solvable_engine(self):
        """Engine in PLAYING state, first click already made, streak and score at 0."""
        eng = make_engine()
        eng._first_click = False
        return eng

    def test_returns_move_result(self):
        eng = self._make_solvable_engine()
        result = eng.dev_solve_board()
        assert isinstance(result, MoveResult)

    def test_returns_success_true_on_playing_board(self):
        eng = self._make_solvable_engine()
        result = eng.dev_solve_board()
        assert result.success is True

    def test_transitions_board_to_won(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.board._state == "won"
        assert eng.board.is_won

    def test_game_over_true_after_solve(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.board.game_over

    def test_all_safe_cells_revealed_after_solve(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.board.safe_revealed_count == eng.board.total_safe

    def test_all_mines_flagged_after_solve(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.board.correct_flags == eng.board.total_mines

    def test_no_incorrect_flags_after_solve(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.board.wrong_flag_positions() == []

    def test_no_questioned_cells_after_solve(self):
        eng = self._make_solvable_engine()
        # Pre-set a question mark to confirm it gets cleared
        eng.board.toggle_flag(0, 0)   # hidden → flag
        eng.board.toggle_flag(0, 0)   # flag → question
        assert eng.board.questioned_count > 0
        eng.dev_solve_board()
        assert eng.board.questioned_count == 0

    def test_score_unchanged_after_solve(self):
        """dev_solve_board must not award or deduct any score."""
        eng = self._make_solvable_engine()
        eng.score = 300
        eng.dev_solve_board()
        assert eng.score == 300

    def test_streak_unchanged_after_solve(self):
        eng = self._make_solvable_engine()
        eng.streak = 7
        eng.dev_solve_board()
        assert eng.streak == 7

    def test_already_won_returns_success_false(self):
        """Calling dev_solve_board on an already-won board must return success=False."""
        mines = {(0, 0)}
        eng = GameEngine(mode="random", width=2, height=2, mines=1, seed=0)
        eng.board = Board(2, 2, mines)
        eng._first_click = False
        eng.start()
        # Win the board the normal way
        eng.left_click(1, 0)
        eng.left_click(0, 1)
        eng.left_click(1, 1)
        assert eng.board.is_won
        result = eng.dev_solve_board()
        assert result.success is False
```

**Acceptance Criteria:**
- All 11 new tests pass
- Each test isolates a single aspect of `dev_solve_board()` behavior
- `pytest tests/unit/test_engine.py::TestDevSolveBoard -v` exits 0

**Risk:** None. New tests only. No source changes.

**Dependencies:** None.

---

### GWHARDEN-012

**Title:** Add test — `Board.game_over` returns `True` after winning

**Priority:** P3
**Category:** Missing Coverage
**File:** `gameworks/tests/unit/test_board.py`
**Target source:** `gameworks/engine.py:162–163`

**Root Cause:**

`TestBoardProperties` tests `game_over` only in the False state. There is no test
that `game_over` returns True after a win transition.

**Required change — add to `TestBoardProperties`:**

```python
def test_game_over_true_after_win(self):
    """game_over must return True once the board transitions to 'won'."""
    mines = {(0, 0)}
    b = Board(2, 2, mines)
    b.reveal(1, 0)
    b.reveal(0, 1)
    b.reveal(1, 1)
    assert b.is_won
    assert b.game_over
```

**Acceptance Criteria:**
- Test passes: `b.game_over is True` after all safe cells revealed
- Test fails if `game_over` is patched to always return `False`
- `pytest tests/unit/test_board.py::TestBoardProperties -v` exits 0

**Risk:** None. New test method only.

**Dependencies:** None.

---

### GWHARDEN-013

**Title:** Add test — `safe_revealed_count` excludes mine-hit cells

**Priority:** P3
**Category:** Missing Coverage
**File:** `gameworks/tests/unit/test_board.py`
**Target source:** `gameworks/engine.py:134–135`

**Root Cause:**

The docstring for `safe_revealed_count` states *"Revealed cells that are NOT mines
(excludes mine-hit cells from count)"*. This exclusion is never verified by the test
suite. A regression that changed the implementation to `int(self._revealed.sum())`
(counting all revealed including mines) would not be caught.

**Required change — add to `TestReveal`:**

```python
def test_safe_revealed_count_excludes_mine_hit(self):
    """Revealing a mine (hit) marks it as revealed but must NOT increment safe_revealed_count."""
    mines = {(0, 0)}
    b = Board(3, 3, mines)
    hit, _ = b.reveal(0, 0)   # hit the mine
    assert hit                           # confirm it was a mine hit
    assert b._revealed[0, 0]            # mine is marked revealed in the array
    assert b.safe_revealed_count == 0   # but not counted as a safe cell
```

**Acceptance Criteria:**
- Test passes: hitting a mine does not increment `safe_revealed_count`
- Test fails if `safe_revealed_count` is changed to count all revealed cells
- `pytest tests/unit/test_board.py::TestReveal -v` exits 0

**Risk:** None. New test method only.

**Dependencies:** None.

---

### GWHARDEN-014

**Title:** Add tests for `GameEngine.restart()` in npy and image modes

**Priority:** P3
**Category:** Missing Coverage
**File:** `gameworks/tests/unit/test_engine.py`
**Target source:** `gameworks/engine.py:667–670` (npy branch), `671–673` (image branch)

**Root Cause:**

`TestRestart` only tests the `"random"` mode restart branch. The `"npy"` branch
(`engine.py:667–668`) and `"image"` branch (`engine.py:669–670`) are untested.

**Required change — add to `TestRestart`:**

```python
def test_npy_mode_restart_preserves_mine_count(self):
    """Restarting an npy-mode engine must reload the same board (same mine count)."""
    import os
    import tempfile
    import numpy as np
    grid = np.zeros((5, 5), dtype=np.int8)
    grid[0, 0] = 1
    grid[4, 4] = 1
    f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
    np.save(f.name, grid)
    f.close()
    try:
        eng = GameEngine(mode="npy", npy_path=f.name, seed=1)
        eng.start()
        mines_before = eng.board.total_mines
        eng.restart()
        assert eng.board.total_mines == mines_before
        assert eng.score == 0
        assert eng.streak == 0
    finally:
        os.unlink(f.name)

def test_npy_mode_restart_preserves_exact_mine_positions(self):
    """Restarting an npy-mode engine must reload the exact same mine layout."""
    import os
    import tempfile
    import numpy as np
    grid = np.zeros((5, 5), dtype=np.int8)
    grid[0, 0] = 1
    grid[4, 4] = 1
    f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
    np.save(f.name, grid)
    f.close()
    try:
        eng = GameEngine(mode="npy", npy_path=f.name, seed=1)
        eng.start()
        positions_before = set(eng.board.all_mine_positions())
        eng.restart()
        positions_after = set(eng.board.all_mine_positions())
        assert positions_after == positions_before
    finally:
        os.unlink(f.name)

def test_image_mode_restart_produces_playable_board(self):
    """Restarting an image-mode engine (pipeline unavailable) falls back to random."""
    eng = GameEngine(mode="image", image_path="/nonexistent/image.png",
                     width=9, height=9, seed=1)
    eng.start()
    assert eng.state == "playing"
    eng.restart()
    assert eng.state == "playing"
    assert eng.board.total_mines >= 1
    assert eng.score == 0
    assert eng.streak == 0
```

**Acceptance Criteria:**
- `test_npy_mode_restart_preserves_mine_count` passes
- `test_npy_mode_restart_preserves_exact_mine_positions` passes
- `test_image_mode_restart_produces_playable_board` passes (pipeline fallback fires)
- `pytest tests/unit/test_engine.py::TestRestart -v` all pass

**Risk:** None. New test methods only.

**Dependencies:** None.

---

### GWHARDEN-015

**Title:** Add test — `load_board_from_npy` raises `ValueError` for 3-dimensional input array

**Priority:** P3
**Category:** Missing Coverage
**File:** `gameworks/tests/unit/test_board_loading.py`
**Target source:** `gameworks/engine.py:317`

**Root Cause:**

`engine.py:317` raises `ValueError` for any `ndim != 2`:
```python
if grid.ndim != 2:
    raise ValueError(f"Expected 2D array, got shape {grid.shape}")
```

`TestLoadErrors` covers 1D arrays but not 3D arrays. Both should be tested as they
are distinct paths into the same validation check.

**Required change — add to `TestLoadErrors`:**

```python
def test_3d_array_raises_value_error(self):
    """A 3-dimensional numpy array must raise ValueError, not load silently."""
    grid = np.zeros((3, 3, 3), dtype=np.int8)
    path = write_npy(grid)
    try:
        with pytest.raises(ValueError, match="Expected 2D array"):
            load_board_from_npy(path)
    finally:
        os.unlink(path)
```

Note: `match="Expected 2D array"` asserts the error message substring. This is pinned
to the message at `engine.py:318`. If the error message is changed, update the match
string here.

**Acceptance Criteria:**
- Test passes: 3D array raises `ValueError` with message containing "Expected 2D array"
- Test fails if the ndim check is removed from `load_board_from_npy`
- `pytest tests/unit/test_board_loading.py::TestLoadErrors -v` exits 0

**Risk:** None. New test method only.

**Dependencies:** None.

---

### GWHARDEN-016

**Title:** Add tests for arrow-key pan events in `Renderer.handle_event()`

**Priority:** P3
**Category:** Missing Coverage
**File:** `gameworks/tests/renderer/test_event_handling.py`
**Target source:** `gameworks/renderer.py:467–479`

**Root Cause:**

The four arrow key handlers (`K_LEFT`, `K_RIGHT`, `K_UP`, `K_DOWN`) are completely
untested. They update `_pan_x`/`_pan_y` and return `None`. A regression removing any
of them would go undetected.

**Required change — add class `TestHandleEventArrowKeys` to `test_event_handling.py`:**

```python
class TestHandleEventArrowKeys:

    def test_left_arrow_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode="")
        result = r.handle_event(ev)
        assert result is None

    def test_right_arrow_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0, unicode="")
        result = r.handle_event(ev)
        assert result is None

    def test_up_arrow_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_UP, mod=0, unicode="")
        result = r.handle_event(ev)
        assert result is None

    def test_down_arrow_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode="")
        result = r.handle_event(ev)
        assert result is None

    def test_left_arrow_moves_pan_x_toward_zero_when_negative(self, renderer_easy):
        """K_LEFT adds tile*3 to pan_x. When pan_x is negative, it moves toward 0."""
        r, _ = renderer_easy
        r._pan_x = -100
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode="")
        r.handle_event(ev)
        assert r._pan_x > -100   # moved right (less negative)

    def test_right_arrow_decreases_pan_x_on_large_board(self):
        """K_RIGHT subtracts tile*3 from pan_x when the board overflows the viewport."""
        from gameworks.engine import GameEngine
        from gameworks.renderer import Renderer
        # 60-wide board at tile=32 = 1920px wide, exceeds any test window
        eng = GameEngine(mode="random", width=60, height=9, mines=10, seed=42)
        eng.start()
        r = Renderer(eng)
        r._pan_x = 0
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0, unicode="")
        r.handle_event(ev)
        assert r._pan_x < 0   # moved left
```

**Note on `test_right_arrow_decreases_pan_x_on_large_board`:** This test constructs
its own `Renderer` instead of using the `renderer_easy` fixture because the easy fixture
(9×9, 32px tile = 288px wide) produces a board that fits entirely in the test window,
causing `max_pan` to be 0 and clamping pan_x to 0 regardless of the key press. A 60-wide
board ensures the board overflows.

**Acceptance Criteria:**
- All 6 new tests pass
- Tests `test_left/right/up/down_arrow_returns_none` fail if arrow keys are removed
- `test_left_arrow_moves_pan_x_toward_zero_when_negative` fails if K_LEFT handler is removed
- `test_right_arrow_decreases_pan_x_on_large_board` fails if K_RIGHT handler is removed
- `pygame.display.set_mode((800, 600))` is already called by the `_pygame_module_init`
  fixture in `renderer/conftest.py` — the new large-board Renderer may resize the window
  in dummy driver mode but must not raise

**Risk:** Low. The new large-board Renderer test creates a window via the dummy driver.
It must be verified that `pygame.display.Info()` returns sensible values under the dummy
driver (it returns 0×0, which the Renderer clamps to minimum sizes of 780×480).

**Dependencies:** None. All renderer tests require the `renderer/conftest.py` fixtures.

---

### GWHARDEN-017

**Title:** Add assertion that `chord()` actually reveals cells when flag count matches

**Priority:** P3
**Category:** Missing Coverage
**File:** `gameworks/tests/unit/test_board.py`
**Lines affected:** 292–298 (existing test `test_chord_fires_when_flag_count_matches`)

**Root Cause:**

`test_chord_fires_when_flag_count_matches` asserts `not hit` but never asserts that any
cells were actually revealed. A chord that fires correctly should reveal at least the
unflagged neighbors of the chording cell. A regression that made `chord()` a no-op would
pass this test.

**Current code at `test_board.py:292–298`:**
```python
def test_chord_fires_when_flag_count_matches(self):
    mines = {(0, 0)}
    b = Board(5, 5, mines)
    b.reveal(1, 1)          # count = 1 (adjacent to mine at 0,0)
    b.toggle_flag(0, 0)     # flag the mine
    hit, revealed = b.chord(1, 1)
    assert not hit
```

**Required change — add the revealed assertion and clarify the setup comment:**

```python
def test_chord_fires_when_flag_count_matches(self):
    """When flag count == cell number, chord reveals all unflagged neighbours."""
    mines = {(0, 0)}
    b = Board(5, 5, mines)
    b.reveal(1, 1)           # neighbour_mines == 1 at (1,1): adjacent to mine at (0,0)
    b.toggle_flag(0, 0)      # flag the mine: flag count around (1,1) now == 1 == number
    hit, revealed = b.chord(1, 1)
    assert not hit            # no unflagged mines in neighbourhood
    assert len(revealed) > 0  # at least one unflagged neighbour was revealed
```

**Acceptance Criteria:**
- Test passes: `len(revealed) > 0` after a valid chord
- Test fails if `chord()` is patched to return `(False, [])` unconditionally
- `pytest tests/unit/test_board.py::TestChord -v` exits 0

**Risk:** None. Adding one assertion to an existing test.

**Dependencies:** None.

---

## 11. Verification Matrix

For each ticket, the following must be confirmed after implementation before marking Done.

| ID | Pre-change state | Post-change state | Regression check |
|----|-----------------|-------------------|-----------------|
| GWHARDEN-001 | `test_board_w_flag`, `test_board_h_flag` FAIL (SystemExit) | Both PASS | All other `test_parser.py` tests unchanged |
| GWHARDEN-002 | `test_easy_sets_diff`, `test_medium_sets_diff`, `test_hard_sets_diff`, `test_diff_default_none` FAIL (AttributeError) | All 4 PASS | `test_easy_and_hard_mutually_exclusive` still raises SystemExit |
| GWHARDEN-003 | `test_invalid_difficulty_raises` FAILS (no exception raised) | PASSES | `test_easy_preset`, `test_medium_preset`, `test_hard_preset` still PASS |
| GWHARDEN-004 | Dead code exists at `engine.py:221–222`; all toggle tests PASS | Dead code removed; all toggle tests still PASS | Win detection via `reveal()` unaffected |
| GWHARDEN-005 | `test_wrong_flag_deducts_score` PASSES with `score <= 500` (may not catch missing penalty) | PASSES with `score == 475` (catches any deviation) | All other `TestScoring` tests unchanged |
| GWHARDEN-006 | `test_fog_surf_stable_across_frames` passes trivially (`None is None`) | PASSES while actually exercising fog draw path; `_fog_surf is not None` verified | `test_fog_surf_type` unchanged |
| GWHARDEN-007 | Tests allow `None` branch (unreachable) | Tests assert `isinstance(dict)` and `len > 0` only | `test_num_surfs_populated_after_draw` still passes |
| GWHARDEN-008 | Docstring says "does NOT descend" (incorrect) | Docstring says "descends into ALL scopes" (correct) | All boundary assertions unchanged |
| GWHARDEN-009 | `test_chord_on_zero_count_cell_is_noop` passes without checking `revealed` | PASSES with `revealed == []` asserted | All other `TestChord` tests unchanged |
| GWHARDEN-010 | Only mine count compared in round-trip | Both count and exact positions compared | Existing `test_saved_board_reloads_same_mine_count` unchanged |
| GWHARDEN-011 | 0 tests for `dev_solve_board()` | 11 new tests, all PASS | No existing test regresses |
| GWHARDEN-012 | `game_over` True state never tested | `test_game_over_true_after_win` PASSES | `test_game_over_false_while_playing` unchanged |
| GWHARDEN-013 | Mine-exclusion in `safe_revealed_count` untested | `test_safe_revealed_count_excludes_mine_hit` PASSES | `test_safe_cells_count_tracks_reveals` unchanged |
| GWHARDEN-014 | Only random-mode restart tested | 3 new restart tests PASS (2 npy, 1 image) | All existing `TestRestart` tests unchanged |
| GWHARDEN-015 | Only 1D array tested for ValueError | 3D array test PASSES with `ValueError` | `test_1d_array_raises_value_error` unchanged |
| GWHARDEN-016 | 0 tests for arrow key events | 6 new arrow key tests, all PASS | All existing `TestHandleEvent*` tests unchanged |
| GWHARDEN-017 | `chord()` success: only `not hit` asserted | Also asserts `len(revealed) > 0` | Other `TestChord` tests unchanged |

---

## 12. CI Configuration Requirements

The following CI settings must be verified before this plan's PRs are merged.
If CI is not yet configured, these are the minimum requirements.

### Environment Variables

All test runs that import `gameworks.renderer` or `pygame` must set:
```
SDL_VIDEODRIVER=dummy
SDL_AUDIODRIVER=dummy
```

These must be set in the CI environment before any test collection begins. The
renderer conftest at `gameworks/tests/renderer/conftest.py:17–18` uses
`os.environ.setdefault()` as a fallback, but CI-level env vars are preferred so
that the setting applies to all workers and is auditable in the pipeline config.

### Test Discovery Command

The authoritative test run command is:
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest gameworks/tests/ -v --tb=short
```

Do **not** use `python -m unittest discover` for this suite. The `DEVELOPER_GUIDE.md`
references it as an alternative but it does not handle `pytest.mark.skip`,
`pytest.importorskip`, or parametrize correctly.

### Required Exit Code

`pytest` must exit 0 (all tests pass or are explicitly skipped) for a PR to be
mergeable. Any `ERROR` in test collection (import errors, fixture errors) counts
as a failure even if pytest reports it separately from `FAILED`.

### Skipped Test Count Must Not Decrease

The baseline skip count (captured in Step 1) represents tests awaiting feature
implementation (R2, R3, R6, R8, R9). If the skip count decreases without a
corresponding feature implementation PR, it indicates a skip marker was accidentally
removed. CI must fail if `skipped < baseline_skipped`.

This can be enforced with:
```bash
SKIP_COUNT=$(pytest gameworks/tests/ --co -q 2>&1 | grep "skipped" | awk '{print $1}')
[ "$SKIP_COUNT" -ge "$BASELINE_SKIP_COUNT" ] || exit 1
```

---

## 13. Regression Protection Rules

These rules apply to every PR produced by this plan, without exception.

**Rule R-1: One concern per PR.**
Each PR addresses either one issue or a coherent group of issues within the same file.
GWHARDEN-001 and GWHARDEN-002 may be combined (both in `test_parser.py`). GWHARDEN-003
and GWHARDEN-004 must be separate PRs (both modify `engine.py` but for unrelated reasons).

**Rule R-2: Source changes require paired test verification.**
GWHARDEN-003 and GWHARDEN-004 modify `engine.py`. Each PR must include a `pytest` run
output confirming that all tests in `tests/unit/test_engine.py` and
`tests/unit/test_board.py` pass. This output must be included in the PR description.

**Rule R-3: No `# type: ignore` additions.**
This plan makes no type-unsafe changes. If a type error surfaces during implementation,
resolve the root cause rather than suppressing the error.

**Rule R-4: No change to skipped test markers.**
The following skip markers must not be added, removed, or modified by this plan:
- `pytestmark = pytest.mark.skip` in `test_config.py`
- `pytestmark = pytest.mark.skip` in `test_preflight.py`
- `@pytest.mark.skip` on methods in `TestBoardLoadResult`, `TestSchemaVersioning`
- `@pytest.mark.skip` on `test_atomic_save_uses_tmp_then_replace`

**Rule R-5: No new source functionality.**
This plan fixes bugs and adds tests. It does not add new public methods, new constants,
or new behavior to `engine.py`, `renderer.py`, or `main.py`. The only source changes
permitted are GWHARDEN-003 (add ValueError raise) and GWHARDEN-004 (remove 2 lines of
dead code).

**Rule R-6: Keep `_imports_in` logic unchanged.**
GWHARDEN-008 modifies only the docstring of `_imports_in`. The function body and all
callers remain identical.

**Rule R-7: All `time.sleep`-based tests must use conservative bounds.**
The renderer animation tests in `test_animations.py` use `time.sleep`. This plan does not
touch those tests, but any new test added in Phase 4 that uses `time.sleep` must use a
duration at least 5× longer than the expected minimum to accommodate slow CI workers.
The existing `test_animations.py` tests already follow this convention.

---

## 14. Out-of-Scope (Explicit)

The following items were identified during the forensic review but are **explicitly
excluded** from this plan. Exclusion is final for v1.0.0. A future plan version is
required to include any of these.

| Item | Reason Excluded |
|------|----------------|
| `test_config.py` (R2 — GameConfig) | Pending feature; no source implementation exists |
| `test_preflight.py` (R6 — preflight_check) | Pending feature; no source implementation exists |
| `TestBoardLoadResult` (R3 — BoardLoadResult) | Pending feature; no source implementation exists |
| `TestSchemaVersioning` (R9 — schema version) | Pending feature; no source implementation exists |
| `test_atomic_save_uses_tmp_then_replace` (R8 — atomic save) | Pending feature; no source implementation exists |
| Renderer visual correctness | Subjective; requires screenshot comparison tooling |
| Performance benchmarking | Out of test hardening scope |
| `GameEngine.restart()` with custom `width/height/mines` args | Niche override path; functional but low risk |
| `_neighbours_iter()` direct unit tests | Private method; covered transitively by reveal/chord tests |
| `_count_adj()` direct unit tests | Private method; used only in `load_board_from_npy` validation |
| `load_board_from_pipeline()` non-fallback path | Requires full Numba/SA pipeline; out of gameworks test scope |
| `GameLoop._save_npy()` integration test | Requires running the game loop; integration test scope |
| New scoring rules or game mechanic changes | Design work; out of scope for hardening |

---

## 15. Definition of Done

This plan is complete when **all** of the following conditions are simultaneously true.
Each condition is binary (pass/fail). There are no partial completions.

### Per-Ticket Completion

- [ ] GWHARDEN-001: `pytest tests/cli/test_parser.py::TestDimensionFlags -v` exits 0
- [ ] GWHARDEN-002: `pytest tests/cli/test_parser.py::TestDifficultyFlags -v` exits 0 and `test_diff_default_none` passes
- [ ] GWHARDEN-003: `pytest tests/unit/test_engine.py::TestFromDifficulty -v` all 4 tests pass
- [ ] GWHARDEN-004: `pytest tests/unit/test_board.py::TestToggleFlag -v` all 9 tests pass; dead check removed from `engine.py`
- [ ] GWHARDEN-005: `pytest tests/unit/test_engine.py::TestScoring::test_wrong_flag_deducts_score -v` passes; assertion is `== 475`
- [ ] GWHARDEN-006: `pytest tests/renderer/test_surface_cache.py::TestFogSurfCache::test_fog_surf_stable_across_frames -v` passes; `_fog_surf is not None` before second draw
- [ ] GWHARDEN-007: `pytest tests/renderer/test_renderer_init.py::TestSurfaceCacheInit::test_num_surfs_populated_after_init -v` passes; `pytest tests/renderer/test_surface_cache.py::TestNumSurfsCache::test_num_surfs_populated_before_first_draw -v` passes
- [ ] GWHARDEN-008: Docstring in `_imports_in` accurately describes `ast.walk()` behavior; all `test_boundaries.py` tests still pass
- [ ] GWHARDEN-009: `pytest tests/unit/test_board.py::TestChord::test_chord_on_zero_count_cell_is_noop -v` passes with both assertions
- [ ] GWHARDEN-010: `pytest tests/integration/test_board_modes.py::TestSaveLoadRoundTrip::test_saved_board_reloads_exact_mine_positions -v` passes
- [ ] GWHARDEN-011: `pytest tests/unit/test_engine.py::TestDevSolveBoard -v` all 11 tests pass
- [ ] GWHARDEN-012: `pytest tests/unit/test_board.py::TestBoardProperties::test_game_over_true_after_win -v` passes
- [ ] GWHARDEN-013: `pytest tests/unit/test_board.py::TestReveal::test_safe_revealed_count_excludes_mine_hit -v` passes
- [ ] GWHARDEN-014: `pytest tests/unit/test_engine.py::TestRestart -v` all 3 new tests pass alongside all existing restart tests
- [ ] GWHARDEN-015: `pytest tests/unit/test_board_loading.py::TestLoadErrors::test_3d_array_raises_value_error -v` passes
- [ ] GWHARDEN-016: `pytest tests/renderer/test_event_handling.py::TestHandleEventArrowKeys -v` all 6 tests pass
- [ ] GWHARDEN-017: `pytest tests/unit/test_board.py::TestChord::test_chord_fires_when_flag_count_matches -v` passes with `len(revealed) > 0` asserted

### Full Suite Completion

- [ ] `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v` exits 0
- [ ] Total `FAILED` count == 0
- [ ] Total `ERROR` count == 0
- [ ] Total `skipped` count >= baseline skip count from Step 1
- [ ] No test that passed in the baseline now fails

### Code Quality

- [ ] No new `# noqa` or `# type: ignore` comments introduced
- [ ] All new test methods have a one-line docstring stating what they verify
- [ ] No test imports from `gameworks.renderer` or `pygame` outside of the `renderer/` subdirectory
- [ ] No source changes exist beyond GWHARDEN-003 and GWHARDEN-004

### Documentation

- [ ] This plan file (`TEST_HARDENING_PLAN.md`) is committed to `gameworks/docs/`
- [ ] `CHANGELOG.md` updated with a `Test Hardening v0.1.1` section listing all 17 tickets

---

*Gameworks Test Hardening Plan v1.0.0 — 2026-05-10*
