# Iter9 Visual Solver Demo — Artifact Consumption Contract

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Demo I/O and input architecture |
| Applies to | `demos/iter9_visual_solver/io/`, `playback/event_source.py`, `domain/demo_input.py` |
| Required before | artifact path resolver, grid loader, metrics loader, event trace loader, event source selector, demo CLI/hook |
| Traceability IDs | DEMO-REQ-001, DEMO-REQ-006, DEMO-REQ-007, DEMO-REQ-009, DEMO-TEST-004, DEMO-TEST-005, DEMO-TEST-006, DEMO-TEST-007, DEMO-TEST-008 |
| Change rule | Any artifact name, location, schema, fallback rule, or loader behavior change must update this file, runtime package contract, schema docs, tests, completion gate, and traceability matrix. |

---

## 1. Purpose

This contract defines what Iter9 artifacts the Visual Solver Demo consumes, where those artifacts are expected to live, which modules load them, how invalid artifacts fail, and how final-grid replay and solver-event trace replay are selected.

The demo must consume existing Iter9 outputs without refactoring the base Iter9 pipeline.

---

## 2. Scope

This contract applies to:

```text
demos/iter9_visual_solver/io/artifact_paths.py
demos/iter9_visual_solver/io/grid_loader.py
demos/iter9_visual_solver/io/metrics_loader.py
demos/iter9_visual_solver/io/event_trace_loader.py
demos/iter9_visual_solver/io/event_trace_writer.py
demos/iter9_visual_solver/io/json_reader.py
demos/iter9_visual_solver/domain/demo_input.py
demos/iter9_visual_solver/playback/event_source.py
tests/demo/iter9_visual_solver/test_artifact_paths.py
tests/demo/iter9_visual_solver/test_grid_loader.py
tests/demo/iter9_visual_solver/test_metrics_loader.py
tests/demo/iter9_visual_solver/test_event_trace_loader.py
tests/demo/iter9_visual_solver/test_event_trace_writer.py
```

This contract does not own Iter9 pipeline generation logic, SA optimization, solver logic, repair logic, matplotlib report generation, pygame rendering, or playback speed formula.

---

## 3. Iter9 Artifact Inputs

## 3.1 Required MVP artifacts

A completed Iter9 run directory must contain:

```text
grid_iter9_latest.npy
metrics_iter9_<board>.json
```

where `<board>` is a board label such as:

```text
300x942
```

## 3.2 Optional/future artifacts

Optional event trace artifact:

```text
solver_event_trace.jsonl
```

Optional image/report artifacts may exist but are not required for MVP playback:

```text
iter9_<board>_FINAL.png
iter9_<board>_FINAL_explained.png
repair_overlay_<board>.png
repair_overlay_<board>_explained.png
failure_taxonomy.json
repair_route_decision.json
visual_delta_summary.json
```

---

## 4. Artifact Names

Executable constants must exist in:

```text
demos/iter9_visual_solver/contracts/artifact_names.py
```

Required constants:

```python
GRID_LATEST_FILENAME = "grid_iter9_latest.npy"
EVENT_TRACE_FILENAME = "solver_event_trace.jsonl"
METRICS_FILENAME_PREFIX = "metrics_iter9_"
METRICS_FILENAME_SUFFIX = ".json"
```

Required helper behavior:

```python
def metrics_filename_for_board(board_label: str) -> str:
    return f"metrics_iter9_{board_label}.json"
```

---

## 5. Artifact Path Resolution

## 5.1 Required API

`io/artifact_paths.py` must define:

```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class DemoArtifactPaths:
    run_dir: Path
    grid_path: Path
    metrics_path: Path
    event_trace_path: Path | None

def metrics_filename_for_board(board_label: str) -> str: ...

def resolve_artifact_paths(
    *,
    run_dir: Path,
    board_label: str | None = None,
    grid_path: Path | None = None,
    metrics_path: Path | None = None,
    event_trace_path: Path | None = None,
) -> DemoArtifactPaths: ...
```

## 5.2 Path resolution rules

Allowed input styles:

| Input Style | Required Behavior |
|---|---|
| explicit `grid_path` and `metrics_path` | use exactly supplied paths |
| `run_dir` + `board_label` | resolve grid latest and metrics by board label |
| `run_dir` without board label | may infer metrics only if exactly one `metrics_iter9_*.json` exists |
| optional `event_trace_path` supplied | use supplied trace path |
| optional trace omitted | look for `solver_event_trace.jsonl` in run dir |

## 5.3 Missing artifact behavior

| Missing Artifact | Behavior |
|---|---|
| grid | blocking error |
| metrics | blocking error |
| event trace | not blocking when final-grid fallback is allowed |
| event trace | blocking when final-grid fallback is disabled |

---

## 6. Grid Artifact Contract

## 6.1 File

```text
grid_iter9_latest.npy
```

## 6.2 Loader API

`io/grid_loader.py` must define:

```python
def load_grid(path: Path) -> np.ndarray: ...
```

## 6.3 Required grid properties

| Property | Required Rule |
|---|---|
| format | NumPy `.npy` |
| dimensions | 2D array |
| shape | `(board_height, board_width)` |
| values | binary mine grid, `0` safe and `1` mine |
| dtype | numeric/bool accepted if values are binary |
| output dtype | implementation may normalize to `np.uint8` or preserve with documented rule |
| contiguous | output should be contiguous if renderer/playback benefits |

## 6.4 Grid validation

Required validation:

- [ ] file exists.
- [ ] file loads with `np.load`.
- [ ] array is 2D.
- [ ] height > 0.
- [ ] width > 0.
- [ ] values are only `0` and `1`.
- [ ] no object dtype.
- [ ] no NaN/inf values.

## 6.5 Grid-derived values

From grid:

```text
board_height = grid.shape[0]
board_width = grid.shape[1]
total_cells = board_width * board_height
total_mines = count(grid == 1)
safe_cells = total_cells - total_mines
```

Grid shape is authoritative for GUI board dimensions.

---

## 7. Metrics Artifact Contract

## 7.1 File

```text
metrics_iter9_<board>.json
```

Example:

```text
metrics_iter9_300x942.json
```

## 7.2 Loader API

`io/metrics_loader.py` must define:

```python
def load_metrics(path: Path) -> dict: ...
```

## 7.3 Required metric fields for demo MVP

The metrics document must provide enough provenance/status context for the demo.

Required preferred fields:

```text
source_image.name or image_name or source_image_name
seed or run_identity.seed
board or run_identity.board
n_unknown
```

Strongly recommended fields:

```text
run_id or run_identity.run_id
source_image.project_relative_path
source_image.sha256
artifact_inventory
solver_summary
repair_route_summary
```

## 7.4 Metrics field fallback rules

| Desired Value | Preferred Source | Fallback Source |
|---|---|---|
| source image name | `source_image.name` | `image_name`, `source_image_name`, `unknown` |
| seed | `run_identity.seed` | `seed`, `unknown` |
| board label | `run_identity.board` | `board`, grid-derived label |
| unknown count | `n_unknown` | replay state computed unknown count |

## 7.5 Metrics validation

Required validation:

- [ ] file exists.
- [ ] valid JSON object.
- [ ] not an array/null/string.
- [ ] board label, if present, is parseable as `<width>x<height>`.
- [ ] seed, if present, is integer or string safely displayable.
- [ ] `n_unknown`, if present, is integer `>= 0`.

Metrics are not authoritative for GUI board dimensions. Grid shape is authoritative.

---

## 8. Solver Event Trace Artifact Contract

## 8.1 File

```text
solver_event_trace.jsonl
```

## 8.2 Purpose

A solver event trace records cell-by-cell replay events in chronological order. This is optional/future for MVP but must have schema and loader contracts so MVP architecture can support it later without refactor.

## 8.3 Loader API

`io/event_trace_loader.py` must define:

```python
def load_event_trace(path: Path) -> list[PlaybackEvent]: ...
```

## 8.4 Writer API

`io/event_trace_writer.py` must define:

```python
def write_event_trace(events: Iterable[PlaybackEvent], path: Path) -> None: ...
```

## 8.5 JSONL row required fields

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

Required row values:

| Field | Rule |
|---|---|
| `schema_version` | `iter9_visual_solver_event_trace.v1` |
| `event_id` | non-empty string; recommended `evt_<zero-padded step>` |
| `step` | integer `>= 0`; zero-based playback step |
| `round` | integer `>= 0` |
| `y` | integer `>= 0` |
| `x` | integer `>= 0` |
| `state` | `SAFE`, `MINE`, `UNKNOWN` |
| `display` | `flag`, `reveal`, `unknown` |

## 8.6 Optional event row fields

The row schema also permits optional fields documented in `solver_event_trace.schema.md`, including:

```text
source
confidence
reason
mine_count_after
safe_count_after
unknown_count_after
elapsed_solver_ms
metadata
```

`source` defaults to `solver_trace` and may be one of:

```text
solver_trace
final_grid_replay
repair_trace
synthetic
```

The MVP renderer must consume normalized playback events and must not require optional diagnostic fields.

## 8.7 Trace ordering

Loader must preserve file order.

Recommended validation:

```text
step values must be strictly increasing
```

If strict monotonic validation is deferred, this must be documented as an approved exception.

## 8.8 Board bounds

Bounds validation requires board dimensions.

When loader receives dimensions, it must reject:

```text
y >= board_height
x >= board_width
```

If loader does not receive dimensions, bounds validation must happen in event source/input validation before playback starts.

---

## 9. Event Source Selection

Owner:

```text
playback/event_source.py
```

Required API:

```python
def build_playback_events_from_final_grid(grid: np.ndarray) -> list[PlaybackEvent]: ...

def select_event_source(
    *,
    input_config: InputConfig,
    grid: np.ndarray,
    trace_events: list[PlaybackEvent] | None,
) -> tuple[list[PlaybackEvent], str]: ...
```

Selection matrix:

| Trace Available | prefer trace | fallback allowed | Result |
|---|---:|---:|---|
| yes | true | any | trace events, source `solver_trace` |
| yes | false | any | final-grid events, source `final_grid_replay` |
| no | any | true | final-grid events, source `final_grid_replay` |
| no | any | false | typed missing trace error |

---

## 10. Final-Grid Replay Contract

MVP final-grid replay must generate deterministic events from grid.

Required behavior:

- Every mine cell eventually produces a flag/mine event.
- Every safe cell may produce a safe/reveal event if safe-cell visualization is enabled or if replay state requires safe counters.
- Event order must be deterministic.
- Event order does not claim to be true solver chronology.
- Replay source must be labeled `final_grid_replay`.

Recommended deterministic order:

```text
row-major order: y from 0 to height-1, x from 0 to width-1
```

If a different order is chosen, it must be documented and tested.

---

## 11. Demo Input Aggregate

`domain/demo_input.py` must define:

```python
@dataclass(frozen=True)
class DemoInput:
    config: DemoConfig
    grid: np.ndarray
    metrics: dict
    board_dimensions: BoardDimensions
    events: list[PlaybackEvent]
    replay_source: str
    artifact_paths: DemoArtifactPaths
```

`DemoInput` must be built only after:

- config validates.
- required artifacts load.
- board dimensions derive from grid.
- event source is selected.
- artifact mismatch policy is applied.

---

## 12. Error Classes

`errors/artifact_errors.py` must define:

```python
class DemoArtifactError(Exception): ...
class DemoArtifactNotFoundError(DemoArtifactError): ...
class DemoArtifactLoadError(DemoArtifactError): ...
class DemoGridValidationError(DemoArtifactError): ...
class DemoMetricsValidationError(DemoArtifactError): ...
class DemoInputValidationError(DemoArtifactError): ...
```

`errors/trace_errors.py` must define:

```python
class DemoTraceError(Exception): ...
class DemoTraceNotFoundError(DemoTraceError): ...
class DemoTraceJsonError(DemoTraceError): ...
class DemoTraceValidationError(DemoTraceError): ...
```

---

## 13. Atomic Write Rule

For event trace writer:

```text
write to temp file
flush/close temp file
replace target with os.replace
```

Required pattern:

```text
solver_event_trace.jsonl.tmp -> solver_event_trace.jsonl
```

No partial trace file may be left as the final file after failure.

---

## 14. Forbidden Ownership

I/O modules must not:

```text
import pygame
open pygame window
calculate playback speed
calculate window geometry
draw status panel
start pygame loop
```

Playback modules must not:

```text
np.load
json.load
open artifacts
discover paths
```

CLI modules must not:

```text
parse grid arrays directly
validate grid values directly
draw GUI directly
```

---

## 15. Required Tests

## 15.1 `test_artifact_paths.py`

- [ ] grid latest filename is `grid_iter9_latest.npy`.
- [ ] metrics filename formats as `metrics_iter9_<board>.json`.
- [ ] event trace filename is `solver_event_trace.jsonl`.
- [ ] resolver accepts explicit grid/metrics paths.
- [ ] resolver accepts run dir + board label.
- [ ] resolver handles missing optional trace.
- [ ] resolver errors on missing grid.
- [ ] resolver errors on missing metrics.
- [ ] resolver errors on ambiguous metrics when board label absent.

## 15.2 `test_grid_loader.py`

- [ ] valid `.npy` grid loads.
- [ ] shape is preserved.
- [ ] binary values accepted.
- [ ] non-binary values rejected.
- [ ] non-2D array rejected.
- [ ] object dtype rejected.
- [ ] missing file raises typed error.
- [ ] malformed `.npy` raises typed error.
- [ ] loader does not import pygame.

## 15.3 `test_metrics_loader.py`

- [ ] valid metrics JSON loads as dict.
- [ ] missing metrics file raises typed error.
- [ ] malformed JSON raises typed error.
- [ ] JSON array/null/string rejected.
- [ ] seed/source/board fallbacks work.
- [ ] invalid board label rejected or handled by documented policy.
- [ ] loader does not import pygame.

## 15.4 `test_event_trace_loader.py`

- [ ] valid JSONL trace loads into playback events.
- [ ] order is preserved.
- [ ] missing required field rejected.
- [ ] invalid JSON row rejected.
- [ ] invalid state rejected.
- [ ] invalid display rejected.
- [ ] negative coordinate rejected.
- [ ] step less than 0 rejected.
- [ ] out-of-bounds cell rejected when dimensions supplied.
- [ ] loader does not import pygame.

## 15.5 `test_event_trace_writer.py`

- [ ] writer creates JSONL file.
- [ ] one JSON object per line.
- [ ] writer preserves event order.
- [ ] writer uses atomic temp/replace behavior.
- [ ] unserializable event rejected.
- [ ] writer does not import pygame.

## 15.6 `test_run_iter9_launch_hook.py`

- [ ] hook receives grid path and metrics path.
- [ ] hook passes paths into demo package.
- [ ] `run_iter9.py` does not import pygame.
- [ ] existing behavior unchanged when demo flag omitted.

---

## 16. Acceptance Evidence

Required commands:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_artifact_paths
python -m unittest tests.demo.iter9_visual_solver.test_grid_loader
python -m unittest tests.demo.iter9_visual_solver.test_metrics_loader
python -m unittest tests.demo.iter9_visual_solver.test_event_trace_loader
python -m unittest tests.demo.iter9_visual_solver.test_event_trace_writer
python -m unittest discover -s tests -p "test_*.py"
```

Manual evidence:

- [ ] A completed Iter9 run directory is used.
- [ ] Demo loads `grid_iter9_latest.npy`.
- [ ] Demo loads matching metrics.
- [ ] If trace is absent, final-grid replay works when fallback is enabled.
- [ ] If fallback is disabled and trace is absent, demo fails before pygame starts with clear error.

---

## 17. Completion Checklist

- [ ] Artifact constants exist.
- [ ] Artifact resolver exists.
- [ ] Grid loader exists.
- [ ] Metrics loader exists.
- [ ] Event trace loader exists.
- [ ] Event trace writer exists.
- [ ] Demo input aggregate exists.
- [ ] Final-grid replay works.
- [ ] Optional solver trace path is supported.
- [ ] Missing required artifact errors are typed and clear.
- [ ] I/O modules do not import pygame.
