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
    clear_surface: bool = True,
) -> None:
    if clear_surface and hasattr(surface, "fill"):
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


def draw_scaled_board_state(
    *,
    surface,
    adapter,
    board_state: Any,
    palette: Any,
    board_width: int,
    board_height: int,
    destination_rect: Any,
    show_safe_cells: bool = False,
    show_unknown_cells: bool = True,
) -> None:
    logical_surface = adapter.create_surface(width=int(board_width), height=int(board_height))
    if logical_surface is None:
        draw_board_state(
            surface=surface,
            adapter=adapter,
            board_state=board_state,
            palette=palette,
            cell_px=max(1, int(getattr(destination_rect, "width", 1)) // max(1, int(board_width))),
            show_safe_cells=show_safe_cells,
            show_unknown_cells=show_unknown_cells,
            origin=(int(getattr(destination_rect, "x", 0)), int(getattr(destination_rect, "y", 0))),
            clear_surface=False,
        )
        return
    draw_board_state(
        surface=logical_surface,
        adapter=adapter,
        board_state=board_state,
        palette=palette,
        cell_px=1,
        show_safe_cells=show_safe_cells,
        show_unknown_cells=show_unknown_cells,
        origin=(0, 0),
        clear_surface=True,
    )
    scaled_surface = adapter.scale_surface_nearest(
        logical_surface,
        width=int(getattr(destination_rect, "width")),
        height=int(getattr(destination_rect, "height")),
    )
    adapter.blit_surface(
        surface,
        scaled_surface,
        (int(getattr(destination_rect, "x")), int(getattr(destination_rect, "y"))),
    )
