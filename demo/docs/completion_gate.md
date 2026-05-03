# Iter9 Visual Solver Demo — Completion Gate

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline for demo completion checks |
| Applies to | Iter9 Visual Solver Demo |
| Gate type | Blocking release/readiness checklist |
| Primary command | `python -m unittest discover -s tests -p "test_*.py"` |
| Primary evidence | Passing tests, committed docs, committed schemas, generated config, no forbidden files |
| Change rule | Any new runtime behavior must add or update a gate row before being called complete. |

---

## 1. Purpose

This document defines the evidence required before the Iter9 Visual Solver Demo can be called complete.

A checkbox is not enough. Every completion item must have:

```text
Gate ID
Requirement
Verification method
Evidence path or command
Failure condition
Owner
Severity
```

---

## 2. Severity Levels

| Severity | Meaning |
|---|---|
| Blocking | Must pass before implementation is accepted. |
| Advisory | Should pass, but may be deferred with written exception. |
| Manual | Requires human inspection in addition to tests. |

Unless explicitly marked otherwise, all gates are **Blocking**.

---

## 3. Approved Exception Rule

An exception is allowed only if all fields below are written in the implementation review notes:

```text
Gate ID:
Reason:
Risk:
Temporary or permanent:
Expiration condition:
Replacement verification:
Reviewer:
Date:
```

No silent exceptions are allowed.

---

## 4. Required Validation Commands

### 4.1 Standard test command

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

### 4.2 Existing Iter9 CLI smoke commands

```powershell
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
```

### 4.3 Demo schema validation behavior

The project may implement this as tests, but the required behavior is:

```text
Validate demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json as Draft 2020-12.
Validate configs/demo/iter9_visual_solver_demo.default.json against that schema.
Validate demo/docs/json_schemas/solver_event_trace.schema.json as Draft 2020-12.
Validate representative valid and invalid solver event trace rows.
```

Preferred evidence:

```text
tests/demo/iter9_visual_solver/test_config_schema_contract.py
tests/demo/iter9_visual_solver/test_event_trace_loader.py
```

---

## 5. Documentation Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| DOC-GATE-001 | Demo docs live under `demo/docs/` | Inspect repo tree or filesystem test | `demo/docs/` | Demo docs appear only in base docs folders without demo namespace | Docs owner | Blocking |
| DOC-GATE-002 | Execution plan exists | File existence check | `demo/docs/iter9_visual_solver_demo_execution_plan.md` | File missing | Planning owner | Blocking |
| DOC-GATE-003 | Generated implementation plan exists | File existence check | `demo/docs/iter9_visual_solver_demo_implementation_plan.md` | File missing | Planning owner | Blocking |
| DOC-GATE-004 | `traceability_matrix.md` exists | File existence check | `demo/docs/traceability_matrix.md` | File missing | QA owner | Blocking |
| DOC-GATE-005 | `source_modularity_standard.md` exists | File existence check | `demo/docs/source_modularity_standard.md` | File missing | Architecture owner | Blocking |
| DOC-GATE-006 | `testing_methodology.md` exists and defines every test file | Manual review + file existence | `demo/docs/testing_methodology.md` | Missing test ownership sections | Test owner | Blocking |
| DOC-GATE-007 | `architecture_decisions.md` exists and uses ADR structure | Manual review | `demo/docs/architecture_decisions.md` | ADRs lack status/context/options/risks/mitigations | Architecture owner | Blocking |
| DOC-GATE-008 | Runtime/artifact/config/playback/rendering contracts exist | File existence check | `demo/docs/*_contract.md` and `demo/docs/runtime_package_contract.md` | Required contract missing | Architecture owner | Blocking |
| DOC-GATE-009 | `acceptance_criteria.md` and `completion_gate.md` exist | File existence check | `demo/docs/acceptance_criteria.md`, `demo/docs/completion_gate.md` | File missing | QA owner | Blocking |
| DOC-GATE-010 | Schema documentation standard exists | File existence check | `demo/docs/schema_docs_specs.md` | File missing | Schema owner | Blocking |
| DOC-GATE-011 | Demo schema docs live under `demo/docs/json_schemas/` | File existence + path check | `demo/docs/json_schemas/` | Schema docs placed in `docs/json_schema/` or root `schemas/` | Schema owner | Blocking |
| DOC-GATE-012 | Demo schema README indexes schema docs | Manual review | `demo/docs/json_schemas/README.md` | Schema docs are orphaned inside the demo docs package | Docs owner | Advisory |

---

## 6. Contract Review Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| CONTRACT-GATE-001 | No unresolved `TBD`, `TODO`, or placeholder decisions in contract docs | Text scan + manual review | All demo contract docs | Contract contains unresolved placeholders | Planning owner | Blocking |
| CONTRACT-GATE-002 | Contracts do not contradict each other | Manual cross-review | Contract review notes | Same field/path/owner defined differently in two docs | Architecture owner | Blocking |
| CONTRACT-GATE-003 | Traceability matrix maps every requirement to a contract | Manual review | `traceability_matrix.md` | Any requirement lacks contract doc | QA owner | Blocking |
| CONTRACT-GATE-004 | Traceability matrix maps every requirement to source owner | Manual review | `traceability_matrix.md` | Any requirement lacks module/package owner | QA owner | Blocking |
| CONTRACT-GATE-005 | Traceability matrix maps every requirement to tests | Manual review | `traceability_matrix.md` | Any requirement lacks test coverage | QA owner | Blocking |
| CONTRACT-GATE-006 | Config fields referenced in contracts exist in schema docs | Manual/schema test | config contract + schema docs | Field mismatch | Config owner | Blocking |
| CONTRACT-GATE-007 | Artifact names referenced in contracts are documented | Manual review | artifact contract + runtime package contract | Loader uses undocumented artifact name | I/O owner | Blocking |
| CONTRACT-GATE-008 | Test methodology defines fixtures/builders/helpers before tests use them | Manual review | `testing_methodology.md` | Test references undefined support file | Test owner | Blocking |

---

## 7. Runtime Package Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| RUNTIME-GATE-001 | Demo runtime code lives under `demos/iter9_visual_solver/` | File tree inspection | `demos/iter9_visual_solver/` | Demo source created at root or unrelated package | Runtime owner | Blocking |
| RUNTIME-GATE-002 | No root-level `demo_config.py` exists | Architecture test | `test_no_root_level_demo_modules_exist` | File exists | Architecture owner | Blocking |
| RUNTIME-GATE-003 | No root-level `demo_visualizer.py` exists | Architecture test | `test_no_root_level_demo_modules_exist` | File exists | Architecture owner | Blocking |
| RUNTIME-GATE-004 | Package areas exist | File tree inspection | `cli`, `config`, `contracts`, `domain`, `io`, `playback`, `rendering`, `errors` | Required package missing | Runtime owner | Blocking |
| RUNTIME-GATE-005 | Existing root modules are not refactored as part of demo work | Git diff review | changed files list | Unapproved changes to core root modules | Architecture owner | Blocking |
| RUNTIME-GATE-006 | `run_iter9.py` hook is thin and optional | Test + diff review | `test_run_iter9_launch_hook.py` | pygame/config/playback logic added directly to `run_iter9.py` | Integration owner | Blocking |
| RUNTIME-GATE-007 | Existing `run_iter9.py --help` still works | CLI smoke command | command output/exit code | command fails | Integration owner | Blocking |
| RUNTIME-GATE-008 | Existing `run_benchmark.py --help` still works | CLI smoke command | command output/exit code | command fails | Integration owner | Blocking |
| RUNTIME-GATE-009 | Prompted wrapper resolves a completed run directory and delegates to demo CLI | Unit test + smoke command | `test_prompted_launcher.py` and prompted launcher smoke | wrapper cannot resolve artifacts, apply prompt config, or delegate | CLI owner | Blocking |

---

## 8. Config and Schema Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| CONFIG-GATE-001 | Default config exists | File existence check | `configs/demo/iter9_visual_solver_demo.default.json` | File missing | Config owner | Blocking |
| CONFIG-GATE-002 | Config JSON Schema exists | File existence check | `demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json` | File missing | Schema owner | Blocking |
| CONFIG-GATE-003 | Config schema Markdown exists | File existence check | `demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md` | File missing | Schema owner | Blocking |
| CONFIG-GATE-004 | Config schema is valid Draft 2020-12 | Schema test | `test_config_schema_contract.py` | `Draft202012Validator.check_schema` fails | Schema owner | Blocking |
| CONFIG-GATE-005 | Default config validates against schema | Schema test | `test_config_schema_contract.py` | Validation fails | Config owner | Blocking |
| CONFIG-GATE-006 | Pydantic models match schema fields | Unit/contract test | `test_config_models.py` / `test_config_schema_contract.py` | Required/default/type mismatch | Config owner | Blocking |
| CONFIG-GATE-007 | Invalid config fails before pygame starts | Unit test | `test_config_loader.py` | pygame opens or playback begins after invalid config | Config owner | Blocking |
| CONFIG-GATE-008 | Config errors identify field path | Unit test | `test_config_loader.py` | Error lacks field path | Config owner | Blocking |
| CONFIG-GATE-009 | Pydantic imports are isolated to `config/` | Architecture test | `test_pydantic_imports_are_config_only` | pydantic imported outside allowed path | Architecture owner | Blocking |
| CONFIG-GATE-010 | jsonschema is not imported by runtime | Architecture test | `test_jsonschema_not_imported_by_runtime` | runtime imports jsonschema | Architecture owner | Blocking |

---

## 9. Solver Event Trace Schema Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| TRACE-GATE-001 | Event trace schema exists | File existence check | `demo/docs/json_schemas/solver_event_trace.schema.json` | File missing | Schema owner | Blocking |
| TRACE-GATE-002 | Event trace schema Markdown exists | File existence check | `demo/docs/json_schemas/solver_event_trace.schema.md` | File missing | Schema owner | Blocking |
| TRACE-GATE-003 | Event trace schema is valid Draft 2020-12 | Schema test | schema contract test | Schema invalid | Schema owner | Blocking |
| TRACE-GATE-004 | Valid trace rows are accepted | Unit/schema test | `test_event_trace_loader.py` | Valid row rejected | I/O owner | Blocking |
| TRACE-GATE-005 | Invalid trace rows are rejected | Unit/schema test | `test_event_trace_loader.py` | Invalid row accepted | I/O owner | Blocking |
| TRACE-GATE-006 | MVP final-grid replay fallback remains supported | Unit test | `test_event_source.py` or equivalent | Missing trace blocks MVP | Playback owner | Blocking |

---

## 10. Playback Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| PLAYBACK-GATE-001 | Playback speed is calculated from validated config | Unit test | `test_speed_policy.py` | speed hardcoded or ignores config | Playback owner | Blocking |
| PLAYBACK-GATE-002 | Playback speed uses mine-count multiplier | Unit test | `test_speed_policy.py` | multiplier has no effect | Playback owner | Blocking |
| PLAYBACK-GATE-003 | Playback speed clamps to min and max | Unit test | `test_speed_policy.py` | out-of-range speed returned | Playback owner | Blocking |
| PLAYBACK-GATE-004 | pygame loop does not calculate speed formula | Architecture/source test | `test_pygame_loop_with_fakes.py`, `test_architecture_boundaries.py` | formula appears in pygame loop | Architecture owner | Blocking |
| PLAYBACK-GATE-005 | Event batching is tested independently from pygame | Unit test | `test_event_batching.py` | batching requires pygame clock | Playback owner | Blocking |
| PLAYBACK-GATE-006 | Scheduler preserves event order | Unit test | `test_event_scheduler.py` | events dropped, duplicated, or reordered | Playback owner | Blocking |
| PLAYBACK-GATE-007 | Replay state tracks mine/safe/unknown counters and playback snapshot values | Unit test | `test_replay_state.py` | counters or resolved speed snapshot wrong | Playback owner | Blocking |
| PLAYBACK-GATE-008 | Finish behavior is independent from pygame | Unit test | `test_finish_policy.py` | finish policy requires pygame loop | Playback owner | Blocking |
| PLAYBACK-GATE-009 | Default finish behavior is `stay_open` | Config + policy test | `test_config_models.py`, `test_finish_policy.py` | default closes window | Playback owner | Blocking |

---

## 11. Window and Rendering Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| RENDER-GATE-001 | Board dimensions come from `grid.shape` | Unit test | `test_board_dimensions.py` | static height/width used | Domain owner | Blocking |
| RENDER-GATE-002 | Window size is derived from board dimensions and config | Unit test | `test_window_geometry.py` | geometry ignores actual board shape | Rendering owner | Blocking |
| RENDER-GATE-003 | Status text shows actual board dimensions | Unit test | `test_status_text.py` | displays `derived-height` placeholder | Rendering owner | Blocking |
| RENDER-GATE-004 | Color palette comes from validated config | Unit test | `test_color_palette.py` | colors hardcoded in draw loop | Rendering owner | Blocking |
| RENDER-GATE-005 | Board surface maps states to configured colors | Unit test | `test_board_surface.py` | wrong state/color mapping | Rendering owner | Blocking |
| RENDER-GATE-006 | Status panel draws provided text only | Unit test | `test_status_panel.py` | status panel parses metrics or calculates text | Rendering owner | Blocking |
| RENDER-GATE-007 | pygame adapter uses injected pygame module in tests | Unit test | `test_pygame_adapter_contract.py` | real window required for unit test | Rendering owner | Blocking |
| RENDER-GATE-008 | pygame loop runs with fakes | Unit test | `test_pygame_loop_with_fakes.py` | fake-loop test cannot run | Rendering owner | Blocking |
| RENDER-GATE-009 | pygame imports are rendering-only | Architecture test | `test_pygame_imports_are_rendering_only` | pygame imported elsewhere | Architecture owner | Blocking |
| RENDER-GATE-010 | Rendering modules do not validate config | Architecture test | `test_rendering_does_not_own_config_validation` | rendering imports pydantic/jsonschema/loader | Architecture owner | Blocking |

---

## 12. I/O Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| IO-GATE-001 | Artifact paths are resolved by I/O layer | Unit test | `test_artifact_paths.py` | paths hardcoded in CLI/rendering | I/O owner | Blocking |
| IO-GATE-002 | Grid loader handles valid `.npy` grid | Unit test | `test_grid_loader.py` | valid grid fails | I/O owner | Blocking |
| IO-GATE-003 | Grid loader rejects invalid shape/type | Unit test | `test_grid_loader.py` | invalid grid accepted | I/O owner | Blocking |
| IO-GATE-004 | Metrics loader handles required fields | Unit test | `test_metrics_loader.py` | required field missing not detected | I/O owner | Blocking |
| IO-GATE-005 | Metrics/grid mismatch behavior is defined and tested | Unit/integration test | demo input validation test | mismatch silently ignored | I/O owner | Blocking |
| IO-GATE-006 | Event trace loader validates rows | Unit test | `test_event_trace_loader.py` | invalid row accepted | I/O owner | Blocking |
| IO-GATE-007 | Event trace writer writes JSONL rows | Unit test | `test_event_trace_writer.py` | invalid file format | I/O owner | Blocking |
| IO-GATE-008 | I/O modules do not import pygame | Architecture test | `test_io_modules_do_not_render` | I/O imports pygame/rendering loop | Architecture owner | Blocking |

---

## 13. Test Infrastructure Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| TEST-GATE-001 | Fixtures directory exists | File tree inspection | `tests/demo/iter9_visual_solver/fixtures/` | missing directory | Test owner | Blocking |
| TEST-GATE-002 | Builders directory exists | File tree inspection | `tests/demo/iter9_visual_solver/builders/` | missing directory | Test owner | Blocking |
| TEST-GATE-003 | Helpers directory exists | File tree inspection | `tests/demo/iter9_visual_solver/helpers/` | missing directory | Test owner | Blocking |
| TEST-GATE-004 | Config fixtures centralize config dictionaries | Modularity test/manual review | `fixtures/configs.py` | large repeated config dicts in tests | Test owner | Blocking |
| TEST-GATE-005 | Grid builders centralize grid variations | Modularity test/manual review | `builders/grid_builder.py` | large repeated grid literals | Test owner | Blocking |
| TEST-GATE-006 | pygame fakes exist | File existence + unit tests | `fixtures/pygame_fakes.py` | real pygame required for unit tests | Test owner | Blocking |
| TEST-GATE-007 | Architecture boundary tests exist | File existence | `test_architecture_boundaries.py` | missing | Architecture owner | Blocking |
| TEST-GATE-008 | Source modularity tests exist | File existence | `test_source_file_modularity.py` | missing | Architecture owner | Blocking |

---

## 14. Architecture Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| ARCH-GATE-001 | pygame imports only under approved paths | Architecture test | `test_pygame_imports_are_rendering_only` | pygame import outside allowlist | Architecture owner | Blocking |
| ARCH-GATE-002 | pydantic imports only under config | Architecture test | `test_pydantic_imports_are_config_only` | pydantic outside config | Architecture owner | Blocking |
| ARCH-GATE-003 | jsonschema not imported by runtime | Architecture test | `test_jsonschema_not_imported_by_runtime` | runtime imports jsonschema | Architecture owner | Blocking |
| ARCH-GATE-004 | Domain modules are pure | Architecture test | `test_domain_modules_are_pure` | domain imports pygame/pydantic/I/O modules | Architecture owner | Blocking |
| ARCH-GATE-005 | Playback modules do not perform I/O or rendering | Architecture test | `test_playback_modules_do_not_perform_io_or_rendering` | playback imports pygame/pathlib/json/np.load | Architecture owner | Blocking |
| ARCH-GATE-006 | I/O modules do not render | Architecture test | `test_io_modules_do_not_render` | I/O imports pygame/rendering loop | Architecture owner | Blocking |
| ARCH-GATE-007 | CLI does not draw pixels | Architecture test | `test_cli_does_not_draw_or_create_pygame_window` | CLI contains pygame display/draw/pixel loops | Architecture owner | Blocking |
| ARCH-GATE-008 | Runtime source files stay under line threshold | Modularity test | `test_demo_runtime_files_do_not_exceed_line_limit` | file > 500 lines without approved exception | Architecture owner | Blocking |
| ARCH-GATE-009 | Test files stay under line threshold | Modularity test | `test_demo_test_files_do_not_exceed_line_limit` | file > 500 lines without approved exception | Test owner | Blocking |
| ARCH-GATE-010 | Responsibility-mixing patterns are rejected | Modularity test | `test_runtime_files_do_not_mix_layer_keywords` | suspicious layer combination found | Architecture owner | Blocking |
| ARCH-GATE-011 | Test setup duplication is rejected | Modularity test | `test_tests_use_shared_fixtures_builders_helpers` | repeated large setup found | Test owner | Blocking |

---

## 15. Manual GUI Review Gates

These gates require human visual inspection.

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| MANUAL-GATE-001 | Demo opens a pygame GUI for valid Iter9 artifacts | Manual run | screenshot or reviewer note | GUI fails to open | Demo owner | Blocking |
| MANUAL-GATE-002 | Status panel displays source image, board dimensions, seed, totals, speed | Manual run | screenshot | status missing required fields | Demo owner | Blocking |
| MANUAL-GATE-003 | Board animates visibly at configured speed | Manual run | reviewer note/video optional | animation static or wrong speed | Demo owner | Blocking |
| MANUAL-GATE-004 | Final board remains open when finish mode is `stay_open` | Manual run | reviewer note | window closes | Demo owner | Blocking |
| MANUAL-GATE-005 | Flags visually represent the source image at completion | Manual inspection | screenshot | completed board does not visually match expected final grid | Demo owner | Manual |

---

## 16. Git / Modified File Review Gates

| Gate ID | Requirement | Verification | Evidence | Failure condition | Owner | Severity |
|---|---|---|---|---|---|---|
| GIT-GATE-001 | Patch does not include unrelated base-project refactor | Git diff review | changed file list | unrelated root module refactor | Reviewer | Blocking |
| GIT-GATE-002 | Generated runtime artifacts are not committed | Git status review | changed file list | `results/` artifacts included unintentionally | Reviewer | Blocking |
| GIT-GATE-003 | Docs updated with behavior changes | Git diff review | changed docs | code changed without corresponding contract/schema/test docs | Reviewer | Blocking |
| GIT-GATE-004 | Traceability matrix updated | Git diff review | `traceability_matrix.md` | new requirement/test/module missing mapping | Reviewer | Blocking |

---

## 17. Final Signoff Record

Before marking the demo complete, fill this out:

```text
Completion date:
Reviewer:
Git commit:
Test command result:
CLI smoke result:
Manual GUI review result:
Known exceptions:
Traceability matrix reviewed: yes/no
Schema docs reviewed: yes/no
Architecture boundary tests passed: yes/no
Existing Iter9 tests passed: yes/no
```

---

## 18. Final Completion Definition

The demo is complete only when:

```text
all blocking documentation gates pass,
all blocking contract gates pass,
all blocking runtime package gates pass,
all blocking config/schema gates pass,
all blocking playback/rendering/I/O gates pass,
all architecture tests pass,
all standard unittest discovery passes,
the existing Iter9 CLI smoke checks pass,
and manual GUI review confirms the visual demo behavior.
```
