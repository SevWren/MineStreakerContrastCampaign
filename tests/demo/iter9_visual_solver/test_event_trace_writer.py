"""Tests for event trace writer."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class EventTraceWriterTests(unittest.TestCase):
    def test_write_event_trace_creates_jsonl_file(self):
        try:
            from demos.iter9_visual_solver.io.event_trace_writer import write_event_trace
        except ModuleNotFoundError:
            self.skipTest("write_event_trace is not implemented yet")
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "solver_event_trace.jsonl"
            write_event_trace([], path)
            self.assertTrue(path.is_file())


if __name__ == "__main__":
    unittest.main()
