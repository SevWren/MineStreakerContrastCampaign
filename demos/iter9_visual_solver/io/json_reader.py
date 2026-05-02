"""Shared JSON reader."""

from __future__ import annotations

import json
from pathlib import Path

from demos.iter9_visual_solver.errors.artifact_errors import DemoArtifactNotFoundError, DemoArtifactValidationError


def read_json_object(path: Path | str) -> dict:
    json_path = Path(path)
    if not json_path.is_file():
        raise DemoArtifactNotFoundError(f"JSON artifact not found: {json_path}")
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DemoArtifactValidationError(f"Invalid JSON artifact {json_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise DemoArtifactValidationError(f"Expected JSON object in {json_path}")
    return data

