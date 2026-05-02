"""Tests for event trace loader."""

from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
