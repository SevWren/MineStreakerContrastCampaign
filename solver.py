"""
solver.py — Numba-compiled deterministic CSP solver (frontier-tracked).

Key optimizations:
  1. Pre-computed neighbor table int32[H*W, 8]
  2. Single monolithic @njit function — zero Python overhead per round
  3. Dirty-queue frontier: only re-examine cells near recent changes
  4. Spatially-local subset: O(n_front × 25) not O(n_front²)
  5. No nested functions (Numba closure restriction avoided)

subset_cap = 2400 unconditional per spec.
"""

import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from numba import njit

try:
    from .core import compute_N as _compute_N
except ImportError:
    from core import compute_N as _compute_N

UNKNOWN = np.int8(0)
SAFE    = np.int8(1)
MINE    = np.int8(2)

subset_cap = 2400


@dataclass
class SolveResult:
    coverage:      float = 0.0
    solvable:      bool  = False
    mine_accuracy: float = 0.0
    n_revealed:    int   = 0
    n_safe:        int   = 0
    n_mines:       int   = 0
    n_unknown:     int   = 0
    state:         Optional[np.ndarray] = field(default=None, repr=False)
    rounds:        int   = 0


def build_neighbor_table(H: int, W: int) -> np.ndarray:
    nb = np.full((H * W, 8), -1, dtype=np.int32)
    for y in range(H):
        for x in range(W):
            idx = y * W + x; k = 0
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dy == 0 and dx == 0: continue
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < H and 0 <= nx < W:
                        nb[idx, k] = ny * W + nx; k += 1
    return np.ascontiguousarray(nb, dtype=np.int32)

_NB_CACHE: dict = {}
def get_neighbor_table(H: int, W: int) -> np.ndarray:
    key = (H, W)
    if key not in _NB_CACHE:
        _NB_CACHE[key] = build_neighbor_table(H, W)
    return _NB_CACHE[key]


def _as_contig_int8_2d(arr: np.ndarray) -> np.ndarray:
    if arr.dtype == np.int8 and arr.flags.c_contiguous:
        return arr
    return np.ascontiguousarray(arr, dtype=np.int8)


@njit(cache=True, fastmath=True)
def _numba_solve(grid_f, N_f, nb, n_cells, W, max_rounds, use_subset, cap):
    """
    Full deterministic solver.  No nested functions — Numba compatible.
    state: 0=UNKNOWN 1=SAFE 2=MINE
    """
    state   = np.zeros(n_cells, dtype=np.int8)
    # Dirty queue — SAFE cells whose neighbourhood changed
    in_dirty = np.zeros(n_cells, dtype=np.uint8)
    dirty_q  = np.empty(n_cells, dtype=np.int32)
    dh = np.int32(0)
    dt = np.int32(0)
    # Flood queue
    flood_q = np.empty(n_cells, dtype=np.int32)
    fh = np.int32(0)
    ft = np.int32(0)
    H = n_cells // W

    # ── Seed flood ────────────────────────────────────────────────────────
    for i in range(n_cells):
        if grid_f[i] == np.int8(0) and N_f[i] == np.uint8(0):
            state[i] = np.int8(1)
            flood_q[ft] = i; ft += 1

    while fh < ft:
        i = flood_q[fh]; fh += 1
        if in_dirty[i] == np.uint8(0):
            in_dirty[i] = np.uint8(1); dirty_q[dt] = i; dt += 1
        for k in range(8):
            j = nb[i, k]
            if j < 0: break
            if state[j] == np.int8(0) and grid_f[j] == np.int8(0):
                state[j] = np.int8(1)
                flood_q[ft] = j; ft += 1
                if in_dirty[j] == np.uint8(0):
                    in_dirty[j] = np.uint8(1); dirty_q[dt] = j; dt += 1

    rounds = np.int32(0)

    while rounds < max_rounds and dh < dt:
        rounds += 1
        prev_dt = dt

        # ── Basic propagation over dirty frontier ─────────────────────────
        for qi in range(dh, prev_dt):
            i = dirty_q[qi]
            in_dirty[i] = np.uint8(0)
            if state[i] != np.int8(1): continue

            n_unk  = np.int32(0)
            n_flag = np.int32(0)
            for k in range(8):
                j = nb[i, k]
                if j < 0: break
                s = state[j]
                if   s == np.int8(0): n_unk  += 1
                elif s == np.int8(2): n_flag += 1
            if n_unk == 0: continue

            rem = np.int32(N_f[i]) - n_flag
            if rem < 0: rem = np.int32(0)

            if rem == n_unk:
                # Flag all unknowns
                for k in range(8):
                    j = nb[i, k]
                    if j < 0: break
                    if state[j] == np.int8(0):
                        state[j] = np.int8(2)
                        # Mark SAFE neighbours of j as dirty
                        for k2 in range(8):
                            jj = nb[j, k2]
                            if jj < 0: break
                            if state[jj] == np.int8(1) and in_dirty[jj] == np.uint8(0):
                                in_dirty[jj] = np.uint8(1); dirty_q[dt] = jj; dt += 1
            elif rem == 0:
                # Reveal all unknowns
                for k in range(8):
                    j = nb[i, k]
                    if j < 0: break
                    if state[j] == np.int8(0) and grid_f[j] == np.int8(0):
                        state[j] = np.int8(1)
                        if N_f[j] == np.uint8(0):
                            flood_q[ft] = j; ft += 1
                            # Drain flood inline
                            while fh < ft:
                                ii = flood_q[fh]; fh += 1
                                if in_dirty[ii] == np.uint8(0):
                                    in_dirty[ii] = np.uint8(1); dirty_q[dt] = ii; dt += 1
                                for k3 in range(8):
                                    jj = nb[ii, k3]
                                    if jj < 0: break
                                    if state[jj] == np.int8(0) and grid_f[jj] == np.int8(0):
                                        state[jj] = np.int8(1)
                                        flood_q[ft] = jj; ft += 1
                                        if in_dirty[jj] == np.uint8(0):
                                            in_dirty[jj] = np.uint8(1); dirty_q[dt] = jj; dt += 1
                        else:
                            if in_dirty[j] == np.uint8(0):
                                in_dirty[j] = np.uint8(1); dirty_q[dt] = j; dt += 1
                        if in_dirty[i] == np.uint8(0):
                            in_dirty[i] = np.uint8(1); dirty_q[dt] = i; dt += 1

        dh = prev_dt

        # ── Subset propagation ─────────────────────────────────────────────
        if not use_subset:
            continue

        # Collect frontier
        front = np.empty(cap, dtype=np.int32)
        front_n  = np.int32(0)
        for i in range(n_cells):
            if state[i] != np.int8(1): continue
            has_unk = False
            for k in range(8):
                j = nb[i, k]
                if j < 0: break
                if state[j] == np.int8(0): has_unk = True; break
            if has_unk:
                front[front_n] = i; front_n += 1
                if front_n >= cap: break

        if front_n < 2: continue

        # Build constraint arrays
        c_cells = np.full((front_n, 8), np.int32(-1), dtype=np.int32)
        c_size = np.zeros(front_n, dtype=np.int32)
        c_rem = np.zeros(front_n, dtype=np.int32)
        for fi in range(front_n):
            i = front[fi]
            n_flag = np.int32(0); k2 = np.int32(0)
            for k in range(8):
                j = nb[i, k]
                if j < 0: break
                if   state[j] == np.int8(2): n_flag += 1
                elif state[j] == np.int8(0): c_cells[fi, k2] = j; k2 += 1
            rem = np.int32(N_f[i]) - n_flag
            if rem < 0: rem = np.int32(0)
            for a in range(k2 - 1):
                for b in range(a + 1, k2):
                    if c_cells[fi, b] < c_cells[fi, a]:
                        tmp = c_cells[fi, a]; c_cells[fi, a] = c_cells[fi, b]; c_cells[fi, b] = tmp
            c_size[fi] = k2; c_rem[fi] = rem

        # cell → front index
        cell_to_fi = np.full(n_cells, np.int32(-1), dtype=np.int32)
        for fi in range(front_n):
            cell_to_fi[front[fi]] = fi

        # Spatially-local comparisons
        sub_changed = False
        for fi in range(front_n):
            sA = c_size[fi]
            if sA == 0: continue
            rA = c_rem[fi]
            src_i = front[fi]
            yi = src_i // W; xi = src_i % W

            for dy in range(-2, 3):
                ny2 = yi + dy
                if ny2 < 0 or ny2 >= H: continue
                for dx in range(-2, 3):
                    nx2 = xi + dx
                    if nx2 < 0 or nx2 >= W: continue
                    src_j = ny2 * W + nx2
                    fj = cell_to_fi[src_j]
                    if fj <= fi: continue
                    sB = c_size[fj]
                    if sB == 0: continue
                    rB = c_rem[fj]

                    # A ⊆ B ?
                    if sA < sB:
                        ia = np.int32(0); ib = np.int32(0)
                        while ia < sA and ib < sB:
                            if   c_cells[fi,ia] == c_cells[fj,ib]: ia += 1; ib += 1
                            elif c_cells[fi,ia] >  c_cells[fj,ib]: ib += 1
                            else: break
                        if ia == sA:
                            rdiff = rB - rA
                            if rdiff == sB - sA:
                                for kb in range(sB):
                                    v = c_cells[fj,kb]; 
                                    if v < 0: break
                                    in_a = False
                                    for ka in range(sA):
                                        if c_cells[fi,ka] == v: in_a = True; break
                                    if not in_a and state[v] == np.int8(0):
                                        state[v] = np.int8(2); sub_changed = True
                                        for k2 in range(8):
                                            jj = nb[v,k2]
                                            if jj < 0: break
                                            if state[jj] == np.int8(1) and in_dirty[jj] == np.uint8(0):
                                                in_dirty[jj] = np.uint8(1); dirty_q[dt] = jj; dt += 1
                            elif rdiff == 0:
                                for kb in range(sB):
                                    v = c_cells[fj,kb]
                                    if v < 0: break
                                    in_a = False
                                    for ka in range(sA):
                                        if c_cells[fi,ka] == v: in_a = True; break
                                    if not in_a and state[v] == np.int8(0) and grid_f[v] == np.int8(0):
                                        state[v] = np.int8(1); sub_changed = True
                                        if N_f[v] == np.uint8(0): flood_q[ft] = v; ft += 1
                                        elif in_dirty[v] == np.uint8(0):
                                            in_dirty[v] = np.uint8(1); dirty_q[dt] = v; dt += 1

                    # B ⊆ A ?
                    elif sB < sA:
                        ib = np.int32(0); ia = np.int32(0)
                        while ib < sB and ia < sA:
                            if   c_cells[fj,ib] == c_cells[fi,ia]: ib += 1; ia += 1
                            elif c_cells[fj,ib] >  c_cells[fi,ia]: ia += 1
                            else: break
                        if ib == sB:
                            rdiff = rA - rB
                            if rdiff == sA - sB:
                                for ka in range(sA):
                                    v = c_cells[fi,ka]
                                    if v < 0: break
                                    in_b = False
                                    for kb in range(sB):
                                        if c_cells[fj,kb] == v: in_b = True; break
                                    if not in_b and state[v] == np.int8(0):
                                        state[v] = np.int8(2); sub_changed = True
                                        for k2 in range(8):
                                            jj = nb[v,k2]
                                            if jj < 0: break
                                            if state[jj] == np.int8(1) and in_dirty[jj] == np.uint8(0):
                                                in_dirty[jj] = np.uint8(1); dirty_q[dt] = jj; dt += 1
                            elif rdiff == 0:
                                for ka in range(sA):
                                    v = c_cells[fi,ka]
                                    if v < 0: break
                                    in_b = False
                                    for kb in range(sB):
                                        if c_cells[fj,kb] == v: in_b = True; break
                                    if not in_b and state[v] == np.int8(0) and grid_f[v] == np.int8(0):
                                        state[v] = np.int8(1); sub_changed = True
                                        if N_f[v] == np.uint8(0): flood_q[ft] = v; ft += 1
                                        elif in_dirty[v] == np.uint8(0):
                                            in_dirty[v] = np.uint8(1); dirty_q[dt] = v; dt += 1

        # Drain flood from subset reveals
        if sub_changed:
            while fh < ft:
                ii = flood_q[fh]; fh += 1
                if in_dirty[ii] == np.uint8(0):
                    in_dirty[ii] = np.uint8(1); dirty_q[dt] = ii; dt += 1
                for k3 in range(8):
                    jj = nb[ii, k3]
                    if jj < 0: break
                    if state[jj] == np.int8(0) and grid_f[jj] == np.int8(0):
                        state[jj] = np.int8(1)
                        flood_q[ft] = jj; ft += 1
                        if in_dirty[jj] == np.uint8(0):
                            in_dirty[jj] = np.uint8(1); dirty_q[dt] = jj; dt += 1

    return state, rounds


@njit(cache=True, fastmath=True)
def _summarize_state(grid_f: np.ndarray, state_f: np.ndarray):
    n_safe = np.int32(0)
    n_mines_g = np.int32(0)
    n_revealed = np.int32(0)
    n_flagged = np.int32(0)
    n_unknown = np.int32(0)
    correct_flags = np.int32(0)

    n_cells = grid_f.size
    for i in range(n_cells):
        g = grid_f[i]
        s = state_f[i]
        if g == np.int8(0):
            n_safe += 1
        elif g == np.int8(1):
            n_mines_g += 1
        if s == np.int8(1) and g == np.int8(0):
            n_revealed += 1
        elif s == np.int8(2):
            n_flagged += 1
            if g == np.int8(1):
                correct_flags += 1
        elif s == np.int8(0):
            n_unknown += 1
    return n_safe, n_mines_g, n_revealed, n_flagged, n_unknown, correct_flags


def _warmup():
    H, W = 12, 12; n = H * W
    nb = np.ascontiguousarray(build_neighbor_table(H, W))
    gf = np.zeros(n, dtype=np.int8); gf[27]=1; gf[55]=1
    Nf = np.zeros(n, dtype=np.uint8)
    for i in range(n):
        y, x = divmod(i, W)
        for dy in range(-1,2):
            for dx in range(-1,2):
                if dy==0 and dx==0: continue
                ny,nx=y+dy,x+dx
                if 0<=ny<H and 0<=nx<W: Nf[i]+=gf[ny*W+nx]
    _numba_solve(gf, Nf, nb, np.int32(n), np.int32(W), np.int32(50),
                 np.uint8(1), np.int32(100))
    print("  Solver kernel warmed up (frontier+local-subset)", flush=True)

_warmed = False
def ensure_solver_warmed():
    global _warmed
    if not _warmed:
        print("  Compiling solver kernel…", flush=True)
        _warmup()
        _warmed = True


def solve_board(grid: np.ndarray,
                max_rounds: int = 300,
                deadline_s: Optional[float] = None,
                mode: str = 'full',
                deterministic: bool = False) -> SolveResult:
    ensure_solver_warmed()
    H, W = grid.shape
    n_cells = np.int32(H * W)
    nb = get_neighbor_table(H, W)
    grid_2d = _as_contig_int8_2d(grid)
    grid_f = grid_2d.ravel()
    Nf_2d = _compute_N(grid_2d)
    N_f = np.ascontiguousarray(Nf_2d.ravel(), dtype=np.uint8)
    use_subset = np.uint8(1 if mode == 'full' else 0)
    cap = np.int32(subset_cap)

    state_f, rounds = _numba_solve(
        grid_f, N_f, nb, n_cells, np.int32(W),
        np.int32(max_rounds), use_subset, cap)

    n_safe, n_mines_g, n_revealed, n_flagged, n_unknown, correct_flags = _summarize_state(grid_f, state_f)
    n_safe = int(n_safe)
    n_mines_g = int(n_mines_g)
    n_revealed = int(n_revealed)
    n_flagged = int(n_flagged)
    n_unknown = int(n_unknown)
    correct_flags = int(correct_flags)
    coverage   = n_revealed / max(n_safe, 1)

    mine_accuracy = 1.0
    if n_flagged > 0:
        mine_accuracy = correct_flags / n_flagged

    solvable = (coverage >= 0.999 and mine_accuracy >= 0.999)
    state_out = state_f.reshape(H, W)
    return SolveResult(
        coverage=coverage, solvable=solvable, mine_accuracy=mine_accuracy,
        n_revealed=n_revealed, n_safe=n_safe, n_mines=n_mines_g,
        n_unknown=n_unknown, state=state_out, rounds=int(rounds),
    )
