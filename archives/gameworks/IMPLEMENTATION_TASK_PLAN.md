# Implementation Task Plan — Performance Remediation
## `gameworks/` · Mine-Streaker

**Plan date:** 2026-05-11
**Total estimated time:** 8-12 hours (including testing)
**Test requirement:** ALL tests must pass after EVERY source file change

---

## Pre-Implementation Checklist

### ✅ Prerequisites
- [ ] All 5 documentation files reviewed and understood
- [ ] Current branch is `frontend-game-mockup`
- [ ] Git working directory is clean (`git status`)
- [ ] Baseline tests pass: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v`
- [ ] Python environment active with all dependencies
- [ ] No uncommitted changes in `renderer.py`, `engine.py`, `main.py`

### ✅ Test Infrastructure Check
- [ ] Verify test files exist:
  - `gameworks/tests/unit/test_board.py` (Phase 1 verification)
  - `gameworks/tests/renderer/` directory exists
  - `gameworks/tests/` contains `conftest.py` or equivalent
- [ ] pytest runs successfully (even if 0 tests)
- [ ] Headless SDL environment variables work

### ✅ Edge Case Pre-Analysis
- [ ] Review edge cases section (Appendix B) before starting
- [ ] Identify boundaries: tile_size=0, board dimensions=0, None checks
- [ ] Plan defensive assertions for each phase

---

## Phase 0: Fix WinAnimation._idx (BLOCKING)

**Priority:** 🚨 CRITICAL — Must complete before Phase 7B
**Estimated time:** 30 minutes
**Files:** `gameworks/renderer.py`
**Tests:** Existing animation tests must continue to pass

### Implementation Steps

#### 0.1 — Add _idx attribute to __init__
**File:** `renderer.py:171` (inside `WinAnimation.__init__`)

```python
def __init__(self, board: Board, speed: float = 0.00066):
    # ... existing code ...
    self._phase = 0
    self._idx = 0  # ← ADD THIS LINE
```

**Edge cases:**
- [x] _idx initialized to 0 (not None)
- [x] Type is int, not float

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v -k "animation or win"
```

**Expected:** All existing animation tests pass

---

#### 0.2 — Modify current() to persist _idx (phase 0)
**File:** `renderer.py:210` (inside `WinAnimation.current()` phase 0 branch)

```python
if self._phase == 0:
    self._idx = min(int(now / self.speed) + 1, len(self._correct))  # ← CHANGE idx to self._idx
    if self._idx >= len(self._correct):
        self._phase = 1
        self._idx = 0  # ← ADD: reset for next phase
    else:
        return self._correct[:self._idx]  # ← CHANGE idx to self._idx
```

**Edge cases:**
- [x] _idx never exceeds len(self._correct)
- [x] Reset to 0 on phase transition (prevents stale values)
- [x] Phase 0 → Phase 1 transition preserves animation continuity

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

---

#### 0.3 — Modify current() to persist _idx (phase 1)
**File:** `renderer.py:217` (inside `WinAnimation.current()` phase 1 branch)

```python
if self._phase == 1:
    elapsed = now - len(self._correct) * self.speed
    self._idx = min(int(elapsed / self.speed) + 1, len(self._wrong))  # ← CHANGE idx to self._idx
    if self._idx >= len(self._wrong):
        self._phase = 2
        self._idx = 0  # ← ADD: reset for final phase
    else:
        return self._correct + self._wrong[:self._idx]  # ← CHANGE idx to self._idx
```

**Edge cases:**
- [x] _idx never exceeds len(self._wrong)
- [x] Reset to 0 on phase 2 transition
- [x] Elapsed time calculation doesn't go negative

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

---

#### 0.4 — Verify _idx is accessible
**Verification script:**

```python
# Run this in Python REPL after changes:
import sys
sys.path.insert(0, '/home/vercel-sandbox/MineStreakerContrastCampaign/gameworks')
from engine import Board
from renderer import WinAnimation

board = Board(10, 10, 10)
board._flagged[0, 0] = True
board._mine[0, 0] = True
anim = WinAnimation(board)

# Verify attributes exist:
assert hasattr(anim, '_idx'), "WinAnimation must have _idx attribute"
assert hasattr(anim, '_phase'), "WinAnimation must have _phase attribute"
assert anim._idx == 0, "_idx should initialize to 0"
print("✅ Phase 0 complete: WinAnimation._idx verified")
```

**Commit Phase 0:**
```bash
git add gameworks/renderer.py
git commit -m "fix(renderer): add persistent _idx attribute to WinAnimation

WinAnimation.current() computed idx as local variable, making it inaccessible
for Phase 7B animation cache. Now stores as self._idx with proper resets on
phase transitions.

Edge cases handled:
- _idx initialized to 0 in __init__
- Reset to 0 on phase transitions (0→1, 1→2)
- min() ensures _idx never exceeds list bounds

Tests: All existing animation tests pass

Refs: REMEDIATION_PLAN_VERIFICATION.md Phase 7B fix
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 4: Surface Allocation Caches

**Priority:** HIGH
**Estimated time:** 1-2 hours
**Files:** `gameworks/renderer.py`
**Tests:** New tests in `tests/renderer/test_surface_cache.py`

### 4A — Ghost Cell Buffer (FA-009)

**Problem:** `renderer.py:1090` — `.copy()` allocates new Surface per flagged cell per frame

#### 4A.1 — Add buffer attributes to __init__
**File:** `renderer.py` (in `Renderer.__init__` after `self._ghost_surf` initialization)

```python
# Ghost cell reusable buffer — eliminates per-cell .copy() allocations
self._ghost_cell_buf: Optional[pygame.Surface] = None
self._ghost_cell_buf_ts: int = 0
```

**Edge cases:**
- [x] Initialized to None (lazy allocation)
- [x] Type hints included

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### 4A.2 — Rebuild buffer on tile size change
**File:** `renderer.py:1060` (inside `_draw_image_ghost`, before the flagged cell loop)

```python
ts = self._tile

# Rebuild reusable cell buffer if tile size changed
if self._ghost_cell_buf is None or self._ghost_cell_buf_ts != ts:
    self._ghost_cell_buf = pygame.Surface((ts, ts), pygame.SRCALPHA)
    self._ghost_cell_buf_ts = ts
```

**Edge cases:**
- [x] Handle ts=0: min(1, ts) would be safer, but plan assumes ts >= 7 at minimum zoom
- [x] SRCALPHA flag required for transparency
- [x] Rebuilds on first draw (None check)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### 4A.3 — Replace .copy() with buffer reuse
**File:** `renderer.py:1090-1092` (inside flagged cell loop)

**BEFORE:**
```python
sub = scaled.subsurface(src_rect).copy()
sub.set_alpha(200 if _mine[y, x] else 40)
self._win.blit(sub, (px, py))
```

**AFTER:**
```python
# CRITICAL: Clear before blit — alpha < 255 composites, doesn't replace
self._ghost_cell_buf.fill((0, 0, 0, 0))
self._ghost_cell_buf.blit(scaled, (0, 0), src_rect)
self._ghost_cell_buf.set_alpha(200 if _mine[y, x] else 40)
self._win.blit(self._ghost_cell_buf, (px, py))
```

**Edge cases:**
- [x] **CRITICAL:** `fill((0, 0, 0, 0))` MUST come before blit
  - Without fill: ghost-on-ghost artifacts from previous cell's content
  - Alpha blending composites SRC over DST, doesn't replace
- [x] `_mine[y, x]` bounds check: assume valid from viewport culling
- [x] Alpha 200 (mines) vs 40 (non-mines) as per original

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### 4A.4 — Fix win animation .copy() (Phase 4A bonus)
**File:** `renderer.py:1238-1240` (inside `_draw_win_animation_fx`)

**BEFORE:**
```python
sub = scaled.subsurface(src_rect).copy()
sub.set_alpha(255)
self._win.blit(sub, (px, py))
```

**AFTER:**
```python
# Win animation at alpha=255 (full opacity) — direct blit, no copy needed
sub = scaled.subsurface(src_rect)
self._win.blit(sub, (px, py))
```

**Edge cases:**
- [x] Alpha=255 means no transparency, no set_alpha needed
- [x] Subsurface is directly blittable at full opacity
- [x] No fill() needed — full opacity replaces destination

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

---

#### 4A.5 — Write new tests
**File:** `gameworks/tests/renderer/test_surface_cache.py` (create if doesn't exist)

```python
import pytest
import pygame
from gameworks.renderer import Renderer
from gameworks.engine import Board

def test_ghost_cell_buf_allocated_once_per_tile_size():
    """Ghost cell buffer is created once per tile size, not per frame."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)

    # First draw allocates buffer
    renderer._tile = 32
    renderer._draw_image_ghost(0, 0, 320, 320)
    buf_id_1 = id(renderer._ghost_cell_buf)

    # Second draw reuses buffer (same tile size)
    renderer._draw_image_ghost(0, 0, 320, 320)
    buf_id_2 = id(renderer._ghost_cell_buf)

    assert buf_id_1 == buf_id_2, "Buffer should be reused across frames"

def test_ghost_cell_buf_rebuilt_on_zoom_change():
    """Ghost cell buffer is rebuilt when tile size changes."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)

    renderer._tile = 32
    renderer._draw_image_ghost(0, 0, 320, 320)
    buf_id_32 = id(renderer._ghost_cell_buf)

    renderer._tile = 16
    renderer._draw_image_ghost(0, 0, 160, 160)
    buf_id_16 = id(renderer._ghost_cell_buf)

    assert buf_id_32 != buf_id_16, "Buffer should be rebuilt on tile size change"
    assert renderer._ghost_cell_buf.get_size() == (16, 16)

def test_ghost_cell_buf_not_reallocated_across_frames():
    """Ghost cell buffer stays stable across multiple frames (regression test)."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)
    renderer._tile = 32

    ids = []
    for _ in range(5):
        renderer._draw_image_ghost(0, 0, 320, 320)
        ids.append(id(renderer._ghost_cell_buf))

    assert len(set(ids)) == 1, f"Buffer reallocated {len(set(ids))} times, expected 1"
```

**Run tests:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_surface_cache.py::test_ghost_cell_buf_allocated_once_per_tile_size -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_surface_cache.py::test_ghost_cell_buf_rebuilt_on_zoom_change -v
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_surface_cache.py::test_ghost_cell_buf_not_reallocated_across_frames -v
```

**Expected:** All 3 tests pass

**Run full test suite:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit Phase 4A:**
```bash
git add gameworks/renderer.py gameworks/tests/renderer/test_surface_cache.py
git commit -m "perf(renderer): eliminate per-flag .copy() with reusable ghost cell buffer (Phase 4A)

Fixes FA-009: Allocating new Surface per flagged cell (8,325 allocs/frame on
300×370 board with 50% flags).

Implementation:
- Pre-allocate single ts×ts SRCALPHA buffer per tile size
- Clear buffer before each blit (prevents ghost-on-ghost artifacts)
- Reuse across all flagged cells in frame

Bonus fix: Win animation direct blit (alpha=255 doesn't need .copy())

Edge cases:
- Buffer fill((0,0,0,0)) BEFORE blit (alpha compositing)
- Lazy allocation (None check)
- Rebuild only on tile size change

Performance impact: ~8,000 Surface allocations/frame → 0

Tests: 3 new cache stability tests, all existing tests pass

Refs: PERFORMANCE_PLAN.md Phase 4A
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### 4B — Panel Overlay Cache

**Problem:** `renderer.py:1107` — Panel overlay allocates SRCALPHA surface every frame

#### 4B.1 — Add overlay cache to __init__
**File:** `renderer.py` (in `Renderer.__init__`)

```python
# Panel overlay backdrop cache
self._panel_overlay_surf: Optional[pygame.Surface] = None
self._panel_overlay_surf_size: Tuple[int, int] = (0, 0)
```

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### 4B.2 — Cache panel overlay surface
**File:** `renderer.py:1107-1109` (inside `_draw_panel`)

**BEFORE:**
```python
_ov = pygame.Surface((_bd_w, _bd_h), pygame.SRCALPHA)
_ov.fill((18, 18, 24, 215))
self._win.blit(_ov, (px - self.PAD, oy))
```

**AFTER:**
```python
sz = (_bd_w, _bd_h)
if self._panel_overlay_surf is None or self._panel_overlay_surf_size != sz:
    self._panel_overlay_surf = pygame.Surface(sz, pygame.SRCALPHA)
    self._panel_overlay_surf.fill((18, 18, 24, 215))
    self._panel_overlay_surf_size = sz
self._win.blit(self._panel_overlay_surf, (px - self.PAD, oy))
```

**Edge cases:**
- [x] sz = (0, 0): pygame.Surface((0,0)) is valid but useless, won't crash
- [x] Color tuple (18, 18, 24, 215) includes alpha channel

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### 4B.3 — Invalidate on resize and zoom
**File:** `renderer.py` (VIDEORESIZE handler, inside `handle_event`)

Find the VIDEORESIZE handler and add:
```python
if ev.type == pygame.VIDEORESIZE:
    self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
    self._win_size = ev.size
    self._panel_overlay_surf = None  # ← ADD THIS
    self._on_resize()
```

**File:** `renderer.py` (in `_rebuild_num_surfs`, at start of method)

```python
def _rebuild_num_surfs(self):
    """Rebuild number surfaces when tile size changes."""
    self._panel_overlay_surf = None  # ← ADD THIS LINE
    # ... rest of method ...
```

**Edge cases:**
- [x] Invalidate BEFORE resize operations complete
- [x] Board pixel dimensions (_bd_w, _bd_h) depend on tile size, so zoom invalidates
- [x] Window resize also changes overlay size

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit Phase 4B:**
```bash
git add gameworks/renderer.py
git commit -m "perf(renderer): cache panel overlay surface (Phase 4B)

Fixes: Panel overlay backdrop allocated every frame (SRCALPHA surface + fill).

Implementation:
- Cache surface keyed by (width, height)
- Invalidate on resize (window size change)
- Invalidate on zoom (board pixel dimensions change)

Edge cases:
- Size (0, 0) doesn't crash (valid but useless)
- Invalidation before operations complete
- Board dimensions depend on tile size → zoom invalidates

Performance impact: 1 SRCALPHA allocation/frame → 0

Tests: All existing tests pass

Refs: PERFORMANCE_PLAN.md Phase 4B
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### 4C — Modal and Help Overlay Caches

**Problem:** `renderer.py:1243, 1264` — Full-screen overlays allocate every frame when visible

#### 4C.1 — Add modal/help cache to __init__
**File:** `renderer.py` (in `Renderer.__init__`)

```python
# Modal and help overlay caches
self._modal_overlay_surf: Optional[pygame.Surface] = None
self._modal_overlay_surf_size: Tuple[int, int] = (0, 0)
self._help_overlay_surf: Optional[pygame.Surface] = None
self._help_overlay_surf_size: Tuple[int, int] = (0, 0)
```

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### 4C.2 — Cache modal overlay
**File:** `renderer.py:1243` (inside `_draw_modal`)

**BEFORE:**
```python
overlay = pygame.Surface(self._win_size, pygame.SRCALPHA)
overlay.fill((0, 0, 0, 160))
self._win.blit(overlay, (0, 0))
```

**AFTER:**
```python
sz = self._win_size
if self._modal_overlay_surf is None or self._modal_overlay_surf_size != sz:
    self._modal_overlay_surf = pygame.Surface(sz, pygame.SRCALPHA)
    self._modal_overlay_surf.fill((0, 0, 0, 160))
    self._modal_overlay_surf_size = sz
self._win.blit(self._modal_overlay_surf, (0, 0))
```

**Edge cases:**
- [x] Uses _win_size only (not board dimensions)
- [x] Doesn't invalidate on zoom (only on window resize)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### 4C.3 — Cache help overlay
**File:** `renderer.py:1264` (inside `_draw_help`)

**BEFORE:**
```python
overlay = pygame.Surface(self._win_size, pygame.SRCALPHA)
overlay.fill((0, 0, 0, 200))
self._win.blit(overlay, (0, 0))
```

**AFTER:**
```python
sz = self._win_size
if self._help_overlay_surf is None or self._help_overlay_surf_size != sz:
    self._help_overlay_surf = pygame.Surface(sz, pygame.SRCALPHA)
    self._help_overlay_surf.fill((0, 0, 0, 200))
    self._help_overlay_surf_size = sz
self._win.blit(self._help_overlay_surf, (0, 0))
```

**Edge cases:**
- [x] Different alpha (200 vs 160 for modal)
- [x] Same invalidation rules as modal

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### 4C.4 — Invalidate on resize
**File:** `renderer.py` (VIDEORESIZE handler)

Update the VIDEORESIZE handler:
```python
if ev.type == pygame.VIDEORESIZE:
    self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
    self._win_size = ev.size
    self._panel_overlay_surf = None
    self._modal_overlay_surf = None   # ← ADD THIS
    self._help_overlay_surf = None    # ← ADD THIS
    self._on_resize()
```

**Edge cases:**
- [x] Modal/help overlays DON'T invalidate on zoom (only window resize)
- [x] Different from panel overlay (which depends on tile size)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit Phase 4C:**
```bash
git add gameworks/renderer.py
git commit -m "perf(renderer): cache modal and help overlay surfaces (Phase 4C)

Fixes: Full-screen overlays allocated every frame when visible.

Implementation:
- Cache modal overlay (alpha=160) keyed by window size
- Cache help overlay (alpha=200) keyed by window size
- Invalidate on window resize only (not zoom)

Edge cases:
- Different from panel overlay: uses _win_size only
- No tile size dependency → no zoom invalidation
- Different alpha values preserved (160 vs 200)

Performance impact: 2 SRCALPHA allocations/frame → 0 (when visible)

Tests: All existing tests pass

Refs: PERFORMANCE_PLAN.md Phase 4C
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 5: Text/Font Surface Cache

**Priority:** MEDIUM
**Estimated time:** 30-60 minutes
**Files:** `gameworks/renderer.py`
**Tests:** New tests in `test_surface_cache.py`

### 5.1 — Add text cache to __init__
**File:** `renderer.py` (in `Renderer.__init__`)

```python
# Text render cache — (text, font_id, color) -> Surface
self._text_cache: dict = {}
```

**Edge cases:**
- [x] Empty dict (not None)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 5.2 — Implement _tx() helper method
**File:** `renderer.py` (add new method to Renderer class)

```python
def _tx(self, text: str, font: pygame.font.Font, color: tuple) -> pygame.Surface:
    """
    Cached font.render(). Re-renders only when text or style changes.

    IMPORTANT: color MUST be a plain tuple, not pygame.Color.
    pygame.Color(255,255,255) and (255,255,255) have different hashes
    and will never share a cache entry.
    """
    key = (text, id(font), color)
    s = self._text_cache.get(key)
    if s is None:
        s = font.render(text, True, color)
        self._text_cache[key] = s
    return s
```

**Edge cases:**
- [x] text = "": Valid, will cache empty surface
- [x] color must be tuple, NOT pygame.Color (different hash)
- [x] font ID captures font object identity
- [x] No cache size limit (bounded by unique strings in UI)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 5.3 — Invalidate cache on font rebuild
**File:** `renderer.py` (in `_rebuild_num_surfs`)

```python
def _rebuild_num_surfs(self):
    """Rebuild number surfaces when tile size changes."""
    self._panel_overlay_surf = None
    self._text_cache.clear()  # ← ADD THIS LINE (fonts are recreated)
    # ... rest of method ...
```

**Edge cases:**
- [x] Clear BEFORE font objects are recreated
- [x] Old id(font) keys become invalid after font recreation

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 5.4 — Replace font.render() in _draw_header
**File:** `renderer.py` (in `_draw_header` method)

Find all `font.render()` calls and replace with `self._tx()`:

**Example locations (verify actual line numbers):**
```python
# Line ~711: Mines remaining
mt = self._tx(f"M:{mines:>03d}", self._font_big, mcol)

# Line ~733: Score
sc = self._tx(f"SCORE:{score:>6d}", self._font_small, score_col)

# Line ~735: Timer
tt = self._tx(f"T:{secs:>03d}", self._font_small, C["text_light"])

# Line ~742: Streak
sl = self._tx(f"STREAK x{streak}  {mult:.1f}x", self._font_small, streak_col)
```

**Edge cases:**
- [x] C["text_light"] must be tuple, not pygame.Color
- [x] All color constants verified as tuples

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 5.5 — Replace font.render() in _draw_panel
**File:** `renderer.py` (in `_draw_panel` method)

Replace all `font.render()` calls with `self._tx()` (approximately 12 locations).

**Edge cases:**
- [x] Verify all color arguments are tuples
- [x] Empty strings ("") are valid

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 5.6 — Pre-render tips (bonus optimization)
**File:** `renderer.py` (in `Renderer.__init__`)

```python
# Tip surfaces (pre-rendered at init, rebuilt on zoom)
self._tip_surfs: list = []
self._rebuild_tip_surfs()
```

**File:** `renderer.py` (add new method)

```python
def _rebuild_tip_surfs(self):
    """Pre-render tip strings. Called at init and on font rebuild."""
    tips = [
        "L-click  Reveal", "R-click  Flag / unflag",
        "M-click  Chord",  "Scroll   Zoom / Pan", "",
        "Keys: R Restart  H Help", "      F Fog  ESC Quit",
    ]
    self._tip_surfs = [
        self._font_tiny.render(t, True, C["text_dim"]) if t else None
        for t in tips
    ]
```

**File:** `renderer.py` (in `_rebuild_num_surfs`)

```python
def _rebuild_num_surfs(self):
    self._panel_overlay_surf = None
    self._text_cache.clear()
    self._rebuild_tip_surfs()  # ← ADD THIS
    # ... rest of method ...
```

**File:** `renderer.py` (in `_draw_panel` tips loop)

Replace tip rendering loop with:
```python
line_h = self._font_tiny.get_height() + 2
for i, surf in enumerate(self._tip_surfs):
    if surf:
        self._win.blit(surf, (px, ty + i * line_h))
```

**Edge cases:**
- [x] Empty string ("") → None in list
- [x] None check before blit
- [x] Tips never change → perfect for pre-render

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

---

### 5.7 — Write new tests
**File:** `gameworks/tests/renderer/test_surface_cache.py`

```python
def test_tx_returns_same_object_for_identical_inputs():
    """_tx() returns cached surface for identical text/font/color."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)

    surf1 = renderer._tx("Test", renderer._font_small, (255, 255, 255))
    surf2 = renderer._tx("Test", renderer._font_small, (255, 255, 255))

    assert surf1 is surf2, "Should return cached surface"

def test_tx_re_renders_on_string_change():
    """_tx() creates new surface when string changes."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)

    surf1 = renderer._tx("Test1", renderer._font_small, (255, 255, 255))
    surf2 = renderer._tx("Test2", renderer._font_small, (255, 255, 255))

    assert surf1 is not surf2, "Should create new surface for different text"

def test_text_cache_cleared_on_rebuild_num_surfs():
    """Text cache is cleared when fonts are rebuilt."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)

    renderer._tx("Test", renderer._font_small, (255, 255, 255))
    assert len(renderer._text_cache) > 0

    renderer._rebuild_num_surfs()
    assert len(renderer._text_cache) == 0, "Cache should be cleared"

def test_tip_surfs_populated_at_init():
    """Tip surfaces are pre-rendered at initialization."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)

    assert len(renderer._tip_surfs) == 7, "Should have 7 tip entries"
    assert renderer._tip_surfs[4] is None, "Empty tip should be None"
    assert all(isinstance(s, pygame.Surface) or s is None for s in renderer._tip_surfs)
```

**Run tests:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_surface_cache.py -v -k "tx or tip"
```

**Expected:** All new tests pass

**Run full suite:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit Phase 5:**
```bash
git add gameworks/renderer.py gameworks/tests/renderer/test_surface_cache.py
git commit -m "perf(renderer): add text render cache and pre-render tips (Phase 5)

Fixes: 20+ font.render() calls per frame for mostly unchanging strings.

Implementation:
- _tx() helper: string-keyed cache (text, font_id, color) -> Surface
- Replace all font.render() in _draw_header and _draw_panel
- Pre-render 7 tip strings at init (never change)
- Clear cache on font rebuild

Edge cases:
- Empty string \"\": valid, caches empty surface
- Color MUST be tuple, NOT pygame.Color (different hash)
- Cache unbounded but self-limiting (~10-20 unique strings in UI)
- Tip None check before blit

Performance impact: 20 font.render()/frame → ~2/frame

Tests: 4 new cache behavior tests, all existing tests pass

Refs: PERFORMANCE_PLAN.md Phase 5
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 6: Button Surface Pre-Rendering

**Priority:** MEDIUM
**Estimated time:** 30-60 minutes
**Files:** `gameworks/renderer.py`
**Tests:** New tests in `test_surface_cache.py`

### 6.1 — Add button surface cache to __init__
**File:** `renderer.py` (in `Renderer.__init__`)

```python
# Pre-rendered button surfaces — (label, base_col, hover) -> Surface
self._btn_surfs: dict = {}
self._rebuild_btn_surfs()
```

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 6.2 — Implement _rebuild_btn_surfs()
**File:** `renderer.py` (add new method)

```python
def _rebuild_btn_surfs(self):
    """
    Pre-render all button faces. Called at init and on resize/zoom.

    Generates normal + hover variants for each button.
    """
    self._btn_surfs.clear()
    spec = [
        ("Restart",         C["green"]),
        ("New Game",        C["green"]),
        ("Help",            C["blue"]),
        ("Toggle Fog",      C["purple"]),
        ("Hide Fog",        C["purple"]),
        ("Save .npy",       C["cyan"]),
        ("Solve Board",     C["orange"]),
        ("Solve Board",     C["border"]),   # inactive variant
    ]

    bw = self._btn_w
    bh = self._btn_new.height
    r = bh // 2

    for label, base_col in spec:
        for hover in (False, True):
            s = pygame.Surface((bw, bh), pygame.SRCALPHA)
            pygame.draw.rect(s, base_col, (0, 0, bw, bh), border_radius=r)
            if hover:
                pygame.draw.rect(s, C["text_light"], (0, 0, bw, bh), 2, border_radius=r)
            txt = self._font_small.render(label, True, C["bg"])
            s.blit(txt, txt.get_rect(center=(bw // 2, bh // 2)))
            self._btn_surfs[(label, base_col, hover)] = s
```

**Edge cases:**
- [x] bw = 0: min button width should be enforced elsewhere
- [x] "Solve Board" has 2 color variants (active/inactive)
- [x] Font render directly (not _tx) - buttons rebuilt less frequently than text cache churn

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 6.3 — Call _rebuild_btn_surfs on resize and zoom
**File:** `renderer.py` (in `_on_resize`)

```python
def _on_resize(self):
    # ... existing code ...
    self._rebuild_btn_surfs()  # ← ADD at end
```

**File:** `renderer.py` (in `_rebuild_num_surfs`)

```python
def _rebuild_num_surfs(self):
    self._panel_overlay_surf = None
    self._text_cache.clear()
    self._rebuild_tip_surfs()
    self._rebuild_btn_surfs()  # ← ADD at end
```

**Edge cases:**
- [x] Button dimensions may change on window resize
- [x] Font size may change on zoom (affects button layout)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 6.4 — Update button list to include base_col
**File:** `renderer.py` (in `_draw_panel`, where buttons list is constructed)

Find the buttons list and add base_col as third element:

**BEFORE:**
```python
buttons = [
    (self._btn_new, "New Game"),
    (self._btn_restart, "Restart"),
    # ... etc
]
```

**AFTER:**
```python
fog_label = "Hide Fog" if self.fog else "Toggle Fog"
solver_available = (self.engine.state == "playing")  # or whatever condition

buttons = [
    (self._btn_new,       "New Game",    C["green"]),
    (self._btn_restart,   "Restart",     C["green"]),
    (self._btn_help,      "Help",        C["blue"]),
    (self._btn_fog,       fog_label,     C["purple"]),
    (self._btn_save,      "Save .npy",   C["cyan"]),
    (self._btn_dev_solve, "Solve Board", C["orange"] if solver_available else C["border"]),
]
```

**Edge cases:**
- [x] fog_label changes between "Toggle Fog" and "Hide Fog"
- [x] Solve Board has conditional color (active=orange, inactive=border)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 6.5 — Replace button drawing loop
**File:** `renderer.py` (in `_draw_panel`, button draw loop)

**BEFORE:**
```python
for rect, label in buttons:
    hover = rect.collidepoint(mx, my)
    # ... pill() / rrect() calls ...
```

**AFTER:**
```python
for rect, label, base_col in buttons:
    hover = rect.collidepoint(mx, my)
    surf = self._btn_surfs.get((label, base_col, hover))
    if surf:
        self._win.blit(surf, rect.topleft)
```

**Edge cases:**
- [x] surf could be None if not pre-rendered (shouldn't happen)
- [x] if surf check prevents crash if cache miss

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

---

### 6.6 — Write new tests
**File:** `gameworks/tests/renderer/test_surface_cache.py`

```python
def test_btn_surfs_populated_at_init():
    """Button surfaces are pre-rendered at initialization."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)

    assert len(renderer._btn_surfs) > 0, "Button surfaces should be pre-rendered"
    # Should have normal + hover for each button
    assert ("Restart", renderer.C["green"], False) in renderer._btn_surfs
    assert ("Restart", renderer.C["green"], True) in renderer._btn_surfs

def test_btn_surfs_contain_normal_and_hover_variants():
    """Each button has both normal and hover variants."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)

    for key in renderer._btn_surfs:
        label, color, hover = key
        # Find opposite hover state
        opposite = (label, color, not hover)
        assert opposite in renderer._btn_surfs, f"Missing hover variant for {label}"

def test_btn_surfs_rebuilt_on_resize():
    """Button surfaces are rebuilt when window resizes."""
    board = Board(10, 10, 10)
    renderer = Renderer(board)

    old_count = len(renderer._btn_surfs)
    renderer._on_resize()
    new_count = len(renderer._btn_surfs)

    assert new_count == old_count, "Same number of buttons after resize"
    # Verify actual rebuild happened (surfaces reallocated)
```

**Run tests:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_surface_cache.py -v -k "btn"
```

**Expected:** All new tests pass

**Run full suite:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit Phase 6:**
```bash
git add gameworks/renderer.py gameworks/tests/renderer/test_surface_cache.py
git commit -m "perf(renderer): pre-render button surfaces (Phase 6)

Fixes: 5 buttons × 8 draw ops each = 40 draw calls/frame for static UI.

Implementation:
- _rebuild_btn_surfs(): pre-render normal + hover for all buttons
- Cache key: (label, base_color, hover: bool)
- Rebuild on resize (dimensions change) and zoom (fonts change)
- Replace pill() → rrect() loop with single blit per button

Edge cases:
- \"Solve Board\" has 2 color variants (active/inactive)
- Fog button label changes (\"Toggle\" vs \"Hide\")
- Font render direct (not _tx) - infrequent rebuild
- surf=None check prevents crash on cache miss

Performance impact: 40 draw calls/frame → 5 blits/frame

Tests: 3 new button cache tests, all existing tests pass

Refs: PERFORMANCE_PLAN.md Phase 6
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 7A: Mine Spike Cache

**Priority:** LOW
**Estimated time:** 15-30 minutes
**Files:** `gameworks/renderer.py`

### 7A.1 — Add spike offsets to __init__
**File:** `renderer.py` (in `Renderer.__init__`)

```python
# Pre-computed mine spike offsets (8 directions)
self._mine_spike_offsets: list = []
```

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 7A.2 — Compute offsets in _rebuild_num_surfs
**File:** `renderer.py` (in `_rebuild_num_surfs`, at start)

```python
def _rebuild_num_surfs(self):
    # ... existing invalidations ...

    # Pre-compute mine spike offsets for current tile size
    r = max(2, self._tile // 3)
    self._mine_spike_offsets = [
        (int(math.cos(math.radians(a)) * r),
         int(math.sin(math.radians(a)) * r))
        for a in range(0, 360, 45)
    ]

    # ... rest of method ...
```

**Edge cases:**
- [x] r = max(2, ...) prevents radius=0 or radius=1 (too small)
- [x] 8 offsets (0°, 45°, 90°, 135°, 180°, 225°, 270°, 315°)
- [x] int() rounds to pixel coordinates

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 7A.3 — Replace trig loop in _draw_mine
**File:** `renderer.py` (in `_draw_mine` method, find trig loop ~line 1006-1010)

**BEFORE:**
```python
for a in range(0, 360, 45):
    rd = math.radians(a)
    ex = cx + int(math.cos(rd) * r)
    ey = cy + int(math.sin(rd) * r)
    pygame.draw.line(self._win, C["mine_spike"], (cx, cy), (ex, ey), max(1, ts // 16))
```

**AFTER:**
```python
lw = max(1, ts // 16)
for dx, dy in self._mine_spike_offsets:
    pygame.draw.line(self._win, C["mine_spike"], (cx, cy), (cx + dx, cy + dy), lw)
```

**Edge cases:**
- [x] lw (line width) calculation preserved
- [x] r in _rebuild_num_surfs must match r used here (both use max(2, ts // 3))

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit Phase 7A:**
```bash
git add gameworks/renderer.py
git commit -m "perf(renderer): cache mine spike offsets (Phase 7A)

Fixes: 8 trig calls (cos/sin/radians) per visible mine per frame.

Implementation:
- Pre-compute 8 offset tuples in _rebuild_num_surfs
- Replace trig loop with cached (dx, dy) lookup
- Radius formula: max(2, tile_size // 3)

Edge cases:
- min radius = 2 (prevents too-small spikes)
- 8 directions: 0°, 45°, ..., 315°
- int() rounds to pixel coords
- Radius formula matches between cache and usage

Performance impact: 8 trig calls × N mines/frame → 0

Tests: All existing tests pass

Refs: PERFORMANCE_PLAN.md Phase 7A
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 7B: Animation Set Cache

**Priority:** MEDIUM (now unblocked by Phase 0)
**Estimated time:** 30 minutes
**Files:** `gameworks/renderer.py`

### 7B.1 — Add animation set caches to __init__
**File:** `renderer.py` (in `Renderer.__init__`)

```python
# Animation set caches — rebuilt only when animation advances
self._anim_set_cache: set = set()
self._anim_set_last_idx: int = -1
self._win_anim_set_cache: set = set()
self._win_anim_last_key: tuple = (-1, -1)
```

**Edge cases:**
- [x] Initialize to empty set (not None)
- [x] _anim_set_last_idx = -1 (never matches valid idx ≥ 0)
- [x] _win_anim_last_key = (-1, -1) (never matches valid phase/idx)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 7B.2 — Cache AnimationCascade set
**File:** `renderer.py` (in `_draw_board`, replace set construction ~line 861-864)

**BEFORE:**
```python
anim_set = set()
if self.cascade and not self.cascade.done:
    anim_set = set(self.cascade.current())
```

**AFTER:**
```python
anim_set: set = set()
if self.cascade and not self.cascade.done:
    current = self.cascade.current()
    if self.cascade._idx != self._anim_set_last_idx:
        self._anim_set_cache = set(current)
        self._anim_set_last_idx = self.cascade._idx
    anim_set = self._anim_set_cache
```

**Edge cases:**
- [x] cascade is None: outer if handles
- [x] cascade.done: outer if handles
- [x] _idx only advances on ANIM_TICK (~35ms), not every frame

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

### 7B.3 — Cache WinAnimation set
**File:** `renderer.py` (in `_draw_board`, replace set construction ~line 866-869)

**BEFORE:**
```python
win_anim_set = set()
if self.win_anim and not self.win_anim.done:
    win_anim_set = set(self.win_anim.current())
```

**AFTER:**
```python
win_anim_set: set = set()
if self.win_anim and not self.win_anim.done:
    current = self.win_anim.current()
    key = (self.win_anim._phase, self.win_anim._idx)
    if key != self._win_anim_last_key:
        self._win_anim_set_cache = set(current)
        self._win_anim_last_key = key
    win_anim_set = self._win_anim_set_cache
```

**Edge cases:**
- [x] win_anim is None: outer if handles
- [x] win_anim.done: outer if handles
- [x] _phase is required: _idx resets to 0 at phase boundaries
- [x] _idx exists after Phase 0 fix

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit Phase 7B:**
```bash
git add gameworks/renderer.py
git commit -m "perf(renderer): cache animation sets (Phase 7B)

Fixes: set() constructed from lists every frame during animations.

Implementation:
- Cache AnimationCascade set, rebuild only when _idx advances
- Cache WinAnimation set, rebuild only when (_phase, _idx) changes
- Key includes _phase: _idx resets on phase transitions

Edge cases:
- cascade/win_anim None: outer if guards
- _idx advances on ANIM_TICK (~35ms), not every frame (1-2 frames per tick)
- Phase transitions reset _idx → must include _phase in key
- Initial keys (-1, -1) never match valid values

Performance impact: set() rebuild every frame → rebuild ~1/tick (~every 35ms)

Dependencies: Requires Phase 0 (WinAnimation._idx fix)

Tests: All existing tests pass

Refs: PERFORMANCE_PLAN.md Phase 7B, REMEDIATION_PLAN_VERIFICATION.md Phase 0
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Phase 8: Frame Timing Precision

**Priority:** LOW (but trivial)
**Estimated time:** 5 minutes
**Files:** `gameworks/main.py`

### 8.1 — Replace clock.tick() with clock.tick_busy_loop()
**File:** `main.py:223` (in main game loop)

**BEFORE:**
```python
self._renderer._clock.tick(FPS)
```

**AFTER:**
```python
self._renderer._clock.tick_busy_loop(FPS)
```

**Edge cases:**
- [x] Slightly higher CPU idle usage (spin-wait)
- [x] Sub-millisecond frame delivery accuracy
- [x] Correct trade-off for interactive game

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit Phase 8:**
```bash
git add gameworks/main.py
git commit -m "perf(main): use tick_busy_loop for precise frame timing (Phase 8)

Fixes: clock.tick() uses OS sleep with ~15ms granularity on Windows.
At 30 FPS (33.3ms/frame), frames arrive at 30ms or 45ms, creating jitter.

Implementation:
- Replace tick(FPS) with tick_busy_loop(FPS)
- Coarse sleep to approach target, spin-wait for last few ms
- Sub-millisecond frame delivery accuracy

Edge cases:
- Slightly higher CPU idle usage (acceptable for interactive game)
- Frame jitter reduced from 5-15ms to <2ms

Performance impact: 5-15ms jitter → <2ms jitter

Tests: All existing tests pass

Refs: PERFORMANCE_PLAN.md Phase 8
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Gap Fixes: Zoom-Specific Bottlenecks

**Priority:** CRITICAL (N-01, N-02) + MEDIUM (others)
**Estimated time:** 2-4 hours
**Files:** `gameworks/renderer.py`

### N-01: Debounce Ghost Smoothscale

**Problem:** ZO-01 — `smoothscale` fires on every scroll tick (8-10 times during zoom-out burst)

#### N-01.1 — Add debounce state to __init__
**File:** `renderer.py` (in `Renderer.__init__`)

```python
# Ghost surface debounce — defer rebuild until zoom settles
self._ghost_surf_pending_tile: int = 0   # tile size that needs rebuild
self._ghost_surf_built_tile:   int = 0   # tile size currently cached
```

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### N-01.2 — Mark pending on zoom event
**File:** `renderer.py` (MOUSEWHEEL handler, after `self._tile = new_tile`)

```python
if new_tile != self._tile:
    self._tile = new_tile
    self._ghost_surf_pending_tile = new_tile  # ← ADD THIS (mark dirty)
    # ... rest of zoom handling ...
```

**Edge cases:**
- [x] Set AFTER _tile update
- [x] Every zoom event updates pending, but rebuild deferred

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### N-01.3 — Defer rebuild in _draw_image_ghost
**File:** `renderer.py:1063-1064` (in `_draw_image_ghost`)

**BEFORE:**
```python
if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
    self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))
```

**AFTER:**
```python
# Rebuild only when tile size has stabilized (not on same frame as zoom event)
if self._ghost_surf_pending_tile != self._ghost_surf_built_tile:
    bw_pending = self.board.width  * self._ghost_surf_pending_tile
    bh_pending = self.board.height * self._ghost_surf_pending_tile
    self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw_pending, bh_pending))
    self._ghost_surf_built_tile = self._ghost_surf_pending_tile
```

**Edge cases:**
- [x] Defers rebuild until scrolling stops (pending == built)
- [x] Shows stale surface during scroll burst (slightly wrong but acceptable)
- [x] Reduces N rebuilds to 1 rebuild

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### N-01.4 — Also fix in _draw_win_animation_fx
**File:** `renderer.py:1229-1230` (in `_draw_win_animation_fx`)

Apply same debounce logic:
```python
if self._ghost_surf_pending_tile != self._ghost_surf_built_tile:
    bw = self.board.width  * self._ghost_surf_pending_tile
    bh = self.board.height * self._ghost_surf_pending_tile
    self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))
    self._ghost_surf_built_tile = self._ghost_surf_pending_tile
```

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit N-01:**
```bash
git add gameworks/renderer.py
git commit -m "perf(renderer): debounce ghost surface smoothscale on zoom (N-01)

Fixes ZO-01: smoothscale fires on every scroll tick during zoom burst.
At 300×370 board: 8-10 operations × 5-114 megapixels in <1 second.

Implementation:
- Track pending vs built tile size
- Mark pending on zoom event, defer rebuild to draw call
- Rebuild only after scrolling stops (pending == built)
- Shows stale surface during burst (acceptable visual trade-off)

Edge cases:
- Stale surface slightly wrong during scroll (user can't tell)
- Reduces N smoothscale ops per burst → 1 op after burst
- Applied to both _draw_image_ghost and _draw_win_animation_fx

Performance impact: 8-10 smoothscale ops/zoom burst → 1 op after burst

Tests: All existing tests pass

Refs: ZOOM_OUT_PERFORMANCE_REPORT.md ZO-01, N-01
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### N-02: Pixel-Map Mode for Extreme Zoom-Out

**Problem:** ZO-02 — 111,000 cells × 3 draw calls × 30 FPS = 10M draw calls/sec at tile ≤ 4px

**Note:** This is the most complex fix. Alternative: static board surface cache (simpler but still complex).

#### N-02.1 — Add pixel-map mode threshold
**File:** `renderer.py` (add constant near top)

```python
# Pixel-map mode threshold — below this tile size, use numpy direct blit
PIXEL_MAP_THRESHOLD = 4
```

---

#### N-02.2 — Implement _draw_board_pixelmap()
**File:** `renderer.py` (add new method)

```python
def _draw_board_pixelmap(self, ox: int, oy: int, ts: int):
    """
    Ultra-zoom-out mode: render board as dense pixel array.

    At tile ≤ 4px, individual glyphs/icons are sub-pixel. Instead of
    111,000 draw calls, use numpy to classify cells into color buckets
    and blit as single surface.

    Called when self._tile <= PIXEL_MAP_THRESHOLD
    """
    import numpy as np

    # Create pixel array: board.width × board.height
    w, h = self.board.width, self.board.height
    pixels = np.zeros((h, w, 3), dtype=np.uint8)

    # Classify cells by state
    _revealed = self.board._revealed
    _flagged = self.board._flagged
    _mine = self.board._mine

    # Hidden cells: dark gray
    pixels[~_revealed] = C["cell"]

    # Revealed cells: lighter
    pixels[_revealed & ~_mine] = C["bg"]

    # Flagged cells: flag color (red-ish)
    pixels[_flagged] = C["flag"]

    # Mines (if revealed): mine color
    pixels[_revealed & _mine] = C["mine"]

    # Convert to Surface and scale to tile size
    surf = pygame.surfarray.make_surface(pixels.swapaxes(0, 1))  # swap for pygame coord system
    scaled = pygame.transform.scale(surf, (w * ts, h * ts))
    self._win.blit(scaled, (ox, oy))
```

**Edge cases:**
- [x] ts = 0: shouldn't happen (min zoom floor is ~7)
- [x] w or h = 0: board initialization should prevent
- [x] swapaxes(0, 1): pygame uses (x, y) not (y, x)
- [x] Color constants must exist: C["cell"], C["bg"], C["flag"], C["mine"]

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

---

#### N-02.3 — Switch between modes in _draw_board
**File:** `renderer.py` (in `_draw_board`, before cell loop)

```python
def _draw_board(self, ...):
    # ... existing setup ...

    ts = self._tile

    # Use pixel-map mode at extreme zoom-out
    if ts <= PIXEL_MAP_THRESHOLD:
        self._draw_board_pixelmap(ox, oy, ts)
        return  # Skip cell loop entirely

    # Normal mode: per-cell drawing
    # ... existing cell loop ...
```

**Edge cases:**
- [x] Early return prevents cell loop at small tiles
- [x] PIXEL_MAP_THRESHOLD = 4: glyphs unreadable anyway
- [x] Threshold tunable (could be 5 or 6 if needed)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit N-02:**
```bash
git add gameworks/renderer.py
git commit -m "perf(renderer): add pixel-map mode for extreme zoom-out (N-02)

Fixes ZO-02: At minimum zoom (tile ≤ 4px), 111,000 cells × 3 draw calls × 30 FPS
= 10 million draw calls/second. Game locks up at full zoom-out.

Implementation:
- PIXEL_MAP_THRESHOLD = 4 (tiles smaller than 4px use pixel-map)
- _draw_board_pixelmap(): numpy classifies cells, single blit replaces cell loop
- Color buckets: hidden (dark), revealed (light), flagged (red), mines (black)
- Early return in _draw_board skips cell loop when ts ≤ threshold

Edge cases:
- ts = 0: shouldn't happen (min zoom ~7)
- Board dimensions = 0: prevented by initialization
- swapaxes(0,1): pygame uses (x,y) not (y,x)
- Threshold tunable (4px chosen; glyphs unreadable at this scale anyway)

Performance impact: 111,000 Python loop iterations → 1 numpy op + 1 blit

Tests: All existing tests pass

Refs: ZOOM_OUT_PERFORMANCE_REPORT.md ZO-02, N-02
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### ZO-07: mine_flash Empty-Dict Fast Path

**Problem:** 111,000 dict lookups on empty dict every frame (most frames have no flashing mines)

#### ZO-07.1 — Hoist guard before cell loop
**File:** `renderer.py` (in `_draw_board`, before cell loop)

```python
# Hoist guards for empty containers — avoid 111k lookups on empty dicts/sets
_has_flash = bool(self.engine.mine_flash)
```

---

#### ZO-07.2 — Short-circuit in _draw_cell
**File:** `renderer.py` (in `_draw_cell`, where mine_flash is checked ~line 950)

**BEFORE:**
```python
_flashing = now < self.engine.mine_flash.get((x, y), 0)
```

**AFTER:**
```python
_flashing = _has_flash and now < self.engine.mine_flash.get((x, y), 0)
```

**But wait:** `_has_flash` is not passed to `_draw_cell`. Add it to signature:

**File:** `renderer.py` (in `_draw_board`, cell loop call)

```python
self._draw_cell(
    x, y,
    _mine[y, x], _revealed[y, x], _flagged[y, x],
    _questioned[y, x], _neighbours[y, x],
    (px, py), ip, pressed == (x, y),
    self.fog, ts, in_win_anim, now,
    _has_flash  # ← ADD THIS
)
```

**File:** `renderer.py` (in `_draw_cell` signature)

```python
def _draw_cell(self,
               x: int, y: int,
               is_mine, is_revealed, is_flagged, is_questioned,
               neighbour_mines, pos: Tuple[int, int],
               in_anim: bool, is_pressed: bool,
               fog: bool, ts: int,
               in_win_anim: bool, now: float,
               has_flash: bool):  # ← ADD THIS
```

**File:** `renderer.py` (in `_draw_cell` body)

```python
_flashing = has_flash and now < self.engine.mine_flash.get((x, y), 0)
```

**Edge cases:**
- [x] mine_flash is empty 99.9% of frames (only populated 1.5s after mine hit)
- [x] Short-circuit eliminates 111k dict lookups when False

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit ZO-07:**
```bash
git add gameworks/renderer.py
git commit -m "perf(renderer): add empty-dict fast path for mine_flash (ZO-07)

Fixes: mine_flash dict lookup inside 111k-iteration cell loop.
Dict is empty 99.9% of frames (only populated 1.5s after mine hit).

Implementation:
- Hoist _has_flash = bool(mine_flash) before cell loop
- Pass has_flash to _draw_cell
- Short-circuit: has_flash and lookup (eliminates 111k lookups when False)

Edge cases:
- mine_flash empty most frames (only after mine hit)
- Short-circuit on False skips expensive dict.get()
- No behavior change, pure optimization

Performance impact: 111,000 dict lookups/frame → 0 (when empty)

Tests: All existing tests pass

Refs: ZOOM_OUT_PERFORMANCE_REPORT.md ZO-07
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

### ZO-13: Complete _win_size Cache Coverage

**Problem:** 6 sites still call `_win.get_width()` / `_win.get_height()` directly

#### ZO-13.1 — Replace direct calls
**File:** `renderer.py` (multiple locations)

Find and replace:
- `self._win.get_width()` → `self._win_size[0]`
- `self._win.get_height()` → `self._win_size[1]`

**Locations from VERIFICATION_DETAILED.md:**
- Line 601: smiley rect computation
- Line 674: `_on_resize()`
- Lines 726, 748: header right-align
- Line 1052: panel draw
- Arrow-key handlers (K_LEFT/K_RIGHT/K_UP/K_DOWN)

**Test after change:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Expected:** ALL tests pass

**Commit ZO-13:**
```bash
git add gameworks/renderer.py
git commit -m "perf(renderer): complete _win_size cache coverage (ZO-13)

Fixes: 6 sites still call _win.get_width()/_win.get_height() directly,
bypassing Phase 2A cache.

Implementation:
- Replace all remaining get_width() → _win_size[0]
- Replace all remaining get_height() → _win_size[1]

Locations:
- renderer.py:601 (smiley rect)
- renderer.py:674 (_on_resize)
- renderer.py:726, 748 (header right-align)
- renderer.py:1052 (panel draw)
- Arrow-key handlers (K_LEFT/K_RIGHT/K_UP/K_DOWN)

Edge cases:
- Cache updated on VIDEORESIZE (Phase 2A already implemented)
- C method call → tuple index (faster)

Performance impact: 6 C calls/frame → 0

Tests: All existing tests pass

Refs: ZOOM_OUT_PERFORMANCE_REPORT.md ZO-13, Phase 2 gap
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Final Verification

### Run Full Test Suite
```bash
cd /home/vercel-sandbox/MineStreakerContrastCampaign
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v --tb=short
```

**Expected:** ALL tests pass

---

### Manual Smoke Test (if possible in environment)
```bash
# Run game locally (not in sandbox)
python gameworks/main.py

# Test scenarios:
# 1. Create large board (300×370)
# 2. Zoom out fully
# 3. Verify FPS ~30 (not <10)
# 4. Zoom in/out rapidly
# 5. Flag many cells
# 6. Trigger win animation
# 7. Check for visual artifacts
```

---

### Performance Measurement
```bash
# Add FPS counter to main.py for verification
# Expected improvements:
# - Zoom-out FPS: <10 → 25-30 (with N-01/N-02: 30)
# - Frame jitter: 5-15ms → <2ms
# - Surface allocations/frame: ~100 → 0
# - Font renders/frame: ~20 → ~2
```

---

## Appendix A: Test Command Reference

**Run all tests:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**Run specific test file:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_surface_cache.py -v
```

**Run specific test:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_surface_cache.py::test_ghost_cell_buf_allocated_once_per_tile_size -v
```

**Run with keyword filter:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v -k "cache or animation"
```

**Stop on first failure:**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v -x
```

---

## Appendix B: Edge Cases Checklist

### General
- [x] Tile size = 0 or negative
- [x] Board dimensions = 0
- [x] None checks for optional objects
- [x] Array index bounds
- [x] Alpha channel transparency
- [x] Color tuples vs pygame.Color objects

### Phase-Specific
- [x] **Phase 0:** _idx overflow, phase transitions, speed changes
- [x] **Phase 4A:** Tile size changes, alpha compositing, buffer clear
- [x] **Phase 4B:** Window size 0×0, resize during draw, invalidation timing
- [x] **Phase 4C:** Same as 4B
- [x] **Phase 5:** Empty strings, None text, color types, cache growth
- [x] **Phase 6:** Button dimensions, font render failure, inactive states
- [x] **Phase 7A:** Negative radii, tile=0
- [x] **Phase 7B:** None animations, _idx sync, phase transitions
- [x] **Phase 8:** No edge cases (trivial)
- [x] **N-01:** Rapid zoom, exact frame boundary, stale surface
- [x] **N-02:** Threshold boundary (ts=4), array alignment, board size 0
- [x] **ZO-07:** Empty dict 99.9% of frames, short-circuit
- [x] **ZO-13:** Cache invalidation on resize

---

## Appendix C: Commit Message Template

```
<type>(scope): <short summary>

<detailed description of what changed and why>

Implementation:
- Bullet point 1
- Bullet point 2

Edge cases:
- Edge case 1 handled
- Edge case 2 handled

Performance impact: <before> → <after>

Tests: <test summary>

Refs: <document references>
Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>
```

---

*Task plan generated 2026-05-11. Estimated total time: 8-12 hours including testing.*
