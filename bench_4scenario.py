#!/usr/bin/env python3
"""
4-scenario benchmark (5 runs each).
Uses metrics JSON for timing — matches baseline measurement methodology.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

BASELINES = {
    (200, "line_art_a1"): 0.914,
    (600, "input_source_image"): 4.186,
    (200, "input_source_image_research"): 1.085,
    (600, "input_source_image_research"): 8.138,
}

SCENARIOS = [
    (200, "assets/line_art_a1.png"),
    (600, "assets/input_source_image.png"),
    (200, "assets/input_source_image_research.png"),
    (600, "assets/input_source_image_research.png"),
]
N_RUNS = 5
SEED = 42
OUT_BASE = Path("results/bench_4s")


def run_one(boardw, image_path, run_idx):
    out_dir = OUT_BASE / f"bw{boardw}_{Path(image_path).stem}_r{run_idx}"
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "run_iter9.py",
           "--image", image_path, "--board-w", str(boardw),
           "--seed", str(SEED), "--out-dir", str(out_dir), "--allow-noncanonical"]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"    FAILED: {result.stderr[:300]}")
        return None

    # Find metrics JSON
    metrics_files = list(out_dir.glob("metrics_iter9_*.json"))
    if not metrics_files:
        print(f"    ERROR: no metrics file found")
        return None

    with open(metrics_files[0]) as f:
        m = json.load(f)
    t = m.get("total_time_s")
    n_unk = m.get("n_unknown")
    cov = m.get("coverage")
    print(f"    run {run_idx+1}: {t:.3f}s  n_unknown={n_unk}  cov={cov:.5f}")
    return {"time": t, "n_unknown": n_unk, "coverage": cov,
            "solvable": m.get("solvable"), "mae": m.get("mean_abs_error")}


def main():
    OUT_BASE.mkdir(parents=True, exist_ok=True)
    print("=" * 72)
    print("4-SCENARIO BENCHMARK (5 runs each)")
    print("=" * 72)

    rows = []
    for boardw, image_path in SCENARIOS:
        stem = Path(image_path).stem
        baseline = BASELINES[(boardw, stem)]
        print(f"\nScenario: boardw={boardw}  image={stem}")
        print(f"  Baseline: {baseline:.3f}s  |  10× target: {baseline/10:.3f}s")

        times = []
        for r in range(N_RUNS):
            res = run_one(boardw, image_path, r)
            if res:
                times.append(res["time"])
                rows.append(dict(boardw=boardw, image=stem, run=r, **res))
        if len(times) < N_RUNS:
            print(f"  INCOMPLETE: {len(times)}/{N_RUNS} runs")
            continue
        avg = sum(times) / len(times)
        speedup = baseline / avg
        print(f"  avg={avg:.3f}s  speedup={speedup:.2f}×  "
              f"({'PASS ✓' if speedup >= 10.0 else f'need {(avg / (baseline / 10.0)):.2f}× more'})")

    # Summary table
    print("\n" + "=" * 72)
    print("SUMMARY TABLE")
    print("=" * 72)
    print(f"{'boardw':>7} | {'image':20} | {'run1':>6} | {'run2':>6} | {'run3':>6} | {'run4':>6} | {'run5':>6} | {'avg_s':>6} | {'speedup':>8}")
    print("-" * 100)
    for boardw, image_path in SCENARIOS:
        stem = Path(image_path).stem
        baseline = BASELINES[(boardw, stem)]
        scenario_rows = [r for r in rows if r["boardw"] == boardw and r["image"] == stem]
        if len(scenario_rows) < N_RUNS:
            print(f"  INCOMPLETE")
            continue
        times = [r["time"] for r in scenario_rows]
        avg = sum(times) / len(times)
        speedup = baseline / avg
        tstr = " | ".join(f"{t:6.3f}" for t in times)
        print(f"{boardw:>7} | {stem:20} | {tstr} | {avg:6.3f} | {speedup:7.2f}×")

    with open(OUT_BASE / "results.json", "w") as f:
        json.dump(rows, f, indent=2)
    print(f"\nFull results saved to {OUT_BASE / 'results.json'}")


if __name__ == "__main__":
    main()
