"""
gameworks/tests/renderer/test_renderer_init.py

Tests for Renderer construction, constants, and surface cache initialisation.

Run headless:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_renderer_init.py -v
"""

from __future__ import annotations

import pytest

pygame = pytest.importorskip("pygame", reason="pygame not installed")


class TestRendererConstruction:

    def test_constructs_without_error(self, renderer_easy):
        r, eng = renderer_easy
        assert r is not None

    def test_engine_reference_stored(self, renderer_easy):
        r, eng = renderer_easy
        assert r.engine is eng

    def test_board_reference_matches_engine_board(self, renderer_easy):
        r, eng = renderer_easy
        assert r.board is eng.board

    def test_help_visible_initially_false(self, renderer_easy):
        r, _ = renderer_easy
        assert r.help_visible is False

    def test_fog_initially_false(self, renderer_easy):
        r, _ = renderer_easy
        assert r.fog is False

    def test_cascade_initially_none(self, renderer_easy):
        r, _ = renderer_easy
        assert r.cascade is None

    def test_win_anim_initially_none(self, renderer_easy):
        r, _ = renderer_easy
        assert r.win_anim is None

    def test_pressed_cell_initially_none(self, renderer_easy):
        r, _ = renderer_easy
        assert r.pressed_cell is None


class TestRendererConstants:

    def test_fps_constant_exists_and_positive(self):
        from gameworks.renderer import FPS
        assert isinstance(FPS, int)
        assert FPS > 0

    def test_base_tile_constant(self):
        from gameworks.renderer import BASE_TILE
        assert isinstance(BASE_TILE, int)
        assert BASE_TILE > 0

    def test_min_tile_size_constant(self):
        from gameworks.renderer import MIN_TILE_SIZE
        assert MIN_TILE_SIZE >= 1

    def test_anim_tick_constant(self):
        from gameworks.renderer import ANIM_TICK
        assert 0 < ANIM_TICK < 1.0

    def test_panel_w_constant(self, renderer_easy):
        r, _ = renderer_easy
        assert hasattr(r, "PANEL_W")
        assert r.PANEL_W > 0

    def test_header_h_constant(self, renderer_easy):
        r, _ = renderer_easy
        assert hasattr(r, "HEADER_H")
        assert r.HEADER_H > 0

    def test_pad_constant(self, renderer_easy):
        r, _ = renderer_easy
        assert hasattr(r, "PAD")
        assert r.PAD >= 0

    def test_btn_w_stored_on_self(self, renderer_easy):
        r, _ = renderer_easy
        assert hasattr(r, "_btn_w")
        assert isinstance(r._btn_w, int)
        assert r._btn_w > 0

    def test_btn_w_matches_panel_calculation(self, renderer_easy):
        r, _ = renderer_easy
        assert r._btn_w == r.PANEL_W - 2 * r.PAD


class TestSurfaceCacheInit:

    def test_ghost_surf_initially_none(self, renderer_easy):
        """Ghost surface is built lazily — must be None at init."""
        r, _ = renderer_easy
        assert r._ghost_surf is None

    def test_fog_surf_initially_none_or_surface(self, renderer_easy):
        """Fog surface may be pre-built or lazy; just assert it's consistent."""
        r, _ = renderer_easy
        assert r._fog_surf is None or isinstance(r._fog_surf, pygame.Surface)

    def test_num_surfs_is_dict_after_init(self, renderer_easy):
        """_num_surfs is populated unconditionally in __init__ via _rebuild_num_surfs()."""
        r, _ = renderer_easy
        assert isinstance(r._num_surfs, dict)

    def test_thumb_surf_none_without_image(self, renderer_easy):
        """No image_path → thumbnail surface must be None."""
        r, _ = renderer_easy
        assert r._thumb_surf is None


# ---------------------------------------------------------------------------
# Phase 2: Frame-local value hoisting (P-15, P-17, P-18, P-21)
# ---------------------------------------------------------------------------

class TestPhase2Caches:
    """
    Regression tests for Phase 2 frame-local caching.
    Validates that expensive OS calls are cached and reused within each frame.
    """

    def test_win_size_cache_exists_at_init(self, renderer_easy):
        """_win_size must be populated at init."""
        r, _ = renderer_easy
        assert hasattr(r, "_win_size")
        assert isinstance(r._win_size, tuple)
        assert len(r._win_size) == 2

    def test_win_size_cache_matches_get_size_at_init(self, renderer_easy):
        """_win_size must match _win.get_size() at construction."""
        r, _ = renderer_easy
        assert r._win_size == r._win.get_size()

    def test_board_rect_cache_exists_at_init(self, renderer_easy):
        """_cached_board_rect attribute must exist."""
        r, _ = renderer_easy
        assert hasattr(r, "_cached_board_rect")

    def test_board_rect_cache_initially_none(self, renderer_easy):
        """_cached_board_rect starts None and is populated on first _board_rect() call."""
        r, _ = renderer_easy
        # After __init__ + _center_board(), cache should be None (invalidated)
        assert r._cached_board_rect is None

    def test_board_rect_cache_populated_on_first_call(self, renderer_easy):
        """First call to _board_rect() populates the cache."""
        r, _ = renderer_easy
        rect = r._board_rect()
        assert r._cached_board_rect is not None
        assert rect is r._cached_board_rect

    def test_board_rect_cache_reused_on_second_call(self, renderer_easy):
        """Second call to _board_rect() returns the same cached Rect object."""
        r, _ = renderer_easy
        rect1 = r._board_rect()
        rect2 = r._board_rect()
        assert rect1 is rect2  # same object identity

    def test_last_mouse_pos_exists_at_init(self, renderer_easy):
        """_last_mouse_pos attribute must exist for MOUSEWHEEL zoom."""
        r, _ = renderer_easy
        assert hasattr(r, "_last_mouse_pos")
        assert isinstance(r._last_mouse_pos, tuple)

    def test_renderer_does_not_call_engine_elapsed(self, renderer_easy):
        """
        Renderer must never call engine.elapsed directly (which would re-invoke time.time()).
        The elapsed value is passed to draw() once per frame by main.py.
        """
        r, _ = renderer_easy
        import inspect
        source = inspect.getsource(r.__class__)
        # renderer.py should never reference 'engine.elapsed' or 'self.engine.elapsed'
        assert "engine.elapsed" not in source
        assert "self.engine.elapsed" not in source

    def test_win_size_cache_updated_on_videoresize(self, renderer_easy):
        """_win_size cache must be updated when VIDEORESIZE event is handled."""
        r, _ = renderer_easy
        from unittest.mock import Mock
        import pygame

        # Simulate VIDEORESIZE event
        old_size = r._win_size
        new_size = (1024, 768)
        event = Mock()
        event.type = pygame.VIDEORESIZE
        event.size = new_size

        # Monkeypatch set_mode to return a mock window
        mock_win = Mock()
        mock_win.get_size.return_value = new_size
        original_set_mode = pygame.display.set_mode
        pygame.display.set_mode = Mock(return_value=mock_win)

        try:
            r.handle_event(event)
            # Cache should be updated
            assert r._win_size == new_size
            assert r._win_size != old_size
        finally:
            pygame.display.set_mode = original_set_mode

    def test_board_rect_cache_invalidated_on_pan_change(self, renderer_easy):
        """_cached_board_rect must be invalidated when pan changes."""
        r, _ = renderer_easy
        from unittest.mock import Mock
        import pygame

        # Populate cache
        _ = r._board_rect()
        assert r._cached_board_rect is not None

        # Simulate arrow key pan (LEFT arrow)
        event = Mock()
        event.type = pygame.KEYDOWN
        event.key = pygame.K_LEFT

        r.handle_event(event)
        # Cache should be invalidated
        assert r._cached_board_rect is None

    def test_board_rect_cache_invalidated_on_zoom_change(self, renderer_easy):
        """_cached_board_rect must be invalidated after MOUSEWHEEL zoom."""
        r, _ = renderer_easy
        from unittest.mock import Mock, patch
        import pygame

        # Populate cache
        _ = r._board_rect()
        assert r._cached_board_rect is not None

        # Simulate MOUSEWHEEL zoom OUT (renderer starts at BASE_TILE=32, zoom in would be no-op)
        event = Mock()
        event.type = pygame.MOUSEWHEEL
        event.y = -1  # scroll down = zoom out

        # Monkeypatch pygame.mouse.get_pos to avoid undefined behavior
        with patch('pygame.mouse.get_pos', return_value=(100, 100)):
            r.handle_event(event)

        # Cache should be invalidated (indirectly via _on_resize or _clamp_pan)
        # After zoom, cache is cleared
        assert r._cached_board_rect is None

    def test_draw_smiley_uses_passed_mouse_pos(self, renderer_easy):
        """
        _draw_smiley must use the passed mouse_pos parameter,
        not call pygame.mouse.get_pos() internally.
        """
        r, _ = renderer_easy
        from unittest.mock import patch

        # Monkeypatch pygame.mouse.get_pos to raise if called
        def forbidden_get_pos():
            raise AssertionError("_draw_smiley called pygame.mouse.get_pos() instead of using passed mouse_pos")

        with patch('pygame.mouse.get_pos', side_effect=forbidden_get_pos):
            # Call _draw_smiley with explicit mouse_pos
            # If it tries to call get_pos(), the test will fail
            r._draw_smiley(100, 100, 50, 40, "playing", mouse_pos=(200, 200))

        # Test passes if no assertion raised
