"""Color palette mapping from validated visual config."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _rgb(config: Any, name: str) -> tuple[int, int, int]:
    value = config[name] if isinstance(config, dict) else getattr(config, name)
    return tuple(int(channel) for channel in value)


@dataclass(frozen=True)
class ColorPalette:
    unseen_cell_rgb: tuple[int, int, int]
    flagged_mine_rgb: tuple[int, int, int]
    safe_cell_rgb: tuple[int, int, int]
    unknown_cell_rgb: tuple[int, int, int]
    background_rgb: tuple[int, int, int]

    @classmethod
    def from_config(cls, visuals_config: Any) -> "ColorPalette":
        return cls(
            unseen_cell_rgb=_rgb(visuals_config, "unseen_cell_rgb"),
            flagged_mine_rgb=_rgb(visuals_config, "flagged_mine_rgb"),
            safe_cell_rgb=_rgb(visuals_config, "safe_cell_rgb"),
            unknown_cell_rgb=_rgb(visuals_config, "unknown_cell_rgb"),
            background_rgb=_rgb(visuals_config, "background_rgb"),
        )

