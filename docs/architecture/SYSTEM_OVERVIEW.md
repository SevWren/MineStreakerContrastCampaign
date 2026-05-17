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
        |
        v
+-------------------+
| GAMEWORKS         |
| SUBSYSTEM         |
|                   |
| gameworks/main.py |
| (interactive      |
|  Pygame game)     |
+-------------------+
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

> **Demo subsystem extracted.** `demos/iter9_visual_solver/` lives on the `demo/standalone`
> branch. Artifact contract: `demo/docs/artifact_consumption_contract.md` on that branch.

---

## Shared Artifact Contracts

The pipeline produces artifacts consumed by gameworks. The governing
schema documents for each:

| Artifact | Schema Doc | Consumer(s) |
|---|---|---|
| `grid_iter9_<board>.npy` | `docs/json_schema/metrics_iter9.schema.md` | Gameworks (`--npy` / `--image` mode) |
| `metrics_iter9_<board>.json` | `docs/json_schema/metrics_iter9.schema.md` | Benchmarking scripts |
| `repair_route_decision.json` | `docs/json_schema/repair_route_decision.schema.md` | Regression tests |
| `failure_taxonomy.json` | `docs/json_schema/failure_taxonomy.schema.md` | Analysis scripts |
| `benchmark_summary.json` | `docs/json_schema/benchmark_summary.schema.md` | External consumers |

Schema index: `docs/json_schema/JSON_OUTPUT_SCHEMA_INDEX.md`

Route state invariants (accepted-move-count rules): `docs/ROUTE_STATE_FIELD_INVARIANTS.md`

---

## What Is Intentionally NOT Shared

- **Gameworks rendering state** — `renderer.py` internal state is private. No pipeline
  module reads or writes it.
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
