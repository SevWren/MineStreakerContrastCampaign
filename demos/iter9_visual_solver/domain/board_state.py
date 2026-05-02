"""Mutable replay board state."""

from __future__ import annotations

from dataclasses import dataclass, field

from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent


@dataclass
class BoardState:
    width: int
    height: int
    cells: dict[tuple[int, int], str] = field(default_factory=dict)

    @classmethod
    def empty(cls, width: int, height: int) -> "BoardState":
        return cls(width=int(width), height=int(height))

    @property
    def total_cells(self) -> int:
        return self.width * self.height

    @property
    def mines_flagged(self) -> int:
        return sum(1 for state in self.cells.values() if state == "MINE")

    @property
    def safe_cells_solved(self) -> int:
        return sum(1 for state in self.cells.values() if state == "SAFE")

    @property
    def unknown_remaining(self) -> int:
        return max(self.total_cells - len(self.cells), 0)

    def apply(self, event: PlaybackEvent) -> None:
        if event.y >= self.height or event.x >= self.width:
            raise ValueError(f"event coordinate out of bounds: ({event.y}, {event.x})")
        self.cells[(event.y, event.x)] = event.state

