"""
report.py - Matplotlib diagnostic and explained report renderers.
"""

from __future__ import annotations

import textwrap

import matplotlib

matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np

try:
    from .core import compute_N
    from .solver import MINE, SAFE, UNKNOWN
except ImportError:
    from core import compute_N
    from solver import MINE, SAFE, UNKNOWN


REPORT_PANEL_CAPTIONS = {
    "target_image": "This panel shows the target image after it was converted into Mine-Streaker number values from 0 to 8.",
    "mine_grid": "This panel shows the generated mine layout itself, where darker cells mark mined positions in the final board.",
    "number_field": "This panel shows the numbers created by the generated mine layout, which is the pattern Mine-Streaker tries to match to the target image.",
    "error_map": "This panel highlights where the generated number field differs from the target image, so brighter areas deserve closer review.",
    "solver_result": "This panel shows what the solver could prove: gray cells are revealed safe cells, orange cells are identified mines, and blue cells remain unresolved.",
    "loss_curve": "This panel tracks how the weighted optimization loss changed during simulated annealing, which helps show whether the search settled into a better solution.",
    "distribution": "This panel compares the overall value distribution of the target image and the generated number field to show whether their shapes broadly agree.",
    "metrics": "This section translates the key quality numbers into plain language so a reviewer can tell whether the board is solved and visually close to the target.",
}

REPAIR_PANEL_CAPTIONS = {
    "target_image": "This panel shows the target image values that the repair pass is trying to respect while it resolves solver failures.",
    "before_unknown": "This panel shows which cells were still unresolved before the late-stage repair route finished its work.",
    "after_unknown": "This panel shows which unresolved cells remained after repair, so an empty or nearly empty view is a good sign.",
    "mine_changes": "This panel marks cells where repair removed mines in red or added mines in green to break solver dead-ends.",
    "error_delta": "This panel shows whether repair made the visual number mismatch better or worse compared with the pre-repair board.",
    "repair_summary": "This section explains how many unknown cells repair removed, how many mines changed, and whether the board ended solved.",
}

_WRAP_WIDTH = 58
_TITLE_WRAP_WIDTH = 92
_FOOTER_WRAP_WIDTH = 108


def _wrap_text(text: str, width: int) -> str:
    paragraphs = [part.strip() for part in str(text).splitlines()]
    wrapped: list[str] = []
    for paragraph in paragraphs:
        if not paragraph:
            wrapped.append("")
            continue
        wrapped.append(textwrap.fill(paragraph, width=width))
    return "\n".join(wrapped)


def _wrap_lines(lines: list[str], width: int) -> str:
    wrapped_parts = [_wrap_text(line, width) for line in lines if str(line).strip()]
    return "\n\n".join(wrapped_parts)


def _text_axis(ax, title: str, lines: list[str], *, width: int, fontsize: int = 10) -> None:
    ax.axis("off")
    body = _wrap_lines(lines, width)
    title_text = _wrap_text(title, width)
    if body:
        text = f"{title_text}\n\n{body}"
    else:
        text = title_text
    ax.text(
        0.02,
        0.98,
        text,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=fontsize,
        wrap=True,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.92),
    )


def _footer_axis(ax, footer_text: str) -> None:
    ax.axis("off")
    ax.text(
        0.01,
        0.45,
        _wrap_text(footer_text, _FOOTER_WRAP_WIDTH),
        transform=ax.transAxes,
        va="center",
        ha="left",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="whitesmoke", alpha=0.95),
    )


def _coalesce(*values):
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _source_name(metrics: dict) -> str | None:
    source_block = metrics.get("source_image", {})
    return _coalesce(
        source_block.get("name"),
        metrics.get("image_name"),
        metrics.get("source_image_name"),
    )


def _board_label(metrics: dict) -> str:
    board = metrics.get("board")
    if board:
        return str(board)
    width = metrics.get("board_width")
    height = metrics.get("board_height")
    if width is not None and height is not None:
        return f"{width}x{height}"
    run_identity = metrics.get("run_identity", {})
    width = run_identity.get("board_width")
    height = run_identity.get("board_height")
    if width is not None and height is not None:
        return f"{width}x{height}"
    return "unknown-size"


def _seed_value(metrics: dict):
    return _coalesce(metrics.get("seed"), metrics.get("run_identity", {}).get("seed"), "unknown")


def _run_id(metrics: dict) -> str:
    return str(_coalesce(metrics.get("run_id"), metrics.get("run_identity", {}).get("run_id"), "unknown-run"))


def _bool_word(value) -> str:
    return "yes" if bool(value) else "no"


def _percent_text(value, *, decimals: int = 1) -> str:
    if value is None:
        return "unknown"
    return f"{float(value) * 100:.{decimals}f}%"


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _count_word(count: int, singular: str, plural: str) -> str:
    return singular if int(count) == 1 else plural


def _solver_map_rgb(sr, shape: tuple[int, int]) -> np.ndarray:
    smap = np.zeros((shape[0], shape[1], 3), dtype=np.float32)
    state = getattr(sr, "state", None)
    if state is None:
        return smap
    smap[state == SAFE] = [0.7, 0.7, 0.7]
    smap[state == MINE] = [1.0, 0.5, 0.0]
    smap[state == UNKNOWN] = [0.2, 0.4, 0.9]
    return smap


def _unknown_mask(sr, shape: tuple[int, int]) -> np.ndarray:
    state = getattr(sr, "state", None)
    if state is None:
        return np.zeros(shape, dtype=np.float32)
    return (state == UNKNOWN).astype(np.float32)


def _mine_change_overlay(grid_before: np.ndarray, grid_after: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    removed = np.argwhere((grid_before == 1) & (grid_after == 0))
    added = np.argwhere((grid_before == 0) & (grid_after == 1))
    overlay = np.zeros((*grid_before.shape, 3), dtype=np.float32)
    for y, x in removed:
        overlay[int(y), int(x)] = [1.0, 0.2, 0.2]
    for y, x in added:
        overlay[int(y), int(x)] = [0.2, 0.9, 0.2]
    return overlay, removed, added


def _format_metric_explanations(metrics: dict) -> list[str]:
    coverage = _safe_float(metrics.get("coverage"))
    mine_accuracy = _safe_float(metrics.get("mine_accuracy"))
    mean_abs_error = _safe_float(metrics.get("mean_abs_error"))
    mine_density = _safe_float(metrics.get("mine_density"))
    n_unknown = _safe_int(metrics.get("n_unknown"))
    route = _coalesce(metrics.get("repair_route_selected"), "unknown repair route")
    lines = [
        f"The solver proved {_percent_text(coverage)} of safe cells, which tells you how complete the logical solve became.",
        (
            "The board finished with no unresolved cells left."
            if n_unknown == 0
            else f"The board still has {n_unknown} unresolved cells, so it is not fully settled yet."
        ),
        f"The generated numbers stayed about {mean_abs_error:.2f} away from the target values on average, so lower is visually better.",
        f"When the solver marked mines, it was correct about {_percent_text(mine_accuracy)} of the time.",
        f"About {_percent_text(mine_density)} of all cells are mines, which describes the final board density.",
        f"The late-stage route used here was {route}, which explains how the pipeline finished the board.",
    ]
    return lines


def build_plain_english_run_summary(metrics: dict) -> list[str]:
    board = _board_label(metrics)
    seed = _seed_value(metrics)
    source_name = _source_name(metrics)
    n_unknown = _safe_int(metrics.get("n_unknown"))
    solved = bool(metrics.get("solvable")) and n_unknown == 0
    route = _coalesce(metrics.get("repair_route_selected"), "unknown route")
    if source_name:
        intro = f"This run used {source_name} to build a {board} board with seed {seed}."
    else:
        intro = f"This run built a {board} board with seed {seed}."
    if solved:
        result = "The solver resolved all cells, so the board finished completely solved."
    else:
        result = f"The solver still left {n_unknown} unresolved cells, so the board did not finish fully solved."
    return [f"{intro} {result} The final route was {route}.", *_format_metric_explanations(metrics)]


def build_plain_english_repair_summary(
    *,
    before_unknown: int,
    after_unknown: int,
    removed_mines: int,
    added_mines: int,
    solved_after: bool,
) -> list[str]:
    lines = [
        f"Repair started with {before_unknown} unresolved cells before the late-stage route made any changes.",
        f"Repair finished with {after_unknown} unresolved cells after those changes were applied.",
        (
            f"Repair removed {removed_mines} {_count_word(removed_mines, 'mine', 'mines')} and "
            f"added {added_mines} {_count_word(added_mines, 'mine', 'mines')} to break dead-ends and open solver progress."
        ),
        (
            "After repair, the board became fully solved."
            if solved_after
            else "After repair, the board still had unresolved cells left."
        ),
    ]
    return lines


def _report_footer(metrics: dict) -> str:
    parts = [f"Run ID: {_run_id(metrics)}", f"Board: {_board_label(metrics)}", f"Seed: {_seed_value(metrics)}"]
    source_name = _source_name(metrics)
    if source_name:
        parts.append(f"Source image: {source_name}")
    return " | ".join(parts)


def render_report(target, grid, sr, history, title, save_path, dpi=120):
    """
    6-subplot report:
      (0,0) Target image [0-8]
      (0,1) Mine grid binary
      (0,2) Number field N
      (1,0) |N-T| error map
      (1,1) Solver state map
      (1,2) Loss curve
      (2,0) T vs N distribution histogram
      (2,1) Metrics text table
    """
    N = compute_N(grid)
    fig = plt.figure(figsize=(18, 12))
    fig.suptitle(title, fontsize=14, fontweight="bold")

    axes = []
    for row in range(3):
        row_axes = []
        for col in range(3):
            ax = fig.add_subplot(3, 3, row * 3 + col + 1)
            row_axes.append(ax)
        axes.append(row_axes)

    im0 = axes[0][0].imshow(target, cmap="inferno", vmin=0, vmax=8)
    axes[0][0].set_title("Target T [0-8]")
    plt.colorbar(im0, ax=axes[0][0], fraction=0.046, pad=0.04)

    axes[0][1].imshow(grid, cmap="binary", vmin=0, vmax=1)
    axes[0][1].set_title(f"Mine Grid  (density={grid.mean():.3f})")

    im2 = axes[0][2].imshow(N, cmap="inferno", vmin=0, vmax=8)
    axes[0][2].set_title("Number Field N")
    plt.colorbar(im2, ax=axes[0][2], fraction=0.046, pad=0.04)

    err = np.abs(N.astype(np.float32) - target)
    im3 = axes[1][0].imshow(err, cmap="hot", vmin=0, vmax=4)
    axes[1][0].set_title(f"|N-T|  mean={err.mean():.3f}")
    plt.colorbar(im3, ax=axes[1][0], fraction=0.046, pad=0.04)

    if sr.state is not None:
        smap = _solver_map_rgb(sr, grid.shape)
        axes[1][1].imshow(smap)
        legend = [
            mpatches.Patch(color=(0.7, 0.7, 0.7), label=f"Revealed ({sr.n_revealed})"),
            mpatches.Patch(color=(1.0, 0.5, 0.0), label=f"Flagged ({sr.n_mines - sr.n_unknown})"),
            mpatches.Patch(color=(0.2, 0.4, 0.9), label=f"Unknown ({sr.n_unknown})"),
        ]
        axes[1][1].legend(handles=legend, loc="lower right", fontsize=7)
    axes[1][1].set_title(f"Solver  cov={sr.coverage:.4f}  solvable={sr.solvable}")

    hist = np.array(history, dtype=np.float64)
    hist = hist[hist > 0]
    if len(hist) > 1:
        axes[1][2].semilogy(hist)
        axes[1][2].set_title("Loss curve (log)")
        axes[1][2].set_xlabel("x50k iters")
        axes[1][2].set_ylabel("Weighted loss")
    else:
        axes[1][2].text(0.5, 0.5, "No history", ha="center")
        axes[1][2].set_title("Loss curve")

    axes[2][0].hist(target.ravel(), bins=50, alpha=0.5, label="Target T", density=True, color="blue")
    axes[2][0].hist(N.ravel(), bins=50, alpha=0.5, label="N field", density=True, color="red")
    axes[2][0].set_title("T vs N distribution")
    axes[2][0].legend(fontsize=8)
    axes[2][0].set_xlabel("Value [0-8]")

    mae = float(err.mean())
    within1 = float(np.mean(err <= 1.0)) * 100
    within2 = float(np.mean(err <= 2.0)) * 100
    metrics_text = (
        f"coverage:      {sr.coverage:.4f}\n"
        f"solvable:      {sr.solvable}\n"
        f"mine_accuracy: {sr.mine_accuracy:.4f}\n"
        f"n_unknown:     {sr.n_unknown}\n"
        f"n_safe:        {sr.n_safe}\n"
        f"n_mines:       {sr.n_mines}\n"
        f"mean_abs_err:  {mae:.4f}\n"
        f"pct_within_1:  {within1:.1f}%\n"
        f"pct_within_2:  {within2:.1f}%\n"
        f"mine_density:  {grid.mean():.4f}\n"
    )
    axes[2][1].axis("off")
    axes[2][1].text(
        0.05,
        0.95,
        metrics_text,
        transform=axes[2][1].transAxes,
        verticalalignment="top",
        fontsize=9,
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )
    axes[2][1].set_title("Metrics")

    axes[2][2].axis("off")

    plt.tight_layout()
    plt.savefig(save_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Report saved: {save_path}", flush=True)


def render_report_explained(
    target,
    grid,
    sr,
    history,
    title,
    save_path,
    *,
    metrics: dict,
    dpi: int = 120,
):
    n_field = compute_N(grid)
    err = np.abs(n_field.astype(np.float32) - target.astype(np.float32))
    hist = np.array(history, dtype=np.float64)
    hist = hist[hist > 0]

    fig = plt.figure(figsize=(21, 14))
    gs = gridspec.GridSpec(
        4,
        4,
        figure=fig,
        height_ratios=[0.9, 2.2, 2.2, 0.7],
        width_ratios=[1.2, 1.2, 1.2, 1.15],
        hspace=0.35,
        wspace=0.28,
    )

    title_ax = fig.add_subplot(gs[0, :])
    title_ax.axis("off")
    title_lines = build_plain_english_run_summary(metrics)
    title_ax.text(
        0.01,
        0.85,
        _wrap_text(title, _TITLE_WRAP_WIDTH),
        transform=title_ax.transAxes,
        va="top",
        ha="left",
        fontsize=18,
        fontweight="bold",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.95),
    )
    title_ax.text(
        0.01,
        0.18,
        _wrap_text(title_lines[0], _TITLE_WRAP_WIDTH),
        transform=title_ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=11,
        bbox=dict(boxstyle="round", facecolor="aliceblue", alpha=0.95),
    )

    ax_target = fig.add_subplot(gs[1, 0])
    ax_grid = fig.add_subplot(gs[1, 1])
    ax_numbers = fig.add_subplot(gs[1, 2])
    ax_error = fig.add_subplot(gs[2, 0])
    ax_solver = fig.add_subplot(gs[2, 1])
    ax_history = fig.add_subplot(gs[2, 2])
    caption_ax = fig.add_subplot(gs[1, 3])
    metrics_ax = fig.add_subplot(gs[2, 3])
    footer_ax = fig.add_subplot(gs[3, :])

    im_target = ax_target.imshow(target, cmap="inferno", vmin=0, vmax=8)
    ax_target.set_title("Target image", fontsize=12)
    plt.colorbar(im_target, ax=ax_target, fraction=0.046, pad=0.04)

    ax_grid.imshow(grid, cmap="binary", vmin=0, vmax=1)
    ax_grid.set_title("Generated mine layout", fontsize=12)

    im_numbers = ax_numbers.imshow(n_field, cmap="inferno", vmin=0, vmax=8)
    ax_numbers.set_title("Generated number field", fontsize=12)
    plt.colorbar(im_numbers, ax=ax_numbers, fraction=0.046, pad=0.04)

    im_error = ax_error.imshow(err, cmap="hot", vmin=0, vmax=4)
    ax_error.set_title("Difference from target", fontsize=12)
    plt.colorbar(im_error, ax=ax_error, fraction=0.046, pad=0.04)

    solver_map = _solver_map_rgb(sr, grid.shape)
    ax_solver.imshow(solver_map)
    ax_solver.set_title("Solver result", fontsize=12)
    legend = [
        mpatches.Patch(color=(0.7, 0.7, 0.7), label=f"Revealed ({getattr(sr, 'n_revealed', 0)})"),
        mpatches.Patch(color=(1.0, 0.5, 0.0), label=f"Flagged ({max(getattr(sr, 'n_mines', 0) - getattr(sr, 'n_unknown', 0), 0)})"),
        mpatches.Patch(color=(0.2, 0.4, 0.9), label=f"Unknown ({getattr(sr, 'n_unknown', 0)})"),
    ]
    ax_solver.legend(handles=legend, loc="lower right", fontsize=7)

    if len(hist) > 1:
        ax_history.semilogy(hist)
        ax_history.set_title("Optimization progress", fontsize=12)
        ax_history.set_xlabel("x50k iterations")
        ax_history.set_ylabel("Weighted loss")
    else:
        ax_history.text(0.5, 0.5, "No optimization history was recorded for this run.", ha="center", va="center")
        ax_history.set_title("Optimization progress", fontsize=12)

    caption_lines = [
        f"Target image: {REPORT_PANEL_CAPTIONS['target_image']}",
        f"Generated number field: {REPORT_PANEL_CAPTIONS['number_field']}",
        f"Solver result: {REPORT_PANEL_CAPTIONS['solver_result']}",
        f"Difference view: {REPORT_PANEL_CAPTIONS['error_map']}",
    ]
    _text_axis(caption_ax, "What these panels mean", caption_lines, width=_WRAP_WIDTH, fontsize=10)

    metric_lines = _format_metric_explanations(metrics)
    metric_lines.append(REPORT_PANEL_CAPTIONS["metrics"])
    _text_axis(metrics_ax, "How to read the results", metric_lines, width=_WRAP_WIDTH, fontsize=10)

    for axis in (ax_target, ax_grid, ax_numbers, ax_error, ax_solver, ax_history):
        axis.set_xticks([])
        axis.set_yticks([])

    _footer_axis(footer_ax, _report_footer(metrics))

    plt.savefig(save_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Report saved: {save_path}", flush=True)


def render_repair_overlay(
    target: np.ndarray,
    grid_before: np.ndarray,
    grid_after: np.ndarray,
    sr_before,
    sr_after,
    repair_log: list,
    save_path: str,
    dpi: int = 120,
) -> None:
    """
    Render repair cause/effect overlay.
    """
    before_unknown = _unknown_mask(sr_before, grid_before.shape)
    after_unknown = _unknown_mask(sr_after, grid_after.shape)

    before_n = compute_N(grid_before)
    after_n = compute_N(grid_after)
    error_delta = np.abs(after_n.astype(np.float32) - target.astype(np.float32)) - np.abs(
        before_n.astype(np.float32) - target.astype(np.float32)
    )
    removed_overlay, removed, added = _mine_change_overlay(grid_before, grid_after)

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    ax = axes.ravel()

    im0 = ax[0].imshow(target, cmap="inferno", vmin=0, vmax=8)
    ax[0].set_title("Target image")
    plt.colorbar(im0, ax=ax[0], fraction=0.046, pad=0.04)

    ax[1].imshow(before_unknown, cmap="Blues", vmin=0, vmax=1)
    ax[1].set_title(f"Before UNKNOWNs ({int(np.sum(before_unknown))})")

    ax[2].imshow(after_unknown, cmap="Blues", vmin=0, vmax=1)
    ax[2].set_title(f"After UNKNOWNs ({int(np.sum(after_unknown))})")

    ax[3].imshow(removed_overlay)
    ax[3].set_title(f"Removed/Add mines (-{len(removed)} / +{len(added)})")

    im4 = ax[4].imshow(error_delta, cmap="coolwarm", vmin=-1.5, vmax=1.5)
    ax[4].set_title("Error delta |N_after-T| - |N_before-T|")
    plt.colorbar(im4, ax=ax[4], fraction=0.046, pad=0.04)

    summary_lines = [
        f"route repairs: {len(repair_log)}",
        f"before unknown: {getattr(sr_before, 'n_unknown', 'n/a')}",
        f"after unknown: {getattr(sr_after, 'n_unknown', 'n/a')}",
        f"removed mines: {len(removed)}",
        f"added mines: {len(added)}",
    ]
    if repair_log:
        last_entry = repair_log[-1]
        summary_lines.append(f"last move: {last_entry.get('move_type', 'n/a')}")
        summary_lines.append(
            f"last delta_unknown: {last_entry.get('delta_unknown', last_entry.get('delta_unk', 'n/a'))}"
        )
    ax[5].axis("off")
    ax[5].text(
        0.05,
        0.95,
        "\n".join(summary_lines),
        transform=ax[5].transAxes,
        verticalalignment="top",
        fontsize=10,
        fontfamily="monospace",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
    )
    ax[5].set_title("Repair summary")

    for item in ax:
        item.set_xticks([])
        item.set_yticks([])

    plt.tight_layout()
    plt.savefig(save_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Repair overlay saved: {save_path}", flush=True)


def render_repair_overlay_explained(
    target: np.ndarray,
    grid_before: np.ndarray,
    grid_after: np.ndarray,
    sr_before,
    sr_after,
    repair_log: list,
    save_path: str,
    *,
    metrics: dict,
    dpi: int = 120,
) -> None:
    before_unknown = _unknown_mask(sr_before, grid_before.shape)
    after_unknown = _unknown_mask(sr_after, grid_after.shape)
    before_n = compute_N(grid_before)
    after_n = compute_N(grid_after)
    error_delta = np.abs(after_n.astype(np.float32) - target.astype(np.float32)) - np.abs(
        before_n.astype(np.float32) - target.astype(np.float32)
    )
    change_overlay, removed, added = _mine_change_overlay(grid_before, grid_after)

    before_unknown_count = _safe_int(metrics.get("before_unknown"), int(np.sum(before_unknown)))
    after_unknown_count = _safe_int(metrics.get("after_unknown"), int(np.sum(after_unknown)))
    removed_count = _safe_int(metrics.get("removed_mines"), len(removed))
    added_count = _safe_int(metrics.get("added_mines"), len(added))
    solved_after = bool(metrics.get("solved_after")) or (
        bool(getattr(sr_after, "solvable", False)) and _safe_int(getattr(sr_after, "n_unknown", 0)) == 0
    )

    fig = plt.figure(figsize=(21, 14))
    gs = gridspec.GridSpec(
        4,
        4,
        figure=fig,
        height_ratios=[0.9, 2.2, 2.2, 0.7],
        width_ratios=[1.2, 1.2, 1.2, 1.15],
        hspace=0.35,
        wspace=0.28,
    )

    title_ax = fig.add_subplot(gs[0, :])
    title_ax.axis("off")
    title_ax.text(
        0.01,
        0.85,
        _wrap_text("Mine-Streaker explained repair overlay", _TITLE_WRAP_WIDTH),
        transform=title_ax.transAxes,
        va="top",
        ha="left",
        fontsize=18,
        fontweight="bold",
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.95),
    )
    title_ax.text(
        0.01,
        0.18,
        _wrap_text(
            (
                f"Repair started with {before_unknown_count} unresolved cells and finished with "
                f"{after_unknown_count}. The board {'did' if solved_after else 'did not'} finish solved."
            ),
            _TITLE_WRAP_WIDTH,
        ),
        transform=title_ax.transAxes,
        va="bottom",
        ha="left",
        fontsize=11,
        bbox=dict(boxstyle="round", facecolor="aliceblue", alpha=0.95),
    )

    ax_target = fig.add_subplot(gs[1, 0])
    ax_before = fig.add_subplot(gs[1, 1])
    ax_after = fig.add_subplot(gs[1, 2])
    ax_changes = fig.add_subplot(gs[2, 0])
    ax_delta = fig.add_subplot(gs[2, 1])
    caption_ax = fig.add_subplot(gs[1, 3])
    summary_ax = fig.add_subplot(gs[2, 2:])
    footer_ax = fig.add_subplot(gs[3, :])

    im_target = ax_target.imshow(target, cmap="inferno", vmin=0, vmax=8)
    ax_target.set_title("Target image", fontsize=12)
    plt.colorbar(im_target, ax=ax_target, fraction=0.046, pad=0.04)

    ax_before.imshow(before_unknown, cmap="Blues", vmin=0, vmax=1)
    ax_before.set_title(f"Before repair ({before_unknown_count} unknown)", fontsize=12)

    ax_after.imshow(after_unknown, cmap="Blues", vmin=0, vmax=1)
    ax_after.set_title(f"After repair ({after_unknown_count} unknown)", fontsize=12)

    ax_changes.imshow(change_overlay)
    ax_changes.set_title(f"Mine changes (-{removed_count} / +{added_count})", fontsize=12)

    im_delta = ax_delta.imshow(error_delta, cmap="coolwarm", vmin=-1.5, vmax=1.5)
    ax_delta.set_title("Visual change after repair", fontsize=12)
    plt.colorbar(im_delta, ax=ax_delta, fraction=0.046, pad=0.04)

    caption_lines = [
        f"Before unknown cells: {REPAIR_PANEL_CAPTIONS['before_unknown']}",
        f"After unknown cells: {REPAIR_PANEL_CAPTIONS['after_unknown']}",
        f"Mine changes: {REPAIR_PANEL_CAPTIONS['mine_changes']}",
        f"Visual change: {REPAIR_PANEL_CAPTIONS['error_delta']}",
    ]
    _text_axis(caption_ax, "What these repair panels mean", caption_lines, width=_WRAP_WIDTH, fontsize=10)

    repair_lines = build_plain_english_repair_summary(
        before_unknown=before_unknown_count,
        after_unknown=after_unknown_count,
        removed_mines=removed_count,
        added_mines=added_count,
        solved_after=solved_after,
    )
    if repair_log:
        last_entry = repair_log[-1]
        move_type = _coalesce(last_entry.get("move_type"), "unknown")
        delta_unknown = _coalesce(last_entry.get("delta_unknown"), last_entry.get("delta_unk"), "unknown")
        repair_lines.append(
            f"The last logged repair move was {move_type}, and it changed the unresolved-cell count by {delta_unknown}."
        )
    repair_lines.append(REPAIR_PANEL_CAPTIONS["repair_summary"])
    _text_axis(summary_ax, "Plain-English repair summary", repair_lines, width=66, fontsize=11)

    for axis in (ax_target, ax_before, ax_after, ax_changes, ax_delta):
        axis.set_xticks([])
        axis.set_yticks([])

    _footer_axis(footer_ax, _report_footer(metrics))

    plt.savefig(save_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)
    print(f"  Repair overlay saved: {save_path}", flush=True)
