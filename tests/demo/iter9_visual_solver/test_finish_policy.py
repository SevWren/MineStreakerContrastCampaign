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

    def test_close_immediately_returns_true_for_any_elapsed(self):
        try:
            from demos.iter9_visual_solver.playback.finish_policy import should_auto_close
        except ModuleNotFoundError:
            self.skipTest("should_auto_close is not implemented yet")
        config = DemoConfigBuilder().with_finish_mode("close_immediately").build_dict()
        finish_behavior = config["window"]["finish_behavior"]
        self.assertTrue(should_auto_close(finish_behavior, elapsed_after_finish_s=0), msg="close_immediately must return True at elapsed=0")
        self.assertTrue(should_auto_close(finish_behavior, elapsed_after_finish_s=999), msg="close_immediately must return True at any elapsed time")

    def test_close_after_seconds_respects_threshold(self):
        try:
            from demos.iter9_visual_solver.playback.finish_policy import should_auto_close
        except ModuleNotFoundError:
            self.skipTest("should_auto_close is not implemented yet")
        finish_behavior = {"mode": "close_after_delay", "close_after_seconds": 5.0}
        self.assertFalse(should_auto_close(finish_behavior, elapsed_after_finish_s=4.9), msg="Must not auto-close before threshold")
        self.assertTrue(should_auto_close(finish_behavior, elapsed_after_finish_s=5.0), msg="Must auto-close at or after threshold")


if __name__ == "__main__":
    unittest.main()
