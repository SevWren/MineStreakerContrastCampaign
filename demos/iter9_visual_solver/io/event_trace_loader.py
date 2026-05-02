"""JSONL event trace loading."""

from __future__ import annotations

import json
from pathlib import Path

from demos.iter9_visual_solver.contracts.schema_versions import EVENT_TRACE_SCHEMA_VERSION
from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
from demos.iter9_visual_solver.errors.trace_errors import DemoTraceJsonError, DemoTraceValidationError


def load_event_trace(
    path: Path | str,
    *,
    board_width: int | None = None,
    board_height: int | None = None,
) -> list[PlaybackEvent]:
    trace_path = Path(path)
    events: list[PlaybackEvent] = []
    seen_steps: set[int] = set()
    for line_number, line in enumerate(trace_path.read_text(encoding="utf-8").splitlines(), start=1):
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
        if event.step in seen_steps:
            raise DemoTraceValidationError(f"{trace_path} line {line_number}: duplicate step {event.step}")
        seen_steps.add(event.step)
        if board_width is not None and event.x >= board_width:
            raise DemoTraceValidationError(f"{trace_path} line {line_number}: x out of bounds")
        if board_height is not None and event.y >= board_height:
            raise DemoTraceValidationError(f"{trace_path} line {line_number}: y out of bounds")
        events.append(event)
    return sorted(events, key=lambda event: event.step)

