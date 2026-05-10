# Resolved Findings

## Resolution Log

| Finding ID | Severity | Resolution Date | Commit | Notes |
|---|---|---|---|---|
| FIND-STATE-HIGH-h008a | HIGH | 2026-05-10 | 09e17c1 | `assets/line_art_irl_18v2.png` committed. All 3 boards have source image. |
| FIND-ARCH-CRITICAL-f001a | CRITICAL | 2026-05-10 | local-fixes | `from .renderer import FPS` added to main.py imports |
| FIND-ARCH-CRITICAL-f002a | CRITICAL | 2026-05-10 | local-fixes | `GameEngine.state` property added |
| FIND-ARCH-CRITICAL-f003a | CRITICAL | 2026-05-10 | local-fixes | Removed erroneous `compile_sa_kernel(w, h, seed)` call; `default_config()` provides kernel |
| FIND-ARCH-CRITICAL-f004a | CRITICAL | 2026-05-10 | local-fixes | `run_phase1_repair(grid, target, weights, forbidden, time_budget_s=90.0, max_rounds=300)` |
| FIND-ARCH-CRITICAL-f005a | CRITICAL | 2026-05-10 | local-fixes | `self._btn_w` stored as instance attr in `__init__`; used in `_draw_panel` |
| FIND-ARCH-CRITICAL-f006a | CRITICAL | 2026-05-10 | local-fixes | `load_board_from_npy()` auto-detects pipeline (0/1) vs game (-1/0-8) format |
| FIND-ARCH-HIGH-h001a | HIGH | 2026-05-10 | local-fixes | Removed duplicate `handle_panel()` block from `GameLoop.run()` |
| FIND-RENDER-HIGH-h002a | HIGH | 2026-05-10 | local-fixes | `_draw_overlay()` now checks `self.fog` not `self._fog` |
| FIND-PERF-HIGH-h003a | HIGH | 2026-05-10 | local-fixes | `_draw_image_ghost()` uses cached `_ghost_surf`; no per-cell smoothscale |
| FIND-PERF-HIGH-h004a | HIGH | 2026-05-10 | local-fixes | `_draw_loss_overlay()` has viewport culling (tx0/ty0/tx1/ty1) |
| FIND-STATE-HIGH-h005a | HIGH | 2026-05-10 | local-fixes | `GameEngine.restart()` respects mode: reloads npy/image path on restart |
| FIND-TEST-HIGH-h006a | HIGH | 2026-05-10 | local-fixes | `tests/test_gameworks_engine.py` created — 29 tests, 27 pass, 2 skip (pygame) |
| FIND-DEVOPS-HIGH-h007a | HIGH | 2026-05-10 | local-fixes | `requirements.txt` created with all 7 dependencies and version ranges |
| FIND-PERF-MEDIUM-m001a | MEDIUM | 2026-05-10 | local-fixes | `Board.__init__` uses scipy convolution; O(H*W) vs O(H*W*9) Python loop |
| FIND-RENDER-MEDIUM-m002a | MEDIUM | 2026-05-10 | local-fixes | `_draw_bg()` dead code removed from renderer.py |
| FIND-ARCH-MEDIUM-m003a | MEDIUM | 2026-05-10 | local-fixes | `_RouteCfg` inner class removed from `load_board_from_pipeline()` |
| FIND-STATE-MEDIUM-m004a | MEDIUM | 2026-05-10 | local-fixes | Redundant `board._state = "lost"` removed from `left_click()` and `middle_click()` |
| FIND-STATE-MEDIUM-m007a | MEDIUM | 2026-05-10 | local-fixes | Win condition: `revealed_count == total_safe AND correct_flags == total_mines` |
| FIND-SECURITY-LOW-l001a | LOW | 2026-05-10 | local-fixes | `traceback.print_exc()` added in pipeline exception handler |
| FIND-DEVOPS-LOW-l002a | LOW | 2026-05-10 | local-fixes | `.github/workflows/ci.yml` created (pytest on push/PR, SDL_VIDEODRIVER=dummy) |
| FIND-DOCS-LOW-l003a | LOW | 2026-05-10 | local-fixes | Gameworks usage section added to README.md (launch modes, controls, tests) |
| FIND-ARCH-LOW-l004a | LOW | 2026-05-10 | local-fixes | Audit prompt moved from repo root to `docs/` |
