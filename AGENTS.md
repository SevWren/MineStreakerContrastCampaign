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

## Active Study Source-of-Truth Docs
For saturation follow-up and promotion decisions, use:

- `docs/saturation_run_matrix.md` (exact phase commands)
- `docs/saturation_preprocess_followup_plan.md` (promotion + refresh policy)
- `docs/saturation_visual_acceptance_checklist.md` (mandatory visual gate)
- `docs/contrast_preprocessing_documentation_plan.md` (reporting rollup + baseline references)

Baseline comparator summaries (read-only references):
- `results/contrast_preprocess_study_sa3x/contrast_study_summary.md`
- `results/contrast_preprocess_study_20260421_100952/contrast_study_summary.md`

## Build, Test, and Development Commands
Use a local venv and install runtime libs used by imports (`numpy`, `scipy`, `numba`, `Pillow`, `matplotlib`, optional `scikit-image`).

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python assets/image_guard.py --path assets/input_source_image.png
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

1. `python assets/image_guard.py --path assets/input_source_image.png`
2. `python run_iter9.py` and confirm expected solvability metrics for the target run.
3. `python run_benchmark.py` for regression across board sizes/seeds.

If you add automated tests, place them in `tests/` with names like `test_solver_frontier.py`.

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
