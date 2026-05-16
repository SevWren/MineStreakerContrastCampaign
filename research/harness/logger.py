"""
research/harness/logger.py — Append-only JSONL result logger.

Each experiment appends one JSON line per run to:
    research/results/<experiment_name>.jsonl

This file is excluded from git (see .gitignore). Use load_results() /
summarize() to inspect accumulated data across runs.
"""

import json
import os
import subprocess
import time
from pathlib import Path

_RESULTS_DIR = Path(__file__).parent.parent / "results"


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        return "unknown"


def log_result(
    experiment_name: str,
    scenario_label: str,
    params: dict,
    result: dict,
) -> None:
    """
    Append one JSON line to research/results/<experiment_name>.jsonl.

    result should contain at minimum:
        n_unknown_post_sa, n_unknown_final, solvable,
        mean_abs_error, repair_wall_s
    """
    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _RESULTS_DIR / f"{experiment_name}.jsonl"

    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "experiment_name": experiment_name,
        "scenario_label": scenario_label,
        "params": params,
        "git_commit": _git_commit(),
        **result,
    }

    with out_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def load_results(experiment_name: str) -> list[dict]:
    """Load all logged results for an experiment."""
    path = _RESULTS_DIR / f"{experiment_name}.jsonl"
    if not path.exists():
        return []
    records = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records


def summarize(experiment_name: str) -> None:
    """Print a human-readable summary table for an experiment."""
    records = load_results(experiment_name)
    if not records:
        print(f"No results found for '{experiment_name}'")
        return

    print(f"\n{'='*80}")
    print(f"Experiment: {experiment_name}  ({len(records)} runs)")
    print(f"{'='*80}")
    print(f"{'scenario':20} {'n_unk_sa':>8} {'n_unk_fin':>9} {'solvable':>8} "
          f"{'MAE':>7} {'repair_s':>9}  params")
    print("-" * 80)
    for r in records:
        p_str = " ".join(f"{k}={v}" for k, v in r.get("params", {}).items())
        print(
            f"{r.get('scenario_label','?'):20} "
            f"{r.get('n_unknown_post_sa', '?'):>8} "
            f"{r.get('n_unknown_final', '?'):>9} "
            f"{str(r.get('solvable','?')):>8} "
            f"{r.get('mean_abs_error', 0):>7.4f} "
            f"{r.get('repair_wall_s', 0):>9.3f}  "
            f"{p_str}"
        )
