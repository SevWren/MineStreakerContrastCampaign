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
        assert b._state == "won"

    def test_f002a_mine_hit_keeps_playing(self):
        """Mine hit returns hit=True but state stays 'playing' (no game-over)."""
        mp = {(4, 4)}
        b = Board(9, 9, mp)
        hit, _ = b.reveal(4, 4)
        assert hit
        assert b._state == "playing"   # game continues after mine hit

    def test_f001a_fps_importable(self):
        """FIND-ARCH-CRITICAL-f001a: FPS must be importable from renderer."""
        pytest.importorskip("pygame", reason="pygame not installed")
        from gameworks.renderer import FPS
        assert isinstance(FPS, int)
        assert FPS > 0

    def test_f005a_btn_w_stored_on_self(self):
        """FIND-ARCH-CRITICAL-f005a: Renderer must store _btn_w as instance attribute."""
        pytest.importorskip("pygame", reason="pygame not installed")
        import inspect
        import gameworks.renderer as r
        src = inspect.getsource(r.Renderer.__init__)
        assert "self._btn_w" in src, "_btn_w must be stored on self in Renderer.__init__"

    def test_f006a_pipeline_npy_loads_correctly(self):
        """FIND-ARCH-CRITICAL-f006a: Pipeline format .npy (0/1) must load with correct mine count."""
        board_path = os.path.join(
            "results", "iter9",
            "20260510T054753Z_tessa_line_art_stiletto_300w_seed11_GAME_DevelopmentBOARD",
            "grid_iter9_300x300.npy",
        )
        if not os.path.exists(board_path):
            pytest.skip("tessa board not present")
        b = load_board_from_npy(board_path)
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
            b = load_board_from_npy(path)
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
            b = load_board_from_npy(path)
            assert b.total_mines == 1
        finally:
            os.unlink(path)

        # Game format: has -1
        g_game = np.array([[-1, 1], [1, 1]], dtype=np.int8)
        path = save_game_format_npy(g_game)
        try:
            b = load_board_from_npy(path)
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
        assert int(b._neighbours[0, 1]) == 1
        # (1, 1) is diagonal to the mine
        assert int(b._neighbours[1, 1]) == 1
        # (2, 2) is far from the mine
        assert int(b._neighbours[2, 2]) == 0

    def test_reveal_mine_returns_hit(self):
        """Mine hit returns hit=True but game continues (no game-over)."""
        mp = {(3, 3)}
        b = Board(9, 9, mp)
        hit, revealed = b.reveal(3, 3)
        assert hit
        # No game-over: mine hit is a penalty, game keeps going
        assert b._state == "playing"
        assert b._revealed[3, 3]   # mine cell is revealed

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
        assert result == "flag"
        assert b._flagged[5, 5]
        result = b.toggle_flag(5, 5)
        assert result == "question"
        assert b._questioned[5, 5]
        result = b.toggle_flag(5, 5)
        assert result == "hidden"
        assert not b._flagged[5, 5]
        assert not b._questioned[5, 5]

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
        """Flagging is optional — win triggers on safe reveals alone."""
        mp = {(0, 0)}
        b = Board(2, 2, mp)
        b.reveal(1, 0)
        b.reveal(0, 1)
        b.reveal(1, 1)
        assert b._state == "won", "All safe cells revealed should trigger win without flags"

    def test_chord_reveals_neighbours(self):
        mp = {(0, 0)}
        b = Board(5, 5, mp)
        b.reveal(1, 1)  # cell adjacent to (0,0) — has count 1
        b.toggle_flag(0, 0)
        hit, revealed = b.chord(1, 1)
        assert not hit

    def test_snapshot_fields(self):
        mp = {(2, 2)}
        b = Board(5, 5, mp)
        b.toggle_flag(2, 2)
        cs = b.snapshot(2, 2)
        assert cs.is_mine
        assert cs.is_flagged
        assert not cs.is_revealed

    def test_wrong_flag_positions(self):
        mp = {(0, 0)}
        b = Board(5, 5, mp)
        b.toggle_flag(1, 1)  # wrong flag (not a mine)
        wrongs = b.wrong_flag_positions()
        assert (1, 1) in wrongs
        assert (0, 0) not in wrongs


# ─────────────────────────────────────────────────────────────────────────────
#  GameEngine Lifecycle
# ─────────────────────────────────────────────────────────────────────────────

class TestGameEngineLifecycle:

    def test_first_click_always_safe(self):
        """First left-click must never hit a mine (board regenerates if needed)."""
        for seed in range(20):
            eng = make_engine(w=9, h=9, mines=70, seed=seed)  # very high mine density
            result = eng.left_click(4, 4)
            assert not result.hit_mine, f"First click hit mine with seed={seed}"

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
        time.sleep(0.05)
        assert eng.elapsed > t0, "Elapsed should grow after start()"

    def test_mine_hit_applies_penalty_and_continues(self):
        """Mine hit deducts score and keeps game playing (no game-over)."""
        mp = {(0, 0)}
        b = Board(3, 3, mp)
        eng = GameEngine(mode="random", width=3, height=3, mines=1, seed=99)
        eng.board = b
        eng._first_click = False
        eng.score = 500
        result = eng.left_click(0, 0)
        assert result.hit_mine
        assert eng.state == "playing"         # game continues
        assert eng.score < 500               # penalty deducted
        assert eng.streak == 0               # streak reset
        assert result.penalty > 0


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
            b = load_board_from_npy(path)
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
