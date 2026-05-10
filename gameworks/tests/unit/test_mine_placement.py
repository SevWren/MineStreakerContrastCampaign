"""
gameworks/tests/unit/test_mine_placement.py

Tests for gameworks.engine.place_random_mines().

Covers:
- Mine count: exactly `count` mines placed
- Safe-zone exclusion: click cell and its 3×3 neighbourhood are mine-free
- Seed reproducibility: same seed produces same mine set
- Edge cases: zero mines, mines = all cells (minus safe zone), small board
"""

from __future__ import annotations

import pytest

from gameworks.engine import place_random_mines


class TestMineCount:

    def test_exact_count_placed(self):
        mines = place_random_mines(9, 9, 10, seed=42)
        assert len(mines) == 10

    def test_zero_mines(self):
        mines = place_random_mines(9, 9, 0, seed=1)
        assert len(mines) == 0

    def test_mines_within_board_bounds(self):
        w, h = 9, 9
        mines = place_random_mines(w, h, 10, seed=42)
        for x, y in mines:
            assert 0 <= x < w
            assert 0 <= y < h

    def test_no_duplicate_positions(self):
        mines = place_random_mines(16, 16, 40, seed=42)
        assert len(mines) == len(set(mines))


class TestSafeZone:

    def _safe_neighbours(self, sx: int, sy: int, w: int, h: int):
        """Return all cells in the 3×3 neighbourhood of (sx, sy) within bounds."""
        cells = set()
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                nx, ny = sx + dx, sy + dy
                if 0 <= nx < w and 0 <= ny < h:
                    cells.add((nx, ny))
        return cells

    def test_safe_cell_is_mine_free(self):
        mines = place_random_mines(9, 9, 10, safe_x=4, safe_y=4, seed=42)
        assert (4, 4) not in mines

    def test_safe_neighbourhood_is_mine_free(self):
        w, h = 9, 9
        sx, sy = 4, 4
        mines = place_random_mines(w, h, 10, safe_x=sx, safe_y=sy, seed=42)
        safe = self._safe_neighbours(sx, sy, w, h)
        for pos in safe:
            assert pos not in mines, f"Mine placed inside safe zone at {pos}"

    def test_safe_zone_at_corner(self):
        """Safe zone at board corner must respect out-of-bounds clipping."""
        mines = place_random_mines(9, 9, 10, safe_x=0, safe_y=0, seed=42)
        safe = self._safe_neighbours(0, 0, 9, 9)
        for pos in safe:
            assert pos not in mines

    def test_no_safe_zone_when_coords_invalid(self):
        """safe_x=-1 means no safe zone — all cells are candidates."""
        mines = place_random_mines(5, 5, 1, safe_x=-1, safe_y=-1, seed=1)
        assert len(mines) == 1


class TestReproducibility:

    def test_same_seed_produces_same_result(self):
        a = place_random_mines(9, 9, 10, seed=99)
        b = place_random_mines(9, 9, 10, seed=99)
        assert a == b

    def test_different_seeds_produce_different_results(self):
        a = place_random_mines(9, 9, 10, seed=1)
        b = place_random_mines(9, 9, 10, seed=2)
        # Not guaranteed to differ, but overwhelmingly likely with 10 mines on 9×9
        assert a != b

    def test_none_seed_is_non_deterministic(self):
        """Passing seed=None should produce non-deterministic results across calls
        (this test is probabilistic but should virtually never fail)."""
        results = [frozenset(place_random_mines(9, 9, 10, seed=None)) for _ in range(5)]
        # At least two of the 5 results should differ
        assert len(set(results)) > 1


class TestEdgeCases:

    def test_small_board_2x2_one_mine(self):
        mines = place_random_mines(2, 2, 1, seed=1)
        assert len(mines) == 1

    def test_high_density_no_duplicates(self):
        mines = place_random_mines(9, 9, 70, seed=42)
        assert len(mines) == 70

    def test_mines_returned_as_set_of_tuples(self):
        mines = place_random_mines(5, 5, 3, seed=42)
        assert isinstance(mines, set)
        for item in mines:
            assert isinstance(item, tuple)
            assert len(item) == 2
