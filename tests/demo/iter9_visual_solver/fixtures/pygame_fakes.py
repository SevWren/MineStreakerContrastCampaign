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

    def fill(self, color, rect=None):
        self.fill_calls.append((color, rect))

    def blit(self, source, dest):
        self.blit_calls.append((source, dest))


@dataclass
class FakeFont:
    rendered_text: list[str] = field(default_factory=list)

    def render(self, text: str, antialias: bool, color):
        self.rendered_text.append(text)
        return FakeSurface((len(text) * 8, 16))


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

    def set_mode(self, size, flags=0):
        self.created_windows.append(tuple(size))
        return FakeSurface(tuple(size))

    def set_caption(self, title: str) -> None:
        self.caption = title

    def flip(self) -> None:
        self.flipped = True


@dataclass
class FakeDraw:
    rect_calls: list[Any] = field(default_factory=list)

    def rect(self, surface, color, rect):
        self.rect_calls.append((surface, color, tuple(rect)))
        if hasattr(surface, "rect_calls"):
            surface.rect_calls.append((color, tuple(rect)))


@dataclass
class FakePygameModule:
    display: FakeDisplay = field(default_factory=FakeDisplay)
    event: FakeEventQueue = field(default_factory=FakeEventQueue)
    draw: FakeDraw = field(default_factory=FakeDraw)

    QUIT: int = 256

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
