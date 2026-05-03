"""Tests for event scheduler."""

from __future__ import annotations

import unittest

from demos.iter9_visual_solver.playback.event_scheduler import EventScheduler


class EventSchedulerTests(unittest.TestCase):
    def test_scheduler_returns_batches_in_order(self):
        scheduler = EventScheduler(events=[1, 2, 3], events_per_frame=2)
        self.assertEqual(scheduler.next_batch(), [1, 2])
        self.assertEqual(scheduler.next_batch(), [3])

    def test_scheduler_respects_batch_size_and_final_partial_batch(self):
        scheduler = EventScheduler(events=[1, 2, 3, 4, 5], events_per_frame=2)
        self.assertEqual(scheduler.next_batch(), [1, 2])
        self.assertEqual(scheduler.next_batch(), [3, 4])
        self.assertEqual(scheduler.next_batch(), [5])

    def test_scheduler_reports_completion_and_counts(self):
        scheduler = EventScheduler(events=[1, 2, 3], events_per_frame=2)
        self.assertFalse(scheduler.finished)
        self.assertEqual(scheduler.applied_count, 0)
        self.assertEqual(scheduler.total_count, 3)
        scheduler.next_batch()
        self.assertEqual(scheduler.applied_count, 2)
        scheduler.next_batch()
        self.assertTrue(scheduler.finished)
        self.assertEqual(scheduler.applied_count, 3)
        self.assertEqual(scheduler.next_batch(), [])

    def test_scheduler_does_not_drop_or_duplicate_events(self):
        events = list(range(11))
        scheduler = EventScheduler(events=events, events_per_frame=3)
        emitted = []
        while not scheduler.finished:
            emitted.extend(scheduler.next_batch())
        self.assertEqual(emitted, events)

    def test_empty_event_list_finishes_immediately(self):
        scheduler = EventScheduler(events=[], events_per_frame=3)
        self.assertTrue(scheduler.finished)
        self.assertEqual(scheduler.applied_count, 0)
        self.assertEqual(scheduler.total_count, 0)
        self.assertEqual(scheduler.next_batch(), [])


if __name__ == "__main__":
    unittest.main()
