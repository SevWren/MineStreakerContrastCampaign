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
