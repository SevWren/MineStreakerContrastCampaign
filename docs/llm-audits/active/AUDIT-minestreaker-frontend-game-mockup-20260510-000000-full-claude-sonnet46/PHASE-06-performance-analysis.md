# PHASE 06 — Performance Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## 1. Runtime Hotspots

### 1.1 gameworks/renderer.py — Image Ghost Rendering
**Impact**: CRITICAL at scale
**Location**: `_draw_image_ghost()` ~lines 820-855
**Cost**: `pygame.Surface(tile×tile)` × n_flags × 60fps. At 10,000 flags on a 300×370 board: ~600,000 Surface objects/second, each requiring GC. FPS will drop below 5.
**Fix**: Pre-compute a composite ghost surface. Cache it. On flag change, only update the cached surface.

### 1.2 gameworks/renderer.py — Win Animation Rescale
**Impact**: HIGH
**Location**: `_draw_win_animation_fx()` ~line 920
**Cost**: `pygame.transform.smoothscale(self._image_surf, (bw, bh))` every frame during win animation. Scales to full board pixel dimensions — 300×370 boards = 111,000 pixels × 4 channels scaled per frame.
**Fix**: Cache the scaled surface: `if self._win_anim_scaled is None: self._win_anim_scaled = pygame.transform.smoothscale(...)`.

### 1.3 gameworks/renderer.py — Loss Overlay
**Impact**: HIGH
**Location**: `_draw_loss_overlay()` ~lines 815-835
**Cost**: 111,000 `board.snapshot()` calls = 111,000 numpy array index operations + 111,000 Python function calls per frame.
**Fix**: Apply viewport culling. Alternatively, cache the loss overlay surface on first computation.

### 1.4 gameworks/engine.py — Board.__init__ Neighbour Loop
**Impact**: HIGH (startup)
**Location**: `Board.__init__` ~lines 70-76
**Cost**: For 300×370 board: 111,000 Python `_count_adj()` calls during construction. Each calls `_count_adj()` which creates a numpy slice and sums.
**Fix**: Replace with scipy convolution (as `core.py::compute_N()` does):
```python
from scipy.ndimage import convolve
kernel = np.ones((3, 3), dtype=np.uint8); kernel[1,1] = 0
self._neighbours = convolve(self._mine.astype(np.uint8), kernel, mode='constant')
```

### 1.5 gameworks/main.py — _save_npy() Cell Iteration
**Impact**: MEDIUM (on save)
**Location**: `_save_npy()` ~lines 265-280
**Cost**: 111,000 `snapshot(x, y)` calls. Each accesses 4 numpy arrays.
**Fix**: `grid = np.where(eng.board._mine, np.int8(-1), eng.board._neighbours.astype(np.int8))`

## 2. Memory Analysis

### Normal Operation
- Board numpy arrays: 5 arrays × (300×370) × 1 byte ≈ 555 KB
- Image surface: 300×370 RGBA = 444 KB
- Font surfaces: ~50 KB cached
- Total baseline: ~1.1 MB — acceptable

### During Image Ghost Rendering
- Per frame: n_flags × (tile² × 4 bytes) Surface objects
- At tile=10, 10,000 flags: 10,000 × 400 bytes × GC overhead ≈ 40+ MB allocation/frame
- GC pressure causes periodic frame stalls

### Numba JIT Cache
- SA kernel and solver compile on first run to `.numba_cache/`
- First run on a new machine: 10-30 seconds of JIT compilation
- Subsequent runs: sub-second load from cache
- gameworks image mode triggers this at game load time — blocks pygame event loop

## 3. Allocation Churn

| Location | Per-Frame Allocations | Severity |
|---|---|---|
| `_draw_image_ghost()` | n_flags × Surface | CRITICAL |
| `_draw_win_animation_fx()` | 1 large Surface (full board) | HIGH |
| `_draw_board()` cursor highlight | 1 tiny Surface | LOW |
| `board.snapshot(x,y)` per draw call | n_visible × CellState dataclass | MEDIUM |

## 4. Expensive Loops

| Location | Loop Size | Issue |
|---|---|---|
| `_draw_board()` | tx1-tx0 × ty1-ty0 | Acceptable — culled to viewport |
| `_draw_loss_overlay()` | H × W (all cells) | PROBLEM — no culling |
| `_draw_image_ghost()` | H × W (flagged check) | PROBLEM — no culling |
| `Board.__init__` neighbours | H × W | PROBLEM — should use convolution |

## 5. Pipeline Performance (run_iter9.py)

### SA Stage Timing (expected on 300×370 board)
- Numba warmup (first run): 10-30 seconds
- Coarse SA (2M iters): ~5-10 seconds
- Fine SA (8M iters): ~15-30 seconds
- Refine passes 1-3 (8M total iters): ~15-25 seconds
- Phase1 repair (90s budget): up to 90 seconds
- Total: 2-5 minutes per run

### Phase1 Repair Parallelism
- `ThreadPoolExecutor` used in repair.py for parallel candidate evaluation
- Numba solver (`_numba_solve`) releases GIL → true parallelism for solver calls
- However, Python setup per candidate (numpy ops) is GIL-bound
- Effective speedup: ~2-3× on 4-core machines (diminishing returns)

## 6. Profiling Strategy

### Recommended Tools
```bash
# Game performance profiling
python -m cProfile -o profile.out -m gameworks.main --random --medium
python -m pstats profile.out

# Per-frame timing
# Add to GameLoop.run():
import time
frame_start = time.perf_counter()
# ... frame ...
frame_time = time.perf_counter() - frame_start
if frame_time > 0.02:  # >50ms = <50FPS
    print(f"SLOW FRAME: {frame_time*1000:.1f}ms")

# Pipeline profiling
python -m cProfile -o pipeline_profile.out run_iter9.py --image assets/...
```

### Benchmark Strategy
```python
# tests/benchmarks/test_render_performance.py
def test_board_init_large():
    start = time.perf_counter()
    mines = place_random_mines(300, 370, 5000)
    Board(300, 370, mines)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.1, f"Board init too slow: {elapsed:.3f}s"
```

## 7. Optimization Roadmap

| Priority | Fix | Expected Gain |
|---|---|---|
| P0 | Pre-compute ghost composite Surface | Ghost render: 600K→0 allocs/sec |
| P0 | Cache win_anim_scaled surface | Win animation: 1 alloc total |
| P1 | Viewport culling in _draw_loss_overlay | Loss overlay: 111K→visible cells |
| P1 | scipy convolution for Board._neighbours | Board init: 5s→<10ms |
| P2 | Cache loss overlay surface on first compute | Loss overlay: ~0 work after first frame |
| P2 | Fix _save_npy to use numpy array ops | Save: 5s→<1ms |
| P3 | Cache number surfaces (8 values × 2 fonts) | Minor alloc reduction |
