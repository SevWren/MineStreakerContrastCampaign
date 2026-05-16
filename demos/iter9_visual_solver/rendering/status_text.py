"""Status line formatting."""

from __future__ import annotations

from typing import Any


def _value(snapshot: Any, name: str, default=None):
    if isinstance(snapshot, dict):
        return snapshot.get(name, default)
    return getattr(snapshot, name, default)


def build_status_lines(snapshot: Any, status_config: Any | None = None) -> list[str]:
    total_cells = int(_value(snapshot, "total_cells", 0) or 0)
    total_mines = int(_value(snapshot, "total_mines", 0) or 0)
    safe_cells = int(_value(snapshot, "safe_cells", max(total_cells - total_mines, 0)) or 0)
    events_per_second = _value(snapshot, "events_per_second", _value(snapshot, "playback_speed", 0))
    lines = [
        f"Source image: {_value(snapshot, 'source_image_name', 'unknown') or 'unknown'}",
        f"Board: {_value(snapshot, 'board_width')} x {_value(snapshot, 'board_height')}",
        f"Seed: {_value(snapshot, 'seed')}",
        f"Total cells: {total_cells}",
        f"Mines flagged: {_value(snapshot, 'mines_flagged')} / {total_mines}",
        f"Safe cells solved: {_value(snapshot, 'safe_cells_solved')} / {safe_cells}",
        f"Unknown remaining: {_value(snapshot, 'unknown_remaining')}",
        f"Playback speed: {events_per_second} cells/sec",
        f"Elapsed time: {_value(snapshot, 'elapsed_seconds', 0):.2f}s",
        f"Finish: {_value(snapshot, 'finish_state')}",
    ]
    if status_config is None:
        return lines
    visibility = [
        "show_source_image",
        "show_board_dimensions",
        "show_seed",
        "show_total_cells",
        "show_mines_flagged",
        "show_safe_cells_solved",
        "show_unknown_remaining",
        "show_playback_speed",
        "show_elapsed_time",
        "show_finish_message",
    ]
    visible: list[str] = []
    for line, key in zip(lines, visibility):
        enabled = status_config.get(key, True) if isinstance(status_config, dict) else getattr(status_config, key)
        if enabled:
            visible.append(line)
    return visible
