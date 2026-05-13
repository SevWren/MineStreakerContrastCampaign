"""Architecture boundary tests for the demo package."""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.demo.iter9_visual_solver.helpers.filesystem_assertions import assert_no_root_ad_hoc_files
from tests.demo.iter9_visual_solver.helpers.import_boundary_assertions import (
    assert_import_only_allowed_under,
    assert_module_does_not_import,
    assert_package_does_not_import,
)


class ArchitectureBoundariesTests(unittest.TestCase):
    def test_no_root_level_demo_modules_exist(self):
        assert_no_root_ad_hoc_files(self, Path("."))

    def test_runtime_package_areas_exist_once_implemented(self):
        runtime_root = Path("demos/iter9_visual_solver")
        if not runtime_root.exists():
            self.skipTest("demo runtime package is not implemented yet")
        for package in ["cli", "config", "contracts", "domain", "errors", "io", "playback", "rendering"]:
            self.assertTrue((runtime_root / package).is_dir(), f"Missing runtime package: {package}")
            self.assertTrue((runtime_root / package / "__init__.py").is_file(), f"Missing __init__.py in runtime package: {package}")

    def test_pygame_imports_are_rendering_only(self):
        runtime_root = Path("demos/iter9_visual_solver")
        if not runtime_root.exists():
            self.skipTest("demo runtime package is not implemented yet")
        assert_import_only_allowed_under(
            self,
            Path("."),
            "pygame",
            [
                "demos/iter9_visual_solver/rendering",
                "tests/demo/iter9_visual_solver/fixtures",
                "tests/demo/iter9_visual_solver",
                "gameworks",
                "tests/test_gameworks_engine.py",
                "tests/test_gameworks_renderer_headless.py",
            ],
        )

    def test_pydantic_imports_are_config_only(self):
        runtime_root = Path("demos/iter9_visual_solver")
        if not runtime_root.exists():
            self.skipTest("demo runtime package is not implemented yet")
        assert_import_only_allowed_under(
            self,
            Path("."),
            "pydantic",
            ["demos/iter9_visual_solver/config"],
        )

    def test_jsonschema_is_test_only(self):
        runtime_root = Path("demos/iter9_visual_solver")
        if not runtime_root.exists():
            self.skipTest("demo runtime package is not implemented yet")
        assert_import_only_allowed_under(
            self,
            Path("."),
            "jsonschema",
            ["tests/demo/iter9_visual_solver"],
        )

    def test_domain_modules_are_pure(self):
        runtime_root = Path("demos/iter9_visual_solver/domain")
        if not runtime_root.exists():
            self.skipTest("demo runtime package is not implemented yet")
        for forbidden in ["pygame", "pydantic", "jsonschema"]:
            assert_package_does_not_import(self, runtime_root, forbidden)

    def test_playback_modules_do_not_render_or_load_files(self):
        runtime_root = Path("demos/iter9_visual_solver/playback")
        if not runtime_root.exists():
            self.skipTest("demo runtime package is not implemented yet")
        for forbidden in ["pygame", "pydantic", "jsonschema"]:
            assert_package_does_not_import(self, runtime_root, forbidden)

    def test_io_modules_do_not_render(self):
        runtime_root = Path("demos/iter9_visual_solver/io")
        if not runtime_root.exists():
            self.skipTest("demo runtime package is not implemented yet")
        assert_package_does_not_import(self, runtime_root, "pygame")

    def test_rendering_modules_do_not_validate_config(self):
        runtime_root = Path("demos/iter9_visual_solver/rendering")
        if not runtime_root.exists():
            self.skipTest("demo runtime package is not implemented yet")
        for forbidden in ["pydantic", "jsonschema"]:
            assert_package_does_not_import(self, runtime_root, forbidden)

    def test_run_iter9_hook_does_not_import_pygame(self):
        assert_module_does_not_import(self, Path("run_iter9.py"), "pygame")

    def test_demo_schema_docs_are_under_demo_docs(self):
        schema_root = Path("demo/docs/json_schemas")
        self.assertTrue(schema_root.is_dir(), f"Missing demo schema root: {schema_root}")
        forbidden = [
            Path("docs/json_schema/iter9_visual_solver_demo_config.schema.json"),
            Path("docs/json_schema/solver_event_trace.schema.json"),
            Path("schemas/iter9_visual_solver_demo_config.schema.json"),
            Path("schemas/solver_event_trace.schema.json"),
        ]
        offenders = [path.as_posix() for path in forbidden if path.exists()]
        self.assertEqual(offenders, [], f"Demo schema file found outside demo/docs/json_schemas/: {offenders}")


if __name__ == "__main__":
    unittest.main()
