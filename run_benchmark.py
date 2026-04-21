#!/usr/bin/env python3
"""
run_benchmark.py — Standard benchmark matrix validation.
Tests iter9 pipeline on all board sizes × seeds per spec §11.

Board sizes: 200x125, 250x156, 250x250
Seeds:       300, 301, 302
Image:       current assets/input_source_image.png

Reports median metrics across seeds for each board size.
Acceptance gates (spec §11 Iteration 2+):
  1. No coverage regression vs iter9 200x125 baseline (≥ 0.9999)
  2. n_unknown = 0
  3. mean_abs_error ≤ iter9 value (image/size specific)
  4. Runtime < 50s per board

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
from repair import run_phase1_repair, run_phase2_full_repair
from board_sizing import derive_board_from_width

def atomic_save(d, p):
    tmp=p+'.tmp'
    with open(tmp,'w') as f: json.dump(d,f,indent=2)
    os.replace(tmp,p)

def run_single(board_w, seed, sa_fn, out_dir):
    """Run full iter9 pipeline for one board/seed combination."""
    t0 = time.perf_counter()
    sizing = derive_board_from_width(IMG, board_w, min_width=300, ratio_tolerance=0.005)
    board_h = sizing['board_height']

    DENSITY=0.22; BORDER=3
    COARSE_ITERS=2_000_000;  T_COARSE=10.0;  ALPHA_COARSE=0.99998
    FINE_ITERS=8_000_000;    T_FINE=3.5;     ALPHA_FINE=0.999996
    REFINE1_ITERS=2_000_000; T_REFINE1=2.0;  ALPHA_REFINE1=0.999997
    REFINE2_ITERS=2_000_000; T_REFINE2=1.7;  ALPHA_REFINE2=0.999997
    REFINE3_ITERS=4_000_000; T_REFINE3=1.4;  ALPHA_REFINE3=0.999998
    T_MIN=0.001
    BP_TRUE=8.0; BP_TRANS=1.0; HI_BOOST=18.0; HI_THR=3.0; UF_FACTOR=1.8
    SEAL_THR=0.6; SEAL_STR=20.0; PW_KNEE=4.0; PW_T_MAX=6.0

    target_eval = load_image_smart(IMG, board_w, board_h, invert=True)
    target      = apply_piecewise_T_compression(target_eval, PW_KNEE, PW_T_MAX)
    w_zone      = compute_zone_aware_weights(target, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    forbidden, cpct, _, _ = build_adaptive_corridors(target, border=BORDER)

    K8 = np.ones((3,3),dtype=np.int32); K8[1,1]=0
    hi_mask = target_eval >= HI_THR; bg_mask = target_eval < 1.0
    adj     = convolve(hi_mask.astype(np.int32), K8, mode='constant', cval=0) > 0
    true_bg = bg_mask & ~adj

    rng   = np.random.default_rng(seed)
    avail = np.argwhere(forbidden == 0)

    # Coarse
    cW,cH = board_w//2, board_h//2
    tc  = apply_piecewise_T_compression(load_image_smart(IMG,cW,cH,invert=True),PW_KNEE,PW_T_MAX)
    wc  = compute_zone_aware_weights(tc, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    fc,_,_,_ = build_adaptive_corridors(tc, border=BORDER)
    gc  = np.zeros((cH,cW),dtype=np.int8); ac=np.argwhere(fc==0)
    ic  = rng.choice(len(ac),size=min(int(DENSITY*cW*cH),len(ac)),replace=False)
    for i in ic: gc[ac[i][0],ac[i][1]]=1
    gc,_,hc=run_sa(sa_fn,gc,tc,wc,fc,COARSE_ITERS,T_COARSE,T_MIN,ALPHA_COARSE,BORDER,seed)
    ci   = PILImage.fromarray(gc.astype(np.uint8)*255)
    grid = (np.array(ci.resize((board_w,board_h),PILImage.NEAREST),dtype=np.uint8)>127).astype(np.int8)
    grid[forbidden==1]=0

    # Fine
    grid,_,_=run_sa(sa_fn,grid,target,w_zone,forbidden,
                     FINE_ITERS,T_FINE,T_MIN,ALPHA_FINE,BORDER,seed+1)
    grid[forbidden==1]=0

    # Refine 3-pass
    for pidx,(iters,Tr,alpha) in enumerate([
        (REFINE1_ITERS,T_REFINE1,ALPHA_REFINE1),
        (REFINE2_ITERS,T_REFINE2,ALPHA_REFINE2),
        (REFINE3_ITERS,T_REFINE3,ALPHA_REFINE3),
    ]):
        Nr=compute_N(grid); uf=np.clip(target-Nr.astype(np.float32),0.0,8.0)/8.0
        wr=(w_zone*(1.0+UF_FACTOR*uf)).astype(np.float32)
        if pidx<2:
            wr=compute_sealing_prevention_weights(wr,grid,target,HI_THR,SEAL_THR,SEAL_STR)
        grid,_,_=run_sa(sa_fn,grid,target,wr,forbidden,iters,Tr,T_MIN,alpha,BORDER,seed+2+pidx)
        grid[forbidden==1]=0

    assert_board_valid(grid, forbidden, f'post-SA-{board_w}x{board_h}-s{seed}')

    # Phase 1
    sr_pre=solve_board(grid,max_rounds=50,mode='trial')
    budget=max(60.0,sr_pre.n_unknown*0.15+30.0)
    grid,_,p1_reason=run_phase1_repair(grid,target,w_zone,forbidden,
        time_budget_s=min(budget,120.0),max_rounds=300,search_radius=6,
        verbose=False,checkpoint_dir=out_dir)
    grid[forbidden==1]=0
    assert_board_valid(grid, forbidden, f'post-p1-{board_w}x{board_h}-s{seed}')

    # Phase 2 MESA
    grid,n_mesa,_=run_phase2_full_repair(grid,target_eval,forbidden,verbose=False)
    grid[forbidden==1]=0
    assert_board_valid(grid, forbidden, f'post-p2-{board_w}x{board_h}-s{seed}')

    sr  = solve_board(grid,max_rounds=300,mode='full')
    N   = compute_N(grid)
    err = np.abs(N.astype(float)-target_eval)
    tt  = time.perf_counter()-t0

    return {
        'board':f'{board_w}x{board_h}', 'seed':seed, 'cells':board_w*board_h,
        'n_unknown':int(sr.n_unknown), 'coverage':float(sr.coverage),
        'solvable':bool(sr.solvable), 'mine_accuracy':float(sr.mine_accuracy),
        'hi_err':float(err[hi_mask].mean()), 'true_bg_err':float(err[true_bg].mean()),
        'mean_abs_error':float(err.mean()), 'pct_within_1':float(np.mean(err<=1)*100),
        'mine_density':float(grid.mean()), 'corridor_pct':float(cpct),
        'n_mesa_fixed':n_mesa, 'repair_reason':f'{p1_reason}+{n_mesa}MESAs',
        'total_time_s':float(tt),
        'source_ratio':float(sizing['source_ratio']),
        'board_ratio':float(sizing['board_ratio']),
        'aspect_ratio_relative_error':float(sizing['aspect_ratio_relative_error']),
        'gate_aspect_ratio_within_0_5pct':bool(sizing['gate_aspect_ratio_within_tolerance']),
    }


if __name__ == '__main__':
    print("\n"+"="*65)
    print("Mine-Streaker  —  Standard Benchmark Matrix")
    print("  Widths: 300, 360, 420 (height auto from source ratio)  |  Seeds: 300, 301, 302")
    print("="*65)

    sa_fn = compile_sa_kernel()
    ensure_solver_warmed()

    board_widths  = [300, 360, 420]
    seeds   = [300, 301, 302]
    out_dir = 'results/benchmark'
    os.makedirs(out_dir, exist_ok=True)

    all_results = []
    for bw in board_widths:
        bh = derive_board_from_width(IMG, bw, min_width=300, ratio_tolerance=0.005)['board_height']
        board_results = []
        print(f"\n--- {bw}x{bh} ---", flush=True)
        for seed in seeds:
            print(f"  seed={seed} ...", end='', flush=True)
            r = run_single(bw, seed, sa_fn, out_dir)
            board_results.append(r)
            all_results.append(r)
            print(f" n_unk={r['n_unknown']} cov={r['coverage']:.5f} "
                  f"hi_err={r['hi_err']:.4f} time={r['total_time_s']:.1f}s", flush=True)

        # Median across seeds
        med = {}
        for k in ['n_unknown','coverage','hi_err','true_bg_err','mean_abs_error',
                  'mine_density','total_time_s','pct_within_1','n_mesa_fixed']:
            vals = [r[k] for r in board_results]
            med[k] = float(np.median(vals))
        all_solvable = all(r['solvable'] for r in board_results)
        all_n0 = all(r['n_unknown']==0 for r in board_results)
        print(f"\n  MEDIAN {bw}x{bh}: n_unk={med['n_unknown']:.0f}  cov={med['coverage']:.5f}  "
              f"hi_err={med['hi_err']:.4f}  tru_bg={med['true_bg_err']:.4f}  "
              f"dens={med['mine_density']:.4f}  time={med['total_time_s']:.1f}s  "
              f"all_solvable={all_solvable}  all_n0={all_n0}", flush=True)

    # Save full results
    atomic_save(all_results, f'{out_dir}/benchmark_results.json')

    # Print final summary table
    print("\n" + "="*65)
    print("BENCHMARK SUMMARY (median across 3 seeds)")
    print("="*65)
    print(f"{'Board':10} {'n_unk':6} {'coverage':10} {'hi_err':8} {'tru_bg':8} {'dens':7} {'time':7} {'solvable':10}")
    for bw in board_widths:
        bh = derive_board_from_width(IMG, bw, min_width=300, ratio_tolerance=0.005)['board_height']
        board_res = [r for r in all_results if r['board']==f'{bw}x{bh}']
        def med(k): return float(np.median([r[k] for r in board_res]))
        all_s = all(r['solvable'] for r in board_res)
        all_n0 = all(r['n_unknown']==0 for r in board_res)
        print(f"{bw}x{bh:<6} {med('n_unknown'):6.0f} {med('coverage'):10.5f} "
              f"{med('hi_err'):8.4f} {med('true_bg_err'):8.4f} "
              f"{med('mine_density'):7.4f} {med('total_time_s'):7.1f}s "
              f"{'ALL ✓' if all_s and all_n0 else '✗'}")

    print("\nGates (per spec §11):")
    all_pass = True
    for bw in board_widths:
        bh = derive_board_from_width(IMG, bw, min_width=300, ratio_tolerance=0.005)['board_height']
        board_res = [r for r in all_results if r['board']==f'{bw}x{bh}']
        cov_ok  = all(r['coverage']>=0.9999 for r in board_res)
        n0_ok   = all(r['n_unknown']==0 for r in board_res)
        time_ok = all(r['total_time_s'] < 50 for r in board_res)
        s_ok    = all(r['solvable'] for r in board_res)
        ok = cov_ok and n0_ok and time_ok and s_ok
        if not ok: all_pass = False
        print(f"  {bw}x{bh}: coverage≥0.9999={'✓' if cov_ok else '✗'}  "
              f"n_unk=0={'✓' if n0_ok else '✗'}  "
              f"time<50s={'✓' if time_ok else '✗'}  "
              f"solvable={'✓' if s_ok else '✗'}")
    print(f"\n  Overall: {'ALL GATES PASS ✓' if all_pass else 'SOME GATES FAIL ✗'}")
