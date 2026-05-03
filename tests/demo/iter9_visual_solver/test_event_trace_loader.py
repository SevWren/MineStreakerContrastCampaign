"""Tests for event trace loader."""

from __future__ import annotations

import unittest
import json

from tests.demo.iter9_visual_solver.builders.event_trace_builder import EventTraceBuilder
from tests.demo.iter9_visual_solver.fixtures.temp_runs import make_temp_iter9_run_dir


class EventTraceLoaderTests(unittest.TestCase):
    def test_load_event_trace_reads_jsonl_rows(self):
        try:
            from demos.iter9_visual_solver.io.event_trace_loader import load_event_trace
        except ModuleNotFoundError:
            self.skipTest("load_event_trace is not implemented yet")
        text = EventTraceBuilder().flag(0, 0).safe(1, 1).build_jsonl()
        with make_temp_iter9_run_dir() as run:
            path = run.write_event_trace_artifact(text)
            events = load_event_trace(path)
        self.assertEqual(len(events), 2)

    def test_load_typed_event_trace_streams_rows_into_typed_store(self):
        from demos.iter9_visual_solver.io.event_trace_loader import load_typed_event_trace
        from demos.iter9_visual_solver.playback.event_source import STATE_MINE, STATE_SAFE

        text = EventTraceBuilder().flag(0, 0).safe(1, 1).build_jsonl()
        with make_temp_iter9_run_dir() as run:
            path = run.write_event_trace_artifact(text)
            store = load_typed_event_trace(path, board_width=3, board_height=2)
        self.assertEqual(store.total_count, 2)
        self.assertEqual(store.mine_count, 1)
        self.assertEqual(store.steps.dtype.name, "uint32")
        self.assertEqual(store.state_codes.tolist(), [STATE_MINE, STATE_SAFE])

    def test_load_event_trace_rejects_decreasing_steps(self):
        from demos.iter9_visual_solver.errors.trace_errors import DemoTraceValidationError
        from demos.iter9_visual_solver.io.event_trace_loader import load_event_trace

        rows = EventTraceBuilder().flag(0, 0).safe(0, 1).build_rows()
        rows[1]["step"] = 0
        text = "\n".join(json.dumps(row) for row in rows)
        with make_temp_iter9_run_dir() as run:
            path = run.write_event_trace_artifact(text)
            with self.assertRaisesRegex(DemoTraceValidationError, "decreasing step"):
                load_event_trace(path)

    def test_load_event_trace_rejects_duplicate_steps(self):
        from demos.iter9_visual_solver.errors.trace_errors import DemoTraceValidationError
        from demos.iter9_visual_solver.io.event_trace_loader import load_event_trace

        rows = EventTraceBuilder().flag(0, 0).safe(0, 1).build_rows()
        rows[1]["step"] = rows[0]["step"]
        text = "\n".join(json.dumps(row) for row in rows)
        with make_temp_iter9_run_dir() as run:
            path = run.write_event_trace_artifact(text)
            with self.assertRaisesRegex(DemoTraceValidationError, "duplicate step"):
                load_event_trace(path)


if __name__ == "__main__":
    unittest.main()
