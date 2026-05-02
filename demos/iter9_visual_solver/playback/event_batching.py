"""Playback event batching policy."""

from __future__ import annotations

import math


def calculate_events_per_frame(
    *,
    events_per_second: int,
    target_fps: int,
    batch_events_per_frame: bool = True,
) -> int:
    if events_per_second <= 0:
        raise ValueError("events_per_second must be positive")
    if target_fps <= 0:
        raise ValueError("target_fps must be positive")
    if not batch_events_per_frame:
        return 1
    return max(1, int(math.ceil(events_per_second / target_fps)))
