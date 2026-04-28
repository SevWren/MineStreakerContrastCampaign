# Explained Report Artifact Contract

## Purpose
Define the required beginner-readable labels, helper behavior, optimization-chart wording, and compatibility rules for explained report PNGs.

## Scope
Applies to:
- `render_report_explained(...)`
- `render_repair_overlay_explained(...)`

Does not change technical report wording or solver/repair algorithms.

## Required Explained Colorbar Labels
- `Target value: 0 background → 8 strongest line`
- `Generated number: 0 no nearby mines → 8 surrounded`
- `Difference: 0 match → 4+ large mismatch`
- `Visual change: negative better → positive worse`

Required explained ticks:
- target ticks = `[0, 2, 4, 6, 8]`
- generated number ticks = `[0, 2, 4, 6, 8]`
- difference ticks = `[0, 1, 2, 3, 4]`
- repair visual-change ticks = `[-1.5, -0.75, 0, 0.75, 1.5]`

## Required Explained Value Text
- `Target values: 0 means background. 8 means the strongest line area from the source image.`
- `Generated mine layout: white cells are safe cells. Black cells are mines.`
- `Generated number values: 0 means a safe cell has no touching mines. 8 means a safe cell is surrounded by mines.`
- `Difference values: 0 means the generated number matched the target at that cell. Higher values mean a larger visual mismatch. 4 or more means a large mismatch.`
- `Solver result colors: gray means revealed safe cells, orange means flagged mines, and blue means unresolved cells.`
- `Optimizer progress: the line shows a match error score. Lower means the generated numbers are closer to the target image.`
- `Optimizer work: each plotted point is saved after 50,000 attempted mine changes. This axis is optimizer work, not clock time.`

## Optimization Chart Wording and Boundary
Required explained wording:
- title: `Optimizer progress: lower is better`
- x-axis: `Optimizer work (50,000 attempted mine changes per point)`
- y-axis: `Match error score (lower is better)`
- legend/line label: `Match error score`
- final callout: `Final score: <value>`

Chart constraints:
- Only one plotted history curve.
- Keep visible numeric ticks.
- One clear legend or direct line label.
- One final-score callout when history exists.
- Do not add extra plotted lines, markers, secondary axes, or extra visual indicators.

Forbidden in explained chart title/axis labels/legend/annotations:
- `Weighted loss`
- `x50k`
- `x50k iterations`

## Helper Behavior Contract
- `_add_explained_colorbar(...)` must apply explicit ticks and a vertical descriptive label.
- `_format_duration(None)` returns `None`.
- `_format_duration(invalid value)` returns `None`.
- `_format_duration(negative value)` returns `None`.
- `_format_duration(12)` returns `about 12 sec`.
- `_format_duration(75)` returns `about 1 min 15 sec`.
- `_format_duration(3660)` returns `about 1 hr 1 min`.
- `_runtime_context_line(metrics)` uses `total_time_s` first, then `runtime_before_report_s`.
- `_runtime_context_line(metrics)` returns `None` when neither field exists.
- `_plot_explained_optimization_progress(...)` must keep one curve and beginner wording.

## Technical Report Preservation
Technical report wording remains unchanged:
- `Loss curve (log)`
- `x50k iters`
- `Weighted loss`

These terms are valid only in technical report artifacts.

## Compatibility Requirements
- Preserve artifact filenames:
  - `iter9_<board>_FINAL.png`
  - `iter9_<board>_FINAL_explained.png`
  - `repair_overlay_<board>.png`
  - `repair_overlay_<board>_explained.png`
  - `visual_<board>.png`
  - `visual_<board>_explained.png`
- Preserve existing CLI behavior for `run_iter9.py` and `run_benchmark.py`.
- Preserve existing metrics fields and final `total_time_s` behavior.
- Keep explained layout anti-clipping behavior:
  - `fig = plt.figure(figsize=(22, 14.5))`
  - `wspace=0.34`
  - `bbox_inches="tight"`

