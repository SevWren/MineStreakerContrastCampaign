# Gameworks — Implementation Backlog
**Package version:** 0.1.1
**Last updated:** 2026-05-11
**Purpose:** Context-preserving backlog for implementation tasks requiring multi-step work

This file preserves full context for implementation tasks that may span sessions or require LLM context recovery. Each entry is self-contained with problem description, solution details, and document references.

---

## Active Tasks

### PERF-000: WinAnimation._idx Missing Attribute (BLOCKING)

**Priority:** 🚨 CRITICAL — Blocks Phase 7B and all subsequent performance work
**Status:** READY TO IMPLEMENT
**Estimated time:** 30 minutes
**Component:** renderer
**File:** `gameworks/renderer.py`
**Assignee:** TBD
**Created:** 2026-05-11

---

#### Problem Statement

`WinAnimation.current()` computes an animation index as a **local variable** (`idx`) that is never persisted as an instance attribute. This makes the index inaccessible to external code that needs to track animation progress.

**Impact:**
- **Blocks Phase 7B:** Animation set cache requires cache key `(self.win_anim._phase, self.win_anim._idx)`
- Attempting to access `anim._idx` raises `AttributeError`
- Without fix, Phase 7B cache would silently use key `(_phase, None)`, matching every frame and defeating optimization
- Blocks 7 other performance phases that can proceed independently

**Root Cause:**
```python
# renderer.py:206-222 (current implementation)
def current(self) -> List[Tuple[int, int]]:
    now = time.monotonic() - self._start
    if self._phase == 0:
        idx = min(int(now / self.speed) + 1, len(self._correct))  # ← LOCAL VAR
        if idx >= len(self._correct):
            self._phase = 1
        else:
            return self._correct[:idx]
    # ... (phase 1 also uses local idx)
```

**Comparison:** `AnimationCascade` (same file, lines 150-156) correctly stores `self._idx`:
```python
def current(self) -> List[Tuple[int, int]]:
    elapsed = self._clock() - self._start
    self._idx = min(int(elapsed / self.speed) + 1, len(self.positions))  # ← PERSISTED
    return self.positions[:self._idx]
```

---

#### Solution Specification

**3 Changes Required:**

1. **Add attribute to `__init__`** (`renderer.py:177`)
   ```python
   def __init__(self, board: Board, speed: float = 0.00066):
       # ... existing code ...
       self._phase = 0
       self._idx = 0  # ← ADD THIS LINE
   ```

2. **Modify phase 0 branch** (`renderer.py:210-214`)
   ```python
   if self._phase == 0:
       self._idx = min(int(now / self.speed) + 1, len(self._correct))  # ← CHANGE
       if self._idx >= len(self._correct):
           self._phase = 1
           self._idx = 0  # ← ADD: reset for next phase
       else:
           return self._correct[:self._idx]  # ← CHANGE
   ```

3. **Modify phase 1 branch** (`renderer.py:217-221`)
   ```python
   if self._phase == 1:
       elapsed = now - len(self._correct) * self.speed
       self._idx = min(int(elapsed / self.speed) + 1, len(self._wrong))  # ← CHANGE
       if self._idx >= len(self._wrong):
           self._phase = 2
           self._idx = 0  # ← ADD: reset for final phase
       else:
           return self._correct + self._wrong[:self._idx]  # ← CHANGE
   ```

**Key Design Decisions:**
- Reset `_idx` to 0 on phase transitions (prevents stale values)
- Use `min()` to ensure `_idx` never exceeds list bounds
- Type is `int` (not `float`, not `None`)

---

#### Edge Cases Handled

- [x] **Initialization:** `_idx = 0` in `__init__` (not None, not omitted)
- [x] **Type safety:** `_idx` is `int`, not `float`
- [x] **Bounds checking:** `min()` ensures `_idx` never exceeds list length
- [x] **Phase 0 → 1 transition:** `_idx` resets to 0 when entering phase 1
- [x] **Phase 1 → 2 transition:** `_idx` resets to 0 when entering phase 2
- [x] **Synchronization:** `_phase` and `_idx` always consistent
- [x] **Empty lists:** Works correctly when `_correct` or `_wrong` are empty (min with 0-length = 0)
- [x] **Speed = 0:** Handled by existing `int(now / self.speed)` logic (would divide by zero, but not introduced by this change)
- [x] **Negative elapsed:** Cannot occur (`time.monotonic()` is monotonic)
- [x] **Concurrent access:** Not thread-safe, but game is single-threaded (no change in thread safety)

---

#### Test Strategy

**Existing Test Coverage:**
- File: `gameworks/tests/renderer/test_animations.py`
- Class: `TestWinAnimation` (lines 89-146)
- Tests: 8 tests covering WinAnimation behavior
- All tests call `.current()` to advance internal state
- Tests verify `.done`, `.correct_done`, timing behavior

**Validation Steps:**

1. **Pre-implementation baseline:**
   ```bash
   cd /home/vercel-sandbox/MineStreakerContrastCampaign
   SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_animations.py::TestWinAnimation -v
   ```
   **Expected:** All 8 tests pass

2. **After each change (0.1, 0.2, 0.3):**
   ```bash
   SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_animations.py::TestWinAnimation -v
   ```
   **Expected:** All 8 tests continue to pass

3. **Full regression suite:**
   ```bash
   SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
   ```
   **Expected:** ALL tests pass (no regressions)

4. **Manual verification script:**
   ```python
   import sys
   sys.path.insert(0, '/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks')
   from engine import Board
   from renderer import WinAnimation

   board = Board(10, 10, 10)
   board._flagged[0, 0] = True
   board._mine[0, 0] = True
   anim = WinAnimation(board)

   # Verify attributes exist
   assert hasattr(anim, '_idx'), "WinAnimation must have _idx attribute"
   assert hasattr(anim, '_phase'), "WinAnimation must have _phase attribute"
   assert anim._idx == 0, "_idx should initialize to 0"
   assert isinstance(anim._idx, int), "_idx should be int type"

   print("✅ Phase 0 complete: WinAnimation._idx verified")
   ```

**Test Coverage After Fix:**
- No new tests required (behavioral change is internal)
- All existing tests MUST continue to pass
- Manual verification confirms attribute exists and is accessible

---

#### Commit Message Template

```
fix(renderer): add persistent _idx attribute to WinAnimation

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
      BACKLOG.md PERF-000
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

#### Document References

**Primary Documentation:**
1. **IMPLEMENTATION_TASK_PLAN.md** (Lines 35-162)
   - Complete step-by-step implementation guide
   - Exact code snippets for all changes
   - Test commands and validation steps
   - Location: `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/IMPLEMENTATION_TASK_PLAN.md`

2. **PHASE_0_IMPLEMENTATION_SUMMARY.md** (Full file)
   - Consolidated implementation guide
   - All documentation references in one place
   - Current code analysis
   - Test coverage analysis
   - Location: `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/PHASE_0_IMPLEMENTATION_SUMMARY.md`

3. **REMEDIATION_PLAN_VERIFICATION.md** (Lines 93-127)
   - Root cause analysis
   - Fix specification with complete code
   - Estimated fix time: 30 minutes
   - Location: `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/REMEDIATION_PLAN_VERIFICATION.md`

4. **REMEDIATION_PLAN_VERIFICATION_DETAILED.md** (Lines 165-276)
   - Detailed verification that `WinAnimation` lacks `_idx`
   - Comparison with `AnimationCascade` (which has it)
   - Two implementation options (Option A recommended)
   - Warning about why `len(current())` should NOT be used
   - Location: `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/REMEDIATION_PLAN_VERIFICATION_DETAILED.md`

5. **PERFORMANCE_PLAN.md** (Lines 850-924, specifically 906-924)
   - Phase 7B specification (blocked by this fix)
   - Pre-condition warning about verifying `_idx` exists
   - Explanation of why `(_phase, _idx)` key is needed
   - Location: `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/PERFORMANCE_PLAN.md`

6. **CROSS_VERIFICATION_REPORT.md** (Full file)
   - Verification that all documents consistently identify the bug
   - Line number accuracy verification
   - Confirmation that fix specification is identical across docs
   - Location: `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/docs/CROSS_VERIFICATION_REPORT.md`

**Code Locations:**
- **Source:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/renderer.py`
  - `WinAnimation` class: lines 164-226
  - `__init__`: line 171
  - `current()` method: lines 206-222
  - Phase 0 branch: lines 209-214
  - Phase 1 branch: lines 215-221

- **Tests:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks/tests/renderer/test_animations.py`
  - `TestWinAnimation` class: lines 89-146
  - 8 tests total

**Related Issues:**
- Blocks: Phase 7B (Animation Set Cache) in PERFORMANCE_PLAN.md
- Blocks: All 5 gap fixes (N-01, N-02, ZO-06, ZO-07, ZO-13)
- Enables: 7 other performance phases (4A/4B/4C, 5, 6, 7A, 8)

---

#### Expected Outcome

**Before Fix:**
```python
anim = WinAnimation(board)
anim._idx  # AttributeError: 'WinAnimation' object has no attribute '_idx'
```

**After Fix:**
```python
anim = WinAnimation(board)
anim._idx  # 0 (initial value)

anim.current()  # Advances _idx based on elapsed time
anim._idx  # Some value ≥ 0, ≤ len(_correct)

# After phase transition:
anim._phase  # 1
anim._idx  # 0 (reset for phase 1)
```

**Phase 7B Usage (Enabled After Fix):**
```python
# In _draw_board (Phase 7B implementation):
win_anim_set: set = set()
if self.win_anim and not self.win_anim.done:
    current = self.win_anim.current()
    key = (self.win_anim._phase, self.win_anim._idx)  # ✅ Now accessible
    if key != self._win_anim_last_key:
        self._win_anim_set_cache = set(current)
        self._win_anim_last_key = key
    win_anim_set = self._win_anim_set_cache
```

---

#### Performance Impact

**Direct Impact:** None (internal refactoring)
- No performance change from this fix alone
- Behavioral equivalence maintained
- All tests pass without modification

**Indirect Impact:** Unblocks Phase 7B
- **Phase 7B:** Animation set cache reduces `set()` construction from every frame to ~1/tick
- **Tick interval:** ~35ms (animation advances on timer, not per frame)
- **Frame rate:** 30 FPS = 33.3ms/frame → 1-2 frames per tick
- **Reduction:** Rebuild every frame → rebuild every 1-2 frames
- **Estimated savings:** ~50% reduction in animation set construction during animations

**Total Performance Roadmap:**
- **Phase 0 (this fix):** 30 min → Unblocks all phases
- **Phases 4-8:** 4-6 hours → Frame rate <10 FPS → 25-30 FPS
- **Gap fixes (N-01, N-02):** 2-4 hours → 25-30 FPS → 30 FPS (target achieved)

---

#### Implementation Checklist

- [ ] Review all 6 documentation files
- [ ] Run baseline tests (8 WinAnimation tests)
- [ ] Implement change 0.1: Add `self._idx = 0` to `__init__`
- [ ] Run tests after 0.1
- [ ] Implement change 0.2: Modify phase 0 branch
- [ ] Run tests after 0.2
- [ ] Implement change 0.3: Modify phase 1 branch
- [ ] Run tests after 0.3
- [ ] Run full regression suite (all tests)
- [ ] Run manual verification script
- [ ] Verify `_idx` attribute exists and is accessible
- [ ] Commit with template message
- [ ] Push to `frontend-game-mockup` branch
- [ ] Mark PERF-000 as RESOLVED in BACKLOG.md
- [ ] Proceed to Phase 4A (next unblocked phase)

---

#### Success Criteria

- [x] Problem clearly documented with code references
- [x] Solution specified with exact code changes
- [x] Edge cases identified and handled (10+ cases)
- [x] Test strategy defined (baseline → incremental → full)
- [x] All 6 documentation files referenced
- [x] Commit message template provided
- [x] Expected outcome documented (before/after)
- [x] Performance impact quantified
- [x] Implementation checklist created

**Status:** ✅ CONTEXT-COMPLETE — All information needed for implementation without LLM context

---

## Completed Tasks

*(Tasks moved here after resolution, with completion date and commit hash)*

---

## Future Tasks

*(Placeholder for Phase 4A and subsequent phases after PERF-000 is resolved)*

---

*Backlog format inspired by industry-standard issue trackers. Each entry is designed to be self-contained and actionable without requiring external context or LLM memory.*
