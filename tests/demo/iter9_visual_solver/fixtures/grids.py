"""Reusable NumPy grid fixtures for Iter9 visual solver demo tests."""

from __future__ import annotations

import numpy as np


def tiny_2x2_grid() -> np.ndarray:
    return np.array([[1, 0], [0, 1]], dtype=np.uint8)


def wide_300x10_grid() -> np.ndarray:
    return np.zeros((10, 300), dtype=np.uint8)


def tall_10x300_grid() -> np.ndarray:
    return np.zeros((300, 10), dtype=np.uint8)


def empty_grid(height: int, width: int) -> np.ndarray:
    return np.zeros((int(height), int(width)), dtype=np.uint8)


def checker_mine_grid(height: int, width: int) -> np.ndarray:
    y, x = np.indices((int(height), int(width)))
    return ((x + y) % 2).astype(np.uint8)


def line_art_like_grid(height: int = 12, width: int = 20) -> np.ndarray:
    grid = np.zeros((height, width), dtype=np.uint8)
    grid[height // 2, :] = 1
    grid[:, width // 2] = 1
    return grid
