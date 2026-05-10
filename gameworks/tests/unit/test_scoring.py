"""
gameworks/tests/unit/test_scoring.py

Tests for scoring constants and streak-multiplier lookup table.

These tests verify the numeric values that drive all score changes.
They must stay in sync with GAME_DESIGN.md § Scoring System.

See also: DEVELOPER_GUIDE.md § Adding a New Scoring Rule
"""

from __future__ import annotations

import pytest

from gameworks.engine import (
    CORRECT_FLAG_BONUS,
    MINE_HIT_PENALTY,
    REVEAL_POINTS,
    STREAK_TIERS,
    WRONG_FLAG_PENALTY,
)


# ---------------------------------------------------------------------------
# Constant values
# ---------------------------------------------------------------------------

class TestScoringConstants:

    def test_reveal_points_length(self):
        """REVEAL_POINTS must have 9 entries: indices 0–8 (neighbour count)."""
        assert len(REVEAL_POINTS) == 9

    def test_reveal_points_zero_neighbours(self):
        assert REVEAL_POINTS[0] == 1

    def test_reveal_points_strictly_increasing(self):
        """Higher neighbour counts must be worth more points."""
        for i in range(1, len(REVEAL_POINTS)):
            assert REVEAL_POINTS[i] > REVEAL_POINTS[i - 1], \
                f"REVEAL_POINTS[{i}]={REVEAL_POINTS[i]} not > REVEAL_POINTS[{i-1}]={REVEAL_POINTS[i-1]}"

    def test_reveal_points_eight_neighbours(self):
        assert REVEAL_POINTS[8] == 150

    def test_correct_flag_bonus(self):
        assert CORRECT_FLAG_BONUS == 50

    def test_wrong_flag_penalty(self):
        assert WRONG_FLAG_PENALTY == 25

    def test_mine_hit_penalty(self):
        assert MINE_HIT_PENALTY == 250

    def test_wrong_flag_less_than_correct_bonus(self):
        """Wrong-flag penalty must be less severe than correct-flag reward."""
        assert WRONG_FLAG_PENALTY < CORRECT_FLAG_BONUS

    def test_mine_hit_greater_than_correct_flag(self):
        """Mine hit is the most severe penalty."""
        assert MINE_HIT_PENALTY > CORRECT_FLAG_BONUS


# ---------------------------------------------------------------------------
# Streak tiers
# ---------------------------------------------------------------------------

class TestStreakTiers:

    def test_streak_tiers_is_list_of_tuples(self):
        for entry in STREAK_TIERS:
            assert isinstance(entry, tuple)
            assert len(entry) == 2

    def test_streak_tiers_sorted_descending_by_threshold(self):
        """Tiers must be ordered from highest threshold to lowest."""
        thresholds = [t for t, _ in STREAK_TIERS]
        assert thresholds == sorted(thresholds, reverse=True)

    def test_base_tier_multiplier_is_1x(self):
        """The last tier (threshold 0) must have multiplier 1.0."""
        last_threshold, last_mult = STREAK_TIERS[-1]
        assert last_threshold == 0
        assert last_mult == 1.0

    def test_tier_25_is_5x(self):
        tier = next((m for t, m in STREAK_TIERS if t == 25), None)
        assert tier == 5.0

    def test_tier_15_is_3x(self):
        tier = next((m for t, m in STREAK_TIERS if t == 15), None)
        assert tier == 3.0

    def test_tier_10_is_2x(self):
        tier = next((m for t, m in STREAK_TIERS if t == 10), None)
        assert tier == 2.0

    def test_tier_5_is_1_5x(self):
        tier = next((m for t, m in STREAK_TIERS if t == 5), None)
        assert tier == 1.5

    def test_all_multipliers_at_least_1x(self):
        for _, mult in STREAK_TIERS:
            assert mult >= 1.0


# ---------------------------------------------------------------------------
# GameEngine.streak_multiplier property
# ---------------------------------------------------------------------------

class TestStreakMultiplierProperty:

    def _eng_at_streak(self, streak: int):
        from gameworks.engine import GameEngine
        eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
        eng.start()
        eng.streak = streak
        return eng

    @pytest.mark.parametrize("streak,expected_mult", [
        (0,  1.0),
        (1,  1.0),
        (4,  1.0),
        (5,  1.5),
        (9,  1.5),
        (10, 2.0),
        (14, 2.0),
        (15, 3.0),
        (24, 3.0),
        (25, 5.0),
        (99, 5.0),
    ])
    def test_multiplier_at_streak(self, streak: int, expected_mult: float):
        eng = self._eng_at_streak(streak)
        assert eng.streak_multiplier == expected_mult, \
            f"streak={streak}: expected {expected_mult}×, got {eng.streak_multiplier}×"
