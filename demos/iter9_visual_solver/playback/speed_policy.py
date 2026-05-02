"""Playback speed policy."""

from __future__ import annotations

from typing import Any


def _get(config: Any, name: str):
    if isinstance(config, dict):
        return config[name]
    return getattr(config, name)


def calculate_events_per_second(playback_config: Any, *, total_mines: int) -> int:
    if total_mines < 0:
        raise ValueError("total_mines must be non-negative")
    calculated = _get(playback_config, "base_events_per_second") + total_mines * _get(
        playback_config,
        "mine_count_multiplier",
    )
    clamped = min(_get(playback_config, "max_events_per_second"), max(_get(playback_config, "min_events_per_second"), calculated))
    return int(round(clamped))

