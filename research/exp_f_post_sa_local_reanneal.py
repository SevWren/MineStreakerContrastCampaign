"""
research/exp_f_post_sa_local_reanneal.py — Experiment F: Post-SA Local Reannealing
                                            with Amplified Sealing-Prevention Weights

Hypothesis:
    Experiment B runs mini-SA with the standard zone-aware weights, which optimize
    for visual fidelity (match target image). This experiment runs mini-SA with
    sealing_strength amplified by 10-20× — the optimizer is explicitly told to
    avoid sealed topologies in that ring, not just minimize visual error.

    The key difference from Exp B:
      Exp B uses w_zone (visual fidelity)
      Exp F uses compute_sealing_prevention_weights(w_zone, ..., sealing_strength=200)
              so the loss heavily penalizes configurations that keep the
              sealed structure intact

Mechanism:
    Same sub-region confinement as Exp B (local_forbidden mask).
    Weight field is built with:
        w = compute_zone_aware_weights(target, ...)
        w = compute_sealing_prevention_weights(w, grid, target,
                density_threshold=SEAL_THR,
                sealing_strength=seal_str_amplifier)
    This makes the SA loss much higher for any mine placement that would
    maintain a high local mine density in non-line regions — directly
    penalizing the root cause of sealed cluster formation.

Parameters swept:
    ring_radius:         {3, 5}
    mini_sa_iters:       {30K, 80K}
    seal_str_amplifier:  {50.0, 100.0, 200.0}

Usage:
    python -m research.exp_f_post_sa_local_reanneal

Results logged to: research/results/exp_f_post_sa_local_reanneal.jsonl
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
from research.exp_b_mini_sa_reannealing import _build_ring_forbidden

EXP_NAME = "exp_f_post_sa_local_reanneal"


def run_post_sa_local_reanneal(
    grid: np.ndarray,
    target: np.ndarray,
    forbidden: np.ndarray,
    sr_post_sa,
    sa_fn,
    ring_radius: int = 4,
    mini_sa_iters: int = 50_000,
    T_start: float = 2.0,
    T_min: float = 0.01,
    alpha: float = 0.9998,
    seal_str_amplifier: float = 100.0,
    max_clusters: int = 50,
    seed: int = SEED,
    verbose: bool = True,
) -> ExperimentResult:
    """
    For each sealed cluster, run mini-SA in its ring with amplified
    sealing-prevention weights that strongly penalize sealed mine density.
    """
    from core import (
        compute_zone_aware_weights,
        compute_sealing_prevention_weights,
        compute_N,
    )
    from repair import find_sealed_unknown_clusters, run_fast_seal_repair
    from sa import run_sa
    from solver import solve_board

    # Pipeline constants
    BP_TRUE, BP_TRANS, HI_BOOST, HI_THR = 8.0, 1.0, 18.0, 3.0
    SEAL_THR = 0.6
    BORDER = 3

    grid = grid.copy()
    t_start = time.perf_counter()

    sr = solve_board(grid, max_rounds=50, mode="full")
    sealed = find_sealed_unknown_clusters(grid, sr, forbidden)

    n_clusters_processed = 0
    n_clusters_solved = 0
    cluster_log = []

    # Precompute base zone weights (reused across clusters)
    w_zone = compute_zone_aware_weights(target, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)

    for cluster_idx, cluster in enumerate(sealed[:max_clusters]):
        if not cluster["external_mines"]:
            continue

        n_unk_before = int(sr.n_unknown)
        local_forbidden = _build_ring_forbidden(grid, forbidden, cluster, ring_radius)

        n_unlocked = int(np.sum(local_forbidden == 0))
        if n_unlocked < 3:
            continue

        # Build amplified sealing-prevention weights for this cluster's region
        w_amplified = compute_sealing_prevention_weights(
            w_zone,
            grid,
            target,
            hi_threshold=HI_THR,
            density_threshold=SEAL_THR,
            sealing_strength=seal_str_amplifier,
        )

        # Run mini-SA with amplified weights, confined to ring
        grid_after, _, _ = run_sa(
            sa_fn,
            grid,
            target,
            w_amplified,
            local_forbidden,
            mini_sa_iters,
            T_start,
            T_min,
            alpha,
            BORDER,
            seed + cluster_idx,
        )
        grid = grid_after

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
            print(f"  [Exp F] cluster {cluster_idx}: size={cluster['cluster_size']} "
                  f"ring_cells={n_unlocked} Δunk={n_unk_before - n_unk_after} [{status}]")

        sr = sr_after
        sealed = find_sealed_unknown_clusters(grid, sr, forbidden)

    # Fallback fast_seal for any remaining sealed clusters
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
            "seal_str_amplifier": seal_str_amplifier,
            "n_clusters_processed": n_clusters_processed,
            "n_clusters_solved_by_mini_sa": n_clusters_solved,
            "n_unknown_before_fallback": remaining_n_unk,
            "cluster_log": cluster_log[:5],
        },
    )


def run_parameter_sweep(
    scenarios: list[dict] | None = None,
    ring_radii: list[int] | None = None,
    mini_sa_iters_list: list[int] | None = None,
    seal_str_amplifiers: list[float] | None = None,
    seed: int = SEED,
) -> None:
    """
    Sweep ring_radius × mini_sa_iters × seal_str_amplifier on HARD_SCENARIO.
    Run best config on all 4 scenarios for regression check.
    """
    target_scenarios = scenarios or [HARD_SCENARIO]
    ring_radii = ring_radii or [3, 5]
    mini_sa_iters_list = mini_sa_iters_list or [30_000, 80_000]
    seal_str_amplifiers = seal_str_amplifiers or [50.0, 100.0, 200.0]

    combos = list(product(ring_radii, mini_sa_iters_list, seal_str_amplifiers))
    print(f"Exp F: {len(combos)} combos × {len(target_scenarios)} scenarios = "
          f"{len(combos) * len(target_scenarios)} runs")
    print("Primary metrics: n_unknown_final, n_clusters_solved_by_mini_sa\n")

    best_n_unk = None
    best_params = None

    for ring_r, iters, amp in combos:
        for scenario in target_scenarios:
            params = {
                "ring_radius": ring_r,
                "mini_sa_iters": iters,
                "seal_str_amplifier": amp,
            }
            print(f"  ring_r={ring_r} iters={iters:<6} amp={amp:<6}  "
                  f"scenario={scenario['label']}")
            results = run_experiment(
                run_post_sa_local_reanneal,
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
            run_experiment(
                run_post_sa_local_reanneal,
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
