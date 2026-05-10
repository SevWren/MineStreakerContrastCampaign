"""
gameworks/tests/integration/test_board_modes.py

Integration tests for GameEngine board modes: random, npy, image-fallback.

Tests verify that each mode produces a playable board and that GameEngine
exposes the expected attributes after start().
"""

from __future__ import annotations

import os
import tempfile

import numpy as np
import pytest

from gameworks.engine import Board, GameEngine, place_random_mines


class TestRandomMode:

    def test_random_engine_starts(self):
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        assert eng.state == "playing"

    def test_random_board_has_correct_mine_count(self):
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        assert eng.board.total_mines == 10

    def test_random_board_has_correct_dimensions(self):
        eng = GameEngine(mode="random", width=16, height=9, mines=20, seed=1)
        eng.start()
        assert eng.board.width == 16
        assert eng.board.height == 9

    def test_auto_mine_count_when_zero(self):
        """mines=0 should auto-compute a non-zero mine count."""
        eng = GameEngine(mode="random", width=9, height=9, mines=0, seed=42)
        eng.start()
        assert eng.board.total_mines >= 1

    def test_mode_attribute_is_random(self):
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        assert eng.mode == "random"


class TestNpyMode:

    def _make_npy(self) -> str:
        """Write a pipeline-format .npy with 2 mines and return path."""
        grid = np.zeros((5, 5), dtype=np.int8)
        grid[0, 0] = 1
        grid[4, 4] = 1
        f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
        np.save(f.name, grid)
        f.close()
        return f.name

    def test_npy_engine_starts(self):
        path = self._make_npy()
        try:
            eng = GameEngine(mode="npy", npy_path=path, seed=1)
            eng.start()
            assert eng.state == "playing"
        finally:
            os.unlink(path)

    def test_npy_engine_mine_count_matches_file(self):
        path = self._make_npy()
        try:
            eng = GameEngine(mode="npy", npy_path=path, seed=1)
            eng.start()
            assert eng.board.total_mines == 2
        finally:
            os.unlink(path)

    def test_npy_mode_attribute(self):
        path = self._make_npy()
        try:
            eng = GameEngine(mode="npy", npy_path=path, seed=1)
            eng.start()
            assert eng.mode == "npy"
        finally:
            os.unlink(path)

    def test_npy_restart_preserves_mine_count(self):
        path = self._make_npy()
        try:
            eng = GameEngine(mode="npy", npy_path=path, seed=1)
            eng.start()
            mines_before = eng.board.total_mines
            eng.restart()
            assert eng.board.total_mines == mines_before
        finally:
            os.unlink(path)


class TestImageFallback:

    def test_image_mode_falls_back_to_random_on_missing_file(self):
        """If pipeline fails (missing numba or bad path), a random board is used."""
        eng = GameEngine(mode="image", image_path="/nonexistent/image.png",
                         width=9, height=9, seed=1)
        eng.start()
        assert eng.state == "playing"
        assert eng.board.total_mines >= 1


class TestSaveLoadRoundTrip:
    """
    Atomic save + reload round-trip.
    R8 (atomic write) tests are pending but the current np.save path is tested here.
    """

    def test_saved_board_reloads_same_mine_count(self):
        from gameworks.engine import load_board_from_npy
        mines = place_random_mines(9, 9, 10, seed=42)
        b = Board(9, 9, mines)
        f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
        np.save(f.name, b._mine.astype(np.int8))
        f.close()
        try:
            b2 = load_board_from_npy(f.name)
            assert b2.total_mines == b.total_mines
            assert set(b2.all_mine_positions()) == set(b.all_mine_positions())
        finally:
            os.unlink(f.name)

    @pytest.mark.skip(reason="Pending R8 — atomic save not yet implemented")
    def test_atomic_save_uses_tmp_then_replace(self, tmp_dir):
        """
        GameLoop._save_npy must write to a .tmp file first and call os.replace.
        Verify no .tmp file remains after a successful save.
        """
        import glob
        from gameworks.engine import GameEngine
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        npy_path = os.path.join(tmp_dir, "board_atomic.npy")
        eng._save_npy_to(npy_path)
        tmp_files = glob.glob(npy_path + ".tmp")
        assert tmp_files == [], "No .tmp files should remain after successful atomic save"
        assert os.path.exists(npy_path)
