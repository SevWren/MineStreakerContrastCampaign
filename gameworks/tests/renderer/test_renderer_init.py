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
