"""Config file loading for the visual solver demo."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from demos.iter9_visual_solver.config.models import DemoConfig
from demos.iter9_visual_solver.errors.config_errors import (
    DemoConfigFileNotFoundError,
    DemoConfigJsonError,
    DemoConfigValidationError,
)


def load_demo_config(path: Path | str) -> DemoConfig:
    config_path = Path(path)
    if not config_path.is_file():
        raise DemoConfigFileNotFoundError(f"Demo config file not found: {config_path}")

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DemoConfigJsonError(f"Invalid JSON in demo config {config_path}: {exc}") from exc

    try:
        return DemoConfig.model_validate(data)
    except ValidationError as exc:
        field_paths = [".".join(str(part) for part in error["loc"]) for error in exc.errors()]
        suffix = f" fields: {', '.join(field_paths)}" if field_paths else ""
        raise DemoConfigValidationError(f"Invalid demo config {config_path}:{suffix} {exc}") from exc

