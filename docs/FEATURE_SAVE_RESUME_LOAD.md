# Feature Implementation Checklist — Save / Resume / Load

**Feature**: Mid-game save, quit-and-resume, and explicit load of a saved session
**Target directory**: `gameworks/`
**Affected files**: `engine.py`, `renderer.py`, `main.py`, `tests/unit/`, `tests/integration/`, `tests/renderer/`
**Depends on**: No external libraries beyond numpy (already imported everywhere)

---

## Branch Strategy

This feature must be developed on its own dedicated branch, isolated from `frontend-game-mockup` and `main`.

### Branch name

```
feature/save-resume-load
```

### Setup

```bash
# Ensure local repo is up to date
git checkout frontend-game-mockup
git pull origin frontend-game-mockup

# Cut the feature branch from frontend-game-mockup (not main)
git checkout -b feature/save-resume-load

# Push and set upstream immediately
git push -u origin feature/save-resume-load
```

### Branch rules

- **Base branch**: `frontend-game-mockup` — the feature builds on the current game, not on `main`
- **Never commit directly to `frontend-game-mockup` or `main`** while this feature is in development
- **One logical commit per phase** — do not squash all phases into a single commit; keep the history readable
- **Commit message format**:

  | Phase | Prefix | Example |
  |---|---|---|
  | engine.py additions | `feat(engine):` | `feat(engine): add save_game_state / load_game_state + Board.from_arrays` |
  | renderer.py additions | `feat(renderer):` | `feat(renderer): add Save & Quit button and toast overlay` |
  | main.py wiring | `feat(main):` | `feat(main): wire --resume CLI flag and _save_state dispatcher` |
  | Tests | `test:` | `test: add save/resume/load unit, renderer, and integration tests` |
  | Docs | `docs:` | `docs: update CHANGELOG and API_REFERENCE for save/resume/load` |

### Merge strategy

- Open a PR from `feature/save-resume-load` → `frontend-game-mockup`
- All tests must be green before merge: `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v`
- Merge via **squash** or **rebase** — no merge commits on `frontend-game-mockup`

---

## Background & Constraints

### What exists today

| Existing item | What it does | What it does NOT do |
|---|---|---|
| `_save_npy()` in `main.py` | Writes mine layout as `int8` array to `.npy` | Saves no player state (flags, score, timer, revealed) |
| `--load <path>` CLI flag | Loads mine layout from `.npy`, starts a fresh game | Does not restore revealed/flagged/score/timer |
| `"save"` action string | Renderer returns it on Save .npy button click | Wired only to `_save_npy()` |
| `GameEngine._paused_elapsed` | Stores frozen elapsed on `stop_timer()` | Not serialised anywhere |
| `Board._flagged`, `_revealed`, `_questioned` | Full game state arrays | Not serialised anywhere |

### Invariants that must not break

- `engine.py` must never import `pygame`, `renderer`, or `main`
- `renderer.py` must never import `main` or mutate engine/board state
- `handle_event()` returns action strings only — all I/O happens in `main.py`
- `Board.__slots__` is defined — no dynamic attribute assignment allowed
- `_n_flags`, `_n_questioned`, `_n_safe_revealed`, `_n_revealed`, `_n_correct_flags` are dirty-int counters that must be recomputed from arrays on load (not stored) to stay consistent
- `GameEngine.elapsed` is a computed `@property` — at save time it must be read once and frozen into `_paused_elapsed`

---

## Phase 0 — Pre-Implementation

- [ ] **Confirm layer ownership for every new symbol**

  | Symbol | File | Reason |
  |---|---|---|
  | `SAVE_SCHEMA_VERSION` | `engine.py` | Pure constant, no pygame |
  | `SaveResult` dataclass | `engine.py` | Produced by engine-layer function |
  | `LoadResult` dataclass | `engine.py` | Consumed by `main.py` dispatcher |
  | `Board.from_arrays()` classmethod | `engine.py` | Board construction is engine concern |
  | `save_game_state()` function | `engine.py` | Pure serialisation, no pygame |
  | `load_game_state()` function | `engine.py` | Pure deserialisation, no pygame |
  | `Renderer._btn_save_state` rect | `renderer.py` | Button geometry is renderer concern |
  | `Renderer._save_toast` state | `renderer.py` | Toast display is renderer concern |
  | `"save_state"` action string | `renderer.py` → `main.py` | Renderer emits; main dispatches |
  | `GameLoop._save_state()` | `main.py` | File I/O is main concern |
  | `GameLoop._start_game(resumed: bool)` | `main.py` | Resume is a parameter of `_start_game`, not a separate method — no `_resume_game()` exists or will be created |
  | `--resume` CLI flag | `main.py` | CLI is main concern |

- [ ] **Confirm `--resume` is mutually exclusive with `--image`, `--load`, `--random`**
  `build_parser()` uses `mode = p.add_mutually_exclusive_group()`. `--resume` must be added to this same group.

- [ ] **Confirm `.mscsave` extension does not collide with `.npy`**
  The existing `--load` flag accepts `.npy` files. `--resume` must only accept `.mscsave` files. The two flags are in the same `mutually_exclusive_group` so they cannot coexist — no runtime guard needed beyond argparse.

- [ ] **Read `Board.__slots__`** — confirm all arrays needed for save are present:
  `_mine`, `_revealed`, `_flagged`, `_questioned`, `_neighbours`, `_state`, `_n_flags`,
  `_n_questioned`, `_n_safe_revealed`, `_n_revealed`, `_n_correct_flags`
  Note: `_neighbours` is derived from `_mine` via convolution — it does NOT need to be saved. It must be recomputed on load via the existing `Board.__init__` convolution path.
  Note: `Board.from_arrays()` assigns `board._revealed`, `board._flagged`, `board._questioned`, `board._state` after `__init__`. Explicitly confirm each of these four names appears in `Board.__slots__` before writing any code — if any is absent, the assignment raises `AttributeError` at runtime.

- [ ] **Confirm `GameEngine` does NOT use `__slots__`**
  `GameEngine.__new__(GameEngine)` + manual attribute assignment (Step 5) is only valid if `GameEngine` has no `__slots__` definition. Open `engine.py`, search for `__slots__` inside the `GameEngine` class body. Confirm it is absent. If it is ever added in the future, `load_game_state` will raise `AttributeError` on every attribute set — this must be called out in a comment inside `load_game_state`.

- [ ] **Confirm `GameEngine` attributes needed for full restore**:
  `score`, `streak`, `seed`, `mode`, `image_path`, `npy_path`, `_paused_elapsed`, `_first_click`, `mine_flash`
  Note: `mine_flash` maps `(x,y) → expiry time`. Expiry times are wall-clock absolute — they are meaningless after quit. `mine_flash` must be restored as `{}` (empty dict) on resume.
  Note: `_first_click` must be restored as `False` on resume — the first click already happened in the original session.

---

## Phase 1 — Design

### 1a. Save file format

**Format**: `numpy .npz` (zip archive of named arrays). Single file, no external dependencies.
**Extension**: `.mscsave` — distinguishes full saves from `.npy` board definitions.
**Filename pattern**: `save_<YYYYMMDD_HHMMSS>_<W>x<H>.mscsave`
**Location**: Current working directory (same as existing `.npy` export).

**Contents of the `.npz` archive**:

| Array key | dtype | shape | Content |
|---|---|---|---|
| `mine` | `bool` | `(H, W)` | Mine positions |
| `revealed` | `bool` | `(H, W)` | Revealed cells |
| `flagged` | `bool` | `(H, W)` | Flagged cells |
| `questioned` | `bool` | `(H, W)` | Question-marked cells |
| `meta` | `object` (0-d) | scalar | JSON-encoded bytes — all scalars |

**`meta` JSON fields**:

```json
{
  "schema":          "gameworks.save.v1",
  "score":           12345,
  "streak":          7,
  "elapsed":         93.4,
  "board_state":     "playing",
  "width":           300,
  "height":          402,
  "seed":            42,
  "mode":            "random",
  "image_path":      "",
  "npy_path":        ""
}
```

**Why `meta` as JSON bytes in a 0-d object array**: `np.savez` coerces Python strings to numpy `str_` arrays with fixed character widths, which corrupts file paths with special characters. Storing JSON as raw `bytes` in a 0-d `object` array avoids all dtype coercion.

### 1b. Schema version constant

```python
# engine.py — top-level constant, UPPER_SNAKE_CASE
SAVE_SCHEMA_VERSION: str = "gameworks.save.v1"
```

Schema must be checked on load before any array access. Mismatch → `LoadResult(success=False)`.

### 1c. New dataclasses

Add to `engine.py` alongside `CellState` and `MoveResult`:

```python
@dataclass(frozen=True)
class SaveResult:
    success: bool
    path: str = ""
    error: str = ""

@dataclass(frozen=True)
class LoadResult:
    success: bool
    engine: Optional["GameEngine"] = None
    elapsed_offset: float = 0.0
    error: str = ""
```

`LoadResult.elapsed_offset` carries the saved elapsed seconds. `main.py` injects it into `engine._paused_elapsed` after construction — engine.py itself never sets `_paused_elapsed` during load because doing so inside `load_game_state()` would require `GameEngine.__init__` bypass which belongs in engine.py but should be explicit.

### 1d. `Board.from_arrays()` classmethod

`Board.__init__` calls `place_random_mines` indirectly (it does not — it takes a `mine_positions: Set` argument). However, `Board.__init__` expects a `Set[Tuple[int,int]]` of mine positions and re-runs the scipy convolution to build `_neighbours`. This convolution is correct and must run on load.

The cleanest approach: add `Board.from_arrays()` that accepts pre-built bool arrays, extracts mine positions as a set, calls `Board.__init__` normally (which re-runs convolution), then overwrites `_revealed`, `_flagged`, `_questioned` and recomputes dirty-int counters.

```python
@classmethod
def from_arrays(
    cls,
    mine: np.ndarray,       # bool (H, W)
    revealed: np.ndarray,   # bool (H, W)
    flagged: np.ndarray,    # bool (H, W)
    questioned: np.ndarray, # bool (H, W)
    state: str,             # "playing" | "won" | "lost"
) -> "Board":
```

**Counter recomputation logic** (must be exact — these drive win condition and HUD):

```python
board._n_revealed      = int(revealed.sum())
board._n_safe_revealed = int((revealed & ~mine).sum())
board._n_flags         = int(flagged.sum())
board._n_questioned    = int(questioned.sum())
board._n_correct_flags = int((flagged & mine).sum())
```

### 1e. `GameLoop` state machine — no new states

Save is a **side-effect within `PLAYING`**, not a state transition. The sequence is:

```
PLAYING  ──[player clicks "Save & Quit"]──▶  _save_state() writes file
                                              │
                                              └──▶  running = False  (quit game loop)

[launch with --resume <path>]  ──▶  _start_game(resumed=True)  ──▶  PLAYING
```

`RESULT` state (win/loss): Save & Quit button must be **disabled** (greyed out, non-clickable) when `board.game_over` is `True`. There is no value in saving a finished game.

---

## Phase 2 — Implementation Order

**Rule**: engine first → renderer second → main last. Each layer depends only on the layers above it.

---

### Step 1 — `engine.py`: `SAVE_SCHEMA_VERSION` constant

```python
SAVE_SCHEMA_VERSION: str = "gameworks.save.v1"
```

Add immediately after the `STREAK_TIERS` constant block.

---

### Step 2 — `engine.py`: `SaveResult` and `LoadResult` dataclasses

Add after `CellState`. Both must be `@dataclass(frozen=True)`. `LoadResult.engine` field type is `Optional["GameEngine"]` — use string annotation to avoid forward reference error since `GameEngine` is defined later in the same file.

---

### Step 3 — `engine.py`: `Board.from_arrays()` classmethod

Add to the `Board` class after `wrong_flag_positions()`.

Full implementation:

```python
@classmethod
def from_arrays(
    cls,
    mine: "np.ndarray",
    revealed: "np.ndarray",
    flagged: "np.ndarray",
    questioned: "np.ndarray",
    state: str,
) -> "Board":
    """Reconstruct a Board from saved numpy arrays (used by load_game_state)."""
    h, w = mine.shape
    mine_positions = {
        (int(x), int(y))
        for y, x in zip(*np.where(mine))
    }
    board = cls(w, h, mine_positions)          # runs __init__ + convolution
    board._revealed   = revealed.astype(bool)
    board._flagged    = flagged.astype(bool)
    board._questioned = questioned.astype(bool)
    board._state      = state
    # Recompute all dirty-int counters from arrays
    board._n_revealed      = int(board._revealed.sum())
    board._n_safe_revealed = int((board._revealed & ~board._mine).sum())
    board._n_flags         = int(board._flagged.sum())
    board._n_questioned    = int(board._questioned.sum())
    board._n_correct_flags = int((board._flagged & board._mine).sum())
    return board
```

**Edge case**: `mine_positions` set construction uses `np.where` which returns `(row_indices, col_indices)`. The `(x, y)` convention is `(col, row)` — confirm `x = col_idx`, `y = row_idx`.

---

### Step 4 — `engine.py`: `save_game_state(engine, path) -> SaveResult`

Top-level function (not a method — pure function, no `self`).

```python
def save_game_state(engine: "GameEngine", path: str) -> SaveResult:
    """
    Serialise full game state to a .mscsave file (numpy .npz archive).
    Uses atomic write: writes to <path>.tmp first, then os.replace().
    """
    import json
    import os

    b = engine.board
    meta_dict = {
        "schema":      SAVE_SCHEMA_VERSION,
        "score":       engine.score,
        "streak":      engine.streak,
        "elapsed":     engine.elapsed,        # @property — freezes timer at call time
        "board_state": b._state,
        "width":       b.width,
        "height":      b.height,
        "seed":        engine.seed,
        "mode":        engine.mode,
        "image_path":  engine.image_path,
        "npy_path":    engine.npy_path,
    }
    meta_bytes = json.dumps(meta_dict).encode("utf-8")

    tmp_path = path + ".tmp"
    try:
        np.savez_compressed(
            tmp_path,
            mine       = b._mine,
            revealed   = b._revealed,
            flagged    = b._flagged,
            questioned = b._questioned,
            meta       = np.array(meta_bytes, dtype=object),
        )
        # np.savez_compressed appends .npz — the actual tmp file is tmp_path + ".npz"
        os.replace(tmp_path + ".npz", path)
    except Exception as exc:
        return SaveResult(success=False, error=str(exc))

    return SaveResult(success=True, path=path)
```

**Critical**: `np.savez_compressed(tmp_path, ...)` writes to `tmp_path + ".npz"` automatically. The `os.replace` source must be `tmp_path + ".npz"`, not `tmp_path`. Confirm this in implementation — it is a common off-by-one error.

**Atomic write guarantee**: If the process dies between `np.savez_compressed` and `os.replace`, only the `.tmp.npz` orphan exists. The original save (if any) at `path` is untouched. `os.replace` is atomic on POSIX and effectively atomic on Windows (single Win32 `MoveFileEx` call).

---

### Step 5 — `engine.py`: `load_game_state(path) -> LoadResult`

Top-level function.

```python
def load_game_state(path: str) -> LoadResult:
    """
    Deserialise a .mscsave file into a ready-to-run GameEngine.
    Returns LoadResult(success=False, error=...) on any failure.
    """
    import json

    try:
        data = np.load(path, allow_pickle=True)
    except Exception as exc:
        return LoadResult(success=False, error=f"Cannot open file: {exc}")

    try:
        meta = json.loads(data["meta"].item().decode("utf-8"))
    except Exception as exc:
        return LoadResult(success=False, error=f"Corrupt metadata: {exc}")

    if meta.get("schema") != SAVE_SCHEMA_VERSION:
        return LoadResult(
            success=False,
            error=f"Incompatible schema '{meta.get('schema')}' "
                  f"(expected '{SAVE_SCHEMA_VERSION}')",
        )

    try:
        board = Board.from_arrays(
            mine       = data["mine"],
            revealed   = data["revealed"],
            flagged    = data["flagged"],
            questioned = data["questioned"],
            state      = meta["board_state"],
        )
    except Exception as exc:
        return LoadResult(success=False, error=f"Board reconstruction failed: {exc}")

    eng = GameEngine.__new__(GameEngine)
    eng.board         = board
    eng.score         = int(meta["score"])
    eng.streak        = int(meta["streak"])
    eng.seed          = int(meta["seed"])
    eng.mode          = str(meta["mode"])
    eng.image_path    = str(meta.get("image_path", ""))
    eng.npy_path      = str(meta.get("npy_path", ""))
    eng._first_click  = False          # first click already happened
    eng._start_time   = 0.0            # timer not running until start() is called
    eng._paused_elapsed = float(meta["elapsed"])
    eng.mine_flash    = {}             # expiry times are stale — reset to empty

    return LoadResult(
        success=True,
        engine=eng,
        elapsed_offset=float(meta["elapsed"]),
    )
```

**`GameEngine.__new__` usage**: Bypasses `__init__` to avoid re-running mine placement and board construction. All attributes set manually. This is the only acceptable use of `__new__` in the codebase — document it with a comment inside `load_game_state`.

**`allow_pickle=True` — SECURITY RISK (accepted for v1)**:
`allow_pickle=True` enables numpy's pickle deserialisation path for `dtype=object` arrays. A maliciously crafted `.mscsave` file can use this to execute arbitrary Python code at load time — this is a known numpy attack vector. Mitigations applied in v1:
- Schema check (`meta["schema"] == SAVE_SCHEMA_VERSION`) runs before any array unpickling at the application level, but this does **not** prevent pickle execution — pickle fires at `np.load()` time, before any Python-level validation.
- The only `dtype=object` array stored is `meta` (raw JSON bytes). Numpy pickles this as a `bytes` object, which is safe.
- **Accepted risk**: `.mscsave` files are user-generated local files. Do not load `.mscsave` files from untrusted sources (network downloads, shared drives, untrusted users). Document this in `docs/SECURITY.md`.
- Add this comment inside `load_game_state` immediately above `np.load`: `# SECURITY: allow_pickle=True required for 0-d object array (meta bytes). Only load .mscsave files from trusted local sources.`

---

### Step 6 — `renderer.py`: Save & Quit button

#### 6a. Add `_btn_save_state` rect in `_on_resize()`

Current button layout (lines 335–344):
```
_btn_new       slot 0
_btn_help      slot 1
_btn_fog       slot 2
_btn_save      slot 3   ("Save .npy")
_btn_restart   slot 4   ("New Game")
_btn_dev_solve slot 5   (dev section, _dev_offset = (btn_h+gap)*5 + gap*3)
```

Insert `_btn_save_state` at **slot 4**, shift `_btn_restart` to **slot 5**, shift `_btn_dev_solve` `_dev_offset` calculation accordingly:

```python
self._btn_save_state = pygame.Rect(px, oy + (btn_h + gap) * 4, btn_w, btn_h)
self._btn_restart    = pygame.Rect(px, oy + (btn_h + gap) * 5, btn_w, btn_h)
_dev_offset = (btn_h + gap) * 6 + gap * 3
```

**Panel height overflow arithmetic — must be verified before coding:**

`PANEL_H = 520`. The panel content height is the bottom edge of the dev button:

```
content_height = _dev_offset + btn_h
               = (btn_h + gap) * 6 + gap * 3 + btn_h
               = 7 * btn_h + 9 * gap
```

At minimum values (`btn_h = 28`, `gap = 6`):
```
7 * 28 + 9 * 6 = 196 + 54 = 250px
```

At `btn_h = max(28, font_base + 10)` where `font_base` is typically 16–20px:
```
btn_h ≈ 30, gap ≈ 6
7 * 30 + 9 * 6 = 210 + 54 = 264px
```

**264px < 520px (`PANEL_H`). No overflow. Panel height is sufficient.**

If `font_base` ever exceeds ~60px (i.e., `btn_h > 68`), overflow would occur at `7 * 68 + 9 * 13 = 476 + 117 = 593 > 520`. This is unreachable in practice but should be noted in the code with a comment.

#### 6b. Add `_save_toast` state

Add to `Renderer.__init__`:
```python
self._save_toast: str = ""          # message to display
self._save_toast_until: float = 0.0 # wall-clock expiry (time.time())
```

These are the only two new instance attributes. They require no `__slots__` change — `Renderer` does not use `__slots__`.

#### 6c. `handle_panel()` — add button hit-test

Add immediately after the `_btn_save` hit-test:

```python
if self._btn_save_state.collidepoint(mx, my):
    if not self.board.game_over:    # disabled when game is finished
        return "save_state"
    return None
```

When `board.game_over` is `True`, the button collision still fires but returns `None` — identical to how a disabled state is handled for other buttons.

#### 6d. `_draw_panel()` — add button to draw list

Add to the `buttons` list in `_draw_panel()`:

```python
(self._btn_save_state, "Save & Quit"),
```

Colour: `C["cyan"]` (same as `Save .npy`).

**Greyed-out appearance when disabled**: Add a conditional after the `pill()` draw:

```python
if label == "Save & Quit" and self.board.game_over:
    # Draw semi-transparent overlay to indicate disabled state
    grey_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    grey_surf.fill((0, 0, 0, 140))
    self._win.blit(grey_surf, rect.topleft)
```

#### 6e. Toast overlay in `draw()`

Add to `draw()` immediately before `pygame.display.flip()`:

```python
if self._save_toast and time.time() < self._save_toast_until:
    surf = self._font_small.render(self._save_toast, True, C["text_light"])
    self._win.blit(surf, (self.BOARD_OX + self.PAD, self.PAD))
elif self._save_toast:
    self._save_toast = ""   # clear expired toast
```

**Note**: `import time` is already present in `renderer.py` — no new import needed.

---

### Step 7 — `main.py`: `--resume` CLI flag

In `build_parser()`, add to the `mode` mutually exclusive group:

```python
mode.add_argument("--resume", type=str, default=None, metavar="PATH",
                  help="Resume a saved game (.mscsave)")
```

`--resume` is mutually exclusive with `--image`, `--load`, `--random` — they share the same `mode` group.

---

### Step 8 — `main.py`: update imports

Add `save_game_state`, `load_game_state`, `SaveResult`, `LoadResult` to both import blocks (try/except for relative vs absolute):

```python
from .engine import (
    Board, GameEngine, MoveResult, SaveResult, LoadResult,
    load_board_from_pipeline, load_board_from_npy, place_random_mines,
    save_game_state, load_game_state,
)
```

---

### Step 9 — `main.py`: `_build_engine()` — add `--resume` branch

Add before the `elif a.load:` branch:

```python
if getattr(a, "resume", None):
    result = load_game_state(a.resume)
    if not result.success:
        print(f"[ERROR] Cannot resume: {a.resume} — {result.error}", file=sys.stderr)
        sys.exit(1)
    return result.engine
```

`result.elapsed_offset` is stored on `result.engine._paused_elapsed` already (set inside `load_game_state`). No additional injection needed.

---

### Step 10 — `main.py`: `_start_game()` — handle resumed engine

`_start_game()` currently calls `eng.start()` which resets `_start_time` and `_paused_elapsed` to zero. A resumed engine must NOT call `start()` — the timer must continue from `_paused_elapsed`.

Add a `resumed: bool` parameter:

```python
def _start_game(self, resumed: bool = False):
    eng = self._build_engine()
    self._engine = eng
    if not resumed:
        self._engine.start()
    else:
        # Resumed: timer is paused at saved elapsed; start it running again
        self._engine._start_time = time.time() - self._engine._paused_elapsed

    image_path = eng.image_path if eng.mode == "image" else None
    self._renderer = Renderer(eng, image_path=image_path)
    self._state = self.PLAYING
    self._result_shown = False
```

Call site in `run()`:

```python
if not self._engine:
    resumed = getattr(self.args, "resume", None) is not None
    self._start_game(resumed=resumed)
```

**Timer resume logic**: `_start_time = time.time() - _paused_elapsed` sets the clock such that `time.time() - _start_time == _paused_elapsed` at this instant — the elapsed property immediately returns the saved value and increases from there.

---

### Step 11 — `main.py`: `_save_state()` method

```python
def _save_state(self):
    """Save full game state to .mscsave and quit."""
    eng = self._engine
    if not eng or eng.board.game_over:
        return
    ts = time.strftime("%Y%m%d_%H%M%S")
    fname = f"save_{ts}_{eng.board.width}x{eng.board.height}.mscsave"
    result = save_game_state(eng, fname)
    if result.success:
        print(f"[SAVE] Game saved → {result.path}")
        # Surface the filename in the renderer toast (shown for 1 frame before quit)
        if self._renderer:
            self._renderer._save_toast = f"Saved: {result.path}"
            self._renderer._save_toast_until = time.time() + 0.1
    else:
        print(f"[SAVE] Failed: {result.error}", file=sys.stderr)
```

---

### Step 12 — `main.py`: wire `"save_state"` action in `run()`

Add to the action dispatch block after `elif r_action == "save":`:

```python
elif r_action == "save_state":
    self._save_state()
    running = False   # quit immediately after save
```

---

### Step 13 — `main.py`: `preflight_check()` — create and wire

`preflight_check()` does **not** currently exist in `main.py`. Create it as a new top-level function, inserted between `build_parser()` and the `GameLoop` class definition. Call it from `main()` before `GameLoop(args).run()`.

**Full function to create:**

```python
def preflight_check(args: argparse.Namespace) -> None:
    """
    Validate all file-path arguments before the pygame window opens.
    Exits with a clear error message on any failure.
    Called once from main() before GameLoop(args).run().
    """
    if getattr(args, "resume", None):
        if not os.path.isfile(args.resume):
            print(f"[PREFLIGHT] Resume file not found: {args.resume}", file=sys.stderr)
            sys.exit(1)
        if not args.resume.endswith(".mscsave"):
            print(
                f"[PREFLIGHT] --resume requires a .mscsave file; got: {args.resume}\n"
                f"  To load a board definition use --load instead.",
                file=sys.stderr,
            )
            sys.exit(1)

    if getattr(args, "load", None):
        if not os.path.isfile(args.load):
            print(f"[PREFLIGHT] --load file not found: {args.load}", file=sys.stderr)
            sys.exit(1)

    if getattr(args, "image", None):
        if not os.path.isfile(args.image):
            print(f"[PREFLIGHT] --image file not found: {args.image}", file=sys.stderr)
            sys.exit(1)
```

**Wire into `main()`:**

```python
def main():
    args = build_parser().parse_args()
    preflight_check(args)          # ← add this line before GameLoop
    ...
    loop = GameLoop(args)
    loop.run()
```

**Why validate `--load` and `--image` here too**: `preflight_check` is the single validation point for all path arguments. Adding `--load` and `--image` validation here is a zero-cost improvement that prevents the pygame window from opening only to immediately crash on a missing file — consistent with the pattern gap P6 identified in `DESIGN_PATTERNS.md`.

---

## Phase 3 — Tests

### `gameworks/tests/unit/test_save_load.py` — new file

All tests are headless (no pygame). Use `tmp_path` pytest fixture for file I/O.

#### Fixtures

```python
@pytest.fixture
def fresh_engine():
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    eng.start()
    return eng

@pytest.fixture
def played_engine(fresh_engine):
    """Engine with some revealed cells, flags, and score."""
    eng = fresh_engine
    eng.left_click(4, 4)      # reveal a cell
    eng.right_click(0, 0)     # place a flag
    eng.right_click(1, 0)     # place another flag
    return eng
```

#### Test cases

- [ ] `test_save_creates_file(played_engine, tmp_path)` — `save_game_state` returns `SaveResult(success=True)` and the file exists at the returned path
- [ ] `test_save_file_is_mscsave_extension(played_engine, tmp_path)` — saved path ends with `.mscsave`
- [ ] `test_no_tmp_file_after_save(played_engine, tmp_path)` — `<path>.tmp.npz` does not exist after successful save
- [ ] `test_round_trip_mine_array(played_engine, tmp_path)` — `load_game_state` returns engine whose `board._mine` equals original `_mine` element-wise
- [ ] `test_round_trip_revealed_array(played_engine, tmp_path)` — `board._revealed` matches
- [ ] `test_round_trip_flagged_array(played_engine, tmp_path)` — `board._flagged` matches
- [ ] `test_round_trip_questioned_array(played_engine, tmp_path)` — `board._questioned` matches
- [ ] `test_round_trip_score(played_engine, tmp_path)` — `engine.score` matches
- [ ] `test_round_trip_streak(played_engine, tmp_path)` — `engine.streak` matches
- [ ] `test_round_trip_elapsed(played_engine, tmp_path)` — loaded `_paused_elapsed` within 0.1s of saved value
- [ ] `test_round_trip_board_state(played_engine, tmp_path)` — `board._state` is `"playing"`
- [ ] `test_round_trip_dirty_counters(played_engine, tmp_path)` — `_n_flags`, `_n_safe_revealed`, `_n_revealed`, `_n_correct_flags`, `_n_questioned` all match originals
- [ ] `test_round_trip_first_click_false(played_engine, tmp_path)` — loaded engine has `_first_click == False`
- [ ] `test_round_trip_mine_flash_empty(played_engine, tmp_path)` — loaded engine has `mine_flash == {}`
- [ ] `test_load_schema_mismatch_returns_failure(tmp_path)` — manually write a `.npz` with `schema="gameworks.save.v0"`, confirm `LoadResult(success=False)` with error mentioning schema
- [ ] `test_load_missing_file_returns_failure()` — `load_game_state("/nonexistent/path.mscsave")` returns `LoadResult(success=False)`
- [ ] `test_load_corrupt_file_returns_failure(tmp_path)` — write garbage bytes to a `.mscsave` file, confirm `LoadResult(success=False)`
- [ ] `test_save_bad_path_returns_failure(played_engine)` — `save_game_state(eng, "/nonexistent/dir/save.mscsave")` returns `SaveResult(success=False)`
- [ ] `test_board_from_arrays_neighbours_recomputed(played_engine, tmp_path)` — loaded `board._neighbours` equals original (confirms convolution runs on load)
- [ ] `test_board_from_arrays_state_preserved(tmp_path)` — save a board in `"playing"` state, load, confirm `_state == "playing"`
- [ ] `test_save_disabled_on_game_over(tmp_path)` — create an engine where `board._state = "won"`, confirm `save_game_state` still works (save itself is not gated in engine — the gate is in renderer/main) OR confirm the renderer gate test below
- [ ] `test_atomic_tmp_file_cleaned_up(played_engine, tmp_path)` — after successful save, confirm neither `<path>.tmp` nor `<path>.tmp.npz` exists on disk; this specifically guards against the `os.replace(tmp_path, path)` vs `os.replace(tmp_path + ".npz", path)` off-by-one error
- [ ] `test_round_trip_image_path(tmp_path)` — create engine with `mode="image"`, non-empty `image_path="test_image.png"`, save and load, confirm `engine.image_path == "test_image.png"` in loaded engine
- [ ] `test_board_from_arrays_total_mines_correct(played_engine, tmp_path)` — loaded `board.total_mines` equals original `board.total_mines`; confirms `from_arrays` mine position extraction produces the correct count

### `gameworks/tests/renderer/test_save_resume.py` — new file

Requires `conftest.py` SDL dummy drivers. Use `renderer_easy` fixture.

- [ ] `test_save_state_button_exists(renderer_easy)` — `hasattr(r, "_btn_save_state")` and `isinstance(r._btn_save_state, pygame.Rect)`
- [ ] `test_save_state_button_returns_action_string(renderer_easy)` — simulate left-click on `_btn_save_state` center, confirm `handle_event()` returns `"save_state"` when `board._state == "playing"`
- [ ] `test_save_state_button_disabled_when_game_over(renderer_easy)` — set `r.board._state = "won"`, simulate click, confirm return is `None` not `"save_state"`
- [ ] `test_save_toast_initially_empty(renderer_easy)` — `r._save_toast == ""`
- [ ] `test_save_toast_expires(renderer_easy)` — set `r._save_toast = "test"` and `r._save_toast_until = time.time() - 1`, call `draw(...)`, confirm `r._save_toast == ""`
- [ ] `test_save_state_button_exists_at_init(renderer_easy)` — add to `TestRendererConstants` in `test_renderer_init.py`: `hasattr(r, "_btn_save_state")` and `isinstance(r._btn_save_state, pygame.Rect)`; this belongs in `test_renderer_init.py` alongside other button init tests, not only in `test_save_resume.py`
- [ ] `test_save_state_button_does_not_overlap_restart(renderer_easy)` — `r._btn_save_state.bottom <= r._btn_restart.top`; guards against slot calculation errors shifting buttons into each other

### `gameworks/tests/integration/test_main.py` — additions

- [ ] `test_resume_flag_loads_saved_state(tmp_path)` — save a game, parse args with `--resume <path>`, call `_build_engine()`, confirm returned engine has correct `score`, `streak`, `_paused_elapsed`
- [ ] `test_resume_flag_mutually_exclusive_with_load(capsys)` — parse args with both `--resume` and `--load`, confirm argparse error
- [ ] `test_resumed_engine_timer_is_running(tmp_path)` — save engine with `elapsed ≈ 50.0`, load it, call `_start_game(resumed=True)`, wait 0.05s, confirm `engine.elapsed > 50.0`; confirms `_start_time` is set correctly so timer actually advances and is not frozen
- [ ] `test_preflight_rejects_npy_file_as_resume(tmp_path, capsys)` — call `preflight_check` with `args.resume = "board.npy"` (a valid path but wrong extension), confirm `sys.exit(1)` is raised with message mentioning `.mscsave`
- [ ] `test_preflight_passes_with_valid_mscsave(played_engine, tmp_path)` — save a real game, call `preflight_check` with the resulting path, confirm no exit raised

### Existing tests that must still pass

- [ ] All 114 renderer tests pass — `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/ -v`
- [ ] All unit tests pass — `pytest gameworks/tests/unit/ -v`
- [ ] Architecture boundary test passes — `pytest gameworks/tests/architecture/ -v`

---

## Phase 4 — Documentation

- [ ] `CHANGELOG.md` — add entry: `feat(gameworks): save/resume/load mid-game state (.mscsave format)`
- [ ] `docs/GAME_DESIGN.md` — add section: Save & Resume. Document what is saved, what is not, and why.
- [ ] `docs/API_REFERENCE.md` — add `save_game_state`, `load_game_state`, `SaveResult`, `LoadResult`, `Board.from_arrays`, `SAVE_SCHEMA_VERSION`, `preflight_check`
- [ ] `docs/ARCHITECTURE.md` — add new data flow entry: `GameLoop._save_state() → engine.save_game_state() → .mscsave` and `--resume → preflight_check() → engine.load_game_state() → GameLoop._start_game(resumed=True)`
- [ ] `docs/DOCS_INDEX.md` — add entry for `FEATURE_SAVE_RESUME_LOAD.md`, `SAVE_FORMAT_SPEC.md`, `SCHEMA_MIGRATION.md`, and `SECURITY.md`
- [ ] `docs/SAVE_FORMAT_SPEC.md` — create: standalone file format reference (array keys, dtypes, shapes, JSON field list with types and valid values, schema version history table, byte-order note, manual inspection command)
- [ ] `docs/SCHEMA_MIGRATION.md` — create: trigger conditions for schema bumps, migration function template, backwards-read policy
- [ ] `docs/SECURITY.md` — create: document `allow_pickle=True` risk, accepted-risk declaration for v1, guidance to only load `.mscsave` files from trusted local sources
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` — create or update: add checklist for this PR (tests green, no TODO left in code, Ambiguity Register reviewed, `DOCS_INDEX.md` updated, version bumped, `allow_pickle` comment present in `load_game_state`)

---

## Phase 5 — Version & Release

- [ ] Bump `gameworks/__init__.py` — **minor version** (new user-facing feature, backwards compatible)
- [ ] Confirm bumped version matches `CHANGELOG.md` entry header
- [ ] Commit message: `feat(gameworks): save/resume/load mid-game state`

---

## Rollback Procedure

If the feature must be reverted after merge to `frontend-game-mockup`:

```bash
# Identify the merge commit SHA from git log
git log --oneline frontend-game-mockup | head -10

# Revert the merge commit (creates a new revert commit, does not rewrite history)
git revert <merge-commit-sha> --no-edit
git push origin frontend-game-mockup
```

**Impact on existing `.mscsave` files**: After revert, `--resume` no longer exists in the parser. Any user who saved a game and attempts `--resume save_xxx.mscsave` receives argparse's standard "unrecognised arguments" error — a clean failure, not a crash. Existing `.mscsave` files on disk are inert and can be deleted manually.

**Impact on existing `--load` and `--random` behaviour**: None. `_save_npy()` and `--load` are unmodified by this feature and survive revert intact.

---

## Schema Migration

`SAVE_SCHEMA_VERSION = "gameworks.save.v1"`. The following changes to the save format **require a schema bump** to `v2` (i.e. the version string in `SAVE_SCHEMA_VERSION` and in all new save files must change):

| Change | Requires bump? |
|---|---|
| Adding a new optional JSON meta field with a default | No — `meta.get("new_field", default)` handles absence in old files |
| Adding a new required JSON meta field (no default) | **Yes** — old v1 files would fail `meta["new_field"]` with `KeyError` |
| Removing a JSON meta field | **Yes** — code reading old files would KeyError on absent field |
| Changing a field's type (e.g. `score: int` → `score: float`) | **Yes** |
| Adding a new numpy array to the archive | No if optional; **Yes** if required on load |
| Renaming an array key | **Yes** |
| Changing an array dtype | **Yes** |

**When a bump is required**, the procedure is:

1. Increment `SAVE_SCHEMA_VERSION` to `"gameworks.save.v2"` in `engine.py`
2. Add a `_migrate_v1_to_v2(data, meta)` function in `engine.py` that transforms a v1 archive into the v2 structure in memory
3. In `load_game_state`, detect `schema == "gameworks.save.v1"` and call the migration function before proceeding; this lets users resume v1 saves after upgrading
4. Update `test_load_schema_mismatch_returns_failure` to use `"gameworks.save.v0"` (unknown), not `"gameworks.save.v1"` (now supported via migration)
5. Add `test_migrate_v1_to_v2_round_trip` confirming v1 files load correctly under v2 reader

---

## Filename Safety

The filename pattern `save_<YYYYMMDD_HHMMSS>_<W>x<H>.mscsave` is confirmed safe on all target platforms:

| Character | Windows illegal? | Present in pattern? |
|---|---|---|
| `<` `>` | Yes | No |
| `:` | Yes | No — `%H%M%S` produces no colons |
| `"` | Yes | No |
| `/` `\` | Yes (path sep) | No |
| `\|` `?` `*` | Yes | No |
| `x` (W×H separator) | No | Yes — safe |
| `_` `-` `.` | No | Yes — safe |

`time.strftime("%Y%m%d_%H%M%S")` on Windows produces e.g. `20260510_143022` — no colons, no illegal characters. **Confirmed safe on Windows, macOS, and Linux.**

---

## Ambiguity Register

Every design decision that could be argued either way is recorded here.

| Decision | Choice | Reason |
|---|---|---|
| `.mscsave` vs `.npz` extension | `.mscsave` | Prevents `--load` / `--resume` confusion; signals intent |
| `meta` as JSON bytes vs structured array | JSON bytes in 0-d object array | `np.savez` coerces strings unsafely; JSON bytes is deterministic |
| `_neighbours` saved or recomputed | Recomputed via convolution on load | Derived data — storing it risks stale values if code changes |
| `mine_flash` saved or reset | Reset to `{}` | Expiry times are wall-clock absolute; meaningless after quit |
| `_first_click` saved or forced False | Forced `False` | A resumed game has already had its first click |
| Timer resume: `start()` vs manual `_start_time` | Manual `_start_time = time.time() - _paused_elapsed` | `start()` resets `_paused_elapsed` to 0, destroying saved elapsed |
| Save location: CWD vs user home vs `~/.minesweeper/` | CWD in v1 | Consistent with existing `.npy` export; no directory management needed in v1 |
| Save on win/loss | Disabled (greyed button) | No value in resuming a finished game; avoids ambiguous reload state |
| Overwrite vs new file per save | New timestamped file per save | No save-slot management complexity; user manages files manually in v1 |
| `save_game_state` as method vs function | Top-level function | Engine should not own its own serialisation; keeps engine pure-logic |
| `total_mines` in meta JSON | Not stored — derived from `mine` array | `total_mines = len(mine_positions)` is computed inside `Board.__init__` from the `mine` array; storing it in meta would create a consistency risk (meta value vs array reality). Do not add it to meta in any future version without removing the derivation path. |
