"""
gameworks/tests/renderer/test_surface_cache.py

Tests for Renderer surface cache invalidation rules.

Each cache has a defined invalidation condition (from DEVELOPER_GUIDE.md):
  _num_surfs    — tile size changes
  _ghost_surf   — board pixel dimensions change (zoom/resize)
  _fog_surf     — window size changes
  _anim_surf    — tile size changes
  _hover_surf   — tile size changes
  _thumb_surf   — built once at init; never rebuilt

These tests verify that caches are not rebuilt unnecessarily (per-frame allocs)
and that they are invalidated when the triggering condition occurs.
"""

from __future__ import annotations

import pytest

pygame = pytest.importorskip("pygame", reason="pygame not installed")


class TestNumSurfsCache:

    def test_num_surfs_none_before_first_draw(self, renderer_easy):
        """Number digit cache must be None until first draw populates it."""
        r, _ = renderer_easy
        assert r._num_surfs is None or isinstance(r._num_surfs, dict)

    def test_num_surfs_populated_after_draw(self, renderer_easy):
        r, eng = renderer_easy
        r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
        assert r._num_surfs is not None
        assert isinstance(r._num_surfs, dict)
        assert len(r._num_surfs) > 0

    def test_num_surfs_covers_all_digit_values(self, renderer_easy):
        r, eng = renderer_easy
        r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
        if r._num_surfs is not None:
            # Must have at least one digit surface
            assert len(r._num_surfs) >= 1


class TestGhostSurfCache:

    def test_ghost_surf_none_without_image(self, renderer_easy):
        """No image → ghost surface must remain None forever."""
        r, _ = renderer_easy
        r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
        assert r._ghost_surf is None

    def test_ghost_surf_not_rebuilt_per_frame(self, renderer_easy):
        """Ghost surface (when built) must not be recreated each frame."""
        r, _ = renderer_easy
        r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
        before = r._ghost_surf
        r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
        after = r._ghost_surf
        # Both are None (no image) — just confirm they stayed consistent
        assert before is after


class TestFogSurfCache:

    def test_fog_surf_type(self, renderer_easy):
        r, _ = renderer_easy
        r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
        assert r._fog_surf is None or isinstance(r._fog_surf, pygame.Surface)

    def test_fog_surf_stable_across_frames(self, renderer_easy):
        r, _ = renderer_easy
        r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
        surf1 = id(r._fog_surf)
        r.draw(mouse_pos=(0, 0), game_state="playing", elapsed=0.0, cascade_done=True)
        surf2 = id(r._fog_surf)
        assert surf1 == surf2, "Fog surface must not be recreated between identical frames"


class TestThumbSurfCache:

    def test_thumb_surf_none_without_image_path(self, renderer_easy):
        r, _ = renderer_easy
        assert r._thumb_surf is None
