"""Tests for event trace writer."""

from __future__ import annotations

import json
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

    def test_write_event_trace_writes_valid_jsonl_for_nonempty_events(self):
        try:
            from demos.iter9_visual_solver.io.event_trace_writer import write_event_trace
            from demos.iter9_visual_solver.domain.playback_event import PlaybackEvent
        except ModuleNotFoundError:
            self.skipTest("write_event_trace or PlaybackEvent is not implemented yet")
        events = [
            PlaybackEvent(step=0, y=0, x=0, state="MINE", display="flag"),
            PlaybackEvent(step=1, y=0, x=1, state="SAFE", display="reveal"),
        ]
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.jsonl"
            write_event_trace(events, path)
            lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        self.assertEqual(len(lines), 2, msg="Each event should produce one JSONL line")
        for line in lines:
            parsed = json.loads(line)
            self.assertIsInstance(parsed, dict, msg=f"Each JSONL line must be a JSON object, got: {line!r}")


if __name__ == "__main__":
    unittest.main()
