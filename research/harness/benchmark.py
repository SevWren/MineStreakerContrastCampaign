"""
research/harness/benchmark.py — Experiment runner and comparison utility.

Design principle: fair A/B comparison.
  The SA phases are deterministic with a fixed seed, so the post-SA board is
  identical for every experiment on the same scenario. The harness runs the
  pipeline through post-SA once, then hands the state to each experiment_fn
  for ONLY the repair phase. This means timing differences are purely from
  the repair strategy, not from SA variance.

Usage:
    from research.harness.benchmark import run_experiment, compare_experiments
    from research.harness.scenario import HARD_SCENARIO

    results = run_experiment(my_repair_fn, params={"ring_radius": 3},
                              scenario=HARD_SCENARIO)

    compare_experiments(["exp_b_mini_sa_reannealing",
                         "exp_d_smarter_fast_seal"])

CLI:
    python -m research.harness.benchmark --compare exp_b exp_d exp_c
    python -m research.harness.benchmark --baseline   (records baseline run)
"""

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

# Add project root to path so we can import from root modules
_ROOT = Path(__file__).parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from research.harness.logger import load_results, log_result, summarize
from research.harness.scenario import SCENARIOS, HARD_SCENARIO, SEED


@dataclass
class ExperimentResult:
    """Returned by every experiment_fn."""
    grid: np.ndarray         # final grid after experiment repair
    n_unknown: int           # final n_unknown (0 = success)
    solvable: bool
    mean_abs_error: float
    repair_wall_s: float     # wall time for THIS experiment's repair logic only
    metadata: dict           # experiment-specific diagnostics (passes, mines_removed, …)


def _build_post_sa_state(scenario: dict, seed: int) -> dict:
    """
    Run the standard pipeline through post-SA and return the state dict.
    Results are NOT cached — each call re-runs SA (deterministic with same seed).

    Returns dict with keys:
        grid, target, target_eval, forbidden, w_zone, sa_fn, sr_post_sa,
        n_unknown_post_sa, bw, bh, phase_timers
    """
    import argparse as _ap
    from PIL import Image as PILImage

    from sa import compile_sa_kernel
    from solver import ensure_solver_warmed, solve_board
    from core import (
        apply_piecewise_T_compression,
        assert_board_valid,
        compute_N,
        compute_sealing_prevention_weights,
        compute_zone_aware_weights,
        load_image_smart,
    )
    from corridors import build_adaptive_corridors
    from board_sizing import derive_board_from_width
    from sa import run_sa
    from sa_parallel import run_sa_parallel_best

    # Pipeline constants (from run_iter9.py)
    DENSITY = 0.22
    BORDER = 3
    COARSE_ITERS = 2_000_000
    T_COARSE, ALPHA_COARSE = 10.0, 0.99998
    FINE_ITERS = 8_000_000
    T_FINE, ALPHA_FINE = 3.5, 0.999996
    REFINE1_ITERS, T_REFINE1, ALPHA_REFINE1 = 2_000_000, 2.0, 0.999997
    REFINE2_ITERS, T_REFINE2, ALPHA_REFINE2 = 2_000_000, 1.7, 0.999997
    REFINE3_ITERS, T_REFINE3, ALPHA_REFINE3 = 4_000_000, 1.4, 0.999998
    T_MIN = 0.001
    BP_TRUE, BP_TRANS, HI_BOOST, HI_THR = 8.0, 1.0, 18.0, 3.0
    UF_FACTOR = 1.8
    SEAL_THR, SEAL_STR = 0.6, 20.0
    PW_KNEE, PW_T_MAX = 4.0, 6.0

    sa_fn = compile_sa_kernel()
    ensure_solver_warmed()

    image_path = str(_ROOT / scenario["image"])
    board_w = scenario["board_w"]
    sizing = derive_board_from_width(image_path, board_w)
    bw, bh = int(sizing["board_width"]), int(sizing["board_height"])

    target_eval = load_image_smart(image_path, bw, bh, invert=True)
    target = apply_piecewise_T_compression(target_eval, PW_KNEE, PW_T_MAX)
    w_zone = compute_zone_aware_weights(target, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    forbidden, _, _, _ = build_adaptive_corridors(target, border=BORDER)

    rng = np.random.default_rng(seed)

    # Coarse SA
    cw, ch = bw // 2, bh // 2
    _teval_pil = PILImage.fromarray(
        (target_eval / 8.0 * 255.0).clip(0, 255).astype(np.uint8)
    ).resize((cw, ch), PILImage.BILINEAR)
    _target_c_raw = np.array(_teval_pil, dtype=np.float32) / 255.0 * 8.0
    target_c = apply_piecewise_T_compression(
        np.ascontiguousarray(_target_c_raw, dtype=np.float32), PW_KNEE, PW_T_MAX
    )
    weight_c = compute_zone_aware_weights(target_c, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    forbidden_c, _, _, _ = build_adaptive_corridors(target_c, border=BORDER)
    grid_c = np.zeros((ch, cw), dtype=np.int8)
    available_c = np.argwhere(forbidden_c == 0)
    picks = rng.choice(len(available_c),
                       size=min(int(DENSITY * cw * ch), len(available_c)),
                       replace=False)
    grid_c[available_c[picks, 0], available_c[picks, 1]] = 1
    grid_c, _, _ = run_sa(sa_fn, grid_c, target_c, weight_c, forbidden_c,
                          COARSE_ITERS, T_COARSE, T_MIN, ALPHA_COARSE, BORDER, seed)

    grid = (np.array(PILImage.fromarray(grid_c.astype(np.uint8) * 255)
                     .resize((bw, bh), PILImage.NEAREST),
                     dtype=np.uint8) > 127).astype(np.int8)
    grid[forbidden == 1] = 0

    # Fine SA
    grid, _, _ = run_sa_parallel_best(sa_fn, grid, target, w_zone, forbidden,
                                       FINE_ITERS, T_FINE, T_MIN, ALPHA_FINE,
                                       BORDER, seed + 1)
    grid[forbidden == 1] = 0

    # Refine SA (3 passes)
    from scipy.ndimage import convolve as _convolve
    for pidx, (iters, temp, alpha) in enumerate([
        (REFINE1_ITERS, T_REFINE1, ALPHA_REFINE1),
        (REFINE2_ITERS, T_REFINE2, ALPHA_REFINE2),
        (REFINE3_ITERS, T_REFINE3, ALPHA_REFINE3),
    ]):
        n_cur = compute_N(grid)
        underfill = np.clip(target - n_cur.astype(np.float32), 0.0, 8.0) / 8.0
        weight_ref = (w_zone * (1.0 + UF_FACTOR * underfill)).astype(np.float32)
        if pidx < 2:
            weight_ref = compute_sealing_prevention_weights(
                weight_ref, grid, target, HI_THR, SEAL_THR, SEAL_STR
            )
        grid, _, _ = run_sa_parallel_best(sa_fn, grid, target, weight_ref, forbidden,
                                           iters, temp, T_MIN, alpha,
                                           BORDER, seed + 2 + pidx)
        grid[forbidden == 1] = 0

    assert_board_valid(grid, forbidden, "post-SA")
    sr_post_sa = solve_board(grid, max_rounds=15, mode="full")

    return {
        "grid": grid,
        "target": target,
        "target_eval": target_eval,
        "forbidden": forbidden,
        "w_zone": w_zone,
        "sa_fn": sa_fn,
        "sr_post_sa": sr_post_sa,
        "n_unknown_post_sa": int(sr_post_sa.n_unknown),
        "bw": bw,
        "bh": bh,
    }


def run_experiment(
    experiment_fn: Callable,
    params: dict,
    scenario: dict,
    seed: int = SEED,
    n_runs: int = 1,
    log_name= None,
) -> list[dict]:
    """
    Run experiment_fn on a scenario and log results.

    experiment_fn signature:
        (grid, target, forbidden, sr_post_sa, sa_fn, **params) -> ExperimentResult

    Returns list of result dicts (length n_runs).
    """
    from solver import solve_board

    records = []
    for run_idx in range(n_runs):
        run_seed = seed + run_idx
        print(f"\n[{scenario['label']}] run {run_idx + 1}/{n_runs} seed={run_seed}")

        state = _build_post_sa_state(scenario, run_seed)
        print(f"  post-SA n_unknown = {state['n_unknown_post_sa']}")

        t0 = time.perf_counter()
        exp_result = experiment_fn(
            grid=state["grid"].copy(),
            target=state["target"],
            forbidden=state["forbidden"],
            sr_post_sa=state["sr_post_sa"],
            sa_fn=state["sa_fn"],
            **params,
        )
        repair_wall_s = time.perf_counter() - t0

        # Final authoritative solve for accurate metrics
        from core import load_image_smart, apply_piecewise_T_compression
        PW_KNEE, PW_T_MAX = 4.0, 6.0
        sr_final = solve_board(exp_result.grid, max_rounds=200, mode="full")
        n_unknown_final = int(sr_final.n_unknown)

        # Compute MAE vs target_eval
        from core import compute_N
        N_final = compute_N(exp_result.grid).astype(np.float32)
        mae = float(np.mean(np.abs(N_final - state["target_eval"])))

        record = {
            "n_unknown_post_sa": state["n_unknown_post_sa"],
            "n_unknown_final": n_unknown_final,
            "solvable": bool(sr_final.solvable),
            "mean_abs_error": mae,
            "repair_wall_s": repair_wall_s,
            "metadata": exp_result.metadata,
        }
        records.append(record)

        if log_name:
            log_result(log_name, scenario["label"], params, record)

        print(f"  n_unknown_final={n_unknown_final}  MAE={mae:.4f}  repair={repair_wall_s:.2f}s")
        if n_unknown_final == 0:
            print(f"  *** SOLVED ***")

    return records


def compare_experiments(names: list[str]) -> None:
    """Print side-by-side comparison of logged experiment results."""
    for name in names:
        summarize(name)


def _cli_main() -> None:
    parser = argparse.ArgumentParser(description="Research experiment harness")
    parser.add_argument("--compare", nargs="+", metavar="EXP",
                        help="Print summary tables for these experiment names")
    parser.add_argument("--baseline", action="store_true",
                        help="Record a baseline run (standard pipeline) on all 4 scenarios")
    args = parser.parse_args()

    if args.compare:
        compare_experiments(args.compare)
    elif args.baseline:
        print("Recording baseline (standard fast_seal pipeline) on all 4 scenarios...")
        from repair import run_fast_seal_repair

        def baseline_fn(grid, target, forbidden, sr_post_sa, sa_fn, **_):
            import time
            t0 = time.perf_counter()
            result = run_fast_seal_repair(
                grid, target, forbidden,
                max_passes=500, solve_max_rounds=50,
                time_budget_s=5.0, verbose=False,
            )
            from solver import solve_board
            sr = solve_board(result.grid, max_rounds=200, mode="full")
            wall = time.perf_counter() - t0
            return ExperimentResult(
                grid=result.grid,
                n_unknown=int(sr.n_unknown),
                solvable=bool(sr.solvable),
                mean_abs_error=0.0,  # computed in run_experiment
                repair_wall_s=wall,
                metadata={"passes": result.n_passes, "mines_removed": result.n_fixed},
            )

        for scenario in SCENARIOS:
            run_experiment(baseline_fn, params={}, scenario=scenario,
                           n_runs=1, log_name="baseline")
    else:
        parser.print_help()


if __name__ == "__main__":
    _cli_main()
