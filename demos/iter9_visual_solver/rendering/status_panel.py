"""Status panel drawing helper."""

from __future__ import annotations


def draw_status_panel(
    surface,
    lines: list[str],
    *,
    panel_rect=None,
    background_rgb=(10, 10, 10),
    text_rgb=(230, 230, 230),
    font=None,
) -> None:
    if hasattr(surface, "fill"):
        try:
            surface.fill(tuple(background_rgb), panel_rect)
        except TypeError:
            surface.fill(tuple(background_rgb))
    if font is None and hasattr(surface, "font"):
        font = surface.font
    x = 12
    y = 12
    if panel_rect is not None:
        x += int(panel_rect[0])
        y += int(panel_rect[1])
    for line in lines:
        rendered = None
        if font is not None and hasattr(font, "render"):
            rendered = font.render(line, True, tuple(text_rgb))
        if rendered is not None and hasattr(surface, "blit"):
            surface.blit(rendered, (x, y))
        y += 20
