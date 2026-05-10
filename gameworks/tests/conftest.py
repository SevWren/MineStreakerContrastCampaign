"""
gameworks/tests/conftest.py

Root-level pytest configuration and shared fixtures for the gameworks test suite.

Fixtures defined here are available to all sub-packages without explicit import.
"""

from __future__ import annotations

import os
import tempfile
from typing import Generator

import numpy as np
import pytest

from gameworks.engine import Board, GameEngine, place_random_mines


# ---------------------------------------------------------------------------
# Board factories
# ---------------------------------------------------------------------------

@pytest.fixture
def tiny_board() -> Board:
    """3×3 board with one mine at (0, 0). Minimal surface area for fast tests."""
    mines = {(0, 0)}
    return Board(3, 3, mines)


@pytest.fixture
def standard_board() -> Board:
    """9×9 board with 10 mines. Mirrors the Easy difficulty preset."""
    mines = place_random_mines(9, 9, 10, seed=42)
    return Board(9, 9, mines)


@pytest.fixture
def no_mine_board() -> Board:
    """5×5 board with zero mines. Useful for flood-fill and win-condition tests."""
    return Board(5, 5, set())


# ---------------------------------------------------------------------------
# Engine factories
# ---------------------------------------------------------------------------

@pytest.fixture
def easy_engine() -> GameEngine:
    """Started GameEngine at Easy difficulty (9×9, 10 mines, seed=42)."""
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    eng.start()
    return eng


@pytest.fixture
def medium_engine() -> GameEngine:
    """Started GameEngine at Medium difficulty (16×16, 40 mines, seed=42)."""
    eng = GameEngine(mode="random", width=16, height=16, mines=40, seed=42)
    eng.start()
    return eng


@pytest.fixture
def high_density_engine() -> GameEngine:
    """Started engine with very high mine density, for first-click-safety stress tests."""
    eng = GameEngine(mode="random", width=9, height=9, mines=70, seed=7)
    eng.start()
    return eng


# ---------------------------------------------------------------------------
# File system helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_npy_pipeline() -> Generator[str, None, None]:
    """
    Write a small pipeline-format .npy (0/1 int8) to a temp file.
    Yields the path; cleans up on teardown.
    """
    grid = np.zeros((5, 5), dtype=np.int8)
    grid[0, 0] = 1   # one mine at top-left
    grid[2, 2] = 1   # one mine in the middle
    f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
    np.save(f.name, grid)
    f.close()
    yield f.name
    os.unlink(f.name)


@pytest.fixture
def tmp_npy_game_format() -> Generator[str, None, None]:
    """
    Write a small game-format .npy (-1=mine, 0-8=neighbours) to a temp file.
    Yields the path; cleans up on teardown.
    """
    # 3×3 board, mine at (0,0): encode as -1 for mines, neighbours elsewhere
    mines = {(0, 0)}
    b = Board(3, 3, mines)
    grid = np.where(b._mine, np.int8(-1), b._neighbours.astype(np.int8))
    f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
    np.save(f.name, grid)
    f.close()
    yield f.name
    os.unlink(f.name)


@pytest.fixture
def tmp_dir() -> Generator[str, None, None]:
    """Yield a temporary directory path; remove it and its contents on teardown."""
    import shutil
    d = tempfile.mkdtemp()
    yield d
    shutil.rmtree(d, ignore_errors=True)
