# Gameworks — Design Patterns & Pipeline Alignment

This document audits the intentional modularity and agentic design patterns found in the
MineStreaker SA pipeline (`run_iter9.py` and supporting modules) and maps each pattern to
its current presence or absence in `gameworks/`. Where a pattern is absent, a concrete
recommendation is given for how to apply it.

The pipeline is the engineering reference model for this codebase. Gameworks should follow
the same discipline.

---

## Table of Contents

1. [Pipeline Design Philosophy](#pipeline-design-philosophy)
2. [Pattern Inventory](#pattern-inventory)
   - [P1 — Single-Responsibility Module Ownership](#p1--single-responsibility-module-ownership)
   - [P2 — Frozen Config Dataclasses](#p2--frozen-config-dataclasses)
   - [P3 — Rich Result Dataclasses at Stage Boundaries](#p3--rich-result-dataclasses-at-stage-boundaries)
   - [P4 — Pure Functions / No Side Effects in Math Cores](#p4--pure-functions--no-side-effects-in-math-cores)
   - [P5 — Neighbor / Lookup Table Caching](#p5--neighbor--lookup-table-caching)
   - [P6 — Warmup-and-Verify Pattern](#p6--warmup-and-verify-pattern)
   - [P7 — Try/Except Relative-then-Absolute Import](#p7--tryexcept-relative-then-absolute-import)
   - [P8 — Atomic File I/O](#p8--atomic-file-io)
   - [P9 — Versioned Schema Strings](#p9--versioned-schema-strings)
   - [P10 — Iteration-Versioned Function Names](#p10--iteration-versioned-function-names)
   - [P11 — Explicit Deprecation on Legacy Paths](#p11--explicit-deprecation-on-legacy-paths)
   - [P12 — Integrity Verification on Loaded Artifacts](#p12--integrity-verification-on-loaded-artifacts)
3. [Alignment Summary Table](#alignment-summary-table)
4. [Recommended Improvements](#recommended-improvements)
5. [Patterns That Do Not Apply to Gameworks](#patterns-that-do-not-apply-to-gameworks)

---

## Pipeline Design Philosophy

The SA pipeline is built around three principles that recur throughout its source:

**1. Every boundary is a named contract.**
Every module transition produces a typed, documented result object. Nothing flows between
modules as a raw dict or untyped tuple. This makes the data contract inspectable, testable,
and self-documenting.

**2. Mutation is isolated to the outermost orchestration layer.**
Math primitives (`core.py`, `sa.py`) are pure functions. The repair and solver modules
produce results; they do not mutate global state. Side effects (file writes, clock reads)
are pushed to the entry point (`run_iter9.py`) and the artifact writer
(`write_repair_route_artifacts`).

**3. History is preserved, not overwritten.**
When an algorithm improves, the old version is kept under an iteration-versioned name
(`compute_asymmetric_weights` → Iter 2, `compute_zone_aware_weights` → Iter 3, etc.).
Schema strings carry version tags. This lets any automated agent trace which iteration
produced a given artifact.

These three principles together make the codebase auditable and agent-friendly: an
autonomous agent reading the pipeline can discover what every module does, what it produces,
and in which iteration its behaviour changed — without reading the full git history.

---

## Pattern Inventory

### P1 — Single-Responsibility Module Ownership

**Pipeline implementation:**
Each module has one named job, stated in its module docstring or first-block comment:
- `source_config.py` — resolve and validate the source image contract
- `board_sizing.py` — derive board dimensions from image width
- `core.py` — pure weight and board math primitives
- `sa.py` — simulated annealing kernel and runner
- `solver.py` — constraint propagation and cluster resolution
- `repair.py` — staged repair routing
- `pipeline.py` — late-stage failure routing and artifact writes
- `run_iter9.py` — entry point, I/O, orchestration only

**Gameworks status:** PRESENT

The three-module split (`engine.py` / `renderer.py` / `main.py`) correctly isolates logic,
rendering, and orchestration. All three modules now have explicit ownership docstrings
at the top that state what each module owns and what it explicitly does not own.

Notes (not blocking):
- `engine.py` owns *both* board state logic *and* game session state (scoring, streak,
  timer, first-click safety). These are separate concerns and grow in complexity
  independently.
- `main.py` owns CLI parsing, the game loop, board construction, and `.npy` saving — four
  distinct responsibilities.

These are acknowledged design debts tracked separately but do not affect the PRESENT status
of the single-responsibility documentation pattern.

---

### P2 — Frozen Config Dataclasses

**Pipeline implementation:**
All stage inputs are `@dataclass(frozen=True)`. Examples:
```python
# source_config.py
@dataclass(frozen=True)
class SourceImageConfig:
    image_path: str
    board_w: int
    seed: int
    sha256: str
    ...

# pipeline.py
@dataclass(frozen=True)
class RepairRoutingConfig:
    npy_path: str
    image_path: str
    board_w: int
    seed: int
    ...
```
Frozen dataclasses prevent accidental mutation during a pipeline run. They are
self-documenting, hashable, and can be serialized to metrics dicts via a `to_metrics_dict()`
method.

**Gameworks status:** ABSENT for configuration; PARTIAL for cell snapshots.

`CellState` is correctly `frozen=True` (immutable cell snapshot). But `GameEngine` takes
7 flat constructor arguments with no config object:
```python
GameEngine(mode="random", width=16, height=16, mines=0,
           image_path="", npy_path="", seed=42)
```
This means:
- Config cannot be serialized, logged, or compared without reconstructing it from
  individual attributes.
- `restart()` re-uses stored attributes implicitly — there is no single source of truth
  for the game configuration.
- An agent or test harness cannot pass a config object; it must know every keyword
  argument individually.

**Recommendation:** See [R2 in Recommended Improvements](#r2--gameconfig-frozen-dataclass).

---

### P3 — Rich Result Dataclasses at Stage Boundaries

**Pipeline implementation:**
Every stage transition returns a typed result dataclass, never a bare tuple or dict:
```python
# solver.py
@dataclass
class SolveResult:
    board: np.ndarray
    unresolved: List[UnresolvedCluster]
    ...

# repair.py
@dataclass
class Phase1RepairResult:
    board: np.ndarray
    repaired_count: int
    attempts: int
    elapsed: float
    ...

# pipeline.py
@dataclass
class RepairRouteResult:
    route: str
    phase1: Phase1RepairResult
    phase2: ...
    solve: SolveResult
    ...
```

**Gameworks status:** PARTIAL

`MoveResult` is a well-designed result object with `__slots__`. `CellState` is a proper
snapshot type. These follow the pattern correctly.

However, the board loader functions return a raw `Board`:
```python
def load_board_from_npy(path: str) -> Board          # no load metadata
def load_board_from_pipeline(image_path, ...) -> Board  # no pipeline result
```
There is no record of *how* the board was loaded: which format was detected, whether the
pipeline fallback fired, what the detected schema was.

**Gap:** Load functions return naked `Board`; no `BoardLoadResult` equivalent.

**Recommendation:** See [R3 in Recommended Improvements](#r3--boardloadresult-dataclass).

---

### P4 — Pure Functions / No Side Effects in Math Cores

**Pipeline implementation:**
`core.py` contains only pure functions. None of them write files, mutate global state, read
from disk, or hold instance state. `sa.py`'s kernel is `@njit` (inherently pure). The
`summarize_sa_output()` function is a pure summary utility separate from the runner.

**Gameworks status:** PRESENT

`Board` correctly contains no Pygame imports and no I/O. The `place_random_mines()` and
`load_board_from_npy()` module-level functions operate on their inputs and return results.
`CellState` is immutable. The module boundary rule (`engine.py` must NOT import `pygame`)
is enforced by convention.

This pattern is well-applied. The only note is that the module boundary is enforced by
convention/documentation rather than by a test that would fail on a bad import.

---

### P5 — Neighbor / Lookup Table Caching

**Pipeline implementation:**
`solver.py` pre-computes and caches a neighbor lookup table:
```python
_NB_CACHE: Dict[Tuple[int,int], List[Tuple[int,int]]] = {}

def _neighbours(r, c, h, w):
    key = (h, w)
    if key not in _NB_CACHE:
        _NB_CACHE[key] = _build_nb_table(h, w)
    return _NB_CACHE[key][r * w + c]
```
This avoids re-computing the same table for repeated calls on the same board shape.

**Gameworks status:** PARTIAL

`Board.__init__` pre-computes neighbor counts at construction via `scipy.ndimage.convolve`,
which is correct and efficient for a single board instance. However, there is no caching
across board instances of the same shape. Each `restart()` call (which constructs a new
`Board`) re-runs the convolution.

For small boards (9×9, 16×16, 30×16) this is negligible. For the image-pipeline boards
that can reach 300×370+, repeated restarts will re-pay the convolution cost each time.

**Gap:** No cross-instance shape cache for the neighbor convolution kernel.

---

### P6 — Warmup-and-Verify Pattern

**Pipeline implementation:**
`sa.py` compiles and verifies the Numba kernel before any pipeline run:
```python
def compile_sa_kernel() -> None:
    """Compile and verify the SA kernel with a minimal dummy board."""
    dummy = np.zeros((5, 5), dtype=np.int8)
    dummy[2, 2] = 1
    result = _sa_kernel(dummy, ...)
    assert result.shape == dummy.shape, "SA kernel compile verification failed"
```
This fails fast at startup, before any expensive work is done, if the kernel is broken.

**Gameworks status:** ABSENT

There is no equivalent startup check. Pygame initialisation errors, missing font files, and
bad `.npy` paths all surface mid-run rather than at startup.

**Gap:** No `preflight_check()` or equivalent that validates the runtime environment before
`GameLoop.run()` begins.

**Recommendation:** See [R6 in Recommended Improvements](#r6--preflight-check).

---

### P7 — Try/Except Relative-then-Absolute Import

**Pipeline implementation:**
All pipeline modules use the two-step import guard to support both package import and
direct script execution:
```python
try:
    from .core import compute_zone_aware_weights
except ImportError:
    from core import compute_zone_aware_weights
```

**Gameworks status:** PRESENT (partially)

`load_board_from_pipeline()` in `engine.py` wraps the pipeline import in a broad
`try/except ImportError` block that falls back to a random board. This is the correct
pattern for the cross-boundary call.

The gameworks package itself does not need the relative/absolute guard for its own internal
imports because it is always imported as a package (never run as `python engine.py`
directly). So this pattern is appropriately absent internally and correctly present at the
pipeline call site.

---

### P8 — Atomic File I/O

**Pipeline implementation:**
All artifact writes use atomic helpers:
```python
def atomic_save_json(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)   # atomic on POSIX

def atomic_save_npy(path: str, arr: np.ndarray) -> None:
    tmp = path + ".tmp"
    np.save(tmp, arr)
    os.replace(tmp, path)
```
`os.replace()` is atomic on POSIX: a reader will always see either the old complete file
or the new complete file, never a partial write.

**Gameworks status:** ABSENT

`GameLoop._save_npy()` writes directly:
```python
np.save(path, board_array)
```
If the process is interrupted mid-write (crash, Ctrl-C), the `.npy` file is left in a
corrupt partial state with no recovery path.

**Gap:** `_save_npy` is not atomic.

**Recommendation:** See [R8 in Recommended Improvements](#r8--atomic-npy-save).

---

### P9 — Versioned Schema Strings

**Pipeline implementation:**
`run_iter9.py` defines a top-level schema version constant:
```python
SCHEMA_VERSION = "metrics.v2.source_image_runtime_contract"
```
This string is embedded in every output JSON artifact. Any downstream consumer (agent,
analysis script, CI check) can assert the schema version before parsing fields, and can
detect when a saved artifact was produced by an older pipeline version.

**Gameworks status:** ABSENT

The `.npy` game-save format has no embedded version string. The auto-detection logic in
`load_board_from_npy` distinguishes pipeline format (0/1) from game-save format (-1/0–8)
by dtype and value range heuristics. If the game-save format changes in a future version,
there is no version field to gate on.

**Gap:** No `GAME_SAVE_SCHEMA_VERSION` constant; `.npy` saves contain no version metadata.

**Recommendation:** See [R9 in Recommended Improvements](#r9--game-save-schema-version).

---

### P10 — Iteration-Versioned Function Names

**Pipeline implementation:**
When an algorithm is improved, the old version is preserved under an iteration-suffixed
name and the new version is added alongside it:
```python
# core.py — all four versions coexist
def compute_asymmetric_weights(...)    # Iter 2: original asymmetric weighting
def compute_zone_aware_weights(...)    # Iter 3: zone-aware extension
def compute_cluster_break_weights(...) # Iter 4: cluster-break heuristic
def compute_sealing_prevention_weights(...) # Iter 5: sealing-prevention layer
```
The active pipeline calls the latest; the older versions remain callable for regression
testing and reproducibility.

**Gameworks status:** NOT APPLICABLE at current scale

`gameworks/` is at v0.1.1 and has not yet iterated its algorithms. The scoring constants
(`REVEAL_POINTS`, `STREAK_TIERS`) and the flood-fill implementation have not been versioned
because they have not yet changed.

When scoring or board-generation algorithms are revised in future versions, this pattern
should be followed: preserve the prior version as `_v1`, introduce the new as the canonical
name, and add a regression test that compares both.

---

### P11 — Explicit Deprecation on Legacy Paths

**Pipeline implementation:**
`pipeline.py` uses `warnings.warn` with `DeprecationWarning` on the old entry point:
```python
def run_board(image_path, board_w, seed):
    warnings.warn(
        "run_board() is deprecated. Use route_late_stage_failure() directly.",
        DeprecationWarning,
        stacklevel=2,
    )
    ...
```

**Gameworks status:** ABSENT

There are no deprecated APIs in gameworks yet. When `GameEngine` or `Board` APIs are
changed in future versions, this pattern should be applied: keep the old signature,
add `DeprecationWarning`, and call the new implementation internally for one release
cycle before removing.

---

### P12 — Integrity Verification on Loaded Artifacts

**Pipeline implementation:**
`source_config.py` computes SHA256 of the source image at config-resolution time and
embeds it in `SourceImageConfig`:
```python
sha256: str = field(default="")

def resolve_source_image_config(image_path, board_w, seed) -> SourceImageConfig:
    ...
    sha = hashlib.sha256(Path(image_path).read_bytes()).hexdigest()
    return SourceImageConfig(..., sha256=sha)
```
This ensures that any downstream agent can verify the artifact was produced from the exact
image it expects.

**Gameworks status:** ABSENT

`load_board_from_npy` performs format auto-detection and a neighbour-count consistency
check, but:
- There is no CRC or checksum on the `.npy` payload.
- There is no record of which image or seed produced a given board file.
- A silently truncated `.npy` (partial write) will pass the format detection check until
  the neighbour-count assertion fires — and that only catches game-save format, not
  pipeline format.

**Gap:** No file integrity check at load time; no provenance metadata in saved boards.

---

## Alignment Summary Table

| Pattern | Pipeline | Gameworks | Gap Severity |
|---|---|---|---|
| P1 — Single-responsibility modules | Full | Present | None |
| P2 — Frozen config dataclasses | Full | Absent | Medium |
| P3 — Rich result dataclasses | Full | Partial | Low |
| P4 — Pure functions / no side effects | Full | Present | None |
| P5 — Lookup table caching | Full | Partial | Low |
| P6 — Warmup-and-verify | Full | Absent | Medium |
| P7 — Try/except import guard | Full | Present | None |
| P8 — Atomic file I/O | Full | Absent | Medium |
| P9 — Versioned schema strings | Full | Absent | Medium |
| P10 — Iteration-versioned functions | Full | N/A (v0.1.1) | Deferred |
| P11 — Explicit deprecation | Full | Absent | Low (no legacy APIs yet) |
| P12 — Integrity verification | Full | Absent | Low |

---

## Recommended Improvements

These recommendations are ordered by impact. Each is self-contained and can be implemented
independently.

---

### R2 — GameConfig Frozen Dataclass

Replace the 7 flat constructor arguments on `GameEngine` with a `GameConfig` frozen
dataclass:

```python
# engine.py

@dataclass(frozen=True)
class GameConfig:
    mode:       str = "random"
    width:      int = 16
    height:     int = 16
    mines:      int = 0          # 0 = auto
    image_path: str = ""
    npy_path:   str = ""
    seed:       int = 42

    def to_metrics_dict(self) -> dict:
        return {
            "mode":       self.mode,
            "width":      self.width,
            "height":     self.height,
            "mines":      self.mines,
            "image_path": self.image_path,
            "npy_path":   self.npy_path,
            "seed":       self.seed,
        }
```

`GameEngine.__init__` accepts a single `config: GameConfig`. `restart()` replaces
`self._config` with a new frozen instance (incrementing seed), keeping one source of truth.
`from_difficulty()` returns `GameEngine(GameConfig(...))`.

Benefits:
- Any agent or test can construct, inspect, log, or compare a full game configuration as a
  single object.
- `restart()` has an explicit config transition rather than mutating individual attributes.
- `to_metrics_dict()` enables structured logging of session starts.

---

### R3 — BoardLoadResult Dataclass

Wrap board loader return values in a result object:

```python
# engine.py

@dataclass
class BoardLoadResult:
    board:          Board
    format_detected: str          # "pipeline" | "game-save" | "random-fallback"
    source_path:    str           # empty for random
    warnings:       List[str]     # non-fatal issues detected during load
```

`load_board_from_npy` and `load_board_from_pipeline` return `BoardLoadResult` instead of
a naked `Board`. `GameEngine._build_board()` stores the result and exposes
`self.load_result: BoardLoadResult` as a readable attribute.

Benefits:
- The renderer or a debug overlay can display which format was loaded.
- The pipeline fallback in `load_board_from_pipeline` is observable (currently silent).
- Tests can assert on `format_detected` rather than inspecting board values.

---

### R6 — Preflight Check

Add a `preflight_check()` function in `main.py` called before `GameLoop.run()`:

```python
# main.py

def preflight_check(args: argparse.Namespace) -> List[str]:
    """
    Validate the runtime environment before starting the game loop.
    Returns a list of fatal error messages. Empty list = OK to start.
    """
    errors = []

    if args.npy and not Path(args.npy).exists():
        errors.append(f"--load path not found: {args.npy}")

    if args.image and not Path(args.image).exists():
        errors.append(f"--image path not found: {args.image}")

    try:
        import pygame
    except ImportError:
        errors.append("pygame is not installed. Run: pip install pygame")

    return errors
```

`main()` calls `preflight_check(args)` and prints each error + exits before `GameLoop` is
constructed, giving a clean error message instead of a mid-loop traceback.

Extend with font and display checks as the project matures.

---

### R8 — Atomic .npy Save

Replace the direct `np.save` in `GameLoop._save_npy()` with the atomic pattern from the
pipeline:

```python
# main.py

def _save_npy(self) -> None:
    board_array = self.engine.board._mines.astype(np.int8)
    ts = int(time.time())
    final_path = f"board_{ts}.npy"
    tmp_path   = final_path + ".tmp"
    try:
        np.save(tmp_path, board_array)
        os.replace(tmp_path, final_path)
        print(f"Saved: {final_path}")
    except Exception as e:
        Path(tmp_path).unlink(missing_ok=True)
        print(f"Save failed: {e}")
```

`os.replace` is atomic on POSIX (Linux, macOS). The `.tmp` cleanup in the `except` block
ensures no orphaned partial files are left on disk.

---

### R9 — Game-Save Schema Version

Add a schema version to the game-save `.npy` format and to the load/save functions:

```python
# engine.py

GAME_SAVE_SCHEMA_VERSION: str = "gameworks.board.v1"
```

For the save side, embed a companion JSON sidecar (same base name, `.json` extension)
alongside the `.npy`:

```json
{
  "schema": "gameworks.board.v1",
  "width": 30,
  "height": 16,
  "mines": 99,
  "seed": 42,
  "saved_at": 1715385600
}
```

`load_board_from_npy` reads the sidecar if present, checks the `schema` field, and
populates the `BoardLoadResult.warnings` list if the schema is absent or mismatched.

This is a non-breaking addition: existing `.npy` files without a sidecar load as before,
with a warning rather than an error.

---

## Patterns That Do Not Apply to Gameworks

The following pipeline patterns exist for reasons specific to the SA pipeline and have no
equivalent in a real-time game loop:

| Pattern | Why it does not apply |
|---|---|
| `@njit` Numba kernel | Gameworks has no compute-intensive tight loops that benefit from JIT compilation. Board operations are O(cells) Python with NumPy/scipy, which is fast enough. |
| `ThreadPoolExecutor` parallel repair candidates | Repair evaluation explores multiple candidate solutions in parallel. Gameworks has no equivalent multi-candidate evaluation path. |
| SHA256 image integrity | The source image in gameworks is user-supplied at launch and consumed immediately; it is not stored and re-verified later. |
| `compile_sa_kernel()` Numba warmup | Specific to JIT compilation; no equivalent compilation step exists in gameworks. |
| `IMAGE_SWEEP_SUMMARY_FIELDS` contract dict | Used to validate the schema of sweep-run summary CSVs. Gameworks does not produce sweep artifacts. |

---

*Gameworks v0.1.1 — Pipeline Alignment Audit*
