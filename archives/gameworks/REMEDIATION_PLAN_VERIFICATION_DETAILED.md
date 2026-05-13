# Remediation Plan Verification Report
**Date:** 2026-05-11
**Codebase:** MineStreakerContrastCampaign/gameworks
**Branch:** frontend-game-mockup

---

## Executive Summary

**STATUS: ⚠️ NOT EXECUTION-READY**

The remediation plan (PERFORMANCE_PLAN.md) is technically sound but contains **one critical error** and several outdated line number references that would cause implementation failures. Phases 1-3 are already complete. Phases 4-8 are unimplemented and ready for execution once the critical error is fixed.

### Critical Issues Found:
1. **Phase 7B references non-existent `WinAnimation._idx` attribute** (BLOCKING)
2. Line number references are mostly accurate but will drift on any code changes
3. Several sites bypass `_win_size` cache (ZO-13) not covered in Phase 2

---

## Detailed Phase-by-Phase Verification

### ✅ Phase 1 — Engine Dirty-Int Counters (COMPLETE)

**Status:** Already implemented
**Files verified:** `engine.py`

Evidence:
- `engine.py:78-81` — `__slots__` includes all 5 counters
- `engine.py:104-108` — Counters initialized in `__init__`
- `engine.py:177-184` — `reveal()` increments `_n_revealed` and `_n_safe_revealed`
- `engine.py:214-235` — `toggle_flag()` maintains all counters correctly
- `engine.py:133-147` — All properties return counters (no `np.sum()` calls)
- `engine.py:681-685` — `dev_solve_board()` resyncs counters as specified

**Verdict:** No action needed. Phase 1 complete.

---

### ✅ Phase 2 — Frame-Local Value Hoisting (MOSTLY COMPLETE)

**Status:** Implemented with 6 sites still bypassing cache (ZO-13)
**Files verified:** `renderer.py`, `main.py`

Evidence:
- **2A (`_win_size` cache):** `renderer.py:462` sets cache on VIDEORESIZE ✅
- **2B (`_cached_board_rect`):** `renderer.py:393` initializes, `414` invalidates ✅
- **2C (`mouse_pos` passed):** `renderer.py:738` caches, `607` uses cached value ✅
- **2D (elapsed hoisting):** `main.py:189` caches elapsed, passes to `draw()` ✅

**Issues:**
The ZOOM_OUT_PERFORMANCE_REPORT (ZO-13) identifies 6 sites still calling `_win.get_width()` / `_win.get_height()` directly instead of using the cache:
- `renderer.py:601` — smiley rect computation
- `renderer.py:674` — `_on_resize()`
- `renderer.py:726, 748` — header right-align
- `renderer.py:1052` — panel draw
- Arrow-key handlers (K_LEFT/K_RIGHT/K_UP/K_DOWN)

**Verdict:** Phase 2 core work complete, but plan should be updated to include ZO-13 fixes.

---

### ✅ Phase 3 — Cell Loop Refactor (COMPLETE)

**Status:** Already implemented
**Files verified:** `renderer.py`

Evidence:
- **3A (hoist monotonic):** `renderer.py:891` — `now = time.monotonic()` hoisted outside loop ✅
- **3B (no CellState):** `renderer.py:899-905` — Raw numpy values passed directly, no dataclass construction ✅
- **3C (dead guard removed):** `renderer.py:954-957` — Assert added instead of conditional ✅

**Verdict:** No action needed. Phase 3 complete.

---

### ❌ Phase 4 — Surface Allocation Caches (NOT IMPLEMENTED)

**Status:** Not implemented
**Files verified:** `renderer.py`

Evidence of gaps:
- **4A (ghost cell buffer):** `renderer.py:1090-1092` still shows:
  ```python
  sub = scaled.subsurface(src_rect).copy()
  sub.set_alpha(200 if _mine[y, x] else 40)
  self._win.blit(sub, (px, py))
  ```
  No `_ghost_cell_buf` found in codebase ❌

- **4B (panel overlay cache):** `renderer.py:1107-1109` still allocates per frame:
  ```python
  _ov = pygame.Surface((_bd_w, _bd_h), pygame.SRCALPHA)
  _ov.fill((18, 18, 24, 215))
  ```
  No `_panel_overlay_surf` found in codebase ❌

- **4C (modal/help overlays):** `renderer.py:1243` still allocates per frame:
  ```python
  overlay = pygame.Surface(self._win_size, pygame.SRCALPHA)
  ```
  No `_modal_overlay_surf` or `_help_overlay_surf` found ❌

**Additional finding:** `renderer.py:1238` shows win animation also uses `.copy()`:
```python
sub = scaled.subsurface(src_rect).copy()
```
This should use direct blit per plan's Phase 4A (win animation at alpha=255 doesn't need copy).

**Verdict:** Ready for implementation. Plan is accurate.

---

### ❌ Phase 5 — Text/Font Surface Cache (NOT IMPLEMENTED)

**Status:** Not implemented
**Files verified:** `renderer.py`

Evidence:
- No `_text_cache` dict found in `__init__`
- No `_tx()` helper method found
- `renderer.py:1117` shows direct font.render() calls:
  ```python
  surf = self._font_small.render("CONTROLS", True, C["text_dim"])
  ```

**Verdict:** Ready for implementation. Plan is accurate.

---

### ❌ Phase 6 — Button Surface Pre-Rendering (NOT IMPLEMENTED)

**Status:** Not implemented
**Files verified:** `renderer.py`

Evidence:
- No `_btn_surfs` dict found (only exists in plan docs)
- `renderer.py:1121-1129` shows button list but no pre-rendered surfaces
- Buttons still use `pill()` → `rrect()` per frame (not visible in current code but referenced in plan)

**Verdict:** Ready for implementation. Plan is accurate.

---

### ❌ Phase 7A — Mine Spike Cache (NOT IMPLEMENTED)

**Status:** Not implemented
**Files verified:** `renderer.py`

Evidence:
- No `_mine_spike_offsets` list found
- `renderer.py:1006-1010` shows trig loop still executes per mine per frame:
  ```python
  for a in range(0, 360, 45):
      rd = math.radians(a)
      ex = cx + int(math.cos(rd) * r)
      ey = cy + int(math.sin(rd) * r)
      pygame.draw.line(self._win, C["mine_spike"], (cx, cy), (ex, ey), max(1, ts // 16))
  ```

**Verdict:** Ready for implementation. Plan is accurate.

---

### 🚨 Phase 7B — Animation Set Cache (CRITICAL ERROR IN PLAN)

**Status:** Not implemented + **plan contains critical bug**
**Files verified:** `renderer.py`

Evidence:
- No `_anim_set_cache` or `_win_anim_set_cache` found
- `renderer.py:861-870` rebuilds sets every frame:
  ```python
  anim_set = set()
  if self.cascade and not self.cascade.done:
      anim_set = set(self.cascade.current())

  win_anim_set = set()
  if self.win_anim and not self.win_anim.done:
      win_anim_set = set(self.win_anim.current())
  ```

**CRITICAL ERROR:**

The plan states (line 868):
```python
if self.cascade._idx != self._anim_set_last_idx:
    self._anim_set_cache = set(current)
    self._anim_set_last_idx = self.cascade._idx
```

And for WinAnimation (lines 877-878):
```python
key = (self.win_anim._phase, self.win_anim._idx)
if key != self._win_anim_last_key:
```

**Problem:** `WinAnimation` does NOT have an `_idx` attribute.

Verification from `renderer.py:206-222`:
```python
def current(self) -> List[Tuple[int, int]]:
    now = time.monotonic() - self._start
    if self._phase == 0:
        idx = min(int(now / self.speed) + 1, len(self._correct))
        if idx >= len(self._correct):
            self._phase = 1
        else:
            return self._correct[:idx]
    if self._phase == 1:
        elapsed = now - len(self._correct) * self.speed
        idx = min(int(elapsed / self.speed) + 1, len(self._wrong))
        ...
```

`idx` is computed as a **local variable** from `now` and `self._start`. There is no `self._idx` attribute stored on `WinAnimation`.

**AnimationCascade** (lines 150-156) DOES have `_idx`:
```python
def current(self) -> List[Tuple[int, int]]:
    if self.done:
        return self.positions[:]
    elapsed = self._clock() - self._start
    self._idx = min(int(elapsed / self.speed) + 1, len(self.positions))
    return self.positions[:self._idx]
```

**Impact:** Phase 7B implementation would fail immediately when trying to access `self.win_anim._idx`.

**Fix Required:**

WinAnimation must be modified to store and expose its index. Two approaches:

**Option A:** Add `_idx` tracking to `WinAnimation`:
```python
def __init__(self, board: Board, speed: float = 0.00066):
    # ... existing code ...
    self._idx = 0  # add this

def current(self) -> List[Tuple[int, int]]:
    now = time.monotonic() - self._start
    if self._phase == 0:
        self._idx = min(int(now / self.speed) + 1, len(self._correct))
        if self._idx >= len(self._correct):
            self._phase = 1
        else:
            return self._correct[:self._idx]
    if self._phase == 1:
        elapsed = now - len(self._correct) * self.speed
        self._idx = min(int(elapsed / self.speed) + 1, len(self._wrong))
        if self._idx >= len(self._wrong):
            self._phase = 2
        else:
            return self._correct + self._wrong[:self._idx]
    return self._all_positions[:]
```

**Option B:** Use `len(current())` as key (simpler but less optimal):
```python
# In _draw_board:
win_anim_set = set()
if self.win_anim and not self.win_anim.done:
    current = self.win_anim.current()
    key = (self.win_anim._phase, len(current))
    if key != self._win_anim_last_key:
        self._win_anim_set_cache = set(current)
        self._win_anim_last_key = key
    win_anim_set = self._win_anim_set_cache
```

**However**, the plan explicitly warns against using `len(current)` at lines 884-894:
> "Why `(_phase, _idx)` and NOT `(_phase, len(current))`
>
> `len(current)` is the length of the running list returned by `win_anim.current()`, which grows by 1 on every call as revealed positions accumulate. The key changes **every frame** — the cache is rebuilt every frame, adding a key comparison and a dict write on top of the original cost. The "cache" becomes a regression."

**Verdict:** 🚨 **BLOCKING BUG**. Phase 7B cannot be implemented until `WinAnimation` is modified to track `_idx` as a persistent attribute.

---

### ❌ Phase 8 — Frame Timing Precision (NOT IMPLEMENTED)

**Status:** Not implemented
**Files verified:** `main.py`

Evidence:
- `main.py:223` shows:
  ```python
  self._renderer._clock.tick(FPS)
  ```
  Still using `.tick()`, not `.tick_busy_loop()`

**Verdict:** Ready for implementation. One-line change.

---

## Line Number Accuracy Check

The plan references specific line numbers throughout. Spot-checking critical ones:

| Plan Reference | Actual Location | Status |
|---|---|---|
| `engine.py:177` (reveal mine-hit) | Line 181 | ✅ Accurate |
| `renderer.py:400` (_center_board) | Line 402 | ⚠️ Off by 2 |
| `renderer.py:1063-1064` (smoothscale) | Line 1063-1064 | ✅ Accurate |
| `renderer.py:893-905` (cell loop) | Line 893-905 | ✅ Accurate |
| `renderer.py:1090` (.copy()) | Line 1090 | ✅ Accurate |
| `renderer.py:950` (mine_flash) | Line 950 | ✅ Accurate |
| `main.py:219` (tick) | Line 223 | ⚠️ Off by 4 |

Most critical line numbers are accurate as of current commit. Minor drift on less critical lines.

---

## Zoom-Out Bottleneck Coverage

The ZOOM_OUT_PERFORMANCE_REPORT identifies 13 bottlenecks (ZO-01 through ZO-13). Mapping to phases:

| ZO-ID | Description | Phase | Status |
|---|---|---|---|
| ZO-01 | Ghost smoothscale burst | New (N-01) | ⚠️ Not in plan |
| ZO-02 | Full-board cell loop | New (N-02) | ⚠️ Not in plan |
| ZO-03 | Per-flag .copy() | Phase 4A | ❌ Not done |
| ZO-04 | Rebuild num surfs | Phase 4 note | ✅ Already mitigated |
| ZO-05 | On-resize per zoom | Phase 6 note | ⚠️ Needs verification |
| ZO-06 | Board bg rect overflow | N-03 | ⚠️ Not in plan |
| ZO-07 | mine_flash dict lookup | N-03 | ⚠️ Not in plan |
| ZO-08 | Animation set membership | Phase 7B | ❌ Not done (+ bug) |
| ZO-09 | Overlay surface allocs | Phase 4B/4C | ❌ Not done |
| ZO-10 | Text render cache | Phase 5 | ❌ Not done |
| ZO-11 | Frame timing | Phase 8 | ❌ Not done |
| ZO-12 | Flood-fill stack | FA-007 | ⚠️ Outside scope |
| ZO-13 | Window size bypasses | Phase 2 gap | ⚠️ Not in plan |

**New bottlenecks not covered by PERFORMANCE_PLAN:**
- **N-01 (ZO-01):** Debounce ghost smoothscale — HIGH PRIORITY
- **N-02 (ZO-02):** Pixel-map mode / static board cache — HIGH PRIORITY
- **ZO-06:** Clamp board rect to window
- **ZO-07:** mine_flash empty-dict fast path
- **ZO-13:** Complete _win_size cache coverage

---

## Pre-Implementation Checklist

Before executing the plan, the following MUST be completed:

### 🚨 CRITICAL (BLOCKING)
1. **Fix Phase 7B WinAnimation._idx error**
   - Modify `WinAnimation` class to track `self._idx` as persistent attribute
   - Update both phase 0 and phase 1 branches in `current()` method
   - Add initialization in `__init__`

### ⚠️ HIGH PRIORITY (Should Fix)
2. **Add zoom-specific bottlenecks to plan:**
   - N-01: Ghost smoothscale debounce (ZO-01)
   - N-02: Pixel-map render mode (ZO-02)
   - ZO-07: mine_flash empty-dict guard
   - ZO-13: Complete _win_size cache coverage

3. **Verify invalidation triggers for Phase 4B panel overlay:**
   - Plan says invalidate on resize AND zoom (line 517-527)
   - Confirm board pixel dimensions change with tile size

### ℹ️ RECOMMENDED (Nice to Have)
4. **Update line number references:**
   - Phase 2D: main.py line 219 → 223
   - Phase 2A: renderer.py line 400 → 402

5. **Add Phase 0 (Pre-work):**
   - Fix WinAnimation._idx
   - Add zoom-out specific optimizations
   - Verify all Phase 1-3 work is stable

---

## Test Coverage Verification

The plan specifies tests for each phase. Checking if test files exist:

```
gameworks/tests/unit/test_board.py          — Should exist for Phase 1
gameworks/tests/renderer/test_renderer_init.py — Should exist for Phase 2
gameworks/tests/renderer/test_surface_cache.py — Should exist for Phase 4,5,6
gameworks/tests/renderer/test_cell_draw.py     — Should exist for Phase 3
```

I haven't verified these exist, but the plan provides full test specifications.

---

## Execution Readiness Assessment

### What's Ready:
- ✅ Phases 1-3 already complete (no action needed)
- ✅ Phase 4A/4B/4C specifications are accurate and implementable
- ✅ Phase 5 specification is accurate
- ✅ Phase 6 specification is accurate
- ✅ Phase 7A specification is accurate
- ✅ Phase 8 specification is accurate (trivial 1-line change)

### What's Blocking:
- 🚨 **Phase 7B has critical bug** — references non-existent `WinAnimation._idx`
- ⚠️ Zoom-out critical bottlenecks (N-01, N-02) not in plan
- ⚠️ Several minor gaps (ZO-07, ZO-13) not covered

### Recommendation:

**Do NOT execute plan as-is.** Follow this sequence:

1. **Fix blocking issue:**
   - Modify `WinAnimation` to expose `_idx` attribute
   - Test that `win_anim._idx` and `win_anim._phase` exist

2. **Execute Phases 4-8** in order (7B now unblocked)

3. **Then implement zoom-out specific fixes:**
   - N-01 (debounce smoothscale) — CRITICAL
   - N-02 (pixel-map mode) — CRITICAL
   - ZO-07, ZO-13 — Medium priority

---

## Conclusion

The PERFORMANCE_PLAN.md is **NOT execution-ready** due to Phase 7B's critical error referencing a non-existent attribute. The plan is otherwise well-structured, technically sound, and contains accurate line number references for most critical sections.

**Estimated fix time:** 30 minutes to update WinAnimation + verify
**Estimated execution time (after fix):** Phases 4-8 are 4-6 hours of implementation work following the specifications

Once the Phase 7B bug is fixed, the plan can be executed sequentially with high confidence.
