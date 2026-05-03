"""Window chrome drawing helpers for the visual solver demo."""

from __future__ import annotations

from typing import Any


def _rect_tuple(rect: Any) -> tuple[int, int, int, int]:
    if hasattr(rect, "as_tuple"):
        return rect.as_tuple()
    return tuple(rect)


def draw_header_strip(
    surface,
    *,
    adapter,
    header_rect,
    text: str,
    background_rgb: tuple[int, int, int],
    text_rgb: tuple[int, int, int],
    font,
) -> None:
    rect = _rect_tuple(header_rect)
    adapter.draw_rect(surface, background_rgb, rect)
    adapter.blit_text(surface, font, text, text_rgb, (rect[0] + 12, rect[1] + 9))


def draw_board_border(
    surface,
    *,
    adapter,
    board_rect,
    border_rgb: tuple[int, int, int],
) -> None:
    adapter.draw_rect(surface, border_rgb, _rect_tuple(board_rect), width=1)


def draw_vertical_divider(
    surface,
    *,
    adapter,
    divider_rect,
    divider_rgb: tuple[int, int, int],
) -> None:
    adapter.draw_rect(surface, divider_rgb, _rect_tuple(divider_rect))
