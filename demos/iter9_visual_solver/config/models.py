"""Pydantic config models for the visual solver demo."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from demos.iter9_visual_solver.contracts.schema_versions import CONFIG_SCHEMA_VERSION

Rgb = tuple[int, int, int]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinishBehaviorConfig(_StrictModel):
    mode: Literal["stay_open", "close_immediately", "close_after_delay"] = "stay_open"
    close_after_seconds: float | None = None

    @model_validator(mode="after")
    def _delay_requires_seconds(self) -> "FinishBehaviorConfig":
        if self.mode == "close_after_delay" and self.close_after_seconds is None:
            raise ValueError("window.finish_behavior.close_after_seconds is required for close_after_delay")
        return self


class WindowConfig(_StrictModel):
    title: str = Field(default="Mine-Streaker Iter9 Visual Solver Demo", min_length=1, max_length=120)
    resizable: bool = False
    max_screen_fraction: float = Field(default=0.92, ge=0.1, le=1.0)
    status_panel_width_px: int = Field(default=360, ge=0, le=1200)
    minimum_board_cell_px: int = Field(default=1, ge=1, le=64)
    preferred_board_cell_px: int = Field(default=2, ge=1, le=64)
    fit_to_screen: bool = True
    center_window: bool = True
    finish_behavior: FinishBehaviorConfig = Field(default_factory=FinishBehaviorConfig)

    @model_validator(mode="after")
    def _preferred_cell_not_below_minimum(self) -> "WindowConfig":
        if self.preferred_board_cell_px < self.minimum_board_cell_px:
            raise ValueError("window.preferred_board_cell_px must be >= window.minimum_board_cell_px")
        return self


class PlaybackConfig(_StrictModel):
    mode: Literal["mine_count_scaled"] = "mine_count_scaled"
    min_events_per_second: int = Field(default=50, ge=1, le=1_000_000)
    base_events_per_second: int = Field(default=1000, ge=0, le=1_000_000)
    mine_count_multiplier: float = Field(default=0.08, ge=0, le=10_000)
    max_events_per_second: int = Field(default=12000, ge=1, le=10_000_000)
    target_fps: int = Field(default=60, ge=1, le=240)
    batch_events_per_frame: bool = True

    @model_validator(mode="after")
    def _min_not_above_max(self) -> "PlaybackConfig":
        if self.min_events_per_second > self.max_events_per_second:
            raise ValueError("playback.min_events_per_second must be <= playback.max_events_per_second")
        return self


class VisualsConfig(_StrictModel):
    unseen_cell_rgb: Rgb = (18, 18, 18)
    flagged_mine_rgb: Rgb = (255, 80, 40)
    safe_cell_rgb: Rgb = (95, 95, 95)
    unknown_cell_rgb: Rgb = (60, 100, 230)
    background_rgb: Rgb = (10, 10, 10)
    show_safe_cells: bool = False
    show_unknown_cells: bool = True

    @field_validator(
        "unseen_cell_rgb",
        "flagged_mine_rgb",
        "safe_cell_rgb",
        "unknown_cell_rgb",
        "background_rgb",
    )
    @classmethod
    def _rgb_channels(cls, value: Rgb) -> Rgb:
        if len(value) != 3 or any(channel < 0 or channel > 255 for channel in value):
            raise ValueError("RGB values must contain exactly three integers in 0..255")
        return tuple(int(channel) for channel in value)


class StatusPanelConfig(_StrictModel):
    show_source_image: bool = True
    show_board_dimensions: bool = True
    show_seed: bool = True
    show_total_cells: bool = True
    show_mines_flagged: bool = True
    show_safe_cells_solved: bool = True
    show_unknown_remaining: bool = True
    show_playback_speed: bool = True
    show_elapsed_time: bool = True
    show_finish_message: bool = True


class InputConfig(_StrictModel):
    prefer_solver_event_trace: bool = True
    allow_final_grid_replay_fallback: bool = True


class DemoConfig(_StrictModel):
    schema_version: Literal[CONFIG_SCHEMA_VERSION]
    window: WindowConfig
    playback: PlaybackConfig
    visuals: VisualsConfig
    status_panel: StatusPanelConfig
    input: InputConfig

