# Iter9 Visual Solver Demo — Playback Speed Contract

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Demo playback architecture |
| Applies to | `demos/iter9_visual_solver/playback/speed_policy.py`, `event_batching.py`, `event_scheduler.py`, `rendering/pygame_loop.py` |
| Required before | playback speed implementation, event batching implementation, pygame loop implementation, speed policy tests |
| Traceability IDs | DEMO-REQ-002, DEMO-REQ-004, DEMO-REQ-005, DEMO-TEST-012, DEMO-TEST-013, DEMO-TEST-014 |
| Change rule | Any playback-speed behavior change must update this file, config contract, config schema docs, test methodology, acceptance criteria, completion gate, and traceability matrix. |

---

## 1. Purpose

This contract defines how the Iter9 Visual Solver Demo calculates, applies, displays, and tests playback speed.

The demo must support a minimum visual playback of at least `50+ cells/sec`, but playback speed must not be hardcoded. Speed must be configurable and may scale dynamically when the number of mines grows.

---

## 2. Scope

This contract applies to:

```text
demos/iter9_visual_solver/playback/speed_policy.py
demos/iter9_visual_solver/playback/event_batching.py
demos/iter9_visual_solver/playback/event_scheduler.py
demos/iter9_visual_solver/playback/replay_state.py
demos/iter9_visual_solver/rendering/pygame_loop.py
demos/iter9_visual_solver/rendering/status_text.py
tests/demo/iter9_visual_solver/test_speed_policy.py
tests/demo/iter9_visual_solver/test_event_batching.py
tests/demo/iter9_visual_solver/test_event_scheduler.py
tests/demo/iter9_visual_solver/test_replay_state.py
tests/demo/iter9_visual_solver/test_pygame_loop_with_fakes.py
tests/demo/iter9_visual_solver/test_status_text.py
```

This contract does not own config loading, artifact loading, pygame window creation, board geometry, or status panel drawing.

---

## 3. Definitions

| Term | Meaning |
|---|---|
| Event | A single cell update applied during replay. |
| Playback event | A normalized event object such as flag mine, reveal safe, or mark unknown. |
| Events per second | Target number of cell events applied per second. |
| Target FPS | Target pygame frame rate. |
| Events per frame | Number of playback events applied during one pygame frame. |
| Batch | A group of playback events applied in one frame. |
| Total mines | Count of mine/flag events in the replay source. |
| Safe cells | `total_cells - total_mines`. |
| Final-grid replay | MVP replay mode that generates playback events from the final grid artifact. |
| Solver trace replay | Future replay mode using `solver_event_trace.jsonl`. |

---

## 4. Ownership

## 4.1 Owner modules

| Responsibility | Owner Module |
|---|---|
| Calculate events/sec from config and mine count | `playback/speed_policy.py` |
| Convert events/sec and FPS into frame batches | `playback/event_batching.py` |
| Preserve event order and emit next event batch | `playback/event_scheduler.py` |
| Track applied event counters | `playback/replay_state.py` |
| Display playback speed text | `rendering/status_text.py` |
| Tick pygame frames and request scheduler batches | `rendering/pygame_loop.py` |

## 4.2 Explicit non-owner modules

| Module | Must Not Own |
|---|---|
| `config/models.py` | playback speed formula |
| `config/loader.py` | playback speed formula |
| `io/event_trace_loader.py` | playback speed formula |
| `rendering/pygame_loop.py` | mine-count multiplier formula |
| `rendering/status_panel.py` | speed calculation |
| `cli/commands.py` | speed calculation |
| `run_iter9.py` | speed calculation |

---

## 5. Config Fields Consumed

Playback speed consumes these validated config fields:

| JSON Path | Type | Required | Owner |
|---|---:|---:|---|
| `$.playback.mode` | enum string | yes | `speed_policy.py` |
| `$.playback.min_events_per_second` | integer | yes | `speed_policy.py` |
| `$.playback.base_events_per_second` | integer | yes | `speed_policy.py` |
| `$.playback.mine_count_multiplier` | number | yes | `speed_policy.py` |
| `$.playback.max_events_per_second` | integer | yes | `speed_policy.py` |
| `$.playback.target_fps` | integer | yes | `event_batching.py`, `pygame_loop.py` |
| `$.playback.batch_events_per_frame` | boolean | yes | `event_batching.py` |

---

## 6. Required Playback Mode

MVP required mode:

```text
mine_count_scaled
```

Unknown modes must be rejected by config validation before runtime playback begins.

---

## 7. Speed Formula

For `mine_count_scaled`, the unbounded speed is:

```text
raw_events_per_second =
    base_events_per_second + (total_mines * mine_count_multiplier)
```

The final speed is:

```text
events_per_second =
    clamp(raw_events_per_second, min_events_per_second, max_events_per_second)
```

Then convert to an integer using this rule:

```text
events_per_second = round(raw clamped value to nearest integer)
```

If implementation chooses floor/ceil instead, this contract and tests must be updated.

---

## 8. Required Public API

## 8.1 `playback/speed_policy.py`

Required API:

```python
def calculate_events_per_second(
    playback_config: PlaybackConfig,
    *,
    total_mines: int,
) -> int: ...
```

Required behavior:

- Accepts a validated playback config object, not raw JSON.
- Accepts `total_mines`.
- Returns integer events/sec.
- Applies mode dispatch.
- Applies min/max clamp.
- Does not mutate config.
- Does not import pygame.
- Does not read files.

Required validation:

| Input | Behavior |
|---|---|
| `total_mines < 0` | raise typed playback/config usage error |
| unsupported mode | raise typed playback error or rely on config validation |
| min > max | should be impossible after config validation; raise defensive error if encountered |

## 8.2 `playback/event_batching.py`

Required API:

```python
def calculate_events_per_frame(
    *,
    events_per_second: int,
    target_fps: int,
    batch_events_per_frame: bool,
) -> int: ...
```

Required behavior:

- If batching enabled, return at least `1` while events remain.
- If batching disabled, return `1`.
- Reject `target_fps <= 0`.
- Reject `events_per_second <= 0`.
- Use deterministic math.

MVP formula:

```text
events_per_frame = max(1, ceil(events_per_second / target_fps))
```

## 8.3 `playback/event_scheduler.py`

Required API:

```python
class EventScheduler:
    def __init__(self, events: list[PlaybackEvent], events_per_frame: int): ...
    def next_batch(self) -> list[PlaybackEvent]: ...
    @property
    def finished(self) -> bool: ...
    @property
    def applied_count(self) -> int: ...
    @property
    def total_count(self) -> int: ...
```

Required behavior:

- Emits events in original order.
- Does not drop events.
- Does not duplicate events.
- Emits final partial batch.
- Finishes immediately for empty event list.
- Does not import pygame.
- Does not sleep/tick; pygame loop owns frame timing.

---

## 9. Rounding and Batch Rules

| Value | Rule |
|---|---|
| `total_mines` | integer, `>= 0` |
| `raw_events_per_second` | number |
| clamp result | number |
| returned events/sec | integer |
| events per frame | integer |
| final partial batch | allowed |

MVP rounding:

```python
int(round(clamped_value))
```

MVP frame batch:

```python
math.ceil(events_per_second / target_fps)
```

---

## 10. Example Calculations

## 10.1 Minimum clamp

```text
base_events_per_second = 10
mine_count_multiplier = 0
total_mines = 100
min_events_per_second = 50
max_events_per_second = 12000

raw = 10
events_per_second = 50
```

## 10.2 Dynamic scaling

```text
base_events_per_second = 1000
mine_count_multiplier = 0.08
total_mines = 25000

raw = 1000 + 25000 * 0.08 = 3000
events_per_second = 3000
```

## 10.3 Maximum clamp

```text
base_events_per_second = 1000
mine_count_multiplier = 10
total_mines = 5000
max_events_per_second = 12000

raw = 51000
events_per_second = 12000
```

## 10.4 Events per frame

```text
events_per_second = 12000
target_fps = 60
batch_events_per_frame = true

events_per_frame = 200
```

---

## 11. Runtime Flow

Playback speed must be resolved before pygame frame loop starts:

```text
validated config
+ event source / grid mine count
    ↓
calculate_events_per_second()
    ↓
calculate_events_per_frame()
    ↓
EventScheduler(events, events_per_frame)
    ↓
pygame_loop asks scheduler.next_batch() each frame
```

The pygame loop may use the final `events_per_second` for status display but must not calculate it.

---

## 12. Status Display Rule

The status panel must show:

```text
Playback speed: <events_per_second> cells/sec
```

The number must be the value returned by `calculate_events_per_second()`.

Forbidden:

```text
Playback speed: 50+ cells/sec
Playback speed: <speed>
Playback speed: static
```

---

## 13. Required Error Behavior

| Condition | Required Behavior |
|---|---|
| `total_mines < 0` | typed playback error |
| `events_per_second <= 0` | typed playback error |
| `target_fps <= 0` | typed playback error |
| unsupported playback mode | config validation error before playback or typed playback error |
| empty event list | scheduler finishes immediately; no crash |
| huge event list | scheduler emits batches without materializing duplicate copies |

Error messages must include the field/argument name, invalid value, and expected rule.

---

## 14. Forbidden Implementation Patterns

Forbidden in `speed_policy.py`:

```text
pygame
time.sleep
Path(
open(
json.load
np.load
```

Forbidden in `pygame_loop.py`:

```text
base_events_per_second + total_mines
mine_count_multiplier
max_events_per_second
min_events_per_second
```

Forbidden anywhere:

```text
hardcoded playback speed as final policy
using 50 as only speed
tying speed to static board width
tying speed to static board height
```

---

## 15. Required Tests

## 15.1 `test_speed_policy.py`

- [ ] `mine_count_scaled` uses `base + total_mines * multiplier`.
- [ ] result clamps to `min_events_per_second`.
- [ ] result clamps to `max_events_per_second`.
- [ ] zero mines returns at least minimum speed.
- [ ] large mine count does not exceed maximum speed.
- [ ] returned speed is integer.
- [ ] negative mine count is rejected.
- [ ] unsupported mode is rejected or impossible through config validation.
- [ ] speed policy does not import pygame.

## 15.2 `test_event_batching.py`

- [ ] events per frame uses `ceil(events_per_second / target_fps)`.
- [ ] events per frame is at least `1`.
- [ ] batching disabled returns `1`.
- [ ] target FPS <= 0 is rejected.
- [ ] events/sec <= 0 is rejected.
- [ ] no pygame clock is required.

## 15.3 `test_event_scheduler.py`

- [ ] scheduler returns events in order.
- [ ] scheduler respects batch size.
- [ ] scheduler returns final partial batch.
- [ ] scheduler reports completion.
- [ ] scheduler does not drop events.
- [ ] scheduler does not duplicate events.
- [ ] empty event list finishes immediately.

## 15.4 `test_pygame_loop_with_fakes.py`

- [ ] pygame loop requests scheduler batches.
- [ ] pygame loop does not calculate speed formula.
- [ ] pygame loop remains responsive to quit event during high speed playback.

## 15.5 `test_status_text.py`

- [ ] status line displays calculated playback speed.
- [ ] status line does not display placeholder speed.

---

## 16. Acceptance Evidence

Required commands:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_speed_policy
python -m unittest tests.demo.iter9_visual_solver.test_event_batching
python -m unittest tests.demo.iter9_visual_solver.test_event_scheduler
python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
python -m unittest discover -s tests -p "test_*.py"
```

Manual evidence:

- [ ] changing `mine_count_multiplier` changes observed playback pace.
- [ ] changing `max_events_per_second` limits observed pace.
- [ ] status panel displays calculated speed.
- [ ] GUI remains responsive during high event rates.

---

## 17. Completion Checklist

- [ ] Playback speed is fully config-driven.
- [ ] Dynamic scaling by mine count is implemented.
- [ ] Min/max clamps are implemented.
- [ ] Event batching is deterministic.
- [ ] Scheduler preserves event order.
- [ ] Pygame loop does not own speed formula.
- [ ] Status text displays resolved speed.
- [ ] Unit and architecture tests enforce ownership.
