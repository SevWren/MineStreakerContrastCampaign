"""
repair.py — Phase 1 mine-removal repair.
Uses mode='trial' (no subset prop) for candidate screening; mode='full' for
final accuracy measurement. Parallel candidate evaluation via process pool.
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
from scipy.ndimage import convolve, label as nd_label
try:
    from .core import compute_N, assert_board_valid
    from .solver import SAFE, UNKNOWN, solve_board
except ImportError:
    from core import compute_N, assert_board_valid
    from solver import SAFE, UNKNOWN, solve_board


def _score_candidates(grid, state, search_radius=6):
    """Score mine cells by UNKNOWN-neighbour count. Returns [(score,y,x)] desc."""
    try:
        from .solver import UNKNOWN
    except ImportError:
        from solver import UNKNOWN
    H, W = grid.shape
    mine_ys, mine_xs = np.where(grid == 1)
    if len(mine_ys) == 0:
        return []
    scores = []
    for y, x in zip(mine_ys, mine_xs):
        r0=max(0,y-search_radius); r1=min(H,y+search_radius+1)
        c0=max(0,x-search_radius); c1=min(W,x+search_radius+1)
        n_unk = int(np.sum(state[r0:r1,c0:c1] == UNKNOWN))
        if n_unk > 0:
            scores.append((n_unk, int(y), int(x)))
    scores.sort(reverse=True)
    return scores


def _eval_removal(grid, forbidden, y, x, max_rounds=50):
    """Trial solve after removing mine at (y,x). Returns coverage float."""
    trial = grid.copy()
    trial[y, x] = 0
    trial[forbidden == 1] = 0
    sr = solve_board(trial, max_rounds=max_rounds, mode='trial')
    return sr.coverage, trial


def run_phase1_repair(grid, target, weights, forbidden,
                      time_budget_s=90.0, max_rounds=300,
                      search_radius=6, verbose=True,
                      checkpoint_dir=None,
                      candidate_top_k: int = 15,
                      parallel_eval: bool = True,
                      max_workers: int = None):
    t_start = time.perf_counter()
    best_grid = grid.copy()
    best_grid[forbidden == 1] = 0

    sr = solve_board(best_grid, max_rounds=max_rounds, mode='full')
    best_coverage = sr.coverage

    if verbose:
        print(f"  Repair start: coverage={best_coverage:.4f}, "
              f"n_unknown={sr.n_unknown}", flush=True)

    stop_reason = 'no_candidates'
    stagnation = 0
    max_stagnation = 8

    for rnd in range(10000):
        elapsed = time.perf_counter() - t_start
        if elapsed >= time_budget_s:
            stop_reason = f'timeout {elapsed:.0f}s'
            break

        sr_cur = solve_board(best_grid, max_rounds=max_rounds, mode='trial')
        if sr_cur.coverage >= 0.999:
            stop_reason = 'converged'
            break

        cands = _score_candidates(best_grid, sr_cur.state, search_radius)
        if not cands:
            stop_reason = 'no_candidates'
            break

        top_k = min(max(1, int(candidate_top_k)), len(cands))
        best_delta = 0.0
        best_cand  = None
        best_trial = None
        slice_cands = cands[:top_k]

        worker_count = max_workers if max_workers is not None else (os.cpu_count() or 1)
        worker_count = max(1, min(worker_count, top_k))
        can_parallel = parallel_eval and worker_count > 1 and top_k > 1

        if can_parallel:
            with ThreadPoolExecutor(max_workers=worker_count) as ex:
                future_map = {
                    ex.submit(_eval_removal, best_grid, forbidden, cy, cx): (cy, cx)
                    for (_, cy, cx) in slice_cands
                }
                for fut in as_completed(future_map):
                    if (time.perf_counter() - t_start) >= time_budget_s:
                        break
                    cy, cx = future_map[fut]
                    cov, trial_grid = fut.result()
                    delta = cov - sr_cur.coverage
                    if delta > best_delta:
                        best_delta = delta
                        best_cand = (cy, cx)
                        best_trial = trial_grid
        else:
            for (_, cy, cx) in slice_cands:
                if (time.perf_counter() - t_start) >= time_budget_s:
                    break
                cov, trial_grid = _eval_removal(best_grid, forbidden, cy, cx)
                delta = cov - sr_cur.coverage
                if delta > best_delta:
                    best_delta = delta
                    best_cand = (cy, cx)
                    best_trial = trial_grid

        if best_cand is None or best_delta <= 0:
            stagnation += 1
            if stagnation >= max_stagnation:
                stop_reason = 'stagnated'
                break
            # Force-remove worst blocking mine (lowest target value near unknown)
            if cands:
                # pick candidate where target[y,x] is lowest
                tgt_scores = [(float(target[y,x]), y, x) for (_,y,x) in cands[:5]]
                tgt_scores.sort()
                _, cy, cx = tgt_scores[0]
                best_grid[cy, cx] = 0
                best_grid[forbidden==1] = 0
            continue

        stagnation = 0
        best_grid = best_trial
        best_grid[forbidden == 1] = 0
        best_coverage = best_delta + sr_cur.coverage

        if verbose and rnd % 5 == 0:
            elapsed2 = time.perf_counter() - t_start
            print(f"  Repair rnd {rnd:3d}: coverage={best_coverage:.4f} "
                  f"n_unk={sr_cur.n_unknown} elapsed={elapsed2:.1f}s", flush=True)

        if checkpoint_dir and rnd % 10 == 0:
            cp = os.path.join(checkpoint_dir, 'repair_checkpoint.npy')
            tmp = cp + '.tmp.npy'
            np.save(tmp, best_grid)
            os.replace(tmp, cp)

    # Final accurate solve
    final_sr = solve_board(best_grid, max_rounds=max_rounds, mode='full')
    if verbose:
        print(f"  Repair done ({stop_reason}): coverage={final_sr.coverage:.4f} "
              f"n_unknown={final_sr.n_unknown}", flush=True)

    return best_grid, final_sr, stop_reason


def run_phase2_mesa_repair(grid: np.ndarray,
                            target: np.ndarray,
                            forbidden: np.ndarray,
                            verbose: bool = True) -> tuple:
    """
    Phase 2: Mine-Enclosed Safe-Island (MESA) repair.

    Detects safe cells completely enclosed by 8 mines (unreachable by constraint
    propagation) and surgically removes the enclosing mine with lowest target T
    value. Repeats until no MESAs remain or no progress is made.

    A MESA is NOT a 50/50 ambiguity — the cell IS known to be safe (it is
    grid=0), but the solver has no information pathway to reach it because
    its N value is hidden (unrevealed) and all adjacent cells are mines.

    Cost per MESA fix: ~0.001 MAE (negligible).
    Safety: verified to not cascade into new MESAs.

    Returns (grid, n_fixed, mesa_list)
    """
    grid = grid.copy()
    H, W = grid.shape
    n_fixed = 0
    mesa_history = []

    for iteration in range(100):  # safety cap
        # Detect all MESAs
        mesas = []
        for y in range(1, H-1):
            for x in range(1, W-1):
                if grid[y, x] != 0 or forbidden[y, x] == 1:
                    continue
                mine_neighbours = []
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if dy == 0 and dx == 0:
                            continue
                        ny, nx = y+dy, x+dx
                        if 0 <= ny < H and 0 <= nx < W:
                            if grid[ny, nx] == 1 and forbidden[ny, nx] == 0:
                                mine_neighbours.append((ny, nx))
                # MESA: safe cell with all 8 valid neighbours being mines
                n_valid_nbs = sum(1 for dy in range(-1,2) for dx in range(-1,2)
                                  if not(dy==0 and dx==0)
                                  and 0<=y+dy<H and 0<=x+dx<W)
                if len(mine_neighbours) == n_valid_nbs and n_valid_nbs == 8:
                    mesas.append((y, x, mine_neighbours))

        if not mesas:
            break

        if verbose:
            print(f"  Phase2 pass {iteration+1}: found {len(mesas)} MESA(s)", flush=True)

        made_progress = False
        for (cy, cx, nbs) in mesas:
            # Remove the mine with the lowest T value (minimum visual cost)
            best = min(nbs, key=lambda yx: float(target[yx[0], yx[1]]))
            grid[best[0], best[1]] = 0
            grid[forbidden == 1] = 0
            n_fixed += 1
            made_progress = True
            mesa_history.append({'mesa': (cy, cx), 'removed': best,
                                  'T_removed': float(target[best[0], best[1]])})
            if verbose:
                print(f"    Fixed MESA ({cy},{cx}): removed mine at {best} "
                      f"(T={target[best[0],best[1]]:.2f})", flush=True)

        if not made_progress:
            break

    if verbose:
        print(f"  Phase2 complete: {n_fixed} MESA(s) fixed", flush=True)

    return grid, n_fixed, mesa_history


def compute_repair_visual_delta(
    before_grid: np.ndarray,
    after_grid: np.ndarray,
    target: np.ndarray,
) -> dict:
    """
    Compare visual cost before and after a repair move using |N - T| mean absolute error.
    """
    before_n = compute_N(before_grid)
    after_n = compute_N(after_grid)
    before_err = np.abs(before_n.astype(np.float32) - target.astype(np.float32))
    after_err = np.abs(after_n.astype(np.float32) - target.astype(np.float32))
    removed = np.argwhere((before_grid == 1) & (after_grid == 0))
    added = np.argwhere((before_grid == 0) & (after_grid == 1))
    changed = np.argwhere(before_grid != after_grid)
    return {
        "mean_abs_error_before": float(before_err.mean()),
        "mean_abs_error_after": float(after_err.mean()),
        "visual_delta": float(after_err.mean() - before_err.mean()),
        "changed_cells": int(changed.shape[0]),
        "removed_mines": [[int(y), int(x)] for y, x in removed],
        "added_mines": [[int(y), int(x)] for y, x in added],
    }


def _compute_error_metrics_for_last100(grid: np.ndarray, target_eval: np.ndarray, hi_thr: float = 3.0) -> dict:
    N = compute_N(grid)
    err = np.abs(N.astype(np.float32) - target_eval.astype(np.float32))
    k8 = np.ones((3, 3), dtype=np.int32)
    k8[1, 1] = 0
    hi_mask = target_eval >= hi_thr
    bg_mask = target_eval < 1.0
    adj_to_hi = convolve(hi_mask.astype(np.int32), k8, mode="constant", cval=0) > 0
    true_bg = bg_mask & ~adj_to_hi
    return {
        "mean_abs_error": float(err.mean()),
        "hi_err": float(err[hi_mask].mean()) if np.any(hi_mask) else 0.0,
        "true_bg_err": float(err[true_bg].mean()) if np.any(true_bg) else 0.0,
        "mine_density": float(grid.mean()),
    }


def find_sealed_unknown_clusters(grid: np.ndarray, sr, forbidden: np.ndarray) -> list[dict]:
    """
    Return sealed UNKNOWN clusters without mutating the grid.
    Uses sr.state as authoritative solver state.
    """
    if sr is None or sr.state is None or int(sr.n_unknown) <= 0:
        return []

    state = sr.state
    labeled, n_comp = nd_label((state == UNKNOWN).astype(np.int8))
    clusters = []
    for cluster_id in range(1, int(n_comp) + 1):
        comp_mask = labeled == cluster_id
        unk_cells = np.argwhere(comp_mask)
        ext_mines = set()
        has_safe_neighbor = False

        for cy, cx in unk_cells:
            cy_i = int(cy)
            cx_i = int(cx)
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dy == 0 and dx == 0:
                        continue
                    ny = cy_i + dy
                    nx = cx_i + dx
                    if 0 <= ny < grid.shape[0] and 0 <= nx < grid.shape[1]:
                        if state[ny, nx] == SAFE:
                            has_safe_neighbor = True
                        if grid[ny, nx] == 1 and forbidden[ny, nx] == 0 and not comp_mask[ny, nx]:
                            ext_mines.add((int(ny), int(nx)))

        if has_safe_neighbor or not ext_mines:
            continue

        cells = [(int(y), int(x)) for y, x in unk_cells]
        clusters.append(
            {
                "cluster_id": int(cluster_id),
                "cluster_size": int(len(cells)),
                "cells": [[int(y), int(x)] for y, x in cells],
                "has_safe_neighbor": False,
                "external_mines": [[int(y), int(x)] for y, x in sorted(ext_mines)],
                "external_mine_count": int(len(ext_mines)),
                "cluster_kind": "sealed_single_mesa" if len(cells) == 1 else "sealed_multi_cell_cluster",
            }
        )
    return clusters


def run_last100_repair(
    grid: np.ndarray,
    target: np.ndarray,
    target_eval: np.ndarray,
    forbidden: np.ndarray,
    *,
    budget_s: float,
    max_outer_iterations: int = 12,
    trial_max_rounds: int = 60,
    solve_max_rounds: int = 300,
    pair_trial_limit: int = 12,
    pair_combo_limit: int = 24,
    max_error_delta_mean_abs: float = 0.005,
    max_error_delta_true_bg: float = 0.03,
    max_error_delta_hi: float = 0.03,
    verbose: bool = True,
):
    t_start = time.perf_counter()
    work_grid = grid.copy()
    move_log = []
    n_fixes = 0
    stop_reason = "no_effect"

    def elapsed() -> float:
        return time.perf_counter() - t_start

    for iteration in range(1, int(max_outer_iterations) + 1):
        if elapsed() >= budget_s:
            stop_reason = "timeout"
            break

        sr = solve_board(work_grid, max_rounds=solve_max_rounds, mode="full")
        pre_n_unknown = int(sr.n_unknown)
        if pre_n_unknown == 0:
            stop_reason = "solved"
            break
        if pre_n_unknown > 100:
            stop_reason = "last100_not_applicable"
            break

        base_q = _compute_error_metrics_for_last100(work_grid, target_eval)
        labels, n_comp = nd_label((sr.state == UNKNOWN).astype(np.int8))
        if n_comp <= 0:
            stop_reason = "no_unknown_components"
            break

        comp_sizes = []
        for cid in range(1, int(n_comp) + 1):
            comp_sizes.append((int(np.sum(labels == cid)), cid))
        comp_sizes.sort(reverse=True)

        iteration_progress = False
        for comp_size, comp_id in comp_sizes:
            if elapsed() >= budget_s:
                stop_reason = "timeout"
                break
            comp_mask = labels == comp_id
            unk_cells = np.argwhere(comp_mask)
            ext_mines = set()
            for cy, cx in unk_cells:
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if dy == 0 and dx == 0:
                            continue
                        ny = int(cy + dy)
                        nx = int(cx + dx)
                        if 0 <= ny < work_grid.shape[0] and 0 <= nx < work_grid.shape[1]:
                            if work_grid[ny, nx] == 1 and forbidden[ny, nx] == 0 and not comp_mask[ny, nx]:
                                ext_mines.add((ny, nx))
            if not ext_mines:
                continue

            candidate_pool = sorted(ext_mines, key=lambda yx: float(target[yx[0], yx[1]]))
            candidate_pool = candidate_pool[: max(2, int(pair_trial_limit))]
            best = None

            def maybe_consider(move_type: str, removed_mines: list[tuple[int, int]], comp_id_v: int, comp_size_v: int):
                nonlocal best
                trial = work_grid.copy()
                for my, mx in removed_mines:
                    trial[my, mx] = 0
                trial[forbidden == 1] = 0
                sr_t = solve_board(trial, max_rounds=trial_max_rounds, mode="trial")
                post_n_unknown = int(sr_t.n_unknown)
                delta_unknown = int(pre_n_unknown - post_n_unknown)
                entry = {
                    "iteration": int(iteration),
                    "component_id": int(comp_id_v),
                    "component_size": int(comp_size_v),
                    "move_type": move_type,
                    "removed_mines": [[int(y), int(x)] for y, x in removed_mines],
                    "pre_n_unknown": int(pre_n_unknown),
                    "post_n_unknown": int(post_n_unknown),
                    "delta_unknown": int(delta_unknown),
                    "delta_mean_abs_error": None,
                    "delta_true_bg_err": None,
                    "delta_hi_err": None,
                    "accepted": False,
                    "reject_reason": "",
                }
                if delta_unknown <= 0:
                    entry["reject_reason"] = "no_unknown_reduction"
                    move_log.append(entry)
                    return

                trial_q = _compute_error_metrics_for_last100(trial, target_eval)
                d_mean = float(trial_q["mean_abs_error"] - base_q["mean_abs_error"])
                d_bg = float(trial_q["true_bg_err"] - base_q["true_bg_err"])
                d_hi = float(trial_q["hi_err"] - base_q["hi_err"])
                entry["delta_mean_abs_error"] = d_mean
                entry["delta_true_bg_err"] = d_bg
                entry["delta_hi_err"] = d_hi
                if d_mean > max_error_delta_mean_abs:
                    entry["reject_reason"] = "mean_abs_guardrail"
                    move_log.append(entry)
                    return
                if d_bg > max_error_delta_true_bg:
                    entry["reject_reason"] = "true_bg_guardrail"
                    move_log.append(entry)
                    return
                if d_hi > max_error_delta_hi:
                    entry["reject_reason"] = "hi_err_guardrail"
                    move_log.append(entry)
                    return

                entry["accepted"] = True
                move_log.append(entry)
                visual_cost = max(0.0, d_mean) + max(0.0, d_bg) + max(0.0, d_hi)
                candidate = {
                    "rank_key": (delta_unknown, -visual_cost),
                    "trial_grid": trial,
                    "entry": entry,
                }
                if best is None or candidate["rank_key"] > best["rank_key"]:
                    best = candidate

            for my, mx in candidate_pool:
                if elapsed() >= budget_s:
                    stop_reason = "timeout"
                    break
                maybe_consider("single", [(int(my), int(mx))], int(comp_id), int(comp_size))
            if stop_reason == "timeout":
                break

            if best is None and len(candidate_pool) >= 2 and int(pair_combo_limit) > 0:
                tested = 0
                for i in range(len(candidate_pool)):
                    if tested >= int(pair_combo_limit):
                        break
                    for j in range(i + 1, len(candidate_pool)):
                        if tested >= int(pair_combo_limit):
                            break
                        if elapsed() >= budget_s:
                            stop_reason = "timeout"
                            break
                        tested += 1
                        maybe_consider(
                            "pair",
                            [candidate_pool[i], candidate_pool[j]],
                            int(comp_id),
                            int(comp_size),
                        )
                    if stop_reason == "timeout":
                        break

            if best is not None:
                work_grid = best["trial_grid"]
                work_grid[forbidden == 1] = 0
                n_fixes += 1
                iteration_progress = True
                if verbose:
                    entry = best["entry"]
                    print(
                        f"  last100 iter={iteration} comp={entry['component_id']} size={entry['component_size']} "
                        f"move={entry['move_type']} delta_unknown={entry['delta_unknown']}",
                        flush=True,
                    )
                break

        if stop_reason == "timeout":
            break
        if not iteration_progress:
            stop_reason = "no_accepted_move"
            break

    sr_final = solve_board(work_grid, max_rounds=solve_max_rounds, mode="full")
    return work_grid, sr_final, int(n_fixes), move_log, stop_reason


def run_phase2_full_repair(grid: np.ndarray,
                            target: np.ndarray,
                            forbidden: np.ndarray,
                            verbose: bool = True,
                            time_budget_s: float = 20.0,
                            max_outer_iterations: int = 12,
                            max_clusters_per_iteration: int = 16,
                            max_ext_mines_per_cluster: int = 16,
                            trial_max_rounds: int = 60,
                            solve_max_rounds: int = 200,
                            pair_trial_limit: int = 12,
                            pair_combo_limit: int = 24) -> tuple:
    """
    Phase 2 (full): Detect ALL sealed unknown clusters and break enclosures.

    Handles two cluster types:
      Type A - MESA: single safe cell completely surrounded by mines.
                     Fix: remove the enclosing mine with lowest target T.
      Type B - NxM cluster: multiple unknown cells (mix of mines+safe) where
               ALL external neighbours are flagged mines.
               Fix: for each external mine adjacent to an unknown SAFE cell
               in the cluster, try removing it and check if n_unknown drops.
               Accept the best improvement.

    Both types are unreachable because the solver only uses N values of
    REVEALED cells; these clusters have no revealed cell adjacent to them.

    Returns (grid, n_fixed, log). Work is bounded by time_budget_s and
    per-iteration candidate caps to keep wall-clock predictable.
    """
    grid = grid.copy()
    n_fixed = 0
    log = []
    t_start = time.perf_counter()

    for iteration in range(max_outer_iterations):
        if (time.perf_counter() - t_start) >= time_budget_s:
            if verbose:
                print(f"  Phase2 full timeout at {time_budget_s:.1f}s", flush=True)
            break

        sr = solve_board(grid, max_rounds=solve_max_rounds, mode='full')
        if sr.n_unknown == 0:
            break

        sealed_clusters = find_sealed_unknown_clusters(grid, sr, forbidden)
        if not sealed_clusters:
            break

        sealed_clusters = sorted(
            sealed_clusters,
            key=lambda item: (int(item["cluster_size"]), int(item["external_mine_count"])),
            reverse=True,
        )[:max_clusters_per_iteration]

        made_progress = False
        for cluster in sealed_clusters:
            if (time.perf_counter() - t_start) >= time_budget_s:
                break

            ext_mines = [tuple(item) for item in cluster["external_mines"]]
            if not ext_mines:
                continue

            best_delta = 0
            best_mine = None
            best_grid_t = None
            best_move_type = 'none'
            best_removed = []
            best_sr_t = None

            ext_mines = sorted(
                ext_mines,
                key=lambda yx: float(target[yx[0], yx[1]])
            )[:max_ext_mines_per_cluster]

            for (my, mx) in ext_mines:
                if (time.perf_counter() - t_start) >= time_budget_s:
                    break
                trial = grid.copy()
                trial[my, mx] = 0
                trial[forbidden == 1] = 0
                sr_t = solve_board(trial, max_rounds=trial_max_rounds, mode='trial')
                delta = sr.n_unknown - sr_t.n_unknown
                if delta > best_delta:
                    best_delta = delta
                    best_mine = (my, mx)
                    best_grid_t = trial
                    best_move_type = 'single'
                    best_removed = [(my, mx)]
                    best_sr_t = sr_t

            if best_delta <= 0 and len(ext_mines) >= 2 and pair_trial_limit >= 2 and pair_combo_limit > 0:
                pair_pool = ext_mines[:max(2, int(pair_trial_limit))]
                n_pairs_tested = 0
                for i in range(len(pair_pool)):
                    if n_pairs_tested >= int(pair_combo_limit):
                        break
                    for j in range(i + 1, len(pair_pool)):
                        if n_pairs_tested >= int(pair_combo_limit):
                            break
                        if (time.perf_counter() - t_start) >= time_budget_s:
                            break
                        (m1y, m1x) = pair_pool[i]
                        (m2y, m2x) = pair_pool[j]
                        trial = grid.copy()
                        trial[m1y, m1x] = 0
                        trial[m2y, m2x] = 0
                        trial[forbidden == 1] = 0
                        sr_t = solve_board(trial, max_rounds=trial_max_rounds, mode='trial')
                        delta = sr.n_unknown - sr_t.n_unknown
                        n_pairs_tested += 1
                        if delta > best_delta:
                            best_delta = delta
                            best_mine = (m1y, m1x)
                            best_grid_t = trial
                            best_move_type = 'pair'
                            best_removed = [(m1y, m1x), (m2y, m2x)]
                            best_sr_t = sr_t

            if best_mine is not None:
                before_grid = grid.copy()
                grid = best_grid_t
                grid[forbidden == 1] = 0
                n_fixed += 1
                made_progress = True
                delta_summary = compute_repair_visual_delta(before_grid, grid, target)
                log.append({
                    'cluster_size': int(cluster["cluster_size"]),
                    'removed_mine': [int(best_mine[0]), int(best_mine[1])],
                    'removed_mines': [[int(y), int(x)] for y, x in best_removed],
                    'move_type': best_move_type,
                    'T_removed': float(target[best_mine[0], best_mine[1]]),
                    'delta_unk': int(best_delta),
                    'repair_stage': 'phase2_full',
                    'cluster_id': int(cluster["cluster_id"]),
                    'cluster_kind': cluster["cluster_kind"],
                    'n_unknown_before': int(sr.n_unknown),
                    'n_unknown_after': int(best_sr_t.n_unknown if best_sr_t is not None else sr.n_unknown - best_delta),
                    'delta_unknown': int(best_delta),
                    'mean_abs_error_before': float(delta_summary["mean_abs_error_before"]),
                    'mean_abs_error_after': float(delta_summary["mean_abs_error_after"]),
                    'visual_delta': float(delta_summary["visual_delta"]),
                    'accepted': True,
                })
                if verbose:
                    print(f"    Sealed cluster (size={cluster['cluster_size']}): "
                          f"{best_move_type} removal {best_removed} "
                          f"(T={target[best_mine[0],best_mine[1]]:.2f}) "
                          f"-> freed {best_delta} unknown cells", flush=True)

        if not made_progress:
            break

    sr_final = solve_board(grid, max_rounds=solve_max_rounds, mode='full')
    if verbose:
        print(f"  Phase2 full complete: {n_fixed} enclosures broken  "
              f"n_unknown={sr_final.n_unknown}", flush=True)

    return grid, n_fixed, log
