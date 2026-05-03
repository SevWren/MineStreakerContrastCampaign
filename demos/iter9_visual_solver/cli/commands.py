"""Standalone visual solver demo command orchestration."""

from __future__ import annotations

from demos.iter9_visual_solver.cli.args import parse_args
from demos.iter9_visual_solver.config.loader import load_demo_config
from demos.iter9_visual_solver.domain.board_dimensions import BoardDimensions
from demos.iter9_visual_solver.io.event_trace_loader import load_event_trace
from demos.iter9_visual_solver.io.grid_loader import load_grid
from demos.iter9_visual_solver.io.metrics_loader import load_metrics
from demos.iter9_visual_solver.playback.event_batching import calculate_events_per_frame
from demos.iter9_visual_solver.playback.event_source import select_event_source
from demos.iter9_visual_solver.playback.speed_policy import calculate_events_per_second
from demos.iter9_visual_solver.rendering.color_palette import ColorPalette
from demos.iter9_visual_solver.rendering.pygame_loop import run_pygame_loop


def _source_image_name(metrics: dict) -> str:
    source_image = metrics.get("source_image")
    if isinstance(source_image, dict) and source_image.get("name"):
        return str(source_image["name"])
    source_validation = metrics.get("source_image_validation")
    if isinstance(source_validation, dict) and source_validation.get("name"):
        return str(source_validation["name"])
    return "unknown"


def _source_image_size(metrics: dict) -> tuple[int, int] | None:
    analysis = metrics.get("source_image_analysis")
    if isinstance(analysis, dict):
        width = analysis.get("width_px")
        height = analysis.get("height_px")
        if width and height:
            return int(width), int(height)
    width = metrics.get("source_width")
    height = metrics.get("source_height")
    if width and height:
        return int(width), int(height)
    validation = metrics.get("source_image_validation")
    if isinstance(validation, dict):
        pixel_shape = validation.get("pixel_shape")
        if isinstance(pixel_shape, (list, tuple)) and len(pixel_shape) >= 2:
            return int(pixel_shape[1]), int(pixel_shape[0])
    return None


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_demo_config(args.config)
    grid = load_grid(args.grid)
    metrics = load_metrics(args.metrics)
    dims = BoardDimensions.from_grid(grid)
    trace_events = None
    if args.event_trace:
        trace_events = load_event_trace(args.event_trace, board_width=dims.width, board_height=dims.height)
    events, _source = select_event_source(input_config=config.input, grid=grid, trace_events=trace_events)
    total_mines = sum(1 for event in events if event.state == "MINE")
    events_per_second = calculate_events_per_second(config.playback, total_mines=total_mines)
    events_per_frame = calculate_events_per_frame(
        events_per_second=events_per_second,
        target_fps=config.playback.target_fps,
        batch_events_per_frame=config.playback.batch_events_per_frame,
    )
    palette = ColorPalette.from_config(config.visuals)
    run_pygame_loop(
        events=events,
        events_per_frame=events_per_frame,
        events_per_second=events_per_second,
        board_width=dims.width,
        board_height=dims.height,
        source_image_name=_source_image_name(metrics),
        source_image_size=_source_image_size(metrics),
        seed=int(metrics.get("seed", 0)),
        replay_source=_source,
        finish_config=config.window.finish_behavior,
        status_config=config.status_panel,
        palette=palette,
        show_safe_cells=config.visuals.show_safe_cells,
        show_unknown_cells=config.visuals.show_unknown_cells,
        window_config=config.window,
        target_fps=config.playback.target_fps,
        title=config.window.title,
        resizable=config.window.resizable,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
