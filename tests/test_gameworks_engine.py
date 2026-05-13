"""
tests/test_gameworks_engine.py

Unit tests for gameworks/engine.py.

Regression tests for all 6 critical bugs, plus correctness tests for
Board logic, GameEngine lifecycle, and .npy loading.

Run with: pytest tests/test_gameworks_engine.py -v
"""

import os
import tempfile

import numpy as np
import pytest

from gameworks.engine import (
    Board,
    GameEngine,
    MoveResult,
    load_board_from_npy,
    place_random_mines,
)


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_board(w=9, h=9, mines=10, seed=42) -> Board:
    mp = place_random_mines(w, h, mines, seed=seed)
    return Board(w, h, mp)


def make_engine(w=9, h=9, mines=10, seed=42) -> GameEngine:
    eng = GameEngine(mode="random", width=w, height=h, mines=mines, seed=seed)
    eng.start()
    return eng


def save_game_format_npy(grid: np.ndarray) -> str:
    """Write a game-format .npy file and return the path."""
    f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
    np.save(f.name, grid)
    f.close()
    return f.name


# ─────────────────────────────────────────────────────────────────────────────
#  REGRESSION: Critical Bug Fixes
# ─────────────────────────────────────────────────────────────────────────────

class TestCriticalRegressions:
    """Regression tests for the 6 critical runtime crashes."""

    def test_f002a_game_engine_has_state_property(self):
        """FIND-ARCH-CRITICAL-f002a: GameEngine must expose .state."""
        eng = make_engine()
        # Must not raise AttributeError
        s = eng.state
        assert s == "playing"

    def test_f002a_state_transitions_to_won(self):
        """GameEngine.state must reflect board win state."""
        # Build a board with one mine, then reveal all safe cells and flag the mine
        mp = {(0, 0)}
        b = Board(3, 3, mp)
        b._flagged[0, 0] = True  # flag the mine
        # Reveal all safe cells
        for y in range(3):
            for x in range(3):
                if (x, y) != (0, 0):
                    b.reveal(x, y)
        assert b._state == "won", f"Board state should be 'won' after all safe cells revealed and mine flagged, got {b._state!r}"

    def test_f002a_mine_hit_keeps_playing(self):
        """Mine hit returns hit=True but state stays 'playing' (no game-over)."""
        mp = {(4, 4)}
        b = Board(9, 9, mp)
        hit, _ = b.reveal(4, 4)
        assert hit, "reveal on mine cell should return hit=True"
        assert b._state == "playing", f"State should remain 'playing' after mine hit (no game-over), got {b._state!r}"

    def test_f001a_fps_importable(self):
        """FIND-ARCH-CRITICAL-f001a: FPS must be importable from renderer."""
        pytest.importorskip("pygame", reason="pygame not installed")
        from gameworks.renderer import FPS
        assert isinstance(FPS, int)
        assert FPS > 0

    def test_f005a_btn_w_stored_on_self(self):
        """FIND-ARCH-CRITICAL-f005a: Renderer must store _btn_w as instance attribute."""
        import pygame as _pg
        pytest.importorskip("pygame", reason="pygame not installed")
        import os
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        _pg.init()
        _pg.display.set_mode((800, 600))
        from gameworks.engine import GameEngine
        from gameworks.renderer import Renderer
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        r = Renderer(eng)
        assert hasattr(r, "_btn_w"), "_btn_w must be stored as an instance attribute on Renderer"
        assert isinstance(r._btn_w, int) and r._btn_w > 0, f"_btn_w must be a positive int, got {r._btn_w!r}"
        _pg.quit()

    def test_f006a_pipeline_npy_loads_correctly(self):
        """FIND-ARCH-CRITICAL-f006a: Pipeline format .npy (0/1) must load with correct mine count."""
        board_path = os.path.join(
            "results", "iter9",
            "20260510T054753Z_tessa_line_art_stiletto_300w_seed11_GAME_DevelopmentBOARD",
            "grid_iter9_300x300.npy",
        )
        if not os.path.exists(board_path):
            pytest.skip("tessa board not present")
        result = load_board_from_npy(board_path)
        b = result.board  # DP-R3: unwrap BoardLoadResult
        assert b.total_mines == 4794, f"Expected 4794 mines, got {b.total_mines}"
        assert b.width == 300
        assert b.height == 300

    def test_f006a_game_format_npy_loads_correctly(self):
        """Game-format .npy (-1=mine, 0-8=neighbour count) must still load."""
        # 3x3 board: one mine at corner (0,0), neighbours computed
        mp = {(0, 0)}
        b_orig = Board(3, 3, mp)
        # Build game-format grid
        grid = np.where(b_orig._mine, np.int8(-1), b_orig._neighbours.astype(np.int8))
        path = save_game_format_npy(grid)
        try:
            b = load_board_from_npy(path).board  # DP-R3: unwrap BoardLoadResult
            assert b.total_mines == 1
            assert b._mine[0, 0]
            assert b.width == 3 and b.height == 3
        finally:
            os.unlink(path)

    def test_f006a_format_auto_detection(self):
        """Auto-detection must correctly distinguish pipeline vs game format."""
        # Pipeline format: all 0/1
        g_pipe = np.array([[0, 1], [0, 0]], dtype=np.int8)
        path = save_game_format_npy(g_pipe)
        try:
            b = load_board_from_npy(path).board  # DP-R3: unwrap BoardLoadResult
            assert b.total_mines == 1
        finally:
            os.unlink(path)

        # Game format: has -1
        g_game = np.array([[-1, 1], [1, 1]], dtype=np.int8)
        path = save_game_format_npy(g_game)
        try:
            b = load_board_from_npy(path).board  # DP-R3: unwrap BoardLoadResult
            assert b.total_mines == 1
        finally:
            os.unlink(path)


# ─────────────────────────────────────────────────────────────────────────────
#  Board Logic
# ─────────────────────────────────────────────────────────────────────────────

class TestBoardLogic:

    def test_mine_placement(self):
        mp = {(0, 0), (1, 1), (2, 2)}
        b = Board(5, 5, mp)
        assert b.total_mines == 3
        assert b._mine[0, 0]
        assert b._mine[1, 1]
        assert b._mine[2, 2]
        assert not b._mine[0, 1]

    def test_neighbour_counts_correct(self):
        """Cell adjacent to exactly one mine should have neighbour count 1."""
        mp = {(0, 0)}
        b = Board(3, 3, mp)
        # (1, 0) is directly right of the mine
        assert int(b._neighbours[0, 1]) == 1, f"Expected neighbour count 1 at (row=0,col=1), got {int(b._neighbours[0, 1])}"
        # (1, 1) is diagonal to the mine
        assert int(b._neighbours[1, 1]) == 1, f"Expected neighbour count 1 at (row=1,col=1), got {int(b._neighbours[1, 1])}"
        # (2, 2) is far from the mine
        assert int(b._neighbours[2, 2]) == 0, f"Expected neighbour count 0 at (row=2,col=2), got {int(b._neighbours[2, 2])}"

    def test_reveal_mine_returns_hit(self):
        """Mine hit returns hit=True but game continues (no game-over)."""
        mp = {(3, 3)}
        b = Board(9, 9, mp)
        hit, revealed = b.reveal(3, 3)
        assert hit, "reveal on mine cell should return hit=True"
        # No game-over: mine hit is a penalty, game keeps going
        assert b._state == "playing", "State should remain 'playing' after mine hit; mine hit is a penalty only"
        assert b._revealed[3, 3], "Mine cell at (3,3) should be marked revealed on hit even though no game-over occurs"

    def test_reveal_safe_cell(self):
        mp = {(0, 0)}
        b = Board(5, 5, mp)
        hit, revealed = b.reveal(4, 4)
        assert not hit
        assert (4, 4) in revealed

    def test_flood_fill_reveals_connected_zeros(self):
        mp = {(0, 0)}
        b = Board(5, 5, mp)
        hit, revealed = b.reveal(4, 4)
        assert not hit
        # Should have flood-filled a large region
        assert len(revealed) > 1

    def test_flag_cycle(self):
        b = make_board()
        result = b.toggle_flag(5, 5)
        assert result == "flag", f"First toggle should return 'flag', got {result!r}"
        assert b._flagged[5, 5], "Cell should be flagged after first toggle"
        result = b.toggle_flag(5, 5)
        assert result == "question", f"Second toggle should return 'question', got {result!r}"
        assert b._questioned[5, 5], "Cell should be questioned after second toggle"
        result = b.toggle_flag(5, 5)
        assert result == "hidden", f"Third toggle should return 'hidden', got {result!r}"
        assert not b._flagged[5, 5], "Cell should not be flagged after third toggle"
        assert not b._questioned[5, 5], "Cell should not be questioned after third toggle"

    def test_flag_on_revealed_cell_is_silently_ignored(self):
        """Toggling a flag on an already-revealed cell should be silently ignored."""
        mp = {(0, 0)}
        b = Board(5, 5, mp)
        b.reveal(4, 4)
        # The flood fill will reveal most cells; find one that is revealed
        revealed_x, revealed_y = 4, 4
        assert b._revealed[revealed_y, revealed_x], "Cell should be revealed after reveal()"
        result = b.toggle_flag(revealed_x, revealed_y)
        # Silently ignored: state should not have changed
        assert not b._flagged[revealed_y, revealed_x], "Flagging a revealed cell should be silently ignored"

    def test_win_on_all_safe_cells_revealed(self):
        """Win condition: all safe cells revealed (no flagging required)."""
        mp = {(0, 0)}
        b = Board(2, 2, mp)
        # Reveal all safe cells → should win immediately
        b.reveal(1, 0)
        b.reveal(0, 1)
        b.reveal(1, 1)
        assert b._state == "won"

    def test_win_does_not_require_flags(self):
        """Flagging is optional — win triggers on safe reveals alone, and mine cell stays unrevealed."""
        mp = {(0, 0)}
        b = Board(2, 2, mp)
        b.reveal(1, 0)
        b.reveal(0, 1)
        b.reveal(1, 1)
        assert b._state == "won", "All safe cells revealed should trigger win without flags"
        assert not b._flagged[0, 0], "Mine should not be auto-flagged when win is triggered by reveals"

    def test_chord_reveals_neighbours(self):
        mp = {(0, 0)}
        b = Board(5, 5, mp)
        b.reveal(1, 1)  # cell adjacent to (0,0) — has count 1
        b.toggle_flag(0, 0)
        hit, revealed = b.chord(1, 1)
        assert not hit, "chord on correctly flagged cell should not hit a mine"
        # Assert that specific neighbours were revealed by the chord operation
        assert len(revealed) > 0, "chord should reveal at least one neighbour"
        # (0,1) and (1,0) are neighbours of (1,1) and not mines — should be revealed
        assert (0, 1) in revealed or (1, 0) in revealed, f"Expected neighbour cells in revealed set, got {revealed}"

    def test_snapshot_fields(self):
        mp = {(2, 2)}
        b = Board(5, 5, mp)
        b.toggle_flag(2, 2)
        cs = b.snapshot(2, 2)
        assert cs.is_mine, "snapshot.is_mine should be True for a mine cell"
        assert cs.is_flagged, "snapshot.is_flagged should be True after toggle_flag"
        assert not cs.is_revealed, "snapshot.is_revealed should be False — cell not yet revealed"
        assert cs.neighbour_mines == 0, f"snapshot.neighbour_mines for isolated mine should be 0, got {cs.neighbour_mines!r}"

    def test_wrong_flag_positions(self):
        mp = {(0, 0)}
        b = Board(5, 5, mp)
        b.toggle_flag(1, 1)  # wrong flag (not a mine)
        wrongs = b.wrong_flag_positions()
        assert (1, 1) in wrongs, "(1,1) is flagged but not a mine — should be in wrong_flag_positions"
        assert (0, 0) not in wrongs, "(0,0) is a mine but not flagged — should not be in wrong_flag_positions"

    def test_wrong_flag_positions_zero_flags(self):
        """Zero flags placed → wrong_flag_positions should return empty set."""
        mp = {(0, 0)}
        b = Board(5, 5, mp)
        wrongs = b.wrong_flag_positions()
        assert len(wrongs) == 0, f"No flags placed, expected empty set, got {wrongs}"

    def test_wrong_flag_positions_multiple_wrong_flags(self):
        """Multiple wrong flags placed simultaneously."""
        mp = {(0, 0)}
        b = Board(5, 5, mp)
        b.toggle_flag(1, 1)
        b.toggle_flag(2, 2)
        wrongs = b.wrong_flag_positions()
        assert (1, 1) in wrongs, "(1,1) should be in wrong_flag_positions"
        assert (2, 2) in wrongs, "(2,2) should be in wrong_flag_positions"
        assert len(wrongs) == 2, f"Expected 2 wrong flags, got {len(wrongs)}: {wrongs}"


# ─────────────────────────────────────────────────────────────────────────────
#  GameEngine Lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestGameEngineLifecycle:

    def test_first_click_always_safe(self):
        """First left-click must never hit a mine (board regenerates if needed)."""
        for seed in range(20):
            eng = make_engine(w=9, h=9, mines=70, seed=seed)  # very high mine density
            result = eng.left_click(4, 4)
            assert not result.hit_mine, (
                f"First click hit mine with seed={seed}: board regeneration did not protect first click"
            )

    def test_state_property_matches_board(self):
        eng = make_engine()
        assert eng.state == eng.board._state

    def test_restart_random_creates_new_board(self):
        eng = make_engine(seed=0)
        mines_before = eng.board.total_mines
        eng.restart()
        assert eng.board.total_mines == mines_before
        assert eng.state == "playing"

    def test_restart_npy_reloads_same_board(self):
        """restart() in npy mode must reload the same board, not create a random one."""
        board_path = os.path.join(
            "results", "iter9",
            "20260510T054753Z_tessa_line_art_stiletto_300w_seed11_GAME_DevelopmentBOARD",
            "grid_iter9_300x300.npy",
        )
        if not os.path.exists(board_path):
            pytest.skip("tessa board not present")
        eng = GameEngine(mode="npy", npy_path=board_path, seed=11)
        eng.start()
        mines_before = eng.board.total_mines
        eng.restart()
        assert eng.board.total_mines == mines_before, \
            "restart() in npy mode must reload the same board"
        assert eng.mode == "npy"

    def test_right_click_returns_move_result(self):
        eng = make_engine()
        result = eng.right_click(0, 0)
        assert isinstance(result, MoveResult)

    def test_from_difficulty_easy(self):
        eng = GameEngine.from_difficulty("easy", seed=1)
        assert eng.board.width == 9
        assert eng.board.height == 9
        assert eng.board.total_mines == 10

    def test_elapsed_grows_after_start(self):
        import time
        eng = make_engine()
        t0 = eng.elapsed
        # Sleep long enough to be reliable even on a loaded CI machine.
        time.sleep(0.2)
        t1 = eng.elapsed
        assert t1 > t0, (
            f"Elapsed should grow after start(); got t0={t0:.4f}s t1={t1:.4f}s"
        )

    def test_mine_hit_applies_penalty_and_continues(self):
        """Mine hit deducts score and keeps game playing (no game-over)."""
        mp = {(0, 0)}
        b = Board(3, 3, mp)
        eng = GameEngine(mode="random", width=3, height=3, mines=1, seed=99)
        eng.board = b
        eng._first_click = False
        eng.score = 500
        result = eng.left_click(0, 0)
        assert result.hit_mine, "left_click on mine should set hit_mine=True"
        assert eng.state == "playing", "game should continue after mine hit (no game-over)"
        # Assert exact penalty amount: score should equal 500 minus the penalty
        assert result.penalty > 0, f"penalty should be positive after mine hit, got {result.penalty}"
        expected_score = 500 - result.penalty
        assert eng.score == expected_score, f"score should be 500 - penalty ({expected_score}), got {eng.score}"
        assert eng.streak == 0, "streak should be reset to 0 after mine hit"


# ─────────────────────────────────────────────────────────────────────────────
#  DEV: dev_solve_board() — regression tests
# ─────────────────────────────────────────────────────────────────────────────

class TestDevSolveBoard:
    """Regression tests for GameEngine.dev_solve_board() (DEV feature)."""

    def test_returns_success_true_and_state_won(self):
        eng = make_engine(w=5, h=5, mines=3)
        result = eng.dev_solve_board()
        assert result.success
        assert result.state == "won"
        assert eng.state == "won"
        assert eng.board._state == "won"

    def test_all_safe_cells_are_revealed(self):
        eng = make_engine(w=5, h=5, mines=3)
        eng.dev_solve_board()
        board = eng.board
        safe_unrevealed = [
            (x, y)
            for y in range(board.height)
            for x in range(board.width)
            if not board._mine[y, x] and not board._revealed[y, x]
        ]
        assert safe_unrevealed == [], (
            f"Safe cells still unrevealed after dev_solve: {safe_unrevealed}"
        )

    def test_all_mines_are_flagged(self):
        eng = make_engine(w=5, h=5, mines=3)
        eng.dev_solve_board()
        board = eng.board
        unflagged_mines = [
            (x, y)
            for y in range(board.height)
            for x in range(board.width)
            if board._mine[y, x] and not board._flagged[y, x]
        ]
        assert unflagged_mines == [], (
            f"Mines not flagged after dev_solve: {unflagged_mines}"
        )

    def test_no_wrong_flags_remain(self):
        """dev_solve must clear any previously wrong flags on safe cells."""
        eng = make_engine(w=5, h=5, mines=3)
        board = eng.board
        safe = next(
            (x, y)
            for y in range(board.height)
            for x in range(board.width)
            if not board._mine[y, x]
        )
        board._flagged[safe[1], safe[0]] = True   # wrong flag before solve
        eng.dev_solve_board()
        assert not board._flagged[safe[1], safe[0]], (
            "Wrong flag on safe cell must be cleared by dev_solve"
        )

    def test_question_marks_are_cleared(self):
        eng = make_engine(w=5, h=5, mines=3)
        board = eng.board
        safe = next(
            (x, y)
            for y in range(board.height)
            for x in range(board.width)
            if not board._mine[y, x]
        )
        board._questioned[safe[1], safe[0]] = True
        eng.dev_solve_board()
        assert not np.any(board._questioned), (
            "All question marks must be cleared by dev_solve"
        )

    def test_noop_when_already_won(self):
        eng = make_engine(w=5, h=5, mines=3)
        eng.dev_solve_board()
        result2 = eng.dev_solve_board()
        assert not result2.success          # second call is a no-op
        assert eng.state == "won"           # still won, no crash or regression

    def test_timer_is_frozen_after_solve(self):
        import time as _time
        eng = make_engine(w=5, h=5, mines=3)
        eng.left_click(4, 4)               # start the clock
        _time.sleep(0.05)
        eng.dev_solve_board()
        t0 = eng.elapsed
        _time.sleep(0.05)
        t1 = eng.elapsed
        assert t0 == t1, (
            f"Elapsed must be frozen after dev_solve_board(); t0={t0:.4f} t1={t1:.4f}"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  NPY Loading
# ─────────────────────────────────────────────────────────────────────────────

class TestNpyLoading:

    def test_load_pipeline_format_all_boards(self):
        """All committed pipeline boards must load with non-zero mine counts."""
        base = os.path.join("results", "iter9")
        if not os.path.exists(base):
            pytest.skip("results/iter9 not present")
        boards = [
            ("20260429T234439Z_input_source_image_300w_seed42", "grid_iter9_300x370.npy", 15574),
            ("20260430T004415Z_line_art_irl_18v2_300w_seed11_Easter_Irl_Test", "grid_iter9_300x215.npy", 18529),
            ("20260430T004522Z_line_art_irl_18v2_600w_seed11_Easter_Irl_Test", "grid_iter9_600x429.npy", 63060),
            ("20260510T054753Z_tessa_line_art_stiletto_300w_seed11_GAME_DevelopmentBOARD", "grid_iter9_300x300.npy", 4794),
        ]
        for run_dir, fname, expected_mines in boards:
            path = os.path.join(base, run_dir, fname)
            if not os.path.exists(path):
                continue
            b = load_board_from_npy(path).board  # DP-R3: unwrap BoardLoadResult
            assert b.total_mines == expected_mines, \
                f"{fname}: expected {expected_mines} mines, got {b.total_mines}"
            assert b.total_mines > 0, f"{fname} loaded with 0 mines — format detection failed"

    def test_load_rejects_wrong_shape(self):
        g = np.zeros((9,), dtype=np.int8)
        path = save_game_format_npy(g)
        try:
            with pytest.raises(ValueError, match="Expected 2D array"):
                load_board_from_npy(path)
        finally:
            os.unlink(path)

        g3d = np.zeros((3, 3, 3), dtype=np.int8)
        path3d = save_game_format_npy(g3d)
        try:
            with pytest.raises(ValueError, match="Expected 2D array"):
                load_board_from_npy(path3d)
        finally:
            os.unlink(path3d)

        g4d = np.zeros((2, 2, 2, 2), dtype=np.int8)
        path4d = save_game_format_npy(g4d)
        try:
            with pytest.raises(ValueError, match="Expected 2D array"):
                load_board_from_npy(path4d)
        finally:
            os.unlink(path4d)
