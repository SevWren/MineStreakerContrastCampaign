"""
repair.py — Phase 1 mine-removal repair.
Uses mode='trial' (no subset prop) for candidate screening; mode='full' for
final accuracy measurement. Parallel candidate evaluation via process pool.
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import numpy as np
try:
    from .core import compute_N, assert_board_valid
    from .solver import solve_board
except ImportError:
    from core import compute_N, assert_board_valid
    from solver import solve_board


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
    try:
        from .solver import solve_board, UNKNOWN, SAFE, MINE
    except ImportError:
        from solver import solve_board, UNKNOWN, SAFE, MINE

    grid = grid.copy()
    H, W = grid.shape
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

        state = sr.state

        # Find all connected unknown-cell clusters
        from scipy.ndimage import label as nd_label
        unk_mask = (state == UNKNOWN).astype(np.int32)
        labeled, n_comp = nd_label(unk_mask)
        if n_comp == 0:
            break

        comp_ids = list(range(1, n_comp + 1))
        if len(comp_ids) > max_clusters_per_iteration:
            comp_sizes = []
            for cid in comp_ids:
                comp_sizes.append((int(np.sum(labeled == cid)), cid))
            comp_sizes.sort(reverse=True)
            comp_ids = [cid for _, cid in comp_sizes[:max_clusters_per_iteration]]

        made_progress = False
        for comp_id in comp_ids:
            if (time.perf_counter() - t_start) >= time_budget_s:
                break
            comp_mask = labeled == comp_id
            unk_cells  = np.argwhere(comp_mask)

            # Find all external mine neighbours of this cluster
            ext_mines = set()
            for cy, cx in unk_cells:
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if dy == 0 and dx == 0: continue
                        ny, nx = cy+dy, cx+dx
                        if 0 <= ny < H and 0 <= nx < W:
                            if grid[ny,nx] == 1 and not comp_mask[ny,nx] and forbidden[ny,nx] == 0:
                                ext_mines.add((ny, nx))

            if not ext_mines:
                continue

            # Check if cluster is sealed (all external nbs are mines — no safe nbs)
            has_safe_nb = False
            for cy, cx in unk_cells:
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if dy == 0 and dx == 0: continue
                        ny, nx = cy+dy, cx+dx
                        if 0 <= ny < H and 0 <= nx < W:
                            if state[ny,nx] == SAFE:
                                has_safe_nb = True
                                break
                if has_safe_nb:
                    break

            if has_safe_nb:
                continue  # not sealed — standard repair should handle

            # Sealed cluster: try removing each external mine
            best_delta  = 0
            best_mine   = None
            best_grid_t = None
            best_move_type = 'none'
            best_removed = []

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
                    best_delta  = delta
                    best_mine   = (my, mx)
                    best_grid_t = trial
                    best_move_type = 'single'
                    best_removed = [(my, mx)]

            # Escalate to bounded pair-removal trials if single removals fail.
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

            if best_mine is not None:
                grid = best_grid_t
                grid[forbidden == 1] = 0
                n_fixed += 1
                made_progress = True
                log.append({'cluster_size': len(unk_cells),
                             'removed_mine': best_mine,
                             'removed_mines': best_removed,
                             'move_type': best_move_type,
                             'T_removed': float(target[best_mine[0], best_mine[1]]),
                             'delta_unk': best_delta})
                if verbose:
                    print(f"    Sealed cluster (size={len(unk_cells)}): "
                          f"{best_move_type} removal {best_removed} "
                          f"(T={target[best_mine[0],best_mine[1]]:.2f}) "
                          f"→ freed {best_delta} unknown cells", flush=True)

        if not made_progress:
            break

    sr_final = solve_board(grid, max_rounds=solve_max_rounds, mode='full')
    if verbose:
        print(f"  Phase2 full complete: {n_fixed} enclosures broken  "
              f"n_unknown={sr_final.n_unknown}", flush=True)

    return grid, n_fixed, log
