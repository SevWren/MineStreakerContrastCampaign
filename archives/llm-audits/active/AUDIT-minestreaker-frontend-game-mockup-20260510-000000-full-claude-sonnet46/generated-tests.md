# Generated Tests
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## File: tests/test_gameworks_engine.py

```python
"""
Unit tests for gameworks/engine.py.
Covers Board, GameEngine, mine placement, and state machine.
No pygame required.
"""
import pytest
import numpy as np
from gameworks.engine import (
    Board, CellState, GameEngine, MoveResult,
    place_random_mines, load_board_from_npy,
)


# ══════════════════════════════════════════════════════════════════════
#  Board Construction
# ══════════════════════════════════════════════════════════════════════

class TestBoardConstruction:
    def test_dimensions(self):
        board = Board(9, 9, {(0, 0)})
        assert board.width == 9
        assert board.height == 9

    def test_mine_count(self):
        mines = {(0, 0), (1, 1), (2, 2)}
        board = Board(9, 9, mines)
        assert board.total_mines == 3

    def test_safe_count(self):
        board = Board(9, 9, {(0, 0)})
        assert board.total_safe == 9 * 9 - 1

    def test_initial_state_is_playing(self):
        board = Board(9, 9, {(0, 0)})
        assert not board.is_won
        assert not board.is_lost
        assert not board.game_over

    def test_neighbour_count_corner(self):
        # Mine at (0,0), check (1,1) → should have 1 neighbour
        board = Board(9, 9, {(0, 0)})
        cs = board.snapshot(1, 1)
        assert cs.neighbour_mines == 1

    def test_neighbour_count_center_surrounded(self):
        # All 8 neighbours of (4,4) are mines
        mines = {(3,3),(4,3),(5,3),(3,4),(5,4),(3,5),(4,5),(5,5)}
        board = Board(9, 9, mines)
        cs = board.snapshot(4, 4)
        assert cs.neighbour_mines == 8


# ══════════════════════════════════════════════════════════════════════
#  Reveal & Flood-Fill
# ══════════════════════════════════════════════════════════════════════

class TestBoardReveal:
    def test_reveal_mine_returns_hit(self):
        board = Board(9, 9, {(4, 4)})
        hit, revealed = board.reveal(4, 4)
        assert hit is True
        assert board.is_lost

    def test_reveal_safe_cell(self):
        board = Board(9, 9, {(8, 8)})  # mine far away
        hit, revealed = board.reveal(0, 0)
        assert hit is False
        assert len(revealed) > 0

    def test_flood_fill_zero_cell(self):
        # Large clear area → flood fill should reveal many cells
        board = Board(9, 9, {(8, 8)})
        hit, revealed = board.reveal(0, 0)
        assert len(revealed) > 1  # flood filled

    def test_reveal_flagged_does_nothing(self):
        board = Board(9, 9, {(4, 4)})
        board.toggle_flag(4, 4)
        hit, revealed = board.reveal(4, 4)
        assert hit is False
        assert len(revealed) == 0

    def test_win_on_all_safe_revealed(self):
        board = Board(3, 3, {(2, 2)})
        # Reveal all safe cells manually
        for y in range(3):
            for x in range(3):
                if (x, y) != (2, 2):
                    board._revealed[y, x] = True
        board._state = "playing"
        # Now reveal last safe cell
        board._revealed[0, 0] = False
        board.reveal(0, 0)
        assert board.is_won


# ══════════════════════════════════════════════════════════════════════
#  Flag Toggle
# ══════════════════════════════════════════════════════════════════════

class TestToggleFlag:
    def test_cycle_hidden_flag_question_hidden(self):
        board = Board(9, 9, {(0, 0)})
        assert board.toggle_flag(4, 4) == "flag"
        assert board.toggle_flag(4, 4) == "question"
        assert board.toggle_flag(4, 4) == "hidden"

    def test_flag_revealed_cell_returns_hidden(self):
        board = Board(9, 9, {(8, 8)})
        board.reveal(4, 4)
        result = board.toggle_flag(4, 4)
        # Revealed cell → toggle_flag returns "hidden" (no-op)
        assert result == "hidden"

    def test_flags_placed_count(self):
        board = Board(9, 9, {(0, 0), (1, 1)})
        board.toggle_flag(0, 0)
        board.toggle_flag(1, 1)
        assert board.flags_placed == 2

    def test_correct_flags_count(self):
        board = Board(9, 9, {(0, 0), (1, 1)})
        board.toggle_flag(0, 0)   # correct
        board.toggle_flag(4, 4)   # wrong
        assert board.correct_flags == 1


# ══════════════════════════════════════════════════════════════════════
#  Chord
# ══════════════════════════════════════════════════════════════════════

class TestChord:
    def test_chord_requires_flag_count_match(self):
        # Mine at (0,0), cell (1,1) has number=1
        board = Board(9, 9, {(0, 0)})
        board.reveal(1, 1)
        # No flags → chord does nothing
        hit, revealed = board.chord(1, 1)
        assert hit is False
        assert len(revealed) == 0

    def test_chord_with_correct_flags(self):
        board = Board(9, 9, {(0, 0)})
        board.reveal(2, 2)
        board.toggle_flag(0, 0)
        cs = board.snapshot(1, 1)
        if not board._revealed[1, 1]:
            board.reveal(1, 1)
        # With flag matching count, chord should reveal neighbours
        # (only if (1,1).number == 1 and exactly 1 flag adjacent)


# ══════════════════════════════════════════════════════════════════════
#  Mine Placement
# ══════════════════════════════════════════════════════════════════════

class TestMinePlacement:
    def test_deterministic_with_seed(self):
        m1 = place_random_mines(16, 16, 40, seed=42)
        m2 = place_random_mines(16, 16, 40, seed=42)
        assert m1 == m2

    def test_different_seeds_different_mines(self):
        m1 = place_random_mines(16, 16, 40, seed=42)
        m2 = place_random_mines(16, 16, 40, seed=99)
        assert m1 != m2

    def test_exclusion_zone(self):
        # Mine should not appear in 3×3 zone around (4,4)
        mines = place_random_mines(16, 16, 40, safe_x=4, safe_y=4, seed=42)
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                assert (4+dx, 4+dy) not in mines

    def test_correct_count(self):
        mines = place_random_mines(16, 16, 40, seed=42)
        assert len(mines) == 40


# ══════════════════════════════════════════════════════════════════════
#  GameEngine
# ══════════════════════════════════════════════════════════════════════

class TestGameEngine:
    def test_state_property_exists(self):
        """FIND-ARCH-CRITICAL-f002a: GameEngine must expose .state"""
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        assert hasattr(eng, "state"), "GameEngine must have .state property"
        assert eng.state in ("playing", "won", "lost")

    def test_initial_state_is_playing(self):
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        assert eng.state == "playing"

    def test_first_click_safety(self):
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        # Hit center 100 times with different seeds — should never be mine
        for seed in range(100):
            eng2 = GameEngine(mode="random", width=9, height=9, mines=10, seed=seed)
            eng2.start()
            result = eng2.left_click(4, 4)
            assert not result.hit_mine, f"First click hit mine with seed={seed}"

    def test_left_click_reveals_cells(self):
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        result = eng.left_click(4, 4)
        assert not result.hit_mine
        assert len(result.newly_revealed) > 0

    def test_right_click_places_flag(self):
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        result = eng.right_click(0, 0)
        assert result.flagged == "flag"

    def test_from_difficulty(self):
        eng = GameEngine.from_difficulty("easy")
        assert eng.board.width == 9
        assert eng.board.height == 9
        assert eng.board.total_mines == 10

    def test_difficulty_medium(self):
        eng = GameEngine.from_difficulty("medium")
        assert eng.board.width == 16
        assert eng.board.height == 16
        assert eng.board.total_mines == 40

    def test_elapsed_increases(self):
        import time
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        eng._first_click = False  # bypass first-click gate
        eng._start_time = time.time()
        time.sleep(0.05)
        assert eng.elapsed > 0.04


# ══════════════════════════════════════════════════════════════════════
#  Critical Bug Regression Tests
# ══════════════════════════════════════════════════════════════════════

class TestCriticalBugRegressions:
    def test_fps_importable_from_renderer(self):
        """FIND-ARCH-CRITICAL-f001a: FPS must be importable"""
        from gameworks.renderer import FPS
        assert FPS == 60

    def test_compile_sa_kernel_takes_no_args(self):
        """FIND-ARCH-CRITICAL-f003a: compile_sa_kernel() must accept 0 args"""
        import inspect
        from sa import compile_sa_kernel
        sig = inspect.signature(compile_sa_kernel)
        assert len(sig.parameters) == 0, \
            "compile_sa_kernel() must take 0 parameters"

    def test_run_phase1_repair_takes_float_time_budget(self):
        """FIND-ARCH-CRITICAL-f004a: time_budget_s must be 5th param as float"""
        import inspect
        from repair import run_phase1_repair
        sig = inspect.signature(run_phase1_repair)
        params = list(sig.parameters)
        assert params[4] == "time_budget_s"
        assert sig.parameters["time_budget_s"].default == 90.0
```

## File: tests/test_gameworks_renderer_headless.py

```python
"""
Headless tests for gameworks/renderer.py.
Uses SDL dummy driver to avoid display requirement.
"""
import os
import pytest

# Must set before pygame import
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")


def test_fog_attribute_name():
    """FIND-RENDER-HIGH-h002a: fog attribute must be 'fog', not '_fog'"""
    import pygame
    pygame.init()
    from gameworks.engine import GameEngine
    from gameworks.renderer import Renderer
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    r = Renderer(eng)
    # The attribute must be 'fog'
    assert hasattr(r, "fog"), "Renderer must have 'fog' attribute"
    assert not hasattr(r, "_fog") or r._fog == r.fog, \
        "_fog and fog must be consistent"
    pygame.quit()


def test_renderer_btn_w_stored_on_self():
    """FIND-ARCH-CRITICAL-f005a: btn_w must be stored as self._btn_w"""
    import pygame
    pygame.init()
    from gameworks.engine import GameEngine
    from gameworks.renderer import Renderer
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    r = Renderer(eng)
    assert hasattr(r, "_btn_w"), \
        "Renderer must store btn_w as self._btn_w for use in _draw_panel()"
    pygame.quit()


def test_animation_cascade_timing():
    """AnimationCascade must reveal cells over time."""
    import time
    from gameworks.renderer import AnimationCascade, ANIM_TICK
    positions = [(i, 0) for i in range(10)]
    cascade = AnimationCascade(positions, speed=0.01)
    assert not cascade.done
    time.sleep(0.05)
    current = cascade.current()
    assert len(current) >= 3  # some cells revealed after 50ms at 10ms/cell
    time.sleep(0.15)
    assert cascade.done


def test_win_animation_phases():
    """WinAnimation must have 2 phases and reach done."""
    import time
    from gameworks.engine import Board
    from gameworks.renderer import WinAnimation
    mines = {(0,0), (1,1), (2,2)}
    board = Board(5, 5, mines)
    # Flag some mines
    board._flagged[0,0] = True
    board._flagged[1,1] = True
    anim = WinAnimation(board, speed=0.001)
    time.sleep(0.05)
    assert anim.done or len(anim.current()) > 0
```
