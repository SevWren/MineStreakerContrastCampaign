"""Playback speed policy."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from demos.iter9_visual_solver.config.models import PlaybackConfig


def calculate_events_per_second(playback_config: "PlaybackConfig", *, total_mines: int) -> int:
    if isinstance(playback_config, dict):
        raise TypeError("playback_config must be a validated PlaybackConfig object, not a dict")
    if total_mines < 0:
        raise ValueError(f"total_mines={total_mines} must be >= 0")
    if playback_config.mode != "mine_count_scaled":
        raise ValueError(f"playback.mode={playback_config.mode!r} must be 'mine_count_scaled'")
    if playback_config.min_events_per_second > playback_config.max_events_per_second:
        raise ValueError(
            "playback.min_events_per_second must be <= playback.max_events_per_second "
            f"(got {playback_config.min_events_per_second} > {playback_config.max_events_per_second})"
        )
    calculated = playback_config.base_events_per_second + total_mines * playback_config.mine_count_multiplier
    clamped = min(
        playback_config.max_events_per_second,
        max(playback_config.min_events_per_second, calculated),
    )
    return int(round(clamped))
