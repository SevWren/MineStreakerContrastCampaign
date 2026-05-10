# Repository Map
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Root Layout

```
MineStreakerContrastCampaign/
├── AGENTS.md                        # Agent/LLM behavioral instructions
├── GEMINI.md                        # Gemini agent variant instructions
├── HARDENING_SUMMARY.md             # Security hardening notes
├── LICENSE                          # License file
├── PULL_REQUEST_DESCRIPTION.md      # PR context document
├── README.md                        # Project overview and quick start
├── for_user_review.md               # User-facing change log
├── full_enterprise_grade_..._prompt.md  # This audit prompt (in-repo)
│
├── archives/                        # Archived/deprecated artifacts
│   ├── Timeout Theory Campaign Plan line_art_irl_9 20min budget.md
│   └── run_contrast_preprocessing_study.py.old
│
├── assets/                          # Source images + image integrity
│   ├── image_guard.py               # SHA256 + pixel integrity checks
│   ├── image_guard.py               # SHA256 + pixel integrity checks
│   ├── input_source_image.png       # Primary canonical source image
│   ├── input_source_image_research*.png  # Research images (9 variants)
│   ├── line_art_a*.png/jpg          # Line-art style images (a1–a7, incl. a6.jpg, a7.jpg)
│   ├── line_art_c*.png              # C-series line art (2 variants)
│   ├── line_art_irl_1–13.*          # IRL photo-traced line art (variants 1–13)
│   ├── line_art_irl_14.png          # NEW (commit 09e17c1)
│   ├── line_art_irl_14_optimized.png / _V2.png  # NEW (commit 09e17c1)
│   ├── line_art_irl_15.png          # NEW (commit 09e17c1)
│   ├── line_art_irl_16.png          # NEW (commit 09e17c1)
│   ├── line_art_irl_17.png          # NEW (commit 09e17c1)
│   ├── line_art_irl_18.png          # NEW (commit 09e17c1)
│   ├── line_art_irl_18v2.png        # NEW (commit 09e17c1) — resolves FIND-STATE-HIGH-h008a
│   └── tessa_line_art_stiletto.png  # Named character art
│
├── board_sizing.py                  # Image-aspect-ratio → board dimensions
├── core.py                          # Image loading, weights, N-field compute (354 LOC)
├── corridors.py                     # MST-based mine-free corridor generation (158 LOC)
├── pipeline.py                      # Repair routing + artifact persistence (415 LOC)
├── repair.py                        # Phase1/Phase2/Last100 mine repair (752 LOC)
├── report.py                        # PNG report rendering (845 LOC)
├── run_benchmark.py                 # Benchmark matrix runner
├── run_iter9.py                     # Primary pipeline entrypoint (1726 LOC)
├── sa.py                            # Numba SA kernel (205 LOC)
├── solver.py                        # Numba deterministic CSP solver (566 LOC)
├── source_config.py                 # Source image config + SHA256 resolution
│
├── configs/
│   └── demo/
│       └── iter9_visual_solver_demo.default.json  # Demo config schema instance
│
├── demo/
│   ├── iter9_visual_solver_demo_plan.md
│   ├── run_iter9_visual_solver_demo_prompted.ps1
│   └── docs/                        # 16 contract docs for the visual solver demo
│       ├── acceptance_criteria.md
│       ├── architecture_boundary_tests.md
│       ├── architecture_decisions.md
│       ├── artifact_consumption_contract.md
│       ├── completion_gate.md
│       ├── config_contract.md
│       ├── finish_behavior_contract.md
│       ├── json_schemas/            # 4 JSON schema files (config + event trace)
│       ├── playback_speed_contract.md
│       ├── pygame_rendering_contract.md
│       ├── runtime_package_contract.md
│       ├── schema_docs_specs.md
│       ├── source_modularity_standard.md
│       ├── status_panel_contract.md
│       ├── testing_methodology.md
│       ├── traceability_matrix.md
│       └── window_sizing_contract.md
│
├── demos/
│   └── iter9_visual_solver/         # Visual solver demo runtime package
│       ├── __init__.py
│       ├── cli/     (4 modules: args, commands, launch_from_iter9, prompted_launcher)
│       ├── config/  (4 modules: loader, models, schema_export, validation_errors)
│       ├── contracts/ (3 modules: artifact_names, defaults, schema_versions)
│       ├── domain/  (5 modules: board_dimensions, board_state, demo_input,
│       │             playback_event, status_snapshot)
│       ├── errors/  (4 modules: artifact_errors, config_errors, rendering_errors,
│       │             trace_errors)
│       ├── io/      (6 modules: artifact_paths, event_trace_loader,
│       │             event_trace_writer, grid_loader, json_reader, metrics_loader)
│       ├── playback/ (5 modules: event_batching, event_scheduler, event_source,
│       │              finish_policy, replay_state, speed_policy)
│       └── rendering/ (8 modules: board_surface, color_palette, pygame_adapter,
│                       pygame_loop, status_panel, status_text, status_view_model,
│                       window_chrome, window_geometry)
│
├── docs/
│   ├── DOCS_INDEX.md
│   ├── GAME_DESIGN.md               # Full product GDD (React/Canvas target)
│   ├── ROUTE_STATE_FIELD_INVARIANTS.md
│   ├── back_log.md                  # Active TODOs
│   ├── example_commands_image_sweep_mode.md
│   ├── explained_report_artifact_contract.md
│   ├── forensic_analysis_accepted_move_count_field_verification.md
│   ├── frontend_spec/               # 10 TypeScript/React specs (NOT IMPLEMENTED)
│   │   ├── 00_PROJECT_STRUCTURE.md  # React 18 + Zustand + Canvas target
│   │   ├── 01_TYPES.md
│   │   ├── 02_BOARD_ENGINE.md
│   │   ├── 03_STATE_MACHINE.md
│   │   ├── 04_SCORING_ENGINE.md
│   │   ├── 05_HINT_ENGINE.md
│   │   ├── 06_UNDO_ENGINE.md
│   │   ├── 06b_RENDERER.md
│   │   ├── 07_GAME_CONTROLLER.md
│   │   ├── 08_UI_COMPONENTS.md
│   │   ├── 09_GAME_FLOW.md
│   │   └── 10_ACCESSIBILITY.md
│   ├── industry_standard_implementation_execution_plan_recommendation_4*.md
│   └── json_schema/                 # JSON output schema documentation
│       ├── JSON_OUTPUT_SCHEMA_INDEX.md
│       ├── benchmark_summary.schema.md
│       ├── failure_taxonomy.schema.md
│       ├── metrics_iter9.schema.md
│       ├── repair_route_decision.schema.md
│       └── visual_delta_summary.schema.md
│
├── gameworks/                       # *** PRIMARY FOCUS *** Pygame Minesweeper game
│   ├── __init__.py                  # Package init, version 0.1.0
│   ├── engine.py                    # Pure game logic — Board, GameEngine (452 LOC)
│   └── main.py                      # CLI + game loop state machine (298 LOC)
│   └── renderer.py                  # Pygame renderer — tiles, HUD, anims (1041 LOC)
│
├── results/                         # Pre-built pipeline output boards (added commit ca3eee4)
│   └── iter9/
│       ├── 20260429T234439Z_input_source_image_300w_seed42/
│       │   ├── grid_iter9_300x370.npy      # shape=(370,300), int8, 0=safe/1=mine, 15574 mines (14.0%)
│       │   └── repair_checkpoint.npy       # intermediate repair state, same format
│       ├── 20260430T004415Z_line_art_irl_18v2_300w_seed11_Easter_Irl_Test/
│       │   ├── grid_iter9_300x215.npy      # shape=(215,300), int8, 0=safe/1=mine, 18529 mines (28.7%)
│       │   └── repair_checkpoint.npy       # ⚠ source image line_art_irl_18v2 NOT in assets/
│       ├── 20260430T004522Z_line_art_irl_18v2_600w_seed11_Easter_Irl_Test/
│       │   ├── grid_iter9_600x429.npy      # shape=(429,600), int8, 0=safe/1=mine, 63060 mines (24.5%)
│       │   └── repair_checkpoint.npy       # source image now present: assets/line_art_irl_18v2.png ✓
│       └── 20260510T054753Z_tessa_line_art_stiletto_300w_seed11_GAME_DevelopmentBOARD/
│           ├── grid_iter9_300x300.npy      # shape=(300,300), int8, 0=safe/1=mine, 4794 mines (5.3%) ← PRIMARY DEV BOARD
│           ├── grid_iter9_latest.npy       # identical to grid_iter9_300x300.npy (canonical alias)
│           ├── iter9_300x300_FINAL.png     # pipeline report image
│           ├── iter9_300x300_FINAL_explained.png
│           ├── repair_overlay_300x300.png  # repair pass overlay report
│           └── repair_overlay_300x300_explained.png
│           # Source image: assets/tessa_line_art_stiletto.png (2048×2048 RGB) ✓ present
│           # Compatibility: pipeline format (0/1) — requires Fix 15 (FIND-ARCH-CRITICAL-f006a)
│
│   NOTE: All boards use pipeline encoding (0=safe, 1=mine). gameworks/engine.py::load_board_from_npy()
│   expects game encoding (-1=mine, 0-8=neighbour_count) — FORMAT INCOMPATIBILITY (FIND-ARCH-CRITICAL-f006a)
│
└── tests/
    ├── __init__.py
    ├── test_benchmark_layout.py
    ├── test_image_guard_contract.py
    ├── test_iter9_image_sweep_contract.py
    ├── test_repair_result_dataclasses.py
    ├── test_repair_route_decision.py
    ├── test_repair_visual_delta.py
    ├── test_report_explanations.py
    ├── test_route_artifact_metadata.py
    ├── test_solver_failure_taxonomy.py
    ├── test_source_config.py
    ├── test_source_image_cli_contract.py
    └── demo/
        └── iter9_visual_solver/     # 30+ test files for demos package
```

## File Count Summary

| Category | Count |
|---|---|
| Python source (runtime) | 12 (root modules) + 4 (gameworks) + ~35 (demos) |
| Test files | 12 (tests/) + 30+ (tests/demo/) |
| Documentation | 35+ .md files |
| JSON schemas | 7 |
| Source images (assets) | 33 PNG/JPEG |
| Config files | 1 JSON |
| Total tracked files | ~155 |
