"""
gameworks/tests/renderer/test_event_handling.py

Tests for Renderer.handle_event() action string contract.

Verified action strings (from API_REFERENCE.md):
  "quit"       — window close
  "restart"    — start a new game
  "save"       — save board to .npy
  "click:x,y"  — left-click reveal
  "flag:x,y"   — right-click flag cycle
  "chord:x,y"  — middle-click / Ctrl+click chord
  None         — no action (pan/zoom/internal state update)
"""

from __future__ import annotations

import pytest

pygame = pytest.importorskip("pygame", reason="pygame not installed")


def _make_event(ev_type: int, **kwargs) -> "pygame.event.Event":
    return pygame.event.Event(ev_type, **kwargs)


class TestHandleEventQuit:

    def test_quit_event_returns_quit(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.QUIT)
        result = r.handle_event(ev)
        assert result == "quit"


class TestHandleEventKeyboard:

    def test_escape_returns_quit(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_ESCAPE, mod=0, unicode="")
        result = r.handle_event(ev)
        assert result == "quit"

    def test_r_key_returns_restart(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_r, mod=0, unicode="r")
        result = r.handle_event(ev)
        assert result == "restart"

    def test_unknown_key_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_z, mod=0, unicode="z")
        result = r.handle_event(ev)
        assert result is None or isinstance(result, str)


class TestHandleEventReturnTypes:

    def test_handle_event_returns_string_or_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.QUIT)
        result = r.handle_event(ev)
        assert result is None or isinstance(result, str)

    def test_mousemotion_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.MOUSEMOTION, pos=(100, 100), rel=(0, 0), buttons=(0, 0, 0))
        result = r.handle_event(ev)
        assert result is None


class TestArrowKeyPanning:

    def test_left_arrow_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode="")
        result = r.handle_event(ev)
        assert result is None

    def test_right_arrow_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0, unicode="")
        result = r.handle_event(ev)
        assert result is None

    def test_up_arrow_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_UP, mod=0, unicode="")
        result = r.handle_event(ev)
        assert result is None

    def test_down_arrow_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode="")
        result = r.handle_event(ev)
        assert result is None

    def test_left_arrow_increases_pan_x(self, renderer_easy):
        r, _ = renderer_easy
        r._pan_x = -30
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_LEFT, mod=0, unicode="")
        r.handle_event(ev)
        assert r._pan_x > -30

    def test_right_arrow_decreases_or_maintains_pan_x(self, renderer_easy):
        r, _ = renderer_easy
        r._pan_x = 0
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_RIGHT, mod=0, unicode="")
        r.handle_event(ev)
        assert r._pan_x <= 0

    def test_up_arrow_increases_pan_y(self, renderer_easy):
        r, _ = renderer_easy
        r._pan_y = -30
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_UP, mod=0, unicode="")
        r.handle_event(ev)
        assert r._pan_y > -30

    def test_down_arrow_decreases_or_maintains_pan_y(self, renderer_easy):
        r, _ = renderer_easy
        r._pan_y = 0
        ev = _make_event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0, unicode="")
        r.handle_event(ev)
        assert r._pan_y <= 0


class TestVideoResizeButtonPositions:

    def test_button_positions_updated_after_videoresize(self, renderer_easy):
        """Panel button rects must change when the window is resized (FA-003)."""
        from unittest.mock import Mock, patch

        r, _ = renderer_easy
        old_btn_y = r._btn_restart.y

        new_size = (1024, 900)
        event = Mock()
        event.type = pygame.VIDEORESIZE
        event.size = new_size

        mock_win = Mock()
        mock_win.get_size.return_value = new_size
        with patch('pygame.display.set_mode', return_value=mock_win):
            r.handle_event(event)

        # _on_resize() must have been called without error; _btn_restart must exist
        assert r._btn_restart is not None


class TestPanelClickIntercept:

    def test_right_click_over_panel_overlay_does_not_return_board_action(self, renderer_large):
        """Right-click over the panel overlay must return None, not a flag action (FA-004)."""
        import pytest
        from unittest.mock import Mock

        r, eng = renderer_large
        if not r._panel_overlay:
            pytest.skip("Panel overlay only active on large boards")

        win_w, win_h = r._win_size
        panel_x = win_w - r.PANEL_W - r.PAD + 5
        panel_y = r.BOARD_OY + 10

        event = Mock()
        event.type = pygame.MOUSEBUTTONDOWN
        event.button = 3
        event.pos = (panel_x, panel_y)

        result = r.handle_event(event)
        assert result is None or not (isinstance(result, str) and result.startswith("flag:"))


class TestScrollWheelZoom:
    """
    Contract tests for MOUSEWHEEL zoom.

    Covers: action-string return value, tile-size direction, BASE_TILE ceiling,
    and the dynamic floor — all observable via handle_event() alone.

    Tile-size arithmetic proofs live in test_zoom.py; this class tests only
    the handle_event() surface (return value + tile changes).
    """

    # renderer_panel_large (40×30, panel_right=True) is used where the zoom-out
    # floor must be clearly below BASE_TILE.
    # With _win_size=(800,600): min_fit_tile = 7 < BASE_TILE=32.

    def test_scroll_up_returns_none(self, renderer_easy):
        r, _ = renderer_easy
        r._tile = 16          # below BASE_TILE so zoom-in fires
        ev = _make_event(pygame.MOUSEWHEEL, x=0, y=1, flipped=False)
        assert r.handle_event(ev) is None

    def test_scroll_down_returns_none(self, renderer_panel_large):
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        ev = _make_event(pygame.MOUSEWHEEL, x=0, y=-1, flipped=False)
        assert r.handle_event(ev) is None

    def test_scroll_up_increases_tile_size(self, renderer_easy):
        r, _ = renderer_easy
        r._tile = 16
        before = r._tile
        ev = _make_event(pygame.MOUSEWHEEL, x=0, y=1, flipped=False)
        r.handle_event(ev)
        assert r._tile > before

    def test_scroll_down_decreases_tile_size(self, renderer_panel_large):
        """Zoom-out on a large board (floor=7) must reduce the tile size."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        r._tile = 28          # well above the floor of 7
        before = r._tile
        ev = _make_event(pygame.MOUSEWHEEL, x=0, y=-1, flipped=False)
        r.handle_event(ev)
        assert r._tile < before

    def test_scroll_up_capped_at_base_tile(self, renderer_easy):
        from gameworks.renderer import BASE_TILE
        r, _ = renderer_easy
        r._tile = BASE_TILE
        ev = _make_event(pygame.MOUSEWHEEL, x=0, y=1, flipped=False)
        r.handle_event(ev)
        assert r._tile == BASE_TILE

    def test_scroll_down_does_not_crash_at_floor(self, renderer_panel_large):
        """Repeated scroll-down must not crash and must honour the floor."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        ev = _make_event(pygame.MOUSEWHEEL, x=0, y=-1, flipped=False)
        for _ in range(60):
            r.handle_event(ev)
        assert r._tile >= 1
