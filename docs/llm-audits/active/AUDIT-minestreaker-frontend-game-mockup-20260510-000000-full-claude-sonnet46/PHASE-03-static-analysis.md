# PHASE 03 — Static Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. Python Issues by File

### gameworks/engine.py

| Issue | Location | Severity |
|---|---|---|
| `compile_sa_kernel(board_w, board_h, seed)` — wrong arg count | ~line 210 | CRITICAL |
| `run_phase1_repair(..., _RouteCfg(), seed)` — wrong arg types | ~line 245 | CRITICAL |
| `_RouteCfg` inner class duplicates `RepairRoutingConfig` | ~lines 228-240 | MEDIUM |
| No `.state` property on `GameEngine` | class definition | CRITICAL |
| `board._state = 'lost'` in `left_click/middle_click` bypasses encapsulation | ~lines 287-292 | MEDIUM |
| Python loop for neighbour count (O(H*W) Python calls) | `Board.__init__` ~lines 70-76 | MEDIUM |
| `Board._mine` numpy array accessed directly from engine (breaks Board boundary) | `left_click()` | LOW |
| Missing type hint: `GameEngine.restart()` has no return type | ~line 330 | LOW |
| Broad `except Exception` in `load_board_from_pipeline` | ~line 250 | LOW |
| `import sys as _sys` / `_backup = _sys.path.copy()` — sys.path mutation in library code | ~lines 175-178 | MEDIUM |
| Win condition doesn't check flag correctness | `Board.toggle_flag` / `Board.reveal` | MEDIUM |

### gameworks/main.py

| Issue | Location | Severity |
|---|---|---|
| `FPS` undefined — NameError on every run | ~line 237 | CRITICAL |
| `TILE` global referenced before assignment in `main()` | ~line 255 | HIGH |
| Double `handle_panel()` call | ~lines 155-175 | HIGH |
| `self._engine.state` — attribute doesn't exist | ~lines 203, 220 | CRITICAL |
| `Optional` not imported (used in `GameLoop` type hints) | line 78 | HIGH |
| `AnimationCascade` imported inline on every reveal action | `_do_left_click`, `_do_chord` | MEDIUM |
| `_save_npy()` iterates all cells via `snapshot()` instead of using arrays | ~lines 265-280 | MEDIUM |
| `GameLoop._build_engine()`: `a.diff` check uses `getattr` but `diff` is always in argparse namespace | ~line 105 | LOW |
| No input validation on `--board-w` / `--board-h` — 0 or negative accepted | `build_parser()` | MEDIUM |

### gameworks/renderer.py

| Issue | Location | Severity |
|---|---|---|
| `btn_w` NameError in `_draw_panel()` | ~line 945 | CRITICAL |
| `_fog` vs `self.fog` — fog feature broken | ~line 540 | HIGH |
| `_draw_bg()` dead code — never called | ~lines 570-585 | MEDIUM |
| Per-cell Surface allocation in `_draw_image_ghost()` | ~lines 820-855 | HIGH |
| No viewport culling in `_draw_loss_overlay()` | ~lines 815-835 | HIGH |
| `smoothscale()` called every frame in `_draw_win_animation_fx()` with same size | ~line 920 | HIGH |
| `handle_event()` and `handle_panel()` both called for same MOUSEBUTTONDOWN | ~lines 490-510 | HIGH |
| Emoji characters in `_draw_header()` (💣 ⏱) — only render if font supports them | ~line 595 | LOW |
| `_on_resize()` only updates panel buttons for bottom-panel layout, not right-panel | ~line 635 | MEDIUM |
| `pygame.display.Info()` called during `__init__` before any display is set | ~line 310 | MEDIUM |

## 2. Type Safety Issues

| Module | Issue |
|---|---|
| `gameworks/engine.py` | `Board._state: str` not annotated as `Literal["playing", "won", "lost"]` |
| `gameworks/engine.py` | `MoveResult.flagged` typed as `bool` but `toggle_flag` returns `str` |
| `gameworks/main.py` | `Optional` not imported; used in `GameLoop` field annotations |
| `gameworks/renderer.py` | `handle_event` return type `Optional[str]` but panel actions can be `None` |

## 3. Dead Code

| Location | Dead Code |
|---|---|
| `gameworks/renderer.py` ~lines 570-585 | `_draw_bg()` — never called |
| `gameworks/engine.py` end of file | `if __name__ == "_test_engine":` — unreachable guard |
| `run_iter9.py` ~lines 78-95 | 4+ commented-out tuning constant lines |
| `board_sizing.py` line ~10 | `#min_width: int = 300,  # Default value before testing` commented param |
| `archives/run_contrast_preprocessing_study.py.old` | Entire file archived |

## 4. Magic Numbers

| File | Magic Number | Context |
|---|---|---|
| `gameworks/renderer.py` line ~65 | `240`, `520` (PANEL_W, PANEL_H) | Should be named constants |
| `gameworks/renderer.py` line ~75 | `1400`, `850` (TARGET_SCREEN_*) | Could be derived from pygame display info |
| `gameworks/engine.py` ~line 337 | `0.15` (density) | Magic density constant in restart? |
| `sa.py` | `50000` (log_interval) | Embedded in JIT kernel |
| `solver.py` | `2400` (subset_cap) | Documented in docstring but magic in use |

## 5. Resource Leaks

| File | Issue |
|---|---|
| `gameworks/renderer.py` `_draw_image_ghost()` | Pygame surfaces created but never freed (CPython GC will eventually collect, but no explicit cleanup) |
| `gameworks/renderer.py` `_draw_win_animation_fx()` | `smoothscale()` creates new Surface every frame — not cached |

## 6. Async/Concurrency Issues

| File | Issue |
|---|---|
| `repair.py` | `ThreadPoolExecutor` used for parallel candidate evaluation — GIL-bound for CPU work; effectively serial for Python-dominated code |
| `gameworks/engine.py` `load_board_from_pipeline()` | Pipeline runs synchronously on game load, blocking Pygame event loop for minutes |

## 7. Import Issues

| File | Issue |
|---|---|
| `gameworks/main.py` | `Optional` used but not imported (from typing) |
| `gameworks/engine.py` | Dynamic `sys.path` manipulation at runtime inside game library |
| `gameworks/main.py` | `from .renderer import AnimationCascade` imported inline in action dispatchers — not at module level |
