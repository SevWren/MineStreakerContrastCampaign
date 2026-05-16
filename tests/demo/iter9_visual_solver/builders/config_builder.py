"""Builder for demo config test data."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tests.demo.iter9_visual_solver.fixtures.configs import default_demo_config_dict
from demos.iter9_visual_solver.config.models import DemoConfig


class DemoConfigBuilder:
    def __init__(self) -> None:
        self._config: dict[str, Any] = default_demo_config_dict()

    def with_finish_mode(self, mode: str, close_after_seconds: float | None = None) -> "DemoConfigBuilder":
        self._config["window"]["finish_behavior"]["mode"] = mode
        self._config["window"]["finish_behavior"]["close_after_seconds"] = close_after_seconds
        return self

    def with_base_events_per_second(self, value: int) -> "DemoConfigBuilder":
        self._config["playback"]["base_events_per_second"] = int(value)
        return self

    def with_mine_count_multiplier(self, value: float) -> "DemoConfigBuilder":
        self._config["playback"]["mine_count_multiplier"] = float(value)
        return self

    def with_max_events_per_second(self, value: int) -> "DemoConfigBuilder":
        self._config["playback"]["max_events_per_second"] = int(value)
        return self

    def with_min_events_per_second(self, value: int) -> "DemoConfigBuilder":
        self._config["playback"]["min_events_per_second"] = int(value)
        return self

    def with_playback_mode(self, value: str) -> "DemoConfigBuilder":
        self._config["playback"]["mode"] = value
        return self

    def build_dict(self) -> dict[str, Any]:
        return deepcopy(self._config)

    def build(self) -> DemoConfig:
        return DemoConfig.model_validate(self.build_dict())
