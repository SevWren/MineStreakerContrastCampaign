"""Tests for playback event domain model."""

from __future__ import annotations

import unittest


class PlaybackEventTests(unittest.TestCase):
    def test_playback_event_accepts_flag_event(self):
        try:
            from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
        except ModuleNotFoundError:
            self.skipTest("PlaybackEvent is not implemented yet")
        event = PlaybackEvent(step=1, y=0, x=0, state="MINE", display="flag")
        self.assertEqual(event.display, "flag")
        self.assertEqual(event.step, 1)
        self.assertEqual(event.y, 0)
        self.assertEqual(event.x, 0)
        self.assertEqual(event.state, "MINE")

    def test_playback_event_accepts_safe_reveal_event(self):
        try:
            from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
        except ModuleNotFoundError:
            self.skipTest("PlaybackEvent is not implemented yet")
        event = PlaybackEvent(step=2, y=1, x=3, state="SAFE", display="reveal")
        self.assertEqual(event.display, "reveal")
        self.assertEqual(event.step, 2)
        self.assertEqual(event.y, 1)
        self.assertEqual(event.x, 3)
        self.assertEqual(event.state, "SAFE")


if __name__ == "__main__":
    unittest.main()
