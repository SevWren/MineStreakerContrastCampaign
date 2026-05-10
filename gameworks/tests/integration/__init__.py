"""
gameworks/tests/integration/

Multi-module integration tests.

These tests exercise cross-module flows:
  - GameLoop state machine (MENU → PLAYING → RESULT → MENU)
  - Board mode loading end-to-end (random, npy, image fallback)
  - Save/load round-trip with atomic write and JSON sidecar

All require SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy for anything that
initialises pygame.
"""
