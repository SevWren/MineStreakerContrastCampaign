"""Builder for status snapshot test data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StatusSnapshotFixture:
    source_image_name: str = "line_art_irl_11_v2.png"
    board_width: int = 300
    board_height: int = 942
    seed: int = 11
    total_cells: int = 282600
    mines_flagged: int = 0
    total_mines: int = 0
    safe_cells_solved: int = 0
    unknown_remaining: int = 0
    playback_speed: int = 1000
    finish_state: str = "running"


class StatusSnapshotBuilder:
    def __init__(self) -> None:
        self._values = StatusSnapshotFixture().__dict__.copy()

    def with_board(self, width: int, height: int) -> "StatusSnapshotBuilder":
        self._values["board_width"] = int(width)
        self._values["board_height"] = int(height)
        self._values["total_cells"] = int(width) * int(height)
        return self

    def with_playback_speed(self, speed: int) -> "StatusSnapshotBuilder":
        self._values["playback_speed"] = int(speed)
        return self

    def with_flagged_mines(self, flagged: int, total_mines: int) -> "StatusSnapshotBuilder":
        self._values["mines_flagged"] = int(flagged)
        self._values["total_mines"] = int(total_mines)
        return self

    def build(self) -> StatusSnapshotFixture:
        return StatusSnapshotFixture(**self._values)
