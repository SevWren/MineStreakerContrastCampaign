# GEMINI.md - Mine-Streaker Project Context

## Project Overview

Mine-Streaker is a Python research codebase dedicated to reconstructing Minesweeper mine layouts from source images. The goal is to achieve high visual fidelity to the source image while ensuring deterministic solver reachability (minimizing unresolved safe cells).

### Core Technologies

- **Language:** Python 3.x
- **Numerical/Scientific:** NumPy, SciPy, Numba (for high-performance kernels), scikit-image
- **Image Processing:** Pillow (PIL)
- **Visualization/Reporting:** Matplotlib
- **Demo/UI:** Pygame (specifically `pygame-ce` is recommended for newer Python versions)
- **Configuration/Validation:** Pydantic (for demo configs)

## Project Architecture

### Root Directory (Core Logic)

- `run_iter9.py`: Primary entrypoint for single-image or batch-image (sweep mode) reconstruction.
- `run_benchmark.py`: Entrypoint for benchmark matrices and fixed regression checks.
- `pipeline.py`: Orchestrates the full reconstruction sequence, including late-stage repair routing.
- `core.py`: Foundational logic for board weights, T-compression, and image loading.
- `sa.py`: Simulated Annealing (SA) optimization kernel.
- `solver.py`: Deterministic Minesweeper solver and unresolved-cell classification.
- `repair.py`: Multi-phase repair logic (Phase 1, Phase 2 Full, Last 100).
- `report.py`: Generation of technical and "explained" (beginner-readable) visual reports.
- `corridors.py`: Building adaptive corridors for the optimization process.
- `board_sizing.py`: Board dimension derivation from aspect ratios.
- `source_config.py`: Source image configuration and validation.

### Specialized Directories

- `assets/`: Source images and `image_guard.py` for integrity verification.
- `demo/` & `demos/`: Contains the Iter9 Visual Solver Demo, including its own documentation, contracts, and runtime package.
- `results/`: **All generated artifacts must be stored here.**
- `tests/`: Unit and contract-focused tests.
- `tests/demo/`: Demo-specific tests.
- `docs/`: Active and archived project documentation.

## Development Workflows

### 1. Primary Execution Commands

- **Single Image Run:** `python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical`
- **Batch Image Sweep:** `python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 300 --seed 11 --allow-noncanonical`
- **Benchmark Run:** `python run_benchmark.py --image <path> --widths 300 360 --seeds 300 301`
- **Regression Check:** `python run_benchmark.py --regression-only`
- **Visual Demo:** `powershell -NoProfile -ExecutionPolicy Bypass -File .\demo\run_iter9_visual_solver_demo_prompted.ps1`

### 2. Testing

```powershell
# Full suite
python -m unittest discover -s tests -p "test_*.py"

# Demo-specific tests
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
```

## Engineering Standards & Conventions

### General Rules

- **Artifact Ownership:** Never generate ad-hoc root-level output files. Keep everything under `results/`.
- **Module Boundaries:**
  - `solver.py`: Classification of unresolved cells.
  - `pipeline.py`: Route selection and route artifacts.
  - `repair.py`: Repair mutations and move logs.
  - `report.py`: Visual proof artifacts.
  - `sa.py`: Optimization kernel only (no repair logic).
- **Coding Style:** PEP 8, 4-space indent, type hints for public functions, `snake_case` for variables/functions.
- **Safety:** Use atomic output writes (`*.tmp` then `os.replace`).
- **Route State Invariants:** All repair route artifacts must satisfy the accepted-move-count invariants defined in `docs/ROUTE_STATE_FIELD_INVARIANTS.md`. This is the binding contract for the 4-field route-state model (`phase1_route`, `phase2_route`, `phase2_repair_status`, `route_resolution_status`).
- **Numba:** Keep kernels isolated and deterministic.

### Iter9 Visual Solver Demo (Strict Contracts)

Work touching the demo (`demo/`, `demos/iter9_visual_solver/`, etc.) must strictly adhere to the contracts in `demo/docs/`.

- **Playback Speed SSOT:** `demo/docs/playback_speed_contract.md` is the binding source of truth for all playback/speed/scheduling logic.
- **TDD Requirement:** Demo work must be TDD-first. Add/update failing tests before implementation.
- **Pygame/Pydantic:** Pygame is restricted to rendering modules; Pydantic to config modules.

## Agent Guidelines

- **Instruction Priority:** User instructions > `AGENTS.md` > `GEMINI.md` > Default System Prompt.
- **Source Image Contract:** Validation occurs after argument parsing, never at import time.
- **Image Sweep:** Prefer native `--image-dir` mode over shell loops for batch processing.
- **Explained Reports:** These are user friendly additive first-look artifacts; they do not replace technical reports. Maintain specific wording and layout as defined in `report.py` and `AGENTS.md`.
