# Migration Plan
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Current State → Fully Functional Game (gameworks/)

### Stage 1: Minimal Viable Game (1-2 days)
Fix all critical and high bugs. Result: game sessions complete without crash.

Files changed:
- `gameworks/engine.py`: state property, compile_sa_kernel fix, run_phase1_repair fix
- `gameworks/main.py`: FPS constant, Optional import, remove double dispatch
- `gameworks/renderer.py`: btn_w→self._btn_w, fog attribute fix

### Stage 2: Feature Complete + Performance (3-5 days)
Add test coverage, fix performance, correct gameplay behaviors.

Files changed:
- `gameworks/renderer.py`: ghost surface cache, loss overlay culling, win anim cache
- `gameworks/engine.py`: scipy convolution for neighbours, correct win condition
- New: `tests/test_gameworks_engine.py`
- New: `tests/test_gameworks_renderer_headless.py`
- New: `requirements.txt`

### Stage 3: DevOps + Docs (1-2 days)
- New: `.github/workflows/ci.yml`
- New: `docs/adr/001-pygame-implementation.md`
- Updated: `README.md` (gameworks section)
- New: `pyproject.toml`

### Stage 4: Long-Term Architecture (2-4 weeks, optional)
Option A: Decompose Renderer into layers (gameworks refactor)
Option B: Implement React/TypeScript frontend per frontend_spec/ (web port)
Option C: Both — maintain pygame version + build web version

## Backward Compatibility Notes

### Win condition change
Changing `revealed_count == total_safe` → `revealed_count == total_safe AND correct_flags == total_mines`:
- Breaks existing "win by revealing all safes" behavior
- Users who relied on winning without flags will need to adapt
- Recommendation: Add `--classic` flag to preserve original behavior

### Board._neighbours computation change
Replacing Python loop with scipy convolution produces identical results. No compatibility concern.

### self.board → self.engine.board in Renderer
Internal refactor only. No external API change.
