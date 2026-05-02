"""Reusable config fixtures for Iter9 visual solver demo tests.

These fixtures intentionally centralize config setup so individual test files do
not copy/paste large JSON dictionaries.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def default_demo_config_dict() -> dict[str, Any]:
    """Return a valid baseline demo config dictionary."""
    return {
        "schema_version": "iter9_visual_solver_demo_config.v1",
        "window": {
            "title": "Mine-Streaker Iter9 Visual Solver Demo",
            "resizable": False,
            "max_screen_fraction": 0.92,
            "status_panel_width_px": 360,
            "minimum_board_cell_px": 1,
            "preferred_board_cell_px": 2,
            "fit_to_screen": True,
            "center_window": True,
            "finish_behavior": {
                "mode": "stay_open",
                "close_after_seconds": None,
            },
        },
        "playback": {
            "mode": "mine_count_scaled",
            "min_events_per_second": 50,
            "base_events_per_second": 1000,
            "mine_count_multiplier": 0.08,
            "max_events_per_second": 12000,
            "target_fps": 60,
            "batch_events_per_frame": True,
        },
        "visuals": {
            "unseen_cell_rgb": [18, 18, 18],
            "flagged_mine_rgb": [255, 80, 40],
            "safe_cell_rgb": [95, 95, 95],
            "unknown_cell_rgb": [60, 100, 230],
            "background_rgb": [10, 10, 10],
            "show_safe_cells": False,
            "show_unknown_cells": True,
        },
        "status_panel": {
            "show_source_image": True,
            "show_board_dimensions": True,
            "show_seed": True,
            "show_total_cells": True,
            "show_mines_flagged": True,
            "show_safe_cells_solved": True,
            "show_unknown_remaining": True,
            "show_playback_speed": True,
            "show_elapsed_time": True,
            "show_finish_message": True,
        },
        "input": {
            "prefer_solver_event_trace": True,
            "allow_final_grid_replay_fallback": True,
        },
    }


def config_with_finish_mode(mode: str, close_after_seconds: float | None = None) -> dict[str, Any]:
    config = deepcopy(default_demo_config_dict())
    config["window"]["finish_behavior"]["mode"] = mode
    config["window"]["finish_behavior"]["close_after_seconds"] = close_after_seconds
    return config


def config_with_playback_multiplier(value: float) -> dict[str, Any]:
    config = deepcopy(default_demo_config_dict())
    config["playback"]["mine_count_multiplier"] = value
    return config


def invalid_config_missing_schema_version() -> dict[str, Any]:
    config = deepcopy(default_demo_config_dict())
    config.pop("schema_version", None)
    return config


def invalid_config_bad_rgb_tuple() -> dict[str, Any]:
    config = deepcopy(default_demo_config_dict())
    config["visuals"]["flagged_mine_rgb"] = [255, 80]
    return config


def invalid_config_negative_speed() -> dict[str, Any]:
    config = deepcopy(default_demo_config_dict())
    config["playback"]["base_events_per_second"] = -1
    return config
