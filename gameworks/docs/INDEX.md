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
| [BUGS.md](BUGS.md) | All known bugs — flat register with root cause, fix spec, and test coverage gap per entry |
| [PERFORMANCE_PLAN.md](PERFORMANCE_PLAN.md) | Performance remediation plan for P-01 through P-18 hot-path optimisations (Phases 1–3 done; 4–8 pending) |
| [ZOOM_OUT_PERFORMANCE_REPORT.md](ZOOM_OUT_PERFORMANCE_REPORT.md) | Forensic analysis of 13 zoom-out bottlenecks; informs PERFORMANCE_PLAN Phases 4–8 and gap fixes N-01/N-02 |
| [REMEDIATION_PLAN_VERIFICATION.md](REMEDIATION_PLAN_VERIFICATION.md) | Pre-execution readiness check for PERFORMANCE_PLAN; identifies Phase 7B WinAnimation._idx blocker |
| [FORENSIC_VISUAL_RECONSTRUCTION_ANALYSIS.md](FORENSIC_VISUAL_RECONSTRUCTION_ANALYSIS.md) | 9-gap spec for pixel-perfect image reconstruction on won boards (unimplemented — ready to execute) |
| [TEST_GAP_ANALYSIS.md](TEST_GAP_ANALYSIS.md) | Test gap analysis: health by category, coverage table, prioritised action plan (counts updated 2026-05-13) |
| [TEST_HARDENING_PLAN.md](TEST_HARDENING_PLAN.md) | Forensic test hardening plan — 25-file audit, 17 GWHARDEN hardening items, verification commands |
| [BACKLOG.md](BACKLOG.md) | Context-preserving backlog — PERF-000 (WinAnimation._idx) is the current blocking implementation task |
| [gameplay_visual_improvement_ideas.md](gameplay_visual_improvement_ideas.md) | 9-gap analysis of solved board vs. source image with per-gap code sketches and prioritized roadmap |

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
    ├── BUGS.md
    ├── PERFORMANCE_PLAN.md
    ├── ZOOM_OUT_PERFORMANCE_REPORT.md
    ├── REMEDIATION_PLAN_VERIFICATION.md
    ├── FORENSIC_VISUAL_RECONSTRUCTION_ANALYSIS.md
    ├── BACKLOG.md
    ├── TEST_GAP_ANALYSIS.md
    ├── TEST_HARDENING_PLAN.md
    └── gameplay_visual_improvement_ideas.md
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

*Gameworks v0.1.3 — part of the Mine-Streaker project.*
