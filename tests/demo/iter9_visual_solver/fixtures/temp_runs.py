"""Temporary Iter9 run directory helpers for I/O tests."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Iterator

import numpy as np


class TempIter9Run:
    """Context-managed temporary Iter9 run folder."""

    def __init__(self) -> None:
        self._tmp = TemporaryDirectory()
        self.path = Path(self._tmp.name)

    def __enter__(self) -> "TempIter9Run":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self._tmp.cleanup()

    def write_grid_artifact(self, grid: np.ndarray, name: str = "grid_iter9_latest.npy") -> Path:
        path = self.path / name
        np.save(path, grid)
        return path

    def write_metrics_artifact(self, metrics: dict[str, Any], name: str = "metrics_iter9_300x942.json") -> Path:
        path = self.path / name
        path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        return path

    def write_event_trace_artifact(self, text: str, name: str = "solver_event_trace.jsonl") -> Path:
        path = self.path / name
        path.write_text(text, encoding="utf-8")
        return path

    def write_demo_config(self, config: dict[str, Any], name: str = "iter9_visual_solver_demo.default.json") -> Path:
        path = self.path / name
        path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return path


def make_temp_iter9_run_dir() -> TempIter9Run:
    return TempIter9Run()
