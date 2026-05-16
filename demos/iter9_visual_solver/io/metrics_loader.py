"""Metrics JSON loading for the visual solver demo."""

from __future__ import annotations

from pathlib import Path

from demos.iter9_visual_solver.errors.artifact_errors import DemoArtifactValidationError
from demos.iter9_visual_solver.io.json_reader import read_json_object


def load_metrics(path: Path | str) -> dict:
    metrics = read_json_object(path)
    required = ["board", "seed"]
    missing = [field for field in required if field not in metrics]
    if missing:
        raise DemoArtifactValidationError(f"Metrics artifact {path} missing fields: {', '.join(missing)}")
    return metrics

