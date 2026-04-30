# Repository Guidelines

## Agent Instruction Priority
When work touches the OpenAI API, ChatGPT Apps SDK, or Codex, use the OpenAI developer documentation MCP server by default.

## Project Scope
This repository is a Python research codebase for reconstructing Minesweeper boards from source images.

Current primary entrypoints:
- `run_iter9.py` (single-run reconstruction pipeline)
- `run_benchmark.py` (normal benchmark matrix and route-aware regression mode)

Legacy/compatibility entrypoints:
- `pipeline.py::run_board(...)` exists but is explicitly deprecated.
- `test_runtime_entrypoint_source_image_contracts_and_deprecated_paths.py` is a historical replay script, not the main runtime workflow.
- `run_repair_only_from_grid.py` is currently a stub marker file.

## Repository Structure
- Runtime modules: `core.py`, `sa.py`, `solver.py`, `corridors.py`, `repair.py`, `report.py`, `pipeline.py`, `board_sizing.py`, `source_config.py`
- Entrypoints: `run_iter9.py`, `run_benchmark.py`
- Assets and image integrity: `assets/`
- Tests: `tests/`
- Generated artifacts: `results/`
- Active docs index: `docs/DOCS_INDEX.md`

Keep algorithm/runtime code in root Python modules. Keep generated artifacts under `results/`.
Do not generate ad-hoc root-level output files.

## Active vs Deprecated Docs
Follow `docs/DOCS_INDEX.md` for active documentation.
Do not resurrect archived/deprecated study plans unless a direct compatibility patch requires it.

## Source Image Runtime Contract
For normal runs:
- Source image selection is CLI-driven via `--image`.
- `assets/input_source_image.png` is only the backward-compatible default when `--image` is omitted.
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

Preserve established child artifact filenames:
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

Do not remove existing metrics fields without an explicit migration plan.

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
python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical
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
