#!/usr/bin/env python3
"""
Generate a single-board visual report artifact for a custom source image.

Default output target:
  results/iris3d_200x246/visual_200x246.png
"""
import argparse
import cProfile
import csv
import hashlib
import json
import os
import platform
import pstats
import shutil
import struct
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numba
import numpy as np
import PIL
import scipy
from PIL import Image as PILImage
from scipy.ndimage import binary_dilation, convolve, label

from assets.image_guard import (
    ALLOW_NONCANONICAL_ENV,
    verify_source_image,
)
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
from repair import run_phase1_repair, run_phase2_full_repair
from sa import compile_sa_kernel, run_sa
from solver import MINE, SAFE, UNKNOWN, ensure_solver_warmed, solve_board


def atomic_save_json(data, path):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def atomic_save_npy(arr, path):
    tmp = path + ".tmp.npy"
    np.save(tmp, arr)
    os.replace(tmp, path)


def compute_file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_numba_num_threads():
    try:
        return int(numba.get_num_threads())
    except Exception:
        return None


def _safe_numba_threading_layer():
    try:
        return str(numba.threading_layer())
    except Exception:
        return None


def resolve_image_path(image_path):
    """
    Resolve common iris3d/irisd3 filename transpositions without guessing outside
    the requested directory.
    """
    if os.path.exists(image_path):
        return image_path
    folder = os.path.dirname(image_path)
    name = os.path.basename(image_path)
    candidates = []
    if "iris3d" in name:
        candidates.append(name.replace("iris3d", "irisd3"))
    if "irisd3" in name:
        candidates.append(name.replace("irisd3", "iris3d"))
    for cand in candidates:
        cand_path = os.path.join(folder, cand) if folder else cand
        if os.path.exists(cand_path):
            return cand_path
    return image_path


def get_git_metadata():
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return {"git_commit": None, "git_dirty": None}

    try:
        porcelain = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo_dir,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        dirty = bool(porcelain.strip())
    except Exception:
        dirty = None
    return {"git_commit": commit, "git_dirty": dirty}


def collect_run_provenance(image_path, allow_noncanonical, run_id, run_tag):
    image_abs = os.path.abspath(image_path)
    image_size = os.path.getsize(image_path) if os.path.exists(image_path) else None
    image_sha256 = compute_file_sha256(image_path) if os.path.exists(image_path) else None
    git_meta = get_git_metadata()
    return {
        "run_id": run_id,
        "run_tag": run_tag,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "image_path": image_abs,
        "image_size_bytes": image_size,
        "image_sha256": image_sha256,
        "allow_noncanonical": bool(allow_noncanonical),
        "python_version": sys.version.split()[0],
        "python_bits": struct.calcsize("P") * 8,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "cpu_count": os.cpu_count(),
        "numba_num_threads": _safe_numba_num_threads(),
        "numba_threading_layer": _safe_numba_threading_layer(),
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "numba_version": numba.__version__,
        "pillow_version": PIL.__version__,
        "matplotlib_version": matplotlib.__version__,
        "git_commit": git_meta["git_commit"],
        "git_dirty": git_meta["git_dirty"],
    }


def append_jsonl_record(path, record):
    if not path:
        return
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def append_csv_row(path, row):
    if not path:
        return
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def build_ledger_row(metrics):
    phase = metrics.get("phase_timing_s", {})
    prov = metrics.get("provenance", {})
    gates = metrics.get("runtime_gates", {})
    row = {
        "run_id": prov.get("run_id"),
        "run_tag": prov.get("run_tag"),
        "started_at_utc": prov.get("started_at_utc"),
        "board": metrics.get("board"),
        "cells": metrics.get("cells"),
        "seed": metrics.get("seed"),
        "source_width": metrics.get("source_width"),
        "source_height": metrics.get("source_height"),
        "source_ratio": metrics.get("source_ratio"),
        "board_width": metrics.get("board_width"),
        "board_height": metrics.get("board_height"),
        "board_ratio": metrics.get("board_ratio"),
        "aspect_ratio_relative_error": metrics.get("aspect_ratio_relative_error"),
        "n_unknown": metrics.get("n_unknown"),
        "coverage": metrics.get("coverage"),
        "solvable": metrics.get("solvable"),
        "mine_accuracy": metrics.get("mine_accuracy"),
        "mean_abs_error": metrics.get("mean_abs_error"),
        "hi_err": metrics.get("hi_err"),
        "true_bg_err": metrics.get("true_bg_err"),
        "mine_density": metrics.get("mine_density"),
        "corridor_pct": metrics.get("corridor_pct"),
        "repair_reason": metrics.get("repair_reason"),
        "n_phase2_fixes": metrics.get("n_phase2_fixes"),
        "solve_time_s": metrics.get("solve_time_s"),
        "total_time_s": metrics.get("total_time_s"),
        "delta_vs_iter9_research_s": metrics.get("delta_vs_iter9_research_s"),
        "delta_vs_iter9_original_s": metrics.get("delta_vs_iter9_original_s"),
        "compile_and_warmup_s": phase.get("compile_and_warmup"),
        "target_and_corridors_s": phase.get("target_and_corridors"),
        "coarse_sa_s": phase.get("coarse_sa"),
        "fine_sa_s": phase.get("fine_sa"),
        "refine_sa_total_s": phase.get("refine_sa_total"),
        "phase1_repair_s": phase.get("phase1_repair"),
        "phase2_repair_s": phase.get("phase2_repair"),
        "final_solve_s": phase.get("final_solve"),
        "render_and_write_s": phase.get("render_and_write"),
        "gate_n_unknown_zero": gates.get("n_unknown_zero"),
        "gate_coverage_1000": gates.get("coverage_1000"),
        "gate_solvable_true": gates.get("solvable_true"),
        "gate_mine_accuracy_1000": gates.get("mine_accuracy_1000"),
        "gate_aspect_ratio_within_0_5pct": gates.get("aspect_ratio_within_0_5pct"),
        "gate_total_time_under_20": gates.get("total_time_under_20"),
        "gate_total_time_under_50": gates.get("total_time_under_50"),
        "gate_total_time_under_60": gates.get("total_time_under_60"),
        "gate_python_64bit": gates.get("python_64bit"),
        "gate_profile_generated": gates.get("profile_generated"),
        "gate_hotspot_candidates_identified": gates.get("hotspot_candidates_identified"),
        "dominant_phase": metrics.get("dominant_phase"),
        "dominant_phase_share": metrics.get("dominant_phase_share"),
        "image_sha256": prov.get("image_sha256"),
        "git_commit": prov.get("git_commit"),
        "python_bits": prov.get("python_bits"),
        "cpu_count": prov.get("cpu_count"),
        "numba_num_threads": prov.get("numba_num_threads"),
        "iters_multiplier": metrics.get("iters_multiplier"),
        "contrast_factor": metrics.get("contrast_factor"),
        "sa_budget_multiplier": metrics.get("sa_budget_multiplier"),
        "max_runtime_s": metrics.get("max_runtime_s"),
        "sa_probe_iters_per_s": metrics.get("runtime_calibration", {}).get("probe_iters_per_s"),
        "sa_budget_s": metrics.get("runtime_calibration", {}).get("sa_budget_s"),
        "sa_base_budget_s": metrics.get("runtime_calibration", {}).get("base_sa_budget_s"),
        "sa_budget_elapsed_before_probe_s": metrics.get("runtime_calibration", {}).get("elapsed_budget_before_probe_s"),
        "compile_excluded_from_sa_budget": metrics.get("runtime_calibration", {}).get("compile_excluded_from_budget_clock"),
        "sa_total_iters_effective": metrics.get("runtime_calibration", {}).get("effective_total_iters"),
        "harm_signal_t_ge_7_pct": metrics.get("preprocess", {}).get("harm_signal_t_ge_7_pct"),
        "harm_signal_t_ge_6_pct": metrics.get("preprocess", {}).get("harm_signal_t_ge_6_pct"),
        "harm_signal_t_le_1_pct": metrics.get("preprocess", {}).get("harm_signal_t_le_1_pct"),
        "hotspot_top1": (metrics.get("hotspot_top3") or [None, None, None])[0],
        "hotspot_top2": (metrics.get("hotspot_top3") or [None, None, None])[1],
        "hotspot_top3": (metrics.get("hotspot_top3") or [None, None, None])[2],
    }
    return row


def detect_line_profile_support() -> bool:
    try:
        import line_profiler  # noqa: F401
        return True
    except Exception:
        return False


def _profile_func_label(filename: str, line_no: int, func_name: str) -> str:
    base = os.path.basename(filename)
    return f"{base}:{line_no}:{func_name}"


def _recommend_optimization(label: str) -> str:
    lname = label.lower()
    if "_sa_kernel" in lname or "run_sa" in lname:
        return "jit_parallel"
    if "_numba_solve" in lname or "solve_board" in lname:
        return "memory_bandwidth"
    if "phase1_repair" in lname or "phase2_full_repair" in lname or "repair.py" in lname:
        return "solver_call_reduction"
    if "numpy" in lname or "scipy" in lname:
        return "memory_layout_vectorization"
    return "reduce_python_overhead"


def _is_64bit_optimization_candidate(label: str) -> bool:
    lname = label.lower()
    return (
        "_sa_kernel" in lname
        or "_numba_solve" in lname
        or "run_sa" in lname
        or "solve_board" in lname
        or "compute_n" in lname
    )


def export_cprofile_artifacts(
    profile: cProfile.Profile,
    profile_out_dir: str,
    run_id: str,
    total_time_s: float,
    candidate_share_threshold: float = 0.08,
) -> dict:
    os.makedirs(profile_out_dir, exist_ok=True)
    pstats_path = os.path.join(profile_out_dir, f"profile_{run_id}.pstats")
    top_csv_path = os.path.join(profile_out_dir, f"top_functions_{run_id}.csv")
    hotspot_json_path = os.path.join(profile_out_dir, f"hotspot_summary_{run_id}.json")
    candidates_json_path = os.path.join(profile_out_dir, f"optimization_candidates_{run_id}.json")

    profile.dump_stats(pstats_path)
    stats_obj = pstats.Stats(profile)
    stats_dict = stats_obj.stats

    total_wall = max(float(total_time_s), 1e-9)
    rows = []
    for key, stat in stats_dict.items():
        filename, line_no, func_name = key
        cc, nc, tt, ct, _callers = stat
        label = _profile_func_label(filename, line_no, func_name)
        rows.append(
            {
                "function": label,
                "filename": filename,
                "line_no": int(line_no),
                "func_name": func_name,
                "primitive_calls": int(cc),
                "total_calls": int(nc),
                "self_time_s": float(tt),
                "cum_time_s": float(ct),
                "self_share_wall": float(tt / total_wall),
                "cum_share_wall": float(ct / total_wall),
            }
        )

    rows_sorted_cum = sorted(rows, key=lambda r: r["cum_time_s"], reverse=True)
    rows_sorted_self = sorted(rows, key=lambda r: r["self_time_s"], reverse=True)

    with open(top_csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "rank_cum",
            "function",
            "self_time_s",
            "cum_time_s",
            "self_share_wall",
            "cum_share_wall",
            "primitive_calls",
            "total_calls",
            "candidate_for_64bit_optimization",
            "recommended_optimization_type",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for idx, row in enumerate(rows_sorted_cum[:200], start=1):
            out_row = {
                "rank_cum": idx,
                "function": row["function"],
                "self_time_s": row["self_time_s"],
                "cum_time_s": row["cum_time_s"],
                "self_share_wall": row["self_share_wall"],
                "cum_share_wall": row["cum_share_wall"],
                "primitive_calls": row["primitive_calls"],
                "total_calls": row["total_calls"],
                "candidate_for_64bit_optimization": _is_64bit_optimization_candidate(row["function"]),
                "recommended_optimization_type": _recommend_optimization(row["function"]),
            }
            writer.writerow(out_row)

    candidates = []
    for row in rows_sorted_cum:
        self_share = row["self_share_wall"]
        cum_share = row["cum_share_wall"]
        if self_share < candidate_share_threshold and cum_share < candidate_share_threshold:
            continue
        rec = _recommend_optimization(row["function"])
        candidates.append(
            {
                "function": row["function"],
                "self_share_wall": self_share,
                "cum_share_wall": cum_share,
                "self_time_s": row["self_time_s"],
                "cum_time_s": row["cum_time_s"],
                "candidate_reason": (
                    f"High runtime share (self={self_share:.3f}, cum={cum_share:.3f}) "
                    f"at threshold {candidate_share_threshold:.3f}"
                ),
                "candidate_for_64bit_optimization": bool(_is_64bit_optimization_candidate(row["function"])),
                "recommended_optimization_type": rec,
            }
        )

    candidates = sorted(
        candidates,
        key=lambda c: max(c["self_share_wall"], c["cum_share_wall"]),
        reverse=True,
    )

    summary = {
        "run_id": run_id,
        "top_by_cumulative_time": rows_sorted_cum[:25],
        "top_by_self_time": rows_sorted_self[:25],
        "candidate_share_threshold": candidate_share_threshold,
        "optimization_candidates_count": len(candidates),
    }

    with open(hotspot_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(candidates_json_path, "w", encoding="utf-8") as f:
        json.dump(candidates, f, indent=2)

    top3 = [r["function"] for r in rows_sorted_cum[:3]]
    top3_64bit = [r["function"] for r in rows_sorted_cum if _is_64bit_optimization_candidate(r["function"])][:3]
    return {
        "enabled": True,
        "pstats_path": pstats_path,
        "top_functions_csv_path": top_csv_path,
        "hotspot_summary_json_path": hotspot_json_path,
        "optimization_candidates_json_path": candidates_json_path,
        "top3_functions_by_cum_time": top3,
        "top3_64bit_candidates_by_cum_time": top3_64bit,
        "optimization_candidates_count": len(candidates),
        "optimization_candidates_top10": candidates[:10],
    }


def export_line_profile_artifact(line_profiler_obj, profile_out_dir: str, run_id: str) -> str:
    os.makedirs(profile_out_dir, exist_ok=True)
    line_txt = os.path.join(profile_out_dir, f"line_profile_{run_id}.txt")
    with open(line_txt, "w", encoding="utf-8") as f:
        line_profiler_obj.print_stats(stream=f)
    return line_txt


def get_iter_schedule(cells, base_cells=25_000, base_total_iters=18_000_000, multiplier=1.0):
    """
    Scale total SA iterations by sqrt(cells / base_cells), then split:
    coarse:fine:refine1:refine2:refine3 = 11:44:11:11:22
    """
    scale = (cells / float(base_cells)) ** 0.5
    total = max(500_000, int(base_total_iters * scale * multiplier))
    coarse = max(100_000, int(total * 0.11))
    fine = max(200_000, int(total * 0.44))
    refine1 = max(100_000, int(total * 0.11))
    refine2 = max(100_000, int(total * 0.11))
    refine3 = max(200_000, int(total * 0.22))
    return coarse, fine, refine1, refine2, refine3


def split_total_iters(total_iters):
    # coarse:fine:refine1:refine2:refine3 = 11:44:11:11:22
    ratios = (11, 44, 11, 11, 22)
    ratio_sum = float(sum(ratios))
    coarse = max(50_000, int(total_iters * ratios[0] / ratio_sum))
    fine = max(100_000, int(total_iters * ratios[1] / ratio_sum))
    refine1 = max(50_000, int(total_iters * ratios[2] / ratio_sum))
    refine2 = max(50_000, int(total_iters * ratios[3] / ratio_sum))
    used = coarse + fine + refine1 + refine2
    refine3 = max(100_000, int(max(total_iters - used, 100_000)))
    return coarse, fine, refine1, refine2, refine3


def summarize_target_distribution(target_arr):
    t = np.asarray(target_arr, dtype=np.float32)
    return {
        "min": float(np.min(t)),
        "max": float(np.max(t)),
        "mean": float(np.mean(t)),
        "std": float(np.std(t)),
        "q50": float(np.percentile(t, 50.0)),
        "q75": float(np.percentile(t, 75.0)),
        "q90": float(np.percentile(t, 90.0)),
        "q98": float(np.percentile(t, 98.0)),
        "pct_t_ge_7": float(np.mean(t >= 7.0)),
        "pct_t_ge_6": float(np.mean(t >= 6.0)),
        "pct_t_le_1": float(np.mean(t <= 1.0)),
    }


def calibrate_sa_schedule_for_budget(
    *,
    kernel,
    target,
    weights,
    forbidden,
    border,
    density,
    seed,
    t_min,
    elapsed_budget_before_probe_s,
    max_runtime_s,
    baseline_total_iters,
    sa_budget_multiplier=1.0,
    compile_excluded_from_budget_clock=False,
):
    h, w = target.shape
    cells = int(h * w)
    avail = np.argwhere(forbidden == 0)
    if len(avail) == 0:
        c, f, r1, r2, r3 = split_total_iters(max(200_000, min(500_000, baseline_total_iters)))
        return {
            "enabled": False,
            "reason": "no_available_cells",
            "probe_iters": 0,
            "probe_elapsed_s": 0.0,
            "probe_iters_per_s": 0.0,
            "sa_budget_s": 0.0,
            "baseline_total_iters": int(baseline_total_iters),
            "effective_total_iters": int(c + f + r1 + r2 + r3),
            "schedule": {
                "coarse": int(c),
                "fine": int(f),
                "refine1": int(r1),
                "refine2": int(r2),
                "refine3": int(r3),
            },
        }

    probe_grid = np.zeros((h, w), dtype=np.int8)
    rng = np.random.default_rng(seed + 9973)
    init_mines = min(int(density * cells), len(avail))
    if init_mines > 0:
        idx = rng.choice(len(avail), size=init_mines, replace=False)
        for i in idx:
            probe_grid[avail[i][0], avail[i][1]] = 1

    probe_iters = int(min(150_000, max(40_000, cells // 4)))
    t_probe = time.perf_counter()
    _probe_grid, _probe_loss, _probe_hist = run_sa(
        kernel,
        probe_grid,
        target,
        weights,
        forbidden,
        probe_iters,
        3.5,
        t_min,
        0.999996,
        border,
        seed + 9974,
    )
    probe_elapsed = max(time.perf_counter() - t_probe, 1e-9)
    probe_iters_per_s = float(probe_iters / probe_elapsed)

    reserve_non_sa_s = max(8.0, max_runtime_s * 0.34)
    base_sa_budget_s = max(2.0, max_runtime_s - elapsed_budget_before_probe_s - probe_elapsed - reserve_non_sa_s)
    sa_budget_scale = max(0.1, float(sa_budget_multiplier))
    sa_budget_s = max(2.0, base_sa_budget_s * sa_budget_scale)
    budget_total_iters = int(probe_iters_per_s * sa_budget_s)
    hard_min_total_iters = int(max(200_000, min(600_000, cells * 1.2)))
    max_total_iters = int(max(baseline_total_iters, baseline_total_iters * sa_budget_scale))
    effective_total_iters = int(min(max_total_iters, max(hard_min_total_iters, budget_total_iters)))
    coarse, fine, refine1, refine2, refine3 = split_total_iters(effective_total_iters)

    return {
        "enabled": True,
        "reason": "throughput_probe",
        "probe_iters": int(probe_iters),
        "probe_elapsed_s": float(probe_elapsed),
        "probe_iters_per_s": float(probe_iters_per_s),
        "sa_budget_s": float(sa_budget_s),
        "base_sa_budget_s": float(base_sa_budget_s),
        "sa_budget_multiplier": float(sa_budget_scale),
        "reserve_non_sa_s": float(reserve_non_sa_s),
        "elapsed_budget_before_probe_s": float(elapsed_budget_before_probe_s),
        "compile_excluded_from_budget_clock": bool(compile_excluded_from_budget_clock),
        "baseline_total_iters": int(baseline_total_iters),
        "max_total_iters": int(max_total_iters),
        "budget_total_iters": int(budget_total_iters),
        "hard_min_total_iters": int(hard_min_total_iters),
        "effective_total_iters": int(coarse + fine + refine1 + refine2 + refine3),
        "schedule": {
            "coarse": int(coarse),
            "fine": int(fine),
            "refine1": int(refine1),
            "refine2": int(refine2),
            "refine3": int(refine3),
        },
    }


def extract_sealed_components(
    solver_state: np.ndarray,
    *,
    min_component_size: int = 64,
    max_components: int = 50,
    dilation_steps: int = 1,
) -> tuple[list[dict], dict]:
    """
    Return sealed unknown components sorted by size (largest first), optionally
    dilated for local-capping neighborhoods.
    """
    unknown_mask = solver_state == UNKNOWN
    safe_mask = solver_state == SAFE
    if not np.any(unknown_mask):
        return [], {
            "unknown_components": 0,
            "sealed_components": 0,
            "selected_components": 0,
            "sealed_cells_total": 0,
            "risk_cells": 0,
        }

    labels, n_components = label(unknown_mask.astype(np.int8))
    structure = np.ones((3, 3), dtype=bool)
    rows = []
    for cid in range(1, int(n_components) + 1):
        comp_mask = labels == cid
        comp_size = int(np.sum(comp_mask))
        if comp_size < int(min_component_size):
            continue
        border_mask = binary_dilation(comp_mask, structure=structure) & (~comp_mask)
        has_safe_adj = bool(np.any(safe_mask & border_mask))
        if has_safe_adj:
            continue
        mask_out = comp_mask
        if dilation_steps > 0:
            mask_out = binary_dilation(
                comp_mask,
                structure=structure,
                iterations=int(dilation_steps),
            )
        rows.append(
            {
                "component_id": int(cid),
                "component_size": int(comp_size),
                "mask": mask_out.astype(bool),
            }
        )

    rows.sort(key=lambda r: r["component_size"], reverse=True)
    selected = rows[: int(max_components)]
    risk_cells = int(np.sum(np.logical_or.reduce([r["mask"] for r in selected]))) if selected else 0
    stats = {
        "unknown_components": int(n_components),
        "sealed_components": int(len(rows)),
        "selected_components": int(len(selected)),
        "sealed_cells_total": int(sum(r["component_size"] for r in rows)),
        "risk_cells": int(risk_cells),
    }
    return selected, stats


def detect_sealed_risk_mask(
    solver_state: np.ndarray,
    *,
    min_component_size: int = 64,
    max_components: int = 50,
    dilation_steps: int = 1,
) -> tuple[np.ndarray, dict]:
    comps, stats = extract_sealed_components(
        solver_state,
        min_component_size=min_component_size,
        max_components=max_components,
        dilation_steps=dilation_steps,
    )
    if not comps:
        return np.zeros_like(solver_state, dtype=bool), stats
    risk_mask = np.logical_or.reduce([c["mask"] for c in comps])
    return risk_mask.astype(bool), stats


def apply_local_target_cap(
    target: np.ndarray,
    target_eval: np.ndarray,
    risk_mask: np.ndarray,
    *,
    local_cap: float,
    trigger_eval: float,
) -> tuple[np.ndarray, dict]:
    """
    Cap target values only inside sealed-risk regions and only for saturated
    target-eval cells.
    """
    target_local = target.copy()
    candidate_mask = risk_mask & (target_eval >= float(trigger_eval))
    if not np.any(candidate_mask):
        return target_local, {
            "local_cap_value": float(local_cap),
            "local_trigger_eval": float(trigger_eval),
            "capped_cells": 0,
            "target_mean_before": float(np.mean(target)),
            "target_mean_after": float(np.mean(target_local)),
        }

    before_vals = target_local[candidate_mask].copy()
    target_local[candidate_mask] = np.minimum(target_local[candidate_mask], float(local_cap))
    after_vals = target_local[candidate_mask]
    stats = {
        "local_cap_value": float(local_cap),
        "local_trigger_eval": float(trigger_eval),
        "capped_cells": int(np.sum(candidate_mask)),
        "capped_delta_mean": float(np.mean(before_vals - after_vals)),
        "capped_before_mean": float(np.mean(before_vals)),
        "capped_after_mean": float(np.mean(after_vals)),
        "target_mean_before": float(np.mean(target)),
        "target_mean_after": float(np.mean(target_local)),
    }
    return target_local, stats


def render_visual_report(target_eval, grid, sr, title, save_path, dpi=150):
    """
    Match the visual style used for large-board fidelity artifacts:
    target / mine grid / N / error + solved state panel + inferno + overlay.
    """
    N = compute_N(grid)
    H, W = grid.shape
    err = np.abs(N.astype(float) - target_eval)

    fig = plt.figure(figsize=(20, 12), facecolor="#1a1a2e")
    fig.suptitle(title, fontsize=14, fontweight="bold", color="white", y=0.98)
    gs = gridspec.GridSpec(
        2, 4, figure=fig, hspace=0.08, wspace=0.05,
        left=0.01, right=0.99, top=0.94, bottom=0.06
    )

    def add_panel(ax, img_data, cmap, vmin, vmax, label):
        ax.imshow(img_data, cmap=cmap, vmin=vmin, vmax=vmax, interpolation="nearest", aspect="equal")
        ax.set_title(label, fontsize=9, color="white", pad=3)
        ax.axis("off")

    ax0 = fig.add_subplot(gs[0, 0])
    add_panel(ax0, target_eval, "hot", 0, 8, f"Target T  [{W}x{H}]")

    ax1 = fig.add_subplot(gs[0, 1])
    add_panel(ax1, grid, "binary_r", 0, 1, f"Mine Grid  dens={grid.mean():.3f}")

    ax2 = fig.add_subplot(gs[0, 2])
    add_panel(ax2, N.astype(float), "hot", 0, 8, "Number Field N")

    ax3 = fig.add_subplot(gs[0, 3])
    add_panel(ax3, err, "hot", 0, 4, f"|N-T|  mean={err.mean():.3f}")

    ax4 = fig.add_subplot(gs[1, 0:2])
    if sr.state is not None:
        smap = np.zeros((H, W, 3), dtype=np.float32)
        smap[sr.state == SAFE] = [0.85, 0.85, 0.85]
        smap[sr.state == MINE] = [1.00, 0.40, 0.10]
        smap[sr.state == UNKNOWN] = [0.10, 0.30, 0.90]
        ax4.imshow(smap, aspect="equal", interpolation="nearest")
    ax4.set_title(
        f"SOLVED BOARD  cov={sr.coverage:.5f}  n_unknown={sr.n_unknown}  solvable={sr.solvable}",
        fontsize=10, color="white", pad=4, fontweight="bold"
    )
    ax4.axis("off")

    ax5 = fig.add_subplot(gs[1, 2])
    add_panel(ax5, N.astype(float), "inferno", 0, 8, "N field (inferno)")

    ax6 = fig.add_subplot(gs[1, 3])
    composite = np.zeros((H, W, 3), dtype=np.float32)
    composite[:, :, 0] = np.clip(N.astype(float) / 8.0, 0.0, 1.0)
    composite[:, :, 2] = np.clip(target_eval / 8.0, 0.0, 1.0)
    composite[:, :, 1] = np.clip((composite[:, :, 0] + composite[:, :, 2]) / 2.0, 0.0, 1.0)
    ax6.imshow(composite, aspect="equal", interpolation="nearest")
    ax6.set_title("N (red) vs Target (blue) overlay", fontsize=9, color="white", pad=3)
    ax6.axis("off")

    plt.savefig(save_path, dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)


def run_single_board(
    image_path,
    out_dir,
    provenance,
    board_w=300,
    board_h=None,
    seed=42,
    density=0.22,
    border=3,
    iters_multiplier=0.25,
    max_runtime_s=50.0,
    pw_knee=4.0,
    pw_t_max=6.0,
    hi_boost=18.0,
    phase1_budget_s=8.0,
    phase2_budget_s=6.0,
    adaptive_local_cap=False,
    adaptive_local_cap_value=4.6,
    adaptive_local_trigger_eval=7.5,
    adaptive_local_min_component=64,
    adaptive_local_max_components=50,
    adaptive_local_dilation=1,
    adaptive_local_sa_budget_s=10.0,
    adaptive_local_cap_ladder=None,
    adaptive_local_clusters_per_step=10,
    adaptive_local_unknown_stop=0,
    solvability_penalty_pass=True,
    solvability_penalty_boost=2.0,
    solvability_penalty_iters_scale=0.12,
    contrast_factor=2.0,
    sa_budget_multiplier=1.0,
):
    os.makedirs(out_dir, exist_ok=True)
    t0 = time.perf_counter()
    phase_timing_s = {}

    # Iter9/large-board defaults.
    bp_true, bp_trans = 8.0, 1.0
    hi_thr = 3.0
    uf_factor = 1.8
    seal_thr, seal_str = 0.6, 20.0
    t_min = 0.001
    if adaptive_local_cap_ladder is None:
        adaptive_local_cap_ladder = [5.4, 5.0, 4.8, float(adaptive_local_cap_value)]
    else:
        adaptive_local_cap_ladder = [float(v) for v in adaptive_local_cap_ladder]
    adaptive_local_cap_ladder = [v for v in adaptive_local_cap_ladder if v > 0.0]

    sizing = derive_board_from_width(
        image_path=image_path,
        board_width=board_w,
        min_width=300,
        ratio_tolerance=0.005,
    )
    board_w = sizing["board_width"]
    board_h = sizing["board_height"]

    cells = board_w * board_h
    ci_base, fi_base, r1i_base, r2i_base, r3i_base = get_iter_schedule(cells, multiplier=iters_multiplier)
    baseline_total_iters = int(ci_base + fi_base + r1i_base + r2i_base + r3i_base)
    print(
        f"[{board_w}x{board_h}] cells={cells:,} "
        f"baseline SA total_iters={baseline_total_iters:,} "
        f"(target runtime <= {max_runtime_s:.1f}s) "
        f"source_ratio={sizing['source_ratio']:.6f} board_ratio={sizing['board_ratio']:.6f}",
        flush=True
    )

    t_budget0 = t0

    def remaining_s():
        return max(0.0, max_runtime_s - (time.perf_counter() - t_budget0))

    t_phase = time.perf_counter()
    sa_fn = compile_sa_kernel()
    ensure_solver_warmed()
    phase_timing_s["compile_and_warmup"] = time.perf_counter() - t_phase
    # Budget clock starts AFTER compile/warmup so JIT latency cannot steal SA budget.
    t_budget0 = time.perf_counter()

    t_phase = time.perf_counter()
    target_eval = load_image_smart(
        image_path,
        board_w,
        board_h,
        invert=True,
        contrast_factor=contrast_factor,
    )
    target_eval_stats = summarize_target_distribution(target_eval)
    target = apply_piecewise_T_compression(target_eval, pw_knee, pw_t_max)
    target_work_stats = summarize_target_distribution(target)
    w_zone = compute_zone_aware_weights(target, bp_true, bp_trans, hi_boost, hi_thr)
    forbidden, corridor_pct, _, _ = build_adaptive_corridors(target, border=border)
    phase_timing_s["target_and_corridors"] = time.perf_counter() - t_phase

    k8 = np.ones((3, 3), dtype=np.int32)
    k8[1, 1] = 0
    hi_mask = target_eval >= hi_thr
    bg_mask = target_eval < 1.0
    adj_to_hi = convolve(hi_mask.astype(np.int32), k8, mode="constant", cval=0) > 0
    true_bg = bg_mask & ~adj_to_hi

    rng = np.random.default_rng(seed)
    avail = np.argwhere(forbidden == 0)
    elapsed_before_probe_s = time.perf_counter() - t_budget0
    t_phase = time.perf_counter()
    runtime_calibration = calibrate_sa_schedule_for_budget(
        kernel=sa_fn,
        target=target,
        weights=w_zone,
        forbidden=forbidden,
        border=border,
        density=density,
        seed=seed,
        t_min=t_min,
        elapsed_budget_before_probe_s=elapsed_before_probe_s,
        max_runtime_s=max_runtime_s,
        baseline_total_iters=baseline_total_iters,
        sa_budget_multiplier=sa_budget_multiplier,
        compile_excluded_from_budget_clock=True,
    )
    phase_timing_s["sa_probe"] = time.perf_counter() - t_phase
    ci = runtime_calibration["schedule"]["coarse"]
    fi = runtime_calibration["schedule"]["fine"]
    r1i = runtime_calibration["schedule"]["refine1"]
    r2i = runtime_calibration["schedule"]["refine2"]
    r3i = runtime_calibration["schedule"]["refine3"]
    print(
        "SA calibrated schedule: "
        f"coarse={ci:,} fine={fi:,} refine={r1i:,}+{r2i:,}+{r3i:,} "
        f"probe={runtime_calibration['probe_iters_per_s']:.0f} it/s "
        f"sa_budget={runtime_calibration['sa_budget_s']:.2f}s",
        flush=True,
    )

    # Coarse SA.
    t_phase = time.perf_counter()
    c_w, c_h = board_w // 2, board_h // 2
    target_c = apply_piecewise_T_compression(
        load_image_smart(
            image_path,
            c_w,
            c_h,
            invert=True,
            contrast_factor=contrast_factor,
        ),
        pw_knee,
        pw_t_max,
    )
    weights_c = compute_zone_aware_weights(target_c, bp_true, bp_trans, hi_boost, hi_thr)
    forbidden_c, _, _, _ = build_adaptive_corridors(target_c, border=border)
    grid_c = np.zeros((c_h, c_w), dtype=np.int8)
    avail_c = np.argwhere(forbidden_c == 0)
    idx_c = rng.choice(len(avail_c), size=min(int(density * c_w * c_h), len(avail_c)), replace=False)
    for i in idx_c:
        grid_c[avail_c[i][0], avail_c[i][1]] = 1
    grid_c, _, hist_c = run_sa(sa_fn, grid_c, target_c, weights_c, forbidden_c, ci, 10.0, t_min, 0.99998, border, seed)

    coarse_img = PILImage.fromarray(grid_c.astype(np.uint8) * 255)
    grid = (np.array(coarse_img.resize((board_w, board_h), PILImage.NEAREST), dtype=np.uint8) > 127).astype(np.int8)
    grid[forbidden == 1] = 0
    phase_timing_s["coarse_sa"] = time.perf_counter() - t_phase

    # Fine SA.
    t_phase = time.perf_counter()
    grid, _, hist_f = run_sa(sa_fn, grid, target, w_zone, forbidden, fi, 3.5, t_min, 0.999996, border, seed + 1)
    grid[forbidden == 1] = 0
    phase_timing_s["fine_sa"] = time.perf_counter() - t_phase

    # Refine SA (3 passes).
    hist_parts = [hist_c, hist_f]
    t_phase = time.perf_counter()
    for pidx, (iters, temp, alpha) in enumerate([(r1i, 2.0, 0.999997), (r2i, 1.7, 0.999997), (r3i, 1.4, 0.999998)]):
        t_ref = time.perf_counter()
        n_cur = compute_N(grid)
        underfill = np.clip(target - n_cur.astype(np.float32), 0.0, 8.0) / 8.0
        w_ref = (w_zone * (1.0 + uf_factor * underfill)).astype(np.float32)
        if pidx < 2:
            w_ref = compute_sealing_prevention_weights(w_ref, grid, target, hi_thr, seal_thr, seal_str)
        grid, _, hist_r = run_sa(sa_fn, grid, target, w_ref, forbidden, iters, temp, t_min, alpha, border, seed + 2 + pidx)
        grid[forbidden == 1] = 0
        hist_parts.append(hist_r)
        phase_timing_s[f"refine_pass_{pidx + 1}"] = time.perf_counter() - t_ref
    phase_timing_s["refine_sa_total"] = time.perf_counter() - t_phase

    # Optional solver-guided rescue pass: increase pressure around unresolved
    # regions so SA can prioritize solvability-critical structures.
    solvability_penalty_stats = {
        "enabled": bool(solvability_penalty_pass),
        "applied": False,
    }
    if solvability_penalty_pass:
        t_phase = time.perf_counter()
        sr_pen_pre = solve_board(grid, max_rounds=120, mode="full")
        solvability_penalty_stats.update(
            {
                "pre_n_unknown": int(sr_pen_pre.n_unknown),
                "pre_coverage": float(sr_pen_pre.coverage),
            }
        )
        if sr_pen_pre.n_unknown > 0:
            unknown_mask = sr_pen_pre.state == UNKNOWN
            penalty_mask = binary_dilation(
                unknown_mask,
                structure=np.ones((3, 3), dtype=bool),
                iterations=1,
            )
            boost_scale = (1.0 + float(solvability_penalty_boost))
            w_pen = (w_zone * np.where(penalty_mask, boost_scale, 1.0)).astype(np.float32)
            probe_rate = float(runtime_calibration.get("probe_iters_per_s", 0.0))
            penalty_budget_s = min(6.0, max(0.0, remaining_s() - max(6.0, 0.30 * max_runtime_s)))
            penalty_iters = int(max(120_000, (fi + r1i + r2i + r3i) * float(solvability_penalty_iters_scale)))
            if probe_rate > 0.0 and penalty_budget_s > 0.0:
                penalty_iters = int(min(penalty_iters, max(80_000, probe_rate * penalty_budget_s)))
            if penalty_iters >= 80_000 and penalty_budget_s > 0.0:
                grid, _, hist_pen = run_sa(
                    sa_fn, grid, target, w_pen, forbidden,
                    penalty_iters, 1.8, t_min, 0.999997, border, seed + 77
                )
                grid[forbidden == 1] = 0
                hist_parts.append(hist_pen)
                sr_pen_post = solve_board(grid, max_rounds=120, mode="full")
                solvability_penalty_stats.update(
                    {
                        "applied": True,
                        "boost": float(solvability_penalty_boost),
                        "penalty_iters": int(penalty_iters),
                        "penalty_budget_s": float(penalty_budget_s),
                        "post_n_unknown": int(sr_pen_post.n_unknown),
                        "post_coverage": float(sr_pen_post.coverage),
                    }
                )
        phase_timing_s["solvability_penalty_pass"] = time.perf_counter() - t_phase

    assert_board_valid(grid, forbidden, "post-sa")
    target_work = target
    w_zone_work = w_zone
    adaptive_local_stats = {
        "enabled": bool(adaptive_local_cap),
        "applied": False,
        "reason": "disabled",
        "ladder": [float(v) for v in adaptive_local_cap_ladder],
        "steps": [],
    }

    if adaptive_local_cap:
        t_phase = time.perf_counter()
        probe_rate = float(runtime_calibration.get("probe_iters_per_s", 0.0))
        reserve_after_local_s = max(6.0, min(18.0, 0.45 * float(max_runtime_s)))
        total_local_budget = min(
            float(adaptive_local_sa_budget_s),
            max(0.0, remaining_s() - reserve_after_local_s),
        )
        adaptive_local_stats["local_sa_budget_s"] = float(total_local_budget)
        adaptive_local_stats["local_budget_used_s"] = 0.0

        if total_local_budget < 0.8:
            adaptive_local_stats["reason"] = "insufficient_runtime_budget"
        else:
            step_records = []
            budget_used = 0.0
            applied_any = False
            reason = "applied"
            ladder = [float(v) for v in adaptive_local_cap_ladder]
            for step_idx, cap_value in enumerate(ladder, start=1):
                step_record = {
                    "step": int(step_idx),
                    "cap_value": float(cap_value),
                }
                sr_step_pre = solve_board(grid, max_rounds=180, mode="full")
                step_record.update(
                    {
                        "pre_n_unknown": int(sr_step_pre.n_unknown),
                        "pre_coverage": float(sr_step_pre.coverage),
                        "pre_solvable": bool(sr_step_pre.solvable),
                    }
                )

                if sr_step_pre.n_unknown <= int(adaptive_local_unknown_stop):
                    step_record["status"] = "unknown_stop_reached"
                    step_records.append(step_record)
                    reason = "unknown_stop_reached"
                    break

                comps, comp_stats = extract_sealed_components(
                    sr_step_pre.state,
                    min_component_size=int(adaptive_local_min_component),
                    max_components=int(adaptive_local_max_components),
                    dilation_steps=int(adaptive_local_dilation),
                )
                step_record.update(comp_stats)
                if not comps:
                    step_record["status"] = "no_sealed_components"
                    step_records.append(step_record)
                    reason = "no_sealed_components"
                    break

                selected = comps[: max(1, int(adaptive_local_clusters_per_step))]
                risk_mask = np.logical_or.reduce([c["mask"] for c in selected]).astype(bool)
                step_record["selected_clusters_this_step"] = int(len(selected))
                step_record["selected_cluster_sizes"] = [
                    int(c["component_size"]) for c in selected[:10]
                ]

                target_local, cap_stats = apply_local_target_cap(
                    target=target_work,
                    target_eval=target_eval,
                    risk_mask=risk_mask,
                    local_cap=float(cap_value),
                    trigger_eval=float(adaptive_local_trigger_eval),
                )
                step_record.update(cap_stats)

                remaining_steps = max(1, len(ladder) - step_idx + 1)
                remaining_budget = max(0.0, total_local_budget - budget_used)
                step_budget = min(
                    max(0.8, remaining_budget / float(remaining_steps)),
                    float(adaptive_local_sa_budget_s),
                )
                step_budget = min(
                    step_budget,
                    max(0.0, remaining_s() - max(4.0, min(12.0, 0.25 * float(max_runtime_s)))),
                )
                step_record["local_step_budget_s"] = float(step_budget)
                if step_budget < 0.8:
                    step_record["status"] = "step_budget_too_low"
                    step_records.append(step_record)
                    reason = "insufficient_runtime_budget"
                    break

                adaptive_total_iters = int(max(220_000, max(probe_rate, 50_000.0) * step_budget))
                _c2, fi2, r12, r22, r32 = split_total_iters(adaptive_total_iters)
                fi2 = int(fi2 + _c2)
                step_record["local_schedule_iters"] = {
                    "fine": int(fi2),
                    "refine1": int(r12),
                    "refine2": int(r22),
                    "refine3": int(r32),
                    "total": int(fi2 + r12 + r22 + r32),
                }

                target_work = target_local
                w_zone_work = compute_zone_aware_weights(target_work, bp_true, bp_trans, hi_boost, hi_thr)

                grid, _, hist_f_local = run_sa(
                    sa_fn, grid, target_work, w_zone_work, forbidden,
                    fi2, 3.0, t_min, 0.999996, border, seed + 101 + step_idx
                )
                grid[forbidden == 1] = 0
                hist_parts.append(hist_f_local)

                for pidx, (iters, temp, alpha) in enumerate(
                    [(r12, 2.0, 0.999997), (r22, 1.7, 0.999997), (r32, 1.4, 0.999998)]
                ):
                    n_cur = compute_N(grid)
                    underfill = np.clip(target_work - n_cur.astype(np.float32), 0.0, 8.0) / 8.0
                    w_ref = (w_zone_work * (1.0 + uf_factor * underfill)).astype(np.float32)
                    if pidx < 2:
                        w_ref = compute_sealing_prevention_weights(
                            w_ref, grid, target_work, hi_thr, seal_thr, seal_str
                        )
                    grid, _, hist_r_local = run_sa(
                        sa_fn, grid, target_work, w_ref, forbidden,
                        iters, temp, t_min, alpha, border, seed + 131 + step_idx + pidx
                    )
                    grid[forbidden == 1] = 0
                    hist_parts.append(hist_r_local)

                sr_step_post = solve_board(grid, max_rounds=180, mode="full")
                step_record.update(
                    {
                        "status": "applied",
                        "post_n_unknown": int(sr_step_post.n_unknown),
                        "post_coverage": float(sr_step_post.coverage),
                        "post_solvable": bool(sr_step_post.solvable),
                    }
                )
                step_records.append(step_record)
                applied_any = True
                budget_used += float(step_budget)
                assert_board_valid(grid, forbidden, f"post-local-cap-step{step_idx}")

                if sr_step_post.n_unknown <= int(adaptive_local_unknown_stop):
                    reason = "unknown_stop_reached"
                    break

            adaptive_local_stats["steps"] = step_records
            adaptive_local_stats["local_budget_used_s"] = float(budget_used)
            adaptive_local_stats["applied"] = bool(applied_any)
            adaptive_local_stats["reason"] = reason if applied_any else "no_effect"
        phase_timing_s["adaptive_local_cap"] = time.perf_counter() - t_phase

    # Repair.
    sr_pre = solve_board(grid, max_rounds=50, mode="trial")
    repair_budget = min(float(phase1_budget_s), max(0.5, remaining_s() - 2.0))
    t_phase = time.perf_counter()
    grid, _, repair_reason = run_phase1_repair(
        grid, target_work, w_zone_work, forbidden,
        time_budget_s=repair_budget, max_rounds=180, search_radius=6,
        verbose=False, checkpoint_dir=out_dir,
        candidate_top_k=6, parallel_eval=True, max_workers=(os.cpu_count() or 1)
    )
    phase_timing_s["phase1_repair"] = time.perf_counter() - t_phase
    grid[forbidden == 1] = 0
    phase2_budget = min(float(phase2_budget_s), max(0.0, remaining_s() - 1.0))
    phase2_unknown_ref = int(sr_pre.n_unknown)
    phase2_outer = 24 if phase2_unknown_ref > 5_000 else (20 if phase2_unknown_ref > 1_000 else 12)
    phase2_clusters = 96 if phase2_unknown_ref > 5_000 else (64 if phase2_unknown_ref > 1_000 else 24)
    phase2_ext = 40 if phase2_unknown_ref > 5_000 else (32 if phase2_unknown_ref > 1_000 else 16)
    phase2_pair_trials = 24 if phase2_unknown_ref > 1_000 else 12
    phase2_pair_combos = 96 if phase2_unknown_ref > 5_000 else (64 if phase2_unknown_ref > 1_000 else 20)
    t_phase = time.perf_counter()
    if phase2_budget >= 1.0:
        grid, n_phase2_fixes, _ = run_phase2_full_repair(
            grid, target_eval, forbidden, verbose=False,
            time_budget_s=phase2_budget,
            max_outer_iterations=phase2_outer,
            max_clusters_per_iteration=phase2_clusters,
            max_ext_mines_per_cluster=phase2_ext,
            trial_max_rounds=80,
            solve_max_rounds=220,
            pair_trial_limit=phase2_pair_trials,
            pair_combo_limit=phase2_pair_combos,
        )
    else:
        n_phase2_fixes = 0
    phase_timing_s["phase2_repair"] = time.perf_counter() - t_phase
    grid[forbidden == 1] = 0
    assert_board_valid(grid, forbidden, "post-repair")

    # Late rescue mode: one more localized cap + short SA + short phase2, only
    # if unresolved unknowns remain and runtime budget allows.
    rescue_mode_stats = {
        "enabled": True,
        "applied": False,
    }
    t_phase = time.perf_counter()
    sr_after_phase2 = solve_board(grid, max_rounds=140, mode="full")
    rescue_mode_stats.update(
        {
            "pre_n_unknown": int(sr_after_phase2.n_unknown),
            "pre_coverage": float(sr_after_phase2.coverage),
            "pre_solvable": bool(sr_after_phase2.solvable),
        }
    )
    if sr_after_phase2.n_unknown > 0 and remaining_s() > 1.5:
        comps_rescue, comp_stats_rescue = extract_sealed_components(
            sr_after_phase2.state,
            min_component_size=max(24, int(adaptive_local_min_component // 2)),
            max_components=max(20, int(adaptive_local_max_components)),
            dilation_steps=max(1, int(adaptive_local_dilation)),
        )
        rescue_mode_stats.update(comp_stats_rescue)
        if comps_rescue:
            selected_rescue = comps_rescue[: min(20, len(comps_rescue))]
            risk_mask_rescue = np.logical_or.reduce([c["mask"] for c in selected_rescue]).astype(bool)
            rescue_target, rescue_cap_stats = apply_local_target_cap(
                target=target_work,
                target_eval=target_eval,
                risk_mask=risk_mask_rescue,
                local_cap=min(4.6, float(adaptive_local_cap_value)),
                trigger_eval=max(7.0, float(adaptive_local_trigger_eval) - 0.2),
            )
            rescue_mode_stats.update(rescue_cap_stats)

            rescue_budget_s = min(3.5, max(0.0, remaining_s() - 1.8))
            rescue_mode_stats["sa_budget_s"] = float(rescue_budget_s)
            probe_rate = float(runtime_calibration.get("probe_iters_per_s", 0.0))
            if rescue_budget_s >= 0.8:
                rescue_total_iters = int(max(160_000, max(probe_rate, 50_000.0) * rescue_budget_s))
                c3, fi3, _r13, _r23, r33 = split_total_iters(rescue_total_iters)
                fi3 = int(fi3 + c3 + _r13 + _r23)
                rescue_mode_stats["sa_iters"] = int(fi3 + r33)
                target_work = rescue_target
                w_zone_work = compute_zone_aware_weights(target_work, bp_true, bp_trans, hi_boost, hi_thr)

                grid, _, hist_rescue_f = run_sa(
                    sa_fn, grid, target_work, w_zone_work, forbidden,
                    fi3, 2.4, t_min, 0.999997, border, seed + 211
                )
                grid[forbidden == 1] = 0
                hist_parts.append(hist_rescue_f)
                n_cur = compute_N(grid)
                underfill = np.clip(target_work - n_cur.astype(np.float32), 0.0, 8.0) / 8.0
                w_ref = (w_zone_work * (1.0 + uf_factor * underfill)).astype(np.float32)
                w_ref = compute_sealing_prevention_weights(w_ref, grid, target_work, hi_thr, seal_thr, seal_str)
                grid, _, hist_rescue_r = run_sa(
                    sa_fn, grid, target_work, w_ref, forbidden,
                    r33, 1.6, t_min, 0.999998, border, seed + 212
                )
                grid[forbidden == 1] = 0
                hist_parts.append(hist_rescue_r)

                rescue_phase2_budget = min(2.4, max(0.0, remaining_s() - 1.2))
                rescue_mode_stats["phase2_budget_s"] = float(rescue_phase2_budget)
                if rescue_phase2_budget >= 0.8:
                    grid, rescue_nfix, _ = run_phase2_full_repair(
                        grid, target_eval, forbidden, verbose=False,
                        time_budget_s=rescue_phase2_budget,
                        max_outer_iterations=10,
                        max_clusters_per_iteration=48,
                        max_ext_mines_per_cluster=32,
                        trial_max_rounds=80,
                        solve_max_rounds=220,
                        pair_trial_limit=20,
                        pair_combo_limit=72,
                    )
                    grid[forbidden == 1] = 0
                    n_phase2_fixes += int(rescue_nfix)
                    rescue_mode_stats["phase2_added_fixes"] = int(rescue_nfix)

                sr_rescue_post = solve_board(grid, max_rounds=180, mode="full")
                rescue_mode_stats.update(
                    {
                        "applied": True,
                        "post_n_unknown": int(sr_rescue_post.n_unknown),
                        "post_coverage": float(sr_rescue_post.coverage),
                        "post_solvable": bool(sr_rescue_post.solvable),
                    }
                )
                if sr_rescue_post.n_unknown > 0 and remaining_s() > 2.2:
                    hard_stage_stats = {
                        "enabled": True,
                        "applied": False,
                        "pre_n_unknown": int(sr_rescue_post.n_unknown),
                    }
                    comps_hard, comp_stats_hard = extract_sealed_components(
                        sr_rescue_post.state,
                        min_component_size=max(18, int(adaptive_local_min_component // 3)),
                        max_components=14,
                        dilation_steps=max(1, int(adaptive_local_dilation)),
                    )
                    hard_stage_stats.update(comp_stats_hard)
                    if comps_hard:
                        selected_hard = comps_hard[: min(12, len(comps_hard))]
                        risk_mask_hard = np.logical_or.reduce([c["mask"] for c in selected_hard]).astype(bool)
                        hard_target, hard_cap_stats = apply_local_target_cap(
                            target=target_work,
                            target_eval=target_eval,
                            risk_mask=risk_mask_hard,
                            local_cap=min(4.2, float(adaptive_local_cap_value)),
                            trigger_eval=max(6.6, float(adaptive_local_trigger_eval) - 0.5),
                        )
                        hard_stage_stats.update(hard_cap_stats)

                        hard_sa_budget_s = min(0.9, max(0.0, remaining_s() - 0.8))
                        hard_stage_stats["sa_budget_s"] = float(hard_sa_budget_s)
                        if hard_sa_budget_s >= 0.5:
                            hard_total_iters = int(max(70_000, max(probe_rate, 45_000.0) * hard_sa_budget_s))
                            c4, fi4, _r14, _r24, r34 = split_total_iters(hard_total_iters)
                            fi4 = int(fi4 + c4 + _r14 + _r24)
                            hard_stage_stats["sa_iters"] = int(fi4 + r34)
                            target_work = hard_target
                            w_zone_work = compute_zone_aware_weights(target_work, bp_true, bp_trans, hi_boost, hi_thr)

                            grid, _, hist_hard_f = run_sa(
                                sa_fn, grid, target_work, w_zone_work, forbidden,
                                fi4, 2.1, t_min, 0.999997, border, seed + 213
                            )
                            grid[forbidden == 1] = 0
                            hist_parts.append(hist_hard_f)
                            n_cur = compute_N(grid)
                            underfill = np.clip(target_work - n_cur.astype(np.float32), 0.0, 8.0) / 8.0
                            w_ref = (w_zone_work * (1.0 + uf_factor * underfill)).astype(np.float32)
                            w_ref = compute_sealing_prevention_weights(w_ref, grid, target_work, hi_thr, seal_thr, seal_str)
                            grid, _, hist_hard_r = run_sa(
                                sa_fn, grid, target_work, w_ref, forbidden,
                                r34, 1.4, t_min, 0.999998, border, seed + 214
                            )
                            grid[forbidden == 1] = 0
                            hist_parts.append(hist_hard_r)

                        hard_phase2_budget = min(0.7, max(0.0, remaining_s() - 0.5))
                        hard_stage_stats["phase2_budget_s"] = float(hard_phase2_budget)
                        if hard_phase2_budget >= 0.5:
                            grid, hard_nfix, _ = run_phase2_full_repair(
                                grid, target_eval, forbidden, verbose=False,
                                time_budget_s=hard_phase2_budget,
                                max_outer_iterations=6,
                                max_clusters_per_iteration=28,
                                max_ext_mines_per_cluster=24,
                                trial_max_rounds=70,
                                solve_max_rounds=180,
                                pair_trial_limit=14,
                                pair_combo_limit=40,
                            )
                            grid[forbidden == 1] = 0
                            n_phase2_fixes += int(hard_nfix)
                            hard_stage_stats["phase2_added_fixes"] = int(hard_nfix)

                        sr_hard_post = solve_board(grid, max_rounds=140, mode="full")
                        hard_stage_stats.update(
                            {
                                "applied": True,
                                "post_n_unknown": int(sr_hard_post.n_unknown),
                                "post_coverage": float(sr_hard_post.coverage),
                                "post_solvable": bool(sr_hard_post.solvable),
                            }
                        )
                    rescue_mode_stats["hard_stage"] = hard_stage_stats
                assert_board_valid(grid, forbidden, "post-rescue")
    phase_timing_s["rescue_mode"] = time.perf_counter() - t_phase

    final_rounds = 160 if remaining_s() > 4.0 else (100 if remaining_s() > 2.0 else 60)
    t_phase = time.perf_counter()
    sr = solve_board(grid, max_rounds=final_rounds, mode="full")
    phase_timing_s["final_solve"] = time.perf_counter() - t_phase
    N = compute_N(grid)
    err = np.abs(N.astype(float) - target_eval)
    solve_time = time.perf_counter() - t0
    schedule_iters = {
        "coarse": int(ci),
        "fine": int(fi),
        "refine1": int(r1i),
        "refine2": int(r2i),
        "refine3": int(r3i),
        "total": int(ci + fi + r1i + r2i + r3i),
    }
    runtime_gates = {
        "n_unknown_zero": bool(sr.n_unknown == 0),
        "coverage_1000": bool(sr.coverage >= 0.9999),
        "solvable_true": bool(sr.solvable),
        "mine_accuracy_1000": bool(sr.mine_accuracy >= 0.999),
        "aspect_ratio_within_0_5pct": bool(sizing["gate_aspect_ratio_within_tolerance"]),
        "python_64bit": bool(provenance.get("python_bits") == 64),
        "total_time_under_20": False,
        "total_time_under_50": False,
        "total_time_under_60": False,
        "profile_generated": False,
        "hotspot_candidates_identified": False,
    }

    metrics = {
        "run_id": provenance.get("run_id"),
        "run_tag": provenance.get("run_tag"),
        "board": f"{board_w}x{board_h}",
        "cells": cells,
        "n_unknown": int(sr.n_unknown),
        "coverage": float(sr.coverage),
        "solvable": bool(sr.solvable),
        "mine_accuracy": float(sr.mine_accuracy),
        "mine_density": float(grid.mean()),
        "mean_abs_error": float(err.mean()),
        "hi_err": float(err[hi_mask].mean()) if hi_mask.any() else 0.0,
        "true_bg_err": float(err[true_bg].mean()) if true_bg.any() else 0.0,
        "corridor_pct": float(corridor_pct),
        "repair_reason": repair_reason,
        "n_phase2_fixes": int(n_phase2_fixes),
        "solve_time_s": float(solve_time),
        "total_time_s": None,
        "seed": int(seed),
        "iters_multiplier": float(iters_multiplier),
        "max_runtime_s": float(max_runtime_s),
        "runtime_budget_hit": False,
        "pw_knee": float(pw_knee),
        "pw_t_max": float(pw_t_max),
        "hi_boost": float(hi_boost),
        "phase1_budget_s": float(phase1_budget_s),
        "phase2_budget_s": float(phase2_budget_s),
        "contrast_factor": float(contrast_factor),
        "sa_budget_multiplier": float(sa_budget_multiplier),
        "solvability_penalty_pass": bool(solvability_penalty_pass),
        "solvability_penalty_boost": float(solvability_penalty_boost),
        "solvability_penalty_iters_scale": float(solvability_penalty_iters_scale),
        "source_width": int(sizing["source_width"]),
        "source_height": int(sizing["source_height"]),
        "source_ratio": float(sizing["source_ratio"]),
        "board_width": int(board_w),
        "board_height": int(board_h),
        "board_ratio": float(sizing["board_ratio"]),
        "aspect_ratio_relative_error": float(sizing["aspect_ratio_relative_error"]),
        "aspect_ratio_tolerance": float(sizing["aspect_ratio_tolerance"]),
        "gate_aspect_ratio_within_0_5pct": bool(sizing["gate_aspect_ratio_within_tolerance"]),
        "schedule_iters": schedule_iters,
        "runtime_calibration": runtime_calibration,
        "preprocess": {
            "loader": "load_image_smart",
            "contrast_factor": float(contrast_factor),
            "target_eval_stats": target_eval_stats,
            "target_after_piecewise_stats": target_work_stats,
            "harm_signal_t_ge_7_pct": float(target_eval_stats.get("pct_t_ge_7", 0.0)),
            "harm_signal_t_ge_6_pct": float(target_eval_stats.get("pct_t_ge_6", 0.0)),
            "harm_signal_t_le_1_pct": float(target_eval_stats.get("pct_t_le_1", 0.0)),
        },
        "solvability_penalty": solvability_penalty_stats,
        "adaptive_local_cap": adaptive_local_stats,
        "rescue_mode": rescue_mode_stats,
        "phase2_config": {
            "outer_iterations": int(phase2_outer),
            "clusters_per_iteration": int(phase2_clusters),
            "ext_mines_per_cluster": int(phase2_ext),
            "pair_trial_limit": int(phase2_pair_trials),
            "pair_combo_limit": int(phase2_pair_combos),
        },
        "parallel_config": {
            "phase1_parallel_eval": True,
            "phase1_max_workers": int(os.cpu_count() or 1),
            "numba_num_threads": provenance.get("numba_num_threads"),
            "numba_threading_layer": provenance.get("numba_threading_layer"),
        },
        "phase_timing_s": phase_timing_s,
        "runtime_gates": runtime_gates,
        "provenance": provenance,
        "analysis_schema_version": "v2_phase_timing_ledger",
        "historical_reference": {
            "iter9_original_total_time_s": 11.6,
            "iter9_research_total_time_s": 14.9,
            "full_solve_target_time_s": 20.0,
        },
    }

    visual_path = os.path.join(out_dir, f"visual_{board_w}x{board_h}.png")
    metrics_path = os.path.join(out_dir, f"metrics_{board_w}x{board_h}.json")
    grid_path = os.path.join(out_dir, f"grid_{board_w}x{board_h}.npy")
    metrics["artifacts"] = {
        "visual_path": visual_path,
        "metrics_path": metrics_path,
        "grid_path": grid_path,
    }

    t_phase = time.perf_counter()
    render_visual_report(
        target_eval,
        grid,
        sr,
        title=(
            f"Mine-Streaker - {board_w}x{board_h} ({cells:,} cells)  "
            f"[solvable={sr.solvable}  coverage={sr.coverage:.4f}]"
        ),
        save_path=visual_path,
        dpi=150,
    )
    atomic_save_npy(grid, grid_path)
    total_time = time.perf_counter() - t0
    phase_timing_s["render_and_write"] = time.perf_counter() - t_phase

    runtime_gates["total_time_under_20"] = bool(total_time < 20.0)
    runtime_gates["total_time_under_50"] = bool(total_time < 50.0)
    runtime_gates["total_time_under_60"] = bool(total_time < 60.0)
    dominant_phase = max(phase_timing_s.items(), key=lambda kv: kv[1])[0] if phase_timing_s else None
    dominant_phase_share = (
        float(phase_timing_s[dominant_phase] / max(total_time, 1e-9))
        if dominant_phase is not None else 0.0
    )
    metrics["total_time_s"] = float(total_time)
    metrics["runtime_budget_hit"] = bool(total_time > max_runtime_s)
    metrics["phase_timing_s"] = phase_timing_s
    metrics["runtime_gates"] = runtime_gates
    metrics["dominant_phase"] = dominant_phase
    metrics["dominant_phase_share"] = dominant_phase_share
    metrics["hotspot_top3"] = []
    metrics["delta_vs_iter9_research_s"] = float(total_time - 14.9)
    metrics["delta_vs_iter9_original_s"] = float(total_time - 11.6)

    atomic_save_json(metrics, metrics_path)

    print(f"Saved visual:  {visual_path}", flush=True)
    print(f"Saved metrics: {metrics_path}", flush=True)
    print(f"Saved grid:    {grid_path}", flush=True)
    print(
        f"Summary: n_unknown={metrics['n_unknown']} "
        f"coverage={metrics['coverage']:.5f} "
        f"hi_err={metrics['hi_err']:.4f} time={metrics['total_time_s']:.1f}s",
        flush=True,
    )
    print(
        "Gates: "
        f"n0={runtime_gates['n_unknown_zero']} "
        f"cov1={runtime_gates['coverage_1000']} "
        f"solvable={runtime_gates['solvable_true']} "
        f"t<20={runtime_gates['total_time_under_20']} "
        f"t<50={runtime_gates['total_time_under_50']}",
        flush=True,
    )
    return metrics


def main():
    parser = argparse.ArgumentParser(description="Generate a visual report for a custom source image with runtime-calibrated SA.")
    parser.add_argument("--image", default="assets/input_source_image.png", help="Input image path.")
    parser.add_argument(
        "--copy-from",
        default=None,
        help="Optional source image path to copy into --copy-to before running."
    )
    parser.add_argument(
        "--copy-to",
        default="assets/input_source_image.png",
        help="Destination path used with --copy-from."
    )
    parser.add_argument("--out-dir", default="results/iris3d_300w_autoar", help="Output directory.")
    parser.add_argument("--board-w", type=int, default=300, help="Board width (minimum 300). Height is computed from source image ratio.")
    parser.add_argument("--board-h", type=int, default=None, help="Deprecated. Ignored; height is always derived from runtime image ratio.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed.")
    parser.add_argument("--iters-multiplier", type=float, default=0.25, help="Scale factor for SA iterations.")
    parser.add_argument("--max-runtime-s", type=float, default=50.0, help="Target wall-clock runtime budget.")
    parser.add_argument("--pw-knee", type=float, default=4.0, help="Piecewise compression knee.")
    parser.add_argument("--pw-t-max", type=float, default=6.0, help="Piecewise compression cap (global).")
    parser.add_argument("--contrast-factor", type=float, default=2.0, help="Contrast factor for load_image_smart preprocessing.")
    parser.add_argument("--hi-boost", type=float, default=18.0, help="High-zone weighting boost.")
    parser.add_argument("--sa-budget-multiplier", type=float, default=1.0, help="Scale SA budget after throughput probe (e.g., 3.0 for method-testing stress runs).")
    parser.add_argument("--method-test-sa-3x", action="store_true", help="Force SA budget multiplier to at least 3x for method-testing runs.")
    parser.add_argument("--phase1-budget-s", type=float, default=8.0, help="Phase-1 repair time budget cap.")
    parser.add_argument("--phase2-budget-s", type=float, default=6.0, help="Phase-2 repair time budget cap.")
    parser.add_argument("--adaptive-local-cap", action="store_true", help="Enable sealed-risk local target cap pass after first solve.")
    parser.add_argument("--adaptive-local-cap-value", type=float, default=4.6, help="Local cap value applied in sealed-risk regions.")
    parser.add_argument("--adaptive-local-trigger-eval", type=float, default=7.5, help="Only cap cells where target_eval exceeds this value.")
    parser.add_argument("--adaptive-local-cap-ladder", default="5.4,5.0,4.8,4.6", help="Comma-separated local cap ladder values.")
    parser.add_argument("--adaptive-local-min-component", type=int, default=64, help="Minimum sealed component size to include.")
    parser.add_argument("--adaptive-local-max-components", type=int, default=50, help="Max sealed components to include.")
    parser.add_argument("--adaptive-local-clusters-per-step", type=int, default=10, help="How many largest sealed clusters to cap per ladder step.")
    parser.add_argument("--adaptive-local-dilation", type=int, default=1, help="Risk-mask dilation steps.")
    parser.add_argument("--adaptive-local-unknown-stop", type=int, default=0, help="Stop ladder once n_unknown <= this value.")
    parser.add_argument("--adaptive-local-sa-budget-s", type=float, default=10.0, help="Extra fine/refine SA budget for local-cap rerun.")
    parser.add_argument("--solvability-penalty-pass", action="store_true", help="Enable solver-guided SA rescue pass.")
    parser.add_argument("--solvability-penalty-boost", type=float, default=2.0, help="Weight boost multiplier around unknown cells for rescue pass.")
    parser.add_argument("--solvability-penalty-iters-scale", type=float, default=0.12, help="Rescue-pass iters scale relative to fine+refine schedule.")
    parser.add_argument("--run-tag", default="", help="Optional free-form experiment tag.")
    parser.add_argument("--ledger-jsonl", default="results/experiment_ledger.jsonl", help="Append-only JSONL run ledger path.")
    parser.add_argument("--ledger-csv", default="results/experiment_ledger.csv", help="Append-only CSV run ledger path.")
    parser.add_argument("--no-ledger", action="store_true", help="Disable ledger writes for this run.")
    parser.add_argument("--profile-runtime", action="store_true", help="Enable cProfile artifact generation for hotspot analysis.")
    parser.add_argument("--profile-out-dir", default="", help="Directory for profiling artifacts. Defaults to <out-dir>/profile.")
    parser.add_argument("--profile-lines", action="store_true", help="Request optional line-level profiling when line_profiler is available.")
    parser.add_argument(
        "--allow-noncanonical",
        action="store_true",
        help=f"Set {ALLOW_NONCANONICAL_ENV}=1 for non-canonical source images."
    )
    args = parser.parse_args()

    def _parse_float_csv(text, fallback):
        vals = []
        for part in str(text).split(","):
            part = part.strip()
            if not part:
                continue
            try:
                vals.append(float(part))
            except ValueError:
                continue
        return vals if vals else list(fallback)

    adaptive_ladder = _parse_float_csv(
        args.adaptive_local_cap_ladder,
        [float(args.adaptive_local_cap_value)],
    )

    if args.method_test_sa_3x:
        args.sa_budget_multiplier = max(float(args.sa_budget_multiplier), 3.0)
    if args.contrast_factor <= 0.0:
        raise ValueError("--contrast-factor must be > 0")
    if args.sa_budget_multiplier <= 0.0:
        raise ValueError("--sa-budget-multiplier must be > 0")

    if args.allow_noncanonical:
        os.environ[ALLOW_NONCANONICAL_ENV] = "1"
        print(f"{ALLOW_NONCANONICAL_ENV}=1", flush=True)

    if args.copy_from:
        if not os.path.exists(args.copy_from):
            raise FileNotFoundError(f"--copy-from path not found: {args.copy_from}")
        dest_dir = os.path.dirname(args.copy_to)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        shutil.copy2(args.copy_from, args.copy_to)
        args.image = args.copy_to
        print(f"Copied source image: {args.copy_from} -> {args.copy_to}", flush=True)

    resolved_image = resolve_image_path(args.image)
    if resolved_image != args.image:
        print(f"Resolved image path alias: {args.image} -> {resolved_image}", flush=True)
    args.image = resolved_image
    if not os.path.exists(args.image):
        raise FileNotFoundError(f"Input image path not found: {args.image}")

    run_id = uuid.uuid4().hex
    provenance = collect_run_provenance(
        image_path=args.image,
        allow_noncanonical=args.allow_noncanonical,
        run_id=run_id,
        run_tag=args.run_tag,
    )
    verify_source_image(args.image, halt_on_failure=True, verbose=True)
    profile_out_dir = args.profile_out_dir if args.profile_out_dir else os.path.join(args.out_dir, "profile")
    cprof = cProfile.Profile() if args.profile_runtime else None
    line_available = detect_line_profile_support()
    line_profile_obj = None
    line_profile_path = None

    runner = run_single_board
    if args.profile_lines and line_available:
        from line_profiler import LineProfiler
        line_profile_obj = LineProfiler()
        runner = line_profile_obj(run_single_board)

    if cprof is not None:
        cprof.enable()
    metrics = runner(
        image_path=args.image,
        out_dir=args.out_dir,
        provenance=provenance,
        board_w=args.board_w,
        board_h=args.board_h,
        seed=args.seed,
        iters_multiplier=args.iters_multiplier,
        max_runtime_s=args.max_runtime_s,
        pw_knee=args.pw_knee,
        pw_t_max=args.pw_t_max,
        contrast_factor=args.contrast_factor,
        hi_boost=args.hi_boost,
        sa_budget_multiplier=args.sa_budget_multiplier,
        phase1_budget_s=args.phase1_budget_s,
        phase2_budget_s=args.phase2_budget_s,
        adaptive_local_cap=args.adaptive_local_cap,
        adaptive_local_cap_value=args.adaptive_local_cap_value,
        adaptive_local_trigger_eval=args.adaptive_local_trigger_eval,
        adaptive_local_cap_ladder=adaptive_ladder,
        adaptive_local_min_component=args.adaptive_local_min_component,
        adaptive_local_max_components=args.adaptive_local_max_components,
        adaptive_local_clusters_per_step=args.adaptive_local_clusters_per_step,
        adaptive_local_dilation=args.adaptive_local_dilation,
        adaptive_local_unknown_stop=args.adaptive_local_unknown_stop,
        adaptive_local_sa_budget_s=args.adaptive_local_sa_budget_s,
        solvability_penalty_pass=args.solvability_penalty_pass,
        solvability_penalty_boost=args.solvability_penalty_boost,
        solvability_penalty_iters_scale=args.solvability_penalty_iters_scale,
    )
    if cprof is not None:
        cprof.disable()

    if line_profile_obj is not None:
        line_profile_path = export_line_profile_artifact(
            line_profiler_obj=line_profile_obj,
            profile_out_dir=profile_out_dir,
            run_id=run_id,
        )

    metrics["line_profile"] = {
        "requested": bool(args.profile_lines),
        "available": bool(line_available),
        "generated": bool(line_profile_path),
        "artifact_path": line_profile_path,
    }

    if cprof is not None:
        profile_artifacts = export_cprofile_artifacts(
            profile=cprof,
            profile_out_dir=profile_out_dir,
            run_id=run_id,
            total_time_s=float(metrics.get("total_time_s", 0.0)),
        )
        metrics["profile_artifacts"] = profile_artifacts
        metrics["runtime_gates"]["profile_generated"] = True
        metrics["runtime_gates"]["hotspot_candidates_identified"] = (
            profile_artifacts.get("optimization_candidates_count", 0) > 0
        )
        metrics["hotspot_top3"] = profile_artifacts.get("top3_functions_by_cum_time", [])
        metrics["hotspot_top3_64bit_candidates"] = profile_artifacts.get(
            "top3_64bit_candidates_by_cum_time", []
        )
        if not metrics["runtime_gates"].get("total_time_under_50", False):
            metrics["sla_failure_hotspots"] = metrics["hotspot_top3"]
    else:
        metrics["runtime_gates"]["profile_generated"] = False
        metrics["runtime_gates"]["hotspot_candidates_identified"] = False
        metrics["hotspot_top3_64bit_candidates"] = []

    metrics_path = metrics.get("artifacts", {}).get("metrics_path")
    if metrics_path:
        atomic_save_json(metrics, metrics_path)

    if not args.no_ledger:
        append_jsonl_record(args.ledger_jsonl, metrics)
        append_csv_row(args.ledger_csv, build_ledger_row(metrics))
        print(f"Ledger append: {args.ledger_jsonl}", flush=True)
        print(f"Ledger append: {args.ledger_csv}", flush=True)


if __name__ == "__main__":
    main()
