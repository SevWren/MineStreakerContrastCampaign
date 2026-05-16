"""Pygame adapter seam.

The module intentionally avoids importing pygame at module import time.
"""

from __future__ import annotations

import importlib

from demos.iter9_visual_solver.rendering.window_geometry import (
    DisplayBounds,
    FALLBACK_DISPLAY_BOUNDS,
    WindowPlacement,
)


class PygameAdapter:
    def __init__(self, pygame_module=None) -> None:
        self.pygame = pygame_module if pygame_module is not None else importlib.import_module("pygame")
        self.surface = None
        self.clock = None

    def open_window(
        self,
        *,
        width: int,
        height: int,
        title: str,
        resizable: bool = False,
        placement: WindowPlacement | None = None,
    ):
        self.pygame.init()
        if hasattr(self.pygame, "font") and hasattr(self.pygame.font, "init"):
            self.pygame.font.init()
        if placement is not None and placement.x is not None:
            self.requested_placement = placement
            if hasattr(self.pygame.display, "set_window_position"):
                self.pygame.display.set_window_position((int(placement.x), int(placement.y or 0)))
        flags = getattr(self.pygame, "RESIZABLE", 0) if resizable else 0
        self.surface = self.pygame.display.set_mode((int(width), int(height)), flags)
        self.pygame.display.set_caption(title)
        self.clock = self.pygame.time.Clock()
        return self.surface

    def get_display_bounds(self) -> DisplayBounds:
        if hasattr(self.pygame, "init"):
            self.pygame.init()
        display = getattr(self.pygame, "display", None)
        if display is not None and hasattr(display, "get_desktop_sizes"):
            sizes = display.get_desktop_sizes()
            if sizes:
                width, height = sizes[0]
                if int(width) > 0 and int(height) > 0:
                    return DisplayBounds(x=0, y=0, width=int(width), height=int(height))
        if display is not None and hasattr(display, "Info"):
            info = display.Info()
            width = int(getattr(info, "current_w", 0) or 0)
            height = int(getattr(info, "current_h", 0) or 0)
            if width > 0 and height > 0:
                return DisplayBounds(x=0, y=0, width=width, height=height)
        return FALLBACK_DISPLAY_BOUNDS

    def resize_window(self, *, width: int, height: int, resizable: bool):
        flags = getattr(self.pygame, "RESIZABLE", 0) if resizable else 0
        self.surface = self.pygame.display.set_mode((int(width), int(height)), flags)
        return self.surface

    def get_surface_size(self, surface=None) -> tuple[int, int]:
        target = surface if surface is not None else self.surface
        if target is not None and hasattr(target, "get_size"):
            width, height = target.get_size()
            return int(width), int(height)
        return FALLBACK_DISPLAY_BOUNDS.width, FALLBACK_DISPLAY_BOUNDS.height

    def is_quit_event(self, event) -> bool:
        return getattr(event, "type", event) == getattr(self.pygame, "QUIT", None)

    def is_resize_event(self, event) -> bool:
        event_type = getattr(event, "type", event)
        resize_types = [
            getattr(self.pygame, "VIDEORESIZE", None),
            getattr(self.pygame, "WINDOWRESIZED", None),
            getattr(self.pygame, "WINDOWSIZECHANGED", None),
            getattr(self.pygame, "WINDOWMAXIMIZED", None),
        ]
        return event_type in [value for value in resize_types if value is not None]

    def get_resize_event_size(self, event) -> tuple[int, int] | None:
        if hasattr(event, "w") and hasattr(event, "h"):
            return int(event.w), int(event.h)
        size = getattr(event, "size", None)
        if size is not None and len(size) == 2:
            return int(size[0]), int(size[1])
        if getattr(event, "type", event) == getattr(self.pygame, "WINDOWMAXIMIZED", None):
            bounds = self.get_display_bounds()
            return bounds.width, bounds.height
        if self.surface is not None:
            return self.get_surface_size(self.surface)
        return None

    def poll_events(self):
        return list(self.pygame.event.get())

    def tick(self, fps: int) -> int:
        if self.clock is None:
            self.clock = self.pygame.time.Clock()
        return self.clock.tick(int(fps))

    def flip(self) -> None:
        self.pygame.display.flip()

    def create_font(self, size: int = 16):
        if hasattr(self.pygame, "font") and hasattr(self.pygame.font, "SysFont"):
            return self.pygame.font.SysFont(None, int(size))
        return None

    def draw_rect(self, surface, color, rect, *, width: int = 0, border_radius: int = 0) -> None:
        if hasattr(self.pygame, "draw") and hasattr(self.pygame.draw, "rect"):
            try:
                self.pygame.draw.rect(
                    surface,
                    tuple(color),
                    tuple(rect),
                    int(width),
                    border_radius=int(border_radius),
                )
            except TypeError:
                if int(width) == 0:
                    self.pygame.draw.rect(surface, tuple(color), tuple(rect))

    def draw_line(self, surface, color, start_pos, end_pos, width: int = 1) -> None:
        if hasattr(self.pygame, "draw") and hasattr(self.pygame.draw, "line"):
            self.pygame.draw.line(surface, tuple(color), tuple(start_pos), tuple(end_pos), int(width))

    def create_surface(self, *, width: int, height: int):
        surface_factory = getattr(self.pygame, "Surface", None)
        if surface_factory is None:
            return None
        return surface_factory((max(1, int(width)), max(1, int(height))))

    def scale_surface_nearest(self, source_surface, *, width: int, height: int):
        transform = getattr(self.pygame, "transform", None)
        if transform is not None and hasattr(transform, "scale"):
            return transform.scale(source_surface, (max(1, int(width)), max(1, int(height))))
        return source_surface

    def blit_surface(self, target_surface, source_surface, dest) -> None:
        if hasattr(target_surface, "blit"):
            target_surface.blit(source_surface, tuple(dest))

    def blit_text(self, surface, font, text: str, color, position) -> None:
        rendered = None
        if font is not None and hasattr(font, "render"):
            rendered = font.render(str(text), True, tuple(color))
        if rendered is not None and hasattr(surface, "blit"):
            surface.blit(rendered, tuple(position))

    def set_mouse_visible(self, visible: bool) -> None:
        mouse = getattr(self.pygame, "mouse", None)
        if mouse is not None and hasattr(mouse, "set_visible"):
            mouse.set_visible(bool(visible))

    def close(self) -> None:
        self.pygame.quit()
