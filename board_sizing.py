"""
Runtime board sizing helpers.

Width is the authoritative input. Height is derived from source image ratio.
"""
from PIL import Image


def derive_board_from_width(
    image_path: str,
    board_width: int,
    min_width: int = 300,
    ratio_tolerance: float = 0.005,
) -> dict:
    """
    Compute board dimensions from source image aspect ratio at run time.

    Returns a dict with source dims, board dims, ratio error, and gate result.
    Raises ValueError when width policy or ratio gate fails.
    """
    if int(board_width) < int(min_width):
        raise ValueError(
            f"Board width policy violation: requested {board_width}, minimum is {min_width}"
        )

    with Image.open(image_path) as img:
        source_w, source_h = img.size

    if source_w <= 0 or source_h <= 0:
        raise ValueError(f"Invalid source image dimensions: {source_w}x{source_h}")

    source_ratio = float(source_w) / float(source_h)
    board_w = int(board_width)
    board_h = max(1, int(round(board_w / source_ratio)))
    board_ratio = float(board_w) / float(board_h)
    rel_err = abs(board_ratio - source_ratio) / source_ratio
    gate_ok = rel_err <= float(ratio_tolerance)

    if not gate_ok:
        raise ValueError(
            f"Aspect ratio gate failed: source_ratio={source_ratio:.6f}, "
            f"board_ratio={board_ratio:.6f}, rel_err={rel_err:.6f}, "
            f"tolerance={ratio_tolerance:.6f}"
        )

    return {
        "source_width": int(source_w),
        "source_height": int(source_h),
        "source_ratio": float(source_ratio),
        "board_width": int(board_w),
        "board_height": int(board_h),
        "board_ratio": float(board_ratio),
        "aspect_ratio_relative_error": float(rel_err),
        "aspect_ratio_tolerance": float(ratio_tolerance),
        "gate_aspect_ratio_within_tolerance": bool(gate_ok),
        "width_policy_min": int(min_width),
    }

