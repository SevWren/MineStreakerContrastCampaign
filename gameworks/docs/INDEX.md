# Gameworks Documentation Index

`gameworks/` is the interactive Pygame-based Minesweeper front-end for the Mine-Streaker project.
All documentation for this package lives here and is self-contained — independent of the pipeline engine docs.

---

## Documents

| Document | Description |
|---|---|
| [README.md](README.md) | Package overview, installation, launch modes, controls |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Module breakdown, class relationships, state machines, data flow |
| [API_REFERENCE.md](API_REFERENCE.md) | Full public API for every class and function in the package |
| [GAME_DESIGN.md](GAME_DESIGN.md) | Game design document: rules, scoring, streaks, difficulty tiers, board modes |
| [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) | Dev environment setup, testing, extending the package |
| [CHANGELOG.md](CHANGELOG.md) | Version history and release notes |
| [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md) | Pipeline alignment audit: design patterns, gaps, and recommended improvements |
| [BUGS.md](BUGS.md) | All open bugs — flat register with root cause, fix spec, and test coverage gap per entry |

---

## Package Layout

```
gameworks/
├── __init__.py        Package entry point, version string
├── engine.py          Pure game logic — Board, GameEngine, scoring, mine placement
├── renderer.py        Pygame rendering — tiles, HUD, animations, image overlay
├── main.py            CLI entry point, GameLoop state machine
└── docs/              ← You are here
    ├── INDEX.md
    ├── README.md
    ├── ARCHITECTURE.md
    ├── API_REFERENCE.md
    ├── GAME_DESIGN.md
    ├── DEVELOPER_GUIDE.md
    ├── CHANGELOG.md
    ├── DESIGN_PATTERNS.md
    └── BUGS.md
```

---

## Quick Navigation

- **New to the game?** Start with [README.md](README.md).
- **Integrating the engine?** Read [API_REFERENCE.md](API_REFERENCE.md).
- **Understanding the design?** Read [ARCHITECTURE.md](ARCHITECTURE.md).
- **Modifying game rules or scoring?** Read [GAME_DESIGN.md](GAME_DESIGN.md).
- **Setting up for development?** Read [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md).
- **Engineering discipline / pipeline alignment?** Read [DESIGN_PATTERNS.md](DESIGN_PATTERNS.md).

---

*Gameworks v0.1.0 — part of the Mine-Streaker project.*
