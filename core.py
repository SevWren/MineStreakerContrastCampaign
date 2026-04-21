"""
core.py — Math primitives.  Iter 2: asymmetric target-aware loss weights.

Key fix: asymmetric weights are NOT normalised to mean=1.
Normalisation destroyed the asymmetry (bg cells dominated by cell count,
so normalising pushed bg weight BELOW 1, the opposite of intent).
Instead weights use raw values — bg cells get weight ~8, hi-target ~12.
The SA loss scale changes but the relative gradient is correct.
"""
import numpy as np
from scipy.ndimage import convolve, gaussian_filter, sobel
from PIL import Image, ImageEnhance

_KERNEL = np.array([[1,1,1],[1,0,1],[1,1,1]], dtype=np.int32)


def _as_binary_u8_contig(grid: np.ndarray) -> np.ndarray:
    if grid.dtype == np.uint8 and grid.flags.c_contiguous:
        return grid
    if grid.dtype == np.int8 and grid.flags.c_contiguous:
        return grid.view(np.uint8)
    if grid.dtype == np.bool_ and grid.flags.c_contiguous:
        return grid.view(np.uint8)
    return np.ascontiguousarray(grid, dtype=np.uint8)


def compute_N(grid: np.ndarray) -> np.ndarray:
    g = _as_binary_u8_contig(grid)
    return convolve(g, _KERNEL, mode='constant', cval=0).astype(np.uint8, copy=False)


def load_image_smart(path: str, board_w: int, board_h: int,
                     invert: bool = True,
                     contrast_factor: float = 2.0) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    if contrast_factor != 1.0:
        img = ImageEnhance.Contrast(img).enhance(float(contrast_factor))
    img = img.resize((board_w, board_h), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32)
    gray = 0.2989*arr[:,:,0] + 0.5870*arr[:,:,1] + 0.1140*arr[:,:,2]
    if invert:
        gray = 255.0 - gray
    p2, p98 = np.percentile(gray, 2), np.percentile(gray, 98)
    if p98 > p2:
        gray = (gray - p2) / (p98 - p2) * 8.0
    else:
        gray = np.zeros_like(gray)
    return np.ascontiguousarray(np.clip(gray, 0.0, 8.0), dtype=np.float32)


def compute_edge_weights(target: np.ndarray,
                         boost: float = 4.0,
                         sigma: float = 1.0) -> np.ndarray:
    """Iter 1 baseline weights — retained for compatibility."""
    blurred = gaussian_filter(target.astype(np.float32), sigma=sigma)
    sx = sobel(blurred, axis=1); sy = sobel(blurred, axis=0)
    mag = np.hypot(sx, sy).astype(np.float32)
    mx = mag.max()
    if mx > 0: mag /= mx
    return np.ascontiguousarray((1.0 + boost * mag).astype(np.float32))


def compute_asymmetric_weights(target: np.ndarray,
                                bg_penalty: float = 6.0,
                                hi_boost: float = 8.0,
                                hi_threshold: float = 3.0,
                                edge_sigma: float = 1.0,
                                edge_boost: float = 2.0) -> np.ndarray:
    """
    Iter 2: asymmetric target-aware weights.  NOT normalised to mean=1.

    Weight formula:
      base(y,x)   = 1 + edge_boost * sobel_magnitude(y,x)    [1 .. 3 typical]
      region(y,x):
        T < 1.0              → bg_penalty                     [×6]
        T >= hi_threshold    → hi_boost                       [×8]
        1 ≤ T < hi_thresh    → linear blend 1 → hi_boost
      w(y,x) = base * region   (raw, not normalised)

    Effect on SA gradient:
      - SA flip cost for a mine placed in background: ~8× higher than iter1
      - SA flip cost for correcting a line cell: ~12× higher than iter1
      → drives density away from background and towards line cells
    """
    target = target.astype(np.float32)
    H, W = target.shape

    blurred = gaussian_filter(target, sigma=edge_sigma)
    sx = sobel(blurred, axis=1); sy = sobel(blurred, axis=0)
    mag = np.hypot(sx, sy).astype(np.float32)
    mx = mag.max()
    if mx > 0: mag /= mx
    base = (1.0 + edge_boost * mag).astype(np.float32)

    region = np.ones((H, W), dtype=np.float32)
    bg_mask  = target < 1.0
    hi_mask  = target >= hi_threshold
    mid_mask = ~bg_mask & ~hi_mask

    region[bg_mask] = bg_penalty
    region[hi_mask] = hi_boost
    if mid_mask.any():
        t_mid = target[mid_mask]
        alpha = (t_mid - 1.0) / max(hi_threshold - 1.0, 1e-6)
        region[mid_mask] = 1.0 + alpha * (hi_boost - 1.0)

    weights = (base * region).astype(np.float32)
    return np.ascontiguousarray(weights, dtype=np.float32)


def assert_board_valid(grid: np.ndarray,
                       forbidden: np.ndarray,
                       label: str = '') -> None:
    tag = f"[{label}] " if label else ""
    uvals = np.unique(grid)
    bad = [v for v in uvals if v not in (0, 1)]
    assert not bad, f"{tag}Grid non-binary: {bad}"
    n_mines_forb = int(np.sum((grid == 1) & (forbidden == 1)))
    assert n_mines_forb == 0, f"{tag}{n_mines_forb} mines in forbidden cells"
    N = compute_N(grid)
    assert N.min() >= 0 and N.max() <= 8, f"{tag}N out of range [{N.min()},{N.max()}]"


def compute_zone_aware_weights(target: np.ndarray,
                                bp_true: float   = 8.0,
                                bp_trans: float  = 0.5,
                                hi_boost: float  = 15.0,
                                hi_threshold: float = 3.0,
                                edge_sigma: float   = 1.0,
                                edge_boost: float   = 2.0) -> np.ndarray:
    """
    Iter 3: zone-aware loss weights.

    Three zones:
      true_bg   : T < 1.0  AND no hi-T neighbour — penalise heavily (bp_true)
      trans_bg  : T < 1.0  AND adjacent to hi-T  — accept contamination (bp_trans)
      hi-target : T >= hi_threshold               — strong pull (hi_boost)
      mid       : linear blend 1→hi_boost

    Key insight: transition zone contamination is geometrically irreducible —
    93% of hi-target cells are adjacent to background. Using a high bg_penalty
    on transition cells wastes gradient budget. Zero/low penalty there frees
    the SA to improve line accuracy and true-background cleanliness together.
    """
    from scipy.ndimage import convolve as _convolve
    target = target.astype(np.float32)
    H, W = target.shape

    hi_mask  = target >= hi_threshold
    bg_mask  = target <  1.0
    K8 = np.ones((3, 3), dtype=np.int32); K8[1, 1] = 0

    # Identify cells adjacent to hi-target (transition zone)
    adj_to_hi  = _convolve(hi_mask.astype(np.int32), K8, mode='constant', cval=0) > 0
    trans_mask = bg_mask & adj_to_hi
    true_bg    = bg_mask & ~trans_mask

    blurred = gaussian_filter(target, sigma=edge_sigma)
    sx = sobel(blurred, axis=1); sy = sobel(blurred, axis=0)
    mag = np.hypot(sx, sy).astype(np.float32)
    mx = mag.max()
    if mx > 0: mag /= mx
    base = (1.0 + edge_boost * mag).astype(np.float32)

    region = np.ones((H, W), dtype=np.float32)
    region[true_bg]    = bp_true
    region[trans_mask] = bp_trans
    region[hi_mask]    = hi_boost
    mid_mask = ~bg_mask & ~hi_mask
    if mid_mask.any():
        alpha = (target[mid_mask] - 1.0) / max(hi_threshold - 1.0, 1e-6)
        region[mid_mask] = 1.0 + alpha * (hi_boost - 1.0)

    weights = (base * region).astype(np.float32)
    return np.ascontiguousarray(weights, dtype=np.float32)


def compute_cluster_break_weights(base_weights: np.ndarray,
                                   N_current: np.ndarray,
                                   target: np.ndarray,
                                   cluster_thr: int  = 5,
                                   cluster_strength: float = 8.0) -> np.ndarray:
    """
    Iter 4: add a cluster-break penalty to the refine-stage weights.

    Dense mine clusters (N>cluster_thr) on non-line cells create locally
    ambiguous N=7/8 configurations that the CSP solver cannot resolve without
    guessing.  Penalising these during the refine SA discourages their formation.

    Only applied to non-hi-target cells (target < 3.0) — we never penalise
    the line-density gradient that drives visual reconstruction quality.

    Returns: (base_weights * underfill_aug) * cluster_multiplier  [float32]
    """
    excess = np.clip(N_current.astype(np.float32) - cluster_thr, 0.0, 3.0)
    non_hi = (target < 3.0).astype(np.float32)
    cluster_mult = (1.0 + cluster_strength * excess * non_hi).astype(np.float32)
    return np.ascontiguousarray((base_weights * cluster_mult).astype(np.float32))


def compute_sealing_prevention_weights(base_weights: np.ndarray,
                                        grid_current: np.ndarray,
                                        target: np.ndarray,
                                        hi_threshold: float = 3.0,
                                        density_threshold: float = 0.6,
                                        sealing_strength: float = 20.0) -> np.ndarray:
    """
    Iter 5: sealing-prevention weight multiplier for the refine stage.

    Penalises cells where the local 3×3 mine density exceeds density_threshold
    on non-hi-target cells. Dense non-line regions produce doubly-sealed
    clusters that no post-hoc repair can resolve.

    Must be recomputed from the CURRENT grid at each refine pass because the
    weight reflects the live mine placement, not a stale snapshot.

    Returns: (base_weights * underfill_aug) * sealing_mult  [float32]
    """
    from scipy.ndimage import convolve as _convolve
    K9 = np.ones((3, 3), dtype=np.float32)
    density = _convolve(grid_current.astype(np.float32), K9,
                        mode='constant', cval=0) / 9.0
    excess = np.clip(density - density_threshold, 0.0, 1.0)
    non_hi = (target < hi_threshold).astype(np.float32)
    seal_mult = (1.0 + sealing_strength * excess * non_hi).astype(np.float32)
    return np.ascontiguousarray((base_weights * seal_mult).astype(np.float32))


def load_image_smart_v2(path: str, board_w: int, board_h: int,
                         invert: bool = True,
                         skel_density_thr: float = 0.35,
                         skel_window: int = 20) -> np.ndarray:
    """
    Iter 6: image loader with hybrid selective skeletonization.

    Problem: source regions with >35% local line density contain line crossings
    and parallel lines that, when downscaled, create T=7-8 saturation zones.
    SA is forced to pack 70-80% mine density locally → N=7-8 everywhere in the
    zone → doubly-sealed clusters the solver cannot enter.

    Fix: in high-density source regions only, apply morphological skeletonization
    (1-pixel thinning) before downscaling. This eliminates crossings and merges,
    reducing saturation-risk cells from ~133 to ~13 at board resolution.

    Low-density regions are unchanged — line quality is preserved there.
    """
    from skimage.morphology import skeletonize as _skeletonize
    from scipy.ndimage import uniform_filter as _uf

    # Step 1: load as grayscale and threshold to binary line mask
    img_gray = np.array(Image.open(path).convert('L'), dtype=np.float32)
    line_bin  = (img_gray < 128).astype(np.uint8)   # 1=line, 0=background

    # Step 2: compute local line density in source coords
    line_density = _uf(line_bin.astype(float), size=skel_window)

    # Step 3: skeletonize only the dense regions
    if (line_density > skel_density_thr).any():
        skel_full = _skeletonize(line_bin.astype(bool)).astype(np.uint8)
        hybrid = line_bin.copy()
        hybrid[line_density > skel_density_thr] = \
            skel_full[line_density > skel_density_thr]
    else:
        hybrid = line_bin

    # Step 4: reconstruct RGB and run standard pipeline
    img_processed = Image.fromarray(
        (255 * (1 - hybrid)).astype(np.uint8), 'L').convert('RGB')

    img_processed = ImageEnhance.Contrast(img_processed).enhance(2.0)
    img_processed = img_processed.resize((board_w, board_h), Image.LANCZOS)
    arr = np.array(img_processed, dtype=np.float32)
    gray = 0.2989 * arr[:, :, 0] + 0.5870 * arr[:, :, 1] + 0.1140 * arr[:, :, 2]

    if invert:
        gray = 255.0 - gray

    p2  = np.percentile(gray, 2)
    p98 = np.percentile(gray, 98)
    if p98 > p2:
        gray = (gray - p2) / (p98 - p2) * 8.0
    else:
        gray = np.zeros_like(gray)

    return np.ascontiguousarray(np.clip(gray, 0.0, 8.0), dtype=np.float32)


def apply_piecewise_T_compression(target: np.ndarray,
                                   knee: float = 4.0,
                                   T_max_new: float = 6.0) -> np.ndarray:
    """
    Iter 8: piecewise linear T compression to prevent saturation sealing.

    Maps T values through:
      f(T) = T                                        if T ≤ knee
      f(T) = knee + (T_max_new - knee)*(T - knee)    if T > knee
                    / (8 - knee)

    Key properties:
      - Identity below knee: background structure and mid-T values fully preserved
      - Linear compression above knee: T=8 → T_max_new, knee → knee
      - No spatial information destroyed (unlike skeletonization)
      - Reduces T=7-8 saturation zones to T≤6 → achievable with <65% density

    Why piecewise beats sigmoid/power-law:
      Sigmoid and power-law compress the ENTIRE T range including low values,
      degrading background accuracy. Piecewise leaves T<knee unchanged.
    """
    T = np.asarray(target, dtype=np.float32).copy()
    above = T > knee
    if above.any():
        T[above] = (knee +
                    (T_max_new - knee) * (T[above] - knee) / (8.0 - knee))
    return np.ascontiguousarray(np.clip(T, 0.0, 8.0), dtype=np.float32)
