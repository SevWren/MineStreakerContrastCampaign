# Iter9 Image Sweep Contract

## 1. Contract Purpose

This document defines the complete behavior contract for adding native Iteration 9 image-sweep mode to `run_iter9.py`.

The implementation covered by this contract adds one batch orchestration mode around the existing single-image Iter9 pipeline. The implementation does not change the reconstruction algorithm, source-image validation algorithm, board-sizing algorithm, solver algorithm, repair algorithm, simulated annealing algorithm, or report rendering algorithm.

## 2. Files Covered By This Contract

### 2.1 Files Allowed To Change

Only these files may be modified for this feature:

```text
run_iter9.py
README.md
AGENTS.md
tests/test_iter9_image_sweep_contract.py
```

### 2.2 Files Forbidden To Change

These files must not be modified:

```text
run_benchmark.py
source_config.py
assets/image_guard.py
board_sizing.py
core.py
corridors.py
pipeline.py
repair.py
report.py
sa.py
solver.py
list_unignored_files.py
test_runtime_entrypoint_source_image_contracts_and_deprecated_paths.py
tests/test_benchmark_layout.py
tests/test_digest_file_listing.py
tests/test_image_guard_contract.py
tests/test_repair_route_decision.py
tests/test_repair_visual_delta.py
tests/test_report_explanations.py
tests/test_route_artifact_metadata.py
tests/test_solver_failure_taxonomy.py
tests/test_source_config.py
tests/test_source_image_cli_contract.py
```

## 3. Existing Runtime Responsibilities

### 3.1 Existing `run_iter9.py` Responsibilities

`run_iter9.py` owns the Iter9 single-image runtime entry point.

Current single-image CLI flags:

```text
--image
--out-dir
--board-w
--seed
--allow-noncanonical
--image-manifest
--run-tag
```

Current single-image default source image:

```text
assets/input_source_image.png
```

Current default board width:

```text
300
```

Current default seed:

```text
42
```

Current result root constant:

```text
results/iter9
```

Current metrics schema version:

```text
metrics.v2.source_image_runtime_contract
```

### 3.2 Existing Supporting Module Responsibilities

The image-sweep feature must call existing module surfaces exactly as owned today:

| File | Existing responsibility used by image-sweep mode |
|---|---|
| `source_config.py` | Resolve source-image paths, compute SHA-256, build `SourceImageConfig`, produce source-image metrics blocks. |
| `assets/image_guard.py` | Validate source-image integrity and return validation details. |
| `board_sizing.py` | Derive board height from image aspect ratio and requested board width. |
| `core.py` | Load images, compute target fields, compute number fields, compute weights, validate board constraints. |
| `corridors.py` | Build adaptive mine-free corridor masks. |
| `sa.py` | Compile and run simulated annealing. |
| `solver.py` | Warm solver and solve board. |
| `repair.py` | Run Phase 1 repair. |
| `pipeline.py` | Route late-stage repair and write repair-route artifacts. |
| `report.py` | Render technical and explained final reports and repair overlays. |

## 4. New Image-Sweep Mode Overview

Image-sweep mode runs the existing Iter9 single-image pipeline once for each discovered source image.

Image-sweep mode is activated only by explicitly supplying:

```text
--image-dir <directory>
```

Image-sweep mode discovers source images from `--image-dir` using `--image-glob`.

Image-sweep mode writes one child run directory per discovered image under a batch root directory.

Image-sweep mode writes batch summary files at the batch root.

Image-sweep mode calls the same single-run helper used by normal single-image mode.

## 5. Required New Standard-Library Imports In `run_iter9.py`

Add these imports near the existing standard-library imports:

```python
import csv
import hashlib
```

No third-party dependency may be added.

## 6. Required Parser Construction Rule

`parse_args(...)` must disable abbreviated long options.

Use this exact parser construction:

```python
parser = argparse.ArgumentParser(
    description="Run Iter9 reconstruction pipeline.",
    allow_abbrev=False,
)
```

The implementation must not use `argparse.ArgumentParser(...)` without `allow_abbrev=False`.

## 7. New CLI Flags

Add these flags to `parse_args(...)`:

```python
parser.add_argument("--image-dir", default=None, help="Directory of source images for Iter9 image-sweep mode.")
parser.add_argument("--image-glob", default="*.png", help="Glob pattern used inside --image-dir. Default: *.png.")
parser.add_argument("--recursive", action="store_true", help="Recursively discover images under --image-dir.")
parser.add_argument("--out-root", default=None, help="Parent output directory for image-sweep child runs.")
parser.add_argument("--continue-on-error", action="store_true", help="Continue image sweep after a failed child run.")
parser.add_argument("--skip-existing", action="store_true", help="Skip child runs whose expected metrics file already exists.")
parser.add_argument("--max-images", type=int, default=None, help="Limit image sweep to the first N discovered images after sorting.")
```

## 8. CLI Mode Selection Contract

### 8.1 Single-Image Mode

Single-image mode is active when:

```python
args.image_dir is None
```

Single-image mode accepts these flags:

```text
--image
--out-dir
--board-w
--seed
--allow-noncanonical
--image-manifest
--run-tag
```

Single-image mode rejects these flags when explicitly supplied:

```text
--image-glob
--recursive
--out-root
--continue-on-error
--skip-existing
--max-images
```

Each rejected flag must raise `argparse` parser error with this exact message pattern:

```text
<flag> requires --image-dir
```

Example:

```text
--out-root requires --image-dir
```

### 8.2 Image-Sweep Mode

Image-sweep mode is active when:

```python
args.image_dir is not None
```

Image-sweep mode accepts these flags:

```text
--image-dir
--image-glob
--recursive
--out-root
--continue-on-error
--skip-existing
--max-images
--allow-noncanonical
--board-w
--seed
--run-tag
```

Image-sweep mode rejects these flags:

```text
--out-dir
--image
--image-manifest
```

`--image` is rejected only when explicitly supplied in the raw argv, because `--image` has the backward-compatible default `assets/input_source_image.png`.

`--image-manifest` is rejected only when explicitly supplied in the raw argv.

`--out-dir` is rejected when `args.out_dir is not None`.

## 9. CLI Validation Contract

### 9.1 Raw Argv Capture

`parse_args(argv)` must normalize raw argv with this exact logic:

```python
raw_argv = list(sys.argv[1:] if argv is None else argv)
args = parser.parse_args(raw_argv)
```

### 9.2 Explicit Flag Detection

Add this exact helper:

```python
def _explicit_flag_present(raw_argv: list[str], flag: str) -> bool:
    for token in raw_argv:
        if token == "--":
            break
        if token == flag or token.startswith(flag + "="):
            return True
    return False
```

The helper detects:

```text
--flag value
--flag=value
```

The helper stops scanning at:

```text
--
```

The helper does not match abbreviated flags. Abbreviated flags are rejected by `allow_abbrev=False`.

### 9.3 Required `parse_args(...)` Validation Block

Replace the final `return parser.parse_args(argv)` in `parse_args(...)` with this exact validation block:

```python
raw_argv = list(sys.argv[1:] if argv is None else argv)
args = parser.parse_args(raw_argv)

if args.max_images is not None and int(args.max_images) < 1:
    parser.error("--max-images must be >= 1")

if args.image_dir is None:
    sweep_only_flags = [
        "--image-glob",
        "--recursive",
        "--out-root",
        "--continue-on-error",
        "--skip-existing",
        "--max-images",
    ]
    for flag in sweep_only_flags:
        if _explicit_flag_present(raw_argv, flag):
            parser.error(f"{flag} requires --image-dir")
else:
    if args.out_dir is not None:
        parser.error("--out-dir cannot be used with --image-dir; use --out-root")
    if _explicit_flag_present(raw_argv, "--image"):
        parser.error("--image cannot be explicitly supplied with --image-dir")
    if _explicit_flag_present(raw_argv, "--image-manifest"):
        parser.error("--image-manifest cannot be used with --image-dir")

return args
```

## 10. Image Discovery Contract

Add this exact function to `run_iter9.py`:

```python
def discover_source_images(
    image_dir: Path,
    image_glob: str,
    *,
    recursive: bool = False,
    max_images: int | None = None,
) -> list[Path]:
    image_dir = Path(image_dir).resolve()
    if not image_dir.exists():
        raise FileNotFoundError(f"Image sweep directory not found: {image_dir}")
    if not image_dir.is_dir():
        raise NotADirectoryError(f"Image sweep path is not a directory: {image_dir}")

    matches = image_dir.rglob(image_glob) if recursive else image_dir.glob(image_glob)
    images = [path for path in matches if path.is_file()]
    images = sorted(images, key=lambda path: path.resolve().as_posix())

    if max_images is not None:
        images = images[: int(max_images)]

    if not images:
        raise ValueError(f"No source images matched {image_glob!r} under {image_dir.as_posix()}")

    return images
```

Discovery rules:

| Rule | Required behavior |
|---|---|
| Directory missing | Raise `FileNotFoundError`. |
| Path is not a directory | Raise `NotADirectoryError`. |
| Non-recursive discovery | Use `Path.glob(image_glob)`. |
| Recursive discovery | Use `Path.rglob(image_glob)`. |
| File filtering | Include only `path.is_file()`. |
| Sorting | Sort by `path.resolve().as_posix()`. |
| `max_images` | Apply after sorting. |
| Empty result | Raise `ValueError`. |
| Default case sensitivity | Preserve Python `Path.glob(...)` behavior. Do not add case-insensitive matching. |
| Image validation | Do not validate image contents in this function. |

## 11. Path Token Contract

### 11.1 Sanitized Path Token

Add this exact function near `sanitize_run_tag(...)`:

```python
def _sanitize_path_token(value: str, *, fallback: str = "item") -> str:
    token = sanitize_run_tag(value)
    return token if token else fallback
```

### 11.2 Path Hash Token

Add this exact function near `_sanitize_path_token(...)`:

```python
def _path_hash_token(path: Path, *, length: int = 8) -> str:
    text = path.resolve().as_posix().encode("utf-8")
    return hashlib.sha256(text).hexdigest()[: int(length)]
```

### 11.3 Markdown Table Cell Escaping

Add this exact function near summary-writing helpers:

```python
def _md_table_cell(value) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace("|", "\\|")
    text = text.replace("\r", " ")
    text = text.replace("\n", " ")
    return text
```

Every Markdown table cell in `iter9_image_sweep_summary.md` must be built through `_md_table_cell(...)`.

## 12. Child Output Directory Contract

### 12.1 Collision Detection Helper

Add this exact helper after `discover_source_images(...)`:

```python
def _colliding_sanitized_stem_tokens(paths: list[Path]) -> set[str]:
    counts: dict[str, int] = {}
    for path in paths:
        token = _sanitize_path_token(path.stem, fallback="image").casefold()
        counts[token] = counts.get(token, 0) + 1
    return {token for token, count in counts.items() if count > 1}
```

### 12.2 Child Directory Helper

Add this exact helper after `_colliding_sanitized_stem_tokens(...)`:

```python
def build_image_sweep_child_out_dir(
    out_root: Path,
    *,
    source_cfg: SourceImageConfig,
    board_label: str,
    seed: int,
    colliding_stem_tokens: set[str],
) -> Path:
    stem_token = _sanitize_path_token(source_cfg.stem, fallback="image")
    if stem_token.casefold() in colliding_stem_tokens:
        stem_token = f"{stem_token}_{source_cfg.sha256[:12]}_{_path_hash_token(source_cfg.absolute_path)}"
    child_name = f"{stem_token}_{board_label}_seed{int(seed)}"
    return out_root / child_name
```

### 12.3 Directory Naming Rules

When sanitized stem tokens are unique, the child directory name is:

```text
<sanitized_image_stem>_<board_width>x<board_height>_seed<seed>
```

When sanitized stem tokens collide after `casefold()`, the child directory name is:

```text
<sanitized_image_stem>_<source_sha256_first12>_<pathhash8>_<board_width>x<board_height>_seed<seed>
```

The collision suffix is required for:

```text
a b.png
a_b.png
Cat.png
cat.png
one/sample.png
two/sample.png
```

The path hash prevents collision when two files have the same sanitized stem and same image SHA-256.

## 13. Batch ID Contract

Add this exact function near `_build_run_id(...)`:

```python
def _build_image_sweep_batch_id(
    *,
    image_dir: Path,
    image_glob: str,
    board_w: int,
    seed: int,
    run_tag: str,
) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dir_token = _sanitize_path_token(image_dir.name, fallback="images")
    glob_token = _sanitize_path_token(image_glob, fallback="glob")
    batch_id = f"{stamp}_{dir_token}_{glob_token}_{int(board_w)}w_seed{int(seed)}"
    safe_tag = sanitize_run_tag(run_tag)
    if safe_tag:
        batch_id = f"{batch_id}_{safe_tag}"
    return batch_id
```

Batch ID requirements:

| Component | Required source |
|---|---|
| UTC timestamp | `datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")` |
| directory token | sanitized `image_dir.name` |
| glob token | sanitized `image_glob` |
| board width | `int(board_w)` with literal suffix `w` |
| seed | `int(seed)` with literal prefix `seed` |
| run tag | sanitized `run_tag`, appended only when non-empty |

## 14. Single-Run Extraction Contract

### 14.1 Required Function Signature

Create this function in `run_iter9.py`:

```python
def run_iter9_single(
    args: argparse.Namespace,
    *,
    source_cfg: SourceImageConfig,
    source_validation: dict,
    out_dir_path: Path,
    project_root: Path,
    sa_fn,
    raw_argv: list[str],
    started_wall: float,
    started_at_utc: str,
    warmup_s: float,
    batch_context: dict | None = None,
) -> dict:
    """
    Execute exactly one Iter9 run and return the final metrics document.
    This function preserves the current single-image Iter9 behavior while allowing
    batch mode to call the same implementation body.
    """
```

### 14.2 Responsibilities Inside `run_iter9_single(...)`

`run_iter9_single(...)` must perform exactly one Iter9 run.

It must:

1. Set `image_validation = dict(source_validation)` at the top.
2. Set `phase_timers: dict[str, float] = {"warmup": float(warmup_s)}`.
3. Call `out_dir_path.mkdir(parents=True, exist_ok=True)` as the first filesystem action.
4. Not reassign `out_dir_path`.
5. Build `run_id` with `_build_run_id(source_cfg.stem, int(args.board_w), int(args.seed), args.run_tag)`.
6. Print the existing Iter9 single-run banner.
7. Derive board size with `derive_board_from_width(...)`.
8. Load and preprocess image.
9. Build weights and corridors.
10. Run coarse SA.
11. Run fine SA.
12. Run refine SA.
13. Validate the board with `assert_board_valid(...)`.
14. Run Phase 1 repair.
15. Run late-stage routing.
16. Render technical and explained PNGs.
17. Save grid files.
18. Build flat metrics.
19. Build structured metrics with `build_metrics_document(...)`.
20. Write metrics JSON.
21. Return `metrics_doc`.

### 14.3 Responsibilities Forbidden Inside `run_iter9_single(...)`

`run_iter9_single(...)` must not:

```text
parse CLI arguments
call resolve_source_image_config(...)
call verify_source_image(...)
choose between --out-dir and default RESULTS_ROOT
call compile_sa_kernel()
call ensure_solver_warmed()
discover batch images
loop over batch images
write batch summaries
return integer status codes
```

### 14.4 Command Invocation Contract

Inside `run_iter9_single(...)`, command invocation must be constructed from the supplied `raw_argv` parameter:

```python
command_invocation = {
    "entry_point": "run_iter9.py",
    "argv": ["run_iter9.py", *[str(arg) for arg in raw_argv]],
}
```

No metrics block may use ambient `sys.argv`. The `raw_argv` parameter supplied to `run_iter9_single(...)` is the authoritative source for command invocation provenance.

### 14.5 Metrics Return Contract

At the end of `run_iter9_single(...)`, return:

```python
return metrics_doc
```

It must not return `0`.

## 15. `build_metrics_document(...)` Batch Context Contract

Modify the signature of `build_metrics_document(...)` by adding this keyword-only parameter after `source_image_validation`:

```python
batch_context: dict | None = None,
```

Immediately before `return document`, add:

```python
    if batch_context is not None:
        document["batch_context"] = dict(batch_context)
```

Single-image mode must pass `batch_context=None`.

Image-sweep child runs must pass populated `batch_context`.

`batch_context` must not be flattened into `flat_metrics`.

## 16. Main Function Contract

Replace:

```python
def main() -> int:
```

with:

```python
def main(argv: list[str] | None = None) -> int:
```

`main(...)` must implement this exact control flow:

```python
def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parse_args(raw_argv)
    started_wall = time.perf_counter()
    started_at_utc = _utc_now_z()
    project_root = Path(__file__).resolve().parent

    if args.image_dir is not None:
        return run_iter9_image_sweep(args, raw_argv=raw_argv, project_root=project_root)

    source_cfg = resolve_source_image_config(
        args.image,
        project_root=project_root,
        allow_noncanonical=args.allow_noncanonical,
        manifest_path=args.image_manifest,
    )
    source_validation = verify_source_image(
        str(source_cfg.absolute_path),
        halt_on_failure=True,
        verbose=True,
        allow_noncanonical=args.allow_noncanonical,
        manifest_path=args.image_manifest,
        return_details=True,
    )

    run_id = _build_run_id(source_cfg.stem, int(args.board_w), int(args.seed), args.run_tag)
    out_dir_path = (
        Path(args.out_dir).expanduser().resolve()
        if args.out_dir
        else (project_root / RESULTS_ROOT / run_id).resolve()
    )

    phase_start = time.perf_counter()
    sa_fn = compile_sa_kernel()
    ensure_solver_warmed()
    warmup_s = time.perf_counter() - phase_start

    run_iter9_single(
        args,
        source_cfg=source_cfg,
        source_validation=source_validation,
        out_dir_path=out_dir_path,
        project_root=project_root,
        sa_fn=sa_fn,
        raw_argv=raw_argv,
        started_wall=started_wall,
        started_at_utc=started_at_utc,
        warmup_s=warmup_s,
        batch_context=None,
    )
    return 0
```

The bottom of file must remain:

```python
if __name__ == "__main__":
    raise SystemExit(main())
```

## 17. Batch Row Schema Contract

Add this exact constant:

```python
IMAGE_SWEEP_SUMMARY_FIELDS = [
    "batch_index",
    "image_path",
    "image_name",
    "image_stem",
    "source_image_sha256",
    "status",
    "child_run_dir",
    "metrics_path",
    "best_artifact_to_open_first",
    "board",
    "seed",
    "n_unknown",
    "coverage",
    "solvable",
    "mean_abs_error",
    "repair_route_selected",
    "error_type",
    "error_message",
]
```

Every row in JSON and CSV must contain exactly these keys in this order.

Permitted row status values:

```text
succeeded
failed
skipped_existing
```

## 18. Row Helper Signatures and Mapping Contract

### 18.1 Required Row Helper Signatures

Add these exact function signatures to `run_iter9.py`:

```python
def _image_sweep_success_row(
    *,
    batch_index: int,
    source_cfg: SourceImageConfig,
    child_run_dir: Path,
    metrics_doc: dict,
    project_root: Path,
) -> dict:
```

```python
def _image_sweep_failure_row(
    *,
    batch_index: int,
    image_path: Path,
    source_cfg: SourceImageConfig | None,
    child_run_dir: Path | None,
    board_label: str | None,
    seed: int,
    error: BaseException,
    project_root: Path,
) -> dict:
```

```python
def _image_sweep_skipped_existing_row(
    *,
    batch_index: int,
    source_cfg: SourceImageConfig,
    child_run_dir: Path,
    metrics_path: Path,
    board_label: str,
    seed: int,
    project_root: Path,
) -> dict:
```

### 18.2 Required Mapping Rules

All three row helpers must return exactly the keys in `IMAGE_SWEEP_SUMMARY_FIELDS`.

**Success row rules:**

1. `status` must be `"succeeded"`.
2. `error_type` must be `None`.
3. `error_message` must be `None`.
4. Metric-bearing fields (`n_unknown`, `coverage`, `solvable`, `mean_abs_error`, `repair_route_selected`) must be extracted from `metrics_doc`.
5. `best_artifact_to_open_first` must be extracted from `metrics_doc["llm_review_summary"]` when available, else `None`.

**Failure row rules:**

1. `status` must be `"failed"`.
2. `error_type` must be `type(error).__name__`.
3. `error_message` must be `str(error)`.
4. All metric-bearing fields must be `None` when unavailable.
5. `image_path` must be the resolved absolute POSIX path string when `source_cfg` is available, else the raw path string.

**Skipped row rules:**

1. `status` must be `"skipped_existing"`.
2. `error_type` must be `None`.
3. `error_message` must be `None`.
4. `metrics_path` must always be set to the expected metrics path string.
5. Metric-bearing fields may be hydrated from the existing metrics JSON when readable; otherwise must be `None`.

### 18.3 Per-Image Source Config Resolution Placement

`discover_source_images(...)` returns an ordered `Path` list only.

`resolve_source_image_config(...)` must run inside the child loop, one image at a time.

No pre-loop bulk resolution list is permitted.

Any resolution failure becomes one failed row for that image and follows the fail-fast or continue-on-error policy.

## 19. Batch Context Schema Contract

Every successful image-sweep child metrics JSON must contain `batch_context`.

`batch_context` must contain exactly these keys:

```text
schema_version
batch_mode
batch_id
batch_index
batch_total
images_discovered
image_dir
image_glob
recursive
batch_out_root
child_run_dir
continue_on_error
skip_existing
max_images
batch_warmup_s
child_warmup_s
```

Required values:

| Key | Required value |
|---|---|
| `schema_version` | `iter9_image_sweep_context.v1` |
| `batch_mode` | `iter9_image_sweep` |
| `batch_id` | batch ID returned by `_build_image_sweep_batch_id(...)` |
| `batch_index` | one-based child index |
| `batch_total` | number of discovered images |
| `images_discovered` | number of discovered images |
| `image_dir` | `_relative_or_absolute(image_dir, project_root)` |
| `image_glob` | `args.image_glob` |
| `recursive` | `bool(args.recursive)` |
| `batch_out_root` | `_relative_or_absolute(out_root, project_root)` |
| `child_run_dir` | `_relative_or_absolute(child_out_dir, project_root)` |
| `continue_on_error` | `bool(args.continue_on_error)` |
| `skip_existing` | `bool(args.skip_existing)` |
| `max_images` | `int(args.max_images)` when supplied, otherwise `None` |
| `batch_warmup_s` | measured batch warmup time as float |
| `child_warmup_s` | `0.0` |

Single-image metrics JSON must not contain `batch_context`.

## 20. Batch Summary Writer Contract

### 20.1 Required Function Signature

Add this exact function signature:

```python
def write_iter9_image_sweep_summaries(
    *,
    out_root: Path,
    batch_id: str,
    image_dir: str,
    image_glob: str,
    recursive: bool,
    board_w: int,
    seed: int,
    started_at_utc: str,
    finished_at_utc: str,
    duration_wall_s: float,
    batch_warmup_s: float,
    rows: list[dict],
    images_discovered: int,
) -> dict:
```

`image_dir` is `str`, not `Path`.

The function must not call `image_dir.as_posix()`.

### 20.2 Required Output Files

The function must write these files under `out_root`:

```text
iter9_image_sweep_summary.json
iter9_image_sweep_summary.csv
iter9_image_sweep_summary.md
```

### 20.3 Atomic Write Contract

The function must use these atomic helpers:

```text
_atomic_save_json(...)
_atomic_save_csv(...)
_atomic_save_text(...)
```

### 20.4 JSON Summary Schema

The JSON summary root object must contain:

```text
schema_version
batch_identity
batch_timing
images_discovered
rows_recorded
runs_attempted
runs_succeeded
runs_failed
runs_skipped
rows
```

Required values:

| Key | Required value |
|---|---|
| `schema_version` | `iter9_image_sweep.v1` |
| `images_discovered` | integer argument `images_discovered` |
| `rows_recorded` | `len(rows)` after normalization |
| `runs_attempted` | count of `succeeded` plus `failed` rows |
| `runs_succeeded` | count of `succeeded` rows |
| `runs_failed` | count of `failed` rows |
| `runs_skipped` | count of `skipped_existing` rows |
| `rows` | normalized row list |

`batch_identity` must contain exactly:

```text
batch_id
entry_point
image_dir
image_glob
recursive
out_root
board_width
seed
```

`batch_timing` must contain exactly:

```text
started_at_utc
finished_at_utc
duration_wall_s
batch_warmup_s
```

### 20.5 Row Normalization Contract

Rows must be materialized using exact `IMAGE_SWEEP_SUMMARY_FIELDS` projection before writing:

```python
normalized_rows = [
    {field: row.get(field) for field in IMAGE_SWEEP_SUMMARY_FIELDS}
    for row in rows
]
```

The JSON `rows` field must contain `normalized_rows`.

The CSV must use `IMAGE_SWEEP_SUMMARY_FIELDS` as the field order. CSV rows and JSON rows must contain the same normalized key set and key order.

### 20.6 Markdown Summary Escaping Contract

Every cell in the Markdown table must call `_md_table_cell(...)`.

Markdown row construction must use this pattern:

```python
for row in rows:
    md_lines.append(
        "| "
        + " | ".join(
            [
                _md_table_cell(row.get("batch_index")),
                _md_table_cell(row.get("status")),
                _md_table_cell(row.get("image_path")),
                _md_table_cell(row.get("board")),
                _md_table_cell(row.get("seed")),
                _md_table_cell(row.get("n_unknown")),
                _md_table_cell(row.get("coverage")),
                _md_table_cell(row.get("solvable")),
                _md_table_cell(row.get("repair_route_selected")),
                _md_table_cell(row.get("best_artifact_to_open_first")),
                _md_table_cell(row.get("error_message")),
            ]
        )
        + " |"
    )
```

## 21. Batch Runner Contract

### 21.1 Required Function Signature

Add this exact function:

```python
def run_iter9_image_sweep(
    args: argparse.Namespace,
    *,
    raw_argv: list[str],
    project_root: Path,
) -> int:
```

### 21.2 Discovery Failure Contract

If `discover_source_images(...)` raises before any images are discovered, `run_iter9_image_sweep(...)` must still write batch summary files before returning `1`.

Required summary contents when discovery fails:

1. `images_discovered = 0`
2. `runs_attempted = 0`, `runs_failed = 1`, `runs_succeeded = 0`, `runs_skipped = 0`
3. One failed row containing available context (`image_path`, `error_type`, `error_message`)
4. Return code `1`

No exception may be silently swallowed. Every discovery exception must be captured into summary row data and then reported via return code.

### 21.3 Batch Warmup Contract

After image discovery and output root creation, batch mode must call:

```python
warmup_start = time.perf_counter()
sa_fn = compile_sa_kernel()
ensure_solver_warmed()
batch_warmup_s = time.perf_counter() - warmup_start
```

If `compile_sa_kernel()` or `ensure_solver_warmed()` raises, `run_iter9_image_sweep(...)` must write batch summary files before returning `1`.

Required summary contents when warmup fails:

1. `images_discovered` reflects the count from discovery
2. `runs_attempted = 0`, `runs_failed = 1`, `runs_succeeded = 0`, `runs_skipped = 0`
3. One failed row for the warmup failure
4. Return code `1`

### 21.4 Per-Image Validation Contract

Inside the batch loop, source-image validation must call:

```python
source_validation = verify_source_image(
    str(source_cfg.absolute_path),
    halt_on_failure=False,
    verbose=True,
    allow_noncanonical=args.allow_noncanonical,
    manifest_path=None,
    return_details=True,
)
if not source_validation.get("ok"):
    raise ValueError(f"Source image validation failed: {source_cfg.absolute_path.as_posix()}")
```

`halt_on_failure=True` is forbidden inside the batch loop.

`SystemExit` must not be used for normal child validation failure.

### 21.5 Per-Image Execution Contract

For each discovered image, execution must follow this exact ordering:

1. Resolve image through `resolve_source_image_config(...)`.
2. Validate image through `verify_source_image(... halt_on_failure=False ...)`.
3. Derive board size with `derive_board_from_width(...)`.
4. Build full board label as `"<board_width>x<board_height>"`.
5. Build child output directory with `build_image_sweep_child_out_dir(...)`.
6. Build expected metrics path as `child_out_dir / f"metrics_iter9_{board_label}.json"`.
7. If `--skip-existing` and that path exists: append skipped row and continue.
8. Build `batch_context`.
9. Call `run_iter9_single(...)`.
10. Append success row on success.
11. Append failed row on exception.
12. Stop after first failed row unless `--continue-on-error` is true.

The expected metrics path must be derived using the full board label (step 6) before the skip decision (step 7). Pre-loop bulk resolution of all source configs is forbidden.

### 21.6 Return Code Contract

`run_iter9_image_sweep(...)` returns:

```text
0 when no child failed
1 when at least one child failed
```

Skipped rows do not make the return code `1`.

### 21.7 Fail-Fast Summary Contract

For any child exception other than `KeyboardInterrupt`, `run_iter9_image_sweep(...)` must:

1. set `any_failed = True`;
2. append a failed row;
3. print a failed-child message;
4. break when `args.continue_on_error` is false;
5. write all batch summary files before returning `1`.

### 21.8 KeyboardInterrupt Contract

`KeyboardInterrupt` must be re-raised.

Do not catch `KeyboardInterrupt` as a normal failed row.

## 22. Artifact Filename Contract

Every single-image run directory and every sweep child run directory must preserve these filenames:

```text
metrics_iter9_<board>.json
grid_iter9_<board>.npy
grid_iter9_latest.npy
iter9_<board>_FINAL.png
iter9_<board>_FINAL_explained.png
repair_overlay_<board>.png
repair_overlay_<board>_explained.png
failure_taxonomy.json
repair_route_decision.json
visual_delta_summary.json
```

No image identity may be added to these filenames.

Image identity belongs in:

```text
child output directory name
source_image metrics block
source_image_validation metrics block
batch_context
batch summary rows
```

## 23. Documentation Contract

### 23.1 README Insertion Point

Insert the image-sweep section immediately after the paragraph ending:

```text
The technical PNGs are the detailed audit view. The explained PNGs are additive first-look review artifacts for humans and LLMs, and they do not replace the technical reports.
```

Insert before:

```text
## Beginner Workflow
```

### 23.2 AGENTS Insertion Point

Insert the image-sweep contract section immediately after:

```text
## Source Image Runtime Contract
```

Do not remove or rewrite existing source-image runtime bullets.

## 24. Validation Commands

The implementation must pass:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python run_iter9.py --help
```

The following single-image validation command uses the canonical asset path `assets/tessa_line_art_stiletto.png`, which is present in the repository as of April 28, 2026:

```powershell
python run_iter9.py --image assets/tessa_line_art_stiletto.png --allow-noncanonical --out-dir results/tmp_validation_single
```

These commands must fail with `argparse` errors:

```powershell
python run_iter9.py --out-root results/x
python run_iter9.py --image-glob "*.jpg"
python run_iter9.py --recursive
python run_iter9.py --continue-on-error
python run_iter9.py --skip-existing
python run_iter9.py --max-images 2
python run_iter9.py --image-dir assets --out-dir results/x
python run_iter9.py --image-dir assets --image assets/foo.png
python run_iter9.py --image-dir assets --image=assets/foo.png
python run_iter9.py --image-dir assets --image-manifest assets/SOURCE_IMAGE_HASH.json
python run_iter9.py --image-dir assets --max-images 0
python run_iter9.py --image-g "*.jpg"
python run_iter9.py --rec
python run_iter9.py --image-dir assets --image-man x.json
```

The following manual traceability inspection command confirms that no forbidden file was modified:

```powershell
git diff --name-only
```

The output must not include any filename from section 2.2.

## 25. Completion Gate

The feature is complete only when all statements below are true:

```text
run_iter9.py --help shows every sweep flag.
Single-image mode still accepts every existing single-image flag.
Single-image mode rejects every sweep-only flag when --image-dir is absent.
Image-sweep mode rejects explicit --image.
Image-sweep mode rejects explicit --image-manifest.
Image-sweep mode rejects --out-dir.
Abbreviated long options are rejected.
Image discovery is deterministic and sorted.
Child directory names include full board labels.
Child directory names cannot collide after sanitization and casefolding.
Batch validation failures become failed rows.
Discovery failures write batch summary files before returning 1.
Warmup failures write batch summary files before returning 1.
Batch fail-fast writes JSON, CSV, and Markdown summaries before returning 1.
--continue-on-error attempts all discovered images.
--skip-existing skips child runs with existing metrics files.
--skip-existing uses the derived full board label before the skip decision.
resolve_source_image_config(...) is called inside the child loop, not before it.
Row helpers return exactly IMAGE_SWEEP_SUMMARY_FIELDS keys.
Success rows set error_type and error_message to None.
Failure rows set error_type and error_message from the caught exception.
Summary JSON rows are normalized through IMAGE_SWEEP_SUMMARY_FIELDS projection.
CSV field order matches IMAGE_SWEEP_SUMMARY_FIELDS order.
Single-image metrics do not contain batch_context.
Successful sweep child metrics contain complete batch_context.
Batch summary Markdown table cells are escaped.
Existing Iter9 artifact filenames are unchanged.
No forbidden file is modified.
All tests pass.
```
