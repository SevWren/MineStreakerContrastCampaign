# Final Optimization Report — board-gen-10x Campaign

**Branch:** `perf/board-gen-10x`
**Target:** ≥ 10× wall-clock speedup for board generation
**Machine:** 64-bit Linux, 1 CPU, Numba threads = 1
**Date:** 2026-05-16
**Status:** **TARGET NOT ACHIEVED** — Best result: 1.24× average speedup

---

## Executive Summary

After systematic implementation and measurement of all planned optimization approaches, the **10× speedup target is not achievable on this 1-CPU machine**. Three major optimization attempts all resulted in either performance degradation or quality regressions:

1. **Checkerboard Parallel SA**: 3× SLOWDOWN
2. **Fast BFS Unknown Detector**: 7.6× SLOWDOWN
3. **Greedy Mine Initialization + SA Reduction**: Quality REGRESSION

**Best achieved result: 1.24× average speedup** (from Iteration 1: vectorized `build_neighbor_table`, already committed).

---

## Baseline (Immutable Reference)

From prior optimization campaign (`perf_optimization_report.md`):

| boardw | image              | baseline_avg_s |
|--------|--------------------|----------------|
| 200    | input_source_image | 1.102          |
| 300    | input_source_image | 1.751          |
| 450    | input_source_image | 2.907          |
| 600    | input_source_image | 4.186          |
| 200    | research           | 1.085          |
| 300    | research           | 1.640          |
| 450    | research           | 3.558          |
| 600    | research           | 8.138          |
| 200    | line_art_a1        | 0.914          |
| 300    | line_art_a1        | 1.342          |
| 450    | line_art_a1        | 2.154          |
| 600    | line_art_a1        | 4.220          |

**Iteration 1 (already committed):** Vectorized `build_neighbor_table` → 1.11–1.38× speedup (average 1.24×).

---

## Attempted Optimizations

### ITERATION 2 — Checkerboard Parallel SA Kernel ❌ FAILED

**Hypothesis:** Process board in 4 color classes where cells within each class are non-interfering (Chebyshev distance ≥ 2). Use `prange` to parallelize within each color class for SIMD vectorization.

**Implementation:**
- Added `_sa_kernel_cb` in `sa.py` with checkerboard coloring
- Pre-computed 4 color classes outside @njit
- Converted iteration count to sweep count with adjusted temperature schedule
- Modified `run_iter9.py` to use checkerboard kernel

**Test Result (200/line_art_a1):**
- **Baseline (with iter1):** 0.822s
- **With checkerboard SA:** 2.517s (pipeline time, excluding warmup)
- **Result:** **3.06× SLOWDOWN**

**Root Cause:**
1. On 1-CPU machine with `numba_threads=1`, `prange` adds overhead without providing parallelism benefit
2. Scattered memory access pattern (processing all cells in one color class) destroys cache locality
3. The sequential SA kernel's linear traversal has better cache behavior

**Verdict:** REVERTED

---

### ITERATION 3 — Fast BFS Unknown Detector in fast_seal_repair ❌ FAILED

**Hypothesis:** Replace `solve_board` calls in `fast_seal_repair` with a Numba-compiled BFS that does only flood-fill and 3 rounds of basic propagation (no subset). Expected 10-30× faster per pass.

**Implementation:**
- Added `_detect_unknowns_bfs` in `solver.py` with @njit
- Added `solve_board_fast` wrapper returning minimal `SolveResult`
- Modified `run_fast_seal_repair` to use `solve_board_fast`

**Test Result (600/research):**
- **Baseline:** 8.138s total, n_unknown=0 (solved)
- **With Fast BFS:** 62.15s total, n_unknown=2300 (NOT solved)
- **Result:** **7.64× SLOWDOWN**

**Root Cause:**
1. Fast BFS with only 3 propagation rounds is insufficient for complex images
2. Board left unsolved (n_unknown=2300) triggered expensive downstream repairs:
   - phase1_repair: 11.4s (vs negligible in baseline)
   - late_stage_routing: 33.8s (vs negligible in baseline)
3. Fast approximation broke quality guarantee, causing massive cascading costs

**Verdict:** REVERTED

---

### ITERATION 4 — Greedy Mine Initialization + SA Iteration Reduction ❌ FAILED

**Hypothesis:** Initialize mines at highest-target cells (greedy) instead of random. SA starts closer to optimal, enabling iteration reduction without quality loss.

**Implementation:**
- Modified coarse SA init in `run_iter9.py` to sort cells by target value descending and place mines at top N
- Reduced SA iterations by 2×: 18M → 9M total

**Test Result (600/research):**
- **Baseline:** 8.138s, n_unknown=0
- **With Greedy Init + 2× SA reduction:** 5.21s, n_unknown=595
- **Result:** 1.56× faster BUT **QUALITY REGRESSION** (n_unknown > 0)

**Regression Gate:** FAILED
- Baseline n_unknown: 0
- Current n_unknown: 595
- Gate requirement: n_unknown ≤ baseline → FAIL

**Also Tried:**
- 1.5× SA reduction: n_unknown=848 (WORSE than 2×)
- Greedy init paradoxically produces worse quality than random init

**Root Cause:**
1. Greedy init creates a biased starting point that's locally optimal but harder for SA to escape from
2. Random init provides better exploration diversity
3. Even with better init, 2× SA reduction insufficient for research/600 complexity

**Verdict:** REVERTED

---

## Why 10× Is Not Achievable on This Machine

After systematically attempting all planned optimizations:

### 1. **Single-CPU Constraint**
- `cpu_count = 1`, `numba_threads = 1`
- Parallel SA approaches (checkerboard, multi-chain) add overhead without benefit
- No parallelism to exploit

### 2. **Profiler-Identified Bottlenecks Exhausted**
- **build_neighbor_table**: Fixed in Iter1 (14.5× faster) ✓
- **_sa_kernel**: Attempted checkerboard parallelization → 3× SLOWDOWN ✗
- **fast_seal_repair**: Attempted Fast BFS → 7.6× SLOWDOWN ✗
- **scipy correlate**: Already at C speed, no room for improvement
- **CSP solver**: Already compiled with Numba, fast per-call

### 3. **Quality vs. Speed Tradeoff**
- Fast approximations (Fast BFS, reduced iterations) break quality guarantees
- Quality regressions trigger expensive downstream repairs that negate any gains
- The problem requires the full solver complexity to maintain quality

### 4. **Algorithmic Limits**
- SA iteration reduction blocked by research/600's sealed cluster density
- Greedy initialization counterproductively biases the search space
- No remaining algorithmic opportunities identified

---

## Path to 10× (What Would Be Required)

The 10× target would require one or more of:

1. **Multi-core Hardware** (≥8 CPUs): parallel SA chains → 4-8× speedup
2. **GPU Acceleration**: CUDA SA kernel → 50-100× on SA phases
3. **Algorithmic Breakthrough**: fundamentally different approach (not found in this campaign)
4. **Relaxed Quality Requirements**: allow higher n_unknown thresholds (violates regression gate)

---

## All Attempted Approaches

| Iteration | Approach | Expected Gain | Measured Result | Status | Failure Reason |
|-----------|----------|---------------|-----------------|--------|----------------|
| 1 | Vectorize `build_neighbor_table` | ~1.1-1.4× | **1.11-1.38×** | **ACCEPTED** | — |
| 2 | Checkerboard Parallel SA | 2-4× | **3× SLOWDOWN** | REVERTED | prange overhead, poor cache locality on 1-CPU |
| 3 | Fast BFS in fast_seal | 5-10× | **7.6× SLOWDOWN** | REVERTED | Incomplete solve → expensive downstream repairs |
| 4 | Greedy Init + 2× SA reduction | Enable SA reduction | n_unknown=595 **REGRESSION** | REVERTED | Greedy init worse than random; research/600 requires full iterations |
| 4b | Greedy Init + 1.5× SA reduction | Less aggressive | n_unknown=848 **WORSE** | REVERTED | Even worse quality and performance |

---

## Final Best Result

**Iteration 1 only (vectorized `build_neighbor_table`):**

| boardw | image              | baseline_avg_s | final_avg_s | speedup   |
|--------|--------------------|----------------|-------------|-----------|
| 200    | input_source_image | 1.102          | 0.910       | **1.21×** |
| 300    | input_source_image | 1.751          | 1.431       | **1.22×** |
| 450    | input_source_image | 2.907          | 2.225       | **1.31×** |
| 600    | input_source_image | 4.186          | 3.022       | **1.38×** |
| 200    | research           | 1.085          | 0.959       | **1.13×** |
| 300    | research           | 1.640          | 1.359       | **1.21×** |
| 450    | research           | 3.558          | 2.912       | **1.22×** |
| 600    | research           | 8.138          | 6.704       | **1.21×** |
| 200    | line_art_a1        | 0.914          | 0.822       | **1.11×** |
| 300    | line_art_a1        | 1.342          | 1.099       | **1.22×** |
| 450    | line_art_a1        | 2.154          | 1.618       | **1.33×** |
| 600    | line_art_a1        | 4.220          | 3.265       | **1.29×** |

**Average speedup: 1.24×**

---

## Remaining Gap

- **Target:** 10× speedup
- **Achieved:** 1.24× speedup
- **Gap:** Need ~8× more reduction from current state
- **Assessment:** Gap cannot be closed on this hardware with profiler-identified optimizations

---

## Conclusion

The 10× speedup target is **not achievable** on this 1-CPU machine using the profiler-identified optimization approaches. All major attempts resulted in either severe performance degradation or quality regressions. The best achievable result is **1.24× average speedup** from vectorizing `build_neighbor_table` (Iteration 1, already committed).

Further speedup would require hardware changes (multi-core CPU, GPU) or algorithmic breakthroughs beyond the scope of standard optimization techniques.
