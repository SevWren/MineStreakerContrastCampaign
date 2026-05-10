# PHASE 13 — Remediation Planning
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Immediate Remediation (Phase 0 — do now)

The 5 critical bugs prevent ANY game session from completing. Fix all in one commit.

### Commit: "fix: resolve 5 critical runtime crashes in gameworks/"

#### gameworks/engine.py — 3 changes

**Change 1**: Add `state` property to `GameEngine` class
```python
# After stop_timer() method:
@property
def state(self) -> str:
    """Game state: 'playing' | 'won' | 'lost'."""
    return self.board._state
```

**Change 2**: Fix `compile_sa_kernel()` call in `load_board_from_pipeline()`
```python
# Replace:
compile_sa_kernel(board_w, board_h, seed)

# With:
kernel = compile_sa_kernel()
```
Then update the `run_sa` call to pass `kernel` as first argument:
```python
grid, *_ = run_sa(kernel, grid, target, weights, forbidden, **params["sa"])
```

**Change 3**: Fix `run_phase1_repair()` call and remove `_RouteCfg`
```python
# Remove the entire _RouteCfg class definition.
# Replace:
grid = run_phase1_repair(grid, target, weights, forbidden, _RouteCfg(), seed)

# With:
grid = run_phase1_repair(grid, target, weights, forbidden, time_budget_s=90.0)
```

#### gameworks/main.py — 1 change

**Change 4**: Add FPS constant
```python
# After imports, before GameLoop class:
FPS = 60  # Frames per second (must match renderer.FPS)
```

#### gameworks/renderer.py — 1 change

**Change 5**: Store btn_w on self
```python
# In __init__, find:
btn_w = self.PANEL_W - 2 * self.PAD
# Change to:
self._btn_w = self.PANEL_W - 2 * self.PAD

# In _draw_panel(), replace all btn_w references with self._btn_w
```

### Regression test to add immediately:
```python
# tests/test_gameworks_critical_regressions.py
def test_game_engine_has_state_property():
    from gameworks.engine import GameEngine
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    assert eng.state == "playing"

def test_fps_defined_in_main():
    import gameworks.main as main_module
    assert hasattr(main_module, "FPS")
    assert main_module.FPS == 60

def test_compile_sa_kernel_zero_args():
    import inspect
    from sa import compile_sa_kernel
    assert len(inspect.signature(compile_sa_kernel).parameters) == 0

def test_run_phase1_repair_time_budget_param():
    import inspect
    from repair import run_phase1_repair
    params = list(inspect.signature(run_phase1_repair).parameters)
    assert params[4] == "time_budget_s"
```

## Short Term Remediation (Phase 1)

### Commit: "fix: resolve high-severity correctness bugs in gameworks/"

1. `gameworks/renderer.py` `_draw_overlay()`: `getattr(self, '_fog', False)` → `self.fog`
2. `gameworks/main.py`: Remove the duplicate `handle_panel()` block (7 lines)
3. `gameworks/main.py`: Add `from typing import Optional` to imports
4. `gameworks/renderer.py`: Replace `self.board = engine.board` with `self.engine = engine` and update all `self.board` → `self.engine.board` (~30 replacements)

### Commit: "perf: fix critical frame-rate regressions in gameworks/renderer.py"

1. Cache ghost composite surface
2. Add viewport culling to `_draw_loss_overlay()`
3. Cache win animation scaled surface

### Commit: "perf: use scipy convolution for Board neighbour computation"

1. Replace Python loop in `Board.__init__`
2. Verify correctness: `board._neighbours` values must match manual calculation

## Risk Register for Remediation

| Fix | Risk | Mitigation |
|---|---|---|
| Add state property | Zero | Pure addition, no behavior change |
| Fix FPS | Zero | Pure addition |
| Fix compile_sa_kernel | Low | Image mode was broken before; now it might work (or still fail with other bugs) |
| Fix run_phase1_repair | Low | Image mode behavior changes; test with actual image |
| Fix btn_w | Zero | Fixes crash; no behavior change when no image |
| Fix fog attribute | Zero | Feature was non-functional; now becomes functional |
| Remove double dispatch | Low | Test restart and save actions after fix |
| Replace self.board with self.engine.board | Medium | 30 replacements; regression test required |
| scipy convolution | Low | Verify neighbour counts match Python loop |
| Win condition flag check | High | Changes gameplay; UX test needed |
