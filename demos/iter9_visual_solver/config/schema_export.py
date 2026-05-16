"""Schema export helpers for config drift tests."""

from __future__ import annotations

from demos.iter9_visual_solver.config.models import DemoConfig


def build_config_json_schema() -> dict:
    return DemoConfig.model_json_schema()

