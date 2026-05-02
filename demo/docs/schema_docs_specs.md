# Iter9 Visual Solver Demo — Schema Documentation and Specification Standard

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Schema/documentation architecture |
| Applies to | `demo/docs/json_schemas/` |
| Required before | JSON schema files, schema Markdown docs, config schema tests, event trace schema tests |
| Traceability IDs | DEMO-REQ-008, DEMO-REQ-007 |
| Change rule | Schema changes require updates to JSON Schema, Markdown docs, config contract, runtime models, tests, and traceability matrix. |

---

## 1. Purpose

This document defines the complete standard for demo JSON Schema specifications and their Markdown documentation.

It exists to prevent inconsistent schema authoring and to make every JSON field traceable to runtime behavior and tests.

---

## 2. Required Schema Location

All demo schema files MUST live under:

```text
demo/docs/json_schemas/
```

Forbidden locations:

```text
docs/json_schema/
schemas/
```

---

## 3. Required Files

```text
demo/docs/json_schemas/README.md
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md
demo/docs/json_schemas/solver_event_trace.schema.json
demo/docs/json_schemas/solver_event_trace.schema.md
```

---

## 4. Required JSON Schema Draft

All demo JSON Schema files MUST use:

```json
"$schema": "https://json-schema.org/draft/2020-12/schema"
```

No other draft is allowed unless this document and the ADRs are updated.

---

## 5. Required `$id` Format

Schema `$id` values MUST be stable relative identifiers:

```text
iter9_visual_solver_demo_config.schema.json
solver_event_trace.schema.json
```

If absolute IDs are later introduced, they MUST be documented in a superseding schema policy.

---

## 6. JSON Schema Authoring Rules

Every schema file MUST define:

```text
$schema
$id
title
description
type
required
additionalProperties
properties
$defs where useful
examples where useful
```

Every object type MUST explicitly define:

```json
"additionalProperties": false
```

unless a contract explicitly allows extensibility.

---

## 7. Nullable Field Policy

Nullable fields MUST use JSON Schema 2020-12 type arrays:

```json
"type": ["number", "null"]
```

Do not use non-standard nullable keywords.

---

## 8. Numeric Range Policy

Every numeric field MUST define minimum/maximum when possible.

Examples:

```json
"minimum": 0
"maximum": 255
```

Fields without ranges MUST document why no range is appropriate.

---

## 9. Enum Policy

Every enum field MUST define:

```json
"enum": [...]
```

The Markdown schema doc MUST explain the runtime meaning of each enum value.

Example:

| Enum Value | Meaning |
|---|---|
| `stay_open` | GUI remains open after playback finishes. |
| `close_immediately` | GUI closes as soon as playback finishes. |
| `close_after_delay` | GUI closes after configured delay. |

---

## 10. RGB Array Policy

RGB fields MUST use:

```json
{
  "type": "array",
  "minItems": 3,
  "maxItems": 3,
  "items": {
    "type": "integer",
    "minimum": 0,
    "maximum": 255
  }
}
```

The Markdown doc MUST include valid and invalid examples.

---

## 11. Config Schema Contract

## 11.1 Required file

```text
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
```

## 11.2 Required top-level fields

```text
schema_version
window
playback
visuals
status_panel
input
```

## 11.3 Required schema version

```text
iter9_visual_solver_demo_config.v1
```

## 11.4 Required top-level object policy

```json
"additionalProperties": false
```

## 11.5 Required nested object policies

Every nested object MUST define `additionalProperties: false`.

---

## 12. Event Trace Schema Contract

## 12.1 Required file

```text
demo/docs/json_schemas/solver_event_trace.schema.json
```

## 12.2 Schema meaning

The solver event trace schema defines **one JSONL row object**, not the entire file.

A JSONL file is valid when every non-empty line validates against this row schema.

## 12.3 Required event row fields

```text
schema_version
event_id
step
round
y
x
state
display
```

## 12.4 Event trace schema version

```text
iter9_visual_solver_event_trace.v1
```

## 12.5 Field rules

| Field | Type | Required | Rule |
|---|---|---:|---|
| `schema_version` | string | yes | must equal `iter9_visual_solver_event_trace.v1` |
| `event_id` | string | yes | non-empty; recommended `evt_<zero-padded step>` |
| `step` | integer | yes | `>= 0` |
| `round` | integer | yes | `>= 0` |
| `y` | integer | yes | `>= 0` |
| `x` | integer | yes | `>= 0` |
| `state` | string enum | yes | `SAFE`, `MINE`, `UNKNOWN` |
| `display` | string enum | yes | `flag`, `reveal`, `unknown` |
| `source` | string enum | no | default `solver_trace`; allowed `solver_trace`, `final_grid_replay`, `repair_trace`, `synthetic` |

## 12.6 Event ordering policy

The schema validates row shape only. Ordering rules are enforced by loader/playback tests.

Ordering rules:

```text
step values SHOULD be strictly increasing after zero-based ordering
duplicate cells MAY be rejected depending on solver trace contract
board bounds are validated by loader when board dimensions are known
```

This distinction MUST be documented in `solver_event_trace.schema.md`.

---

## 13. Markdown Schema Documentation Requirements

Each Markdown schema doc MUST include:

1. Purpose
2. Schema file path
3. Schema draft
4. Schema ID
5. Schema version field
6. Top-level required fields
7. `additionalProperties` policy
8. Field-by-field documentation
9. Valid complete example
10. Invalid examples
11. Runtime owner matrix
12. Test coverage matrix
13. Versioning/migration policy
14. Completion checklist

---

## 14. Required Field Documentation Template

Every field MUST use this template:

```markdown
## `<field name>`

| Property | Value |
|---|---|
| JSON path | `$.path.to.field` |
| Type | string / integer / number / boolean / object / array |
| Required | yes/no |
| Default | value or N/A |
| Nullable | yes/no |
| Valid values/range | exact range or enum |
| JSON Schema rule | exact schema rule |
| Pydantic field | `Model.field_name` or N/A |
| Runtime owner | `module.py` |
| Runtime effect | clear behavior |
| Invalid examples | examples |
| Expected validation failure | exact failure expectation |
| Tests | test file(s) |
```

---

## 15. Required Runtime Owner Matrix

Every schema doc MUST include a table like:

| JSON Path | Runtime Owner | Test File |
|---|---|---|
| `$.playback.mine_count_multiplier` | `playback/speed_policy.py` | `test_speed_policy.py` |
| `$.window.finish_behavior.mode` | `playback/finish_policy.py` | `test_finish_policy.py` |
| `$.visuals.flagged_mine_rgb` | `rendering/color_palette.py` | `test_color_palette.py` |

---

## 16. Required Valid Examples

Each schema doc MUST include:

- one complete valid example
- at least one minimal invalid example per validation category
- expected failure explanation for each invalid example

Config invalid categories:

```text
missing required field
unknown field
invalid enum
invalid RGB length
invalid RGB range
invalid numeric range
cross-field failure in the Pydantic/config model layer
```

Event trace invalid categories:

```text
missing field
invalid schema_version
invalid state
invalid display
negative coordinate
step less than 0
unknown extra field
malformed JSONL row
```

---

## 17. Schema Validation Tests

Required tests:

```text
test_config_schema_contract.py
test_event_trace_loader.py
```

Required assertions:

- [ ] schema JSON parses as JSON.
- [ ] schema passes `Draft202012Validator.check_schema`.
- [ ] default config validates against config schema.
- [ ] invalid config examples fail.
- [ ] valid event trace row validates.
- [ ] invalid event trace row examples fail.
- [ ] Markdown docs exist beside JSON schema files.
- [ ] Markdown docs document every top-level field.
- [ ] Schema files are not placed in forbidden locations.

---

## 18. Pydantic / JSON Schema Drift Policy

The following artifacts MUST agree:

```text
config_contract.md
iter9_visual_solver_demo_config.schema.json
iter9_visual_solver_demo_config.schema.md
config/models.py
configs/demo/iter9_visual_solver_demo.default.json
test_config_schema_contract.py
```

Drift examples:

- schema has field missing from Pydantic model
- Pydantic model has field missing from schema
- defaults differ
- enum values differ
- numeric ranges differ
- unknown-field policy differs

Any drift is a blocking failure.

Clarification: Draft 2020-12 JSON Schema cannot portably compare two numeric sibling fields such as `min_events_per_second <= max_events_per_second` without non-standard extensions. Cross-field config rules remain blocking requirements, but they are enforced by Pydantic model validation and config contract tests rather than by a non-portable JSON Schema extension.

---

## 19. Hand-Authored vs Generated Schema Policy

The committed schema is the authoritative artifact.

If generated from Pydantic:

- generator must be deterministic
- generated schema must be compared to committed schema
- differences must fail tests unless intentionally accepted
- generated output must not silently overwrite hand-edited docs

If hand-authored:

- test must validate default config and invalid examples
- model/schema drift test must exist
- schema docs must be updated manually with every field change

---

## 20. Versioning Policy

A schema version MUST change when:

- a required field is added
- a required field is removed
- a field type changes
- enum values change incompatibly
- validation ranges change incompatibly
- unknown-field policy changes
- runtime meaning of a field changes

A schema version MAY remain the same when:

- descriptions are clarified
- examples are added
- Markdown docs are improved without schema behavior change

---

## 21. Backward Compatibility Policy

For v1, no backward compatibility migration is required until a v2 schema exists.

When v2 exists, the docs MUST define:

```text
v1 accepted or rejected
migration path
deprecation date
runtime loader behavior
tests for old/new versions
```

---

## 22. Completion Checklist

- [ ] Schema files live under `demo/docs/json_schemas/`.
- [ ] No demo schema files exist under forbidden paths.
- [ ] Both schemas use Draft 2020-12.
- [ ] Every object sets `additionalProperties`.
- [ ] Every field is documented in Markdown.
- [ ] Every field has runtime owner and tests.
- [ ] Default config validates.
- [ ] Valid event row validates.
- [ ] Invalid examples fail.
- [ ] Drift prevention tests exist.
- [ ] Versioning policy is documented.
