# Mine-Streaker

**Mine-Streaker** is a Python research project that converts line-art images into Minesweeper mine layouts. The goal is not only to make a board that visually resembles an input image, but also to make the resulting Minesweeper board logically solvable with deterministic solver logic.

This project tries to turn an image into a black-and-white drawing into a Minesweeper puzzle where the revealed number pattern reconstructs the original image.

---

## Status

This repository is an active research codebase, not a polished end-user application.

It is currently focused on:

* converting source images into Minesweeper-compatible mine grids,
* improving visual fidelity of the reconstructed number field,
* maximizing deterministic solvability,
* reducing unresolved solver pockets,
* testing repair strategies for late-stage solver failures,
* recording reproducible metrics, reports, and campaign artifacts.

The latest major finding is that a targeted repair-only campaign showed that near-pass boards can be resolved without rerunning simulated annealing when the remaining failure mode is localized sealed solver pockets.

---

## Source Image Runtime Contract

Normal runs must pass source images explicitly:

```powershell
python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical
python run_benchmark.py --image assets/line_art_irl_11_v2.png --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical
```

`python run_iter9.py` remains backward-compatible and defaults to `assets/input_source_image.png` only when `--image` is omitted.

Validation modes:

- default image strict validation uses `assets/SOURCE_IMAGE_HASH.json`
- explicit image + `--image-manifest <path>` validates against that manifest
- explicit image + `--allow-noncanonical` allows noncanonical validation with structured warnings

Source-image provenance is written into metrics (`source_image`, `source_image_validation`, `command_invocation`, `run_identity`, and artifact paths).

---

## Beginner Summary

### What problem does this project solve?

Minesweeper boards contain mines. Every safe square shows a number from `0` to `8`, telling you how many mines touch that square.

This project uses that rule backward:

1. Start with an image.
2. Choose where mines should go.
3. Compute the Minesweeper numbers caused by those mines.
4. Compare those numbers to the image.
5. Improve the mine layout until the number field looks like the image.
6. Check whether a deterministic solver can reveal the board without guessing.

### Why is this hard?

A board can look visually good but still be bad as a puzzle.

For example:

* The image may look correct.
* The number field may match the drawing well.
* But the solver may get stuck because some safe cells are trapped behind mine walls.

The project therefore has two competing goals:

| Goal                | Meaning                                                               |
| ------------------- | --------------------------------------------------------------------- |
| Visual fidelity     | The Minesweeper number field should look like the source image.       |
| Logical solvability | The board should be solvable by deterministic logic without guessing. |

The research challenge is balancing both.

---

## The Technical Summary

Mine-Streaker is an inverse-design pipeline for Minesweeper reconstruction.

The current pipeline consists of:

1. **Image preprocessing** — load and normalize the source image.
2. **Board sizing** — derive a board size that preserves the source aspect ratio.
3. **Target construction** — convert image intensity into a target number field.
4. **Weight construction** — assign higher or lower penalties to regions of the image.
5. **Corridor generation** — reserve mine-free paths to support solver reachability.
6. **Simulated annealing** — optimize a binary mine grid against the target number field.
7. **Deterministic solving** — evaluate how much of the board can be solved logically.
8. **Repair phases** — adjust late-stage mine placement to reduce unresolved unknown cells.
9. **Reporting** — write metrics, visual reports, grids, logs, and campaign summaries.

---

## Repository Layout

```text
.
├── board_sizing.py
├── core.py
├── corridors.py
├── pipeline.py
├── repair.py
├── report.py
├── run_benchmark.py
├── run_iter9.py
├── run_repair_only_from_grid.py
├── sa.py
├── solver.py
├── assets/
├── docs/
├── Larger_boards_fidelity_iteration/
└── results/
```

### Main Runtime Modules

| File                                  | Responsibility                                                                                   |
| ------------------------------------- | ------------------------------------------------------------------------------------------------ |
| `board_sizing.py`                     | Derives board dimensions from source image aspect ratio.                                         |
| `core.py`                             | Loads images, computes target fields, number fields, loss weights, and preprocessing transforms. |
| `corridors.py`                        | Builds mine-free corridor masks to improve solver reachability.                                  |
| `sa.py`                               | Runs simulated annealing to optimize mine placement.                                             |
| `solver.py`                           | Runs deterministic Minesweeper solving logic and reports coverage/unknowns.                      |
| `repair.py`                           | Applies post-solver repair heuristics such as Phase 1, Phase 2, and Last-100 repair.             |
| `pipeline.py`                         | Older orchestration path for the reconstruction pipeline.                                        |
| `report.py`                           | Renders visual reports and diagnostic outputs.                                                   |
| `run_iter9.py`                        | Main current reconstruction entry point.                                                         |
| `run_benchmark.py`                    | Runs multi-board/multi-seed benchmark checks.                                                    |
| `run_contrast_preprocessing_study.py` | Runs contrast preprocessing experiments and writes comparison summaries.                         |
| `run_repair_only_from_grid.py`        | Runs repair-only experiments from existing baseline grids.                                       |
| `list_unignored_files.py`             | Builds file lists/digests for review and archival workflows.                                     |

---

## Installation

### Requirements

Use Python 3.11+ if available. The project uses scientific Python libraries and Numba acceleration.

Required runtime libraries:

```text
numpy
scipy
numba
Pillow
matplotlib
```

Optional:

```text
scikit-image
```

### Windows PowerShell Setup

From the repository root:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install numpy scipy numba Pillow matplotlib scikit-image
```

### Verify The Source Image

Before long runs, validate the source image you will run:

```powershell
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

Backward-compatible strict default check:

```powershell
python assets/image_guard.py --path assets/input_source_image.png
```

---

## Quick Start

### Run The Main Reconstruction Pipeline

```powershell
python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical
```

Expected output location:

```text
results/iter9/
```

Typical artifacts include:

```text
grid_<board>.npy
metrics_<board>.json
visual_<board>.png
report_<board>.png
```

## Beginner Workflow

Use this order if you are new to the project.

### Step 1: Check the input image

```powershell
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

This confirms the source image exists and passes the chosen validation mode.

### Step 2: Run the main pipeline

```powershell
python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical
```

This creates a Minesweeper board attempt from the explicit source image.

### Step 3: Open the results folder

Look in:

```text
results/iter9/
```

Start with:

```text
visual_<board>.png
metrics_<board>.json
```

### Step 4: Read the key numbers

In the metrics file, focus on:

| Metric           | Beginner meaning                                                        |
| ---------------- | ----------------------------------------------------------------------- |
| `coverage`       | How much of the board the solver could reveal. Higher is better.        |
| `n_unknown`      | How many safe cells remain unrevealed. Lower is better.                 |
| `mean_abs_error` | How far the number field is from the target image. Lower is better.     |
| `mine_accuracy`  | Whether mines are correctly identified by the solver. Higher is better. |
| `solvable`       | Whether the solver considers the board logically solved enough.         |

### Step 5: Run benchmarks before trusting a change

```powershell
python run_benchmark.py
```

Do not trust a change from one seed or one board size only.

---

## Key Concepts

### Mine Grid

A 2D array where:

```text
0 = no mine
1 = mine
```

### Number Field

The Minesweeper numbers produced by the mine grid. Each safe cell gets a number from `0` to `8` based on nearby mines.

### Target Field

The image converted into number-like values. The optimizer tries to make the Minesweeper number field match this target.

### Simulated Annealing

The optimization method that repeatedly moves mines around and keeps changes that improve the result.

### Solver Coverage

The fraction of safe cells that the deterministic solver can reveal.

### `n_unknown`

The number of safe cells still unrevealed after solving. This is one of the most important metrics.

### Repair

A post-processing step that changes small parts of the mine grid to help the solver finish.

---

## Latest Campaign Finding: Repair-Only Last-100 Campaign

The latest major campaign was:

```text
line_art_robustness_campaign_2_line_art_irl_9_repair_only_last100
```

### Campaign Scope

* Source image: `line_art_irl_9.png`
* Board: `300x942`
* Cells: `282,600`
* Seeds: `11`, `22`, `33`
* Attempts: `12`
* Policy: no `sa3x_adaptive`, no SA reruns, immutable campaign 2 `global46` baselines

### Repair Variants Tested

| Variant                        | Purpose                                          |
| ------------------------------ | ------------------------------------------------ |
| `baseline_recheck`             | Re-run the near-pass baseline for comparison.    |
| `phase2_extended_only`         | Test Phase 2 repair alone.                       |
| `last100_only`                 | Test Last-100 repair alone.                      |
| `phase2_extended_then_last100` | Try Phase 2 first, then Last-100 only if needed. |

### Main Result

The baseline rechecks still had unresolved cells:

| Seed | Baseline `n_unknown` |
| ---: | -------------------: |
|   11 |                   89 |
|   22 |                   20 |
|   33 |                   37 |

All repair variants solved the board numerically:

| Variant                        | Attempts | Promoted | Max `n_unknown` |
| ------------------------------ | -------: | -------: | --------------: |
| `baseline_recheck`             |        3 |        0 |              89 |
| `phase2_extended_only`         |        3 |        3 |               0 |
| `last100_only`                 |        3 |        3 |               0 |
| `phase2_extended_then_last100` |        3 |        3 |               0 |

The final best-per-seed result was `3 / 3` promoted with `0` final unresolved cells.

### Practical Lesson

The campaign showed that this late-stage failure family was repair-resolvable without rerunning simulated annealing.

The strongest next architecture direction is:

```text
solve → diagnose unresolved failure type → route to targeted repair → measure → audit visual change
```

Instead of treating every solver stall as a generic optimization failure, the pipeline should classify the remaining unknown-cell structure and choose the cheapest targeted intervention.

### Important Visual Caveat

The campaign also recorded a `P1 background leakage` watch finding. This should be treated as a visual-risk signal, not as proof that one repair method alone caused the artifact.

Future repair work should add visual-delta evidence around each accepted repair move.

---

## Pipeline Direction

The project is currently moving toward this routing model:

```text
1. Run simulated annealing.
2. Run deterministic solver.
3. If n_unknown == 0, accept the result.
4. If unresolved cells remain, classify the failure type.
5. If sealed clusters dominate, run Phase 2 full repair.
6. If Phase 2 fails and unknown count is small, run Last-100 repair.
7. If repair still fails, mark the run as needing broader SA/adaptive rerun.
8. Emit repair logs, visual overlays, and route-decision artifacts.
```

Target future artifacts:

```text
failure_taxonomy.json
repair_route_decision.json
visual_delta_summary.json
repair_overlay_<board>.png
```

---

## Metrics Guide

| Metric           | Technical meaning                                    | Desired direction              |
| ---------------- | ---------------------------------------------------- | ------------------------------ |
| `loss`           | Weighted optimization loss.                          | Lower                          |
| `loss_per_cell`  | Loss normalized by board size.                       | Lower                          |
| `mean_abs_error` | Mean absolute error between target and number field. | Lower                          |
| `coverage`       | Fraction of safe cells revealed by solver.           | Higher                         |
| `n_unknown`      | Count of unrevealed safe cells.                      | Lower                          |
| `mine_accuracy`  | Accuracy of solver mine identification.              | Higher                         |
| `solvable`       | Solver success boolean.                              | `true`                         |
| `total_time_s`   | Runtime in seconds.                                  | Lower, if quality is preserved |

---

## Generated Artifacts to expect

| Artifact                   | Meaning                                           |
| -------------------------- | ------------------------------------------------- |
| `grid_<board>.npy`         | Binary mine grid.                                 |
| `metrics_<board>.json`     | Main machine-readable run metrics.                |
| `visual_<board>.png`       | Rendered visual reconstruction.                   |
| `report_<board>.png`       | Multi-panel diagnostic report.                    |
| `repair_checkpoint.npy`    | Intermediate repair grid checkpoint when emitted. |
| `repair_move_log.jsonl`    | Accepted/rejected repair moves.                   |
| `campaign_summary.md`      | Human-readable campaign summary.                  |
| `campaign_summary.json`    | Machine-readable campaign summary.                |
| `campaign_runs.csv`        | Per-run campaign table.                           |
| `visual_anomaly_review.md` | Visual review findings.                           |

Generated outputs should live under:

```text
results/
```

---

## Development Rules

Follow these rules when modifying the codebase.

### Reproducibility

* Use fixed seeds (11 22 33 etc)
* Record exact metrics.
* Keep generated outputs under `results/`.
* Prefer machine-readable JSON/CSV logs for experiments.

### Solver and Optimization Changes

* Must not claim improvement(s) from one seed.
* Compare median behavior across seeds.
* Check both visual fidelity and solver coverage.
* Do not trade a large coverage regression for a small loss improvement.

### Code Style

* Use PEP 8 style.
* Use 4-space indentation.
* Use `snake_case` for functions and variables.
* Use `UPPER_CASE` for constants.
* Add type hints for public functions.
* Keep Numba-heavy logic isolated in `sa.py` and `solver.py`.

---

## Benchmark Expectations

Use at least three seeds per meaningful comparison.

Important board sizes used in historical benchmarking include:

```text
200x125
250x156
250x250
```

Report at minimum:

```text
loss_per_cell
mean_abs_error
coverage
n_unknown
mine_accuracy
runtime
```

A candidate change should be treated as risky if it improves image loss but increases unresolved unknown cells or lowers solver coverage.

---

## Troubleshooting

### `Board sizing mismatch`

Cause: the source image dimensions changed, or board sizing logic changed.

Action:

```powershell
python assets/image_guard.py --path assets/input_source_image.png
```

Then inspect `board_sizing.py` and the relevant metrics file.

### `n_unknown` remains high

Cause: the solver is stuck with unresolved safe cells.

Action:

1. Inspect `metrics_<board>.json`.
2. Check `coverage` and `n_unknown`.
3. Inspect repair logs if present.
4. Run benchmark before changing repair logic.

### Visual output looks worse after repair

Cause: repair may have improved logical solvability while changing visual fidelity. Logical Solvability is a machine readable value where visual fidelity is the human element.

Action:

1. Compare `visual_<board>.png` before and after repair.
2. Check `mean_abs_error`.
3. Inspect `repair_move_log.jsonl`.
4. Prefer future visual-delta instrumentation before changing repair policy.

### Run is slow

Cause: large boards, high SA iteration counts, full solver passes, or expensive repair search.

Action:

1. Check `total_time_s` in metrics.
2. Reduce experiment scope before changing algorithm logic.
3. Use benchmarks to compare before/after behavior.

---

## Recommended Reading Order

### For Beginners

1. This `README.md`
2. `docs/project_result_summary.md`
3. `results/line_art_campaigns.md`
4. Latest `campaign_summary.md`
5. `metrics_<board>.json` from a recent run

### For Advanced Contributors

1. `AGENTS.md`
2. `core.py`
3. `sa.py`
4. `solver.py`
5. `repair.py`
6. `run_iter9.py`
7. `run_benchmark.py`
8. Latest campaign reports under `results/`

---

## Roadmap

High value next improvements:

1. Adding unresolved-cell failure taxonomy to `solver.py`.
2. Adding late stage repair routing to `pipeline.py` / `run_iter9.py`.
3. Making `run_phase2_full_repair()` emit stronger before/after visual evidence.
4. Adding `repair_overlay_<board>.png` reports.
5. Promoting the `line_art_irl_9.png` repair-only result into a regression benchmark.
6. Add visual delta gates so repair cannot silently damage image fidelity (this is controversial based off the interpretive nature of image fidelity)

