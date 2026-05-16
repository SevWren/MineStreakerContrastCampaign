"""JSONL event trace loading."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from demos.iter9_visual_solver.contracts.schema_versions import EVENT_TRACE_SCHEMA_VERSION
from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
from demos.iter9_visual_solver.errors.trace_errors import DemoTraceJsonError, DemoTraceValidationError
from demos.iter9_visual_solver.playback.event_source import (
    STATE_TO_CODE,
    TypedPlaybackEventStore,
    UINT32_MAX,
)


def load_event_trace(
    path: Path | str,
    *,
    board_width: int | None = None,
    board_height: int | None = None,
) -> list[PlaybackEvent]:
    return list(_iter_validated_event_trace(path, board_width=board_width, board_height=board_height))


def load_typed_event_trace(
    path: Path | str,
    *,
    board_width: int | None = None,
    board_height: int | None = None,
) -> TypedPlaybackEventStore:
    events = _iter_validated_event_trace(path, board_width=board_width, board_height=board_height)
    steps: list[int] = []
    y_values: list[int] = []
    x_values: list[int] = []
    state_codes: list[int] = []
    max_x = 0
    max_y = 0
    for event in events:
        steps.append(event.step)
        y_values.append(event.y)
        x_values.append(event.x)
        state_codes.append(STATE_TO_CODE[event.state])
        max_x = max(max_x, event.x)
        max_y = max(max_y, event.y)
    return TypedPlaybackEventStore(
        steps=np.asarray(steps, dtype=np.uint32),
        y=np.asarray(y_values, dtype=np.uint32),
        x=np.asarray(x_values, dtype=np.uint32),
        state_codes=np.asarray(state_codes, dtype=np.uint8),
        board_width=int(board_width if board_width is not None else max_x + 1),
        board_height=int(board_height if board_height is not None else max_y + 1),
        source="solver_event_trace",
    )


def _iter_validated_event_trace(
    path: Path | str,
    *,
    board_width: int | None = None,
    board_height: int | None = None,
):
    trace_path = Path(path)
    previous_step: int | None = None
    with trace_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DemoTraceJsonError(f"Invalid JSON in {trace_path} line {line_number}: {exc}") from exc
            if row.get("schema_version") != EVENT_TRACE_SCHEMA_VERSION:
                raise DemoTraceValidationError(f"{trace_path} line {line_number}: invalid schema_version")
            if "event_id" not in row:
                row["event_id"] = f"evt_{int(row.get('step', line_number)):06d}"
            try:
                event = PlaybackEvent(**row)
            except Exception as exc:
                raise DemoTraceValidationError(f"{trace_path} line {line_number}: {exc}") from exc
            if event.step > UINT32_MAX or event.y > UINT32_MAX or event.x > UINT32_MAX:
                raise DemoTraceValidationError(f"{trace_path} line {line_number}: uint32 overflow")
            if previous_step is not None and event.step <= previous_step:
                problem = "duplicate" if event.step == previous_step else "decreasing"
                raise DemoTraceValidationError(f"{trace_path} line {line_number}: {problem} step {event.step}")
            previous_step = event.step
            if board_width is not None and event.x >= board_width:
                raise DemoTraceValidationError(f"{trace_path} line {line_number}: x out of bounds")
            if board_height is not None and event.y >= board_height:
                raise DemoTraceValidationError(f"{trace_path} line {line_number}: y out of bounds")
            yield event
