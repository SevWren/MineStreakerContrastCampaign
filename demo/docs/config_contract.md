# Iter9 Visual Solver Demo — Config Contract

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Demo config/schema architecture |
| Applies to | `configs/demo/iter9_visual_solver_demo.default.json`, `demos/iter9_visual_solver/config/`, `demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.*` |
| Required before | config models, config loader, playback speed, finish behavior, window sizing, rendering colors, status panel visibility |
| Traceability IDs | DEMO-REQ-002, DEMO-REQ-003, DEMO-REQ-004, DEMO-REQ-005, DEMO-REQ-008, DEMO-TEST-001, DEMO-TEST-002, DEMO-TEST-003 |
| Change rule | Any config field addition/change/removal requires updates to this file, JSON Schema, Markdown schema docs, default config, Pydantic models, config tests, affected runtime tests, and traceability matrix. |

---

## 1. Purpose

This contract defines the complete JSON configuration contract for the Iter9 Visual Solver Demo.

The config controls playback speed, dynamic mine-count scaling, finish behavior, window sizing, colors, status panel visibility, and replay input fallback behavior.

---

## 2. Required File Locations

| Artifact | Required Path |
|---|---|
| Default config | `configs/demo/iter9_visual_solver_demo.default.json` |
| Config JSON Schema | `demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json` |
| Config Markdown schema documentation | `demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md` |
| Runtime models | `demos/iter9_visual_solver/config/models.py` |
| Runtime loader | `demos/iter9_visual_solver/config/loader.py` |
| Config errors | `demos/iter9_visual_solver/config/validation_errors.py` |

---

## 3. Tooling Decision

| Tool | Purpose |
|---|---|
| Pydantic v2 | Runtime typed config models and validation |
| jsonschema | Test-time validation of committed JSON Schema and examples |
| JSON Schema Draft 2020-12 | Required schema draft |
| plain JSON | User-editable config format |

JSONC, YAML, TOML, and comments are not supported for MVP.

---

## 4. Loading Rules

## 4.1 Default path

If no explicit config path is supplied, the demo uses:

```text
configs/demo/iter9_visual_solver_demo.default.json
```

## 4.2 CLI override

Standalone demo CLI and optional `run_iter9.py` hook may accept:

```text
--demo-config <path>
```

or standalone:

```text
--config <path>
```

The exact flag names are owned by CLI contract, but both must eventually resolve to the same config loader.

## 4.3 Missing file

Missing config must raise:

```python
DemoConfigFileNotFoundError
```

Required message content:

```text
config path
not found
```

## 4.4 Malformed JSON

Malformed JSON must raise:

```python
DemoConfigJsonError
```

Required message content:

```text
config path
line/column when available
parse failure
```

## 4.5 Validation failure

Invalid config must raise:

```python
DemoConfigValidationError
```

Required message content:

```text
field path
invalid value when safe to display
expected rule
```

## 4.6 Unknown fields

Unknown fields must be rejected.

Pydantic requirement:

```python
model_config = ConfigDict(extra="forbid")
```

JSON Schema requirement:

```json
"additionalProperties": false
```

for every object unless explicitly allowed by a future contract.

---

## 5. Required Top-Level Shape

Required top-level fields:

```text
schema_version
window
playback
visuals
status_panel
input
```

All are required.

Top-level unknown fields are forbidden.

---

## 6. Required Pydantic Models

`config/models.py` must define:

```python
class DemoConfig(BaseModel): ...
class WindowConfig(BaseModel): ...
class FinishBehaviorConfig(BaseModel): ...
class PlaybackConfig(BaseModel): ...
class VisualsConfig(BaseModel): ...
class StatusPanelConfig(BaseModel): ...
class InputConfig(BaseModel): ...
```

All models must reject extra fields.

---

## 7. Field-Level Contract

## 7.1 `schema_version`

| Property | Value |
|---|---|
| JSON path | `$.schema_version` |
| Type | string |
| Required | yes |
| Default | `iter9_visual_solver_demo_config.v1` |
| Allowed values | `iter9_visual_solver_demo_config.v1` |
| Nullable | no |
| Runtime owner | `config/models.py` |
| Tests | `test_config_models.py`, `test_config_schema_contract.py` |

---

## 7.2 `window.title`

| Property | Value |
|---|---|
| JSON path | `$.window.title` |
| Type | string |
| Required | yes |
| Default | `Mine-Streaker Iter9 Visual Solver Demo` |
| Range/constraint | length 1–120 |
| Runtime owner | `rendering/pygame_adapter.py` |
| Tests | `test_config_models.py`, `test_pygame_adapter_contract.py` |

---

## 7.3 `window.resizable`

| Property | Value |
|---|---|
| JSON path | `$.window.resizable` |
| Type | boolean |
| Required | yes |
| Default | `false` |
| Runtime owner | `rendering/pygame_adapter.py` |

---

## 7.4 `window.max_screen_fraction`

| Property | Value |
|---|---|
| JSON path | `$.window.max_screen_fraction` |
| Type | number |
| Required | yes |
| Default | `0.92` |
| Range | `0.10 <= value <= 1.00` |
| Runtime owner | `rendering/window_geometry.py` |
| Tests | `test_window_geometry.py`, `test_config_models.py` |

---

## 7.5 `window.status_panel_width_px`

| Property | Value |
|---|---|
| JSON path | `$.window.status_panel_width_px` |
| Type | integer |
| Required | yes |
| Default | `360` |
| Range | `0 <= value <= 1200` |
| Runtime owner | `rendering/window_geometry.py`, `rendering/status_panel.py` |
| Tests | `test_window_geometry.py`, `test_status_panel.py` |

---

## 7.6 `window.minimum_board_cell_px`

| Property | Value |
|---|---|
| JSON path | `$.window.minimum_board_cell_px` |
| Type | integer |
| Required | yes |
| Default | `1` |
| Range | `1 <= value <= 64` |
| Runtime owner | `rendering/window_geometry.py` |

---

## 7.7 `window.preferred_board_cell_px`

| Property | Value |
|---|---|
| JSON path | `$.window.preferred_board_cell_px` |
| Type | integer |
| Required | yes |
| Default | `2` |
| Range | `1 <= value <= 64` |
| Cross-field rule | must be `>= minimum_board_cell_px` |
| Runtime owner | `rendering/window_geometry.py` |

---

## 7.8 `window.fit_to_screen`

| Property | Value |
|---|---|
| JSON path | `$.window.fit_to_screen` |
| Type | boolean |
| Required | yes |
| Default | `true` |
| Runtime owner | `rendering/window_geometry.py` |
| Behavior | Allows dynamic cell-size shrink-to-fit. Board dimensions do not change. |

---

## 7.9 `window.center_window`

| Property | Value |
|---|---|
| JSON path | `$.window.center_window` |
| Type | boolean |
| Required | yes |
| Default | `true` |
| Runtime owner | `rendering/pygame_adapter.py` |

---

## 7.10 `window.finish_behavior.mode`

| Property | Value |
|---|---|
| JSON path | `$.window.finish_behavior.mode` |
| Type | string enum |
| Required | yes |
| Default | `stay_open` |
| Allowed values | `stay_open`, `close_immediately`, `close_after_delay` |
| Runtime owner | `playback/finish_policy.py` |
| Tests | `test_finish_policy.py`, `test_config_models.py` |

---

## 7.11 `window.finish_behavior.close_after_seconds`

| Property | Value |
|---|---|
| JSON path | `$.window.finish_behavior.close_after_seconds` |
| Type | number or null |
| Required | yes |
| Default | `null` |
| Range | number must be `>= 0` |
| Cross-field rule | required as number when mode is `close_after_delay` |
| Runtime owner | `playback/finish_policy.py` |

---

## 7.12 `playback.mode`

| Property | Value |
|---|---|
| JSON path | `$.playback.mode` |
| Type | string enum |
| Required | yes |
| Default | `mine_count_scaled` |
| Allowed values | `mine_count_scaled` |
| Runtime owner | `playback/speed_policy.py` |

---

## 7.13 `playback.min_events_per_second`

| Property | Value |
|---|---|
| JSON path | `$.playback.min_events_per_second` |
| Type | integer |
| Required | yes |
| Default | `50` |
| Range | `1 <= value <= 1_000_000` |
| Cross-field rule | must be `<= max_events_per_second` |
| Runtime owner | `playback/speed_policy.py` |

---

## 7.14 `playback.base_events_per_second`

| Property | Value |
|---|---|
| JSON path | `$.playback.base_events_per_second` |
| Type | integer |
| Required | yes |
| Default | `1000` |
| Range | `0 <= value <= 1_000_000` |
| Runtime owner | `playback/speed_policy.py` |

---

## 7.15 `playback.mine_count_multiplier`

| Property | Value |
|---|---|
| JSON path | `$.playback.mine_count_multiplier` |
| Type | number |
| Required | yes |
| Default | `0.08` |
| Range | `0 <= value <= 10_000` |
| Runtime owner | `playback/speed_policy.py` |
| Formula role | `base_events_per_second + total_mines * mine_count_multiplier` |

---

## 7.16 `playback.max_events_per_second`

| Property | Value |
|---|---|
| JSON path | `$.playback.max_events_per_second` |
| Type | integer |
| Required | yes |
| Default | `12000` |
| Range | `1 <= value <= 10_000_000` |
| Cross-field rule | must be `>= min_events_per_second` |
| Runtime owner | `playback/speed_policy.py` |

---

## 7.17 `playback.target_fps`

| Property | Value |
|---|---|
| JSON path | `$.playback.target_fps` |
| Type | integer |
| Required | yes |
| Default | `60` |
| Range | `1 <= value <= 240` |
| Runtime owner | `playback/event_batching.py`, `rendering/pygame_loop.py` |

---

## 7.18 `playback.batch_events_per_frame`

| Property | Value |
|---|---|
| JSON path | `$.playback.batch_events_per_frame` |
| Type | boolean |
| Required | yes |
| Default | `true` |
| Runtime owner | `playback/event_batching.py` |

---

## 7.19 RGB visual fields

Fields:

```text
$.visuals.unseen_cell_rgb
$.visuals.flagged_mine_rgb
$.visuals.safe_cell_rgb
$.visuals.unknown_cell_rgb
$.visuals.background_rgb
```

Rule:

```text
array of exactly 3 integers
each integer from 0 to 255 inclusive
```

Defaults:

| Field | Default |
|---|---|
| `unseen_cell_rgb` | `[18, 18, 18]` |
| `flagged_mine_rgb` | `[255, 80, 40]` |
| `safe_cell_rgb` | `[95, 95, 95]` |
| `unknown_cell_rgb` | `[60, 100, 230]` |
| `background_rgb` | `[10, 10, 10]` |

Runtime owner:

```text
rendering/color_palette.py
```

---

## 7.20 Visual boolean fields

Fields:

```text
$.visuals.show_safe_cells
$.visuals.show_unknown_cells
```

Type:

```text
boolean
```

Defaults:

```text
show_safe_cells = false
show_unknown_cells = true
```

Runtime owner:

```text
rendering/board_surface.py
```

---

## 7.21 Status panel boolean fields

Fields:

```text
show_source_image
show_board_dimensions
show_seed
show_total_cells
show_mines_flagged
show_safe_cells_solved
show_unknown_remaining
show_playback_speed
show_elapsed_time
show_finish_message
```

All are required booleans.

Default:

```text
true
```

Runtime owner:

```text
rendering/status_text.py
```

---

## 7.22 Input fields

## `input.prefer_solver_event_trace`

| Property | Value |
|---|---|
| Type | boolean |
| Required | yes |
| Default | `true` |
| Runtime owner | `playback/event_source.py` |

## `input.allow_final_grid_replay_fallback`

| Property | Value |
|---|---|
| Type | boolean |
| Required | yes |
| Default | `true` |
| Runtime owner | `playback/event_source.py` |

Behavior matrix:

| Trace exists | Prefer trace | Fallback allowed | Result |
|---|---:|---:|---|
| yes | true | any | use solver trace |
| yes | false | any | use final-grid replay |
| no | any | true | use final-grid replay |
| no | any | false | raise missing event trace/input error |

---

## 8. Required Default Config

The default config must contain every required field:

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

## 9. Cross-Field Rules

| Rule ID | Rule |
|---|---|
| CFG-X-001 | `preferred_board_cell_px >= minimum_board_cell_px` |
| CFG-X-002 | `min_events_per_second <= max_events_per_second` |
| CFG-X-003 | `close_after_delay` requires `close_after_seconds` number `>= 0` |
| CFG-X-004 | RGB arrays must be exactly length 3 |
| CFG-X-005 | unknown config fields are rejected |
| CFG-X-006 | `schema_version` must match v1 exactly |

---

## 10. Required Error Classes

`config/validation_errors.py` must define:

```python
class DemoConfigError(Exception): ...
class DemoConfigFileNotFoundError(DemoConfigError): ...
class DemoConfigJsonError(DemoConfigError): ...
class DemoConfigValidationError(DemoConfigError): ...
```

---

## 11. Forbidden Ownership

Config modules must not:

```text
import pygame
open pygame window
load grid .npy
load metrics JSON
calculate replay state
draw status panel
start playback
```

Rendering modules must not:

```text
import Pydantic
validate config fields
load config file
```

---

## 12. Required Tests

| Test File | Required Coverage |
|---|---|
| `test_config_models.py` | field types, defaults, enums, numeric ranges, cross-field rules |
| `test_config_loader.py` | missing file, malformed JSON, invalid config, typed errors |
| `test_config_schema_contract.py` | schema validity, default config validity, invalid examples |
| `test_speed_policy.py` | playback fields consumed through validated `PlaybackConfig`, raw dict rejection, mine-count formula, and min/max clamps |
| `test_finish_policy.py` | finish fields consumed correctly |
| `test_window_geometry.py` | window fields consumed correctly |
| `test_color_palette.py` | RGB fields consumed correctly |
| `test_status_text.py` | status visibility fields consumed correctly |
| `test_architecture_boundaries.py` | Pydantic import isolation, jsonschema runtime exclusion |

---

## 13. Acceptance Evidence

Required commands:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_config_models
python -m unittest tests.demo.iter9_visual_solver.test_config_loader
python -m unittest tests.demo.iter9_visual_solver.test_config_schema_contract
python -m unittest discover -s tests -p "test_*.py"
```

Required manual checks:

- [ ] Default config file exists at correct path.
- [ ] Default finish mode is `stay_open`.
- [ ] Playback speed values can be edited without code changes.
- [ ] Invalid config fails before pygame starts.
- [ ] Error message identifies bad field path.

---

## 14. Completion Checklist

- [ ] Every config field is documented.
- [ ] Every config field exists in schema.
- [ ] Every config field exists in Pydantic model.
- [ ] Default config validates.
- [ ] Unknown fields are rejected.
- [ ] Cross-field rules are tested.
- [ ] Config does not leak into rendering logic.
- [ ] Schema docs and config contract agree.
