"""Source/test modularity smoke tests."""

from __future__ import annotations

import unittest
from pathlib import Path

from tests.demo.iter9_visual_solver.helpers.import_boundary_assertions import assert_no_file_exceeds_line_limit


class SourceFileModularityTests(unittest.TestCase):
    def test_demo_runtime_files_do_not_exceed_line_limit(self):
        runtime_root = Path("demos/iter9_visual_solver")
        if not runtime_root.exists():
            self.skipTest("demo runtime package is not implemented yet")
        assert_no_file_exceeds_line_limit(self, runtime_root, max_lines=500)

    def test_demo_test_files_do_not_exceed_line_limit(self):
        test_root = Path("tests/demo/iter9_visual_solver")
        if not test_root.exists():
            self.skipTest("demo test package is not present")
        assert_no_file_exceeds_line_limit(self, test_root, max_lines=500)


if __name__ == "__main__":
    unittest.main()
