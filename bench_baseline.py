#!/usr/bin/env python3
"""
bench_baseline.py — Baseline benchmark harness for run_iter9.py.

Runs all 12 (board_w × image) scenarios 5 times each as separate subprocess
calls.  Reads total_time_s from each run's metrics JSON.

Usage:
  python bench_baseline.py [--runs N] [--out results_dir] [--tag TAG]

Outputs:
  baseline_timings.json  — all raw timing data
  baseline_table.md      — human-readable table
  bench_reference_quality.json — quality reference for regression gate
"""
from __future__ import annotations
import argparse
import glob
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent

BOARD_WIDTHS = [200, 300, 450, 600]

IMAGES = [
    ("input_source_image",    "assets/input_source_image.png",          False),
    ("research",              "assets/input_source_image_research.png",  True),
    ("line_art_a1",           "assets/line_art_a1.png",                  True),
]

DEFAULT_RUNS = 5
DEFAULT_SEED = 42


def run_one(board_w: int, image_path: str, allow_noncanonical: bool,
            out_dir: str, seed: int, run_idx: int) -> dict:
    """Run the pipeline once; return timing + quality metrics dict."""
    cmd = [
        sys.executable, "run_iter9.py",
        "--board-w", str(board_w),
        "--image", image_path,
        "--out-dir", out_dir,
        "--seed", str(seed),
    ]
    if allow_noncanonical:
        cmd.append("--allow-noncanonical")

    t_start = time.perf_counter()
    result = subprocess.run(
        cmd,
        cwd=str(REPO),
        capture_output=True,
        text=True,
    )
    wall_subprocess = time.perf_counter() - t_start

    if result.returncode != 0:
        print(f"  FAILED (board_w={board_w}, img={image_path}, run={run_idx}):")
        print(result.stderr[-2000:])
        return {"error": result.stderr[-500:], "total_time_s": None}

    # Find the metrics JSON
    pattern = os.path.join(out_dir, "metrics_iter9_*.json")
    matches = glob.glob(pattern)
    if not matches:
        return {"error": "metrics JSON not found", "total_time_s": None}

    with open(matches[0]) as f:
        metrics = json.load(f)

    return {
        "total_time_s": float(metrics["total_time_s"]),
        "subprocess_wall_s": float(wall_subprocess),
        "n_unknown": int(metrics.get("n_unknown", -1)),
        "solvable": bool(metrics.get("solvable", False)),
        "coverage": float(metrics.get("coverage", 0.0)),
        "mean_abs_error": float(metrics.get("mean_abs_error", 0.0)),
        "board": str(metrics.get("board", "")),
        "runtime_phase_timing_s": dict(metrics.get("runtime_phase_timing_s", {})),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS)
    parser.add_argument("--out", default="/tmp/bench_runs")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--tag", default="baseline")
    args = parser.parse_args()

    n_runs = args.runs
    base_out = args.out
    seed = args.seed
    tag = args.tag

    print(f"\n{'='*60}")
    print(f"Benchmark harness — {tag}")
    print(f"  {len(BOARD_WIDTHS)} board widths × {len(IMAGES)} images × {n_runs} runs")
    print(f"  = {len(BOARD_WIDTHS) * len(IMAGES) * n_runs} total pipeline executions")
    print(f"{'='*60}\n")

    all_results: list[dict] = []
    quality_refs: list[dict] = []
    table_rows: list[dict] = []
    phase_rows: list[dict] = []

    scenario_count = 0
    total_scenarios = len(BOARD_WIDTHS) * len(IMAGES)

    for image_name, image_path, allow_nc in IMAGES:
        for board_w in BOARD_WIDTHS:
            scenario_count += 1
            print(f"[{scenario_count}/{total_scenarios}] board_w={board_w:4d}  image={image_name}")

            run_times: list[float] = []
            last_quality: dict = {}
            last_phases: dict = {}

            for run_idx in range(1, n_runs + 1):
                out_dir = os.path.join(
                    base_out,
                    f"{tag}_{image_name}_w{board_w}_run{run_idx}"
                )
                os.makedirs(out_dir, exist_ok=True)

                r = run_one(board_w, image_path, allow_nc, out_dir, seed, run_idx)

                t = r.get("total_time_s")
                if t is None:
                    print(f"  run {run_idx}: FAILED — {r.get('error','?')[:80]}")
                    run_times.append(float("nan"))
                else:
                    run_times.append(t)
                    last_quality = {
                        "n_unknown": r["n_unknown"],
                        "solvable": r["solvable"],
                        "coverage": r["coverage"],
                        "mean_abs_error": r["mean_abs_error"],
                    }
                    last_phases = r.get("runtime_phase_timing_s", {})
                    print(f"  run {run_idx}: {t:.3f}s  n_unknown={r['n_unknown']}  "
                          f"solvable={r['solvable']}  board={r.get('board','?')}")

            valid = [t for t in run_times if not (t != t)]  # remove NaN
            avg = sum(valid) / len(valid) if valid else float("nan")

            row = {
                "boardw": board_w,
                "image": image_name,
                "run1": run_times[0] if len(run_times) > 0 else None,
                "run2": run_times[1] if len(run_times) > 1 else None,
                "run3": run_times[2] if len(run_times) > 2 else None,
                "run4": run_times[3] if len(run_times) > 3 else None,
                "run5": run_times[4] if len(run_times) > 4 else None,
                "avg_s": avg,
            }
            table_rows.append(row)

            quality_ref = {
                "boardw": board_w,
                "image": image_name,
                "image_path": image_path,
                "allow_noncanonical": allow_nc,
                **last_quality,
            }
            quality_refs.append(quality_ref)

            phase_row = {"boardw": board_w, "image": image_name, **last_phases}
            phase_rows.append(phase_row)

            all_results.append({
                "boardw": board_w,
                "image": image_name,
                "run_times": run_times,
                "avg_s": avg,
                "quality": last_quality,
                "phases": last_phases,
            })

            print(f"  avg: {avg:.3f}s\n")

    # Save raw data
    out_path = REPO / f"{tag}_timings.json"
    with open(out_path, "w") as f:
        json.dump({"tag": tag, "runs": n_runs, "scenarios": all_results}, f, indent=2)
    print(f"Saved raw timings: {out_path}")

    # Save quality reference (for regression gate)
    qref_path = REPO / "bench_reference_quality.json"
    with open(qref_path, "w") as f:
        json.dump(quality_refs, f, indent=2)
    print(f"Saved quality reference: {qref_path}")

    # Save phase timing breakdown
    phase_path = REPO / f"{tag}_phase_timings.json"
    with open(phase_path, "w") as f:
        json.dump(phase_rows, f, indent=2)
    print(f"Saved phase timings: {phase_path}")

    # Print BASELINE TABLE
    print(f"\n{'='*60}")
    print(f"{'='*60}")
    print(f"BASELINE TABLE — {tag}")
    print(f"{'='*60}")
    header = f"{'boardw':>6} | {'image':<25} | {'run1':>7} | {'run2':>7} | {'run3':>7} | {'run4':>7} | {'run5':>7} | {'avg_s':>7}"
    print(header)
    print("-" * len(header))
    for row in table_rows:
        def fmt(v):
            return f"{v:.3f}" if v is not None and v == v else "  N/A "
        print(
            f"{row['boardw']:>6} | {row['image']:<25} | "
            f"{fmt(row['run1']):>7} | {fmt(row['run2']):>7} | "
            f"{fmt(row['run3']):>7} | {fmt(row['run4']):>7} | "
            f"{fmt(row['run5']):>7} | {fmt(row['avg_s']):>7}"
        )
    print(f"{'='*60}\n")

    # Print phase timing breakdown
    print("PHASE TIMING BREAKDOWN (from last run of each scenario):")
    phases_of_interest = [
        "warmup", "image_load_and_preprocess", "corridor_build",
        "coarse_sa", "fine_sa", "refine_sa_total",
        "fast_seal_repair", "phase1_repair", "late_stage_routing", "total"
    ]
    ph_header = f"{'boardw':>6} | {'image':<20} | " + " | ".join(f"{p[:12]:>12}" for p in phases_of_interest)
    print(ph_header)
    print("-" * len(ph_header))
    for row in phase_rows:
        vals = " | ".join(f"{row.get(p, 0.0):>12.4f}" for p in phases_of_interest)
        print(f"{row['boardw']:>6} | {row['image']:<20} | {vals}")
    print()


if __name__ == "__main__":
    main()
