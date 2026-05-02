"""Artifact path resolution for completed Iter9 runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from demos.iter9_visual_solver.contracts.artifact_names import (
    EVENT_TRACE_FILENAME,
    GRID_LATEST_FILENAME,
    METRICS_FILENAME_PREFIX,
    METRICS_FILENAME_SUFFIX,
)
from demos.iter9_visual_solver.errors.artifact_errors import DemoArtifactNotFoundError


@dataclass(frozen=True)
class DemoArtifactPaths:
    run_dir: Path
    grid_path: Path
    metrics_path: Path
    event_trace_path: Path | None


def metrics_filename_for_board(board_label: str) -> str:
    return f"{METRICS_FILENAME_PREFIX}{board_label}{METRICS_FILENAME_SUFFIX}"


def resolve_artifact_paths(
    run_dir: Path | str,
    *,
    board_label: str | None = None,
    require_event_trace: bool = False,
) -> DemoArtifactPaths:
    root = Path(run_dir)
    grid_path = root / GRID_LATEST_FILENAME
    if not grid_path.is_file():
        raise DemoArtifactNotFoundError(f"Grid artifact not found: {grid_path}")

    if board_label is None:
        matches = sorted(root.glob(f"{METRICS_FILENAME_PREFIX}*{METRICS_FILENAME_SUFFIX}"))
        if not matches:
            raise DemoArtifactNotFoundError(f"Metrics artifact not found in {root}")
        metrics_path = matches[0]
    else:
        metrics_path = root / metrics_filename_for_board(board_label)
        if not metrics_path.is_file():
            raise DemoArtifactNotFoundError(f"Metrics artifact not found: {metrics_path}")

    event_trace_path = root / EVENT_TRACE_FILENAME
    if not event_trace_path.is_file():
        if require_event_trace:
            raise DemoArtifactNotFoundError(f"Event trace artifact not found: {event_trace_path}")
        event_trace_path = None

    return DemoArtifactPaths(
        run_dir=root,
        grid_path=grid_path,
        metrics_path=metrics_path,
        event_trace_path=event_trace_path,
    )

