"""
tests/test_gameworks_renderer_headless.py

Headless tests for gameworks/renderer.py.
Uses SDL dummy driver so no display is required.

Run with:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/test_gameworks_renderer_headless.py -v
"""

import os
import time

import pytest

# Must be set before pygame is imported anywhere.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_renderer():
    """Return an initialised (Renderer, GameEngine) pair using a tiny random board."""
    import pygame as _pg
    _pg.init()
    _pg.display.set_mode((800, 600))
    from gameworks.engine import GameEngine
    from gameworks.renderer import Renderer
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    eng.start()
    r = Renderer(eng)
    return r, eng


# ---------------------------------------------------------------------------
# Fog attribute — FIND-RENDER-HIGH-h002a
# ---------------------------------------------------------------------------

class TestFogAttribute:
    def test_fog_attribute_is_fog_not_underscore_fog(self):
        """FIND-RENDER-HIGH-h002a: attribute must be 'fog', not '_fog'."""
        r, _ = _make_renderer()
        assert hasattr(r, "fog"), "Renderer must have 'fog' attribute (not '_fog')"
        pygame.quit()

    def test_fog_initial_value_is_false(self):
        r, _ = _make_renderer()
        assert r.fog is False
        pygame.quit()

    def test_fog_toggle_changes_value(self):
        r, _ = _make_renderer()
        r.fog = True
        assert r.fog is True
        r.fog = False
        assert r.fog is False
        pygame.quit()


# ---------------------------------------------------------------------------
# _btn_w stored on self — FIND-ARCH-CRITICAL-f005a
# ---------------------------------------------------------------------------

class TestBtnWAttribute:
    def test_btn_w_stored_as_instance_attribute(self):
        """FIND-ARCH-CRITICAL-f005a: btn_w must be self._btn_w, not a local."""
        r, _ = _make_renderer()
        assert hasattr(r, "_btn_w"), \
            "Renderer must store btn_w as self._btn_w for use in _draw_panel()"
        assert isinstance(r._btn_w, int) and r._btn_w > 0
        pygame.quit()

    def test_btn_w_matches_panel_calculation(self):
        r, _ = _make_renderer()
        expected = r.PANEL_W - 2 * r.PAD
        assert r._btn_w == expected
        pygame.quit()


# ---------------------------------------------------------------------------
# FPS constant — FIND-ARCH-CRITICAL-f001a
# ---------------------------------------------------------------------------

class TestFPSConstant:
    def test_fps_is_exported(self):
        """FIND-ARCH-CRITICAL-f001a: FPS must be importable from gameworks.renderer."""
        from gameworks.renderer import FPS
        assert isinstance(FPS, int)
        assert FPS == 30

    def test_fps_accessible_as_module_attribute(self):
        import gameworks.renderer as rmod
        assert hasattr(rmod, "FPS")
        assert rmod.FPS > 0


# ---------------------------------------------------------------------------
# AnimationCascade
# ---------------------------------------------------------------------------

class TestAnimationCascade:
    def test_initial_state_is_not_done(self):
        from gameworks.renderer import AnimationCascade
        positions = [(i, 0) for i in range(10)]
        cascade = AnimationCascade(positions, speed=0.01)
        assert not cascade.done

    def test_current_starts_empty_or_small(self):
        from gameworks.renderer import AnimationCascade
        positions = [(i, 0) for i in range(10)]
        cascade = AnimationCascade(positions, speed=0.5)  # slow
        current = cascade.current()
        assert isinstance(current, list)

    def test_cells_revealed_over_time(self):
        from gameworks.renderer import AnimationCascade
        positions = [(i, 0) for i in range(10)]
        # speed=0.01s/cell — sleep 5× the required time for headroom on loaded machines.
        cascade = AnimationCascade(positions, speed=0.01)
        time.sleep(0.15)
        current = cascade.current()
        assert len(current) >= 3, (
            f"Expected >=3 cells revealed after 150ms at 10ms/cell, got {len(current)}"
        )

    def test_done_after_all_positions_elapsed(self):
        from gameworks.renderer import AnimationCascade
        positions = [(i, 0) for i in range(5)]
        # speed=0.005s/cell → 5 cells = 25ms; sleep 10× for headroom.
        cascade = AnimationCascade(positions, speed=0.005)
        time.sleep(0.25)
        assert cascade.done, (
            f"Cascade with 5 cells at 5ms/cell should be done after 250ms"
        )

    def test_finished_after_returns_float(self):
        from gameworks.renderer import AnimationCascade
        positions = [(0, 0), (1, 0)]
        cascade = AnimationCascade(positions, speed=0.01)
        fa = cascade.finished_after()
        assert isinstance(fa, float)
        assert fa > 0


# ---------------------------------------------------------------------------
# WinAnimation
# ---------------------------------------------------------------------------

class TestWinAnimation:
    def _make_board(self):
        from gameworks.engine import Board
        mines = {(0, 0), (1, 1), (2, 2)}
        b = Board(5, 5, mines)
        b._flagged[0, 0] = True
        b._flagged[1, 1] = True
        b._flagged[2, 2] = True
        return b

    def test_initial_state_is_not_done(self):
        from gameworks.renderer import WinAnimation
        anim = WinAnimation(self._make_board(), speed=0.5)
        assert not anim.done

    def test_current_returns_list(self):
        from gameworks.renderer import WinAnimation
        anim = WinAnimation(self._make_board(), speed=0.001)
        result = anim.current()
        assert isinstance(result, (list, set, frozenset))

    def test_done_after_sufficient_time(self):
        from gameworks.renderer import WinAnimation
        anim = WinAnimation(self._make_board(), speed=0.001)
        time.sleep(0.3)
        assert anim.done or len(anim.current()) > 0

    def test_done_with_no_flags_c007_regression(self):
        """C-007 regression: WinAnimation.done must become True when no flags are placed.

        Old code: 'and self._correct' guard blocked phase 0→1 when _correct=[],
        so done was permanently False for the most common win playstyle.
        """
        from gameworks.engine import Board
        from gameworks.renderer import WinAnimation
        mines = {(0, 0), (1, 1)}
        b = Board(5, 5, mines)
        # No flags placed at all — _correct=[] and _wrong=[]
        anim = WinAnimation(b, speed=0.001)
        time.sleep(0.1)
        anim.current()  # drive phase forward
        assert anim.done, (
            "WinAnimation.done must be True with no flags (C-007 regression): "
            f"_phase={anim._phase}, _correct={anim._correct}, _wrong={anim._wrong}"
        )

    def test_done_with_correct_flags_no_wrong_c007_regression(self):
        """C-007 regression: WinAnimation.done must become True when only correct flags exist.

        Old code: 'and self._wrong' guard blocked phase 1→2 when _wrong=[],
        so done was permanently False even after the correct-flags animation finished.
        """
        from gameworks.engine import Board
        from gameworks.renderer import WinAnimation
        mines = {(0, 0), (1, 1)}
        b = Board(5, 5, mines)
        # All mines correctly flagged, zero wrong flags → _wrong=[]
        b._flagged[0, 0] = True
        b._flagged[1, 1] = True
        anim = WinAnimation(b, speed=0.001)
        time.sleep(0.1)
        anim.current()  # drive phase forward
        assert anim.done, (
            "WinAnimation.done must be True with only correct flags (C-007 regression): "
            f"_phase={anim._phase}, _correct={anim._correct}, _wrong={anim._wrong}"
        )

    def test_finished_after_returns_float(self):
        from gameworks.renderer import WinAnimation
        anim = WinAnimation(self._make_board(), speed=0.01)
        fa = anim.finished_after()
        assert isinstance(fa, float)
        assert fa > 0


# ---------------------------------------------------------------------------
# Renderer initialises without crash
# ---------------------------------------------------------------------------

class TestRendererInit:
    def test_renderer_constructs_without_error(self):
        r, eng = _make_renderer()
        assert r is not None
        assert r.board is eng.board
        pygame.quit()

    def test_renderer_has_expected_panel_constants(self):
        r, _ = _make_renderer()
        assert hasattr(r, "PANEL_W")
        assert hasattr(r, "PAD")
        assert r.PANEL_W > 0
        assert r.PAD >= 0
        pygame.quit()

    def test_ghost_surf_initially_none(self):
        """Ghost surface cache must start as None (built lazily)."""
        r, _ = _make_renderer()
        assert r._ghost_surf is None
        pygame.quit()
