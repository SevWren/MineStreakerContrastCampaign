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

`run_benchmark.py --regression-only` is a fixed-case mode and must preserve stable behavior.
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

## Coding Style
- Follow PEP 8 with 4-space indentation.
- Use type hints for public functions.
- Use `snake_case` for functions/variables and `UPPER_CASE` for constants.
- Keep Numba kernels isolated and deterministic with explicit seeds.
- Prefer atomic output writes (`*.tmp` then `os.replace`) for new emitters.

## Commit and PR Guidance
If git metadata is available:
- Commit style: `<scope>: <imperative summary>`
- Keep commits focused.
- For behavior changes, include metric-impact notes and artifact-path evidence in PR descriptions.
