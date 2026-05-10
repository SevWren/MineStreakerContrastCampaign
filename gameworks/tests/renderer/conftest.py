"""
gameworks/tests/renderer/conftest.py

Shared fixtures for headless renderer tests.

Sets SDL dummy drivers before any pygame import, then provides
initialised Renderer/GameEngine pairs as pytest fixtures.
"""

from __future__ import annotations

import os

import pytest

# Must be set before pygame is first imported anywhere in this process.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

pygame = pytest.importorskip("pygame", reason="pygame not installed — renderer tests skipped")


@pytest.fixture(scope="module", autouse=True)
def _pygame_module_init():
    """Initialise pygame once per test module; quit after all tests complete."""
    pygame.init()
    pygame.display.set_mode((800, 600))
    yield
    pygame.quit()


@pytest.fixture
def renderer_easy():
    """Return an initialised (Renderer, GameEngine) for a 9×9 Easy board."""
    from gameworks.engine import GameEngine
    from gameworks.renderer import Renderer
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    eng.start()
    r = Renderer(eng)
    return r, eng


@pytest.fixture
def renderer_medium():
    """Return an initialised (Renderer, GameEngine) for a 16×16 Medium board."""
    from gameworks.engine import GameEngine
    from gameworks.renderer import Renderer
    eng = GameEngine(mode="random", width=16, height=16, mines=40, seed=42)
    eng.start()
    r = Renderer(eng)
    return r, eng


@pytest.fixture
def renderer_panel_large():
    """Return (Renderer, GameEngine) for a 40×30 board with _panel_right=True.

    40×30 is large enough that at a forced 800×600 viewport the dynamic zoom
    floor (min_fit_tile = 7) falls below MIN_TILE_SIZE (10), which makes it
    the canonical fixture for zoom-floor behaviour tests.

    Tests that care about deterministic floor values should set:
        r._win_size = (800, 600)
    after receiving this fixture, since the dummy display size may vary.
    """
    from gameworks.engine import GameEngine
    from gameworks.renderer import Renderer
    eng = GameEngine(mode="random", width=40, height=30, mines=60, seed=42)
    eng.start()
    r = Renderer(eng)
    return r, eng


@pytest.fixture
def animation_positions():
    """Standard list of (x, y) positions for animation tests."""
    return [(i, 0) for i in range(10)]


@pytest.fixture
def renderer_large():
    """Return an initialised (Renderer, GameEngine) for a 300×370 board where _panel_overlay is True."""
    from gameworks.engine import GameEngine
    from gameworks.renderer import Renderer
    eng = GameEngine(mode="random", width=300, height=370, mines=0, seed=42)
    eng.start()
    r = Renderer(eng)
    return r, eng
