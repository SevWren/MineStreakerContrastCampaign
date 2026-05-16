"""
research/exp_b_mini_sa_reannealing.py — Experiment B: Mini-SA Reannealing

Hypothesis:
    The standard SA exits at a local minimum where sealed cluster topology forms.
    A short SA (~50K iterations) confined to each sealed cluster's 3-ring boundary
    neighborhood can escape this local minimum. Unlike the greedy mine-removal
    heuristic, the mini-SA can REARRANGE mines (add and remove) within the
    ring — not just delete them — which gives it more degrees of freedom to
    find a valid non-sealed configuration.

Mechanism:
    Uses the existing run_sa() from sa.py without any modification.
    The key insight: run_sa() accepts a `forbidden` mask that constrains
    which cells the SA can flip. By setting forbidden[y,x]=1 for all cells
    OUTSIDE the ring neighborhood of a sealed cluster, the SA is confined
    to only rearranging mines in the local neighborhood.

Per sealed cluster:
    1. Compute bounding box of cluster's external_mines + ring_radius padding
    2. Extract sub-arrays (copy)
    3. Build local_forbidden: 1 everywhere outside ring, preserve original inside
    4. Run run_sa() on full grid but with local_forbidden (confines flips to ring)
    5. Check if n_unknown decreased after the mini-SA

Note: We run on the FULL grid (not a sub-grid) to avoid border-copy bookkeeping
bugs. The forbidden mask does the confinement. This is safe because run_sa()
clips to forbidden after completion.

Parameters swept:
    ring_radius: {2, 3, 5}       — ring padding around cluster external_mines
    mini_sa_iters: {20K, 50K, 100K}  — SA iterations per cluster

Usage:
    python -m research.exp_b_mini_sa_reannealing

Results logged to: research/results/exp_b_mini_sa_reannealing.jsonl
"""

import sys
import time
from itertools import product
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from research.harness.benchmark import ExperimentResult, run_experiment
from research.harness.logger import summarize
from research.harness.scenario import HARD_SCENARIO, SCENARIOS, SEED

EXP_NAME = "exp_b_mini_sa_reannealing"


def _build_ring_forbidden(
    grid: np.ndarray,
    forbidden: np.ndarray,
    cluster: dict,
    ring_radius: int,
) -> np.ndarray:
    """
    Build a modified forbidden mask that permits SA flips ONLY within
    a ring of radius `ring_radius` around the cluster's external mines.

    Strategy:
    - Start from the external_mines positions of the sealed cluster
    - Expand outward by ring_radius cells (Chebyshev / L∞ distance)
    - Allow flips only in this region AND only where not forbidden
    - Everywhere outside the ring: forbidden = 1 (locked)
    """
    H, W = grid.shape
    local_forbidden = np.ones((H, W), dtype=np.int8)  # everything locked by default

    for yx in cluster["external_mines"]:
        my, mx = int(yx[0]), int(yx[1])
        y0 = max(0, my - ring_radius)
        y1 = min(H, my + ring_radius + 1)
        x0 = max(0, mx - ring_radius)
        x1 = min(W, mx + ring_radius + 1)
        local_forbidden[y0:y1, x0:x1] = 0  # unlock the ring region

    # Also unlock the unknown cluster cells themselves
    for yx in cluster["cells"]:
        cy, cx = int(yx[0]), int(yx[1])
        y0 = max(0, cy - ring_radius)
        y1 = min(H, cy + ring_radius + 1)
        x0 = max(0, cx - ring_radius)
        x1 = min(W, cx + ring_radius + 1)
        local_forbidden[y0:y1, x0:x1] = 0

    # Re-apply the original forbidden mask (corridors etc. are always locked)
    local_forbidden = np.maximum(local_forbidden, forbidden)
    return local_forbidden


def run_mini_sa_reannealing(
    grid: np.ndarray,
    target: np.ndarray,
    forbidden: np.ndarray,
    sr_post_sa,
    sa_fn,
    ring_radius: int = 3,
    mini_sa_iters: int = 50_000,
    T_start: float = 2.0,
    T_min: float = 0.01,
    alpha: float = 0.9998,
    max_clusters: int = 50,
    seed: int = SEED,
    verbose: bool = True,
) -> ExperimentResult:
    """
    For each sealed cluster (up to max_clusters), run a short SA confined
    to the cluster's ring neighborhood to break the sealed topology.

    After processing all clusters, runs fast_seal_repair for any remaining
    sealed clusters that the mini-SA could not resolve.
    """
    from core import compute_zone_aware_weights
    from repair import find_sealed_unknown_clusters, run_fast_seal_repair
    from sa import run_sa
    from solver import solve_board

    # Pipeline constants for zone-aware weights
    BP_TRUE, BP_TRANS, HI_BOOST, HI_THR = 8.0, 1.0, 18.0, 3.0
    BORDER = 3

    grid = grid.copy()
    t_start = time.perf_counter()

    # Solve to find current sealed clusters
    sr = solve_board(grid, max_rounds=50, mode="full")
    sealed = find_sealed_unknown_clusters(grid, sr, forbidden)

    n_clusters_processed = 0
    n_clusters_solved = 0
    cluster_log = []
    w_zone = compute_zone_aware_weights(target, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)

    for cluster_idx, cluster in enumerate(sealed[:max_clusters]):
        if not cluster["external_mines"]:
            continue

        n_unk_before = int(sr.n_unknown)
        local_forbidden = _build_ring_forbidden(grid, forbidden, cluster, ring_radius)

        # Count unlocked cells in the ring
        n_unlocked = int(np.sum(local_forbidden == 0))
        if n_unlocked < 3:
            # Too small a ring to do anything useful
            continue

        # Run mini-SA confined to the ring
        grid_after, _, _ = run_sa(
            sa_fn,
            grid,
            target,
            w_zone,
            local_forbidden,
            mini_sa_iters,
            T_start,
            T_min,
            alpha,
            BORDER,
            seed + cluster_idx,
        )
        grid = grid_after

        # Check if the cluster is now accessible
        sr_after = solve_board(grid, max_rounds=50, mode="full")
        n_unk_after = int(sr_after.n_unknown)
        solved_this = n_unk_after < n_unk_before

        n_clusters_processed += 1
        if solved_this:
            n_clusters_solved += 1

        entry = {
            "cluster_idx": cluster_idx,
            "cluster_size": cluster["cluster_size"],
            "n_ext_mines": cluster["external_mine_count"],
            "n_unlocked_cells": n_unlocked,
            "n_unk_before": n_unk_before,
            "n_unk_after": n_unk_after,
            "delta_unk": n_unk_before - n_unk_after,
        }
        cluster_log.append(entry)

        if verbose:
            status = "SOLVED" if solved_this else "no change"
            print(f"  [Exp B] cluster {cluster_idx}: size={cluster['cluster_size']} "
                  f"ring_cells={n_unlocked} Δunk={n_unk_before - n_unk_after} [{status}]")

        # Update sr for next cluster
        sr = sr_after
        sealed = find_sealed_unknown_clusters(grid, sr, forbidden)

    # Fallback: run standard fast_seal for anything still remaining
    remaining_n_unk = int(sr.n_unknown)
    if remaining_n_unk > 0:
        board_area = grid.shape[0] * grid.shape[1]
        budget = max(2.0, min(5.0, board_area / 150_000))
        fast_seal_result = run_fast_seal_repair(
            grid, target, forbidden,
            max_passes=200,
            solve_max_rounds=50,
            time_budget_s=budget,
            verbose=verbose,
        )
        grid = fast_seal_result.grid

    sr_final = solve_board(grid, max_rounds=200, mode="full")

    return ExperimentResult(
        grid=grid,
        n_unknown=int(sr_final.n_unknown),
        solvable=bool(sr_final.solvable),
        mean_abs_error=0.0,
        repair_wall_s=0.0,
        metadata={
            "ring_radius": ring_radius,
            "mini_sa_iters": mini_sa_iters,
            "n_clusters_found": len(sealed) if sealed else 0,
            "n_clusters_processed": n_clusters_processed,
            "n_clusters_solved_by_mini_sa": n_clusters_solved,
            "n_unknown_before_fallback": remaining_n_unk,
            "cluster_log": cluster_log[:5],  # first 5 for diagnostics
        },
    )


def run_parameter_sweep(
    scenarios= None,
    ring_radii= None,
    mini_sa_iters_list= None,
    seed: int = SEED,
) -> None:
    """
    Sweep ring_radius and mini_sa_iters on HARD_SCENARIO first,
    then run the best configuration on all 4 scenarios for regression check.
    """
    target_scenarios = scenarios or [HARD_SCENARIO]
    ring_radii = ring_radii or [2, 3, 5]
    mini_sa_iters_list = mini_sa_iters_list or [20_000, 50_000, 100_000]
    combos = list(product(ring_radii, mini_sa_iters_list))

    print(f"Exp B: {len(combos)} combos × {len(target_scenarios)} scenarios = "
          f"{len(combos) * len(target_scenarios)} runs")
    print("Primary metric: n_unknown_final, n_clusters_solved_by_mini_sa\n")

    best_n_unk = None
    best_params = None

    for ring_r, iters in combos:
        for scenario in target_scenarios:
            params = {"ring_radius": ring_r, "mini_sa_iters": iters}
            print(f"  ring_radius={ring_r}  mini_sa_iters={iters:<7}  "
                  f"scenario={scenario['label']}")
            results = run_experiment(
                run_mini_sa_reannealing,
                params=params,
                scenario=scenario,
                seed=seed,
                n_runs=1,
                log_name=EXP_NAME,
            )
            if results:
                n_fin = results[0].get("n_unknown_final", 9999)
                if scenario["label"] == HARD_SCENARIO["label"]:
                    if best_n_unk is None or n_fin < best_n_unk:
                        best_n_unk = n_fin
                        best_params = params

    print(f"\nBest on {HARD_SCENARIO['label']}: n_unknown_final={best_n_unk}  params={best_params}")

    if best_params and best_n_unk == 0:
        print("\nWinner found! Running regression check on all 4 scenarios...")
        for scenario in SCENARIOS:
            if scenario["label"] == HARD_SCENARIO["label"]:
                continue
            results = run_experiment(
                run_mini_sa_reannealing,
                params={**best_params, "regression_check": True},
                scenario=scenario,
                seed=seed,
                n_runs=1,
                log_name=EXP_NAME,
            )

    print(f"\nResults logged to research/results/{EXP_NAME}.jsonl")
    summarize(EXP_NAME)


if __name__ == "__main__":
    run_parameter_sweep()
