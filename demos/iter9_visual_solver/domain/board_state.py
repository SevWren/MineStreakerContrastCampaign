"""Mutable replay board state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
from demos.iter9_visual_solver.playback.event_source import STATE_MINE, STATE_SAFE, STATE_TO_CODE


@dataclass
class BoardState:
    width: int
    height: int
    cells: dict[tuple[int, int], str] = field(default_factory=dict)
    _grid: np.ndarray = field(init=False, repr=False)
    _mines_flagged: int = field(default=0, init=False)
    _safe_cells_solved: int = field(default=0, init=False)
    _known_cells: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        self.width = int(self.width)
        self.height = int(self.height)
        self._grid = np.zeros((self.height, self.width), dtype=np.uint8)
        if self.cells:
            existing = dict(self.cells)
            self.cells.clear()
            for (y, x), state in existing.items():
                self._apply_code(int(y), int(x), STATE_TO_CODE[str(state).upper()])

    @classmethod
    def empty(cls, width: int, height: int) -> "BoardState":
        return cls(width=int(width), height=int(height))

    @property
    def total_cells(self) -> int:
        return self.width * self.height

    @property
    def mines_flagged(self) -> int:
        return self._mines_flagged

    @property
    def safe_cells_solved(self) -> int:
        return self._safe_cells_solved

    @property
    def unknown_remaining(self) -> int:
        return max(self.total_cells - self._known_cells, 0)

    def apply(self, event: PlaybackEvent) -> None:
        self._apply_code(int(event.y), int(event.x), STATE_TO_CODE[event.state])

    def apply_batch(self, events: Any) -> None:
        if hasattr(events, "y") and hasattr(events, "x") and hasattr(events, "state_codes"):
            for y, x, code in zip(events.y, events.x, events.state_codes):
                self._apply_code(int(y), int(x), int(code))
            return
        for event in events:
            self.apply(event)

    def _apply_code(self, y: int, x: int, code: int) -> None:
        if y >= self.height or x >= self.width or y < 0 or x < 0:
            raise ValueError(f"event coordinate out of bounds: ({y}, {x})")
        previous = int(self._grid[y, x])
        if previous == code:
            return
        if previous == STATE_MINE:
            self._mines_flagged -= 1
        elif previous == STATE_SAFE:
            self._safe_cells_solved -= 1
        elif previous == 0 and code != 0:
            self._known_cells += 1
        if previous != 0 and code == 0:
            self._known_cells -= 1
        if code == STATE_MINE:
            self._mines_flagged += 1
            self.cells[(y, x)] = "MINE"
        elif code == STATE_SAFE:
            self._safe_cells_solved += 1
            self.cells[(y, x)] = "SAFE"
        else:
            self.cells.pop((y, x), None)
        self._grid[y, x] = np.uint8(code)
