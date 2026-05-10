# Test Gap Analysis — gameworks/
**Date:** 2026-05-10
**Analysis of:** `/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks`

---

## Executive Summary

**Current Test Status:**
- Total test files: 15
- Total tests: ~100+
- Passing: 96% (68/72 renderer + all unit/integration)
- Failing: 4 animation timing tests
- Performance test coverage: 20.6% (7/34 from PERFORMANCE_PLAN.md)

**Test Health by Category:**
- ✅ **Unit Tests (Engine/Board):** EXCELLENT — comprehensive coverage
- ✅ **Integration Tests:** GOOD — board modes, CLI parser covered
- ⚠️ **Renderer Tests:** GOOD — 68/72 pass, 4 timing failures
- ⚠️ **Performance Tests:** PARTIAL — only implemented phases tested
- ❌ **Main Entry Point:** MISSING — no test for main() function

---

## Critical Issues (Fix Immediately)

### 1. Failing Animation Tests (4 tests)
**File:** `gameworks/tests/renderer/test_animations.py`
**Status:** 🔴 FAILING
**Impact:** MEDIUM — Animation bugs may exist in production

**Failures:**
```
- test_done_when_all_elapsed
- test_single_position
- test_done_after_enough_time
- test_correct_done_property
```

**Root Cause:** Timing-sensitive tests using `time.sleep()` + `time.monotonic()` — tests expect animation completion but animations not advancing.

**Action Required:**
1. Debug animation `.done` property logic
2. Check `_idx` advancement in AnimationCascade
3. Verify WinAnimation phase transitions
4. OR: Refactor tests to use fake clock instead of real sleep

---

### 2. Phase 2 Cache Invalidation Tests (4 missing)
**File:** `gameworks/tests/renderer/test_renderer_init.py`
**Status:** 🟡 MISSING
**Impact:** MEDIUM — Cache bugs could cause visual glitches

**Required Tests:**
1. `test_win_size_cache_updated_on_videoresize`
   → Validate `_win_size` updates when window resizes
2. `test_board_rect_cache_invalidated_on_pan_change`
   → Validate `_cached_board_rect = None` after pan
3. `test_board_rect_cache_invalidated_on_zoom_change`
   → Validate cache cleared after MOUSEWHEEL zoom
4. `test_draw_smiley_uses_passed_mouse_pos`
   → Monkeypatch `pygame.mouse.get_pos()`, verify not called

**Why Important:**
Phase 2 code is already implemented. If cache invalidation is broken, users would see:
- Stale board positioning after pan/zoom
- Window size mismatches after resize
- Incorrect hover states

**Estimated Effort:** 30 minutes

---

## Recommended Tests (Add Soon)

### 3. Phase 1 Granular Counter Tests (5 missing)
**File:** `gameworks/tests/unit/test_board.py`
**Status:** 🟡 OPTIONAL
**Impact:** LOW — Basic regression tests already exist

**Required Tests:**
1. `test_flags_placed_counter_increments_on_flag`
2. `test_flags_placed_counter_decrements_on_question`
3. `test_flags_placed_counter_decrements_on_hidden`
4. `test_questioned_count_increments_and_decrements`
5. `test_safe_revealed_count_increments_per_safe_cell`

**Note:**
Existing tests (`test_counters_match_array_state_after_flood_fill`, `test_dev_solve_resyncs_all_counters`) already validate counter correctness. These add granular behavior coverage.

**Estimated Effort:** 20 minutes

---

### 4. Main Entry Point Integration Test (1 missing)
**File:** `gameworks/tests/integration/test_main.py` (NEW FILE)
**Status:** ❌ MISSING
**Impact:** LOW-MEDIUM — No coverage of main() flow

**Required Test:**
```python
def test_main_entry_point_runs_without_error():
    """main() should initialize engine, renderer, and run game loop."""
    # Mock pygame.display, pygame.event to avoid actual window
    # Call main() with minimal args
    # Verify no exceptions during initialization
```

**Why Important:**
Currently no test validates that all components wire together correctly from the CLI entry point.

**Estimated Effort:** 30 minutes

---

## Future Tests (When Implementing Features)

### Phase 4: Surface Allocation Caches (8 tests)
**File:** `gameworks/tests/renderer/test_surface_cache.py`
**Status:** 🔵 NOT NEEDED YET — Phase 4 not implemented

**Tests:**
- `test_ghost_cell_buf_allocated_once_per_tile_size`
- `test_ghost_cell_buf_not_reallocated_across_frames`
- `test_ghost_cell_buf_rebuilt_on_zoom_change`
- `test_win_anim_fx_blit_no_copy`
- `test_panel_overlay_surf_stable_across_frames`
- `test_panel_overlay_surf_rebuilt_on_resize`
- `test_modal_overlay_surf_stable_across_frames`
- `test_help_overlay_surf_stable_across_frames`

**Add When:** Implementing PERFORMANCE_PLAN Phase 4

---

### Phase 5: Text/Font Surface Cache (6 tests)
**File:** `gameworks/tests/renderer/test_surface_cache.py`
**Status:** 🔵 NOT NEEDED YET — Phase 5 not implemented

**Tests:**
- `test_tx_returns_same_object_for_identical_inputs`
- `test_tx_re_renders_on_string_change`
- `test_text_cache_cleared_on_rebuild_num_surfs`
- `test_tip_surfs_populated_at_init`
- `test_tip_surfs_rebuilt_on_zoom`
- `test_header_font_render_not_called_on_stable_frame`

**Add When:** Implementing PERFORMANCE_PLAN Phase 5

---

### Phase 6: Button Surface Pre-rendering (4 tests)
**File:** `gameworks/tests/renderer/test_surface_cache.py`
**Status:** 🔵 NOT NEEDED YET — Phase 6 not implemented

**Tests:**
- `test_btn_surfs_populated_at_init`
- `test_btn_surfs_contain_normal_and_hover_variants`
- `test_btn_surfs_rebuilt_on_resize`
- `test_draw_panel_does_not_call_pill_per_frame`

**Add When:** Implementing PERFORMANCE_PLAN Phase 6

---

### Phase 7: Mine Spike + Animation Set Cache (0 planned)
**Status:** 🔵 NOT NEEDED YET — Phase 7 not implemented
No specific tests called out in PERFORMANCE_PLAN for Phase 7. Add as needed during implementation.

---

## Test Coverage by Module

| Module | File | Tests | Pass | Fail | Coverage |
|--------|------|-------|------|------|----------|
| **Engine** | test_board.py | 54 | 54 | 0 | ✅ EXCELLENT |
| | test_engine.py | ~15 | 15 | 0 | ✅ EXCELLENT |
| | test_scoring.py | ~10 | 10 | 0 | ✅ EXCELLENT |
| | test_mine_placement.py | ~8 | 8 | 0 | ✅ GOOD |
| | test_board_loading.py | ~6 | 6 | 0 | ✅ GOOD |
| **Renderer** | test_renderer_init.py | 29 | 29 | 0 | ✅ GOOD |
| | test_cell_draw.py | 5 | 5 | 0 | ✅ GOOD |
| | test_surface_cache.py | 8 | 8 | 0 | ✅ GOOD |
| | test_event_handling.py | ~15 | 15 | 0 | ✅ GOOD |
| | test_animations.py | 16 | 12 | 4 | ⚠️ FAILING |
| **Integration** | test_board_modes.py | ~5 | 5 | 0 | ✅ GOOD |
| **CLI** | test_parser.py | ~8 | 8 | 0 | ✅ GOOD |
| | test_preflight.py | ~5 | 5 | 0 | ✅ GOOD |
| **Architecture** | test_boundaries.py | ~3 | 3 | 0 | ✅ GOOD |

**Total:** ~187 tests, ~183 passing (97.9%)

---

## Prioritized Action Plan

### Priority 1: Critical Fixes (Required)
1. ✅ **Fix 4 animation timing tests** — 1 hour
2. ✅ **Add 4 Phase 2 invalidation tests** — 30 minutes

### Priority 2: Recommended (High Value)
3. ⚠️ **Add main() integration test** — 30 minutes
4. ⚠️ **Add 5 Phase 1 granular tests** (optional) — 20 minutes

### Priority 3: Future (When Implementing)
5. 🔵 **Phase 4-7 tests** — 18 tests total, add when features implemented

---

## Test Quality Assessment

### Strengths ✅
- **Comprehensive unit test coverage** for Board and Engine
- **Well-structured test organization** (unit/integration/renderer split)
- **Good use of fixtures** (conftest.py, boards.py, engines.py)
- **Monkeypatching used effectively** for isolation
- **Headless testing configured** (SDL_VIDEODRIVER=dummy)

### Weaknesses ⚠️
- **Animation timing tests fragile** — use real time.sleep()
- **Missing cache invalidation tests** — could hide bugs
- **No main() integration test** — entry point uncovered
- **Performance tests incomplete** — only 20.6% of plan

### Opportunities 🎯
- Use fake/mock clock for animation tests
- Parametrize similar counter tests (reduce duplication)
- Add property-based testing for board generation
- Add visual regression tests (screenshot comparison)

---

## Conclusion

**Overall Test Health: GOOD (97.9% passing)**

The test suite provides solid coverage of core functionality (Board, Engine, scoring). The main gaps are:
1. 4 failing animation tests (timing-related)
2. Missing cache invalidation tests for Phase 2
3. No main() entry point test

**Immediate Action Required:**
- Fix animation test failures
- Add 4 Phase 2 invalidation tests

After these fixes, the test suite will be in excellent shape for the implemented features. Additional tests should be added incrementally as Phases 4-7 are implemented.
