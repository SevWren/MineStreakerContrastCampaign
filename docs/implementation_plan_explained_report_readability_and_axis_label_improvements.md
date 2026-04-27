# Implementation Plan: Explained Report Readability and Axis Label Improvements

## 1. Purpose of This Plan

This plan modifies the beginner-facing explained report PNGs so a non-expert can understand the report without knowing Mine-Streaker internals.

The changes are limited to report readability, chart labeling, plain-English copy, tests, and documentation. They must not change mine generation, solver behavior, repair behavior, benchmark routing, artifact filenames, or technical PNG audit behavior.

The required user-facing problem comes from the attached annotated report image and the attached planning prompt, which requires beginner-friendly explanations for target values, generated number values, difference values, solver colors, weighted loss, iteration-axis meaning, and higher/lower chart values. 

## 2. Inputs Reviewed

| Input                           | Reviewed Content                                                                                                                             | Plan Use                                         |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------ |
| Attached annotated report image | Visual report titled `Benchmark explained report 300x300 seed=11`, with red review comments pointing at colorbars and the optimization chart | Source of product requirements                   |
| `digest.txt`                    | Repository file listing, active runtime modules, report rendering code, run entry points, tests, and docs                                    | Source of implementation targets                 |
| `Pasted markdown.md`            | Required plan structure, required tests, required behavior preservation, and forbidden ambiguity rules                                       | Source of final plan format and acceptance scope |

The repository contains `report.py`, `run_iter9.py`, `run_benchmark.py`, `pipeline.py`, `README.md`, `AGENTS.md`, `docs/`, and report-related tests under `tests/`, including `tests/test_report_explanations.py` and `tests/test_benchmark_layout.py`. 

## 3. User Comments Extracted From the Attached Image

| Requirement ID | User Comment                                                                                                  | Image Location                                                          | Affected Report Element                                            | Beginner Problem                                                                                                                                                              |
| -------------- | ------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| REQ-001        | “This axis needs a descriptive label and explanation of values”                                               | Top-left red box pointing to the target image colorbar                  | `Target image` colorbar showing values `0` through `8`             | The numeric colorbar has no plain-language meaning. A beginner does not know that `0` means background and `8` means strongest source-image line area.                        |
| REQ-002        | “This axis needs a descriptive label and explanation of values”                                               | Top-right red box pointing to the generated number field colorbar       | `Generated number field` colorbar showing values `0` through `8`   | The report does not explain that these are Minesweeper numbers caused by mine placement.                                                                                      |
| REQ-003        | “This axis needs a descriptive label and explanation of values”                                               | Middle-left red box pointing to the difference-from-target colorbar     | `Difference from target` colorbar showing values `0` through `4.0` | The report does not explain that `0` means exact match and larger values mean larger visual mismatch.                                                                         |
| REQ-004        | `"Weighted loss" has 4 indicators by no indication of their values. "Weighted Loss" is too technical/complex` | Center red box pointing at the optimization progress chart              | `Optimization progress` chart y-axis label `Weighted loss`         | “Weighted loss” is optimizer jargon. The chart does not tell a beginner what the value means or whether lower/higher is better.                                               |
| REQ-005        | Same red box: “has 4 indicators by no indication of their values”                                             | Center red box arrows pointing to chart axis/line indicators            | `Optimization progress` chart tick/line/axis markings              | The chart contains visible marks and a plotted curve without readable beginner labels, numeric value callouts, or legend meaning.                                             |
| REQ-006        | `"x50k iterations" needs some type of relatable time element to ground the user in reality`                   | Bottom red box pointing at x-axis                                       | `Optimization progress` x-axis label `x50k iterations`             | `x50k iterations` is not relatable. A beginner needs to know that each point represents 50,000 attempted mine-layout changes and that this is optimizer work, not clock time. |
| REQ-007        | Implied by all red comments and existing right-side text                                                      | Right-side “What these panels mean” and “How to read the results” boxes | Existing explanatory copy                                          | The explanatory boxes do not explain the colorbars or the optimization chart enough for a non-expert.                                                                         |
| REQ-008        | Implied by the screenshot layout                                                                              | All explained-report panels                                             | Overall beginner readability                                       | The report mixes helpful prose with unlabeled technical axes, causing a mismatch between “explained report” intent and visual-detail clarity.                                 |

## 4. Current Codebase Findings

### 4.1 Active report-rendering files

| File                                | Confirmed Role                                                                                                                                                                                                                                       | Change Required                                                 |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| `report.py`                         | Owns technical and explained report rendering. It defines `render_report()`, `render_report_explained()`, `render_repair_overlay()`, `render_repair_overlay_explained()`, caption dictionaries, summary text helpers, and Matplotlib layout helpers. | Yes                                                             |
| `run_iter9.py`                      | Main current pipeline entry point. It imports `render_report`, `render_report_explained`, `render_repair_overlay`, and `render_repair_overlay_explained`, then writes both technical and explained final/overlay reports.                            | Yes, only to pass runtime context into explained report metrics |
| `run_benchmark.py`                  | Benchmark entry point. It imports the same report functions and writes child-run technical and explained reports.                                                                                                                                    | Yes, only to pass runtime context into explained report metrics |
| `pipeline.py`                       | Legacy `run_board()` path calls `render_report()` only, not `render_report_explained()`.                                                                                                                                                             | No readability change required                                  |
| `README.md`                         | Documents technical PNGs, explained PNGs, metrics, generated artifacts, and beginner workflow.                                                                                                                                                       | Yes                                                             |
| `AGENTS.md`                         | States visual artifact guidance: technical PNGs are detailed audit/debug views; explained PNGs are first-look review artifacts.                                                                                                                      | No required change                                              |
| `tests/test_report_explanations.py` | Tests plain-English report summaries, caption dictionaries, and that `render_report_explained()` writes a non-empty PNG.                                                                                                                             | Yes                                                             |
| `tests/test_benchmark_layout.py`    | Tests benchmark child directory names, preserved artifact filenames, and child metrics document explained-artifact hints.                                                                                                                            | Yes                                                             |

### 4.2 Current explained final report behavior in `report.py`

`render_report_explained()` currently:

1. Renders `Target image` with `imshow(..., vmin=0, vmax=8)` and an unlabeled colorbar.
2. Renders `Generated mine layout` without a colorbar.
3. Renders `Generated number field` with `imshow(..., vmin=0, vmax=8)` and an unlabeled colorbar.
4. Renders `Difference from target` with `imshow(..., vmin=0, vmax=4)` and an unlabeled colorbar.
5. Renders `Solver result` with a legend for revealed, flagged, and unknown cells.
6. Renders `Optimization progress` using `ax_history.semilogy(hist)`.
7. Labels the optimization x-axis as `x50k iterations`.
8. Labels the optimization y-axis as `Weighted loss`.
9. Adds explanatory text for target image, generated number field, solver result, and difference view.
10. Does not include the mine-layout panel caption in the right-side panel explanation.
11. Does not include the optimization-progress caption in the right-side panel explanation.
12. Hides ticks for `ax_history` in the same loop that hides ticks for image panels.

The current chart label strings and colorbar calls appear directly in `report.py`: `plt.colorbar(im_target...)`, `plt.colorbar(im_numbers...)`, `plt.colorbar(im_error...)`, `ax_history.set_xlabel("x50k iterations")`, and `ax_history.set_ylabel("Weighted loss")`. The digest search confirms those exact current labels and calls. 

### 4.3 Current technical report behavior in `report.py`

`render_report()` currently uses the technical labels:

```text
Loss curve (log)
x50k iters
Weighted loss
```

This behavior is suitable for audit/debug output and must remain unchanged.

### 4.4 Current runtime metrics passed into explained reports

Both `run_iter9.py` and `run_benchmark.py` build a `render_metrics` dictionary for explained report rendering. The current `render_metrics` dictionaries include:

```text
run_id
board
board_width
board_height
seed
source_image.name
source_image.project_relative_path
repair_route_selected
coverage
solvable
mine_accuracy
n_unknown
mean_abs_error
mine_density
before_unknown
after_unknown
removed_mines
added_mines
solved_after
```

`run_benchmark.py` already has `duration_s` available before report rendering and later writes it as `total_time_s`. 
`run_iter9.py` currently computes `duration_wall_s` after report rendering, then writes `total_time_s` into final metrics. 

## 5. Requirement-to-Code Mapping

| Requirement ID | Exact File                                   | Exact Function/Class/Block                                                          | Current Behavior                                                                                 | Required Change                                                                                                                           | Verification                                                                                 |
| -------------- | -------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| REQ-001        | `report.py`                                  | `render_report_explained()` target-image colorbar block                             | Calls `plt.colorbar(im_target, ...)` with no label                                               | Replace direct colorbar call with `_add_explained_colorbar(..., label=EXPLAINED_COLORBAR_LABELS["target"], ticks=[0,2,4,6,8])`            | Unit test checks target colorbar label text and caption copy                                 |
| REQ-001        | `report.py`                                  | `REPORT_PANEL_CAPTIONS["target_image"]` and explained caption list                  | Says values are from `0` to `8` but does not explain endpoints                                   | Add exact endpoint explanation text from Section 8                                                                                        | Unit test checks `0 means background` and `8 means strongest line` appear                    |
| REQ-002        | `report.py`                                  | `render_report_explained()` number-field colorbar block                             | Calls `plt.colorbar(im_numbers, ...)` with no label                                              | Replace direct colorbar call with `_add_explained_colorbar(..., label=EXPLAINED_COLORBAR_LABELS["number_field"], ticks=[0,2,4,6,8])`      | Unit test checks number-field colorbar label text                                            |
| REQ-002        | `report.py`                                  | `REPORT_PANEL_CAPTIONS["number_field"]` and explained caption list                  | Describes generated numbers but not 0–8 meaning                                                  | Add exact endpoint explanation text from Section 8                                                                                        | Unit test checks `0 means no touching mines` and `8 means surrounded by mines`               |
| REQ-003        | `report.py`                                  | `render_report_explained()` error colorbar block                                    | Calls `plt.colorbar(im_error, ...)` with no label                                                | Replace direct colorbar call with `_add_explained_colorbar(..., label=EXPLAINED_COLORBAR_LABELS["error_map"], ticks=[0,1,2,3,4])`         | Unit test checks difference colorbar label and explanation                                   |
| REQ-003        | `report.py`                                  | `REPORT_PANEL_CAPTIONS["error_map"]` and explained caption list                     | Says brighter areas deserve review, but not what values mean                                     | Add exact endpoint explanation text from Section 8                                                                                        | Unit test checks `0 means exact match` and `4 or more means large mismatch`                  |
| REQ-004        | `report.py`                                  | `render_report_explained()` history chart block                                     | Uses title `Optimization progress`, y-label `Weighted loss`                                      | Replace explained-report y-label with `Match error score (lower is better)` and add caption that explains the score                       | Unit test checks explained chart does not contain `Weighted loss`                            |
| REQ-005        | `report.py`                                  | New helper `_plot_explained_optimization_progress()`                                | One plotted curve appears without legend, final value, or beginner note                          | Plot one named line only, add legend `Match error score`, keep numeric tick labels visible, add final-score callout                       | Unit test checks legend text, final-score annotation, and visible axis label strings         |
| REQ-006        | `report.py`                                  | New helper `_plot_explained_optimization_progress()`                                | x-label is `x50k iterations`                                                                     | Replace with `Optimizer work (50,000 attempted mine changes per point)` and add runtime note when a runtime metric is present             | Unit test checks exact x-label text                                                          |
| REQ-006        | `run_benchmark.py`                           | `render_metrics` construction in `run_normal_child()`                               | `duration_s` exists but is not passed into `render_report_explained()`                           | Add `"total_time_s": float(duration_s)` to `render_metrics` before render calls                                                           | Unit test checks benchmark render metrics include runtime field through helper-level fixture |
| REQ-006        | `run_iter9.py`                               | `render_metrics` construction before `_atomic_render(render_report_explained, ...)` | Final `total_time_s` is computed after rendering                                                 | Add `"runtime_before_report_s": float(time.perf_counter() - started_wall)` to `render_metrics`; do not alter final metrics `total_time_s` | Unit test checks runtime text helper handles `runtime_before_report_s`                       |
| REQ-007        | `report.py`                                  | `caption_lines` in `render_report_explained()`                                      | Caption list omits generated mine layout and optimization chart                                  | Add lines for `Generated mine layout` and `Optimizer progress`                                                                            | Unit test checks caption list covers every visible panel                                     |
| REQ-008        | `README.md`                                  | Generated artifacts / beginner workflow / new explained report guide section        | Docs identify explained PNGs but do not document colorbar meanings or optimization chart wording | Add a short “How to read explained report PNGs” section with the exact Section 8 meanings                                                 | Documentation review and grep checks                                                         |
| REQ-008        | `docs/explained_report_artifact_contract.md` | New doc                                                                             | No dedicated contract for explained-report readability                                           | Add a contract document defining explained vs technical report language, colorbar labels, and chart semantics                             | Documentation review and DOCS_INDEX entry                                                    |

## 6. Required Behavior Changes

### 6.1 Explained Report Only

Modify only beginner/human-friendly explained PNG behavior:

1. `render_report_explained()` target colorbar receives a vertical label:

   ```text
   Target value: 0 background → 8 strongest line
   ```

2. `render_report_explained()` generated number field colorbar receives a vertical label:

   ```text
   Generated number: 0 no nearby mines → 8 surrounded
   ```

3. `render_report_explained()` difference colorbar receives a vertical label:

   ```text
   Difference: 0 match → 4+ large mismatch
   ```

4. The right-side “What these panels mean” box includes one explanation line for each visible panel:

   * Target image
   * Generated mine layout
   * Generated number field
   * Difference from target
   * Solver result
   * Optimizer progress

5. The explained optimization chart changes from technical optimizer jargon to beginner-readable chart language:

   * Chart title:

     ```text
     Optimizer progress: lower is better
     ```
   * X-axis:

     ```text
     Optimizer work (50,000 attempted mine changes per point)
     ```
   * Y-axis:

     ```text
     Match error score (lower is better)
     ```
   * Legend:

     ```text
     Match error score
     ```
   * Final callout:

     ```text
     Final score: <formatted value>
     ```

6. `ax_history` must not be included in the tick-hiding loop. Numeric axis ticks must remain visible on the optimization chart.

7. `render_repair_overlay_explained()` must use the same helper for its target-image colorbar and visual-change colorbar. This keeps explained overlay artifacts aligned with the explained-report readability contract.

### 6.2 Technical Report Preservation

Do not change these technical report behaviors:

1. `render_report()` title strings remain:

   ```text
   Target T [0-8]
   Number Field N
   |N-T| mean=<value>
   Loss curve (log)
   ```

2. `render_report()` optimization labels remain:

   ```text
   x50k iters
   Weighted loss
   ```

3. `render_repair_overlay()` technical colorbars and labels remain unchanged.

4. Technical PNG artifact filenames remain unchanged:

   * Iter9: `iter9_<board>_FINAL.png`
   * Benchmark: `visual_<board>.png`
   * Repair overlay: `repair_overlay_<board>.png`

### 6.3 Shared Helper Changes

Add helpers in `report.py` used by explained report paths only:

```python
EXPLAINED_HISTORY_SAMPLE_INTERVAL = 50_000
EXPLAINED_COLORBAR_LABELS = {...}
EXPLAINED_VALUE_EXPLANATIONS = {...}
TECHNICAL_HISTORY_X_LABEL = "x50k iters"
TECHNICAL_HISTORY_Y_LABEL = "Weighted loss"

def _add_explained_colorbar(...): ...
def _format_duration(seconds: float | int | None) -> str | None: ...
def _runtime_context_line(metrics: dict) -> str | None: ...
def _plot_explained_optimization_progress(ax, hist: np.ndarray, metrics: dict) -> None: ...
```

`TECHNICAL_HISTORY_X_LABEL` and `TECHNICAL_HISTORY_Y_LABEL` are used only by `render_report()` to lock existing technical wording through tests.

## 7. File-by-File Implementation Plan

### File: `report.py`

#### Current responsibility

`report.py` owns all Matplotlib report rendering and report copy. It renders both technical PNGs and explained PNGs.

#### Required changes

Add explained-report-specific colorbar labels, colorbar value explanations, beginner-readable optimization chart text, runtime/iteration grounding copy, and tests-facing helper constants.

#### Exact functions/classes/blocks to modify

* `REPORT_PANEL_CAPTIONS`
* New constants directly below caption dictionaries
* New helper `_add_explained_colorbar()`
* New helper `_format_duration()`
* New helper `_runtime_context_line()`
* New helper `_plot_explained_optimization_progress()`
* `render_report()`
* `render_report_explained()`
* `render_repair_overlay_explained()`

#### Step-by-step code changes

1. Add these constants below `_FOOTER_WRAP_WIDTH`:

   ```python
   EXPLAINED_HISTORY_SAMPLE_INTERVAL = 50_000
   TECHNICAL_HISTORY_X_LABEL = "x50k iters"
   TECHNICAL_HISTORY_Y_LABEL = "Weighted loss"

   EXPLAINED_COLORBAR_LABELS = {
       "target_image": "Target value: 0 background → 8 strongest line",
       "number_field": "Generated number: 0 no nearby mines → 8 surrounded",
       "error_map": "Difference: 0 match → 4+ large mismatch",
       "repair_error_delta": "Visual change: negative better → positive worse",
   }

   EXPLAINED_VALUE_EXPLANATIONS = {
       "target_image": "Target values: 0 means background. 8 means the strongest line area from the source image.",
       "number_field": "Generated number values: 0 means a safe cell has no touching mines. 8 means a safe cell is surrounded by mines.",
       "error_map": "Difference values: 0 means the generated number matched the target at that cell. Higher values mean a larger visual mismatch. 4 or more means a large mismatch.",
       "mine_grid": "Generated mine layout: white cells are safe cells. Black cells are mines.",
       "solver_result": "Solver result colors: gray means revealed safe cells, orange means flagged mines, and blue means unresolved cells.",
       "loss_curve": "Optimizer progress: the line shows a match error score. Lower means the generated numbers are closer to the target image.",
       "history_axis": "Optimizer work: each plotted point is saved after 50,000 attempted mine changes. This axis is optimizer work, not clock time.",
   }
   ```

2. Replace `REPORT_PANEL_CAPTIONS["target_image"]`, `["number_field"]`, `["error_map"]`, `["loss_curve"]`, and `["mine_grid"]` with wording that matches the constants above. Keep `solver_result`, `distribution`, and `metrics` meanings intact unless the new solver color wording is appended.

3. Add `_add_explained_colorbar()`:

   ```python
   def _add_explained_colorbar(image, ax, label: str, *, ticks: list[float]) -> object:
       cbar = plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04, ticks=ticks)
       cbar.ax.set_ylabel(label, rotation=90, labelpad=9, fontsize=8)
       cbar.ax.tick_params(labelsize=8)
       return cbar
   ```

4. Add `_format_duration()`:

   ```python
   def _format_duration(seconds: float | int | None) -> str | None:
       if seconds is None:
           return None
       try:
           total = int(round(float(seconds)))
       except Exception:
           return None
       if total < 0:
           return None
       minutes, secs = divmod(total, 60)
       hours, minutes = divmod(minutes, 60)
       if hours:
           return f"about {hours} hr {minutes} min"
       if minutes:
           return f"about {minutes} min {secs} sec"
       return f"about {secs} sec"
   ```

5. Add `_runtime_context_line()`:

   ```python
   def _runtime_context_line(metrics: dict) -> str | None:
       duration = _format_duration(_coalesce(metrics.get("total_time_s"), metrics.get("runtime_before_report_s")))
       if duration:
           return f"Runtime context: this run took {duration} for the work recorded before this report image was written."
       return None
   ```

6. Add `_plot_explained_optimization_progress()`:

   ```python
   def _plot_explained_optimization_progress(ax, hist: np.ndarray, metrics: dict) -> None:
       if len(hist) > 1:
           x_work = np.arange(len(hist), dtype=np.int64) * EXPLAINED_HISTORY_SAMPLE_INTERVAL
           ax.semilogy(x_work, hist, label="Match error score")
           ax.set_title("Optimizer progress: lower is better", fontsize=12)
           ax.set_xlabel("Optimizer work (50,000 attempted mine changes per point)")
           ax.set_ylabel("Match error score (lower is better)")
           ax.legend(loc="best", fontsize=8)
           ax.tick_params(axis="both", labelsize=8)
           ax.annotate(
               f"Final score: {hist[-1]:.3g}",
               xy=(x_work[-1], hist[-1]),
               xytext=(0.58, 0.12),
               textcoords="axes fraction",
               fontsize=8,
               bbox=dict(boxstyle="round", facecolor="white", alpha=0.85),
               arrowprops=dict(arrowstyle="->", linewidth=0.8),
           )
           runtime_line = _runtime_context_line(metrics)
           note_lines = [EXPLAINED_VALUE_EXPLANATIONS["history_axis"]]
           if runtime_line:
               note_lines.append(runtime_line)
           ax.text(
               0.03,
               0.97,
               _wrap_lines(note_lines, 42),
               transform=ax.transAxes,
               va="top",
               ha="left",
               fontsize=8,
               bbox=dict(boxstyle="round", facecolor="white", alpha=0.82),
           )
       else:
           ax.text(
               0.5,
               0.5,
               "No optimization progress history was recorded for this run.",
               ha="center",
               va="center",
           )
           ax.set_title("Optimizer progress", fontsize=12)
           ax.set_xticks([])
           ax.set_yticks([])
   ```

7. Modify `render_report()` technical chart block to use technical constants without changing rendered text:

   ```python
   axes[1][2].set_xlabel(TECHNICAL_HISTORY_X_LABEL)
   axes[1][2].set_ylabel(TECHNICAL_HISTORY_Y_LABEL)
   ```

8. In `render_report_explained()`, replace:

   ```python
   plt.colorbar(im_target, ax=ax_target, fraction=0.046, pad=0.04)
   ```

   with:

   ```python
   _add_explained_colorbar(
       im_target,
       ax_target,
       EXPLAINED_COLORBAR_LABELS["target_image"],
       ticks=[0, 2, 4, 6, 8],
   )
   ```

9. In `render_report_explained()`, replace number-field colorbar call with:

   ```python
   _add_explained_colorbar(
       im_numbers,
       ax_numbers,
       EXPLAINED_COLORBAR_LABELS["number_field"],
       ticks=[0, 2, 4, 6, 8],
   )
   ```

10. In `render_report_explained()`, replace difference colorbar call with:

    ```python
    _add_explained_colorbar(
        im_error,
        ax_error,
        EXPLAINED_COLORBAR_LABELS["error_map"],
        ticks=[0, 1, 2, 3, 4],
    )
    ```

11. Replace the entire inline `ax_history.semilogy()` block in `render_report_explained()` with:

    ```python
    _plot_explained_optimization_progress(ax_history, hist, metrics)
    ```

12. Replace `caption_lines` in `render_report_explained()` with:

    ```python
    caption_lines = [
        EXPLAINED_VALUE_EXPLANATIONS["target_image"],
        EXPLAINED_VALUE_EXPLANATIONS["mine_grid"],
        EXPLAINED_VALUE_EXPLANATIONS["number_field"],
        EXPLAINED_VALUE_EXPLANATIONS["error_map"],
        EXPLAINED_VALUE_EXPLANATIONS["solver_result"],
        EXPLAINED_VALUE_EXPLANATIONS["loss_curve"],
        EXPLAINED_VALUE_EXPLANATIONS["history_axis"],
    ]
    runtime_line = _runtime_context_line(metrics)
    if runtime_line:
        caption_lines.append(runtime_line)
    ```

13. Change the tick-hiding loop in `render_report_explained()` from:

    ```python
    for axis in (ax_target, ax_grid, ax_numbers, ax_error, ax_solver, ax_history):
    ```

    to:

    ```python
    for axis in (ax_target, ax_grid, ax_numbers, ax_error, ax_solver):
    ```

14. In `render_repair_overlay_explained()`, replace target colorbar with `_add_explained_colorbar(..., EXPLAINED_COLORBAR_LABELS["target_image"], ticks=[0, 2, 4, 6, 8])`.

15. In `render_repair_overlay_explained()`, replace visual delta colorbar with `_add_explained_colorbar(..., EXPLAINED_COLORBAR_LABELS["repair_error_delta"], ticks=[-1.5, -0.75, 0, 0.75, 1.5])`.

16. Increase explained report layout spacing to prevent clipping:

    * Change `fig = plt.figure(figsize=(21, 14))` to `fig = plt.figure(figsize=(22, 14.5))`.
    * Change GridSpec `wspace=0.28` to `wspace=0.34`.
    * Keep `bbox_inches="tight"` in `plt.savefig()`.

#### Tests affected

* `tests/test_report_explanations.py`
* `tests/test_benchmark_layout.py`

#### Acceptance criteria

* Explained final PNGs have labeled target, generated-number, and difference colorbars.
* Explained final PNGs no longer show `Weighted loss`.
* Explained final PNGs no longer show `x50k iterations`.
* Explained optimization chart has a legend, visible numeric tick labels, and final-score callout.
* Technical report PNG labels remain unchanged.

### File: `run_iter9.py`

#### Current responsibility

Runs the main Iter9 pipeline and writes final technical/explained reports.

#### Required changes

Pass runtime context into explained report metrics before rendering.

#### Exact functions/classes/blocks to modify

* `main()`
* `render_metrics` dictionary built before `_atomic_render(...)`

#### Step-by-step code changes

1. Immediately before `render_metrics = { ... }`, add:

   ```python
   runtime_before_report_s = float(time.perf_counter() - started_wall)
   ```

2. Add this key to `render_metrics`:

   ```python
   "runtime_before_report_s": runtime_before_report_s,
   ```

3. Do not remove or rename the later final metrics field:

   ```python
   "total_time_s": float(duration_wall_s),
   ```

4. Do not reorder artifact rendering, metrics writing, or artifact inventory construction.

#### Tests affected

* `tests/test_report_explanations.py`

#### Acceptance criteria

* `render_report_explained()` can display runtime context for Iter9 without changing final JSON schema.
* Existing final `total_time_s` remains in metrics.
* Existing Iter9 artifact names remain unchanged.

### File: `run_benchmark.py`

#### Current responsibility

Runs normal benchmark child runs and writes technical/explained reports plus benchmark summaries.

#### Required changes

Pass existing benchmark runtime context into explained report metrics.

#### Exact functions/classes/blocks to modify

* `run_normal_child()`
* `render_metrics` dictionary built before `_atomic_render(...)`

#### Step-by-step code changes

1. In the existing `render_metrics` dictionary, add:

   ```python
   "total_time_s": float(duration_s),
   ```

2. Do not change `benchmark_child_artifact_filenames()`.

3. Do not change benchmark child directory naming.

4. Do not change benchmark summary rows or aggregate metrics.

#### Tests affected

* `tests/test_benchmark_layout.py`
* `tests/test_report_explanations.py`

#### Acceptance criteria

* Benchmark explained reports can show runtime context.
* `visual_<board>_explained.png` filename remains unchanged.
* Existing benchmark summary files remain unchanged.

### File: `tests/test_report_explanations.py`

#### Current responsibility

Tests plain-English summary helpers, caption dictionaries, and render smoke behavior.

#### Required changes

Add tests for colorbar labels, value explanations, optimization chart language, technical label preservation, and runtime formatting.

#### Exact functions/classes/blocks to modify

* Imports at top of file
* `ReportExplanationTests`

#### Step-by-step code changes

1. Import these new helpers/constants from `report.py`:

   ```python
   EXPLAINED_COLORBAR_LABELS
   EXPLAINED_VALUE_EXPLANATIONS
   TECHNICAL_HISTORY_X_LABEL
   TECHNICAL_HISTORY_Y_LABEL
   _add_explained_colorbar
   _format_duration
   _plot_explained_optimization_progress
   ```

2. Add test:

   ```python
   def test_explained_colorbar_labels_are_beginner_readable(self):
   ```

   Required assertions:

   * target label contains `Target value`
   * target label contains `0 background`
   * target label contains `8 strongest line`
   * number label contains `Generated number`
   * number label contains `0 no nearby mines`
   * number label contains `8 surrounded`
   * error label contains `Difference`
   * error label contains `0 match`
   * error label contains `4+ large mismatch`

3. Add test:

   ```python
   def test_explained_value_explanations_define_zero_and_high_values(self):
   ```

   Required assertions:

   * target explanation contains `0 means background`
   * target explanation contains `8 means the strongest line area`
   * number explanation contains `0 means a safe cell has no touching mines`
   * number explanation contains `8 means a safe cell is surrounded by mines`
   * difference explanation contains `0 means the generated number matched`
   * difference explanation contains `4 or more means a large mismatch`

4. Add test:

   ```python
   def test_add_explained_colorbar_sets_label_and_ticks(self):
   ```

   Required assertions:

   * Create a small Matplotlib figure and image.
   * Call `_add_explained_colorbar(...)`.
   * Assert `cbar.ax.get_ylabel()` equals the passed label.
   * Assert tick labels are present.

5. Add test:

   ```python
   def test_explained_optimization_progress_uses_beginner_labels(self):
   ```

   Required assertions:

   * Call `_plot_explained_optimization_progress()` with `hist=np.array([100.0, 50.0, 25.0])`.
   * Assert title contains `lower is better`.
   * Assert x-label equals `Optimizer work (50,000 attempted mine changes per point)`.
   * Assert y-label equals `Match error score (lower is better)`.
   * Assert legend contains `Match error score`.
   * Assert no axis title, x-label, y-label, legend text, or annotation text contains `Weighted loss`.
   * Assert no axis title, x-label, y-label, legend text, or annotation text contains `x50k`.

6. Add test:

   ```python
   def test_format_duration_outputs_plain_english(self):
   ```

   Required assertions:

   * `_format_duration(12)` returns `about 12 sec`
   * `_format_duration(75)` returns `about 1 min 15 sec`
   * `_format_duration(3660)` returns `about 1 hr 1 min`

7. Add test:

   ```python
   def test_technical_history_labels_are_preserved(self):
   ```

   Required assertions:

   * `TECHNICAL_HISTORY_X_LABEL == "x50k iters"`
   * `TECHNICAL_HISTORY_Y_LABEL == "Weighted loss"`

8. Extend `test_caption_dictionaries_are_complete()` so `REPORT_PANEL_CAPTIONS["loss_curve"]` and `EXPLAINED_VALUE_EXPLANATIONS["loss_curve"]` contain `lower`.

#### Tests affected

This file is directly modified.

#### Acceptance criteria

* Tests prove all explained-report copy requirements exist.
* Tests prove technical chart labels remain available and unchanged.

### File: `tests/test_benchmark_layout.py`

#### Current responsibility

Tests benchmark artifact names and benchmark metrics document explained artifact hints.

#### Required changes

Add a lightweight assertion that benchmark explained reports use the shared explained renderer and preserve explained artifact filenames.

#### Exact functions/classes/blocks to modify

* Imports from `run_benchmark`
* `BenchmarkLayoutTests`

#### Step-by-step code changes

1. Add import:

   ```python
   import run_benchmark
   import report
   ```

2. Add test:

   ```python
   def test_benchmark_uses_shared_explained_report_renderer(self):
   ```

   Required assertions:

   * `run_benchmark.render_report_explained is report.render_report_explained`
   * `run_benchmark.render_repair_overlay_explained is report.render_repair_overlay_explained`

3. Keep `test_preserved_child_artifact_filenames()` unchanged except for no functional changes. It already asserts `visual_<board>_explained.png`.

#### Tests affected

This file is directly modified.

#### Acceptance criteria

* Benchmark path is proven to use the same explained renderer as Iter9.
* Benchmark explained artifact filenames remain locked.

### File: `README.md`

#### Current responsibility

Documents project purpose, beginner workflow, metrics, generated artifacts, and report files.

#### Required changes

Add a beginner section explaining the improved explained-report PNG language.

#### Exact functions/classes/blocks to modify

* Add section after “Generated Artifacts to expect”
* Add one cross-reference in “Beginner Workflow” Step 3

#### Step-by-step code changes

1. In “Beginner Workflow” Step 3, change the “Start with” line from:

   ```text
   iter9_<board>_FINAL.png
   metrics_iter9_<board>.json
   ```

   to:

   ```text
   iter9_<board>_FINAL_explained.png
   iter9_<board>_FINAL.png
   metrics_iter9_<board>.json
   ```

2. Add new section:

   ```markdown
   ## How to Read Explained Report PNGs

   Explained PNGs are the first file to open when you want a human-readable overview.

   | Report element | Meaning |
   |---|---|
   | Target value colorbar | `0` means background. `8` means the strongest line area from the source image. |
   | Generated number colorbar | `0` means a safe cell has no touching mines. `8` means a safe cell is surrounded by mines. |
   | Difference colorbar | `0` means the generated number matched the target. Higher values mean a larger visual mismatch. `4+` means a large mismatch. |
   | Solver colors | Gray means revealed safe cells. Orange means flagged mines. Blue means unresolved cells. |
   | Optimizer progress | Lower is better. Each point is saved after 50,000 attempted mine changes. This axis shows optimizer work, not clock time. |
   ```

#### Tests affected

No automated README test exists in the current digest. Manual review and grep validation required.

#### Acceptance criteria

* README explains every value range called out in the annotated image.
* README directs beginners to open explained PNGs first.

### File: `docs/explained_report_artifact_contract.md`

#### Current responsibility

New document.

#### Required changes

Create a dedicated artifact contract for explained report readability.

#### Exact functions/classes/blocks to modify

New file.

#### Step-by-step code changes

Create file with this structure:

```markdown
# Explained Report Artifact Contract

## Purpose

## Scope

## Explained Final Report Required Labels

## Explained Repair Overlay Required Labels

## Optimization Progress Wording

## Technical Report Preservation

## Required Tests

## Backward Compatibility
```

Required content summary:

* Explained reports must avoid unexplained optimizer jargon.
* Explained colorbars must have labels and endpoint explanations.
* `Weighted loss` remains allowed in technical PNGs.
* `x50k iters` remains allowed in technical PNGs.
* Explained chart x-axis must explain 50,000 attempted mine changes per point.
* Explained chart must say lower is better.
* Artifact filenames must not change.

#### Tests affected

No direct automated doc test exists. Add DOCS_INDEX entry.

#### Acceptance criteria

* Document exists under `docs/`.
* Document matches implemented labels from `report.py`.

### File: `docs/DOCS_INDEX.md`

#### Current responsibility

Indexes active documentation.

#### Required changes

Add the new explained report artifact contract.

#### Exact functions/classes/blocks to modify

* Existing docs index list/table

#### Step-by-step code changes

Add one entry:

```markdown
- `docs/explained_report_artifact_contract.md` — Contract for beginner-readable explained report PNG labels, colorbar explanations, and optimization chart wording.
```

#### Tests affected

No direct automated docs index test exists. Manual review required.

#### Acceptance criteria

* New doc is discoverable from docs index.

## 8. Exact Text and Label Copy to Add

### 8.1 Colorbar labels

```text
Target value: 0 background → 8 strongest line
Generated number: 0 no nearby mines → 8 surrounded
Difference: 0 match → 4+ large mismatch
Visual change: negative better → positive worse
```

### 8.2 Panel explanation text

```text
Target values: 0 means background. 8 means the strongest line area from the source image.

Generated mine layout: white cells are safe cells. Black cells are mines.

Generated number values: 0 means a safe cell has no touching mines. 8 means a safe cell is surrounded by mines.

Difference values: 0 means the generated number matched the target at that cell. Higher values mean a larger visual mismatch. 4 or more means a large mismatch.

Solver result colors: gray means revealed safe cells, orange means flagged mines, and blue means unresolved cells.

Optimizer progress: the line shows a match error score. Lower means the generated numbers are closer to the target image.

Optimizer work: each plotted point is saved after 50,000 attempted mine changes. This axis is optimizer work, not clock time.
```

### 8.3 Optimization chart copy

```text
Optimizer progress: lower is better
Optimizer work (50,000 attempted mine changes per point)
Match error score (lower is better)
Match error score
Final score: <value>
```

### 8.4 Runtime text

When `total_time_s` or `runtime_before_report_s` is available:

```text
Runtime context: this run took about <duration> for the work recorded before this report image was written.
```

When no runtime field is available:

```text
No runtime sentence is shown. The optimization-axis note still explains that each point is 50,000 attempted mine changes.
```

### 8.5 Technical-report copy that must remain unchanged

```text
x50k iters
Weighted loss
Loss curve (log)
```

## 9. Plot and Layout Changes

### 9.1 Weighted-loss chart decision

Do not keep `Weighted loss` in explained reports.

Replace the explained chart with a beginner-readable optimizer-progress chart that still plots the same `hist` values from the same `history` input. This preserves technical correctness while removing unexplained jargon.

### 9.2 Indicators and values

The explained chart must show:

1. One plotted line only.
2. Legend label:

   ```text
   Match error score
   ```
3. Visible x-axis tick labels.
4. Visible y-axis tick labels.
5. Final value annotation:

   ```text
   Final score: <value>
   ```
6. Text note explaining:

   ```text
   Each plotted point is saved after 50,000 attempted mine changes.
   ```

### 9.3 X-axis conversion

Replace:

```text
x50k iterations
```

with:

```text
Optimizer work (50,000 attempted mine changes per point)
```

The x-values should be plotted as:

```python
x_work = np.arange(len(hist), dtype=np.int64) * 50_000
```

This means the axis values represent attempted mine changes directly, not opaque checkpoint counts.

### 9.4 Y-axis conversion

Replace:

```text
Weighted loss
```

with:

```text
Match error score (lower is better)
```

Keep `semilogy()` because the score range can vary by large factors. The plain-English title and axis label explain the meaning.

### 9.5 Colorbar layout

Each explained colorbar must:

* have a vertical label,
* use small readable font size `8`,
* keep numeric ticks,
* use explicit tick locations,
* avoid clipping through larger figure width and wider GridSpec spacing.

### 9.6 Tick-hiding correction

Do not hide ticks on `ax_history`.

Keep tick hiding only for image-like panels:

```python
for axis in (ax_target, ax_grid, ax_numbers, ax_error, ax_solver):
    axis.set_xticks([])
    axis.set_yticks([])
```

### 9.7 Report readability

Keep the existing 4x4 explained report structure. Do not add new subplots. Add meaning through labels, callouts, and right-side text.

## 10. Metrics and Data Requirements

| Data Item                         | Current Availability                                | Field Name                          | Type    | Unit                             | Producer                              | Required for Rendering     | Old Artifact Behavior                     |
| --------------------------------- | --------------------------------------------------- | ----------------------------------- | ------- | -------------------------------- | ------------------------------------- | -------------------------- | ----------------------------------------- |
| Coverage                          | Already in `render_metrics`                         | `coverage`                          | `float` | fraction `0.0–1.0`               | `run_iter9.py`, `run_benchmark.py`    | Existing                   | Existing artifacts unaffected             |
| Mine accuracy                     | Already in `render_metrics`                         | `mine_accuracy`                     | `float` | fraction `0.0–1.0`               | `run_iter9.py`, `run_benchmark.py`    | Existing                   | Existing artifacts unaffected             |
| Mean absolute error               | Already in `render_metrics`                         | `mean_abs_error`                    | `float` | target-number units              | `run_iter9.py`, `run_benchmark.py`    | Existing                   | Existing artifacts unaffected             |
| Mine density                      | Already in `render_metrics`                         | `mine_density`                      | `float` | fraction `0.0–1.0`               | `run_iter9.py`, `run_benchmark.py`    | Existing                   | Existing artifacts unaffected             |
| Route name                        | Already in `render_metrics`                         | `repair_route_selected`             | `str`   | route identifier                 | `run_iter9.py`, `run_benchmark.py`    | Existing                   | Existing artifacts unaffected             |
| Final optimization score          | Already derivable from `history`                    | `hist[-1]`                          | `float` | optimizer score                  | `report.py` from `history` parameter  | Yes                        | If history missing, chart says no history |
| History step size                 | Existing label implies 50,000                       | `EXPLAINED_HISTORY_SAMPLE_INTERVAL` | `int`   | attempted mine changes per point | `report.py` constant                  | Yes                        | No JSON change                            |
| Benchmark runtime                 | Available before render                             | `total_time_s`                      | `float` | seconds                          | `run_benchmark.py`                    | Optional                   | If missing, runtime line omitted          |
| Iter9 runtime before report write | Not currently passed to renderer                    | `runtime_before_report_s`           | `float` | seconds                          | `run_iter9.py`                        | Optional                   | If missing, runtime line omitted          |
| Total final runtime               | Already written after render in Iter9 final metrics | `total_time_s`                      | `float` | seconds                          | `run_iter9.py` final metrics document | Not required for rendering | Existing field preserved                  |

No algorithm metric is required. No change is required in `core.py`, `sa.py`, `solver.py`, `repair.py`, or `pipeline.py`.

## 11. Test Plan

| Test File                           | Test Name                                                       | Purpose                                                                 | Required Assertions                                                                                                                                           |
| ----------------------------------- | --------------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_report_explanations.py` | `test_explained_colorbar_labels_are_beginner_readable`          | Verify every explained colorbar label has concrete endpoint meaning     | Assert target, number-field, and difference labels contain exact beginner-readable phrases from Section 8                                                     |
| `tests/test_report_explanations.py` | `test_explained_value_explanations_define_zero_and_high_values` | Verify right-side explanatory copy defines values                       | Assert target, number-field, and difference explanations define `0`, `8`, and `4 or more`                                                                     |
| `tests/test_report_explanations.py` | `test_add_explained_colorbar_sets_label_and_ticks`              | Verify colorbar helper sets real Matplotlib labels                      | Assert `cbar.ax.get_ylabel()` equals the passed label and tick labels exist                                                                                   |
| `tests/test_report_explanations.py` | `test_explained_optimization_progress_uses_beginner_labels`     | Verify explained optimizer chart removes technical wording              | Assert chart title, x-label, y-label, legend, and annotations contain beginner wording and do not contain `Weighted loss` or `x50k`                           |
| `tests/test_report_explanations.py` | `test_format_duration_outputs_plain_english`                    | Verify runtime text is understandable                                   | Assert `12`, `75`, and `3660` seconds format as plain English                                                                                                 |
| `tests/test_report_explanations.py` | `test_technical_history_labels_are_preserved`                   | Lock technical report behavior                                          | Assert `TECHNICAL_HISTORY_X_LABEL == "x50k iters"` and `TECHNICAL_HISTORY_Y_LABEL == "Weighted loss"`                                                         |
| `tests/test_report_explanations.py` | `test_render_report_explained_writes_non_empty_png`             | Existing smoke test remains valid                                       | Keep existing non-empty PNG assertion; add `total_time_s` to fixture metrics                                                                                  |
| `tests/test_report_explanations.py` | `test_caption_dictionaries_are_complete`                        | Ensure caption dictionaries still cover required panels                 | Assert existing keys remain; assert new explanation constants include target, mine grid, number field, error map, solver result, loss curve, and history axis |
| `tests/test_benchmark_layout.py`    | `test_benchmark_uses_shared_explained_report_renderer`          | Verify benchmark explained path receives same renderer changes as Iter9 | Assert `run_benchmark.render_report_explained is report.render_report_explained` and same for repair overlay explained                                        |
| `tests/test_benchmark_layout.py`    | `test_preserved_child_artifact_filenames`                       | Preserve benchmark output names                                         | Existing assertions remain unchanged for `visual_<board>_explained.png` and repair overlay explained filenames                                                |

## 12. Documentation Plan

| File Path                                                       | Section to Modify                                 | Required / Optional | Exact New Content Summary                                                                                                                                          |
| --------------------------------------------------------------- | ------------------------------------------------- | ------------------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `README.md`                                                     | Beginner Workflow → Step 3                        |            Required | Tell beginners to open `iter9_<board>_FINAL_explained.png` before technical PNG and metrics JSON                                                                   |
| `README.md`                                                     | New section after “Generated Artifacts to expect” |            Required | Add “How to Read Explained Report PNGs” table with target colorbar, generated number colorbar, difference colorbar, solver colors, and optimizer progress meanings |
| `docs/explained_report_artifact_contract.md`                    | New file                                          |            Required | Define exact explained-report labels, value explanations, optimization chart wording, and technical report preservation rules                                      |
| `docs/DOCS_INDEX.md`                                            | Docs index list/table                             |            Required | Add one entry for `docs/explained_report_artifact_contract.md`                                                                                                     |
| `AGENTS.md`                                                     | No change                                         |        Not required | Existing visual artifact guidance already separates technical PNGs and explained PNGs                                                                              |
| `docs/codex_late_stage_repair_routing_implementation_status.md` | No change                                         |        Not required | This plan is readability/report-only, not repair-routing implementation status                                                                                     |
| `docs/forensic_cleanup_audit_after_source_image_contract.md`    | No change                                         |        Not required | No source-image contract behavior changes                                                                                                                          |

## 13. Backward Compatibility and Behavior Preservation

### Artifact filenames that must not change

```text
iter9_<board>_FINAL.png
iter9_<board>_FINAL_explained.png
repair_overlay_<board>.png
repair_overlay_<board>_explained.png
visual_<board>.png
visual_<board>_explained.png
metrics_iter9_<board>.json
metrics_<board>.json
benchmark_summary.json
benchmark_summary.csv
benchmark_summary.md
```

### CLI behavior that must not change

```powershell
python run_iter9.py --help
python run_benchmark.py --help
python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical
python run_benchmark.py --image assets/line_art_irl_11_v2.png --widths 300 --seeds 11 --allow-noncanonical
```

### Technical report behavior that must not change

* `render_report()` remains the technical diagnostic report.
* `Weighted loss` remains in technical PNGs.
* `x50k iters` remains in technical PNGs.
* Technical colorbars remain audit-oriented.
* Technical metrics table remains monospaced.
* Technical report panel count remains unchanged.

### Metrics compatibility that must not change

* Existing metrics fields are not removed.
* Existing JSON schema string remains unchanged.
* Existing benchmark summary fields remain unchanged.
* New render-only metric keys are optional.
* Old metrics dictionaries still render without runtime text.

### Algorithm behavior that must not change

No changes to:

```text
core.py
sa.py
solver.py
repair.py
corridors.py
board_sizing.py
pipeline.py repair routing logic
```

## 14. Risks and Edge Cases

| Risk / Edge Case                                              | Failure Mode                                        | Mitigation                                                                                                                            |
| ------------------------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Colorbar label clipping                                       | Vertical labels clipped by tight bounding box       | Increase explained figure width to `22`, increase `wspace` to `0.34`, keep `bbox_inches="tight"`, use fontsize `8`                    |
| Text box overcrowding                                         | Right-side explanation box becomes too dense        | Use short exact sentences from Section 8, keep `_WRAP_WIDTH`, avoid repeating full metric explanations inside chart                   |
| Optimization chart callout overlap                            | Final-score callout covers curve                    | Place annotation text in axes fraction at `(0.58, 0.12)` and use arrow to final point                                                 |
| Log-scale invalid data                                        | `hist` has zero or negative values                  | Preserve existing filtering `hist = hist[hist > 0]`; if fewer than two values remain, show “No optimization progress history...”      |
| Missing runtime field                                         | Old fixtures or direct calls lack `total_time_s`    | `_runtime_context_line()` returns `None`; report still explains 50,000 attempted changes per point                                    |
| Benchmark runtime includes incomplete time                    | Benchmark `duration_s` is measured before rendering | Text says “work recorded before this report image was written,” matching the field timing                                             |
| Iter9 runtime before report differs from final `total_time_s` | Rendered runtime excludes final image write time    | Use field name `runtime_before_report_s` and wording “before this report image was written”                                           |
| High-DPI / low-DPI rendering differences                      | Text size appears small in generated PNG            | Use explicit fontsize `8–12`, preserve `dpi=120`, and smoke-test generated PNG                                                        |
| Board sizes with narrow/tall aspect ratios                    | Colorbars and chart text compete for space          | The report’s 4-column layout remains; widened figure and wrapped text reduce overlap                                                  |
| Long source image names                                       | Header or footer wrapping grows vertically          | Existing `_wrap_text()` and `_footer_axis()` remain; no new source-name text added to chart                                           |
| Beginner wording becomes technically inaccurate               | Simplified terms hide that loss is weighted         | Use “match error score” and state “lower means generated numbers are closer to target”; keep technical PNG for weighted audit wording |
| Existing tests checking exact captions fail                   | Caption dictionary values change                    | Modify tests to assert required meaning rather than old exact full strings                                                            |

## 15. Validation Commands

Run from the repository root in Windows PowerShell:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical
python run_benchmark.py --image assets/line_art_irl_11_v2.png --widths 300 --seeds 11 --allow-noncanonical
python run_benchmark.py --regression-only
```

Manual artifact checks after generation:

```powershell
Get-ChildItem -Recurse results -Filter "*_explained.png" | Select-Object -First 20 FullName
Get-ChildItem -Recurse results -Filter "visual_*_explained.png" | Select-Object -First 20 FullName
```

Manual visual inspection checklist:

```text
Open the generated explained PNG.
Confirm the target colorbar has a descriptive label.
Confirm the generated-number colorbar has a descriptive label.
Confirm the difference colorbar has a descriptive label.
Confirm the right-side text explains 0, 8, and 4+ values.
Confirm the optimization chart does not say Weighted loss.
Confirm the optimization chart does not say x50k iterations.
Confirm the optimization chart says lower is better.
Confirm the optimization chart explains 50,000 attempted mine changes per point.
Confirm the technical PNG still says Weighted loss and x50k iters.
```

## 16. Acceptance Criteria

1. Every red user comment in the attached image is resolved.
2. The target-image colorbar in explained final reports has a meaningful label.
3. The generated-number-field colorbar in explained final reports has a meaningful label.
4. The difference-from-target colorbar in explained final reports has a meaningful label.
5. The explained report text defines target values:

   * `0` means background.
   * `8` means strongest line area.
6. The explained report text defines generated number values:

   * `0` means no touching mines.
   * `8` means surrounded by mines.
7. The explained report text defines difference values:

   * `0` means match.
   * higher means larger mismatch.
   * `4+` means large mismatch.
8. The explained optimization chart does not show `Weighted loss`.
9. The explained optimization chart does not show `x50k iterations`.
10. The explained optimization chart says lower is better.
11. The explained optimization chart explains that each point is 50,000 attempted mine changes.
12. The explained optimization chart has a legend or direct label for the plotted line.
13. The explained optimization chart shows a final-score callout when history is available.
14. The optimization chart keeps readable numeric tick labels.
15. Benchmark explained reports receive the same renderer changes as Iter9 explained reports.
16. Technical reports preserve `Weighted loss` and `x50k iters`.
17. Artifact filenames remain unchanged.
18. Existing CLI commands still work.
19. Unit tests pass.
20. README and docs describe the new explained-report reading rules.
21. The generated explained PNG is visually inspectable without codebase knowledge.
22. The technical PNG remains suitable for detailed audit.

## 17. Implementation Order

1. Modify `report.py` by adding constants and helper functions.
2. Modify `render_report()` only enough to use technical label constants with unchanged strings.
3. Modify `render_report_explained()` colorbars, caption lines, optimization chart helper call, and tick-hiding loop.
4. Modify `render_repair_overlay_explained()` to reuse explained colorbar helper.
5. Modify `run_benchmark.py` to pass `total_time_s` into `render_metrics`.
6. Modify `run_iter9.py` to pass `runtime_before_report_s` into `render_metrics`.
7. Add and adjust tests in `tests/test_report_explanations.py`.
8. Add benchmark shared-renderer test in `tests/test_benchmark_layout.py`.
9. Run unit tests.
10. Modify `README.md`.
11. Add `docs/explained_report_artifact_contract.md`.
12. Modify `docs/DOCS_INDEX.md`.
13. Run validation commands.
14. Generate one Iter9 explained PNG and one benchmark explained PNG.
15. Manually inspect the explained PNGs and technical PNGs against Section 16.

## 18. Final Self-Audit Checklist

* [ ] I inspected the attached image.
* [ ] I extracted every visible red-box user comment.
* [ ] I reviewed the full digest.
* [ ] I identified exact files and functions.
* [ ] I mapped every requirement to code.
* [ ] I specified exact text where text is required.
* [ ] I included tests.
* [ ] I included docs.
* [ ] I avoided assumptions.
* [ ] I preserved technical artifacts unless explicitly changed.
* [ ] I preserved artifact filenames.
* [ ] I preserved CLI behavior.
* [ ] I preserved metrics compatibility.
* [ ] I provided validation commands.
* [ ] I removed ambiguous implementation instructions.
* [ ] I reviewed all proposed label replacements for a reader with no knowledge of the codebase or coding.
