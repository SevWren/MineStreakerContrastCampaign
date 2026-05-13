#!/usr/bin/env python3
"""
run_benchmark.py - Normal benchmark matrix plus fixed regression validation.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image as PILImage
from scipy.ndimage import convolve

from assets.image_guard import verify_source_image
from board_sizing import derive_board_from_width
from core import (
    apply_piecewise_T_compression,
    assert_board_valid,
    compute_N,
    compute_sealing_prevention_weights,
    compute_zone_aware_weights,
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
DEFAULT_WIDTHS = [300, 360, 420]
DEFAULT_SEEDS = [300, 301, 302]
DEFAULT_BENCHMARK_RESULTS_ROOT = "results/benchmark"
SCHEMA_VERSION = "metrics.v2.source_image_runtime_contract"

REGRESSION_CASES = [
    {
        "name": "line_art_irl_9_phase2_full_repair",
        "image_path": "assets/line_art_irl_9.png",
        "image_name": "line_art_irl_9.png",
        "board_w": 300,
        "board_h": 942,
        "seeds": [11, 22, 33],
        "expected_baseline_unknowns": [89, 20, 37],
        "expected_final_unknown": 0,
        "expected_route": "phase2_full_repair",
        "baseline_root": "results/line_art_robustness_campaign_2/runs/global46",
    }
]

REGRESSION_INCOMPATIBLE_FLAGS = (
    "--image",
    "--widths",
    "--seeds",
    "--allow-noncanonical",
    "--image-manifest",
    "--include-regressions",
)

# Iter9 runtime settings preserved.
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


def _utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _to_posix(path: Path | str) -> str:
    return Path(path).resolve().as_posix()


def _relative_or_absolute(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except Exception:
        return path.resolve().as_posix()


def _atomic_write_json(payload: dict | list, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    os.replace(tmp, path)


def _atomic_write_text(text: str, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _atomic_write_csv(fieldnames: list[str], rows: list[dict], path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})
    os.replace(tmp, path)


def _atomic_write_npy(array: np.ndarray, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp.npy")
    np.save(tmp, array)
    os.replace(tmp, path)


def _atomic_render(render_fn, save_path: Path, *args, **kwargs) -> None:
    tmp_path = save_path.with_suffix(save_path.suffix + ".tmp.png")
    kwargs = dict(kwargs)
    kwargs["save_path"] = str(tmp_path)
    render_fn(*args, **kwargs)
    os.replace(tmp_path, save_path)


def _build_benchmark_run_id(image_stem: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}_{image_stem}_benchmark"


def _child_dir_name(board_w: int, board_h: int, seed: int) -> str:
    return f"{board_w}x{board_h}_seed{seed}"


def benchmark_child_artifact_filenames(board: str) -> dict:
    return {
        "metrics": f"metrics_{board}.json",
        "grid": f"grid_{board}.npy",
        "visual": f"visual_{board}.png",
        "visual_explained": f"visual_{board}_explained.png",
        "overlay": f"repair_overlay_{board}.png",
        "overlay_explained": f"repair_overlay_{board}_explained.png",
        "failure_taxonomy": "failure_taxonomy.json",
        "repair_route_decision": "repair_route_decision.json",
        "visual_delta_summary": "visual_delta_summary.json",
    }


def _find_regression_incompatible_flags(raw_argv: list[str]) -> list[str]:
    found: list[str] = []
    for token in raw_argv[1:]:
        if token == "--":
            break
        for flag in REGRESSION_INCOMPATIBLE_FLAGS:
            if token == flag or token.startswith(f"{flag}="):
                if flag not in found:
                    found.append(flag)
    return found


def _validate_regression_flag_mix(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
    raw_argv: list[str],
) -> None:
    if not args.regression_only:
        return
    conflicts = _find_regression_incompatible_flags(raw_argv)
    if conflicts:
        parser.error(
            "--regression-only cannot be combined with these explicitly supplied normal-mode flags: "
            + ", ".join(conflicts)
        )


def parse_args(argv: list[str] | None = None, raw_argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run benchmark matrix and route-aware regressions.")
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Source image path for normal benchmark mode.")
    parser.add_argument("--widths", nargs="+", type=int, default=list(DEFAULT_WIDTHS), help="Benchmark board widths.")
    parser.add_argument("--seeds", nargs="+", type=int, default=list(DEFAULT_SEEDS), help="Benchmark random seeds.")
    parser.add_argument("--out-dir", default=None, help="Benchmark output root. In normal mode this is the benchmark-run root.")
    parser.add_argument("--allow-noncanonical", action="store_true", help="Allow non-default source image without manifest match.")
    parser.add_argument("--image-manifest", default=None, help="Optional source image manifest path.")
    parser.add_argument("--regression-only", action="store_true", help="Run only fixed regression cases.")
    parser.add_argument(
        "--include-regressions",
        action="store_true",
        help="Also run fixed regression cases after normal benchmark mode.",
    )
    args = parser.parse_args(argv)
    raw = raw_argv if raw_argv is not None else (sys.argv if argv is None else ["run_benchmark.py", *argv])
    _validate_regression_flag_mix(parser, args, raw)
    return args


def _target_stats(target_eval: np.ndarray, hi_mask: np.ndarray, bg_mask: np.ndarray) -> dict:
    return {
        "min": float(np.min(target_eval)),
        "max": float(np.max(target_eval)),
        "mean": float(np.mean(target_eval)),
        "std": float(np.std(target_eval)),
        "hi_pct": float(np.mean(hi_mask) * 100.0),
        "bg_pct": float(np.mean(bg_mask) * 100.0),
    }


def _build_child_metrics_document(
    flat_metrics: dict,
    *,
    run_identity: dict,
    run_timing: dict,
    source_image: dict,
    source_image_validation: dict,
    board_sizing: dict,
    target_stats: dict,
    route_summary: dict,
    artifact_inventory: dict,
    phase_timing: dict,
) -> dict:
    document = dict(flat_metrics)
    document.update(
        {
            "schema_version": SCHEMA_VERSION,
            "run_identity": run_identity,
            "run_timing": run_timing,
            "project_identity": {
                "project_root": _to_posix(Path(__file__).resolve().parent),
                "project_root_name": Path(__file__).resolve().parent.name,
            },
            "command_invocation": {"entry_point": "run_benchmark.py", "argv": [str(v) for v in sys.argv]},
            "source_image": source_image,
            "source_image_analysis": target_stats,
            "effective_config": {
                "benchmark_mode": "normal",
                "benchmark_run_id": run_identity["benchmark_run_id"],
                "board_width": run_identity["board_width"],
                "board_height": run_identity["board_height"],
                "seed": run_identity["seed"],
                "child_run_dir": run_identity["child_run_dir"],
            },
            "board_sizing": board_sizing,
            "preprocessing_config": {"loader": "load_image_smart", "invert": True},
            "target_field_stats": target_stats,
            "weight_config": {
                "bp_true": BP_TRUE,
                "bp_trans": BP_TRANS,
                "hi_boost": HI_BOOST,
                "hi_threshold": HI_THR,
                "underfill_factor": UF_FACTOR,
            },
            "corridor_config": {"border": BORDER, "corridor_pct": flat_metrics["corridor_pct"]},
            "sa_config": {
                "density": DENSITY,
                "coarse_iters": COARSE_ITERS,
                "fine_iters": FINE_ITERS,
                "refine_iters": [REFINE1_ITERS, REFINE2_ITERS, REFINE3_ITERS],
            },
            "repair_config": {
                "phase1_budget_s": flat_metrics["phase1_budget_s"],
                "phase2_budget_s": 360.0,
                "last100_budget_s": 300.0,
                "last100_unknown_threshold": 100,
            },
            "solver_summary": flat_metrics["solver_summary"],
            "repair_route_summary": route_summary,
            "visual_quality_summary": {
                "mean_abs_error": flat_metrics["mean_abs_error"],
                "visual_delta": flat_metrics["visual_delta"],
                "pct_within_1": flat_metrics["pct_within_1"],
            },
            "runtime_phase_timing_s": phase_timing,
            "environment": {
                "python_version": sys.version.split()[0],
                "platform": sys.platform,
                "cpu_count": os.cpu_count(),
            },
            "artifact_inventory": artifact_inventory,
            "validation_gates": {
                "source_image_validated": bool(source_image_validation.get("ok")),
                "canonical_image_match": source_image_validation.get("canonical_match"),
                "noncanonical_allowed": bool(source_image_validation.get("noncanonical_allowed")),
                "n_unknown_zero": bool(flat_metrics["n_unknown"] == 0),
                "coverage_at_least_9999": bool(flat_metrics["coverage"] >= 0.9999),
                "solvable_true": bool(flat_metrics["solvable"]),
            },
            "warnings_and_exceptions": list(source_image_validation.get("warnings", [])),
            "llm_review_summary": {
                "one_sentence_result": (
                    f"Benchmark child run {run_identity['board']} seed={run_identity['seed']} "
                    f"finished with route={flat_metrics['repair_route_selected']} "
                    f"and n_unknown={flat_metrics['n_unknown']}."
                ),
                "best_artifact_to_open_first": artifact_inventory.get("visual_explained_png"),
                "best_artifact_to_open_second": artifact_inventory.get("visual_png"),
                "best_repair_artifact_to_open_first": artifact_inventory.get("repair_overlay_explained_png"),
                "best_repair_artifact_to_open_second": artifact_inventory.get("repair_overlay_png"),
                "best_metric_to_check_first": "n_unknown",
            },
            "benchmark_mode": "normal",
            "benchmark_run_id": run_identity["benchmark_run_id"],
            "child_run_dir": run_identity["child_run_dir"],
            "source_image_validation": source_image_validation,
        }
    )
    return document


def run_normal_child(
    *,
    source_cfg: SourceImageConfig,
    source_validation: dict,
    board_w: int,
    seed: int,
    sa_fn,
    benchmark_root: Path,
    benchmark_run_id: str,
    project_root: Path,
) -> dict:
    started_wall = time.perf_counter()
    started_at = _utc_now_z()
    phase_timing: dict[str, float] = {}

    sizing = derive_board_from_width(str(source_cfg.absolute_path), board_w, min_width=300, ratio_tolerance=0.005)
    board_h = int(sizing["board_height"])
    board = f"{board_w}x{board_h}"
    child_dir = benchmark_root / _child_dir_name(board_w, board_h, seed)
    os.makedirs(child_dir, exist_ok=True)

    phase_start = time.perf_counter()
    target_eval = load_image_smart(str(source_cfg.absolute_path), board_w, board_h, invert=True)
    target = apply_piecewise_T_compression(target_eval, PW_KNEE, PW_T_MAX)
    w_zone = compute_zone_aware_weights(target, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    forbidden, cpct, _, _ = build_adaptive_corridors(target, border=BORDER)
    phase_timing["image_load_and_weights"] = float(time.perf_counter() - phase_start)

    k8 = np.ones((3, 3), dtype=np.int32)
    k8[1, 1] = 0
    hi_mask = target_eval >= HI_THR
    bg_mask = target_eval < 1.0
    adj = convolve(hi_mask.astype(np.int32), k8, mode="constant", cval=0) > 0
    true_bg = bg_mask & ~adj
    rng = np.random.default_rng(seed)

    phase_start = time.perf_counter()
    c_w, c_h = board_w // 2, board_h // 2
    target_c = apply_piecewise_T_compression(
        load_image_smart(str(source_cfg.absolute_path), c_w, c_h, invert=True), PW_KNEE, PW_T_MAX
    )
    weight_c = compute_zone_aware_weights(target_c, BP_TRUE, BP_TRANS, HI_BOOST, HI_THR)
    forbidden_c, _, _, _ = build_adaptive_corridors(target_c, border=BORDER)
    grid_c = np.zeros((c_h, c_w), dtype=np.int8)
    available_c = np.argwhere(forbidden_c == 0)
    picks = rng.choice(len(available_c), size=min(int(DENSITY * c_w * c_h), len(available_c)), replace=False)
    for idx in picks:
        grid_c[available_c[idx][0], available_c[idx][1]] = 1
    grid_c, _, hist_c = run_sa(
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
        seed,
    )
    coarse_img = PILImage.fromarray(grid_c.astype(np.uint8) * 255)
    grid = (np.array(coarse_img.resize((board_w, board_h), PILImage.NEAREST), dtype=np.uint8) > 127).astype(np.int8)
    grid[forbidden == 1] = 0
    phase_timing["coarse_sa"] = float(time.perf_counter() - phase_start)

    phase_start = time.perf_counter()
    grid, _, hist_f = run_sa(
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
        seed + 1,
    )
    grid[forbidden == 1] = 0
    phase_timing["fine_sa"] = float(time.perf_counter() - phase_start)

    phase_start = time.perf_counter()
    histories = [hist_c, hist_f]
    for p_idx, (iters, temp, alpha) in enumerate(
        [
            (REFINE1_ITERS, T_REFINE1, ALPHA_REFINE1),
            (REFINE2_ITERS, T_REFINE2, ALPHA_REFINE2),
            (REFINE3_ITERS, T_REFINE3, ALPHA_REFINE3),
        ]
    ):
        n_cur = compute_N(grid)
        underfill = np.clip(target - n_cur.astype(np.float32), 0.0, 8.0) / 8.0
        weight_ref = (w_zone * (1.0 + UF_FACTOR * underfill)).astype(np.float32)
        if p_idx < 2:
            weight_ref = compute_sealing_prevention_weights(
                weight_ref,
                grid,
                target,
                HI_THR,
                SEAL_THR,
                SEAL_STR,
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
            seed + 2 + p_idx,
        )
        grid[forbidden == 1] = 0
        histories.append(hist)
    phase_timing["refine_sa_total"] = float(time.perf_counter() - phase_start)

    assert_board_valid(grid, forbidden, f"post-SA-{board}-s{seed}")
    sr_post_sa = solve_board(grid, max_rounds=300, mode="full")
    sr_pre = solve_board(grid, max_rounds=50, mode="trial")
    baseline_unknown = int(sr_pre.n_unknown)

    phase_start = time.perf_counter()
    phase1_budget = max(60.0, sr_pre.n_unknown * 0.15 + 30.0)
    phase1_result = run_phase1_repair(
        grid,
        target,
        w_zone,
        forbidden,
        time_budget_s=min(phase1_budget, 120.0),
        max_rounds=300,
        search_radius=6,
        verbose=False,
        checkpoint_dir=str(child_dir),
    )
    grid = phase1_result.grid
    phase1_reason = phase1_result.stop_reason
    phase1_repair_hit_time_budget = bool(phase1_result.phase1_repair_hit_time_budget)
    grid[forbidden == 1] = 0
    assert_board_valid(grid, forbidden, f"post-p1-{board}-s{seed}")
    sr_phase1 = solve_board(grid, max_rounds=300, mode="full")
    phase_timing["phase1_repair"] = float(time.perf_counter() - phase_start)

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
    assert_board_valid(grid, forbidden, f"post-route-{board}-s{seed}")
    sr_final = route.sr
    phase_timing["late_stage_routing"] = float(time.perf_counter() - phase_start)

    n_final = compute_N(grid)
    err = np.abs(n_final.astype(np.float32) - target_eval)
    duration_s = float(time.perf_counter() - started_wall)
    finished_at = _utc_now_z()

    artifact_files = benchmark_child_artifact_filenames(board)
    metrics_path = child_dir / artifact_files["metrics"]
    grid_path = child_dir / artifact_files["grid"]
    visual_path = child_dir / artifact_files["visual"]
    visual_explained_path = child_dir / artifact_files["visual_explained"]
    overlay_path = child_dir / artifact_files["overlay"]
    overlay_explained_path = child_dir / artifact_files["overlay_explained"]

    route_artifact_meta = {
        "run_id": f"{benchmark_run_id}_{board}_seed{seed}",
        "generated_at_utc": _utc_now_z(),
        "source_image_project_relative_path": source_cfg.project_relative_path,
        "source_image_sha256": source_cfg.sha256,
        "metrics_path": _relative_or_absolute(metrics_path, project_root),
        "phase1_repair_hit_time_budget": phase1_repair_hit_time_budget,
        "phase2_full_repair_hit_time_budget": bool(route.phase2_full_repair_hit_time_budget),
        "last100_repair_hit_time_budget": bool(route.last100_repair_hit_time_budget),
    }
    route_artifacts = write_repair_route_artifacts(
        str(child_dir),
        board,
        route,
        artifact_metadata=route_artifact_meta,
    )

    removed_mines = int(np.sum((grid_before_route == 1) & (grid == 0)))
    added_mines = int(np.sum((grid_before_route == 0) & (grid == 1)))
    render_metrics = {
        "run_id": f"{benchmark_run_id}_{board}_seed{seed}",
        "board": board,
        "board_width": int(board_w),
        "board_height": int(board_h),
        "seed": int(seed),
        "source_image": {
            "name": source_cfg.name,
            "project_relative_path": source_cfg.project_relative_path,
        },
        **route.route_state_fields(),
        "repair_route_selected": route.selected_route,
        "repair_route_result": route.route_result,
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
        "total_time_s": float(duration_s),
    }

    phase_start = time.perf_counter()
    _atomic_render(
        render_repair_overlay,
        overlay_path,
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
        visual_path,
        target_eval,
        grid,
        sr_final,
        all_history,
        f"Benchmark {board} seed={seed}",
        dpi=120,
    )
    _atomic_render(
        render_repair_overlay_explained,
        overlay_explained_path,
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
        visual_explained_path,
        target_eval,
        grid,
        sr_final,
        all_history,
        f"Benchmark explained report {board} seed={seed}",
        metrics=render_metrics,
        dpi=120,
    )
    phase_timing["render_and_write"] = float(time.perf_counter() - phase_start)

    _atomic_write_npy(grid, grid_path)

    run_identity = {
        "run_id": f"{benchmark_run_id}_{board}_seed{seed}",
        "benchmark_run_id": benchmark_run_id,
        "entry_point": "run_benchmark.py",
        "board": board,
        "board_width": board_w,
        "board_height": board_h,
        "seed": seed,
        "child_run_dir": _relative_or_absolute(child_dir, project_root),
    }
    run_timing = {
        "started_at_utc": started_at,
        "finished_at_utc": finished_at,
        "duration_wall_s": duration_s,
    }
    route_summary = {
        **route.route_state_fields(),
        "repair_route_selected": route.selected_route,
        "repair_route_result": route.route_result,
        "dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
        "sealed_cluster_count": int(route.failure_taxonomy.get("sealed_cluster_count", 0) or 0),
        "phase1_repair_hit_time_budget": phase1_repair_hit_time_budget,
        "phase2_full_repair_hit_time_budget": bool(route.phase2_full_repair_hit_time_budget),
        "last100_repair_hit_time_budget": bool(route.last100_repair_hit_time_budget),
        "sa_rerun_invoked": bool(route.decision.get("sa_rerun_invoked", False)),
    }
    artifact_inventory = {
        "metrics_json": _relative_or_absolute(metrics_path, project_root),
        "grid_npy": _relative_or_absolute(grid_path, project_root),
        "visual_png": _relative_or_absolute(visual_path, project_root),
        "visual_explained_png": _relative_or_absolute(visual_explained_path, project_root),
        "repair_overlay_png": _relative_or_absolute(overlay_path, project_root),
        "repair_overlay_explained_png": _relative_or_absolute(overlay_explained_path, project_root),
        "failure_taxonomy_json": _relative_or_absolute(Path(route_artifacts["failure_taxonomy"]), project_root),
        "repair_route_decision_json": _relative_or_absolute(
            Path(route_artifacts["repair_route_decision"]),
            project_root,
        ),
        "visual_delta_summary_json": _relative_or_absolute(
            Path(route_artifacts["visual_delta_summary"]),
            project_root,
        ),
    }
    solver_summary = {
        "post_sa": {"n_unknown": int(sr_post_sa.n_unknown), "coverage": float(sr_post_sa.coverage)},
        "post_phase1": {"n_unknown": int(sr_phase1.n_unknown), "coverage": float(sr_phase1.coverage)},
        "post_routing": {"n_unknown": int(sr_final.n_unknown), "coverage": float(sr_final.coverage)},
    }
    flat_metrics = {
        "label": board,
        "board": board,
        "seed": seed,
        "cells": int(board_w * board_h),
        "benchmark_mode": "normal",
        "benchmark_run_id": benchmark_run_id,
        "child_run_dir": _relative_or_absolute(child_dir, project_root),
        "image_name": source_cfg.name,
        "image_stem": source_cfg.stem,
        "source_image_sha256": source_cfg.sha256,
        "source_image_project_relative_path": source_cfg.project_relative_path,
        "baseline_n_unknown": baseline_unknown,
        "n_unknown": int(sr_final.n_unknown),
        "coverage": float(sr_final.coverage),
        "solvable": bool(sr_final.solvable),
        "mine_accuracy": float(sr_final.mine_accuracy),
        "hi_err": float(err[hi_mask].mean()) if np.any(hi_mask) else 0.0,
        "true_bg_err": float(err[true_bg].mean()) if np.any(true_bg) else 0.0,
        "mean_abs_error": float(err.mean()),
        "pct_within_1": float(np.mean(err <= 1.0) * 100.0),
        "mine_density": float(grid.mean()),
        "corridor_pct": float(cpct),
        "repair_reason": (
            f"phase1={phase1_reason}"
            f"+selected_route={route.selected_route}"
            f"+route_result={route.route_result}"
            f"+route_outcome_detail={route.route_outcome_detail}"
            f"+next_recommended_route={route.next_recommended_route}"
        ),
        **route.route_state_fields(),
        "repair_route_selected": route.selected_route,
        "repair_route_result": route.route_result,
        "dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
        "sealed_cluster_count": int(route.failure_taxonomy.get("sealed_cluster_count", 0) or 0),
        "phase2_fixes": route.phase2_full_repair_accepted_move_count,
        "last100_fixes": route.last100_n_fixes,
        "phase1_repair_hit_time_budget": phase1_repair_hit_time_budget,
        "phase2_full_repair_hit_time_budget": bool(route.phase2_full_repair_hit_time_budget),
        "last100_repair_hit_time_budget": bool(route.last100_repair_hit_time_budget),
        "visual_delta": route.visual_delta_summary.get("visual_delta"),
        "total_time_s": duration_s,
        "source_ratio": float(sizing["source_ratio"]),
        "board_ratio": float(sizing["board_ratio"]),
        "aspect_ratio_relative_error": float(sizing["aspect_ratio_relative_error"]),
        "gate_aspect_ratio_within_0_5pct": bool(sizing["gate_aspect_ratio_within_tolerance"]),
        "failure_taxonomy_path": _relative_or_absolute(Path(route_artifacts["failure_taxonomy"]), project_root),
        "repair_route_decision_path": _relative_or_absolute(
            Path(route_artifacts["repair_route_decision"]),
            project_root,
        ),
        "visual_delta_summary_path": _relative_or_absolute(
            Path(route_artifacts["visual_delta_summary"]),
            project_root,
        ),
        "repair_overlay_path": _relative_or_absolute(overlay_path, project_root),
        "phase1_budget_s": float(min(phase1_budget, 120.0)),
        "solver_summary": solver_summary,
    }

    metrics_doc = _build_child_metrics_document(
        flat_metrics,
        run_identity=run_identity,
        run_timing=run_timing,
        source_image=source_cfg.to_metrics_dict(),
        source_image_validation=source_validation,
        board_sizing=dict(sizing),
        target_stats=_target_stats(target_eval, hi_mask, bg_mask),
        route_summary=route_summary,
        artifact_inventory=artifact_inventory,
        phase_timing=phase_timing,
    )
    _atomic_write_json(metrics_doc, metrics_path)
    return metrics_doc


def _rows_from_child_metrics(metrics_docs: Iterable[dict]) -> list[dict]:
    rows: list[dict] = []
    for metrics in metrics_docs:
        source_image = dict(metrics.get("source_image", {}))
        rows.append(
            {
                "board": metrics.get("board"),
                "seed": metrics.get("seed"),
                "child_dir": metrics.get("child_run_dir"),
                "n_unknown": metrics.get("n_unknown"),
                "coverage": metrics.get("coverage"),
                "solvable": metrics.get("solvable"),
                "selected_route": metrics.get("selected_route"),
                "route_result": metrics.get("route_result"),
                "route_outcome_detail": metrics.get("route_outcome_detail"),
                "next_recommended_route": metrics.get("next_recommended_route"),
                "repair_route_selected": metrics.get("selected_route"),   # exact alias
                "repair_route_result": metrics.get("route_result"),        # exact alias
                "phase2_fixes": metrics.get("phase2_fixes"),
                "last100_fixes": metrics.get("last100_fixes"),
                "phase2_full_repair_invoked": metrics.get("phase2_full_repair_invoked"),
                "phase2_full_repair_accepted_move_count": metrics.get("phase2_full_repair_accepted_move_count"),
                "last100_invoked": metrics.get("last100_invoked"),
                "last100_accepted_move_count": metrics.get("last100_accepted_move_count"),
                "phase1_repair_hit_time_budget": bool(metrics.get("phase1_repair_hit_time_budget", False)),
                "phase2_full_repair_hit_time_budget": bool(
                    metrics.get("phase2_full_repair_hit_time_budget", False)
                ),
                "last100_repair_hit_time_budget": bool(metrics.get("last100_repair_hit_time_budget", False)),
                "visual_delta": metrics.get("visual_delta"),
                "total_time_s": metrics.get("total_time_s"),
                "source_image_name": source_image.get("name"),
                "source_image_stem": source_image.get("stem"),
                "source_image_project_relative_path": source_image.get("project_relative_path"),
                "source_image_sha256": source_image.get("sha256"),
            }
        )
    return rows


def _board_aggregates(rows: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        grouped.setdefault(str(row["board"]), []).append(row)
    output: list[dict] = []
    for board, board_rows in sorted(grouped.items()):
        output.append(
            {
                "board": board,
                "runs": len(board_rows),
                "median_n_unknown": float(np.median([float(r["n_unknown"]) for r in board_rows])),
                "median_coverage": float(np.median([float(r["coverage"]) for r in board_rows])),
                "median_visual_delta": float(
                    np.median([float(r["visual_delta"] or 0.0) for r in board_rows])
                ),
                "median_total_time_s": float(np.median([float(r["total_time_s"]) for r in board_rows])),
                "all_solved": all(bool(r["solvable"]) and int(r["n_unknown"]) == 0 for r in board_rows),
                "phase1_repair_timeout_count": sum(
                    1 for r in board_rows if bool(r.get("phase1_repair_hit_time_budget", False))
                ),
                "phase2_full_repair_timeout_count": sum(
                    1 for r in board_rows if bool(r.get("phase2_full_repair_hit_time_budget", False))
                ),
                "last100_repair_timeout_count": sum(
                    1 for r in board_rows if bool(r.get("last100_repair_hit_time_budget", False))
                ),
                "any_repair_timeout": any(
                    bool(r.get("phase1_repair_hit_time_budget", False))
                    or bool(r.get("phase2_full_repair_hit_time_budget", False))
                    or bool(r.get("last100_repair_hit_time_budget", False))
                    for r in board_rows
                ),
            }
        )
    return output


def _build_summary_markdown(
    *,
    benchmark_run_id: str,
    benchmark_root: Path,
    source_cfg: SourceImageConfig,
    rows: list[dict],
    aggregates: list[dict],
) -> str:
    lines = [
        "# Benchmark Summary",
        "",
        f"- benchmark_run_id: `{benchmark_run_id}`",
        f"- benchmark_root: `{benchmark_root.as_posix()}`",
        f"- source_image: `{source_cfg.command_arg}`",
        f"- source_image_sha256: `{source_cfg.sha256}`",
        "",
        "## Board Aggregates (medians)",
        "",
        "| board | runs | median_n_unknown | median_coverage | median_visual_delta | median_total_time_s | all_solved | phase1_timeouts | phase2_full_timeouts | last100_timeouts | any_repair_timeout |",
        "|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for agg in aggregates:
        lines.append(
            f"| {agg['board']} | {agg['runs']} | {agg['median_n_unknown']:.1f} | "
            f"{agg['median_coverage']:.5f} | {agg['median_visual_delta']:.5f} | "
            f"{agg['median_total_time_s']:.2f} | {agg['all_solved']} | "
            f"{agg['phase1_repair_timeout_count']} | {agg['phase2_full_repair_timeout_count']} | "
            f"{agg['last100_repair_timeout_count']} | {agg['any_repair_timeout']} |"
        )
    lines.extend(
        [
            "",
            "## Child Runs",
            "",
            "| board | seed | child_dir | n_unknown | coverage | solvable | selected_route | route_result | route_outcome_detail | next_recommended_route | phase2_accepted | last100_accepted | phase1_timeout | phase2_full_timeout | last100_timeout | visual_delta | total_time_s |",
            "|---|---:|---|---:|---:|---|---|---|---|---|---:|---:|---|---|---|---:|---:|",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['board']} | {row['seed']} | {row['child_dir']} | {row['n_unknown']} | "
            f"{float(row['coverage']):.5f} | {row['solvable']} | {row.get('selected_route')} | "
            f"{row.get('route_result')} | {row.get('route_outcome_detail')} | {row.get('next_recommended_route')} | "
            f"{row.get('phase2_full_repair_accepted_move_count')} | {row.get('last100_accepted_move_count')} | "
            f"{row['phase1_repair_hit_time_budget']} | {row['phase2_full_repair_hit_time_budget']} | "
            f"{row['last100_repair_hit_time_budget']} | {float(row['visual_delta'] or 0.0):.5f} | "
            f"{float(row['total_time_s']):.2f} |"
        )
    return "\n".join(lines) + "\n"


def write_normal_benchmark_summaries(
    *,
    benchmark_root: Path,
    benchmark_run_id: str,
    source_cfg: SourceImageConfig,
    source_validation: dict,
    rows: list[dict],
    widths: list[int],
    seeds: list[int],
) -> dict:
    aggregates = _board_aggregates(rows)
    summary_json = {
        "benchmark_mode": "normal",
        "benchmark_run_id": benchmark_run_id,
        "generated_at_utc": _utc_now_z(),
        "benchmark_root": benchmark_root.as_posix(),
        "widths": list(widths),
        "seeds": list(seeds),
        "source_image": source_cfg.to_metrics_dict(),
        "source_image_validation": source_validation,
        "rows": rows,
        "board_aggregates": aggregates,
    }

    summary_json_path = benchmark_root / "benchmark_summary.json"
    summary_csv_path = benchmark_root / "benchmark_summary.csv"
    summary_md_path = benchmark_root / "benchmark_summary.md"
    compatibility_json_path = benchmark_root / "benchmark_results.json"

    _atomic_write_json(summary_json, summary_json_path)
    _atomic_write_json(rows, compatibility_json_path)

    csv_fields = [
        "board",
        "seed",
        "child_dir",
        "n_unknown",
        "coverage",
        "solvable",
        "selected_route",
        "route_result",
        "route_outcome_detail",
        "next_recommended_route",
        "phase2_full_repair_invoked",
        "phase2_full_repair_n_fixed",
        "phase2_full_repair_accepted_move_count",
        "last100_invoked",
        "last100_n_fixes",
        "last100_accepted_move_count",
        "repair_route_selected",   # exact alias
        "repair_route_result",     # exact alias
        "phase2_fixes",
        "last100_fixes",
        "phase1_repair_hit_time_budget",
        "phase2_full_repair_hit_time_budget",
        "last100_repair_hit_time_budget",
        "visual_delta",
        "total_time_s",
        "source_image_name",
        "source_image_stem",
        "source_image_project_relative_path",
        "source_image_sha256",
    ]
    _atomic_write_csv(csv_fields, rows, summary_csv_path)

    summary_md = _build_summary_markdown(
        benchmark_run_id=benchmark_run_id,
        benchmark_root=benchmark_root,
        source_cfg=source_cfg,
        rows=rows,
        aggregates=aggregates,
    )
    _atomic_write_text(summary_md, summary_md_path)

    return {
        "benchmark_summary_json": summary_json_path.as_posix(),
        "benchmark_summary_csv": summary_csv_path.as_posix(),
        "benchmark_summary_md": summary_md_path.as_posix(),
        "benchmark_results_json": compatibility_json_path.as_posix(),
    }


def run_regression_from_baseline(case: dict, seed: int) -> dict:
    image_path = case["image_path"]
    board_w = int(case["board_w"])
    board_h = int(case["board_h"])
    baseline_dir = os.path.join(case["baseline_root"], f"{case['image_name']}_s{seed}")
    baseline_grid_path = os.path.join(baseline_dir, f"grid_{board_w}x{board_h}.npy")
    baseline_metrics_path = os.path.join(baseline_dir, f"metrics_{board_w}x{board_h}.json")

    baseline_grid = np.load(baseline_grid_path)
    with open(baseline_metrics_path, "r", encoding="utf-8") as handle:
        baseline_metrics = json.load(handle)

    target_eval = load_image_smart(image_path, board_w, board_h, invert=True)
    target = apply_piecewise_T_compression(target_eval, 4.0, 4.6)
    w_zone = compute_zone_aware_weights(target, 8.0, 1.0, 18.0, 3.0)
    forbidden, cpct, _, _ = build_adaptive_corridors(target, border=3)
    assert_board_valid(baseline_grid, forbidden, f"baseline-{board_w}x{board_h}-s{seed}")

    sr = solve_board(baseline_grid, max_rounds=300, mode="full")
    route = route_late_stage_failure(
        grid=baseline_grid,
        target=target_eval,
        weights=w_zone,
        forbidden=forbidden,
        sr=sr,
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
    assert_board_valid(grid, forbidden, f"post-regression-route-{board_w}x{board_h}-s{seed}")

    k8 = np.ones((3, 3), dtype=np.int32)
    k8[1, 1] = 0
    hi_mask = target_eval >= 3.0
    bg_mask = target_eval < 1.0
    adj = convolve(hi_mask.astype(np.int32), k8, mode="constant", cval=0) > 0
    true_bg = bg_mask & ~adj
    n_final = compute_N(grid)
    err = np.abs(n_final.astype(float) - target_eval)

    return {
        "image_path": image_path,
        "image_name": case["image_name"],
        "board": f"{board_w}x{board_h}",
        "seed": seed,
        "cells": board_w * board_h,
        "baseline_n_unknown": int(baseline_metrics["n_unknown"]),
        "n_unknown": int(route.sr.n_unknown),
        "coverage": float(route.sr.coverage),
        "solvable": bool(route.sr.solvable),
        "mine_accuracy": float(route.sr.mine_accuracy),
        "hi_err": float(err[hi_mask].mean()) if np.any(hi_mask) else 0.0,
        "true_bg_err": float(err[true_bg].mean()) if np.any(true_bg) else 0.0,
        "mean_abs_error": float(err.mean()),
        "pct_within_1": float(np.mean(err <= 1) * 100),
        "mine_density": float(grid.mean()),
        "corridor_pct": float(cpct),
        "repair_reason": (
            f"baseline={baseline_metrics.get('repair_reason')}"
            f"+selected_route={route.selected_route}"
            f"+route_result={route.route_result}"
            f"+route_outcome_detail={route.route_outcome_detail}"
            f"+next_recommended_route={route.next_recommended_route}"
        ),
        **route.route_state_fields(),
        "repair_route_selected": route.selected_route,
        "repair_route_result": route.route_result,
        "dominant_failure_class": route.failure_taxonomy.get("dominant_failure_class"),
        "sealed_cluster_count": int(route.failure_taxonomy.get("sealed_cluster_count", 0) or 0),
        "phase2_fixes": route.phase2_full_repair_accepted_move_count,
        "last100_fixes": route.last100_n_fixes,
        "phase1_repair_hit_time_budget": False,
        "phase2_full_repair_hit_time_budget": bool(route.phase2_full_repair_hit_time_budget),
        "last100_repair_hit_time_budget": bool(route.last100_repair_hit_time_budget),
        "visual_delta": route.visual_delta_summary.get("visual_delta"),
        "total_time_s": 0.0,
        "source_ratio": float(baseline_metrics.get("source_ratio", board_h / max(board_w, 1))),
        "board_ratio": float(baseline_metrics.get("board_ratio", board_h / max(board_w, 1))),
        "aspect_ratio_relative_error": float(baseline_metrics.get("aspect_ratio_relative_error", 0.0)),
        "gate_aspect_ratio_within_0_5pct": bool(baseline_metrics.get("gate_aspect_ratio_within_0_5pct", True)),
    }


def run_regression_cases(out_dir: Path) -> list[dict]:
    regression_results: list[dict] = []
    for case in REGRESSION_CASES:
        print(f"\n--- regression: {case['name']} ---", flush=True)
        case_validation = verify_source_image(
            case["image_path"],
            halt_on_failure=True,
            verbose=False,
            allow_noncanonical=True,
            return_details=True,
        )
        case_results = []
        for idx, seed in enumerate(case["seeds"]):
            print(f"  seed={seed} ...", end="", flush=True)
            result = run_regression_from_baseline(case, seed)
            result["source_image_validation"] = case_validation
            expected_baseline = case["expected_baseline_unknowns"][idx]
            if result["baseline_n_unknown"] != expected_baseline:
                raise RuntimeError(
                    f"Baseline unknown mismatch for {case['name']} seed {seed}: "
                    f"expected {expected_baseline}, got {result['baseline_n_unknown']}"
                )
            if result["selected_route"] != case["expected_route"]:
                raise RuntimeError(
                    f"Regression route mismatch for {case['name']} seed {seed}: "
                    f"expected {case['expected_route']}, got {result['selected_route']}"
                )
            if result["n_unknown"] != case["expected_final_unknown"]:
                raise RuntimeError(
                    f"Regression unknown mismatch for {case['name']} seed {seed}: "
                    f"expected {case['expected_final_unknown']}, got {result['n_unknown']}"
                )
            if result["coverage"] < 0.9999 or not result["solvable"] or result["last100_fixes"] != 0:
                raise RuntimeError(
                    f"Regression gate failed for {case['name']} seed {seed}: "
                    f"coverage={result['coverage']}, solvable={result['solvable']}, "
                    f"last100_fixes={result['last100_fixes']}"
                )
            case_results.append(result)
            regression_results.append(result)
            print(
                f" baseline_n_unk={result['baseline_n_unknown']}"
                f" route={result['selected_route']}"
                f" route_result={result['route_result']}"
                f" route_outcome_detail={result['route_outcome_detail']}"
                f" n_unk={result['n_unknown']} cov={result['coverage']:.5f}",
                flush=True,
            )
        _atomic_write_json(case_results, out_dir / f"{case['name']}_results.json")
    _atomic_write_json(regression_results, out_dir / "benchmark_regression_results.json")
    return regression_results


def _normal_benchmark_root(args: argparse.Namespace, project_root: Path, source_cfg: SourceImageConfig) -> tuple[Path, str]:
    if args.out_dir:
        return Path(args.out_dir).expanduser().resolve(), _build_benchmark_run_id(source_cfg.stem)
    run_id = _build_benchmark_run_id(source_cfg.stem)
    return (project_root / DEFAULT_BENCHMARK_RESULTS_ROOT / run_id).resolve(), run_id


def main(argv: list[str] | None = None, raw_argv: list[str] | None = None) -> int:
    args = parse_args(argv=argv, raw_argv=raw_argv)
    project_root = Path(__file__).resolve().parent

    if args.regression_only:
        regression_root = (
            Path(args.out_dir).expanduser().resolve()
            if args.out_dir
            else (project_root / DEFAULT_BENCHMARK_RESULTS_ROOT).resolve()
        )
        os.makedirs(regression_root, exist_ok=True)
        print("\n" + "=" * 65)
        print("Mine-Streaker  -  Benchmark (regression-only)")
        print("=" * 65)
        run_regression_cases(regression_root)
        print("\nRegression-only benchmark validation passed.")
        return 0

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

    benchmark_root, benchmark_run_id = _normal_benchmark_root(args, project_root, source_cfg)
    os.makedirs(benchmark_root, exist_ok=True)

    print("\n" + "=" * 65)
    print("Mine-Streaker  -  Standard Benchmark Matrix")
    print(f"  source_image={source_cfg.absolute_path.as_posix()}")
    print(f"  benchmark_run_id={benchmark_run_id}")
    print("=" * 65)

    sa_fn = compile_sa_kernel()
    ensure_solver_warmed()

    metrics_docs = []
    for board_w in list(args.widths):
        board_h = derive_board_from_width(
            str(source_cfg.absolute_path), board_w, min_width=300, ratio_tolerance=0.005
        )["board_height"]
        print(f"\n--- {board_w}x{board_h} ---", flush=True)
        for seed in list(args.seeds):
            print(f"  seed={seed} ...", end="", flush=True)
            metrics = run_normal_child(
                source_cfg=source_cfg,
                source_validation=source_validation,
                board_w=int(board_w),
                seed=int(seed),
                sa_fn=sa_fn,
                benchmark_root=benchmark_root,
                benchmark_run_id=benchmark_run_id,
                project_root=project_root,
            )
            metrics_docs.append(metrics)
            print(
                f" n_unk={metrics['n_unknown']} cov={metrics['coverage']:.5f} "
                f"route={metrics['repair_route_selected']} phase2_fixes={metrics['phase2_fixes']} "
                f"last100_fixes={metrics['last100_fixes']} time={metrics['total_time_s']:.1f}s",
                flush=True,
            )

    rows = _rows_from_child_metrics(metrics_docs)
    summary_paths = write_normal_benchmark_summaries(
        benchmark_root=benchmark_root,
        benchmark_run_id=benchmark_run_id,
        source_cfg=source_cfg,
        source_validation=source_validation,
        rows=rows,
        widths=list(args.widths),
        seeds=list(args.seeds),
    )

    if args.include_regressions:
        run_regression_cases(benchmark_root)

    print("\nBenchmark summaries written:")
    print(f"  {summary_paths['benchmark_summary_json']}")
    print(f"  {summary_paths['benchmark_summary_csv']}")
    print(f"  {summary_paths['benchmark_summary_md']}")
    print(f"  {summary_paths['benchmark_results_json']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
