# Untested Methods Validation Protocol (3x SA Budget)

## Scope
- Methods in scope:
  - Exact SAT/ILP on sealed components
  - Contradiction-driven lookahead solver
  - Min-cost flow / graph-cut frontier consistency
  - Continuous relaxation + projected optimization
  - Learned preprocess prior (edge-confidence target prior)

## Fixed Test Controls
- Use identical test set for all methods and baseline:
  - `irisd3.png`
  - `assets/input_source_image.png`
  - `assets/input_source_image_research.png`
  - `assets/input_source_image_research_irl1.png`
- Fixed run settings unless explicitly stated:
  - `--board-w 300`
  - `--iters-multiplier 0.25`
  - `--max-runtime-s 50`
  - `--phase1-budget-s 8`
  - `--phase2-budget-s 20`
  - `--adaptive-local-cap --adaptive-local-cap-ladder 4.6`
  - `--allow-noncanonical`
- Method-test SA budget policy:
  - Always run with `--method-test-sa-3x` (or `--sa-budget-multiplier 3.0`)
  - Verify in metrics: `runtime_calibration.sa_budget_multiplier == 3.0`

## Required Evidence Per Method
- Functional correctness:
  - No regressions in board validity checks.
  - Deterministic replay for fixed seed.
- KPI outputs (from `metrics_*.json`):
  - `n_unknown`, `coverage`, `solvable`, `mine_accuracy`
  - `hi_err`, `mean_abs_error`, `total_time_s`
  - `phase_timing_s.*`, `dominant_phase`, hotspot candidates (profiled subset)
- Acceptance thresholds against current baseline cohort:
  - Primary: lower `n_unknown` without dropping `coverage`
  - Secondary: no unacceptable `hi_err` regression
  - Runtime: document both with/without profile

## Test Matrix
- Phase A (smoke): 1 seed x 4 images x baseline + method variant
- Phase B (robustness): 5 seeds x 4 images
- Phase C (stress): board widths `300, 362, 428` for top 2 methods
- Phase D (ablation): isolate each major subsystem of the method

## Reporting Requirements
- Store all runs in dedicated result roots:
  - `results/method_test_<method_name>_<timestamp>/...`
- Produce:
  - `method_runs.csv` (flat run table)
  - `method_summary.json` (aggregates + significance checks)
  - `method_summary.md` (human-readable conclusions)
- Evidence-only rule:
  - Any causal claim must reference measured deltas from the run table.
