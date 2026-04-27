"""
pipeline.py — Full orchestration.  Iter 2: asymmetric weights + extended schedule.
"""
import os, sys, json, time, warnings
from dataclasses import dataclass, field
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

try:
    from .core import (compute_N, load_image_smart,
                       compute_edge_weights, compute_asymmetric_weights,
                       assert_board_valid)
    from .corridors import build_adaptive_corridors
    from .sa import compile_sa_kernel, run_sa
    from .repair import run_last100_repair, run_phase1_repair, run_phase2_full_repair
    from .report import render_report
    from .solver import classify_unresolved_clusters, solve_board
except ImportError:
    from core import (compute_N, load_image_smart,
                      compute_edge_weights, compute_asymmetric_weights,
                      assert_board_valid)
    from corridors import build_adaptive_corridors
    from sa import compile_sa_kernel, run_sa
    from repair import run_last100_repair, run_phase1_repair, run_phase2_full_repair
    from report import render_report
    from solver import classify_unresolved_clusters, solve_board


def atomic_save_json(data, path):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f: json.dump(data, f, indent=2)
    os.replace(tmp, path)

def atomic_save_npy(arr, path):
    tmp = path + '.tmp.npy'
    np.save(tmp, arr)
    os.replace(tmp, path)


@dataclass
class RepairRoutingConfig:
    phase2_budget_s: float = 360.0
    last100_budget_s: float = 300.0
    last100_unknown_threshold: int = 100
    solve_max_rounds: int = 300
    trial_max_rounds: int = 60
    enable_phase2: bool = True
    enable_last100: bool = True
    enable_sa_rerun: bool = False


@dataclass
class RepairRouteResult:
    grid: np.ndarray
    sr: object
    selected_route: str
    route_result: str
    failure_taxonomy: dict
    phase2_log: list = field(default_factory=list)
    last100_log: list = field(default_factory=list)
    visual_delta_summary: dict = field(default_factory=dict)
    decision: dict = field(default_factory=dict)


def route_late_stage_failure(
    grid: np.ndarray,
    target: np.ndarray,
    weights: np.ndarray,
    forbidden: np.ndarray,
    sr,
    config: RepairRoutingConfig,
) -> RepairRouteResult:
    """
    Choose the cheapest next intervention based on unresolved-cell diagnosis.
    """
    del weights
    failure_taxonomy = classify_unresolved_clusters(grid, sr)
    decision = {
        "solver_n_unknown_before": int(sr.n_unknown),
        "dominant_failure_class": failure_taxonomy.get("dominant_failure_class"),
        "recommended_route": failure_taxonomy.get("recommended_route"),
        "selected_route": "needs_sa_or_adaptive_rerun",
        "phase2_budget_s": float(config.phase2_budget_s),
        "last100_budget_s": float(config.last100_budget_s),
        "last100_invoked": False,
        "sa_rerun_invoked": False,
        "solver_n_unknown_after": int(sr.n_unknown),
        "route_result": "unresolved_after_repair",
    }

    if int(sr.n_unknown) == 0:
        decision["selected_route"] = "already_solved"
        decision["route_result"] = "solved"
        return RepairRouteResult(
            grid=grid.copy(),
            sr=sr,
            selected_route="already_solved",
            route_result="solved",
            failure_taxonomy=failure_taxonomy,
            decision=decision,
        )

    if config.enable_phase2 and int(failure_taxonomy.get("sealed_cluster_count", 0)) > 0:
        routed_grid, _, phase2_log = run_phase2_full_repair(
            grid,
            target,
            forbidden,
            verbose=True,
            time_budget_s=float(config.phase2_budget_s),
            trial_max_rounds=int(config.trial_max_rounds),
            solve_max_rounds=int(config.solve_max_rounds),
        )
        routed_sr = solve_board(routed_grid, max_rounds=int(config.solve_max_rounds), mode="full")
        if int(routed_sr.n_unknown) == 0:
            decision["selected_route"] = "phase2_full_repair"
            decision["solver_n_unknown_after"] = int(routed_sr.n_unknown)
            decision["route_result"] = "solved"
            visual_delta_summary = phase2_log[-1] if phase2_log else {}
            return RepairRouteResult(
                grid=routed_grid,
                sr=routed_sr,
                selected_route="phase2_full_repair",
                route_result="solved",
                failure_taxonomy=failure_taxonomy,
                phase2_log=phase2_log,
                visual_delta_summary=visual_delta_summary,
                decision=decision,
            )
        grid = routed_grid
        sr = routed_sr

    if config.enable_last100 and int(sr.n_unknown) <= int(config.last100_unknown_threshold):
        routed_grid, routed_sr, _, last100_log, stop_reason = run_last100_repair(
            grid,
            target,
            target,
            forbidden,
            budget_s=float(config.last100_budget_s),
            trial_max_rounds=int(config.trial_max_rounds),
            solve_max_rounds=int(config.solve_max_rounds),
            verbose=True,
        )
        decision["selected_route"] = "last100_repair"
        decision["last100_invoked"] = True
        decision["solver_n_unknown_after"] = int(routed_sr.n_unknown)
        decision["route_result"] = "solved" if int(routed_sr.n_unknown) == 0 else "unresolved_after_repair"
        decision["last100_stop_reason"] = stop_reason
        visual_delta_summary = last100_log[-1] if last100_log else {}
        return RepairRouteResult(
            grid=routed_grid,
            sr=routed_sr,
            selected_route="last100_repair",
            route_result=decision["route_result"],
            failure_taxonomy=failure_taxonomy,
            last100_log=last100_log,
            visual_delta_summary=visual_delta_summary,
            decision=decision,
        )

    return RepairRouteResult(
        grid=grid.copy(),
        sr=sr,
        selected_route="needs_sa_or_adaptive_rerun",
        route_result="unresolved_after_repair",
        failure_taxonomy=failure_taxonomy,
        decision=decision,
    )


def write_repair_route_artifacts(
    out_dir: str,
    board_label: str,
    route_result: RepairRouteResult,
    artifact_metadata: dict | None = None,
) -> dict:
    """
    Write failure_taxonomy.json, repair_route_decision.json, visual_delta_summary.json.
    Return artifact paths.
    """
    del board_label
    failure_taxonomy_path = os.path.join(out_dir, "failure_taxonomy.json")
    repair_route_decision_path = os.path.join(out_dir, "repair_route_decision.json")
    visual_delta_summary_path = os.path.join(out_dir, "visual_delta_summary.json")
    failure_taxonomy = dict(route_result.failure_taxonomy)
    repair_route_decision = dict(route_result.decision)
    visual_delta_summary = dict(route_result.visual_delta_summary)
    if artifact_metadata is not None:
        failure_taxonomy["artifact_metadata"] = dict(artifact_metadata)
        repair_route_decision["artifact_metadata"] = dict(artifact_metadata)
        visual_delta_summary["artifact_metadata"] = dict(artifact_metadata)
    atomic_save_json(failure_taxonomy, failure_taxonomy_path)
    atomic_save_json(repair_route_decision, repair_route_decision_path)
    atomic_save_json(visual_delta_summary, visual_delta_summary_path)
    return {
        "failure_taxonomy": failure_taxonomy_path,
        "repair_route_decision": repair_route_decision_path,
        "visual_delta_summary": visual_delta_summary_path,
    }


def run_board(board_w, board_h, label, sa_fn, img_path, out_dir,
              iter_num=2,
              density=0.22, border=3, seed=42,
              coarse_iters=2_000_000, fine_iters=6_000_000, refine_iters=8_000_000,
              T_coarse_start=10.0, T_fine=3.5, T_refine=2.0,
              alpha_coarse=0.99998, alpha_fine=0.999996, alpha_refine=0.999997,
              T_min=0.001,
              # Iter 2 weight params
              bg_penalty=6.0, hi_boost=8.0, hi_threshold=3.0,
              edge_sigma=1.0, edge_boost=2.0,
              verbose=True):
    """Legacy orchestration path kept for compatibility. Deprecated."""
    warnings.warn(
        "pipeline.run_board() is legacy/deprecated and will be removed in a future cleanup.",
        DeprecationWarning,
        stacklevel=2,
    )

    t_total = time.perf_counter()

    # ── Step 0: guard ────────────────────────────────────────────────────
    from assets.image_guard import verify_source_image
    verify_source_image(img_path, halt_on_failure=True, verbose=verbose)
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    # ── Step 1: image + weights ──────────────────────────────────────────
    print(f"\n[{label}] Loading image…", flush=True)
    target  = load_image_smart(img_path, board_w, board_h, invert=True)

    # ITER 2 PRIMARY CHANGE: asymmetric weights
    weights = compute_asymmetric_weights(target,
                                          bg_penalty=bg_penalty,
                                          hi_boost=hi_boost,
                                          hi_threshold=hi_threshold,
                                          edge_sigma=edge_sigma,
                                          edge_boost=edge_boost)
    print(f"  Asymmetric weights: bg_penalty={bg_penalty}  hi_boost={hi_boost}  "
          f"hi_threshold={hi_threshold}", flush=True)
    print(f"  Weight range: [{weights.min():.2f}, {weights.max():.2f}]  "
          f"mean={weights.mean():.3f}", flush=True)
    print(f"  Target range: [{target.min():.2f}, {target.max():.2f}]  "
          f"mean={target.mean():.3f}", flush=True)

    # ── Step 2: corridors ───────────────────────────────────────────────
    print(f"[{label}] Building corridors…", flush=True)
    forbidden, corridor_pct, seeds, mst = build_adaptive_corridors(
        target, border=border, corridor_width=0, low_target_bias=5.5)
    print(f"  corridor_pct={corridor_pct:.1f}%  n_seeds={len(seeds)}", flush=True)

    # ── Step 3: coarse SA ───────────────────────────────────────────────
    cW, cH = max(10, board_w//2), max(8, board_h//2)
    print(f"[{label}] Coarse SA ({cW}×{cH}, {coarse_iters:,} iters)…", flush=True)
    target_c  = load_image_smart(img_path, cW, cH, invert=True)
    weights_c = compute_asymmetric_weights(target_c, bg_penalty=bg_penalty,
                                           hi_boost=hi_boost, hi_threshold=hi_threshold,
                                           edge_sigma=edge_sigma, edge_boost=edge_boost)
    forbidden_c, _, _, _ = build_adaptive_corridors(target_c, border=border)

    grid_c = np.zeros((cH, cW), dtype=np.int8)
    avail_c = np.argwhere(forbidden_c == 0)
    idx_c = rng.choice(len(avail_c), size=min(int(density*cW*cH), len(avail_c)), replace=False)
    for i in idx_c: grid_c[avail_c[i][0], avail_c[i][1]] = 1

    t1 = time.perf_counter()
    grid_c, lc, hc = run_sa(sa_fn, grid_c, target_c, weights_c, forbidden_c,
                              n_iters=coarse_iters, T_start=T_coarse_start,
                              T_min=T_min, alpha=alpha_coarse, border=border, seed=seed)
    print(f"  Coarse done {time.perf_counter()-t1:.1f}s  loss={lc:.0f}  density={grid_c.mean():.3f}", flush=True)

    # ── Upsample ────────────────────────────────────────────────────────
    from PIL import Image as PILImage
    ci = PILImage.fromarray(grid_c.astype(np.uint8)*255)
    fi = ci.resize((board_w, board_h), PILImage.NEAREST)
    grid = (np.array(fi, dtype=np.uint8) > 127).astype(np.int8)
    grid[forbidden == 1] = 0

    # ── Step 4: fine SA ─────────────────────────────────────────────────
    print(f"[{label}] Fine SA ({fine_iters:,} iters)…", flush=True)
    t2 = time.perf_counter()
    grid, lf, hf = run_sa(sa_fn, grid, target, weights, forbidden,
                           n_iters=fine_iters, T_start=T_fine, T_min=T_min,
                           alpha=alpha_fine, border=border, seed=seed+1)
    grid[forbidden == 1] = 0
    print(f"  Fine done {time.perf_counter()-t2:.1f}s  loss={lf:.0f}  density={grid.mean():.3f}", flush=True)

    # ── Step 5: refine SA with underfill-augmented weights ───────────────
    print(f"[{label}] Refine SA ({refine_iters:,} iters)…", flush=True)
    N_cur    = compute_N(grid)
    underfill = np.clip(target - N_cur.astype(np.float32), 0.0, 8.0) / 8.0
    w_aug     = (weights * (1.0 + 1.5 * underfill)).astype(np.float32)

    t3 = time.perf_counter()
    grid, lr, hr = run_sa(sa_fn, grid, target, w_aug, forbidden,
                           n_iters=refine_iters, T_start=T_refine, T_min=T_min,
                           alpha=alpha_refine, border=border, seed=seed+2)
    grid[forbidden == 1] = 0
    print(f"  Refine done {time.perf_counter()-t3:.1f}s  loss={lr:.0f}  density={grid.mean():.3f}", flush=True)

    # ── Step 6: validate ────────────────────────────────────────────────
    assert_board_valid(grid, forbidden, label='post-SA')
    print(f"  assert_board_valid PASSED (post-SA)", flush=True)

    # ── Step 7: repair ──────────────────────────────────────────────────
    try:
        from .solver import solve_board
    except ImportError:
        from solver import solve_board
    sr_pre = solve_board(grid, max_rounds=50, mode='trial')
    repair_budget = max(60.0, sr_pre.n_unknown * 0.15 + 30.0)
    print(f"[{label}] Repair budget={repair_budget:.0f}s  n_unknown={sr_pre.n_unknown}…", flush=True)

    grid, sr, repair_reason = run_phase1_repair(
        grid, target, weights, forbidden,
        time_budget_s=min(repair_budget, 120.0), max_rounds=300,
        search_radius=6, verbose=verbose, checkpoint_dir=out_dir)
    grid[forbidden == 1] = 0

    # ── Step 8: validate post-repair ────────────────────────────────────
    assert_board_valid(grid, forbidden, label='post-repair')
    print(f"  assert_board_valid PASSED (post-repair)", flush=True)

    # ── Step 9: metrics ──────────────────────────────────────────────────
    try:
        from .solver import solve_board as _solve
    except ImportError:
        from solver import solve_board as _solve
    sr_final = _solve(grid, max_rounds=300, mode='full')
    N_final  = compute_N(grid)
    err      = np.abs(N_final.astype(np.float32) - target)
    total_time = time.perf_counter() - t_total

    metrics = {
        "label":          label,
        "board":          f"{board_w}x{board_h}",
        "cells":          board_w * board_h,
        "loss_per_cell":  float(err.var()),
        "mean_abs_error": float(err.mean()),
        "pct_within_1":   float(np.mean(err <= 1.0) * 100),
        "pct_within_2":   float(np.mean(err <= 2.0) * 100),
        "hi_err":         float(err[target >= 3.0].mean()) if (target >= 3.0).any() else 0.0,
        "bg_err":         float(err[target <  1.0].mean()) if (target <  1.0).any() else 0.0,
        "mine_density":   float(grid.mean()),
        "corridor_pct":   float(corridor_pct),
        "coverage":       float(sr_final.coverage),
        "solvable":       bool(sr_final.solvable),
        "mine_accuracy":  float(sr_final.mine_accuracy),
        "n_unknown":      int(sr_final.n_unknown),
        "repair_reason":  repair_reason,
        "total_time_s":   float(total_time),
        "seed":           seed,
        # Iter 2 extra fields
        "bg_penalty":     bg_penalty,
        "hi_boost":       hi_boost,
        "hi_threshold":   hi_threshold,
        "iter":           iter_num,
    }

    print(f"\n{'='*55}", flush=True)
    print(f"  RESULTS [{label}] iter{iter_num}", flush=True)
    for k, v in metrics.items():
        print(f"    {k:22s}: {v}", flush=True)
    print(f"{'='*55}\n", flush=True)

    # ── Step 10: saves + report ──────────────────────────────────────────
    base     = f"iter{iter_num}_{label}"
    json_path = os.path.join(out_dir, f"metrics_{base}.json")
    npy_path  = os.path.join(out_dir, f"grid_{base}.npy")
    png_path  = os.path.join(out_dir, f"{base}_FINAL.png")

    atomic_save_json(metrics, json_path)
    atomic_save_npy(grid, npy_path)

    all_hist = np.concatenate([hc, hf, hr])
    render_report(target, grid, sr_final, all_hist,
                  title=f"Mine-Streaker Iter{iter_num} — {label}  "
                        f"[bg={bg_penalty} hi={hi_boost}]",
                  save_path=png_path, dpi=120)

    print(f"  Saved: {json_path}", flush=True)
    print(f"  Saved: {npy_path}",  flush=True)
    print(f"  Saved: {png_path}",  flush=True)
    return metrics
