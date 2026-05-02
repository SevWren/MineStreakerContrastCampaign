"""Deterministic event scheduler."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EventScheduler:
    events: list[Any]
    events_per_frame: int = 1
    _index: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.events_per_frame = max(1, int(self.events_per_frame))

    @property
    def finished(self) -> bool:
        return self._index >= len(self.events)

    def next_batch(self) -> list[Any]:
        if self.finished:
            return []
        start = self._index
        end = min(len(self.events), start + self.events_per_frame)
        self._index = end
        return self.events[start:end]

