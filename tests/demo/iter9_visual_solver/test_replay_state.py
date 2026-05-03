"""Tests for replay state."""

from __future__ import annotations

import unittest

from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
from demos.iter9_visual_solver.playback.replay_state import ReplayState


class ReplayStateTests(unittest.TestCase):
    def test_replay_state_tracks_finished(self):
        state = ReplayState(total_events=0)
        self.assertTrue(state.finished)

    def test_replay_state_tracks_applied_counters_and_snapshot_speed(self):
        events = [
            PlaybackEvent(step=0, y=0, x=0, state="MINE", display="flag"),
            PlaybackEvent(step=1, y=0, x=1, state="SAFE", display="reveal"),
        ]
        state = ReplayState(events=events, events_per_second=12000, board_width=2, board_height=1)
        self.assertEqual(state.total_count, 2)
        self.assertEqual(state.applied_count, 0)
        state.apply_batch(events)
        self.assertEqual(state.applied_count, 2)
        self.assertTrue(state.finished)
        snapshot = state.snapshot()
        self.assertEqual(snapshot.events_per_second, 12000)
        self.assertEqual(snapshot.mines_flagged, 1)


if __name__ == "__main__":
    unittest.main()
