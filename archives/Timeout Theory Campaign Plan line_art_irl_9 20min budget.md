# Targeted Repair-Only Follow-Up Plan: `line_art_irl_9` from `global46` Near-Pass Outputs

## Summary
Run a focused, decision-complete repair-only mini-campaign for one source image (`line_art_irl_9.png`) using the existing near-pass `global46` outputs as fixed starting points.

This plan replaces the earlier 20-minute full-pipeline timeout campaign. The previous plan reran `global46` and then invoked `sa3x_adaptive` fallback when the primary failed. This revised plan deliberately avoids `sa3x_adaptive` for this image family because prior evidence showed the fallback made `line_art_irl_9.png` worse numerically and visually.

### Experiment question
Can the already-near-pass `global46` boards for `line_art_irl_9.png` be finished by a targeted late repair pass, without rerunning simulated annealing and without introducing background leakage?

### Main hypothesis
The failure is not primarily an image-load, board-size, or full-SA-generation problem. The likely bottleneck is the final deterministic repair stage: the `global46` boards reached only 20–89 unresolved cells, but campaign pass criteria require `n_unknown == 0`.

### Campaign root
```text
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2_line_art_irl_9_repair_only_last100
```

### Source image
```text
D:\Github\MineSweeper_Line_Art\line_art_irl_9.png
```

### Fixed board sizing
```text
300x942
```

### Seeds
```text
11, 22, 33
```

### Runtime model
Repair-only extended budget. Do not rerun coarse SA, fine SA, refine SA, adaptive local cap, rescue SA, or `sa3x_adaptive` fallback.

### Rollup scope
Also update:

```text
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_campaigns.md
```

---

## Baseline Evidence That Motivates This Experiment

Use the existing campaign_2 `global46` artifacts as the baseline starting boards.

| seed | starting profile | expected baseline `n_unknown` | expected baseline coverage | expected baseline solvable | purpose |
|---:|---|---:|---:|---|---|
| 11 | `global46` | 89 | ~0.999624 | true | near-pass repair input |
| 22 | `global46` | 20 | ~0.999911 | true | strongest near-pass repair input |
| 33 | `global46` | 37 | ~0.999848 | true | near-pass repair input |

The old fallback direction is explicitly not used here because the `sa3x_adaptive` fallback ended with thousands of unknown cells for the same image family and produced background-leakage visual rejections.

---

## Required Baseline Inputs

For each seed, read the prior `global46` artifacts from campaign_2.

```text
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s11\grid_300x942.npy
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s11\metrics_300x942.json
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s11\visual_300x942.png

D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s22\grid_300x942.npy
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s22\metrics_300x942.json
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s22\visual_300x942.png

D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s33\grid_300x942.npy
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s33\metrics_300x942.json
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s33\visual_300x942.png
```

If any baseline artifact is missing, malformed, from the wrong profile, wrong image hash, wrong board size, or wrong seed, fail fast and do not substitute `sa3x_adaptive` artifacts.

---

## Implementation Changes

### 1. Create a dedicated repair-only campaign runner

Create:

```text
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2_line_art_irl_9_repair_only_last100\run_repair_only_campaign.py
```

Responsibilities:

1. Lock source scope to exactly `line_art_irl_9.png`.
2. Lock seed scope to exactly `11,22,33`.
3. Locate the prior `global46` baseline artifacts for each seed.
4. Validate baseline metrics and grid integrity.
5. Fan out the repair-only variants listed below.
6. Emit campaign_2-style artifacts and summary documents.
7. Update `line_art_campaigns.md` with this campaign section.

Do not adapt the old plan's `global46` primary / `sa3x_adaptive` fallback control flow. This campaign does not have a fallback profile. It has fixed baseline inputs and repair variants.

---

### 2. Add a repair-only board runner

Create one reusable script at repo root or under the campaign root. Recommended repo-root path:

```text
D:\Github\MineSweepResearchFilesFinalIteration\run_repair_only_from_grid.py
```

Purpose:

```text
Load an existing mine grid, reconstruct the same target/weights/forbidden-mask context, run only the selected repair strategy, solve, render, and write metrics.
```

The script should import the existing project modules:

```python
from board_sizing import derive_board_from_width
from core import (
    load_image_smart,
    apply_piecewise_T_compression,
    compute_zone_aware_weights,
    compute_N,
    assert_board_valid,
)
from corridors import build_adaptive_corridors
from repair import run_phase2_full_repair
from solver import solve_board, ensure_solver_warmed
```

The existing `run_phase2_full_repair` should be reused for the Phase 2-only variant because it already detects sealed unknown clusters and tries bounded single/pair mine removals. It accepts parameters for time budget, outer iterations, clusters per iteration, external mines per cluster, trial rounds, solve rounds, and pair-search limits.

---

### 3. Add CLI arguments for repair-only execution

`run_repair_only_from_grid.py` should support:

```powershell
python run_repair_only_from_grid.py `
  --image "D:\Github\MineSweeper_Line_Art\line_art_irl_9.png" `
  --baseline-grid "<CAMPAIGN_2_GLOBAL46_GRID>" `
  --baseline-metrics "<CAMPAIGN_2_GLOBAL46_METRICS>" `
  --out-dir "<ROOT>\runs\<repair_variant>\line_art_irl_9.png_s<seed>" `
  --run-tag "alt_line_art_irl_9.png_s<seed>_<repair_variant>" `
  --board-w 300 `
  --seed <seed> `
  --repair-variant <baseline_recheck|phase2_extended_only|last100_only|phase2_extended_then_last100> `
  --phase2-budget-s <seconds> `
  --last100-budget-s <seconds> `
  --pw-knee 4.0 `
  --pw-t-max 4.6 `
  --contrast-factor 2.0 `
  --hi-boost 18 `
  --background-leakage-gate `
  --allow-noncanonical `
  --ledger-jsonl "<ROOT>\worker_ledgers\<repair_variant>\alt_line_art_irl_9.png_s<seed>_<repair_variant>.jsonl" `
  --ledger-csv "<ROOT>\worker_ledgers\<repair_variant>\alt_line_art_irl_9.png_s<seed>_<repair_variant>.csv"
```

Important: this script must not expose or use these flags:

```text
--method-test-sa-3x
--adaptive-local-cap
--adaptive-local-cap-ladder
--adaptive-local-cap-value
--adaptive-local-trigger-eval
--adaptive-local-sa-budget-s
```

Those flags belong to the rejected fallback path and are intentionally excluded.

---

## Repair Variants To Execute

Run each variant independently from the original saved `global46` grid. Do not chain a previous variant's output into the next variant unless the variant explicitly says so.

### Variant A: `baseline_recheck`

Purpose:

```text
Verify that loading the saved `global46` grid and recomputing target/solver state reproduces the prior near-pass condition.
```

Behavior:

1. Load baseline grid.
2. Rebuild target, target_eval, weights, and forbidden mask using `global46` parameters.
3. Run `solve_board(..., mode="full")`.
4. Write metrics and visual report.
5. Make no grid modifications.

Acceptance expectation:

```text
n_unknown should match or be extremely close to prior campaign_2 baseline metrics.
```

If `baseline_recheck` does not reproduce the prior near-pass state, stop the campaign and investigate artifact drift before testing repair variants.

---

### Variant B: `phase2_extended_only`

Purpose:

```text
Test whether the original failure was simply caused by insufficient Phase 2 repair time.
```

Behavior:

1. Start from the saved `global46` grid.
2. Skip Phase 1 repair.
3. Skip all SA stages.
4. Run only `run_phase2_full_repair` with an extended budget.
5. Run final full solve.
6. Render and write artifacts.

Recommended parameters:

```python
time_budget_s = 720
max_outer_iterations = 96
max_clusters_per_iteration = 128
max_ext_mines_per_cluster = 64
trial_max_rounds = 120
solve_max_rounds = 400
pair_trial_limit = 48
pair_combo_limit = 256
```

Interpretation:

| outcome | meaning |
|---|---|
| `n_unknown == 0` and visual gate passes | Timeout theory strongly supported. Existing Phase 2 can solve this if given enough time. |
| `n_unknown` decreases but does not reach zero | Phase 2 helps, but its search policy is incomplete. |
| `n_unknown` does not improve | The remaining unknowns are not reachable by current Phase 2 logic. |
| numeric pass but background leakage fails | Repair can solve the board but harms visual quality. |

---

### Variant C: `last100_only`

Purpose:

```text
Test whether the final 20–89 unresolved cells need a specialized final cleanup pass instead of more generic Phase 2 time.
```

Trigger condition:

```text
1 <= n_unknown <= 100
```

Behavior:

1. Start from the saved `global46` grid.
2. Skip Phase 1 repair.
3. Skip Phase 2 extended repair.
4. Run the new `last100_repair` routine.
5. Run final full solve.
6. Render and write artifacts.

Recommended parameters:

```python
last100_budget_s = 300
last100_max_outer_iterations = 200
last100_trial_max_rounds = 160
last100_solve_max_rounds = 500
last100_pair_trial_limit = 64
last100_pair_combo_limit = 512
last100_max_error_delta_mean_abs = 0.020
last100_max_error_delta_true_bg = 0.010
last100_max_error_delta_hi = 0.050
```

Required algorithm shape:

1. Solve the current grid in full mode.
2. If `n_unknown == 0`, stop.
3. If `n_unknown > 100`, stop and mark `last100_not_applicable`.
4. Label connected unknown components.
5. For each unknown component, collect adjacent external mine candidates where `forbidden == 0`.
6. Try single-mine removals first.
7. If no single removal improves `n_unknown`, try bounded pair removals.
8. For every candidate move, compute trial solve metrics.
9. Accept only moves that reduce `n_unknown` and do not exceed error-delta guardrails.
10. Prefer the move with the largest `n_unknown` reduction, then the lowest visual cost.
11. Repeat until solved, budget exhausted, or no accepted move exists.

Each accepted move must log:

```json
{
  "iteration": 1,
  "component_id": 3,
  "component_size": 7,
  "move_type": "single|pair",
  "removed_mines": [[y, x]],
  "pre_n_unknown": 37,
  "post_n_unknown": 21,
  "delta_unknown": 16,
  "delta_mean_abs_error": 0.0031,
  "delta_true_bg_err": 0.0004,
  "delta_hi_err": 0.012,
  "accepted": true
}
```

Interpretation:

| outcome | meaning |
|---|---|
| Last-100 solves while Phase 2-only does not | The failure is a final-heuristic limitation, not just a raw timeout. |
| Last-100 fails but Phase 2-only solves | Existing Phase 2 logic is sufficient with more time. |
| Both solve | Promote the cheaper/cleaner variant after visual review. |
| Both fail | Repair logic needs a deeper redesign. |

---

### Variant D: `phase2_extended_then_last100`

Purpose:

```text
Test the most practical promotion path: let Phase 2 reduce anything it can, then use Last-100 mode only if final unresolved cells remain.
```

Behavior:

1. Start from the saved `global46` grid.
2. Run `phase2_extended_only` behavior with a shorter cap.
3. Re-solve.
4. If `1 <= n_unknown <= 100`, run `last100_repair`.
5. Re-solve and write final artifacts.

Recommended parameters:

```python
phase2_budget_s = 360
last100_budget_s = 300
```

Interpretation:

| outcome | meaning |
|---|---|
| Solves and passes visual gate | Best promotion candidate. |
| Solves but visual gate fails | Need stronger visual-cost constraints. |
| Does not solve | Combined late repair is insufficient. |

---

## Explicit No-`sa3x_adaptive` Policy

This campaign must not execute `sa3x_adaptive` under any condition.

### Disallowed behavior

```text
Do not run adaptive local cap fallback.
Do not run SA3x fallback.
Do not run rescue SA.
Do not rerun coarse/fine/refine SA.
Do not substitute `sa3x_adaptive` grids as repair inputs.
Do not mark `sa3x_adaptive` as a fallback row in campaign output.
```

### Required failure behavior

If a baseline `global46` artifact is missing or invalid:

```text
fail fast
record artifact failure
write the failure row
stop that seed
```

Do not recover by running `sa3x_adaptive`.

---

## Visual Gate: Background Leakage Protection

A repair result is not promotable unless it passes both numeric gates and visual gates.

### Numeric pass gate

Keep campaign_2 numeric semantics:

```text
n_rate_raw = n_unknown / cells
passed_numeric = (n_rate_raw <= 1e-12) AND solvable=true AND coverage>=0.9999 AND aspect_gate != false
```

### New visual pass gate

Add:

```text
passed_visual = no P0/P1 rejected background leakage AND no P0/P1 rejected smears AND no P0/P1 rejected polarity/background dominance
```

### Promotion gate

```text
promoted = passed_numeric AND passed_visual
```

### Background leakage review requirements

Each final visual must be reviewed against:

1. White or low-target background regions remain visually clean.
2. Repair does not introduce smeared mine/number texture into background areas.
3. Line readability is not sacrificed to solve the puzzle.
4. No accepted repair move creates a visually obvious dirty halo around line art.

### Required visual review file

```text
<ROOT>\visual_anomaly_review.md
```

Minimum columns:

| severity | anomaly | disposition | image_rel | seed | repair_variant | n_rate_raw | n_unknown | coverage | screenshot | metrics |
|---|---|---|---|---:|---|---:|---:|---:|---|---|

Allowed anomaly taxonomy:

```text
background leakage
smears
polarity/background dominance
rays
artifact missing
line damage
```

Allowed dispositions:

```text
accepted
watch
rejected
```

---

## Attempt Matrix

Expected planned rows:

```text
3 seeds x 4 repair variants = 12 attempts
```

| seed | baseline source | variant | expected output folder |
|---:|---|---|---|
| 11 | campaign_2 `global46` grid | `baseline_recheck` | `<ROOT>\runs\baseline_recheck\line_art_irl_9.png_s11` |
| 11 | campaign_2 `global46` grid | `phase2_extended_only` | `<ROOT>\runs\phase2_extended_only\line_art_irl_9.png_s11` |
| 11 | campaign_2 `global46` grid | `last100_only` | `<ROOT>\runs\last100_only\line_art_irl_9.png_s11` |
| 11 | campaign_2 `global46` grid | `phase2_extended_then_last100` | `<ROOT>\runs\phase2_extended_then_last100\line_art_irl_9.png_s11` |
| 22 | campaign_2 `global46` grid | `baseline_recheck` | `<ROOT>\runs\baseline_recheck\line_art_irl_9.png_s22` |
| 22 | campaign_2 `global46` grid | `phase2_extended_only` | `<ROOT>\runs\phase2_extended_only\line_art_irl_9.png_s22` |
| 22 | campaign_2 `global46` grid | `last100_only` | `<ROOT>\runs\last100_only\line_art_irl_9.png_s22` |
| 22 | campaign_2 `global46` grid | `phase2_extended_then_last100` | `<ROOT>\runs\phase2_extended_then_last100\line_art_irl_9.png_s22` |
| 33 | campaign_2 `global46` grid | `baseline_recheck` | `<ROOT>\runs\baseline_recheck\line_art_irl_9.png_s33` |
| 33 | campaign_2 `global46` grid | `phase2_extended_only` | `<ROOT>\runs\phase2_extended_only\line_art_irl_9.png_s33` |
| 33 | campaign_2 `global46` grid | `last100_only` | `<ROOT>\runs\last100_only\line_art_irl_9.png_s33` |
| 33 | campaign_2 `global46` grid | `phase2_extended_then_last100` | `<ROOT>\runs\phase2_extended_then_last100\line_art_irl_9.png_s33` |

---

## Command Templates

### `baseline_recheck`

```powershell
python run_repair_only_from_grid.py --image "D:\Github\MineSweeper_Line_Art\line_art_irl_9.png" --baseline-grid "D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s<seed>\grid_300x942.npy" --baseline-metrics "D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s<seed>\metrics_300x942.json" --out-dir "<ROOT>\runs\baseline_recheck\line_art_irl_9.png_s<seed>" --run-tag "alt_line_art_irl_9.png_s<seed>_baseline_recheck" --board-w 300 --seed <seed> --repair-variant baseline_recheck --phase2-budget-s 0 --last100-budget-s 0 --pw-knee 4.0 --pw-t-max 4.6 --contrast-factor 2.0 --hi-boost 18 --background-leakage-gate --allow-noncanonical --ledger-jsonl "<ROOT>\worker_ledgers\baseline_recheck\alt_line_art_irl_9.png_s<seed>_baseline_recheck.jsonl" --ledger-csv "<ROOT>\worker_ledgers\baseline_recheck\alt_line_art_irl_9.png_s<seed>_baseline_recheck.csv"
```

### `phase2_extended_only`

```powershell
python run_repair_only_from_grid.py --image "D:\Github\MineSweeper_Line_Art\line_art_irl_9.png" --baseline-grid "D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s<seed>\grid_300x942.npy" --baseline-metrics "D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s<seed>\metrics_300x942.json" --out-dir "<ROOT>\runs\phase2_extended_only\line_art_irl_9.png_s<seed>" --run-tag "alt_line_art_irl_9.png_s<seed>_phase2_extended_only" --board-w 300 --seed <seed> --repair-variant phase2_extended_only --phase2-budget-s 720 --last100-budget-s 0 --pw-knee 4.0 --pw-t-max 4.6 --contrast-factor 2.0 --hi-boost 18 --background-leakage-gate --allow-noncanonical --ledger-jsonl "<ROOT>\worker_ledgers\phase2_extended_only\alt_line_art_irl_9.png_s<seed>_phase2_extended_only.jsonl" --ledger-csv "<ROOT>\worker_ledgers\phase2_extended_only\alt_line_art_irl_9.png_s<seed>_phase2_extended_only.csv"
```

### `last100_only`

```powershell
python run_repair_only_from_grid.py --image "D:\Github\MineSweeper_Line_Art\line_art_irl_9.png" --baseline-grid "D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s<seed>\grid_300x942.npy" --baseline-metrics "D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s<seed>\metrics_300x942.json" --out-dir "<ROOT>\runs\last100_only\line_art_irl_9.png_s<seed>" --run-tag "alt_line_art_irl_9.png_s<seed>_last100_only" --board-w 300 --seed <seed> --repair-variant last100_only --phase2-budget-s 0 --last100-budget-s 300 --pw-knee 4.0 --pw-t-max 4.6 --contrast-factor 2.0 --hi-boost 18 --background-leakage-gate --allow-noncanonical --ledger-jsonl "<ROOT>\worker_ledgers\last100_only\alt_line_art_irl_9.png_s<seed>_last100_only.jsonl" --ledger-csv "<ROOT>\worker_ledgers\last100_only\alt_line_art_irl_9.png_s<seed>_last100_only.csv"
```

### `phase2_extended_then_last100`

```powershell
python run_repair_only_from_grid.py --image "D:\Github\MineSweeper_Line_Art\line_art_irl_9.png" --baseline-grid "D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s<seed>\grid_300x942.npy" --baseline-metrics "D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_robustness_campaign_2\runs\global46\line_art_irl_9.png_s<seed>\metrics_300x942.json" --out-dir "<ROOT>\runs\phase2_extended_then_last100\line_art_irl_9.png_s<seed>" --run-tag "alt_line_art_irl_9.png_s<seed>_phase2_extended_then_last100" --board-w 300 --seed <seed> --repair-variant phase2_extended_then_last100 --phase2-budget-s 360 --last100-budget-s 300 --pw-knee 4.0 --pw-t-max 4.6 --contrast-factor 2.0 --hi-boost 18 --background-leakage-gate --allow-noncanonical --ledger-jsonl "<ROOT>\worker_ledgers\phase2_extended_then_last100\alt_line_art_irl_9.png_s<seed>_phase2_extended_then_last100.jsonl" --ledger-csv "<ROOT>\worker_ledgers\phase2_extended_then_last100\alt_line_art_irl_9.png_s<seed>_phase2_extended_then_last100.csv"
```

---

## Required Per-Attempt Artifacts

Each attempt must emit:

```text
metrics_300x942.json
grid_300x942.npy
visual_300x942.png
attempt_meta.json
repair_move_log.jsonl
log.txt
ledger CSV
ledger JSONL
command_signature
```

Metrics must include:

```json
{
  "source_profile": "global46",
  "repair_variant": "phase2_extended_only",
  "baseline_grid_path": "...",
  "baseline_metrics_path": "...",
  "baseline_n_unknown": 37,
  "baseline_coverage": 0.999848,
  "baseline_solvable": true,
  "final_n_unknown": 0,
  "final_coverage": 1.0,
  "final_solvable": true,
  "n_rate_raw": 0.0,
  "passed_numeric": true,
  "passed_visual": true,
  "promoted": true,
  "phase2_repair_applied": true,
  "last100_repair_applied": false,
  "n_phase2_fixes": 4,
  "n_last100_fixes": 0,
  "background_leakage_gate": {
    "required": true,
    "status": "accepted|watch|rejected",
    "reviewer_notes": ""
  }
}
```

---

## Campaign-Level Outputs

Emit the same campaign-level documentation style as campaign_2, but with repair-only terminology.

```text
<ROOT>\campaign_runs.csv
<ROOT>\campaign_summary.json
<ROOT>\campaign_summary.md
<ROOT>\n_unknown_board_attempts.md
<ROOT>\campaign_executive_scorecard.md
<ROOT>\per_image_diagnostics.md
<ROOT>\visual_anomaly_review.md
<ROOT>\campaign_reproducibility.md
<ROOT>\repair_variant_comparison.md
<ROOT>\last100_move_audit.md
```

### `repair_variant_comparison.md`

Required table:

| seed | variant | baseline_unknown | final_unknown | unknown_delta | final_coverage | final_solvable | passed_numeric | passed_visual | promoted | total_time_s |
|---:|---|---:|---:|---:|---:|---|---|---|---|---:|

### `last100_move_audit.md`

Required sections:

1. Per-seed accepted moves.
2. Per-seed rejected candidate move counts.
3. Largest `n_unknown` reduction move.
4. Largest visual-cost move.
5. Moves rejected by background/error guardrails.

---

## Shared Rollup Update

Update:

```text
D:\Github\MineSweepResearchFilesFinalIteration\results\line_art_campaigns.md
```

Add a new section:

```markdown
## line_art_robustness_campaign_2_line_art_irl_9_repair_only_last100
```

Include:

1. Campaign purpose.
2. Link to campaign root.
3. Links to campaign summary docs.
4. Full per-attempt inline table.
5. Delta table vs campaign_2 `global46` baseline.
6. Delta table vs campaign_2 `sa3x_adaptive` fallback.
7. Final decision statement:
   - timeout confirmed,
   - last-100 heuristic required,
   - repair redesign required,
   - or visual gate blocks promotion.

---

## Test Plan

### 1. Baseline input integrity

- Verify exactly one source image is used.
- Verify source image decodes successfully.
- Verify source hash matches expected campaign_2 image hash if available.
- Verify board size recomputes to `300x942`.
- Verify each baseline grid exists.
- Verify each baseline metrics file exists.
- Verify each baseline metrics file says seed is one of `11,22,33`.
- Verify each baseline metrics file is from `global46`, not `sa3x_adaptive`.
- Verify each baseline grid shape is `(942, 300)`.
- Verify each baseline grid is binary.
- Verify each baseline grid has no mines in forbidden cells after reconstruction.

### 2. Baseline reproduction integrity

For `baseline_recheck`:

- Recompute solve state.
- Confirm `n_unknown` is close to prior `global46` metric.
- Confirm coverage is close to prior `global46` metric.
- Confirm `solvable=true` if that was true in prior metrics.
- If reproduction differs materially, stop and mark campaign invalid.

### 3. Execution integrity

- Planned rows = `12`.
- No fallback rows.
- No `sa3x_adaptive` rows.
- No commands contain `--method-test-sa-3x`.
- No commands contain `--adaptive-local-cap`.
- No commands execute coarse/fine/refine SA.
- Every attempt has metrics/grid/visual/log/ledger artifacts.
- Every attempt records the baseline grid path.
- Every attempt records the repair variant.

### 4. Metric integrity

- Recompute `n_rate_raw = n_unknown / cells` for every attempt.
- Confirm `cells == 282600` for every attempt.
- Confirm `passed_numeric` matches campaign_2 semantics.
- Confirm `promoted = passed_numeric AND passed_visual`.
- Reconcile counts across:
  - `campaign_runs.csv`
  - `campaign_summary.json`
  - `n_unknown_board_attempts.md`
  - `repair_variant_comparison.md`

### 5. Last-100 integrity

For every `last100_only` and `phase2_extended_then_last100` run:

- Confirm Last-100 mode only triggers when `1 <= n_unknown <= 100`.
- Confirm every accepted move reduces `n_unknown`.
- Confirm every accepted move satisfies error-delta guardrails.
- Confirm every accepted move is written to `repair_move_log.jsonl`.
- Confirm rejected move counts are summarized.
- Confirm no accepted move violates forbidden-mask constraints.

### 6. Visual gate integrity

- Generate visual for every final grid.
- Review every final visual.
- Mark background leakage as `accepted`, `watch`, or `rejected`.
- Do not mark `promoted=true` unless visual gate passes.
- Ensure `visual_anomaly_review.md` includes all attempts.

### 7. Cross-campaign integrity

- Confirm `line_art_campaigns.md` contains the new campaign section.
- Confirm all links from the rollup work.
- Confirm the campaign section explicitly states that `sa3x_adaptive` was intentionally excluded.
- Confirm the campaign section includes deltas against the campaign_2 `global46` and `sa3x_adaptive` outcomes.

---

## Decision Table

| observed result | conclusion | next action |
|---|---|---|
| `phase2_extended_only` solves all seeds and visual gate passes | Timeout theory confirmed for this image. | Promote extended Phase 2 for this image family. |
| `phase2_extended_only` improves but does not solve | Time helps, but current Phase 2 search is incomplete. | Use Last-100 result to decide next repair logic. |
| `last100_only` solves when Phase 2-only does not | Final residuals need specialized last-mile repair. | Promote Last-100 mode after visual review. |
| `phase2_extended_then_last100` solves and passes visual gate | Best practical pipeline for near-pass `global46` boards. | Promote combined late-repair path. |
| Numeric pass occurs but visual gate rejects | Solver success is not enough. | Tighten visual-cost constraints and rerun. |
| No variant solves | Failure is structural, not just timeout. | Redesign repair candidate selection or solver reasoning. |
| Baseline recheck fails | Artifact drift or reconstruction mismatch. | Stop campaign and fix reproducibility before repair testing. |

---

## Assumptions and Defaults

- Source scope is intentionally one image: `line_art_irl_9.png`.
- Seed scope is intentionally `11,22,33`.
- Baseline inputs must be campaign_2 `global46` outputs.
- `sa3x_adaptive` is intentionally excluded.
- Metric convention remains campaign_2-style `n_rate_raw`, with `n_unknown` retained as the main human-readable count.
- Numeric pass semantics remain campaign_2-compatible.
- Visual pass semantics are stricter than campaign_2 because background leakage is now promotion-blocking.
- Output root is isolated and must not mutate existing campaign_2 artifacts.
- The original timeout-campaign root is superseded by the repair-only root.

