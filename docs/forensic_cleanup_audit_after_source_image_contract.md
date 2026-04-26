# Forensic Cleanup Audit After Source-Image Runtime Contract Implementation
**Input audited:** `/mnt/data/digest.txt`  
**Generated:** 2026-04-26T23:28:33Z  
**Audit purpose:** identify every code/documentation line or contiguous line range that should be cleaned up after completion of the source-image runtime contract and late-stage repair-routing work.
---
## Audit Scope
- Parsed file sections from digest: **34**.
- Line numbers below are **line numbers within each file section in `digest.txt`**.
- This is a cleanup ledger, not a claim that every listed item is a runtime bug.
- Files with no source-contract cleanup are listed separately under **Clean / No Immediate Cleanup Found**.

### Files Parsed
- `README.md` — 578 lines
- `AGENTS.md` — 105 lines
- `board_sizing.py` — 60 lines
- `core.py` — 356 lines
- `corridors.py` — 160 lines
- `LICENSE` — 23 lines
- `list_unignored_files.py` — 141 lines
- `pipeline.py` — 380 lines
- `repair.py` — 683 lines
- `report.py` — 217 lines
- `run_benchmark.py` — 1060 lines
- `run_iris3d_visual_report.py` — 1753 lines
- `run_iter9.py` — 823 lines
- `run_repair_only_from_grid.py` — 798 lines
- `sa.py` — 207 lines
- `solver.py` — 568 lines
- `source_config.py` — 89 lines
- `archives/run_contrast_preprocessing_study.py.old` — 320 lines
- `archives/Timeout Theory Campaign Plan line_art_irl_9 20min budget.md` — 736 lines
- `assets/image_guard.py` — 374 lines
- `docs/codex_late_stage_repair_routing_implementation_status.md` — 696 lines
- `docs/codex_late_stage_repair_routing_plan.md` — 1510 lines
- `docs/implement_clarified_source_image_runtime_contract.md` — 196 lines
- `docs/implement_clarified_source_image_runtime_contract_implementation_checklist.md` — 704 lines
- `docs/industry_standard_plan_remove_hardcoded_input_source_image.md` — 1834 lines
- `tests/test_benchmark_layout.py` — 91 lines
- `tests/test_digest_file_listing.py` — 46 lines
- `tests/test_image_guard_contract.py` — 131 lines
- `tests/test_repair_route_decision.py` — 52 lines
- `tests/test_repair_visual_delta.py` — 30 lines
- `tests/test_route_artifact_metadata.py` — 53 lines
- `tests/test_solver_failure_taxonomy.py` — 49 lines
- `tests/test_source_config.py` — 56 lines
- `tests/test_source_image_cli_contract.py` — 175 lines

---
## Severity Legend

| Severity | Meaning |
|---|---|
| P1 | Cleanup needed because it can mislead users/LLMs, preserve legacy behavior, or cause contract drift. |
| P2 | Structural cleanup / bloat reduction / duplicated code; not necessarily breaking today. |
| P3 | Historical or optional cleanup; safe to defer if intentionally archived. |

---
## Executive Findings

1. **The main runtime entry points mostly satisfy the new source-image contract**, but cleanup debt remains in documentation, older orchestration scripts, and duplicate helper code.
2. **The largest remaining contract risk is documentation drift**: README and AGENTS still contain stale artifact names, stale validation instructions, or pre-implementation wording.
3. **The largest code bloat risk is duplicated orchestration** across `run_iter9.py`, `run_benchmark.py`, `run_iris3d_visual_report.py`, and `run_repair_only_from_grid.py`.
4. **The highest-value correctness cleanup is source path resolution** in `source_config.py` and `assets/image_guard.py`, because relative paths currently depend on process CWD in places where project-root behavior is safer.
5. **Archived and historical docs should either be clearly marked historical or moved under a docs/archive policy**, otherwise future LLM agents may treat old plans as active instructions.

---
## Cleanup Ledger

| File | Lines | Severity | Problem | Required cleanup |
|---|---:|---|---|---|
| `README.md` | `43` | P1 | README claims metrics include `source_image_validation`, but `run_iter9.py` metrics currently do not emit a top-level `source_image_validation` block. | Either add top-level `source_image_validation` to Iter9 metrics or change README wording to match actual Iter9 JSON. Prefer adding the field for consistency with benchmark metrics. |
| `README.md` | `101-120` | P1 | Repository layout is stale: it omits `source_config.py`, `tests/`, and `archives/`, while listing `Larger_boards_fidelity_iteration/`, which is not present in this digest. | Rewrite repository layout from the current directory tree. |
| `README.md` | `124-139` | P1 | Main runtime module table omits `source_config.py` and still lists `run_contrast_preprocessing_study.py` as an active root script even though the digest only has `archives/run_contrast_preprocessing_study.py.old`. | Add `source_config.py`; remove or relocate contrast-study entry under archive/deprecated notes. |
| `README.md` | `199-212` | P1 | Quick Start output description still uses generic legacy artifact names (`grid_<board>.npy`, `metrics_<board>.json`, `visual_<board>.png`, `report_<board>.png`) instead of the new Iter9 run-specific directory and preserved Iter9 filenames. | Update to `results/iter9/<run_id>/metrics_iter9_<board>.json`, `grid_iter9_<board>.npy`, `grid_iter9_latest.npy`, `iter9_<board>_FINAL.png`, `repair_overlay_<board>.png`, and route JSON files. |
| `README.md` | `377-397` | P2 | Pipeline direction describes late-stage routing as future-facing and target artifacts as future artifacts, but the route artifacts are now implemented. | Change wording from future direction to current architecture, or move this section to historical/campaign notes. |
| `README.md` | `503-505` | P1 | Troubleshooting directs users to validate `assets/input_source_image.png` for board-sizing mismatch, which re-centers the old default instead of the actual source image used for the run. | Replace with `python assets/image_guard.py --path <same path passed to --image> [--allow-noncanonical|--manifest ...]`; mention default only if `--image` was omitted. |
| `README.md` | `515-526` | P2 | Troubleshooting references generic `metrics_<board>.json` and `visual_<board>.png`; Iter9 outputs use `metrics_iter9_<board>.json` and `iter9_<board>_FINAL.png`. | Update artifact names or distinguish Iter9 vs benchmark artifact naming. |
| `README.md` | `547-550` | P2 | Recommended reading order references `docs/project_result_summary.md` and `results/line_art_campaigns.md`, which are not present in the digest. | Verify those files exist outside the digest or replace with current docs that are present. |
| `README.md` | `570-575` | P2 | Roadmap lists already-implemented or partially-implemented items as future work: failure taxonomy, late-stage routing, repair overlay, line_art_irl_9 regression promotion. | Rewrite roadmap around remaining work: quality regression on `420x311_seed22`, visual-delta gates, shared runner extraction, docs cleanup. |
| `AGENTS.md` | `11-13` | P1 | Project structure references root `run_contrast_preprocessing_study.py`, `input_source_image_research.png`, and saturation docs that are not present in the current digest. | Update structure to current files; move removed/deprecated assets and docs to an explicit historical note only if they still exist elsewhere. |
| `AGENTS.md` | `31-33` | P1 | Command sequence validates `line_art_irl_11_v2.png` but then runs `python run_iter9.py` without `--image`, which uses the default image instead of the validated image. | Change to `python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical` and matching benchmark command. |
| `AGENTS.md` | `48-58` | P1 | Validation section says there is no dedicated `tests/` suite, but the digest contains a tests directory with multiple contract tests. | Replace this section with `python -m unittest discover -s tests -p "test_*.py"` plus the acceptance commands. |
| `AGENTS.md` | `84-96` | P2 | Saturation Campaign Rules reference `docs/saturation_run_matrix.md` and `results/saturation_matrix_TEMPLATE/...`, neither of which is present in the digest. | Archive this section, mark it historical, or replace with current benchmark/source-image contract validation rules. |
| `source_config.py` | `68` | P1 | Relative `image_path` is resolved against the current working directory, not `project_root`. This can break `--image assets/...` if the script is invoked from outside the repo root. | When `project_root` is supplied and `image_path` is relative, resolve it as `Path(project_root) / image_path` before `.resolve()`. |
| `source_config.py` | `86` | P2 | `manifest_path` is serialized with `Path(manifest_path).as_posix()` but is not resolved relative to `project_root`; on non-Windows hosts a backslash path may remain unnormalized. | Normalize manifest path with the same project-root-aware logic and emit a forward-slash absolute or project-relative path consistently. |
| `assets/image_guard.py` | `17-18,247-258` | P1 | Default image and manifest paths are resolved from the process CWD, not from the repository root. Running the script from another directory can validate the wrong path or fail unexpectedly. | Define repo root from `Path(__file__).resolve().parents[1]`; resolve default image and manifest relative to that root. |
| `assets/image_guard.py` | `84-97,335-351` | P2 | Image hash/stat computation is duplicated in `_compute_stats()` and `compute_image_hashes()`. | Make `compute_image_hashes()` call `_compute_stats()` and add only compatibility extras such as MD5 if still needed. |
| `assets/image_guard.py` | `86,338` | P2 | `Image.open(...)` is used without a context manager in two hash/stat paths. | Use `with Image.open(path) as img:` and convert/copy the array inside the context. |
| `assets/image_guard.py` | `199-239` | P2 | Missing-file and not-a-file branches assign `validation_mode='noncanonical_allowed'`, which is semantically misleading for filesystem failures. | Keep the public schema if required, but add an explicit error warning/code such as `SOURCE_IMAGE_NOT_FOUND` or `SOURCE_IMAGE_NOT_FILE` so LLM review is not misled. |
| `assets/image_guard.py` | `285-289` | P1 | When a non-default image lacks a manifest and noncanonical mode is not allowed, the code still sets `validation_mode='noncanonical_allowed'` before failing. | Use a clearer failure marker in warnings/errors, or add `noncanonical_allowed=False` plus a structured error warning such as `NONCANONICAL_SOURCE_REJECTED`. |
| `assets/image_guard.py` | `216-218,323-327` | P2 | Library function calls `sys.exit(1)` when `halt_on_failure=True`; this is legacy-compatible but awkward for callers that want exceptions/details. | Keep legacy behavior for public compatibility, but add an exception-returning lower-level helper and have CLI handle `SystemExit`. |
| `pipeline.py` | `6` | P2 | Manual `sys.path.insert(...)` points three directories upward and is likely leftover import scaffolding. | Remove if not required, or replace with normal package/import strategy. |
| `pipeline.py` | `30-38` | P2 | Atomic JSON/NPY helpers duplicate equivalent logic in `run_iter9.py`, `run_benchmark.py`, `run_iris3d_visual_report.py`, and `run_repair_only_from_grid.py`. | Extract shared `atomic_write_json`, `atomic_write_npy`, and `atomic_render` helpers into a small utility module. |
| `pipeline.py` | `202-378` | P1 | `run_board()` is a legacy full orchestration path using Iter2/asymmetric settings, old metrics shape, old artifact names, and no source-image provenance contract. | Either archive/remove `run_board()` if unused, or update it to accept `SourceImageConfig`, image validation details, provenance-rich metrics, and the same artifact metadata contract. |
| `pipeline.py` | `217-218` | P1 | `run_board()` validates `img_path` through `verify_source_image()` without `allow_noncanonical`, `manifest_path`, or structured returned details. | Add parameters or remove this legacy path. Do not leave custom images dependent on the environment variable fallback. |
| `pipeline.py` | `361-364` | P1 | `run_board()` writes `metrics_iterX_label.json`, `grid_iterX_label.npy`, and final PNG without the new run-id directory/provenance policy. | If keeping this path, align artifact layout with current run-specific policy or mark as deprecated. |
| `core.py` | `51-61` | P3 | `compute_edge_weights()` is retained for compatibility but is not used by active runtime paths in this digest. | Mark as deprecated/experimental or move to archive once compatibility is no longer needed. |
| `core.py` | `63-176` | P3 | `compute_asymmetric_weights()` appears to be used only by legacy `pipeline.run_board()`. | If `pipeline.run_board()` is archived, archive this or explicitly mark as legacy Iter2 support. |
| `core.py` | `178-221` | P2 | `compute_cluster_break_weights()` has no runtime references in the digest. | Remove, archive, or add tests/documented call sites before keeping it in active core primitives. |
| `core.py` | `269-333` | P2 | `load_image_smart_v2()` is unused in the digest and imports optional `skimage` inside the function. | Move to archived experiment code or mark experimental; do not leave dormant optional-dependency code in active core without tests. |
| `repair.py` | `49` | P2 | `run_phase1_repair()` accepts `weights` but never uses it. | Remove the parameter in a coordinated API cleanup or mark it reserved/backward-compatible; update callers/tests when safe. |
| `repair.py` | `164-274` | P3 | `run_phase2_mesa_repair()` remains as compatibility code after main routing moved to `run_phase2_full_repair()`. | Keep only if tests/docs prove compatibility need; otherwise mark deprecated or move to archive. |
| `repair.py` | `333-519` | P2 | `run_last100_repair()` overlaps conceptually with a separate `run_last100_repair()` implementation in `run_repair_only_from_grid.py`. | Consolidate to a single implementation in `repair.py`; make repair-only runner call it. |
| `run_iter9.py` | `83-101` | P2 | Atomic write/render helpers are duplicated with `run_benchmark.py` and older scripts. | Extract to shared utility module after current contract behavior is stable. |
| `run_iter9.py` | `118-119` | P3 | `_sanitize_run_tag()` is only a wrapper around public `sanitize_run_tag()`. | Remove wrapper and call `sanitize_run_tag()` directly. |
| `run_iter9.py` | `154-172` | P2 | `_source_image_analysis()` opens the image without a context manager. | Use `with PILImage.open(path) as image:` and copy required data before leaving the context. |
| `run_iter9.py` | `187-201` | P2 | `_environment_summary()` sets `numba_num_threads` to `None` instead of capturing actual Numba thread information. | Use safe `numba.get_num_threads()` / threading-layer helpers like the older visual report script, or remove the field. |
| `run_iter9.py` | `307-817` | P2 | `main()` is a 500+ line orchestration function. The implementation is correct but bloated after adding source-image/provenance logic. | Extract stages: resolve/validate source, build target/corridors, run SA, repair route, write artifacts, build metrics. |
| `run_iter9.py` | `641-644` | P2 | `command_invocation.argv` reads ambient `sys.argv`, which makes tests and programmatic calls less reproducible. | Allow `main(argv=None)` and pass the parsed raw argv into metrics, as `run_benchmark.py` partially does. |
| `run_iter9.py` | `645-646,786-811` | P1 | Iter9 metrics do not emit a top-level `source_image_validation` block, while README says metrics include it and benchmark child metrics do include it. | Add top-level `source_image_validation=image_validation` to `build_metrics_document()` inputs/output, or update README and benchmark for one consistent schema. |
| `run_benchmark.py` | `100-149` | P2 | UTC/path/atomic/render helpers duplicate `run_iter9.py`. | Extract shared helper module after behavior is stable. |
| `run_benchmark.py` | `231-326` | P2 | `_build_child_metrics_document()` duplicates much of `run_iter9.py::build_metrics_document()` but with a different schema quality level. | Create a shared provenance/metrics builder or make benchmark call the Iter9 builder with benchmark-specific additions. |
| `run_benchmark.py` | `250-253` | P1 | Benchmark child `project_identity` lacks `git_commit`, `git_branch`, and `git_dirty`, unlike the intended provenance-rich metrics. | Reuse `run_iter9` git metadata logic or shared helper. |
| `run_benchmark.py` | `254` | P2 | Benchmark child `command_invocation` uses ambient `sys.argv`; programmatic calls via `main(argv=...)` may record the wrong command. | Pass raw argv from `main()` / `parse_args()` into child metrics and summaries. |
| `run_benchmark.py` | `256,645-653` | P1 | `source_image_analysis` is populated with target-field stats, not actual source image facts. | Compute real source image analysis or rename/remove this field; keep target stats under `target_field_stats` only. |
| `run_benchmark.py` | `266` | P1 | `preprocessing_config` omits piecewise compression fields even though normal benchmark applies `apply_piecewise_T_compression()`. | Include `piecewise_compression_enabled`, `pw_knee`, `pw_t_max`, and contrast settings. |
| `run_benchmark.py` | `296-300` | P2 | Benchmark environment block is sparse compared with Iter9 metrics and lacks NumPy/SciPy/Pillow/matplotlib versions. | Use a shared environment summary helper. |
| `run_benchmark.py` | `329-658` | P2 | `run_normal_child()` is a 330-line duplicated pipeline runner, largely parallel to `run_iter9.py`. | Extract a reusable single-run engine used by both Iter9 and benchmark child runs. |
| `run_benchmark.py` | `825-904,911-922` | P1 | Regression rows add `source_image_validation` but do not add nested `source_image` provenance via `SourceImageConfig.to_metrics_dict()`. | Resolve each regression case image through `resolve_source_image_config()` and include nested `source_image` in each regression row. |
| `run_iris3d_visual_report.py` | `54-72,110-132,165-186` | P2 | This script duplicates atomic write, hash, git metadata, JSONL, and CSV helper logic now present elsewhere. | Replace duplicated helpers with shared utility/source_config helpers if the script remains active. |
| `run_iris3d_visual_report.py` | `1550-1559,1630-1638` | P1 | The script still has `--copy-from` / `--copy-to` workflow defaulting to copying into `assets/input_source_image.png`, which directly conflicts with the new no-overwrite source-image contract. | Remove copy-overwrite workflow or mark this script archived/deprecated; require explicit `--image` instead. |
| `run_iris3d_visual_report.py` | `1626-1628,1654` | P1 | The script sets `MINESTREAKER_ALLOW_NONCANONICAL` in the environment but calls `verify_source_image()` without passing `allow_noncanonical` or `return_details`. | Use explicit `verify_source_image(..., allow_noncanonical=args.allow_noncanonical, return_details=True)` and record validation details. |
| `run_iris3d_visual_report.py` | `771-1545` | P2 | `run_single_board()` is a 775-line experimental orchestration path that overlaps heavily with Iter9/benchmark logic. | Move to archive or split into reusable stages; otherwise it will keep drifting from the source-image runtime contract. |
| `run_repair_only_from_grid.py` | `44-86,392-407` | P2 | Duplicates atomic write, file hashing, and git metadata helpers. | Use shared helpers and `source_config.compute_file_sha256()`. |
| `run_repair_only_from_grid.py` | `418-420` | P1 | Repair-only runner sets `MINESTREAKER_ALLOW_NONCANONICAL` instead of passing explicit validation arguments and does not capture structured validation details. | Call `verify_source_image(str(image_path), allow_noncanonical=args.allow_noncanonical, return_details=True)` and record the details in metrics. |
| `run_repair_only_from_grid.py` | `204-389` | P2 | Contains a local `run_last100_repair()` implementation that overlaps with `repair.py`. | Consolidate to the canonical repair implementation. |
| `docs/codex_late_stage_repair_routing_implementation_status.md` | `26,552,625,689-690` | P1 | Status document still says strict canonical validation for `assets/input_source_image.png` is blocked/failing, contradicting the later source-image contract verification refresh. | Mark the document historical or append a superseding status note that strict default validation now passes after source-image contract implementation. |
| `docs/codex_late_stage_repair_routing_plan.md` | `1189,1289,1425` | P3 | Historical plan still contains default-image validation commands. This is acceptable only if clearly historical. | No code change required; optionally move old plans under docs/archive or add `Historical plan; not current workflow` banner. |
| `docs/industry_standard_plan_remove_hardcoded_input_source_image.md` | `1554-1599,1616-1800` | P3 | Implementation plan still contains unchecked checklist / pre-implementation prompt sections after implementation is complete. | Either keep as historical plan or move active checklist/status to the implementation checklist doc and add a historical banner. |
| `docs/implement_clarified_source_image_runtime_contract_implementation_checklist.md` | `692-696` | P2 | Checklist notes residual historical references but does not link a cleanup ledger. | Add a pointer to this cleanup audit or convert residual references into tracked cleanup issues. |
| `tests/test_source_image_cli_contract.py` | `57-65` | P2 | Import-time validation test patches `assets.image_guard.verify_source_image`, but `run_iter9.py` and `run_benchmark.py` import the function directly; this test may not catch already-bound aliases after import order changes. | Add direct module import/reload checks and inspect that no validation call occurs through either module-level alias. |
| `tests/test_benchmark_layout.py` | `1-91` | P2 | Benchmark layout tests likely verify helper naming but not a real small end-to-end child artifact set. | Add a cheap smoke test with mocked SA/solver or fixture grid to prove child directory artifact inventory is written. |
| `tests/test_image_guard_contract.py` | `1-131` | P2 | Image guard tests cover default/manifest cases but should also cover running from a non-repo current working directory after fixing default path resolution. | Add CWD-shift test for default image and default manifest resolution. |

---
## File-by-File Detailed Ledger

### `AGENTS.md`

- **Lines `11-13` — P1**
  - **Problem:** Project structure references root `run_contrast_preprocessing_study.py`, `input_source_image_research.png`, and saturation docs that are not present in the current digest.
  - **Cleanup:** Update structure to current files; move removed/deprecated assets and docs to an explicit historical note only if they still exist elsewhere.
- **Lines `31-33` — P1**
  - **Problem:** Command sequence validates `line_art_irl_11_v2.png` but then runs `python run_iter9.py` without `--image`, which uses the default image instead of the validated image.
  - **Cleanup:** Change to `python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical` and matching benchmark command.
- **Lines `48-58` — P1**
  - **Problem:** Validation section says there is no dedicated `tests/` suite, but the digest contains a tests directory with multiple contract tests.
  - **Cleanup:** Replace this section with `python -m unittest discover -s tests -p "test_*.py"` plus the acceptance commands.
- **Lines `84-96` — P2**
  - **Problem:** Saturation Campaign Rules reference `docs/saturation_run_matrix.md` and `results/saturation_matrix_TEMPLATE/...`, neither of which is present in the digest.
  - **Cleanup:** Archive this section, mark it historical, or replace with current benchmark/source-image contract validation rules.

### `README.md`

- **Lines `43` — P1**
  - **Problem:** README claims metrics include `source_image_validation`, but `run_iter9.py` metrics currently do not emit a top-level `source_image_validation` block.
  - **Cleanup:** Either add top-level `source_image_validation` to Iter9 metrics or change README wording to match actual Iter9 JSON. Prefer adding the field for consistency with benchmark metrics.
- **Lines `101-120` — P1**
  - **Problem:** Repository layout is stale: it omits `source_config.py`, `tests/`, and `archives/`, while listing `Larger_boards_fidelity_iteration/`, which is not present in this digest.
  - **Cleanup:** Rewrite repository layout from the current directory tree.
- **Lines `124-139` — P1**
  - **Problem:** Main runtime module table omits `source_config.py` and still lists `run_contrast_preprocessing_study.py` as an active root script even though the digest only has `archives/run_contrast_preprocessing_study.py.old`.
  - **Cleanup:** Add `source_config.py`; remove or relocate contrast-study entry under archive/deprecated notes.
- **Lines `199-212` — P1**
  - **Problem:** Quick Start output description still uses generic legacy artifact names (`grid_<board>.npy`, `metrics_<board>.json`, `visual_<board>.png`, `report_<board>.png`) instead of the new Iter9 run-specific directory and preserved Iter9 filenames.
  - **Cleanup:** Update to `results/iter9/<run_id>/metrics_iter9_<board>.json`, `grid_iter9_<board>.npy`, `grid_iter9_latest.npy`, `iter9_<board>_FINAL.png`, `repair_overlay_<board>.png`, and route JSON files.
- **Lines `377-397` — P2**
  - **Problem:** Pipeline direction describes late-stage routing as future-facing and target artifacts as future artifacts, but the route artifacts are now implemented.
  - **Cleanup:** Change wording from future direction to current architecture, or move this section to historical/campaign notes.
- **Lines `503-505` — P1**
  - **Problem:** Troubleshooting directs users to validate `assets/input_source_image.png` for board-sizing mismatch, which re-centers the old default instead of the actual source image used for the run.
  - **Cleanup:** Replace with `python assets/image_guard.py --path <same path passed to --image> [--allow-noncanonical|--manifest ...]`; mention default only if `--image` was omitted.
- **Lines `515-526` — P2**
  - **Problem:** Troubleshooting references generic `metrics_<board>.json` and `visual_<board>.png`; Iter9 outputs use `metrics_iter9_<board>.json` and `iter9_<board>_FINAL.png`.
  - **Cleanup:** Update artifact names or distinguish Iter9 vs benchmark artifact naming.
- **Lines `547-550` — P2**
  - **Problem:** Recommended reading order references `docs/project_result_summary.md` and `results/line_art_campaigns.md`, which are not present in the digest.
  - **Cleanup:** Verify those files exist outside the digest or replace with current docs that are present.
- **Lines `570-575` — P2**
  - **Problem:** Roadmap lists already-implemented or partially-implemented items as future work: failure taxonomy, late-stage routing, repair overlay, line_art_irl_9 regression promotion.
  - **Cleanup:** Rewrite roadmap around remaining work: quality regression on `420x311_seed22`, visual-delta gates, shared runner extraction, docs cleanup.

### `assets/image_guard.py`

- **Lines `17-18,247-258` — P1**
  - **Problem:** Default image and manifest paths are resolved from the process CWD, not from the repository root. Running the script from another directory can validate the wrong path or fail unexpectedly.
  - **Cleanup:** Define repo root from `Path(__file__).resolve().parents[1]`; resolve default image and manifest relative to that root.
- **Lines `84-97,335-351` — P2**
  - **Problem:** Image hash/stat computation is duplicated in `_compute_stats()` and `compute_image_hashes()`.
  - **Cleanup:** Make `compute_image_hashes()` call `_compute_stats()` and add only compatibility extras such as MD5 if still needed.
- **Lines `86,338` — P2**
  - **Problem:** `Image.open(...)` is used without a context manager in two hash/stat paths.
  - **Cleanup:** Use `with Image.open(path) as img:` and convert/copy the array inside the context.
- **Lines `199-239` — P2**
  - **Problem:** Missing-file and not-a-file branches assign `validation_mode='noncanonical_allowed'`, which is semantically misleading for filesystem failures.
  - **Cleanup:** Keep the public schema if required, but add an explicit error warning/code such as `SOURCE_IMAGE_NOT_FOUND` or `SOURCE_IMAGE_NOT_FILE` so LLM review is not misled.
- **Lines `285-289` — P1**
  - **Problem:** When a non-default image lacks a manifest and noncanonical mode is not allowed, the code still sets `validation_mode='noncanonical_allowed'` before failing.
  - **Cleanup:** Use a clearer failure marker in warnings/errors, or add `noncanonical_allowed=False` plus a structured error warning such as `NONCANONICAL_SOURCE_REJECTED`.
- **Lines `216-218,323-327` — P2**
  - **Problem:** Library function calls `sys.exit(1)` when `halt_on_failure=True`; this is legacy-compatible but awkward for callers that want exceptions/details.
  - **Cleanup:** Keep legacy behavior for public compatibility, but add an exception-returning lower-level helper and have CLI handle `SystemExit`.

### `core.py`

- **Lines `51-61` — P3**
  - **Problem:** `compute_edge_weights()` is retained for compatibility but is not used by active runtime paths in this digest.
  - **Cleanup:** Mark as deprecated/experimental or move to archive once compatibility is no longer needed.
- **Lines `63-176` — P3**
  - **Problem:** `compute_asymmetric_weights()` appears to be used only by legacy `pipeline.run_board()`.
  - **Cleanup:** If `pipeline.run_board()` is archived, archive this or explicitly mark as legacy Iter2 support.
- **Lines `178-221` — P2**
  - **Problem:** `compute_cluster_break_weights()` has no runtime references in the digest.
  - **Cleanup:** Remove, archive, or add tests/documented call sites before keeping it in active core primitives.
- **Lines `269-333` — P2**
  - **Problem:** `load_image_smart_v2()` is unused in the digest and imports optional `skimage` inside the function.
  - **Cleanup:** Move to archived experiment code or mark experimental; do not leave dormant optional-dependency code in active core without tests.

### `docs/codex_late_stage_repair_routing_implementation_status.md`

- **Lines `26,552,625,689-690` — P1**
  - **Problem:** Status document still says strict canonical validation for `assets/input_source_image.png` is blocked/failing, contradicting the later source-image contract verification refresh.
  - **Cleanup:** Mark the document historical or append a superseding status note that strict default validation now passes after source-image contract implementation.

### `docs/codex_late_stage_repair_routing_plan.md`

- **Lines `1189,1289,1425` — P3**
  - **Problem:** Historical plan still contains default-image validation commands. This is acceptable only if clearly historical.
  - **Cleanup:** No code change required; optionally move old plans under docs/archive or add `Historical plan; not current workflow` banner.

### `docs/implement_clarified_source_image_runtime_contract_implementation_checklist.md`

- **Lines `692-696` — P2**
  - **Problem:** Checklist notes residual historical references but does not link a cleanup ledger.
  - **Cleanup:** Add a pointer to this cleanup audit or convert residual references into tracked cleanup issues.

### `docs/industry_standard_plan_remove_hardcoded_input_source_image.md`

- **Lines `1554-1599,1616-1800` — P3**
  - **Problem:** Implementation plan still contains unchecked checklist / pre-implementation prompt sections after implementation is complete.
  - **Cleanup:** Either keep as historical plan or move active checklist/status to the implementation checklist doc and add a historical banner.

### `pipeline.py`

- **Lines `6` — P2**
  - **Problem:** Manual `sys.path.insert(...)` points three directories upward and is likely leftover import scaffolding.
  - **Cleanup:** Remove if not required, or replace with normal package/import strategy.
- **Lines `30-38` — P2**
  - **Problem:** Atomic JSON/NPY helpers duplicate equivalent logic in `run_iter9.py`, `run_benchmark.py`, `run_iris3d_visual_report.py`, and `run_repair_only_from_grid.py`.
  - **Cleanup:** Extract shared `atomic_write_json`, `atomic_write_npy`, and `atomic_render` helpers into a small utility module.
- **Lines `202-378` — P1**
  - **Problem:** `run_board()` is a legacy full orchestration path using Iter2/asymmetric settings, old metrics shape, old artifact names, and no source-image provenance contract.
  - **Cleanup:** Either archive/remove `run_board()` if unused, or update it to accept `SourceImageConfig`, image validation details, provenance-rich metrics, and the same artifact metadata contract.
- **Lines `217-218` — P1**
  - **Problem:** `run_board()` validates `img_path` through `verify_source_image()` without `allow_noncanonical`, `manifest_path`, or structured returned details.
  - **Cleanup:** Add parameters or remove this legacy path. Do not leave custom images dependent on the environment variable fallback.
- **Lines `361-364` — P1**
  - **Problem:** `run_board()` writes `metrics_iterX_label.json`, `grid_iterX_label.npy`, and final PNG without the new run-id directory/provenance policy.
  - **Cleanup:** If keeping this path, align artifact layout with current run-specific policy or mark as deprecated.

### `repair.py`

- **Lines `49` — P2**
  - **Problem:** `run_phase1_repair()` accepts `weights` but never uses it.
  - **Cleanup:** Remove the parameter in a coordinated API cleanup or mark it reserved/backward-compatible; update callers/tests when safe.
- **Lines `164-274` — P3**
  - **Problem:** `run_phase2_mesa_repair()` remains as compatibility code after main routing moved to `run_phase2_full_repair()`.
  - **Cleanup:** Keep only if tests/docs prove compatibility need; otherwise mark deprecated or move to archive.
- **Lines `333-519` — P2**
  - **Problem:** `run_last100_repair()` overlaps conceptually with a separate `run_last100_repair()` implementation in `run_repair_only_from_grid.py`.
  - **Cleanup:** Consolidate to a single implementation in `repair.py`; make repair-only runner call it.

### `run_benchmark.py`

- **Lines `100-149` — P2**
  - **Problem:** UTC/path/atomic/render helpers duplicate `run_iter9.py`.
  - **Cleanup:** Extract shared helper module after behavior is stable.
- **Lines `231-326` — P2**
  - **Problem:** `_build_child_metrics_document()` duplicates much of `run_iter9.py::build_metrics_document()` but with a different schema quality level.
  - **Cleanup:** Create a shared provenance/metrics builder or make benchmark call the Iter9 builder with benchmark-specific additions.
- **Lines `250-253` — P1**
  - **Problem:** Benchmark child `project_identity` lacks `git_commit`, `git_branch`, and `git_dirty`, unlike the intended provenance-rich metrics.
  - **Cleanup:** Reuse `run_iter9` git metadata logic or shared helper.
- **Lines `254` — P2**
  - **Problem:** Benchmark child `command_invocation` uses ambient `sys.argv`; programmatic calls via `main(argv=...)` may record the wrong command.
  - **Cleanup:** Pass raw argv from `main()` / `parse_args()` into child metrics and summaries.
- **Lines `256,645-653` — P1**
  - **Problem:** `source_image_analysis` is populated with target-field stats, not actual source image facts.
  - **Cleanup:** Compute real source image analysis or rename/remove this field; keep target stats under `target_field_stats` only.
- **Lines `266` — P1**
  - **Problem:** `preprocessing_config` omits piecewise compression fields even though normal benchmark applies `apply_piecewise_T_compression()`.
  - **Cleanup:** Include `piecewise_compression_enabled`, `pw_knee`, `pw_t_max`, and contrast settings.
- **Lines `296-300` — P2**
  - **Problem:** Benchmark environment block is sparse compared with Iter9 metrics and lacks NumPy/SciPy/Pillow/matplotlib versions.
  - **Cleanup:** Use a shared environment summary helper.
- **Lines `329-658` — P2**
  - **Problem:** `run_normal_child()` is a 330-line duplicated pipeline runner, largely parallel to `run_iter9.py`.
  - **Cleanup:** Extract a reusable single-run engine used by both Iter9 and benchmark child runs.
- **Lines `825-904,911-922` — P1**
  - **Problem:** Regression rows add `source_image_validation` but do not add nested `source_image` provenance via `SourceImageConfig.to_metrics_dict()`.
  - **Cleanup:** Resolve each regression case image through `resolve_source_image_config()` and include nested `source_image` in each regression row.

### `run_iris3d_visual_report.py`

- **Lines `54-72,110-132,165-186` — P2**
  - **Problem:** This script duplicates atomic write, hash, git metadata, JSONL, and CSV helper logic now present elsewhere.
  - **Cleanup:** Replace duplicated helpers with shared utility/source_config helpers if the script remains active.
- **Lines `1550-1559,1630-1638` — P1**
  - **Problem:** The script still has `--copy-from` / `--copy-to` workflow defaulting to copying into `assets/input_source_image.png`, which directly conflicts with the new no-overwrite source-image contract.
  - **Cleanup:** Remove copy-overwrite workflow or mark this script archived/deprecated; require explicit `--image` instead.
- **Lines `1626-1628,1654` — P1**
  - **Problem:** The script sets `MINESTREAKER_ALLOW_NONCANONICAL` in the environment but calls `verify_source_image()` without passing `allow_noncanonical` or `return_details`.
  - **Cleanup:** Use explicit `verify_source_image(..., allow_noncanonical=args.allow_noncanonical, return_details=True)` and record validation details.
- **Lines `771-1545` — P2**
  - **Problem:** `run_single_board()` is a 775-line experimental orchestration path that overlaps heavily with Iter9/benchmark logic.
  - **Cleanup:** Move to archive or split into reusable stages; otherwise it will keep drifting from the source-image runtime contract.

### `run_iter9.py`

- **Lines `83-101` — P2**
  - **Problem:** Atomic write/render helpers are duplicated with `run_benchmark.py` and older scripts.
  - **Cleanup:** Extract to shared utility module after current contract behavior is stable.
- **Lines `118-119` — P3**
  - **Problem:** `_sanitize_run_tag()` is only a wrapper around public `sanitize_run_tag()`.
  - **Cleanup:** Remove wrapper and call `sanitize_run_tag()` directly.
- **Lines `154-172` — P2**
  - **Problem:** `_source_image_analysis()` opens the image without a context manager.
  - **Cleanup:** Use `with PILImage.open(path) as image:` and copy required data before leaving the context.
- **Lines `187-201` — P2**
  - **Problem:** `_environment_summary()` sets `numba_num_threads` to `None` instead of capturing actual Numba thread information.
  - **Cleanup:** Use safe `numba.get_num_threads()` / threading-layer helpers like the older visual report script, or remove the field.
- **Lines `307-817` — P2**
  - **Problem:** `main()` is a 500+ line orchestration function. The implementation is correct but bloated after adding source-image/provenance logic.
  - **Cleanup:** Extract stages: resolve/validate source, build target/corridors, run SA, repair route, write artifacts, build metrics.
- **Lines `641-644` — P2**
  - **Problem:** `command_invocation.argv` reads ambient `sys.argv`, which makes tests and programmatic calls less reproducible.
  - **Cleanup:** Allow `main(argv=None)` and pass the parsed raw argv into metrics, as `run_benchmark.py` partially does.
- **Lines `645-646,786-811` — P1**
  - **Problem:** Iter9 metrics do not emit a top-level `source_image_validation` block, while README says metrics include it and benchmark child metrics do include it.
  - **Cleanup:** Add top-level `source_image_validation=image_validation` to `build_metrics_document()` inputs/output, or update README and benchmark for one consistent schema.

### `run_repair_only_from_grid.py`

- **Lines `44-86,392-407` — P2**
  - **Problem:** Duplicates atomic write, file hashing, and git metadata helpers.
  - **Cleanup:** Use shared helpers and `source_config.compute_file_sha256()`.
- **Lines `418-420` — P1**
  - **Problem:** Repair-only runner sets `MINESTREAKER_ALLOW_NONCANONICAL` instead of passing explicit validation arguments and does not capture structured validation details.
  - **Cleanup:** Call `verify_source_image(str(image_path), allow_noncanonical=args.allow_noncanonical, return_details=True)` and record the details in metrics.
- **Lines `204-389` — P2**
  - **Problem:** Contains a local `run_last100_repair()` implementation that overlaps with `repair.py`.
  - **Cleanup:** Consolidate to the canonical repair implementation.

### `source_config.py`

- **Lines `68` — P1**
  - **Problem:** Relative `image_path` is resolved against the current working directory, not `project_root`. This can break `--image assets/...` if the script is invoked from outside the repo root.
  - **Cleanup:** When `project_root` is supplied and `image_path` is relative, resolve it as `Path(project_root) / image_path` before `.resolve()`.
- **Lines `86` — P2**
  - **Problem:** `manifest_path` is serialized with `Path(manifest_path).as_posix()` but is not resolved relative to `project_root`; on non-Windows hosts a backslash path may remain unnormalized.
  - **Cleanup:** Normalize manifest path with the same project-root-aware logic and emit a forward-slash absolute or project-relative path consistently.

### `tests/test_benchmark_layout.py`

- **Lines `1-91` — P2**
  - **Problem:** Benchmark layout tests likely verify helper naming but not a real small end-to-end child artifact set.
  - **Cleanup:** Add a cheap smoke test with mocked SA/solver or fixture grid to prove child directory artifact inventory is written.

### `tests/test_image_guard_contract.py`

- **Lines `1-131` — P2**
  - **Problem:** Image guard tests cover default/manifest cases but should also cover running from a non-repo current working directory after fixing default path resolution.
  - **Cleanup:** Add CWD-shift test for default image and default manifest resolution.

### `tests/test_source_image_cli_contract.py`

- **Lines `57-65` — P2**
  - **Problem:** Import-time validation test patches `assets.image_guard.verify_source_image`, but `run_iter9.py` and `run_benchmark.py` import the function directly; this test may not catch already-bound aliases after import order changes.
  - **Cleanup:** Add direct module import/reload checks and inspect that no validation call occurs through either module-level alias.

---
## Clean / No Immediate Cleanup Found

- `board_sizing.py` — No source-image-contract cleanup found. It correctly accepts `image_path` as a runtime parameter.
- `corridors.py` — No source-image-contract cleanup found. Contains active corridor and diagnostic helpers.
- `LICENSE` — No cleanup needed.
- `list_unignored_files.py` — No source-image-contract cleanup found. Optional future enhancement: ensure docs/archive policy is reflected in file digest tooling.
- `report.py` — No source-image-contract cleanup found. Rendering helpers remain active.
- `sa.py` — No source-image-contract cleanup found. Keep routing logic out of this file.
- `solver.py` — No source-image-contract cleanup found. Failure taxonomy ownership is consistent with AGENTS.
- `archives/run_contrast_preprocessing_study.py.old` — Archived/deprecated by path; no runtime cleanup required unless archive policy changes.
- `archives/Timeout Theory Campaign Plan line_art_irl_9 20min budget.md` — Historical campaign plan; no runtime cleanup required.
- `tests/test_source_config.py` — Covers source_config basics; add CWD/project-root edge case if source_config is fixed.
- `tests/test_route_artifact_metadata.py` — Covers route artifact metadata; no immediate cleanup found.
- `tests/test_repair_route_decision.py` — No immediate cleanup found.
- `tests/test_repair_visual_delta.py` — No immediate cleanup found.
- `tests/test_solver_failure_taxonomy.py` — No immediate cleanup found.
- `tests/test_digest_file_listing.py` — No immediate cleanup found.

---
## Recommended Cleanup Order

### Step 1: Fix source path correctness and validation semantics
1. `source_config.py` lines 68 and 86.
2. `assets/image_guard.py` lines 17-18, 247-258, 285-289.

### Step 2: Fix user/LLM-facing documentation drift
1. `README.md` lines 43, 101-139, 199-212, 377-397, 503-526, 547-575.
2. `AGENTS.md` lines 11-13, 31-33, 48-58, 84-96.
3. `docs/codex_late_stage_repair_routing_implementation_status.md` lines 26, 552, 625, 689-690.

### Step 3: Remove or isolate legacy orchestration paths
1. `pipeline.py::run_board()` lines 202-378.
2. `run_iris3d_visual_report.py` copy-over workflow lines 1550-1559 and 1630-1638.
3. `run_repair_only_from_grid.py` image validation and duplicated Last-100 implementation.

### Step 4: Extract shared utilities after behavior is stable
1. Atomic writers/render helpers.
2. Git/environment/provenance helpers.
3. Single-run engine shared by Iter9 and benchmark child runs.

---
## Codex Cleanup Prompt

```markdown
Perform a cleanup-only pass after the source-image runtime contract implementation.

Rules:
- Do not change optimization behavior unless the cleanup item explicitly requires it.
- Do not remove compatibility APIs without a test proving no active caller needs them.
- Preserve established artifact filenames and run-specific directories.
- Preserve `python run_iter9.py`, `python run_benchmark.py --regression-only`, and explicit-image workflows.
- Update tests when fixing path resolution, docs, or validation semantics.

Priorities:
1. Fix project-root-relative source path resolution in `source_config.py`.
2. Fix repo-root-relative default image/manifest resolution in `assets/image_guard.py`.
3. Add/align `source_image_validation` schema consistently between Iter9, benchmark, and README.
4. Update README and AGENTS to remove stale artifact names, stale tests guidance, and copy/default-image centered instructions.
5. Mark historical docs as historical or move them under a docs/archive policy.
6. Remove or explicitly deprecate `pipeline.run_board()` if no active caller exists.
7. Remove copy-over workflow from `run_iris3d_visual_report.py` or archive the script.
8. Consolidate duplicated helper functions only after tests pass.

Validation:
- python -m unittest discover -s tests -p "test_*.py"
- python run_iter9.py --help
- python run_benchmark.py --help
- python assets/image_guard.py --path assets/input_source_image.png
- python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical
- python run_iter9.py --image assets/line_art_irl_11_v2.png --allow-noncanonical
- python run_benchmark.py --regression-only
- git grep "assets/input_source_image.png"
```
