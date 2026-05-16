"""Board dimension derivation from loaded grids."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BoardDimensions:
    width: int
    height: int
    total_cells: int

    @classmethod
    def from_grid(cls, grid: Any) -> "BoardDimensions":
        shape = getattr(grid, "shape", None)
        if shape is None or len(shape) != 2:
            raise ValueError("grid must be a 2D array")
        height = int(shape[0])
        width = int(shape[1])
        if width <= 0 or height <= 0:
            raise ValueError("grid dimensions must be positive")
        return cls(width=width, height=height, total_cells=width * height)

