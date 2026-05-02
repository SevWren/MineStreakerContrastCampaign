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
4. `demo/docs/iter9_visual_solver_demo_ui_polish_implementation_plan.md` and
   `demo/docs/iter9_visual_solver_responsive_layout_refactor_requirements.md`
   when work touches the current GUI/layout direction.
5. `demo/iter9_visual_solver_demo_plan.md` for background sequencing and design
   rationale, interpreted through the dedicated `demo/docs/` layout.
6. `tests/demo/iter9_visual_solver/` when tests agree with the demo contracts.
7. `demo/docs/iter9_visual_solver_demo_implementation_plan.md` and
   `demo/docs/iter9_visual_solver_demo_execution_plan.md` as the current
   execution maps.

Canonical demo contract set:
- Plans and current layout work:
  `demo/docs/iter9_visual_solver_demo_implementation_plan.md`,
  `demo/docs/iter9_visual_solver_demo_execution_plan.md`,
  `demo/docs/iter9_visual_solver_demo_ui_polish_implementation_plan.md`,
  `demo/docs/iter9_visual_solver_responsive_layout_refactor_requirements.md`,
  and `demo/iter9_visual_solver_demo_plan.md`
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

```powershell
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

Metrics field removals are allowed when they improve the runtime/data model. When a change may affect external consumers, document applicability, impact, and transition notes in `for_user_review.md`.

## Build and Validation Commands
Use a local virtual environment and runtime dependencies (`numpy`, `scipy`, `numba`, `Pillow`, `matplotlib`, optional `scikit-image`).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install numpy scipy numba Pillow matplotlib scikit-image
```

Minimum validation for runtime-contract changes:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

Extended runtime validation (expensive):

```powershell
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
