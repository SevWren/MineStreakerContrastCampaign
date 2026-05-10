"""
gameworks/tests/unit/test_board.py

Unit tests for gameworks.engine.Board.

Covers:
- Construction: mine placement, neighbour pre-computation, property values
- reveal():  safe reveal, flood-fill, mine hit (no game-over), already-revealed no-op
- toggle_flag(): hidden→flag→question→hidden cycle, win-on-flag
- chord(): flag-count match triggers reveal, mismatch is a no-op
- snapshot(): CellState fields match board arrays
- Win detection: safe cells only, flags optional
- Boundary conditions: corners, edges, zero-mine board
"""

from __future__ import annotations

import pytest

from gameworks.engine import Board, CellState, place_random_mines


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def board(w: int = 9, h: int = 9, mine_set: set | None = None, seed: int = 42) -> Board:
    if mine_set is not None:
        return Board(w, h, mine_set)
    return Board(w, h, place_random_mines(w, h, 10, seed=seed))


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestBoardConstruction:

    def test_total_mines_matches_input(self):
        mines = {(0, 0), (1, 1), (2, 2)}
        b = Board(5, 5, mines)
        assert b.total_mines == 3

    def test_total_safe_is_area_minus_mines(self):
        mines = {(0, 0)}
        b = Board(4, 4, mines)
        assert b.total_safe == 15

    def test_width_and_height_properties(self):
        b = Board(7, 11, set())
        assert b.width == 7
        assert b.height == 11

    def test_mine_array_correct_positions(self):
        mines = {(0, 0), (4, 4)}
        b = Board(5, 5, mines)
        assert b._mine[0, 0]
        assert b._mine[4, 4]
        assert not b._mine[0, 1]

    def test_neighbour_count_adjacent_to_one_mine(self):
        """Cell directly beside one mine must have neighbour count 1."""
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        assert int(b._neighbours[0, 1]) == 1   # right of mine
        assert int(b._neighbours[1, 0]) == 1   # below mine
        assert int(b._neighbours[1, 1]) == 1   # diagonal

    def test_neighbour_count_far_from_all_mines(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        assert int(b._neighbours[4, 4]) == 0

    def test_neighbour_count_surrounded_by_mines(self):
        """Centre cell surrounded by 8 mines must have count 8."""
        mines = {(0, 0), (1, 0), (2, 0),
                 (0, 1),          (2, 1),
                 (0, 2), (1, 2), (2, 2)}
        b = Board(3, 3, mines)
        assert int(b._neighbours[1, 1]) == 8

    def test_zero_mine_board_all_neighbours_zero(self):
        b = Board(5, 5, set())
        assert (b._neighbours == 0).all()

    def test_initial_state_is_playing(self):
        b = board()
        assert b._state == "playing"

    def test_initial_revealed_count_zero(self):
        b = board()
        assert b.revealed_count == 0

    def test_initial_flags_placed_zero(self):
        b = board()
        assert b.flags_placed == 0


# ---------------------------------------------------------------------------
# reveal()
# ---------------------------------------------------------------------------

class TestReveal:

    def test_safe_reveal_returns_false_hit(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        hit, revealed = b.reveal(4, 4)
        assert not hit

    def test_safe_reveal_includes_clicked_cell(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        _, revealed = b.reveal(4, 4)
        assert (4, 4) in revealed

    def test_mine_reveal_returns_true_hit(self):
        mines = {(3, 3)}
        b = Board(9, 9, mines)
        hit, _ = b.reveal(3, 3)
        assert hit

    def test_mine_hit_does_not_end_game(self):
        """Mine hit is a penalty only — state stays 'playing'."""
        mines = {(3, 3)}
        b = Board(9, 9, mines)
        b.reveal(3, 3)
        assert b._state == "playing"

    def test_mine_cell_marked_revealed_after_hit(self):
        mines = {(2, 2)}
        b = Board(5, 5, mines)
        b.reveal(2, 2)
        assert b._revealed[2, 2]

    def test_already_revealed_cell_is_noop(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        b.reveal(4, 4)
        hit, revealed = b.reveal(4, 4)
        assert not hit
        assert revealed == []

    def test_flagged_cell_cannot_be_revealed(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        b.toggle_flag(0, 0)
        hit, revealed = b.reveal(0, 0)
        assert not hit
        assert revealed == []

    def test_flood_fill_expands_from_zero_cell(self):
        """Clicking a zero-count cell should reveal more than just itself."""
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        _, revealed = b.reveal(4, 4)
        assert len(revealed) > 1

    def test_flood_fill_does_not_cross_mine(self):
        """Flood-fill must not reveal mine cells."""
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        _, revealed = b.reveal(4, 4)
        assert (0, 0) not in revealed

    def test_reveal_numbered_cell_reveals_only_itself(self):
        """A numbered cell (>0 neighbours) should reveal only itself, not flood-fill."""
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        # (1, 0) has neighbour count 1 — should not flood-fill
        _, revealed = b.reveal(1, 0)
        assert revealed == [(1, 0)]

    def test_safe_cells_count_tracks_reveals(self):
        mines = {(0, 0)}
        b = Board(3, 3, mines)
        assert b.safe_revealed_count == 0
        b.reveal(2, 2)
        assert b.safe_revealed_count > 0

    def test_win_when_all_safe_cells_revealed(self):
        mines = {(0, 0)}
        b = Board(2, 2, mines)
        b.reveal(1, 0)
        b.reveal(0, 1)
        b.reveal(1, 1)
        assert b._state == "won"

    def test_win_does_not_require_flagging_mines(self):
        """Win is purely safe-cell count — no flags needed."""
        mines = {(0, 0)}
        b = Board(2, 2, mines)
        b.reveal(1, 0)
        b.reveal(0, 1)
        b.reveal(1, 1)
        assert b.is_won


# ---------------------------------------------------------------------------
# toggle_flag()
# ---------------------------------------------------------------------------

class TestToggleFlag:

    def test_hidden_to_flag(self):
        b = board()
        result = b.toggle_flag(5, 5)
        assert result == "flag"
        assert b._flagged[5, 5]

    def test_flag_to_question(self):
        b = board()
        b.toggle_flag(5, 5)
        result = b.toggle_flag(5, 5)
        assert result == "question"
        assert b._questioned[5, 5]
        assert not b._flagged[5, 5]

    def test_question_to_hidden(self):
        b = board()
        b.toggle_flag(5, 5)
        b.toggle_flag(5, 5)
        result = b.toggle_flag(5, 5)
        assert result == "hidden"
        assert not b._flagged[5, 5]
        assert not b._questioned[5, 5]

    def test_revealed_cell_toggle_is_noop(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        b.reveal(4, 4)
        result = b.toggle_flag(4, 4)
        assert result == "hidden"
        assert not b._flagged[4, 4]

    def test_flags_placed_counter_increments(self):
        b = board()
        b.toggle_flag(3, 3)
        assert b.flags_placed == 1

    def test_flags_placed_counter_decrements_on_cycle(self):
        b = board()
        b.toggle_flag(3, 3)   # → flag
        b.toggle_flag(3, 3)   # → question
        assert b.flags_placed == 0

    def test_mines_remaining_decrements_with_flag(self):
        mines = {(0, 0), (1, 1)}
        b = Board(5, 5, mines)
        before = b.mines_remaining
        b.toggle_flag(0, 0)
        assert b.mines_remaining == before - 1

    def test_correct_flags_count(self):
        mines = {(0, 0), (1, 1)}
        b = Board(5, 5, mines)
        b.toggle_flag(0, 0)   # correct
        b.toggle_flag(2, 2)   # wrong
        assert b.correct_flags == 1

    def test_wrong_flag_positions(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        b.toggle_flag(3, 3)   # wrong flag
        wrongs = b.wrong_flag_positions()
        assert (3, 3) in wrongs
        assert (0, 0) not in wrongs


# ---------------------------------------------------------------------------
# chord()
# ---------------------------------------------------------------------------

class TestChord:

    def test_chord_requires_revealed_cell(self):
        """Chord on an unrevealed cell is a no-op."""
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        hit, revealed = b.chord(4, 4)
        assert not hit
        assert revealed == []

    def test_chord_on_zero_count_cell_is_noop(self):
        """Chord on a revealed cell with 0 neighbours is a no-op."""
        mines = {(0, 0)}
        b = Board(9, 9, mines)
        b.reveal(8, 8)   # far corner, should be 0-count and flood-filled
        hit, revealed = b.chord(8, 8)
        assert not hit
        assert revealed == []

    def test_chord_fires_when_flag_count_matches(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        b.reveal(1, 1)          # count = 1 (adjacent to mine at 0,0)
        b.toggle_flag(0, 0)     # flag the mine
        hit, revealed = b.chord(1, 1)
        assert not hit
        assert len(revealed) > 0

    def test_chord_noop_when_flag_count_does_not_match(self):
        mines = {(0, 0), (2, 0)}
        b = Board(5, 5, mines)
        b.reveal(1, 1)          # count = 2
        b.toggle_flag(0, 0)     # only one flag — mismatch
        hit, revealed = b.chord(1, 1)
        assert revealed == []


# ---------------------------------------------------------------------------
# snapshot()
# ---------------------------------------------------------------------------

class TestSnapshot:

    def test_snapshot_mine_field(self):
        mines = {(1, 1)}
        b = Board(5, 5, mines)
        cs = b.snapshot(1, 1)
        assert isinstance(cs, CellState)
        assert cs.is_mine

    def test_snapshot_flagged_field(self):
        mines = {(1, 1)}
        b = Board(5, 5, mines)
        b.toggle_flag(1, 1)
        cs = b.snapshot(1, 1)
        assert cs.is_flagged

    def test_snapshot_questioned_field(self):
        b = board()
        b.toggle_flag(3, 3)
        b.toggle_flag(3, 3)
        cs = b.snapshot(3, 3)
        assert cs.is_questioned

    def test_snapshot_revealed_field(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        b.reveal(4, 4)
        cs = b.snapshot(4, 4)
        assert cs.is_revealed

    def test_snapshot_neighbour_mines_count(self):
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        cs = b.snapshot(1, 0)
        assert cs.neighbour_mines == 1

    def test_snapshot_is_frozen(self):
        b = board()
        cs = b.snapshot(4, 4)
        with pytest.raises((AttributeError, TypeError)):
            cs.is_mine = True   # type: ignore[misc]


# ---------------------------------------------------------------------------
# Board properties
# ---------------------------------------------------------------------------

class TestBoardProperties:

    def test_all_mine_positions_returns_complete_list(self):
        mines = {(0, 0), (1, 1), (4, 4)}
        b = Board(5, 5, mines)
        found = set(b.all_mine_positions())
        assert found == mines

    def test_game_over_false_while_playing(self):
        b = board()
        assert not b.game_over

    def test_game_over_true_after_win(self):
        """game_over must return True once the board reaches 'won' state."""
        mines = {(0, 0)}
        b = Board(2, 2, mines)
        b.reveal(1, 0)
        b.reveal(0, 1)
        b.reveal(1, 1)
        assert b._state == "won"
        assert b.game_over

    def test_is_lost_initially_false(self):
        """is_lost must always be False — there is no lose state."""
        b = board()
        assert not b.is_lost

    def test_safe_revealed_count_excludes_mine_hit(self):
        """Clicking a mine cell increments revealed_count but NOT safe_revealed_count."""
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        safe_before = b.safe_revealed_count
        b.reveal(0, 0)   # mine hit — should NOT increment safe_revealed_count
        assert b.safe_revealed_count == safe_before

    def test_questioned_count_tracks_cycle(self):
        b = board()
        b.toggle_flag(2, 2)   # → flag
        b.toggle_flag(2, 2)   # → question
        assert b.questioned_count == 1
        b.toggle_flag(2, 2)   # → hidden
        assert b.questioned_count == 0


# ---------------------------------------------------------------------------
# Counter correctness — Phase 1 regression guards
# ---------------------------------------------------------------------------

class TestDirtyIntCounters:
    """
    Regression tests for Phase 1 dirty-int counters (P-06, P-07, P-08, P-23).
    These tests validate that counter values always match the underlying numpy
    array state after any sequence of actions.
    """

    def test_counters_match_array_state_after_flood_fill(self):
        """After flood-fill, all counters must exactly match their array sum()."""
        mines = {(0, 0)}
        b = Board(5, 5, mines)
        b.reveal(4, 4)   # flood-fill from far corner

        # Validate all four counters
        assert b._n_revealed == int(b._revealed.sum())
        assert b._n_safe_revealed == int((b._revealed & ~b._mine).sum())
        assert b._n_flags == int(b._flagged.sum())
        assert b._n_questioned == int(b._questioned.sum())

    def test_counters_match_after_flag_cycle(self):
        """Flag → question → hidden cycle must keep counters in sync."""
        b = board()
        b.toggle_flag(3, 3)   # → flag
        assert b._n_flags == int(b._flagged.sum())
        assert b._n_questioned == int(b._questioned.sum())

        b.toggle_flag(3, 3)   # → question
        assert b._n_flags == int(b._flagged.sum())
        assert b._n_questioned == int(b._questioned.sum())

        b.toggle_flag(3, 3)   # → hidden
        assert b._n_flags == int(b._flagged.sum())
        assert b._n_questioned == int(b._questioned.sum())

    def test_counters_match_after_mine_hit(self):
        """Mine hit increments revealed_count but not safe_revealed_count."""
        mines = {(2, 2)}
        b = Board(5, 5, mines)
        b.reveal(2, 2)   # mine hit

        assert b._n_revealed == int(b._revealed.sum())
        assert b._n_safe_revealed == int((b._revealed & ~b._mine).sum())
        assert b._n_safe_revealed == 0   # mine hit does not count as safe reveal

    def test_counters_match_after_mixed_actions(self):
        """Complex action sequence: reveal + flag + chord."""
        mines = {(0, 0)}
        b = Board(5, 5, mines)

        b.reveal(4, 4)      # flood-fill
        b.toggle_flag(0, 0) # flag
        b.toggle_flag(1, 1) # flag
        b.toggle_flag(1, 1) # → question

        assert b._n_revealed == int(b._revealed.sum())
        assert b._n_safe_revealed == int((b._revealed & ~b._mine).sum())
        assert b._n_flags == int(b._flagged.sum())
        assert b._n_questioned == int(b._questioned.sum())

    def test_dev_solve_resyncs_all_counters(self):
        """dev_solve_board() bulk ops must resync counters correctly."""
        from gameworks.engine import GameEngine

        mines = {(0, 0), (1, 1)}
        b = Board(5, 5, mines)
        eng = GameEngine(mode="random", width=5, height=5, mines=2, seed=42)
        eng.board = b

        # Partially reveal, flag, question some cells before dev_solve
        b.reveal(4, 4)
        b.toggle_flag(3, 3)
        b.toggle_flag(2, 2)
        b.toggle_flag(2, 2)  # → question

        eng.dev_solve_board()

        # After dev_solve, all counters must match the numpy arrays
        assert b._n_revealed == int(b._revealed.sum())
        assert b._n_safe_revealed == b.total_safe
        assert b._n_flags == b.total_mines
        assert b._n_questioned == 0

        # Validate against arrays
        assert b._n_flags == int(b._flagged.sum())
        assert b._n_questioned == int(b._questioned.sum())

    def test_flags_placed_counter_increments_on_flag(self):
        """flags_placed (_n_flags) must increment by 1 when hidden cell → flag."""
        b = board()
        initial = b.flags_placed
        b.toggle_flag(3, 3)   # hidden → flag
        assert b.flags_placed == initial + 1
        assert b.flags_placed == int(b._flagged.sum())

    def test_flags_placed_counter_decrements_on_question(self):
        """flags_placed (_n_flags) must decrement by 1 when flag → question."""
        b = board()
        b.toggle_flag(3, 3)   # hidden → flag
        flagged = b.flags_placed
        b.toggle_flag(3, 3)   # flag → question
        assert b.flags_placed == flagged - 1
        assert b.flags_placed == int(b._flagged.sum())

    def test_flags_placed_counter_decrements_on_hidden(self):
        """flags_placed (_n_flags) must remain 0 when question → hidden."""
        b = board()
        b.toggle_flag(3, 3)   # hidden → flag
        b.toggle_flag(3, 3)   # flag → question
        b.toggle_flag(3, 3)   # question → hidden
        assert b.flags_placed == 0
        assert b.flags_placed == int(b._flagged.sum())

    def test_questioned_count_increments_and_decrements(self):
        """questioned count (_n_questioned) must increment on flag→question and decrement on question→hidden."""
        b = board()
        assert b._n_questioned == 0

        b.toggle_flag(3, 3)   # hidden → flag
        assert b._n_questioned == 0

        b.toggle_flag(3, 3)   # flag → question
        assert b._n_questioned == 1
        assert b._n_questioned == int(b._questioned.sum())

        b.toggle_flag(3, 3)   # question → hidden
        assert b._n_questioned == 0
        assert b._n_questioned == int(b._questioned.sum())

    def test_safe_revealed_count_increments_per_safe_cell(self):
        """safe_revealed_count (_n_safe_revealed) must increment by 1 per safe cell revealed, not count mine hits."""
        mines = {(2, 2)}
        b = Board(5, 5, mines)

        # Reveal one safe cell with neighbors (won't flood-fill)
        b.reveal(2, 1)   # cell adjacent to mine at (2,2)
        assert b._n_safe_revealed == 1
        assert b._n_safe_revealed == int((b._revealed & ~b._mine).sum())

        # Hit a mine — safe_revealed should NOT increment
        b.reveal(2, 2)   # mine hit
        assert b._n_safe_revealed == 1   # still 1, mine hit doesn't count
        assert b._n_safe_revealed == int((b._revealed & ~b._mine).sum())

        # Reveal another safe cell
        b.reveal(1, 1)   # another cell adjacent to mine
        assert b._n_safe_revealed == 2
        assert b._n_safe_revealed == int((b._revealed & ~b._mine).sum())
