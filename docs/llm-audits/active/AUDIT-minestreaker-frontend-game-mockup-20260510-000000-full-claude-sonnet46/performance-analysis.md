# Performance Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

See PHASE-06-performance-analysis.md for full detail.

## Hotspot Summary

| Hotspot | Location | Severity | Fix |
|---|---|---|---|
| Per-cell Surface allocation in ghost rendering | renderer.py _draw_image_ghost | CRITICAL | Cache ghost composite Surface |
| Full-board smoothscale per frame (win anim) | renderer.py _draw_win_animation_fx | HIGH | Cache scaled surface |
| Loss overlay iterates all cells | renderer.py _draw_loss_overlay | HIGH | Viewport cull |
| Python loop for Board._neighbours | engine.py Board.__init__ | HIGH | scipy convolution |
| _save_npy() iterates via snapshot() | main.py _save_npy | MEDIUM | Vectorize with numpy |

## Expected Performance Profile (after fixes)

| Scenario | Before | After |
|---|---|---|
| Normal gameplay (no image) | ~60fps | ~60fps (no change) |
| Image mode, 100 flags | <30fps | ~60fps |
| Image mode, 1000 flags | <5fps | ~60fps |
| Loss screen (300×370) | <10fps | ~60fps |
| Board init (300×370) | ~2-5s | <10ms |
| Save board (300×370) | ~2-5s | <1ms |
