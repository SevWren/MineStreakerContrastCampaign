"""Reusable event trace fixtures for Iter9 visual solver demo tests."""

from __future__ import annotations

import json
from typing import Any


def trace_line(**overrides: Any) -> str:
    row = {
        "schema_version": "iter9_visual_solver_event_trace.v1",
        "step": 1,
        "round": 0,
        "y": 0,
        "x": 0,
        "state": "MINE",
        "display": "flag",
        "source": "final_grid_replay",
    }
    row.update(overrides)
    return json.dumps(row)


def valid_flag_only_trace() -> str:
    return "\n".join([
        trace_line(step=1, y=0, x=0, state="MINE", display="flag"),
        trace_line(step=2, y=0, x=1, state="MINE", display="flag"),
    ]) + "\n"


def valid_safe_and_mine_trace() -> str:
    return "\n".join([
        trace_line(step=1, y=0, x=0, state="SAFE", display="reveal"),
        trace_line(step=2, y=0, x=1, state="MINE", display="flag"),
    ]) + "\n"


def trace_with_duplicate_cell() -> str:
    return "\n".join([
        trace_line(step=1, y=0, x=0),
        trace_line(step=2, y=0, x=0),
    ]) + "\n"


def trace_with_out_of_bounds_cell() -> str:
    return trace_line(step=1, y=999_999, x=999_999) + "\n"


def trace_with_unknown_state() -> str:
    return trace_line(step=1, state="NOT_A_STATE") + "\n"
