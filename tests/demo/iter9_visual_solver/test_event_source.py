"""Tests for playback event source selection."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.builders.grid_builder import GridBuilder
from tests.demo.iter9_visual_solver.fixtures.configs import default_demo_config_dict


class EventSourceTests(unittest.TestCase):
    def test_final_grid_replay_builds_deterministic_cell_events(self):
        from demos.iter9_visual_solver.playback.event_source import build_playback_events_from_final_grid

        grid = GridBuilder(height=3, width=3).with_mines([(0, 0), (2, 2)]).build()
        events = build_playback_events_from_final_grid(grid)
        self.assertEqual([(event.y, event.x) for event in events], [
            (0, 0), (0, 1), (0, 2),
            (1, 0), (1, 1), (1, 2),
            (2, 0), (2, 1), (2, 2),
        ])
        self.assertEqual([event.state for event in events], [
            "MINE", "SAFE", "SAFE",
            "SAFE", "SAFE", "SAFE",
            "SAFE", "SAFE", "MINE",
        ])
        self.assertTrue(all(event.source == "final_grid_replay" for event in events))

    def test_select_event_source_uses_final_grid_fallback(self):
        from demos.iter9_visual_solver.playback.event_source import select_event_source

        grid = GridBuilder(height=2, width=2).with_mines([(1, 1)]).build()
        input_config = default_demo_config_dict()["input"]
        events, source = select_event_source(input_config=input_config, grid=grid, trace_events=None)
        self.assertEqual(source, "final_grid_replay")
        self.assertEqual(len(events), 4)


if __name__ == "__main__":
    unittest.main()
