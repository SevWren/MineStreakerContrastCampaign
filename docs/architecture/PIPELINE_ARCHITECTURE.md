# Pipeline Architecture

## Last Updated: 2026-05-13

This document describes the internal architecture of the MineStreaker reconstruction
pipeline — the sequence of stages, the modules responsible for each, and the artifacts
produced. For the broader system context (pipeline + gameworks + demo), see
`docs/architecture/SYSTEM_OVERVIEW.md`.

---

## Pipeline Stages

The pipeline runs in this fixed sequence, each stage feeding into the next:

```
1. Source Config Resolution
   source_config.py
        |
        v
2. Board Sizing
   board_sizing.py
        |
        v
3. Image Loading + Weight Construction
   core.py
        |
        v
4. Adaptive Corridor Construction
   corridors.py
        |
        v
5. Simulated Annealing Optimization
   sa.py (Numba JIT kernel)
        |
        v
6. CSP Solver + Cluster Classification
   solver.py
        |
        v
7. Phase 1 Repair
   repair.py
        |
        v
8. Late-Stage Failure Routing (Phase 2 / Last100)
   pipeline.py
        |
        v
9. Report Generation
   report.py
        |
        v
10. Artifact Persistence
    run_iter9.py (orchestrator)
```

---

## Module-to-Stage Mapping

| Module | Stage | Responsibility |
|---|---|---|
| `source_config.py` | Stage 1 | Resolve and validate the source image contract. Produces `SourceImageConfig` (frozen dataclass). Computes SHA256 for integrity. |
| `board_sizing.py` | Stage 2 | Derive board height from image aspect ratio and requested width. |
| `core.py` | Stage 3 | Pure weight and board math primitives: `compute_zone_aware_weights()`, T-compression, image loading. No I/O. |
| `corridors.py` | Stage 4 | Build adaptive corridor masks that guide SA placement. |
| `sa.py` | Stage 5 | Numba-JIT SA kernel and runner. Runs coarse/fine/refine passes. First run requires JIT compilation (10–30 s). |
| `solver.py` | Stage 6 | Deterministic CSP solver. Classifies each unresolved cell cluster. Produces `SolveResult`. |
| `repair.py` | Stage 7 | Staged repair: Phase 1 (cluster sealing), Phase 2 Full (full board repair), Last100 (100-cell budget repair). Produces `Phase1RepairResult`, etc. |
| `pipeline.py` | Stage 8 | Route late-stage failures through phase2/last100 logic. Determines the 4-field route state. Writes repair route artifacts atomically. |
| `report.py` | Stage 9 | Renders technical PNG and explained PNG reports. `figsize=(24, 15.5)` for explained reports (contract: `docs/explained_report_artifact_contract.md`). |
| `run_iter9.py` | Orchestrator | Entry point. CLI argument parsing, I/O, all stage invocations, artifact persistence under `results/`. Defines `SCHEMA_VERSION`. |

**Pipeline consumers (board construction):**

Two callers invoke pipeline stages to construct boards and must stay in sync on
SA/solver tuning parameters:

| Caller | Purpose | Output |
|---|---|---|
| `run_iter9.py` | Full pipeline — image → all artifacts | Board + `results/` artifacts |
| `engine.py::load_board_from_pipeline()` | Board-only for gameworks `image` mode | `BoardLoadResult` only, no file artifacts |

When tuning constants change in `run_iter9.py` (e.g. `T_COARSE`, `DENSITY`, `SEAL_THR`),
update the defaults in `load_board_from_pipeline()` in the same commit.

---

## Route State Machine

The pipeline determines a final route state using four fields. These fields are the
binding contract for all repair route artifacts:

| Field | Values | Meaning |
|---|---|---|
| `phase1_route` | `"phase1_clean"` \| `"phase1_partial"` \| `"phase1_unresolved"` | Outcome of Phase 1 repair |
| `phase2_route` | `"phase2_full_repair"` \| `"phase2_partial"` \| `"phase2_skipped"` \| `"phase2_unresolved"` | Outcome of Phase 2 repair (if triggered) |
| `phase2_repair_status` | `"not_attempted"` \| `"success"` \| `"partial"` \| `"failed"` | Repair execution status |
| `route_resolution_status` | `"resolved"` \| `"partial"` \| `"unresolved"` | Final board resolution state |

**Invariant rules:** `docs/ROUTE_STATE_FIELD_INVARIANTS.md` — includes the accepted-move-count
constraints that must hold for Phase 2 and Last100 repairs.

---

## Artifact Output Map

All artifacts are written to `results/iter9/<run_id>/` for single runs, or
`results/iter9/<batch_id>/<child_id>/` for image-sweep children.

| Artifact | Produced By | Schema Doc |
|---|---|---|
| `grid_iter9_<board>.npy` | `run_iter9.py` | `docs/json_schema/metrics_iter9.schema.md` |
| `grid_iter9_latest.npy` | `run_iter9.py` | (symlink/copy to latest run) |
| `metrics_iter9_<board>.json` | `run_iter9.py` | `docs/json_schema/metrics_iter9.schema.md` |
| `repair_route_decision.json` | `pipeline.py` | `docs/json_schema/repair_route_decision.schema.md` |
| `visual_delta_summary.json` | `pipeline.py` | `docs/json_schema/visual_delta_summary.schema.md` |
| `failure_taxonomy.json` | `solver.py` / `pipeline.py` | `docs/json_schema/failure_taxonomy.schema.md` |
| `iter9_<board>_FINAL.png` | `report.py` | Technical report |
| `iter9_<board>_FINAL_explained.png` | `report.py` | Explained (beginner-readable) report |
| `repair_overlay_<board>.png` | `report.py` | Repair overlay (technical) |
| `repair_overlay_<board>_explained.png` | `report.py` | Repair overlay (explained) |

**Batch-level artifacts** (image-sweep runs, written to `results/iter9/<batch_id>/`):
- `iter9_image_sweep_summary.json`
- `iter9_image_sweep_summary.csv`
- `iter9_image_sweep_summary.md`

**Schema index:** `docs/json_schema/JSON_OUTPUT_SCHEMA_INDEX.md`

---

## Config Injection Points

### `configs/` Directory

The `configs/` directory holds JSON config files for reproducible runs. Used primarily
by `source_config.py` for image manifest validation.
Demo configs are in the `demo/standalone` branch under `configs/demo/`.

### `source_config.py` Config Model

`SourceImageConfig` (frozen dataclass) is the primary config object flowing through the
pipeline. It is resolved from CLI arguments at startup and is immutable for the duration
of a run. Fields include: `image_path`, `board_w`, `seed`, `sha256`, and validation flags.

### Schema Version

`run_iter9.py` defines:
```python
SCHEMA_VERSION = "metrics.v2.source_image_runtime_contract"
```
This string is embedded in every output JSON artifact. Downstream consumers can gate on
this version string to detect artifacts from older pipeline versions.

---

## Key Design Constraints

### Accepted-Move-Count Invariant
All Phase 2 and Last100 repair results must satisfy accepted-move-count invariants. See
`docs/ROUTE_STATE_FIELD_INVARIANTS.md` for the exact rules.

### Explained Report Layout
The explained report figure uses `figsize=(24, 15.5)` — this is the binding value per
`docs/explained_report_artifact_contract.md` and `report.py:535`. Do not change without
updating both.

### Image-Sweep vs Single-Image
- Single-image mode: CLI flag `--image <path>`
- Image-sweep mode: CLI flag `--image-dir <dir>` with optional `--image-glob`
- Never use a shell loop over single-image runs for batches that sweep mode can express.

### Atomic File Writes
All artifact writes use `os.replace()` via a `.tmp` intermediate (P8 pattern). Direct
writes are forbidden for any user-facing output file.

---

## Design Patterns in Use

The pipeline is the **reference implementation** for all P1–P12 design patterns documented
in `gameworks/docs/DESIGN_PATTERNS.md`. All 12 patterns are fully implemented here.
Gameworks is expected to converge toward this standard over time (R2–R9 are pending
gameworks implementations).

| Pattern | Pipeline Status |
|---|---|
| P1 — Single-responsibility modules | Full |
| P2 — Frozen config dataclasses | Full (`SourceImageConfig`, `RepairRoutingConfig`) |
| P3 — Rich result dataclasses at boundaries | Full (`SolveResult`, `Phase1RepairResult`, `RepairRouteResult`) |
| P4 — Pure functions / no side effects in math cores | Full (`core.py`, `sa.py` kernel) |
| P5 — Lookup table caching | Full (`solver.py` neighbor cache) |
| P6 — Warmup-and-verify | Full (`sa.py compile_sa_kernel()`) |
| P7 — Try/except relative-then-absolute import | Full (all modules) |
| P8 — Atomic file I/O | Full (`atomic_save_json`, `atomic_save_npy`) |
| P9 — Versioned schema strings | Full (`SCHEMA_VERSION` in every artifact) |
| P10 — Iteration-versioned function names | Full (`core.py` weight functions Iter 2–5) |
| P11 — Explicit deprecation on legacy paths | Full (`pipeline.py run_board()`) |
| P12 — Integrity verification on loaded artifacts | Full (SHA256 in `SourceImageConfig`) |
