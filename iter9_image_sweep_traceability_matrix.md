# Iter9 Image Sweep Traceability Matrix

## 1. Matrix Purpose

This document maps every required Iter9 image-sweep behavior to the exact implementation location, exact test coverage, and exact verification command.

The implementation is complete only when every requirement row has an implemented code change and a passing test.

This corrected matrix locks the Iter9 image-sweep requirements for:

- row helper signatures and mappings,
- summary row normalization and field order,
- discovery and warmup failure summaries,
- exact raw-argv command provenance,
- skip-existing board-label path sequencing,
- manual validation commands,
- manual traceability inspection requirements.

## 2. File Scope Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| FS-001 | Modify only approved feature files. | `run_iter9.py`, `README.md`, `AGENTS.md`, `tests/test_iter9_image_sweep_contract.py` | Whole feature scope | Manual review | `git diff --name-only` must list no other files. |
| FS-002 | Do not modify solver, repair, SA, rendering, board sizing, source config, image guard, benchmark, or report internals for image-sweep mode. | No changes allowed in forbidden files | Forbidden file list from the contract | Manual review | `git diff --name-only` must exclude forbidden files. |
| FS-003 | Add new tests only in `tests/test_iter9_image_sweep_contract.py`. | `tests/test_iter9_image_sweep_contract.py` | Entire file | `tests/test_iter9_image_sweep_contract.py` | Full unittest discovery passes. |
| FS-004 | Preserve the allowed-change boundary exactly. | `run_iter9.py`, `README.md`, `AGENTS.md`, `tests/test_iter9_image_sweep_contract.py` | Whole feature scope | Manual review | The diff contains no modified file outside the allowed list. |

## 3. CLI Contract Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| CLI-001 | `parse_args(...)` must construct `ArgumentParser` with `allow_abbrev=False`. | `run_iter9.py` | `parse_args(...)` parser construction | `tests/test_iter9_image_sweep_contract.py` | `test_argparse_rejects_abbreviated_long_flags` |
| CLI-002 | `--image-dir` must be exposed in `run_iter9.py --help`. | `run_iter9.py` | `parse_args(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_help_exposes_all_image_sweep_flags` |
| CLI-003 | `--image-glob` must be exposed in `run_iter9.py --help`. | `run_iter9.py` | `parse_args(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_help_exposes_all_image_sweep_flags` |
| CLI-004 | `--recursive` must be exposed in `run_iter9.py --help`. | `run_iter9.py` | `parse_args(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_help_exposes_all_image_sweep_flags` |
| CLI-005 | `--out-root` must be exposed in `run_iter9.py --help`. | `run_iter9.py` | `parse_args(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_help_exposes_all_image_sweep_flags` |
| CLI-006 | `--continue-on-error` must be exposed in `run_iter9.py --help`. | `run_iter9.py` | `parse_args(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_help_exposes_all_image_sweep_flags` |
| CLI-007 | `--skip-existing` must be exposed in `run_iter9.py --help`. | `run_iter9.py` | `parse_args(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_help_exposes_all_image_sweep_flags` |
| CLI-008 | `--max-images` must be exposed in `run_iter9.py --help`. | `run_iter9.py` | `parse_args(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_help_exposes_all_image_sweep_flags` |
| CLI-009 | Sweep-only flags must fail when `--image-dir` is absent. | `run_iter9.py` | `parse_args(...)` validation block | `tests/test_iter9_image_sweep_contract.py` | `test_sweep_only_flags_without_image_dir_fail` |
| CLI-010 | `--image-dir` plus explicit `--image value` must fail. | `run_iter9.py` | `parse_args(...)`, `_explicit_flag_present(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_image_dir_plus_explicit_image_fails` |
| CLI-011 | `--image-dir` plus explicit `--image=value` must fail. | `run_iter9.py` | `parse_args(...)`, `_explicit_flag_present(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_image_dir_plus_explicit_image_fails` |
| CLI-012 | `--image-dir` plus `--out-dir` must fail. | `run_iter9.py` | `parse_args(...)` validation block | `tests/test_iter9_image_sweep_contract.py` | `test_image_dir_plus_out_dir_fails` |
| CLI-013 | `--image-dir` plus `--image-manifest` must fail. | `run_iter9.py` | `parse_args(...)`, `_explicit_flag_present(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_image_dir_plus_image_manifest_fails` |
| CLI-014 | `--max-images 0` must fail. | `run_iter9.py` | `parse_args(...)` validation block | `tests/test_iter9_image_sweep_contract.py` | `test_max_images_zero_fails` |
| CLI-015 | Existing single-image flags must remain in help. | `run_iter9.py` | Existing `parse_args(...)` flags | `tests/test_source_image_cli_contract.py` | Existing `test_run_iter9_help_exposes_contract_flags` |

## 4. Discovery Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| DISC-001 | Add `discover_source_images(...)`. | `run_iter9.py` | New helper function | `tests/test_iter9_image_sweep_contract.py` | `test_discovery_direct_matches_are_sorted` |
| DISC-002 | Non-recursive discovery must return only top-level matching files. | `run_iter9.py` | `discover_source_images(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_discovery_direct_matches_are_sorted` |
| DISC-003 | Recursive discovery must include nested matching files. | `run_iter9.py` | `discover_source_images(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_discovery_recursive_includes_nested_matches` |
| DISC-004 | Discovery must sort by resolved POSIX path before truncation. | `run_iter9.py` | `discover_source_images(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_discovery_applies_max_images_after_sorting` |
| DISC-005 | Missing image directory must raise `FileNotFoundError`. | `run_iter9.py` | `discover_source_images(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_discovery_missing_directory_fails` |
| DISC-006 | File passed as image directory must raise `NotADirectoryError`. | `run_iter9.py` | `discover_source_images(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_discovery_file_instead_of_directory_fails` |
| DISC-007 | Empty match set must raise `ValueError`. | `run_iter9.py` | `discover_source_images(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_discovery_empty_match_fails` |
| DISC-008 | Discovery helper must not validate image bytes. | `run_iter9.py` | `discover_source_images(...)` | `tests/test_iter9_image_sweep_contract.py` | Discovery tests use fake `.png` byte contents and must pass. |
| DISC-009 | Discovery must return an ordered `Path` list only. It must not return source configs, metrics rows, validation results, or child directories. | `run_iter9.py` | `discover_source_images(...)` | `tests/test_iter9_image_sweep_contract.py` plus code review | Discovery tests assert `Path` output; batch tests verify per-image resolution happens later. |

## 5. Path And Directory Naming Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| PATH-001 | Add `_sanitize_path_token(...)` reusing `sanitize_run_tag(...)`. | `run_iter9.py` | New helper near `sanitize_run_tag(...)` | `tests/test_iter9_image_sweep_contract.py` | Covered by child directory tests. |
| PATH-002 | Add `_path_hash_token(...)` using resolved POSIX path SHA-256. | `run_iter9.py` | New helper near `_sanitize_path_token(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_same_stem_same_sha_duplicate_produces_distinct_child_directories` |
| PATH-003 | Add `_colliding_sanitized_stem_tokens(...)`. | `run_iter9.py` | New helper after discovery helper | `tests/test_iter9_image_sweep_contract.py` | `test_sanitized_stem_collisions_include_sha_and_path_hash` |
| PATH-004 | Child directory must include full board label. | `run_iter9.py` | `build_image_sweep_child_out_dir(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_child_output_directory_includes_full_board_label` |
| PATH-005 | Sanitized collisions such as `a b.png` and `a_b.png` must be protected. | `run_iter9.py` | `_colliding_sanitized_stem_tokens(...)`, `build_image_sweep_child_out_dir(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_sanitized_stem_collisions_include_sha_and_path_hash` |
| PATH-006 | Casefold collisions such as `Cat.png` and `cat.png` must be detected. | `run_iter9.py` | `_colliding_sanitized_stem_tokens(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_case_insensitive_stem_collisions_are_detected` |
| PATH-007 | Same-stem same-SHA duplicate files in different directories must produce distinct child directories. | `run_iter9.py` | `_path_hash_token(...)`, `build_image_sweep_child_out_dir(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_same_stem_same_sha_duplicate_produces_distinct_child_directories` |
| PATH-008 | Duplicate-stem safety must remain deterministic when child directory names require suffixing. | `run_iter9.py` | `_colliding_sanitized_stem_tokens(...)`, `_path_hash_token(...)`, `build_image_sweep_child_out_dir(...)` | `tests/test_iter9_image_sweep_contract.py` | Path collision tests must pass repeatedly with stable expected names. |

## 6. Single-Run Extraction Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| SINGLE-001 | Add `run_iter9_single(...)` with the required signature. | `run_iter9.py` | New helper extracted from current `main()` body | `tests/test_iter9_image_sweep_contract.py` | Import and mocked batch tests must call this helper. |
| SINGLE-002 | `run_iter9_single(...)` must receive `source_validation` and create `image_validation = dict(source_validation)`. | `run_iter9.py` | Top of `run_iter9_single(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_batch_runner_calls_single_run_once_per_image` exercises successful call path. |
| SINGLE-003 | `run_iter9_single(...)` must not resolve or validate source images. | `run_iter9.py` | `run_iter9_single(...)` body | Code review plus tests | Batch tests patch resolution and validation before helper call. |
| SINGLE-004 | `run_iter9_single(...)` must not compile SA or warm solver. | `run_iter9.py` | `run_iter9_single(...)` body | Code review plus tests | Batch tests patch compile/warm before helper call. |
| SINGLE-005 | `run_iter9_single(...)` must use provided `out_dir_path` and not reassign it. | `run_iter9.py` | `run_iter9_single(...)` first filesystem action | Code review | First filesystem action is `out_dir_path.mkdir(parents=True, exist_ok=True)`. |
| SINGLE-006 | `run_iter9_single(...)` must return `metrics_doc`. | `run_iter9.py` | End of `run_iter9_single(...)` | `tests/test_iter9_image_sweep_contract.py` | Batch success row tests require returned metrics document. |
| SINGLE-007 | Command invocation must use exact raw argv construction. | `run_iter9.py` | `run_iter9_single(...)` metrics construction | `tests/test_iter9_image_sweep_contract.py` | `test_command_invocation_uses_exact_raw_argv_prefix` |
| SINGLE-008 | Single-image metrics must not contain `batch_context`. | `run_iter9.py` | `main(...)`, `run_iter9_single(...)`, `build_metrics_document(...)` | `tests/test_iter9_image_sweep_contract.py` or smoke validation | `test_build_metrics_document_includes_optional_batch_context` covers optional schema behavior; manual single-image smoke must verify omission. |
| SINGLE-009 | `run_iter9_single(...)` must do exactly one run and return `metrics_doc`. | `run_iter9.py` | Full `run_iter9_single(...)` body | `tests/test_iter9_image_sweep_contract.py` plus code review | Batch tests assert one helper call per attempted child and success rows consume returned metrics. |
| SINGLE-010 | `run_iter9_single(...)` must not parse CLI, discover images, write batch summaries, or mutate batch orchestration state. | `run_iter9.py` | Full `run_iter9_single(...)` body | Code review plus batch tests | No `parse_args(...)`, `discover_source_images(...)`, or `write_iter9_image_sweep_summaries(...)` call occurs inside `run_iter9_single(...)`. |
| SINGLE-011 | Single-image mode must pass `batch_context=None`. | `run_iter9.py` | `main(...)` single-image call to `run_iter9_single(...)` | `tests/test_iter9_image_sweep_contract.py` plus manual smoke | Single-image metrics omit `batch_context`. |
| SINGLE-012 | Sweep mode must pass populated `batch_context`. | `run_iter9.py` | `run_iter9_image_sweep(...)` call to `run_iter9_single(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_batch_context_passed_to_single_run_is_complete` |

### 6.1 Exact Command Invocation Construction

`run_iter9_single(...)` must construct command provenance exactly as:

```python
command_invocation = {
    "entry_point": "run_iter9.py",
    "argv": ["run_iter9.py", *raw_argv],
}
```

`sys.argv` must not be used inside single-run metrics composition.

## 7. Metrics And Batch Context Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| MET-001 | `build_metrics_document(...)` must accept `batch_context`. | `run_iter9.py` | Function signature | `tests/test_iter9_image_sweep_contract.py` | `test_build_metrics_document_includes_optional_batch_context` |
| MET-002 | `build_metrics_document(...)` must add `document["batch_context"]` only when non-None. | `run_iter9.py` | End of `build_metrics_document(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_build_metrics_document_includes_optional_batch_context` |
| MET-003 | Batch child metrics must receive complete `batch_context`. | `run_iter9.py` | `run_iter9_image_sweep(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_batch_context_passed_to_single_run_is_complete` |
| MET-004 | `batch_context["schema_version"]` must equal `iter9_image_sweep_context.v1`. | `run_iter9.py` | `run_iter9_image_sweep(...)` batch context literal | `tests/test_iter9_image_sweep_contract.py` | `test_batch_context_passed_to_single_run_is_complete` |
| MET-005 | `batch_context["child_warmup_s"]` must equal `0.0`. | `run_iter9.py` | `run_iter9_image_sweep(...)` batch context literal | `tests/test_iter9_image_sweep_contract.py` | `test_batch_context_passed_to_single_run_is_complete` |
| MET-006 | Successful sweep child metrics must contain `batch_context`. | `run_iter9.py` | `build_metrics_document(...)` and child metrics writer | Manual traceability inspection | Verify one sweep child metrics JSON contains `batch_context`. |
| MET-007 | Single-image metrics must omit `batch_context`. | `run_iter9.py` | `build_metrics_document(...)` and single-image metrics writer | Manual traceability inspection | Verify single-image metrics JSON has no `batch_context` key. |

## 8. Row Helper Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| ROW-001 | Add `_image_sweep_success_row(...)` with the exact signature shown in section 8.1. | `run_iter9.py` | New summary row helper section before summary writer | `tests/test_iter9_image_sweep_contract.py` | `test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping` |
| ROW-002 | Add `_image_sweep_failure_row(...)` with the exact signature shown in section 8.1. | `run_iter9.py` | New summary row helper section before summary writer | `tests/test_iter9_image_sweep_contract.py` | `test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping` |
| ROW-003 | Add `_image_sweep_skipped_existing_row(...)` with the exact signature shown in section 8.1. | `run_iter9.py` | New summary row helper section before summary writer | `tests/test_iter9_image_sweep_contract.py` | `test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping` |
| ROW-004 | Every row helper must return exactly the keys in `IMAGE_SWEEP_SUMMARY_FIELDS`. | `run_iter9.py` | All three row helpers | `tests/test_iter9_image_sweep_contract.py` | `test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping` |
| ROW-005 | Success rows must set `status` to `succeeded` and must set `error_type=None` and `error_message=None`. | `run_iter9.py` | `_image_sweep_success_row(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping` |
| ROW-006 | Failure rows must set `status` to `failed`, `error_type=type(error).__name__`, `error_message=str(error)`, and unavailable metric-bearing fields to `None`. | `run_iter9.py` | `_image_sweep_failure_row(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping` |
| ROW-007 | Skipped rows must set `status` to `skipped_existing`, must set expected `metrics_path`, and may hydrate readable metrics fields from existing metrics JSON. | `run_iter9.py` | `_image_sweep_skipped_existing_row(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping`, `test_skip_existing_metrics_path_uses_derived_full_board_label` |
| ROW-008 | Row helpers must produce normalized values compatible with JSON, CSV, and Markdown summary emitters. | `run_iter9.py` | All three row helpers and summary writer | `tests/test_iter9_image_sweep_contract.py` | `test_summaries_write_json_csv_and_markdown`, `test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping` |

### 8.1 Required Row Helper Signatures

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

## 9. Batch Summary Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| SUM-001 | Add `IMAGE_SWEEP_SUMMARY_FIELDS`. | `run_iter9.py` | Summary constants section | `tests/test_iter9_image_sweep_contract.py` | `test_image_sweep_summary_fields_exact_order` |
| SUM-002 | Add `_atomic_save_text(...)`. | `run_iter9.py` | After `_atomic_save_json(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_summaries_write_json_csv_and_markdown` |
| SUM-003 | Add `_atomic_save_csv(...)`. | `run_iter9.py` | After `_atomic_save_text(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_summaries_write_json_csv_and_markdown` |
| SUM-004 | Add `_md_table_cell(...)`. | `run_iter9.py` | Near summary writer | `tests/test_iter9_image_sweep_contract.py` | `test_md_table_cell_escapes_pipes_and_newlines` |
| SUM-005 | Markdown summary rows must use `_md_table_cell(...)`. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_summary_markdown_escapes_table_cells` |
| SUM-006 | `write_iter9_image_sweep_summaries(...)` must write JSON. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_summaries_write_json_csv_and_markdown` |
| SUM-007 | `write_iter9_image_sweep_summaries(...)` must write CSV. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_summaries_write_json_csv_and_markdown` |
| SUM-008 | `write_iter9_image_sweep_summaries(...)` must write Markdown. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_summaries_write_json_csv_and_markdown` |
| SUM-009 | Summary JSON `schema_version` must equal `iter9_image_sweep.v1`. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_summaries_write_json_csv_and_markdown`, `test_summary_writer_accepts_image_dir_string_and_stores_images_discovered` |
| SUM-010 | Summary JSON `batch_identity` must contain exactly `batch_id`, `entry_point`, `image_dir`, `image_glob`, `recursive`, `out_root`, `board_width`, and `seed`. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` plus manual inspection | `test_summary_writer_accepts_image_dir_string_and_stores_images_discovered` |
| SUM-011 | Summary JSON `batch_timing` must contain exactly `started_at_utc`, `finished_at_utc`, `duration_wall_s`, and `batch_warmup_s`. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` plus manual inspection | `test_summaries_write_json_csv_and_markdown` |
| SUM-012 | Summary JSON must include `images_discovered` as the count of matched files discovered before child execution. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` call sites | `tests/test_iter9_image_sweep_contract.py` | `test_summary_writer_accepts_image_dir_string_and_stores_images_discovered` |
| SUM-013 | Summary counts must use exact semantics: succeeded rows count as `runs_succeeded`, failed rows count as `runs_failed`, skipped rows count as `runs_skipped`, and `runs_attempted = runs_succeeded + runs_failed`. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_summaries_write_json_csv_and_markdown`, `test_discovery_failure_writes_failure_summary_and_returns_1`, `test_warmup_failure_writes_failure_summary_and_returns_1` |
| SUM-014 | Summary rows must be normalized with exact `IMAGE_SWEEP_SUMMARY_FIELDS` projection before JSON, CSV, or Markdown output. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_image_sweep_summary_fields_exact_order`, `test_summaries_write_json_csv_and_markdown` |
| SUM-015 | CSV must use exact `IMAGE_SWEEP_SUMMARY_FIELDS` order. | `run_iter9.py` | `_atomic_save_csv(...)`, `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_image_sweep_summary_fields_exact_order`, `test_summaries_write_json_csv_and_markdown` |
| SUM-016 | JSON rows and CSV rows must contain the same normalized key set and key-order contract. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` | `tests/test_iter9_image_sweep_contract.py` plus manual inspection | `test_summaries_write_json_csv_and_markdown` |
| SUM-017 | `write_iter9_image_sweep_summaries(...)` must accept `image_dir: str` and persist that exact string in `batch_identity.image_dir`. | `run_iter9.py` | Function signature and `batch_identity` construction | `tests/test_iter9_image_sweep_contract.py` | `test_summary_writer_accepts_image_dir_string_and_stores_images_discovered` |
| SUM-018 | `write_iter9_image_sweep_summaries(...)` must not call `image_dir.as_posix()` internally. | `run_iter9.py` | `write_iter9_image_sweep_summaries(...)` body | `tests/test_iter9_image_sweep_contract.py` plus code review | `test_summary_writer_accepts_image_dir_string_and_stores_images_discovered` |

### 9.1 Exact Row Normalization Projection

Rows must be materialized before writing as:

```python
normalized_rows = [
    {field: row.get(field) for field in IMAGE_SWEEP_SUMMARY_FIELDS}
    for row in rows
]
```

The JSON `rows` field must contain `normalized_rows`.

The CSV must use `IMAGE_SWEEP_SUMMARY_FIELDS` as its field order.

## 10. Batch Runner Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| BATCH-001 | Add `run_iter9_image_sweep(...)`. | `run_iter9.py` | New batch runner function | `tests/test_iter9_image_sweep_contract.py` | `test_batch_runner_calls_single_run_once_per_image` |
| BATCH-002 | Batch runner must call `discover_source_images(...)`. | `run_iter9.py` | `run_iter9_image_sweep(...)` start | `tests/test_iter9_image_sweep_contract.py` | Batch runner tests use temp images discovered from disk. |
| BATCH-003 | Batch runner must compute colliding stem tokens from discovered images. | `run_iter9.py` | `run_iter9_image_sweep(...)` after discovery | `tests/test_iter9_image_sweep_contract.py` | Collision helper tests cover helper behavior. |
| BATCH-004 | Batch runner must compile SA and warm solver once per batch. | `run_iter9.py` | `run_iter9_image_sweep(...)` before loop | `tests/test_iter9_image_sweep_contract.py` | `test_warmup_failure_writes_failure_summary_and_returns_1` plus mocked batch success tests. |
| BATCH-005 | Batch runner must pass `warmup_s=0.0` to child single runs. | `run_iter9.py` | `run_iter9_image_sweep(...)` call to `run_iter9_single(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_batch_context_passed_to_single_run_is_complete` and call kwargs assertion. |
| BATCH-006 | Batch child validation must use `halt_on_failure=False`. | `run_iter9.py` | `verify_source_image(...)` call in loop | `tests/test_iter9_image_sweep_contract.py` | `test_validation_failure_writes_failed_row_and_summary` |
| BATCH-007 | Failed child validation must become `ValueError`. | `run_iter9.py` | Validation result check in loop | `tests/test_iter9_image_sweep_contract.py` | `test_validation_failure_writes_failed_row_and_summary` |
| BATCH-008 | Batch runner must call `run_iter9_single(...)` once per successful or runtime-attempted image. | `run_iter9.py` | `run_iter9_image_sweep(...)` loop | `tests/test_iter9_image_sweep_contract.py` | `test_batch_runner_calls_single_run_once_per_image` |
| BATCH-009 | Fail-fast mode must stop after first runtime failure. | `run_iter9.py` | Exception handler in loop | `tests/test_iter9_image_sweep_contract.py` | `test_fail_fast_stops_after_first_runtime_failure_and_writes_summaries` |
| BATCH-010 | Fail-fast mode must write summary before returning `1`. | `run_iter9.py` | Post-loop summary writer call | `tests/test_iter9_image_sweep_contract.py` | `test_fail_fast_stops_after_first_runtime_failure_and_writes_summaries` |
| BATCH-011 | Continue-on-error must attempt all discovered images. | `run_iter9.py` | Exception handler in loop | `tests/test_iter9_image_sweep_contract.py` | `test_continue_on_error_attempts_all_images` |
| BATCH-012 | Skip-existing must skip child run when expected metrics exists. | `run_iter9.py` | Skip branch before `run_iter9_single(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_skip_existing_prevents_single_run_call` |
| BATCH-013 | Batch runner must return `0` when no child fails. | `run_iter9.py` | Final return in `run_iter9_image_sweep(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_batch_runner_calls_single_run_once_per_image` |
| BATCH-014 | Batch runner must return `1` when any child fails. | `run_iter9.py` | Final return in `run_iter9_image_sweep(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_validation_failure_writes_failed_row_and_summary`, `test_continue_on_error_attempts_all_images` |
| BATCH-015 | Discovery failure must write JSON, CSV, and Markdown summary files before returning `1`. | `run_iter9.py` | Discovery failure handler in `run_iter9_image_sweep(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_discovery_failure_writes_failure_summary_and_returns_1` |
| BATCH-016 | Discovery failure summary must set `images_discovered=0`, `runs_attempted=0`, `runs_failed=1`, `runs_succeeded=0`, `runs_skipped=0`, and one failed row. | `run_iter9.py` | Discovery failure handler and summary writer call | `tests/test_iter9_image_sweep_contract.py` | `test_discovery_failure_writes_failure_summary_and_returns_1` |
| BATCH-017 | Compile or warmup failure must write JSON, CSV, and Markdown summary files before returning `1`. | `run_iter9.py` | Warmup failure handler in `run_iter9_image_sweep(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_warmup_failure_writes_failure_summary_and_returns_1` |
| BATCH-018 | Warmup failure summary must preserve discovered image count, set `runs_attempted=0`, `runs_failed=1`, `runs_succeeded=0`, `runs_skipped=0`, and one failed row. | `run_iter9.py` | Warmup failure handler and summary writer call | `tests/test_iter9_image_sweep_contract.py` | `test_warmup_failure_writes_failure_summary_and_returns_1` |
| BATCH-019 | Batch runner must re-raise `KeyboardInterrupt`. | `run_iter9.py` | `except KeyboardInterrupt: raise` | Code review | `KeyboardInterrupt` is not caught as failed row. |
| BATCH-020 | Batch runner must pass exact raw argv to `run_iter9_single(...)`. | `run_iter9.py` | Call kwargs in `run_iter9_image_sweep(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_single_run_receives_exact_raw_argv`, `test_command_invocation_uses_exact_raw_argv_prefix` |
| BATCH-021 | `resolve_source_image_config(...)` must run inside the child loop, one image at a time. | `run_iter9.py` | Child loop in `run_iter9_image_sweep(...)` | `tests/test_iter9_image_sweep_contract.py` plus code review | Batch tests assert resolver call count and call order; no pre-loop bulk resolution exists. |
| BATCH-022 | Any per-image source-config resolution failure must become a failed row and follow fail-fast or continue-on-error policy. | `run_iter9.py` | Child loop exception handling | `tests/test_iter9_image_sweep_contract.py` | `test_validation_failure_writes_failed_row_and_summary` pattern applies to pre-run child failures; add specific resolver-failure assertion if needed. |
| BATCH-023 | Skip-existing decision must occur only after source resolution, source validation, board-size derivation, full board-label construction, child directory construction, and expected metrics-path construction. | `run_iter9.py` | Child loop before skip branch | `tests/test_iter9_image_sweep_contract.py` | `test_skip_existing_metrics_path_uses_derived_full_board_label` |
| BATCH-024 | Expected skip-existing metrics path must be `child_out_dir / f"metrics_iter9_{board_label}.json"` using the derived full board label. | `run_iter9.py` | Child loop skip branch | `tests/test_iter9_image_sweep_contract.py` | `test_skip_existing_metrics_path_uses_derived_full_board_label`, `test_skip_existing_prevents_single_run_call` |
| BATCH-025 | Skipped rows must not make the batch return code `1`. | `run_iter9.py` | Final return calculation in `run_iter9_image_sweep(...)` | `tests/test_iter9_image_sweep_contract.py` | `test_skip_existing_prevents_single_run_call` |
| BATCH-026 | Discovery, warmup, validation, resolver, child runtime, and skipped-existing paths must all route through row helpers before summary writing. | `run_iter9.py` | Failure handlers, skip branch, success branch | `tests/test_iter9_image_sweep_contract.py` | Row helper mapping test plus batch path tests. |

### 10.1 Exact Per-Image Execution Ordering

For each discovered image, execution must follow this order:

1. Resolve image through `resolve_source_image_config(...)`.
2. Validate image through `verify_source_image(... halt_on_failure=False ...)`.
3. Derive board size with `derive_board_from_width(...)`.
4. Build full board label as `"<board_width>x<board_height>"`.
5. Build child output directory with `build_image_sweep_child_out_dir(...)`.
6. Build expected metrics path as `child_out_dir / f"metrics_iter9_{board_label}.json"`.
7. If `--skip-existing` and that path exists, append skipped row and continue.
8. Build `batch_context`.
9. Call `run_iter9_single(...)`.
10. Append success row on success.
11. Append failed row on exception.
12. Stop after first failed row unless `--continue-on-error` is true.

Pre-loop bulk resolution of all source configs is forbidden.

## 11. Artifact Preservation Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| ART-001 | Preserve `metrics_iter9_<board>.json`. | `run_iter9.py` | `run_iter9_single(...)` moved body | Existing smoke validation | Single-image and batch smoke validation. |
| ART-002 | Preserve `grid_iter9_<board>.npy`. | `run_iter9.py` | `run_iter9_single(...)` moved body | Existing smoke validation | Single-image and batch smoke validation. |
| ART-003 | Preserve `grid_iter9_latest.npy`. | `run_iter9.py` | `run_iter9_single(...)` moved body | Existing smoke validation | Single-image and batch smoke validation. |
| ART-004 | Preserve `iter9_<board>_FINAL.png`. | `run_iter9.py` | `run_iter9_single(...)` moved body | Existing smoke validation | Single-image and batch smoke validation. |
| ART-005 | Preserve `iter9_<board>_FINAL_explained.png`. | `run_iter9.py` | `run_iter9_single(...)` moved body | Existing smoke validation | Single-image and batch smoke validation. |
| ART-006 | Preserve `repair_overlay_<board>.png`. | `run_iter9.py` | `run_iter9_single(...)` moved body | Existing smoke validation | Single-image and batch smoke validation. |
| ART-007 | Preserve `repair_overlay_<board>_explained.png`. | `run_iter9.py` | `run_iter9_single(...)` moved body | Existing smoke validation | Single-image and batch smoke validation. |
| ART-008 | Preserve `failure_taxonomy.json`. | `run_iter9.py`, `pipeline.py` | Existing `write_repair_route_artifacts(...)` call remains in moved body | Existing route artifact tests | Existing `tests/test_route_artifact_metadata.py` plus smoke validation. |
| ART-009 | Preserve `repair_route_decision.json`. | `run_iter9.py`, `pipeline.py` | Existing `write_repair_route_artifacts(...)` call remains in moved body | Existing route artifact tests | Existing `tests/test_route_artifact_metadata.py` plus smoke validation. |
| ART-010 | Preserve `visual_delta_summary.json`. | `run_iter9.py`, `pipeline.py` | Existing `write_repair_route_artifacts(...)` call remains in moved body | Existing route artifact tests | Existing `tests/test_route_artifact_metadata.py` plus smoke validation. |
| ART-011 | Artifact filenames inside child directories must remain unchanged. | `run_iter9.py` | Single-run body and child directory routing | Manual smoke validation | Manual single-image and batch smoke runs produce expected artifact filenames. |

## 12. Documentation Traceability

| ID | Requirement | Implementation File | Implementation Location | Test File | Required Test |
|---|---|---|---|---|---|
| DOC-001 | README must document image-sweep command. | `README.md` | Insert before `## Beginner Workflow` | Manual review | README contains `python run_iter9.py --image-dir assets --image-glob "*.png" ...`. |
| DOC-002 | README must document batch summary files. | `README.md` | New image-sweep section | Manual review | README contains all three summary filenames. |
| DOC-003 | README must document preserved child artifact filenames. | `README.md` | New image-sweep section | Manual review | README contains Iter9 artifact list. |
| DOC-004 | AGENTS must document image-sweep contract. | `AGENTS.md` | Insert after `## Source Image Runtime Contract` | Manual review | AGENTS contains `## Iter9 Image Sweep Contract`. |
| DOC-005 | AGENTS must forbid solver, repair, SA, rendering, source-image validation, and artifact filename behavior changes for image-sweep mode. | `AGENTS.md` | New image-sweep section | Manual review | AGENTS contains explicit prohibition line. |
| DOC-006 | README and AGENTS must use `assets/line_art_irl_11_v2.png` for the standardized manual single-image validation path. | `README.md`, `AGENTS.md` | Image-sweep and validation sections | Manual review | Search docs for manual validation command path. |

## 13. Verification Command Traceability

| ID | Requirement | Verification Command | Required Result |
|---|---|---|---|
| VER-001 | Full test suite must pass. | `python -m unittest discover -s tests -p "test_*.py"` | Exit code `0`. |
| VER-002 | Iter9 help must expose sweep flags. | `python run_iter9.py --help` | Exit code `0`; stdout includes every sweep flag. |
| VER-003 | Guard command must pass for standardized manual path. | `python assets/image_guard.py --path assets/line_art_irl_11_v2.png --allow-noncanonical` | Exit code `0`. |
| VER-004 | Single-image smoke must pass and omit `batch_context` from metrics. | `python run_iter9.py --image assets/line_art_irl_11_v2.png --seed 11 --allow-noncanonical --out-dir results/iter9_manual_single_validation` | Exit code `0`; metrics JSON exists; metrics JSON omits `batch_context`. |
| VER-005 | Batch smoke must pass and write summaries. | `python run_iter9.py --image-dir assets --image-glob "*.png" --seed 11 --allow-noncanonical --out-root results/iter9_manual_explained_validation --max-images 2` | Exit code `0` when selected images pass; summary JSON, CSV, and Markdown exist at batch root. |
| VER-006 | `--out-root` without `--image-dir` must fail. | `python run_iter9.py --out-root results/x` | Nonzero exit; argparse error. |
| VER-007 | `--image-glob` without `--image-dir` must fail. | `python run_iter9.py --image-glob "*.jpg"` | Nonzero exit; argparse error. |
| VER-008 | `--recursive` without `--image-dir` must fail. | `python run_iter9.py --recursive` | Nonzero exit; argparse error. |
| VER-009 | `--continue-on-error` without `--image-dir` must fail. | `python run_iter9.py --continue-on-error` | Nonzero exit; argparse error. |
| VER-010 | `--skip-existing` without `--image-dir` must fail. | `python run_iter9.py --skip-existing` | Nonzero exit; argparse error. |
| VER-011 | `--max-images` without `--image-dir` must fail. | `python run_iter9.py --max-images 2` | Nonzero exit; argparse error. |
| VER-012 | `--image-dir` plus `--out-dir` must fail. | `python run_iter9.py --image-dir assets --out-dir results/x` | Nonzero exit; argparse error. |
| VER-013 | `--image-dir` plus explicit `--image` must fail. | `python run_iter9.py --image-dir assets --image assets/foo.png` | Nonzero exit; argparse error. |
| VER-014 | `--image-dir` plus explicit `--image=` must fail. | `python run_iter9.py --image-dir assets --image=assets/foo.png` | Nonzero exit; argparse error. |
| VER-015 | `--image-dir` plus `--image-manifest` must fail. | `python run_iter9.py --image-dir assets --image-manifest assets/SOURCE_IMAGE_HASH.json` | Nonzero exit; argparse error. |
| VER-016 | `--max-images 0` in sweep mode must fail. | `python run_iter9.py --image-dir assets --max-images 0` | Nonzero exit; argparse error. |
| VER-017 | Abbreviated `--image-g` must fail. | `python run_iter9.py --image-g "*.jpg"` | Nonzero exit; argparse error. |
| VER-018 | Abbreviated `--rec` must fail. | `python run_iter9.py --rec` | Nonzero exit; argparse error. |
| VER-019 | Abbreviated `--image-man` must fail. | `python run_iter9.py --image-dir assets --image-man x.json` | Nonzero exit; argparse error. |
| VER-020 | Traceability inspection must verify batch summary root keys and exact row-field set. | Inspect `iter9_image_sweep_summary.json`, `iter9_image_sweep_summary.csv`, and `iter9_image_sweep_summary.md` at batch root. | Root schema, counts, normalized row fields, and CSV field order match this matrix. |
| VER-021 | Traceability inspection must verify one sweep child metrics contains `batch_context`. | Open one child metrics JSON under the batch root. | `batch_context` exists and contains the complete context schema. |
| VER-022 | Traceability inspection must verify single-image metrics omits `batch_context`. | Open `results/iter9_manual_single_validation/metrics_iter9_<board>.json`. | `batch_context` key is absent. |
| VER-023 | Traceability inspection must verify no forbidden source file changed. | `git diff --name-only` | Output excludes every forbidden file. |

## 14. Requirement-To-Test Coverage Summary

| Requirement Family | Required Tests |
|---|---|
| Help surface | `test_help_exposes_all_image_sweep_flags` |
| Argparse abbreviation | `test_argparse_rejects_abbreviated_long_flags` |
| CLI mode conflicts | `test_sweep_only_flags_without_image_dir_fail`, `test_image_dir_plus_explicit_image_fails`, `test_image_dir_plus_out_dir_fails`, `test_image_dir_plus_image_manifest_fails`, `test_max_images_zero_fails` |
| Discovery | `test_discovery_direct_matches_are_sorted`, `test_discovery_recursive_includes_nested_matches`, `test_discovery_applies_max_images_after_sorting`, `test_discovery_missing_directory_fails`, `test_discovery_file_instead_of_directory_fails`, `test_discovery_empty_match_fails` |
| Discovery and warmup failure summaries | `test_discovery_failure_writes_failure_summary_and_returns_1`, `test_warmup_failure_writes_failure_summary_and_returns_1` |
| Path collision | `test_child_output_directory_includes_full_board_label`, `test_sanitized_stem_collisions_include_sha_and_path_hash`, `test_case_insensitive_stem_collisions_are_detected`, `test_same_stem_same_sha_duplicate_produces_distinct_child_directories` |
| Metrics schema | `test_build_metrics_document_includes_optional_batch_context`, `test_batch_context_passed_to_single_run_is_complete` |
| Row helpers | `test_success_failure_skipped_row_helpers_return_exact_field_set_and_mapping` |
| Summary field order | `test_image_sweep_summary_fields_exact_order` |
| Summary writing | `test_md_table_cell_escapes_pipes_and_newlines`, `test_summaries_write_json_csv_and_markdown`, `test_summary_markdown_escapes_table_cells`, `test_summary_writer_accepts_image_dir_string_and_stores_images_discovered` |
| Batch execution | `test_batch_runner_calls_single_run_once_per_image`, `test_validation_failure_writes_failed_row_and_summary`, `test_fail_fast_stops_after_first_runtime_failure_and_writes_summaries`, `test_continue_on_error_attempts_all_images`, `test_skip_existing_prevents_single_run_call` |
| Skip-existing sequencing | `test_skip_existing_metrics_path_uses_derived_full_board_label`, `test_skip_existing_prevents_single_run_call` |
| Raw argv provenance | `test_single_run_receives_exact_raw_argv`, `test_command_invocation_uses_exact_raw_argv_prefix` |

## 15. Manual Traceability Inspection Checklist

After the automated tests and smoke commands pass, inspect the generated files in this order:

1. Open the batch root summary JSON.
2. Verify root keys are exactly:
   - `schema_version`
   - `batch_identity`
   - `batch_timing`
   - `images_discovered`
   - `rows_recorded`
   - `runs_attempted`
   - `runs_succeeded`
   - `runs_failed`
   - `runs_skipped`
   - `rows`
3. Verify `schema_version` is `iter9_image_sweep.v1`.
4. Verify `batch_identity.image_dir` is the exact string passed to the summary writer.
5. Verify every row contains exactly the `IMAGE_SWEEP_SUMMARY_FIELDS` key set.
6. Open the batch CSV.
7. Verify the CSV header order exactly matches `IMAGE_SWEEP_SUMMARY_FIELDS`.
8. Open the batch Markdown.
9. Verify table cells with pipes, backslashes, carriage returns, or newlines are escaped or flattened by `_md_table_cell(...)`.
10. Open one successful sweep child metrics JSON.
11. Verify `batch_context` exists.
12. Open the single-image smoke metrics JSON.
13. Verify `batch_context` is absent.
14. Run `git diff --name-only`.
15. Verify no forbidden source file is modified.

## 16. Completion Gate

The traceability matrix is satisfied only when every row below is true:

```text
Every implementation row maps to an implemented code location.
Every test row maps to a concrete unittest method.
Every required unittest method exists in tests/test_iter9_image_sweep_contract.py.
Every required unittest method passes.
The full unittest discovery command exits 0.
The help command exits 0 and lists all sweep flags.
Every invalid CLI verification command exits nonzero.
No forbidden source file is modified.
README contains the image-sweep usage section.
AGENTS contains the Iter9 Image Sweep Contract section.
Row helpers return exactly IMAGE_SWEEP_SUMMARY_FIELDS keys.
Success rows set error_type and error_message to None.
Failure rows set error_type and error_message from the caught exception.
Skipped rows set expected metrics_path and status skipped_existing.
Discovery failures write batch summary files before returning 1.
Warmup failures write batch summary files before returning 1.
Summary JSON rows are normalized through IMAGE_SWEEP_SUMMARY_FIELDS projection.
CSV field order matches IMAGE_SWEEP_SUMMARY_FIELDS order.
command_invocation uses ["run_iter9.py", *raw_argv].
No sys.argv usage exists inside single-run metrics composition.
resolve_source_image_config(...) is called inside the child loop, not before it.
--skip-existing uses the derived full board label before the skip decision.
Manual validation uses assets/line_art_irl_11_v2.png.
Manual traceability inspection confirms batch_context presence for sweep metrics and absence for single-image metrics.
```
