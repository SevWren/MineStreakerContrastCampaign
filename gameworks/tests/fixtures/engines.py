"""
gameworks/tests/fixtures/engines.py

GameEngine factory helpers for the gameworks test suite.

Usage:
    from gameworks.tests.fixtures.engines import EngineFactory

    eng = EngineFactory.easy()                  # started Easy engine
    eng = EngineFactory.mid_game()              # engine after first click
    eng = EngineFactory.high_streak(n=10)       # engine with streak set to n
    eng = EngineFactory.with_mine_at(x, y)      # board has exactly one mine at (x,y)
"""

from __future__ import annotations

from gameworks.engine import Board, GameEngine, place_random_mines


class EngineFactory:

    @staticmethod
    def easy(seed: int = 42) -> GameEngine:
        """Started Easy engine (9×9, 10 mines)."""
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=seed)
        eng.start()
        return eng

    @staticmethod
    def medium(seed: int = 42) -> GameEngine:
        """Started Medium engine (16×16, 40 mines)."""
        eng = GameEngine(mode="random", width=16, height=16, mines=40, seed=seed)
        eng.start()
        return eng

    @staticmethod
    def hard(seed: int = 42) -> GameEngine:
        """Started Hard engine (30×16, 99 mines)."""
        eng = GameEngine(mode="random", width=30, height=16, mines=99, seed=seed)
        eng.start()
        return eng

    @staticmethod
    def mid_game(seed: int = 42) -> GameEngine:
        """Easy engine after one left-click at the centre (first click is always safe)."""
        eng = EngineFactory.easy(seed=seed)
        eng.left_click(4, 4)
        return eng

    @staticmethod
    def high_streak(n: int = 15, seed: int = 42) -> GameEngine:
        """Easy engine with streak manually set to n. Use for multiplier tests."""
        eng = EngineFactory.easy(seed=seed)
        eng.streak = n
        return eng

    @staticmethod
    def with_mine_at(x: int, y: int, w: int = 9, h: int = 9) -> GameEngine:
        """
        Engine whose board has exactly one mine at (x, y).
        First-click guard is disabled so left_click(x, y) will hit the mine.
        """
        eng = GameEngine(mode="random", width=w, height=h, mines=1, seed=0)
        eng.board = Board(w, h, {(x, y)})
        eng._first_click = False
        eng.start()
        return eng

    @staticmethod
    def with_score(score: int, seed: int = 42) -> GameEngine:
        """Easy engine with score pre-set. Use for penalty floor tests."""
        eng = EngineFactory.easy(seed=seed)
        eng.score = score
        return eng

    @staticmethod
    def npy(path: str, seed: int = 1) -> GameEngine:
        """Started npy-mode engine loaded from path."""
        eng = GameEngine(mode="npy", npy_path=path, seed=seed)
        eng.start()
        return eng
