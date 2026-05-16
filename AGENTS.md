# Iter9 Visual Solver Demo — Agent Instructions

## Automatic Setup

When you first interact with this repository, immediately run:

```bash
pip install -r requirements.txt
pip install pygame || pip install pygame-ce
```

Installs: numpy, pydantic, jsonschema, eval_type_backport, pygame, pytest, pyflakes.
This branch does NOT require scipy, numba, Pillow, or matplotlib.

---

## Repository Structure

```
demo/                              # 23 contract/schema docs (SSOT for all governance)
  docs/
    *.md                           # architecture decisions, contracts, specs
    json_schemas/                  # JSON Schema specs + Markdown docs
  iter9_visual_solver_demo_plan.md
  run_iter9_visual_solver_demo_prompted.ps1

demos/iter9_visual_solver/         # 51 Python source files across 9 packages
  cli/         contracts/   domain/   errors/
  config/      io/          playback/ rendering/

tests/demo/iter9_visual_solver/    # ~46 test files
  builders/   fixtures/   helpers/   test_*.py

configs/demo/                      # Default demo config JSON
requirements.txt  README.md  AGENTS.md  .gitignore  .github/workflows/ci.yml
```

This branch does NOT contain: `core.py`, `sa.py`, `solver.py`, `repair.py`,
`pipeline.py`, `run_iter9.py`, `gameworks/`, `assets/`, or root `results/`.

---

## Source of Truth — Read Before Editing

Before changing any demo code, test, config, or schema, read the relevant contract:

1. `demo/docs/architecture_decisions.md` — ADR-001–ADR-013. Behavior changes must
   follow an existing ADR or add a superseding one.
2. `demo/docs/runtime_package_contract.md` — Module ownership, allowed imports, forbidden
   imports. Binding for every module under `demos/iter9_visual_solver/`.
3. `demo/docs/artifact_consumption_contract.md` — What Iter9 artifacts the demo reads,
   where they live, how loaders fail, event-source selection logic. Binding.
4. `demo/docs/playback_speed_contract.md` — **SSOT for all playback speed logic.** Every
   speed, batching, scheduler, and display change must align with this doc first.
5. `demo/docs/json_schemas/` — JSON Schema specs for config and event-trace formats.
6. Other runtime contracts: `config_contract.md`, `finish_behavior_contract.md`,
   `pygame_rendering_contract.md`, `status_panel_contract.md`, `window_sizing_contract.md`.

---

## Development Boundaries

Allowed imports by package (violations caught by `test_architecture_boundaries`):
- `pygame` — only `demos/iter9_visual_solver/rendering/` and pygame test fakes.
- `pydantic` — only `demos/iter9_visual_solver/config/` and config tests.
- `jsonschema` — test/tooling only; not in runtime code.
- `numpy` — `io/`, `domain/`, `playback/` only (not `rendering/` or `config/`).

Forbidden:
- Root-level `demo_config.py`, `demo_visualizer.py`, `visual_solver_demo.py`.
- Speed formula in `pygame_loop.py`, `status_panel.py`, `cli/commands.py`, config
  loading, or artifact loading.
- pygame, file I/O, JSON loading, numpy, or sleeps in `speed_policy.py`,
  `event_batching.py`, or `event_scheduler.py`.
- Artifact path resolution or file loading in `playback/` or `rendering/`.
- Draw calls or pygame calls in the CLI orchestrator.

---

## Playback Speed SSOT

`demo/docs/playback_speed_contract.md` is the **binding source of truth** for all
playback speed work. When implementation conflicts with the contract, fix the
implementation — do not weaken the contract.

**Playback-speed work is TDD-first:** write failing tests for the exact contract rule
before changing runtime code.

Required playback behavior (do not break):
- `calculate_events_per_second()` accepts a validated `PlaybackConfig`, not raw JSON.
- Speed formula: `round(clamp(base + total_mines * multiplier, min, max))`.
- `calculate_events_per_frame()`: `max(1, ceil(eps / fps))` batching on; `1` batching off.
- `EventScheduler`: preserves order, emits partial batches, exposes `finished` / `applied_count` / `total_count`.
- `ReplayState` owns applied event counters and status snapshot values.
- `pygame_loop.py` consumes resolved speed; does not calculate the mine-count formula.
- `status_text.py` displays exactly `Playback speed: <events_per_second> cells/sec`.

---

## Testing & Verification

After any code change:

```bash
# Architecture boundaries — run first, fails fast on import violations
python -m unittest tests.demo.iter9_visual_solver.test_architecture_boundaries

# Full suite
python -m unittest discover -s tests/demo/iter9_visual_solver -p "test_*.py"

# Compile check + lint
python -m compileall -q demos tests/demo
pyflakes demos tests/demo

# CLI smoke
python -m demos.iter9_visual_solver.cli.commands --help
```

Playback speed changes — also run:
```bash
python -m unittest tests.demo.iter9_visual_solver.test_speed_policy
python -m unittest tests.demo.iter9_visual_solver.test_event_batching
python -m unittest tests.demo.iter9_visual_solver.test_event_scheduler
python -m unittest tests.demo.iter9_visual_solver.test_replay_state
python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
python -m unittest tests.demo.iter9_visual_solver.test_status_text
```

Headless pygame (CI / no display):
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy \
  python -m unittest tests.demo.iter9_visual_solver.test_pygame_loop_with_fakes
```

---

## Commit Standards

- Style: `<scope>: <imperative summary>` — e.g. `playback: enforce speed formula contract`
- Cite ADR numbers for behavior changes: `ADR-010: ...`
- Reference `demo/docs/` contract name if behavior changes.
- Always include:
  ```
  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
  ```
