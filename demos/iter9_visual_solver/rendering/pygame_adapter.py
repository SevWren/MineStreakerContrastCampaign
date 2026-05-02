"""Pygame adapter seam.

The module intentionally avoids importing pygame at module import time.
"""

from __future__ import annotations

import importlib


class PygameAdapter:
    def __init__(self, pygame_module=None) -> None:
        self.pygame = pygame_module if pygame_module is not None else importlib.import_module("pygame")
        self.surface = None
        self.clock = None

    def open_window(self, *, width: int, height: int, title: str, resizable: bool = False):
        self.pygame.init()
        if hasattr(self.pygame, "font") and hasattr(self.pygame.font, "init"):
            self.pygame.font.init()
        flags = getattr(self.pygame, "RESIZABLE", 0) if resizable else 0
        self.surface = self.pygame.display.set_mode((int(width), int(height)), flags)
        self.pygame.display.set_caption(title)
        self.clock = self.pygame.time.Clock()
        return self.surface

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

    def draw_rect(self, surface, color, rect) -> None:
        if hasattr(self.pygame, "draw") and hasattr(self.pygame.draw, "rect"):
            self.pygame.draw.rect(surface, tuple(color), tuple(rect))

    def close(self) -> None:
        self.pygame.quit()
