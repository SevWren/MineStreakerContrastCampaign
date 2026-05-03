"""Pure status panel view models for polished demo rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from demos.iter9_visual_solver.rendering.status_text import build_status_lines


@dataclass(frozen=True)
class ProgressSpec:
    key: str
    label: str
    current: int
    total: int
    ratio: float
    value_text: str
    good_when_zero: bool = False


@dataclass(frozen=True)
class MetricRowSpec:
    label: str
    value: str


@dataclass(frozen=True)
class MetricCardSpec:
    key: str
    title: str
    lines: tuple[str, ...]
    rows: tuple[MetricRowSpec, ...] = ()


@dataclass(frozen=True)
class LegendItemSpec:
    label: str
    rgb: tuple[int, int, int]


@dataclass(frozen=True)
class CompletionBadgeSpec:
    label: str
    detail: str
    state: str


@dataclass(frozen=True)
class SourcePreviewSpec:
    label: str
    detail: str
    state: str = "placeholder"


@dataclass(frozen=True)
class StatusPanelViewModel:
    header_text: str
    badge: CompletionBadgeSpec
    cards: tuple[MetricCardSpec, ...]
    progress_bars: tuple[ProgressSpec, ...]
    legend_items: tuple[LegendItemSpec, ...]
    raw_lines: tuple[str, ...]
    source_preview: SourcePreviewSpec


def _value(source: Any, name: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _visible(config: Any, name: str) -> bool:
    if config is None:
        return True
    return bool(_value(config, name, True))


def _ratio(current: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(float(current) / float(total), 1.0))


def _progress(key: str, label: str, current: int, total: int, *, good_when_zero: bool = False) -> ProgressSpec:
    return ProgressSpec(
        key=key,
        label=label,
        current=int(current),
        total=int(total),
        ratio=_ratio(int(current), int(total)),
        value_text=f"{int(current)} / {int(total)}",
        good_when_zero=good_when_zero,
    )


def build_status_panel_view_model(
    *,
    snapshot: Any,
    status_config: Any | None,
    palette: Any,
    show_safe_cells: bool,
    show_unknown_cells: bool,
) -> StatusPanelViewModel:
    raw_lines = tuple(build_status_lines(snapshot, status_config))
    source_name = str(_value(snapshot, "source_image_name", "") or "unknown")
    board = f"{int(_value(snapshot, 'board_width', 0))} x {int(_value(snapshot, 'board_height', 0))}"
    seed = _value(snapshot, "seed", "unknown")
    replay_source = str(_value(snapshot, "replay_source", "") or "").strip()
    header_parts = ["Mine-Streaker Iter9 Visual Solver Demo"]
    if _visible(status_config, "show_source_image"):
        header_parts.append(f"Source: {source_name}")
    if _visible(status_config, "show_board_dimensions"):
        header_parts.append(f"Board: {board}")
    if _visible(status_config, "show_seed"):
        header_parts.append(f"Seed: {seed}")
    if replay_source:
        header_parts.append(f"Replay: {replay_source}")

    unknown_remaining = int(_value(snapshot, "unknown_remaining", 0) or 0)
    finish_state = str(_value(snapshot, "finish_state", "running") or "running")
    if unknown_remaining == 0 and finish_state.startswith("complete"):
        badge = CompletionBadgeSpec(label="SOLVED", detail="0 unknown cells", state="solved")
    elif finish_state == "running":
        badge = CompletionBadgeSpec(label="RUNNING", detail=f"{unknown_remaining} unknown remaining", state="running")
    else:
        badge = CompletionBadgeSpec(label="IN REVIEW", detail=f"{unknown_remaining} unknown remaining", state="warning")

    cards: list[MetricCardSpec] = []
    if _visible(status_config, "show_total_cells") or _visible(status_config, "show_board_dimensions"):
        lines = []
        rows = []
        if _visible(status_config, "show_board_dimensions"):
            lines.append(f"Board: {board}")
            rows.append(MetricRowSpec("Board", board))
        if _visible(status_config, "show_total_cells"):
            total_cells_text = str(int(_value(snapshot, 'total_cells', 0) or 0))
            lines.append(f"Total cells: {total_cells_text}")
            rows.append(MetricRowSpec("Total cells", total_cells_text))
        cards.append(MetricCardSpec(key="board", title="Board", lines=tuple(lines), rows=tuple(rows)))
    count_lines = []
    count_rows = []
    if _visible(status_config, "show_mines_flagged"):
        value = f"{int(_value(snapshot, 'mines_flagged', 0) or 0)} / {int(_value(snapshot, 'total_mines', 0) or 0)}"
        count_lines.append(f"Mines flagged: {value}")
        count_rows.append(MetricRowSpec("Mines flagged", value))
    if _visible(status_config, "show_safe_cells_solved"):
        value = f"{int(_value(snapshot, 'safe_cells_solved', 0) or 0)} / {int(_value(snapshot, 'safe_cells', 0) or 0)}"
        count_lines.append(f"Safe solved: {value}")
        count_rows.append(MetricRowSpec("Safe solved", value))
    if _visible(status_config, "show_unknown_remaining"):
        count_lines.append(f"Unknown: {unknown_remaining}")
        count_rows.append(MetricRowSpec("Unknown", str(unknown_remaining)))
    if count_lines:
        cards.append(MetricCardSpec(key="progress", title="Progress", lines=tuple(count_lines), rows=tuple(count_rows)))

    total_cells = int(_value(snapshot, "total_cells", 0) or 0)
    progress_bars = (
        _progress("mines", "Mines", int(_value(snapshot, "mines_flagged", 0) or 0), int(_value(snapshot, "total_mines", 0) or 0)),
        _progress("safe", "Safe", int(_value(snapshot, "safe_cells_solved", 0) or 0), int(_value(snapshot, "safe_cells", 0) or 0)),
        _progress("resolved", "Resolved", max(total_cells - unknown_remaining, 0), total_cells, good_when_zero=True),
    )

    legend = [LegendItemSpec("Mine", tuple(palette.flagged_mine_rgb))]
    if show_safe_cells:
        legend.append(LegendItemSpec("Safe", tuple(palette.safe_cell_rgb)))
    if show_unknown_cells:
        legend.append(LegendItemSpec("Unknown", tuple(palette.unknown_cell_rgb)))
    legend.append(LegendItemSpec("Unseen", tuple(palette.unseen_cell_rgb)))

    preview_detail = "Reserved preview slot"
    if source_name == "unknown":
        preview_detail = "Source image unavailable"
    return StatusPanelViewModel(
        header_text=" | ".join(header_parts),
        badge=badge,
        cards=tuple(cards),
        progress_bars=progress_bars,
        legend_items=tuple(legend),
        raw_lines=raw_lines,
        source_preview=SourcePreviewSpec(label=source_name, detail=preview_detail),
    )
