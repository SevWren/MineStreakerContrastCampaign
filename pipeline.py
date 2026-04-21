"""
pipeline.py — Full orchestration.  Iter 2: asymmetric weights + extended schedule.
"""
import os, sys, json, time
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

try:
    from .core import (compute_N, load_image_smart,
                       compute_edge_weights, compute_asymmetric_weights,
                       assert_board_valid)
    from .corridors import build_adaptive_corridors
    from .sa import compile_sa_kernel, run_sa
    from .repair import run_phase1_repair
    from .report import render_report
except ImportError:
    from core import (compute_N, load_image_smart,
                      compute_edge_weights, compute_asymmetric_weights,
                      assert_board_valid)
    from corridors import build_adaptive_corridors
    from sa import compile_sa_kernel, run_sa
    from repair import run_phase1_repair
    from report import render_report


def atomic_save_json(data, path):
    tmp = path + '.tmp'
    with open(tmp, 'w') as f: json.dump(data, f, indent=2)
    os.replace(tmp, path)

def atomic_save_npy(arr, path):
    tmp = path + '.tmp.npy'
    np.save(tmp, arr)
    os.replace(tmp, path)


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
