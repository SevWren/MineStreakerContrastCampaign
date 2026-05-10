"""
gameworks/tests/fixtures/boards.py

Board factory helpers for the gameworks test suite.

Usage:
    from gameworks.tests.fixtures.boards import BoardFactory

    b = BoardFactory.minimal()          # 3×3, one mine at (0,0)
    b = BoardFactory.easy()             # 9×9, 10 mines, seed=42
    b = BoardFactory.won()              # 2×2, one mine, all safe cells revealed
    b = BoardFactory.all_flagged()      # 3×3, all mines flagged
    b = BoardFactory.fully_revealed()   # 5×5, zero mines, all cells revealed
"""

from __future__ import annotations

from gameworks.engine import Board, place_random_mines


class BoardFactory:

    @staticmethod
    def minimal(seed: int = 42) -> Board:
        """3×3 board with one mine at (0, 0). Smallest useful test surface."""
        return Board(3, 3, {(0, 0)})

    @staticmethod
    def easy(seed: int = 42) -> Board:
        """9×9 board with 10 mines. Mirrors Easy difficulty preset."""
        mines = place_random_mines(9, 9, 10, seed=seed)
        return Board(9, 9, mines)

    @staticmethod
    def medium(seed: int = 42) -> Board:
        """16×16 board with 40 mines. Mirrors Medium difficulty preset."""
        mines = place_random_mines(16, 16, 40, seed=seed)
        return Board(16, 16, mines)

    @staticmethod
    def hard(seed: int = 42) -> Board:
        """30×16 board with 99 mines. Mirrors Hard difficulty preset."""
        mines = place_random_mines(30, 16, 99, seed=seed)
        return Board(30, 16, mines)

    @staticmethod
    def no_mines(w: int = 5, h: int = 5) -> Board:
        """Board with zero mines. All cells are safe; flood-fill reveals everything."""
        return Board(w, h, set())

    @staticmethod
    def single_mine(x: int = 0, y: int = 0, w: int = 5, h: int = 5) -> Board:
        """Board with exactly one mine at (x, y)."""
        return Board(w, h, {(x, y)})

    @staticmethod
    def won() -> Board:
        """
        2×2 board with one mine. All safe cells are pre-revealed so state == 'won'.
        Use for testing victory modal and WinAnimation triggers.
        """
        b = Board(2, 2, {(0, 0)})
        b.reveal(1, 0)
        b.reveal(0, 1)
        b.reveal(1, 1)
        return b

    @staticmethod
    def all_mines_flagged(seed: int = 42) -> Board:
        """
        5×5 board where every mine has a correct flag.
        Use for testing correct_flags count and WinAnimation ordering.
        """
        mines = place_random_mines(5, 5, 5, seed=seed)
        b = Board(5, 5, mines)
        for x, y in mines:
            b._flagged[y, x] = True
        return b

    @staticmethod
    def fully_revealed(w: int = 5, h: int = 5) -> Board:
        """
        Board with no mines, all cells revealed.
        Use for testing rendering of a fully-open board.
        """
        b = Board(w, h, set())
        for y in range(h):
            for x in range(w):
                b._revealed[y, x] = True
        return b

    @staticmethod
    def with_wrong_flags(seed: int = 42) -> Board:
        """
        9×9 board where 3 safe cells are incorrectly flagged.
        Use for testing wrong_flag_positions() and WRONG_FLAG_PENALTY.
        """
        mines = place_random_mines(9, 9, 10, seed=seed)
        b = Board(9, 9, mines)
        # Flag 3 cells that are definitely not mines
        safe_cells = [(x, y) for x in range(9) for y in range(9)
                      if (x, y) not in mines][:3]
        for x, y in safe_cells:
            b._flagged[y, x] = True
        return b
