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

from gameworks.engine import (
    Board,
    GameEngine,
    MoveResult,
    MINE_HIT_PENALTY,
    REVEAL_POINTS,
    WRONG_FLAG_PENALTY,
)


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
    eng.start()
    eng._first_click = False  # must be set after start() to avoid reset
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
# middle_click() — chord scoring, penalty, streak, win
# ---------------------------------------------------------------------------

class TestMiddleClick:
    """
    Covers GameEngine.middle_click() behaviour end-to-end.

    Board setup convention for all tests below:
      - mine at (0, 0) only
      - cell (1, 1) is revealed: neighbour_count = 1, adjacent to the mine
      - cell (0, 0) is flagged:  flag_count == mine_count → chord fires
    """

    # ── helper ────────────────────────────────────────────────────────────

    @staticmethod
    def _setup_chord_ready(w: int = 5, h: int = 5) -> GameEngine:
        """Return an engine with one mine at (0,0), (1,1) revealed, (0,0) flagged."""
        eng = GameEngine(mode="random", width=w, height=h, mines=1, seed=0)
        eng.board = Board(w, h, {(0, 0)})
        eng.start()
        eng._first_click = False
        eng.board.reveal(1, 1)          # reveal the clue cell
        eng.board.toggle_flag(0, 0)     # flag the mine → chord condition satisfied
        eng.streak = 0
        eng.score = 0
        return eng

    @staticmethod
    def _setup_chord_wrong_flag(w: int = 5, h: int = 5) -> GameEngine:
        """Return an engine where the flag is on a safe cell (wrong flag scenario)."""
        # mine at (0,0); flag placed on (2,0) which is NOT a mine
        eng = GameEngine(mode="random", width=w, height=h, mines=1, seed=0)
        eng.board = Board(w, h, {(0, 0)})
        eng.start()
        eng._first_click = False
        # reveal (1,0) which has neighbour_count=1 (adjacent to mine at 0,0)
        eng.board.reveal(1, 0)
        # flag a safe neighbour of (1,0) instead of the mine
        eng.board.toggle_flag(2, 0)
        eng.streak = 0
        eng.score = 0
        return eng

    # ── no-op cases ───────────────────────────────────────────────────────

    def test_middle_click_noop_returns_zero_score_delta(self):
        """Chord on cell with mismatched flag count must not change score."""
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        # Cell (4,4) is unrevealed — chord must be a no-op
        result = eng.middle_click(4, 4)
        assert result.score_delta == 0
        assert result.newly_revealed == []
        assert not result.hit_mine

    def test_middle_click_noop_leaves_streak_unchanged(self):
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        eng.streak = 7
        eng.middle_click(4, 4)    # unrevealed cell → no-op
        assert eng.streak == 7

    # ── safe chord ────────────────────────────────────────────────────────

    def test_middle_click_safe_chord_reveals_neighbours(self):
        eng = self._setup_chord_ready()
        result = eng.middle_click(1, 1)
        assert len(result.newly_revealed) > 0
        assert not result.hit_mine

    def test_middle_click_safe_chord_awards_points(self):
        """Each revealed cell earns REVEAL_POINTS[n] * streak_multiplier."""
        eng = self._setup_chord_ready()
        result = eng.middle_click(1, 1)
        assert result.score_delta > 0
        assert eng.score > 0

    def test_middle_click_safe_chord_increments_streak(self):
        """Streak must increment by 1 after a chord that reveals at least one cell."""
        eng = self._setup_chord_ready()
        eng.streak = 3
        eng.middle_click(1, 1)
        assert eng.streak == 4

    def test_middle_click_safe_chord_score_delta_matches_reveal_points(self):
        """
        Exact accounting: score_delta == sum of REVEAL_POINTS[n] * multiplier
        for every revealed cell, at streak=0 (1.0× multiplier).
        """
        eng = self._setup_chord_ready()
        result = eng.middle_click(1, 1)
        expected = sum(
            REVEAL_POINTS[int(eng.board._neighbours[ry, rx])]
            for rx, ry in result.newly_revealed
        )
        assert result.score_delta == expected

    # ── mine hit chord ────────────────────────────────────────────────────

    def test_middle_click_mine_hit_deducts_penalty(self):
        """Wrong-flag chord: MINE_HIT_PENALTY deducted, score floored at 0."""
        eng = self._setup_chord_wrong_flag()
        eng.score = 1000
        result = eng.middle_click(1, 0)    # chord on the clue cell
        assert result.hit_mine
        assert eng.score == 1000 - MINE_HIT_PENALTY

    def test_middle_click_mine_hit_resets_streak(self):
        eng = self._setup_chord_wrong_flag()
        eng.streak = 10
        eng.middle_click(1, 0)
        assert eng.streak == 0

    def test_middle_click_mine_hit_penalty_floored_at_zero(self):
        """Score must not go negative after mine hit."""
        eng = self._setup_chord_wrong_flag()
        eng.score = 0
        eng.middle_click(1, 0)
        assert eng.score >= 0

    def test_middle_click_mine_hit_populates_mine_flash(self):
        """mine_flash dict must contain the hit mine coord after a wrong-flag chord."""
        eng = self._setup_chord_wrong_flag()
        # The mine is at (0, 0) — it will be revealed by the wrong-flag chord
        eng.middle_click(1, 0)
        assert len(eng.mine_flash) > 0

    def test_middle_click_mine_hit_game_continues(self):
        """
        Mine hit via chord does NOT end the game — state remains 'playing'.
        This is consistent with direct left-click mine hit behaviour.
        """
        eng = self._setup_chord_wrong_flag()
        result = eng.middle_click(1, 0)
        assert result.state == "playing"

    # ── win via chord ─────────────────────────────────────────────────────

    def test_middle_click_triggers_win_when_last_cell_revealed(self):
        """Chording the last safe cell must transition state to 'won'."""
        # 3×1 board: mine at (2,0). Reveal clue (1,0). Flag mine (2,0). (0,0) unrevealed.
        # Chord (1,0): reveals (0,0) — last safe cell → win.
        eng = GameEngine(mode="random", width=3, height=1, mines=1, seed=0)
        eng.board = Board(3, 1, {(2, 0)})
        eng.start()
        eng._first_click = False
        eng.board.reveal(1, 0)
        eng.board.toggle_flag(2, 0)

        result = eng.middle_click(1, 0)   # chord reveals (0,0) — last safe cell
        assert result.state == "won" or eng.board._state == "won"


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
                    assert eng.score == 500 - WRONG_FLAG_PENALTY
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

    def test_correct_flag_increments_streak(self):
        """Placing a flag on a mine cell must increment streak (FA-020)."""
        eng = make_engine()
        mine_pos = next(iter(eng.board.all_mine_positions()))
        eng.streak = 0
        eng.right_click(*mine_pos)
        assert eng.streak == 1, \
            f"Correct flag did not increment streak: streak={eng.streak}"

    def test_wrong_flag_resets_streak(self):
        """Placing a flag on a safe cell must reset streak to 0 (FA-020)."""
        eng = make_engine()
        eng.streak = 5
        for y in range(9):
            for x in range(9):
                if not eng.board._mine[y, x]:
                    eng.right_click(x, y)
                    assert eng.streak == 0
                    return
        pytest.skip("No safe cell found")


# ---------------------------------------------------------------------------
# mine_flash
# ---------------------------------------------------------------------------

class TestMineFlash:

    def test_mine_flash_populated_on_hit(self):
        mines = {(2, 2)}
        eng = GameEngine(mode="random", width=9, height=9, mines=1, seed=0)
        eng.board = Board(9, 9, mines)
        eng.start()
        eng._first_click = False  # must be set after start() to avoid reset
        eng.left_click(2, 2)
        assert (2, 2) in eng.mine_flash

    def test_mine_flash_value_is_future_timestamp(self):
        mines = {(2, 2)}
        eng = GameEngine(mode="random", width=9, height=9, mines=1, seed=0)
        eng.board = Board(9, 9, mines)
        eng.start()
        eng._first_click = False  # must be set after start() to avoid reset
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
        eng.start()
        eng._first_click = False  # must be set after start() to avoid reset
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


# ---------------------------------------------------------------------------
# dev_solve_board()
# ---------------------------------------------------------------------------

class TestDevSolveBoard:

    def _make_solvable_engine(self) -> GameEngine:
        """Return a started engine with one mine that has NOT been triggered."""
        mines = {(0, 0)}
        eng = GameEngine(mode="random", width=5, height=5, mines=1, seed=0)
        eng.board = Board(5, 5, mines)
        eng._first_click = False
        eng.start()
        return eng

    def test_dev_solve_returns_move_result(self):
        eng = self._make_solvable_engine()
        result = eng.dev_solve_board()
        assert isinstance(result, MoveResult)

    def test_dev_solve_success_true_while_playing(self):
        eng = self._make_solvable_engine()
        result = eng.dev_solve_board()
        assert result.success is True

    def test_dev_solve_state_is_won(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.state == "won"

    def test_dev_solve_all_safe_cells_revealed(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.board.safe_revealed_count == eng.board.total_safe

    def test_dev_solve_all_mines_flagged(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.board.correct_flags == eng.board.total_mines

    def test_dev_solve_no_wrong_flags(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.board.wrong_flag_positions() == []

    def test_dev_solve_no_question_marks(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        assert eng.board.questioned_count == 0

    def test_dev_solve_score_delta_is_zero(self):
        eng = self._make_solvable_engine()
        result = eng.dev_solve_board()
        assert result.score_delta == 0

    def test_dev_solve_timer_stopped(self):
        import time
        eng = self._make_solvable_engine()
        eng.dev_solve_board()
        t0 = eng.elapsed
        time.sleep(0.05)
        assert eng.elapsed == t0

    def test_dev_solve_already_won_returns_success_false(self):
        eng = self._make_solvable_engine()
        eng.dev_solve_board()          # first call wins
        result = eng.dev_solve_board() # second call — already terminal
        assert result.success is False

    def test_dev_solve_clears_question_marks_set_before_call(self):
        eng = self._make_solvable_engine()
        eng.board.toggle_flag(2, 2)    # → flag
        eng.board.toggle_flag(2, 2)    # → question
        assert eng.board.questioned_count == 1
        eng.dev_solve_board()
        assert eng.board.questioned_count == 0


# ---------------------------------------------------------------------------
# restart() — npy and image mode variants (GWHARDEN-014)
# ---------------------------------------------------------------------------

class TestRestartModes:

    def test_restart_npy_mode_preserves_mine_count(self, tmp_path):
        import numpy as np
        grid = np.zeros((5, 5), dtype=np.int8)
        grid[0, 0] = 1
        grid[4, 4] = 1
        npy_file = str(tmp_path / "board.npy")
        np.save(npy_file, grid)

        eng = GameEngine(mode="npy", npy_path=npy_file, seed=1)
        eng.start()
        mines_before = eng.board.total_mines
        eng.restart()
        assert eng.board.total_mines == mines_before

    def test_restart_image_mode_produces_playable_board(self):
        eng = GameEngine(mode="image", image_path="/nonexistent/img.png",
                         width=9, height=9, seed=1)
        eng.start()
        eng.restart()
        assert eng.state == "playing"
        assert eng.board.total_mines >= 1


class TestFirstClickSafety:

    def test_first_click_mine_count_preserved_on_tiny_board(self):
        """On a tiny board where the safe zone covers all cells, mine count must not drop (FA-018)."""
        eng = GameEngine(mode="random", width=3, height=3, mines=8, seed=0)
        eng.start()
        eng._first_click = True
        # Place a single mine at the click target to trigger regen
        eng.board = Board(3, 3, {(1, 1)})
        result = eng.left_click(1, 1)
        assert eng.board.total_mines == 1, \
            f"Mine count changed after first-click regen: {eng.board.total_mines}"
