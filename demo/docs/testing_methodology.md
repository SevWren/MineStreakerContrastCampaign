# Iter9 Visual Solver Demo — Testing Methodology

## Target Path

This document is intended for:

```text
D:\Github\MineSweepResearchFilesFinalIteration\demo\docs\testing_methodology.md
```

## Purpose

This document defines exactly what belongs in each test support file and each test file for the Iter9 Visual Solver Demo.

The testing design is built for LLM-assisted development. It prevents the LLM from creating large, duplicate-heavy, mixed-responsibility test files.

## Core Rule

Every test file has one ownership area.

A test file must not become a general demo test bucket. If a test needs setup from multiple unrelated areas, move setup into fixtures, builders, or helpers.

---

# 1. Test Package Layout

Correct structure:

```text
tests/
  demo/
    __init__.py

    iter9_visual_solver/
      __init__.py

      fixtures/
        __init__.py
        configs.py
        grids.py
        metrics.py
        event_traces.py
        temp_runs.py
        pygame_fakes.py

      builders/
        __init__.py
        config_builder.py
        grid_builder.py
        metrics_builder.py
        event_trace_builder.py
        status_snapshot_builder.py

      helpers/
        __init__.py
        assertions.py
        schema_assertions.py
        filesystem_assertions.py
        import_boundary_assertions.py
        pygame_assertions.py

      test_config_models.py
      test_config_loader.py
      test_config_schema_contract.py
      test_artifact_paths.py
      test_grid_loader.py
      test_metrics_loader.py
      test_event_trace_loader.py
      test_event_trace_writer.py
      test_board_dimensions.py
      test_playback_event.py
      test_speed_policy.py
      test_event_batching.py
      test_event_scheduler.py
      test_replay_state.py
      test_finish_policy.py
      test_color_palette.py
      test_window_geometry.py
      test_board_surface.py
      test_status_text.py
      test_status_panel.py
      test_pygame_adapter_contract.py
      test_pygame_loop_with_fakes.py
      test_cli_args.py
      test_cli_commands.py
      test_run_iter9_launch_hook.py
      test_prompted_launcher.py
      test_architecture_boundaries.py
      test_source_file_modularity.py
```

---

# 2. Universal Test File Rules

Each test file must contain:

1. A module docstring stating the exact behavior under test.
2. `from __future__ import annotations`.
3. `import unittest`.
4. Only the fixtures/builders/helpers needed for that file.
5. One `unittest.TestCase` class whose name matches the behavior.
6. Test method names that describe the exact rule being tested.
7. No large inline config dictionaries.
8. No large inline NumPy grids.
9. No repeated JSONL event blocks.
10. No pygame window creation unless the file is a specifically isolated real-pygame smoke test.

Each test file must not contain:

1. Unrelated behavior from another runtime module.
2. Setup duplicated from another file.
3. Pygame imports unless that file is a pygame fake/adapter/loop test.
4. Pydantic imports unless testing config models directly.
5. jsonschema imports except through `helpers/schema_assertions.py`.
6. Business logic copied from the runtime implementation.

---

# 3. Test Support Files: Exact Contents

## 3.1 `fixtures/configs.py`

Belongs here:

- valid baseline config dictionary
- invalid config dictionary variants
- simple config mutation helpers

Must include:

```python
default_demo_config_dict()
config_with_finish_mode(mode, close_after_seconds=None)
config_with_playback_multiplier(value)
invalid_config_missing_schema_version()
invalid_config_bad_rgb_tuple()
invalid_config_negative_speed()
```

Must not include:

- Pydantic model imports
- file I/O
- pygame imports
- playback speed calculations

## 3.2 `fixtures/grids.py`

Belongs here:

- reusable NumPy grids
- tiny, wide, tall, empty, checkerboard, and line-art-like grids

Must include:

```python
tiny_2x2_grid()
wide_300x10_grid()
tall_10x300_grid()
empty_grid(height, width)
checker_mine_grid(height, width)
line_art_like_grid()
```

Must not include:

- file I/O
- metrics dictionaries
- pygame surfaces
- playback events

## 3.3 `fixtures/metrics.py`

Belongs here:

- reusable Iter9 metrics dictionaries
- source-image metrics variants
- unknown-count variants
- artifact inventory variants

Must include:

```python
minimal_iter9_metrics(board="300x942", seed=11)
metrics_with_source_image(name)
metrics_with_unknowns(n_unknown)
metrics_with_artifact_inventory(**paths)
```

Must not include:

- NumPy grids
- Pydantic models
- pygame objects

## 3.4 `fixtures/event_traces.py`

Belongs here:

- reusable JSONL event trace strings
- valid and invalid trace examples

Must include:

```python
valid_flag_only_trace()
valid_safe_and_mine_trace()
trace_with_duplicate_cell()
trace_with_out_of_bounds_cell()
trace_with_unknown_state()
```

Must not include:

- event scheduling
- pygame drawing
- file writing

## 3.5 `fixtures/temp_runs.py`

Belongs here:

- temporary Iter9 run folder creation
- helper methods that write grid, metrics, config, and trace files

Must include:

```python
make_temp_iter9_run_dir()
write_grid_artifact()
write_metrics_artifact()
write_event_trace_artifact()
write_demo_config()
```

Must not include:

- assertions
- playback logic
- rendering logic

## 3.6 `fixtures/pygame_fakes.py`

Belongs here:

- fake pygame seams used by tests that must not open a real window

Must include:

```python
FakeClock
FakeSurface
FakeFont
FakeEventQueue
FakeDisplay
FakePygameModule
```

Must not include:

- real pygame import
- real display creation
- actual rendering implementation

## 3.7 `builders/config_builder.py`

Belongs here:

- fluent config builder for controlled variations

Must include:

```python
DemoConfigBuilder.with_finish_mode(...)
DemoConfigBuilder.with_base_events_per_second(...)
DemoConfigBuilder.with_mine_count_multiplier(...)
DemoConfigBuilder.with_max_events_per_second(...)
DemoConfigBuilder.build_dict()
```

Must not include:

- config validation
- file loading
- pygame

## 3.8 `builders/grid_builder.py`

Belongs here:

- fluent grid builder for controlled mine placement

Must include:

```python
GridBuilder(height, width)
GridBuilder.with_mines(cells)
GridBuilder.with_diagonal_mines()
GridBuilder.build()
```

Must not include:

- file writing
- metrics generation
- playback event generation

## 3.9 `builders/metrics_builder.py`

Belongs here:

- fluent metrics dictionary builder

Must include:

```python
MetricsBuilder.with_source_image(name)
MetricsBuilder.with_board(board)
MetricsBuilder.with_seed(seed)
MetricsBuilder.with_unknown_count(n_unknown)
MetricsBuilder.build_dict()
```

Must not include:

- grid generation
- schema validation
- pygame

## 3.10 `builders/event_trace_builder.py`

Belongs here:

- fluent JSONL trace builder

Must include:

```python
EventTraceBuilder.flag(y, x)
EventTraceBuilder.safe(y, x)
EventTraceBuilder.unknown(y, x)
EventTraceBuilder.build_rows()
EventTraceBuilder.build_jsonl()
```

Must not include:

- event scheduling
- grid loading
- rendering

## 3.11 `builders/status_snapshot_builder.py`

Belongs here:

- status snapshot test object builder

Must include:

```python
StatusSnapshotBuilder.with_board(width, height)
StatusSnapshotBuilder.with_playback_speed(speed)
StatusSnapshotBuilder.with_flagged_mines(flagged, total_mines)
StatusSnapshotBuilder.build()
```

Must not include:

- status text formatting
- pygame drawing
- metrics loading

## 3.12 `helpers/assertions.py`

Belongs here:

- semantic assertions that are not file-system, schema, pygame, or import-boundary specific

Must include:

```python
assert_board_dimensions(...)
assert_event_sequence_is_monotonic(...)
assert_replay_finished(...)
assert_status_snapshot_matches_metrics(...)
```

## 3.13 `helpers/schema_assertions.py`

Belongs here:

- JSON and JSON Schema assertions

Must include:

```python
load_json(path)
assert_json_schema_valid(...)
assert_json_validates(...)
assert_json_rejected(...)
```

Must not be used by runtime code.

## 3.14 `helpers/filesystem_assertions.py`

Belongs here:

- path/file assertions

Must include:

```python
assert_file_exists(...)
assert_no_root_ad_hoc_files(...)
assert_only_expected_files_written(...)
```

## 3.15 `helpers/import_boundary_assertions.py`

Belongs here:

- AST/text-based import boundary assertions

Must include:

```python
assert_module_does_not_import(...)
assert_package_does_not_import(...)
assert_import_only_allowed_under(...)
assert_no_forbidden_root_files(...)
assert_no_file_exceeds_line_limit(...)
```

Must not import runtime demo modules.

## 3.16 `helpers/pygame_assertions.py`

Belongs here:

- rendering-specific assertions

Must include:

```python
assert_surface_size(...)
assert_pixel_rgb(...)
assert_window_geometry_fits_screen(...)
```

---

# 4. Exact Contents for Each Test File


## 4.1 `test_config_models.py`

### Ownership

Config model validation

### Runtime module(s) under test

- `demos/iter9_visual_solver/config/models.py`

### Allowed shared test support

- `tests.demo.iter9_visual_solver.fixtures.configs`
- `tests.demo.iter9_visual_solver.builders.config_builder`

### What belongs in this file

This file tests Pydantic model shape and field-level validation only.

### Required test cases

- [ ] valid default config is accepted
- [ ] missing schema_version is rejected
- [ ] invalid finish_behavior.mode is rejected
- [ ] invalid RGB array length is rejected
- [ ] RGB value outside 0-255 is rejected
- [ ] negative playback speeds are rejected
- [ ] min_events_per_second greater than max_events_per_second is rejected
- [ ] close_after_delay requires close_after_seconds
- [ ] stay_open allows close_after_seconds to be null

### What must not belong in this file

Do not load config files from disk. Do not import pygame. Do not test playback speed math beyond validating config fields.

---


## 4.2 `test_config_loader.py`

### Ownership

Config file loading

### Runtime module(s) under test

- `demos/iter9_visual_solver/config/loader.py`

### Allowed shared test support

- `fixtures/configs.py`
- `fixtures/temp_runs.py`

### What belongs in this file

This file tests file-based config loading and conversion into validated runtime config.

### Required test cases

- [ ] loader reads valid JSON config from a provided path
- [ ] loader returns typed config model, not raw dict
- [ ] missing config path raises typed config error
- [ ] malformed JSON raises typed config error with path
- [ ] invalid config content raises typed config validation error
- [ ] loader does not start pygame or playback

### What must not belong in this file

Do not test the full JSON Schema. Do not test pygame. Do not test runtime playback behavior.

---


## 4.3 `test_config_schema_contract.py`

### Ownership

Config JSON Schema contract

### Runtime module(s) under test

- `demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json`
- `demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.md`

### Allowed shared test support

- `fixtures/configs.py`
- `helpers/schema_assertions.py`

### What belongs in this file

This file verifies committed config schema artifacts, not Pydantic internals.

### Required test cases

- [ ] config schema JSON file exists under demo/docs/json_schemas
- [ ] config schema is valid Draft 2020-12 JSON Schema
- [ ] default config fixture validates against schema
- [ ] missing schema_version fixture fails against schema
- [ ] bad RGB tuple fixture fails against schema
- [ ] negative speed fixture fails against schema
- [ ] Markdown schema doc exists beside JSON schema
- [ ] Markdown schema doc documents every top-level section

### What must not belong in this file

Do not import pygame. Do not import runtime rendering modules. Do not duplicate large config dictionaries inline.

---


## 4.4 `test_artifact_paths.py`

### Ownership

Artifact path and name contracts

### Runtime module(s) under test

- `demos/iter9_visual_solver/io/artifact_paths.py`
- `demos/iter9_visual_solver/contracts/artifact_names.py`

### Allowed shared test support

- `fixtures/temp_runs.py`
- `helpers/filesystem_assertions.py`

### What belongs in this file

This file tests artifact naming and path resolution only.

### Required test cases

- [ ] grid latest filename is grid_iter9_latest.npy
- [ ] metrics filename pattern accepts board label
- [ ] event trace filename is solver_event_trace.jsonl
- [ ] artifact path resolver finds required grid and metrics paths
- [ ] artifact path resolver reports missing required files clearly
- [ ] artifact path resolver treats solver_event_trace as optional for MVP

### What must not belong in this file

Do not load NumPy grids here. Do not parse metrics JSON here. Those belong in loader tests.

---


## 4.5 `test_grid_loader.py`

### Ownership

Grid artifact loading

### Runtime module(s) under test

- `demos/iter9_visual_solver/io/grid_loader.py`

### Allowed shared test support

- `fixtures/grids.py`
- `fixtures/temp_runs.py`
- `builders/grid_builder.py`

### What belongs in this file

This file tests loading and validating grid artifacts.

### Required test cases

- [ ] valid .npy grid loads as NumPy array
- [ ] loaded grid preserves shape
- [ ] loaded grid preserves mine values
- [ ] missing grid file raises artifact error
- [ ] non-2D grid is rejected
- [ ] non-numeric or unsupported dtype is rejected if contract forbids it
- [ ] loader does not calculate window size
- [ ] loader does not create playback events

### What must not belong in this file

Do not test pygame surfaces. Do not test final-grid replay ordering. Do not parse metrics.

---


## 4.6 `test_metrics_loader.py`

### Ownership

Metrics artifact loading

### Runtime module(s) under test

- `demos/iter9_visual_solver/io/metrics_loader.py`

### Allowed shared test support

- `fixtures/metrics.py`
- `fixtures/temp_runs.py`
- `builders/metrics_builder.py`

### What belongs in this file

This file tests metrics JSON loading and required-field validation.

### Required test cases

- [ ] valid metrics JSON loads into expected data structure
- [ ] source image name is preserved
- [ ] board width and height are read
- [ ] seed is read
- [ ] n_unknown is read
- [ ] missing metrics file raises artifact error
- [ ] malformed metrics JSON raises artifact error
- [ ] missing required metrics field raises artifact error
- [ ] loader does not validate grid shape against metrics; mismatch behavior belongs in integration/demo input validation

### What must not belong in this file

Do not calculate status text. Do not calculate playback speed. Do not import pygame.

---


## 4.7 `test_event_trace_loader.py`

### Ownership

Solver event trace loading

### Runtime module(s) under test

- `demos/iter9_visual_solver/io/event_trace_loader.py`
- `demos/iter9_visual_solver/domain/playback_event.py`

### Allowed shared test support

- `fixtures/event_traces.py`
- `builders/event_trace_builder.py`
- `helpers/assertions.py`

### What belongs in this file

This file tests reading event trace rows and converting them into domain events.

### Required test cases

- [ ] valid JSONL trace loads into playback event objects
- [ ] event order is preserved
- [ ] steps are monotonic or rejected according to contract
- [ ] invalid JSONL row is rejected
- [ ] unknown state is rejected
- [ ] unknown display value is rejected
- [ ] missing required field is rejected
- [ ] out-of-bounds cell handling follows contract

### What must not belong in this file

Do not schedule events per frame. Do not draw events. Do not load final grid fallback.

---


## 4.8 `test_event_trace_writer.py`

### Ownership

Solver event trace writing

### Runtime module(s) under test

- `demos/iter9_visual_solver/io/event_trace_writer.py`

### Allowed shared test support

- `builders/event_trace_builder.py`
- `fixtures/temp_runs.py`

### What belongs in this file

This file tests writing event trace artifacts only.

### Required test cases

- [ ] writer creates solver_event_trace.jsonl
- [ ] writer writes one JSON object per line
- [ ] writer preserves step order
- [ ] writer rejects unserializable event data
- [ ] writer creates parent directory if contract allows it
- [ ] writer does not validate playback scheduling

### What must not belong in this file

Do not test loading. Do not test pygame. Do not calculate solver events.

---


## 4.9 `test_board_dimensions.py`

### Ownership

Board dimension domain model

### Runtime module(s) under test

- `demos/iter9_visual_solver/domain/board_dimensions.py`

### Allowed shared test support

- `fixtures/grids.py`
- `builders/grid_builder.py`
- `helpers/assertions.py`

### What belongs in this file

This file tests pure board dimension logic.

### Required test cases

- [ ] board dimensions are derived from grid.shape
- [ ] height comes from first grid dimension
- [ ] width comes from second grid dimension
- [ ] total cells equals width * height
- [ ] invalid zero-sized grid is rejected
- [ ] board label formats as WxH if contract requires it

### What must not belong in this file

Do not calculate window size. Do not load files. Do not import pygame.

---


## 4.10 `test_playback_event.py`

### Ownership

Playback event domain model

### Runtime module(s) under test

- `demos/iter9_visual_solver/domain/playback_event.py`

### Allowed shared test support

- `builders/event_trace_builder.py`

### What belongs in this file

This file tests event data validity only.

### Required test cases

- [ ] MINE/flag event is accepted
- [ ] SAFE/reveal event is accepted
- [ ] UNKNOWN/unknown event is accepted if contract allows it
- [ ] invalid state is rejected
- [ ] invalid display is rejected
- [ ] negative coordinates are rejected
- [ ] step must be positive
- [ ] event source is preserved if modeled

### What must not belong in this file

Do not load JSONL. Do not schedule frames. Do not draw board updates.

---


## 4.11 `test_speed_policy.py`

### Ownership

Playback speed policy

### Runtime module(s) under test

- `demos/iter9_visual_solver/playback/speed_policy.py`

### Allowed shared test support

- `builders/config_builder.py`

### What belongs in this file

This file tests playback speed math independently from pygame.
It must pass a validated `PlaybackConfig` object to the speed policy and assert
that raw playback dictionaries are rejected.

### Required test cases

- [ ] mine_count_scaled uses base + total_mines * multiplier
- [ ] result clamps to min_events_per_second
- [ ] result clamps to max_events_per_second
- [ ] zero mines returns at least min speed
- [ ] large mine count does not exceed max speed
- [ ] speed calculation returns integer or documented numeric type
- [ ] raw dict playback config is rejected
- [ ] negative mine count is rejected
- [ ] unsupported playback mode is rejected
- [ ] speed policy does not import pygame

### What must not belong in this file

Do not load config from disk. Do not open pygame. Do not schedule event batches.

---


## 4.12 `test_event_batching.py`

### Ownership

Event batching per frame

### Runtime module(s) under test

- `demos/iter9_visual_solver/playback/event_batching.py`

### Allowed shared test support

- `builders/config_builder.py`

### What belongs in this file

This file tests converting playback speed into per-frame batch sizes.

### Required test cases

- [ ] events per frame uses events_per_second / target_fps
- [ ] batch size is at least 1 when events remain
- [ ] fractional remainder behavior follows contract
- [ ] events_per_second <= 0 is rejected
- [ ] target_fps <= 0 is rejected
- [ ] batching can be disabled if config supports it

### What must not belong in this file

Do not test scheduler state. Do not import pygame clock.

---


## 4.13 `test_event_scheduler.py`

### Ownership

Playback event scheduler

### Runtime module(s) under test

- `demos/iter9_visual_solver/playback/event_scheduler.py`

### Allowed shared test support

- `builders/event_trace_builder.py`
- `helpers/assertions.py`

### What belongs in this file

This file tests stateful event scheduling.

### Required test cases

- [ ] scheduler returns events in order
- [ ] scheduler respects batch size
- [ ] scheduler returns final partial batch
- [ ] scheduler reports completion
- [ ] scheduler does not drop or duplicate events
- [ ] empty event list finishes immediately

### What must not belong in this file

Do not calculate playback speed. Do not draw events. Do not load artifacts.

---


## 4.14 `test_replay_state.py`

### Ownership

Replay state tracking

### Runtime module(s) under test

- `demos/iter9_visual_solver/playback/replay_state.py`

### Allowed shared test support

- `builders/event_trace_builder.py`

### What belongs in this file

This file tests in-memory replay counters and completion state.

### Required test cases

- [ ] initial state starts with zero applied events
- [ ] applying mine event increments flagged mine count
- [ ] applying safe event increments safe solved count
- [ ] unknown remaining updates according to contract
- [ ] applied event count is exposed
- [ ] total event count is exposed
- [ ] status snapshot includes resolved playback speed
- [ ] finished is true after all events applied
- [ ] duplicate event handling follows contract

### What must not belong in this file

Do not schedule batches. Do not import pygame. Do not format status text.

---


## 4.15 `test_finish_policy.py`

### Ownership

Finish behavior policy

### Runtime module(s) under test

- `demos/iter9_visual_solver/playback/finish_policy.py`

### Allowed shared test support

- `builders/config_builder.py`

### What belongs in this file

This file tests close/stay-open policy independently from pygame.

### Required test cases

- [ ] stay_open never auto-closes
- [ ] close_immediately closes when playback finishes
- [ ] close_after_delay does not close before delay
- [ ] close_after_delay closes after delay
- [ ] invalid mode is rejected by config model, not by pygame loop

### What must not belong in this file

Do not run pygame loop. Do not test window events.

---


## 4.16 `test_color_palette.py`

### Ownership

Color palette mapping

### Runtime module(s) under test

- `demos/iter9_visual_solver/rendering/color_palette.py`

### Allowed shared test support

- `fixtures/configs.py`
- `builders/config_builder.py`

### What belongs in this file

This file tests conversion from validated visual config to renderer palette.

### Required test cases

- [ ] palette uses unseen_cell_rgb
- [ ] palette uses flagged_mine_rgb
- [ ] palette uses safe_cell_rgb
- [ ] palette uses unknown_cell_rgb
- [ ] palette uses background_rgb
- [ ] RGB values convert to tuples if renderer expects tuples

### What must not belong in this file

Do not import Pydantic. Do not open pygame.

---


## 4.17 `test_window_geometry.py`

### Ownership

Window geometry calculation

### Runtime module(s) under test

- `demos/iter9_visual_solver/rendering/window_geometry.py`
- `demos/iter9_visual_solver/domain/board_dimensions.py`

### Allowed shared test support

- `builders/grid_builder.py`
- `fixtures/configs.py`
- `helpers/pygame_assertions.py`

### What belongs in this file

This file tests pure window sizing logic.

### Required test cases

- [ ] window geometry uses actual board width and height
- [ ] status panel width is included
- [ ] preferred cell size is honored when it fits
- [ ] minimum cell size is enforced
- [ ] fit_to_screen scales display without changing board dimensions
- [ ] max_screen_fraction limits window dimensions
- [ ] wide and tall boards both fit correctly
- [ ] maximized windows produce an enlarged board draw rect with `board_scale > 1`
- [ ] smaller resize produces `board_scale < 1` without distorting board aspect
- [ ] source preview rect preserves source-image aspect when source dimensions are available

### What must not belong in this file

Do not create pygame window. Do not draw surfaces.

---


## 4.18 `test_board_surface.py`

### Ownership

Board surface model/pixel mapping

### Runtime module(s) under test

- `demos/iter9_visual_solver/rendering/board_surface.py`

### Allowed shared test support

- `builders/grid_builder.py`
- `fixtures/configs.py`

### What belongs in this file

This file tests board pixel/state mapping.

### Required test cases

- [ ] surface/model width equals board width
- [ ] surface/model height equals board height
- [ ] mine event maps to flagged mine color
- [ ] safe event maps to safe color when show_safe_cells is enabled
- [ ] unknown event maps to unknown color when show_unknown_cells is enabled
- [ ] unseen cells use unseen color
- [ ] logical offscreen board surface is nearest-neighbor scaled/blitted into the destination rect

### What must not belong in this file

Do not run pygame loop. Do not parse metrics.

---


## 4.19 `test_status_text.py`

### Ownership

Status text generation

### Runtime module(s) under test

- `demos/iter9_visual_solver/rendering/status_text.py`
- `demos/iter9_visual_solver/domain/status_snapshot.py`

### Allowed shared test support

- `builders/status_snapshot_builder.py`

### What belongs in this file

This file tests status text formatting only.

### Required test cases

- [ ] source image line is formatted
- [ ] board dimensions line shows actual W x H
- [ ] seed line is formatted
- [ ] total cells line is formatted
- [ ] mines flagged line is formatted as current / total
- [ ] safe cells solved line is formatted
- [ ] unknown remaining line is formatted
- [ ] playback speed line uses calculated speed
- [ ] finish message appears only when finished

### What must not belong in this file

Do not draw fonts. Do not load metrics. Do not import pygame.

---


## 4.20 `test_status_panel.py`

### Ownership

Status panel drawing

### Runtime module(s) under test

- `demos/iter9_visual_solver/rendering/status_panel.py`

### Allowed shared test support

- `fixtures/pygame_fakes.py`
- `builders/status_snapshot_builder.py`

### What belongs in this file

This file tests drawing status lines onto a surface seam.

### Required test cases

- [ ] status panel fills background
- [ ] status panel renders provided text lines
- [ ] status panel uses injected/fake font
- [ ] status panel does not compute status text itself
- [ ] status panel handles empty line list
- [ ] wide mode renders structured label/value rows with right-aligned values
- [ ] narrow mode wraps/clips structured rows safely

### What must not belong in this file

Do not parse metrics. Do not calculate playback speed.

---


## 4.21 `test_pygame_adapter_contract.py`

### Ownership

pygame adapter seam

### Runtime module(s) under test

- `demos/iter9_visual_solver/rendering/pygame_adapter.py`

### Allowed shared test support

- `fixtures/pygame_fakes.py`

### What belongs in this file

This file tests pygame adapter behavior through fakes.

### Required test cases

- [ ] adapter initializes injected pygame module
- [ ] adapter opens window with requested size
- [ ] adapter sets caption
- [ ] adapter exposes event polling seam
- [ ] adapter exposes clock/tick seam
- [ ] adapter closes pygame cleanly
- [ ] adapter creates offscreen surfaces and scale/blit operations for responsive board rendering

### What must not belong in this file

Do not use real pygame in default unit test path.

---


## 4.22 `test_pygame_loop_with_fakes.py`

### Ownership

pygame loop orchestration with fakes

### Runtime module(s) under test

- `demos/iter9_visual_solver/rendering/pygame_loop.py`

### Allowed shared test support

- `fixtures/pygame_fakes.py`
- `builders/event_trace_builder.py`
- `builders/status_snapshot_builder.py`

### What belongs in this file

This file tests event-loop orchestration without a real window.

### Required test cases

- [ ] loop accepts injected fake pygame module
- [ ] loop draws at least one frame
- [ ] loop applies event batches
- [ ] loop updates status snapshot/text through provided seams
- [ ] loop exits on fake QUIT event
- [ ] loop honors finish policy
- [ ] loop preserves replay state while recomputing geometry on resize/maximize
- [ ] loop passes the current dynamic board/status/source-preview rects to renderers

### What must not belong in this file

Do not validate config. Do not load artifacts. Do not calculate speed formula.

---


## 4.23 `test_cli_args.py`

### Ownership

CLI argument parsing

### Runtime module(s) under test

- `demos/iter9_visual_solver/cli/args.py`

### Allowed shared test support

- none beyond standard library unless needed

### What belongs in this file

This file tests CLI parsing only.

### Required test cases

- [ ] parser accepts --grid
- [ ] parser accepts --metrics
- [ ] parser accepts --config
- [ ] parser accepts optional --event-trace if implemented
- [ ] missing required args fail
- [ ] default config path matches contract

### What must not belong in this file

Do not load files. Do not start pygame.

---


## 4.24 `test_cli_commands.py`

### Ownership

CLI command orchestration

### Runtime module(s) under test

- `demos/iter9_visual_solver/cli/commands.py`

### Allowed shared test support

- `fixtures/temp_runs.py`

### What belongs in this file

This file tests command-level orchestration seams.

### Required test cases

- [ ] main function exists
- [ ] command wires parsed args into loader/playback/rendering orchestration
- [ ] command passes resolved events_per_second and events_per_frame into the pygame loop
- [ ] command returns success code on valid run
- [ ] command returns nonzero or raises typed error on invalid config
- [ ] command does not contain business logic directly

### What must not belong in this file

Do not test individual speed/window/loader rules here.

Additional responsive/polish test ownership:

- `test_status_view_model.py` covers badge state, progress ratios, legend
  colors, raw status-line reuse, and source-preview placeholder metadata.
- `test_window_chrome.py` covers header, board border, and divider drawing
  through adapter/fakes without pygame imports.
- `test_window_geometry.py` covers display bounds, placement, live resize
  geometry, fit flags, scaled board draw rects, dynamic panel width, and the
  bottom-right aspect-fit `source_preview_rect`.
- `test_pygame_adapter_contract.py` covers display bounds, placement,
  resize-window behavior, resize event helpers, and backwards-compatible
  drawing primitives plus offscreen surface scale/blit seams.

---


## 4.25 `test_run_iter9_launch_hook.py`

### Ownership

Optional run_iter9 hook contract

### Runtime module(s) under test

- `run_iter9.py`
- `demos/iter9_visual_solver/cli/launch_from_iter9.py`

### Allowed shared test support

- `fixtures/temp_runs.py`

### What belongs in this file

This file tests that integration with the existing pipeline remains thin.

### Required test cases

- [ ] launch hook function exists
- [ ] hook receives completed grid path and metrics path
- [ ] hook passes paths to demo command/orchestrator
- [ ] run_iter9 behavior is unchanged when --demo-gui is omitted
- [ ] run_iter9 does not import pygame directly

### What must not belong in this file

Do not test full Iter9 pipeline here. Do not draw GUI.

---

## 4.25.1 `test_prompted_launcher.py`

### Ownership

Prompted run-directory launcher contract

### Runtime module(s) under test

- `demos/iter9_visual_solver/cli/prompted_launcher.py`
- `demo/run_iter9_visual_solver_demo_prompted.ps1` by command documentation

### Allowed shared test support

- `fixtures/temp_runs.py`
- `builders/config_builder.py`
- `builders/grid_builder.py`
- `builders/metrics_builder.py`

### What belongs in this file

This file tests that the interactive wrapper resolves completed run artifacts,
parses prompt values, writes a temporary config override, and delegates to the
standalone demo CLI.

### Required test cases

- [ ] speed modifiers accept values such as `50x`, `100x`, and `300x`
- [ ] Y/N prompt values map to close-immediately or stay-open finish behavior
- [ ] wrapper resolves `grid_iter9_latest.npy` and `metrics_iter9_<board>.json`
- [ ] wrapper includes `solver_event_trace.jsonl` when present
- [ ] generated config applies speed modifier and finish behavior
- [ ] wrapper delegates to `cli.commands.main(...)`

### What must not belong in this file

Do not open a real pygame window. Do not test the full Iter9 pipeline.

---


## 4.26 `test_architecture_boundaries.py`

### Ownership

Import and ownership boundaries

### Runtime module(s) under test

- `all demo runtime modules`

### Allowed shared test support

- `helpers/import_boundary_assertions.py`
- `helpers/filesystem_assertions.py`

### What belongs in this file

This file is an architecture fitness test suite.

### Required test cases

- [ ] no root-level demo_config.py or demo_visualizer.py
- [ ] pygame imports are rendering-only except fakes/tests
- [ ] Pydantic imports are config-only
- [ ] jsonschema imports are test/schema-helper only
- [ ] domain modules do not import pygame/pydantic/file I/O
- [ ] playback modules do not import pygame
- [ ] pygame loop does not own playback speed formula fields
- [ ] io modules do not import pygame
- [ ] rendering modules do not import Pydantic
- [ ] CLI does not draw pixels or create pygame window directly

### What must not belong in this file

Do not test runtime behavior here except import/source-boundary facts.

---


## 4.27 `test_source_file_modularity.py`

### Ownership

File size and responsibility smoke tests

### Runtime module(s) under test

- `all demo runtime and test files`

### Allowed shared test support

- `helpers/import_boundary_assertions.py`

### What belongs in this file

This file detects architectural drift and test bloat.

### Required test cases

- [ ] runtime files do not exceed 500 physical lines unless exempted
- [ ] test files do not exceed 500 physical lines unless exempted
- [ ] suspicious layer-mixing keyword combinations are rejected
- [ ] large repeated inline config dictionaries are rejected when fixtures exist
- [ ] large repeated grid literals are rejected when grid builders exist

### What must not belong in this file

Do not enforce line count as the only rule. It must also check responsibility/import smells.

---


# 5. Completion Checklist for This Testing Methodology

- [ ] Every test file has one clear ownership area.
- [ ] Every planned runtime module has a matching test file.
- [ ] Every fixture file has defined contents and exclusions.
- [ ] Every builder file has defined contents and exclusions.
- [ ] Every helper file has defined contents and exclusions.
- [ ] pygame is tested through fakes before any real-window smoke test.
- [ ] Config/schema testing is isolated from rendering.
- [ ] Playback math is isolated from pygame.
- [ ] Window sizing is isolated from pygame.
- [ ] Architecture boundary tests prevent dependency drift.
- [ ] Source modularity tests prevent large mixed-responsibility files.
- [ ] No test file becomes a dumping ground for multiple modules.

---

# 6. Runtime Optimization Test Addendum

Large-board playback optimization must add focused tests in the existing owner
test files rather than creating broad integration-only coverage.

Required ownership:

- `test_event_source.py`: typed/lazy event-store metadata, overflow rejection,
  row-major final-grid batches, and no final-grid event materialization for
  metadata.
- `test_event_scheduler.py`: typed batch views and unchanged list-backed
  compatibility behavior.
- `test_replay_state.py`: duplicate/state-change counters and O(1) snapshot
  behavior.
- `test_board_surface.py`: logical surface creation once, dirty batch cell
  drawing, and scale/blit reuse.
- `test_pygame_loop_with_fakes.py`: resize/maximize reuse of the logical board
  surface and close responsiveness.
- `test_status_view_model.py`: static cache reuse with dynamic snapshot updates.
- `test_event_trace_loader.py`: streaming typed store output and duplicate or
  decreasing step rejection.
