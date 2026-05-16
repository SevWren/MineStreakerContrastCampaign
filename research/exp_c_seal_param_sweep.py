"""
research/exp_c_seal_param_sweep.py — Experiment C: SEAL_STR / SEAL_THR Grid Search

Hypothesis:
    SEAL_STR=20.0 and SEAL_THR=0.6 were not tuned against research/600. A higher
    sealing_strength during the refine SA phases may prevent sealed cluster formation
    before it needs repair, so fast_seal finishes in budget with n_unknown=0.

Mechanism:
    compute_sealing_prevention_weights() multiplies the SA loss weights for cells
    in dense non-line regions where local mine density exceeds density_threshold.
    Higher sealing_strength → stronger penalty for creating sealed topology → SA
    avoids configurations that would produce sealed clusters.

Primary metric: n_unknown_post_sa (before any repair).
Secondary: n_unknown_final (after fast_seal), mean_abs_error (visual quality guard).

Usage:
    python -m research.exp_c_seal_param_sweep

Results logged to: research/results/exp_c_seal_param_sweep.jsonl
"""

import sys
import time
from itertools import product
from pathlib import Path

import numpy as np

_ROOT = Path(__file__).parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from research.harness.logger import log_result, summarize
from research.harness.scenario import HARD_SCENARIO, SCENARIOS, SEED

EXP_NAME = "exp_c_seal_param_sweep"

# Grid search space
SEAL_STR_VALUES = [10.0, 20.0, 30.0, 50.0, 80.0, 120.0]
SEAL_THR_VALUES = [0.4, 0.5, 0.6, 0.7, 0.8]


def run_pipeline_with_params(
    seal_str: float,
    seal_thr: float,
    scenario: dict,
    seed: int = SEED,
) -> dict:
    """
    Run the full pipeline (SA + fast_seal) with custom SEAL_STR / SEAL_THR.
    Returns result dict suitable for logging.
    """
    from PIL import Image as PILImage

    from sa import compile_sa_kernel, run_sa
    from sa_parallel import run_sa_parallel_best
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
    from repair import run_fast_seal_repair

    # Pipeline constants (unchanged from run_iter9.py)
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
    PW_KNEE, PW_T_MAX = 4.0, 6.0

    sa_fn = compile_sa_kernel()
    ensure_solver_warmed()

    image_path = str(_ROOT / scenario["image"])
    sizing = derive_board_from_width(image_path, scenario["board_w"])
    bw, bh = int(sizing["board_w"]), int(sizing["board_h"])

    target_eval = load_image_smart(image_path, bw, bh, invert=True)
    target = apply_piecewise_T_compression(target_eval, PW_KNEE, PW_T_MAX)
    w_zone = compute_zone_aware_weights(target, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    forbidden, _, _, _ = build_adaptive_corridors(target, border=BORDER)

    rng = np.random.default_rng(seed)

    # Coarse SA (unchanged)
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

    # Fine SA (unchanged)
    grid, _, _ = run_sa_parallel_best(sa_fn, grid, target, w_zone, forbidden,
                                       FINE_ITERS, T_FINE, T_MIN, ALPHA_FINE,
                                       BORDER, seed + 1)
    grid[forbidden == 1] = 0

    # Refine SA — using experiment's seal_str and seal_thr
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
                weight_ref, grid, target,
                hi_threshold=HI_THR,
                density_threshold=seal_thr,   # ← experiment parameter
                sealing_strength=seal_str,    # ← experiment parameter
            )
        grid, _, _ = run_sa_parallel_best(sa_fn, grid, target, weight_ref, forbidden,
                                           iters, temp, T_MIN, alpha,
                                           BORDER, seed + 2 + pidx)
        grid[forbidden == 1] = 0

    assert_board_valid(grid, forbidden, "post-SA")
    sr_post_sa = solve_board(grid, max_rounds=15, mode="full")
    n_unknown_post_sa = int(sr_post_sa.n_unknown)

    # fast_seal repair
    t_repair = time.perf_counter()
    board_area = bw * bh
    fast_seal_budget = max(3.0, min(5.0, board_area / 150_000))
    fast_seal_result = run_fast_seal_repair(
        grid, target, forbidden,
        max_passes=500,
        solve_max_rounds=50,
        time_budget_s=fast_seal_budget,
        verbose=False,
    )
    repair_wall_s = time.perf_counter() - t_repair

    sr_final = solve_board(fast_seal_result.grid, max_rounds=200, mode="full")
    N_final = compute_N(fast_seal_result.grid).astype(np.float32)
    mae = float(np.mean(np.abs(N_final - target_eval)))

    return {
        "n_unknown_post_sa": n_unknown_post_sa,
        "n_unknown_final": int(sr_final.n_unknown),
        "solvable": bool(sr_final.solvable),
        "mean_abs_error": mae,
        "repair_wall_s": repair_wall_s,
        "fast_seal_passes": fast_seal_result.n_passes,
        "fast_seal_mines_removed": fast_seal_result.n_fixed,
    }


def run_sweep(
    scenarios: list[dict] | None = None,
    seal_str_values: list[float] = SEAL_STR_VALUES,
    seal_thr_values: list[float] = SEAL_THR_VALUES,
    seed: int = SEED,
) -> None:
    """
    Run the full SEAL_STR × SEAL_THR grid search.

    Strategy: run the full grid on HARD_SCENARIO (research/600) first.
    For the winning configuration, run all 4 scenarios to verify no regression.
    """
    target_scenarios = scenarios or [HARD_SCENARIO]
    combos = list(product(seal_str_values, seal_thr_values))
    total = len(combos) * len(target_scenarios)

    print(f"Exp C: {len(combos)} SEAL_STR×SEAL_THR combos × {len(target_scenarios)} scenarios = {total} runs")
    print("Primary metric: n_unknown_post_sa (lower → better sealing prevention)\n")

    best_n_unk = None
    best_params = None

    for i, (seal_str, seal_thr) in enumerate(combos):
        for scenario in target_scenarios:
            params = {"seal_str": seal_str, "seal_thr": seal_thr}
            print(f"[{i+1}/{len(combos)}] SEAL_STR={seal_str:<6} SEAL_THR={seal_thr}  "
                  f"scenario={scenario['label']}", end="  ", flush=True)

            try:
                result = run_pipeline_with_params(seal_str, seal_thr, scenario, seed)
                log_result(EXP_NAME, scenario["label"], params, result)
                n_post = result["n_unknown_post_sa"]
                n_fin = result["n_unknown_final"]
                mae = result["mean_abs_error"]
                print(f"n_unk_post_sa={n_post:4d}  n_unk_final={n_fin:4d}  MAE={mae:.4f}")

                if scenario["label"] == HARD_SCENARIO["label"]:
                    if best_n_unk is None or n_post < best_n_unk:
                        best_n_unk = n_post
                        best_params = params
            except Exception as exc:
                print(f"ERROR: {exc}")
                log_result(EXP_NAME, scenario["label"], params, {"error": str(exc)})

    print(f"\nBest on {HARD_SCENARIO['label']}: n_unknown_post_sa={best_n_unk}  params={best_params}")

    if best_params and best_n_unk is not None and best_n_unk < 100:
        print("\nWinner found — running all 4 scenarios for regression check...")
        for scenario in SCENARIOS:
            if scenario["label"] == HARD_SCENARIO["label"]:
                continue  # already run
            print(f"  {scenario['label']}...", end=" ", flush=True)
            try:
                result = run_pipeline_with_params(
                    best_params["seal_str"], best_params["seal_thr"], scenario, seed
                )
                tag = {**best_params, "regression_check": True}
                log_result(EXP_NAME, scenario["label"], tag, result)
                print(f"n_unk={result['n_unknown_final']}  MAE={result['mean_abs_error']:.4f}")
            except Exception as exc:
                print(f"ERROR: {exc}")
    else:
        print("\nNo single winner with n_unknown_post_sa < 100; review the sweep results.")

    print(f"\nResults logged to research/results/{EXP_NAME}.jsonl")
    summarize(EXP_NAME)


if __name__ == "__main__":
    run_sweep()
