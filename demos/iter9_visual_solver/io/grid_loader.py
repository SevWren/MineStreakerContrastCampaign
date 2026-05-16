"""NumPy grid loading."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from demos.iter9_visual_solver.errors.artifact_errors import DemoArtifactNotFoundError, DemoArtifactValidationError


def load_grid(path: Path | str) -> np.ndarray:
    grid_path = Path(path)
    if not grid_path.is_file():
        raise DemoArtifactNotFoundError(f"Grid artifact not found: {grid_path}")
    try:
        grid = np.load(grid_path)
    except Exception as exc:  # np.load raises several format-specific exceptions.
        raise DemoArtifactValidationError(f"Could not load grid artifact {grid_path}: {exc}") from exc
    if getattr(grid, "ndim", None) != 2:
        raise DemoArtifactValidationError(f"Grid artifact must be 2D: {grid_path}")
    return grid

