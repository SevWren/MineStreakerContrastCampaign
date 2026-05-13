# Generated Fixes
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Fix 1: GameEngine.state property (FIND-ARCH-CRITICAL-f002a)

**File**: `gameworks/engine.py`
**Insert after**: `def stop_timer(self):` block (~line 258)

```python
@property
def state(self) -> str:
    """Expose board state for callers. Returns 'playing' | 'won' | 'lost'."""
    return self.board._state
```

**Rationale**: `main.py` references `self._engine.state`. Board._state is the authoritative state string.

---

## Fix 2: FPS constant in main.py (FIND-ARCH-CRITICAL-f001a)

**File**: `gameworks/main.py`
**Add at module level** after imports:

```python
FPS = 60  # Match renderer.FPS
```

Or import from renderer (preferred for DRY):
```python
from .renderer import FPS
```

---

## Fix 3: compile_sa_kernel() call signature (FIND-ARCH-CRITICAL-f003a)

**File**: `gameworks/engine.py`, function `load_board_from_pipeline`
**Find**: `compile_sa_kernel(board_w, board_h, seed)`
**Replace with**:
```python
kernel = compile_sa_kernel()

# ... build params dict ...
params = default_config(board_w, board_h, seed)
grid, *_ = run_sa(kernel, grid, target, weights, forbidden, **params["sa"])
```

**Note**: `sa.py::run_sa()` takes `kernel` as first argument. See `run_iter9.py` for the canonical call pattern.

---

## Fix 4: run_phase1_repair() call signature (FIND-ARCH-CRITICAL-f004a)

**File**: `gameworks/engine.py`, function `load_board_from_pipeline`
**Find**:
```python
class _RouteCfg:
    phase2_budget_s = 360.0
    last100_budget_s = 300.0
    last100_unknown_threshold = 100
    solve_max_rounds = 300
    trial_max_rounds = 60
    enable_phase2 = True
    enable_last100 = True
    enable_sa_rerun = False

grid = run_phase1_repair(grid, target, weights, forbidden, _RouteCfg(), seed)
```

**Replace with**:
```python
grid = run_phase1_repair(
    grid, target, weights, forbidden,
    time_budget_s=90.0,
    max_rounds=300,
)
```

**Rationale**: `_RouteCfg` is a routing config for `pipeline.py::route_late_stage_failure()`, not for `run_phase1_repair()`. Remove the inner class entirely.

---

## Fix 5: btn_w stored on self (FIND-ARCH-CRITICAL-f005a)

**File**: `gameworks/renderer.py`, `Renderer.__init__`
**Find**: `btn_w = self.PANEL_W - 2 * self.PAD`
**Replace with**: `self._btn_w = self.PANEL_W - 2 * self.PAD`

Then in `_draw_panel()`, replace all occurrences of `btn_w` with `self._btn_w`.

**Rationale**: Local variables in `__init__` are not accessible in other methods.

---

## Fix 6: Double panel click (FIND-ARCH-HIGH-h001a)

**File**: `gameworks/main.py`
**Find in `GameLoop.run()`**:
```python
# Panel button via collidepoint
if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
    panel_action = self._renderer.handle_panel(ev.pos)
    if panel_action == "quit":
        running = False
        break
    elif panel_action == "restart":
        self._start_game()
        continue
    elif panel_action == "save":
        self._save_npy()
```

**Delete this entire block**. `handle_event()` already calls `handle_panel()` internally and returns the action. The main loop's `r_action` handling already covers restart/quit.

---

## Fix 7: Fog attribute name (FIND-RENDER-HIGH-h002a)

**File**: `gameworks/renderer.py`
**Find in `_draw_overlay()`**:
```python
if not getattr(self, '_fog', False):
    return
```
**Replace with**:
```python
if not self.fog:
    return
```

---

## Fix 8: Ghost surface performance (FIND-PERF-HIGH-h003a)

**File**: `gameworks/renderer.py`

### In `Renderer.__init__`, after image loading:
```python
# Pre-compute ghost composite surface (cached)
self._ghost_surf: Optional[pygame.Surface] = None
self._ghost_needs_update = True
```

### Add method `_get_ghost_surf()`:
```python
def _get_ghost_surf(self, bw: int, bh: int) -> Optional[pygame.Surface]:
    """Return cached ghost surface, rebuilding if board dimensions changed."""
    if self._image_surf is None:
        return None
    if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
        scaled = pygame.transform.smoothscale(self._image_surf, (bw, bh))
        self._ghost_surf = scaled
    return self._ghost_surf
```

### Replace `_draw_image_ghost()`:
```python
def _draw_image_ghost(self, ox, oy, bw, bh):
    ghost = self._get_ghost_surf(bw, bh)
    if ghost is None:
        return
    ts = self._tile
    for y in range(self.board.height):
        for x in range(self.board.width):
            if not self.board._flagged[y, x]:
                continue
            # Draw pixel from cached ghost surface
            px = ox + x * ts
            py = oy + y * ts
            src_rect = pygame.Rect(x * ts, y * ts, ts, ts)
            self._win.blit(ghost, (px, py), area=src_rect,
                          special_flags=pygame.BLEND_RGBA_MULT if not self.board._mine[y, x] else 0)
```

**Note**: This eliminates per-cell Surface creation entirely — uses cached blit with rect source.

---

## Fix 9: Loss overlay viewport culling (FIND-PERF-HIGH-h004a)

**File**: `gameworks/renderer.py`, `_draw_loss_overlay()`
**Find**:
```python
def _draw_loss_overlay(self, ox, oy):
    ts = self._tile
    for y in range(self.board.height):
        for x in range(self.board.width):
```
**Replace with**:
```python
def _draw_loss_overlay(self, ox, oy):
    ts = self._tile
    win_w, win_h = self._win.get_size()
    tx0 = max(0, (-self._pan_x) // ts - 1)
    ty0 = max(0, (-self._pan_y) // ts - 1)
    tx1 = min(self.board.width, (win_w - ox) // ts + 2)
    ty1 = min(self.board.height, (win_h - oy) // ts + 2)
    for y in range(ty0, ty1):
        for x in range(tx0, tx1):
```

---

## Fix 10: Board neighbour computation (FIND-PERF-MEDIUM-m001a)

**File**: `gameworks/engine.py`, `Board.__init__`
**Find the neighbour loop**:
```python
self._neighbours = np.zeros((height, width), dtype=np.uint8)
for y in range(height):
    for x in range(width):
        if not self._mine[y, x]:
            self._neighbours[y, x] = self._count_adj(x, y)
```
**Replace with**:
```python
from scipy.ndimage import convolve as _convolve
_kernel = np.ones((3, 3), dtype=np.uint8)
_kernel[1, 1] = 0
raw = _convolve(self._mine.astype(np.uint8), _kernel, mode='constant', cval=0)
self._neighbours = np.where(self._mine, np.uint8(0), raw.astype(np.uint8))
```

**Speedup**: Python loop O(H*W*9) → scipy O(H*W) with C implementation. ~1000× faster on 300×370 boards.

---

## Fix 11: _save_npy vectorization (FIND-PERF-MEDIUM-m008a)

**File**: `gameworks/main.py`, `GameLoop._save_npy()`
**Find**:
```python
grid = np.zeros((eng.board.height, eng.board.width), dtype=np.int8)
for y in range(eng.board.height):
    for x in range(eng.board.width):
        cell = eng.board.snapshot(x, y)
        if cell.is_mine:
            grid[y, x] = -1
        else:
            grid[y, x] = cell.neighbour_mines
```
**Replace with**:
```python
grid = np.where(
    eng.board._mine,
    np.int8(-1),
    eng.board._neighbours.astype(np.int8)
)
```

---

## Fix 12: Optional import in main.py

**File**: `gameworks/main.py`
**Add to imports**:
```python
from typing import Optional
```

---

## Fix 13: Win condition — correct flag check

**File**: `gameworks/engine.py`, `Board.reveal()` (win check at end)
**Current**:
```python
if self.revealed_count == self.total_safe:
    self._state = "won"
```
**Replace with**:
```python
if (self.revealed_count == self.total_safe and
        self.correct_flags == self.total_mines):
    self._state = "won"
```

Apply the same change in `toggle_flag()`.

**Note**: This changes game behavior. The player must correctly flag ALL mines AND reveal all safe cells to win. This matches `GAME_DESIGN.md` spec and the image-reconstruction mechanic.

---

## Fix 15: Pipeline .npy format adapter (FIND-ARCH-CRITICAL-f006a)

**File**: `gameworks/engine.py`, function `load_board_from_npy`

Pipeline boards (from `run_iter9.py`) use `int8` with `0=safe, 1=mine`. Game boards (saved by `_save_npy()`) use `int8` with `-1=mine, 0-8=neighbour_count`. The current implementation only handles game format.

### Option A — Auto-detect format (recommended):

```python
def load_board_from_npy(path: str) -> Board:
    grid = np.load(path)
    h, w = grid.shape

    # Detect pipeline format: only values {0, 1}, no negatives, no values > 1
    is_pipeline_format = (grid.min() >= 0 and grid.max() <= 1)

    if is_pipeline_format:
        # Pipeline format: 1=mine, 0=safe; no neighbour counts stored
        mine_map = (grid == 1)
        mine_pos = {(x, y) for y, x in zip(*np.where(mine_map))}
    else:
        # Game format: -1=mine, 0-8=neighbour count
        mine_pos = {(x, y) for y, x in zip(*np.where(grid < 0))}

    board = Board(w, h, mine_pos)
    # Skip neighbour validation for pipeline format (values are 0/1, not counts)
    if not is_pipeline_format:
        _validate_neighbours(board, grid)  # existing validation logic
    return board
```

### Option B — Dedicated function:

```python
def load_board_from_pipeline_npy(path: str) -> Board:
    """Load a board from run_iter9.py pipeline output (0=safe, 1=mine)."""
    grid = np.load(path)
    h, w = grid.shape
    mine_pos = {(x, y) for y, x in zip(*np.where(grid == 1))}
    return Board(w, h, mine_pos)
```

And update `GameEngine._build_engine()` for `--npy` mode to detect and dispatch accordingly.

**Note**: Fix 15 should be applied before any NPY board development, as all three committed boards are in pipeline format.

---

## Fix 14: Stale board reference in Renderer

**File**: `gameworks/renderer.py`, `Renderer.__init__`

Store engine reference, not board:
```python
self.engine = engine
# Remove: self.board = engine.board
```

Change all `self.board` references to `self.engine.board`.

OR: In `left_click()` in `GameEngine`, after board regeneration:
```python
# Notify renderer of new board
# (if Renderer is available — requires back-reference or event system)
```

The simplest fix is to make Renderer always read `self.engine.board` instead of caching `self.board`. This requires replacing ~30 occurrences in renderer.py.
