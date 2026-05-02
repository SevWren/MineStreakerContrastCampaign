"""Thin launch seam used by optional run_iter9.py integration."""

from __future__ import annotations

from pathlib import Path

from demos.iter9_visual_solver.cli.commands import main


def run_demo_from_completed_iter9_run(
    *,
    grid_path: Path,
    metrics_path: Path,
    config_path: Path,
    event_trace_path: Path | None = None,
) -> int:
    argv = [
        "--grid",
        str(grid_path),
        "--metrics",
        str(metrics_path),
        "--config",
        str(config_path),
    ]
    if event_trace_path is not None:
        argv.extend(["--event-trace", str(event_trace_path)])
    return main(argv)

