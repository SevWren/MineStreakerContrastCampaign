"""Pygame event loop for the visual solver demo."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from demos.iter9_visual_solver.playback.finish_policy import should_auto_close
from demos.iter9_visual_solver.playback.event_scheduler import EventScheduler
from demos.iter9_visual_solver.playback.replay_state import ReplayState
from demos.iter9_visual_solver.rendering.board_surface import CachedBoardSurfaceRenderer
from demos.iter9_visual_solver.rendering.color_palette import ColorPalette
from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter
from demos.iter9_visual_solver.rendering.status_panel import draw_status_panel_view_model
from demos.iter9_visual_solver.rendering.status_view_model import StatusPanelViewModelFactory
from demos.iter9_visual_solver.rendering.window_chrome import draw_board_border, draw_header_strip, draw_vertical_divider
from demos.iter9_visual_solver.rendering.window_geometry import (
    DisplayBounds,
    LayoutRequest,
    WindowGeometry,
    calculate_responsive_window_geometry,
    calculate_window_geometry,
    calculate_window_placement,
)


@dataclass(frozen=True)
class PygameLoopResult:
    exit_reason: str
    playback_finished: bool
    frames_rendered: int
    events_applied: int
    elapsed_time_s: float
    closed_by_user: bool = False

    @property
    def frames(self) -> int:
        return self.frames_rendered

    @property
    def completed(self) -> bool:
        return self.playback_finished


def _get(config: Any, name: str, default=None):
    if config is None:
        return default
    if isinstance(config, dict):
        return config.get(name, default)
    return getattr(config, name, default)


def _finish_state(*, playback_finished: bool, finish_config: Any, elapsed_after_finish_s: float) -> str:
    if not playback_finished:
        return "running"
    mode = _get(finish_config, "mode", "stay_open")
    if mode == "stay_open":
        return "complete - staying open"
    if mode == "close_immediately":
        return "complete - closing"
    if mode == "close_after_delay":
        delay = float(_get(finish_config, "close_after_seconds", 0.0) or 0.0)
        remaining = max(delay - elapsed_after_finish_s, 0.0)
        if remaining <= 0:
            return "complete - closing"
        return f"complete - closing in {remaining:.1f}s"
    return "error"


def _exit_reason_for_finish(finish_config: Any) -> str:
    mode = _get(finish_config, "mode", "stay_open")
    if mode == "close_after_delay":
        return "playback_finished_close_after_delay"
    return "playback_finished_close_immediately"


def run_pygame_loop(
    *,
    pygame_module=None,
    events=None,
    events_per_frame: int = 1,
    events_per_second: int = 0,
    board_width: int | None = None,
    board_height: int | None = None,
    source_image_name: str = "unknown",
    source_image_size: tuple[int, int] | None = None,
    seed: int = 0,
    replay_source: str = "",
    finish_config=None,
    status_config=None,
    palette: ColorPalette | None = None,
    show_safe_cells: bool = False,
    show_unknown_cells: bool = True,
    geometry: WindowGeometry | None = None,
    window_config=None,
    cell_px: int = 1,
    board_pixel_width: int | None = None,
    status_panel_width_px: int = 0,
    max_frames: int | None = None,
    target_fps: int = 60,
    width: int = 100,
    height: int = 100,
    title: str = "Mine-Streaker Iter9 Visual Solver Demo",
    resizable: bool = False,
) -> PygameLoopResult:
    event_source = events if events is not None else []
    adapter = PygameAdapter(pygame_module=pygame_module)
    display_bounds = adapter.get_display_bounds()
    if window_config is not None:
        resizable = bool(_get(window_config, "resizable", resizable))
    if geometry is None:
        geometry = calculate_window_geometry(
            board_width=board_width or width,
            board_height=board_height or height,
            status_panel_width_px=_get(window_config, "status_panel_width_px", status_panel_width_px),
            preferred_board_cell_px=_get(window_config, "preferred_board_cell_px", cell_px),
            minimum_board_cell_px=_get(window_config, "minimum_board_cell_px", 1),
            max_screen_fraction=_get(window_config, "max_screen_fraction", 1.0),
            fit_to_screen=_get(window_config, "fit_to_screen", True),
            display_bounds=display_bounds,
            source_image_width_px=source_image_size[0] if source_image_size else None,
            source_image_height_px=source_image_size[1] if source_image_size else None,
        )
    placement = calculate_window_placement(
        window_width=geometry.window_width,
        window_height=geometry.window_height,
        display_bounds=display_bounds,
        center_window=bool(_get(window_config, "center_window", False)),
    )
    surface = adapter.open_window(
        width=geometry.window_width,
        height=geometry.window_height,
        title=title,
        resizable=resizable,
        placement=placement,
    )
    font = adapter.create_font()
    scheduler = EventScheduler(events=event_source, events_per_frame=events_per_frame)
    replay_state = ReplayState(
        events=event_source,
        board_width=board_width or width,
        board_height=board_height or height,
        source_image_name=source_image_name,
        seed=seed,
        events_per_second=events_per_second,
        replay_source=replay_source,
    )
    palette = palette or ColorPalette(
        unseen_cell_rgb=(18, 18, 18),
        flagged_mine_rgb=(255, 80, 40),
        safe_cell_rgb=(95, 95, 95),
        unknown_cell_rgb=(60, 100, 230),
        background_rgb=(10, 10, 10),
    )
    finish_config = finish_config or {"mode": "close_immediately", "close_after_seconds": None}
    board_renderer = CachedBoardSurfaceRenderer(
        board_width=geometry.board_width,
        board_height=geometry.board_height,
        adapter=adapter,
        palette=palette,
        show_safe_cells=show_safe_cells,
        show_unknown_cells=show_unknown_cells,
    )
    status_view_models = StatusPanelViewModelFactory(
        status_config=status_config,
        palette=palette,
        show_safe_cells=show_safe_cells,
        show_unknown_cells=show_unknown_cells,
    )
    board_pixel_width = int(board_pixel_width if board_pixel_width is not None else geometry.board_pixel_width)
    status_panel_width_px = max(0, int(status_panel_width_px or geometry.status_panel_width_px))
    frames = 0
    events_applied = 0
    elapsed_time_s = 0.0
    finish_started_s: float | None = None
    try:
        while True:
            for event in adapter.poll_events():
                if adapter.is_quit_event(event):
                    return PygameLoopResult(
                        exit_reason="user_closed_window",
                        playback_finished=scheduler.finished,
                        frames_rendered=frames,
                        events_applied=events_applied,
                        elapsed_time_s=elapsed_time_s,
                        closed_by_user=True,
                    )
                if resizable and adapter.is_resize_event(event):
                    event_size = adapter.get_resize_event_size(event)
                    if event_size is not None:
                        requested_width, requested_height = event_size
                        geometry = calculate_responsive_window_geometry(
                            LayoutRequest(
                                board_width=board_width or geometry.board_width,
                                board_height=board_height or geometry.board_height,
                                requested_window_width=requested_width,
                                requested_window_height=requested_height,
                                status_panel_width_px=_get(window_config, "status_panel_width_px", geometry.status_panel_width_px),
                                preferred_board_cell_px=_get(window_config, "preferred_board_cell_px", geometry.cell_px),
                                minimum_board_cell_px=_get(window_config, "minimum_board_cell_px", 1),
                                max_screen_fraction=_get(window_config, "max_screen_fraction", 1.0),
                                fit_to_screen=_get(window_config, "fit_to_screen", True),
                                display_bounds=display_bounds,
                                source_image_width_px=source_image_size[0] if source_image_size else None,
                                source_image_height_px=source_image_size[1] if source_image_size else None,
                            )
                        )
                        surface = adapter.resize_window(
                            width=max(geometry.window_width, geometry.minimum_window_width),
                            height=max(geometry.window_height, geometry.minimum_window_height),
                            resizable=resizable,
                        )
            if not scheduler.finished:
                batch = scheduler.next_batch()
                replay_state.apply_batch(batch)
                board_renderer.apply_batch(batch)
                events_applied += len(batch)
            if scheduler.finished and finish_started_s is None:
                finish_started_s = elapsed_time_s
            elapsed_after_finish_s = 0.0 if finish_started_s is None else elapsed_time_s - finish_started_s
            finish_state = _finish_state(
                playback_finished=scheduler.finished,
                finish_config=finish_config,
                elapsed_after_finish_s=elapsed_after_finish_s,
            )
            if hasattr(surface, "fill"):
                surface.fill(tuple(palette.background_rgb))
            snapshot = replay_state.snapshot(
                finish_state=finish_state,
                elapsed_seconds=elapsed_time_s,
            )
            view_model = status_view_models.build(snapshot)
            draw_header_strip(
                surface,
                adapter=adapter,
                header_rect=geometry.header_rect,
                text=view_model.header_text,
                background_rgb=(20, 20, 20),
                text_rgb=(230, 230, 230),
                font=font,
            )
            board_renderer.draw_scaled(
                surface=surface,
                destination_rect=geometry.board_draw_rect,
            )
            draw_board_border(
                surface,
                adapter=adapter,
                board_rect=geometry.board_rect,
                border_rgb=(90, 90, 90),
            )
            if geometry.divider_rect is not None:
                draw_vertical_divider(
                    surface,
                    adapter=adapter,
                    divider_rect=geometry.divider_rect,
                    divider_rgb=(70, 70, 70),
                )
            if geometry.status_panel_rect is not None:
                draw_status_panel_view_model(
                    surface,
                    view_model,
                    adapter=adapter,
                    panel_rect=geometry.status_panel_rect,
                    palette=palette,
                    font=font,
                    source_preview_rect=geometry.source_preview_rect,
                )
            adapter.flip()
            tick_ms = adapter.tick(target_fps)
            frames += 1
            elapsed_time_s += float(tick_ms or 0) / 1000.0
            if scheduler.finished and should_auto_close(
                finish_config,
                elapsed_after_finish_s=elapsed_after_finish_s,
            ):
                return PygameLoopResult(
                    exit_reason=_exit_reason_for_finish(finish_config),
                    playback_finished=True,
                    frames_rendered=frames,
                    events_applied=events_applied,
                    elapsed_time_s=elapsed_time_s,
                )
            if max_frames is not None and frames >= max_frames:
                return PygameLoopResult(
                    exit_reason="max_frames_test_limit",
                    playback_finished=scheduler.finished,
                    frames_rendered=frames,
                    events_applied=events_applied,
                    elapsed_time_s=elapsed_time_s,
                )
    finally:
        adapter.close()
