"""Import-boundary assertion helpers.

These helpers intentionally use text scanning instead of importing modules so
architecture tests do not execute side effects.
"""

from __future__ import annotations

import ast
from pathlib import Path


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.add(node.module.split(".")[0])
                names.add(node.module)
    return names


def assert_module_does_not_import(testcase, module_path: Path | str, forbidden_import: str) -> None:
    imports = _imported_names(Path(module_path))
    testcase.assertNotIn(forbidden_import, imports, f"{module_path} imports forbidden dependency {forbidden_import}")


def assert_package_does_not_import(testcase, package_path: Path | str, forbidden_import: str) -> None:
    for path in Path(package_path).rglob("*.py"):
        assert_module_does_not_import(testcase, path, forbidden_import)


def assert_import_only_allowed_under(testcase, project_root: Path | str, import_name: str, allowed_paths: list[str]) -> None:
    root = Path(project_root)
    allowed = [root / item for item in allowed_paths]
    offenders = []
    for path in root.rglob("*.py"):
        if import_name in _imported_names(path) and not any(path.is_relative_to(item) for item in allowed):
            offenders.append(path.relative_to(root).as_posix())
    testcase.assertEqual(offenders, [], f"{import_name} import found outside allowed paths")


def assert_no_forbidden_root_files(testcase, project_root: Path | str, forbidden_names: list[str]) -> None:
    root = Path(project_root)
    offenders = [name for name in forbidden_names if (root / name).exists()]
    testcase.assertEqual(offenders, [])


def assert_no_file_exceeds_line_limit(testcase, path: Path | str, max_lines: int, allowed_exceptions: set[str] | None = None) -> None:
    root = Path(path)
    allowed = allowed_exceptions or set()
    offenders = []
    for py_file in root.rglob("*.py"):
        rel = py_file.relative_to(root).as_posix()
        if rel in allowed:
            continue
        line_count = len(py_file.read_text(encoding="utf-8").splitlines())
        if line_count > int(max_lines):
            offenders.append((rel, line_count))
    testcase.assertEqual(offenders, [], f"Files exceed {max_lines} lines: {offenders}")
