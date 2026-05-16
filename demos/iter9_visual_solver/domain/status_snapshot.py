"""Status panel data snapshot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatusSnapshot:
    source_image_name: str
    board_width: int
    board_height: int
    seed: int
    total_cells: int
    mines_flagged: int
    total_mines: int
    safe_cells_solved: int
    safe_cells: int
    unknown_remaining: int
    events_per_second: int
    finish_state: str
    replay_source: str = ""
    elapsed_seconds: float = 0.0

    @property
    def playback_speed(self) -> int:
        return self.events_per_second
