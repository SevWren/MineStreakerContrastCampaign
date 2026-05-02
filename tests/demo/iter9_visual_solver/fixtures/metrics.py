"""Reusable metrics fixtures for Iter9 visual solver demo tests."""

from __future__ import annotations

from typing import Any


def minimal_iter9_metrics(board: str = "300x942", seed: int = 11) -> dict[str, Any]:
    width, height = [int(part) for part in board.split("x")]
    return {
        "schema_version": "metrics.v2.source_image_runtime_contract",
        "board": board,
        "board_width": width,
        "board_height": height,
        "cells": width * height,
        "seed": int(seed),
        "n_unknown": 0,
        "source_image": {
            "name": "line_art_irl_11_v2.png",
            "project_relative_path": "assets/line_art_irl_11_v2.png",
        },
        "artifact_inventory": {
            "grid_npy": f"results/iter9/example/grid_iter9_{board}.npy",
            "metrics_json": f"results/iter9/example/metrics_iter9_{board}.json",
        },
    }


def metrics_with_source_image(name: str) -> dict[str, Any]:
    metrics = minimal_iter9_metrics()
    metrics["source_image"]["name"] = name
    return metrics


def metrics_with_unknowns(n_unknown: int) -> dict[str, Any]:
    metrics = minimal_iter9_metrics()
    metrics["n_unknown"] = int(n_unknown)
    return metrics


def metrics_with_artifact_inventory(**paths: str) -> dict[str, Any]:
    metrics = minimal_iter9_metrics()
    metrics["artifact_inventory"].update(paths)
    return metrics
