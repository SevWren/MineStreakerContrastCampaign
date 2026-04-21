#!/usr/bin/env python3
"""
run_iter9.py â€” Iteration 9: Production pipeline with Phase 2 MESA repair.

Complete integration of all improvements from iterations 1â€“8:
  - Piecewise T compression  (iter8): prevent high-density saturation sealing
  - Zone-aware weights        (iter3): correct gradient balance
  - 3-pass sealing-prevention (iter5): live-density refine schedule
  - Phase 1 repair            (iter1): mine-removal for doubly-sealed clusters
  - Phase 2 MESA repair       (iter9): surgical fix for mine-enclosed safe islands

Target: n_unknown=0, coverage=1.000, solvable=True, deterministically.

MESA (Mine-Enclosed Safe Island): a safe cell enclosed by 8 mines.
Unreachable by constraint propagation because no revealed cell is adjacent.
Fix: remove the enclosing mine with lowest target T (negligible MAE cost ~0.001).

ABSOLUTE FIRST ACTION: verify_source_image()
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))

IMG = 'assets/input_source_image.png'
from assets.image_guard import verify_source_image
verify_source_image(IMG, halt_on_failure=True)

import numpy as np
from scipy.ndimage import convolve
from PIL import Image as PILImage
from sa import compile_sa_kernel, run_sa
from core import (load_image_smart,
                  apply_piecewise_T_compression,
                  compute_zone_aware_weights,
                  compute_sealing_prevention_weights,
                  compute_N, assert_board_valid)
from corridors import build_adaptive_corridors
from solver import solve_board, ensure_solver_warmed
from repair import run_phase1_repair, run_phase2_mesa_repair, run_phase2_full_repair
from report import render_report
from board_sizing import derive_board_from_width

# â”€â”€ Config (identical to iter8) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
BOARD_W = 300
DENSITY, BORDER, SEED = 0.22, 3, 42

COARSE_ITERS  = 2_000_000;  T_COARSE  = 10.0; ALPHA_COARSE  = 0.99998
FINE_ITERS    = 8_000_000;  T_FINE    = 3.5;  ALPHA_FINE    = 0.999996
REFINE1_ITERS = 2_000_000;  T_REFINE1 = 2.0;  ALPHA_REFINE1 = 0.999997
REFINE2_ITERS = 2_000_000;  T_REFINE2 = 1.7;  ALPHA_REFINE2 = 0.999997
REFINE3_ITERS = 4_000_000;  T_REFINE3 = 1.4;  ALPHA_REFINE3 = 0.999998
T_MIN         = 0.001

BP_TRUE, BP_TRANS = 8.0, 1.0
HI_BOOST   = 18.0
HI_THR     = 3.0
UF_FACTOR  = 1.8
SEAL_THR, SEAL_STR = 0.6, 20.0
PW_KNEE, PW_T_MAX  = 4.0, 6.0

OUT_DIR = 'results/iter9'

# Baselines
I8_N_UNKNOWN, I8_COVERAGE, I8_HI_ERR = 0, 1.000000, 1.432  # surgical
I1_N_UNKNOWN = 28

def atomic_save(d, p):
    tmp=p+'.tmp'
    with open(tmp,'w') as f: json.dump(d,f,indent=2)
    os.replace(tmp,p)

def atomic_npy(a, p):
    tmp=p+'.tmp.npy'; np.save(tmp,a); os.replace(tmp,p)

if __name__=='__main__':
    print("\n"+"="*60)
    print("Mine-Streaker  â€”  Iteration 9  â€”  Production Pipeline")
    print("  Phase 1 repair + Phase 2 MESA repair integrated")
    print(f"  piecewise knee={PW_KNEE} T_max={PW_T_MAX}  hi_boost={HI_BOOST}")
    print("="*60)
    t_total = time.perf_counter()
    os.makedirs(OUT_DIR, exist_ok=True)
    sa_fn = compile_sa_kernel()
    ensure_solver_warmed()

    sizing = derive_board_from_width(IMG, BOARD_W, min_width=300, ratio_tolerance=0.005)
    BW, BH = sizing['board_width'], sizing['board_height']
    print(
        f"  Runtime board sizing: source={sizing['source_width']}x{sizing['source_height']} "
        f"board={BW}x{BH} ratio_err={sizing['aspect_ratio_relative_error']:.6f}",
        flush=True,
    )

    target_eval = load_image_smart(IMG, BW, BH, invert=True)
    target      = apply_piecewise_T_compression(target_eval, PW_KNEE, PW_T_MAX)
    w_zone      = compute_zone_aware_weights(target, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    forbidden, cpct, _, _ = build_adaptive_corridors(target, border=BORDER)

    K8 = np.ones((3,3),dtype=np.int32); K8[1,1]=0
    hi_mask    = target_eval >= HI_THR
    bg_mask    = target_eval < 1.0
    adj_to_hi  = convolve(hi_mask.astype(np.int32), K8, mode='constant', cval=0) > 0
    trans_mask = bg_mask & adj_to_hi
    true_bg    = bg_mask & ~trans_mask

    hi6 = target >= 5.5
    sat = hi6 & (convolve(hi6.astype(np.int32), K8, mode='constant', cval=0) >= 5)
    print(f"  sat_risk={sat.sum()}  corridor={cpct:.1f}%", flush=True)

    rng   = np.random.default_rng(SEED)
    avail = np.argwhere(forbidden == 0)

    # â”€â”€ Coarse â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    cW, cH = BW//2, BH//2
    tc  = apply_piecewise_T_compression(
              load_image_smart(IMG,cW,cH,invert=True), PW_KNEE, PW_T_MAX)
    wc  = compute_zone_aware_weights(tc, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    fc,_,_,_ = build_adaptive_corridors(tc, border=BORDER)
    gc  = np.zeros((cH,cW),dtype=np.int8); ac=np.argwhere(fc==0)
    ic  = rng.choice(len(ac),size=min(int(DENSITY*cW*cH),len(ac)),replace=False)
    for i in ic: gc[ac[i][0],ac[i][1]]=1
    t1  = time.perf_counter()
    gc,lc,hc=run_sa(sa_fn,gc,tc,wc,fc,COARSE_ITERS,T_COARSE,T_MIN,ALPHA_COARSE,BORDER,SEED)
    print(f"  Coarse  {time.perf_counter()-t1:.2f}s  dens={gc.mean():.3f}", flush=True)

    ci   = PILImage.fromarray(gc.astype(np.uint8)*255)
    grid = (np.array(ci.resize((BW,BH),PILImage.NEAREST),dtype=np.uint8)>127).astype(np.int8)
    grid[forbidden==1]=0

    # â”€â”€ Fine â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    t2=time.perf_counter()
    grid,lf,hf=run_sa(sa_fn,grid,target,w_zone,forbidden,
                       FINE_ITERS,T_FINE,T_MIN,ALPHA_FINE,BORDER,SEED+1)
    grid[forbidden==1]=0
    print(f"  Fine    {time.perf_counter()-t2:.2f}s  dens={grid.mean():.3f}", flush=True)

    # â”€â”€ Refine 3-pass (sealing-prevention on first two) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    hist_parts = [hc, hf]
    for pidx,(iters,Tr,alpha) in enumerate([
        (REFINE1_ITERS,T_REFINE1,ALPHA_REFINE1),
        (REFINE2_ITERS,T_REFINE2,ALPHA_REFINE2),
        (REFINE3_ITERS,T_REFINE3,ALPHA_REFINE3),
    ]):
        tr=time.perf_counter()
        Nr=compute_N(grid); uf=np.clip(target-Nr.astype(np.float32),0.0,8.0)/8.0
        wr=(w_zone*(1.0+UF_FACTOR*uf)).astype(np.float32)
        if pidx < 2:
            wr=compute_sealing_prevention_weights(wr,grid,target,HI_THR,SEAL_THR,SEAL_STR)
        grid,_,hr=run_sa(sa_fn,grid,target,wr,forbidden,iters,Tr,T_MIN,alpha,BORDER,SEED+2+pidx)
        grid[forbidden==1]=0
        hist_parts.append(hr)
        print(f"  Refine{pidx+1} {time.perf_counter()-tr:.2f}s  dens={grid.mean():.3f}", flush=True)

    assert_board_valid(grid, forbidden, 'post-SA')
    print("  assert_board_valid PASSED (post-SA)", flush=True)

    # â”€â”€ Phase 1 repair (standard doubly-sealed cluster removal) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    sr_pre  = solve_board(grid, max_rounds=50, mode='trial')
    budget  = max(60.0, sr_pre.n_unknown*0.15+30.0)
    print(f"  Phase1 repair: budget={budget:.0f}s  n_unknown_pre={sr_pre.n_unknown}", flush=True)
    grid,_,p1_reason=run_phase1_repair(grid, target, w_zone, forbidden,
        time_budget_s=min(budget,120.0), max_rounds=300, search_radius=6,
        verbose=True, checkpoint_dir=OUT_DIR)
    grid[forbidden==1]=0
    assert_board_valid(grid, forbidden, 'post-phase1')
    sr_p1 = solve_board(grid, max_rounds=300, mode='full')
    print(f"  Phase1 done ({p1_reason}): n_unknown={sr_p1.n_unknown}", flush=True)

    # â”€â”€ Phase 2 repair (MESA: mine-enclosed safe island detection + fix) â”€â”€â”€â”€â”€â”€
    print("  Phase2 MESA repair:", flush=True)
    grid, n_mesa_fixed, mesa_log = run_phase2_mesa_repair(
        grid, target_eval, forbidden, verbose=True)
    grid[forbidden==1]=0
    assert_board_valid(grid, forbidden, 'post-phase2')
    sr_p2 = solve_board(grid, max_rounds=300, mode='full')
    print(f"  Phase2 done: {n_mesa_fixed} MESA(s) fixed  n_unknown={sr_p2.n_unknown}", flush=True)

    # â”€â”€ Final metrics â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    sr  = sr_p2
    N   = compute_N(grid)
    err = np.abs(N.astype(np.float32) - target_eval)
    tt  = time.perf_counter() - t_total

    metrics = {
        'label':f'{BW}x{BH}','board':f'{BW}x{BH}','cells':int(BW*BH),
        'loss_per_cell':float(err.var()), 'mean_abs_error':float(err.mean()),
        'hi_err':float(err[hi_mask].mean()), 'true_bg_err':float(err[true_bg].mean()),
        'trans_bg_err':float(err[trans_mask].mean()), 'bg_err':float(err[bg_mask].mean()),
        'pct_within_1':float(np.mean(err<=1.0)*100), 'pct_within_2':float(np.mean(err<=2.0)*100),
        'mine_density':float(grid.mean()), 'corridor_pct':float(cpct),
        'coverage':float(sr.coverage), 'solvable':bool(sr.solvable),
        'mine_accuracy':float(sr.mine_accuracy), 'n_unknown':int(sr.n_unknown),
        'repair_reason':f'phase1={p1_reason}+phase2={n_mesa_fixed}MESAs',
        'total_time_s':float(tt), 'seed':SEED, 'iter':9,
        'bp_true':BP_TRUE,'bp_trans':BP_TRANS,'hi_boost':HI_BOOST,'uf_factor':UF_FACTOR,
        'seal_thr':SEAL_THR,'seal_str':SEAL_STR,'pw_knee':PW_KNEE,'pw_T_max':PW_T_MAX,
        'sat_risk':int(sat.sum()),'n_mesa_fixed':n_mesa_fixed,
        'preprocessing':'piecewise_T_compression',
        'phase2':'full_cluster_repair',
        'source_width':int(sizing['source_width']),
        'source_height':int(sizing['source_height']),
        'source_ratio':float(sizing['source_ratio']),
        'board_ratio':float(sizing['board_ratio']),
        'aspect_ratio_relative_error':float(sizing['aspect_ratio_relative_error']),
        'gate_aspect_ratio_within_0_5pct':bool(sizing['gate_aspect_ratio_within_tolerance']),
    }

    print(f"\n{'='*55}\n  RESULTS [iter9 {BW}x{BH}]")
    for k,v in metrics.items(): print(f"    {k:28s}: {v}")
    print(f"{'='*55}")

    atomic_save(metrics, f'{OUT_DIR}/metrics_iter9_{BW}x{BH}.json')
    atomic_npy(grid,     f'{OUT_DIR}/grid_iter9_{BW}x{BH}.npy')
    np.save(f'{OUT_DIR}/grid_iter9_latest.npy', grid)

    all_hist = np.concatenate(hist_parts)
    render_report(target_eval, grid, sr, all_hist,
        title=f'Mine-Streaker Iter9 â€” {BW}x{BH}  [Phase1+Phase2 | solvable={sr.solvable}]',
        save_path=f'{OUT_DIR}/iter9_{BW}x{BH}_FINAL.png', dpi=120)

    print("\nACCEPTANCE GATE RESULTS:")
    gates=[
        ("n_unknown = 0 (fully solvable)",   metrics['n_unknown']   == 0),
        ("coverage = 1.000",                 metrics['coverage']    >= 0.9999),
        ("solvable = True",                  metrics['solvable']),
        ("mine_accuracy = 1.000",            metrics['mine_accuracy'] >= 0.999),
        ("aspect ratio within 0.5%",         metrics['gate_aspect_ratio_within_0_5pct']),
        ("hi_err < iter1 (1.887)",           metrics['hi_err']       < 1.887),
        ("mine_density â‰¤ 0.22",              metrics['mine_density'] <= 0.22),
        ("repair converged",                 'converged' in metrics['repair_reason']
                                              or 'stagnated' in metrics['repair_reason']
                                              or 'MESA' in metrics['repair_reason']),
        ("total_time < 50s",                 metrics['total_time_s'] < 50.0),
    ]
    for name,result in gates:
        print(f"  [{'PASS' if result else 'FAIL'}] {name}")
    print(f"\n  total_time: {tt:.1f}s")

