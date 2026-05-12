"""
gameworks/main.py — Entry point for Mine-Streaker Minesweeper.

Handles CLI args, game loop, state machine, event dispatch,
and ties the engine to the renderer.
"""

from __future__ import annotations

import argparse
import threading
import time
from pathlib import Path

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

        if a.tile:
            import gameworks.renderer as _r
            _r.TILE = a.tile

        eng = GameEngine(
            mode=mode, width=a.board_w, height=a.board_h,
            mines=a.mines, image_path=image_path, seed=a.seed,
        )
        return eng

    # ── Menu screen ───────────────────────────────────────────────────

    def _show_menu_screen(self):
        """FA-014: Minimal MENU state — blocks until any key / click is pressed.

        Implements the documented MENU→PLAYING arc.  Uses pygame directly so
        there is no dependency on a Renderer that hasn't been built yet.
        """
        pygame.init()
        # If no renderer yet, open a minimal window just for the splash.
        if not self._renderer:
            win = pygame.display.set_mode((640, 200), pygame.RESIZABLE)
            pygame.display.set_caption("Mine-Streaker")
        else:
            win = self._renderer._win
        font_big   = pygame.font.SysFont("consolas", 36, bold=True)
        font_small = pygame.font.SysFont("consolas", 18)
        clock = pygame.time.Clock()
        waiting = True
        while waiting:
            for ev in pygame.event.get():
                if ev.type in (pygame.QUIT,):
                    pygame.quit()
                    raise SystemExit
                if ev.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    waiting = False
            win.fill((18, 18, 24))
            w, h = win.get_size()
            t1 = font_big.render("MINE-STREAKER", True, (55, 195, 195))
            t2 = font_small.render("Press any key to start", True, (120, 120, 140))
            win.blit(t1, t1.get_rect(center=(w // 2, h // 2 - 24)))
            win.blit(t2, t2.get_rect(center=(w // 2, h // 2 + 20)))
            pygame.display.flip()
            clock.tick(30)

    # ── Start / retry a game ─────────────────────────────────────────

    def _retry_game(self):
        """M-003: Replay the exact same board (same seed).  Reuses existing Renderer."""
        if self._engine:
            self._engine.retry()
            self._engine.start()
        if self._renderer:
            self._renderer.win_anim = None
            self._renderer.cascade = None
            self._renderer._ghost_surf = None
            self._renderer._ghost_mine_surf = None
            self._renderer._ghost_wrong_surf = None
        self._state = self.PLAYING
        self._result_shown = False

    def _start_game(self):
        """Build the engine on a background thread to keep the event loop alive.

        Board generation (especially the SA pipeline for --image mode) can block
        for 30-90+ seconds.  Running it on the main thread freezes the pygame
        event queue, causing Windows to mark the window "(Not Responding)".
        This method runs _build_engine() on a daemon thread and shows an animated
        loading screen while waiting, so the window stays responsive throughout.
        """
        result: list = []           # filled by worker: [eng] on success, [None, exc] on error
        done = threading.Event()

        def _worker():
            try:
                result.append(self._build_engine())
            except Exception as exc:  # noqa: BLE001
                result.append(None)
                result.append(exc)
            finally:
                done.set()

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

        # ── Loading screen — main thread keeps pumping events ─────────────
        win = pygame.display.get_surface()
        if win is None:
            pygame.init()
            win = pygame.display.set_mode((640, 200), pygame.RESIZABLE)
            pygame.display.set_caption("Mine-Streaker")

        font_big   = pygame.font.SysFont("consolas", 28, bold=True)
        font_small = pygame.font.SysFont("consolas", 16)
        clock      = pygame.time.Clock()
        start_t    = time.monotonic()
        dots       = ["   ", ".  ", ".. ", "..."]

        while not done.is_set():
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    raise SystemExit
            elapsed  = time.monotonic() - start_t
            dot_idx  = int(elapsed * 2) % len(dots)
            w, h     = win.get_size()
            win.fill((18, 18, 24))
            t1 = font_big.render("Generating board" + dots[dot_idx], True, (55, 195, 195))
            t2 = font_small.render(
                f"elapsed: {elapsed:.0f}s  (SA pipeline may take up to 90s)",
                True, (90, 90, 110),
            )
            win.blit(t1, t1.get_rect(center=(w // 2, h // 2 - 20)))
            win.blit(t2, t2.get_rect(center=(w // 2, h // 2 + 20)))
            pygame.display.flip()
            clock.tick(30)

        t.join()

        # Re-raise any exception that occurred in the worker thread
        if len(result) == 2 and result[0] is None:
            raise result[1]

        eng = result[0]
        self._engine = eng
        self._engine.start()
        image_path = eng.image_path if eng.mode == "image" else None
        self._renderer = Renderer(eng, image_path=image_path)
        self._state = self.PLAYING
        self._result_shown = False

    # ── Main loop ─────────────────────────────────────────────────────

    def run(self):
        # FA-014: MENU state is now honoured — show a simple "Press any key" splash
        # before starting the first game, implementing the documented MENU→PLAYING arc.
        if self._state == self.MENU:
            self._show_menu_screen()
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
                    self._state = self.MENU         # FA-014: RESULT → MENU → PLAYING
                    self._show_menu_screen()
                    self._start_game()
                    continue
                elif r_action == "retry":           # M-003: replay same board layout
                    self._retry_game()
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

                elif r_action == "dev:solve":
                    if self._state == self.PLAYING:
                        self._do_dev_solve()

                elif r_action == "save":        # H-005: wire Save button to _save_npy()
                    self._save_npy()

                elif ev.type == pygame.QUIT:
                    running = False
                    break

                # Global keys handled by renderer already (KEYDOWN)

            if not running:
                break

            # ── State update ──────────────────────────────────────────
            elapsed = self._engine.elapsed   # FA-002: engine.stop_timer() already freezes this on win

            if self._state == self.PLAYING:
                if self._engine.state == "won":
                    self._state = self.RESULT
                    self._result_time = time.time()
                    self._result_shown = False
                    self._renderer.start_win_animation()
                # "lost" state no longer exists — mine hits are penalties, not game over

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
                    pygame.display.flip()   # FA-001: second flip required — draw() already flipped
                # no "lost" branch — game never ends on mine hit

            self._renderer._clock.tick(FPS)

        pygame.quit()

    # ── Action dispatchers ────────────────────────────────────────────

    def _do_left_click(self, x, y):
        result = self._engine.left_click(x, y)
        if result.newly_revealed:
            from .renderer import AnimationCascade
            self._renderer.cascade = AnimationCascade(result.newly_revealed)
        # Mine hit is a score penalty — game continues, do NOT transition to RESULT

    def _do_right_click(self, x, y):
        self._engine.right_click(x, y)

    def _do_chord(self, x, y):
        result = self._engine.middle_click(x, y)
        if result.newly_revealed:
            from .renderer import AnimationCascade
            self._renderer.cascade = AnimationCascade(result.newly_revealed)
        # Mine hit via chord is a penalty — game continues

    def _do_dev_solve(self):
        """DEV: instantly reveal all safe cells and flag all mines, then win the board.

        Skips AnimationCascade — boards can have 100k+ safe cells and the cascade
        would take hours at normal speed.  The game loop detects 'won' next frame
        and fires the win sequence (animation + modal) through the normal path.
        """
        self._engine.dev_solve_board()
        # board._state is now "won"; game loop picks it up on the next iteration

    def _save_npy(self):
        """Construct save path and delegate to engine."""
        if not self._engine:
            return

        # Path construction (CLI/UI concern - stays in main.py)
        out_dir = Path(__file__).parent.parent / "results"
        out_dir.mkdir(exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        path = out_dir / f"board_{ts}_{self._engine.board.width}x{self._engine.board.height}.npy"

        # Delegate to engine (serialization + I/O)
        try:
            self._engine._save_npy_to(str(path))
            print(f"[SAVE] Board saved to {path}")
        except (PermissionError, OSError) as e:
            print(f"[SAVE FAILED] {e}")


# ═══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ═══════════════════════════════════════════════════════════════════════════════

def preflight_check(args) -> None:
    """DP-R6: Validate CLI args before constructing GameLoop.

    Raises SystemExit with a human-readable message on any detected problem
    so errors surface before the game window opens, not mid-loop.
    """
    import sys
    errors: list = []

    if args.image:
        if not Path(args.image).exists():
            errors.append(f"--image path not found: {args.image!r}")
        elif not Path(args.image).is_file():
            errors.append(f"--image is not a file: {args.image!r}")

    if args.load:
        if not Path(args.load).exists():
            errors.append(f"--load path not found: {args.load!r}")
        elif not args.load.endswith(".npy"):
            errors.append(f"--load expects a .npy file, got: {args.load!r}")

    if getattr(args, 'board_w', 1) < 1 or getattr(args, 'board_h', 1) < 1:
        errors.append(f"Board dimensions must be >= 1 (got {args.board_w}x{args.board_h})")

    if getattr(args, 'mines', 0) < 0:
        errors.append(f"Mine count must be >= 0 (got {args.mines})")

    try:
        import pygame  # noqa: F401 — confirm pygame is importable
    except ImportError:
        errors.append("pygame is not installed — run: pip install pygame")

    if errors:
        sys.stderr.write("preflight_check failed:\n")
        for e in errors:
            sys.stderr.write(f"  • {e}\n")
        sys.exit(1)


def main():
    args = build_parser().parse_args()
    preflight_check(args)       # DP-R6: validate before opening window

    loop = GameLoop(args)
    loop.run()


if __name__ == "__main__":
    main()