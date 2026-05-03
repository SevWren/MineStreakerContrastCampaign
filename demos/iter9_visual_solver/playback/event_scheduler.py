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
        if self.events_per_frame <= 0:
            raise ValueError(f"events_per_frame={self.events_per_frame} must be > 0")
        self.events_per_frame = int(self.events_per_frame)

    @property
    def finished(self) -> bool:
        return self._index >= len(self.events)

    @property
    def applied_count(self) -> int:
        return self._index

    @property
    def total_count(self) -> int:
        return len(self.events)

    def next_batch(self) -> list[Any]:
        if self.finished:
            return []
        start = self._index
        end = min(len(self.events), start + self.events_per_frame)
        self._index = end
        return self.events[start:end]
