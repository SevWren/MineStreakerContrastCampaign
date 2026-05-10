"""
gameworks/tests/cli/test_parser.py

Tests for gameworks.main.build_parser().

Covers:
- All documented flags are present
- Default values match documentation
- Mutually exclusive flags are rejected
- Difficulty flags map to correct presets
- Board dimension flags are integers
"""

from __future__ import annotations

import pytest

from gameworks.main import build_parser


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse(*args: str):
    """Parse args through build_parser; raise SystemExit on invalid input."""
    return build_parser().parse_args(list(args))


# ---------------------------------------------------------------------------
# Board mode flags
# ---------------------------------------------------------------------------

class TestModeFlagPresence:

    def test_random_flag_exists(self):
        args = parse("--random")
        assert args.random is True

    def test_image_flag_exists(self):
        args = parse("--image", "test.png")
        assert args.image == "test.png"

    def test_load_flag_exists(self):
        args = parse("--load", "board.npy")
        assert args.load == "board.npy"


# ---------------------------------------------------------------------------
# Difficulty flags
# ---------------------------------------------------------------------------

class TestDifficultyFlags:

    def test_easy_flag_exists(self):
        args = parse("--random", "--easy")
        assert args.diff == "easy"

    def test_medium_flag_exists(self):
        args = parse("--random", "--medium")
        assert args.diff == "medium"

    def test_hard_flag_exists(self):
        args = parse("--random", "--hard")
        assert args.diff == "hard"


# ---------------------------------------------------------------------------
# Board dimension flags
# ---------------------------------------------------------------------------

class TestDimensionFlags:

    def test_width_flag(self):
        args = parse("--random", "--board-w", "20")
        assert args.board_w == 20

    def test_height_flag(self):
        args = parse("--random", "--board-h", "15")
        assert args.board_h == 15

    def test_mines_flag(self):
        args = parse("--random", "--mines", "30")
        assert args.mines == 30

    def test_tile_flag(self):
        args = parse("--random", "--tile", "24")
        assert args.tile == 24

    def test_seed_flag(self):
        args = parse("--random", "--seed", "99")
        assert args.seed == 99


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

class TestDefaults:

    def test_mines_default_zero(self):
        """--mines 0 means auto-compute (width*height // 6)."""
        args = parse("--random")
        assert args.mines == 0

    def test_seed_default(self):
        args = parse("--random")
        assert isinstance(args.seed, int)

    def test_easy_medium_hard_default_none(self):
        args = parse("--random")
        assert args.diff is None


# ---------------------------------------------------------------------------
# Mutual exclusion
# ---------------------------------------------------------------------------

class TestMutualExclusion:

    def test_easy_and_hard_mutually_exclusive(self):
        """Cannot set both --easy and --hard."""
        with pytest.raises(SystemExit):
            parse("--random", "--easy", "--hard")

    def test_easy_and_medium_mutually_exclusive(self):
        with pytest.raises(SystemExit):
            parse("--random", "--easy", "--medium")
