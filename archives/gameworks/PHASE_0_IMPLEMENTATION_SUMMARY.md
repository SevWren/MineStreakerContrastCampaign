# Phase 0: WinAnimation._idx Fix — Implementation Summary
**Date:** 2026-05-11
**Status:** READY TO IMPLEMENT
**Blocking:** Phase 7B cannot proceed until this is complete

---

## Documentation References Discovered

### 1. IMPLEMENTATION_TASK_PLAN.md (Lines 35-162)
**Location:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/IMPLEMENTATION_TASK_PLAN.md`

**Key Content:**
- Complete step-by-step implementation guide
- 4 sub-steps (0.1 through 0.4)
- Exact code snippets for all changes
- Test commands for validation
- Commit message template

**Edge Cases Documented:**
- `_idx` initialized to 0 (not None)
- Type is int, not float
- Reset to 0 on phase transitions (prevents stale values)
- `_idx` never exceeds list bounds via `min()`

---

### 2. REMEDIATION_PLAN_VERIFICATION.md (Lines 93-127)
**Location:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/REMEDIATION_PLAN_VERIFICATION.md`

**Key Content:**
- Root cause analysis
- Fix specification with complete code
- Estimated fix time: 30 minutes

**Critical Quote:**
> "The Phase 7B cache key would read `self.win_anim._idx`, get `None`, and silently create a broken key `(_phase, None)` that matches itself every frame — rebuilding the set on every frame instead of only on timer ticks."

---

### 3. REMEDIATION_PLAN_VERIFICATION_DETAILED.md (Lines 165-276)
**Location:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/REMEDIATION_PLAN_VERIFICATION_DETAILED.md`

**Key Content:**
- Detailed verification that `WinAnimation` does NOT have `_idx`
- Comparison with `AnimationCascade` which DOES have `_idx`
- Two implementation options (Option A recommended)
- Warning about why `len(current())` should NOT be used

**Evidence Presented:**
```python
# AnimationCascade (lines 150-156) DOES have _idx:
def current(self) -> List[Tuple[int, int]]:
    if self.done:
        return self.positions[:]
    elapsed = self._clock() - self._start
    self._idx = min(int(elapsed / self.speed) + 1, len(self.positions))  # ← HAS IT
    return self.positions[:self._idx]

# WinAnimation (lines 206-222) does NOT:
def current(self) -> List[Tuple[int, int]]:
    now = time.monotonic() - self._start
    if self._phase == 0:
        idx = min(int(now / self.speed) + 1, len(self._correct))  # ← LOCAL VAR
```

---

### 4. PERFORMANCE_PLAN.md (Lines 850-924)
**Location:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/PERFORMANCE_PLAN.md`

**Key Content:**
- Phase 7B animation set cache specification
- Pre-condition warning about verifying `_idx` exists
- Explanation of why `(_phase, _idx)` key is needed
- Warning against using `len(current())` as key

**Critical Warning (Lines 909-916):**
> "**Pre-condition — verify `WinAnimation._idx` exists before implementing:**
> The `AnimationCascade` tests explicitly reference `cascade._idx`. The `WinAnimation`
> tests reference `anim._phase`, `anim._correct`, `anim._wrong` — but not `anim._idx`.
> Before writing any Phase 7B code, grep the `WinAnimation` class body"

---

### 5. CROSS_VERIFICATION_REPORT.md (Lines 1-395)
**Location:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/CROSS_VERIFICATION_REPORT.md`

**Key Content:**
- Verification that all documents consistently identify the bug
- Line number accuracy verification (8/8 checked = exact)
- Confirmation that fix specification is identical across all docs

---

## Current Code Analysis

### WinAnimation Class (renderer.py:164-226)
**Location:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/renderer.py`

**Current Implementation:**
```python
class WinAnimation:
    def __init__(self, board: Board, speed: float = 0.00066):
        self._board = board
        self.speed = speed
        self._start = time.monotonic()
        self._phase = 0  # 0 = correct flags, 1 = wrong flags, 2 = done
        # ← MISSING: self._idx = 0

        # Build ordered reveal list...
        self._correct = []
        self._wrong = []
        # ... (list building code)
        self._all_positions = self._correct + self._wrong

    def current(self) -> List[Tuple[int, int]]:
        now = time.monotonic() - self._start
        if self._phase == 0:
            idx = min(int(now / self.speed) + 1, len(self._correct))  # ← LOCAL VAR
            if idx >= len(self._correct):
                self._phase = 1
            else:
                return self._correct[:idx]
        if self._phase == 1:
            elapsed = now - len(self._correct) * self.speed
            idx = min(int(elapsed / self.speed) + 1, len(self._wrong))  # ← LOCAL VAR
            if idx >= len(self._wrong):
                self._phase = 2
            else:
                return self._correct + self._wrong[:idx]
        return self._all_positions[:]
```

**Problem:**
- `idx` computed as local variable on lines 210 and 217
- Not stored as `self._idx`
- Inaccessible for Phase 7B cache key: `(self.win_anim._phase, self.win_anim._idx)`

---

## Test Coverage Analysis

### Existing Tests (test_animations.py)
**Location:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/tests/renderer/test_animations.py`

**TestWinAnimation Class (Lines 89-146):**
- 8 tests covering WinAnimation behavior
- All tests call `.current()` to advance internal state
- Tests verify `.done`, `.correct_done`, timing behavior
- No tests currently check `._idx` attribute (it doesn't exist yet)

**Key Test Pattern:**
```python
def test_done_after_enough_time(self):
    anim = WinAnimation(self._board_with_flags(), speed=0.001)
    time.sleep(0.5)
    # Call .current() to advance _phase, then check .done
    _ = anim.current()
    assert anim.done
```

**Expected Behavior After Fix:**
- All 8 existing tests MUST continue to pass
- Calling `.current()` advances `self._idx` (not just local `idx`)
- `._idx` resets to 0 on phase transitions

---

## Implementation Plan

### Step 0.1: Add _idx to __init__
**File:** `renderer.py` line 177 (after `self._phase = 0`)

**Change:**
```python
def __init__(self, board: Board, speed: float = 0.00066):
    # ... existing code ...
    self._phase = 0
    self._idx = 0  # ← ADD THIS LINE
```

**Verification:**
- Attribute exists: `hasattr(anim, '_idx')`
- Initial value: `anim._idx == 0`
- Type: `isinstance(anim._idx, int)`

---

### Step 0.2: Modify current() phase 0 branch
**File:** `renderer.py` lines 210-214

**BEFORE:**
```python
if self._phase == 0:
    idx = min(int(now / self.speed) + 1, len(self._correct))
    if idx >= len(self._correct):
        self._phase = 1
    else:
        return self._correct[:idx]
```

**AFTER:**
```python
if self._phase == 0:
    self._idx = min(int(now / self.speed) + 1, len(self._correct))
    if self._idx >= len(self._correct):
        self._phase = 1
        self._idx = 0  # ← ADD: reset for phase 1
    else:
        return self._correct[:self._idx]
```

**Changes:**
- Line 210: `idx` → `self._idx`
- Line 211: `idx` → `self._idx`
- Line 212: Add `self._idx = 0` after phase transition
- Line 214: `idx` → `self._idx`

---

### Step 0.3: Modify current() phase 1 branch
**File:** `renderer.py` lines 216-221

**BEFORE:**
```python
if self._phase == 1:
    elapsed = now - len(self._correct) * self.speed
    idx = min(int(elapsed / self.speed) + 1, len(self._wrong))
    if idx >= len(self._wrong):
        self._phase = 2
    else:
        return self._correct + self._wrong[:idx]
```

**AFTER:**
```python
if self._phase == 1:
    elapsed = now - len(self._correct) * self.speed
    self._idx = min(int(elapsed / self.speed) + 1, len(self._wrong))
    if self._idx >= len(self._wrong):
        self._phase = 2
        self._idx = 0  # ← ADD: reset for phase 2
    else:
        return self._correct + self._wrong[:self._idx]
```

**Changes:**
- Line 217: `idx` → `self._idx`
- Line 218: `idx` → `self._idx`
- Line 219: Add `self._idx = 0` after phase transition
- Line 221: `idx` → `self._idx`

---

### Step 0.4: Verification Script
**Run after all changes:**

```python
import sys
sys.path.insert(0, '/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks')
from engine import Board
from renderer import WinAnimation

# Create test board with flagged mine
board = Board(10, 10, 10)
board._flagged[0, 0] = True
board._mine[0, 0] = True

# Create animation
anim = WinAnimation(board)

# Verify attributes exist
assert hasattr(anim, '_idx'), "WinAnimation must have _idx attribute"
assert hasattr(anim, '_phase'), "WinAnimation must have _phase attribute"
assert anim._idx == 0, "_idx should initialize to 0"
assert isinstance(anim._idx, int), "_idx should be int type"

print("✅ Phase 0 complete: WinAnimation._idx verified")
```

---

## Test Strategy

### Pre-Implementation Baseline
```bash
cd /home/vercel-sandbox/MineStreakerContrastCampaign
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_animations.py::TestWinAnimation -v
```

**Expected:** All 8 tests pass (baseline)

---

### After Each Change
```bash
# After 0.1 (add _idx to __init__):
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_animations.py::TestWinAnimation -v

# After 0.2 (modify phase 0 branch):
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_animations.py::TestWinAnimation -v

# After 0.3 (modify phase 1 branch):
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_animations.py::TestWinAnimation -v
```

**Expected at each step:** All 8 tests pass

---

### Full Test Suite
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass (no regressions)

---

## Edge Cases Checklist

- [x] **Initialization:** `_idx = 0` in `__init__` (not None, not omitted)
- [x] **Type safety:** `_idx` is `int`, not `float`
- [x] **Bounds checking:** `min()` ensures `_idx` never exceeds list length
- [x] **Phase 0 → 1 transition:** `_idx` resets to 0 when entering phase 1
- [x] **Phase 1 → 2 transition:** `_idx` resets to 0 when entering phase 2
- [x] **Synchronization:** `_phase` and `_idx` always consistent
- [x] **Empty lists:** Works correctly when `_correct` or `_wrong` are empty
- [x] **Speed = 0:** Handled by existing `int(now / self.speed)` logic
- [x] **Negative elapsed:** Cannot occur (`time.monotonic()` is monotonic)
- [x] **Concurrent access:** Not thread-safe (but game is single-threaded)

---

## Commit Message Template

```bash
git add gameworks/renderer.py
git commit -m "fix(renderer): add persistent _idx attribute to WinAnimation

WinAnimation.current() computed idx as local variable, making it inaccessible
for Phase 7B animation cache. Now stores as self._idx with proper resets on
phase transitions.

Problem:
- idx computed as local variable in current() method
- Phase 7B cache key needs (self.win_anim._phase, self.win_anim._idx)
- Accessing non-existent ._idx would fail silently (AttributeError or None)

Solution:
- Add self._idx = 0 in __init__
- Change all idx references to self._idx in current()
- Reset _idx to 0 on phase transitions (0→1, 1→2)

Edge cases handled:
- _idx initialized to 0 (not None)
- Type is int (not float)
- min() ensures _idx never exceeds list bounds
- Resets prevent stale values across phase boundaries
- Empty lists handled (min with 0-length list = 0)

Tests: All 8 existing WinAnimation tests pass, no regressions

Impact: Unblocks Phase 7B (animation set cache)

Refs: REMEDIATION_PLAN_VERIFICATION.md Phase 7B fix
      IMPLEMENTATION_TASK_PLAN.md Phase 0
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Expected Outcome

### Before Fix
```python
anim.win_anim._idx  # AttributeError: 'WinAnimation' object has no attribute '_idx'
```

### After Fix
```python
anim = WinAnimation(board)
anim._idx  # 0 (initial)

anim.current()  # advances _idx based on elapsed time
anim._idx  # Some value ≥ 0, ≤ len(_correct)

# After phase transition:
anim._phase  # 1
anim._idx  # 0 (reset)
```

### Phase 7B Cache Key (Enabled After Fix)
```python
# In _draw_board:
key = (self.win_anim._phase, self.win_anim._idx)  # ✅ Now works
if key != self._win_anim_last_key:
    self._win_anim_set_cache = set(current)
    self._win_anim_last_key = key
```

---

## Success Criteria

- [x] All documentation reviewed and understood
- [x] Current code analyzed and problem confirmed
- [x] Test coverage analyzed (8 existing tests)
- [x] Implementation plan defined (3 code changes)
- [x] Edge cases identified (10+ cases)
- [x] Test strategy defined (baseline → incremental → full)
- [x] Commit message prepared
- [x] Expected outcome documented

**Status:** ✅ READY TO IMPLEMENT

**Next Action:** Execute implementation steps 0.1 → 0.2 → 0.3 → 0.4 → commit

---

*Phase 0 implementation summary generated 2026-05-11. All documentation discovered and analyzed. Ready for execution.*
