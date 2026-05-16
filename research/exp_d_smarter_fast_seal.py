"""
research/exp_d_smarter_fast_seal.py — Experiment D: Constraint-Score Mine Selector

Hypothesis:
    The current fast_seal_repair selector removes the external mine with the
    lowest target value (greedy visual cost). This ignores solver accessibility
    entirely. A selector that scores candidates by how many constraint equations
    removing the mine would "unlock" can converge in fewer passes without doing
    a full trial solve.

Constraint-score estimator (O(1) per candidate, no solver call):
    For each external mine candidate (my, mx) adjacent to a sealed cluster:

        score(my, mx) = Σ over 8-neighbors (ny, nx) of (my, mx):
            unknown(ny, nx) / max(N_field[ny, nx], 1)

    Cells that are unknown AND have low N values are closest to becoming
    deterministically solvable: removing the mine at (my,mx) reduces their
    remaining mine count most proportionally, making a direct-inference deduction
    more likely on the next solve pass.

Three selector strategies are compared:
    "lowest_T"        — current baseline (remove lowest target-value mine)
    "constraint_score"— new estimator (maximize constraint unlocking)
    "combined"        — 0.6 * constraint_score + 0.4 * (1 / max(T, 0.01))

Usage:
    python -m research.exp_d_smarter_fast_seal

Results logged to: research/results/exp_d_smarter_fast_seal.jsonl
"""

import sys
import time
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from research.harness.benchmark import ExperimentResult, run_experiment
from research.harness.logger import summarize
from research.harness.scenario import HARD_SCENARIO, SCENARIOS, SEED

EXP_NAME = "exp_d_smarter_fast_seal"


def _constraint_score(
    my: int, mx: int,
    state: np.ndarray,
    N_field: np.ndarray,
    H: int, W: int,
    UNKNOWN: int = 0,
) -> float:
    """
    Estimate how many constraint equations removing mine (my, mx) would unlock.
    Higher score → removing this mine is more likely to unblock deterministic solves.
    """
    score = 0.0
    for dy in range(-1, 2):
        ny = my + dy
        if ny < 0 or ny >= H:
            continue
        for dx in range(-1, 2):
            nx = mx + dx
            if ny == my and nx == mx:
                continue
            if nx < 0 or nx >= W:
                continue
            if state[ny, nx] == UNKNOWN:
                n_val = max(int(N_field[ny, nx]), 1)
                score += 1.0 / n_val
    return score


def smarter_mine_selector(
    cluster: dict,
    target: np.ndarray,
    state: np.ndarray,
    N_field: np.ndarray,
    strategy: str,
) -> tuple[int, int]:
    """
    Select the best external mine to remove from a sealed cluster.

    Args:
        cluster:   dict from find_sealed_unknown_clusters()
        target:    target image array [H, W] float32
        state:     solver state array [H, W] int8 (UNKNOWN=0, SAFE=1, MINE=2)
        N_field:   neighbor mine count [H, W] uint8
        strategy:  "lowest_T" | "constraint_score" | "combined"

    Returns:
        (y, x) of selected mine
    """
    from solver import UNKNOWN as _UNKNOWN
    H, W = target.shape
    ext_mines = [(int(yx[0]), int(yx[1])) for yx in cluster["external_mines"]]
    if not ext_mines:
        raise ValueError("Cluster has no external mines")

    if strategy == "lowest_T":
        return min(ext_mines, key=lambda yx: float(target[yx[0], yx[1]]))

    if strategy == "constraint_score":
        return max(
            ext_mines,
            key=lambda yx: _constraint_score(
                yx[0], yx[1], state, N_field, H, W, _UNKNOWN
            ),
        )

    if strategy == "combined":
        def combined_score(yx):
            cs = _constraint_score(yx[0], yx[1], state, N_field, H, W, _UNKNOWN)
            t_inv = 1.0 / max(float(target[yx[0], yx[1]]), 0.01)
            return 0.6 * cs + 0.4 * t_inv
        return max(ext_mines, key=combined_score)

    raise ValueError(f"Unknown strategy: {strategy!r}")


def run_smarter_fast_seal(
    grid: np.ndarray,
    target: np.ndarray,
    forbidden: np.ndarray,
    sr_post_sa,
    sa_fn,
    strategy: str = "constraint_score",
    max_passes: int = 500,
    solve_max_rounds: int = 50,
    time_budget_s: float = 5.0,
    verbose: bool = True,
) -> ExperimentResult:
    """
    Replacement for run_fast_seal_repair using a pluggable mine selector.

    Args:
        strategy: "lowest_T" | "constraint_score" | "combined"
    """
    from core import compute_N
    from repair import find_sealed_unknown_clusters, FastSealRepairResult
    from solver import solve_board, UNKNOWN

    grid = grid.copy()
    n_fixed = 0
    n_passes = 0
    pass_log = []
    t_start = time.perf_counter()

    for pass_idx in range(max_passes):
        if (time.perf_counter() - t_start) >= time_budget_s:
            if verbose:
                print(f"  [Exp D] time budget {time_budget_s:.1f}s at pass {pass_idx}")
            break

        sr = solve_board(grid, max_rounds=solve_max_rounds, mode="full")
        n_passes += 1

        if int(sr.n_unknown) == 0:
            if verbose:
                print(f"  [Exp D] pass {pass_idx}: n_unknown=0 — done")
            break

        sealed = find_sealed_unknown_clusters(grid, sr, forbidden)
        if not sealed:
            if verbose:
                print(f"  [Exp D] pass {pass_idx}: no sealed clusters — done")
            break

        N_field = compute_N(grid)
        n_this_pass = 0
        for cluster in sealed:
            if not cluster["external_mines"]:
                continue
            best_mine = smarter_mine_selector(
                cluster, target, sr.state, N_field, strategy
            )
            grid[best_mine[0], best_mine[1]] = 0
            n_this_pass += 1
            n_fixed += 1

        grid[forbidden == 1] = 0

        if verbose:
            print(f"  [Exp D] pass {pass_idx}: removed {n_this_pass} mines "
                  f"(total={n_fixed}), n_unknown={sr.n_unknown}")

        pass_log.append({"pass": pass_idx, "removed": n_this_pass, "n_unknown": int(sr.n_unknown)})

        if n_this_pass == 0:
            break

    sr_final = solve_board(grid, max_rounds=200, mode="full")
    n_passes += 1

    from core import compute_N as _cN
    from research.harness.scenario import SEED
    N_f = _cN(grid).astype(np.float32)

    return ExperimentResult(
        grid=grid,
        n_unknown=int(sr_final.n_unknown),
        solvable=bool(sr_final.solvable),
        mean_abs_error=0.0,  # computed externally in run_experiment
        repair_wall_s=0.0,   # computed externally in run_experiment
        metadata={
            "strategy": strategy,
            "passes": n_passes,
            "mines_removed": n_fixed,
            "pass_log": pass_log[:10],  # first 10 passes for diagnostics
        },
    )


def run_all_strategies(
    scenarios= None,
    seed: int = SEED,
) -> None:
    """
    Compare all three selector strategies on each scenario.
    """
    target_scenarios = scenarios or [HARD_SCENARIO]
    strategies = ["lowest_T", "constraint_score", "combined"]

    print(f"Exp D: {len(strategies)} strategies × {len(target_scenarios)} scenarios")
    print("Primary metric: passes-to-solve and n_unknown_final\n")

    for strategy in strategies:
        for scenario in target_scenarios:
            print(f"  strategy={strategy:<18} scenario={scenario['label']}")
            results = run_experiment(
                run_smarter_fast_seal,
                params={"strategy": strategy},
                scenario=scenario,
                seed=seed,
                n_runs=1,
                log_name=EXP_NAME,
            )

    # Also run regression check on all 4 scenarios for best strategy
    print("\n--- Regression check (all 4 scenarios) with best non-baseline strategies ---")
    for strategy in ["constraint_score", "combined"]:
        for scenario in SCENARIOS:
            if any(r.get("scenario_label") == scenario["label"]
                   and r.get("params", {}).get("strategy") == strategy
                   for r in []):
                continue
            results = run_experiment(
                run_smarter_fast_seal,
                params={"strategy": strategy, "regression_check": True},
                scenario=scenario,
                seed=seed,
                n_runs=1,
                log_name=EXP_NAME,
            )

    print(f"\nResults logged to research/results/{EXP_NAME}.jsonl")
    summarize(EXP_NAME)


if __name__ == "__main__":
    run_all_strategies()
