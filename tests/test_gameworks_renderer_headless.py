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
        cascade.current()  # drive _idx forward before checking done
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
# Overlay panel click routing — regression for "Solve Board does nothing"
# ---------------------------------------------------------------------------

class TestOverlayPanelClickRouting:
    """Regression: when _panel_overlay is True, the board rect covers the full
    window width.  Panel button clicks were silently swallowed by the board drag
    handler (returned None) before reaching handle_panel.

    These tests reproduce the exact bug condition by forcing _panel_overlay=True
    and positioning a button inside the board rect, then asserting handle_event
    returns the expected action string rather than None.
    """

    def _make_overlay_renderer(self):
        import pygame as _pg
        _pg.init()
        _pg.display.set_mode((800, 600))
        from gameworks.engine import GameEngine
        from gameworks.renderer import Renderer
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        r = Renderer(eng)
        # Force overlay mode and place the dev button INSIDE the board rect
        # — this is exactly what happens on a 300×370 board (board rect spans
        # the full window width, panel buttons land inside it).
        r._panel_overlay = True
        board_rect = r._board_rect()
        r._btn_dev_solve.x = board_rect.x + 10
        r._btn_dev_solve.y = board_rect.y + 10
        return r, eng

    def test_dev_solve_click_returns_action_not_none(self):
        """REGRESSION: clicking _btn_dev_solve in overlay mode must return
        'dev:solve', not None (board drag handler must not swallow it)."""
        r, _ = self._make_overlay_renderer()
        pos = r._btn_dev_solve.center
        ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos})
        action = r.handle_event(ev)
        assert action == "dev:solve", (
            f"Overlay button click returned {action!r}; expected 'dev:solve'. "
            "Board drag handler likely swallowed the MOUSEBUTTONDOWN event."
        )
        pygame.quit()

    def test_restart_click_in_overlay_not_swallowed(self):
        """Other overlay panel buttons must also not be swallowed."""
        r, _ = self._make_overlay_renderer()
        board_rect = r._board_rect()
        r._btn_new.x = board_rect.x + 10
        r._btn_new.y = board_rect.y + 10
        pos = r._btn_new.center
        ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": pos})
        action = r.handle_event(ev)
        assert action == "restart", (
            f"Overlay restart button click returned {action!r}; expected 'restart'."
        )
        pygame.quit()

    def test_board_click_outside_panel_still_works(self):
        """Board cell clicks that do NOT land on a panel button must still register."""
        r, _ = self._make_overlay_renderer()
        # Move all buttons far off-screen so no panel button intercepts the click
        for btn in (r._btn_new, r._btn_help, r._btn_fog,
                    r._btn_save, r._btn_restart, r._btn_dev_solve):
            btn.x, btn.y = 9999, 9999

        ox = r.BOARD_OX + r._pan_x
        oy = r.BOARD_OY + r._pan_y
        cell_px = ox + r._tile // 2
        cell_py = oy + r._tile // 2

        ev_dn = pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"button": 1, "pos": (cell_px, cell_py)})
        ev_up = pygame.event.Event(pygame.MOUSEBUTTONUP,   {"button": 1, "pos": (cell_px, cell_py)})
        r.handle_event(ev_dn)
        action = r.handle_event(ev_up)
        assert action is not None and action.startswith("click:"), (
            f"Board cell click must return 'click:x,y' when not on a panel button; got {action!r}"
        )
        pygame.quit()


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
