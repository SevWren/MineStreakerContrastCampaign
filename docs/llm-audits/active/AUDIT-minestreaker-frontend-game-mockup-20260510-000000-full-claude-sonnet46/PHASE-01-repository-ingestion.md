# PHASE 01 — Repository Ingestion
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. Repository Identity

| Field | Value |
|---|---|
| Repository | SevWren/MineStreakerContrastCampaign |
| Branch | frontend-game-mockup |
| Commit | c475dd267958bc92db6402a62dd368a42e69a7f0 |
| Audit Date | 2026-05-10 |
| Primary Language | Python 3 |
| Secondary Language | None (TypeScript specs exist but no implementation) |

## 2. Subsystem Inventory

### 2.1 Production Pipeline (`run_iter9.py` + core modules)
The primary research pipeline reconstructs Minesweeper mine layouts from source images using Simulated Annealing. This is a mature, heavily tested subsystem.

- `run_iter9.py` — main entrypoint, 1726 LOC, handles single-run and sweep modes
- `core.py` — image loading, N-field computation, zone-aware weights (354 LOC)
- `sa.py` — Numba-compiled SA kernel: coarse/fine/refine stages (205 LOC)
- `solver.py` — Numba-compiled deterministic CSP solver (566 LOC)
- `repair.py` — Phase1/Phase2/Last100 mine-removal repair (752 LOC)
- `pipeline.py` — repair routing, late-stage failure handling (415 LOC)
- `report.py` — matplotlib PNG artifact rendering (845 LOC)
- `corridors.py` — MST-based mine-free corridor generation (158 LOC)
- `board_sizing.py` — aspect-ratio-based board dimension derivation
- `source_config.py` — SHA256-based source image config resolution
- `assets/image_guard.py` — mandatory pre-flight image integrity verification

### 2.2 Gameworks Package (`gameworks/`) — PRIMARY AUDIT FOCUS
The interactive Minesweeper game that consumes `run_iter9.py` pipeline output.

- `gameworks/engine.py` — pure game logic, Board + GameEngine (452 LOC estimated)
- `gameworks/renderer.py` — Pygame full-screen renderer (1041 LOC)
- `gameworks/main.py` — CLI entrypoint + game loop state machine (298 LOC)

### 2.3 Visual Solver Demo (`demos/iter9_visual_solver/`)
A standalone, well-tested Pygame playback demo that replays solver event traces.
Separate from `gameworks/`. Has 30+ dedicated tests. Contractually governed by `demo/docs/`.

### 2.4 Pre-Built Pipeline Boards (`results/iter9/`) — NEW (commit ca3eee4)

Three committed pipeline output boards, intended as pre-computed inputs for gameworks `--npy` mode:

| Board | Shape | Mines | Density | Source Image |
|---|---|---|---|---|
| `grid_iter9_300x370.npy` | (370,300) | 15,574 | 14.0% | `assets/input_source_image.png` ✓ |
| `grid_iter9_300x215.npy` | (215,300) | 18,529 | 28.7% | `line_art_irl_18v2` ✗ NOT in assets/ |
| `grid_iter9_600x429.npy` | (429,600) | 63,060 | 24.5% | `line_art_irl_18v2` ✗ NOT in assets/ |

**Critical format issue**: All boards are `int8` with values `{0, 1}` only (pipeline format: `0=safe, 1=mine`). `load_board_from_npy()` uses `grid[y,x] < 0` to detect mines. No negative values exist in these boards → all boards load with **zero mines**. See FIND-ARCH-CRITICAL-f006a.

### 2.5 Test Suite (`tests/`)
- 12 root-level tests targeting pipeline contracts
- 30+ demo-specific tests for `demos/iter9_visual_solver/`
- **Zero tests for `gameworks/`**

## 3. Dependency Inventory

### 3.1 Runtime Python Dependencies
| Package | Usage | Version Pinned? |
|---|---|---|
| `numpy` | Core arrays throughout all modules | No |
| `scipy` | `convolve`, `ndimage.label`, sparse graph MST | No |
| `numba` | JIT compilation of SA kernel and solver | No |
| `Pillow` (PIL) | Image loading, pixel access | No |
| `matplotlib` | Report PNG rendering | No |
| `scikit-image` | Image processing in pipeline | No |
| `pygame` | Minesweeper game rendering + input | No |

### 3.2 Dependency Management Files
- **No `requirements.txt`** exists
- **No `pyproject.toml`** exists
- **No `setup.py`** or `setup.cfg` exists
- README documents manual pip install only

### 3.3 Build Systems
None. Pure Python, no build step.

## 4. Environment Assumptions

- Python 3.10+ (uses `match`-adjacent patterns, type unions with `|`)
- Numba JIT compilation at first run (warmup required before game starts)
- Pygame display available (requires X11 or windowing system)
- Working directory must be repository root for relative imports to resolve
- `assets/` directory must be present and populated for default image mode

## 5. Configuration Files

| File | Purpose |
|---|---|
| `configs/demo/iter9_visual_solver_demo.default.json` | Demo runtime config schema |
| `assets/SOURCE_IMAGE_HASH.json` | Canonical image integrity manifest (referenced, not confirmed present) |

## 6. Key Observations

1. **No requirements file**: Reproducible environment cannot be achieved without manual documentation knowledge.
2. **gameworks/ has no tests**: The game package is entirely untested.
3. **Frontend spec exists but is unimplemented**: `docs/frontend_spec/` describes a React 18 + TypeScript + Canvas 2D application; no such code exists in the repo.
4. **DENSITY/BORDER/SA constants in run_iter9.py**: 30+ pipeline tuning constants are defined as module-level globals with commented-out alternatives, creating tuning debt.
