"""Playback event source selection."""

from __future__ import annotations

from typing import Any

from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent


def _get(config: Any, name: str):
    if isinstance(config, dict):
        return config[name]
    return getattr(config, name)


def build_playback_events_from_final_grid(grid: Any) -> list[PlaybackEvent]:
    events: list[PlaybackEvent] = []
    height, width = grid.shape
    for y in range(int(height)):
        for x in range(int(width)):
            state = "MINE" if int(grid[y, x]) != 0 else "SAFE"
            step = len(events)
            events.append(
                PlaybackEvent(
                    step=step,
                    round=0,
                    y=y,
                    x=x,
                    state=state,
                    display="flag" if state == "MINE" else "reveal",
                    source="final_grid_replay",
                    confidence="known_from_final_grid",
                    reason="final_grid_replay",
                ),
            )
    return events


def select_event_source(
    *,
    input_config: Any,
    grid: Any,
    trace_events: list[PlaybackEvent] | None,
) -> tuple[list[PlaybackEvent], str]:
    if _get(input_config, "prefer_solver_event_trace") and trace_events:
        return list(trace_events), "solver_event_trace"
    if _get(input_config, "allow_final_grid_replay_fallback"):
        return build_playback_events_from_final_grid(grid), "final_grid_replay"
    raise ValueError("No solver event trace is available and final-grid replay fallback is disabled")
