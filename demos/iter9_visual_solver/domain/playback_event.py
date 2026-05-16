"""Playback event model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from demos.iter9_visual_solver.contracts.schema_versions import EVENT_TRACE_SCHEMA_VERSION

STATE_DISPLAY = {
    "MINE": "flag",
    "SAFE": "reveal",
    "UNKNOWN": "unknown",
}


@dataclass(frozen=True)
class PlaybackEvent:
    step: int
    y: int
    x: int
    state: str
    display: str
    round: int = 0
    event_id: str = ""
    schema_version: str = EVENT_TRACE_SCHEMA_VERSION
    source: str | None = None
    confidence: str | None = None
    reason: str | None = None
    mine_count_after: int | None = None
    safe_count_after: int | None = None
    unknown_count_after: int | None = None
    elapsed_solver_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        state = self.state.upper()
        display = self.display
        if self.schema_version != EVENT_TRACE_SCHEMA_VERSION:
            raise ValueError(f"unsupported event schema_version: {self.schema_version}")
        if self.step < 0 or self.round < 0 or self.y < 0 or self.x < 0:
            raise ValueError("step, round, y, and x must be non-negative")
        if state not in STATE_DISPLAY:
            raise ValueError(f"unsupported playback state: {self.state}")
        if display != STATE_DISPLAY[state]:
            raise ValueError(f"{state} requires display={STATE_DISPLAY[state]}")
        object.__setattr__(self, "state", state)
        if not self.event_id:
            object.__setattr__(self, "event_id", f"evt_{self.step:06d}")
