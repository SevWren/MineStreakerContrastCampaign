# MineStreaker: Frontend Architecture & Game Logic Specification v1.0

**Status**: Complete specification — ready for implementation
**Target**: React 18 + TypeScript + Canvas 2D
**Backend contract**: `pipeline.py` + `solver.py` + `sa.py` + `core.py` + `repair.py`
**Companion doc**: `GAME_DESIGN.md` (product/UX overview)

---

## Project Structure

```
src/
├── types/
│   ├── game.ts              # Core types — single source of truth
│   └── api.ts               # API contract types
├── engine/
│   ├── state-machine.ts     # Deterministic state machine
│   ├── board-engine.ts      # Cell logic, reveal, flag, flood-fill
│   ├── scoring-engine.ts    # Pure score calculation
│   ├── hint-engine.ts       # Solver-driven hint generation
│   ├── undo-engine.ts       # Action stack and undo system
│   └── animation-engine.ts  # Timeline and easing
├── render/
│   ├── renderer.ts          # Canvas main draw loop
│   └── layers/
│       ├── grid-layer.ts    # Grid lines and borders
│       ├── ghost-layer.ts   # Source image overlay
│       ├── cell-layer.ts    # Cell backgrounds
│       ├── flag-layer.ts    # Flag rendering
│       ├── number-layer.ts  # Number glyphs
│       └── effect-layer.ts  # Reveal/explosion animations
├── ui/
│   ├── components/
│   │   ├── GameShell.tsx         # Layout container
│   │   ├── CanvasBoard.tsx       # Canvas + event binding
│   │   ├── ControlPanel.tsx      # Upload, difficulty, buttons
│   │   ├── TopBar.tsx            # Score, timer, mine counter, stars
│   │   ├── ResultOverlay.tsx     # Win/fail overlay with comparison
│   │   ├── ComparisonView.tsx    # Original vs reconstruction
│   │   ├── Gallery.tsx           # Built-in image presets
│   │   ├── Leaderboard.tsx       # Score rankings
│   │   ├── Tutorial.tsx          # First-time onboarding
│   │   └── Settings.tsx          # Sound, theme, accessibility
│   ├── hooks/
│   │   ├── useGameState.ts      # Zustand reactive store
│   │   ├── useCanvas.ts         # Canvas ref and resize
│   │   ├── useInput.ts          # Mouse, touch, keyboard
│   │   ├── useTimer.ts          # Countdown / countup
│   │   └── useSound.ts          # Audio playback
│   └── state/
│       ├── store.ts              # Global Zustand store
│       └── selectors.ts          # Memoized derived selectors
├── api/
│   ├── client.ts                 # WebSocket + REST transport
│   └── board-gen.ts              # Board gen request/response
├── assets/
│   ├── images/                   # Default image library
│   ├── sounds/                   # SFX files
│   └── fonts/                    # Custom monospace font
├── utils/
│   ├── geometry.ts               # Coordinate and neighbor math
│   ├── image-processing.ts       # Client-side image prep
│   ├── animation.ts              # Easing curves
│   └── persistence.ts            # LocalStorage save/load
├── App.tsx
├── main.tsx
└── index.css
```

Each file below is self-contained with complete, compilable TypeScript. No ellipses. No `// rest of code`. Every function terminates properly.