"""
gameworks/tests/unit/test_engine.py

Unit tests for gameworks.engine.GameEngine.

Covers:
- Lifecycle: start(), stop_timer(), elapsed, state
- First-click safety: board regenerated when first click lands on mine
- Player actions: left_click, right_click, middle_click return MoveResult
- Scoring: reveal points, flag bonus/penalty, mine hit penalty, score floor
- Streak: increments on safe reveal, resets on mine hit / flag action
- restart(): preserves mode, increments seed, resets score/streak
- from_difficulty(): Easy/Medium/Hard preset dimensions
- mine_flash: populated on mine hit, keyed by (x, y)
"""

from __future__ import annotations

import time

import pytest

from gameworks.engine import Board, GameEngine, MoveResult, place_random_mines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_engine(w=9, h=9, mines=10, seed=42) -> GameEngine:
    eng = GameEngine(mode="random", width=w, height=h, mines=mines, seed=seed)
    eng.start()
    return eng


def engine_with_mine_at(x: int, y: int, w: int = 9, h: int = 9) -> GameEngine:
    """Return a started engine whose board has a mine at (x, y) and nowhere else."""
    mines = {(x, y)}
    eng = GameEngine(mode="random", width=w, height=h, mines=1, seed=0)
    eng.board = Board(w, h, mines)
    eng._first_click = False
    eng.start()
    return eng


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

class TestLifecycle:

    def test_start_initialises_timer(self):
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        assert eng.elapsed >= 0.0

    def test_elapsed_grows_after_start(self):
        eng = make_engine()
        t0 = eng.elapsed
        time.sleep(0.05)
        assert eng.elapsed > t0

    def test_stop_timer_freezes_elapsed(self):
        eng = make_engine()
        eng.stop_timer()
        t0 = eng.elapsed
        time.sleep(0.05)
        assert eng.elapsed == t0

    def test_state_initially_playing(self):
        eng = make_engine()
        assert eng.state == "playing"

    def test_state_property_mirrors_board_state(self):
        eng = make_engine()
        assert eng.state == eng.board._state

    def test_score_initially_zero(self):
        eng = make_engine()
        assert eng.score == 0

    def test_streak_initially_zero(self):
        eng = make_engine()
        assert eng.streak == 0

    def test_mine_flash_initially_empty(self):
        eng = make_engine()
        assert eng.mine_flash == {}


# ---------------------------------------------------------------------------
# First-click safety
# ---------------------------------------------------------------------------

class TestFirstClickSafety:

    def test_first_click_never_hits_mine(self):
        """Board must be regenerated so the first click is always safe."""
        for seed in range(30):
            eng = GameEngine(mode="random", width=9, height=9, mines=70, seed=seed)
            eng.start()
            result = eng.left_click(4, 4)
            assert not result.hit_mine, f"First click hit mine with seed={seed}"

    def test_second_click_can_hit_mine(self):
        """After first click, no board regeneration protection applies."""
        eng = make_engine()
        eng.left_click(4, 4)   # first click — safe
        # subsequent clicks are not protected (may or may not hit a mine)
        result = eng.left_click(4, 4)
        assert isinstance(result, MoveResult)   # just assert it returns a result


# ---------------------------------------------------------------------------
# Player actions return MoveResult
# ---------------------------------------------------------------------------

class TestMoveResultReturns:

    def test_left_click_returns_move_result(self):
        eng = make_engine()
        result = eng.left_click(4, 4)
        assert isinstance(result, MoveResult)

    def test_right_click_returns_move_result(self):
        eng = make_engine()
        result = eng.right_click(0, 0)
        assert isinstance(result, MoveResult)

    def test_middle_click_returns_move_result(self):
        eng = make_engine()
        result = eng.middle_click(4, 4)
        assert isinstance(result, MoveResult)

    def test_move_result_has_state_field(self):
        eng = make_engine()
        result = eng.left_click(4, 4)
        assert result.state in ("playing", "won")

    def test_move_result_streak_field(self):
        eng = make_engine()
        result = eng.left_click(4, 4)
        assert isinstance(result.streak, int)
        assert result.streak >= 0

    def test_move_result_score_delta_type(self):
        eng = make_engine()
        result = eng.left_click(4, 4)
        assert isinstance(result.score_delta, int)


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

class TestScoring:

    def test_safe_reveal_increases_score(self):
        eng = make_engine()
        eng.left_click(4, 4)
        assert eng.score > 0

    def test_score_floor_never_negative(self):
        """Score must be clamped to 0 — never go negative."""
        eng = make_engine()
        eng.score = 0
        # Force a mine-hit penalty
        mines = {(3, 3)}
        eng.board = Board(9, 9, mines)
        eng._first_click = False
        eng.left_click(3, 3)
        assert eng.score >= 0

    def test_mine_hit_deducts_penalty(self):
        eng = make_engine()
        eng.score = 1000
        mines = {(1, 1)}
        eng.board = Board(9, 9, mines)
        eng._first_click = False
        eng.left_click(1, 1)
        assert eng.score < 1000

    def test_correct_flag_increases_score(self):
        eng = make_engine()
        eng.score = 0
        # Find a mine position
        mine_pos = next(iter(eng.board.all_mine_positions()))
        eng.right_click(*mine_pos)
        assert eng.score > 0

    def test_wrong_flag_deducts_score(self):
        eng = make_engine()
        eng.score = 500
        # Flag a non-mine cell — find one
        for y in range(9):
            for x in range(9):
                if not eng.board._mine[y, x]:
                    eng.right_click(x, y)
                    assert eng.score <= 500
                    return
        pytest.skip("No safe cell found")


# ---------------------------------------------------------------------------
# Streak
# ---------------------------------------------------------------------------

class TestStreak:

    def test_streak_increments_on_safe_reveal(self):
        eng = make_engine()
        eng.left_click(4, 4)
        assert eng.streak > 0

    def test_streak_resets_on_mine_hit(self):
        eng = make_engine()
        eng.left_click(4, 4)   # build some streak
        mines = {(0, 0)}
        eng.board = Board(9, 9, mines)
        eng._first_click = False
        eng.left_click(0, 0)   # hit mine
        assert eng.streak == 0

    def test_streak_multiplier_at_zero_is_1x(self):
        eng = make_engine()
        assert eng.streak_multiplier == 1.0

    def test_streak_multiplier_increases_with_streak(self):
        eng = make_engine()
        eng.streak = 5
        assert eng.streak_multiplier >= 1.5

    def test_streak_multiplier_tiers(self):
        eng = make_engine()
        cases = [(0, 1.0), (4, 1.0), (5, 1.5), (10, 2.0), (15, 3.0), (25, 5.0)]
        for streak, expected in cases:
            eng.streak = streak
            assert eng.streak_multiplier == expected, \
                f"streak={streak}: expected {expected}×, got {eng.streak_multiplier}×"


# ---------------------------------------------------------------------------
# mine_flash
# ---------------------------------------------------------------------------

class TestMineFlash:

    def test_mine_flash_populated_on_hit(self):
        mines = {(2, 2)}
        eng = GameEngine(mode="random", width=9, height=9, mines=1, seed=0)
        eng.board = Board(9, 9, mines)
        eng._first_click = False
        eng.start()
        eng.left_click(2, 2)
        assert (2, 2) in eng.mine_flash

    def test_mine_flash_value_is_future_timestamp(self):
        mines = {(2, 2)}
        eng = GameEngine(mode="random", width=9, height=9, mines=1, seed=0)
        eng.board = Board(9, 9, mines)
        eng._first_click = False
        eng.start()
        eng.left_click(2, 2)
        expiry = eng.mine_flash[(2, 2)]
        assert expiry > time.monotonic()


# ---------------------------------------------------------------------------
# restart()
# ---------------------------------------------------------------------------

class TestRestart:

    def test_restart_resets_score(self):
        eng = make_engine()
        eng.left_click(4, 4)
        assert eng.score > 0
        eng.restart()
        assert eng.score == 0

    def test_restart_resets_streak(self):
        eng = make_engine()
        eng.left_click(4, 4)
        eng.restart()
        assert eng.streak == 0

    def test_restart_state_is_playing(self):
        eng = make_engine()
        eng.restart()
        assert eng.state == "playing"

    def test_restart_increments_seed(self):
        eng = make_engine(seed=10)
        eng.restart()
        assert eng.seed == 11

    def test_restart_preserves_mode(self):
        eng = make_engine()
        mode = eng.mode
        eng.restart()
        assert eng.mode == mode

    def test_restart_clears_mine_flash(self):
        mines = {(2, 2)}
        eng = GameEngine(mode="random", width=9, height=9, mines=1, seed=0)
        eng.board = Board(9, 9, mines)
        eng._first_click = False
        eng.start()
        eng.left_click(2, 2)
        assert len(eng.mine_flash) > 0
        eng.restart()
        assert eng.mine_flash == {}


# ---------------------------------------------------------------------------
# from_difficulty()
# ---------------------------------------------------------------------------

class TestFromDifficulty:

    def test_easy_preset(self):
        eng = GameEngine.from_difficulty("easy")
        assert eng.board.width == 9
        assert eng.board.height == 9
        assert eng.board.total_mines == 10

    def test_medium_preset(self):
        eng = GameEngine.from_difficulty("medium")
        assert eng.board.width == 16
        assert eng.board.height == 16
        assert eng.board.total_mines == 40

    def test_hard_preset(self):
        eng = GameEngine.from_difficulty("hard")
        assert eng.board.width == 30
        assert eng.board.height == 16
        assert eng.board.total_mines == 99

    def test_invalid_difficulty_raises(self):
        with pytest.raises((KeyError, ValueError)):
            GameEngine.from_difficulty("impossible")
