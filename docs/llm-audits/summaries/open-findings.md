# Open Findings Summary
## Last Updated: 2026-05-10 (session 5 — design pattern scaffold applied)

## CRITICAL (0)
All 6 critical findings resolved.

## HIGH (0)
All 9 high findings resolved (including FIND-STATE-HIGH-h008a via asset commit 09e17c1).

## MEDIUM (3 open — deferred / require design decision)

| ID | Title | Reason deferred |
|---|---|---|
| FIND-DOCS-MEDIUM-m005a | frontend_spec/ describes unimplemented React app | Design decision — aspirational spec; pygame is the current implementation |
| FIND-ARCH-MEDIUM-m006a | 30+ SA constants in run_iter9.py | Large refactor, pipeline-only concern, no runtime impact |
| FIND-PERF-MEDIUM-m008a | _save_npy() not atomic; no schema versioning | See below |

**FIND-PERF-MEDIUM-m008a — updated scope (session 5)**

Original finding described a Python loop O(H×W) in `_save_npy`. That specific loop was
resolved in earlier sessions. The remaining gap is broader:

1. **Not atomic** — `np.save(path)` writes directly; corrupt partial file left on crash.
   Design recommendation: `DESIGN_PATTERNS.md § R8` (atomic save via `os.replace`).
   Test scaffold: `gameworks/tests/integration/test_board_modes.py::test_atomic_save_uses_tmp_then_replace` (skipped).

2. **No schema version** — Saved `.npy` files have no version metadata or companion JSON
   sidecar. Format detection relies on value-range heuristics.
   Design recommendation: `DESIGN_PATTERNS.md § R9` (GAME_SAVE_SCHEMA_VERSION + sidecar).
   Test scaffold: `gameworks/tests/unit/test_board_loading.py` (schema section, skipped).

Both sub-items are tracked in `docs/ISSUE-LOG.md § DP-R8` and `§ DP-R9`.

## LOW (0)
All 4 low findings resolved.
