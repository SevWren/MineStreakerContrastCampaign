# Project Result Summary

This page gives one plain-English table for every saved result folder in the repository.
Use it as the entry point, then open the per-folder pages in `docs/result_reports/` when you need details.

## Quick Counts
- Result folders with metrics: 44
- Fully solved folders: 5
- Runtime-budget hits: 14
- Profiled folders: 6
- Fastest solved folder: `theory_test_global46_assets` at 11.36s
- Slowest solved folder: `theory_test_global46_irisd3` at 40.20s
- Largest unknown count: `theory_test_opt4_irisd3_profile` with 52672 unknown cells

## Main Pattern
- The small `iris3d_200x246` runs are solved cleanly.
- The `global46` runs solved, but most `irisd3` and `adaptive` runs still end with unknown cells.
- Profiled failures show time is often lost in compile/warmup or `phase2_repair`, not in the final render step.

## Folder Table
| # | Folder | Run Tag | Board | Solved | Unknown | Coverage | Time (s) | Note | Doc |
|---:|---|---|---|---|---:|---:|---:|---|---|
| 1 | `iris3d_200x246` | `iris3d_200x246` | `200x246` | yes | 0 | 1.000000 | 28.90 | fully solved; repair: converged | [open](result_reports/iris3d_200x246.md) |
| 2 | `iris3d_200x246_smoke` | `iris3d_200x246_smoke` | `200x246` | yes | 0 | 1.000000 | 21.49 | fully solved; repair: converged | [open](result_reports/iris3d_200x246_smoke.md) |
| 3 | `iris3d_alias_300w_profile` | `iris3d_alias_check` | `300x824` | no | 51339 | 0.922949 | 31.52 | not fully solved; repair: timeout 11s; dominant phase: phase1_repair (0.36); hotspot: run_iris3d_visual_report.py:616:run_single_board; 64-bit candidate: solver.py:354:solve_board | [open](result_reports/iris3d_alias_300w_profile.md) |
| 4 | `irisd3_200x246` | `irisd3_200x246` | `200x246` | no | 4950 | 0.938988 | 2109.26 | not fully solved; repair: stagnated | [open](result_reports/irisd3_200x246.md) |
| 5 | `irisd3_200x246_fast` | `irisd3_200x246_fast` | `200x246` | no | 21062 | 0.736580 | 46.43 | not fully solved; repair: stagnated | [open](result_reports/irisd3_200x246_fast.md) |
| 6 | `irisd3_200x246_fast45` | `irisd3_200x246_fast45` | `200x246` | no | 21073 | 0.736593 | 26.57 | not fully solved; repair: stagnated | [open](result_reports/irisd3_200x246_fast45.md) |
| 7 | `irisd3_200x246_fast_cached` | `irisd3_200x246_fast_cached` | `200x246` | no | 20994 | 0.737530 | 46.03 | not fully solved; repair: stagnated | [open](result_reports/irisd3_200x246_fast_cached.md) |
| 8 | `irisd3_200x246_instrumented` | `instrumentation_check` | `200x246` | no | 5830 | 0.953256 | 21.53 | not fully solved; repair: stagnated | [open](result_reports/irisd3_200x246_instrumented.md) |
| 9 | `irisd3_200x246_instrumented_quick` | `instrumentation_quick` | `200x246` | no | 5665 | 0.954701 | 24.52 | not fully solved; repair: stagnated | [open](result_reports/irisd3_200x246_instrumented_quick.md) |
| 10 | `irisd3_300w_autoar` | `iris3d_runtime_calibrated` | `300x824` | no | 51585 | 0.922404 | 30.64 | not fully solved; repair: timeout 9s; dominant phase: phase1_repair (0.28); hotspot: run_iris3d_visual_report.py:616:run_single_board; 64-bit candidate: solver.py:354:solve_board | [open](result_reports/irisd3_300w_autoar.md) |
| 11 | `irisd3_profile_001` | `irisd3_profile_001` | `200x246` | no | 6995 | 0.912632 | 2028.85 | not fully solved; repair: stagnated | [open](result_reports/irisd3_profile_001.md) |
| 12 | `proof_method_test_sa3x` | `proof_method_test_sa3x` | `300x824` | no | 2020 | 0.994643 | 21.98 | not fully solved; runtime budget hit; repair: timeout 5s; dominant phase: phase1_repair (0.21) | [open](result_reports/proof_method_test_sa3x.md) |
| 13 | `theory_test_adaptive_ladder_irisd3` | `theory_adaptive_ladder_irisd3` | `300x824` | no | 6919 | 0.982105 | 50.09 | not fully solved; runtime budget hit; repair: timeout 9s; dominant phase: phase2_repair (0.40) | [open](result_reports/theory_test_adaptive_ladder_irisd3.md) |
| 14 | `theory_test_adaptive_ladder_irisd3_tuned1` | `theory_adaptive_ladder_irisd3_tuned1` | `300x824` | no | 3385 | 0.989846 | 46.23 | not fully solved; repair: timeout 10s; dominant phase: phase2_repair (0.43) | [open](result_reports/theory_test_adaptive_ladder_irisd3_tuned1.md) |
| 15 | `theory_test_adaptive_ladder_irisd3_tuned2` | `theory_adaptive_ladder_irisd3_tuned2` | `300x824` | no | 3404 | 0.989595 | 51.06 | not fully solved; runtime budget hit; repair: timeout 10s; dominant phase: phase2_repair (0.49) | [open](result_reports/theory_test_adaptive_ladder_irisd3_tuned2.md) |
| 16 | `theory_test_adaptive_ladder_irisd3_tuned3` | `theory_adaptive_ladder_irisd3_tuned3` | `300x824` | no | 3714 | 0.989116 | 43.11 | not fully solved; repair: timeout 8s; dominant phase: phase2_repair (0.47) | [open](result_reports/theory_test_adaptive_ladder_irisd3_tuned3.md) |
| 17 | `theory_test_adaptive_local40_irisd3_tuned11` | `theory_adaptive_local40_irisd3_tuned11` | `300x824` | no | 632 | 0.998516 | 47.65 | not fully solved; repair: timeout 9s; dominant phase: phase2_repair (0.42) | [open](result_reports/theory_test_adaptive_local40_irisd3_tuned11.md) |
| 18 | `theory_test_adaptive_local42_irisd3_tuned10` | `theory_adaptive_local42_irisd3_tuned10` | `300x824` | no | 809 | 0.997941 | 49.25 | not fully solved; repair: timeout 10s; dominant phase: phase2_repair (0.41) | [open](result_reports/theory_test_adaptive_local42_irisd3_tuned10.md) |
| 19 | `theory_test_adaptive_local42_wide_irisd3_tuned12` | `theory_adaptive_local42_wide_irisd3_tuned12` | `300x824` | no | 1003 | 0.997535 | 48.51 | not fully solved; repair: timeout 10s; dominant phase: phase2_repair (0.41) | [open](result_reports/theory_test_adaptive_local42_wide_irisd3_tuned12.md) |
| 20 | `theory_test_adaptive_local44_irisd3_tuned9` | `theory_adaptive_local44_irisd3_tuned9` | `300x824` | no | 1109 | 0.996915 | 47.26 | not fully solved; repair: timeout 8s; dominant phase: phase2_repair (0.42) | [open](result_reports/theory_test_adaptive_local44_irisd3_tuned9.md) |
| 21 | `theory_test_adaptive_local46_irisd3` | `theory_adaptive_local46_irisd3` | `300x824` | no | 50079 | 0.924610 | 52.45 | not fully solved; runtime budget hit; repair: timeout 9s; dominant phase: phase2_repair (0.59) | [open](result_reports/theory_test_adaptive_local46_irisd3.md) |
| 22 | `theory_test_adaptive_local46_irisd3_p20` | `theory_adaptive_local46_irisd3_p20` | `300x824` | no | 1105 | 0.996689 | 43.78 | not fully solved; repair: timeout 10s; dominant phase: phase2_repair (0.46) | [open](result_reports/theory_test_adaptive_local46_irisd3_p20.md) |
| 23 | `theory_test_adaptive_single46_irisd3_tuned4` | `theory_adaptive_single46_irisd3_tuned4` | `300x824` | no | 1965 | 0.994530 | 43.55 | not fully solved; repair: timeout 10s; dominant phase: phase2_repair (0.46) | [open](result_reports/theory_test_adaptive_single46_irisd3_tuned4.md) |
| 24 | `theory_test_adaptive_single46_irisd3_tuned4_rescue` | `theory_adaptive_single46_irisd3_tuned4_rescue` | `300x824` | no | 1673 | 0.995405 | 47.22 | not fully solved; repair: timeout 10s; dominant phase: phase2_repair (0.43) | [open](result_reports/theory_test_adaptive_single46_irisd3_tuned4_rescue.md) |
| 25 | `theory_test_adaptive_single46_irisd3_tuned4_rescue_profile` | `theory_adaptive_single46_irisd3_tuned4_rescue_profile` | `300x824` | no | 1684 | 0.995401 | 50.21 | not fully solved; runtime budget hit; repair: timeout 11s; dominant phase: phase2_repair (0.40); hotspot: run_iris3d_visual_report.py:736:run_single_board; 64-bit candidate: solver.py:354:solve_board | [open](result_reports/theory_test_adaptive_single46_irisd3_tuned4_rescue_profile.md) |
| 26 | `theory_test_adaptive_single46_irisd3_tuned5_hardstage` | `theory_adaptive_single46_irisd3_tuned5_hardstage` | `300x824` | no | 1221 | 0.996095 | 50.98 | not fully solved; runtime budget hit; repair: timeout 9s; dominant phase: phase2_repair (0.39) | [open](result_reports/theory_test_adaptive_single46_irisd3_tuned5_hardstage.md) |
| 27 | `theory_test_adaptive_single46_irisd3_tuned6_balanced` | `theory_adaptive_single46_irisd3_tuned6_balanced` | `300x824` | no | 1400 | 0.995887 | 47.76 | not fully solved; repair: timeout 8s; dominant phase: phase2_repair (0.42) | [open](result_reports/theory_test_adaptive_single46_irisd3_tuned6_balanced.md) |
| 28 | `theory_test_adaptive_single46_irisd3_tuned7_penalty` | `theory_adaptive_single46_irisd3_tuned7_penalty` | `300x824` | no | 1381 | 0.995840 | 47.31 | not fully solved; repair: timeout 9s; dominant phase: phase2_repair (0.42) | [open](result_reports/theory_test_adaptive_single46_irisd3_tuned7_penalty.md) |
| 29 | `theory_test_adaptive_single46_irisd3_tuned8_penalty_hi` | `theory_adaptive_single46_irisd3_tuned8_penalty_hi` | `300x824` | no | 1363 | 0.995773 | 47.33 | not fully solved; repair: timeout 8s; dominant phase: phase2_repair (0.42) | [open](result_reports/theory_test_adaptive_single46_irisd3_tuned8_penalty_hi.md) |
| 30 | `theory_test_budget_decoupled_irisd3` | `theory_budget_decoupled_irisd3` | `300x824` | no | 1564 | 0.995494 | 46.69 | not fully solved; repair: timeout 9s; dominant phase: phase2_repair (0.43) | [open](result_reports/theory_test_budget_decoupled_irisd3.md) |
| 31 | `theory_test_budget_shift_irisd3_tuned13` | `theory_budget_shift_irisd3_tuned13` | `300x824` | no | 1003 | 0.997635 | 51.32 | not fully solved; runtime budget hit; repair: timeout 10s; dominant phase: phase2_repair (0.51) | [open](result_reports/theory_test_budget_shift_irisd3_tuned13.md) |
| 32 | `theory_test_global46_assets` | `theory_global46_assets` | `300x370` | yes | 0 | 1.000000 | 11.36 | fully solved; repair: converged; dominant phase: render_and_write (0.21) | [open](result_reports/theory_test_global46_assets.md) |
| 33 | `theory_test_global46_irisd3` | `theory_global46_irisd3` | `300x824` | yes | 0 | 1.000000 | 40.20 | fully solved; repair: timeout 10s; dominant phase: phase2_repair (0.44) | [open](result_reports/theory_test_global46_irisd3.md) |
| 34 | `theory_test_global60_assets` | `theory_global60_assets` | `300x370` | yes | 0 | 1.000000 | 11.67 | fully solved; repair: converged; dominant phase: render_and_write (0.20) | [open](result_reports/theory_test_global60_assets.md) |
| 35 | `theory_test_global60_irisd3` | `theory_global60_irisd3` | `300x824` | no | 51053 | 0.923140 | 51.24 | not fully solved; runtime budget hit; repair: timeout 9s; dominant phase: phase2_repair (0.59) | [open](result_reports/theory_test_global60_irisd3.md) |
| 36 | `theory_test_global60_irisd3_p20` | `theory_global60_irisd3_p20` | `300x824` | no | 50399 | 0.924519 | 41.49 | not fully solved; repair: timeout 9s; dominant phase: phase2_repair (0.49) | [open](result_reports/theory_test_global60_irisd3_p20.md) |
| 37 | `theory_test_opt4_irisd3_nonprofile` | `theory_opt4_irisd3_nonprofile` | `300x824` | no | 1352 | 0.996116 | 49.41 | not fully solved; repair: timeout 10s; dominant phase: phase2_repair (0.41) | [open](result_reports/theory_test_opt4_irisd3_nonprofile.md) |
| 38 | `theory_test_opt4_irisd3_nonprofile_v2` | `theory_opt4_irisd3_nonprofile_v2` | `300x824` | no | 1781 | 0.995114 | 51.47 | not fully solved; runtime budget hit; repair: timeout 10s; dominant phase: phase2_repair (0.30) | [open](result_reports/theory_test_opt4_irisd3_nonprofile_v2.md) |
| 39 | `theory_test_opt4_irisd3_nonprofile_v3` | `theory_opt4_irisd3_nonprofile_v3` | `300x824` | no | 1319 | 0.996017 | 51.45 | not fully solved; runtime budget hit; repair: timeout 9s; dominant phase: phase2_repair (0.32) | [open](result_reports/theory_test_opt4_irisd3_nonprofile_v3.md) |
| 40 | `theory_test_opt4_irisd3_nonprofile_v4` | `theory_opt4_irisd3_nonprofile_v4` | `300x824` | no | 1521 | 0.995717 | 51.47 | not fully solved; runtime budget hit; repair: timeout 10s; dominant phase: compile_and_warmup (0.28) | [open](result_reports/theory_test_opt4_irisd3_nonprofile_v4.md) |
| 41 | `theory_test_opt4_irisd3_nonprofile_v5` | `theory_opt4_irisd3_nonprofile_v5` | `300x824` | no | 1356 | 0.996157 | 47.33 | not fully solved; repair: timeout 10s; dominant phase: phase2_repair (0.42) | [open](result_reports/theory_test_opt4_irisd3_nonprofile_v5.md) |
| 42 | `theory_test_opt4_irisd3_profile` | `theory_opt4_irisd3_profile` | `300x824` | no | 52672 | 0.919088 | 54.58 | not fully solved; runtime budget hit; repair: timeout 8s; dominant phase: compile_and_warmup (0.52); hotspot: run_iris3d_visual_report.py:736:run_single_board; 64-bit candidate: sa.py:162:run_sa | [open](result_reports/theory_test_opt4_irisd3_profile.md) |
| 43 | `theory_test_opt4_irisd3_profile_v2` | `theory_opt4_irisd3_profile_v2` | `300x824` | no | 1542 | 0.995604 | 51.78 | not fully solved; runtime budget hit; repair: timeout 10s; dominant phase: phase2_repair (0.39); hotspot: run_iris3d_visual_report.py:736:run_single_board; 64-bit candidate: solver.py:388:solve_board | [open](result_reports/theory_test_opt4_irisd3_profile_v2.md) |
| 44 | `theory_test_opt4_irisd3_profile_warm` | `theory_opt4_irisd3_profile_warm` | `300x824` | no | 1456 | 0.995697 | 50.95 | not fully solved; runtime budget hit; repair: timeout 10s; dominant phase: phase2_repair (0.39); hotspot: run_iris3d_visual_report.py:736:run_single_board; 64-bit candidate: solver.py:411:solve_board | [open](result_reports/theory_test_opt4_irisd3_profile_warm.md) |

## Study Notes
- [Contrast preprocessing plan](contrast_preprocessing_documentation_plan.md)
- [Contrast preprocessing follow-up tests](saturation_preprocess_followup_plan.md)
- [Folder-level report index](result_reports/README.md)

_Generated: 2026-04-21T11:58:11.935585+00:00_
