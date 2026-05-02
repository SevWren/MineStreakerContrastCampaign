"""Tests for configurable finish behavior."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.builders.config_builder import DemoConfigBuilder


class FinishPolicyTests(unittest.TestCase):
    def test_default_stay_open_never_auto_closes(self):
        try:
            from demos.iter9_visual_solver.playback.finish_policy import should_auto_close
        except ModuleNotFoundError:
            self.skipTest("should_auto_close is not implemented yet")
        config = DemoConfigBuilder().with_finish_mode("stay_open").build_dict()
        self.assertFalse(should_auto_close(config["window"]["finish_behavior"], elapsed_after_finish_s=999))


if __name__ == "__main__":
    unittest.main()
