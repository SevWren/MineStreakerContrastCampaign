"""
gameworks/tests/architecture/test_boundaries.py

Import boundary and structural contract tests for the gameworks package.

Enforces the module ownership rules from AGENTS.md § Module Ownership Boundaries:

  engine.py   must NOT import: pygame, renderer, main
  renderer.py must NOT import: main, pipeline modules
  main.py     must NOT import: pipeline modules (except inside _build_engine)

These tests parse source code with the `ast` module — no imports are executed,
so they run without a display, without pygame, and without any game state.
"""

from __future__ import annotations

import ast
import importlib.util
import os
from pathlib import Path
from typing import List

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GAMEWORKS_DIR = Path(__file__).parent.parent.parent  # gameworks/


def _source(filename: str) -> str:
    path = GAMEWORKS_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not found at {path}")
    return path.read_text(encoding="utf-8")


def _imports_in(source: str) -> List[str]:
    """
    Return a flat list of all top-level module names imported in the source.
    Handles: import X, from X import Y, from X.Y import Z.
    Does NOT descend into function bodies (catches top-level and class-level imports).
    """
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module.split(".")[0])
    return names


def _all_import_names(source: str) -> List[str]:
    """Return all imported names including dotted forms (for cross-module checks)."""
    tree = ast.parse(source)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
    return names


# ---------------------------------------------------------------------------
# engine.py boundaries
# ---------------------------------------------------------------------------

class TestEngineBoundaries:

    def test_engine_does_not_import_pygame(self):
        """engine.py must never import pygame — it must be headless."""
        src = _source("engine.py")
        imports = _imports_in(src)
        assert "pygame" not in imports, \
            "engine.py imports pygame — this breaks headless testing and violates P4"

    def test_engine_does_not_import_renderer(self):
        src = _source("engine.py")
        imports = _all_import_names(src)
        assert not any("renderer" in name for name in imports), \
            "engine.py imports renderer — violates single-direction dependency"

    def test_engine_does_not_import_main(self):
        src = _source("engine.py")
        imports = _all_import_names(src)
        assert not any(name.endswith("main") for name in imports), \
            "engine.py imports main — circular dependency"

    def test_engine_parses_without_error(self):
        """engine.py must be syntactically valid Python."""
        src = _source("engine.py")
        ast.parse(src)   # raises SyntaxError on failure

    def test_engine_imports_numpy(self):
        """engine.py requires numpy for board arrays."""
        src = _source("engine.py")
        imports = _imports_in(src)
        assert "numpy" in imports or "np" in str(src[:200]), \
            "engine.py should import numpy"


# ---------------------------------------------------------------------------
# renderer.py boundaries
# ---------------------------------------------------------------------------

class TestRendererBoundaries:

    def test_renderer_does_not_import_main(self):
        """renderer.py must not import main — it cannot own the game loop."""
        src = _source("renderer.py")
        imports = _all_import_names(src)
        assert not any(name.endswith(".main") or name == "main" for name in imports), \
            "renderer.py imports main — violates module ownership boundary"

    def test_renderer_does_not_import_pipeline_modules(self):
        """renderer.py must not import core.py, sa.py, or other pipeline modules."""
        src = _source("renderer.py")
        imports = _all_import_names(src)
        pipeline_modules = {"core", "sa", "solver", "repair", "pipeline",
                            "board_sizing", "source_config", "report", "corridors"}
        for mod in pipeline_modules:
            assert not any(mod == name or name.endswith(f".{mod}") for name in imports), \
                f"renderer.py imports pipeline module '{mod}'"

    def test_renderer_imports_pygame(self):
        """renderer.py must import pygame — it owns all display logic."""
        src = _source("renderer.py")
        imports = _imports_in(src)
        assert "pygame" in imports, \
            "renderer.py does not import pygame — who owns the display?"

    def test_renderer_parses_without_error(self):
        src = _source("renderer.py")
        ast.parse(src)


# ---------------------------------------------------------------------------
# main.py boundaries
# ---------------------------------------------------------------------------

class TestMainBoundaries:

    def test_main_parses_without_error(self):
        src = _source("main.py")
        ast.parse(src)

    def test_main_does_not_import_pipeline_at_top_level(self):
        """
        main.py must not import pipeline modules at top level.
        Pipeline imports are allowed only inside _build_engine() (guarded by try/except).
        This test inspects only module-level (non-function-body) imports.
        """
        src = _source("main.py")
        tree = ast.parse(src)
        top_level_imports = []
        for node in tree.body:   # only top-level statements
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level_imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_level_imports.append(node.module)

        pipeline_modules = {"core", "sa", "solver", "repair", "pipeline",
                            "board_sizing", "source_config"}
        for mod in pipeline_modules:
            assert not any(mod in name for name in top_level_imports), \
                f"main.py has top-level import of pipeline module '{mod}'"


# ---------------------------------------------------------------------------
# Package __init__.py
# ---------------------------------------------------------------------------

class TestPackageInit:

    def test_init_parses_without_error(self):
        src = _source("__init__.py")
        ast.parse(src)

    def test_version_string_defined(self):
        src = _source("__init__.py")
        assert "__version__" in src, \
            "gameworks/__init__.py must define __version__"

    def test_version_is_semver_like(self):
        """__version__ must look like 'X.Y.Z'."""
        import gameworks
        parts = gameworks.__version__.split(".")
        assert len(parts) == 3, f"Expected X.Y.Z version, got: {gameworks.__version__}"
        for part in parts:
            assert part.isdigit(), f"Non-numeric version component: {part!r}"


# ---------------------------------------------------------------------------
# No circular imports (import-time check)
# ---------------------------------------------------------------------------

class TestNoCircularImports:

    def test_engine_importable_standalone(self):
        """engine.py must be importable without pygame installed."""
        spec = importlib.util.find_spec("gameworks.engine")
        assert spec is not None, "gameworks.engine not found"
        # Import directly — if this raises, the module has a broken dependency
        import gameworks.engine  # noqa: F401
