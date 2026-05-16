# Repository Guidelines

## Agent Instruction Priority
When work touches the OpenAI API, ChatGPT Apps SDK, or Codex, use the OpenAI developer documentation MCP server by default.

## Project Scope
This repository is a Python research codebase for reconstructing Minesweeper boards from source images.

Current primary entrypoints:
- `run_iter9.py` (single-run reconstruction pipeline)
- `run_benchmark.py` (normal benchmark matrix and route-aware regression mode)

## Repository Structure
- Runtime modules: `core.py`, `sa.py`, `solver.py`, `corridors.py`, `repair.py`, `report.py`, `pipeline.py`, `board_sizing.py`, `source_config.py`
- Entrypoints: `run_iter9.py`, `run_benchmark.py`
- Assets and image integrity: `assets/`
- Tests: `tests/`
- Demo documentation: `demo/docs/`
- Demo runtime package: `demos/iter9_visual_solver/`
- Demo config: `configs/demo/`
- Generated artifacts: `results/`
- Active docs index: `docs/DOCS_INDEX.md`

Keep algorithm/runtime code in root Python modules. Keep generated artifacts under `results/`.
Do not generate ad-hoc root-level output files.

## Iter9 Visual Solver Demo Contract
The Iter9 visual solver demo is a bounded additive feature, not a monolithic
repository refactor. When work touches `demo/`, `demos/iter9_visual_solver/`,
`tests/demo/iter9_visual_solver/`, `configs/demo/`, or the optional
`run_iter9.py` demo hook, treat `demo/docs/` as the dedicated demo source of
truth.

Before changing demo code, docs, tests, config, schemas, or hook behavior, read
the relevant files under `demo/docs/` and keep the implementation aligned with
them. Do not use stale root-level `docs/` paths as the demo contract, and do
not move demo contracts into the base repository documentation tree.

Demo source-of-truth priority:
1. Current user correction for the task.
2. `demo/docs/json_schemas/*.schema.json` for machine-checkable JSON shape.
3. `demo/docs/*.md` contracts, requirements, and gates for runtime behavior and
   ownership boundaries.
4. `demo/iter9_visual_solver_demo_plan.md` for background sequencing and design
   rationale, interpreted through the dedicated `demo/docs/` layout.
5. `tests/demo/iter9_visual_solver/` when tests agree with the demo contracts.

Canonical demo contract set:
- Plan: `demo/iter9_visual_solver_demo_plan.md`
- Runtime contracts: `demo/docs/runtime_package_contract.md`,
  `demo/docs/artifact_consumption_contract.md`,
  `demo/docs/config_contract.md`, `demo/docs/playback_speed_contract.md`,
  `demo/docs/finish_behavior_contract.md`,
  `demo/docs/pygame_rendering_contract.md`,
  `demo/docs/status_panel_contract.md`, and
  `demo/docs/window_sizing_contract.md`
- Governance and gates: `demo/docs/acceptance_criteria.md`,
  `demo/docs/architecture_boundary_tests.md`,
  `demo/docs/architecture_decisions.md`,
  `demo/docs/completion_gate.md`,
  `demo/docs/source_modularity_standard.md`,
  `demo/docs/testing_methodology.md`, and
  `demo/docs/traceability_matrix.md`
- Schema docs and baselines: `demo/docs/schema_docs_specs.md` and
  `demo/docs/json_schemas/`

### Demo Playback Speed SSOT
For every visual-demo playback-speed, batching, scheduler, replay-counter,
pygame-loop playback, and playback-speed status-text change,
`demo/docs/playback_speed_contract.md` is the binding source of truth after the
current user correction for the task.

This applies to:
- `demos/iter9_visual_solver/playback/speed_policy.py`
- `demos/iter9_visual_solver/playback/event_batching.py`
- `demos/iter9_visual_solver/playback/event_scheduler.py`
- `demos/iter9_visual_solver/playback/replay_state.py`
- `demos/iter9_visual_solver/rendering/pygame_loop.py`
- `demos/iter9_visual_solver/rendering/status_text.py`
- `demos/iter9_visual_solver/cli/commands.py` when it wires playback speed
- `tests/demo/iter9_visual_solver/test_speed_policy.py`
- `tests/demo/iter9_visual_solver/test_event_batching.py`
- `tests/demo/iter9_visual_solver/test_event_scheduler.py`
- `tests/demo/iter9_visual_solver/test_replay_state.py`
- `tests/demo/iter9_visual_solver/test_pygame_loop_with_fakes.py`
- `tests/demo/iter9_visual_solver/test_status_text.py`
- any architecture or CLI tests needed to enforce the contract

When implementation, tests, config docs, or other demo docs conflict with
`demo/docs/playback_speed_contract.md`, refresh the conflicting artifact to
match the playback contract. Do not weaken the playback contract to preserve
current loose implementation or incomplete tests.

Playback-speed work must be TDD-first:
- Add or update failing tests for the exact contract rule before changing
  runtime code.
- Cover every required test item in the contract's Required Tests section.
- Keep tests in the contract-owned test files unless a CLI or architecture
  boundary test is needed to enforce flow or forbidden imports.
- Treat "tests pass" as insufficient when a required contract rule has no
  explicit assertion.

Required playback behavior to preserve:
- `calculate_events_per_second()` accepts a validated `PlaybackConfig` object,
  not raw JSON or dicts.
- The speed formula is exactly
  `round(clamp(base_events_per_second + total_mines * mine_count_multiplier,
  min_events_per_second, max_events_per_second))`.
- `calculate_events_per_frame()` uses
  `max(1, ceil(events_per_second / target_fps))` when batching is enabled, and
  returns `1` when batching is disabled.
- `EventScheduler` preserves event order, emits final partial batches, finishes
  immediately for empty events, and exposes `finished`, `applied_count`, and
  `total_count`.
- `ReplayState` owns applied event counters and status snapshot values.
- `pygame_loop.py` may consume resolved `events_per_second` for display and
  resolved `events_per_frame` for scheduling, but must not calculate the
  mine-count speed formula.
- `status_text.py` must display the resolved numeric line exactly as
  `Playback speed: <events_per_second> cells/sec` and must not calculate speed.

Forbidden playback-speed shortcuts:
- Do not hardcode final playback speed as `50`, `50+`, or any static board-size
  rule.
- Do not tie playback speed to static board width or static board height.
- Do not put speed formula ownership in `pygame_loop.py`, `status_panel.py`,
  `cli/commands.py`, `run_iter9.py`, config loading, artifact loading, or event
  trace loading.
- Do not add pygame, file I/O, JSON loading, NumPy loading, or sleeps/timing
  ownership to `speed_policy.py`, `event_batching.py`, or `event_scheduler.py`.

Minimum validation for playback-speed changes:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_speed_policy
python -m unittest tests.demo.iter9_visual_solver.test_event_batching
python -m unittest tests.demo.iter9_visual_solver.test_event_scheduler
python -m unittest tests.demo.iter9_visual_solver.test_replay_state
python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
python -m unittest tests.demo.iter9_visual_solver.test_status_text
python -m unittest tests.demo.iter9_visual_solver.test_cli_commands
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
```

For playback-speed behavior changes, also run the full repo suite before
completion:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Demo development boundaries:
- Runtime code lives under `demos/iter9_visual_solver/`.
- Demo tests live under `tests/demo/iter9_visual_solver/`.
- The default demo config lives at
  `configs/demo/iter9_visual_solver_demo.default.json`.
- The prompted playback wrapper lives at
  `demos/iter9_visual_solver/cli/prompted_launcher.py` with the PowerShell
  entrypoint `demo/run_iter9_visual_solver_demo_prompted.ps1`.
- Demo docs and schema docs stay under `demo/docs/` and
  `demo/docs/json_schemas/`.
- Do not create root-level `demo_config.py`, `demo_visualizer.py`,
  `visual_solver_demo.py`, or `iter9_visual_solver_demo.py`.
- Do not refactor existing root reconstruction modules for demo work.
- Pygame imports are allowed only in pygame rendering adapter/loop modules and
  pygame-specific tests/fakes.
- Pydantic imports are allowed only in `demos/iter9_visual_solver/config/` and
  config-focused tests.
- `jsonschema` is test/tooling only for the MVP; runtime config validation is
  Pydantic-driven.
- Playback speed, batching, scheduling, replay, and finish policy belong in
  `demos/iter9_visual_solver/playback/`, not in pygame code.
- Artifact path resolution and file loading belong in
  `demos/iter9_visual_solver/io/`, not in playback or rendering.
- The standalone CLI orchestrates existing modules; it does not draw pixels or
  own business rules.
- The prompted wrapper only gathers a results directory, playback speed, and
  finish choice, then delegates to the standalone CLI with resolved artifacts
  and a generated temp config.
- `run_iter9.py` may only expose optional demo flags and delegate through
  `demos.iter9_visual_solver.cli.launch_from_iter9` after a successful Iter9
  run. It must not import pygame or own demo rendering behavior.

Minimum validation for demo changes:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries
python -m unittest tests.demo.iter9_visual_solver.test_prompted_launcher
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
python -m compileall -q demos tests/demo tests/__init__.py run_iter9.py
python -m demos.iter9_visual_solver.cli.commands --help
```

For demo integration or optional hook changes, also run:

### Linux / macOS
```bash
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
# Demo entrypoint (via prompted launcher):
# python -m demos.iter9_visual_solver.cli.commands
```

### Windows (PowerShell)
```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
.\demo\run_iter9_visual_solver_demo_prompted.ps1
```

### Windows (CMD)
```cmd
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
powershell -NoProfile -ExecutionPolicy Bypass -File .\demo\run_iter9_visual_solver_demo_prompted.ps1
```

On Python 3.14, if the `pygame` package attempts a source build instead of
installing a wheel, install `pygame-ce`; it provides the `pygame` import used by
the demo runtime.


## Source Image Runtime Contract
For normal runs:
- Source image selection is CLI-driven via `--image`.
- fallback image is opt-in only
- Import-time image validation is forbidden in `run_iter9.py` and `run_benchmark.py`; validation happens after argument parsing.

Required source provenance in metrics/document blocks:
- command argument
- project-relative path (or null)
- absolute path
- image name and stem
- SHA-256 and size
- noncanonical flag
- manifest path

Validation behavior:
- `assets/image_guard.py` supports default-manifest, explicit-manifest, and noncanonical-allowed modes.
- Entrypoints expose `--image-manifest` and `--allow-noncanonical`.

## Iter9 Image Sweep Contract
`run_iter9.py` supports image-sweep mode when `--image-dir` is supplied.

For multi-image Iter9 work, use native image-sweep mode.
Do not document or recommend shell loops that call `run_iter9.py --image ...` once per source image when `--image-dir` / `--image-glob` can express the same batch.

Sweep CLI surface:
- `--image-dir`
- `--image-glob` (default `*.png`)
- `--recursive`
- `--out-root` (optional; defaults to `results/iter9/<batch_id>/`)
- `--continue-on-error`
- `--skip-existing`
- `--max-images`

Sweep mode constraints:
- `--out-dir`, explicit `--image`, and explicit `--image-manifest` are rejected with `--image-dir`.
- Sweep-only flags are rejected unless `--image-dir` is present.
- `--max-images` must be `>= 1` when supplied.

Sweep outputs:
- One child run directory per discovered image.
- Child directory names include image identity plus full board label and seed.
- Child artifact filenames remain unchanged (`metrics_iter9_<board>.json`, `iter9_<board>_FINAL.png`, etc.).
- Batch root writes:
  - `iter9_image_sweep_summary.json`
  - `iter9_image_sweep_summary.csv`
  - `iter9_image_sweep_summary.md`

Metrics behavior:
- Single-image metrics include top-level `source_image_validation` and omit `batch_context`.
- Successful sweep child metrics include top-level `source_image_validation` and full `batch_context`.

## Benchmark Layout Contract
Normal benchmark mode writes under a benchmark-run root with child directories named:
- `<board_width>x<board_height>_seed<seed>/`

Versioned artifact naming is permitted. The following names are the current v1 baseline:
- `metrics_<board>.json`
- `grid_<board>.npy`
- `visual_<board>.png`
- `visual_<board>_explained.png`
- `repair_overlay_<board>.png`
- `repair_overlay_<board>_explained.png`
- `failure_taxonomy.json`
- `repair_route_decision.json`
- `visual_delta_summary.json`

`run_benchmark.py --regression-only` is a fixed-case mode and must preserve stable case selection, validation gates, and explicit normal-mode flag rejection. Route-state field semantics may be corrected when required by an approved route-state contract, but regression-only outputs, checks, docs, and expected-route comparisons must be updated consistently in the same change.
When `--regression-only` is set, explicit normal-mode flags must remain rejected as currently implemented.

## Explained Report Contract
Explained reports are additive first-look artifacts and do not replace technical PNGs.

Keep explained report wording/layout aligned with `report.py` and tests:
- colorbar labels:
  - `Target value: 0 background -> 8 strongest line`
  - `Generated number: 0 no nearby mines -> 8 surrounded`
  - `Difference: 0 match -> 4+ large mismatch`
  - `Visual change: negative better -> positive worse`
- optimization chart wording:
  - title: `Optimizer progress: lower is better`
  - x-axis includes: `Optimizer work, in millions of attempted mine changes` and `1 plotted point = 50,000 attempted changes`
  - y-axis: `Match error score (lower is better)`
  - legend label: `Match error score`
  - final annotation: `Final score: <value>`
- explained chart must keep a single history curve, visible numeric ticks, and no secondary axes.

Forbidden in explained chart text:
- `Weighted loss`
- `x50k`
- `x50k iterations`

Technical report wording remains unchanged:
- `Loss curve (log)`
- `x50k iters`
- `Weighted loss`

Keep explained report layout/readability settings in sync with code/tests:
- `figsize=(24, 15.5)`
- right-column `subgridspec` sidebar split
- `wspace=0.34`

## Late-Stage Repair Routing Ownership
When modifying solver/repair/pipeline behavior:
- `solver.py` owns unresolved-cell classification and taxonomy.
- `pipeline.py` owns route selection and route artifact writing.
- `repair.py` owns repair grid mutation and move logs.
- `report.py` owns visual proof artifacts.
- `sa.py` must not contain repair routing logic.

Metrics field removals are allowed when they improve the runtime/data model. 
When a change may affect external consumers, document applicability, impact, and transition notes in `for_user_review.md`.

## Route-State Field Invariants

When implementing repair route artifacts (Recommendation 4 or future repair work):

**Mandatory governance contract**: `docs/ROUTE_STATE_FIELD_INVARIANTS.md`

All route-state artifacts must maintain the accepted-move-count invariant:

```python
accepted_move_count = sum(1 for e in repair_log if e["accepted"] == True)
                    == repair_result.n_fixed      (for Phase2)
                    == repair_result.n_fixes      (for Last100)
```

**This invariant:**
- Fixes the Last100 log-mixing bug (move_log contains accepted AND rejected entries; old code incorrectly counts both)
- Provides defensive verification (catches if repair functions change logging behavior)
- Enforces artifact consistency (all three consumers—metrics, visual_delta, repair_route_decision—report the same count)

**Before implementing Recommendation 4, read**: `docs/ROUTE_STATE_FIELD_INVARIANTS.md`

**Enforcement**:
- Serializer guard in `pipeline.py::write_repair_route_artifacts(...)` rejects artifact writes if invariant is violated
- Test suite (Section 2 of Recommendation 4) validates invariant for all repair routes
- Forensic rerun (Recommendation 4 step 12.8) asserts cross-artifact equality

**Implementation requirement**: Any new repair function that modifies the grid must:
1. Return a counter field (`n_fixed`, `n_fixes`, or equivalent)
2. Log accepted moves with `"accepted": True` and rejected moves with `"accepted": False`
3. Submit to the same invariant verification in `pipeline.py` serializer guard
4. Pass validation tests that assert counter equals accepted-log count

## Build and Validation Commands
Use a local virtual environment and runtime dependencies (`numpy`, `scipy`, `numba`, `Pillow`, `matplotlib`, optional `scikit-image`).

### Linux / macOS
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy scipy numba Pillow matplotlib scikit-image
```

### Windows (PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install numpy scipy numba Pillow matplotlib scikit-image
```

### Windows (CMD)
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install numpy scipy numba Pillow matplotlib scikit-image
```

Minimum validation for runtime-contract changes:

### Linux / macOS
```bash
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

### Windows (PowerShell)
```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

### Windows (CMD)
```cmd
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

Extended runtime validation (expensive):

### Linux / macOS
```bash
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 300 --seed 11 --allow-noncanonical --max-images 2 --run-tag "assets_smoke_top2_w300_s11" --out-root "results/iter9/sweep_assets_smoke_top2_w300_s11"
python run_benchmark.py --regression-only
```

### Windows (PowerShell)
```powershell
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 300 --seed 11 --allow-noncanonical --max-images 2 --run-tag "assets_smoke_top2_w300_s11" --out-root "results/iter9/sweep_assets_smoke_top2_w300_s11"
python run_benchmark.py --regression-only
```

### Windows (CMD)
```cmd
python run_iter9.py --image-dir assets --image-glob "*.png" --board-w 300 --seed 11 --allow-noncanonical --max-images 2 --run-tag "assets_smoke_top2_w300_s11" --out-root "results/iter9/sweep_assets_smoke_top2_w300_s11"
python run_benchmark.py --regression-only
```

## Gameworks Package Contract

`gameworks/` is the interactive Pygame-based Minesweeper game. It lives independently
of the reconstruction pipeline. All gameworks documentation is the source of truth under
`gameworks/docs/`. Read the relevant doc before changing behaviour.

Gameworks doc source-of-truth priority:
1. Current user correction for the task.
2. `gameworks/docs/DESIGN_PATTERNS.md` — module discipline, pipeline alignment, and
   all recommended improvements (R2–R9).
3. `gameworks/docs/ARCHITECTURE.md` — module ownership, state machines, data flow.
4. `gameworks/docs/API_REFERENCE.md` — public API contracts for every class/function.
5. `gameworks/docs/GAME_DESIGN.md` — rules, scoring, streak tiers, board modes.
6. `gameworks/docs/DEVELOPER_GUIDE.md` — setup, testing, extension patterns.

### Module Ownership Boundaries

| Module | Owns | Must NOT import |
|---|---|---|
| `engine.py` | `Board`, `GameEngine`, scoring, mine placement, board loading | `pygame`, `renderer`, `main` |
| `renderer.py` | Pygame window, all drawing, animations, event→action translation | `main`, pipeline modules |
| `main.py` | CLI parsing, `GameLoop` state machine, board construction wiring | pipeline modules (except inside `_build_engine`) |

These boundaries are hard rules. An import that crosses them is a bug, not a style issue.

### Modular Design Rules

**1. Frozen config dataclass (R2)**
Game configuration must use a `GameConfig` frozen dataclass rather than flat keyword
arguments. `GameEngine` accepts a single `config: GameConfig`. `restart()` produces a new
frozen config instance (incrementing seed). Do not scatter config fields as loose instance
attributes.

**2. Rich result dataclasses at boundaries (R3)**
Board loader functions (`load_board_from_npy`, `load_board_from_pipeline`) must return a
`BoardLoadResult` dataclass, not a naked `Board`. `format_detected`, `source_path`, and
`warnings` fields are required. `GameEngine` must expose `self.load_result`.

**3. Pure engine core (P4)**
`engine.py` contains no I/O, no Pygame, no clock reads, no mutable global state. All
scoring math is expressed as functions of inputs — no silent mutation of shared objects.

**4. Single-responsibility per module (P1)**
Each module has one named job. If a change requires adding a second distinct concern to a
module (e.g., adding file format logic to `renderer.py`, or adding draw calls to
`engine.py`), stop and create the appropriate module or helper instead.

**5. Atomic file saves (R8)**
All `.npy` saves use `os.replace` via a `.tmp` intermediate:
```python
np.save(tmp_path, arr)
os.replace(tmp_path, final_path)
```
Direct `np.save(final_path, arr)` is forbidden for any user-facing save operation.

**6. Schema versioning for saved artifacts (R9)**
Every `.npy` board save must write a companion `.json` sidecar containing at minimum:
`schema`, `width`, `height`, `mines`, `seed`, `saved_at`.
The schema string is the module-level constant `GAME_SAVE_SCHEMA_VERSION` in `engine.py`.
`load_board_from_npy` reads the sidecar when present and populates `BoardLoadResult.warnings`
on schema mismatch. Missing sidecar is a warning, not an error (backward compatibility).

**7. Preflight check before game loop (R6)**
`main.py` must call `preflight_check(args)` before constructing `GameLoop`. It must
validate file paths and import availability and print actionable error messages before
any Pygame window opens. The game loop must not be the first place a missing file is
detected.

**8. No ad-hoc result tuples**
Every function that returns more than one meaningful value must return a dataclass, not a
bare tuple. `Board.reveal` and `Board.chord` return `(bool, list)` — this is acceptable
only as an internal primitive. Any new public function returning compound results must use
a dataclass.

### Import Boundary Enforcement

The following import is forbidden and must be caught by the architecture test:

```python
# engine.py — FORBIDDEN
import pygame          # any form
from pygame import *
```

Run the architecture boundary test before committing any gameworks change:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/test_gameworks_engine.py -v
```

The engine test suite must remain runnable without a display server. If a change breaks
headless execution of `tests/test_gameworks_engine.py`, it is a regression.

### Image-Reveal Pipeline Contract

`engine.py::load_board_from_pipeline()` is the **sole call site** for all image-based
board construction within the gameworks subsystem.

1. **Single call site.** Any gameworks code path needing a `Board` from a source image
   must call `engine.py::load_board_from_pipeline()`. Do not inline pipeline stage calls
   (`core`, `sa`, `solver`, `repair`, `corridors`) anywhere else in gameworks.
2. **`main.py` boundary.** `main.py` may reach the pipeline only through
   `_build_engine` → `engine.py::load_board_from_pipeline()`. Direct imports of `core`,
   `sa`, `solver`, `repair`, `corridors`, or `board_sizing` in `main.py` or `renderer.py`
   are forbidden and must be caught by the architecture boundary test.
3. **Parameter sync obligation.** When SA/solver tuning constants change in `run_iter9.py`
   (e.g. `T_COARSE`, `DENSITY`, `SEAL_THR`, `BORDER`), update the matching defaults in
   `load_board_from_pipeline()` in the **same commit**. These two callers are parallel
   consumers of the same pipeline modules and must not silently diverge.
4. **No silent divergence.** `run_iter9.py` is the reference full-pipeline implementation
   (artifacts + metrics + repair routing). `load_board_from_pipeline()` is the board-only
   counterpart. They must produce boards of equivalent quality from the same image and
   seed. Silent divergence is a bug.

### Gameworks Test Commands

```bash
# Package-local suite — unit, architecture, CLI, integration (no display required)
pytest gameworks/tests/unit/ gameworks/tests/architecture/ gameworks/tests/cli/ gameworks/tests/integration/ -v

# Headless renderer suite
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/ -v

# Full package-local suite
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v

# Legacy root-level gameworks tests (regression guard)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/test_gameworks_engine.py tests/test_gameworks_renderer_headless.py -v
```

### Gameworks Versioning

When gameworks behaviour changes:
1. Update `gameworks/__init__.py`: `__version__ = "x.y.z"`
2. Add a section to `gameworks/docs/CHANGELOG.md`.
3. Run the full gameworks test suite.
4. Commit: `gameworks: <imperative summary>`

Do not bump the gameworks version for documentation-only changes.

---

## Coding Style
- Follow PEP 8 with 4-space indentation.
- Use type hints for public functions.
- Use `snake_case` for functions/variables and `UPPER_CASE` for constants.
- Keep Numba kernels isolated and deterministic with explicit seeds.
- Prefer atomic output writes (`*.tmp` then `os.replace`) for new emitters.

## gameworks/ — Mine-Streaker Pygame Package

`gameworks/` is a standalone pygame Minesweeper engine with image-reveal mode.
It is developed on the `frontend-game-mockup` branch and is independent of the
reconstruction pipeline modules (`core.py`, `sa.py`, etc.).

Primary files:
- `gameworks/engine.py` — `Board`, `GameEngine`, scoring, mine-flash, flood-fill
- `gameworks/renderer.py` — All pygame drawing, animation, HUD, panel, image ghost
- `gameworks/main.py` — CLI args, game loop state machine, event dispatch
- `corridors.py` (repo root) — `build_adaptive_corridors()` (returns `(forbidden, coverage_pct, seeds, mst)` tuple — NOT a dict); imported dynamically inside `engine.py::load_board_from_pipeline` — **sole pipeline call site for gameworks image mode; see Image-Reveal Pipeline Contract above**

Issue tracking: `gameworks/docs/BUGS.md` — canonical bug register with severity, root cause, and fix spec per entry.
Performance analysis: `gameworks/docs/ZOOM_OUT_PERFORMANCE_REPORT.md` (13 bottleneck forensics) and `gameworks/docs/PERFORMANCE_PLAN.md` (Phases 1–8 remediation plan)

Key design decisions:
- No-game-over on mine hit: `Board._state` is NEVER set to `"lost"`. Mine hit = score penalty + 1.5 s flash.
- Viewport culling: `tx0/ty0/tx1/ty1` computed from `_pan_x/_pan_y` — all cell loops must stay within these bounds.
- numpy arrays accessed directly (`_mine`, `_revealed`, `_flagged`, `_questioned`, `_neighbours`) — do NOT call `board.snapshot()` inside hot per-frame paths.
- Surface caches: `_num_surfs`, `_question_surf`, `_thumb_surf`, `_fog_surf`, `_ghost_surf` — rebuild only on tile/window-size change, never per-frame.

gameworks validation — AST syntax check (Step 5 of Pre-Push Protocol):
```bash
python -c "import ast; ast.parse(open('gameworks/renderer.py').read()); print('renderer OK')"
python -c "import ast; ast.parse(open('gameworks/engine.py').read()); print('engine OK')"
python -c "import ast; ast.parse(open('gameworks/main.py').read()); print('main OK')"
```

gameworks test suite (Step 6 of Pre-Push Protocol):
```bash
# Package-local suite — unit, architecture, CLI, integration (no display required)
pytest gameworks/tests/unit/ gameworks/tests/architecture/ gameworks/tests/cli/ gameworks/tests/integration/ -v

# Headless renderer suite (SDL dummy driver)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/ -v

# Legacy root-level suite (regression guard)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/test_gameworks_engine.py tests/test_gameworks_renderer_headless.py -v
```

Pending implementation tests (activate when the corresponding R2/R3/R9 feature is built):
- `gameworks/tests/unit/test_config.py` — R2: GameConfig frozen dataclass
- `gameworks/tests/unit/test_board_loading.py` (partial) — R3: BoardLoadResult
- `gameworks/tests/cli/test_preflight.py` — R6: preflight_check() (DP-R6 resolved; test un-skip pending)
- `gameworks/tests/unit/test_board_loading.py` (schema section) — R9: GAME_SAVE_SCHEMA_VERSION

---

## Pre-Push Verification Protocol (MANDATORY)

Before **every** `git push`, regardless of how small the change appears, execute
every step below in order. If any step fails, fix the gap and restart from step 1.

> **LLM-session note:** An LLM agent's memory of what it changed is unreliable.
> Every step below that can be grounded in a shell command must be. Self-certification
> ("I believe I checked this") is not sufficient evidence for any step.

**Automated helper — runs Steps 1, 2, 5, and 6 and prints auditable output:**

```bash
bash scripts/pre_push_check.sh                  # default: full test suite
bash scripts/pre_push_check.sh --suite gameworks # gameworks tests only
bash scripts/pre_push_check.sh --suite demo      # demo tests only
```

Post the complete script output as evidence before pushing. Steps 3, 4, and 7
require reasoning and are not automated; complete them alongside the script run.

---

### Step 0 — Capture the pre-change failure baseline (before editing)

Run the relevant test suite *before* making any changes and save the output.
This must happen at the start of the session, not after edits are complete.

```bash
python -m unittest discover -s tests -p "test_*.py" 2>&1 | tee /tmp/baseline_failures.txt
```

If the session has already started without a baseline, run the suite on a
`git stash` snapshot and restore:

```bash
git stash
python -m unittest discover -s tests -p "test_*.py" 2>&1 | tee /tmp/baseline_failures.txt
git stash pop
```

This baseline is the ground truth used in Step 6 to separate pre-existing
failures from newly introduced regressions.

---

### Step 1 — Read the ground-truth diff, not memory

Do not rely on recalling what you edited. Run:

```bash
git diff --staged
```

Read every hunk. For each changed block, confirm:
- It belongs to the stated task scope.
- It says what you intended, not what you remember intending.
- No unintended lines were added or removed (e.g., debug prints, accidental
  whitespace-only changes, edits in the wrong file).

Any hunk not attributable to the stated task is an **unintended change** and
must be reverted with `git restore --staged <file>` before continuing.

Memory of what you *intended* to write is not evidence. The diff is.

---

### Step 2 — Cross-check scope with diff statistics

Run:

```bash
git diff --staged --stat
```

Read the per-file insertion/deletion counts. Tally the number of distinct
changes against the stated task scope. A commit message that names 5 fixes
with a diff showing 3 files changed is a **failed push**.

Draft the commit message **only after** reading `--staged` and `--stat`.
Do not draft the message from memory and then check the diff — this ordering
produces the mismatch problem this protocol was created to prevent.

---

### Step 3 — Trace each fix end-to-end

For every bug fixed, follow the call chain from the broken call site through to
the corrected return value. Confirm no intermediate function still passes the old
(wrong) value or stale variable reference.

State the specific **concrete wrong value** that would be returned or observed
if the code regressed. "It would fail somehow" is not sufficient. Name the value.

---

### Step 4 — Audit for partial fixes and unintended co-located changes

Two separate checks:

**Partial fixes:** A fix that corrects the primary symptom while leaving a
secondary bug in the same function is incomplete. Read the entire function body
of every function you changed, not just the lines you modified. Check callers
for assumptions about return type or value that your change may have invalidated.

**Unintended changes:** For every file in `git diff --staged`, read the full
diff of that file and confirm there are no changes outside the intended scope.
Common LLM-specific sources of unintended changes: rewriting a nearby docstring,
reformatting an unrelated function, removing an import that was still needed,
changing a variable name globally when only one site was intended.

---

### Step 5 — Run AST parse and pyflakes on every edited `.py` file

**Syntax (AST parse):**

```bash
python -c "import ast; ast.parse(open('FILE').read()); print('FILE OK')"
```

**Undefined names and unused imports (pyflakes):**

```bash
python -m pyflakes FILE.py
```

Run both on every `.py` file in `git diff --staged --name-only`. AST parse
catches syntax errors; pyflakes catches the class of errors LLM edits most
commonly introduce: referencing a name that was renamed mid-session, leaving
an unused import from an abandoned approach, or shadowing a name from an outer
scope. A clean pyflakes run is required before proceeding.

---

### Step 6 — Run the relevant test suite, compare against baseline, and isolate new tests

**Compare against baseline:**

After running the suite, diff against the Step 0 baseline:

```bash
python -m unittest discover -s tests -p "test_*.py" 2>&1 | tee /tmp/after_failures.txt
diff /tmp/baseline_failures.txt /tmp/after_failures.txt
```

Only lines that appear in `after_failures.txt` but not in `baseline_failures.txt`
are regressions introduced by this change. All other failures are pre-existing
and must be documented in the commit message — they are
not acceptable to silently push over.

**Suite commands by change area:**

*gameworks/ changes* (engine, renderer, main, corridors):

```bash
# Package-local suite — unit, architecture, CLI, integration (no display required)
pytest gameworks/tests/unit/ gameworks/tests/architecture/ gameworks/tests/cli/ gameworks/tests/integration/ -v

# Headless renderer suite (SDL dummy driver)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/ -v

# Legacy root-level regression guard
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  pytest tests/test_gameworks_engine.py tests/test_gameworks_renderer_headless.py -v
```

*Pipeline / reconstruction changes* (core, sa, solver, corridors, repair, report, pipeline):

```bash
python -m unittest discover -s tests -p "test_*.py"
```

*Demo changes* (`demos/`, `tests/demo/`):

```bash
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"
```

**Run each new test in isolation:**

For every new test method added in this change, run it individually:

```bash
python -m pytest tests/test_foo.py::TestClass::test_new_method -v
# or
python -m unittest tests.test_foo.TestClass.test_new_method
```

A test that passes in the bulk suite but fails in isolation has a hidden
dependency on test ordering or shared mutable state. Fix it before pushing.

**Rules:**

- All tests that were passing before your change must still pass after it.
- If your change caused a previously-passing test to fail: **fix the code or
  update the test** before pushing. Do not push failing tests.
- If a test was already failing *before* your change (pre-existing breakage):
  document it explicitly in the commit message.
  Do not silently push over pre-existing failures as if they are acceptable —
  make the state visible.
- If you add new behaviour (new function, new fix, new feature): check whether
  existing tests cover it. If they do not, add a test. A fix with zero test
  coverage that can silently regress is an incomplete fix.

---

### Step 7 — Verify new tests actually catch regressions

Writing a test that always passes regardless of the fix provides no protection.
This is the most common LLM-specific test-quality failure: the test is written
to match what the code currently does, not what it must do.

For each new test added, verify it would fail without the change using one of
these two methods:

**Method A — Revert and run:**
Temporarily revert the specific line(s) the test is guarding, run the test
alone, confirm it fails, restore the line(s).

**Method B — State the concrete failure:**
Without running, state explicitly: "If this code regressed to `<old behaviour>`,
this assertion would receive `<specific wrong value>` instead of
`<expected value>`." Vague statements ("it would fail") are not acceptable.
Name the wrong value.

Method A is required for fixes where the regression is subtle. Method B is
acceptable for new feature tests where the behaviour being tested did not
previously exist.

Extend the appropriate test file for the change:
- `gameworks/tests/unit/test_board.py` — Board logic: reveal, flag, chord, flood-fill
- `gameworks/tests/unit/test_engine.py` — GameEngine: lifecycle, scoring, streak, restart
- `gameworks/tests/unit/test_scoring.py` — scoring constants and multiplier tiers
- `gameworks/tests/unit/test_mine_placement.py` — place_random_mines
- `gameworks/tests/unit/test_board_loading.py` — load_board_from_npy, format detection
- `gameworks/tests/renderer/test_renderer_init.py` — Renderer construction, constants
- `gameworks/tests/renderer/test_animations.py` — AnimationCascade, WinAnimation
- `gameworks/tests/renderer/test_surface_cache.py` — per-frame cache stability
- `gameworks/tests/architecture/test_boundaries.py` — import boundary enforcement
- `gameworks/tests/fixtures/boards.py` / `engines.py` — add shared factory helpers here
- `tests/test_gameworks_engine.py` — regression guard for critical bugs (root suite)

---

### Step 8 — Push

Only after steps 0–7 pass completely. If any step above revealed a gap, fix it
and restart the checklist from step 1.

---

This protocol exists because previous sessions pushed commits where: (a) the
claimed fix list in the message did not fully match the diff, and (b) no test
coverage was added for fixes, allowing regressions to go undetected. Steps 0–4
were subsequently added to address the specific failure modes of LLM-driven
development: unreliable session memory, self-certified verification, and tests
written to match current behaviour rather than intended behaviour.

---

## Commit and PR Guidance
If git metadata is available:
- Commit style: `<scope>: <imperative summary>`
- Keep commits focused.
- For behavior changes, include metric-impact notes and artifact-path evidence in PR descriptions.
- **Apply the Pre-Push Verification Protocol above before every push.**
