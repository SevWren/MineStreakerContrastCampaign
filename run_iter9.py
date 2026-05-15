#!/usr/bin/env python3
"""
run_iter9.py

Production Iter9 pipeline with explicit source-image runtime contract.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image as PILImage
from scipy.ndimage import convolve

from assets.image_guard import verify_source_image
from board_sizing import derive_board_from_width
from core import (
    apply_piecewise_T_compression,
    assert_board_valid,
    compute_N,
    compute_zone_aware_weights,
    compute_sealing_prevention_weights,
    load_image_smart,
)
from corridors import build_adaptive_corridors
from pipeline import RepairRoutingConfig, route_late_stage_failure, write_repair_route_artifacts
from repair import run_phase1_repair
from report import (
    render_repair_overlay,
    render_repair_overlay_explained,
    render_report,
    render_report_explained,
)
from sa import compile_sa_kernel, run_sa
from solver import ensure_solver_warmed, solve_board
from source_config import SourceImageConfig, resolve_source_image_config

DEFAULT_IMAGE = "assets/input_source_image.png"
DEFAULT_BOARD_W = 300
DEFAULT_SEED = 42
DEFAULT_DEMO_CONFIG = "configs/demo/iter9_visual_solver_demo.default.json"
RESULTS_ROOT = "results/iter9"
SCHEMA_VERSION = "metrics.v2.source_image_runtime_contract"
IMAGE_SWEEP_SUMMARY_FIELDS = [
    "batch_index",
    "image_path",
    "image_name",
    "image_stem",
    "source_image_sha256",
    "status",
    "child_run_dir",
    "metrics_path",
    "best_artifact_to_open_first",
    "board",
    "seed",
    "n_unknown",
    "coverage",
    "solvable",
    "mean_abs_error",
    "repair_route_selected",
    "selected_route",
    "route_result",
    "route_outcome_detail",
    "next_recommended_route",
    "error_type",
    "error_message",
]

# Reset these back closer to the original values then run the board test one more time & compare results
# T_COARSE = 10.0 # (Default)
# T_REFINE1 = 2.0 (default)
# T_REFINE2 = 1.7 (default)

# Pipeline config
# What this controls: How many mine cells the coarse starting board begins with.
# In this pipeline: It sets the first rough guess before optimization starts.
# In practice: Higher values start with more mines; lower values start with fewer mines.
DENSITY = 0.22

# What this controls: The safety margin near edges where mine placement is restricted.
# In this pipeline: It is passed into corridor and optimization rules to protect border behavior.
# In practice: Higher values protect a wider edge area; lower values allow tighter edge fitting.
BORDER = 3

# What this controls: How long the first broad search phase runs.
# In this pipeline: It sets the number of trial changes in the coarse optimization stage.
# In practice: Higher values can improve rough alignment but take longer to run.
COARSE_ITERS = 2_000_000

# What this controls: The starting "freedom to explore" in coarse search.
# In this pipeline: It sets the initial search temperature for large early moves.
# In practice: Higher values explore more aggressively; lower values stay conservative earlier.
# T_COARSE = 10.0 # (Default)
T_COARSE = 10.0

# What this controls: How quickly coarse search cools down over time.
# In this pipeline: It is the per-step cooling factor during coarse optimization.
# In practice: Values closer to 1 cool more slowly (more exploration); smaller values cool faster.
ALPHA_COARSE = 0.99998

# What this controls: How long the main high-detail search phase runs.
# In this pipeline: It sets the number of trial changes in fine optimization.
# In practice: Higher values usually improve final detail but increase runtime.
FINE_ITERS = 8_000_000

# What this controls: The starting exploration level for fine search.
# In this pipeline: It sets the initial temperature for the fine stage.
# In practice: Higher values allow bigger adjustments; lower values favor stable smaller adjustments.
T_FINE = 3.5

# What this controls: How quickly the fine search reduces its exploration.
# In this pipeline: It is the cooling factor used in the fine stage.
# In practice: Closer to 1 keeps searching broadly longer; lower values lock in sooner.
ALPHA_FINE = 0.999996

# What this controls: Length of the first refinement pass after fine search.
# In this pipeline: It sets the number of trial changes in refine pass 1.
# In practice: Higher values can polish more, but cost additional time.
REFINE1_ITERS = 2_000_000

# What this controls: Starting exploration level for refinement pass 1.
# In this pipeline: It sets the initial temperature for the first polish pass.
# In practice: Higher values allow larger corrective moves; lower values keep moves tighter.
# T_REFINE1 = 2.0 (default)
T_REFINE1 = 2.0

# What this controls: Cooling speed for refinement pass 1.
# In this pipeline: It is the cooling factor while refine pass 1 runs.
# In practice: Closer to 1 extends exploration; lower values settle decisions faster.
ALPHA_REFINE1 = 0.999997

# What this controls: Length of the second refinement pass.
# In this pipeline: It sets the number of trial changes in refine pass 2.
# In practice: Higher values provide more cleanup time, with longer runtime.
REFINE2_ITERS = 2_000_000

# What this controls: Starting exploration level for refinement pass 2.
# In this pipeline: It sets the initial temperature for the second polish pass.
# In practice: Higher values permit bolder late corrections; lower values keep changes small.
# T_REFINE2 = 1.7 (default)
T_REFINE2 = 1.7

# What this controls: Cooling speed for refinement pass 2.
# In this pipeline: It is the cooling factor used during refine pass 2.
# In practice: Closer to 1 cools gently; lower values make it settle sooner.
ALPHA_REFINE2 = 0.999997

# What this controls: Length of the final refinement pass.
# In this pipeline: It sets the number of trial changes in refine pass 3.
# In practice: Higher values spend more time polishing the final result.
REFINE3_ITERS = 4_000_000

# What this controls: Starting exploration level for refinement pass 3.
# In this pipeline: It sets the initial temperature for the final polish pass.
# In practice: Higher values allow bigger late moves; lower values keep final edits minimal.
T_REFINE3 = 1.4

# What this controls: Cooling speed for refinement pass 3.
# In this pipeline: It is the cooling factor for the final pass.
# In practice: Closer to 1 keeps flexibility longer; lower values finalize faster.
ALPHA_REFINE3 = 0.999998

# What this controls: The floor for how low optimization temperature can go.
# In this pipeline: It prevents search temperature from dropping to zero.
# In practice: Higher values keep some flexibility late; lower values make the end stage stricter.
T_MIN = 0.001

# What this controls: Importance weight for true background zones.
# In this pipeline: It shapes zone-based matching priorities for clearly empty areas.
# In practice: Higher values push stronger background fidelity; lower values relax it.
BP_TRUE = 8.0

# What this controls: Importance weight for transition background zones near stronger features.
# In this pipeline: It balances matching pressure in boundary-like background areas.
# In practice: Higher values enforce transitions more strongly; lower values soften that pressure.
BP_TRANS = 1.0

# What this controls: Extra emphasis for high-value target regions.
# In this pipeline: It boosts matching priority where the target signal is strong.
# In practice: Higher values focus more on strong features; lower values spread attention more evenly.
HI_BOOST = 18.0

# What this controls: The cutoff used to decide what counts as a high-value region.
# In this pipeline: It defines which target cells receive high-region treatment.
# In practice: Higher values label fewer cells as high; lower values label more cells as high.
HI_THR = 3.0

# What this controls: How strongly underfilled areas get extra attention during refinement.
# In this pipeline: It amplifies weights where current counts are below target levels.
# In practice: Higher values push harder to fill weak spots; lower values apply gentler correction.
UF_FACTOR = 1.8

# What this controls: The trigger point for sealing-prevention behavior.
# In this pipeline: It helps decide when protective anti-sealing weighting should activate.
# In practice: Higher values trigger protection less often; lower values trigger it more often.
SEAL_THR = 0.6

# What this controls: Strength of sealing-prevention pressure once triggered.
# In this pipeline: It scales how strongly the refinement weights resist sealing patterns.
# In practice: Higher values resist sealing more aggressively; lower values keep that effect mild.
SEAL_STR = 20.0

# What this controls: Where piecewise target-value compression begins to bend.
# In this pipeline: It sets the knee point for remapping loaded image target values.
# In practice: Higher values delay compression; lower values start compression earlier.
PW_KNEE = 4.0

# What this controls: The maximum cap used by piecewise target-value compression.
# In this pipeline: It limits the top end of compressed target values before weighting and search.
# In practice: Higher values preserve more high-end contrast; lower values flatten peaks more.
PW_T_MAX = 6.0


def _to_posix_path(path: Path | str) -> str:
    return Path(path).resolve().as_posix()


def _atomic_save_json(data: dict, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(tmp, path)


def _atomic_save_text(text: str, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    os.replace(tmp, path)


def _atomic_save_csv(rows: list[dict], fieldnames: list[str], path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fieldnames})
    os.replace(tmp, path)


def _atomic_save_npy(array: np.ndarray, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp.npy")
    np.save(tmp, array)
    os.replace(tmp, path)


def _atomic_render(render_fn, save_path: Path, *args, **kwargs) -> None:
    tmp_path = save_path.with_suffix(save_path.suffix + ".tmp.png")
    kwargs = dict(kwargs)
    kwargs["save_path"] = str(tmp_path)
    render_fn(*args, **kwargs)
    os.replace(tmp_path, save_path)


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sanitize_run_tag(value: str) -> str:
    text = value.strip().replace(" ", "_")
    text = re.sub(r"[^A-Za-z0-9_-]", "_", text)
    text = re.sub(r"[_-]+", "_", text)
    text = text.strip("_-")
    text = text[:64]
    text = text.strip("_-")
    return text


def _sanitize_run_tag(value: str) -> str:
    return sanitize_run_tag(value)


def _sanitize_path_token(value: str, *, fallback: str = "item") -> str:
    token = sanitize_run_tag(value)
    return token if token else fallback


def _path_hash_token(path: Path, *, length: int = 8) -> str:
    text = path.resolve().as_posix().encode("utf-8")
    return hashlib.sha256(text).hexdigest()[: int(length)]


def _build_run_id(image_stem: str, board_w: int, seed: int, run_tag: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{stamp}_{image_stem}_{board_w}w_seed{seed}"
    safe_tag = _sanitize_run_tag(run_tag)
    if safe_tag:
        run_id = f"{run_id}_{safe_tag}"
    return run_id


def _build_image_sweep_batch_id(
    *,
    image_dir: Path,
    image_glob: str,
    board_w: int,
    seed: int,
    run_tag: str,
) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dir_token = _sanitize_path_token(image_dir.name, fallback="images")
    glob_token = _sanitize_path_token(image_glob, fallback="glob")
    batch_id = f"{stamp}_{dir_token}_{glob_token}_{int(board_w)}w_seed{int(seed)}"
    safe_tag = sanitize_run_tag(run_tag)
    if safe_tag:
        batch_id = f"{batch_id}_{safe_tag}"
    return batch_id


def _git_cmd(project_root: Path, args: list[str]) -> str | None:
    try:
        out = subprocess.check_output(
            ["git", *args],
            cwd=str(project_root),
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return None
    return out or None


def _git_metadata(project_root: Path) -> dict:
    return {
        "project_root": project_root.as_posix(),
        "project_root_name": project_root.name,
        "git_commit": _git_cmd(project_root, ["rev-parse", "HEAD"]),
        "git_branch": _git_cmd(project_root, ["branch", "--show-current"]),
        "git_dirty": bool(_git_cmd(project_root, ["status", "--porcelain"])),
    }


def _source_image_analysis(path: Path) -> dict:
    image = PILImage.open(path)
    arr = np.array(image, dtype=np.uint8)
    if arr.ndim == 2:
        luma = arr.astype(np.float32)
    elif arr.shape[2] >= 3:
        rgb = arr[:, :, :3].astype(np.float32)
        luma = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    else:
        luma = arr[:, :, 0].astype(np.float32)
    return {
        "width_px": int(arr.shape[1]),
        "height_px": int(arr.shape[0]),
        "aspect_ratio": float(arr.shape[1] / max(arr.shape[0], 1)),
        "mode": image.mode,
        "has_alpha": bool("A" in image.mode),
        "mean_luma": float(luma.mean()),
        "std_luma": float(luma.std()),
    }


def _target_field_stats(target_eval: np.ndarray) -> dict:
    return {
        "min": float(np.min(target_eval)),
        "max": float(np.max(target_eval)),
        "mean": float(np.mean(target_eval)),
        "std": float(np.std(target_eval)),
        "pct_t_ge_6": float(np.mean(target_eval >= 6.0) * 100.0),
        "pct_t_ge_7": float(np.mean(target_eval >= 7.0) * 100.0),
        "pct_t_le_1": float(np.mean(target_eval <= 1.0) * 100.0),
    }


def _environment_summary() -> dict:
    import matplotlib
    import scipy

    return {
        "os": platform.platform(),
        "python_version": platform.python_version(),
        "python_bits": 64 if sys.maxsize > 2**32 else 32,
        "cpu_count": os.cpu_count(),
        "numba_num_threads": None,
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "pillow_version": PILImage.__version__,
        "matplotlib_version": matplotlib.__version__,
    }


def _llm_review_summary(
    source_cfg: SourceImageConfig,
    board_label: str,
    seed: int,
    selected_route: str,
    n_unknown: int,
    artifact_inventory: dict,
    warnings: list[dict],
    route_result: str = "unresolved_after_repair",
    route_outcome_detail: str = "no_late_stage_route_invoked",
    next_recommended_route: object = None,
) -> dict:
    risk = "No critical risks detected."
    if warnings:
        risk = warnings[0].get("message", risk)
    next_text = (
        f" Next recommended route: {next_recommended_route}."
        if next_recommended_route is not None
        else " No next route is required."
    )
    one_sentence_result = (
        f"The run used {source_cfg.command_arg} at {board_label} with seed {seed} "
        f"and ended after selected_route={selected_route} "
        f"with route_result={route_result} "
        f"and route_outcome_detail={route_outcome_detail}."
        f"{next_text}"
    )
    return {
        "one_sentence_result": one_sentence_result,
        "main_success": "The routed repair pipeline completed and produced final artifacts.",
        "main_risk": risk,
        "best_artifact_to_open_first": artifact_inventory.get("visual_explained_png"),
        "best_artifact_to_open_second": artifact_inventory.get("visual_png"),
        "best_repair_artifact_to_open_first": artifact_inventory.get("repair_overlay_explained_png"),
        "best_repair_artifact_to_open_second": artifact_inventory.get("repair_overlay_png"),
        "best_metric_to_check_first": "n_unknown",
        "next_recommended_check": "Start with the explained final visual, then use the technical reports for detailed audit.",
    }


def _relative_or_absolute(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return path.resolve().as_posix()


def discover_source_images(
    image_dir: Path,
    image_glob: str,
    *,
    recursive: bool = False,
    max_images: int | None = None,
) -> list[Path]:
    image_dir = Path(image_dir).resolve()
    if not image_dir.exists():
        raise FileNotFoundError(f"Image sweep directory not found: {image_dir}")
    if not image_dir.is_dir():
        raise NotADirectoryError(f"Image sweep path is not a directory: {image_dir}")

    matches = image_dir.rglob(image_glob) if recursive else image_dir.glob(image_glob)
    images = [path for path in matches if path.is_file()]
    images = sorted(images, key=lambda path: path.resolve().as_posix())

    if max_images is not None:
        images = images[: int(max_images)]

    if not images:
        raise ValueError(f"No source images matched {image_glob!r} under {image_dir.as_posix()}")

    return images


def _colliding_sanitized_stem_tokens(paths: list[Path]) -> set[str]:
    counts: dict[str, int] = {}
    for path in paths:
        token = _sanitize_path_token(path.stem, fallback="image").casefold()
        counts[token] = counts.get(token, 0) + 1
    return {token for token, count in counts.items() if count > 1}


def build_image_sweep_child_out_dir(
    out_root: Path,
    *,
    source_cfg: SourceImageConfig,
    board_label: str,
    seed: int,
    colliding_stem_tokens: set[str],
) -> Path:
    stem_token = _sanitize_path_token(source_cfg.stem, fallback="image")
    if stem_token.casefold() in colliding_stem_tokens:
        stem_token = f"{stem_token}_{source_cfg.sha256[:12]}_{_path_hash_token(source_cfg.absolute_path)}"
    child_name = f"{stem_token}_{board_label}_seed{int(seed)}"
    return out_root / child_name


def _md_table_cell(value) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    return text


def _explicit_flag_present(raw_argv: list[str], flag: str) -> bool:
    for token in raw_argv:
        if token == "--":
            break
        if token == flag or token.startswith(flag + "="):
            return True
    return False


def build_metrics_document(
    flat_metrics: dict,
    *,
    run_identity: dict,
    run_timing: dict,
    project_identity: dict,
    command_invocation: dict,
    source_image: dict,
    source_image_analysis: dict,
    effective_config: dict,
    board_sizing: dict,
    preprocessing_config: dict,
    target_field_stats: dict,
    weight_config: dict,
    corridor_config: dict,
    sa_config: dict,
    repair_config: dict,
    solver_summary: dict,
    repair_route_summary: dict,
    visual_quality_summary: dict,
    runtime_phase_timing_s: dict,
    environment: dict,
    artifact_inventory: dict,
    validation_gates: dict,
    warnings_and_exceptions: list[dict],
    llm_review_summary: dict,
    source_image_validation: dict | None = None,
    batch_context: dict | None = None,
) -> dict:
    document = dict(flat_metrics)
    document.update(
        {
            "schema_version": SCHEMA_VERSION,
            "run_identity": run_identity,
            "run_timing": run_timing,
            "project_identity": project_identity,
            "command_invocation": command_invocation,
            "source_image": source_image,
            "source_image_analysis": source_image_analysis,
            "effective_config": effective_config,
            "board_sizing": board_sizing,
            "preprocessing_config": preprocessing_config,
            "target_field_stats": target_field_stats,
            "weight_config": weight_config,
            "corridor_config": corridor_config,
            "sa_config": sa_config,
            "repair_config": repair_config,
            "solver_summary": solver_summary,
            "repair_route_summary": repair_route_summary,
            "visual_quality_summary": visual_quality_summary,
            "runtime_phase_timing_s": runtime_phase_timing_s,
            "environment": environment,
            "artifact_inventory": artifact_inventory,
            "validation_gates": validation_gates,
            "warnings_and_exceptions": warnings_and_exceptions,
            "llm_review_summary": llm_review_summary,
            "source_image_validation": dict(source_image_validation or {}),
        }
    )
    if batch_context is not None:
        document["batch_context"] = dict(batch_context)
    return document


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run Iter9 reconstruction pipeline.",
        allow_abbrev=False,
    )
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Input image path.")
    parser.add_argument("--out-dir", default=None, help="Exact output run directory.")
    parser.add_argument("--board-w", type=int, default=DEFAULT_BOARD_W, help="Board width.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed.")
    parser.add_argument("--allow-noncanonical", action="store_true", help="Allow noncanonical image.")
    parser.add_argument("--image-manifest", default=None, help="Path to image manifest JSON.")
    parser.add_argument("--run-tag", default="", help="Optional run tag appended to run id.")
    parser.add_argument("--image-dir", default=None, help="Directory of source images for Iter9 image-sweep mode.")
    parser.add_argument("--image-glob", default="*.png", help="Glob pattern used inside --image-dir. Default: *.png.")
    parser.add_argument("--recursive", action="store_true", help="Recursively discover images under --image-dir.")
    parser.add_argument("--out-root", default=None, help="Parent output directory for image-sweep child runs.")
    parser.add_argument("--continue-on-error", action="store_true", help="Continue image sweep after a failed child run.")
    parser.add_argument("--skip-existing", action="store_true", help="Skip child runs whose expected metrics file already exists.")
    parser.add_argument("--max-images", type=int, default=None, help="Limit image sweep to the first N discovered images after sorting.")
    parser.add_argument("--demo-gui", action="store_true", help="Launch the Iter9 visual solver demo after a successful single-image run.")
    parser.add_argument("--demo-config", default=DEFAULT_DEMO_CONFIG, help="Visual solver demo config path used with --demo-gui.")

    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(raw_argv)

    if args.max_images is not None and int(args.max_images) < 1:
        parser.error("--max-images must be >= 1")

    if args.image_dir is None:
        sweep_only_flags = [
            "--image-glob",
            "--recursive",
            "--out-root",
            "--continue-on-error",
            "--skip-existing",
            "--max-images",
        ]
        for flag in sweep_only_flags:
            if _explicit_flag_present(raw_argv, flag):
                parser.error(f"{flag} requires --image-dir")
    else:
        if args.out_dir is not None:
            parser.error("--out-dir cannot be used with --image-dir; use --out-root")
        if _explicit_flag_present(raw_argv, "--image"):
            parser.error("--image cannot be explicitly supplied with --image-dir")
        if _explicit_flag_present(raw_argv, "--image-manifest"):
            parser.error("--image-manifest cannot be used with --image-dir")
        if args.demo_gui:
            parser.error("--demo-gui cannot be used with --image-dir")
        if _explicit_flag_present(raw_argv, "--demo-config"):
            parser.error("--demo-config cannot be used with --image-dir")

    if not args.demo_gui and _explicit_flag_present(raw_argv, "--demo-config"):
        parser.error("--demo-config requires --demo-gui")

    return args


def run_iter9_single(
    args: argparse.Namespace,
    *,
    source_cfg: SourceImageConfig,
    source_validation: dict,
    out_dir_path: Path,
    project_root: Path,
    sa_fn,
    raw_argv: list[str],
    started_wall: float,
    started_at_utc: str,
    warmup_s: float,
    batch_context: dict | None = None,) -> dict:
    image_validation = dict(source_validation)
    phase_timers: dict[str, float] = {"warmup": float(warmup_s)}
    out_dir_path.mkdir(parents=True, exist_ok=True)
    run_id = _build_run_id(source_cfg.stem, int(args.board_w), int(args.seed), args.run_tag)

    print("\n" + "=" * 60)
    print("Mine-Streaker - Iteration 9 - Production Pipeline")
    print("  Phase 1 repair + late-stage repair routing")
    print(f"  source_image={source_cfg.absolute_path.as_posix()}")
    print("=" * 60)

    phase_start = time.perf_counter()
    sizing = derive_board_from_width(
        
        # str(source_cfg.absolute_path), int(args.board_w), min_width=300, ratio_tolerance=0.005      # The default value of 'min_width=' was 300 prior to testing
        str(source_cfg.absolute_path), int(args.board_w), min_width=50, ratio_tolerance=0.005)
    bw = int(sizing["board_width"])
    bh = int(sizing["board_height"])
    target_eval = load_image_smart(str(source_cfg.absolute_path), bw, bh, invert=True)
    target = apply_piecewise_T_compression(target_eval, PW_KNEE, PW_T_MAX)
    phase_timers["image_load_and_preprocess"] = time.perf_counter() - phase_start

    phase_start = time.perf_counter()
    w_zone = compute_zone_aware_weights(target, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    forbidden, cpct, _, _ = build_adaptive_corridors(target, border=BORDER)
    phase_timers["corridor_build"] = time.perf_counter() - phase_start

    k8 = np.ones((3, 3), dtype=np.int32)
    k8[1, 1] = 0
    hi_mask = target_eval >= HI_THR
    bg_mask = target_eval < 1.0
    adj_to_hi = convolve(hi_mask.astype(np.int32), k8, mode="constant", cval=0) > 0
    trans_mask = bg_mask & adj_to_hi
    true_bg = bg_mask & ~trans_mask
    hi6 = target >= 5.5
    sat = hi6 & (convolve(hi6.astype(np.int32), k8, mode="constant", cval=0) >= 5)

    rng = np.random.default_rng(int(args.seed))

    # Coarse SA
    phase_start = time.perf_counter()
    cw, ch = bw // 2, bh // 2
    _teval_pil = PILImage.fromarray(
        (target_eval / 8.0 * 255.0).clip(0, 255).astype(np.uint8)
    ).resize((cw, ch), PILImage.BILINEAR)
    _target_c_raw = np.array(_teval_pil, dtype=np.float32) / 255.0 * 8.0
    target_c = apply_piecewise_T_compression(
        np.ascontiguousarray(_target_c_raw, dtype=np.float32), PW_KNEE, PW_T_MAX
    )
    weight_c = compute_zone_aware_weights(target_c, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    forbidden_c, _, _, _ = build_adaptive_corridors(target_c, border=BORDER)
    grid_c = np.zeros((ch, cw), dtype=np.int8)
    available_c = np.argwhere(forbidden_c == 0)
    picks = rng.choice(
        len(available_c),
        size=min(int(DENSITY * cw * ch), len(available_c)),
        replace=False,
    )
    for idx in picks:
        grid_c[available_c[idx][0], available_c[idx][1]] = 1
    grid_c, _, history_c = run_sa(
        sa_fn,
        grid_c,
        target_c,
        weight_c,
        forbidden_c,
        COARSE_ITERS,
        T_COARSE,
        T_MIN,
        ALPHA_COARSE,
        BORDER,
        int(args.seed),
    )
    phase_timers["coarse_sa"] = time.perf_counter() - phase_start

    coarse_img = PILImage.fromarray(grid_c.astype(np.uint8) * 255)
    grid = (np.array(coarse_img.resize((bw, bh), PILImage.NEAREST), dtype=np.uint8) > 127).astype(np.int8)
    grid[forbidden == 1] = 0

    # Fine SA
    phase_start = time.perf_counter()
    grid, _, history_f = run_sa(
        sa_fn,
        grid,
        target,
        w_zone,
        forbidden,
        FINE_ITERS,
        T_FINE,
        T_MIN,
        ALPHA_FINE,
        BORDER,
        int(args.seed) + 1,
    )
    grid[forbidden == 1] = 0
    phase_timers["fine_sa"] = time.perf_counter() - phase_start

    # Refine SA
    phase_start = time.perf_counter()
    histories = [history_c, history_f]
    for pidx, (iters, temp, alpha) in enumerate(
        [
            (REFINE1_ITERS, T_REFINE1, ALPHA_REFINE1),
            (REFINE2_ITERS, T_REFINE2, ALPHA_REFINE2),
            (REFINE3_ITERS, T_REFINE3, ALPHA_REFINE3),
        ]
    ):
        n_cur = compute_N(grid)
        underfill = np.clip(target - n_cur.astype(np.float32), 0.0, 8.0) / 8.0
        weight_ref = (w_zone * (1.0 + UF_FACTOR * underfill)).astype(np.float32)
        if pidx < 2:
            weight_ref = compute_sealing_prevention_weights(
                weight_ref, grid, target, HI_THR, SEAL_THR, SEAL_STR
            )
        grid, _, hist = run_sa(
            sa_fn,
            grid,
            target,
            weight_ref,
            forbidden,
            iters,
            temp,
            T_MIN,
            alpha,
            BORDER,
            int(args.seed) + 2 + pidx,
        )
        grid[forbidden == 1] = 0
        histories.append(hist)
    phase_timers["refine_sa_total"] = time.perf_counter() - phase_start

    assert_board_valid(grid, forbidden, "post-SA")
    sr_post_sa = solve_board(grid, max_rounds=300, mode="full")

    # Phase 1 repair
    phase_start = time.perf_counter()
    sr_trial = solve_board(grid, max_rounds=50, mode="trial")
    phase1_budget = max(60.0, sr_trial.n_unknown * 0.15 + 30.0)
    phase1_result = run_phase1_repair(
        grid,
        target,
        w_zone,
        forbidden,
        time_budget_s=min(phase1_budget, 120.0),
        max_rounds=300,
        search_radius=6,
        verbose=True,
        checkpoint_dir=str(out_dir_path),
    )
    grid = phase1_result.grid
    phase1_reason = phase1_result.stop_reason
    phase1_repair_hit_time_budget = bool(phase1_result.phase1_repair_hit_time_budget)
    grid[forbidden == 1] = 0
    assert_board_valid(grid, forbidden, "post-phase1")
    sr_phase1 = solve_board(grid, max_rounds=300, mode="full")
    phase_timers["phase1_repair"] = time.perf_counter() - phase_start

    # Late-stage routing
    phase_start = time.perf_counter()
    grid_before_route = grid.copy()
    sr_before_route = sr_phase1
    route = route_late_stage_failure(
        grid=grid,
        target=target_eval,
        weights=w_zone,
        forbidden=forbidden,
        sr=sr_phase1,
        config=RepairRoutingConfig(
            phase2_budget_s=360.0,
            last100_budget_s=300.0,
            last100_unknown_threshold=100,
            solve_max_rounds=300,
            trial_max_rounds=60,
            enable_phase2=True,
            enable_last100=True,
            enable_sa_rerun=False,
        ),
    )
    grid = route.grid
    grid[forbidden == 1] = 0
    assert_board_valid(grid, forbidden, "post-late-stage-routing")
    sr_final = route.sr
    phase_timers["late_stage_routing"] = time.perf_counter() - phase_start

    n_final = compute_N(grid)
    err = np.abs(n_final.astype(np.float32) - target_eval)
    before_route_err = np.abs(compute_N(grid_before_route).astype(np.float32) - target_eval)

    board_label = f"{bw}x{bh}"
    metrics_path = out_dir_path / f"metrics_iter9_{board_label}.json"
    grid_path = out_dir_path / f"grid_iter9_{board_label}.npy"
    grid_latest_path = out_dir_path / "grid_iter9_latest.npy"
    final_png = out_dir_path / f"iter9_{board_label}_FINAL.png"
    final_explained_png = out_dir_path / f"iter9_{board_label}_FINAL_explained.png"
    overlay_png = out_dir_path / f"repair_overlay_{board_label}.png"
    overlay_explained_png = out_dir_path / f"repair_overlay_{board_label}_explained.png"

    route_artifact_meta = {
        "run_id": run_id,
        "generated_at_utc": _utc_now_z(),
        "source_image_project_relative_path": source_cfg.project_relative_path,
        "source_image_sha256": source_cfg.sha256,
        "metrics_path": _relative_or_absolute(metrics_path, project_root),
        "phase1_repair_hit_time_budget": phase1_repair_hit_time_budget,
        "phase2_full_repair_hit_time_budget": bool(route.phase2_full_repair_hit_time_budget),
        "last100_repair_hit_time_budget": bool(route.last100_repair_hit_time_budget),
    }
    route_artifacts = write_repair_route_artifacts(
        str(out_dir_path),
        board_label,
        route,
        artifact_metadata=route_artifact_meta,
    )

    removed_mines = int(np.sum((grid_before_route == 1) & (grid == 0)))
    added_mines = int(np.sum((grid_before_route == 0) & (grid == 1)))
    runtime_before_report_s = float(time.perf_counter() - started_wall)
    render_metrics = {
        "run_id": run_id,
        "board": board_label,
        "board_width": int(bw),
        "board_height": int(bh),
        "seed": int(args.seed),
        "source_image": {
            "name": source_cfg.name,
            "project_relative_path": source_cfg.project_relative_path,
        },
        **route.route_state_fields(),
        "repair_route_selected": route.selected_route,   # exact alias
        "repair_route_result": route.route_result,        # exact alias
        "coverage": float(sr_final.coverage),
        "solvable": bool(sr_final.solvable),
        "mine_accuracy": float(sr_final.mine_accuracy),
        "n_unknown": int(sr_final.n_unknown),
        "mean_abs_error": float(err.mean()),
        "mine_density": float(grid.mean()),
        "before_unknown": int(sr_before_route.n_unknown),
        "after_unknown": int(sr_final.n_unknown),
        "removed_mines": removed_mines,
        "added_mines": added_mines,
        "solved_after": bool(sr_final.solvable and sr_final.n_unknown == 0),
        "runtime_before_report_s": runtime_before_report_s,
    }

    phase_start = time.perf_counter()
    _atomic_render(
        render_repair_overlay,
        overlay_png,
        target_eval,
        grid_before_route,
        grid,
        sr_before_route,
        sr_final,
        route.phase2_log + route.last100_log,
        dpi=120,
    )
    all_history = np.concatenate(histories)
    _atomic_render(
        render_report,
        final_png,
        target_eval,
        grid,
        sr_final,
        all_history,
        f"Mine-Streaker Iter9 - {board_label} [solvable={sr_final.solvable}]",
        dpi=120,
    )
    _atomic_render(
        render_repair_overlay_explained,
        overlay_explained_png,
        target_eval,
        grid_before_route,
        grid,
        sr_before_route,
        sr_final,
        route.phase2_log + route.last100_log,
        metrics=render_metrics,
        dpi=120,
    )
    _atomic_render(
        render_report_explained,
        final_explained_png,
        target_eval,
        grid,
        sr_final,
        all_history,
        "Mine-Streaker explained final report",
        metrics=render_metrics,
        dpi=120,
    )
    phase_timers["render_and_write"] = time.perf_counter() - phase_start

    _atomic_save_npy(grid, grid_path)
    _atomic_save_npy(grid, grid_latest_path)

    duration_wall_s = time.perf_counter() - started_wall
    finished_at_utc = _utc_now_z()

    flat_metrics = {
        "label": board_label,
        "board": board_label,
        "cells": int(bw * bh),
        "abs_error_variance": float(err.var()),
        "mean_abs_error": float(err.mean()),
        "hi_err": float(err[hi_mask].mean()) if np.any(hi_mask) else 0.0,
        "true_bg_err": float(err[true_bg].mean()) if np.any(true_bg) else 0.0,
        "trans_bg_err": float(err[trans_mask].mean()) if np.any(trans_mask) else 0.0,
        "bg_err": float(err[bg_mask].mean()) if np.any(bg_mask) else 0.0,
        "pct_within_1": float(np.mean(err <= 1.0) * 100.0),
        "pct_within_2": float(np.mean(err <= 2.0) * 100.0),
        "mine_density": float(grid.mean()),
        "corridor_pct": float(cpct),
        "coverage": float(sr_final.coverage),
        "solvable": bool(sr_final.solvable),
        "mine_accuracy": float(sr_final.mine_accuracy),
        "n_unknown": int(sr_final.n_unknown),
        "repair_reason": (
            f"phase1={phase1_reason}"
            f"+selected_route={route.selected_route}"
            f"+route_result={route.route_result}"
            f"+route_outcome_detail={route.route_outcome_detail}"
            f"+next_recommended_route={route.next_recommended_route}"
        ),
        "total_time_s": float(duration_wall_s),
        "seed": int(args.seed),
        "iter": 9,
        "bp_true": BP_TRUE,
        "bp_trans": BP_TRANS,
        "hi_boost": HI_BOOST,
        "uf_factor": UF_FACTOR,
        "seal_thr": SEAL_THR,
        "seal_str": SEAL_STR,
        "pw_knee": PW_KNEE,
        "pw_T_max": PW_T_MAX,
        "sat_risk": int(sat.sum()),
        "preprocessing": "piecewise_T_compression",
        "phase2": "full_cluster_repair",
        "source_width": int(sizing["source_width"]),
        "source_height": int(sizing["source_height"]),
        "source_ratio": float(sizing["source_ratio"]),
        "board_ratio": float(sizing["board_ratio"]),
        "aspect_ratio_relative_error": float(sizing["aspect_ratio_relative_error"]),
        "gate_aspect_ratio_within_0_5pct": bool(sizing["gate_aspect_ratio_within_tolerance"]),
        **route.route_state_fields(),
        "repair_route_selected": route.selected_route,   # exact alias
        "repair_route_result": route.route_result,        # exact alias
        "dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
        "sealed_cluster_count": route.failure_taxonomy.get("sealed_cluster_count"),
        "sealed_single_mesa_count": route.failure_taxonomy.get("sealed_single_mesa_count"),
        "sealed_multi_cell_cluster_count": route.failure_taxonomy.get("sealed_multi_cell_cluster_count"),
        "phase2_fixes": route.phase2_full_repair_accepted_move_count,
        "last100_fixes": route.last100_n_fixes,
        "phase1_repair_hit_time_budget": phase1_repair_hit_time_budget,
        "phase2_full_repair_hit_time_budget": bool(route.phase2_full_repair_hit_time_budget),
        "last100_repair_hit_time_budget": bool(route.last100_repair_hit_time_budget),
        "visual_delta": route.visual_delta_summary.get("visual_delta"),
        "failure_taxonomy_path": _relative_or_absolute(Path(route_artifacts["failure_taxonomy"]), project_root),
        "repair_route_decision_path": _relative_or_absolute(
            Path(route_artifacts["repair_route_decision"]), project_root
        ),
        "visual_delta_summary_path": _relative_or_absolute(
            Path(route_artifacts["visual_delta_summary"]), project_root
        ),
        "repair_overlay_path": _relative_or_absolute(overlay_png, project_root),
    }

    run_identity = {
        "run_id": run_id,
        "entry_point": "run_iter9.py",
        "output_dir": _relative_or_absolute(out_dir_path, project_root),
        "board_width": int(bw),
        "board_height": int(bh),
        "seed": int(args.seed),
    }
    run_timing = {
        "started_at_utc": started_at_utc,
        "finished_at_utc": finished_at_utc,
        "duration_wall_s": float(duration_wall_s),
    }
    project_identity = _git_metadata(project_root)
    command_invocation = {
        "entry_point": "run_iter9.py",
        "argv": ["run_iter9.py", *[str(arg) for arg in raw_argv]],
    }
    source_image_block = source_cfg.to_metrics_dict()
    source_image_analysis = _source_image_analysis(source_cfg.absolute_path)
    effective_config = {
        "board_width": int(bw),
        "board_height": int(bh),
        "seed": int(args.seed),
        "density": DENSITY,
        "border": BORDER,
        "invert": True,
        "piecewise_compression_enabled": True,
        "pw_knee": PW_KNEE,
        "pw_t_max": PW_T_MAX,
        "out_dir": _relative_or_absolute(out_dir_path, project_root),
    }
    board_sizing = dict(sizing)
    preprocessing_config = {
        "loader": "load_image_smart",
        "invert": True,
        "piecewise_compression_enabled": True,
        "pw_knee": PW_KNEE,
        "pw_t_max": PW_T_MAX,
    }
    target_stats = _target_field_stats(target_eval)
    weight_config = {
        "method": "compute_zone_aware_weights",
        "bp_true": BP_TRUE,
        "bp_trans": BP_TRANS,
        "hi_boost": HI_BOOST,
        "hi_threshold": HI_THR,
        "underfill_factor": UF_FACTOR,
    }
    corridor_config = {
        "method": "build_adaptive_corridors",
        "border": BORDER,
        "corridor_pct": float(cpct),
    }
    sa_config = {
        "density": DENSITY,
        "coarse_iters": COARSE_ITERS,
        "fine_iters": FINE_ITERS,
        "refine_iters": [REFINE1_ITERS, REFINE2_ITERS, REFINE3_ITERS],
        "T_coarse": T_COARSE,
        "T_fine": T_FINE,
        "T_refine": [T_REFINE1, T_REFINE2, T_REFINE3],
        "T_min": T_MIN,
        "alpha_coarse": ALPHA_COARSE,
        "alpha_fine": ALPHA_FINE,
        "alpha_refine": [ALPHA_REFINE1, ALPHA_REFINE2, ALPHA_REFINE3],
    }
    repair_config = {
        "phase1_budget_s": float(min(phase1_budget, 120.0)),
        "phase2_budget_s": 360.0,
        "last100_budget_s": 300.0,
        "last100_unknown_threshold": 100,
        "solve_max_rounds": 300,
        "trial_max_rounds": 60,
    }
    solver_summary = {
        "post_sa": {
            "coverage": float(sr_post_sa.coverage),
            "n_unknown": int(sr_post_sa.n_unknown),
            "solvable": bool(sr_post_sa.solvable),
        },
        "post_phase1": {
            "coverage": float(sr_phase1.coverage),
            "n_unknown": int(sr_phase1.n_unknown),
            "solvable": bool(sr_phase1.solvable),
        },
        "post_routing": {
            "coverage": float(sr_final.coverage),
            "n_unknown": int(sr_final.n_unknown),
            "solvable": bool(sr_final.solvable),
        },
    }
    repair_route_summary = {
        **route.route_state_fields(),
        "repair_route_selected": route.selected_route,
        "repair_route_result": route.route_result,
        "phase2_fixes": route.phase2_full_repair_accepted_move_count,
        "last100_fixes": route.last100_n_fixes,
        "dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
        "sealed_cluster_count": int(route.failure_taxonomy.get("sealed_cluster_count", 0) or 0),
        "phase1_repair_hit_time_budget": phase1_repair_hit_time_budget,
        "phase2_full_repair_hit_time_budget": bool(route.phase2_full_repair_hit_time_budget),
        "last100_repair_hit_time_budget": bool(route.last100_repair_hit_time_budget),
        "sa_rerun_invoked": bool(route.decision.get("sa_rerun_invoked", False)),
    }
    visual_quality_summary = {
        "mean_abs_error_before_repair": float(before_route_err.mean()),
        "mean_abs_error_after_repair": float(err.mean()),
        "visual_delta": float(route.visual_delta_summary.get("visual_delta", err.mean() - before_route_err.mean())),
        "pct_within_1": float(np.mean(err <= 1.0) * 100.0),
        "pct_within_2": float(np.mean(err <= 2.0) * 100.0),
        "hi_err": float(err[hi_mask].mean()) if np.any(hi_mask) else 0.0,
        "true_bg_err": float(err[true_bg].mean()) if np.any(true_bg) else 0.0,
    }
    runtime_phase_timing_s = {
        "warmup": float(phase_timers.get("warmup", 0.0)),
        "image_load_and_preprocess": float(phase_timers.get("image_load_and_preprocess", 0.0)),
        "corridor_build": float(phase_timers.get("corridor_build", 0.0)),
        "coarse_sa": float(phase_timers.get("coarse_sa", 0.0)),
        "fine_sa": float(phase_timers.get("fine_sa", 0.0)),
        "refine_sa_total": float(phase_timers.get("refine_sa_total", 0.0)),
        "phase1_repair": float(phase_timers.get("phase1_repair", 0.0)),
        "late_stage_routing": float(phase_timers.get("late_stage_routing", 0.0)),
        "render_and_write": float(phase_timers.get("render_and_write", 0.0)),
        "total": float(duration_wall_s),
    }
    environment = _environment_summary()
    artifact_inventory = {
        "metrics_json": _relative_or_absolute(metrics_path, project_root),
        "grid_npy": _relative_or_absolute(grid_path, project_root),
        "grid_latest_npy": _relative_or_absolute(grid_latest_path, project_root),
        "visual_png": _relative_or_absolute(final_png, project_root),
        "visual_explained_png": _relative_or_absolute(final_explained_png, project_root),
        "repair_overlay_png": _relative_or_absolute(overlay_png, project_root),
        "repair_overlay_explained_png": _relative_or_absolute(overlay_explained_png, project_root),
        "failure_taxonomy_json": _relative_or_absolute(Path(route_artifacts["failure_taxonomy"]), project_root),
        "repair_route_decision_json": _relative_or_absolute(
            Path(route_artifacts["repair_route_decision"]), project_root
        ),
        "visual_delta_summary_json": _relative_or_absolute(
            Path(route_artifacts["visual_delta_summary"]), project_root
        ),
    }
    validation_gates = {
        "board_valid": True,
        "forbidden_cells_mine_free": bool(np.all(grid[forbidden == 1] == 0)),
        "aspect_ratio_within_tolerance": bool(sizing["gate_aspect_ratio_within_tolerance"]),
        "n_unknown_zero": bool(sr_final.n_unknown == 0),
        "coverage_at_least_9999": bool(sr_final.coverage >= 0.9999),
        "solvable_true": bool(sr_final.solvable),
        "source_image_validated": bool(image_validation["ok"]),
        "canonical_image_match": image_validation["canonical_match"],
        "noncanonical_allowed": bool(image_validation["noncanonical_allowed"]),
    }
    warnings_and_exceptions = list(image_validation.get("warnings", []))
    llm_review = _llm_review_summary(
        source_cfg,
        board_label,
        int(args.seed),
        route.selected_route,
        int(sr_final.n_unknown),
        artifact_inventory,
        warnings_and_exceptions,
        route_result=route.route_result,
        route_outcome_detail=route.route_outcome_detail,
        next_recommended_route=route.next_recommended_route,
    )

    metrics_doc = build_metrics_document(
        flat_metrics,
        run_identity=run_identity,
        run_timing=run_timing,
        project_identity=project_identity,
        command_invocation=command_invocation,
        source_image=source_image_block,
        source_image_analysis=source_image_analysis,
        effective_config=effective_config,
        board_sizing=board_sizing,
        preprocessing_config=preprocessing_config,
        target_field_stats=target_stats,
        weight_config=weight_config,
        corridor_config=corridor_config,
        sa_config=sa_config,
        repair_config=repair_config,
        solver_summary=solver_summary,
        repair_route_summary=repair_route_summary,
        visual_quality_summary=visual_quality_summary,
        runtime_phase_timing_s=runtime_phase_timing_s,
        environment=environment,
        artifact_inventory=artifact_inventory,
        validation_gates=validation_gates,
        warnings_and_exceptions=warnings_and_exceptions,
        llm_review_summary=llm_review,
        source_image_validation=image_validation,
        batch_context=batch_context,
    )
    _atomic_save_json(metrics_doc, metrics_path)

    print(f"\n  Results written to: {out_dir_path.as_posix()}")
    print(f"  Route: {route.selected_route}  n_unknown={sr_final.n_unknown}  coverage={sr_final.coverage:.5f}")
    print(f"  Total time: {duration_wall_s:.2f}s")
    return metrics_doc


def _image_sweep_success_row(
    *,
    batch_index: int,
    source_cfg: SourceImageConfig,
    child_run_dir: Path,
    metrics_doc: dict,
    project_root: Path,
) -> dict:
    artifact_inventory = metrics_doc.get("artifact_inventory", {})
    llm_review = metrics_doc.get("llm_review_summary", {})
    row = {
        "batch_index": int(batch_index),
        "image_path": source_cfg.absolute_path.resolve().as_posix(),
        "image_name": source_cfg.name,
        "image_stem": source_cfg.stem,
        "source_image_sha256": source_cfg.sha256,
        "status": "succeeded",
        "child_run_dir": _relative_or_absolute(child_run_dir, project_root),
        "metrics_path": artifact_inventory.get("metrics_json"),
        "best_artifact_to_open_first": llm_review.get("best_artifact_to_open_first"),
        "board": metrics_doc.get("board"),
        "seed": metrics_doc.get("seed"),
        "n_unknown": metrics_doc.get("n_unknown"),
        "coverage": metrics_doc.get("coverage"),
        "solvable": metrics_doc.get("solvable"),
        "mean_abs_error": metrics_doc.get("mean_abs_error"),
        "repair_route_selected": metrics_doc.get("repair_route_selected"),
        "selected_route": metrics_doc.get("selected_route"),
        "route_result": metrics_doc.get("route_result"),
        "route_outcome_detail": metrics_doc.get("route_outcome_detail"),
        "next_recommended_route": metrics_doc.get("next_recommended_route"),
        "error_type": None,
        "error_message": None,
    }
    return {field: row.get(field) for field in IMAGE_SWEEP_SUMMARY_FIELDS}


def _image_sweep_failure_row(
    *,
    batch_index: int,
    image_path: Path,
    source_cfg: SourceImageConfig | None,
    child_run_dir: Path | None,
    board_label: str | None,
    seed: int,
    error: BaseException,
    project_root: Path,
) -> dict:
    if source_cfg is not None:
        resolved_image_path = source_cfg.absolute_path.resolve().as_posix()
        image_name = source_cfg.name
        image_stem = source_cfg.stem
        source_sha = source_cfg.sha256
    else:
        resolved_image_path = str(image_path)
        image_name = None
        image_stem = None
        source_sha = None
    row = {
        "batch_index": int(batch_index),
        "image_path": resolved_image_path,
        "image_name": image_name,
        "image_stem": image_stem,
        "source_image_sha256": source_sha,
        "status": "failed",
        "child_run_dir": _relative_or_absolute(child_run_dir, project_root) if child_run_dir is not None else None,
        "metrics_path": None,
        "best_artifact_to_open_first": None,
        "board": board_label,
        "seed": int(seed),
        "n_unknown": None,
        "coverage": None,
        "solvable": None,
        "mean_abs_error": None,
        "repair_route_selected": None,
        "selected_route": None,
        "route_result": None,
        "route_outcome_detail": None,
        "next_recommended_route": None,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    return {field: row.get(field) for field in IMAGE_SWEEP_SUMMARY_FIELDS}


def _image_sweep_skipped_existing_row(
    *,
    batch_index: int,
    source_cfg: SourceImageConfig,
    child_run_dir: Path,
    metrics_path: Path,
    board_label: str,
    seed: int,
    project_root: Path,
) -> dict:
    hydrated = {
        "best_artifact_to_open_first": None,
        "n_unknown": None,
        "coverage": None,
        "solvable": None,
        "mean_abs_error": None,
        "repair_route_selected": None,
        "selected_route": None,
        "route_result": None,
        "route_outcome_detail": None,
        "next_recommended_route": None,
    }
    try:
        existing = json.loads(metrics_path.read_text(encoding="utf-8"))
        llm_review = existing.get("llm_review_summary", {})
        hydrated["best_artifact_to_open_first"] = llm_review.get("best_artifact_to_open_first")
        hydrated["n_unknown"] = existing.get("n_unknown")
        hydrated["coverage"] = existing.get("coverage")
        hydrated["solvable"] = existing.get("solvable")
        hydrated["mean_abs_error"] = existing.get("mean_abs_error")
        hydrated["repair_route_selected"] = existing.get("repair_route_selected")
        # Use selected_route directly — do NOT synthesize from repair_route_selected
        hydrated["selected_route"] = existing.get("selected_route")
        hydrated["route_result"] = existing.get("route_result")
        hydrated["route_outcome_detail"] = existing.get("route_outcome_detail")
        hydrated["next_recommended_route"] = existing.get("next_recommended_route")
    except Exception:
        pass

    row = {
        "batch_index": int(batch_index),
        "image_path": source_cfg.absolute_path.resolve().as_posix(),
        "image_name": source_cfg.name,
        "image_stem": source_cfg.stem,
        "source_image_sha256": source_cfg.sha256,
        "status": "skipped_existing",
        "child_run_dir": _relative_or_absolute(child_run_dir, project_root),
        "metrics_path": _relative_or_absolute(metrics_path, project_root),
        "best_artifact_to_open_first": hydrated["best_artifact_to_open_first"],
        "board": board_label,
        "seed": int(seed),
        "n_unknown": hydrated["n_unknown"],
        "coverage": hydrated["coverage"],
        "solvable": hydrated["solvable"],
        "mean_abs_error": hydrated["mean_abs_error"],
        "repair_route_selected": hydrated["repair_route_selected"],
        "selected_route": hydrated["selected_route"],
        "route_result": hydrated["route_result"],
        "route_outcome_detail": hydrated["route_outcome_detail"],
        "next_recommended_route": hydrated["next_recommended_route"],
        "error_type": None,
        "error_message": None,
    }
    return {field: row.get(field) for field in IMAGE_SWEEP_SUMMARY_FIELDS}


def write_iter9_image_sweep_summaries(
    *,
    out_root: Path,
    batch_id: str,
    image_dir: str,
    image_glob: str,
    recursive: bool,
    board_w: int,
    seed: int,
    started_at_utc: str,
    finished_at_utc: str,
    duration_wall_s: float,
    batch_warmup_s: float,
    rows: list[dict],
    images_discovered: int,
) -> dict:
    normalized_rows = [
        {field: row.get(field) for field in IMAGE_SWEEP_SUMMARY_FIELDS}
        for row in rows
    ]
    runs_succeeded = sum(1 for row in normalized_rows if row.get("status") == "succeeded")
    runs_failed = sum(1 for row in normalized_rows if row.get("status") == "failed")
    runs_skipped = sum(1 for row in normalized_rows if row.get("status") == "skipped_existing")
    runs_attempted = runs_succeeded + sum(
        1
        for row in normalized_rows
        if row.get("status") == "failed" and int(row.get("batch_index") or 0) > 0
    )

    summary_doc = {
        "schema_version": "iter9_image_sweep.v1",
        "batch_identity": {
            "batch_id": batch_id,
            "entry_point": "run_iter9.py",
            "image_dir": image_dir,
            "image_glob": image_glob,
            "recursive": bool(recursive),
            "out_root": out_root.resolve().as_posix(),
            "board_width": int(board_w),
            "seed": int(seed),
        },
        "batch_timing": {
            "started_at_utc": started_at_utc,
            "finished_at_utc": finished_at_utc,
            "duration_wall_s": float(duration_wall_s),
            "batch_warmup_s": float(batch_warmup_s),
        },
        "images_discovered": int(images_discovered),
        "rows_recorded": len(normalized_rows),
        "runs_attempted": int(runs_attempted),
        "runs_succeeded": int(runs_succeeded),
        "runs_failed": int(runs_failed),
        "runs_skipped": int(runs_skipped),
        "rows": normalized_rows,
    }

    out_root.mkdir(parents=True, exist_ok=True)
    summary_json_path = out_root / "iter9_image_sweep_summary.json"
    summary_csv_path = out_root / "iter9_image_sweep_summary.csv"
    summary_md_path = out_root / "iter9_image_sweep_summary.md"

    _atomic_save_json(summary_doc, summary_json_path)
    _atomic_save_csv(normalized_rows, IMAGE_SWEEP_SUMMARY_FIELDS, summary_csv_path)

    md_lines = [
        "# Iter9 Image Sweep Summary",
        "",
        f"- batch_id: `{batch_id}`",
        f"- image_dir: `{image_dir}`",
        f"- image_glob: `{image_glob}`",
        f"- recursive: `{bool(recursive)}`",
        f"- board_width: `{int(board_w)}`",
        f"- seed: `{int(seed)}`",
        f"- images_discovered: `{int(images_discovered)}`",
        f"- runs_attempted: `{int(runs_attempted)}`",
        f"- runs_succeeded: `{int(runs_succeeded)}`",
        f"- runs_failed: `{int(runs_failed)}`",
        f"- runs_skipped: `{int(runs_skipped)}`",
        "",
        "| batch_index | status | image_path | board | seed | n_unknown | coverage | solvable | selected_route | route_result | repair_route_selected | best_artifact_to_open_first | error_message |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in normalized_rows:
        md_lines.append(
            "| "
            + " | ".join(
                [
                    _md_table_cell(row.get("batch_index")),
                    _md_table_cell(row.get("status")),
                    _md_table_cell(row.get("image_path")),
                    _md_table_cell(row.get("board")),
                    _md_table_cell(row.get("seed")),
                    _md_table_cell(row.get("n_unknown")),
                    _md_table_cell(row.get("coverage")),
                    _md_table_cell(row.get("solvable")),
                    _md_table_cell(row.get("selected_route")),
                    _md_table_cell(row.get("route_result")),
                    _md_table_cell(row.get("repair_route_selected")),
                    _md_table_cell(row.get("best_artifact_to_open_first")),
                    _md_table_cell(row.get("error_message")),
                ]
            )
            + " |"
        )
    _atomic_save_text("\n".join(md_lines) + "\n", summary_md_path)
    return summary_doc


def run_iter9_image_sweep(
    args: argparse.Namespace,
    *,
    raw_argv: list[str],
    project_root: Path,
) -> int:
    started_wall = time.perf_counter()
    started_at_utc = _utc_now_z()
    image_dir_path = Path(args.image_dir).expanduser().resolve()
    batch_id = _build_image_sweep_batch_id(
        image_dir=image_dir_path,
        image_glob=args.image_glob,
        board_w=int(args.board_w),
        seed=int(args.seed),
        run_tag=args.run_tag,
    )
    out_root = (
        Path(args.out_root).expanduser().resolve()
        if args.out_root
        else (project_root / RESULTS_ROOT / batch_id).resolve()
    )
    out_root.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    images_discovered = 0
    batch_warmup_s = 0.0
    any_failed = False

    try:
        images = discover_source_images(
            image_dir_path,
            args.image_glob,
            recursive=bool(args.recursive),
            max_images=args.max_images,
        )
        images_discovered = len(images)
    except Exception as error:
        rows.append(
            _image_sweep_failure_row(
                batch_index=0,
                image_path=Path(args.image_dir).expanduser(),
                source_cfg=None,
                child_run_dir=None,
                board_label=None,
                seed=int(args.seed),
                error=error,
                project_root=project_root,
            )
        )
        write_iter9_image_sweep_summaries(
            out_root=out_root,
            batch_id=batch_id,
            image_dir=_relative_or_absolute(image_dir_path, project_root),
            image_glob=args.image_glob,
            recursive=bool(args.recursive),
            board_w=int(args.board_w),
            seed=int(args.seed),
            started_at_utc=started_at_utc,
            finished_at_utc=_utc_now_z(),
            duration_wall_s=(time.perf_counter() - started_wall),
            batch_warmup_s=0.0,
            rows=rows,
            images_discovered=0,
        )
        return 1

    colliding_stem_tokens = _colliding_sanitized_stem_tokens(images)

    try:
        warmup_start = time.perf_counter()
        sa_fn = compile_sa_kernel()
        ensure_solver_warmed()
        batch_warmup_s = time.perf_counter() - warmup_start
    except Exception as error:
        rows.append(
            {
                "batch_index": 0,
                "image_path": _relative_or_absolute(image_dir_path, project_root),
                "image_name": None,
                "image_stem": None,
                "source_image_sha256": None,
                "status": "failed",
                "child_run_dir": None,
                "metrics_path": None,
                "best_artifact_to_open_first": None,
                "board": None,
                "seed": int(args.seed),
                "n_unknown": None,
                "coverage": None,
                "solvable": None,
                "mean_abs_error": None,
                "repair_route_selected": None,
                "selected_route": None,
                "route_result": None,
                "route_outcome_detail": None,
                "next_recommended_route": None,
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
        )
        write_iter9_image_sweep_summaries(
            out_root=out_root,
            batch_id=batch_id,
            image_dir=_relative_or_absolute(image_dir_path, project_root),
            image_glob=args.image_glob,
            recursive=bool(args.recursive),
            board_w=int(args.board_w),
            seed=int(args.seed),
            started_at_utc=started_at_utc,
            finished_at_utc=_utc_now_z(),
            duration_wall_s=(time.perf_counter() - started_wall),
            batch_warmup_s=batch_warmup_s,
            rows=rows,
            images_discovered=images_discovered,
        )
        return 1

    for batch_index, image_path in enumerate(images, start=1):
        source_cfg: SourceImageConfig | None = None
        child_out_dir: Path | None = None
        board_label: str | None = None
        try:
            source_cfg = resolve_source_image_config(
                str(image_path),
                project_root=project_root,
                allow_noncanonical=args.allow_noncanonical,
                manifest_path=None,
            )
            source_validation = verify_source_image(
                str(source_cfg.absolute_path),
                halt_on_failure=False,
                verbose=True,
                allow_noncanonical=args.allow_noncanonical,
                manifest_path=None,
                return_details=True,
            )
            if not source_validation.get("ok"):
                raise ValueError(f"Source image validation failed: {source_cfg.absolute_path.as_posix()}")
            sizing = derive_board_from_width(
                # str(source_cfg.absolute_path), int(args.board_w), min_width=300, ratio_tolerance=0.005  # Default value prior to testing
                str(source_cfg.absolute_path), int(args.board_w), min_width=50, ratio_tolerance=0.005
            )
            board_label = f"{int(sizing['board_width'])}x{int(sizing['board_height'])}"
            child_out_dir = build_image_sweep_child_out_dir(
                out_root,
                source_cfg=source_cfg,
                board_label=board_label,
                seed=int(args.seed),
                colliding_stem_tokens=colliding_stem_tokens,
            )
            expected_metrics_path = child_out_dir / f"metrics_iter9_{board_label}.json"
            if args.skip_existing and expected_metrics_path.exists():
                rows.append(
                    _image_sweep_skipped_existing_row(
                        batch_index=batch_index,
                        source_cfg=source_cfg,
                        child_run_dir=child_out_dir,
                        metrics_path=expected_metrics_path,
                        board_label=board_label,
                        seed=int(args.seed),
                        project_root=project_root,
                    )
                )
                continue

            batch_context = {
                "schema_version": "iter9_image_sweep_context.v1",
                "batch_mode": "iter9_image_sweep",
                "batch_id": batch_id,
                "batch_index": int(batch_index),
                "batch_total": int(images_discovered),
                "images_discovered": int(images_discovered),
                "image_dir": _relative_or_absolute(image_dir_path, project_root),
                "image_glob": args.image_glob,
                "recursive": bool(args.recursive),
                "batch_out_root": _relative_or_absolute(out_root, project_root),
                "child_run_dir": _relative_or_absolute(child_out_dir, project_root),
                "continue_on_error": bool(args.continue_on_error),
                "skip_existing": bool(args.skip_existing),
                "max_images": int(args.max_images) if args.max_images is not None else None,
                "batch_warmup_s": float(batch_warmup_s),
                "child_warmup_s": 0.0,
            }
            metrics_doc = run_iter9_single(
                args,
                source_cfg=source_cfg,
                source_validation=source_validation,
                out_dir_path=child_out_dir,
                project_root=project_root,
                sa_fn=sa_fn,
                raw_argv=raw_argv,
                started_wall=time.perf_counter(),
                started_at_utc=_utc_now_z(),
                warmup_s=0.0,
                batch_context=batch_context,
            )
            rows.append(
                _image_sweep_success_row(
                    batch_index=batch_index,
                    source_cfg=source_cfg,
                    child_run_dir=child_out_dir,
                    metrics_doc=metrics_doc,
                    project_root=project_root,
                )
            )
        except KeyboardInterrupt:
            raise
        except Exception as error:
            any_failed = True
            rows.append(
                _image_sweep_failure_row(
                    batch_index=batch_index,
                    image_path=image_path,
                    source_cfg=source_cfg,
                    child_run_dir=child_out_dir,
                    board_label=board_label,
                    seed=int(args.seed),
                    error=error,
                    project_root=project_root,
                )
            )
            print(f"[image-sweep] failed child {batch_index}/{images_discovered}: {error}")
            if not args.continue_on_error:
                break

    write_iter9_image_sweep_summaries(
        out_root=out_root,
        batch_id=batch_id,
        image_dir=_relative_or_absolute(image_dir_path, project_root),
        image_glob=args.image_glob,
        recursive=bool(args.recursive),
        board_w=int(args.board_w),
        seed=int(args.seed),
        started_at_utc=started_at_utc,
        finished_at_utc=_utc_now_z(),
        duration_wall_s=(time.perf_counter() - started_wall),
        batch_warmup_s=batch_warmup_s,
        rows=rows,
        images_discovered=images_discovered,
    )
    return 1 if any_failed else 0


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parse_args(raw_argv)
    started_wall = time.perf_counter()
    started_at_utc = _utc_now_z()
    project_root = Path(__file__).resolve().parent

    if args.image_dir is not None:
        return run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=project_root)

    source_cfg = resolve_source_image_config(
        args.image,
        project_root=project_root,
        allow_noncanonical=args.allow_noncanonical,
        manifest_path=args.image_manifest,
    )
    source_validation = verify_source_image(
        str(source_cfg.absolute_path),
        halt_on_failure=True,
        verbose=True,
        allow_noncanonical=args.allow_noncanonical,
        manifest_path=args.image_manifest,
        return_details=True,
    )

    run_id = _build_run_id(source_cfg.stem, int(args.board_w), int(args.seed), args.run_tag)
    out_dir_path = (
        Path(args.out_dir).expanduser().resolve()
        if args.out_dir
        else (project_root / RESULTS_ROOT / run_id).resolve()
    )

    phase_start = time.perf_counter()
    sa_fn = compile_sa_kernel()
    ensure_solver_warmed()
    warmup_s = time.perf_counter() - phase_start

    metrics_doc = run_iter9_single(
        args,
        source_cfg=source_cfg,
        source_validation=source_validation,
        out_dir_path=out_dir_path,
        project_root=project_root,
        sa_fn=sa_fn,
        raw_argv=raw_argv,
        started_wall=started_wall,
        started_at_utc=started_at_utc,
        warmup_s=warmup_s,
        batch_context=None,
    )
    if args.demo_gui:
        from demos.iter9_visual_solver.cli.launch_from_iter9 import run_demo_from_completed_iter9_run

        board_label = str(metrics_doc["board"])
        demo_config_path = Path(args.demo_config).expanduser()
        if not demo_config_path.is_absolute():
            demo_config_path = (project_root / demo_config_path).resolve()
        return int(
            run_demo_from_completed_iter9_run(
                grid_path=out_dir_path / "grid_iter9_latest.npy",
                metrics_path=out_dir_path / f"metrics_iter9_{board_label}.json",
                config_path=demo_config_path,
                event_trace_path=None,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
