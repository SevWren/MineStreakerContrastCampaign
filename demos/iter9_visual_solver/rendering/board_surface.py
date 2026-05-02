"""Board surface view model helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BoardSurfaceModel:
    width: int
    height: int
    cell_count: int


def build_board_surface_model(grid: Any) -> BoardSurfaceModel:
    shape = getattr(grid, "shape", None)
    if shape is None or len(shape) != 2:
        raise ValueError("grid must be 2D")
    height = int(shape[0])
    width = int(shape[1])
    return BoardSurfaceModel(width=width, height=height, cell_count=width * height)


def draw_board_state(
    *,
    surface,
    adapter,
    board_state: Any,
    palette: Any,
    cell_px: int,
    show_safe_cells: bool = False,
    show_unknown_cells: bool = True,
    origin: tuple[int, int] = (0, 0),
) -> None:
    if hasattr(surface, "fill"):
        surface.fill(tuple(palette.background_rgb))
    origin_x, origin_y = origin
    cell_px = max(1, int(cell_px))
    for (y, x), state in board_state.cells.items():
        color = None
        if state == "MINE":
            color = palette.flagged_mine_rgb
        elif state == "SAFE" and show_safe_cells:
            color = palette.safe_cell_rgb
        elif state == "UNKNOWN" and show_unknown_cells:
            color = palette.unknown_cell_rgb
        if color is None:
            continue
        rect = (origin_x + int(x) * cell_px, origin_y + int(y) * cell_px, cell_px, cell_px)
        adapter.draw_rect(surface, tuple(color), rect)
