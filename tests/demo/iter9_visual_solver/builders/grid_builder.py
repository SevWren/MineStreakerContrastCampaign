"""Builder for demo grid test data."""

from __future__ import annotations

import numpy as np


class GridBuilder:
    def __init__(self, height: int = 6, width: int = 8) -> None:
        self.height = int(height)
        self.width = int(width)
        self._mines: list[tuple[int, int]] = []

    def with_mines(self, cells: list[tuple[int, int]]) -> "GridBuilder":
        self._mines.extend((int(y), int(x)) for y, x in cells)
        return self

    def with_diagonal_mines(self) -> "GridBuilder":
        self._mines.extend((idx, idx) for idx in range(min(self.height, self.width)))
        return self

    def build(self) -> np.ndarray:
        grid = np.zeros((self.height, self.width), dtype=np.uint8)
        for y, x in self._mines:
            grid[y, x] = 1
        return grid
