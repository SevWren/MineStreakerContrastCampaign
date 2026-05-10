"""
gameworks/tests/

Package-local test suite for the gameworks package.

Layout
------
unit/           Pure-logic tests — no pygame, no display required.
renderer/       Headless pygame tests (SDL_VIDEODRIVER=dummy).
integration/    Multi-module flows: GameLoop states, board modes, save/load.
architecture/   Import boundary and structural contract tests.
cli/            Argument parser and preflight check tests.
fixtures/       Shared board/engine factories and sample .npy files.

Run the full suite (headless):
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest gameworks/tests/ -v

Run unit tests only (no SDL env var needed):
    pytest gameworks/tests/unit/ -v
"""
