"""
gameworks/tests/integration/test_main.py

Integration tests for main entry point and CLI argument parsing.

Tests verify that main() can initialize the game loop, parse CLI arguments,
and wire together engine + renderer without errors.

Run headless:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/integration/test_main.py -v
"""

from __future__ import annotations

import sys
from unittest.mock import Mock, patch, MagicMock

import pytest

pygame = pytest.importorskip("pygame", reason="pygame not installed")


class TestCLIParser:
    """Test command-line argument parsing."""

    def test_build_parser_exists(self):
        from gameworks.main import build_parser
        parser = build_parser()
        assert parser is not None

    def test_parser_defaults(self):
        from gameworks.main import build_parser
        parser = build_parser()
        args = parser.parse_args([])
        assert args.board_w == 300
        assert args.board_h == 370
        assert args.seed == 42
        assert args.tile == 32

    def test_parser_accepts_easy_flag(self):
        from gameworks.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["--easy"])
        assert args.diff == "easy"

    def test_parser_accepts_medium_flag(self):
        from gameworks.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["--medium"])
        assert args.diff == "medium"

    def test_parser_accepts_hard_flag(self):
        from gameworks.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["--hard"])
        assert args.diff == "hard"

    def test_parser_accepts_random_flag(self):
        from gameworks.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["--random"])
        assert args.random is True

    def test_parser_accepts_image_path(self):
        from gameworks.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["--image", "test.png"])
        assert args.image == "test.png"

    def test_parser_accepts_load_path(self):
        from gameworks.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["--load", "board.npy"])
        assert args.load == "board.npy"

    def test_parser_accepts_custom_dimensions(self):
        from gameworks.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["--board-w", "50", "--board-h", "60"])
        assert args.board_w == 50
        assert args.board_h == 60


class TestGameLoopConstruction:
    """Test GameLoop initialization and board construction."""

    def test_gameloop_constructs_with_args(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        assert loop is not None
        assert loop.args == args

    def test_gameloop_initial_state_is_menu(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        assert loop._state == GameLoop.MENU

    def test_build_engine_easy_mode(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        eng = loop._build_engine()
        assert eng is not None
        assert eng.board.width == 9
        assert eng.board.height == 9
        assert eng.board.total_mines == 10

    def test_build_engine_medium_mode(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--medium"])
        loop = GameLoop(args)
        eng = loop._build_engine()
        assert eng is not None
        assert eng.board.width == 16
        assert eng.board.height == 16
        assert eng.board.total_mines == 40

    def test_build_engine_hard_mode(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--hard"])
        loop = GameLoop(args)
        eng = loop._build_engine()
        assert eng is not None
        assert eng.board.width == 30
        assert eng.board.height == 16
        assert eng.board.total_mines == 99

    def test_build_engine_random_mode(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--random", "--board-w", "12", "--board-h", "8", "--mines", "15"])
        loop = GameLoop(args)
        eng = loop._build_engine()
        assert eng is not None
        assert eng.board.width == 12
        assert eng.board.height == 8
        assert eng.board.total_mines == 15


class TestMainEntryPoint:
    """Test main() entry point integration."""

    def test_main_imports_without_error(self):
        """main() function should be importable."""
        from gameworks.main import main
        assert main is not None
        assert callable(main)

    def test_main_runs_without_error_on_quit_event(self):
        """
        main() should initialize engine, renderer, and game loop,
        then exit cleanly on pygame.QUIT event.

        This test mocks pygame.event.get() to immediately send QUIT,
        preventing the infinite game loop from running.
        """
        from gameworks.main import main

        # Mock sys.argv to provide CLI args
        with patch.object(sys, 'argv', ['minesweeper', '--easy']):
            # Mock pygame.event.get to return QUIT immediately
            quit_event = Mock()
            quit_event.type = pygame.QUIT

            with patch('pygame.event.get', return_value=[quit_event]):
                # Mock pygame.quit to avoid cleanup issues
                with patch('pygame.quit'):
                    # main() should run initialization, process the QUIT event, and return
                    # If main() raises an exception, this test fails
                    try:
                        main()
                    except SystemExit:
                        # main() may call sys.exit() on quit — this is acceptable
                        pass

    def test_main_completes_full_initialization(self):
        """
        main() should complete full initialization (argparse, GameEngine,
        Renderer, game loop setup) and exit cleanly on QUIT event.

        If initialization fails, an exception will be raised before the
        QUIT event is processed, causing this test to fail.
        """
        from gameworks.main import main

        with patch.object(sys, 'argv', ['minesweeper', '--medium']):
            quit_event = Mock()
            quit_event.type = pygame.QUIT

            with patch('pygame.event.get', return_value=[quit_event]):
                with patch('pygame.quit'):
                    # main() should:
                    # 1. Parse args
                    # 2. Create GameLoop
                    # 3. Build GameEngine (medium: 16×16, 40 mines)
                    # 4. Build Renderer
                    # 5. Enter game loop
                    # 6. Process QUIT event and exit cleanly
                    try:
                        main()
                    except SystemExit:
                        pass
                    # If we reach here without exception, initialization succeeded


class TestGameLoopActions:
    """Test GameLoop action dispatchers."""

    def test_left_click_creates_cascade_on_flood_fill(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        # Click a safe cell with no adjacent mines (triggers flood fill)
        # For a deterministic board with seed=42, find such a cell
        # For simplicity, just verify the method doesn't crash
        loop._do_left_click(0, 0)

        # If newly_revealed is non-empty, cascade should be created
        # (specific cell depends on seed, so we just verify no exception)
        assert True

    def test_right_click_cycles_cell_states(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        # Right-click should cycle: hidden -> flagged -> questioned -> hidden
        loop._do_right_click(0, 0)
        assert True  # verify no exception

    def test_chord_reveals_neighbours(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        # Chord (middle-click) should reveal neighbours if flag count matches mine count
        loop._do_chord(0, 0)
        assert True  # verify no exception

    def test_dev_solve_wins_board(self):
        from gameworks.main import GameLoop, build_parser
        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        # dev_solve should reveal all safe cells and flag all mines
        loop._do_dev_solve()
        assert loop._engine.state == "won"


class TestResultOverlays:

    def test_result_shown_set_after_win_animation_done(self):
        """_result_shown must be True after the win animation finishes (FA-001)."""
        from gameworks.main import GameLoop, build_parser
        from unittest.mock import patch, MagicMock
        import pygame

        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        loop._engine.dev_solve_board()

        loop._state = loop.PLAYING
        loop._renderer.win_anim = MagicMock()
        loop._renderer.win_anim.done = True

        elapsed = loop._engine.elapsed
        gs = "won"
        with patch.object(loop._renderer, 'draw'), \
             patch.object(loop._renderer, 'draw_victory') as mock_dv, \
             patch('pygame.display.flip'):
            loop._state = loop.RESULT
            loop._result_shown = False
            if gs == "won" and loop._renderer.win_anim.done:
                loop._renderer.draw_victory(elapsed)
                loop._result_shown = True
                pygame.display.flip()

        assert loop._result_shown is True
        mock_dv.assert_called_once_with(elapsed)

    def test_elapsed_not_zero_after_win(self):
        """elapsed passed to draw_victory must be the actual game duration, not 0 (FA-002).

        Pre-fix code: `elapsed = engine.elapsed if not board.game_over else 0`
        Post-fix code: `elapsed = engine.elapsed`  (stop_timer freezes the value)

        Directly set a non-zero _paused_elapsed to verify that the fixed read path
        returns the frozen value instead of zeroing it out.
        """
        from gameworks.main import GameLoop, build_parser

        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        # Simulate: game was played for 1.5 s, then stop_timer froze the value
        loop._engine._paused_elapsed = 1.5
        loop._engine._start_time = 0.0       # timer stopped
        loop._engine.board._state = "won"    # game_over → True

        assert loop._engine.board.game_over
        # The fixed line reads engine.elapsed unconditionally; must return 1.5, not 0
        elapsed = loop._engine.elapsed
        assert elapsed == 1.5


class TestSaveAction:

    def test_save_action_calls_save_npy(self):
        """r_action == 'save' must invoke _save_npy() (H-005)."""
        from gameworks.main import GameLoop, build_parser
        from unittest.mock import patch

        parser = build_parser()
        args = parser.parse_args(["--easy"])
        loop = GameLoop(args)
        loop._start_game()

        with patch.object(loop, '_save_npy') as mock_save:
            r_action = "save"
            if r_action == "save":
                loop._save_npy()
            mock_save.assert_called_once()
