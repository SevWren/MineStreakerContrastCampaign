"""
gameworks/tests/unit/test_config.py

Tests for the GameConfig frozen dataclass.

Status: PENDING — GameConfig does not exist yet.
Implement per DESIGN_PATTERNS.md § R2 — GameConfig Frozen Dataclass.

When R2 is implemented:
1. Remove the module-level skip.
2. Update the imports to include GameConfig.
3. All tests in this file must pass.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.skip(reason="Pending R2 — GameConfig frozen dataclass not yet implemented")


# ---------------------------------------------------------------------------
# Once R2 is implemented, replace this stub import:
#   from gameworks.engine import GameConfig, GameEngine
# ---------------------------------------------------------------------------


class TestGameConfigConstruction:

    def test_default_values(self):
        """GameConfig() with no arguments must produce the documented defaults."""
        from gameworks.engine import GameConfig  # noqa: F401  (import after skip guard removed)
        cfg = GameConfig()
        assert cfg.mode == "random"
        assert cfg.width == 16
        assert cfg.height == 16
        assert cfg.mines == 0
        assert cfg.image_path == ""
        assert cfg.npy_path == ""
        assert cfg.seed == 42

    def test_is_frozen(self):
        """GameConfig must be immutable (frozen=True)."""
        from gameworks.engine import GameConfig
        cfg = GameConfig()
        with pytest.raises((AttributeError, TypeError)):
            cfg.width = 999  # type: ignore[misc]

    def test_custom_values_stored(self):
        from gameworks.engine import GameConfig
        cfg = GameConfig(mode="npy", width=30, height=16, mines=99, seed=7)
        assert cfg.mode == "npy"
        assert cfg.width == 30
        assert cfg.height == 16
        assert cfg.mines == 99
        assert cfg.seed == 7

    def test_is_hashable(self):
        """Frozen dataclasses must be hashable."""
        from gameworks.engine import GameConfig
        cfg = GameConfig(seed=1)
        assert isinstance(hash(cfg), int)

    def test_equality_by_value(self):
        from gameworks.engine import GameConfig
        a = GameConfig(seed=10, width=9, height=9)
        b = GameConfig(seed=10, width=9, height=9)
        assert a == b

    def test_inequality_different_seed(self):
        from gameworks.engine import GameConfig
        a = GameConfig(seed=10)
        b = GameConfig(seed=11)
        assert a != b


class TestGameConfigMetrics:

    def test_to_metrics_dict_keys(self):
        from gameworks.engine import GameConfig
        cfg = GameConfig(mode="random", width=9, height=9, mines=10, seed=42)
        d = cfg.to_metrics_dict()
        expected_keys = {"mode", "width", "height", "mines", "image_path", "npy_path", "seed"}
        assert set(d.keys()) == expected_keys

    def test_to_metrics_dict_values(self):
        from gameworks.engine import GameConfig
        cfg = GameConfig(mode="random", width=9, height=9, mines=10, seed=42)
        d = cfg.to_metrics_dict()
        assert d["mode"] == "random"
        assert d["width"] == 9
        assert d["seed"] == 42


class TestGameEngineAcceptsConfig:

    def test_engine_constructed_from_config(self):
        from gameworks.engine import GameConfig, GameEngine
        cfg = GameConfig(mode="random", width=9, height=9, mines=10, seed=42)
        eng = GameEngine(cfg)
        eng.start()
        assert eng.board.width == 9
        assert eng.board.total_mines == 10

    def test_engine_exposes_config(self):
        from gameworks.engine import GameConfig, GameEngine
        cfg = GameConfig(mode="random", width=9, height=9, mines=10, seed=42)
        eng = GameEngine(cfg)
        assert eng.config is cfg

    def test_restart_produces_new_frozen_config(self):
        """restart() must produce a new GameConfig with seed+1."""
        from gameworks.engine import GameConfig, GameEngine
        cfg = GameConfig(seed=5)
        eng = GameEngine(cfg)
        eng.start()
        eng.restart()
        assert eng.config.seed == 6
        assert eng.config is not cfg   # different object

    def test_from_difficulty_uses_config(self):
        """from_difficulty() must produce an engine whose .config is a GameConfig."""
        from gameworks.engine import GameConfig, GameEngine
        eng = GameEngine.from_difficulty("easy", seed=1)
        assert isinstance(eng.config, GameConfig)
        assert eng.config.width == 9
