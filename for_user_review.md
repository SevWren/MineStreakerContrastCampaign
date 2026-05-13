Metrics field removals are allowed when they improve the runtime/data model.

When a change may affect external consumers, document applicability, impact, and transition notes in `for_user_review.md`.

applicability: Iter9 metrics, repair route decision artifacts, visual delta summary artifacts,
  repair overlays, image-sweep summaries, normal benchmark child metrics, normal benchmark
  summaries, benchmark_results.json, regression-only output, and report text.
impact: selected_route now means the invoked route; needs_sa_or_adaptive_rerun moves to
  next_recommended_route for unresolved follow-up work.
transition: repair_route_selected may remain only as an exact alias of selected_route in
  newly written artifacts; consumers must read next_recommended_route for follow-up strategy.
validation evidence: targeted tests, full test suite, help checks, image guard check, and
  the forensic rerun path.