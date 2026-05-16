# System Overview

## Last Updated: 2026-05-13

This document describes the three top-level subsystems of MineStreaker and how they interact.
For session-level architectural decisions and known technical debt, see `repository-memory.md`
in this directory.

---

## Subsystem Map

```
Source Image (assets/*.png)
        |
        v
+-----------------------------------------------+
|         PIPELINE SUBSYSTEM                   |
|  run_iter9.py / run_benchmark.py              |
|                                               |
|  source_config -> core -> sa -> solver        |
|     -> repair -> pipeline -> report           |
+-----------------------------------------------+
        |
        |  Shared Artifacts (results/iter9/<run_id>/)
        |  - grid_iter9_<board>.npy         (board layout)
        |  - metrics_iter9_<board>.json     (full metrics)
        |  - repair_route_decision.json     (route state)
        |  - visual_delta_summary.json      (delta report)
        |  - failure_taxonomy.json          (solver taxonomy)
        |  - *.png (technical + explained reports)
        |
        +-------------------+-------------------+
        |                                       |
        v                                       v
+-------------------+             +---------------------------+
| GAMEWORKS         |             | DEMO SUBSYSTEM            |
| SUBSYSTEM         |             | demos/iter9_visual_solver/|
|                   |             |                           |
| gameworks/main.py |             | Reads pipeline artifacts  |
| (interactive      |             | and replays solver events |
|  Pygame game)     |             | frame-by-frame visually   |
+-------------------+             +---------------------------+
```

---

## Subsystem Responsibilities

### Pipeline (`run_iter9.py`, `run_benchmark.py`, and root modules)

The pipeline is the engineering reference model for the entire codebase. Its responsibilities:

- Accept a source image and derive board dimensions from its aspect ratio
- Run Simulated Annealing (SA) to optimize mine placement for visual fidelity
- Run the deterministic CSP solver to identify unresolved safe cells
- Apply staged repair (Phase 1, Phase 2 Full, Last100) to resolve clusters
- Determine the final route state via the 4-field model
- Render technical and explained report PNGs
- Persist all artifacts under `results/`

The pipeline defines and fully implements all P1–P12 design patterns (see
`gameworks/docs/DESIGN_PATTERNS.md`). It is the reference implementation that gameworks
is expected to converge toward over time.

**Entry points:**
| Script | Purpose |
|---|---|
| `run_iter9.py` | Single-image or image-sweep batch run |
| `run_benchmark.py` | Benchmark matrix (multiple widths × seeds) + regression checks |

**Architecture detail:** `docs/architecture/PIPELINE_ARCHITECTURE.md`

---

### Gameworks (`gameworks/`)

An interactive Pygame-based Minesweeper game that can consume pipeline output boards. Its
responsibilities:

- Provide interactive Minesweeper gameplay (reveal, flag, chord, zoom, pan)
- Support three board modes: `random` (RNG), `npy` (pre-built board file), `image` (invoke pipeline at launch)
- Render all game state via `renderer.py` — never modifying engine state
- Track scoring, streaks, and session timer via `GameEngine`

The gameworks package is **independent of the pipeline** at runtime except for the optional
`image` mode, which invokes `load_board_from_pipeline()` in `engine.py` via a guarded
dynamic import. This function is the **sole call site** for image-based board construction
within gameworks — no other gameworks module may import pipeline modules directly. If
SA/solver tuning parameters change in `run_iter9.py`, the corresponding defaults in
`load_board_from_pipeline()` must be updated in the same commit to prevent silent quality
divergence between the interactive game and the standalone pipeline.
Gameworks rendering state is private and never written back to pipeline artifacts.

**Entry point:** `python -m gameworks.main [--random|--npy|--image] [flags]`

**Architecture detail:** `gameworks/docs/ARCHITECTURE.md`

---

### Demo (`demos/iter9_visual_solver/`)

A standalone visual playback package that reads pipeline artifacts and replays the solver
decision sequence frame-by-frame. Its responsibilities:

- Load solver event trace JSON artifacts produced by the pipeline
- Drive a Pygame window to render each solver event over the source image
- Enforce playback speed contracts (see `demo/docs/playback_speed_contract.md`)
- Produce no output artifacts — read-only consumer of pipeline results

The demo does **not** write back to pipeline artifacts and does **not** depend on gameworks.
It has its own test suite under `tests/demo/` (~60 files) and its own contract docs under
`demo/docs/` (21 files).

**Entry point:** `python -m demos.iter9_visual_solver --config configs/demo/<config>.json`

**Contracts and schema:** `demo/docs/`

---

## Shared Artifact Contracts

The pipeline produces artifacts consumed by both gameworks and the demo. The governing
schema documents for each:

| Artifact | Schema Doc | Consumer(s) |
|---|---|---|
| `grid_iter9_<board>.npy` | `docs/json_schema/metrics_iter9.schema.md` | Gameworks (`--npy` / `--image` mode) |
| `metrics_iter9_<board>.json` | `docs/json_schema/metrics_iter9.schema.md` | Demo, benchmarking scripts |
| `repair_route_decision.json` | `docs/json_schema/repair_route_decision.schema.md` | Demo, regression tests |
| `visual_delta_summary.json` | `docs/json_schema/visual_delta_summary.schema.md` | Demo |
| `failure_taxonomy.json` | `docs/json_schema/failure_taxonomy.schema.md` | Demo, analysis scripts |
| `benchmark_summary.json` | `docs/json_schema/benchmark_summary.schema.md` | External consumers |

Schema index: `docs/json_schema/JSON_OUTPUT_SCHEMA_INDEX.md`

Route state invariants (accepted-move-count rules): `docs/ROUTE_STATE_FIELD_INVARIANTS.md`

---

## What Is Intentionally NOT Shared

- **Gameworks rendering state** — `renderer.py` internal state is private. No pipeline
  module reads or writes it.
- **Demo event scheduler state** — internal to `demos/iter9_visual_solver/`. Not exposed
  to pipeline or gameworks.
- **Gameworks game-save `.npy`** — uses a different format than pipeline `.npy` boards
  (game-save: `-1`=mine, `0–8`=neighbour count; pipeline: `0`=safe, `1`=mine). The formats
  are distinguished by the auto-detection logic in `load_board_from_npy()`.

---

## Entry Points Reference

| Entry Point | Module | Description |
|---|---|---|
| `python run_iter9.py` | Pipeline | Single image or image-sweep batch |
| `python run_benchmark.py` | Pipeline | Benchmark matrix + regression |
| `python -m gameworks.main` | Gameworks | Interactive Minesweeper game |
| `python -m demos.iter9_visual_solver` | Demo | Visual solver playback |
| `powershell .\demo\run_iter9_visual_solver_demo_prompted.ps1` | Demo | Prompted demo launcher (Windows) |
