# Repository Guidelines

## Agent Instruction Priority
When work touches the OpenAI API, ChatGPT Apps SDK, or Codex, use the OpenAI developer documentation MCP server by default.

## Project Structure & Module Organization
This repository is a Python research codebase for Minesweeper-board reconstruction.

- Root runtime modules: `core.py`, `sa.py`, `solver.py`, `corridors.py`, `repair.py`, `report.py`, `pipeline.py`
- Main entry scripts: `run_iter9.py`, `run_benchmark.py`
- Study/orchestration scripts: `run_contrast_preprocessing_study.py`, `run_iris3d_visual_report.py`
- Assets: `assets/` (`input_source_image.png`, `input_source_image_research.png`, guards/checks)
- Documentation: `docs/` (including saturation matrix and visual-gate workflow docs)
- Outputs: `results/` (all generated runs, summaries, ledgers, visuals)

Keep algorithm/runtime code in root Python modules. Keep generated artifacts under `results/` and avoid committing ad-hoc output files at repo root.

## Deprecated Study Docs (Out Of Scope)
The prior saturation/contrast planning docs were intentionally deprecated and removed from active workflow.

- Do not resurrect or edit deprecated saturation/contrast study docs unless a direct compatibility issue requires a minimal patch.
- Keep deprecated study scripts and plans out of normal implementation scope.
- Use current runtime entry points (`run_iter9.py`, `run_benchmark.py`) and active `docs/` contracts for ongoing work.

## Build, Test, and Development Commands
Use a local venv and install runtime libs used by imports (`numpy`, `scipy`, `numba`, `Pillow`, `matplotlib`, optional `scikit-image`).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
python run_iter9.py
python run_benchmark.py
```

Notes:
- `image_guard.py` validates image integrity before long runs.
- `run_iter9.py` runs the main reconstruction pipeline and writes metrics/grids/reports.
- `run_benchmark.py` runs multi-board/multi-seed regression checks.

## Coding Style & Naming Conventions
- Follow PEP 8 with 4-space indentation and type hints on public functions.
- Use `snake_case` for functions/variables and `UPPER_CASE` for constants.
- Prefer vectorized NumPy operations where practical.
- Keep Numba kernels isolated (`sa.py`, `solver.py`) and deterministic with explicit seeds.
- Use atomic write patterns for outputs (`*.tmp` then `os.replace`) for any new file emitters.

## Validation Guidelines
There is no dedicated `tests/` suite in this snapshot. Minimum required validation:

1. `python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical`
2. `python run_iter9.py` and confirm expected solvability metrics for the target run.
3. `python run_benchmark.py` for regression across board sizes/seeds.

Backward-compatible strict default check (only when intentionally validating the legacy default image):
- `python assets/image_guard.py --path assets/input_source_image.png`

If you add automated tests, place them in `tests/` with names like `test_solver_frontier.py`.

## Late-Stage Repair Routing Contract
When modifying solver/repair/pipeline behavior:

- `solver.py` owns unresolved-cell classification.
- `pipeline.py` owns repair route selection.
- `repair.py` owns grid mutation and repair move logs.
- `report.py` owns visual proof artifacts.
- `sa.py` must not contain repair routing logic.
- Existing metrics fields must not be removed.
- New artifacts must be written under `results/`.
- Generated root-level ad-hoc files are forbidden.
- Deprecated study scripts must not be modified unless required for direct compatibility.

## Source Image Runtime Contract
When modifying runtime entry points and benchmark workflows:

- Source images must be CLI-driven (`--image`) for normal runs.
- `assets/input_source_image.png` is only a backward-compatible argparse default when `--image` is omitted.
- Import-time image validation is forbidden in `run_iter9.py` and `run_benchmark.py`; validate only in `main()` after argument parsing.
- Source image provenance must be recorded in metrics: command arg, project-relative path (or null), absolute path, name, stem, SHA-256, size, noncanonical flag, and manifest path.
- Normal benchmark mode must write to a benchmark-run root containing per-board/per-seed child directories named `<board_width>x<board_height>_seed<seed>/`.
- Keep established artifact filenames inside run directories; identity belongs in directory names and provenance fields, not expanded filenames.
- `run_benchmark.py --regression-only` is the fixed-case exception and must preserve stable regression behavior.

## Saturation Campaign Rules
When running saturation matrix campaigns:

- Use SA3x settings for refresh-eligible evidence.
- Keep seeds, controls, stress widths, and phase sequencing aligned with `docs/saturation_run_matrix.md`.
- Produce required campaign outputs:
  - `matrix_runs.csv`
  - `matrix_summary.json`
  - `matrix_summary.md`
  - `winner_visual_review.csv`
- Apply mandatory visual approval before promoting any metric winner.
- Use `results/saturation_matrix_TEMPLATE/winner_visual_review.csv` as the header template when bootstrapping campaigns.
- Do not treat SA1x-only runs as refresh-eligible evidence.

## Commit & PR Guidelines
If git metadata is available, use:

- Commit format: `<scope>: <imperative summary>` (example: `repair: break sealed unknown clusters earlier`)
- Keep commits focused and include metric-impact notes for behavior changes.
- PRs should include purpose, algorithm/config changes, before/after metrics, and updated output paths/screenshots where relevant.
