"""Window geometry calculation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WindowGeometry:
    board_width: int
    board_height: int
    cell_px: int
    board_pixel_width: int
    board_pixel_height: int
    status_panel_width_px: int
    window_width: int
    window_height: int


def calculate_window_geometry(
    *,
    board_width: int,
    board_height: int,
    status_panel_width_px: int = 360,
    preferred_board_cell_px: int = 2,
    minimum_board_cell_px: int = 1,
    max_screen_fraction: float = 1.0,
    screen_width: int = 1920,
    screen_height: int = 1080,
    fit_to_screen: bool = True,
) -> WindowGeometry:
    board_width = int(board_width)
    board_height = int(board_height)
    status_panel_width_px = int(status_panel_width_px)
    cell_px = int(preferred_board_cell_px)
    if fit_to_screen:
        max_width = max(1, int(screen_width * float(max_screen_fraction)) - status_panel_width_px)
        max_height = max(1, int(screen_height * float(max_screen_fraction)))
        cell_px = min(cell_px, max_width // max(board_width, 1), max_height // max(board_height, 1))
    cell_px = max(int(minimum_board_cell_px), cell_px)
    board_pixel_width = board_width * cell_px
    board_pixel_height = board_height * cell_px
    return WindowGeometry(
        board_width=board_width,
        board_height=board_height,
        cell_px=cell_px,
        board_pixel_width=board_pixel_width,
        board_pixel_height=board_pixel_height,
        status_panel_width_px=status_panel_width_px,
        window_width=board_pixel_width + status_panel_width_px,
        window_height=board_pixel_height,
    )

