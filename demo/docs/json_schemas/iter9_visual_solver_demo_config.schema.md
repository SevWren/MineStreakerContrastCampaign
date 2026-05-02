# Iter9 Visual Solver Demo Config Schema

## File

```text
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
```

## Purpose

This schema defines the JSON configuration contract for the pygame-based Iter9 Visual Solver Demo.

The config file controls behavior that must not be hardcoded inside pygame rendering code:

- window sizing
- finish behavior
- playback speed
- color palette
- status panel visibility
- input source selection

## Schema Version

```text
iter9_visual_solver_demo_config.v1
```

## Runtime Ownership

| Concern | Owner |
|---|---|
| Runtime validation | `demos/iter9_visual_solver/config/models.py` |
| Config file loading | `demos/iter9_visual_solver/config/loader.py` |
| Schema contract tests | `tests/demo/iter9_visual_solver/test_config_schema_contract.py` |
| Playback rate calculation | `demos/iter9_visual_solver/playback/speed_policy.py` |
| Window geometry calculation | `demos/iter9_visual_solver/rendering/window_geometry.py` |
| Finish behavior | `demos/iter9_visual_solver/playback/finish_policy.py` |
| pygame drawing | `demos/iter9_visual_solver/rendering/` |

---

## Required Top-Level Object

```json
{
  "schema_version": "iter9_visual_solver_demo_config.v1",
  "window": {},
  "playback": {},
  "visuals": {},
  "status_panel": {},
  "input": {}
}
```

`additionalProperties` is `false`. Unknown top-level keys must fail validation.

---

## `schema_version`

| Property | Value |
|---|---|
| JSON path | `$.schema_version` |
| Type | string |
| Required | yes |
| Allowed value | `iter9_visual_solver_demo_config.v1` |
| Runtime owner | `config/models.py` |
| Runtime effect | Prevents silently loading an incompatible config version. |

### Valid example

```json
"schema_version": "iter9_visual_solver_demo_config.v1"
```

### Invalid example

```json
"schema_version": "v1"
```

### Expected failure

Validation must reject unknown schema versions before pygame starts.

---

# `window`

## `window.title`

| Property | Value |
|---|---|
| JSON path | `$.window.title` |
| Type | string |
| Required | yes |
| Default | `Mine-Streaker Iter9 Visual Solver Demo` |
| Runtime owner | `rendering/pygame_adapter.py` |
| Runtime effect | Sets the pygame window caption. |

Invalid when empty.

## `window.resizable`

| Property | Value |
|---|---|
| JSON path | `$.window.resizable` |
| Type | boolean |
| Required | yes |
| Default | `false` |
| Runtime owner | `rendering/pygame_adapter.py` |
| Runtime effect | Controls whether the window should request pygame resizable mode. |

## `window.max_screen_fraction`

| Property | Value |
|---|---|
| JSON path | `$.window.max_screen_fraction` |
| Type | number |
| Required | yes |
| Default | `0.92` |
| Valid range | `0.10` through `1.00` |
| Runtime owner | `rendering/window_geometry.py` |
| Runtime effect | Caps the window size to a fraction of detected screen dimensions. |

Invalid values: values below `0.10`, negative numbers, values greater than `1`.

## `window.status_panel_width_px`

| Property | Value |
|---|---|
| JSON path | `$.window.status_panel_width_px` |
| Type | integer |
| Required | yes |
| Default | `360` |
| Valid range | `0` through `1200` |
| Runtime owner | `rendering/window_geometry.py` |
| Runtime effect | Reserves horizontal pixels for status text. `0` means no reserved side panel. |

## `window.minimum_board_cell_px`

| Property | Value |
|---|---|
| JSON path | `$.window.minimum_board_cell_px` |
| Type | integer |
| Required | yes |
| Default | `1` |
| Valid range | `1` through `64` |
| Runtime owner | `rendering/window_geometry.py` |
| Runtime effect | Smallest rendered board cell size allowed after fit-to-screen scaling. |

## `window.preferred_board_cell_px`

| Property | Value |
|---|---|
| JSON path | `$.window.preferred_board_cell_px` |
| Type | integer |
| Required | yes |
| Default | `2` |
| Valid range | `1` through `64` |
| Runtime owner | `rendering/window_geometry.py` |
| Runtime effect | Preferred board cell size before screen fitting. |

Pydantic must reject configs where preferred cell size is less than minimum cell size.

## `window.fit_to_screen`

| Property | Value |
|---|---|
| JSON path | `$.window.fit_to_screen` |
| Type | boolean |
| Required | yes |
| Default | `true` |
| Runtime owner | `rendering/window_geometry.py` |
| Runtime effect | Allows the geometry policy to reduce cell size for large boards. |

## `window.center_window`

| Property | Value |
|---|---|
| JSON path | `$.window.center_window` |
| Type | boolean |
| Required | yes |
| Default | `true` |
| Runtime owner | `rendering/pygame_adapter.py` |
| Runtime effect | Allows pygame adapter to request centered window placement when supported. |

---

# `window.finish_behavior`

## `window.finish_behavior.mode`

| Property | Value |
|---|---|
| JSON path | `$.window.finish_behavior.mode` |
| Type | string enum |
| Required | yes |
| Default | `stay_open` |
| Allowed values | `stay_open`, `close_immediately`, `close_after_delay` |
| Runtime owner | `playback/finish_policy.py` |
| Runtime effect | Controls what the GUI does after playback finishes. |

### Behavior

| Value | Behavior |
|---|---|
| `stay_open` | Leave final solved board visible until user closes the window. |
| `close_immediately` | Close automatically when playback finishes. |
| `close_after_delay` | Keep final board visible for `close_after_seconds`, then close. |

## `window.finish_behavior.close_after_seconds`

| Property | Value |
|---|---|
| JSON path | `$.window.finish_behavior.close_after_seconds` |
| Type | number or null |
| Required | yes |
| Default | `null` |
| Valid range | `>= 0` when mode is `close_after_delay`; otherwise may be `null` |
| Runtime owner | `playback/finish_policy.py` |
| Runtime effect | Delay before closing after playback completes. |

---

# `playback`

## `playback.mode`

| Property | Value |
|---|---|
| JSON path | `$.playback.mode` |
| Type | string enum |
| Required | yes |
| Default | `mine_count_scaled` |
| Allowed values | `mine_count_scaled` |
| Runtime owner | `playback/speed_policy.py` |
| Runtime effect | Selects how events-per-second is calculated. |

## `playback.min_events_per_second`

| Property | Value |
|---|---|
| JSON path | `$.playback.min_events_per_second` |
| Type | integer |
| Required | yes |
| Default | `50` |
| Valid range | `1` through `1_000_000` |
| Runtime owner | `playback/speed_policy.py` |
| Runtime effect | Lower clamp for playback speed. |

## `playback.base_events_per_second`

| Property | Value |
|---|---|
| JSON path | `$.playback.base_events_per_second` |
| Type | integer |
| Required | yes |
| Default | `1000` |
| Valid range | `0` through `1_000_000` |
| Runtime owner | `playback/speed_policy.py` |
| Runtime effect | Base rate for mine-count-scaled playback. |

## `playback.mine_count_multiplier`

| Property | Value |
|---|---|
| JSON path | `$.playback.mine_count_multiplier` |
| Type | number |
| Required | yes |
| Default | `0.08` |
| Valid range | `0` through `10_000` |
| Runtime owner | `playback/speed_policy.py` |
| Runtime effect | Adds speed as total mine count grows. |

### Expected formula

```text
raw_events_per_second =
  base_events_per_second + (total_mines * mine_count_multiplier)
```

Then clamp:

```text
events_per_second =
  min(max(raw_events_per_second, min_events_per_second), max_events_per_second)
```

Only `mine_count_scaled` is valid for MVP. Future modes require updating this schema, config contract, playback contract, tests, and traceability matrix.

## `playback.max_events_per_second`

| Property | Value |
|---|---|
| JSON path | `$.playback.max_events_per_second` |
| Type | integer |
| Required | yes |
| Default | `12000` |
| Valid range | `1` through `10_000_000` and `>= min_events_per_second` |
| Runtime owner | `playback/speed_policy.py` |
| Runtime effect | Upper clamp for playback speed. |

Pydantic must enforce `min_events_per_second <= max_events_per_second`.

## `playback.target_fps`

| Property | Value |
|---|---|
| JSON path | `$.playback.target_fps` |
| Type | integer |
| Required | yes |
| Default | `60` |
| Valid range | `1` through `240` |
| Runtime owner | `rendering/pygame_loop.py` |
| Runtime effect | Sets pygame clock tick target. |

## `playback.batch_events_per_frame`

| Property | Value |
|---|---|
| JSON path | `$.playback.batch_events_per_frame` |
| Type | boolean |
| Required | yes |
| Default | `true` |
| Valid values | `true`, `false` |
| Runtime owner | `playback/event_batching.py` |
| Runtime effect | Enables multiple playback events per frame. When `false`, the scheduler applies one event per frame. |

---

# `visuals`

All RGB fields use this format:

```json
[red, green, blue]
```

Each channel must be an integer from `0` through `255`.

The MVP config contract does not define `grid_line_rgb`. Adding grid-line color is a future schema change and must update the config contract, renderer contract, default config, and tests.

## `visuals.unseen_cell_rgb`

Initial cell color before any playback event.

Default:

```json
[18, 18, 18]
```

## `visuals.flagged_mine_rgb`

Color used for cells flagged as mines.

Default:

```json
[255, 80, 40]
```

## `visuals.safe_cell_rgb`

Color used for safe/revealed cells.

Default:

```json
[95, 95, 95]
```

## `visuals.unknown_cell_rgb`

Color used when unknown-state events are displayed.

Default:

```json
[60, 100, 230]
```

## `visuals.background_rgb`

Window background color.

Default:

```json
[10, 10, 10]
```


## `visuals.show_safe_cells`

Controls whether safe-cell events visibly paint safe cells.

## `visuals.show_unknown_cells`

Controls whether unknown-cell events visibly paint unknown cells.

---

# `status_panel`

Every field is a required boolean.

| JSON path | Runtime effect |
|---|---|
| `$.status_panel.show_source_image` | Show source image filename/path label. |
| `$.status_panel.show_board_dimensions` | Show actual board dimensions from grid shape. |
| `$.status_panel.show_seed` | Show run seed. |
| `$.status_panel.show_total_cells` | Show `board_width * board_height`. |
| `$.status_panel.show_mines_flagged` | Show mine progress counter. |
| `$.status_panel.show_safe_cells_solved` | Show safe-cell progress counter. |
| `$.status_panel.show_unknown_remaining` | Show remaining unknown count. |
| `$.status_panel.show_playback_speed` | Show active events-per-second. |
| `$.status_panel.show_elapsed_time` | Show playback elapsed time. |
| `$.status_panel.show_finish_message` | Show final completion message. |

---

# `input`

## `input.prefer_solver_event_trace`

| Property | Value |
|---|---|
| JSON path | `$.input.prefer_solver_event_trace` |
| Type | boolean |
| Required | yes |
| Default | `true` |
| Runtime owner | `playback/event_source.py` |
| Runtime effect | Prefer real `solver_event_trace.jsonl` when present. |

## `input.allow_final_grid_replay_fallback`

| Property | Value |
|---|---|
| JSON path | `$.input.allow_final_grid_replay_fallback` |
| Type | boolean |
| Required | yes |
| Default | `true` |
| Runtime owner | `playback/event_source.py` |
| Runtime effect | Allows MVP to synthesize playback events from final grid artifact. |

---

# Valid Minimal Example

```json
{
  "schema_version": "iter9_visual_solver_demo_config.v1",
  "window": {
    "title": "Mine-Streaker Iter9 Visual Solver Demo",
    "resizable": false,
    "max_screen_fraction": 0.92,
    "status_panel_width_px": 360,
    "minimum_board_cell_px": 1,
    "preferred_board_cell_px": 2,
    "fit_to_screen": true,
    "center_window": true,
    "finish_behavior": {
      "mode": "stay_open",
      "close_after_seconds": null
    }
  },
  "playback": {
    "mode": "mine_count_scaled",
    "min_events_per_second": 50,
    "base_events_per_second": 1000,
    "mine_count_multiplier": 0.08,
    "max_events_per_second": 12000,
    "target_fps": 60,
    "batch_events_per_frame": true
  },
  "visuals": {
    "unseen_cell_rgb": [18, 18, 18],
    "flagged_mine_rgb": [255, 80, 40],
    "safe_cell_rgb": [95, 95, 95],
    "unknown_cell_rgb": [60, 100, 230],
    "background_rgb": [10, 10, 10],
    "show_safe_cells": false,
    "show_unknown_cells": true
  },
  "status_panel": {
    "show_source_image": true,
    "show_board_dimensions": true,
    "show_seed": true,
    "show_total_cells": true,
    "show_mines_flagged": true,
    "show_safe_cells_solved": true,
    "show_unknown_remaining": true,
    "show_playback_speed": true,
    "show_elapsed_time": true,
    "show_finish_message": true
  },
  "input": {
    "prefer_solver_event_trace": true,
    "allow_final_grid_replay_fallback": true
  }
}
```

---

# Invalid Examples

## Bad playback rate

```json
{
  "playback": {
    "min_events_per_second": -1
  }
}
```

Expected failure: playback rates must be positive.

## Bad RGB tuple

```json
{
  "visuals": {
    "flagged_mine_rgb": [255, 0]
  }
}
```

Expected failure: RGB must contain exactly three integer channels.

## Bad finish delay

```json
{
  "window": {
    "finish_behavior": {
      "mode": "close_after_delay",
      "close_after_seconds": null
    }
  }
}
```

Expected failure: delayed close requires a positive numeric delay.

---

# Completion Checklist

- [ ] JSON schema validates as Draft 2020-12.
- [ ] Default config validates against this schema.
- [ ] Pydantic model enforces cross-field rules not expressible in plain JSON Schema.
- [ ] Invalid config fails before pygame starts.
- [ ] pygame modules do not import Pydantic or jsonschema.
- [ ] playback speed is not hardcoded in pygame loop.
- [ ] window size is derived from board dimensions and config.
