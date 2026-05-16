"""Shared semantic assertions for demo tests."""

from __future__ import annotations


def assert_board_dimensions(testcase, actual_width: int, actual_height: int, expected_width: int, expected_height: int) -> None:
    testcase.assertEqual(int(actual_width), int(expected_width))
    testcase.assertEqual(int(actual_height), int(expected_height))


def assert_event_sequence_is_monotonic(testcase, events) -> None:
    steps = [int(getattr(event, "step", event.get("step"))) for event in events]
    testcase.assertEqual(steps, sorted(steps))


def assert_replay_finished(testcase, replay_state) -> None:
    testcase.assertTrue(getattr(replay_state, "finished", False))


def assert_status_snapshot_matches_metrics(testcase, snapshot, metrics: dict) -> None:
    testcase.assertEqual(snapshot.board_width, int(metrics["board_width"]))
    testcase.assertEqual(snapshot.board_height, int(metrics["board_height"]))
    testcase.assertEqual(snapshot.seed, int(metrics["seed"]))
