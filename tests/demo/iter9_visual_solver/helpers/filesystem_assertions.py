"""Shared filesystem assertions."""

from __future__ import annotations

from pathlib import Path


def assert_file_exists(testcase, path: Path | str) -> None:
    testcase.assertTrue(Path(path).is_file(), f"Expected file to exist: {path}")


def assert_no_root_ad_hoc_files(testcase, project_root: Path | str) -> None:
    root = Path(project_root)
    forbidden = ["demo_config.py", "demo_visualizer.py"]
    for name in forbidden:
        testcase.assertFalse((root / name).exists(), f"Forbidden root file exists: {name}")


def assert_only_expected_files_written(testcase, root: Path | str, expected_relative_paths: set[str]) -> None:
    root = Path(root)
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    testcase.assertEqual(actual, set(expected_relative_paths))
