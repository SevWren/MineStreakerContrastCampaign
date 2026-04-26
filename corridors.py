"""
corridors.py — MST-based adaptive mine-free corridors.
Routes prefer dark (low-target) regions so corridors are visually hidden.
"""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import minimum_spanning_tree
from scipy.ndimage import distance_transform_edt, label as nd_label


def build_adaptive_corridors(target: np.ndarray,
                              border: int = 3,
                              corridor_width: int = 0,
                              low_target_bias: float = 5.5):
    """
    1. Create seed nodes on a grid spaced ~sqrt(H*W)//10 apart.
    2. Edge weight = mean target along straight path ** low_target_bias
       (routes through dark/low regions → less visual disruption).
    3. Compute MST, burn edges into forbidden mask.
    4. Add border cells to forbidden mask.

    Returns:
        forbidden    : int8 (H, W) — 1 = mine-free required
        coverage_pct : float — % of cells that are forbidden
        seeds        : list of (row, col)
        mst          : scipy coo_matrix
    """
    H, W = target.shape
    spacing = max(5, int(np.sqrt(H * W)) // 10)

    # Build seed grid
    rows = list(range(border + spacing // 2, H - border, spacing))
    cols = list(range(border + spacing // 2, W - border, spacing))
    seeds = [(r, c) for r in rows for c in cols]
    n = len(seeds)

    if n < 2:
        # Fallback: just border
        forbidden = np.zeros((H, W), dtype=np.int8)
        forbidden[:border, :] = 1
        forbidden[-border:, :] = 1
        forbidden[:, :border] = 1
        forbidden[:, -border:] = 1
        return forbidden, float(forbidden.mean() * 100), seeds, None

    # Build full edge weight matrix (sparse upper triangle)
    src_list, dst_list, w_list = [], [], []
    for i in range(n):
        for j in range(i + 1, n):
            r0, c0 = seeds[i]
            r1, c1 = seeds[j]
            # Sample along straight line
            steps = max(abs(r1 - r0), abs(c1 - c0), 1)
            rs = np.round(np.linspace(r0, r1, steps + 1)).astype(int)
            cs = np.round(np.linspace(c0, c1, steps + 1)).astype(int)
            rs = np.clip(rs, 0, H - 1)
            cs = np.clip(cs, 0, W - 1)
            mean_val = float(target[rs, cs].mean())
            # Low-target (dark) bias: prefer dark paths
            w = (mean_val + 0.1) ** low_target_bias
            src_list.append(i); dst_list.append(j); w_list.append(w)

    graph = coo_matrix((w_list, (src_list, dst_list)), shape=(n, n))
    mst = minimum_spanning_tree(graph.tocsr())

    # Burn MST edges into forbidden mask
    forbidden = np.zeros((H, W), dtype=np.int8)
    cx_mst = mst.tocoo()
    hw = max(0, corridor_width)
    for i, j in zip(cx_mst.row, cx_mst.col):
        r0, c0 = seeds[i]
        r1, c1 = seeds[j]
        steps = max(abs(r1 - r0), abs(c1 - c0), 1)
        rs = np.round(np.linspace(r0, r1, steps + 1)).astype(int)
        cs = np.round(np.linspace(c0, c1, steps + 1)).astype(int)
        rs = np.clip(rs, border, H - border - 1)
        cs = np.clip(cs, border, W - border - 1)
        forbidden[rs, cs] = 1
        # Optional width expansion
        for dw in range(-hw, hw + 1):
            rr = np.clip(rs + dw, border, H - border - 1)
            cc = np.clip(cs + dw, border, W - border - 1)
            forbidden[rr, cs] = 1
            forbidden[rs, cc] = 1

    # Add border
    forbidden[:border, :] = 1
    forbidden[-border:, :] = 1
    forbidden[:, :border] = 1
    forbidden[:, -border:] = 1

    coverage_pct = float(forbidden.mean() * 100)
    return forbidden, coverage_pct, seeds, mst


def analyze_corridor_access_to_unknowns(forbidden: np.ndarray, sr) -> dict:
    """
    Measure whether unresolved clusters are near corridor paths.
    """
    try:
        from .solver import SAFE, UNKNOWN
    except ImportError:
        from solver import SAFE, UNKNOWN

    if sr is None or sr.state is None:
        return {
            "unknown_cells": int(getattr(sr, "n_unknown", 0) or 0),
            "unknown_clusters_touching_corridor": 0,
            "mean_distance_unknown_to_corridor": None,
            "sealed_clusters_isolated_from_corridor": 0,
        }

    unknown_mask = sr.state == UNKNOWN
    unknown_cells = int(np.sum(unknown_mask))
    if unknown_cells == 0:
        return {
            "unknown_cells": 0,
            "unknown_clusters_touching_corridor": 0,
            "mean_distance_unknown_to_corridor": None,
            "sealed_clusters_isolated_from_corridor": 0,
        }

    labels, n_comp = nd_label(unknown_mask.astype(np.int8))
    corridor_mask = forbidden == 1
    dist = distance_transform_edt(~corridor_mask)

    touching = 0
    isolated = 0
    for cid in range(1, int(n_comp) + 1):
        comp_mask = labels == cid
        if np.any(corridor_mask & comp_mask):
            touching += 1
        has_safe_neighbor = False
        coords = np.argwhere(comp_mask)
        for cy, cx in coords:
            for dy in range(-1, 2):
                for dx in range(-1, 2):
                    if dy == 0 and dx == 0:
                        continue
                    ny = int(cy + dy)
                    nx = int(cx + dx)
                    if 0 <= ny < sr.state.shape[0] and 0 <= nx < sr.state.shape[1]:
                        if sr.state[ny, nx] == SAFE:
                            has_safe_neighbor = True
                            break
                if has_safe_neighbor:
                    break
            if has_safe_neighbor:
                break
        if not has_safe_neighbor and not np.any(corridor_mask & comp_mask):
            isolated += 1

    return {
        "unknown_cells": unknown_cells,
        "unknown_clusters_touching_corridor": int(touching),
        "mean_distance_unknown_to_corridor": float(dist[unknown_mask].mean()) if unknown_cells else None,
        "sealed_clusters_isolated_from_corridor": int(isolated),
    }
