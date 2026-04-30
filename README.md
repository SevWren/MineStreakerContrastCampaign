# Mine-Streaker

Mine-Streaker is a Python research codebase that reconstructs Minesweeper mine layouts from source images.
The objective is dual:
- visual fidelity to the source image
- deterministic solver reachability (low or zero unresolved safe cells)

## Current Reality (April 2026 Snapshot)
Primary workflows:
- `run_iter9.py` for single image reconstruction
- `run_benchmark.py` for benchmark matrices and regression-only checks

## Quick Start

### 1. Create environment and install dependencies

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install numpy scipy numba Pillow matplotlib scikit-image
```

### 2. Check runtime help contracts

```powershell
python run_iter9.py --help
python run_benchmark.py --help
```

### 3. Verify your image input

```powershell
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

### 4. Run a normal Iter9 pipeline

```powershell
python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical
```

### 5. Run benchmark matrix mode

```powershell
python run_benchmark.py --image assets/line_art_irl_11_v2.png --widths 300 360 420 --seeds 300 301 302 --allow-noncanonical
```

### 6. Run fixed regression mode

```powershell
python run_benchmark.py --regression-only
```

## Source Image Runtime Contract
Normal runs are CLI image driven (`--image`).

Validation model:
- default image with default manifest
- explicit image with explicit manifest
- explicit image with `--allow-noncanonical` (warning mode)

Entrypoint flags:
- `run_iter9.py`: `--image`, `--out-dir`, `--board-w`, `--seed`, `--allow-noncanonical`, `--image-manifest`, `--run-tag`
- `run_benchmark.py`: `--image`, `--widths`, `--seeds`, `--out-dir`, `--allow-noncanonical`, `--image-manifest`, `--regression-only`, `--include-regressions`

## Repository Layout

```text
.
|-- AGENTS.md
|-- README.md
|-- board_sizing.py
|-- core.py
|-- corridors.py
|-- pipeline.py
|-- repair.py
|-- report.py
|-- run_iter9.py
|-- run_benchmark.py
|-- sa.py
|-- solver.py
|-- source_config.py
|-- assets/
|-- docs/
|-- tests/
`-- results/
```

## Pipeline Summary
`run_iter9.py` and benchmark child runs use this sequence:
1. Resolve source config and validate image integrity.
2. Derive board height from source-image aspect ratio (`board_sizing.py`).
3. Build target field and zone-aware weights (`core.py`).
4. Build adaptive corridors (`corridors.py`).
5. Run coarse/fine/refine SA (`sa.py`).
6. Run deterministic solver (`solver.py`).
7. Run Phase 1 repair (`repair.py`).
8. Route late-stage unresolved failures (`pipeline.py`) through phase2/last100 logic when appropriate.
9. Render technical and explained reports (`report.py`).
10. Persist metrics/artifacts under `results/`.

## Output Artifacts
### Iter9 run directory (`results/iter9/<run_id>/`)
- `metrics_iter9_<board>.json`
- `grid_iter9_<board>.npy`
- `grid_iter9_latest.npy`
- `iter9_<board>_FINAL.png`
- `iter9_<board>_FINAL_explained.png`
- `repair_overlay_<board>.png`
- `repair_overlay_<board>_explained.png`
- `failure_taxonomy.json`
- `repair_route_decision.json`
- `visual_delta_summary.json`

### Benchmark root (`results/benchmark/<benchmark_run_id>/`)
- child dirs named `<board_width>x<board_height>_seed<seed>/`
- benchmark summaries:
  - `benchmark_summary.json`
  - `benchmark_summary.csv`
  - `benchmark_summary.md`
  - `benchmark_results.json`

## Explained vs Technical Reports
Technical PNGs are detailed audit/debug artifacts.
Explained PNGs are beginner-readable first-look artifacts and do not replace technical artifacts.

## Iter9 Image Sweep Mode
Use image-sweep mode to run Iter9 across discovered images in one batch.

```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --seed 11 --allow-noncanonical --out-root results/iter9_manual_explained_validation --max-images 2
```

Core sweep flags:
- `--image-dir` activates sweep mode.
- `--image-glob` selects files (default `*.png`).
- `--recursive` includes nested folders.
- `--out-root` sets the batch root. If omitted, output defaults to `results/iter9/<batch_id>/`.
- `--continue-on-error` keeps processing after failed child runs.
- `--skip-existing` skips children when expected metrics already exist.
- `--max-images` limits discovered files after sorting.

Batch root outputs:
- `iter9_image_sweep_summary.json`
- `iter9_image_sweep_summary.csv`
- `iter9_image_sweep_summary.md`

Per-child metrics behavior:
- Single-image runs include top-level `source_image_validation` and omit `batch_context`.
- Sweep child runs include top-level `source_image_validation` and populated `batch_context`.

Required explained labels include:
- `Target value: 0 background -> 8 strongest line`
- `Generated number: 0 no nearby mines -> 8 surrounded`
- `Difference: 0 match -> 4+ large mismatch`
- `Visual change: negative better -> positive worse`

Explained optimization chart must use:
- title: `Optimizer progress: lower is better`
- x-axis text including `Optimizer work, in millions of attempted mine changes` and `1 plotted point = 50,000 attempted changes`
- y-axis: `Match error score (lower is better)`

Technical report wording remains:
- `Loss curve (log)`
- `x50k iters`
- `Weighted loss`

## Tests and Validation
Default test suite:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Contract-focused tests include:
- `tests/test_source_image_cli_contract.py`
- `tests/test_benchmark_layout.py`
- `tests/test_report_explanations.py`
- `tests/test_repair_route_decision.py`
- `tests/test_route_artifact_metadata.py`
- `tests/test_solver_failure_taxonomy.py`

## Contributor Rules
- Keep generated artifacts under `results/`.
- Keep ownership boundaries:
  - `solver.py`: unresolved-cell classification
  - `pipeline.py`: route selection and route artifacts
  - `repair.py`: repair mutations and move logs
  - `report.py`: visual proof artifacts
  - `sa.py`: optimization kernel only, no repair routing logic

## Active Documentation
Use `docs/DOCS_INDEX.md` to determine active vs archived docs before editing.
