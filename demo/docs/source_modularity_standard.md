# Iter9 Visual Solver Demo — Source Modularity Standard

## Purpose
Define concrete design methods that make files naturally stay small. A 500-line threshold is only a smoke alarm, not the design method.

## Required methods
1. Change-axis decomposition
2. One-abstraction-level-per-file
3. Functional-core / imperative-shell split
4. Policy extraction
5. Port-adapter boundaries
6. Schema-first config contracts
7. Event model separation
8. Renderer/view-model separation
9. Responsibility budgets
10. Public API budgets
11. Growth-trigger split rules
12. Architecture fitness tests

## Change-axis decomposition
Split files by reason they change. Do not create a generic `pygame_renderer.py` that owns window size, colors, status text, playback, draw calls, and finish behavior. Split into `rendering/window_geometry.py`, `rendering/color_palette.py`, `rendering/status_text.py`, `rendering/status_panel.py`, `rendering/board_surface.py`, `rendering/pygame_loop.py`, `playback/finish_policy.py`, and `playback/speed_policy.py`.

## One abstraction level per file
A file must operate at one abstraction level only: CLI orchestration, use-case orchestration, policy/calculation, I/O adapter, rendering adapter, or data model/contract. A file must not mix CLI orchestration, JSON parsing, policy math, and pygame drawing.

## Functional core / imperative shell
Pure files include `speed_policy.py`, `event_batching.py`, `window_geometry.py`, `status_text.py`, and `board_dimensions.py`. Shell files include `grid_loader.py`, `metrics_loader.py`, `pygame_loop.py`, and `commands.py`. Pure files must not open files, create pygame windows, read clocks, or write artifacts.

## Policy extraction
Any configurable rule becomes a policy module. Playback speed, finish behavior, event batching, window geometry, and color palette must not live inside the pygame loop.

## Renderer/view-model separation
Correct flow: metrics JSON → `metrics_loader.py` → `status_snapshot.py` → `status_text.py` → `status_panel.py`. The status panel draws data; it does not parse metrics.

## Responsibility budget
Review a file when it has more than one primary responsibility, three public functions/classes, three imported internal package areas, or one side-effect category.

## Public API budget
Target 1–3 public functions/classes per file. If a file needs 6–10 public functions, split it.

## File size smoke alarm
| Size | Meaning |
|---:|---|
| 0–150 | ideal focused module |
| 150–300 | acceptable single-responsibility module |
| 300–400 | review boundaries |
| 400–500 | requires documented reason |
| 500+ | architecture failure unless generated/data-only/approved exception |

## Split triggers
Split immediately when a new import belongs to another architecture layer; a second config section is consumed; a function needs both pygame objects and domain calculations; a test needs unrelated fixtures; a function name contains “and”; section headers separate unrelated areas; a helper exists only to support a second responsibility; or a new feature edits more than one conceptual section.

## Import boundaries
| Package | Forbidden imports |
|---|---|
| `domain/` | pygame, pydantic, pathlib/file I/O |
| `config/` | pygame |
| `io/` | pygame |
| `playback/` | pygame, file I/O |
| `rendering/` | pydantic, schema validation |
| `cli/` | low-level pixel drawing |
| `contracts/` | runtime imports |

## Required architecture tests
- `test_architecture_boundaries.py`
- `test_source_file_modularity.py`
