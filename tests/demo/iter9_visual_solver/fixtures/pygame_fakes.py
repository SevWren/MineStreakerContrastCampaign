"""Fake pygame seams for tests that must not open a real pygame window."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeClock:
    ticks: list[int] = field(default_factory=list)

    def tick(self, fps: int) -> int:
        self.ticks.append(int(fps))
        return int(1000 / max(int(fps), 1))


@dataclass
class FakeSurface:
    size: tuple[int, int]
    fill_calls: list[Any] = field(default_factory=list)
    blit_calls: list[Any] = field(default_factory=list)
    rect_calls: list[Any] = field(default_factory=list)
    scaled_from: Any = None

    def fill(self, color, rect=None):
        self.fill_calls.append((color, rect))

    def blit(self, source, dest):
        self.blit_calls.append((source, dest))

    def get_size(self):
        return self.size


@dataclass
class FakeFont:
    rendered_text: list[str] = field(default_factory=list)

    def render(self, text: str, antialias: bool, color):
        self.rendered_text.append(text)
        return FakeSurface((len(text) * 8, 16))

    def size(self, text: str):
        return (len(str(text)) * 8, 16)

    def get_linesize(self):
        return 16


@dataclass
class FakeEventQueue:
    events: list[Any] = field(default_factory=list)

    def get(self):
        events = list(self.events)
        self.events.clear()
        return events


@dataclass
class FakeDisplay:
    created_windows: list[tuple[int, int]] = field(default_factory=list)
    set_mode_calls: list[Any] = field(default_factory=list)
    desktop_sizes: list[tuple[int, int]] = field(default_factory=lambda: [(1280, 720)])
    position_calls: list[tuple[int, int]] = field(default_factory=list)

    def set_mode(self, size, flags=0):
        self.created_windows.append(tuple(size))
        self.set_mode_calls.append((tuple(size), flags))
        self.surface = FakeSurface(tuple(size))
        return self.surface

    def set_caption(self, title: str) -> None:
        self.caption = title

    def flip(self) -> None:
        self.flipped = True

    def get_desktop_sizes(self):
        return list(self.desktop_sizes)

    def Info(self):
        width, height = self.desktop_sizes[0] if self.desktop_sizes else (0, 0)
        return type("FakeDisplayInfo", (), {"current_w": width, "current_h": height})()

    def set_window_position(self, position) -> None:
        x, y = position
        self.position_calls.append((int(x), int(y)))


@dataclass
class FakeDraw:
    rect_calls: list[Any] = field(default_factory=list)
    line_calls: list[Any] = field(default_factory=list)

    def rect(self, surface, color, rect, width=0, border_radius=0):
        self.rect_calls.append((surface, color, tuple(rect), int(width), int(border_radius)))
        if hasattr(surface, "rect_calls"):
            surface.rect_calls.append((color, tuple(rect)))

    def line(self, surface, color, start_pos, end_pos, width=1):
        self.line_calls.append((surface, color, tuple(start_pos), tuple(end_pos), int(width)))


@dataclass
class FakeTransform:
    scale_calls: list[Any] = field(default_factory=list)

    def scale(self, source, size):
        self.scale_calls.append((source, tuple(size)))
        return FakeSurface(tuple(size), scaled_from=source)


@dataclass
class FakePygameModule:
    display: FakeDisplay = field(default_factory=FakeDisplay)
    event: FakeEventQueue = field(default_factory=FakeEventQueue)
    draw: FakeDraw = field(default_factory=FakeDraw)
    transform: FakeTransform = field(default_factory=FakeTransform)

    QUIT: int = 256
    VIDEORESIZE: int = 32769
    WINDOWRESIZED: int = 32778
    WINDOWSIZECHANGED: int = 32780
    WINDOWMAXIMIZED: int = 32781
    RESIZABLE: int = 16
    surface_calls: list[tuple[int, int]] = field(default_factory=list)

    def Surface(self, size):
        self.surface_calls.append(tuple(size))
        return FakeSurface(tuple(size))

    def init(self) -> None:
        self.initialized = True

    def quit(self) -> None:
        self.quit_called = True

    class time:
        Clock = FakeClock

    class font:
        @staticmethod
        def SysFont(name, size):
            return FakeFont()

    class mouse:
        visible: bool = True

        @classmethod
        def set_visible(cls, visible: bool) -> None:
            cls.visible = bool(visible)
