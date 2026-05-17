# Testing Strategy

## Last Updated: 2026-05-13

This document describes the project-wide testing strategy for MineStreaker: what is
tested, where tests live, how to run them, and what is intentionally not covered by
automated tests.

For gameworks-specific test coverage and hardening plans, see:
- `gameworks/docs/TEST_GAP_ANALYSIS.md`
- `gameworks/docs/TEST_HARDENING_PLAN.md`

---

## Test Suite Map

The project has two primary test domains, each with its own location and runner:

```
tests/                          Pipeline contract tests + gameworks legacy guards
gameworks/tests/                Gameworks package tests (unit, integration, renderer, CLI, architecture)
```

### `tests/` — Pipeline Contract Tests and Legacy Guards

These tests verify the public contracts of the pipeline: JSON output schemas, CLI
argument behavior, route state invariants, and solver taxonomy. They also include
two legacy regression guards for gameworks that predate the `gameworks/tests/` suite.

| File | What it tests |
|---|---|
| `test_source_image_cli_contract.py` | CLI argument parsing and source image validation |
| `test_benchmark_layout.py` | Benchmark output directory structure and field layout |
| `test_report_explanations.py` | Explained report label wording and layout contract |
| `test_repair_route_decision.py` | Route decision JSON schema and 4-field model |
| `test_route_artifact_metadata.py` | Route artifact metadata fields |
| `test_solver_failure_taxonomy.py` | Failure taxonomy JSON schema |
| `test_repair_result_dataclasses.py` | Repair result dataclass field contracts |
| `test_repair_visual_delta.py` | Visual delta summary JSON contract |
| `test_iter9_image_sweep_contract.py` | Image-sweep summary field contract |
| `test_image_guard_contract.py` | Image guard integrity contract |
| `test_source_config.py` | Source config resolution and validation |
| `test_gameworks_engine.py` | Legacy regression guard — gameworks engine (root `tests/`, NOT `gameworks/tests/`) |
| `test_gameworks_renderer_headless.py` | Legacy regression guard — renderer headless (root `tests/`, NOT `gameworks/tests/`) |

**Runner:**
```bash
python -m unittest discover -s tests -p "test_*.py"
```

Or with pytest:
```bash
pytest tests/ -v
```

---

### `gameworks/tests/` — Gameworks Package Tests

The full package-local test suite for the interactive game. Organized by category:

| Directory | What it tests |
|---|---|
| `gameworks/tests/unit/` | Board logic, engine state, config (some tests skipped pending R2/R3 implementation) |
| `gameworks/tests/integration/` | Full game loop integration, board mode loading |
| `gameworks/tests/renderer/` | Renderer headless rendering (requires SDL dummy driver) |
| `gameworks/tests/cli/` | CLI argument parsing, preflight behavior |
| `gameworks/tests/architecture/` | Import boundary enforcement (no `pygame` in `engine.py`, etc.) |

**Runner (headless — required for renderer tests):**
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
```

**By category:**
```bash
# Unit, integration, CLI, architecture (no display needed)
pytest gameworks/tests/unit/ gameworks/tests/architecture/ gameworks/tests/cli/ gameworks/tests/integration/ -v

# Renderer tests only (requires SDL dummy driver)
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/ -v
```

---

## What Each Category Tests

### Pipeline contract tests (`tests/`)

- **JSON schema conformance:** Every output JSON artifact (`metrics_iter9_*.json`,
  `repair_route_decision.json`, etc.) must match its schema doc in `docs/json_schema/`.
- **Route state invariants:** The 4-field route-state model must satisfy accepted-move-count
  rules per `docs/ROUTE_STATE_FIELD_INVARIANTS.md`.
- **CLI contract:** Argument parsing behaves as documented. Source image validation fires
  after argument parsing, not at import time.
- **Explained report contract:** Label wording, figsize, and layout match
  `docs/explained_report_artifact_contract.md`.
- **Image-sweep contract:** Sweep summary fields match `IMAGE_SWEEP_SUMMARY_FIELDS`.

### Gameworks tests (`gameworks/tests/`)

- **Architecture boundary:** `engine.py` must not import `pygame`. Enforced by
  `gameworks/tests/architecture/` — this test fails immediately on a bad import.
- **Engine logic:** Board state transitions, scoring, streak calculation, first-click safety.
- **Renderer headless:** All rendering paths execute without crashing under `SDL_VIDEODRIVER=dummy`.
- **CLI:** `--random`, `--npy`, `--image`, `--easy`, `--medium`, `--hard` flags parse correctly.
- **Integration:** Board construction and full game-loop steps for all three board modes.

---

## Headless Test Requirement

Renderer tests and some integration tests open a Pygame window. In headless environments
(CI, remote, no display), set the SDL dummy driver:

```bash
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
```

Or prefix individual runs:
```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/ -v
```

Without this, renderer tests will either fail or hang waiting for a display.

---

## What Is NOT Tested (and Why)

| Untested Area | Reason |
|---|---|
| SA convergence quality | SA is stochastic; convergence depends on random seed and image. Outcome quality is evaluated manually via benchmark runs (`run_benchmark.py`), not by pytest assertions. |
| Full end-to-end pipeline run | A full `run_iter9.py` invocation takes minutes (SA + Numba warmup). End-to-end coverage is provided by `run_benchmark.py --regression-only`, not pytest. |
| Visual report pixel correctness | Reports are visual artifacts. Layout contract is tested (figsize, labels, wording) but not pixel-level rendering fidelity. |
| Demo playback frame accuracy | Frame timing depends on real-time clock; tested via speed policy contract, not frame-by-frame pixel comparison. |

---

## Adding a New Pipeline Test

1. **Location:** `tests/test_<contract_name>.py`
2. **Pattern:** Use `unittest.TestCase`. Import the relevant module; call the function; assert on the returned dataclass or JSON structure.
3. **No end-to-end runs:** Do not invoke `run_iter9.py` as a subprocess in a pytest test. Test individual module functions instead.
4. **Fixtures:** Small test fixtures (tiny `.npy` boards, minimal JSON dicts) go inline or in a `tests/fixtures/` subdirectory if reused across multiple test files.
5. **Schema assertions:** For JSON output contracts, load a sample artifact and assert required keys and value types. Do not assert on specific numeric values — assert on structure and type.

**Example skeleton:**
```python
import unittest
from repair import Phase1RepairResult

class TestPhase1RepairResultContract(unittest.TestCase):
    def test_required_fields_present(self):
        result = Phase1RepairResult(
            board=None, repaired_count=2, attempts=5, elapsed=0.1
        )
        self.assertIsNotNone(result.repaired_count)
        self.assertIsInstance(result.elapsed, float)
```

---

## CI/CD Status

No CI is configured as of 2026-05-13. The current quality gate is:

```bash
# Must pass before any merge:
python -m unittest discover -s tests -p "test_*.py"
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v
pyflakes gameworks/ gameworks/tests/
```

See `CONTRIBUTING.md` for the full pre-merge checklist.
