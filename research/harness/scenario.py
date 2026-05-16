"""
research/harness/scenario.py — 4-scenario verification matrix.

These are the canonical scenarios used across all research experiments.
HARD_SCENARIO (research/600) is the primary stall target.
The other three act as regression guards.

Baseline timings (perf/board-gen-10x, 5-run averages):
  easy/200   : 0.849s  (n_unknown=0)
  normal/600 : 3.010s  (n_unknown=0)
  research/200: 0.971s (n_unknown=0)
  research/600: 4.895s (n_unknown=0 — stalls intermittently on some seeds/boards)

Baseline MAE values are recorded per-run in research/results/baseline.jsonl.
"""

SCENARIOS = [
    {
        "board_w": 200,
        "image": "assets/line_art_a1.png",
        "label": "easy/200",
    },
    {
        "board_w": 600,
        "image": "assets/input_source_image.png",
        "label": "normal/600",
    },
    {
        "board_w": 200,
        "image": "assets/input_source_image_research.png",
        "label": "research/200",
    },
    {
        "board_w": 600,
        "image": "assets/input_source_image_research.png",
        "label": "research/600",
    },
]

# Primary stall target — this is the scenario that intermittently fails
HARD_SCENARIO = SCENARIOS[3]

# Default seed for deterministic runs
SEED = 42

# Regression guard: max allowed MAE increase vs baseline for any scenario
MAE_TOLERANCE = 0.005

# Acceptance gate: all 4 scenarios must hit n_unknown=0
def check_acceptance(results: list[dict], baseline_maes: dict | None = None) -> dict:
    """
    Check whether a set of experiment results passes the acceptance gate.

    Args:
        results: list of result dicts, one per scenario. Each must have:
                 'label', 'n_unknown_final', 'solvable', 'mean_abs_error'
        baseline_maes: optional dict mapping label -> baseline MAE value

    Returns:
        dict with 'passed' (bool), 'failures' (list of strings describing failures)
    """
    failures = []
    by_label = {r["label"]: r for r in results if "label" in r}

    for s in SCENARIOS:
        label = s["label"]
        if label not in by_label:
            failures.append(f"{label}: no result recorded")
            continue
        r = by_label[label]
        if r.get("n_unknown_final", -1) != 0:
            failures.append(f"{label}: n_unknown={r.get('n_unknown_final')} (need 0)")
        if baseline_maes and label in baseline_maes:
            delta = r.get("mean_abs_error", 0) - baseline_maes[label]
            if delta > MAE_TOLERANCE:
                failures.append(f"{label}: MAE increased by {delta:.4f} (limit {MAE_TOLERANCE})")

    return {"passed": len(failures) == 0, "failures": failures}
