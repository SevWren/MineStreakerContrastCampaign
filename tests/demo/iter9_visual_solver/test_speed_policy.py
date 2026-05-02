"""Tests for playback speed policy."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.builders.config_builder import DemoConfigBuilder


class SpeedPolicyTests(unittest.TestCase):
    def test_mine_count_scaled_speed_uses_multiplier(self):
        try:
            from demos.iter9_visual_solver.playback.speed_policy import calculate_events_per_second
        except ModuleNotFoundError:
            self.skipTest("calculate_events_per_second is not implemented yet")
        config = DemoConfigBuilder().with_base_events_per_second(1000).with_mine_count_multiplier(0.10).build_dict()
        speed = calculate_events_per_second(config["playback"], total_mines=5000)
        self.assertEqual(speed, 1500)

    def test_speed_clamps_to_max(self):
        try:
            from demos.iter9_visual_solver.playback.speed_policy import calculate_events_per_second
        except ModuleNotFoundError:
            self.skipTest("calculate_events_per_second is not implemented yet")
        config = DemoConfigBuilder().with_base_events_per_second(1000).with_mine_count_multiplier(10).with_max_events_per_second(2000).build_dict()
        speed = calculate_events_per_second(config["playback"], total_mines=5000)
        self.assertEqual(speed, 2000)


if __name__ == "__main__":
    unittest.main()
