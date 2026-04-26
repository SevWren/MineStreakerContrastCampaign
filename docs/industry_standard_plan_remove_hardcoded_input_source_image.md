# Industry Standard Plan: Remove Hard-Coded `assets/input_source_image.png`

**Project:** Mine-Streaker / Minesweeper Image Reconstruction  
**Plan target:** Replace the legacy hard-coded source-image behavior with an explicit source-image runtime contract  
**Primary entry points:** `run_iter9.py`, `run_benchmark.py`  
**Related support files:** `assets/image_guard.py`, `source_config.py`, `README.md`, `AGENTS.md`, `tests/`  
**Primary user problem:** The pipeline currently treats `assets/input_source_image.png` as an implicit global source image, forcing users to copy/overwrite that path instead of passing the desired source image directly.  
**Strategic outcome:** Every run should explicitly record which exact source image was used, when it ran, which project/worktree produced it, what command/config generated it, and where all output artifacts were written.

---

## 1. Purpose

The current behavior still carries an old assumption:

```text
The project has one special input image:
assets/input_source_image.png
```

That assumption is now wrong.

The project has evolved into a research pipeline that must support many source images, many board sizes, many seeds, and many experiment variants. The source image must therefore become a first-class runtime input, not a hidden global constant.

The new contract should be:

```text
Every production run receives an explicit source image path.
Every output artifact records the exact source image identity.
The default assets/input_source_image.png remains only for backward compatibility.
```

This plan removes the architectural workaround of copying a new source image over `assets/input_source_image.png`.

---

## 2. Current Problem

### 2.1 Legacy hard-coded input path

The project still contains patterns like:

```python
IMG = "assets/input_source_image.png"
```

This causes several problems:

1. Users cannot naturally run the pipeline against a new image.
2. Multiple experiments can accidentally reuse the wrong image.
3. Output folders can be ambiguous.
4. Metrics may not prove which source image created the result.
5. Image guard validation becomes tied to one old file path.
6. Future LLM review can misinterpret results because the JSON does not fully identify the input image.

---

## 3. Target Behavior

### 3.1 Main run with explicit image

The normal workflow should become:

```powershell
python run_iter9.py --image "D:\Github\MineSweepResearchFilesFinalIteration\assets\line_art_irl_11_v2.png" --out-dir "results\iter9_line_art_irl_11_v2" --board-w 300 --seed 42 --allow-noncanonical
```

### 3.2 Default backward-compatible run

This should still work:

```powershell
python run_iter9.py
```

But it should mean:

```text
Use assets/input_source_image.png only because no --image argument was supplied.
```

It must not mean:

```text
The project only supports assets/input_source_image.png.
```

### 3.3 Benchmark with explicit image

The benchmark should support:

```powershell
python run_benchmark.py --image "assets\line_art_irl_11_v2.png" --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical
```

### 3.4 Regression-only remains stable

The existing known regression case should remain available:

```powershell
python run_benchmark.py --regression-only
```

Regression mode may continue to use fixed known images and baseline artifacts. Normal experiment mode must not.

---

## 4. Non-Negotiable Requirements

1. Do not require users to copy or overwrite `assets/input_source_image.png`.
2. Do not remove the default behavior of `python run_iter9.py`.
3. Do not break `python run_benchmark.py --regression-only`.
4. Do not remove existing repair-routing metrics.
5. Do not remove existing repair-route artifacts.
6. Do not add new production dependencies.
7. Do not perform unrelated refactors.
8. Do not validate any source image at import time.
9. Do not make a single global canonical image the only valid runtime image.
10. Metrics JSON must record the exact input image path, hash, run timing, project identity, command, config, artifacts, validation gates, and LLM review summary.

---

## 5. Target Architecture

### 5.1 Old architecture

```text
run_iter9.py
  └── hard-coded IMG = assets/input_source_image.png
        └── image_guard validates that one path
              └── pipeline runs
                    └── metrics do not fully prove source image identity
```

### 5.2 New architecture

```text
CLI args
  └── source_config.py resolves image identity
        └── image_guard validates explicit image path
              └── pipeline runs against explicit image
                    └── metrics record full source/run/project provenance
                          └── linked artifacts record run_id + metrics_path
```

---

## 6. Required Files To Modify

```text
run_iter9.py
run_benchmark.py
assets/image_guard.py
README.md
AGENTS.md
```

---

## 7. Required New File

```text
source_config.py
```

---

## 8. Required Tests

```text
tests/test_source_image_cli_contract.py
tests/test_source_config.py
```

---

# Phase 1: Add `source_config.py`

## 1.1 Objective

Create a small source-image identity module that resolves, validates, hashes, and describes the source image for a run.

This module should not own image preprocessing. It only owns runtime source-image identity.

---

## 1.2 Add Dataclass

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourceImageConfig:
    command_arg: str
    absolute_path: Path
    project_relative_path: str | None
    name: str
    stem: str
    sha256: str
    size_bytes: int
    allow_noncanonical: bool
    manifest_path: str | None
```

---

## 1.3 Add Function: `compute_file_sha256`

```python
def compute_file_sha256(path: Path) -> str:
    """
    Compute SHA-256 for a source image file.
    """
```

Required behavior:

- Read in chunks.
- Return lowercase hex digest.
- Raise `FileNotFoundError` if missing.
- Do not mutate the file.

---

## 1.4 Add Function: `project_relative_or_none`

```python
def project_relative_or_none(path: Path, project_root: Path) -> str | None:
    """
    Return project-relative path with forward slashes when the image is inside the project.
    Return None when the image is outside the project.
    """
```

Required behavior:

- Use normalized resolved paths.
- Use forward slashes in JSON.
- Do not fail if image is outside the project.

---

## 1.5 Add Function: `resolve_source_image_config`

```python
def resolve_source_image_config(
    image_path: str,
    *,
    project_root: str | Path | None = None,
    allow_noncanonical: bool = False,
    manifest_path: str | None = None,
) -> SourceImageConfig:
    """
    Resolve, validate, hash, and describe the source image for a run.
    """
```

Required behavior:

- Resolve absolute path.
- Verify file exists.
- Verify file is a file.
- Compute SHA-256.
- Compute size.
- Populate name and stem.
- Populate project-relative path if possible.
- Preserve the original command argument string.
- Do not copy, rename, or mutate the source image.

---

## 1.6 Acceptance Criteria

- Can resolve `assets/line_art_irl_11_v2.png`.
- Can resolve an absolute Windows path.
- Can resolve a project-relative path.
- Can record external images outside the repo.
- Returns JSON-serializable values after conversion.
- Does not depend on NumPy, Pillow, SciPy, or Matplotlib.

---

# Phase 2: Refactor `assets/image_guard.py`

## 2.1 Objective

Change the image guard from a single hard-coded canonical-image validator into a reusable validator that supports:

1. Backward-compatible default validation.
2. Explicit custom-image validation.
3. Explicit noncanonical mode.
4. Per-image manifest mode.

---

## 2.2 Current Problem

The current strict image guard behavior is tied to the legacy default image. When source images change, validation can fail for reasons unrelated to runtime correctness.

This has already created a workflow problem where a run can be valid for experimentation but blocked by canonical metadata tied to a different file identity.

---

## 2.3 New CLI

```powershell
python assets/image_guard.py --path "assets\line_art_irl_11_v2.png" --allow-noncanonical
```

```powershell
python assets/image_guard.py --path "assets\line_art_irl_11_v2.png" --manifest "assets\image_manifests\line_art_irl_11_v2.json"
```

Backward-compatible:

```powershell
python assets/image_guard.py --path "assets/input_source_image.png"
```

---

## 2.4 Add Arguments

```python
parser.add_argument("--path", required=True)
parser.add_argument("--allow-noncanonical", action="store_true")
parser.add_argument("--manifest", default=None)
```

If the current CLI already has `--path`, preserve it and add only missing arguments.

---

## 2.5 Manifest Validation

Add support for a manifest file:

```json
{
  "image_name": "line_art_irl_11_v2.png",
  "file_sha256": "...",
  "file_size": 123456,
  "pixel_sha256": "...",
  "pixel_shape": [1024, 831, 3],
  "pixel_dtype": "uint8",
  "pixel_mean": 231.403371,
  "pixel_std": 63.732681,
  "pixel_min": 0,
  "pixel_max": 255
}
```

Required behavior:

- If `--manifest` is supplied, validate against the manifest.
- If no manifest is supplied and image is the legacy default, use legacy expected metadata if present.
- If no manifest is supplied and image is not the legacy default:
  - pass only if `--allow-noncanonical` is supplied,
  - otherwise fail with a clear message telling the user to provide `--allow-noncanonical` or `--manifest`.

---

## 2.6 Function Return Contract

Update or wrap `verify_source_image()` so callers can receive structured validation info:

```python
{
  "source_image_validated": true,
  "canonical_image_match": false,
  "noncanonical_allowed": true,
  "manifest_path": null,
  "warnings": [
    {
      "code": "NONCANONICAL_SOURCE_ALLOWED",
      "severity": "warning",
      "message": "Source image was allowed without canonical manifest validation."
    }
  ]
}
```

Preserve old behavior where `halt_on_failure=True` raises or exits on failure.

---

## 2.7 Acceptance Criteria

- `assets/input_source_image.png` still works by default.
- Custom images work with `--allow-noncanonical`.
- Custom images can be promoted to canonical by manifest.
- Validation details are available to metrics.
- No caller is forced to copy a file into the legacy path.

---

# Phase 3: Refactor `run_iter9.py`

## 3.1 Objective

Make `run_iter9.py` accept an explicit source image path and record complete run/source provenance.

---

## 3.2 Add CLI Arguments

```python
parser.add_argument("--image", default="assets/input_source_image.png")
parser.add_argument("--out-dir", default=None)
parser.add_argument("--board-w", type=int, default=300)
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--allow-noncanonical", action="store_true")
parser.add_argument("--image-manifest", default=None)
```

Optional but recommended:

```python
parser.add_argument("--run-tag", default="")
parser.add_argument("--results-root", default="results/iter9")
```

---

## 3.3 Remove Hard-Coded Runtime Dependency

Replace:

```python
IMG = "assets/input_source_image.png"
```

with:

```python
DEFAULT_IMAGE = "assets/input_source_image.png"
```

`DEFAULT_IMAGE` may only be used as an argparse default.

No pipeline code should read `IMG` as a global runtime source.

---

## 3.4 Move Validation After CLI Parsing

Bad pattern to remove:

```python
IMG = "assets/input_source_image.png"
verify_source_image(IMG, halt_on_failure=True)
```

Correct pattern:

```python
def main() -> int:
    args = parse_args()
    source = resolve_source_image_config(
        args.image,
        project_root=Path(__file__).resolve().parent,
        allow_noncanonical=args.allow_noncanonical,
        manifest_path=args.image_manifest,
    )
    image_validation = verify_source_image(
        str(source.absolute_path),
        halt_on_failure=True,
        verbose=True,
        allow_noncanonical=args.allow_noncanonical,
        manifest_path=args.image_manifest,
    )
```

---

## 3.5 Derive Default Output Directory From Image Identity

If `--out-dir` is omitted, generate:

```text
results/iter9/<run_id>/
```

Recommended `run_id`:

```text
YYYYMMDDTHHMMSSZ_<image_stem>_<board_width>w_seed<seed>
```

Example:

```text
results/iter9/20260425T211403Z_line_art_irl_11_v2_300w_seed42/
```

---

## 3.6 Record Run Timing

Add UTC timestamps:

```json
"run_timing": {
  "started_at_utc": "2026-04-25T21:14:03.421Z",
  "finished_at_utc": "2026-04-25T21:31:48.902Z",
  "duration_wall_s": 1065.481
}
```

Implementation notes:

- Use `datetime.now(timezone.utc)`.
- Use trailing `Z`.
- Use `time.perf_counter()` for wall duration.

---

## 3.7 Record Source Image Identity In Metrics

Add:

```json
"source_image": {
  "command_arg": "assets/line_art_irl_11_v2.png",
  "project_relative_path": "assets/line_art_irl_11_v2.png",
  "absolute_path": "D:/Github/MineSweepResearchFilesFinalIteration/assets/line_art_irl_11_v2.png",
  "name": "line_art_irl_11_v2.png",
  "stem": "line_art_irl_11_v2",
  "sha256": "...",
  "size_bytes": 123456,
  "allow_noncanonical": true,
  "manifest_path": null
}
```

Rules:

- Use forward slashes in JSON paths.
- Store both project-relative and absolute path.
- Store what the user typed in `command_arg`.
- Store hash and size.

---

## 3.8 Record Project Identity

Add:

```json
"project_identity": {
  "project_root": "D:/Github/MineSweepResearchFilesFinalIteration",
  "project_root_name": "MineSweepResearchFilesFinalIteration",
  "git_commit": "abc123...",
  "git_branch": "codex/source-image-runtime-contract",
  "git_dirty": true
}
```

Add helper functions:

```python
def get_git_metadata(project_root: Path) -> dict:
    ...
```

Required behavior:

- Return `None` for git fields if git is unavailable.
- Do not fail runs because git metadata cannot be read.

---

## 3.9 Record Command Invocation

Add:

```json
"command_invocation": {
  "entry_point": "run_iter9.py",
  "argv": [
    "run_iter9.py",
    "--image",
    "assets/line_art_irl_11_v2.png",
    "--out-dir",
    "results/iter9_line_art_irl_11_v2",
    "--board-w",
    "300",
    "--seed",
    "42",
    "--allow-noncanonical"
  ]
}
```

Use `sys.argv`.

---

## 3.10 Record Effective Config

Add:

```json
"effective_config": {
  "board_width": 300,
  "board_height": 370,
  "seed": 42,
  "density": 0.22,
  "border": 3,
  "invert": true,
  "contrast_factor": 2.0,
  "out_dir": "results/iter9/20260425T211403Z_line_art_irl_11_v2_300w_seed42"
}
```

This must reflect the actual values used, not only values typed by the user.

---

## 3.11 Preserve Existing Metrics

Do not remove existing fields, including but not limited to:

```text
coverage
solvable
mine_accuracy
n_unknown
repair_reason
total_time_s
sat_risk
phase2
gate_aspect_ratio_within_0_5pct
repair_route_selected
repair_route_result
dominant_failure_class
sealed_cluster_count
sealed_single_mesa_count
sealed_multi_cell_cluster_count
phase2_fixes
last100_fixes
visual_delta
failure_taxonomy_path
repair_route_decision_path
visual_delta_summary_path
repair_overlay_path
```

---

## 3.12 Acceptance Criteria

- `python run_iter9.py --image "assets/line_art_irl_11_v2.png" --allow-noncanonical` uses that exact image.
- `python run_iter9.py` still works.
- Importing `run_iter9.py` does not validate any image.
- Metrics identify the source image fully.
- Output path is image-specific by default.
- Repair-routing metrics and artifacts still exist.

---

# Phase 4: Refactor `run_benchmark.py`

## 4.1 Objective

Make normal benchmark mode accept an explicit source image while preserving known regression-only mode.

---

## 4.2 Add CLI Arguments

```python
parser.add_argument("--image", default="assets/input_source_image.png")
parser.add_argument("--widths", nargs="+", type=int, default=[300, 360, 420])
parser.add_argument("--seeds", nargs="+", type=int, default=[300, 301, 302])
parser.add_argument("--out-dir", default="results/benchmark")
parser.add_argument("--allow-noncanonical", action="store_true")
parser.add_argument("--image-manifest", default=None)
parser.add_argument("--regression-only", action="store_true")
parser.add_argument("--include-regressions", action="store_true")
```

---

## 4.3 Remove Standard Benchmark Global `IMG`

Replace standard benchmark usage of:

```python
IMG = "assets/input_source_image.png"
```

with parsed `args.image`.

A default image constant may exist only as:

```python
DEFAULT_IMAGE = "assets/input_source_image.png"
```

and only for argparse defaulting.

---

## 4.4 Separate Benchmark Modes

### Mode 1: Normal explicit-image benchmark

```powershell
python run_benchmark.py --image "assets\line_art_irl_11_v2.png" --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical
```

Behavior:

- Uses only the requested image.
- Uses requested widths.
- Uses requested seeds.
- Writes image-specific result rows.

### Mode 2: Regression-only

```powershell
python run_benchmark.py --regression-only
```

Behavior:

- Uses fixed `REGRESSION_CASES`.
- Does not use `--image`.
- Preserves known `line_art_irl_9` behavior.
- Fails loudly if regression route or unknown-count expectations fail.

### Mode 3: Normal benchmark plus regressions

```powershell
python run_benchmark.py --image "assets\line_art_irl_11_v2.png" --include-regressions --allow-noncanonical
```

Behavior:

- Runs the standard requested-image benchmark.
- Also runs fixed regression cases.

---

## 4.5 Add Source Provenance To Every Row

Each benchmark row should include:

```json
"source_image": {
  "command_arg": "assets/line_art_irl_11_v2.png",
  "project_relative_path": "assets/line_art_irl_11_v2.png",
  "absolute_path": "...",
  "name": "line_art_irl_11_v2.png",
  "stem": "line_art_irl_11_v2",
  "sha256": "...",
  "size_bytes": 123456,
  "allow_noncanonical": true,
  "manifest_path": null
}
```

For regression cases, source-image identity should be recorded from the regression case image path.

---

## 4.6 Acceptance Criteria

- Normal benchmark does not depend on `assets/input_source_image.png`.
- Regression-only still passes or fails based on known regression criteria.
- All benchmark result JSON rows identify the source image.
- Importing `run_benchmark.py` does not validate an image.
- `--help` clearly documents the new arguments.

---

# Phase 5: Add LLM-Friendly Metrics Context

## 5.1 Objective

Make metrics JSON self-contained enough that a future LLM can understand and review the run without needing the terminal log.

---

## 5.2 Add Top-Level Schema Version

```json
"schema_version": "metrics.v2.source_image_runtime_contract"
```

---

## 5.3 Recommended Top-Level JSON Layout

```json
{
  "schema_version": "metrics.v2.source_image_runtime_contract",
  "run_identity": {},
  "run_timing": {},
  "project_identity": {},
  "command_invocation": {},
  "source_image": {},
  "source_image_analysis": {},
  "effective_config": {},
  "board_sizing": {},
  "preprocessing_config": {},
  "target_field_stats": {},
  "weight_config": {},
  "corridor_config": {},
  "sa_config": {},
  "repair_config": {},
  "solver_summary": {},
  "repair_route_summary": {},
  "visual_quality_summary": {},
  "runtime_phase_timing_s": {},
  "environment": {},
  "artifact_inventory": {},
  "validation_gates": {},
  "warnings_and_exceptions": [],
  "llm_review_summary": {}
}
```

Existing flat metrics may remain for backward compatibility, but the new structured blocks should be added.

---

## 5.4 Add `run_identity`

```json
"run_identity": {
  "run_id": "20260425T211403Z_line_art_irl_11_v2_300w_seed42",
  "entry_point": "run_iter9.py",
  "output_dir": "results/iter9/20260425T211403Z_line_art_irl_11_v2_300w_seed42",
  "board_width": 300,
  "board_height": 370,
  "seed": 42
}
```

---

## 5.5 Add `run_timing`

```json
"run_timing": {
  "started_at_utc": "2026-04-25T21:14:03.421Z",
  "finished_at_utc": "2026-04-25T21:31:48.902Z",
  "duration_wall_s": 1065.481
}
```

---

## 5.6 Add `project_identity`

```json
"project_identity": {
  "project_root": "D:/Github/MineSweepResearchFilesFinalIteration",
  "project_root_name": "MineSweepResearchFilesFinalIteration",
  "git_commit": "abc123...",
  "git_branch": "codex/source-image-runtime-contract",
  "git_dirty": true
}
```

---

## 5.7 Add `command_invocation`

```json
"command_invocation": {
  "entry_point": "run_iter9.py",
  "argv": [
    "run_iter9.py",
    "--image",
    "assets/line_art_irl_11_v2.png",
    "--out-dir",
    "results/iter9_line_art_irl_11_v2",
    "--board-w",
    "300",
    "--seed",
    "42",
    "--allow-noncanonical"
  ]
}
```

---

## 5.8 Add `source_image`

```json
"source_image": {
  "command_arg": "assets/line_art_irl_11_v2.png",
  "project_relative_path": "assets/line_art_irl_11_v2.png",
  "absolute_path": "D:/Github/MineSweepResearchFilesFinalIteration/assets/line_art_irl_11_v2.png",
  "name": "line_art_irl_11_v2.png",
  "stem": "line_art_irl_11_v2",
  "sha256": "...",
  "size_bytes": 123456,
  "allow_noncanonical": true,
  "manifest_path": null
}
```

---

## 5.9 Add `source_image_analysis`

```json
"source_image_analysis": {
  "width_px": 1024,
  "height_px": 1264,
  "aspect_ratio": 0.810126,
  "mode": "RGB",
  "has_alpha": false,
  "mean_luma": 231.4,
  "std_luma": 63.7
}
```

Implementation notes:

- Use Pillow.
- Keep this summary small.
- Do not embed image data.

---

## 5.10 Add `effective_config`

```json
"effective_config": {
  "board_width": 300,
  "board_height": 370,
  "seed": 42,
  "density": 0.22,
  "border": 3,
  "invert": true,
  "contrast_factor": 2.0,
  "out_dir": "results/iter9/20260425T211403Z_line_art_irl_11_v2_300w_seed42"
}
```

---

## 5.11 Add `board_sizing`

Use the full return shape from `derive_board_from_width()`.

```json
"board_sizing": {
  "source_width": 1024,
  "source_height": 1264,
  "source_ratio": 0.810126,
  "board_width": 300,
  "board_height": 370,
  "board_ratio": 0.810811,
  "aspect_ratio_relative_error": 0.000845,
  "aspect_ratio_tolerance": 0.005,
  "gate_aspect_ratio_within_tolerance": true
}
```

---

## 5.12 Add `preprocessing_config`

```json
"preprocessing_config": {
  "loader": "load_image_smart",
  "invert": true,
  "contrast_factor": 2.0,
  "piecewise_compression_enabled": true,
  "pw_knee": 4.0,
  "pw_t_max": 6.0
}
```

---

## 5.13 Add `target_field_stats`

```json
"target_field_stats": {
  "min": 0.0,
  "max": 8.0,
  "mean": 1.284,
  "std": 2.115,
  "pct_t_ge_6": 4.82,
  "pct_t_ge_7": 2.31,
  "pct_t_le_1": 72.44
}
```

---

## 5.14 Add `weight_config`

```json
"weight_config": {
  "method": "compute_zone_aware_weights",
  "bp_true": 8.0,
  "bp_trans": 1.0,
  "hi_boost": 18.0,
  "hi_threshold": 3.0,
  "underfill_factor": 1.8
}
```

---

## 5.15 Add `corridor_config`

```json
"corridor_config": {
  "method": "build_adaptive_corridors",
  "border": 3,
  "corridor_width": 0,
  "low_target_bias": 5.5,
  "corridor_pct": 8.72
}
```

---

## 5.16 Add `sa_config`

```json
"sa_config": {
  "density": 0.22,
  "coarse_iters": 2000000,
  "fine_iters": 8000000,
  "refine_iters": [2000000, 2000000, 4000000],
  "T_coarse": 10.0,
  "T_fine": 3.5,
  "T_refine": [2.0, 1.7, 1.4],
  "T_min": 0.001,
  "alpha_coarse": 0.99998,
  "alpha_fine": 0.999996,
  "alpha_refine": [0.999997, 0.999997, 0.999998]
}
```

---

## 5.17 Add `repair_config`

```json
"repair_config": {
  "phase1_budget_s": 120.0,
  "phase2_budget_s": 360.0,
  "last100_budget_s": 300.0,
  "last100_unknown_threshold": 100,
  "solve_max_rounds": 300,
  "trial_max_rounds": 60
}
```

---

## 5.18 Add `solver_summary`

```json
"solver_summary": {
  "post_sa": {
    "coverage": 0.9821,
    "n_unknown": 2043,
    "solvable": false
  },
  "post_phase1": {
    "coverage": 0.9994,
    "n_unknown": 37,
    "solvable": false
  },
  "post_routing": {
    "coverage": 1.0,
    "n_unknown": 0,
    "solvable": true
  }
}
```

---

## 5.19 Add `repair_route_summary`

```json
"repair_route_summary": {
  "selected_route": "phase2_full_repair",
  "route_result": "solved",
  "dominant_failure_class": "sealed_multi_cell_cluster",
  "sealed_cluster_count": 9,
  "phase2_fixes": 4,
  "last100_fixes": 0,
  "sa_rerun_invoked": false
}
```

---

## 5.20 Add `visual_quality_summary`

```json
"visual_quality_summary": {
  "mean_abs_error_before_repair": 1.1692,
  "mean_abs_error_after_repair": 1.1694,
  "visual_delta": 0.0002,
  "pct_within_1": 74.3,
  "pct_within_2": 91.8,
  "hi_err": 1.72,
  "true_bg_err": 0.41
}
```

---

## 5.21 Add `runtime_phase_timing_s`

```json
"runtime_phase_timing_s": {
  "image_load_and_preprocess": 0.42,
  "corridor_build": 0.18,
  "coarse_sa": 4.91,
  "fine_sa": 18.72,
  "refine_sa_total": 21.44,
  "phase1_repair": 8.31,
  "late_stage_routing": 2.14,
  "render_and_write": 1.09,
  "total": 57.21
}
```

---

## 5.22 Add `environment`

```json
"environment": {
  "os": "Windows-10",
  "python_version": "3.11.8",
  "python_bits": 64,
  "cpu_count": 16,
  "numba_num_threads": 16,
  "numpy_version": "1.26.4",
  "scipy_version": "1.12.0",
  "pillow_version": "10.2.0",
  "matplotlib_version": "3.8.2"
}
```

---

## 5.23 Add `artifact_inventory`

```json
"artifact_inventory": {
  "metrics_json": "results/iter9_line_art_irl_11_v2/metrics_300x370.json",
  "grid_npy": "results/iter9_line_art_irl_11_v2/grid_300x370.npy",
  "visual_png": "results/iter9_line_art_irl_11_v2/visual_300x370.png",
  "repair_overlay_png": "results/iter9_line_art_irl_11_v2/repair_overlay_300x370.png",
  "failure_taxonomy_json": "results/iter9_line_art_irl_11_v2/failure_taxonomy.json",
  "repair_route_decision_json": "results/iter9_line_art_irl_11_v2/repair_route_decision.json",
  "visual_delta_summary_json": "results/iter9_line_art_irl_11_v2/visual_delta_summary.json"
}
```

---

## 5.24 Add `validation_gates`

```json
"validation_gates": {
  "board_valid": true,
  "forbidden_cells_mine_free": true,
  "aspect_ratio_within_tolerance": true,
  "n_unknown_zero": true,
  "coverage_at_least_9999": true,
  "solvable_true": true,
  "source_image_validated": true,
  "canonical_image_match": false,
  "noncanonical_allowed": true
}
```

---

## 5.25 Add `warnings_and_exceptions`

```json
"warnings_and_exceptions": [
  {
    "code": "NONCANONICAL_SOURCE_ALLOWED",
    "message": "Source image did not use a canonical manifest, but --allow-noncanonical was enabled.",
    "severity": "warning"
  }
]
```

---

## 5.26 Add `llm_review_summary`

```json
"llm_review_summary": {
  "one_sentence_result": "The run used assets/line_art_irl_11_v2.png at 300x370 with seed 42 and solved to n_unknown=0 through phase2_full_repair.",
  "main_success": "The routed repair path solved all remaining unknown cells.",
  "main_risk": "The source image was allowed as noncanonical, so strict manifest validation was not used.",
  "best_artifact_to_open_first": "results/iter9_line_art_irl_11_v2/repair_overlay_300x370.png",
  "best_metric_to_check_first": "n_unknown",
  "next_recommended_check": "Visually inspect the final reconstruction and repair overlay before treating the run as promoted."
}
```

---

## 5.27 Acceptance Criteria

- Metrics JSON is self-contained for LLM review.
- Metrics JSON records source image path, project-relative path, absolute path, hash, and size.
- Metrics JSON records run timing.
- Metrics JSON records git identity when available.
- Metrics JSON records the command invocation.
- Metrics JSON records artifact paths.
- Metrics JSON records validation gates and warnings.
- No large arrays are embedded in metrics JSON.

---

# Phase 6: Add Minimal Metadata To Route Artifacts

## 6.1 Objective

Keep smaller route artifacts linked to the full metrics file without duplicating the entire metrics payload.

Target artifacts:

```text
failure_taxonomy.json
repair_route_decision.json
visual_delta_summary.json
```

---

## 6.2 Add Shared Artifact Metadata

Each smaller JSON artifact should include:

```json
"artifact_metadata": {
  "run_id": "20260425T211403Z_line_art_irl_11_v2_300w_seed42",
  "generated_at_utc": "2026-04-25T21:31:48.902Z",
  "source_image_project_relative_path": "assets/line_art_irl_11_v2.png",
  "source_image_sha256": "...",
  "metrics_path": "results/iter9/20260425T211403Z_line_art_irl_11_v2_300w_seed42/metrics_300x370.json"
}
```

---

## 6.3 Acceptance Criteria

- Smaller JSON artifacts can be traced back to the metrics file.
- The source image identity is still visible in small artifacts.
- The artifact writer remains backward-compatible where possible.

---

# Phase 7: Update `README.md`

## 7.1 Objective

Stop teaching the legacy copy/overwrite workflow.

---

## 7.2 Replace Old Beginner Workflow

Replace:

```powershell
python assets/image_guard.py --path assets/input_source_image.png
python run_iter9.py
```

with:

```powershell
python assets/image_guard.py --path "assets\line_art_irl_11_v2.png" --allow-noncanonical
python run_iter9.py --image "assets\line_art_irl_11_v2.png" --out-dir "results\iter9_line_art_irl_11_v2" --allow-noncanonical
```

Also keep a backward-compatible note:

```markdown
If no `--image` is supplied, `run_iter9.py` defaults to `assets/input_source_image.png` for old workflows.
For new experiments, pass `--image` explicitly.
```

---

## 7.3 Add New Section

```markdown
## Source Image Runtime Contract

For new runs, always pass the source image explicitly:

```powershell
python run_iter9.py --image "assets\your_image.png" --out-dir "results\iter9_your_image" --allow-noncanonical
```

Do not overwrite `assets/input_source_image.png` to run a different image.
```

---

## 7.4 Acceptance Criteria

- README shows explicit-image usage.
- README does not present overwriting `assets/input_source_image.png` as normal.
- README explains noncanonical custom images.
- README explains where source image identity appears in metrics.

---

# Phase 8: Update `AGENTS.md`

## 8.1 Objective

Make future LLM agents respect the source-image contract.

---

## 8.2 Add Section

```markdown
## Source Image Runtime Contract

When modifying entry scripts or experiment workflows:

- Entry scripts must accept source images through explicit CLI arguments.
- Do not require users to overwrite `assets/input_source_image.png`.
- `assets/input_source_image.png` is only a backward-compatible default.
- Image validation must happen after CLI parsing, not at import time.
- Metrics must record source image path, project-relative path, absolute path, name, SHA-256, and canonical/noncanonical status.
- Metrics must record run timestamps, project identity, command invocation, effective config, artifact inventory, validation gates, and warnings.
- Output directories must include image identity or an explicit user-provided output root.
- Regression cases may use fixed image paths, but normal experiment runs must not.
```

---

## 8.3 Acceptance Criteria

- AGENTS.md prevents future regression into hard-coded image behavior.
- AGENTS.md explicitly distinguishes normal runs from fixed regression cases.
- AGENTS.md requires JSON provenance.

---

# Phase 9: Add Tests

## 9.1 Test File

```text
tests/test_source_image_cli_contract.py
```

---

## 9.2 Required Test: `run_iter9.py --help`

Run:

```powershell
python run_iter9.py --help
```

Assert help output contains:

```text
--image
--out-dir
--board-w
--seed
--allow-noncanonical
--image-manifest
```

---

## 9.3 Required Test: `run_benchmark.py --help`

Run:

```powershell
python run_benchmark.py --help
```

Assert help output contains:

```text
--image
--widths
--seeds
--out-dir
--allow-noncanonical
--image-manifest
--regression-only
```

---

## 9.4 Required Test: No Import-Time Validation

Import:

```python
import run_iter9
import run_benchmark
```

Expected:

```text
No image guard validation is executed during import.
```

Implementation approach:

- Use `unittest.mock.patch` around `assets.image_guard.verify_source_image`.
- Import modules with `importlib`.
- Assert mocked function was not called.

---

## 9.5 Required Test: Source Config Hashing

Create a temporary small file or PNG.

Call:

```python
resolve_source_image_config(path)
```

Assert:

```text
command_arg
absolute_path
project_relative_path
name
stem
sha256
size_bytes
```

---

## 9.6 Required Test: Default Path Is Backward-Compatible

Assert argparse default for `--image` equals:

```text
assets/input_source_image.png
```

But also assert scripts do not use a module-level `IMG` as the only runtime source.

---

## 9.7 Required Test: Metrics Provenance

For a lightweight test path, use a small helper function if a full run is too expensive.

Assert generated metrics include:

```text
schema_version
run_identity
run_timing
project_identity
command_invocation
source_image
effective_config
artifact_inventory
validation_gates
llm_review_summary
```

If a full run is too expensive, test the metrics-construction helper directly.

---

# Phase 10: Validation Commands

Run from repository root.

## 10.1 Unit tests

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

## 10.2 CLI help checks

```powershell
python run_iter9.py --help
python run_benchmark.py --help
```

## 10.3 Custom image guard check

```powershell
python assets/image_guard.py --path "assets\line_art_irl_11_v2.png" --allow-noncanonical
```

## 10.4 Custom image main pipeline run

```powershell
python run_iter9.py --image "assets\line_art_irl_11_v2.png" --out-dir "results\iter9_line_art_irl_11_v2" --board-w 300 --seed 42 --allow-noncanonical
```

## 10.5 Custom image benchmark run

```powershell
python run_benchmark.py --image "assets\line_art_irl_11_v2.png" --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical
```

## 10.6 Regression-only run

```powershell
python run_benchmark.py --regression-only
```

---

# Phase 11: Definition Of Done

The hard-coded source-image behavior is resolved only when all items below are true.

## 11.1 Runtime Behavior

- [ ] `run_iter9.py` accepts `--image`.
- [ ] `run_benchmark.py` accepts `--image`.
- [ ] Neither script validates an image at import time.
- [ ] `assets/input_source_image.png` remains only as a backward-compatible default.
- [ ] Users can run `line_art_irl_11_v2.png` without copying or overwriting the default image.
- [ ] Regression-only benchmark behavior remains intact.

## 11.2 Metrics Behavior

- [ ] Metrics include `schema_version`.
- [ ] Metrics include `run_identity`.
- [ ] Metrics include `run_timing`.
- [ ] Metrics include `project_identity`.
- [ ] Metrics include `command_invocation`.
- [ ] Metrics include `source_image`.
- [ ] Metrics include `source_image.project_relative_path`.
- [ ] Metrics include `source_image.absolute_path`.
- [ ] Metrics include `source_image.sha256`.
- [ ] Metrics include `effective_config`.
- [ ] Metrics include `artifact_inventory`.
- [ ] Metrics include `validation_gates`.
- [ ] Metrics include `warnings_and_exceptions`.
- [ ] Metrics include `llm_review_summary`.

## 11.3 Artifact Behavior

- [ ] Output directories are image-specific by default.
- [ ] Smaller JSON artifacts include `artifact_metadata`.
- [ ] Smaller JSON artifacts link back to the metrics JSON.
- [ ] Existing repair-routing artifacts remain present:
  - `failure_taxonomy.json`
  - `repair_route_decision.json`
  - `visual_delta_summary.json`
  - `repair_overlay_<board>.png`

## 11.4 Documentation Behavior

- [ ] README shows explicit-image commands.
- [ ] README does not instruct users to overwrite `assets/input_source_image.png`.
- [ ] AGENTS.md contains the Source Image Runtime Contract.
- [ ] Documentation explains noncanonical vs manifest-validated images.

## 11.5 Test Behavior

- [ ] CLI contract tests pass.
- [ ] Source config tests pass.
- [ ] Import-time validation tests pass.
- [ ] Metrics provenance tests pass.
- [ ] Existing repair-routing tests pass.
- [ ] Regression-only benchmark passes.

---

# Phase 12: Codex Execution Prompt

Paste the following into OpenAI Codex:

```markdown
Implement the source-image runtime contract described below.

Repository context:
- This is the Mine-Streaker / Minesweeper image reconstruction repo.
- The late-stage repair routing architecture is already implemented.
- `run_iter9.py` is the main current reconstruction entry point.
- `run_benchmark.py` runs benchmark and regression validation.
- The current legacy behavior hard-codes `assets/input_source_image.png` in entry scripts.
- This is blocking clean use of new source images such as `assets/line_art_irl_11_v2.png`.

Goal:
Remove the architectural dependency on `assets/input_source_image.png` as the only runtime image.

The project must support:

```powershell
python run_iter9.py --image "assets\line_art_irl_11_v2.png" --out-dir "results\iter9_line_art_irl_11_v2" --board-w 300 --seed 42 --allow-noncanonical
```

and:

```powershell
python run_benchmark.py --image "assets\line_art_irl_11_v2.png" --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical
```

while preserving:

```powershell
python run_iter9.py
python run_benchmark.py --regression-only
```

Required changes:

1. Add `source_config.py`
   - Add `SourceImageConfig` dataclass.
   - Add `compute_file_sha256(path)`.
   - Add `project_relative_or_none(path, project_root)`.
   - Add `resolve_source_image_config(image_path, project_root=None, allow_noncanonical=False, manifest_path=None)`.
   - Record command arg, absolute path, project-relative path, name, stem, SHA-256, size bytes, noncanonical flag, and manifest path.

2. Refactor `assets/image_guard.py`
   - Preserve backward compatibility for `assets/input_source_image.png`.
   - Add or preserve CLI support for `--path`.
   - Add `--allow-noncanonical`.
   - Add `--manifest`.
   - Support custom images with `--allow-noncanonical`.
   - Support per-image manifest validation.
   - Return or expose structured validation info for metrics.
   - Do not force all runtime images to match the old default file.

3. Refactor `run_iter9.py`
   - Add argparse options:
     - `--image`, default `assets/input_source_image.png`
     - `--out-dir`, default image-specific output directory
     - `--board-w`, default 300
     - `--seed`, default 42
     - `--allow-noncanonical`
     - `--image-manifest`
     - optional `--run-tag`
   - Remove runtime dependency on a module-level `IMG`.
   - Move image validation inside `main()` after CLI parsing.
   - Use the parsed image path everywhere currently using the old global image.
   - Preserve existing repair-routing behavior and metrics.
   - Preserve existing output artifacts.
   - Add full metrics provenance blocks:
     - `schema_version`
     - `run_identity`
     - `run_timing`
     - `project_identity`
     - `command_invocation`
     - `source_image`
     - `source_image_analysis`
     - `effective_config`
     - `board_sizing`
     - `preprocessing_config`
     - `target_field_stats`
     - `weight_config`
     - `corridor_config`
     - `sa_config`
     - `repair_config`
     - `solver_summary`
     - `repair_route_summary`
     - `visual_quality_summary`
     - `runtime_phase_timing_s`
     - `environment`
     - `artifact_inventory`
     - `validation_gates`
     - `warnings_and_exceptions`
     - `llm_review_summary`

4. Refactor `run_benchmark.py`
   - Add argparse options:
     - `--image`, default `assets/input_source_image.png`
     - `--widths`, nargs `+`, default `[300, 360, 420]`
     - `--seeds`, nargs `+`, default `[300, 301, 302]`
     - `--out-dir`, default `results/benchmark`
     - `--allow-noncanonical`
     - `--image-manifest`
     - keep `--regression-only`
     - optionally add `--include-regressions`
   - Standard benchmark mode must use the parsed image path.
   - Regression-only mode must preserve the fixed known regression cases.
   - Benchmark result rows must include source image provenance.
   - Do not validate images at import time.

5. Add metadata to smaller route artifacts
   - Add `artifact_metadata` to:
     - `failure_taxonomy.json`
     - `repair_route_decision.json`
     - `visual_delta_summary.json`
   - Include:
     - `run_id`
     - `generated_at_utc`
     - `source_image_project_relative_path`
     - `source_image_sha256`
     - `metrics_path`

6. Update README.md
   - Show explicit-image commands.
   - Do not present overwriting `assets/input_source_image.png` as normal workflow.
   - Explain that `assets/input_source_image.png` is only a backward-compatible default.
   - Explain `--allow-noncanonical` and manifest validation.

7. Update AGENTS.md
   - Add a Source Image Runtime Contract:
     - Entry scripts must accept source images through explicit CLI arguments.
     - Do not require users to overwrite `assets/input_source_image.png`.
     - `assets/input_source_image.png` is only a backward-compatible default.
     - Image validation must happen after CLI parsing, not at import time.
     - Metrics must record source image path, project-relative path, absolute path, name, SHA-256, and canonical/noncanonical status.
     - Metrics must record timestamps, project identity, command invocation, effective config, artifact inventory, validation gates, and warnings.
     - Output directories must include image identity or an explicit user-provided output root.
     - Regression cases may use fixed image paths, but normal experiment runs must not.

8. Add tests
   - Add `tests/test_source_image_cli_contract.py`.
   - Add `tests/test_source_config.py` or combine source-config coverage into the CLI test file.
   - Test:
     - `run_iter9.py --help` exposes `--image`, `--out-dir`, `--board-w`, `--seed`, `--allow-noncanonical`, `--image-manifest`.
     - `run_benchmark.py --help` exposes `--image`, `--widths`, `--seeds`, `--out-dir`, `--allow-noncanonical`, `--image-manifest`, `--regression-only`.
     - Importing `run_iter9.py` does not call image validation.
     - Importing `run_benchmark.py` does not call image validation.
     - `resolve_source_image_config()` records command arg, absolute path, project-relative path, name, stem, SHA-256, and size bytes.
     - Metrics-construction helper includes required provenance blocks.

Validation commands:
```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
python run_benchmark.py --help
python assets/image_guard.py --path "assets\line_art_irl_11_v2.png" --allow-noncanonical
python run_iter9.py --image "assets\line_art_irl_11_v2.png" --out-dir "results\iter9_line_art_irl_11_v2" --board-w 300 --seed 42 --allow-noncanonical
python run_benchmark.py --image "assets\line_art_irl_11_v2.png" --widths 300 360 420 --seeds 11 22 33 --allow-noncanonical
python run_benchmark.py --regression-only
```

Do not:
- Do not require copying over `assets/input_source_image.png`.
- Do not remove existing repair-routing metrics.
- Do not remove existing repair-routing artifacts.
- Do not break `run_benchmark.py --regression-only`.
- Do not add new production dependencies.
- Do not perform unrelated refactors.
- Do not validate images at import time.
```

---

# Phase 13: Recommended Post-Implementation Review Prompt

After Codex completes the implementation, run a review using this prompt:

```markdown
Review the implementation for the source-image runtime contract.

Verify:
1. `assets/input_source_image.png` is only a backward-compatible default, not the only runtime source.
2. `run_iter9.py --image ...` uses the provided image everywhere.
3. `run_benchmark.py --image ...` uses the provided image in normal benchmark mode.
4. `run_benchmark.py --regression-only` still uses fixed known regression cases.
5. No image validation happens at import time.
6. Metrics JSON contains full source image provenance.
7. Metrics JSON contains run timing.
8. Metrics JSON contains project identity and git state.
9. Metrics JSON contains command invocation and effective config.
10. Metrics JSON contains artifact inventory, validation gates, warnings, and LLM review summary.
11. Smaller route artifacts include metadata linking back to the metrics file.
12. README and AGENTS.md no longer teach copying over `assets/input_source_image.png`.
13. Existing late-stage repair routing behavior remains intact.
14. Existing tests pass.
15. New CLI/source-image/provenance tests pass.

Output:
- Pass/fail table by file.
- Any remaining hard-coded `assets/input_source_image.png` usages, categorized as:
  - acceptable default
  - fixed regression case
  - unacceptable runtime dependency
- Required fixes if any unacceptable runtime dependency remains.
```

---

# Final Outcome

After this plan is implemented, the project should support first-class custom image runs like:

```powershell
python run_iter9.py --image "D:\Github\MineSweepResearchFilesFinalIteration\assets\line_art_irl_11_v2.png" --out-dir "results\iter9_line_art_irl_11_v2" --board-w 300 --seed 42 --allow-noncanonical
```

without any copying, renaming, or overwriting of:

```text
assets/input_source_image.png
```

The metrics JSON should then be able to prove:

```text
This exact run used this exact source image, from this exact project path,
at this exact time, with this exact command and config, producing these exact artifacts.
```
