# Documentation Plan and Master Sheet

This document records the contrast preprocessing study in plain English. It is written so a reader can find the main result, see the controls, and scan every indexed run without digging through code.

## Documentation Plan
- Keep one master sheet for every indexed run.
- Use simple labels for image, contrast, solve result, unknown count, and runtime.
- Write one short finding block above the master sheet so the reader can see the main pattern first.
- Keep the source of truth in the result CSV files and mirror the important fields here for easy review.
- Add new runs as new rows instead of replacing old records.

## Reading Guide
- `harm(T>=7)` is stored as a fraction. For example, `0.26` means `26%`.
- `severe` means `harm(T>=7) > 0.20`.
- `solvable=True` means the board finished with no unknown cells.
- `unknown` is the number of cells the solver could not finish.

## Short Findings
- Total indexed runs: 42
- Severe runs: 6
- Non-severe runs: 36
- Severe runs were unsolved in every case: 0/6 solved
- Non-severe runs solved more often overall: 28/36 solved
- On `irisd3.png`, higher contrast lowered unknowns but did not reach a fully solved board.

## Master Sheet
| # | Cohort | Run Tag | Image | Contrast | Unknown | Coverage | Solved | Time (s) | Harm T>=7 | Note |
|---:|---|---|---|---:|---:|---:|---|---:|---:|---|
| 1 | 1x SA baseline | `contrast_study_input_source_image_c0p6` | `assets/input_source_image.png` | 0.6 | 0 | 1.000000 | yes | 13.64 | 0.0376 | non-severe |
| 2 | 3x SA study | `contrast_study_input_source_image_c0p6` | `assets/input_source_image.png` | 0.6 | 0 | 1.000000 | yes | 19.74 | 0.0376 | non-severe |
| 3 | 1x SA baseline | `contrast_study_input_source_image_c0p8` | `assets/input_source_image.png` | 0.8 | 0 | 1.000000 | yes | 13.13 | 0.0378 | non-severe |
| 4 | 3x SA study | `contrast_study_input_source_image_c0p8` | `assets/input_source_image.png` | 0.8 | 0 | 1.000000 | yes | 19.69 | 0.0378 | non-severe |
| 5 | 1x SA baseline | `contrast_study_input_source_image_c1p0` | `assets/input_source_image.png` | 1.0 | 0 | 1.000000 | yes | 12.10 | 0.0363 | non-severe |
| 6 | 3x SA study | `contrast_study_input_source_image_c1p0` | `assets/input_source_image.png` | 1.0 | 0 | 1.000000 | yes | 18.85 | 0.0363 | non-severe |
| 7 | 1x SA baseline | `contrast_study_input_source_image_c1p2` | `assets/input_source_image.png` | 1.2 | 0 | 1.000000 | yes | 12.79 | 0.0375 | non-severe |
| 8 | 3x SA study | `contrast_study_input_source_image_c1p2` | `assets/input_source_image.png` | 1.2 | 0 | 1.000000 | yes | 19.62 | 0.0375 | non-severe |
| 9 | 1x SA baseline | `contrast_study_input_source_image_c1p5` | `assets/input_source_image.png` | 1.5 | 0 | 1.000000 | yes | 12.03 | 0.0396 | non-severe |
| 10 | 3x SA study | `contrast_study_input_source_image_c1p5` | `assets/input_source_image.png` | 1.5 | 0 | 1.000000 | yes | 17.89 | 0.0396 | non-severe |
| 11 | 1x SA baseline | `contrast_study_input_source_image_c2p0` | `assets/input_source_image.png` | 2.0 | 0 | 1.000000 | yes | 13.10 | 0.0404 | non-severe |
| 12 | 3x SA study | `contrast_study_input_source_image_c2p0` | `assets/input_source_image.png` | 2.0 | 0 | 1.000000 | yes | 18.65 | 0.0404 | non-severe |
| 13 | 1x SA baseline | `contrast_study_input_source_image_c2p5` | `assets/input_source_image.png` | 2.5 | 0 | 1.000000 | yes | 14.57 | 0.0415 | non-severe |
| 14 | 3x SA study | `contrast_study_input_source_image_c2p5` | `assets/input_source_image.png` | 2.5 | 0 | 1.000000 | yes | 19.44 | 0.0415 | non-severe |
| 15 | 1x SA baseline | `contrast_study_input_source_image_research_c0p6` | `assets/input_source_image_research.png` | 0.6 | 0 | 1.000000 | yes | 10.99 | 0.0395 | non-severe |
| 16 | 3x SA study | `contrast_study_input_source_image_research_c0p6` | `assets/input_source_image_research.png` | 0.6 | 0 | 1.000000 | yes | 16.66 | 0.0395 | non-severe |
| 17 | 1x SA baseline | `contrast_study_input_source_image_research_c0p8` | `assets/input_source_image_research.png` | 0.8 | 0 | 1.000000 | yes | 12.05 | 0.0395 | non-severe |
| 18 | 3x SA study | `contrast_study_input_source_image_research_c0p8` | `assets/input_source_image_research.png` | 0.8 | 0 | 1.000000 | yes | 17.31 | 0.0395 | non-severe |
| 19 | 1x SA baseline | `contrast_study_input_source_image_research_c1p0` | `assets/input_source_image_research.png` | 1.0 | 0 | 1.000000 | yes | 13.56 | 0.0401 | non-severe |
| 20 | 3x SA study | `contrast_study_input_source_image_research_c1p0` | `assets/input_source_image_research.png` | 1.0 | 0 | 1.000000 | yes | 19.36 | 0.0401 | non-severe |
| 21 | 1x SA baseline | `contrast_study_input_source_image_research_c1p2` | `assets/input_source_image_research.png` | 1.2 | 0 | 1.000000 | yes | 13.82 | 0.0464 | non-severe |
| 22 | 3x SA study | `contrast_study_input_source_image_research_c1p2` | `assets/input_source_image_research.png` | 1.2 | 0 | 1.000000 | yes | 18.93 | 0.0464 | non-severe |
| 23 | 1x SA baseline | `contrast_study_input_source_image_research_c1p5` | `assets/input_source_image_research.png` | 1.5 | 0 | 1.000000 | yes | 14.23 | 0.0520 | non-severe |
| 24 | 3x SA study | `contrast_study_input_source_image_research_c1p5` | `assets/input_source_image_research.png` | 1.5 | 0 | 1.000000 | yes | 19.48 | 0.0520 | non-severe |
| 25 | 1x SA baseline | `contrast_study_input_source_image_research_c2p0` | `assets/input_source_image_research.png` | 2.0 | 0 | 1.000000 | yes | 17.26 | 0.0579 | non-severe |
| 26 | 3x SA study | `contrast_study_input_source_image_research_c2p0` | `assets/input_source_image_research.png` | 2.0 | 0 | 1.000000 | yes | 22.76 | 0.0579 | non-severe |
| 27 | 1x SA baseline | `contrast_study_input_source_image_research_c2p5` | `assets/input_source_image_research.png` | 2.5 | 0 | 1.000000 | yes | 15.10 | 0.0623 | non-severe |
| 28 | 3x SA study | `contrast_study_input_source_image_research_c2p5` | `assets/input_source_image_research.png` | 2.5 | 0 | 1.000000 | yes | 20.00 | 0.0623 | non-severe |
| 29 | 1x SA baseline | `contrast_study_irisd3_c0p6` | `irisd3.png` | 0.6 | 2645 | 0.992759 | no | 47.87 | 0.1383 | non-severe |
| 30 | 3x SA study | `contrast_study_irisd3_c0p6` | `irisd3.png` | 0.6 | 3230 | 0.991638 | no | 51.94 | 0.1383 | non-severe |
| 31 | 1x SA baseline | `contrast_study_irisd3_c0p8` | `irisd3.png` | 0.8 | 2489 | 0.993031 | no | 47.20 | 0.1385 | non-severe |
| 32 | 3x SA study | `contrast_study_irisd3_c0p8` | `irisd3.png` | 0.8 | 2413 | 0.993286 | no | 51.83 | 0.1385 | non-severe |
| 33 | 1x SA baseline | `contrast_study_irisd3_c1p0` | `irisd3.png` | 1.0 | 2396 | 0.993500 | no | 50.96 | 0.1381 | non-severe |
| 34 | 3x SA study | `contrast_study_irisd3_c1p0` | `irisd3.png` | 1.0 | 2301 | 0.993693 | no | 51.45 | 0.1381 | non-severe |
| 35 | 1x SA baseline | `contrast_study_irisd3_c1p2` | `irisd3.png` | 1.2 | 2009 | 0.994419 | no | 48.31 | 0.1779 | non-severe |
| 36 | 3x SA study | `contrast_study_irisd3_c1p2` | `irisd3.png` | 1.2 | 1959 | 0.994632 | no | 49.85 | 0.1779 | non-severe |
| 37 | 1x SA baseline | `contrast_study_irisd3_c1p5` | `irisd3.png` | 1.5 | 2143 | 0.993957 | no | 48.53 | 0.2204 | severe |
| 38 | 3x SA study | `contrast_study_irisd3_c1p5` | `irisd3.png` | 1.5 | 1967 | 0.994228 | no | 50.78 | 0.2204 | severe |
| 39 | 1x SA baseline | `contrast_study_irisd3_c2p0` | `irisd3.png` | 2.0 | 1620 | 0.995471 | no | 49.33 | 0.2641 | severe |
| 40 | 3x SA study | `contrast_study_irisd3_c2p0` | `irisd3.png` | 2.0 | 1368 | 0.996019 | no | 50.48 | 0.2641 | severe |
| 41 | 1x SA baseline | `contrast_study_irisd3_c2p5` | `irisd3.png` | 2.5 | 1162 | 0.996430 | no | 49.76 | 0.2870 | severe |
| 42 | 3x SA study | `contrast_study_irisd3_c2p5` | `irisd3.png` | 2.5 | 1369 | 0.996066 | no | 50.69 | 0.2870 | severe |

## Reporting Method and Refresh Source-of-Truth
- Reporting method:
  - Keep this document as the reader-facing rollup of indexed contrast runs.
  - Keep run-level truth in generated result artifacts (`contrast_study_runs.csv`, metrics JSON, visual PNG).
  - Use the saturation matrix workflow as the promotion pipeline for any future winner claims.
- Baseline comparator sources (read-only reference):
  - [`results/contrast_preprocess_study_sa3x/contrast_study_summary.md`](../results/contrast_preprocess_study_sa3x/contrast_study_summary.md)
  - [`results/contrast_preprocess_study_20260421_100952/contrast_study_summary.md`](../results/contrast_preprocess_study_20260421_100952/contrast_study_summary.md)
- Refresh source-of-truth policy:
  - Only refresh saturation follow-up conclusions from eligible SA3x matrix campaigns that pass controls, stress, and visual approval.
  - Parallel matrix runs are refresh-eligible only after all phase shards complete, phase-local worker ledgers are merged or retained, and missing `metrics_*.json` files are resolved.
  - Runtime reporting should separate solve-clock budget fields (`solve_budget_hit`) from total-clock artifact fields (`total_runtime_budget_hit`, `post_solve_overhead_s`).
  - Do not treat SA1x-only new runs as refresh-eligible evidence.
  - If matrix outputs are incomplete (missing required artifacts or visual review ledger), keep current documentation state and mark campaign incomplete.

## Source Files
- [1x SA baseline CSV](../results/contrast_preprocess_study_20260421_100952/contrast_study_runs.csv)
- [3x SA study CSV](../results/contrast_preprocess_study_sa3x/contrast_study_runs.csv)
- [1x SA summary](../results/contrast_preprocess_study_20260421_100952/contrast_study_summary.md)
- [3x SA summary](../results/contrast_preprocess_study_sa3x/contrast_study_summary.md)
- [Saturation preprocess follow-up plan](saturation_preprocess_followup_plan.md)

_Generated: 2026-04-21T10:48:47.885012+00:00_
