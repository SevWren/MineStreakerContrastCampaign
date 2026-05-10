"""
gameworks/tests/cli/test_preflight.py

Tests for gameworks.main.preflight_check().

Status: PENDING — preflight_check() does not exist yet.
Implement per DESIGN_PATTERNS.md § R6 — Preflight Check.

When R6 is implemented:
1. Remove the module-level skip.
2. Update the import to include preflight_check.
3. All tests in this file must pass.
"""

from __future__ import annotations

import os
import tempfile

import pytest

pytestmark = pytest.mark.skip(reason="Pending R6 — preflight_check() not yet implemented")


# ---------------------------------------------------------------------------
# Once R6 is implemented, add to import:
#   from gameworks.main import build_parser, preflight_check
# ---------------------------------------------------------------------------


class TestPreflightCleanArgs:

    def test_random_mode_no_errors(self):
        from gameworks.main import build_parser, preflight_check
        args = build_parser().parse_args(["--random"])
        errors = preflight_check(args)
        assert errors == []

    def test_easy_difficulty_no_errors(self):
        from gameworks.main import build_parser, preflight_check
        args = build_parser().parse_args(["--random", "--easy"])
        errors = preflight_check(args)
        assert errors == []


class TestPreflightMissingFile:

    def test_missing_npy_file_produces_error(self):
        from gameworks.main import build_parser, preflight_check
        args = build_parser().parse_args(["--load", "/tmp/does_not_exist_gameworks.npy"])
        errors = preflight_check(args)
        assert len(errors) > 0
        assert any("not found" in e.lower() or "does_not_exist" in e for e in errors)

    def test_missing_image_file_produces_error(self):
        from gameworks.main import build_parser, preflight_check
        args = build_parser().parse_args(["--image", "/tmp/no_such_image.png"])
        errors = preflight_check(args)
        assert len(errors) > 0

    def test_existing_npy_file_no_error(self):
        from gameworks.main import build_parser, preflight_check
        import numpy as np
        f = tempfile.NamedTemporaryFile(suffix=".npy", delete=False)
        np.save(f.name, np.zeros((5, 5), dtype=np.int8))
        f.close()
        try:
            args = build_parser().parse_args(["--load", f.name])
            errors = preflight_check(args)
            file_errors = [e for e in errors if "not found" in e.lower()]
            assert file_errors == []
        finally:
            os.unlink(f.name)


class TestPreflightReturnType:

    def test_returns_list(self):
        from gameworks.main import build_parser, preflight_check
        args = build_parser().parse_args(["--random"])
        result = preflight_check(args)
        assert isinstance(result, list)

    def test_errors_are_strings(self):
        from gameworks.main import build_parser, preflight_check
        args = build_parser().parse_args(["--load", "/nonexistent.npy"])
        errors = preflight_check(args)
        for e in errors:
            assert isinstance(e, str)
            assert len(e) > 0
