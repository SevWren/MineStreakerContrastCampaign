# Findings Register
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Summary

| Severity | Count |
|---|---|
| CRITICAL | 6 |
| HIGH | 8 (1 resolved) |
| MEDIUM | 7 |
| LOW | 4 |
| **Open** | **25** |
| **Total (incl. resolved)** | **26** |

_Updated 2026-05-10 (ca3eee4): +2 findings (FIND-ARCH-CRITICAL-f006a, FIND-STATE-HIGH-h008a)_
_Updated 2026-05-10 (09e17c1): FIND-STATE-HIGH-h008a resolved — line_art_irl_18v2.png committed to assets/_

---

## CRITICAL Findings

### FIND-ARCH-CRITICAL-f001a — FPS NameError in main.py

**File**: `gameworks/main.py` ~line 237
**Severity**: CRITICAL | **Confidence**: HIGH

`self._renderer._clock.tick(FPS)` references `FPS` which is defined only in `renderer.py` (value: 60) and never imported into `main.py`. **Every game session crashes with `NameError: name 'FPS' is not defined` on the first frame tick.**

**Fix**: Add `FPS = 60` to `main.py` or import it: `from .renderer import FPS`

---

### FIND-ARCH-CRITICAL-f002a — GameEngine has no .state property

**File**: `gameworks/main.py` ~lines 203, 220; `gameworks/engine.py` ~lines 280-310
**Severity**: CRITICAL | **Confidence**: HIGH

`GameLoop.run()` accesses `self._engine.state` to determine game outcome for rendering and state transitions. `GameEngine` has no `.state` attribute. `Board._state` is private and internal to `Board`. **Results in `AttributeError` on every run.**

**Fix**: Add to `GameEngine`:
```python
@property
def state(self) -> str:
    return self.board._state
```

---

### FIND-ARCH-CRITICAL-f003a — compile_sa_kernel() called with 3 args, accepts 0

**File**: `gameworks/engine.py` ~line 210; `sa.py` line 73
**Severity**: CRITICAL | **Confidence**: HIGH

`load_board_from_pipeline()` calls `compile_sa_kernel(board_w, board_h, seed)`. Actual signature: `def compile_sa_kernel():` — no parameters. **TypeError in `--image` mode.** Silently caught and falls back to random board.

**Fix**: `kernel = compile_sa_kernel()` then pass `kernel` to `run_sa()` as first arg.

---

### FIND-ARCH-CRITICAL-f004a — run_phase1_repair() called with wrong argument types

**File**: `gameworks/engine.py` ~line 245; `repair.py` lines 70-80
**Severity**: CRITICAL | **Confidence**: HIGH

Call: `run_phase1_repair(grid, target, weights, forbidden, _RouteCfg(), seed)`
Signature: `run_phase1_repair(grid, target, weights, forbidden, time_budget_s=90.0, max_rounds=300, ...)`

`_RouteCfg()` object passed as `time_budget_s` (float), `seed` integer passed as `max_rounds`. **TypeError or incorrect repair on image mode.** Silently swallowed.

**Fix**: `run_phase1_repair(grid, target, weights, forbidden, time_budget_s=90.0)` — remove `_RouteCfg` class.

---

### FIND-ARCH-CRITICAL-f006a — Pipeline .npy format incompatible with load_board_from_npy()

**Files**: `gameworks/engine.py`, `results/iter9/*/grid_iter9_*.npy`
**Severity**: CRITICAL | **Confidence**: HIGH
**Added**: 2026-05-10 (commit ca3eee4)

All three committed pipeline boards in `results/iter9/` use `int8` encoding where `0=safe, 1=mine`. `load_board_from_npy()` detects mines with `if grid[y, x] < 0`. Pipeline values of `1` are not negative, so **every mine cell is treated as safe**. All three boards load with **zero mines** — the game is immediately won on first reveal.

```python
# gameworks/engine.py — BROKEN for pipeline boards
for y in range(h):
    for x in range(w):
        if grid[y, x] < 0:   # ← pipeline boards have no negative values
            mine_pos.add((x, y))
```

**Root cause**: Two separate encoding conventions developed without coordination:
- Game format (`_save_npy()`): `-1=mine, 0-8=neighbour_count`
- Pipeline format (`run_iter9.py`): `0=safe, 1=mine` (raw SA optimization grid)

**Fix**: Add format auto-detection in `load_board_from_npy()`:
```python
# Detect pipeline format: values are only {0, 1}, no negatives
if grid.min() >= 0 and grid.max() <= 1:
    mine_pos = set(zip(*np.where(grid == 1)[::-1]))  # (x,y) pairs
else:
    mine_pos = set(zip(*np.where(grid < 0)[::-1]))
```
Or add a dedicated `load_board_from_pipeline_npy()` function.

---

### FIND-ARCH-CRITICAL-f005a — btn_w NameError in _draw_panel()

**File**: `gameworks/renderer.py` ~lines 940-950
**Severity**: CRITICAL | **Confidence**: HIGH

`_draw_panel()` uses `btn_w` for thumbnail positioning. `btn_w` is a local variable in `__init__()` not stored as `self._btn_w`. **`NameError: name 'btn_w' is not defined` on every frame when an image is loaded.**

**Fix**: In `__init__`: `self._btn_w = self.PANEL_W - 2 * self.PAD`. In `_draw_panel`: use `self._btn_w`.

---

## HIGH Findings

### FIND-ARCH-HIGH-h001a — Double panel click processing

**File**: `gameworks/main.py` lines 155-175; `gameworks/renderer.py` 490-510

`handle_event()` already calls `handle_panel()` internally. The main loop also calls `handle_panel()` directly for the same event. Panel clicks (Restart, Save) fire twice per click.

**Fix**: Remove the redundant `handle_panel()` call from `GameLoop.run()`.

---

### FIND-RENDER-HIGH-h002a — Fog-of-war completely non-functional

**File**: `gameworks/renderer.py` ~line 540

`_draw_overlay()` checks `getattr(self, '_fog', False)` but attribute is `self.fog`. Always returns False → fog is never rendered.

**Fix**: Change to `if not self.fog: return`.

---

### FIND-PERF-HIGH-h003a — Per-cell Surface allocation in _draw_image_ghost()

**File**: `gameworks/renderer.py` ~lines 820-855

Creates `pygame.Surface((tile, tile))` per flagged cell per frame. On 300×370 boards: up to 111,000 allocations/frame at 60 FPS = ~6.6M Surface objects/second.

**Fix**: Pre-compute full-board ghost surface; blit masked regions instead of per-cell surfaces.

---

### FIND-PERF-HIGH-h004a — _draw_loss_overlay() has no viewport culling

**File**: `gameworks/renderer.py` ~lines 815-835

Iterates all H×W cells without culling. 111,000 `board.snapshot()` calls per frame on loss screen.

**Fix**: Apply same tx0/ty0/tx1/ty1 culling as `_draw_board()`.

---

### FIND-STATE-HIGH-h005a — GameEngine.restart() ignores image/npy mode

**File**: `gameworks/engine.py` ~lines 330-342

`restart()` always creates random boards. Image-mode and npy-mode boards revert to random on restart.

**Fix**: Check `self.mode` and reload accordingly.

---

### FIND-TEST-HIGH-h006a — Zero test coverage for gameworks/

**Files**: All gameworks/ files

1791+ LOC across 4 files with zero unit tests. All 5 critical bugs detectable by basic tests.

**Fix**: Create `tests/test_gameworks_engine.py` and `tests/test_gameworks_renderer_headless.py`.

---

### FIND-DEVOPS-HIGH-h007a — No requirements.txt or environment specification

**File**: README.md (prose-only dependencies)

No `requirements.txt`, `pyproject.toml`, or `setup.py`. Reproducible environments impossible.

**Fix**: Create `requirements.txt` with pinned versions.

---

### ~~FIND-STATE-HIGH-h008a~~ — Source image missing for 2 of 3 committed pipeline boards ✓ RESOLVED (commit 09e17c1)

**Files**: `results/iter9/20260430T004415Z_line_art_irl_18v2_300w_*/`, `results/iter9/20260430T004522Z_line_art_irl_18v2_600w_*/`, `assets/`
**Severity**: HIGH | **Confidence**: HIGH
**Added**: 2026-05-10 (commit ca3eee4) | **Resolved**: 2026-05-10 (commit 09e17c1)

`assets/line_art_irl_18v2.png` (712KB) committed. All 3 pipeline boards now have their source image available.

Two of the three committed boards were generated from `line_art_irl_18v2`, which does not exist in `assets/`. The `assets/` directory only contains line art images up to `line_art_irl_13.jpeg`. Without the source image:

- Image ghost overlay cannot be rendered (`--image` mode falls back to random or fails)
- Win animation has no image to reveal
- Panel thumbnail absent

Only the 300×370 board (`input_source_image_300w_seed42`) has its source image present at `assets/input_source_image.png`.

**Fix**: Commit `line_art_irl_18v2` source image to `assets/`, or document which asset to use as a substitute, or remove the two orphaned board directories.

---

## MEDIUM Findings

### FIND-PERF-MEDIUM-m001a — Board.__init__ uses Python loop for neighbour counts
- `gameworks/engine.py` ~lines 70-76
- Use `core.compute_N()` numpy convolution instead

### FIND-RENDER-MEDIUM-m002a — _draw_bg() is dead code
- `gameworks/renderer.py` ~lines 570-585
- Never called. Remove or wire up.

### FIND-ARCH-MEDIUM-m003a — _RouteCfg duplicates pipeline.RepairRoutingConfig
- `gameworks/engine.py` ~lines 228-240
- Use canonical class or remove entirely.

### FIND-STATE-MEDIUM-m004a — Board._state mutated externally after Board already sets it
- `gameworks/engine.py` ~lines 287-292, 316-321
- Remove redundant `board._state = 'lost'` lines.

### FIND-DOCS-MEDIUM-m005a — frontend_spec/ describes unimplemented React app
- `docs/frontend_spec/`
- Spec describes React 18/TypeScript; only pygame implementation exists.

### FIND-ARCH-MEDIUM-m006a — 30+ SA tuning constants in run_iter9.py
- `run_iter9.py` ~lines 75-200
- Extract to config file.

### FIND-STATE-MEDIUM-m007a — Win condition ignores correct flag count
- `gameworks/engine.py` ~lines 140-160
- Win triggers on reveal-all; image-reconstruction win (flags = mines) not checked.

---

## LOW Findings

### FIND-SECURITY-LOW-l001a — Broad except swallows all pipeline errors silently
- `gameworks/engine.py` ~lines 250-258

### FIND-DEVOPS-LOW-l002a — No CI/CD pipeline
- No `.github/workflows/`

### FIND-DOCS-LOW-l003a — No gameworks usage docs in README
- README only covers pipeline, not game usage.

### FIND-ARCH-LOW-l004a — Audit prompt file committed to repo root
- `full_enterprise_grade_repository_audit_and_remediation_analysis_prompt.md`
