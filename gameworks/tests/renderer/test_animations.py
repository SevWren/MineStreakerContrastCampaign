"""
gameworks/tests/renderer/test_animations.py

Tests for AnimationCascade and WinAnimation.

These classes have no pygame display dependency and can run without a window,
but they live in renderer.py so this file sits in the renderer/ directory.
"""

from __future__ import annotations

import time

import pytest

pygame = pytest.importorskip("pygame", reason="pygame not installed")


# ---------------------------------------------------------------------------
# AnimationCascade
# ---------------------------------------------------------------------------

class TestAnimationCascade:

    def test_import(self):
        from gameworks.renderer import AnimationCascade
        assert AnimationCascade is not None

    def test_initial_not_done(self):
        from gameworks.renderer import AnimationCascade
        anim = AnimationCascade([(i, 0) for i in range(10)], speed=0.5)
        assert not anim.done

    def test_empty_positions_immediately_done(self):
        from gameworks.renderer import AnimationCascade
        anim = AnimationCascade([], speed=0.01)
        assert anim.done

    def test_current_returns_list(self):
        from gameworks.renderer import AnimationCascade
        anim = AnimationCascade([(0, 0), (1, 0)], speed=0.5)
        result = anim.current()
        assert isinstance(result, list)

    def test_current_grows_over_time(self):
        from gameworks.renderer import AnimationCascade
        positions = [(i, 0) for i in range(20)]
        anim = AnimationCascade(positions, speed=0.01)
        time.sleep(0.05)
        count = len(anim.current())
        assert count >= 3, f"Expected >=3 cells revealed after 50ms, got {count}"

    def test_done_when_all_elapsed(self):
        from gameworks.renderer import AnimationCascade
        anim = AnimationCascade([(i, 0) for i in range(5)], speed=0.005)
        time.sleep(0.1)
        # Call .current() to advance _idx, then check .done
        _ = anim.current()
        assert anim.done

    def test_current_does_not_exceed_total(self):
        from gameworks.renderer import AnimationCascade
        positions = [(i, 0) for i in range(5)]
        anim = AnimationCascade(positions, speed=0.001)
        time.sleep(0.5)
        assert len(anim.current()) <= len(positions)

    def test_finished_after_returns_positive_float(self):
        from gameworks.renderer import AnimationCascade
        anim = AnimationCascade([(0, 0), (1, 0), (2, 0)], speed=0.05)
        fa = anim.finished_after()
        assert isinstance(fa, float)
        assert fa > 0

    def test_single_position(self):
        from gameworks.renderer import AnimationCascade
        anim = AnimationCascade([(3, 7)], speed=0.001)
        time.sleep(0.05)
        # Call .current() to advance _idx
        current = anim.current()
        assert anim.done
        assert (3, 7) in current


# ---------------------------------------------------------------------------
# WinAnimation
# ---------------------------------------------------------------------------

class TestWinAnimation:

    def _board_with_flags(self):
        """3 mines, all flagged — standard WinAnimation input."""
        from gameworks.engine import Board
        mines = {(0, 0), (1, 1), (2, 2)}
        b = Board(5, 5, mines)
        for (x, y) in mines:
            b._flagged[y, x] = True
        return b

    def test_import(self):
        from gameworks.renderer import WinAnimation
        assert WinAnimation is not None

    def test_initial_not_done(self):
        from gameworks.renderer import WinAnimation
        anim = WinAnimation(self._board_with_flags(), speed=5.0)
        assert not anim.done

    def test_current_returns_iterable(self):
        from gameworks.renderer import WinAnimation
        anim = WinAnimation(self._board_with_flags(), speed=0.001)
        result = anim.current()
        assert hasattr(result, "__iter__")

    def test_done_after_enough_time(self):
        from gameworks.renderer import WinAnimation
        anim = WinAnimation(self._board_with_flags(), speed=0.001)
        time.sleep(0.5)
        # Call .current() to advance _phase, then check .done
        _ = anim.current()
        assert anim.done

    def test_finished_after_positive(self):
        from gameworks.renderer import WinAnimation
        anim = WinAnimation(self._board_with_flags(), speed=0.01)
        fa = anim.finished_after()
        assert isinstance(fa, float)
        assert fa > 0

    def test_correct_done_property(self):
        from gameworks.renderer import WinAnimation
        anim = WinAnimation(self._board_with_flags(), speed=0.001)
        time.sleep(0.5)
        # Call .current() to advance _phase, then check .correct_done
        _ = anim.current()
        assert anim.correct_done

    def test_no_flags_board_is_immediately_done(self):
        """A board with no flagged cells should produce a completed animation at once."""
        from gameworks.engine import Board
        from gameworks.renderer import WinAnimation
        b = Board(5, 5, {(0, 0)})
        anim = WinAnimation(b, speed=0.01)
        # With no flags, animation has nothing to reveal — should be done immediately
        assert anim.done or len(list(anim.current())) == 0
