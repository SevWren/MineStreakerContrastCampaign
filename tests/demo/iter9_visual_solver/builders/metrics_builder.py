"""Builder for Iter9 metrics test documents."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from tests.demo.iter9_visual_solver.fixtures.metrics import minimal_iter9_metrics


class MetricsBuilder:
    def __init__(self) -> None:
        self._metrics: dict[str, Any] = minimal_iter9_metrics()

    def with_source_image(self, name: str) -> "MetricsBuilder":
        self._metrics["source_image"]["name"] = name
        return self

    def with_board(self, board: str) -> "MetricsBuilder":
        width, height = [int(part) for part in board.split("x")]
        self._metrics["board"] = board
        self._metrics["board_width"] = width
        self._metrics["board_height"] = height
        self._metrics["cells"] = width * height
        return self

    def with_seed(self, seed: int) -> "MetricsBuilder":
        self._metrics["seed"] = int(seed)
        return self

    def with_unknown_count(self, n_unknown: int) -> "MetricsBuilder":
        self._metrics["n_unknown"] = int(n_unknown)
        return self

    def build_dict(self) -> dict[str, Any]:
        return deepcopy(self._metrics)
