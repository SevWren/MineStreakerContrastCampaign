# PHASE 12 — Refactor Roadmap
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Cross-reference
See `roadmap.md` for the full prioritized roadmap.

## Implementation Sequencing Detail

### Sprint 1: Make It Work (Phase 0 — Critical Fixes)

All items are trivial code changes. No tests need to pass before fixing.

**Step 1**: `gameworks/engine.py` — add `state` property to `GameEngine`
```python
@property
def state(self) -> str:
    return self.board._state
```

**Step 2**: `gameworks/main.py` — add `FPS = 60` after imports

**Step 3**: `gameworks/engine.py` — fix `compile_sa_kernel()` call (remove args)

**Step 4**: `gameworks/engine.py` — fix `run_phase1_repair()` call (use keyword args)

**Step 5**: `gameworks/renderer.py` — fix `btn_w` → `self._btn_w` (init + draw_panel)

**Validation**: `python -m gameworks.main --random --easy` must run without NameError/AttributeError.

### Sprint 2: Make It Correct (Phase 1 — Correctness)

**Step 6**: `gameworks/renderer.py` — fix `_fog` → `self.fog` in `_draw_overlay()`

**Step 7**: `gameworks/main.py` — remove duplicate `handle_panel()` block

**Step 8**: `gameworks/renderer.py` — replace all `self.board` with `self.engine.board`
  - Migration concern: ~30 occurrences. Use find-replace.
  - Risk: Low (same object, just re-dereferenced)
  - Alternative: Keep self.board but update it after first-click regeneration

**Step 9**: `gameworks/engine.py` — fix `MoveResult.flagged` type
  - Change: `MoveResult.flagged: bool` → `MoveResult.flagged: str`
  - Or: Store str return value directly: `flagged=placed if placed == 'flag' else placed`

### Sprint 3: Make It Fast (Phase 2 — Performance)

Apply fixes in order of impact:
1. Cache ghost surface (largest win)
2. Viewport culling for loss overlay (second largest)
3. scipy convolution for Board init
4. Cache win_anim_scaled

### Sprint 4: Make It Safe (Phase 3 — Tests)

Add gameworks test files. Priority:
1. Regression tests for Phase 0 bugs (confirm they stay fixed)
2. Board unit tests (correctness)
3. GameEngine integration tests
4. Headless renderer tests

## Migration Concerns

### stale board reference refactor
When changing `self.board` to `self.engine.board` in Renderer:
- 30 occurrences in renderer.py
- All are read-only accesses (board.width, board.height, board.snapshot, etc.)
- No write operations through self.board in renderer
- Low risk: board reference is always valid through self.engine
- Alternative approach: Override `__getattr__` to delegate to `self.engine.board`

### Win condition change
Changing win condition to require correct flags changes gameplay:
- Current behavior: player can win without flagging anything
- New behavior: player must correctly flag ALL mines
- This is a meaningful UX change that affects casual players
- Recommend adding a `require_flags: bool = True` config option to allow classic mode

## Rollout Sequencing

Phase 0 → Phase 1 → Phase 3 (tests) → Phase 2 (performance) → Phase 4 (devops)

Phase 3 (tests) should come before Phase 2 (performance) to ensure performance changes don't break correctness.
