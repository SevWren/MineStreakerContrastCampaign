"""Replay state mutation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from demos.iter9_visual_solver.domain.board_state import BoardState
from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
from demos.iter9_visual_solver.domain.status_snapshot import StatusSnapshot


@dataclass
class ReplayState:
    events: list[PlaybackEvent] = field(default_factory=list)
    total_events: int | None = None
    board_width: int = 0
    board_height: int = 0
    source_image_name: str = ""
    seed: int = 0
    events_per_second: int = 0
    replay_source: str = ""
    _applied: int = field(default=0, init=False)
    _board: BoardState = field(init=False)
    _total_mines: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.total_events is not None and not self.events:
            self.events = []
        if not self.board_width and self.events:
            self.board_width = max(event.x for event in self.events) + 1
        if not self.board_height and self.events:
            self.board_height = max(event.y for event in self.events) + 1
        self._board = BoardState.empty(width=max(self.board_width, 1), height=max(self.board_height, 1))
        self._total_mines = sum(1 for event in self.events if event.state == "MINE")

    @property
    def finished(self) -> bool:
        if self.total_events is not None and not self.events:
            return self.total_events == 0
        return self._applied >= len(self.events)

    @property
    def applied_count(self) -> int:
        return self._applied

    @property
    def total_count(self) -> int:
        if self.total_events is not None:
            return self.total_events
        return len(self.events)

    @property
    def board(self) -> BoardState:
        return self._board

    def apply(self, event: PlaybackEvent) -> None:
        self._board.apply(event)
        self._applied += 1

    def apply_batch(self, events: list[PlaybackEvent]) -> None:
        for event in events:
            self.apply(event)

    def snapshot(self, *, finish_state: str = "running", elapsed_seconds: float = 0.0) -> StatusSnapshot:
        return StatusSnapshot(
            source_image_name=self.source_image_name,
            board_width=self._board.width,
            board_height=self._board.height,
            seed=self.seed,
            total_cells=self._board.total_cells,
            mines_flagged=self._board.mines_flagged,
            total_mines=self._total_mines,
            safe_cells_solved=self._board.safe_cells_solved,
            safe_cells=max(self._board.total_cells - self._total_mines, 0),
            unknown_remaining=self._board.unknown_remaining,
            events_per_second=self.events_per_second,
            finish_state=finish_state,
            replay_source=self.replay_source,
            elapsed_seconds=elapsed_seconds,
        )
