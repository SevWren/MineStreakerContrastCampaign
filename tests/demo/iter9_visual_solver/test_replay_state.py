"""Tests for replay state."""

from __future__ import annotations

import unittest

import numpy as np

from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
from demos.iter9_visual_solver.playback.event_source import STATE_MINE, STATE_SAFE, TypedPlaybackEventStore
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

    def test_board_state_counters_handle_duplicates_and_state_changes(self):
        events = [
            PlaybackEvent(step=0, y=0, x=0, state="MINE", display="flag"),
            PlaybackEvent(step=1, y=0, x=0, state="MINE", display="flag"),
            PlaybackEvent(step=2, y=0, x=0, state="SAFE", display="reveal"),
            PlaybackEvent(step=3, y=0, x=1, state="UNKNOWN", display="unknown"),
        ]
        state = ReplayState(events=events, board_width=2, board_height=1)
        state.apply_batch(events)
        self.assertEqual(state.board.mines_flagged, 0, msg="mines_flagged must be 0: final cell state is SAFE, not MINE")
        self.assertEqual(state.board.safe_cells_solved, 1, msg="safe_cells_solved must be 1: cell (0,0) ends in SAFE state")
        self.assertEqual(state.board.unknown_remaining, 1, msg="unknown_remaining must be 1: cell (0,1) is UNKNOWN")

    def test_snapshot_uses_counters_without_scanning_cells(self):
        store = TypedPlaybackEventStore(
            steps=np.array([0, 1], dtype=np.uint32),
            y=np.array([0, 0], dtype=np.uint32),
            x=np.array([0, 1], dtype=np.uint32),
            state_codes=np.array([STATE_MINE, STATE_SAFE], dtype=np.uint8),
            board_width=2,
            board_height=1,
        )
        state = ReplayState(events=store)
        state.apply_batch(store.batch(0, 2))
        class NoScanCells(dict):
            def values(self):
                raise AssertionError("snapshot scanned cells")

        state.board.cells = NoScanCells(state.board.cells)
        snapshot = state.snapshot()
        self.assertEqual(snapshot.mines_flagged, 1, msg="snapshot.mines_flagged must be 1 after applying one MINE event")
        self.assertEqual(snapshot.safe_cells_solved, 1, msg="snapshot.safe_cells_solved must be 1 after applying one SAFE event")


if __name__ == "__main__":
    unittest.main()
