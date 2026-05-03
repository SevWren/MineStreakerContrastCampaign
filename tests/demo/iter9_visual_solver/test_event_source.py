"""Tests for playback event source selection."""

from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np

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

    def test_lazy_final_grid_replay_exposes_metadata_and_row_major_batches(self):
        from demos.iter9_visual_solver.playback.event_source import (
            STATE_MINE,
            STATE_SAFE,
            build_lazy_playback_events_from_final_grid,
        )

        grid = GridBuilder(height=2, width=3).with_mines([(0, 1), (1, 2)]).build()
        store = build_lazy_playback_events_from_final_grid(grid)
        self.assertEqual(store.total_count, 6)
        self.assertEqual(store.mine_count, 2)
        self.assertEqual(store.board_width, 3)
        self.assertEqual(store.board_height, 2)
        batch = store.batch(1, 5)
        self.assertEqual(batch.steps.dtype, np.uint32)
        self.assertEqual(batch.y.dtype, np.uint32)
        self.assertEqual(batch.x.dtype, np.uint32)
        self.assertEqual(batch.state_codes.dtype, np.uint8)
        self.assertEqual(list(zip(batch.y.tolist(), batch.x.tolist())), [(0, 1), (0, 2), (1, 0), (1, 1)])
        self.assertEqual(batch.state_codes.tolist(), [STATE_MINE, STATE_SAFE, STATE_SAFE, STATE_SAFE])

    def test_final_grid_store_does_not_materialize_cell_events_for_metadata(self):
        from demos.iter9_visual_solver.playback.event_source import build_lazy_playback_events_from_final_grid

        grid = GridBuilder(height=4, width=4).with_mines([(0, 0)]).build()
        with patch("demos.iter9_visual_solver.playback.event_source.PlaybackEvent") as event_model:
            store = build_lazy_playback_events_from_final_grid(grid)
            self.assertEqual(store.total_count, 16)
            self.assertEqual(store.mine_count, 1)
            event_model.assert_not_called()

    def test_typed_store_rejects_coordinate_overflow(self):
        from demos.iter9_visual_solver.playback.event_source import TypedPlaybackEventStore, STATE_SAFE

        with self.assertRaises(ValueError):
            TypedPlaybackEventStore(
                steps=np.array([0], dtype=np.uint32),
                y=np.array([3], dtype=np.uint32),
                x=np.array([0], dtype=np.uint32),
                state_codes=np.array([STATE_SAFE], dtype=np.uint8),
                board_width=1,
                board_height=3,
            )


if __name__ == "__main__":
    unittest.main()
