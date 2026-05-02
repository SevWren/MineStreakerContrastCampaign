# Iter9 Visual Solver Demo — Finish Behavior Contract

## Document Control

| Field | Value |
|---|---|
| Document status | Accepted baseline |
| Owner | Demo playback/runtime architecture |
| Applies to | `demos/iter9_visual_solver/playback/finish_policy.py`, `rendering/pygame_loop.py`, config schema/docs |
| Required before | finish policy implementation, pygame loop completion behavior, acceptance testing |
| Traceability IDs | DEMO-REQ-003, DEMO-REQ-004, DEMO-REQ-005, DEMO-TEST-016, DEMO-TEST-021 |
| Change rule | Any finish behavior change must update this file, config contract, config schema docs, pygame rendering contract, acceptance criteria, tests, and traceability matrix. |

---

## 1. Purpose

This contract defines what the GUI does after playback finishes.

The MVP must start automatically and stop playback automatically, but the GUI must have the option to remain open after playback completes. The default behavior must not auto-close.

---

## 2. Scope

This contract applies to:

```text
demos/iter9_visual_solver/playback/finish_policy.py
demos/iter9_visual_solver/rendering/pygame_loop.py
demos/iter9_visual_solver/domain/status_snapshot.py
demos/iter9_visual_solver/rendering/status_text.py
demos/iter9_visual_solver/config/models.py
demo/docs/json_schemas/iter9_visual_solver_demo_config.schema.json
tests/demo/iter9_visual_solver/test_finish_policy.py
tests/demo/iter9_visual_solver/test_pygame_loop_with_fakes.py
tests/demo/iter9_visual_solver/test_status_text.py
```

This contract does not own event scheduling, playback speed calculation, window geometry, artifact loading, or config file parsing.

---

## 3. Required Finish Modes

The config must support these modes:

| Mode | Meaning |
|---|---|
| `stay_open` | After playback finishes, keep the GUI window open until the user closes it. |
| `close_immediately` | Close the GUI as soon as playback finishes. |
| `close_after_delay` | Keep the GUI open for `close_after_seconds`, then close automatically. |

Default mode:

```text
stay_open
```

---

## 4. Config Fields

| JSON Path | Type | Required | Default | Owner |
|---|---:|---:|---|---|
| `$.window.finish_behavior.mode` | enum string | yes | `stay_open` | `finish_policy.py` |
| `$.window.finish_behavior.close_after_seconds` | number or null | yes | `null` | `finish_policy.py` |

Validation rules:

| Mode | `close_after_seconds` Rule |
|---|---|
| `stay_open` | must be null or ignored; recommended null |
| `close_immediately` | must be null or `0`; recommended null |
| `close_after_delay` | must be number `>= 0` |

MVP strict validation:

```text
close_after_delay requires close_after_seconds to be a number >= 0.
stay_open allows close_after_seconds to be null.
close_immediately allows close_after_seconds to be null or 0.
```

---

## 5. Ownership

## 5.1 Owner modules

| Responsibility | Owner Module |
|---|---|
| Decide whether auto-close should happen | `playback/finish_policy.py` |
| Track elapsed time after playback completion | `rendering/pygame_loop.py` |
| Apply OS/window close event | `rendering/pygame_loop.py` |
| Display finish state | `rendering/status_text.py` |
| Validate finish config fields | `config/models.py` |

## 5.2 Explicit non-owner modules

| Module | Must Not Own |
|---|---|
| `speed_policy.py` | finish behavior |
| `event_scheduler.py` | window close decision |
| `status_panel.py` | finish decision |
| `pygame_adapter.py` | finish policy |
| `cli/commands.py` | finish policy |
| `run_iter9.py` | finish policy |

---

## 6. Required Public API

## 6.1 `playback/finish_policy.py`

Required API:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class FinishDecision:
    should_close: bool
    finish_state: str
    message: str

def evaluate_finish_behavior(
    *,
    mode: str,
    close_after_seconds: float | None,
    playback_finished: bool,
    elapsed_after_finish_s: float,
) -> FinishDecision: ...
```

Allowed simpler API:

```python
def should_auto_close(
    finish_config: FinishBehaviorConfig,
    *,
    playback_finished: bool,
    elapsed_after_finish_s: float,
) -> bool: ...
```

If the simpler API is used, status text still needs access to finish state/message from replay or loop state.

---

## 7. Required Behavior Matrix

| playback_finished | mode | elapsed_after_finish_s | close_after_seconds | should_close | finish_state |
|---|---|---:|---:|---:|---|
| false | any | any | any | false | `running` |
| true | `stay_open` | any | null/any | false | `complete_staying_open` |
| true | `close_immediately` | any | null/0 | true | `complete_closing` |
| true | `close_after_delay` | `< delay` | delay | false | `complete_waiting_to_close` |
| true | `close_after_delay` | `>= delay` | delay | true | `complete_closing` |

---

## 8. Pygame Loop Contract

The pygame loop MUST:

1. Detect playback completion from scheduler/replay state.
2. Record finish timestamp once.
3. Continue polling OS/window events after playback completion while window remains open.
4. Keep rendering the final board while waiting.
5. Update status text after completion.
6. Close only when finish policy says to close or user closes the window.
7. Return structured result explaining why the loop exited.

The pygame loop MUST NOT:

```text
hardcode auto-close
ignore stay_open
stop polling close events while staying open
sleep for close_after_seconds without polling events
calculate finish behavior inside status_panel.py
```

---

## 9. Structured Result

The pygame loop should return:

```python
@dataclass(frozen=True)
class DemoRunResult:
    exit_reason: str
    playback_finished: bool
    frames_rendered: int
    events_applied: int
    elapsed_time_s: float
```

Allowed exit reasons:

```text
user_closed_window
playback_finished_close_immediately
playback_finished_close_after_delay
max_frames_test_limit
error
```

---

## 10. Status Text Contract

After completion, status text must show one of:

```text
Finish: complete - staying open
Finish: complete - closing
Finish: complete - closing in <seconds>s
```

During playback:

```text
Finish: running
```

Forbidden:

```text
Finish: <finish>
Finish: done maybe closing
```

---

## 11. Error Behavior

| Invalid Condition | Required Behavior |
|---|---|
| unknown finish mode | config validation error before playback |
| `close_after_delay` with null delay | config validation error |
| negative close delay | config validation error |
| non-numeric close delay | config validation error |
| elapsed after finish < 0 | finish policy defensive error |
| playback not finished | never auto-close |

---

## 12. Forbidden Implementation Patterns

Forbidden in `finish_policy.py`:

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
time.sleep(close_after_seconds)
hardcoded close at playback finish
while True without event polling
```

Forbidden default config behavior:

```text
mode = close_immediately
mode = close_after_delay
```

---

## 13. Required Tests

## 13.1 `test_finish_policy.py`

- [ ] playback not finished never closes.
- [ ] `stay_open` never auto-closes.
- [ ] `close_immediately` closes when playback finishes.
- [ ] `close_after_delay` does not close before delay.
- [ ] `close_after_delay` closes at delay.
- [ ] zero-second delay closes immediately after finish.
- [ ] negative elapsed time is rejected defensively.
- [ ] invalid mode is rejected or impossible through config validation.

## 13.2 `test_config_models.py`

- [ ] default finish mode is `stay_open`.
- [ ] `close_after_delay` requires numeric delay.
- [ ] negative delay is rejected.
- [ ] invalid mode is rejected.

## 13.3 `test_pygame_loop_with_fakes.py`

- [ ] loop keeps final board open for `stay_open` until fake quit or max frame limit.
- [ ] loop closes immediately for `close_immediately`.
- [ ] loop waits for delay while still polling events.
- [ ] user close event overrides waiting state.
- [ ] loop returns correct exit reason.

## 13.4 `test_status_text.py`

- [ ] running finish status line.
- [ ] staying-open finish status line.
- [ ] closing-after-delay finish status line.
- [ ] no placeholders.

---

## 14. Acceptance Evidence

Required commands:

```powershell
python -m unittest tests.demo.iter9_visual_solver.test_finish_policy
python -m unittest tests.demo.iter9_visual_solver.test_config_models
python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
python -m unittest tests.demo.iter9_visual_solver.test_status_text
python -m unittest discover -s tests -p "test_*.py"
```

Manual evidence:

- [ ] default config leaves GUI open after playback.
- [ ] `close_immediately` closes after playback.
- [ ] `close_after_delay` closes after configured delay.
- [ ] OS close button works in all finish modes.

---

## 15. Completion Checklist

- [ ] Finish config fields exist.
- [ ] Default finish mode is `stay_open`.
- [ ] Finish policy is pure and pygame-free.
- [ ] Pygame loop honors finish policy.
- [ ] Pygame loop remains responsive after playback completes.
- [ ] Status text reports finish state.
- [ ] Unit tests cover every mode.
- [ ] Manual GUI acceptance covers default stay-open behavior.
