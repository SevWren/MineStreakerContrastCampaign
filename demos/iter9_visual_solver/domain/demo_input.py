"""Aggregate of loaded inputs needed to launch the demo."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from demos.iter9_visual_solver.domain.board_dimensions import BoardDimensions
from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent


@dataclass(frozen=True)
class DemoInput:
    grid: Any
    metrics: dict
    board_dimensions: BoardDimensions
    grid_path: Path
    metrics_path: Path
    event_trace_path: Path | None = None
    trace_events: list[PlaybackEvent] | None = None

