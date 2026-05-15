"""
sa_parallel.py — Multi-start parallel SA wrapper.

Runs N independent SA chains in parallel via ProcessPoolExecutor.
Each chain uses (seed + chain_idx) for deterministic reproducibility.
Best result (lowest best_loss) is returned.

_parallel_worker is module-level (picklable under Python 3.9).
Each worker re-imports sa.py in the child process to load the
Numba-cached kernel (~100ms startup per worker, paid once).

Falls back to run_sa() transparently when cpu_count <= 1, so this
module is safe to import and use on any machine without conditionals
at the call site.
"""

import math
import os

import numpy as np
from concurrent.futures import ProcessPoolExecutor, as_completed

try:
    from .sa import _as_contig, run_sa
    from .core import compute_N as _compute_N
except ImportError:
    from sa import _as_contig, run_sa
    from core import compute_N as _compute_N


def _parallel_worker(args):
    """
    Picklable module-level worker. Runs one SA chain in a child process.
    Re-imports sa.py to load the Numba-cached _sa_kernel.
    """
    import numpy as _np
    try:
        from sa import _sa_kernel
    except ImportError:
        from .sa import _sa_kernel

    (grid_b, shape, N_b, target_b, weights_b, forbidden_b,
     n_iters, T_start, T_min, alpha_chain, border, H, W, seed) = args

    grid      = _np.frombuffer(grid_b,      dtype=_np.int8   ).reshape(shape).copy()
    N_field   = _np.frombuffer(N_b,         dtype=_np.uint8  ).reshape(shape).copy()
    target    = _np.frombuffer(target_b,    dtype=_np.float32).reshape(shape)
    weights   = _np.frombuffer(weights_b,   dtype=_np.float32).reshape(shape)
    forbidden = _np.frombuffer(forbidden_b, dtype=_np.int8   ).reshape(shape)

    best_grid, best_loss, history = _sa_kernel(
        grid, N_field, target, weights, forbidden,
        _np.int64(n_iters), _np.float64(T_start), _np.float64(T_min),
        _np.float64(alpha_chain), _np.int32(border),
        _np.int32(H), _np.int32(W), _np.int32(seed))

    best_grid[forbidden == 1] = 0
    return best_grid.tobytes(), float(best_loss), history


def run_sa_parallel_best(kernel, grid, target, weights, forbidden,
                          n_iters, T_start, T_min, alpha, border, seed,
                          n_chains=None):
    """
    Run N SA chains in parallel; return the best (lowest best_loss) result.

    n_chains: number of parallel chains. Defaults to min(os.cpu_count(), 8).
    Falls back to run_sa() when cpu_count <= 1 (zero overhead on single-core).

    Each chain runs n_iters // n_chains iterations. alpha is recomputed so
    each chain's temperature schedule covers T_start -> T_min in the reduced
    iteration count (same shape as the original schedule, compressed in time):
        alpha_chain = exp(log(T_min / T_start) / iters_per_chain)

    Seed contract: chain i uses (seed + i). Results are fully deterministic
    given the same inputs, seed, and n_chains.
    """
    cpu = os.cpu_count() or 1
    n = n_chains if n_chains is not None else min(cpu, 8)

    if n <= 1 or cpu <= 1:
        return run_sa(kernel, grid, target, weights, forbidden,
                      n_iters, T_start, T_min, alpha, border, seed)

    H, W = grid.shape
    iters_per_chain = max(n_iters // n, 100_000)

    # Recompute alpha to preserve T_start -> T_min range in compressed iterations:
    #   Original: T_start * alpha^n_iters ~= T_min
    #   Per chain: T_start * alpha_chain^iters_per_chain = T_min
    alpha_chain = math.exp(math.log(T_min / T_start) / iters_per_chain)

    g = _as_contig(grid,      np.int8)
    t = _as_contig(target,    np.float32)
    w = _as_contig(weights,   np.float32)
    f = _as_contig(forbidden, np.int8)
    N_init = _as_contig(_compute_N(g), np.uint8)

    args_list = [
        (g.tobytes(), g.shape, N_init.tobytes(), t.tobytes(), w.tobytes(), f.tobytes(),
         iters_per_chain, T_start, T_min, alpha_chain, border, H, W, seed + i)
        for i in range(n)
    ]

    results = []
    with ProcessPoolExecutor(max_workers=n) as pool:
        futures = [pool.submit(_parallel_worker, a) for a in args_list]
        for fut in as_completed(futures):
            grid_b, loss, history = fut.result()
            bg = np.frombuffer(grid_b, dtype=np.int8).reshape(H, W).copy()
            results.append((loss, bg, history))

    results.sort(key=lambda r: r[0])
    best_loss, best_grid_final, best_history = results[0]
    best_grid_final[f == 1] = 0
    return best_grid_final, best_loss, best_history
