# research/stall-breakers — Experiment Log

**Branch base:** `perf/board-gen-10x` (commit `4fc09fa`)
**PR target on success:** `perf/board-gen-10x`

## Problem Statement

The SA + repair pipeline leaves `n_unknown > 0` on hard boards (research/600).
The SA optimizes only for visual fidelity — it does not maintain solvability —
so it exits with hundreds of sealed unknown clusters (groups of unknowns completely
surrounded by mines, unreachable by the CSP solver). `fast_seal_repair` fixes these
greedily but exhausts its 3–5 s budget without reaching `n_unknown=0`.

## Acceptance Gate (for promotion to `perf/board-gen-10x`)

All 4 scenarios must pass:

| Scenario       | Requirement               |
|----------------|---------------------------|
| research/600   | `n_unknown = 0` (primary target) |
| easy/200       | `n_unknown = 0` (no regression)  |
| normal/600     | `n_unknown = 0` (no regression)  |
| research/200   | `n_unknown = 0` (no regression)  |
| All            | `mean_abs_error ≤ baseline + 0.005` |

## Experiments

### C — SEAL_STR / SEAL_THR Grid Search  *(run first)*

`python -m research.exp_c_seal_param_sweep`

Sweeps `sealing_strength` ∈ {10, 20, 30, 50, 80, 120} and
`density_threshold` ∈ {0.4, 0.5, 0.6, 0.7, 0.8} (30 combinations).
Primary metric: `n_unknown_post_sa`. If SEAL_STR≈40–80 drops
`n_unknown_post_sa` to near-0 without MAE regression, the fix is trivial.

### D — Constraint-Score Mine Selector  *(run second)*

`python -m research.exp_d_smarter_fast_seal`

Replaces the "remove lowest-T mine" heuristic with a constraint-score
selector that estimates which mine removal unlocks the most solver
deductions. Strategies: `lowest_T` (baseline), `constraint_score`, `combined`.

### B — Mini-SA Reannealing  *(run third)*

`python -m research.exp_b_mini_sa_reannealing`

Runs a short SA (20K–100K iters) confined to each sealed cluster's ring
neighborhood. Unlike greedy removal, the mini-SA can rearrange mines within
the ring — adding and removing — to find a non-sealed configuration.

### F — Post-SA Local Reannealing (amplified weights)  *(run fourth)*

`python -m research.exp_f_post_sa_local_reanneal`

Same as Exp B but uses `compute_sealing_prevention_weights` with
`sealing_strength` amplified by 50–200× in the ring. The mini-SA is
explicitly penalized for maintaining sealed topology.

## Compare Results

```bash
python -m research.harness.benchmark --compare \
    exp_c_seal_param_sweep \
    exp_d_smarter_fast_seal \
    exp_b_mini_sa_reannealing \
    exp_f_post_sa_local_reanneal
```

## Results Log

Results are written to `research/results/<exp_name>.jsonl` (gitignored).

---

*Update this file with findings as experiments run.*
