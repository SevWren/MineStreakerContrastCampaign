"""Playback event source selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent

UINT32_MAX = int(np.iinfo(np.uint32).max)
STATE_UNKNOWN = 0
STATE_SAFE = 1
STATE_MINE = 2
STATE_TO_CODE = {
    "UNKNOWN": STATE_UNKNOWN,
    "SAFE": STATE_SAFE,
    "MINE": STATE_MINE,
}
CODE_TO_STATE = {
    STATE_UNKNOWN: "UNKNOWN",
    STATE_SAFE: "SAFE",
    STATE_MINE: "MINE",
}


def _get(config: Any, name: str):
    if isinstance(config, dict):
        return config[name]
    return getattr(config, name)


def _validate_uint32(value: int, label: str) -> int:
    value = int(value)
    if value < 0 or value > UINT32_MAX:
        raise ValueError(f"{label}={value} exceeds uint32 playback storage")
    return value


def _display_for_code(code: int) -> str:
    state = CODE_TO_STATE[int(code)]
    return "flag" if state == "MINE" else "reveal" if state == "SAFE" else "unknown"


@dataclass(frozen=True)
class PlaybackEventBatch:
    """Lightweight view over typed playback event arrays."""

    steps: np.ndarray
    y: np.ndarray
    x: np.ndarray
    state_codes: np.ndarray
    source: str = ""

    def __len__(self) -> int:
        return int(self.steps.shape[0])

    def __iter__(self):
        for index in range(len(self)):
            code = int(self.state_codes[index])
            state = CODE_TO_STATE[code]
            yield PlaybackEvent(
                step=int(self.steps[index]),
                round=0,
                y=int(self.y[index]),
                x=int(self.x[index]),
                state=state,
                display=_display_for_code(code),
                source=self.source or None,
            )

    def __getitem__(self, index: int) -> PlaybackEvent:
        if isinstance(index, slice):
            return list(self)[index]
        if index < 0:
            index += len(self)
        if index < 0 or index >= len(self):
            raise IndexError(index)
        code = int(self.state_codes[index])
        state = CODE_TO_STATE[code]
        return PlaybackEvent(
            step=int(self.steps[index]),
            round=0,
            y=int(self.y[index]),
            x=int(self.x[index]),
            state=state,
            display=_display_for_code(code),
            source=self.source or None,
        )


@dataclass(frozen=True)
class TypedPlaybackEventStore:
    steps: np.ndarray
    y: np.ndarray
    x: np.ndarray
    state_codes: np.ndarray
    board_width: int
    board_height: int
    source: str = ""

    def __post_init__(self) -> None:
        lengths = {len(self.steps), len(self.y), len(self.x), len(self.state_codes)}
        if len(lengths) != 1:
            raise ValueError("typed playback arrays must have equal length")
        object.__setattr__(self, "steps", np.asarray(self.steps, dtype=np.uint32))
        object.__setattr__(self, "y", np.asarray(self.y, dtype=np.uint32))
        object.__setattr__(self, "x", np.asarray(self.x, dtype=np.uint32))
        object.__setattr__(self, "state_codes", np.asarray(self.state_codes, dtype=np.uint8))
        width = _validate_uint32(self.board_width, "board_width")
        height = _validate_uint32(self.board_height, "board_height")
        object.__setattr__(self, "board_width", width)
        object.__setattr__(self, "board_height", height)
        if len(self.x) and int(np.max(self.x)) >= width:
            raise ValueError("typed playback x coordinate out of bounds")
        if len(self.y) and int(np.max(self.y)) >= height:
            raise ValueError("typed playback y coordinate out of bounds")
        bad_codes = np.setdiff1d(self.state_codes, np.array(list(CODE_TO_STATE), dtype=np.uint8))
        if len(bad_codes):
            raise ValueError(f"typed playback state code out of range: {int(bad_codes[0])}")

    def __len__(self) -> int:
        return int(self.steps.shape[0])

    @property
    def total_count(self) -> int:
        return len(self)

    @property
    def mine_count(self) -> int:
        return int(np.count_nonzero(self.state_codes == STATE_MINE))

    def batch(self, start: int, end: int) -> PlaybackEventBatch:
        start = max(0, int(start))
        end = min(len(self), int(end))
        return PlaybackEventBatch(
            steps=self.steps[start:end],
            y=self.y[start:end],
            x=self.x[start:end],
            state_codes=self.state_codes[start:end],
            source=self.source,
        )

    def __iter__(self):
        return iter(self.batch(0, len(self)))


@dataclass(frozen=True)
class FinalGridPlaybackEventStore:
    """Lazy row-major event store backed by the final grid."""

    grid: Any
    source: str = "final_grid_replay"

    def __post_init__(self) -> None:
        shape = getattr(self.grid, "shape", None)
        if shape is None or len(shape) != 2:
            raise ValueError("grid must be 2D")
        height, width = int(shape[0]), int(shape[1])
        _validate_uint32(width, "board_width")
        _validate_uint32(height, "board_height")
        total = int(width) * int(height)
        _validate_uint32(total - 1 if total else 0, "step")
        object.__setattr__(self, "board_width", width)
        object.__setattr__(self, "board_height", height)
        object.__setattr__(self, "_grid", np.asarray(self.grid))
        object.__setattr__(self, "_mine_count", int(np.count_nonzero(np.asarray(self.grid) != 0)))

    def __len__(self) -> int:
        return int(self.board_width) * int(self.board_height)

    @property
    def total_count(self) -> int:
        return len(self)

    @property
    def mine_count(self) -> int:
        return int(self._mine_count)

    def batch(self, start: int, end: int) -> PlaybackEventBatch:
        start = max(0, int(start))
        end = min(len(self), int(end))
        steps = np.arange(start, end, dtype=np.uint32)
        y = (steps // np.uint32(self.board_width)).astype(np.uint32, copy=False)
        x = (steps % np.uint32(self.board_width)).astype(np.uint32, copy=False)
        state_codes = np.where(self._grid[y, x] != 0, STATE_MINE, STATE_SAFE).astype(np.uint8, copy=False)
        return PlaybackEventBatch(steps=steps, y=y, x=x, state_codes=state_codes, source=self.source)

    def __iter__(self):
        return iter(self.batch(0, len(self)))


def build_typed_playback_event_store(events: list[PlaybackEvent], *, board_width: int, board_height: int) -> TypedPlaybackEventStore:
    steps = np.empty(len(events), dtype=np.uint32)
    y = np.empty(len(events), dtype=np.uint32)
    x = np.empty(len(events), dtype=np.uint32)
    state_codes = np.empty(len(events), dtype=np.uint8)
    for index, event in enumerate(events):
        steps[index] = _validate_uint32(event.step, "step")
        y[index] = _validate_uint32(event.y, "y")
        x[index] = _validate_uint32(event.x, "x")
        state_codes[index] = STATE_TO_CODE[event.state]
    return TypedPlaybackEventStore(
        steps=steps,
        y=y,
        x=x,
        state_codes=state_codes,
        board_width=board_width,
        board_height=board_height,
        source="solver_event_trace",
    )


def build_lazy_playback_events_from_final_grid(grid: Any) -> FinalGridPlaybackEventStore:
    return FinalGridPlaybackEventStore(grid)


def build_playback_events_from_final_grid(grid: Any) -> list[PlaybackEvent]:
    return list(build_lazy_playback_events_from_final_grid(grid))


def select_event_source(
    *,
    input_config: Any,
    grid: Any,
    trace_events: Any | None,
) -> tuple[Any, str]:
    if _get(input_config, "prefer_solver_event_trace") and trace_events:
        return trace_events, "solver_event_trace"
    if _get(input_config, "allow_final_grid_replay_fallback"):
        return build_lazy_playback_events_from_final_grid(grid), "final_grid_replay"
    raise ValueError("No solver event trace is available and final-grid replay fallback is disabled")
