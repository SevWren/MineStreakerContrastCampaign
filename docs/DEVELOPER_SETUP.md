# Developer Setup

This document covers project-wide setup for the MineStreaker pipeline and gameworks
packages. For gameworks-specific developer guidance, see `gameworks/docs/DEVELOPER_GUIDE.md`.
For demo-specific setup, see `demo/docs/`.

---

## Requirements

**Python version:** 3.10, 3.11, or 3.12 recommended.

Python 3.13+ is **not yet supported** for pre-built `pygame` wheels on Windows. If you
must use 3.13/3.14, install pygame separately first:
```bash
pip install pygame --pre
```

---

## Installation

```bash
# Clone the working-changes branch
git clone --branch working-changes https://github.com/SevWren/MineStreakerContrastCampaign.git
cd MineStreakerContrastCampaign

# Install all dependencies
pip install -r requirements.txt
```

`requirements.txt` installs: `numpy`, `scipy`, `Pillow`, `matplotlib`, `scikit-image`,
`numba`, `pygame`, `pytest`, `pyflakes`.

---

## First-Run Note: Numba JIT Compilation

The SA kernel (`sa.py`) uses Numba JIT compilation. On the **first pipeline run** after
install, Numba compiles the kernel — this takes 10–30 seconds and is unavoidable. Subsequent
runs use the cached compiled kernel and start normally.

---

## Running the Pipeline

**Single image run:**
```bash
python run_iter9.py --image assets/line_art_a2_upscaled.png --board-w 300 --seed 11 --allow-noncanonical
```

**Image-sweep batch (all PNGs in assets/):**
```bash
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 300 --seed 11 \
    --allow-noncanonical --run-tag "smoke_w300_s11" \
    --out-root "results/iter9/sweep_smoke_w300_s11" --max-images 2
```

**Benchmark matrix:**
```bash
python run_benchmark.py --image assets/line_art_a2_upscaled.png --widths 300 360 --seeds 11 12
```

**Regression check only:**
```bash
python run_benchmark.py --regression-only
```

All output artifacts are written under `results/`. Do not generate root-level output files.

---

## Running the Game

```bash
# Random board (easy)
python -m gameworks.main --random --easy

# Load a pre-built pipeline board
python -m gameworks.main --load results/iter9/<run_id>/grid_iter9_300x300.npy

# Image mode (runs full pipeline at launch — slow, requires Numba warmup)
python -m gameworks.main --image assets/line_art_a2_upscaled.png --board-w 300
```

See `gameworks/docs/README.md` for full controls and launch modes.

---

## Running the Demo

```bash
python -m demos.iter9_visual_solver --config configs/demo/<config_file>.json
```

Or on Windows with the prompted launcher:
```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\demo\run_iter9_visual_solver_demo_prompted.ps1
```

---

## Running All Tests

See `docs/TESTING_STRATEGY.md` for the full test strategy. Quick-start commands:

```bash
# Pipeline contract tests
python -m unittest discover -s tests -p "test_*.py"

# Full gameworks test suite (headless — no display required)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v

# Demo tests
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"

# Lint check
pyflakes gameworks/ gameworks/tests/
```

---

## Project Structure Orientation

```
MineStreakerContrastCampaign/
|-- run_iter9.py          # Pipeline entry point (single / sweep)
|-- run_benchmark.py      # Benchmark entry point
|-- pipeline.py           # Late-stage routing + artifact writes
|-- core.py               # Pure math primitives (weights, image load)
|-- sa.py                 # SA kernel (Numba JIT)
|-- solver.py             # CSP solver + cluster classification
|-- repair.py             # Staged repair
|-- report.py             # Report rendering (figsize=(24,15.5) for explained)
|-- source_config.py      # Source image config + validation
|-- board_sizing.py       # Board dimension derivation
|-- corridors.py          # Corridor construction
|-- assets/               # Source images
|-- configs/              # Run and demo config JSON files
|   `-- demo/
|-- demos/
|   `-- iter9_visual_solver/  # Demo package
|-- demo/
|   `-- docs/                 # Demo contracts (21 files)
|-- docs/                     # Pipeline and governance docs
|   |-- architecture/         # System and pipeline architecture
|   |-- json_schema/          # Output artifact schemas
|   `-- DOCS_INDEX.md         # Active vs archived doc index
|-- gameworks/                # Interactive Pygame game
|   |-- engine.py
|   |-- renderer.py
|   |-- main.py
|   |-- docs/                 # Gameworks documentation (17 files)
|   `-- tests/                # Gameworks test suite
|-- tests/                    # Pipeline contract tests + legacy regression guards
`-- results/                  # All generated artifacts (git-ignored)
```

### Key relationships

- `core.py` + `sa.py` are pure (no I/O, no Pygame). Safe to import anywhere.
- `pipeline.py` orchestrates repair routing; it does NOT render reports.
- `report.py` renders reports; it does NOT write route decisions.
- `run_iter9.py` is the only module that should perform full artifact persistence.
- `gameworks/` does not import from `pipeline.py`, `sa.py`, or `solver.py` directly.

---

## configs/ Directory

The `configs/` directory holds JSON files for reproducible demo runs. To create a new
demo config, copy an existing file from `configs/demo/` and adjust the `image_path`,
`board_w`, and `seed` fields. Schema: `demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json`.

---

## Generated Artifacts (`results/`)

All generated output goes under `results/`. The directory is git-ignored. Structure:

```
results/
|-- iter9/
|   |-- <run_id>/          # Single-image run output
|   |   |-- metrics_iter9_<board>.json
|   |   |-- grid_iter9_<board>.npy
|   |   |-- repair_route_decision.json
|   |   |-- visual_delta_summary.json
|   |   |-- failure_taxonomy.json
|   |   `-- *.png
|   `-- <batch_id>/        # Image-sweep batch root
|       |-- iter9_image_sweep_summary.*
|       `-- <child_id>/    # One child per image
`-- benchmark/
    `-- <benchmark_run_id>/
        |-- benchmark_summary.*
        `-- <child_dirs>/
```

To clean runs: delete the relevant subdirectory under `results/`. There is no automated
cleanup script — manual deletion is the current approach.

---

## Further Reading

- Architecture: `docs/architecture/SYSTEM_OVERVIEW.md`, `docs/architecture/PIPELINE_ARCHITECTURE.md`
- Testing strategy: `docs/TESTING_STRATEGY.md`
- Contribution guidelines: `CONTRIBUTING.md`
- Gameworks developer guide: `gameworks/docs/DEVELOPER_GUIDE.md`
- Demo contracts: `demo/docs/`
- Agent instructions: `CLAUDE.md`, `AGENTS.md`
