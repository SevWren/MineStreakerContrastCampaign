# PHASE 07 — Testing Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. Current Test Coverage

### Pipeline Tests (tests/) — WELL COVERED
| Test File | What It Tests |
|---|---|
| `test_benchmark_layout.py` | Benchmark output directory structure |
| `test_image_guard_contract.py` | Image integrity verification |
| `test_iter9_image_sweep_contract.py` | Image sweep CLI contract |
| `test_repair_result_dataclasses.py` | Repair result dataclass fields |
| `test_repair_route_decision.py` | Repair routing decisions |
| `test_repair_visual_delta.py` | Visual delta computation |
| `test_report_explanations.py` | Report label text contract |
| `test_route_artifact_metadata.py` | Route artifact JSON fields |
| `test_solver_failure_taxonomy.py` | Solver failure classification |
| `test_source_config.py` | SourceImageConfig resolution |
| `test_source_image_cli_contract.py` | CLI contract for image input |

### Demo Tests (tests/demo/iter9_visual_solver/) — WELL COVERED
30+ test files covering all demos subsystems with builders, fixtures, and contract tests.

### gameworks/ Tests — ZERO
**No test files for gameworks/engine.py, gameworks/renderer.py, or gameworks/main.py.**

## 2. Coverage Gaps

### gameworks/engine.py — Critical Untested Areas
- `Board.__init__` neighbour calculation
- `Board.reveal()` flood-fill correctness
- `Board.reveal()` win/loss state transitions
- `Board.toggle_flag()` cycle behavior
- `Board.chord()` edge cases
- `Board.snapshot()` accuracy
- `Board.all_mine_positions()` and `wrong_flag_positions()`
- `place_random_mines()` distribution and exclusion zone
- `load_board_from_npy()` validation logic
- `GameEngine.left_click()` first-click safety
- `GameEngine.right_click()` MoveResult correctness
- `GameEngine.middle_click()` chord result
- `GameEngine.restart()` mode preservation (BUG)
- `GameEngine.elapsed` timer behavior
- `GameEngine.from_difficulty()` presets

### gameworks/renderer.py — Critical Untested Areas
- `AnimationCascade.current()` timing
- `AnimationCascade.done` condition
- `WinAnimation` phase transitions
- `Renderer` initialization without pygame display (headless)
- Event handling and action string returns
- `_fog` vs `self.fog` attribute (would catch FIND-RENDER-HIGH-h002a)

### gameworks/main.py — Critical Untested Areas
- `build_parser()` argument validation
- `GameLoop._build_engine()` mode dispatch
- `_do_left_click()` / `_do_right_click()` / `_do_chord()` dispatchers
- `_save_npy()` output correctness

## 3. Missing Test Types

### Missing: Regression Tests for Critical Bugs
All 5 critical bugs identified in this audit have no regression tests. Any fix must add:
- `test_engine_state_property_exists()`
- `test_fps_constant_importable_from_renderer()`
- `test_compile_sa_kernel_no_args()`
- `test_run_phase1_repair_correct_signature()`
- `test_btn_w_not_a_free_variable()`

### Missing: Board Correctness Tests
- Flood-fill coverage: 0-cell reveals cascade correctly
- Mine count: total mines == len(mine_positions)
- Neighbour count: each cell has correct count for known layouts
- Win detection: all safe revealed → won
- Loss detection: mine revealed → lost

### Missing: Save/Load Round-Trip
```python
def test_save_load_roundtrip():
    mines = place_random_mines(9, 9, 10, seed=42)
    board = Board(9, 9, mines)
    # Save via _save_npy (mocked to in-memory)
    # Load via load_board_from_npy
    # Assert mine positions and neighbour counts identical
```

### Missing: Determinism Tests
```python
def test_random_board_deterministic():
    m1 = place_random_mines(16, 16, 40, seed=42)
    m2 = place_random_mines(16, 16, 40, seed=42)
    assert m1 == m2
```

## 4. Generated Tests (see generated-tests.md for full implementations)

### Priority Test List
1. `test_gameworks_engine_state_property` — catches FIND-ARCH-CRITICAL-f002a
2. `test_fps_available_in_main_namespace` — catches FIND-ARCH-CRITICAL-f001a
3. `test_board_reveal_flood_fill` — correctness
4. `test_board_win_condition` — state correctness
5. `test_board_loss_condition` — state correctness
6. `test_board_toggle_flag_cycle` — toggle_flag semantics
7. `test_board_chord` — chording correctness
8. `test_first_click_safety` — first click never mine
9. `test_board_neighbour_counts` — grid accuracy
10. `test_place_random_mines_exclusion` — safe zone respected
11. `test_animation_cascade_timing` — animation timing
12. `test_fog_attribute_name` — catches FIND-RENDER-HIGH-h002a
13. `test_draw_panel_btn_w_accessible` — catches FIND-ARCH-CRITICAL-f005a
14. `test_compile_sa_kernel_signature` — catches FIND-ARCH-CRITICAL-f003a
15. `test_run_phase1_repair_signature` — catches FIND-ARCH-CRITICAL-f004a

## 5. Test Framework Recommendations

### pytest (recommended)
```toml
# pyproject.toml [tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v --tb=short"
```

### Headless Pygame Testing
```python
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
pygame.init()
```

### Builder Pattern (for engine tests)
```python
class BoardBuilder:
    def __init__(self, w=9, h=9):
        self._w = w; self._h = h; self._mines = set()
    def with_mine(self, x, y): self._mines.add((x,y)); return self
    def build(self): return Board(self._w, self._h, self._mines)
```
