"""Status panel drawing helper."""

from __future__ import annotations

from typing import Any

PANEL_PADDING_X = 12
PANEL_PADDING_Y = 12
LINE_GAP_PX = 4
SECTION_GAP_PX = 8
CARD_GAP_Y = 8
PROGRESS_BAR_HEIGHT = 8
LEGEND_SWATCH_SIZE = 10
BADGE_HEIGHT = 34


def _rect_tuple(rect: Any | None):
    if rect is None:
        return None
    if hasattr(rect, "as_tuple"):
        return rect.as_tuple()
    return tuple(rect)


def _line_height(font) -> int:
    if font is not None and hasattr(font, "get_linesize"):
        return max(1, int(font.get_linesize()))
    return 20


def _measure_text(font, text: str) -> int:
    if font is not None and hasattr(font, "size"):
        size = font.size(text)
        return int(size[0])
    return len(text) * 8


def wrap_status_line(text: str, *, max_width_px: int, font) -> list[str]:
    if max_width_px <= 0:
        return []
    if _measure_text(font, text) <= max_width_px:
        return [text]
    words = text.split()
    if not words:
        return [text]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if _measure_text(font, candidate) <= max_width_px:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _blit_text(surface, adapter, font, text: str, color, x: int, y: int) -> None:
    if adapter is not None and hasattr(adapter, "blit_text"):
        adapter.blit_text(surface, font, text, color, (x, y))
        return
    rendered = None
    if font is not None and hasattr(font, "render"):
        rendered = font.render(text, True, tuple(color))
    if rendered is not None and hasattr(surface, "blit"):
        surface.blit(rendered, (x, y))


def draw_status_panel(
    surface,
    lines: list[str],
    *,
    panel_rect=None,
    background_rgb=(10, 10, 10),
    text_rgb=(230, 230, 230),
    font=None,
) -> None:
    panel_rect = _rect_tuple(panel_rect)
    if hasattr(surface, "fill"):
        try:
            surface.fill(tuple(background_rgb), panel_rect)
        except TypeError:
            surface.fill(tuple(background_rgb))
    if font is None and hasattr(surface, "font"):
        font = surface.font
    x = PANEL_PADDING_X
    y = PANEL_PADDING_Y
    if panel_rect is not None:
        x += int(panel_rect[0])
        y += int(panel_rect[1])
        max_width = max(0, int(panel_rect[2]) - PANEL_PADDING_X * 2)
        bottom = int(panel_rect[1]) + int(panel_rect[3]) - PANEL_PADDING_Y
    else:
        max_width = 10_000
        bottom = 10_000
    line_height = _line_height(font)
    for line in lines:
        for wrapped in wrap_status_line(str(line), max_width_px=max_width, font=font):
            if y + line_height > bottom:
                return
            _blit_text(surface, None, font, wrapped, tuple(text_rgb), x, y)
            y += line_height + LINE_GAP_PX


def draw_status_panel_view_model(
    surface,
    view_model,
    *,
    adapter,
    panel_rect,
    palette,
    font,
    text_rgb: tuple[int, int, int] = (230, 230, 230),
    source_preview_rect=None,
) -> None:
    rect = _rect_tuple(panel_rect)
    if rect is None:
        return
    adapter.draw_rect(surface, tuple(palette.background_rgb), rect)
    x = rect[0] + PANEL_PADDING_X
    y = rect[1] + PANEL_PADDING_Y
    width = max(0, rect[2] - PANEL_PADDING_X * 2)
    bottom = rect[1] + rect[3] - PANEL_PADDING_Y
    line_height = _line_height(font)

    badge_color = (30, 120, 65) if view_model.badge.state == "solved" else (80, 80, 80)
    if y + BADGE_HEIGHT <= bottom:
        adapter.draw_rect(surface, badge_color, (x, y, width, BADGE_HEIGHT), border_radius=4)
        _blit_text(surface, adapter, font, f"{view_model.badge.label} - {view_model.badge.detail}", text_rgb, x + 8, y + 9)
        y += BADGE_HEIGHT + CARD_GAP_Y

    for card in view_model.cards:
        rows = tuple(getattr(card, "rows", ()) or ())
        row_count = len(rows) if rows else len(card.lines)
        needed = line_height * (row_count + 1) + CARD_GAP_Y
        if y + needed > bottom:
            break
        adapter.draw_rect(surface, (24, 24, 24), (x, y, width, needed), border_radius=4)
        _blit_text(surface, adapter, font, card.title, text_rgb, x + 8, y + 6)
        line_y = y + line_height + 8
        if rows and width >= 440:
            for row in rows:
                label = f"{row.label}:"
                value = str(row.value)
                value_x = x + width - 8 - _measure_text(font, value)
                _blit_text(surface, adapter, font, label, text_rgb, x + 8, line_y)
                _blit_text(surface, adapter, font, value, text_rgb, max(x + 8, value_x), line_y)
                line_y += line_height + LINE_GAP_PX
        elif rows:
            for row in rows:
                line = f"{row.label}: {row.value}"
                for wrapped in wrap_status_line(line, max_width_px=max(1, width - 16), font=font):
                    if line_y + line_height > y + needed:
                        break
                    _blit_text(surface, adapter, font, wrapped, text_rgb, x + 8, line_y)
                    line_y += line_height + LINE_GAP_PX
        else:
            for line in card.lines:
                _blit_text(surface, adapter, font, line, text_rgb, x + 8, line_y)
                line_y += line_height + LINE_GAP_PX
        y += needed + CARD_GAP_Y

    for progress in view_model.progress_bars:
        if y + line_height + PROGRESS_BAR_HEIGHT + SECTION_GAP_PX > bottom:
            break
        _blit_text(surface, adapter, font, f"{progress.label}: {progress.value_text}", text_rgb, x, y)
        y += line_height + LINE_GAP_PX
        adapter.draw_rect(surface, (52, 52, 52), (x, y, width, PROGRESS_BAR_HEIGHT))
        filled = int(width * progress.ratio)
        fill_color = (40, 150, 85) if progress.good_when_zero else (85, 130, 210)
        adapter.draw_rect(surface, fill_color, (x, y, filled, PROGRESS_BAR_HEIGHT))
        y += PROGRESS_BAR_HEIGHT + SECTION_GAP_PX

    legend_y = y
    for item in view_model.legend_items:
        if legend_y + LEGEND_SWATCH_SIZE > bottom:
            break
        adapter.draw_rect(surface, tuple(item.rgb), (x, legend_y + 3, LEGEND_SWATCH_SIZE, LEGEND_SWATCH_SIZE))
        _blit_text(surface, adapter, font, item.label, text_rgb, x + LEGEND_SWATCH_SIZE + 6, legend_y)
        legend_y += line_height + LINE_GAP_PX

    preview_rect = _rect_tuple(source_preview_rect)
    if preview_rect is not None:
        adapter.draw_rect(surface, (18, 18, 18), preview_rect, border_radius=4)
        adapter.draw_rect(surface, (95, 95, 95), preview_rect, width=1, border_radius=4)
        px = preview_rect[0] + 8
        py = preview_rect[1] + 8
        _blit_text(surface, adapter, font, "Source preview", text_rgb, px, py)
        _blit_text(surface, adapter, font, view_model.source_preview.label, text_rgb, px, py + line_height + 2)
        _blit_text(surface, adapter, font, view_model.source_preview.detail, text_rgb, px, py + (line_height + 2) * 2)
