"""JSONL event trace writing."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from demos.iter9_visual_solver.contracts.schema_versions import EVENT_TRACE_SCHEMA_VERSION


def _row_from_event(event: Any) -> dict:
    if is_dataclass(event):
        row = asdict(event)
    elif isinstance(event, dict):
        row = dict(event)
    else:
        row = dict(vars(event))
    row.setdefault("schema_version", EVENT_TRACE_SCHEMA_VERSION)
    row.setdefault("event_id", f"evt_{int(row.get('step', 0)):06d}")
    return row


def write_event_trace(path: Path | str, events=None) -> None:
    if isinstance(path, list):
        path, events = events, path
    if events is None:
        events = []
    trace_path = Path(path)
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = trace_path.with_suffix(trace_path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(json.dumps(_row_from_event(event), sort_keys=True))
            handle.write("\n")
    os.replace(tmp_path, trace_path)
