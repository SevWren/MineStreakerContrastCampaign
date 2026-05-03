"""Tests for event scheduler."""

from __future__ import annotations

import unittest

import numpy as np

from demos.iter9_visual_solver.playback.event_scheduler import EventScheduler
from demos.iter9_visual_solver.playback.event_source import STATE_SAFE, TypedPlaybackEventStore


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

    def test_scheduler_returns_typed_batch_views_without_list_slicing(self):
        store = TypedPlaybackEventStore(
            steps=np.arange(5, dtype=np.uint32),
            y=np.zeros(5, dtype=np.uint32),
            x=np.arange(5, dtype=np.uint32),
            state_codes=np.full(5, STATE_SAFE, dtype=np.uint8),
            board_width=5,
            board_height=1,
        )
        scheduler = EventScheduler(events=store, events_per_frame=2)
        first = scheduler.next_batch()
        second = scheduler.next_batch()
        self.assertIs(first.steps.base, store.steps)
        self.assertEqual(first.x.tolist(), [0, 1])
        self.assertEqual(second.x.tolist(), [2, 3])


if __name__ == "__main__":
    unittest.main()
