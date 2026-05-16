# Iter9 Visual Solver Demo JSON Schemas

## Purpose

This directory contains the JSON Schema specifications and field-level Markdown documentation for the Iter9 Visual Solver Demo.

These files belong under:

```text
demo/docs/json_schemas/
```

They do **not** belong under the base-project schema directory:

```text
docs/json_schema/
```

The separation matters because the demo is a durable package feature, not a base-project artifact-schema refactor.

---

## Files

| File | Purpose |
|---|---|
| `README.md` | This directory guide. |
| `iter9_visual_solver_demo_config.schema.json` | Machine-readable JSON Schema for the demo runtime config. |
| `iter9_visual_solver_demo_config.schema.md` | Painstaking field-by-field documentation for the demo runtime config schema. |
| `solver_event_trace.schema.json` | Machine-readable JSON Schema for one JSONL solver event trace row. |
| `solver_event_trace.schema.md` | Painstaking field-by-field documentation for solver event trace rows. |

---

## Runtime Contract Summary

The demo uses a pygame GUI that visualizes Iter9 solver output as a fast, automatic playback.

The config schema controls:

- window sizing and finish behavior
- playback speed policy
- visual colors
- status panel fields
- event trace / final-grid fallback behavior

The event trace schema controls:

- one playback event per JSONL line
- event cell coordinates
- logical cell state
- visual action
- optional counters and diagnostic metadata

---

## Validation Tools

Use:

```text
Pydantic v2
jsonschema
```

Ownership:

| Tool | Runtime Area |
|---|---|
| Pydantic v2 | `demos/iter9_visual_solver/config/` runtime validation |
| jsonschema | schema contract tests only |
| pygame | `demos/iter9_visual_solver/rendering/` only |

---

## Required Tests

Expected tests:

```text
tests/demo/iter9_visual_solver/test_config_schema_contract.py
tests/demo/iter9_visual_solver/test_event_trace_loader.py
tests/demo/iter9_visual_solver/test_architecture_boundaries.py
```

Required assertions:

- default config validates against `iter9_visual_solver_demo_config.schema.json`
- invalid config examples fail before pygame starts
- every solver event trace row validates independently
- invalid event trace rows fail with clear field paths
- demo schemas are not placed in base-project schema folders
- runtime does not import `jsonschema`

---

## Important Boundary Rule

The renderer must consume already validated config values and normalized playback events.

The renderer must not:

- parse raw JSON config
- validate JSON Schema
- calculate playback speed
- read `.npy` grid files directly
- read metrics JSON directly

Correct flow:

```text
config JSON
→ config loader / Pydantic model
→ playback and rendering policies
→ pygame renderer
```

Correct event flow:

```text
solver_event_trace.jsonl OR final grid artifact
→ event loader/source adapter
→ normalized playback events
→ replay state
→ pygame renderer
```
