"""Tests for playback event batching."""

from __future__ import annotations

import unittest
from pathlib import Path

from demos.iter9_visual_solver.playback.event_batching import calculate_events_per_frame


class EventBatchingTests(unittest.TestCase):
    def test_events_per_frame_uses_target_fps(self):
        self.assertEqual(calculate_events_per_frame(events_per_second=600, target_fps=60), 10)

    def test_events_per_frame_rounds_up_to_avoid_dropping_speed(self):
        self.assertEqual(calculate_events_per_frame(events_per_second=61, target_fps=60), 2)

    def test_events_per_frame_is_at_least_one(self):
        self.assertEqual(calculate_events_per_frame(events_per_second=1, target_fps=60), 1)

    def test_batching_disabled_returns_one_event_per_frame(self):
        self.assertEqual(
            calculate_events_per_frame(
                events_per_second=600,
                target_fps=60,
                batch_events_per_frame=False,
            ),
            1,
        )

    def test_target_fps_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "target_fps=0.*> 0"):
            calculate_events_per_frame(events_per_second=600, target_fps=0)

    def test_events_per_second_must_be_positive(self):
        with self.assertRaisesRegex(ValueError, "events_per_second=0.*> 0"):
            calculate_events_per_frame(events_per_second=0, target_fps=60)

    def test_no_pygame_clock_is_required(self):
        source = Path("demos/iter9_visual_solver/playback/event_batching.py").read_text(encoding="utf-8")
        self.assertNotIn("pygame", source)
        self.assertNotIn("Clock", source)


if __name__ == "__main__":
    unittest.main()
