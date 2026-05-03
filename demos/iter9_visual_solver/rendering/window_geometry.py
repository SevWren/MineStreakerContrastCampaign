"""Pure window geometry calculation for the visual solver demo."""

from __future__ import annotations

from dataclasses import dataclass

FALLBACK_DISPLAY_BOUNDS: "DisplayBounds"
DEFAULT_HEADER_HEIGHT_PX = 34
DEFAULT_DIVIDER_WIDTH_PX = 1
DEFAULT_GUTTER_PX = 16
MAX_STATUS_PANEL_WIDTH_PX = 560
STATUS_PANEL_WINDOW_FRACTION = 0.28

SCALE_PREFERRED = "preferred_cell_size_used"
SCALE_FIT_TO_SCREEN = "fit_to_screen_reduced_cell_size"
SCALE_RESIZE = "resize_reduced_cell_size"
SCALE_SCREEN_OVERFLOW = "minimum_cell_size_exceeds_screen_budget"
SCALE_WINDOW_OVERFLOW = "minimum_cell_size_exceeds_window_size"


@dataclass(frozen=True)
class RectSpec:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        for name in ("x", "y", "width", "height"):
            value = int(getattr(self, name))
            if value < 0:
                raise ValueError(f"{name}={value} must be >= 0")
            object.__setattr__(self, name, value)

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.x, self.y, self.width, self.height)


@dataclass(frozen=True)
class DisplayBounds:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", int(self.x))
        object.__setattr__(self, "y", int(self.y))
        width = int(self.width)
        height = int(self.height)
        if width <= 0:
            raise ValueError(f"width={width} must be > 0")
        if height <= 0:
            raise ValueError(f"height={height} must be > 0")
        object.__setattr__(self, "width", width)
        object.__setattr__(self, "height", height)


FALLBACK_DISPLAY_BOUNDS = DisplayBounds(x=0, y=0, width=1920, height=1080)


@dataclass(frozen=True)
class WindowPlacement:
    x: int | None
    y: int | None
    horizontally_centered: bool


@dataclass(frozen=True)
class LayoutRequest:
    board_width: int
    board_height: int
    requested_window_width: int | None
    requested_window_height: int | None
    status_panel_width_px: int
    preferred_board_cell_px: int
    minimum_board_cell_px: int
    max_screen_fraction: float
    fit_to_screen: bool
    display_bounds: DisplayBounds
    header_height_px: int = DEFAULT_HEADER_HEIGHT_PX
    source_image_width_px: int | None = None
    source_image_height_px: int | None = None


@dataclass(frozen=True)
class WindowGeometry:
    board_width: int
    board_height: int
    total_cells: int
    cell_px: int
    window_rect: RectSpec
    content_rect: RectSpec
    header_rect: RectSpec
    board_viewport_rect: RectSpec
    board_draw_rect: RectSpec
    board_scale: float
    board_rect: RectSpec
    status_panel_rect: RectSpec | None
    status_panel_content_rect: RectSpec | None
    divider_rect: RectSpec | None
    source_preview_rect: RectSpec | None
    board_pixel_width: int
    board_pixel_height: int
    status_panel_width_px: int
    window_width: int
    window_height: int
    minimum_window_width: int
    minimum_window_height: int
    preferred_window_width: int
    preferred_window_height: int
    fits_screen: bool
    fits_window: bool
    scale_reason: str


def _coerce_display_bounds(
    *,
    display_bounds: DisplayBounds | None,
    screen_width: int | None,
    screen_height: int | None,
) -> DisplayBounds:
    if display_bounds is not None:
        return display_bounds
    if screen_width is not None and screen_height is not None:
        return DisplayBounds(x=0, y=0, width=int(screen_width), height=int(screen_height))
    return FALLBACK_DISPLAY_BOUNDS


def calculate_window_placement(
    *,
    window_width: int,
    window_height: int,
    display_bounds: DisplayBounds,
    center_window: bool,
) -> WindowPlacement:
    del window_height
    if not center_window:
        return WindowPlacement(x=None, y=None, horizontally_centered=False)
    available = max(int(display_bounds.width) - int(window_width), 0)
    return WindowPlacement(
        x=int(display_bounds.x) + available // 2,
        y=None,
        horizontally_centered=True,
    )


def calculate_window_geometry(
    *,
    board_width: int,
    board_height: int,
    status_panel_width_px: int = 360,
    preferred_board_cell_px: int = 2,
    minimum_board_cell_px: int = 1,
    max_screen_fraction: float = 1.0,
    screen_width: int | None = None,
    screen_height: int | None = None,
    fit_to_screen: bool = True,
    display_bounds: DisplayBounds | None = None,
    source_image_width_px: int | None = None,
    source_image_height_px: int | None = None,
) -> WindowGeometry:
    bounds = _coerce_display_bounds(
        display_bounds=display_bounds,
        screen_width=screen_width,
        screen_height=screen_height,
    )
    return calculate_responsive_window_geometry(
        LayoutRequest(
            board_width=board_width,
            board_height=board_height,
            requested_window_width=None,
            requested_window_height=None,
            status_panel_width_px=status_panel_width_px,
            preferred_board_cell_px=preferred_board_cell_px,
            minimum_board_cell_px=minimum_board_cell_px,
            max_screen_fraction=max_screen_fraction,
            fit_to_screen=fit_to_screen,
            display_bounds=bounds,
            source_image_width_px=source_image_width_px,
            source_image_height_px=source_image_height_px,
        )
    )


def calculate_responsive_window_geometry(request: LayoutRequest) -> WindowGeometry:
    board_width = max(1, int(request.board_width))
    board_height = max(1, int(request.board_height))
    status_panel_width_px = max(0, int(request.status_panel_width_px))
    preferred_cell = max(1, int(request.preferred_board_cell_px))
    minimum_cell = max(1, int(request.minimum_board_cell_px))
    preferred_cell = max(preferred_cell, minimum_cell)
    header_height = max(0, int(request.header_height_px))

    preferred_panel_width = _calculate_panel_width(
        window_width=board_width * preferred_cell + status_panel_width_px,
        configured_width=status_panel_width_px,
    )
    preferred_board_width = board_width * preferred_cell
    preferred_board_height = board_height * preferred_cell
    preferred_window_width = (
        DEFAULT_GUTTER_PX
        + preferred_board_width
        + (DEFAULT_GUTTER_PX + DEFAULT_DIVIDER_WIDTH_PX + DEFAULT_GUTTER_PX + preferred_panel_width if preferred_panel_width else DEFAULT_GUTTER_PX)
    )
    preferred_window_height = header_height + preferred_board_height + DEFAULT_GUTTER_PX * 2
    minimum_panel_width = min(status_panel_width_px, max(0, status_panel_width_px))
    minimum_window_width = (
        DEFAULT_GUTTER_PX
        + board_width * minimum_cell
        + (DEFAULT_GUTTER_PX + DEFAULT_DIVIDER_WIDTH_PX + DEFAULT_GUTTER_PX + minimum_panel_width if minimum_panel_width else DEFAULT_GUTTER_PX)
    )
    minimum_window_height = header_height + board_height * minimum_cell + DEFAULT_GUTTER_PX * 2

    screen_width = max(1, int(request.display_bounds.width * float(request.max_screen_fraction)))
    screen_height = max(1, int(request.display_bounds.height * float(request.max_screen_fraction)))

    if request.requested_window_width is None or request.requested_window_height is None:
        if request.fit_to_screen:
            available_width = min(preferred_window_width, screen_width)
            available_height = min(preferred_window_height, screen_height)
        else:
            available_width = preferred_window_width
            available_height = preferred_window_height
        resize_mode = False
    else:
        available_width = max(1, int(request.requested_window_width))
        available_height = max(1, int(request.requested_window_height))
        resize_mode = True

    panel_width = _calculate_panel_width(
        window_width=available_width,
        configured_width=status_panel_width_px,
    )
    content_width_for_layout = available_width
    content_height_for_layout = max(1, available_height - header_height)
    panel_claim = DEFAULT_GUTTER_PX + DEFAULT_DIVIDER_WIDTH_PX + DEFAULT_GUTTER_PX + panel_width if panel_width else DEFAULT_GUTTER_PX
    board_area_width = max(1, content_width_for_layout - DEFAULT_GUTTER_PX - panel_claim)
    board_area_height = max(1, content_height_for_layout - DEFAULT_GUTTER_PX * 2)
    board_scale = max(min(board_area_width / board_width, board_area_height / board_height), 1 / max(board_width, board_height))
    fits_window = board_scale >= minimum_cell
    cell_px = max(minimum_cell, int(board_scale))

    board_pixel_width = max(1, int(round(board_width * board_scale)))
    board_pixel_height = max(1, int(round(board_height * board_scale)))
    content_width = board_pixel_width + panel_claim
    content_height = board_pixel_height + DEFAULT_GUTTER_PX * 2
    if resize_mode:
        window_width = max(int(available_width), content_width)
        window_height = max(int(available_height), header_height + content_height)
    else:
        window_width = content_width
        window_height = header_height + content_height
    content_height = max(content_height, window_height - header_height)
    fits_screen = window_width <= screen_width and window_height <= screen_height

    if not fits_window:
        scale_reason = SCALE_WINDOW_OVERFLOW if resize_mode else SCALE_SCREEN_OVERFLOW
    elif resize_mode and board_scale < preferred_cell:
        scale_reason = SCALE_RESIZE
    elif request.fit_to_screen and board_scale < preferred_cell:
        scale_reason = SCALE_FIT_TO_SCREEN
    else:
        scale_reason = SCALE_PREFERRED

    header_rect = RectSpec(0, 0, window_width, header_height)
    content_rect = RectSpec(0, header_height, window_width, content_height)
    board_area_right = max(DEFAULT_GUTTER_PX + board_pixel_width, window_width - (panel_width + DEFAULT_GUTTER_PX + DEFAULT_DIVIDER_WIDTH_PX + DEFAULT_GUTTER_PX if panel_width else 0))
    board_viewport_rect = RectSpec(
        DEFAULT_GUTTER_PX,
        header_height + DEFAULT_GUTTER_PX,
        max(1, board_area_right - DEFAULT_GUTTER_PX),
        max(1, window_height - header_height - DEFAULT_GUTTER_PX * 2),
    )
    board_x = board_viewport_rect.x + max(0, board_viewport_rect.width - board_pixel_width) // 2
    board_y = board_viewport_rect.y + max(0, board_viewport_rect.height - board_pixel_height) // 2
    board_draw_rect = RectSpec(board_x, board_y, board_pixel_width, board_pixel_height)
    board_rect = board_draw_rect
    status_panel_rect = None
    status_panel_content_rect = None
    divider_rect = None
    source_preview_rect = None
    if panel_width > 0:
        panel_x = max(0, window_width - panel_width - DEFAULT_GUTTER_PX)
        status_panel_rect = RectSpec(panel_x, header_height + DEFAULT_GUTTER_PX, panel_width, max(1, window_height - header_height - DEFAULT_GUTTER_PX * 2))
        status_panel_content_rect = RectSpec(
            status_panel_rect.x + 12,
            status_panel_rect.y + 12,
            max(1, status_panel_rect.width - 24),
            max(1, status_panel_rect.height - 24),
        )
        divider_x = max(0, panel_x - DEFAULT_GUTTER_PX)
        divider_rect = RectSpec(divider_x, header_height + DEFAULT_GUTTER_PX, DEFAULT_DIVIDER_WIDTH_PX, status_panel_rect.height)
        preview_width = max(0, min(status_panel_rect.width - 24, status_panel_rect.width))
        preview_height = max(0, min(status_panel_rect.height // 3, 260))
        preview_width, preview_height = _aspect_fit_size(
            outer_width=preview_width,
            outer_height=preview_height,
            content_width=request.source_image_width_px,
            content_height=request.source_image_height_px,
        )
        if preview_width > 0 and preview_height > 0:
            source_preview_rect = RectSpec(
                status_panel_rect.x + status_panel_rect.width - preview_width - 12,
                status_panel_rect.y + status_panel_rect.height - preview_height - 12,
                preview_width,
                preview_height,
            )

    return WindowGeometry(
        board_width=board_width,
        board_height=board_height,
        total_cells=board_width * board_height,
        cell_px=cell_px,
        window_rect=RectSpec(0, 0, window_width, window_height),
        content_rect=content_rect,
        header_rect=header_rect,
        board_viewport_rect=board_viewport_rect,
        board_draw_rect=board_draw_rect,
        board_scale=board_scale,
        board_rect=board_rect,
        status_panel_rect=status_panel_rect,
        status_panel_content_rect=status_panel_content_rect,
        divider_rect=divider_rect,
        source_preview_rect=source_preview_rect,
        board_pixel_width=board_pixel_width,
        board_pixel_height=board_pixel_height,
        status_panel_width_px=panel_width,
        window_width=window_width,
        window_height=window_height,
        minimum_window_width=minimum_window_width,
        minimum_window_height=minimum_window_height,
        preferred_window_width=preferred_window_width,
        preferred_window_height=preferred_window_height,
        fits_screen=fits_screen,
        fits_window=fits_window,
        scale_reason=scale_reason,
    )


def _calculate_panel_width(*, window_width: int, configured_width: int) -> int:
    configured_width = max(0, int(configured_width))
    if configured_width <= 0:
        return 0
    window_width = max(1, int(window_width))
    target = min(
        max(configured_width, int(window_width * STATUS_PANEL_WINDOW_FRACTION)),
        min(MAX_STATUS_PANEL_WIDTH_PX, window_width // 2),
    )
    return max(1, int(target))


def _aspect_fit_size(
    *,
    outer_width: int,
    outer_height: int,
    content_width: int | None,
    content_height: int | None,
) -> tuple[int, int]:
    outer_width = max(0, int(outer_width))
    outer_height = max(0, int(outer_height))
    if outer_width <= 0 or outer_height <= 0:
        return (0, 0)
    source_width = int(content_width or 4)
    source_height = int(content_height or 3)
    if source_width <= 0 or source_height <= 0:
        source_width, source_height = 4, 3
    scale = min(outer_width / source_width, outer_height / source_height)
    return (max(1, int(round(source_width * scale))), max(1, int(round(source_height * scale))))
