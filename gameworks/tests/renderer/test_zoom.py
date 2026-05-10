"""
gameworks/tests/renderer/test_zoom.py

Tests for the dynamic zoom-out floor system introduced in renderer.py.

Background
----------
The scroll-wheel zoom-out floor was previously a static constant (MIN_TILE_SIZE=10).
It is now computed dynamically each time the user scrolls out, so the board can
always be zoomed until it fits entirely within the viewport:

    avail_w = win_w - BOARD_OX [- PANEL_W - PAD when panel is on the right]
    avail_h = win_h - BOARD_OY
    min_fit_tile = max(1, min(avail_w // board_width, avail_h // board_height))

Key fixtures
------------
renderer_easy   9×9    panel_right=True   min_fit_tile ≈ 32 at 800×600
renderer_large  40×30  panel_right=True   min_fit_tile = 7  at 800×600

All tests that depend on a specific floor value force _win_size=(800,600) so the
result is deterministic regardless of the SDL dummy driver's reported screen size.

Run headless:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/renderer/test_zoom.py -v
"""

from __future__ import annotations

import pytest

pygame = pytest.importorskip("pygame", reason="pygame not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scroll_event(y: int) -> pygame.event.Event:
    """MOUSEWHEEL event: y=1 zoom-in, y=-1 zoom-out."""
    return pygame.event.Event(pygame.MOUSEWHEEL, x=0, y=y, flipped=False)


def _min_fit_tile(r, win_size=None) -> int:
    """
    Mirror the dynamic floor formula from handle_event() without importing
    the private implementation.  Used only to form expected values in assertions.

    Must stay in sync with the MOUSEWHEEL else-branch in renderer.py.
    """
    win_w, win_h = win_size if win_size is not None else r._win_size
    avail_w = win_w - r.BOARD_OX
    if r._panel_right:
        avail_w -= r.PANEL_W + r.PAD
    else:
        avail_w -= r.PAD           # right-margin PAD for non-panel-right layout
    avail_h = win_h - r.BOARD_OY - r.HEADER_H   # matches _clamp_pan zero-pan threshold
    avail_w = max(0, avail_w)
    avail_h = max(0, avail_h)
    return max(1, min(avail_w // r.board.width, avail_h // r.board.height))


def _scroll_out_fully(r, n: int = 50) -> None:
    """Fire n zoom-out events to drive the tile to its floor."""
    ev = _scroll_event(y=-1)
    for _ in range(n):
        r.handle_event(ev)


# ---------------------------------------------------------------------------
# min_fit_tile formula
# ---------------------------------------------------------------------------

class TestMinFitTileFormula:
    """
    Unit tests for the floor-computation formula.

    These tests verify the formula in isolation by constructing expected values
    from the renderer's own layout attributes (BOARD_OX, PANEL_W, …) and
    comparing against the helper above — which mirrors exactly what
    handle_event() now executes.
    """

    def test_formula_subtracts_board_origin_from_window(self, renderer_panel_large):
        """avail dimensions must exclude BOARD_OX/BOARD_OY, not start at 0."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        tile = _min_fit_tile(r)
        # A naive calculation ignoring offsets would be larger
        naive = max(1, min(800 // r.board.width, 600 // r.board.height))
        assert tile <= naive

    def test_formula_panel_right_subtracts_panel_width(self, renderer_panel_large):
        """panel_right=True: PANEL_W + PAD must be removed from avail_w."""
        r, _ = renderer_panel_large
        assert r._panel_right
        r._win_size = (800, 600)
        avail_w = 800 - r.BOARD_OX - r.PANEL_W - r.PAD
        avail_h = 600 - r.BOARD_OY
        expected = max(1, min(avail_w // r.board.width, avail_h // r.board.height))
        assert _min_fit_tile(r) == expected

    def test_formula_no_panel_right_subtracts_right_margin_pad(self):
        """panel_right=False (≥100 cols): right-margin PAD must be subtracted but NOT PANEL_W."""
        from gameworks.engine import GameEngine
        from gameworks.renderer import Renderer
        eng = GameEngine(mode="random", width=100, height=30, mines=100, seed=42)
        eng.start()
        r = Renderer(eng)
        assert not r._panel_right
        r._win_size = (900, 600)
        # Right-margin PAD is subtracted; PANEL_W is not (panel is below, not beside).
        avail_w = max(0, 900 - r.BOARD_OX - r.PAD)
        avail_h = max(0, 600 - r.BOARD_OY - r.HEADER_H)
        expected = max(1, min(avail_w // r.board.width, avail_h // r.board.height))
        assert _min_fit_tile(r, win_size=(900, 600)) == expected

    def test_floor_is_never_zero_or_negative(self, renderer_panel_large):
        """max(1, …) guard: even a tiny viewport must produce a floor of ≥ 1."""
        r, _ = renderer_panel_large
        r._win_size = (300, 200)
        assert _min_fit_tile(r) >= 1

    def test_larger_board_produces_smaller_or_equal_floor(self):
        """Doubling board dimensions must halve (or more) the min_fit_tile."""
        from gameworks.engine import GameEngine
        from gameworks.renderer import Renderer
        WIN = (800, 600)

        eng_s = GameEngine(mode="random", width=9, height=9, mines=10, seed=1)
        eng_s.start()
        r_s = Renderer(eng_s)
        r_s._win_size = WIN

        eng_l = GameEngine(mode="random", width=40, height=30, mines=60, seed=1)
        eng_l.start()
        r_l = Renderer(eng_l)
        r_l._win_size = WIN

        assert _min_fit_tile(r_l) <= _min_fit_tile(r_s)

    def test_larger_window_produces_larger_or_equal_floor(self, renderer_panel_large):
        """Giving the renderer more screen space must raise (or hold) the floor."""
        r, _ = renderer_panel_large
        floor_small = _min_fit_tile(r, win_size=(600, 400))
        floor_large = _min_fit_tile(r, win_size=(1400, 900))
        assert floor_large >= floor_small

    def test_formula_avail_h_uses_header_h_offset(self, renderer_panel_large):
        """avail_h must subtract HEADER_H to match _clamp_pan's zero-pan threshold."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        # Without HEADER_H subtraction, avail_h = 540 and min_fit_tile could differ.
        # With it: avail_h = 492.  For this board both give 7, but the formula path is tested.
        avail_h_correct = max(0, 600 - r.BOARD_OY - r.HEADER_H)
        avail_h_naive   =       600 - r.BOARD_OY
        avail_w = max(0, 800 - r.BOARD_OX - r.PANEL_W - r.PAD)
        # Verify the helper uses the correct formula
        expected = max(1, min(avail_w // r.board.width, avail_h_correct // r.board.height))
        assert _min_fit_tile(r) == expected
        # Confirm the naive formula would differ for a tall enough board
        assert avail_h_correct < avail_h_naive   # 492 < 540

    def test_floor_for_known_40x30_at_800x600(self, renderer_panel_large):
        """
        Regression: 40×30 board at 800×600 with panel_right=True must yield 7.

        avail_w = 800 - BOARD_OX(252) - PANEL_W(240) - PAD(12) = 296
        avail_h = 600 - BOARD_OY(60) - HEADER_H(48)            = 492
        min_fit_tile = min(296//40, 492//30) = min(7, 16)       = 7
        """
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        assert _min_fit_tile(r) == 7


# ---------------------------------------------------------------------------
# Zoom-out floor behaviour
# ---------------------------------------------------------------------------

class TestZoomOutFloor:
    """
    Behavioural tests: what the tile size does across multiple scroll-out events.
    """

    def test_scroll_down_can_go_below_old_static_min(self, renderer_panel_large):
        """
        The new dynamic floor allows tile sizes below the old MIN_TILE_SIZE=10.
        This is the primary regression test for the feature.
        """
        from gameworks.renderer import MIN_TILE_SIZE
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        floor = _min_fit_tile(r)

        if floor >= MIN_TILE_SIZE:
            pytest.skip("Board/viewport combo does not exercise sub-MIN_TILE_SIZE floor")

        _scroll_out_fully(r)
        assert r._tile < MIN_TILE_SIZE, (
            f"tile={r._tile} should be below old static floor "
            f"MIN_TILE_SIZE={MIN_TILE_SIZE} (dynamic floor={floor})"
        )

    def test_scroll_down_bottoms_out_exactly_at_min_fit_tile(self, renderer_panel_large):
        """After exhaustive scroll-out the tile must equal the dynamic floor."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        floor = _min_fit_tile(r)
        _scroll_out_fully(r)
        assert r._tile == floor, (
            f"Expected tile to settle at floor={floor}, got {r._tile}"
        )

    def test_scroll_down_cannot_go_below_floor(self, renderer_panel_large):
        """Further scroll events beyond the floor must not reduce the tile."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        _scroll_out_fully(r)
        tile_at_floor = r._tile

        ev = _scroll_event(y=-1)
        for _ in range(20):
            r.handle_event(ev)

        assert r._tile == tile_at_floor

    def test_floor_adapts_to_viewport_size(self, renderer_panel_large):
        """A larger viewport must produce a higher (or equal) zoom-out floor."""
        r, _ = renderer_panel_large

        r._tile = 32
        r._win_size = (600, 400)
        _scroll_out_fully(r)
        tile_small = r._tile

        r._tile = 32
        r._win_size = (1400, 900)
        _scroll_out_fully(r)
        tile_large = r._tile

        assert tile_large >= tile_small

    def test_tile_is_integer_after_zoom_out(self, renderer_panel_large):
        """Tile size must remain a Python int throughout zoom-out."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        ev = _scroll_event(y=-1)
        for _ in range(30):
            r.handle_event(ev)
            assert isinstance(r._tile, int), f"_tile became {type(r._tile)}"

    def test_pan_remains_integer_after_zoom_out(self, renderer_panel_large):
        """Pan values must stay int after zoom (float pan breaks range() in _draw_board)."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        _scroll_out_fully(r)
        assert isinstance(r._pan_x, int)
        assert isinstance(r._pan_y, int)


# ---------------------------------------------------------------------------
# Board fits in viewport after maximum zoom-out
# ---------------------------------------------------------------------------

class TestBoardFitsViewport:
    """
    Functional tests: after the user scrolls all the way out, the entire board
    must fit within the available viewport area.
    """

    def test_board_width_fits_after_full_zoom_out(self, renderer_panel_large):
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        _scroll_out_fully(r)

        avail_w = r._win_size[0] - r.BOARD_OX
        if r._panel_right:
            avail_w -= r.PANEL_W + r.PAD
        board_px_w = r.board.width * r._tile

        assert board_px_w <= avail_w, (
            f"Board width {board_px_w}px exceeds available {avail_w}px at tile={r._tile}"
        )

    def test_board_height_fits_after_full_zoom_out(self, renderer_panel_large):
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        _scroll_out_fully(r)

        avail_h = r._win_size[1] - r.BOARD_OY
        board_px_h = r.board.height * r._tile

        assert board_px_h <= avail_h, (
            f"Board height {board_px_h}px exceeds available {avail_h}px at tile={r._tile}"
        )

    def test_both_dimensions_fit_simultaneously(self, renderer_panel_large):
        """Width AND height must both fit — not just the dominant axis."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        _scroll_out_fully(r)

        avail_w = r._win_size[0] - r.BOARD_OX
        if r._panel_right:
            avail_w -= r.PANEL_W + r.PAD
        avail_h = r._win_size[1] - r.BOARD_OY

        assert r.board.width * r._tile <= avail_w
        assert r.board.height * r._tile <= avail_h

    def test_floor_math_guarantees_fit(self, renderer_panel_large):
        """
        Algebraic guarantee: if tile == min_fit_tile, the board fits by definition.

        min_fit_tile = min(avail_w // W, avail_h // H)
        ⟹  W * min_fit_tile ≤ W * (avail_w // W) ≤ avail_w   ✓
        ⟹  H * min_fit_tile ≤ H * (avail_h // H) ≤ avail_h   ✓
        """
        r, _ = renderer_panel_large
        WIN = (800, 600)
        r._win_size = WIN
        floor = _min_fit_tile(r)

        avail_w = WIN[0] - r.BOARD_OX
        if r._panel_right:
            avail_w -= r.PANEL_W + r.PAD
        avail_h = WIN[1] - r.BOARD_OY

        assert r.board.width * floor <= avail_w
        assert r.board.height * floor <= avail_h


# ---------------------------------------------------------------------------
# Zoom-in ceiling (unchanged by this feature — regression guard)
# ---------------------------------------------------------------------------

class TestZoomInCeiling:

    def test_scroll_up_capped_at_base_tile(self, renderer_easy):
        from gameworks.renderer import BASE_TILE
        r, _ = renderer_easy
        r._tile = BASE_TILE
        r.handle_event(_scroll_event(y=1))
        assert r._tile == BASE_TILE

    def test_scroll_up_from_below_increases_tile(self, renderer_easy):
        r, _ = renderer_easy
        r._tile = 16
        r.handle_event(_scroll_event(y=1))
        assert r._tile > 16

    def test_scroll_up_never_exceeds_base_tile(self, renderer_easy):
        from gameworks.renderer import BASE_TILE
        r, _ = renderer_easy
        r._tile = BASE_TILE - 4
        for _ in range(30):
            r.handle_event(_scroll_event(y=1))
        assert r._tile <= BASE_TILE

    def test_zoom_in_then_out_returns_to_floor(self, renderer_panel_large):
        """Zoom all the way out, in, then out again — floor must be consistent."""
        from gameworks.renderer import BASE_TILE
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        floor = _min_fit_tile(r)

        _scroll_out_fully(r)
        assert r._tile == floor

        # Zoom back in
        for _ in range(30):
            r.handle_event(_scroll_event(y=1))
        assert r._tile == BASE_TILE

        # Zoom out again — must settle at the same floor
        _scroll_out_fully(r)
        assert r._tile == floor


# ---------------------------------------------------------------------------
# Cache invalidation after zoom (regression: must stay consistent with feature)
# ---------------------------------------------------------------------------

class TestZoomCacheInvalidation:

    def test_board_rect_cache_cleared_after_zoom_out(self, renderer_panel_large):
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        r._tile = 20          # above the floor of 7
        _ = r._board_rect()   # populate cache
        assert r._cached_board_rect is not None

        r.handle_event(_scroll_event(y=-1))
        assert r._cached_board_rect is None

    def test_board_rect_cache_cleared_after_zoom_in(self, renderer_easy):
        r, _ = renderer_easy
        r._tile = 16
        _ = r._board_rect()
        assert r._cached_board_rect is not None

        r.handle_event(_scroll_event(y=1))
        assert r._cached_board_rect is None

    def test_num_surfs_tile_tracks_tile_after_zoom(self, renderer_panel_large):
        """_num_tile must match _tile after every zoom event."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        ev = _scroll_event(y=-1)
        for _ in range(20):
            r.handle_event(ev)
            assert r._num_tile == r._tile, (
                f"_num_tile={r._num_tile} out of sync with _tile={r._tile}"
            )


# ---------------------------------------------------------------------------
# Hardening: negative / degenerate viewport guards
# ---------------------------------------------------------------------------

class TestHardeningGuards:
    """
    Tests for edge cases identified during hardening analysis:
      H1 — negative avail values on very narrow/short windows
      H2 — right-margin PAD included for non-panel-right boards
      H3 — upward snap when _tile is already below the floor
    """

    def test_h1_tiny_window_does_not_crash(self, renderer_panel_large):
        """Scrolling out on a window smaller than BOARD_OX must not crash."""
        r, _ = renderer_panel_large
        # Force a window so narrow that avail_w would be negative without the guard
        r._win_size = (50, 50)
        ev = _scroll_event(y=-1)
        for _ in range(10):
            r.handle_event(ev)   # must not raise
        assert r._tile >= 1

    def test_h1_floor_is_one_on_degenerate_window(self, renderer_panel_large):
        """min_fit_tile must be 1 (not 0 or negative) when avail clamps to 0."""
        r, _ = renderer_panel_large
        r._win_size = (10, 10)   # smaller than any offset constant
        assert _min_fit_tile(r) == 1

    def test_h2_non_panel_right_includes_right_pad_in_avail_w(self):
        """For non-panel-right boards, avail_w = win_w - BOARD_OX - PAD (right margin)."""
        from gameworks.engine import GameEngine
        from gameworks.renderer import Renderer
        eng = GameEngine(mode="random", width=100, height=30, mines=100, seed=42)
        eng.start()
        r = Renderer(eng)
        assert not r._panel_right
        r._win_size = (1000, 600)
        # avail_w must subtract PAD on the right; avail_w = 1000 - 12 - 12 = 976
        avail_w_expected = max(0, 1000 - r.BOARD_OX - r.PAD)
        avail_h_expected = max(0, 600 - r.BOARD_OY - r.HEADER_H)
        expected_floor = max(1, min(avail_w_expected // r.board.width,
                                    avail_h_expected // r.board.height))
        assert _min_fit_tile(r, win_size=(1000, 600)) == expected_floor
        # Also confirm the right-margin PAD actually reduces avail_w vs no-PAD
        avail_w_no_right_pad = 1000 - r.BOARD_OX
        assert avail_w_expected < avail_w_no_right_pad

    def test_h3_scroll_down_snaps_up_when_tile_below_floor(self, renderer_panel_large):
        """
        If _tile is somehow below min_fit_tile (e.g. window was enlarged),
        scroll-down must snap tile UP to the floor, not decrease it further.
        """
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        floor = _min_fit_tile(r)   # 7

        # Manually put tile below the floor (simulates enlarged window scenario)
        r._tile = floor - 2        # e.g. 5
        assert r._tile < floor

        ev = _scroll_event(y=-1)
        r.handle_event(ev)

        # After the snap, tile must equal the floor (not go further down)
        assert r._tile == floor, (
            f"Expected upward snap to floor={floor}, got {r._tile}"
        )

    def test_h3_no_further_decrease_after_upward_snap(self, renderer_panel_large):
        """After a snap-up event, subsequent scroll-out events must stay at floor."""
        r, _ = renderer_panel_large
        r._win_size = (800, 600)
        floor = _min_fit_tile(r)
        r._tile = floor - 2   # below floor

        ev = _scroll_event(y=-1)
        for _ in range(10):
            r.handle_event(ev)
        assert r._tile == floor
