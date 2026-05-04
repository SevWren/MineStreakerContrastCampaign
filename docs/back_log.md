# Back Log

  - Double check `docs/industry_standard_implementation_execution_plan_recommendation_4.md` `docs/industry_standard_implementation_execution_plan_recommendation_4_forensic_review.md` `docs/industry_standard_implementation_execution_plan_recommendation_4_forensic_audit.md` for readiness.



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
