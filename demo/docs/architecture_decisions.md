# Iter9 Visual Solver Demo — Architecture Decisions

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline for demo planning |
| Applies to | Iter9 Visual Solver Demo only |
| Runtime package | `demos/iter9_visual_solver/` |
| Documentation package | `demo/docs/` |
| Schema documentation package | `demo/docs/json_schemas/` |
| Test package | `tests/demo/iter9_visual_solver/` |
| Primary audience | Human reviewer, LLM implementation agent, future maintainer |
| Change rule | Any behavior-changing implementation patch must either follow these ADRs or add a new ADR that supersedes the old one. |

---

## 1. Purpose

This document records architecture decisions for the Iter9 Visual Solver Demo. It exists to prevent future implementation agents, especially LLM agents, from silently changing architecture, collapsing module boundaries, or treating temporary shortcuts as acceptable design.

---

## 2. Scope Boundary

These ADRs apply to the demo package only:

```text
demos/iter9_visual_solver/
tests/demo/iter9_visual_solver/
demo/docs/
configs/demo/
```

These ADRs do **not** authorize a refactor of the existing base project root modules:

```text
core.py
sa.py
solver.py
corridors.py
repair.py
report.py
pipeline.py
board_sizing.py
source_config.py
run_iter9.py
run_benchmark.py
```

The existing project remains a root-module research codebase. The visual solver demo is an additive optional package layered beside the existing pipeline.

---

## 3. ADR Status Values

| Status | Meaning |
|---|---|
| Proposed | Candidate decision not yet approved. |
| Accepted | Approved and binding for implementation. |
| Superseded | Replaced by a newer ADR. |
| Deprecated | Still present but should not guide new work. |
| Rejected | Considered and intentionally not chosen. |

All ADRs in this document are currently **Accepted** unless explicitly marked otherwise.

---

## 4. Required ADR Template for Future Decisions

Future ADRs must use this structure:

```markdown
## ADR-###: Title

| Field | Value |
|---|---|
| Status | Proposed / Accepted / Superseded / Deprecated / Rejected |
| Date | YYYY-MM-DD |
| Owner | Person or role |
| Decision scope | Runtime / docs / tests / schema / CLI / integration |
| Traceability IDs | DEMO-REQ-###, DEMO-CONTRACT-###, DEMO-TEST-### |

### Context
### Decision Drivers
### Options Considered
### Decision
### Consequences
### Risks
### Mitigations
### Implementation Impact
### Testing Impact
### Documentation Impact
### Supersession Rule
```

---

## 5. Decision Index

| ADR | Decision | Status | Primary impact |
|---|---|---|---|
| ADR-001 | Use pygame for GUI rendering | Accepted | Rendering/runtime |
| ADR-002 | Use Pydantic v2 and jsonschema for config/schema validation | Accepted | Config/schema/tests |
| ADR-003 | Implement the demo as an additive durable runtime package | Accepted | Source layout |
| ADR-004 | Human contracts precede executable contract code | Accepted | LLM development sequence |
| ADR-005 | Store demo schema specs/docs under `demo/docs/json_schemas/` | Accepted | Documentation layout |
| ADR-006 | MVP uses final-grid replay before true solver trace replay | Accepted | Playback/input strategy |
| ADR-007 | Architecture fitness tests are required before broad implementation | Accepted | Test strategy |
| ADR-008 | Use fixture-builder-helper testing architecture | Accepted | Test maintainability |
| ADR-009 | Keep `run_iter9.py` integration thin and optional | Accepted | Integration safety |
| ADR-010 | Use config-driven playback and finish behavior | Accepted | Runtime behavior |
| ADR-011 | Keep pygame isolated behind adapter/rendering seams | Accepted | Testability and architecture |
| ADR-012 | Treat line count as smoke alarm, not design method | Accepted | Modularity |

---

## ADR-001: Use pygame for GUI Rendering

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Demo architecture |
| Decision scope | Runtime rendering |
| Traceability IDs | DEMO-REQ-010, DEMO-REQ-011, DEMO-TEST-020, DEMO-TEST-021 |

### Context

The demo needs to show a large Minesweeper-derived board as fast visual playback. The core interaction is high-speed 2D board animation with a status panel. The demo does not require a form-heavy desktop UI, docking panels, or user-driven workflows.

### Decision Drivers

- Fast 2D pixel/surface drawing.
- Simple event loop.
- Easy animation at controlled frame rates.
- Good fit for NumPy-backed grid data.
- Lower implementation complexity than a full GUI framework.
- Sufficient for a non-interactive MVP.

### Options Considered

| Option | Result | Reason |
|---|---|---|
| pygame | Accepted | Best fit for simple fast 2D animation. |
| Tkinter | Rejected | Easier widgets, weaker fast grid animation model. |
| PyQt/PySide | Rejected | Too heavy for MVP and increases packaging complexity. |
| Dear PyGui | Rejected for MVP | Powerful but unnecessary for a no-controls visual demo. |
| Browser UI | Rejected for MVP | Adds web server/frontend complexity. |

### Decision

Use:

```text
pygame
numpy
```

for the visual solver demo GUI.

### Consequences

- pygame imports are allowed only under `demos/iter9_visual_solver/rendering/`.
- Tests must use pygame fakes before any real-window smoke testing.
- Rendering modules must not own config validation, artifact loading, or playback policy math.
- The pygame event loop is a thin imperative shell.

### Risks

- pygame can become a god module if playback, config, and drawing are mixed.
- Headless test environments may not support real windows.
- LLM agents may place pygame imports in CLI or playback modules.

### Mitigations

- `architecture_boundary_tests.md` defines pygame import isolation.
- `pygame_adapter.py` isolates pygame primitives.
- `pygame_fakes.py` supports tests without opening a real window.
- `pygame_loop.py` orchestrates only already-tested policies and render helpers.

### Implementation Impact

Required modules:

```text
demos/iter9_visual_solver/rendering/pygame_adapter.py
demos/iter9_visual_solver/rendering/pygame_loop.py
demos/iter9_visual_solver/rendering/board_surface.py
demos/iter9_visual_solver/rendering/status_panel.py
```

### Testing Impact

Required tests:

```text
tests/demo/iter9_visual_solver/test_pygame_adapter_contract.py
tests/demo/iter9_visual_solver/test_pygame_loop_with_fakes.py
tests/demo/iter9_visual_solver/test_architecture_boundaries.py
```

### Documentation Impact

Affected docs:

```text
pygame_rendering_contract.md
architecture_boundary_tests.md
testing_methodology.md
completion_gate.md
```

### Supersession Rule

A future ADR must supersede this ADR before replacing pygame with another rendering stack.

---

## ADR-002: Use Pydantic v2 and jsonschema for Config/Schema Validation

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Config/schema architecture |
| Decision scope | Config, schema, tests |
| Traceability IDs | DEMO-REQ-002, DEMO-REQ-008, DEMO-REQ-011 |

### Context

The demo requires a user-editable JSON config file controlling playback speed, finish behavior, colors, window sizing, and input fallback behavior. The config needs runtime validation and committed schema documentation.

### Decision Drivers

- Runtime validation must produce clear errors.
- JSON schema must validate committed config artifacts.
- Human-readable schema docs must be maintained beside schema files.
- Config rules must not be duplicated inside rendering or playback code.

### Options Considered

| Option | Result | Reason |
|---|---|---|
| Pydantic v2 + jsonschema | Accepted | Strong runtime models plus independent schema validation. |
| jsonschema only | Rejected | Weaker runtime developer ergonomics and typed access. |
| Pydantic only | Rejected | Does not independently test committed schema artifacts. |
| Manual validation | Rejected | Too error-prone and likely to drift. |

### Decision

Use:

```text
pydantic v2
jsonschema
```

Pydantic owns runtime config models. jsonschema owns schema contract tests.

### Consequences

- Pydantic imports are allowed only in `demos/iter9_visual_solver/config/`.
- jsonschema imports are allowed only in schema tests/helpers.
- Config fields must identify their runtime owner.
- Rendering receives validated config values, not raw dictionaries.

### Risks

- Pydantic model and JSON Schema can drift.
- LLM agents may validate config inside rendering modules.
- Schema docs may become stale.

### Mitigations

- `test_config_schema_contract.py` validates default config against schema.
- Completion gate requires model/schema field alignment.
- Schema Markdown docs must document every field.

### Implementation Impact

Required modules:

```text
config/models.py
config/loader.py
config/schema_export.py
config/validation_errors.py
```

### Testing Impact

Required tests:

```text
test_config_models.py
test_config_loader.py
test_config_schema_contract.py
test_architecture_boundaries.py
```

### Documentation Impact

Affected docs:

```text
config_contract.md
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md
schema_docs_specs.md
```

### Supersession Rule

Any change to config tooling requires a superseding ADR and migration notes.

---

## ADR-003: Implement the Demo as an Additive Durable Runtime Package

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Source architecture |
| Decision scope | Source layout |
| Traceability IDs | DEMO-REQ-009, DEMO-REQ-013, DEMO-REQ-014 |

### Context

The base repository currently uses root-level runtime modules. The demo is optional UI/demo functionality and should not be implemented as root-level ad hoc scripts.

### Decision Drivers

- Avoid short-term files that become unplanned architecture.
- Keep demo-specific runtime isolated.
- Do not refactor the base project merely to add the demo.
- Allow the demo to be tested and evolved independently.

### Options Considered

| Option | Result | Reason |
|---|---|---|
| `demos/iter9_visual_solver/` package | Accepted | Clean additive isolation. |
| root `demo_visualizer.py` | Rejected | Encourages god-file implementation. |
| merge into `run_iter9.py` | Rejected | Pollutes pipeline entrypoint with demo behavior. |
| refactor entire project into packages first | Rejected | Not required and too disruptive. |

### Decision

The demo runtime package is:

```text
demos/iter9_visual_solver/
```

This is an additive exception to the current root-module project structure.

### Consequences

- Existing root runtime modules stay where they are.
- `run_iter9.py` receives only a thin optional hook.
- Architecture tests reject root-level demo modules.
- Demo code can import existing root modules only through explicit integration seams.

### Risks

- LLM agents may interpret this as a whole-project refactor.
- The demo package may accidentally duplicate pipeline logic.

### Mitigations

- This ADR explicitly forbids base-project refactor as part of demo work.
- Runtime package contract defines boundaries.
- Completion gate checks for root ad hoc files.

### Implementation Impact

Required package areas:

```text
cli/
config/
contracts/
domain/
io/
playback/
rendering/
errors/
```

### Testing Impact

Required tests:

```text
test_architecture_boundaries.py
test_source_file_modularity.py
test_run_iter9_launch_hook.py
```

### Documentation Impact

Affected docs:

```text
runtime_package_contract.md
source_modularity_standard.md
completion_gate.md
```

### Supersession Rule

A repository-wide refactor requires a separate approved architecture plan and must not be implied by this demo ADR.

---

## ADR-004: Human Contracts Precede Executable Contract Code

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | LLM development governance |
| Decision scope | Planning, docs, implementation sequence |
| Traceability IDs | DEMO-REQ-001 through DEMO-REQ-014 |

### Context

LLM-assisted implementation can easily invent constants, modules, and behavior before requirements are locked. This creates false authority in code.

### Decision Drivers

- Prevent contract code from becoming guessed behavior.
- Force unknowns into documentation first.
- Make implementation modules mirror approved docs.
- Preserve traceability from requirement to test.

### Options Considered

| Option | Result | Reason |
|---|---|---|
| Human contract docs first | Accepted | Safest for LLM-driven development. |
| Code constants first | Rejected | Constants would be guesses. |
| Tests first without contracts | Rejected | Tests would encode unreviewed assumptions. |
| Prototype first, document later | Rejected | High risk of cementing bad architecture. |

### Decision

The sequence is:

```text
dedicated demo contract set under demo/docs/
-> contradiction review
-> traceability matrix
-> test support and architecture gates
-> executable contract constants
-> runtime modules
```

### Consequences

- `contracts/*.py` files are not first deliverables.
- Every runtime module must have a matching contract.
- LLM tasks must reference contract docs.

### Risks

- Planning phase is longer.
- Over-documentation can become stale if not tied to tests.

### Mitigations

- Traceability matrix maps docs to tests.
- Completion gate requires contradiction review.
- Architecture tests enforce key contract decisions.

### Implementation Impact

Executable constants must mirror approved docs:

```text
contracts/artifact_names.py
contracts/schema_versions.py
contracts/defaults.py
```

### Testing Impact

Architecture and contract tests must fail if executable constants drift from docs/schema.

### Documentation Impact

Affected docs:

```text
iter9_visual_solver_demo_execution_plan.md
iter9_visual_solver_demo_implementation_plan.md
acceptance_criteria.md
traceability_matrix.md
completion_gate.md
```

### Supersession Rule

No implementation agent may bypass this sequence without a new ADR.

---

## ADR-005: Store Demo Schema Specs and Docs under `demo/docs/json_schemas/`

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Documentation/schema architecture |
| Decision scope | Documentation layout |
| Traceability IDs | DEMO-REQ-008 |

### Context

The base project already has its own docs and schema documentation. The demo needs separate schema specs and Markdown schema docs.

### Decision Drivers

- Keep demo docs separate from base-project docs.
- Avoid mixing optional demo schema with core runtime schemas.
- Make schema path ownership unambiguous.

### Options Considered

| Option | Result | Reason |
|---|---|---|
| `demo/docs/json_schemas/` | Accepted | Clear demo ownership. |
| `docs/json_schema/` | Rejected | Mixes demo docs with base project schema docs. |
| root `schemas/` | Rejected | Not aligned with current docs structure. |
| `demos/iter9_visual_solver/schemas/` | Rejected | Runtime package should not own documentation docs. |

### Decision

Demo schema specs and Markdown docs live under:

```text
demo/docs/json_schemas/
```

### Consequences

Required files:

```text
README.md
iter9_visual_solver_demo_config.schema.json
iter9_visual_solver_demo_config.schema.md
solver_event_trace.schema.json
solver_event_trace.schema.md
```

### Risks

- Developers may look in the base `docs/json_schema/` folder.
- Schema docs may be duplicated.

### Mitigations

- `demo/docs/json_schemas/README.md` indexes demo schema docs.
- Completion gate rejects schema docs in wrong folders.
- Schema contract tests check the path.

### Supersession Rule

Any schema relocation requires a docs-index update and a superseding ADR.

---

## ADR-006: MVP Uses Final-Grid Replay before True Solver Trace Replay

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Playback/input architecture |
| Decision scope | Playback strategy |
| Traceability IDs | DEMO-REQ-006, DEMO-REQ-007 |

### Context

The existing Iter9 pipeline already produces final grid artifacts. A true solver-event trace would require additional instrumentation.

### Decision Drivers

- Create MVP value without modifying solver internals first.
- Preserve a future path to true event-order replay.
- Keep renderer independent from event source.

### Options Considered

| Option | Result | Reason |
|---|---|---|
| final-grid replay for MVP | Accepted | Fastest useful demo with existing artifacts. |
| true solver trace first | Deferred | Requires new instrumentation. |
| static final image only | Rejected | Does not demonstrate solving playback. |
| fake random animation | Rejected | Misrepresents solver/demo behavior. |

### Decision

MVP uses final-grid replay. Future v2 supports:

```text
solver_event_trace.jsonl
```

### Consequences

- `event_source.py` normalizes final-grid replay and trace replay into the same event model.
- Renderer consumes playback events without knowing their source.
- Schema docs for solver trace still exist to support future work.

### Risks

- MVP playback order is not true solver order.
- Users may interpret final-grid replay as actual solve chronology.

### Mitigations

- User guide and technical spec must label MVP as final-grid replay.
- Config field `prefer_solver_event_trace` supports future trace preference.
- Status panel may indicate replay source if required by contract.

### Supersession Rule

When solver trace instrumentation exists, a new ADR may change the default replay source.

---

## ADR-007: Architecture Fitness Tests Are Required before Broad Implementation

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Test architecture |
| Decision scope | Test strategy |
| Traceability IDs | DEMO-REQ-010, DEMO-REQ-011, DEMO-REQ-012 |

### Context

LLM-generated code tends to collapse boundaries unless boundaries are executable.

### Decision Drivers

- Prevent pygame leakage.
- Prevent config validation in rendering.
- Prevent domain modules from performing I/O.
- Prevent root-level demo scripts.
- Detect file-size and responsibility drift.

### Decision

Create architecture tests early:

```text
test_architecture_boundaries.py
test_source_file_modularity.py
```

### Consequences

These tests are blocking. They run with normal unittest discovery.

### Risks

- False positives can slow implementation.
- Bad exception lists can weaken the tests.

### Mitigations

- Exception mechanism must be explicit.
- Test failure messages must show exact offending file and rule.
- Approved exceptions require documented rationale.

### Supersession Rule

Removing or weakening an architecture boundary requires an ADR.

---

## ADR-008: Use Fixture-Builder-Helper Testing Architecture

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Test maintainability |
| Decision scope | Tests |
| Traceability IDs | DEMO-REQ-012 |

### Context

The demo requires many config, grid, metrics, trace, and pygame-loop tests. Without shared test support, LLM agents will duplicate setup.

### Decision

Tests use three support categories:

```text
fixtures = ready-made common objects
builders = controlled variation objects
helpers = reusable assertions/actions
```

### Consequences

Required directories:

```text
fixtures/
builders/
helpers/
```

### Risks

- Support files can become dumping grounds.
- Test authors may bypass them.

### Mitigations

- `testing_methodology.md` defines exact contents of every support file.
- Source modularity tests detect repeated inline setup.

### Supersession Rule

Alternative test architecture requires updating `testing_methodology.md` and a superseding ADR.

---

## ADR-009: Keep `run_iter9.py` Integration Thin and Optional

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Integration safety |
| Decision scope | CLI/integration |
| Traceability IDs | DEMO-REQ-013 |

### Context

`run_iter9.py` is the primary existing Iter9 pipeline entrypoint. The demo must not destabilize existing command behavior.

### Decision

`run_iter9.py` may only:

```text
add --demo-gui
add --demo-config
call demos.iter9_visual_solver.cli.launch_from_iter9
```

It must not:

```text
import pygame
parse demo config directly
calculate playback speed
draw GUI
own demo runtime behavior
```

### Consequences

- Existing behavior is unchanged when demo flags are omitted.
- Demo launch orchestration lives in the demo package.
- Integration tests check flag absence and thin hook behavior.

### Risks

- LLM agents may insert demo logic directly into `run_iter9.py`.

### Mitigations

- Architecture tests scan `run_iter9.py` for pygame and direct demo logic.
- Completion gate requires existing Iter9 tests to pass.

### Supersession Rule

Any broader `run_iter9.py` integration requires a dedicated integration ADR.

---

## ADR-010: Use Config-Driven Playback and Finish Behavior

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Runtime behavior |
| Decision scope | Playback/config |
| Traceability IDs | DEMO-REQ-002, DEMO-REQ-004, DEMO-REQ-005 |

### Context

Playback speed and finish behavior must not be hardcoded. The user needs dynamic speeds and a finish mode that can stay open after playback ends.

### Decision

Playback speed is derived from config. Finish behavior is derived from config.

Required finish modes:

```text
stay_open
close_immediately
close_after_delay
```

Default:

```text
stay_open
```

### Consequences

- `speed_policy.py` owns speed calculation.
- `finish_policy.py` owns close/stay-open behavior.
- pygame loop consumes policy results only.

### Risks

- Renderer may accidentally own policy logic.
- Config/schema/model fields may drift.

### Mitigations

- Config schema contract tests.
- Architecture tests reject `calculate_events_per_second` in pygame loop.
- Unit tests cover finish policy independently from pygame.

### Supersession Rule

Any hardcoded playback or finish behavior violates this ADR.

---

## ADR-011: Keep pygame Isolated Behind Adapter/Rendering Seams

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Rendering architecture |
| Decision scope | Testability |
| Traceability IDs | DEMO-REQ-010 |

### Context

pygame is useful for rendering but unsafe as a dependency in pure logic.

### Decision

pygame access goes through:

```text
rendering/pygame_adapter.py
rendering/pygame_loop.py
```

Pure rendering helpers do not need to create windows.

### Consequences

- pygame loop tests use injected fake pygame.
- Board surface/status text can be tested independently.
- CLI/playback/config/domain stay pygame-free.

### Risks

- Adapter becomes too broad.
- pygame loop becomes an orchestration god file.

### Mitigations

- Public API budget.
- Source file line-count smoke alarms.
- Responsibility-mixing tests.

### Supersession Rule

Direct pygame usage outside rendering requires a new ADR.

---

## ADR-012: Treat Line Count as a Smoke Alarm, Not the Design Method

| Field | Value |
|---|---|
| Status | Accepted |
| Date | 2026-05-01 |
| Owner | Source modularity |
| Decision scope | Architecture/testing |
| Traceability IDs | DEMO-REQ-012 |

### Context

A static 500-line cap alone is insufficient. Files stay small because ownership boundaries are narrow.

### Decision

Use architectural methods first:

```text
change-axis decomposition
one-abstraction-level-per-file
functional-core / imperative-shell split
policy extraction
adapter boundaries
fixture-builder-helper testing
architecture fitness tests
```

Line count is a smoke alarm only.

### Consequences

- Files over 300 lines require review.
- Files over 500 lines fail unless generated/data-only/approved exception.
- A file may be split earlier because of responsibility drift even if under 500 lines.

### Risks

- LLM agents may treat 500 lines as permission to create large files.
- Tests may enforce line count without checking responsibility.

### Mitigations

- `source_modularity_standard.md` defines split triggers.
- `test_source_file_modularity.py` checks responsibility-mixing patterns.

### Supersession Rule

Any policy replacing this must preserve proactive modular design methods, not only line caps.

---

## 6. ADR Completion Checklist

Before implementation begins:

- [ ] Every ADR has status, scope, owner, and traceability IDs.
- [ ] Every ADR has options considered.
- [ ] Every ADR has risks and mitigations.
- [ ] Every ADR has implementation and testing impact.
- [ ] No ADR implies refactoring the base project unless explicitly scoped.
- [ ] Every ADR is represented in `traceability_matrix.md`.
- [ ] Every architecture boundary from these ADRs is represented in `architecture_boundary_tests.md`.
- [ ] Every completion requirement from these ADRs is represented in `completion_gate.md`.

---

## 7. LLM Implementation Instruction

An LLM implementation task must cite the relevant ADR IDs before touching source code.

Valid instruction:

```text
Implement `playback/speed_policy.py` under ADR-010 and ADR-012.
Do not import pygame.
Do not edit run_iter9.py.
Use tests from test_speed_policy.py.
```

Invalid instruction:

```text
Implement the visual demo.
```
