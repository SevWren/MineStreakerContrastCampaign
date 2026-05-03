"""Tests for pygame loop using fakes instead of a real window."""

from __future__ import annotations

import unittest
from pathlib import Path

from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
from tests.demo.iter9_visual_solver.fixtures.pygame_fakes import FakePygameModule


class PygameLoopWithFakesTests(unittest.TestCase):
    def test_loop_can_run_with_fake_pygame(self):
        try:
            from demos.iter9_visual_solver.rendering.pygame_loop import run_pygame_loop
        except ModuleNotFoundError:
            self.skipTest("run_pygame_loop is not implemented yet")
        fake = FakePygameModule()
        result = run_pygame_loop(pygame_module=fake, events=[], max_frames=1)
        self.assertIsNotNone(result)

    def test_loop_applies_configured_event_batches(self):
        from demos.iter9_visual_solver.rendering.pygame_loop import run_pygame_loop

        fake = FakePygameModule()
        events = [
            PlaybackEvent(step=0, y=0, x=0, state="MINE", display="flag"),
            PlaybackEvent(step=1, y=0, x=1, state="SAFE", display="reveal"),
            PlaybackEvent(step=2, y=0, x=2, state="SAFE", display="reveal"),
        ]
        result = run_pygame_loop(
            pygame_module=fake,
            events=events,
            events_per_frame=2,
            board_width=3,
            board_height=1,
            max_frames=1,
        )
        self.assertEqual(result.events_applied, 2)
        self.assertEqual(result.exit_reason, "max_frames_test_limit")
        self.assertTrue(fake.display.created_windows)

    def test_loop_honors_close_immediately_finish_policy(self):
        from demos.iter9_visual_solver.rendering.pygame_loop import run_pygame_loop

        fake = FakePygameModule()
        events = [PlaybackEvent(step=0, y=0, x=0, state="MINE", display="flag")]
        result = run_pygame_loop(
            pygame_module=fake,
            events=events,
            events_per_frame=1,
            board_width=1,
            board_height=1,
            finish_config={"mode": "close_immediately", "close_after_seconds": None},
        )
        self.assertEqual(result.exit_reason, "playback_finished_close_immediately")
        self.assertTrue(result.playback_finished)
        self.assertEqual(result.events_applied, 1)

    def test_loop_honors_stay_open_with_test_frame_limit(self):
        from demos.iter9_visual_solver.rendering.pygame_loop import run_pygame_loop

        fake = FakePygameModule()
        events = [PlaybackEvent(step=0, y=0, x=0, state="MINE", display="flag")]
        result = run_pygame_loop(
            pygame_module=fake,
            events=events,
            events_per_frame=1,
            board_width=1,
            board_height=1,
            finish_config={"mode": "stay_open", "close_after_seconds": None},
            max_frames=2,
        )
        self.assertEqual(result.exit_reason, "max_frames_test_limit")
        self.assertTrue(result.playback_finished)
        self.assertEqual(result.frames_rendered, 2)

    def test_loop_exits_on_user_close_event(self):
        from demos.iter9_visual_solver.rendering.pygame_loop import run_pygame_loop

        fake = FakePygameModule()
        fake.event.events.append(type("FakeQuitEvent", (), {"type": fake.QUIT})())
        result = run_pygame_loop(pygame_module=fake, events=[], max_frames=5)
        self.assertEqual(result.exit_reason, "user_closed_window")
        self.assertTrue(result.closed_by_user)

    def test_loop_does_not_calculate_speed_formula(self):
        source = Path("demos/iter9_visual_solver/rendering/pygame_loop.py").read_text(encoding="utf-8")
        forbidden = [
            "base_events_per_second",
            "mine_count_multiplier",
            "max_events_per_second",
            "min_events_per_second",
        ]
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
