"""Tests for playback speed policy."""

from __future__ import annotations

import unittest
from pathlib import Path
from types import SimpleNamespace

from tests.demo.iter9_visual_solver.builders.config_builder import DemoConfigBuilder
from demos.iter9_visual_solver.playback.speed_policy import calculate_events_per_second


class SpeedPolicyTests(unittest.TestCase):
    def test_mine_count_scaled_speed_uses_multiplier(self):
        config = DemoConfigBuilder().with_base_events_per_second(1000).with_mine_count_multiplier(0.10).build()
        speed = calculate_events_per_second(config.playback, total_mines=5000)
        self.assertEqual(speed, 1500, msg="speed = base(1000) + mines(5000)*multiplier(0.10) = 1500")

    def test_speed_clamps_to_min(self):
        config = (
            DemoConfigBuilder()
            .with_min_events_per_second(50)
            .with_base_events_per_second(10)
            .with_mine_count_multiplier(0)
            .build()
        )
        speed = calculate_events_per_second(config.playback, total_mines=100)
        self.assertEqual(speed, 50, msg="calculated speed 10 is below min 50, must clamp to min=50")

    def test_speed_clamps_to_max(self):
        config = DemoConfigBuilder().with_base_events_per_second(1000).with_mine_count_multiplier(10).with_max_events_per_second(2000).build()
        speed = calculate_events_per_second(config.playback, total_mines=5000)
        self.assertEqual(speed, 2000, msg="calculated speed 51000 exceeds max 2000, must clamp to max=2000")

    def test_zero_mines_returns_at_least_minimum_speed(self):
        config = DemoConfigBuilder().with_min_events_per_second(50).with_base_events_per_second(0).build()
        speed = calculate_events_per_second(config.playback, total_mines=0)
        self.assertEqual(speed, 50, msg="zero mines with base=0 must still return minimum speed 50")

    def test_large_mine_count_does_not_exceed_maximum_speed(self):
        config = DemoConfigBuilder().with_base_events_per_second(1000).with_mine_count_multiplier(10).with_max_events_per_second(12000).build()
        speed = calculate_events_per_second(config.playback, total_mines=1_000_000)
        self.assertEqual(speed, 12000, msg="very large mine count must clamp to max=12000")

    def test_returned_speed_is_integer(self):
        config = DemoConfigBuilder().with_base_events_per_second(1000).with_mine_count_multiplier(0.25).build()
        speed = calculate_events_per_second(config.playback, total_mines=5)
        self.assertIsInstance(speed, int, msg="calculate_events_per_second must return int, not float")

    def test_negative_mine_count_is_rejected(self):
        config = DemoConfigBuilder().build()
        with self.assertRaisesRegex(ValueError, "total_mines=-1.*>= 0"):
            calculate_events_per_second(config.playback, total_mines=-1)

    def test_none_mine_count_is_rejected(self):
        config = DemoConfigBuilder().build()
        with self.assertRaises(TypeError):
            calculate_events_per_second(config.playback, total_mines=None)

    def test_raw_dict_config_is_rejected(self):
        config = DemoConfigBuilder().build_dict()
        with self.assertRaisesRegex(TypeError, "PlaybackConfig.*not a dict"):
            calculate_events_per_second(config["playback"], total_mines=1)

    def test_unsupported_mode_is_rejected_defensively(self):
        config = SimpleNamespace(
            mode="static",
            min_events_per_second=50,
            base_events_per_second=1000,
            mine_count_multiplier=0.08,
            max_events_per_second=12000,
        )
        with self.assertRaisesRegex(ValueError, "playback.mode='static'.*mine_count_scaled"):
            calculate_events_per_second(config, total_mines=1)

    def test_speed_policy_does_not_import_pygame(self):
        path = Path("demos/iter9_visual_solver/playback/speed_policy.py")
        self.assertTrue(path.exists(), msg=f"Source file missing: {path}")
        source = path.read_text(encoding="utf-8")
        self.assertNotIn("pygame", source)


if __name__ == "__main__":
    unittest.main()
