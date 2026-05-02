"""Tests for playback event batching."""

from __future__ import annotations

import unittest


class EventBatchingTests(unittest.TestCase):
    def test_events_per_frame_uses_target_fps(self):
        try:
            from demos.iter9_visual_solver.playback.event_batching import calculate_events_per_frame
        except ModuleNotFoundError:
            self.skipTest("calculate_events_per_frame is not implemented yet")
        self.assertEqual(calculate_events_per_frame(events_per_second=600, target_fps=60), 10)

    def test_events_per_frame_rounds_up_to_avoid_dropping_speed(self):
        from demos.iter9_visual_solver.playback.event_batching import calculate_events_per_frame

        self.assertEqual(calculate_events_per_frame(events_per_second=61, target_fps=60), 2)

    def test_batching_disabled_returns_one_event_per_frame(self):
        from demos.iter9_visual_solver.playback.event_batching import calculate_events_per_frame

        self.assertEqual(
            calculate_events_per_frame(
                events_per_second=600,
                target_fps=60,
                batch_events_per_frame=False,
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()
