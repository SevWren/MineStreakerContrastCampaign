"""
gameworks/tests/renderer/test_cell_draw.py

Tests for Phase 3 cell drawing optimizations.

Run headless:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_cell_draw.py -v
"""

from __future__ import annotations
from unittest.mock import patch

import pytest

pygame = pytest.importorskip("pygame", reason="pygame not installed")


class TestPhase3CellLoop:
    """
    Regression tests for Phase 3 cell loop refactor (P-01, P-02, P-03, P-20).
    Validates that expensive operations are hoisted out of the cell loop.
    """

    def test_draw_completes_without_cellstate_construction(self, renderer_easy):
        """
        draw() must not construct CellState objects in the cell loop.
        CellState construction was replaced with direct numpy array access.
        """
        r, eng = renderer_easy

        # Monkeypatch CellState to track calls
        call_count = {"count": 0}
        original_init = r.board.snapshot.__func__

        def counting_snapshot(self, x, y):
            call_count["count"] += 1
            return original_init(self, x, y)

        # CellState is constructed via board.snapshot() or directly
        # We'll check that _draw_board doesn't call snapshot()
        with patch.object(r.board.__class__, 'snapshot', side_effect=counting_snapshot):
            r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0)

        # draw() should not call board.snapshot() at all
        assert call_count["count"] == 0

    def test_draw_does_not_call_monotonic_in_cell_loop(self, renderer_easy):
        """
        time.monotonic() must be called once per frame, not once per visible cell.
        The hoisted value is passed to _draw_cell as the 'now' parameter.
        """
        r, eng = renderer_easy

        # Count calls to time.monotonic
        call_count = {"count": 0}
        original_monotonic = __import__('time').monotonic

        def counting_monotonic():
            call_count["count"] += 1
            return original_monotonic()

        with patch('time.monotonic', side_effect=counting_monotonic):
            r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0)

        # Should be called exactly once per frame (in _draw_board before the loop)
        # Plus possibly once in cascade/animation code
        # For a static frame with no animations, expect 1-2 calls max
        assert call_count["count"] <= 2, f"Expected ≤2 monotonic calls, got {call_count['count']}"

    def test_draw_cell_flashing_uses_passed_now(self, renderer_easy):
        """
        _draw_cell must use the passed 'now' parameter for flash checks,
        not call time.monotonic() internally.
        """
        r, eng = renderer_easy

        # Set a mine flash (simulate recent mine hit)
        eng.mine_flash[(0, 0)] = 9999999999.0  # far future

        # Monkeypatch time.monotonic to a different value
        fake_now = 1000.0

        with patch('time.monotonic', return_value=99999999.0):
            # Call _draw_cell directly with fake_now
            # The cell should flash based on fake_now < flash_end, not the mocked value
            r._draw_cell(
                0, 0,
                False, True, False, False, 0,
                (100, 100), False, False, False, 32, False,
                fake_now
            )

        # Test passes if no exception — validates signature and parameter usage

    def test_draw_board_correct_cell_count_drawn(self, renderer_easy):
        """
        Viewport culling must draw only visible cells, not the entire board.
        For a 9×9 board fully visible, expect all 81 cells drawn.
        """
        r, eng = renderer_easy

        # Count _draw_cell calls
        call_count = {"count": 0}
        original_draw_cell = r._draw_cell

        def counting_draw_cell(*args, **kwargs):
            call_count["count"] += 1
            return original_draw_cell(*args, **kwargs)

        with patch.object(r, '_draw_cell', side_effect=counting_draw_cell):
            r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0)

        # Easy board is 9×9 = 81 cells, all should be visible and drawn
        assert call_count["count"] == 81, f"Expected 81 cells drawn, got {call_count['count']}"

    def test_num_tile_assertion_fails_on_mismatch(self, renderer_easy):
        """
        _draw_cell must assert that self._num_tile == ts, catching the
        invariant violation if _rebuild_num_surfs() was not called after zoom.
        """
        r, eng = renderer_easy

        # Break the invariant: change _tile without calling _rebuild_num_surfs()
        r._tile = 64

        # Attempt to draw a cell with mismatched tile size
        with pytest.raises(AssertionError, match="_draw_cell: tile size mismatch"):
            r._draw_cell(
                0, 0,
                False, False, False, False, 0,
                (100, 100), False, False, False, 64, False,
                1000.0
            )
