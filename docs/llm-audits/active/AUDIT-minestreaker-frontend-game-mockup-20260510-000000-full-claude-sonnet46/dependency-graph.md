# Dependency Graph
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Import Graph (runtime modules)

```
run_iter9.py
├── core.py
│   └── (numpy, scipy, PIL)
├── sa.py
│   ├── core.py (compute_N)
│   └── (numpy, numba)
├── solver.py
│   ├── core.py (compute_N)
│   └── (numpy, numba, scipy)
├── repair.py
│   ├── core.py (compute_N, assert_board_valid)
│   ├── solver.py (SAFE, UNKNOWN, solve_board)
│   └── (numpy, scipy, concurrent.futures)
├── pipeline.py
│   ├── solver.py
│   ├── repair.py
│   └── (numpy)
├── corridors.py
│   ├── solver.py (SAFE, UNKNOWN) [inside analyze_* only]
│   └── (numpy, scipy.sparse, scipy.ndimage)
├── report.py
│   └── (numpy, matplotlib, PIL)
├── board_sizing.py
│   └── (PIL)
├── source_config.py
│   └── (hashlib, pathlib)
└── assets/image_guard.py
    └── (numpy, PIL, hashlib, json)

gameworks/engine.py
├── [runtime import] core.py
├── [runtime import] sa.py          ← SIGNATURE MISMATCH: compile_sa_kernel()
├── [runtime import] corridors.py
├── [runtime import] repair.py      ← SIGNATURE MISMATCH: run_phase1_repair()
├── [runtime import] board_sizing.py
└── (numpy, pathlib)

gameworks/renderer.py
├── gameworks/engine.py (Board, CellState, GameEngine, MoveResult)
└── (pygame, math, time)

gameworks/main.py
├── gameworks/engine.py
├── gameworks/renderer.py (Renderer)
│   └── [inline import] gameworks/renderer.AnimationCascade
├── (argparse, pygame, numpy, time, pathlib)
└── [runtime import] gameworks/engine (for difficulty preset)

demos/iter9_visual_solver/
├── [NO dependency on gameworks/]
├── [NO dependency on run_iter9.py at import time]
└── [Reads run_iter9.py OUTPUT ARTIFACTS via io/ modules]

results/iter9/*/grid_iter9_*.npy   ← pipeline output, int8 {0,1} encoding
    └── gameworks/engine.py::load_board_from_npy()
        BROKEN: expects int8 {-1, 0-8} encoding → mines undetected (FIND-ARCH-CRITICAL-f006a)
```

## Coupling Matrix

| Module | Couples To | Coupling Type |
|---|---|---|
| `gameworks/engine.py` | `sa.py`, `repair.py`, `corridors.py`, `core.py`, `board_sizing.py` | Dynamic runtime import inside try/except |
| `gameworks/main.py` | `gameworks/engine.py`, `gameworks/renderer.py` | Static import (with fallback) |
| `gameworks/renderer.py` | `gameworks/engine.py` | Static import (with fallback) |
| `run_iter9.py` | All root modules | Static import |
| `repair.py` | `core.py`, `solver.py` | Static import |
| `pipeline.py` | `solver.py`, `repair.py` | Static import |
| `demos/iter9_visual_solver/` | None of the above | Artifact-based (reads JSON/NPY output) |

## Critical Coupling Issues

### 1. gameworks/engine.py → sa.py: Signature Mismatch
- **File**: `gameworks/engine.py`, function `load_board_from_pipeline`, line ~210
- **Call**: `compile_sa_kernel(board_w, board_h, seed)` — 3 arguments
- **Actual signature** in `sa.py` line 73: `compile_sa_kernel()` — 0 arguments
- **Impact**: `TypeError` at runtime when `--image` mode is used in gameworks

### 2. gameworks/engine.py → repair.py: Signature Mismatch
- **File**: `gameworks/engine.py`, function `load_board_from_pipeline`, line ~245
- **Call**: `run_phase1_repair(grid, target, weights, forbidden, _RouteCfg(), seed)`
- **Actual signature**: `run_phase1_repair(grid, target, weights, forbidden, time_budget_s=90.0, max_rounds=300, ...)`
- **Impact**: `_RouteCfg()` object passed as `time_budget_s` float; `seed` (int) passed as `max_rounds`
- **Impact**: `TypeError` or incorrect repair behavior at runtime

### 3. gameworks/main.py: Missing Constants (FPS, TILE)
- **File**: `gameworks/main.py` line ~237: `self._renderer._clock.tick(FPS)`
- `FPS` is defined in `gameworks/renderer.py` but **not imported** into `main.py`
- **Impact**: `NameError: name 'FPS' is not defined` at runtime
