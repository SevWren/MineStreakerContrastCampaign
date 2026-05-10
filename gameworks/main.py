"""
gameworks/main.py — Entry point for Mine-Streaker Minesweeper.

Handles CLI args, game loop, state machine, event dispatch,
and ties the engine to the renderer.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np
import pygame

try:
    from .engine import (
        Board, GameEngine, MoveResult,
        load_board_from_pipeline, load_board_from_npy, place_random_mines,
    )
    from .renderer import Renderer, FPS
except ImportError:
    from engine import (
        Board, GameEngine, MoveResult,
        load_board_from_pipeline, load_board_from_npy, place_random_mines,
    )
    from renderer import Renderer, FPS


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="minesweeper",
        description="Mine-Streaker Image Minesweeper — classic & image-reveal modes."
    )
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--image", type=str, default=None,
                      help="Source image — activates image-reveal mode (MineStreaker pipeline)")
    mode.add_argument("--load",  type=str, default=None,
                      help="Load a saved mine grid (.npy)")
    mode.add_argument("--random", action="store_true",
                      help="Classic random-mine board")

    diff = p.add_mutually_exclusive_group()
    diff.add_argument("--easy",   action="store_const", const="easy",   dest="diff")
    diff.add_argument("--medium", action="store_const", const="medium", dest="diff")
    diff.add_argument("--hard",   action="store_const", const="hard",   dest="diff")

    p.add_argument("--board-w",  type=int, default=300,  help="Board width  (tiles)")
    p.add_argument("--board-h",  type=int, default=370,  help="Board height (tiles)")
    p.add_argument("--mines",    type=int, default=0,     help="Mine count (0 = auto)")
    p.add_argument("--seed",     type=int, default=42,    help="Random seed")
    p.add_argument("--tile",     type=int, default=32,    help="Tile size (px)")
    return p


# ═══════════════════════════════════════════════════════════════════════════════
#  Game Loop
# ═══════════════════════════════════════════════════════════════════════════════

class GameLoop:
    """
    Top-level state machine:
      MENU → PLAYING → RESULT → MENU
    """

    MENU       = "menu"
    PLAYING    = "playing"
    RESULT     = "result"

    def __init__(self, args):
        self.args = args
        self._state = self.MENU
        self._engine: Optional[GameEngine] = None
        self._renderer: Optional[Renderer] = None
        self._result_time = 0.0
        self._result_shown = False

    # ── Board construction ────────────────────────────────────────────

    def _build_engine(self) -> GameEngine:
        a = self.args
        mode = "random"
        image_path = None

        if a.image:
            mode = "image"
            image_path = a.image
        elif a.load:
            eng = GameEngine(mode="npy", npy_path=a.load, seed=a.seed)
            return eng

        elif a.random or (not a.image):
            mode = "random"

        if getattr(a, 'diff', None):
            import gameworks.engine as _eng
            eng = _eng.GameEngine.from_difficulty(a.diff, seed=a.seed)
            return eng

        global TILE
        if a.tile:
            import gameworks.renderer as _r
            _r.TILE = a.tile
            TILE = a.tile

        eng = GameEngine(
            mode=mode, width=a.board_w, height=a.board_h,
            mines=a.mines, image_path=image_path, seed=a.seed,
        )
        return eng

    # ── Start a fresh game ────────────────────────────────────────────

    def _start_game(self):
        eng = self._build_engine()
        self._engine = eng
        self._engine.start()

        image_path = eng.image_path if eng.mode == "image" else None
        self._renderer = Renderer(eng, image_path=image_path)
        self._state = self.PLAYING
        self._result_shown = False

    # ── Main loop ─────────────────────────────────────────────────────

    def run(self):
        if not self._engine:
            self._start_game()

        running = True
        while running:
            dt_str = ""
            mouse_pos = pygame.mouse.get_pos()

            # ── Event handling ────────────────────────────────────────
            for ev in pygame.event.get():

                # Let renderer process events first
                r_action = self._renderer.handle_event(ev)

                if r_action == "quit":
                    running = False
                    break
                elif r_action == "restart":
                    self._start_game()
                    continue
                elif r_action and r_action.startswith("click:"):
                    _, rc = r_action.split(":")
                    x, y = map(int, rc.split(","))
                    if self._state == self.PLAYING:
                        self._do_left_click(x, y)

                elif r_action and r_action.startswith("flag:"):
                    _, rc = r_action.split(":")
                    x, y = map(int, rc.split(","))
                    if self._state == self.PLAYING:
                        self._do_right_click(x, y)

                elif r_action and r_action.startswith("chord:"):
                    _, rc = r_action.split(":")
                    x, y = map(int, rc.split(","))
                    if self._state == self.PLAYING:
                        self._do_chord(x, y)

                elif ev.type == pygame.QUIT:
                    running = False
                    break

                # Global keys handled by renderer already (KEYDOWN)

            if not running:
                break

            # ── State update ──────────────────────────────────────────
            elapsed = self._engine.elapsed if not self._engine.board.game_over else 0

            if self._state == self.PLAYING:
                if self._engine.state == "won":
                    self._state = self.RESULT
                    self._result_time = time.time()
                    self._result_shown = False
                    self._renderer.start_win_animation()
                elif self._engine.state == "lost":
                    self._state = self.RESULT
                    self._result_time = time.time()
                    self._result_shown = False

            # ── Draw ──────────────────────────────────────────────────
            cascade_done = True
            if self._renderer.cascade and not self._renderer.cascade.done:
                cascade_done = False

            gs = self._engine.state if self._engine else "waiting"
            self._renderer.draw(
                mouse_pos=mouse_pos,
                game_state=gs,
                elapsed=elapsed,
                cascade_done=cascade_done,
            )

            # Draw result overlays
            if self._state == self.RESULT and not self._result_shown:
                # During win animation, let draw_victory handle it (it shows modal only after anim completes)
                if gs == "won" and self._renderer.win_anim and not self._renderer.win_anim.done:
                    pass  # animation still running — draw_victory skips modal
                elif gs == "won":
                    self._renderer.draw_victory(elapsed)
                    self._result_shown = True
                elif gs == "lost":
                    self._renderer.draw_defeat()
                    self._result_shown = True

            self._renderer._clock.tick(FPS)

        pygame.quit()

    # ── Action dispatchers ────────────────────────────────────────────

    def _do_left_click(self, x, y):
        result = self._engine.left_click(x, y)
        if result.newly_revealed:
            from .renderer import AnimationCascade
            self._renderer.cascade = AnimationCascade(result.newly_revealed)
        if result.hit_mine:
            self._state = self.RESULT
            self._result_time = time.time()

    def _do_right_click(self, x, y):
        state = self._engine.right_click(x, y)
        return state

    def _do_chord(self, x, y):
        result = self._engine.middle_click(x, y)
        if result.newly_revealed:
            from .renderer import AnimationCascade
            self._renderer.cascade = AnimationCascade(result.newly_revealed)
        if result.hit_mine:
            self._state = self.RESULT
            self._result_time = time.time()

    def _save_npy(self):
        """Save current board's grid to an npy file."""
        eng = self._engine
        if not eng:
            return
        grid = np.zeros((eng.board.height, eng.board.width), dtype=np.int8)
        for y in range(eng.board.height):
            for x in range(eng.board.width):
                cell = eng.board.snapshot(x, y)
                if cell.is_mine:
                    grid[y, x] = -1
                else:
                    grid[y, x] = cell.neighbour_mines
        ts = time.strftime("%Y%m%d_%H%M%S")
        fname = f"board_{ts}_{eng.board.width}x{eng.board.height}.npy"
        np.save(fname, grid)
        print(f"[SAVE] Board saved to {fname}")


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    args = build_parser().parse_args()

    # Allow overriding TILE globally
    global TILE
    if args.tile:
        TILE = args.tile

    loop = GameLoop(args)
    loop.run()


if __name__ == "__main__":
    main()