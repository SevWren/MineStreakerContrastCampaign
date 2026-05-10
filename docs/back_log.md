# Back Log

  - Double check `docs/industry_standard_implementation_execution_plan_recommendation_4.md` `docs/industry_standard_implementation_execution_plan_recommendation_4_forensic_review.md` `docs/industry_standard_implementation_execution_plan_recommendation_4_forensic_audit.md` for readiness.
  - **[READY] Implement Visual Reconstruction Fix** — Complete specification at `gameworks/docs/FORENSIC_VISUAL_RECONSTRUCTION_ANALYSIS.md`. Restores pixel-perfect image reconstruction on solved boards by fixing 9 rendering gaps (grayscale backgrounds, border suppression, number text removal, mine cell luminance inversion). Self-contained document with exact line numbers, complete code, 11 edge cases, 5 metrics, 8 acceptance criteria. Estimated: 80 minutes (Phase 1: 5min, Phase 2: 30min, Phase 3: 45min). Files affected: `gameworks/renderer.py` only (14 locations, ~40 lines). Branch: `frontend-game-mockup`.



- TODO: Implement supporting accepting multiple seed(s) in CLI instead of the current limitations of a single seed
- TODO: Fully refactor remaining non-repair tuple-return APIs to the new named result-object format instead of continuing to use tuple returns
- Tuple-return follow-up audit:
  - `corridors.py::build_adaptive_corridors(...)`
  - `sa.py::_sa_kernel(...)`
  - `sa.py::run_sa(...)`
  - `solver.py::_numba_solve(...)`
  - `solver.py::_summarize_state(...)`
  - `report.py::_mine_change_overlay(...)`
  - `run_benchmark.py::_normal_benchmark_root(...)`
- TODO: Review current run artifact JSON files to verify that all appropriate data fields are being reported
- TODO: Perform a semantic-tension review of the entire codebase after the image-sweep features and run-artifact revisions
- TODO: Strengthen the pipeline features
- TODO: Brainstorm, theory-craft, and hypothesize about ways to optimize the repair process, investigate additional repair methods that apply to the currently failing black-and-white line art, and eventually improve IRL source-image coverage
- TODO: Implement Save / Resume / Load feature for `gameworks` — full design spec and implementation checklist at `docs/FEATURE_SAVE_RESUME_LOAD.md`. Branch: `feature/save-resume-load` cut from `frontend-game-mockup`. Supplementary docs required: `docs/SAVE_FORMAT_SPEC.md`, `docs/SCHEMA_MIGRATION.md`, `docs/SECURITY.md`. 16 pre-implementation defects were identified and resolved in the spec before any code is written.
