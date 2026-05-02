# Solver Event Trace Schema

## File

```text
demo/docs/json_schemas/solver_event_trace.schema.json
```

## Purpose

This schema defines one JSONL row in the optional solver event trace used by the Iter9 Visual Solver Demo.

The event trace allows the demo to show cells being solved over time instead of only showing the final result.

MVP may synthesize equivalent playback events from the final grid artifact. Future versions may emit true solver-order events during `solver.py`, repair routing, or pipeline execution.

---

## Schema Version

```text
iter9_visual_solver_event_trace.v1
```

---

## File Format

The trace file is JSONL:

```text
solver_event_trace.jsonl
```

Each line is one complete JSON object.

Example:

```json
{"schema_version":"iter9_visual_solver_event_trace.v1","event_id":"evt_000000","step":0,"round":0,"y":12,"x":77,"state":"MINE","display":"flag","source":"final_grid_replay","confidence":"known_from_final_grid","reason":"final_grid_replay","mine_count_after":1,"safe_count_after":0,"unknown_count_after":null,"elapsed_solver_ms":null,"metadata":{}}
```

---

## Runtime Ownership

| Concern | Owner |
|---|---|
| Event row schema | `demo/docs/json_schemas/solver_event_trace.schema.json` |
| Event row loading | `demos/iter9_visual_solver/io/event_trace_loader.py` |
| Final-grid replay adapter | `demos/iter9_visual_solver/playback/event_source.py` |
| Event data model | `demos/iter9_visual_solver/domain/playback_event.py` |
| Replay state mutation | `demos/iter9_visual_solver/playback/replay_state.py` |
| Rendering | `demos/iter9_visual_solver/rendering/board_surface.py` |

---

# Required Fields

## `schema_version`

| Property | Value |
|---|---|
| JSON path | `$.schema_version` |
| Type | string |
| Required | yes |
| Allowed value | `iter9_visual_solver_event_trace.v1` |
| Runtime owner | `io/event_trace_loader.py` |
| Runtime effect | Rejects incompatible event trace rows. |

## `event_id`

| Property | Value |
|---|---|
| JSON path | `$.event_id` |
| Type | string |
| Required | yes |
| Recommended format | `evt_<zero-padded step>` |
| Runtime owner | `io/event_trace_loader.py` |
| Runtime effect | Gives each event a stable debug identifier. |

## `step`

| Property | Value |
|---|---|
| JSON path | `$.step` |
| Type | integer |
| Required | yes |
| Valid range | `>= 0` |
| Runtime owner | `playback/event_scheduler.py` |
| Runtime effect | Defines playback order. |

Validation beyond schema:

- steps must be monotonic
- duplicate steps should fail loader or contract tests
- rows should be sorted or normalized by loader

## `round`

| Property | Value |
|---|---|
| JSON path | `$.round` |
| Type | integer |
| Required | yes |
| Valid range | `>= 0` |
| Runtime owner | `io/event_trace_loader.py` |
| Runtime effect | Identifies solver/repair/synthetic round that produced this event. |

## `y`

| Property | Value |
|---|---|
| JSON path | `$.y` |
| Type | integer |
| Required | yes |
| Valid range | `>= 0` |
| Runtime owner | `domain/playback_event.py` |
| Runtime effect | Board row index. |

Validation beyond schema:

- must be `< board_height`
- board height comes from actual grid shape

## `x`

| Property | Value |
|---|---|
| JSON path | `$.x` |
| Type | integer |
| Required | yes |
| Valid range | `>= 0` |
| Runtime owner | `domain/playback_event.py` |
| Runtime effect | Board column index. |

Validation beyond schema:

- must be `< board_width`
- board width comes from actual grid shape

## `state`

| Property | Value |
|---|---|
| JSON path | `$.state` |
| Type | string enum |
| Required | yes |
| Allowed values | `SAFE`, `MINE`, `UNKNOWN` |
| Runtime owner | `domain/playback_event.py` |
| Runtime effect | Logical state applied to the replay board. |

## `display`

| Property | Value |
|---|---|
| JSON path | `$.display` |
| Type | string enum |
| Required | yes |
| Allowed values | `reveal`, `flag`, `unknown` |
| Runtime owner | `rendering/board_surface.py` |
| Runtime effect | Visual action applied to the cell. |

Required pairings:

| `state` | required `display` |
|---|---|
| `MINE` | `flag` |
| `SAFE` | `reveal` |
| `UNKNOWN` | `unknown` |

---

# Optional Fields

## `source`

| Property | Value |
|---|---|
| JSON path | `$.source` |
| Type | string enum |
| Required | no |
| Default | `solver_trace` |
| Allowed values | `solver_trace`, `final_grid_replay`, `repair_trace`, `synthetic` |
| Runtime effect | Explains where the event came from. |

## `confidence`

| Property | Value |
|---|---|
| JSON path | `$.confidence` |
| Type | string enum |
| Required | no |
| Default | `deduced` |
| Allowed values | `deduced`, `known_from_final_grid`, `synthetic_replay` |
| Runtime effect | Explains why the event can be rendered. |

## `reason`

| Property | Value |
|---|---|
| JSON path | `$.reason` |
| Type | string or null |
| Required | no |
| Default | `null` |
| Runtime effect | Optional short reason label for debugging. |

Examples:

```text
deterministic_solver
phase1_repair
phase2_full_repair
last100_repair
final_grid_replay
```

## `mine_count_after`

| Property | Value |
|---|---|
| JSON path | `$.mine_count_after` |
| Type | integer or null |
| Required | no |
| Valid range | `>= 0` |
| Runtime effect | Optional status panel counter after this event. |

## `safe_count_after`

| Property | Value |
|---|---|
| JSON path | `$.safe_count_after` |
| Type | integer or null |
| Required | no |
| Valid range | `>= 0` |
| Runtime effect | Optional status panel counter after this event. |

## `unknown_count_after`

| Property | Value |
|---|---|
| JSON path | `$.unknown_count_after` |
| Type | integer or null |
| Required | no |
| Valid range | `>= 0` |
| Runtime effect | Optional status panel counter after this event. |

## `elapsed_solver_ms`

| Property | Value |
|---|---|
| JSON path | `$.elapsed_solver_ms` |
| Type | number or null |
| Required | no |
| Valid range | `>= 0` |
| Runtime effect | Optional diagnostic timing. |

The playback visualizer must not use this value to determine playback speed. Playback speed comes from the demo config.

## `metadata`

| Property | Value |
|---|---|
| JSON path | `$.metadata` |
| Type | object |
| Required | no |
| Default | `{}` |
| Runtime effect | Optional diagnostics for trace review. Renderer must not require it. |

---

# Valid Examples

## Flagged mine event

```json
{
  "schema_version": "iter9_visual_solver_event_trace.v1",
  "event_id": "evt_000001",
  "step": 1,
  "round": 0,
  "y": 12,
  "x": 77,
  "state": "MINE",
  "display": "flag",
  "source": "final_grid_replay",
  "confidence": "known_from_final_grid",
  "reason": "final_grid_replay",
  "mine_count_after": 1,
  "safe_count_after": 0,
  "unknown_count_after": null,
  "elapsed_solver_ms": null,
  "metadata": {}
}
```

## Revealed safe-cell event

```json
{
  "schema_version": "iter9_visual_solver_event_trace.v1",
  "event_id": "evt_000002",
  "step": 2,
  "round": 0,
  "y": 13,
  "x": 77,
  "state": "SAFE",
  "display": "reveal",
  "source": "solver_trace",
  "confidence": "deduced",
  "reason": "deterministic_solver",
  "mine_count_after": 1,
  "safe_count_after": 1,
  "unknown_count_after": 282598,
  "elapsed_solver_ms": 14.5,
  "metadata": {
    "solver_mode": "full"
  }
}
```

---

# Invalid Examples

## State/display mismatch

```json
{
  "schema_version": "iter9_visual_solver_event_trace.v1",
  "event_id": "evt_bad",
  "step": 0,
  "round": 0,
  "y": 1,
  "x": 1,
  "state": "MINE",
  "display": "reveal"
}
```

Expected failure: `MINE` requires `display = flag`.

## Negative coordinate

```json
{
  "schema_version": "iter9_visual_solver_event_trace.v1",
  "event_id": "evt_bad",
  "step": 0,
  "round": 0,
  "y": -1,
  "x": 1,
  "state": "SAFE",
  "display": "reveal"
}
```

Expected failure: coordinates must be non-negative.

## Unknown schema version

```json
{
  "schema_version": "v0",
  "event_id": "evt_bad",
  "step": 0,
  "round": 0,
  "y": 1,
  "x": 1,
  "state": "SAFE",
  "display": "reveal"
}
```

Expected failure: schema version must match `iter9_visual_solver_event_trace.v1`.

---

# Loader-Level Rules Not Fully Expressible In JSON Schema

The event trace loader must also enforce:

- [ ] `step` values are monotonic and unique.
- [ ] `(y, x)` coordinates are inside actual grid bounds.
- [ ] duplicate contradictory events for the same cell are rejected or explicitly resolved.
- [ ] total counters do not become negative.
- [ ] `mine_count_after + safe_count_after + unknown_count_after` does not exceed total cells when all counters are present.
- [ ] event source fallback behavior matches config.
- [ ] malformed JSONL line numbers are included in error messages.

---

# Completion Checklist

- [ ] Schema validates as Draft 2020-12.
- [ ] Each JSONL row validates independently.
- [ ] State/display pairings are enforced.
- [ ] Loader rejects out-of-bounds coordinates using actual grid shape.
- [ ] Loader rejects duplicate or non-monotonic steps.
- [ ] Renderer consumes normalized playback events only.
- [ ] Playback speed comes from config, not event timestamps.
