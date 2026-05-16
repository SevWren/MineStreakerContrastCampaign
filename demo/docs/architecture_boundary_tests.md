# Iter9 Visual Solver Demo — Architecture Boundary Tests

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline for architecture fitness tests |
| Applies to | Iter9 Visual Solver Demo |
| Required test files | `test_architecture_boundaries.py`, `test_source_file_modularity.py` |
| Required helper file | `helpers/import_boundary_assertions.py` |
| Test framework | `unittest` |
| Primary command | `python -m unittest discover -s tests -p "test_*.py"` |
| Change rule | Any boundary weakening requires an ADR update. |

---

## 1. Purpose

This document defines exact executable architecture-boundary tests for the Iter9 Visual Solver Demo.

These tests exist because LLM-generated code tends to create shortcuts unless architecture is enforced by code.

The tests must detect:

```text
wrong files
wrong imports
wrong dependency direction
wrong ownership
large mixed-responsibility modules
duplicated test setup
pygame leakage
config validation leakage
I/O leakage into playback/rendering
```

---

## 2. Project Root and Path Normalization Rules

All tests must compute the project root from the test file location or from an explicit helper.

Required behavior:

```python
PROJECT_ROOT = Path(__file__).resolve().parents[N]
```

The helper must normalize all paths to POSIX-style relative paths for stable Windows/Linux comparison:

```python
relative = path.resolve().relative_to(project_root.resolve()).as_posix()
```

Windows backslashes must not cause false failures.

---

## 3. Runtime and Test Roots

| Name | Path |
|---|---|
| Demo runtime root | `demos/iter9_visual_solver/` |
| Demo test root | `tests/demo/iter9_visual_solver/` |
| Demo fixtures root | `tests/demo/iter9_visual_solver/fixtures/` |
| Demo builders root | `tests/demo/iter9_visual_solver/builders/` |
| Demo helpers root | `tests/demo/iter9_visual_solver/helpers/` |
| Demo docs root | `demo/docs/` |
| Demo schema docs root | `demo/docs/json_schemas/` |
| Demo config root | `configs/demo/` |

---

## 4. Required Helper API

The file below must exist:

```text
tests/demo/iter9_visual_solver/helpers/import_boundary_assertions.py
```

It must provide these helpers:

```python
iter_python_files(root: Path) -> list[Path]
relative_posix(path: Path, root: Path) -> str
parse_imports(path: Path) -> set[str]
parse_from_imports(path: Path) -> set[str]
assert_module_does_not_import(testcase, module_path: Path, forbidden_import: str) -> None
assert_package_does_not_import(testcase, package_path: Path, forbidden_import: str) -> None
assert_import_only_allowed_under(testcase, project_root: Path, import_name: str, allowed_paths: list[str]) -> None
assert_no_forbidden_root_files(testcase, project_root: Path, forbidden_names: list[str]) -> None
assert_no_file_exceeds_line_limit(testcase, root: Path, max_lines: int, allowed_exceptions: set[str]) -> None
assert_no_forbidden_text_patterns(testcase, root: Path, patterns: dict[str, list[str]], allowed_exceptions: set[str]) -> None
```

---

## 5. Import Parsing Rules

Import parsing must use Python `ast`, not only raw text.

The parser must detect:

```python
import pygame
import pygame.display
from pygame import display
from pydantic import BaseModel
import jsonschema
from demos.iter9_visual_solver.config.loader import load_demo_config
```

The parser must ignore:

```text
comments
docstrings
Markdown fenced examples in docs
string literals that are not executed imports
```

A secondary text-pattern scanner may be used for responsibility-mixing checks, but import-boundary checks must use AST parsing.

---

## 6. Approved Exception Mechanism

Architecture tests may allow exceptions only through an explicit constant in the test file:

```python
APPROVED_ARCHITECTURE_EXCEPTIONS = {
    "ARCH-RULE-ID": {
        "relative/path.py": "reason and expiration condition"
    }
}
```

Exception entries must include:

```text
rule ID
relative path
reason
expiration condition
reviewer/date if known
```

An exception without a reason must fail the test.

No broad wildcard exception is allowed.

Forbidden:

```python
APPROVED_ARCHITECTURE_EXCEPTIONS = {"*": "*"}
```

---

## 7. Test File: `test_architecture_boundaries.py`

### Required class

```python
class ArchitectureBoundariesTests(unittest.TestCase):
    ...
```

### Required tests

```text
test_no_root_level_demo_modules_exist
test_demo_runtime_root_exists_after_implementation_starts
test_pygame_imports_are_rendering_only
test_pydantic_imports_are_config_only
test_jsonschema_not_imported_by_runtime
test_domain_modules_are_pure
test_playback_modules_do_not_perform_io_or_rendering
test_rendering_does_not_own_config_validation
test_io_modules_do_not_render
test_cli_does_not_draw_or_create_pygame_window
test_run_iter9_hook_does_not_import_pygame
test_demo_docs_are_not_mixed_into_base_schema_docs
```

---

## 8. Boundary Test 1 — No Root Demo Files

| Field | Value |
|---|---|
| Rule ID | ARCH-ROOT-001 |
| Test method | `test_no_root_level_demo_modules_exist` |
| Helper | `assert_no_forbidden_root_files` |
| Applies to | repository root |
| Forbidden files | `demo_config.py`, `demo_visualizer.py`, `visual_solver_demo.py`, `iter9_visual_solver_demo.py` |
| Failure severity | Blocking |

### Failure message must include

```text
Forbidden root-level demo file exists: <relative path>
Use demos/iter9_visual_solver/ instead.
```

### Rationale

Root-level demo files encourage god-file implementation and bypass package boundaries.

---

## 9. Boundary Test 2 — Runtime Root Exists after Implementation Starts

| Field | Value |
|---|---|
| Rule ID | ARCH-PKG-001 |
| Test method | `test_demo_runtime_root_exists_after_implementation_starts` |
| Applies to | `demos/iter9_visual_solver/` |
| Failure severity | Blocking once demo source implementation begins |

### Required behavior

If any demo runtime source file exists, then the runtime package root must exist and contain:

```text
__init__.py
cli/
config/
contracts/
domain/
io/
playback/
rendering/
errors/
```

### Historical pre-implementation behavior

Before runtime implementation began, this test was allowed to skip with:

```text
Demo runtime package is not implemented yet.
```

Now that `demos/iter9_visual_solver/` exists, the package-root and package-area
checks are blocking and must pass.

---

## 10. Boundary Test 3 — pygame Import Isolation

| Field | Value |
|---|---|
| Rule ID | ARCH-IMPORT-001 |
| Test method | `test_pygame_imports_are_rendering_only` |
| Import name | `pygame` |
| Helper | `assert_import_only_allowed_under` |
| Failure severity | Blocking |

### Allowed runtime paths

```text
demos/iter9_visual_solver/rendering/
```

### Allowed test paths

```text
tests/demo/iter9_visual_solver/fixtures/pygame_fakes.py
tests/demo/iter9_visual_solver/helpers/pygame_assertions.py
tests/demo/iter9_visual_solver/test_pygame_adapter_contract.py
tests/demo/iter9_visual_solver/test_pygame_loop_with_fakes.py
```

### Forbidden runtime paths

```text
demos/iter9_visual_solver/config/
demos/iter9_visual_solver/contracts/
demos/iter9_visual_solver/domain/
demos/iter9_visual_solver/io/
demos/iter9_visual_solver/playback/
demos/iter9_visual_solver/cli/
run_iter9.py
run_benchmark.py
```

### Failure message must include

```text
pygame import found outside approved rendering/test seam: <relative path>
```

---

## 11. Boundary Test 4 — Pydantic Import Isolation

| Field | Value |
|---|---|
| Rule ID | ARCH-IMPORT-002 |
| Test method | `test_pydantic_imports_are_config_only` |
| Import name | `pydantic` |
| Failure severity | Blocking |

### Allowed runtime paths

```text
demos/iter9_visual_solver/config/
```

### Allowed test paths

```text
tests/demo/iter9_visual_solver/test_config_models.py
```

### Forbidden paths

```text
demos/iter9_visual_solver/domain/
demos/iter9_visual_solver/io/
demos/iter9_visual_solver/playback/
demos/iter9_visual_solver/rendering/
demos/iter9_visual_solver/cli/
```

### Failure message must include

```text
pydantic import found outside config package: <relative path>
```

---

## 12. Boundary Test 5 — jsonschema Runtime Exclusion

| Field | Value |
|---|---|
| Rule ID | ARCH-IMPORT-003 |
| Test method | `test_jsonschema_not_imported_by_runtime` |
| Import name | `jsonschema` |
| Failure severity | Blocking |

### Allowed paths

```text
tests/demo/iter9_visual_solver/helpers/schema_assertions.py
tests/demo/iter9_visual_solver/test_config_schema_contract.py
tests/demo/iter9_visual_solver/test_event_trace_loader.py
```

### Forbidden paths

```text
demos/iter9_visual_solver/
```

### Failure message must include

```text
jsonschema must not be imported by runtime module: <relative path>
```

### Rationale

Runtime validation is owned by Pydantic config models. jsonschema validates committed schema artifacts in tests.

---

## 13. Boundary Test 6 — Domain Purity

| Field | Value |
|---|---|
| Rule ID | ARCH-DOMAIN-001 |
| Test method | `test_domain_modules_are_pure` |
| Applies to | `demos/iter9_visual_solver/domain/` |
| Failure severity | Blocking |

### Forbidden imports

```text
pygame
pydantic
jsonschema
pathlib
os
sys
json
```

### Conditionally allowed imports

```text
numpy
```

NumPy is allowed only when needed for typed grid/domain shape handling. If used, the domain file must not call:

```text
np.load
np.save
```

### Failure message must include

```text
domain module imports forbidden dependency <dependency>: <relative path>
```

### Rationale

Domain files model data and pure rules. They must not perform I/O, config validation, or rendering.

---

## 14. Boundary Test 7 — Playback Isolation

| Field | Value |
|---|---|
| Rule ID | ARCH-PLAYBACK-001 |
| Test method | `test_playback_modules_do_not_perform_io_or_rendering` |
| Applies to | `demos/iter9_visual_solver/playback/` |
| Failure severity | Blocking |

### Forbidden imports

```text
pygame
pathlib
json
os
sys
```

### Forbidden text patterns

```text
np.load
np.save
open(
Path(
pygame.
display.
```

### Failure message must include

```text
playback module performs I/O or rendering responsibility: <relative path>
```

### Rationale

Playback owns speed, batching, scheduling, replay state, and finish behavior. It does not load files and does not render.

---

## 15. Boundary Test 8 — Rendering Does Not Validate Config

| Field | Value |
|---|---|
| Rule ID | ARCH-RENDER-001 |
| Test method | `test_rendering_does_not_own_config_validation` |
| Applies to | `demos/iter9_visual_solver/rendering/` |
| Failure severity | Blocking |

### Forbidden imports

```text
pydantic
jsonschema
demos.iter9_visual_solver.config.loader
```

### Forbidden text patterns

```text
model_validate
validate_json
json.load
open(
```

### Allowed

Rendering may consume:

```text
validated config object
plain color tuple
plain window geometry settings
status snapshot object
```

### Failure message must include

```text
rendering module owns config validation/loading responsibility: <relative path>
```

---

## 16. Boundary Test 9 — I/O Does Not Render

| Field | Value |
|---|---|
| Rule ID | ARCH-IO-001 |
| Test method | `test_io_modules_do_not_render` |
| Applies to | `demos/iter9_visual_solver/io/` |
| Failure severity | Blocking |

### Forbidden imports

```text
pygame
demos.iter9_visual_solver.rendering.pygame_loop
demos.iter9_visual_solver.rendering.pygame_adapter
```

### Forbidden text patterns

```text
pygame.
display.
draw.
blit
```

### Failure message must include

```text
I/O module imports or performs rendering responsibility: <relative path>
```

---

## 17. Boundary Test 10 — CLI Does Not Draw Pixels

| Field | Value |
|---|---|
| Rule ID | ARCH-CLI-001 |
| Test method | `test_cli_does_not_draw_or_create_pygame_window` |
| Applies to | `demos/iter9_visual_solver/cli/` |
| Failure severity | Blocking |

### Forbidden imports

```text
pygame
```

### Forbidden text patterns

```text
pygame.draw
pygame.display.set_mode
surfarray
set_at(
get_at(
for y in range
for x in range
```

### Allowed

CLI may call a high-level demo runner/orchestrator function.

### Failure message must include

```text
CLI module contains rendering/pixel drawing responsibility: <relative path>
```

---

## 18. Boundary Test 11 — `run_iter9.py` Hook Does Not Import pygame

| Field | Value |
|---|---|
| Rule ID | ARCH-INTEGRATION-001 |
| Test method | `test_run_iter9_hook_does_not_import_pygame` |
| Applies to | `run_iter9.py` |
| Failure severity | Blocking |

### Forbidden imports

```text
pygame
pydantic
jsonschema
```

### Forbidden text patterns

```text
pygame.
calculate_events_per_second
DemoConfig
model_validate
```

### Allowed

```text
from demos.iter9_visual_solver.cli.launch_from_iter9 import ...
```

or an equivalent lazy import inside the demo flag branch.

### Failure message must include

```text
run_iter9.py contains demo runtime responsibility instead of thin launch hook.
```

---

## 19. Boundary Test 12 — Demo Docs Are Not Mixed into Base Schema Docs

| Field | Value |
|---|---|
| Rule ID | ARCH-DOCS-001 |
| Test method | `test_demo_docs_are_not_mixed_into_base_schema_docs` |
| Applies to | `demo/docs/` plus forbidden legacy schema roots |
| Failure severity | Blocking |

### Required demo schema path

```text
demo/docs/json_schemas/
```

### Forbidden demo schema paths

```text
docs/json_schema/iter9_visual_solver_demo_config.schema.json
docs/json_schema/solver_event_trace.schema.json
schemas/iter9_visual_solver_demo_config.schema.json
schemas/solver_event_trace.schema.json
```

### Failure message must include

```text
Demo schema file found outside demo/docs/json_schemas/: <relative path>
```

---

## 20. Test File: `test_source_file_modularity.py`

### Required class

```python
class SourceFileModularityTests(unittest.TestCase):
    ...
```

### Required tests

```text
test_demo_runtime_files_do_not_exceed_line_limit
test_demo_test_files_do_not_exceed_line_limit
test_runtime_files_do_not_mix_layer_keywords
test_tests_use_shared_fixtures_builders_helpers
test_no_large_inline_config_dicts_outside_config_fixtures
test_no_large_inline_grid_literals_outside_grid_fixtures_or_builders
```

---

## 21. Modularity Test 1 — Runtime File Line Limit

| Field | Value |
|---|---|
| Rule ID | ARCH-SIZE-001 |
| Test method | `test_demo_runtime_files_do_not_exceed_line_limit` |
| Applies to | `demos/iter9_visual_solver/**/*.py` |
| Failure severity | Blocking |

### Thresholds

```text
Review threshold: 300 physical lines
Blocking threshold: 500 physical lines
```

### Allowed exceptions

Only:

```text
generated files
data-only generated constants
explicitly approved exception with reason
```

### Failure message must include

```text
Runtime file exceeds 500-line smoke alarm: <relative path> has <N> lines.
Split by ownership before continuing.
```

---

## 22. Modularity Test 2 — Test File Line Limit

| Field | Value |
|---|---|
| Rule ID | ARCH-SIZE-002 |
| Test method | `test_demo_test_files_do_not_exceed_line_limit` |
| Applies to | `tests/demo/iter9_visual_solver/**/*.py` |
| Failure severity | Blocking |

### Thresholds

```text
Review threshold: 300 physical lines
Blocking threshold: 500 physical lines
```

### Failure message must include

```text
Test file exceeds 500-line smoke alarm: <relative path> has <N> lines.
Move setup to fixtures/builders/helpers.
```

---

## 23. Modularity Test 3 — Responsibility-Mixing Keyword Patterns

| Field | Value |
|---|---|
| Rule ID | ARCH-MIX-001 |
| Test method | `test_runtime_files_do_not_mix_layer_keywords` |
| Applies to | `demos/iter9_visual_solver/**/*.py` |
| Failure severity | Blocking |

### Forbidden combinations

A file fails if it contains both sides of any pair below, unless explicitly approved:

| Pair ID | Forbidden combination |
|---|---|
| MIX-001 | `pygame` + `json.load` |
| MIX-002 | `pygame` + `pydantic` |
| MIX-003 | `pygame` + `calculate_events_per_second` |
| MIX-004 | `np.load` + `pygame.display` |
| MIX-005 | `json.load` + `pygame.display` |
| MIX-006 | `model_validate` + `pygame` |
| MIX-007 | `argparse` + `pygame.draw` |
| MIX-008 | `Path(` + `pygame.display.set_mode` |

### Failure message must include

```text
Runtime file mixes architecture layers: <relative path> matched <Pair ID>.
```

---

## 24. Modularity Test 4 — Tests Use Shared Fixtures, Builders, and Helpers

| Field | Value |
|---|---|
| Rule ID | ARCH-TEST-001 |
| Test method | `test_tests_use_shared_fixtures_builders_helpers` |
| Applies to | `tests/demo/iter9_visual_solver/test_*.py` |
| Failure severity | Blocking |

### Repetition patterns to flag

| Pattern | Expected home |
|---|---|
| Large `schema_version` config dictionaries | `fixtures/configs.py` or `builders/config_builder.py` |
| Repeated NumPy array grid literals | `fixtures/grids.py` or `builders/grid_builder.py` |
| Repeated metrics dictionaries | `fixtures/metrics.py` or `builders/metrics_builder.py` |
| Repeated JSONL event strings | `fixtures/event_traces.py` or `builders/event_trace_builder.py` |
| Repeated pygame fake classes | `fixtures/pygame_fakes.py` |
| Repeated AST import scan helpers | `helpers/import_boundary_assertions.py` |

### Failure message must include

```text
Test file duplicates setup that belongs in shared test support: <relative path>
```

---

## 25. Modularity Test 5 — No Large Inline Config Dictionaries

| Field | Value |
|---|---|
| Rule ID | ARCH-TEST-002 |
| Test method | `test_no_large_inline_config_dicts_outside_config_fixtures` |
| Applies to | demo test files |
| Failure severity | Blocking |

### Allowed paths

```text
tests/demo/iter9_visual_solver/fixtures/configs.py
tests/demo/iter9_visual_solver/builders/config_builder.py
```

### Detection heuristic

Flag a test file outside allowed paths if it contains at least three of:

```text
schema_version
window
playback
visuals
status_panel
finish_behavior
```

### Failure message must include

```text
Large inline demo config found outside config fixture/builder: <relative path>
```

---

## 26. Modularity Test 6 — No Large Inline Grid Literals

| Field | Value |
|---|---|
| Rule ID | ARCH-TEST-003 |
| Test method | `test_no_large_inline_grid_literals_outside_grid_fixtures_or_builders` |
| Applies to | demo test files |
| Failure severity | Blocking |

### Allowed paths

```text
tests/demo/iter9_visual_solver/fixtures/grids.py
tests/demo/iter9_visual_solver/builders/grid_builder.py
```

### Detection heuristic

Flag files outside allowed paths containing suspicious repeated grid literals:

```text
np.array([
[[1, 0
[[0, 1
dtype=np.uint8
```

### Failure message must include

```text
Large inline grid setup found outside grid fixture/builder: <relative path>
```

---

## 27. Recommended Implementation Skeleton for Architecture Tests

```python
from __future__ import annotations

import unittest
from pathlib import Path

from tests.demo.iter9_visual_solver.helpers.import_boundary_assertions import (
    assert_import_only_allowed_under,
    assert_no_file_exceeds_line_limit,
    assert_no_forbidden_root_files,
    assert_no_forbidden_text_patterns,
    assert_package_does_not_import,
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]

class ArchitectureBoundariesTests(unittest.TestCase):
    def test_no_root_level_demo_modules_exist(self):
        assert_no_forbidden_root_files(
            self,
            PROJECT_ROOT,
            [
                "demo_config.py",
                "demo_visualizer.py",
                "visual_solver_demo.py",
                "iter9_visual_solver_demo.py",
            ],
        )
```

This skeleton is illustrative. The actual tests must implement every rule in this document.

---

## 28. Required Failure Message Quality

Every failure must tell the implementer:

```text
what rule failed
which file failed
which dependency/pattern caused failure
where the responsibility belongs instead
```

Bad failure:

```text
AssertionError: pygame found
```

Good failure:

```text
ARCH-IMPORT-001 failed:
pygame import found outside approved rendering/test seam:
demos/iter9_visual_solver/playback/event_scheduler.py

Move pygame usage to:
demos/iter9_visual_solver/rendering/pygame_loop.py
```

---

## 29. Completion Checklist

- [ ] `test_architecture_boundaries.py` exists.
- [ ] `test_source_file_modularity.py` exists.
- [ ] `helpers/import_boundary_assertions.py` exists.
- [ ] Import parser uses AST.
- [ ] Windows paths normalize correctly.
- [ ] pygame isolation test exists and has exact allowlist.
- [ ] Pydantic isolation test exists and has exact allowlist.
- [ ] jsonschema runtime exclusion test exists.
- [ ] Domain purity test exists.
- [ ] Playback isolation test exists.
- [ ] Rendering/config separation test exists.
- [ ] I/O/rendering separation test exists.
- [ ] CLI no-pixel-drawing test exists.
- [ ] `run_iter9.py` thin-hook test exists.
- [ ] Demo schema path test exists.
- [ ] Runtime file line-count test exists.
- [ ] Test file line-count test exists.
- [ ] Responsibility-mixing pattern test exists.
- [ ] Test setup duplication guard exists.
- [ ] Approved exception mechanism exists and rejects empty reasons.
- [ ] All failures include actionable messages.

---

## 30. Optimization Boundary Rules

Runtime optimization must preserve the same import boundaries:

- typed event stores may import NumPy but must not import pygame, pathlib file
  loading, JSON loading, or config models.
- event trace streaming belongs in `io/event_trace_loader.py`, not playback.
- dirty board-surface rendering belongs in `rendering/board_surface.py`, not
  playback or I/O.
- status view-model caching belongs in `rendering/status_view_model.py` and
  must remain pygame-free.
- `pygame_loop.py` may orchestrate cached objects but must not own typed trace
  parsing, final-grid event generation, or playback-speed formulas.

Architecture tests must continue to pass after optimization changes.
