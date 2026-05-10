"""
gameworks/tests/unit/test_board_loading.py

Tests for board loading functions and the BoardLoadResult dataclass.

Covers:
- load_board_from_npy(): pipeline format (0/1), game-save format (-1/0-8)
- Auto-detection of format
- Error conditions: 1D array, empty file, corrupt neighbour counts
- BoardLoadResult contract (R3 — pending)
- GAME_SAVE_SCHEMA_VERSION sidecar read/write (R9 — pending)
"""

from __future__ import annotations

import json
import os
import tempfile

import numpy as np
import pytest

from gameworks.engine import Board, load_board_from_npy, place_random_mines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_npy(grid: np.ndarray) -> str:
    f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
    np.save(f.name, grid)
    f.close()
    return f.name


# ---------------------------------------------------------------------------
# Pipeline format (0/1 int8)
# ---------------------------------------------------------------------------

class TestPipelineFormat:

    def test_single_mine_loads_correctly(self):
        grid = np.zeros((5, 5), dtype=np.int8)
        grid[0, 0] = 1
        path = write_npy(grid)
        try:
            b = load_board_from_npy(path)
            assert b.total_mines == 1
            assert b._mine[0, 0]
        finally:
            os.unlink(path)

    def test_multiple_mines_load_correctly(self):
        grid = np.zeros((9, 9), dtype=np.int8)
        grid[0, 0] = 1
        grid[4, 4] = 1
        grid[8, 8] = 1
        path = write_npy(grid)
        try:
            b = load_board_from_npy(path)
            assert b.total_mines == 3
        finally:
            os.unlink(path)

    def test_all_safe_board_loads(self):
        grid = np.zeros((5, 5), dtype=np.int8)
        path = write_npy(grid)
        try:
            b = load_board_from_npy(path)
            assert b.total_mines == 0
        finally:
            os.unlink(path)

    def test_dimensions_preserved(self):
        grid = np.zeros((7, 13), dtype=np.int8)
        path = write_npy(grid)
        try:
            b = load_board_from_npy(path)
            assert b.height == 7
            assert b.width == 13
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Game-save format (-1 = mine, 0-8 = neighbour count)
# ---------------------------------------------------------------------------

class TestGameSaveFormat:

    def _make_game_format_grid(self, mines: set, w: int = 5, h: int = 5) -> np.ndarray:
        b = Board(w, h, mines)
        return np.where(b._mine, np.int8(-1), b._neighbours.astype(np.int8))

    def test_mine_at_corner_loads(self):
        grid = self._make_game_format_grid({(0, 0)})
        path = write_npy(grid)
        try:
            b = load_board_from_npy(path)
            assert b.total_mines == 1
            assert b._mine[0, 0]
        finally:
            os.unlink(path)

    def test_mine_count_preserved(self):
        mines = {(0, 0), (2, 2), (4, 4)}
        grid = self._make_game_format_grid(mines)
        path = write_npy(grid)
        try:
            b = load_board_from_npy(path)
            assert b.total_mines == 3
        finally:
            os.unlink(path)

    def test_neighbour_counts_recomputed_correctly(self):
        """After loading a game-save board, neighbour counts must match fresh computation."""
        mines = {(0, 0)}
        grid = self._make_game_format_grid(mines)
        path = write_npy(grid)
        try:
            b = load_board_from_npy(path)
            fresh = Board(5, 5, mines)
            assert (b._neighbours == fresh._neighbours).all()
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Format auto-detection
# ---------------------------------------------------------------------------

class TestFormatAutoDetection:

    def test_pipeline_format_detected_no_negative_values(self):
        grid = np.array([[0, 1], [0, 0]], dtype=np.int8)
        path = write_npy(grid)
        try:
            b = load_board_from_npy(path)
            assert b.total_mines == 1
        finally:
            os.unlink(path)

    def test_game_format_detected_by_negative_values(self):
        grid = np.array([[-1, 1], [1, 1]], dtype=np.int8)
        path = write_npy(grid)
        try:
            b = load_board_from_npy(path)
            assert b.total_mines == 1
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Error conditions
# ---------------------------------------------------------------------------

class TestLoadErrors:

    def test_1d_array_raises_value_error(self):
        grid = np.zeros((9,), dtype=np.int8)
        path = write_npy(grid)
        try:
            with pytest.raises(ValueError):
                load_board_from_npy(path)
        finally:
            os.unlink(path)

    def test_missing_file_raises(self):
        with pytest.raises((FileNotFoundError, OSError, ValueError)):
            load_board_from_npy("/tmp/does_not_exist_gameworks_test.npy")


# ---------------------------------------------------------------------------
# BoardLoadResult (R3 — PENDING)
# ---------------------------------------------------------------------------

class TestBoardLoadResult:
    """
    Tests for the BoardLoadResult dataclass.

    Status: PENDING — BoardLoadResult does not exist yet.
    Implement per DESIGN_PATTERNS.md § R3 — BoardLoadResult Dataclass.
    """

    @pytest.mark.skip(reason="Pending R3 — BoardLoadResult not yet implemented")
    def test_load_npy_returns_board_load_result(self):
        from gameworks.engine import BoardLoadResult
        grid = np.zeros((5, 5), dtype=np.int8)
        path = write_npy(grid)
        try:
            result = load_board_from_npy(path)
            assert isinstance(result, BoardLoadResult)
        finally:
            os.unlink(path)

    @pytest.mark.skip(reason="Pending R3 — BoardLoadResult not yet implemented")
    def test_result_has_board_attribute(self):
        from gameworks.engine import BoardLoadResult
        grid = np.zeros((5, 5), dtype=np.int8)
        path = write_npy(grid)
        try:
            result = load_board_from_npy(path)
            assert isinstance(result.board, Board)
        finally:
            os.unlink(path)

    @pytest.mark.skip(reason="Pending R3 — BoardLoadResult not yet implemented")
    def test_format_detected_pipeline(self):
        grid = np.zeros((5, 5), dtype=np.int8)
        path = write_npy(grid)
        try:
            result = load_board_from_npy(path)
            assert result.format_detected == "pipeline"
        finally:
            os.unlink(path)

    @pytest.mark.skip(reason="Pending R3 — BoardLoadResult not yet implemented")
    def test_format_detected_game_save(self):
        mines = {(0, 0)}
        b = Board(3, 3, mines)
        grid = np.where(b._mine, np.int8(-1), b._neighbours.astype(np.int8))
        path = write_npy(grid)
        try:
            result = load_board_from_npy(path)
            assert result.format_detected == "game-save"
        finally:
            os.unlink(path)

    @pytest.mark.skip(reason="Pending R3 — BoardLoadResult not yet implemented")
    def test_warnings_list_is_present(self):
        grid = np.zeros((5, 5), dtype=np.int8)
        path = write_npy(grid)
        try:
            result = load_board_from_npy(path)
            assert isinstance(result.warnings, list)
        finally:
            os.unlink(path)

    @pytest.mark.skip(reason="Pending R3 — BoardLoadResult not yet implemented")
    def test_random_fallback_format_detected(self):
        """load_board_from_pipeline fallback must record 'random-fallback' format."""
        from gameworks.engine import load_board_from_pipeline
        result = load_board_from_pipeline("/nonexistent/image.png", board_w=9, seed=1)
        assert result.format_detected == "random-fallback"


# ---------------------------------------------------------------------------
# Schema versioning (R9 — PENDING)
# ---------------------------------------------------------------------------

class TestSchemaVersioning:
    """
    Tests for GAME_SAVE_SCHEMA_VERSION and JSON sidecar read/write.

    Status: PENDING — schema versioning not yet implemented.
    Implement per DESIGN_PATTERNS.md § R9 — Game-Save Schema Version.
    """

    @pytest.mark.skip(reason="Pending R9 — GAME_SAVE_SCHEMA_VERSION not yet implemented")
    def test_schema_version_constant_exists(self):
        from gameworks.engine import GAME_SAVE_SCHEMA_VERSION
        assert isinstance(GAME_SAVE_SCHEMA_VERSION, str)
        assert GAME_SAVE_SCHEMA_VERSION.startswith("gameworks.board.")

    @pytest.mark.skip(reason="Pending R9 — sidecar JSON not yet implemented")
    def test_sidecar_written_on_save(self, tmp_dir):
        """Saving a board must produce a .json sidecar alongside the .npy file."""
        from gameworks.engine import GameEngine
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        npy_path = os.path.join(tmp_dir, "board_test.npy")
        eng._save_npy_to(npy_path)
        sidecar = npy_path.replace(".npy", ".json")
        assert os.path.exists(sidecar)

    @pytest.mark.skip(reason="Pending R9 — sidecar JSON not yet implemented")
    def test_sidecar_contains_required_fields(self, tmp_dir):
        from gameworks.engine import GAME_SAVE_SCHEMA_VERSION, GameEngine
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        npy_path = os.path.join(tmp_dir, "board_test.npy")
        eng._save_npy_to(npy_path)
        sidecar = npy_path.replace(".npy", ".json")
        with open(sidecar) as f:
            meta = json.load(f)
        for key in ("schema", "width", "height", "mines", "seed", "saved_at"):
            assert key in meta, f"Sidecar missing field: {key}"
        assert meta["schema"] == GAME_SAVE_SCHEMA_VERSION

    @pytest.mark.skip(reason="Pending R9 — sidecar JSON not yet implemented")
    def test_load_warns_on_schema_mismatch(self, tmp_dir):
        """Loading a board saved with a different schema version must add a warning."""
        npy_path = os.path.join(tmp_dir, "old_board.npy")
        grid = np.zeros((5, 5), dtype=np.int8)
        np.save(npy_path, grid)
        sidecar = npy_path.replace(".npy", ".json")
        with open(sidecar, "w") as f:
            json.dump({"schema": "gameworks.board.v0"}, f)
        result = load_board_from_npy(npy_path)
        assert any("schema" in w.lower() for w in result.warnings)

    @pytest.mark.skip(reason="Pending R9 — sidecar JSON not yet implemented")
    def test_load_without_sidecar_succeeds_with_warning(self, tmp_dir):
        """Loading a .npy file with no sidecar must succeed (backward compat) with a warning."""
        npy_path = os.path.join(tmp_dir, "legacy.npy")
        grid = np.zeros((5, 5), dtype=np.int8)
        np.save(npy_path, grid)
        result = load_board_from_npy(npy_path)
        assert result.board is not None
        assert isinstance(result.warnings, list)
