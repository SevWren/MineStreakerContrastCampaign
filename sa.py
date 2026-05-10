"""
sa.py — Compiled simulated annealing kernel with Numba.
Structured for parallel multi-start execution at the caller level.
"""
import numpy as np
from numba import njit

try:
    from .core import compute_N as _compute_N
except ImportError:
    from core import compute_N as _compute_N


def _as_contig(arr: np.ndarray, dtype) -> np.ndarray:
    if arr.dtype == dtype and arr.flags.c_contiguous:
        return arr
    return np.ascontiguousarray(arr, dtype=dtype)


@njit(cache=True, fastmath=True)
def _sa_kernel(grid, N_field, target, weights, forbidden,
               n_iters, T_start, T_min, alpha,
               border, H, W, seed):
    """
    Single SA chain. All inputs are fixed-width NumPy arrays.
    Returns (best_grid int8, best_loss float64, history float64[]).
    """
    # Seed the Numba PRNG
    np.random.seed(seed)

    best_grid = grid.copy()
    current_loss = np.float64(0.0)
    for y in range(H):
        for x in range(W):
            diff = np.float64(N_field[y, x]) - np.float64(target[y, x])
            current_loss += np.float64(weights[y, x]) * diff * diff

    best_loss = current_loss
    T = np.float64(T_start)
    log_interval = np.int64(50000)
    n_log = n_iters // log_interval + 1
    history = np.zeros(n_log, dtype=np.float64)
    h_idx = np.int64(0)

    for it in range(n_iters):
        # Random candidate cell
        y = np.int32(border + np.random.randint(0, H - 2 * border))
        x = np.int32(border + np.random.randint(0, W - 2 * border))

        # Hard-reject: forbidden cell that is currently 0 (would become mine)
        cur_val = grid[y, x]
        if cur_val == 0 and forbidden[y, x] == 1:
            continue

        # Proposed new value
        new_val = np.int8(1 - cur_val)

        # Compute delta loss for this flip
        # Affected neighbours: all cells in [y-1:y+2, x-1:x+2]
        delta = np.float64(0.0)
        for dy in range(-1, 2):
            ny = y + dy
            if ny < 0 or ny >= H:
                continue
            for dx in range(-1, 2):
                nx = x + dx
                if ny == y and nx == x:
                    # Centre cell: N[y,x] doesn't include itself
                    continue
                if nx < 0 or nx >= W:
                    continue
                old_N = np.float64(N_field[ny, nx])
                new_N = old_N + np.float64(new_val - cur_val)
                # Hard-reject if N would leave [0, 8]
                if new_N < 0.0 or new_N > 8.0:
                    delta = np.float64(1e18)  # sentinel
                    break
                t = np.float64(target[ny, nx])
                w = np.float64(weights[ny, nx])
                delta += w * (new_N - t) * (new_N - t) - w * (old_N - t) * (old_N - t)
            if delta >= 1e17:
                break

        if delta >= 1e17:
            continue

        # Metropolis acceptance
        if delta < 0.0 or np.random.random() < np.exp(-delta / T):
            # Apply flip
            grid[y, x] = new_val
            # Update N field incrementally
            for dy in range(-1, 2):
                ny = y + dy
                if ny < 0 or ny >= H:
                    continue
                for dx in range(-1, 2):
                    nx = x + dx
                    if ny == y and nx == x:
                        continue
                    if nx < 0 or nx >= W:
                        continue
                    N_field[ny, nx] = np.uint8(
                        np.int32(N_field[ny, nx]) + np.int32(new_val - cur_val))
            current_loss += delta
            if current_loss < best_loss:
                best_loss = current_loss
                best_grid = grid.copy()

        # Temperature schedule
        T = T * alpha
        if T < T_min:
            T = np.float64(T_min)

        # Log
        if it % log_interval == 0:
            history[h_idx] = current_loss
            h_idx += 1

    history[h_idx] = current_loss
    return best_grid, best_loss, history


def compile_sa_kernel():
    """
    Warm up Numba kernel on tiny board, verify correctness, return callable.
    Returns the compiled _sa_kernel function.
    """
    print("  Warming up SA kernel on 8×8 board…", flush=True)
    H, W = 8, 8
    grid_w = np.zeros((H, W), dtype=np.int8)
    # Manually set a few mines for warmup
    grid_w[2, 2] = 1; grid_w[5, 5] = 1
    N_w = np.zeros((H, W), dtype=np.uint8)
    for r in range(H):
        for c in range(W):
            s = 0
            for dr in range(-1, 2):
                for dc in range(-1, 2):
                    if dr == 0 and dc == 0: continue
                    nr, nc = r+dr, c+dc
                    if 0 <= nr < H and 0 <= nc < W:
                        s += int(grid_w[nr, nc])
            N_w[r, c] = s
    target_w = np.full((H, W), 2.0, dtype=np.float32)
    weights_w = np.ones((H, W), dtype=np.float32)
    forbidden_w = np.zeros((H, W), dtype=np.int8)
    forbidden_w[:1, :] = 1; forbidden_w[-1:, :] = 1
    forbidden_w[:, :1] = 1; forbidden_w[:, -1:] = 1

    bg, bl, bh = _sa_kernel(
        grid_w.copy(), N_w.copy(), target_w, weights_w, forbidden_w,
        n_iters=np.int64(200), T_start=np.float64(2.0), T_min=np.float64(0.001),
        alpha=np.float64(0.9999), border=np.int32(1),
        H=np.int32(H), W=np.int32(W), seed=np.int32(0))

    assert bg.shape == (H, W), f"Warmup shape wrong: {bg.shape}"
    assert float(bl) >= 0.0, f"Warmup loss negative: {bl}"
    print(f"  SA warmup OK — best_loss={bl:.3f}", flush=True)
    return _sa_kernel


def run_sa(kernel, grid, target, weights, forbidden,
           n_iters, T_start, T_min, alpha, border, seed=42):
    """
    Run one SA chain using the compiled kernel.
    Handles dtype coercion and returns (best_grid int8, best_loss float64, history).
    Enforces corridor constraints after completion.
    """
    H, W = grid.shape
    g = _as_contig(grid, np.int8)
    t = _as_contig(target, np.float32)
    w = _as_contig(weights, np.float32)
    f = _as_contig(forbidden, np.int8)
    N_init = _as_contig(_compute_N(g), np.uint8)

    best_grid, best_loss, history = kernel(
        g, N_init, t, w, f,
        np.int64(n_iters), np.float64(T_start), np.float64(T_min),
        np.float64(alpha), np.int32(border),
        np.int32(H), np.int32(W), np.int32(seed))

    # Enforce corridors post-SA
    best_grid[f == 1] = 0
    return best_grid, float(best_loss), history


def default_config(board_w: int, board_h: int, seed: int = 42) -> dict:
    """
    Return a ready-to-use SA configuration dict for the given board size.
    Keys:
      "kernel" — compiled SA kernel callable (from compile_sa_kernel)
      "sa"     — kwargs dict for run_sa (n_iters, T_start, T_min, alpha, border, seed)
    """
    kernel = compile_sa_kernel()
    n_iters = board_w * board_h * 300
    return {
        "kernel": kernel,
        "sa": {
            "n_iters": n_iters,
            "T_start": 3.5,
            "T_min": 0.001,
            "alpha": 0.999996,
            "border": 3,
            "seed": seed,
        },
    }


def summarize_sa_output(
    grid: np.ndarray,
    target: np.ndarray,
    forbidden: np.ndarray,
) -> dict:
    """
    Return density, local mine-density risk, target saturation overlap,
    and corridor compliance.
    """
    high_target_mask = target >= 5.5
    overlap_count = int(np.sum((grid == 1) & high_target_mask))
    forbidden_mine_count = int(np.sum((grid == 1) & (forbidden == 1)))
    return {
        "mine_density": float(grid.mean()),
        "forbidden_mine_count": forbidden_mine_count,
        "forbidden_violation": bool(forbidden_mine_count > 0),
        "high_target_mine_overlap_count": overlap_count,
        "high_target_mine_overlap_pct": float(overlap_count / max(int(np.sum(high_target_mask)), 1)),
    }
