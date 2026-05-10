# Refactor Roadmap
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Phase 0 — Critical Fixes (Make the game playable)

All 6 critical bugs must be fixed before ANY game session can complete successfully.

| Item | Complexity | Risk | Finding |
|---|---|---|---|
| Add `GameEngine.state` property | Trivial | Zero | FIND-ARCH-CRITICAL-f002a |
| Add `FPS = 60` to main.py | Trivial | Zero | FIND-ARCH-CRITICAL-f001a |
| Fix compile_sa_kernel() call | Low | Low | FIND-ARCH-CRITICAL-f003a |
| Fix run_phase1_repair() call | Low | Low | FIND-ARCH-CRITICAL-f004a |
| Fix btn_w → self._btn_w | Trivial | Zero | FIND-ARCH-CRITICAL-f005a |
| Add pipeline .npy format adapter | Low | Low | FIND-ARCH-CRITICAL-f006a |

**Estimated effort**: 1-2 hours for all 6 fixes
**Risk**: Zero regression risk (fixing crashes introduces no new behavior)
**Sequencing**: Can be done in any order. Do all 6 in a single commit.

**Note on Fix 6 (format adapter)**: The three pre-built boards in `results/iter9/` cannot be loaded at all without this fix — `load_board_from_npy()` will either raise `ValueError` (neighbour validation mismatch) or silently load 0 mines. This fix is required before the NPY boards can be used for game development.

---

## Phase 1 — Correctness & Feature Fixes (2-4 hours)

| Item | Complexity | Risk | Finding |
|---|---|---|---|
| Fix fog attribute `_fog` → `fog` | Trivial | Zero | FIND-RENDER-HIGH-h002a |
| Remove double panel click dispatch | Low | Low | FIND-ARCH-HIGH-h001a |
| Fix `Optional` import in main.py | Trivial | Zero | PHASE-03 static analysis |
| Fix stale board reference (store engine, not board) | Medium | Low | PHASE-04 §3.1 |
| Fix MoveResult.flagged type (str, not bool) | Low | Low | PHASE-04 §3.3 |
| Add win condition flag check | Medium | Medium | FIND-STATE-MEDIUM-m007a |

**Win condition note**: Adding the flag check changes gameplay behavior. This should be a deliberate decision aligned with `GAME_DESIGN.md`.

---

## Phase 2 — Performance (4-8 hours)

| Item | Complexity | Risk | Finding |
|---|---|---|---|
| Cache ghost surface (fix per-cell allocation) | Medium | Low | FIND-PERF-HIGH-h003a |
| Cache win_anim scaled surface | Low | Zero | PHASE-06 §1.2 |
| Viewport culling in _draw_loss_overlay | Low | Zero | FIND-PERF-HIGH-h004a |
| scipy convolution for Board._neighbours | Low | Low | FIND-PERF-MEDIUM-m001a |
| Vectorize _save_npy | Low | Zero | FIND-PERF-MEDIUM-m008a |
| Cache number glyph surfaces | Low | Zero | PHASE-06 §7 |

---

## Phase 3 — Test Coverage (4-8 hours)

| Item | Complexity | Notes |
|---|---|---|
| Create tests/test_gameworks_engine.py | Medium | Use generated-tests.md as starting point |
| Create tests/test_gameworks_renderer_headless.py | Medium | Requires SDL_VIDEODRIVER=dummy |
| Add regression tests for all 5 critical bugs | Low | Per generated-tests.md |
| Add Board correctness tests | Low | Flood-fill, win/loss, chord |
| Add GameEngine lifecycle tests | Medium | start(), restart(), timer |

---

## Phase 4 — DevOps & Documentation (2-4 hours)

| Item | Complexity | Notes |
|---|---|---|
| Create requirements.txt | Trivial | Pin versions |
| Create .github/workflows/ci.yml | Low | Per PHASE-09 |
| Add gameworks usage to README | Low | Python commands, examples |
| Create docs/adr/001-pygame-implementation.md | Low | Document tech choice |
| Move audit prompt to docs/ | Trivial | FIND-ARCH-LOW-l004a |
| Extract SA constants to config file | Medium | FIND-ARCH-MEDIUM-m006a |

---

## Phase 5 — Architecture Refactor (Long Term, 20-40 hours)

| Item | Complexity | Risk | Notes |
|---|---|---|---|
| Decompose Renderer into layers | High | Medium | Breaks existing behavior; requires retest |
| Move pipeline load to background thread | High | Medium | Requires async/threading in main loop |
| Implement scoring system per GAME_DESIGN.md | High | Low | New feature |
| Implement hint engine | High | Low | New feature; uses solver.py |
| Implement undo engine | Medium | Medium | Action stack |
| Web port (React + FastAPI) | Very High | Low | Frontend spec implementation |

---

## Dependency-Aware Sequencing

```
Phase 0 (critical fixes) ─────────────────────────────────────┐
    │                                                           │
    ├── Phase 1 (correctness fixes) depends on Phase 0         │
    │       │                                                   │
    │       ├── Phase 2 (performance) independent of Phase 1   │
    │       │                                                   │
    │       └── Phase 3 (tests) helps validate Phase 0+1+2     │
    │                                                           │
    └── Phase 4 (devops/docs) independent of all above         │
                                                               │
Phase 5 (architecture) depends on Phase 0+1+3 complete ───────┘
```

## Suggested PR Breakdown

| PR | Changes | Reviewable |
|---|---|---|
| PR-01: Fix 6 critical runtime crashes | Phase 0 items (incl. pipeline .npy adapter) | 6 changes, one commit |
| PR-02: Fix high-severity correctness bugs | Phase 1 items | ~10 changes |
| PR-03: Performance improvements | Phase 2 items | ~6 changes |
| PR-04: Test coverage for gameworks | Phase 3 items | New files only |
| PR-05: DevOps & documentation | Phase 4 items | New files + README update |
| PR-06+: Architecture refactors | Phase 5 items | Large, sequential |
