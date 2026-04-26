#!/usr/bin/env python3
"""
run_iter9.py

Production Iter9 pipeline with explicit source-image runtime contract.
"""

from __future__ import annotations

import argparse
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
from report import render_repair_overlay, render_report
from sa import compile_sa_kernel, run_sa
from solver import ensure_solver_warmed, solve_board
from source_config import SourceImageConfig, resolve_source_image_config

DEFAULT_IMAGE = "assets/input_source_image.png"
DEFAULT_BOARD_W = 300
DEFAULT_SEED = 42
RESULTS_ROOT = "results/iter9"
SCHEMA_VERSION = "metrics.v2.source_image_runtime_contract"

# Pipeline config (existing Iter9 settings preserved)
DENSITY = 0.22
BORDER = 3
COARSE_ITERS = 2_000_000
T_COARSE = 10.0
ALPHA_COARSE = 0.99998
FINE_ITERS = 8_000_000
T_FINE = 3.5
ALPHA_FINE = 0.999996
REFINE1_ITERS = 2_000_000
T_REFINE1 = 2.0
ALPHA_REFINE1 = 0.999997
REFINE2_ITERS = 2_000_000
T_REFINE2 = 1.7
ALPHA_REFINE2 = 0.999997
REFINE3_ITERS = 4_000_000
T_REFINE3 = 1.4
ALPHA_REFINE3 = 0.999998
T_MIN = 0.001
BP_TRUE = 8.0
BP_TRANS = 1.0
HI_BOOST = 18.0
HI_THR = 3.0
UF_FACTOR = 1.8
SEAL_THR = 0.6
SEAL_STR = 20.0
PW_KNEE = 4.0
PW_T_MAX = 6.0


def _to_posix_path(path: Path | str) -> str:
    return Path(path).resolve().as_posix()


def _atomic_save_json(data: dict, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
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


def _build_run_id(image_stem: str, board_w: int, seed: int, run_tag: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{stamp}_{image_stem}_{board_w}w_seed{seed}"
    safe_tag = _sanitize_run_tag(run_tag)
    if safe_tag:
        run_id = f"{run_id}_{safe_tag}"
    return run_id


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
) -> dict:
    risk = "No critical risks detected."
    if warnings:
        risk = warnings[0].get("message", risk)
    return {
        "one_sentence_result": (
            f"The run used {source_cfg.command_arg} at {board_label} with seed {seed} "
            f"and ended with n_unknown={n_unknown} through {selected_route}."
        ),
        "main_success": "The routed repair pipeline completed and produced final artifacts.",
        "main_risk": risk,
        "best_artifact_to_open_first": artifact_inventory.get("repair_overlay_png"),
        "best_metric_to_check_first": "n_unknown",
        "next_recommended_check": "Review final visual output and repair overlay before promotion.",
    }


def _relative_or_absolute(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return path.resolve().as_posix()


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
        }
    )
    return document


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Iter9 reconstruction pipeline.")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Input image path.")
    parser.add_argument("--out-dir", default=None, help="Exact output run directory.")
    parser.add_argument("--board-w", type=int, default=DEFAULT_BOARD_W, help="Board width.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Random seed.")
    parser.add_argument("--allow-noncanonical", action="store_true", help="Allow noncanonical image.")
    parser.add_argument("--image-manifest", default=None, help="Path to image manifest JSON.")
    parser.add_argument("--run-tag", default="", help="Optional run tag appended to run id.")
    return parser.parse_args(argv)


def main() -> int:
    args = parse_args()
    started_wall = time.perf_counter()
    started_at_utc = _utc_now_z()
    project_root = Path(__file__).resolve().parent

    source_cfg = resolve_source_image_config(
        args.image,
        project_root=project_root,
        allow_noncanonical=args.allow_noncanonical,
        manifest_path=args.image_manifest,
    )

    image_validation = verify_source_image(
        str(source_cfg.absolute_path),
        halt_on_failure=True,
        verbose=True,
        allow_noncanonical=args.allow_noncanonical,
        manifest_path=args.image_manifest,
        return_details=True,
    )

    run_id = _build_run_id(source_cfg.stem, int(args.board_w), int(args.seed), args.run_tag)
    if args.out_dir:
        out_dir_path = Path(args.out_dir).expanduser().resolve()
    else:
        out_dir_path = (project_root / RESULTS_ROOT / run_id).resolve()
    os.makedirs(out_dir_path, exist_ok=True)

    print("\n" + "=" * 60)
    print("Mine-Streaker - Iteration 9 - Production Pipeline")
    print("  Phase 1 repair + late-stage repair routing")
    print(f"  source_image={source_cfg.absolute_path.as_posix()}")
    print("=" * 60)

    phase_timers: dict[str, float] = {}
    phase_start = time.perf_counter()
    sa_fn = compile_sa_kernel()
    ensure_solver_warmed()
    phase_timers["warmup"] = time.perf_counter() - phase_start

    phase_start = time.perf_counter()
    sizing = derive_board_from_width(
        str(source_cfg.absolute_path), int(args.board_w), min_width=300, ratio_tolerance=0.005
    )
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
    target_c = apply_piecewise_T_compression(
        load_image_smart(str(source_cfg.absolute_path), cw, ch, invert=True), PW_KNEE, PW_T_MAX
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
    grid, _, phase1_reason = run_phase1_repair(
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
    overlay_png = out_dir_path / f"repair_overlay_{board_label}.png"

    route_artifact_meta = {
        "run_id": run_id,
        "generated_at_utc": _utc_now_z(),
        "source_image_project_relative_path": source_cfg.project_relative_path,
        "source_image_sha256": source_cfg.sha256,
        "metrics_path": _relative_or_absolute(metrics_path, project_root),
    }
    route_artifacts = write_repair_route_artifacts(
        str(out_dir_path),
        board_label,
        route,
        artifact_metadata=route_artifact_meta,
    )

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
    phase_timers["render_and_write"] = time.perf_counter() - phase_start

    _atomic_save_npy(grid, grid_path)
    _atomic_save_npy(grid, grid_latest_path)

    duration_wall_s = time.perf_counter() - started_wall
    finished_at_utc = _utc_now_z()

    flat_metrics = {
        "label": board_label,
        "board": board_label,
        "cells": int(bw * bh),
        "loss_per_cell": float(err.var()),
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
        "repair_reason": f"phase1={phase1_reason}+route={route.selected_route}",
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
        "repair_route_selected": route.selected_route,
        "repair_route_result": route.route_result,
        "dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
        "sealed_cluster_count": route.failure_taxonomy.get("sealed_cluster_count"),
        "sealed_single_mesa_count": route.failure_taxonomy.get("sealed_single_mesa_count"),
        "sealed_multi_cell_cluster_count": route.failure_taxonomy.get("sealed_multi_cell_cluster_count"),
        "phase2_fixes": len(route.phase2_log),
        "last100_fixes": len(route.last100_log),
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
        "argv": [str(arg) for arg in sys.argv],
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
        "selected_route": route.selected_route,
        "route_result": route.route_result,
        "dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
        "sealed_cluster_count": int(route.failure_taxonomy.get("sealed_cluster_count", 0) or 0),
        "phase2_fixes": len(route.phase2_log),
        "last100_fixes": len(route.last100_log),
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
        "repair_overlay_png": _relative_or_absolute(overlay_png, project_root),
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
    )
    _atomic_save_json(metrics_doc, metrics_path)

    print(f"\n  Results written to: {out_dir_path.as_posix()}")
    print(f"  Route: {route.selected_route}  n_unknown={sr_final.n_unknown}  coverage={sr_final.coverage:.5f}")
    print(f"  Total time: {duration_wall_s:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
