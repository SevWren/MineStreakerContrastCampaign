"""
gameworks/tests/renderer/

Headless renderer tests using SDL dummy drivers.

ALL tests in this directory require:
    SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy

These are set in renderer/conftest.py via os.environ before pygame is imported.
"""
