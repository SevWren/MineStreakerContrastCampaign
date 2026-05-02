"""Builder for solver event trace JSONL content."""

from __future__ import annotations

import json
from typing import Any


class EventTraceBuilder:
    def __init__(self, board_height: int = 6, board_width: int = 8) -> None:
        self.board_height = int(board_height)
        self.board_width = int(board_width)
        self._rows: list[dict[str, Any]] = []

    def flag(self, y: int, x: int, *, round_id: int = 0) -> "EventTraceBuilder":
        return self._add(y, x, state="MINE", display="flag", round_id=round_id)

    def safe(self, y: int, x: int, *, round_id: int = 0) -> "EventTraceBuilder":
        return self._add(y, x, state="SAFE", display="reveal", round_id=round_id)

    def unknown(self, y: int, x: int, *, round_id: int = 0) -> "EventTraceBuilder":
        return self._add(y, x, state="UNKNOWN", display="unknown", round_id=round_id)

    def _add(self, y: int, x: int, *, state: str, display: str, round_id: int) -> "EventTraceBuilder":
        self._rows.append({
            "schema_version": "iter9_visual_solver_event_trace.v1",
            "step": len(self._rows) + 1,
            "round": int(round_id),
            "y": int(y),
            "x": int(x),
            "state": state,
            "display": display,
            "source": "solver_trace",
        })
        return self

    def build_rows(self) -> list[dict[str, Any]]:
        return list(self._rows)

    def build_jsonl(self) -> str:
        return "\n".join(json.dumps(row) for row in self._rows) + ("\n" if self._rows else "")
