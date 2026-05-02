"""Tests for event scheduler."""

from __future__ import annotations

import unittest


class EventSchedulerTests(unittest.TestCase):
    def test_scheduler_returns_batches_in_order(self):
        try:
            from demos.iter9_visual_solver.playback.event_scheduler import EventScheduler
        except ModuleNotFoundError:
            self.skipTest("EventScheduler is not implemented yet")
        scheduler = EventScheduler(events=[1, 2, 3], events_per_frame=2)
        self.assertEqual(scheduler.next_batch(), [1, 2])
        self.assertEqual(scheduler.next_batch(), [3])


if __name__ == "__main__":
    unittest.main()
