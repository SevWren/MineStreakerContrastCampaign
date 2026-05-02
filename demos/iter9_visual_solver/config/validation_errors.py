"""Compatibility exports for config validation errors."""

from demos.iter9_visual_solver.errors.config_errors import (
    DemoConfigError,
    DemoConfigFileNotFoundError,
    DemoConfigJsonError,
    DemoConfigValidationError,
)

__all__ = [
    "DemoConfigError",
    "DemoConfigFileNotFoundError",
    "DemoConfigJsonError",
    "DemoConfigValidationError",
]

