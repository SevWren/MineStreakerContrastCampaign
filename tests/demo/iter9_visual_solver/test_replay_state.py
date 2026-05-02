"""Tests for replay state."""

from __future__ import annotations

import unittest


class ReplayStateTests(unittest.TestCase):
    def test_replay_state_tracks_finished(self):
        try:
            from demos.iter9_visual_solver.playback.replay_state import ReplayState
        except ModuleNotFoundError:
            self.skipTest("ReplayState is not implemented yet")
        state = ReplayState(total_events=0)
        self.assertTrue(state.finished)


if __name__ == "__main__":
    unittest.main()
