"""Finish behavior policy."""

from __future__ import annotations

from typing import Any


def _get(config: Any, name: str):
    if isinstance(config, dict):
        return config.get(name)
    return getattr(config, name)


def should_auto_close(finish_config: Any, *, elapsed_after_finish_s: float) -> bool:
    mode = _get(finish_config, "mode")
    if mode == "stay_open":
        return False
    if mode == "close_immediately":
        return True
    if mode == "close_after_delay":
        delay = _get(finish_config, "close_after_seconds")
        if delay is None:
            raise ValueError("close_after_seconds is required for close_after_delay")
        return elapsed_after_finish_s >= float(delay)
    raise ValueError(f"Unknown finish behavior mode: {mode}")

