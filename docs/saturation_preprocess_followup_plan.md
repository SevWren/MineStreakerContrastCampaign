# Saturation Preprocess Follow-Up Plan

This plan defines one full SA3x-only saturation campaign with fixed controls, fixed seeds, strict promotion gates, and a mandatory visual approval checkpoint before any winner is promoted.

## Interface Impact
- Public API/interface changes: none (documentation + workflow only).

## Fixed Campaign Controls
- SA mode: `--method-test-sa-3x` on every run.
- Runtime target: `total_time_s <= 50` for compliant runs.
- Seed set: `11,22,33,44,55`.
- Control seeds: `11,22`.
- Control images: `assets/input_source_image.png`, `assets/input_source_image_research.png`.
- Stress widths: `362`, `428`.
- Baseline comparator summaries (reference only):
  - [`results/contrast_preprocess_study_sa3x/contrast_study_summary.md`](../results/contrast_preprocess_study_sa3x/contrast_study_summary.md)
  - [`results/contrast_preprocess_study_20260421_100952/contrast_study_summary.md`](../results/contrast_preprocess_study_20260421_100952/contrast_study_summary.md)

## Full Phase Matrix (Exact Commands)
The exact execution blocks are in [`docs/saturation_run_matrix.md`](saturation_run_matrix.md).
Run phases in order and keep the same root campaign folder for all artifacts.

### Phase Index
1. Phase 0: setup + campaign root variables.
2. Phase 1A: fine contrast sweep (`irisd3`, seed 42).
3. Phase 1B: low-end floor sweep (`irisd3`, seed 42).
4. Phase 1C: top-4 contrast selection by `(n_unknown, hi_err, total_time_s)`.
5. Phase 2A: multi-seed repeats on `irisd3` for top contrasts; parallel unit is `(contrast, seed)`.
6. Phase 2B: control reruns on both control images; parallel unit is `(control image, contrast, seed)`.
7. Phase 3A: piecewise screen for top-2 contrasts; parallel unit is `(contrast, pw_knee, pw_t_max)`.
8. Phase 3B: pick top-4 piecewise combos, then repeat in parallel by `(piecewise row, seed)`.
9. Phase 4: adaptive local-cap ablation at best contrast + piecewise; parallel unit is `(local_cap_mode, seed)`.
10. Phase 5: control reruns for Phase 4 winning mode; parallel unit is `(control image, seed)`.
11. Phase 6: stress reruns at widths `362` and `428`; parallel unit is `(width, seed)`.
12. Phase 7: mandatory visual approval gate (`winner_visual_review.csv`).

## Parallel Execution Policy For Phases 2A-6
- Default launcher: PowerShell `Start-Job` batches with a bounded worker pool.
- Default concurrency: `MAX_PARALLEL = 4`; lower it if runtime variance or memory pressure appears.
- Ledger rule: each parallel worker writes to phase-local ledger files under `results/<campaign_root>/worker_ledgers/<phase>/`; merge ledgers only after all jobs in that phase have completed successfully.
- Output isolation rule: every shard must use a unique `--out-dir` and `--run-tag` derived from its full parameter tuple.
- Barrier rule: do not run a selection step until every shard from its source phase has completed and its `metrics_*.json` exists.
- Failure rule: if any shard fails, rerun only the missing or failed shard with the same `--out-dir`, `--run-tag`, seed, and parameters before continuing.
- Ordering rule: preserve phase dependencies even when shards run in parallel: Phase 1C after 1A/1B, Phase 3B selection after 3A, Phase 4 after 3B repeats, and final promotion after Phases 5/6 and visual review.
- Phase 5 and Phase 6 may be launched as separate parallel batches after the Phase 4 winner configuration is fixed; final promotion waits for both batches.
- Low-contention diagnostic reruns should cap nested worker pressure with `--phase1-max-workers 2` and per-process thread caps (`NUMBA_NUM_THREADS=2`, `OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`, `OPENBLAS_NUM_THREADS=2`).
- Runtime interpretation must distinguish `solve_budget_hit` from `total_runtime_budget_hit`; legacy `runtime_budget_hit` remains total-clock based until downstream docs and gates are intentionally migrated.

## Promotion Rules (Combined Metric + Visual)
- Phase 1 -> Phase 2: top 4 contrasts by `n_unknown`, tie-break `hi_err`, then `total_time_s`.
- Phase 2 -> Phase 3: top 2 by median `n_unknown` across 5 seeds; reject if median runtime > 50s.
- Phase 3 -> Phase 4: top 1 piecewise config by median `n_unknown`; require `hi_err` not worse than +10% vs best Phase 2.
- Phase 4 winner: best median `n_unknown`; ties by `hi_err`, then runtime.
- Final winner requires all of:
  - metric win,
  - Phase 5 control pass,
  - Phase 6 stress pass,
  - visual approval (`user_approved=yes`) in `winner_visual_review.csv`.
- If metric winner is visually rejected:
  - promote next-ranked candidate,
  - rerun any missing controls/stress checks,
  - repeat until approved winner or `no accepted winner`.

## Mandatory Visual-Approval Rule
- Every metric winner candidate must be reviewed by you before promotion.
- Visual acceptance criteria are defined in [`docs/saturation_visual_acceptance_checklist.md`](saturation_visual_acceptance_checklist.md).
- Review ledger file must exist at `results/<campaign_root>/winner_visual_review.csv`.
- Template header file is provided at `results/saturation_matrix_TEMPLATE/winner_visual_review.csv`.
- Candidate may be promoted only when ledger row has `user_approved=yes`.

## Reporting and Refresh Gate
Required campaign outputs:
- `matrix_runs.csv`
- `matrix_summary.json`
- `matrix_summary.md`
- `winner_visual_review.csv`

`matrix_runs.csv` required columns:
- `phase,image,seed,board_w,contrast_factor,pw_knee,pw_t_max,local_cap_mode,n_unknown,coverage,solvable,hi_err,mean_abs_error,total_time_s,runtime_budget_hit,harm_signal_t_ge_7_pct,sa_budget_multiplier`

Recommended parallel audit columns for generated summaries:
- `parallel_batch_id,shard_id,worker_ledger_jsonl,worker_ledger_csv`

Recommended runtime accounting columns for new metrics:
- `solve_budget_hit,total_runtime_budget_hit,post_solve_overhead_s`

## Refresh Eligibility
`docs/saturation_preprocess_followup_plan.md` may be refreshed only from new matrix outputs that satisfy all gates:
- SA3x proof:
  - `sa_budget_multiplier == 3.0` in run summary rows, and
  - `runtime_calibration.sa_budget_multiplier == 3.0` in run metrics JSON.
- Complete artifacts per candidate:
  - `metrics_*.json`
  - `visual_*.png`
  - campaign ledger row or phase-local worker ledger row.
- Candidate source:
  - selected from 5-seed `irisd3` repeats (Phases 2/3/4).
- Control gate pass (Phase 5):
  - both control images must have `solvable=True` and `n_unknown=0`.
- Stress gate pass (Phase 6):
  - both widths `362` and `428` validated.
- Visual gate pass:
  - `winner_visual_review.csv` row has `parallel_batch_id`, `shard_id`, and `user_approved=yes` for selected winner.

Do not treat SA1x-only new runs as refresh-eligible evidence.

## Baseline Usage Policy
- Use the two existing contrast summaries only as baseline comparators.
- Do not overwrite or reinterpret baseline claims from partial campaigns.
- Update follow-up conclusions only from eligible matrix campaigns that pass all gates above.

## Test Cases and Scenarios
- High-contrast settings reduce unknowns but degrade fidelity.
- Piecewise compression outperforms pure contrast on tradeoff.
- Adaptive local cap materially helps versus no-local-cap.
- Candidate overfits width 300 but fails 362/428.
- Candidate passes metrics but fails visual acceptance.
- Candidate passes visuals but fails controls.
- No candidate passes all gates.

## Assumptions and Defaults
- Seed set fixed: `11,22,33,44,55`.
- Stress widths fixed: `362` and `428`.
- Refresh policy fixed: `SA3x + controls + stress + visual approval`.
- Runtime target remains `<= 50s`; over-50s runs are non-compliant unless explicitly tagged exploratory.
- Reviewer is you; visual approval is authoritative.
