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


if __name__ == "__main__":
    unittest.main()
