"""
gameworks/tests/unit/test_board_edge_cases.py

Edge case and boundary condition tests for Board class.

Tests extreme scenarios, boundary conditions, and error handling:
- Minimum/maximum board dimensions
- Edge/corner cell operations
- Invalid input handling
- Empty/full mine configurations
"""

from __future__ import annotations

import pytest

from gameworks.engine import Board, place_random_mines


class TestBoardBoundaries:
    """Test extreme board dimensions and configurations."""

    def test_single_cell_board_no_mines(self):
        """1×1 board with no mines should be playable."""
        b = Board(1, 1, set())
        assert b.width == 1
        assert b.height == 1
        assert b.total_mines == 0
        assert b.total_safe == 1

    def test_single_cell_board_with_mine(self):
        """1×1 board with one mine."""
        b = Board(1, 1, {(0, 0)})
        assert b.total_mines == 1
        assert b.total_safe == 0
        b.reveal(0, 0)   # mine hit
        assert b._n_revealed == 1
        assert b._n_safe_revealed == 0

    def test_tiny_board_2x2(self):
        """2×2 board should work correctly."""
        mines = {(0, 0)}
        b = Board(2, 2, mines)
        assert b.width == 2
        assert b.height == 2
        assert b.total_safe == 3

    def test_long_thin_board_100x1(self):
        """Very wide, 1-cell-tall board."""
        mines = {(0, 0), (99, 0)}
        b = Board(100, 1, mines)
        assert b.width == 100
        assert b.height == 1
        assert b.total_mines == 2

    def test_tall_thin_board_1x100(self):
        """Very tall, 1-cell-wide board."""
        mines = {(0, 0), (0, 99)}
        b = Board(1, 100, mines)
        assert b.width == 1
        assert b.height == 100
        assert b.total_mines == 2

    def test_all_mines_board(self):
        """Board where every cell is a mine."""
        mines = {(x, y) for x in range(5) for y in range(5)}
        b = Board(5, 5, mines)
        assert b.total_mines == 25
        assert b.total_safe == 0
        assert b._state == "playing"

    def test_no_mines_board(self):
        """Board with zero mines."""
        b = Board(5, 5, set())
        assert b.total_mines == 0
        assert b.total_safe == 25
        # Reveal any cell — should flood-fill entire board and win
        b.reveal(2, 2)
        assert b._n_safe_revealed == 25
        assert b._state == "won"


class TestCornerAndEdgeOperations:
    """Test operations on corner and edge cells."""

    def test_reveal_top_left_corner(self):
        """Top-left corner (0, 0) should handle reveal correctly."""
        mines = {(2, 2)}
        b = Board(5, 5, mines)
        b.reveal(0, 0)
        assert b._revealed[0, 0]

    def test_reveal_top_right_corner(self):
        """Top-right corner should reveal correctly."""
        mines = {(2, 2)}
        b = Board(5, 5, mines)
        b.reveal(4, 0)
        assert b._revealed[0, 4]

    def test_reveal_bottom_left_corner(self):
        """Bottom-left corner should reveal correctly."""
        mines = {(2, 2)}
        b = Board(5, 5, mines)
        b.reveal(0, 4)
        assert b._revealed[4, 0]

    def test_reveal_bottom_right_corner(self):
        """Bottom-right corner should reveal correctly."""
        mines = {(2, 2)}
        b = Board(5, 5, mines)
        b.reveal(4, 4)
        assert b._revealed[4, 4]

    def test_flag_all_corners(self):
        """All four corners can be flagged."""
        b = Board(5, 5, {(2, 2)})
        b.toggle_flag(0, 0)
        b.toggle_flag(4, 0)
        b.toggle_flag(0, 4)
        b.toggle_flag(4, 4)
        assert b._flagged[0, 0]
        assert b._flagged[0, 4]
        assert b._flagged[4, 0]
        assert b._flagged[4, 4]
        assert b.flags_placed == 4

    def test_chord_on_corner_cell(self):
        """Chording a corner cell should work (fewer neighbours)."""
        mines = {(1, 1)}
        b = Board(5, 5, mines)
        # Place flag on mine
        b.toggle_flag(1, 1)
        # Reveal corner cell (0,0) which has 1 neighbour mine
        b.reveal(0, 0)
        # Chord on (0,0) — 1 flag placed, 1 neighbour mine → should reveal safe neighbours
        revealed_before = b._n_safe_revealed
        hit_mine, newly_revealed = b.chord(0, 0)
        # If chord worked, neighbours should be revealed
        assert len(newly_revealed) > 0 or b._n_safe_revealed > revealed_before


class TestNeighbourCountEdgeCases:
    """Test neighbour count calculation at boundaries."""

    def test_corner_cell_max_3_neighbours(self):
        """Corner cell can have at most 3 neighbours."""
        mines = {(0, 1), (1, 0), (1, 1)}
        b = Board(5, 5, mines)
        assert int(b._neighbours[0, 0]) == 3

    def test_edge_cell_max_5_neighbours(self):
        """Edge cell (not corner) can have at most 5 neighbours."""
        mines = {(0, 0), (1, 0), (2, 0), (0, 1), (2, 1)}
        b = Board(5, 5, mines)
        # Cell (1,1) is surrounded by mines on top row
        # It should count all 5 neighbouring mines
        assert int(b._neighbours[1, 1]) == 5

    def test_centre_cell_max_8_neighbours(self):
        """Centre cell can have all 8 neighbours as mines."""
        mines = {(0, 0), (1, 0), (2, 0),
                 (0, 1),          (2, 1),
                 (0, 2), (1, 2), (2, 2)}
        b = Board(5, 5, mines)
        assert int(b._neighbours[1, 1]) == 8


class TestRepeatOperations:
    """Test repeated operations on same cell."""

    def test_reveal_already_revealed_is_noop(self):
        """Revealing an already-revealed cell should be a no-op."""
        b = Board(5, 5, {(0, 0)})
        b.reveal(2, 2)
        revealed_count = b._n_revealed
        # Reveal again
        b.reveal(2, 2)
        assert b._n_revealed == revealed_count   # no change

    def test_flag_cycle_returns_to_hidden(self):
        """Flagging 3 times should cycle back to hidden."""
        b = Board(5, 5, {(0, 0)})
        b.toggle_flag(2, 2)   # hidden → flag
        b.toggle_flag(2, 2)   # flag → question
        b.toggle_flag(2, 2)   # question → hidden
        assert not b._flagged[2, 2]
        assert not b._questioned[2, 2]
        assert not b._revealed[2, 2]

    def test_chord_on_unflagged_mine_is_safe(self):
        """Chording without sufficient flags should be a no-op."""
        mines = {(1, 1)}
        b = Board(5, 5, mines)
        b.reveal(0, 0)   # reveal cell adjacent to mine
        # Chord without flagging mine first
        revealed_before = b._n_revealed
        b.chord(0, 0)
        # Should not reveal anything (flag count != mine count)
        assert b._n_revealed == revealed_before


class TestWinConditionEdgeCases:
    """Test win detection in edge scenarios."""

    def test_win_on_last_safe_cell_revealed(self):
        """Winning by revealing the last safe cell."""
        mines = {(0, 0)}
        b = Board(2, 2, mines)
        b.reveal(1, 0)
        b.reveal(0, 1)
        b.reveal(1, 1)   # last safe cell
        assert b._state == "won"

    def test_win_after_revealing_all_safe_cells(self):
        """Winning by revealing all safe cells (flags optional)."""
        mines = {(0, 0)}
        b = Board(3, 3, mines)
        # Reveal from far corner — triggers flood-fill revealing all 8 safe cells
        b.reveal(2, 2)
        # Game is won once all safe cells revealed (flags not required)
        assert b._state == "won"
        assert b._n_safe_revealed == b.total_safe

    def test_no_win_if_safe_cells_remain(self):
        """Board should not win if safe cells are unrevealed."""
        mines = {(1, 1)}
        b = Board(3, 3, mines)
        # Reveal one safe cell adjacent to mine (won't flood-fill)
        b.reveal(1, 0)
        # Flag the mine
        b.toggle_flag(1, 1)
        # Should not win — other safe cells (0,0), (2,0), (0,2), etc. still hidden
        assert b._state == "playing"
        assert b._n_safe_revealed < b.total_safe

    def test_no_win_on_mine_hit(self):
        """Mine hit should not cause game over or win (just penalty)."""
        mines = {(0, 0)}
        b = Board(3, 3, mines)
        b.reveal(0, 0)   # mine hit
        assert b._state == "playing"   # game continues
        assert b._n_safe_revealed == 0


class TestRandomMinePlacement:
    """Test random mine placement helper."""

    def test_place_random_mines_correct_count(self):
        """place_random_mines should return exactly N mines."""
        mines = place_random_mines(10, 10, 15, seed=42)
        assert len(mines) == 15

    def test_place_random_mines_within_bounds(self):
        """All mine positions should be within board bounds."""
        mines = place_random_mines(10, 10, 15, seed=42)
        for x, y in mines:
            assert 0 <= x < 10
            assert 0 <= y < 10

    def test_place_random_mines_unique_positions(self):
        """No duplicate mine positions."""
        mines = place_random_mines(10, 10, 15, seed=42)
        assert len(mines) == len(set(mines))

    def test_place_random_mines_deterministic_with_seed(self):
        """Same seed should produce same mine positions."""
        mines1 = place_random_mines(10, 10, 15, seed=42)
        mines2 = place_random_mines(10, 10, 15, seed=42)
        assert mines1 == mines2

    def test_place_random_mines_different_with_different_seed(self):
        """Different seeds should (likely) produce different positions."""
        mines1 = place_random_mines(10, 10, 15, seed=42)
        mines2 = place_random_mines(10, 10, 15, seed=99)
        assert mines1 != mines2

    @pytest.mark.parametrize("count", [0, 1, 50, 99])
    def test_place_random_mines_various_counts(self, count):
        """place_random_mines should handle various mine counts."""
        mines = place_random_mines(10, 10, count, seed=42)
        assert len(mines) == count

    def test_place_random_mines_max_density(self):
        """100% mine density (all cells are mines) should work."""
        mines = place_random_mines(5, 5, 25, seed=42)
        assert len(mines) == 25
