"""
report.py — 6-subplot matplotlib diagnostic report.
"""
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

try:
    from .core import compute_N
    from .solver import SAFE, MINE, UNKNOWN
except ImportError:
    from core import compute_N
    from solver import SAFE, MINE, UNKNOWN


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
    fig.suptitle(title, fontsize=14, fontweight='bold')

    # Layout: 3 rows × 3 cols, but last row has 2 items with the second spanning
    axes = []
    for row in range(3):
        row_axes = []
        for col in range(3):
            ax = fig.add_subplot(3, 3, row * 3 + col + 1)
            row_axes.append(ax)
        axes.append(row_axes)

    # (0,0) Target
    im0 = axes[0][0].imshow(target, cmap='inferno', vmin=0, vmax=8)
    axes[0][0].set_title('Target T [0-8]')
    plt.colorbar(im0, ax=axes[0][0], fraction=0.046, pad=0.04)

    # (0,1) Mine grid
    axes[0][1].imshow(grid, cmap='binary', vmin=0, vmax=1)
    axes[0][1].set_title(f'Mine Grid  (density={grid.mean():.3f})')

    # (0,2) Number field N
    im2 = axes[0][2].imshow(N, cmap='inferno', vmin=0, vmax=8)
    axes[0][2].set_title('Number Field N')
    plt.colorbar(im2, ax=axes[0][2], fraction=0.046, pad=0.04)

    # (1,0) Error map
    err = np.abs(N.astype(np.float32) - target)
    im3 = axes[1][0].imshow(err, cmap='hot', vmin=0, vmax=4)
    axes[1][0].set_title(f'|N-T|  mean={err.mean():.3f}')
    plt.colorbar(im3, ax=axes[1][0], fraction=0.046, pad=0.04)

    # (1,1) Solver map
    if sr.state is not None:
        smap = np.zeros((*grid.shape, 3), dtype=np.float32)
        smap[sr.state == SAFE]  = [0.7, 0.7, 0.7]   # gray
        smap[sr.state == MINE]  = [1.0, 0.5, 0.0]   # orange
        smap[sr.state == UNKNOWN] = [0.2, 0.4, 0.9]  # blue
        axes[1][1].imshow(smap)
        legend = [
            mpatches.Patch(color=(0.7,0.7,0.7), label=f'Revealed ({sr.n_revealed})'),
            mpatches.Patch(color=(1.0,0.5,0.0), label=f'Flagged ({sr.n_mines - sr.n_unknown})'),
            mpatches.Patch(color=(0.2,0.4,0.9), label=f'Unknown ({sr.n_unknown})'),
        ]
        axes[1][1].legend(handles=legend, loc='lower right', fontsize=7)
    axes[1][1].set_title(f'Solver  cov={sr.coverage:.4f}  solvable={sr.solvable}')

    # (1,2) Loss curve
    hist = np.array(history, dtype=np.float64)
    hist = hist[hist > 0]
    if len(hist) > 1:
        axes[1][2].semilogy(hist)
        axes[1][2].set_title('Loss curve (log)')
        axes[1][2].set_xlabel('×50k iters')
        axes[1][2].set_ylabel('Weighted loss')
    else:
        axes[1][2].text(0.5, 0.5, 'No history', ha='center')
        axes[1][2].set_title('Loss curve')

    # (2,0) Histogram T vs N
    axes[2][0].hist(target.ravel(), bins=50, alpha=0.5, label='Target T', density=True, color='blue')
    axes[2][0].hist(N.ravel(),      bins=50, alpha=0.5, label='N field',  density=True, color='red')
    axes[2][0].set_title('T vs N distribution')
    axes[2][0].legend(fontsize=8)
    axes[2][0].set_xlabel('Value [0-8]')

    # (2,1) Metrics text
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
    axes[2][1].axis('off')
    axes[2][1].text(0.05, 0.95, metrics_text,
                    transform=axes[2][1].transAxes,
                    verticalalignment='top', fontsize=9,
                    fontfamily='monospace',
                    bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    axes[2][1].set_title('Metrics')

    # Hide unused (2,2)
    axes[2][2].axis('off')

    plt.tight_layout()
    plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
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
    before_unknown = np.zeros_like(grid_before, dtype=np.float32)
    after_unknown = np.zeros_like(grid_after, dtype=np.float32)
    if getattr(sr_before, "state", None) is not None:
        before_unknown = (sr_before.state == UNKNOWN).astype(np.float32)
    if getattr(sr_after, "state", None) is not None:
        after_unknown = (sr_after.state == UNKNOWN).astype(np.float32)

    before_n = compute_N(grid_before)
    after_n = compute_N(grid_after)
    error_delta = np.abs(after_n.astype(np.float32) - target.astype(np.float32)) - np.abs(
        before_n.astype(np.float32) - target.astype(np.float32)
    )
    removed = np.argwhere((grid_before == 1) & (grid_after == 0))
    added = np.argwhere((grid_before == 0) & (grid_after == 1))

    removed_overlay = np.zeros((*grid_before.shape, 3), dtype=np.float32)
    for y, x in removed:
        removed_overlay[int(y), int(x)] = [1.0, 0.2, 0.2]
    for y, x in added:
        removed_overlay[int(y), int(x)] = [0.2, 0.9, 0.2]

    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    ax = axes.ravel()

    im0 = ax[0].imshow(target, cmap='inferno', vmin=0, vmax=8)
    ax[0].set_title('Target image')
    plt.colorbar(im0, ax=ax[0], fraction=0.046, pad=0.04)

    ax[1].imshow(before_unknown, cmap='Blues', vmin=0, vmax=1)
    ax[1].set_title(f'Before UNKNOWNs ({int(np.sum(before_unknown))})')

    ax[2].imshow(after_unknown, cmap='Blues', vmin=0, vmax=1)
    ax[2].set_title(f'After UNKNOWNs ({int(np.sum(after_unknown))})')

    ax[3].imshow(removed_overlay)
    ax[3].set_title(f'Removed/Add mines (-{len(removed)} / +{len(added)})')

    im4 = ax[4].imshow(error_delta, cmap='coolwarm', vmin=-1.5, vmax=1.5)
    ax[4].set_title('Error delta |N_after-T| - |N_before-T|')
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
        summary_lines.append(f"last delta_unknown: {last_entry.get('delta_unknown', last_entry.get('delta_unk', 'n/a'))}")
    ax[5].axis('off')
    ax[5].text(
        0.05,
        0.95,
        "\n".join(summary_lines),
        transform=ax[5].transAxes,
        verticalalignment='top',
        fontsize=10,
        fontfamily='monospace',
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8),
    )
    ax[5].set_title('Repair summary')

    for item in ax:
        item.set_xticks([])
        item.set_yticks([])

    plt.tight_layout()
    plt.savefig(save_path, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
    print(f"  Repair overlay saved: {save_path}", flush=True)
