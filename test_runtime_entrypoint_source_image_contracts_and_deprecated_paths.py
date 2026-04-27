#!/usr/bin/env python3

"""
Repair-only board follow-up runner for line_art_irl_9.

This script starts from a saved baseline mine grid and runs only late-repair
variants (no SA / no adaptive-local fallback path), then emits metrics, grid,
visual, move log, and ledger rows.

Legacy repair-only campaign replay runner for saved baseline grids.

This script starts from an existing baseline mine grid and matching baseline
metrics, then runs late-stage repair variants without running the full normal
reconstruction pipeline. It does not perform simulated annealing from scratch,
and it does not represent the current main source-image runtime workflow.

Current main entry points:
- Use `run_iter9.py` for normal single-image reconstruction runs.
- Use `run_benchmark.py` for benchmark and regression validation.

This file is retained for historical reproducibility of repair-only campaign
experiments, especially the `line_art_irl_9` late-stage repair campaign. It can
replay known baseline grids, compare repair-only variants, and emit metrics,
grids, visual reports, move logs, and ledger rows for campaign analysis.

Soft deprecation candidate:
This means the file is not currently recommended as a primary workflow for new
experiments, but it is also not safe to delete yet. It may still be useful for
reproducing historical campaign results, auditing prior repair decisions, or
comparing old repair-only behavior against newer routed repair behavior.

Do not remove this file unless a later cleanup pass confirms that historical
repair-only campaign replay is no longer needed and any required reproducibility
evidence has been archived elsewhere.
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import convolve, label as nd_label

from assets.image_guard import ALLOW_NONCANONICAL_ENV, verify_source_image
from board_sizing import derive_board_from_width
from core import (
    apply_piecewise_T_compression,
    assert_board_valid,
    compute_N,
    compute_zone_aware_weights,
    load_image_smart,
)
from corridors import build_adaptive_corridors
from repair import run_phase2_full_repair
from run_iris3d_visual_report import render_visual_report
from solver import UNKNOWN, ensure_solver_warmed, solve_board


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_save_json(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def atomic_save_npy(arr: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp.npy")
    np.save(tmp, arr)
    os.replace(tmp, path)


def append_jsonl_record(path: Path, record: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def append_csv_row(path: Path, row: dict) -> None:
    if not path:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def file_sha256(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def parse_bool(v):
    if isinstance(v, bool):
        return v
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in {"true", "1", "yes", "y"}:
        return True
    if s in {"false", "0", "no", "n"}:
        return False
    return None


def parse_int(v):
    try:
        if v is None or v == "":
            return None
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return None


def parse_float(v):
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def compute_error_metrics(grid: np.ndarray, target_eval: np.ndarray, hi_thr: float = 3.0) -> dict:
    N = compute_N(grid)
    err = np.abs(N.astype(float) - target_eval.astype(float))
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


def classify_visual_findings(n_rate_raw, coverage, hi_err, true_bg_err, mine_density):
    findings = []
    if true_bg_err is not None and true_bg_err >= 0.16:
        findings.append({"severity": "P1", "anomaly": "background leakage", "disposition": "rejected"})
    elif true_bg_err is not None and true_bg_err >= 0.08:
        findings.append({"severity": "P1", "anomaly": "background leakage", "disposition": "watch"})

    if coverage is not None and coverage < 0.97:
        findings.append({"severity": "P1", "anomaly": "smears", "disposition": "rejected"})

    if mine_density is not None and mine_density >= 0.36:
        findings.append({"severity": "P1", "anomaly": "polarity/background dominance", "disposition": "rejected"})
    elif mine_density is not None and mine_density >= 0.30 and (n_rate_raw or 0.0) > 0.0:
        findings.append({"severity": "P1", "anomaly": "polarity/background dominance", "disposition": "watch"})

    if hi_err is not None and hi_err >= 3.6:
        findings.append({"severity": "P1", "anomaly": "rays", "disposition": "rejected"})
    elif hi_err is not None and hi_err >= 3.1:
        findings.append({"severity": "P2", "anomaly": "rays", "disposition": "watch"})

    uniq = []
    seen = set()
    for f in findings:
        key = (f["severity"], f["anomaly"], f["disposition"])
        if key in seen:
            continue
        seen.add(key)
        uniq.append(f)
    return uniq


def visual_gate_status(findings):
    rejection_blockers = {"background leakage", "smears", "polarity/background dominance"}
    blocked = False
    for f in findings:
        if f["severity"] in {"P0", "P1"} and f["disposition"] == "rejected" and f["anomaly"] in rejection_blockers:
            blocked = True
            break
    if blocked:
        return "rejected", False
    has_watch = any(f["disposition"] == "watch" for f in findings)
    return ("watch", True) if has_watch else ("accepted", True)


def compute_command_signature(args: argparse.Namespace, baseline_grid_sha: str, baseline_metrics_sha: str) -> str:
    payload = {
        "image": str(Path(args.image).resolve()),
        "baseline_grid": str(Path(args.baseline_grid).resolve()),
        "baseline_metrics": str(Path(args.baseline_metrics).resolve()),
        "seed": int(args.seed),
        "repair_variant": args.repair_variant,
        "board_w": int(args.board_w),
        "pw_knee": float(args.pw_knee),
        "pw_t_max": float(args.pw_t_max),
        "contrast_factor": float(args.contrast_factor),
        "hi_boost": float(args.hi_boost),
        "phase2_budget_s": float(args.phase2_budget_s),
        "last100_budget_s": float(args.last100_budget_s),
        "baseline_grid_sha": baseline_grid_sha,
        "baseline_metrics_sha": baseline_metrics_sha,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def run_last100_repair(
    grid: np.ndarray,
    target: np.ndarray,
    target_eval: np.ndarray,
    forbidden: np.ndarray,
    *,
    budget_s: float,
    max_outer_iterations: int,
    trial_max_rounds: int,
    solve_max_rounds: int,
    pair_trial_limit: int,
    pair_combo_limit: int,
    max_error_delta_mean_abs: float,
    max_error_delta_true_bg: float,
    max_error_delta_hi: float,
    verbose: bool = True,
):
    t_start = time.perf_counter()
    work_grid = grid.copy()
    move_log = []
    n_fixes = 0
    stop_reason = "no_effect"

    def elapsed():
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

        base_q = compute_error_metrics(work_grid, target_eval)
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
                        ny, nx = int(cy + dy), int(cx + dx)
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

                trial_q = compute_error_metrics(trial, target_eval)
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
                entry["reject_reason"] = ""
                move_log.append(entry)
                visual_cost = max(0.0, d_mean) + max(0.0, d_bg) + max(0.0, d_hi)
                rank_key = (delta_unknown, -visual_cost)
                candidate = {
                    "rank_key": rank_key,
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
                        m1 = candidate_pool[i]
                        m2 = candidate_pool[j]
                        maybe_consider("pair", [m1, m2], int(comp_id), int(comp_size))
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


def get_git_metadata(repo_dir: Path) -> dict:
    try:
        commit = (
            os.popen(f'git -C "{repo_dir}" rev-parse HEAD')
            .read()
            .strip()
        )
    except Exception:
        commit = ""
    dirty = None
    try:
        rc = os.system(f'git -C "{repo_dir}" diff --quiet')
        dirty = bool(rc != 0)
    except Exception:
        dirty = None
    return {"git_commit": commit or None, "git_dirty": dirty}


def run_once(args: argparse.Namespace):
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    image_path = Path(args.image).resolve()
    baseline_grid_path = Path(args.baseline_grid).resolve()
    baseline_metrics_path = Path(args.baseline_metrics).resolve()
    t0 = time.perf_counter()

    if args.allow_noncanonical:
        os.environ[ALLOW_NONCANONICAL_ENV] = "1"
    verify_source_image(str(image_path), halt_on_failure=True, verbose=True)

    if not baseline_grid_path.exists():
        raise FileNotFoundError(f"Baseline grid missing: {baseline_grid_path}")
    if not baseline_metrics_path.exists():
        raise FileNotFoundError(f"Baseline metrics missing: {baseline_metrics_path}")

    baseline_grid = np.load(baseline_grid_path)
    baseline_metrics = json.loads(baseline_metrics_path.read_text(encoding="utf-8"))

    sizing = derive_board_from_width(
        image_path=str(image_path),
        board_width=int(args.board_w),
        min_width=300,
        ratio_tolerance=0.005,
    )
    board_w = int(sizing["board_width"])
    board_h = int(sizing["board_height"])
    if baseline_grid.shape != (board_h, board_w):
        raise RuntimeError(f"Baseline grid shape mismatch: expected {(board_h, board_w)} got {baseline_grid.shape}")

    target_eval = load_image_smart(
        str(image_path),
        board_w,
        board_h,
        invert=True,
        contrast_factor=float(args.contrast_factor),
    )
    target = apply_piecewise_T_compression(target_eval, float(args.pw_knee), float(args.pw_t_max))
    _weights = compute_zone_aware_weights(target, 8.0, 1.0, float(args.hi_boost), 3.0)
    forbidden, corridor_pct, _, _ = build_adaptive_corridors(target, border=3)
    assert_board_valid(baseline_grid, forbidden, label="baseline_grid")

    baseline_sr = solve_board(baseline_grid, max_rounds=500, mode="full")
    baseline_q = compute_error_metrics(baseline_grid, target_eval)

    work_grid = baseline_grid.copy()
    n_phase2_fixes = 0
    n_last100_fixes = 0
    phase2_applied = False
    last100_applied = False
    variant_stop_reason = "none"
    move_log = []

    variant = args.repair_variant
    if variant == "baseline_recheck":
        variant_stop_reason = "baseline_recheck"
    elif variant == "phase2_extended_only":
        phase2_applied = True
        work_grid, n_phase2_fixes, phase2_log = run_phase2_full_repair(
            work_grid,
            target,
            forbidden,
            verbose=True,
            time_budget_s=float(args.phase2_budget_s),
            max_outer_iterations=96,
            max_clusters_per_iteration=128,
            max_ext_mines_per_cluster=64,
            trial_max_rounds=120,
            solve_max_rounds=400,
            pair_trial_limit=48,
            pair_combo_limit=256,
        )
        for idx, entry in enumerate(phase2_log, start=1):
            move_log.append(
                {
                    "iteration": idx,
                    "component_id": None,
                    "component_size": int(entry.get("cluster_size", 0)),
                    "move_type": str(entry.get("move_type", "phase2")),
                    "removed_mines": [[int(y), int(x)] for y, x in entry.get("removed_mines", [])],
                    "pre_n_unknown": None,
                    "post_n_unknown": None,
                    "delta_unknown": int(entry.get("delta_unk", 0)),
                    "delta_mean_abs_error": None,
                    "delta_true_bg_err": None,
                    "delta_hi_err": None,
                    "accepted": True,
                    "reject_reason": "",
                    "stage": "phase2_extended_only",
                }
            )
        variant_stop_reason = "phase2_complete"
    elif variant == "last100_only":
        last100_applied = True
        work_grid, sr_last, n_last100_fixes, move_log, variant_stop_reason = run_last100_repair(
            work_grid,
            target,
            target_eval,
            forbidden,
            budget_s=float(args.last100_budget_s),
            max_outer_iterations=200,
            trial_max_rounds=160,
            solve_max_rounds=500,
            pair_trial_limit=64,
            pair_combo_limit=512,
            max_error_delta_mean_abs=0.020,
            max_error_delta_true_bg=0.010,
            max_error_delta_hi=0.050,
            verbose=True,
        )
        _ = sr_last
    elif variant == "phase2_extended_then_last100":
        phase2_applied = True
        work_grid, n_phase2_fixes, phase2_log = run_phase2_full_repair(
            work_grid,
            target,
            forbidden,
            verbose=True,
            time_budget_s=float(args.phase2_budget_s),
            max_outer_iterations=96,
            max_clusters_per_iteration=128,
            max_ext_mines_per_cluster=64,
            trial_max_rounds=120,
            solve_max_rounds=400,
            pair_trial_limit=48,
            pair_combo_limit=256,
        )
        for idx, entry in enumerate(phase2_log, start=1):
            move_log.append(
                {
                    "iteration": idx,
                    "component_id": None,
                    "component_size": int(entry.get("cluster_size", 0)),
                    "move_type": str(entry.get("move_type", "phase2")),
                    "removed_mines": [[int(y), int(x)] for y, x in entry.get("removed_mines", [])],
                    "pre_n_unknown": None,
                    "post_n_unknown": None,
                    "delta_unknown": int(entry.get("delta_unk", 0)),
                    "delta_mean_abs_error": None,
                    "delta_true_bg_err": None,
                    "delta_hi_err": None,
                    "accepted": True,
                    "reject_reason": "",
                    "stage": "phase2_first",
                }
            )
        sr_after_phase2 = solve_board(work_grid, max_rounds=500, mode="full")
        if 1 <= int(sr_after_phase2.n_unknown) <= 100:
            last100_applied = True
            work_grid, sr_last, n_last100_fixes, last100_log, last100_reason = run_last100_repair(
                work_grid,
                target,
                target_eval,
                forbidden,
                budget_s=float(args.last100_budget_s),
                max_outer_iterations=200,
                trial_max_rounds=160,
                solve_max_rounds=500,
                pair_trial_limit=64,
                pair_combo_limit=512,
                max_error_delta_mean_abs=0.020,
                max_error_delta_true_bg=0.010,
                max_error_delta_hi=0.050,
                verbose=True,
            )
            move_log.extend(last100_log)
            variant_stop_reason = f"phase2_then_last100:{last100_reason}"
            _ = sr_last
        else:
            variant_stop_reason = "phase2_then_last100:not_applicable"
    else:
        raise ValueError(f"Unsupported repair variant: {variant}")

    final_sr = solve_board(work_grid, max_rounds=500, mode="full")
    final_q = compute_error_metrics(work_grid, target_eval)
    n_rate_raw = float(final_sr.n_unknown) / float(work_grid.size)
    n_rate_pct = n_rate_raw * 100.0
    passed_numeric = (
        n_rate_raw <= 1e-12
        and bool(final_sr.solvable) is True
        and float(final_sr.coverage) >= 0.9999
        and sizing.get("gate_aspect_ratio_within_tolerance", True) is not False
    )
    findings = classify_visual_findings(
        n_rate_raw,
        float(final_sr.coverage),
        final_q["hi_err"],
        final_q["true_bg_err"],
        final_q["mine_density"],
    )
    gate_status, passed_visual = visual_gate_status(findings)
    promoted = bool(passed_numeric and passed_visual)

    run_id = uuid.uuid4().hex
    title = (
        f"Mine-Streaker - {board_w}x{board_h} ({work_grid.size:,} cells)  "
        f"[solvable={final_sr.solvable}  coverage={final_sr.coverage:.4f}]"
    )
    metrics_path = out_dir / f"metrics_{board_w}x{board_h}.json"
    grid_path = out_dir / f"grid_{board_w}x{board_h}.npy"
    visual_path = out_dir / f"visual_{board_w}x{board_h}.png"
    move_log_path = out_dir / "repair_move_log.jsonl"

    render_visual_report(target_eval, work_grid, final_sr, title, str(visual_path), dpi=150)
    atomic_save_npy(work_grid, grid_path)

    baseline_grid_sha = file_sha256(baseline_grid_path)
    baseline_metrics_sha = file_sha256(baseline_metrics_path)
    command_signature = compute_command_signature(args, baseline_grid_sha, baseline_metrics_sha)
    git_meta = get_git_metadata(Path(__file__).resolve().parent)

    metrics = {
        "run_id": run_id,
        "run_tag": args.run_tag,
        "source_profile": "global46",
        "repair_variant": variant,
        "board": f"{board_w}x{board_h}",
        "cells": int(work_grid.size),
        "seed": int(args.seed),
        "source_width": int(sizing["source_width"]),
        "source_height": int(sizing["source_height"]),
        "source_ratio": float(sizing["source_ratio"]),
        "board_width": int(board_w),
        "board_height": int(board_h),
        "board_ratio": float(sizing["board_ratio"]),
        "aspect_ratio_relative_error": float(sizing["aspect_ratio_relative_error"]),
        "aspect_ratio_tolerance": float(sizing["aspect_ratio_tolerance"]),
        "gate_aspect_ratio_within_0_5pct": bool(sizing["gate_aspect_ratio_within_tolerance"]),
        "baseline_grid_path": str(baseline_grid_path),
        "baseline_metrics_path": str(baseline_metrics_path),
        "baseline_grid_sha256": baseline_grid_sha,
        "baseline_metrics_sha256": baseline_metrics_sha,
        "baseline_n_unknown": int(parse_int(baseline_metrics.get("n_unknown")) or baseline_sr.n_unknown),
        "baseline_coverage": float(parse_float(baseline_metrics.get("coverage")) or baseline_sr.coverage),
        "baseline_solvable": bool(parse_bool(baseline_metrics.get("solvable")) if parse_bool(baseline_metrics.get("solvable")) is not None else baseline_sr.solvable),
        "final_n_unknown": int(final_sr.n_unknown),
        "final_coverage": float(final_sr.coverage),
        "final_solvable": bool(final_sr.solvable),
        "n_unknown": int(final_sr.n_unknown),
        "coverage": float(final_sr.coverage),
        "solvable": bool(final_sr.solvable),
        "n_rate_raw": float(n_rate_raw),
        "n_rate_pct": float(n_rate_pct),
        "passed_numeric": bool(passed_numeric),
        "passed_visual": bool(passed_visual),
        "promoted": bool(promoted),
        "phase2_repair_applied": bool(phase2_applied),
        "last100_repair_applied": bool(last100_applied),
        "n_phase2_fixes": int(n_phase2_fixes),
        "n_last100_fixes": int(n_last100_fixes),
        "variant_stop_reason": variant_stop_reason,
        "mean_abs_error": float(final_q["mean_abs_error"]),
        "true_bg_err": float(final_q["true_bg_err"]),
        "hi_err": float(final_q["hi_err"]),
        "mine_density": float(final_q["mine_density"]),
        "corridor_pct": float(corridor_pct),
        "background_leakage_gate": {
            "required": bool(args.background_leakage_gate),
            "status": gate_status,
            "reviewer_notes": "heuristic automated review",
        },
        "visual_findings": findings,
        "repair_move_log_path": str(move_log_path),
        "total_time_s": float(time.perf_counter() - t0),
        "runtime_budget_hit": False,
        "pw_knee": float(args.pw_knee),
        "pw_t_max": float(args.pw_t_max),
        "contrast_factor": float(args.contrast_factor),
        "hi_boost": float(args.hi_boost),
        "phase2_budget_s": float(args.phase2_budget_s),
        "last100_budget_s": float(args.last100_budget_s),
        "allow_noncanonical": bool(args.allow_noncanonical),
        "command_signature": command_signature,
        "provenance": {
            "started_at_utc": utc_now_iso(),
            "image_path": str(image_path),
            "image_sha256": file_sha256(image_path),
            "python_version": sys.version.split()[0],
            "python_bits": 64 if sys.maxsize > 2**32 else 32,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "git_commit": git_meta.get("git_commit"),
            "git_dirty": git_meta.get("git_dirty"),
        },
        "artifacts": {
            "visual_path": str(visual_path),
            "metrics_path": str(metrics_path),
            "grid_path": str(grid_path),
            "move_log_path": str(move_log_path),
        },
    }

    atomic_save_json(metrics, metrics_path)
    with move_log_path.open("w", encoding="utf-8") as f:
        for row in move_log:
            f.write(json.dumps(row, sort_keys=True) + "\n")

    ledger_row = {
        "run_id": run_id,
        "run_tag": args.run_tag,
        "repair_variant": variant,
        "seed": int(args.seed),
        "board": metrics["board"],
        "cells": metrics["cells"],
        "baseline_n_unknown": metrics["baseline_n_unknown"],
        "final_n_unknown": metrics["final_n_unknown"],
        "n_rate_raw": metrics["n_rate_raw"],
        "coverage": metrics["final_coverage"],
        "solvable": metrics["final_solvable"],
        "passed_numeric": metrics["passed_numeric"],
        "passed_visual": metrics["passed_visual"],
        "promoted": metrics["promoted"],
        "n_phase2_fixes": metrics["n_phase2_fixes"],
        "n_last100_fixes": metrics["n_last100_fixes"],
        "total_time_s": metrics["total_time_s"],
        "mean_abs_error": metrics["mean_abs_error"],
        "true_bg_err": metrics["true_bg_err"],
        "hi_err": metrics["hi_err"],
        "background_leakage_gate_status": gate_status,
        "metrics_path": str(metrics_path),
        "visual_path": str(visual_path),
        "grid_path": str(grid_path),
        "move_log_path": str(move_log_path),
        "command_signature": command_signature,
    }
    if args.ledger_jsonl:
        append_jsonl_record(Path(args.ledger_jsonl), ledger_row)
    if args.ledger_csv:
        append_csv_row(Path(args.ledger_csv), ledger_row)

    print(f"Saved visual:  {visual_path}", flush=True)
    print(f"Saved metrics: {metrics_path}", flush=True)
    print(f"Saved grid:    {grid_path}", flush=True)
    print(f"Saved move log:{move_log_path}", flush=True)
    print(
        f"Summary: baseline_n_unknown={metrics['baseline_n_unknown']} "
        f"final_n_unknown={metrics['final_n_unknown']} "
        f"coverage={metrics['final_coverage']:.6f} "
        f"promoted={metrics['promoted']}",
        flush=True,
    )
    return metrics


def build_parser():
    p = argparse.ArgumentParser(description="Repair-only runner from a saved baseline mine grid.")
    p.add_argument("--image", required=True)
    p.add_argument("--baseline-grid", required=True)
    p.add_argument("--baseline-metrics", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--run-tag", required=True)
    p.add_argument("--board-w", type=int, required=True)
    p.add_argument("--seed", type=int, required=True)
    p.add_argument(
        "--repair-variant",
        required=True,
        choices=[
            "baseline_recheck",
            "phase2_extended_only",
            "last100_only",
            "phase2_extended_then_last100",
        ],
    )
    p.add_argument("--phase2-budget-s", type=float, required=True)
    p.add_argument("--last100-budget-s", type=float, required=True)
    p.add_argument("--pw-knee", type=float, required=True)
    p.add_argument("--pw-t-max", type=float, required=True)
    p.add_argument("--contrast-factor", type=float, required=True)
    p.add_argument("--hi-boost", type=float, required=True)
    p.add_argument("--background-leakage-gate", action="store_true")
    p.add_argument("--allow-noncanonical", action="store_true")
    p.add_argument("--ledger-jsonl", default="")
    p.add_argument("--ledger-csv", default="")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    ensure_solver_warmed()
    run_once(args)


if __name__ == "__main__":
    main()
