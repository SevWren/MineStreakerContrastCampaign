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

## Measured Results (seed=42, research/600 primary target)

### Exp C — SEAL_STR sweep (SEAL_THR=0.6)

| SEAL_STR | n_unk_post_sa | n_unk_final | MAE    | passes |
|----------|---------------|-------------|--------|--------|
| 20.0     | 5795          | 0           | 0.4033 | 62     |
| 50.0     | 5533          | 0           | 0.4032 | 58     |
| 80.0     | 5366          | 0           | 0.4031 | 63     |
| 120.0    | 5443          | 0           | 0.4027 | 58     |

**Finding:** Higher SEAL_STR reduces post-SA unknowns only marginally (~6–7%). Does not
significantly reduce repair passes. All configurations already solve (n_unknown=0).
**Verdict: Neutral — not worth changing SEAL_STR.**

---

### Exp D — Constraint-score selector vs baseline (research/600)

| strategy         | n_unk_final | passes | repair_s |
|------------------|-------------|--------|----------|
| lowest_T (baseline) | 0        | 63     | 2.635s   |
| constraint_score | 0           | **25** | **1.053s** |
| combined         | 0           | **25** | 1.124s   |

**All 4 scenarios — constraint_score:**

| scenario      | n_unk_post_sa | n_unk_final | MAE    | passes | repair_s |
|---------------|---------------|-------------|--------|--------|----------|
| easy/200      | 31            | 0           | 0.4530 | 4      | 0.015s   |
| normal/600    | 972           | 0           | 0.4065 | 12     | 0.384s   |
| research/200  | 27            | 0           | 0.6561 | 4      | 0.016s   |
| research/600  | 5795          | 0           | 0.4042 | 25     | 1.115s   |

**Finding:** Constraint-score selector uses 2.5× fewer passes and runs 2.4× faster on
research/600 with zero regression across all 4 scenarios. MAE is within +0.001 of baseline.
**Verdict: WINNER — ready for promotion to `perf/board-gen-10x`.**

---

### Exp B — Mini-SA reannealing (research/600)

| ring_r | iters  | n_solved_mini | n_unk_final | MAE    | repair_s |
|--------|--------|---------------|-------------|--------|----------|
| 2      | 20K    | 2             | 0           | 0.9142 | 0.826s   |
| 3      | 50K    | 2             | 0           | 0.9142 | 0.871s   |
| 3      | 100K   | 2             | 0           | 0.9142 | 0.974s   |

**Finding:** Achieves n_unknown=0 but MAE rises to 0.914 (2.27× worse than 0.403 baseline).
The mini-SA rearranges mines within ring neighborhoods in ways that reduce sealed clusters but
significantly degrade visual fidelity. Only 2 of 50 clusters were solved BY the mini-SA;
the rest were resolved by the fallback fast_seal anyway, meaning the mini-SA changes
added visual cost without proportional benefit.
**Verdict: FAILS MAE gate (tolerance: baseline + 0.005). Not suitable for production.**

---

### Exp F — Post-SA local reannealing with amplified weights (research/600)

| ring_r | iters | amp | n_solved_mini | n_unk_final | MAE    | repair_s |
|--------|-------|-----|---------------|-------------|--------|----------|
| 3      | 30K   | 50  | 2             | 0           | 0.9142 | 1.221s   |
| 3      | 80K   | 100 | 2             | 0           | 0.9142 | 1.300s   |
| 5      | 80K   | 200 | 2             | 0           | 0.9141 | 1.279s   |

**Finding:** Same MAE degradation as Exp B (0.914). Amplifying sealing-prevention weights
does not prevent the mini-SA from making visually-costly mine rearrangements; it only
changes WHICH rearrangements are chosen. 2/50 clusters solved by mini-SA — rest via fallback.
**Verdict: FAILS MAE gate. Same root problem as Exp B.**

---

## Summary

| Exp | Technique | n_unk=0? | MAE OK? | Verdict |
|-----|-----------|----------|---------|---------|
| C   | SEAL_STR/THR sweep | ✓ | ✓ | Neutral — no benefit |
| D   | Constraint-score selector | ✓ | ✓ | **PROMOTE to perf/board-gen-10x** |
| B   | Mini-SA reannealing | ✓ | ✗ (0.914 vs 0.403) | Fails quality gate |
| F   | Amplified-weight mini-SA | ✓ | ✗ (0.914 vs 0.403) | Fails quality gate |

**Recommended action:** Implement Exp D `constraint_score` selector in
`repair.py:run_fast_seal_repair` and open a PR to `perf/board-gen-10x`.
The selector change is ~20 lines, passes all 4 scenarios, and delivers
2.4× speedup on the repair phase with no quality regression.
