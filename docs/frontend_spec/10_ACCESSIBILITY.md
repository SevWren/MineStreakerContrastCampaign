# Module: Accessibility Specification

WCAG 2.1 AA compliance target. All features usable without vision,
without mouse, and without time pressure.

---

## 10.1 Visual Accessibility

### Colorblind Modes

| Mode | Implementation |
|---|---|
| **Deuteranopia** (red-green) | Shift palette to blue/orange. Numbers use WBHM (White, Blue, Yellow, Magenta) scheme. |
| **Protanopia** (red-blind) | Same as deuteranopia but with higher luminance contrast. |
| **Tritanopia** (blue-yellow) | Use red/green/white differentiators. |
| **None** (default) | Standard number colors from `ThemeConfig.numberColors`. |

**Enforcement**: Color is NEVER the only differentiator. Every cell also
uses: (a) numbers for revealed cells, (b) flag shape for flagged cells,
(c) mine symbol for revealed mines, (d) X overlay for wrong flags.

### High Contrast Mode

- All cell borders become 2px solid white
- Numbers rendered in white with black outline
- Ghost overlay disabled by default (can re-enable)
- Focus indicators are 3px dashed yellow

### Cell Size

Configurable: 16px (compact, expert), 24px (default), 32px (comfortable),
48px (accessibility). Default for `easy` difficulty is 32px.

---

## 10.2 Motor Accessibility

### Full Keyboard Navigation

```
Tab / Shift+Tab    Navigate between cells (grid order, left→right, top→bottom)
Arrow keys         Navigate within board (N/E/S/W)
Enter / Space      Reveal current cell
F                  Flag/unflag current cell
C                  Chord current cell (if valid)
H                  Use hint
Z / Ctrl+Z         Undo
G                  Toggle ghost image overlay
Escape             Surrender / close modal / pause
```

### Focus Management

- Board cells receive visible focus ring (3px dashed, high-contrast color)
- Focus starts on cell (0,0) when game begins
- After each action, focus stays on acted cell (or shifts to result modal)
- Tab from board goes to Control Panel, then TopBar, then footer

### Touch Accessibility

- Minimum tap target: 44×44px (WCAG 2.5.8)
- Long press (>500ms) on cell = flag
- Double-tap on revealed number = chord
- Swipe left/right to navigate between cells (optional enhancement)

### One-Handed Mode

Settings toggle: "One-click mode"
- Left-click/tap = toggle flag (mines are dangerous cells)
- Separate "Reveal All Safe" button reveals all logically safe cells at once

---

## 10.3 Screen Reader Support

### ARIA Roles and Labels

```html
<div role="grid" aria-label="Minesweeper board, 32 by 32, 150 mines">
  <!-- Each row -->
  <div role="row" aria-rowindex="1">
    <!-- Each cell -->
    <div role="gridcell"
         aria-label="Cell A1, unrevealed, not flagged"
         aria-describedby="cell-0-0">
    </div>
  </div>
</div>
```

### Live Regions

```html
<div aria-live="assertive" id="game-status">
  <!-- Announces every state change -->
  "Revealed cell B3: number 4. 147 mines remaining."
  "Flagged cell C5 as mine. 146 mines remaining."
  "Chain reveal: 23 cells opened."
  "Mine hit at D7. Game over."
  "Puzzle complete! Score: 2,840. Four stars."
</div>

<div aria-live="polite" id="timer-status">
  "Time: 2 minutes 34 seconds elapsed."
</div>
```

### Screen Reader Announcements

| Event | Announcement |
|---|---|
| Game starts | "New game. 32 by 32 board. 150 mines. Ghost image visible." |
| Cell revealed | "Cell B3. Number 4. 147 mines remaining." |
| Cell flagged | "Cell D5 flagged as mine. 149 mines remaining." |
| Flag removed | "Cell D5 unflagged. 149 mines remaining." |
| Chain reveal | "Chain reveal. 23 cells opened." |
| Mine hit | "Mine hit! Game over." |
| Win | "Puzzle complete! Score 2,840. Four stars. Perfect score!" |
| Hint used | "Hint: Cell F2 is safe and has been revealed." |
| Undo | "Undo. Last action reverted: reveal at C4." |
| Timer warning (if <2min) | "2 minutes remaining." |

---

## 10.4 Cognitive Accessibility

### Tutorial

- First-time users see a step-by-step overlay tutorial
- 6 steps covering: upload, difficulty, reveal, flag, review, score
- Can be re-accessed from Settings → "Replay Tutorial"
- Each step has "Skip" and "Next" controls

### Tooltips

- Hovering any number cell shows: "This cell touches N mines"
- Hovering any button shows action description
- Hovering game state shows explanation

### Progress Visibility

- Mine counter always visible (how many mines found / total)
- Score counter updates in real-time
- Timer always visible when active
- Completion percentage shown (cells resolved / total)

### Undo Forgiveness

- Unlimited undos on Easy difficulty
- Generous undo limits on other difficulties
- Score penalty is small enough to not discourage experimentation

---

## 10.5 Auditory Accessibility

- All sound effects have visual equivalents (screen flash for mine hit, etc.)
- Sound is off by default (opt-in in Settings)
- Volume independent of system volume (internal slider)
- Caption/describe sounds in screen reader announcements ("Explosion sound: mine hit")

---

## 10.6 Keyboard Shortcuts Reference

```
╔══════════════════════════════════════════════════════════╗
║  MINESTREAKER — KEYBOARD SHORTCUTS                      ║
╠══════════════════════════════════════════════════════════╣
║  Navigation                                             ║
║  Tab            Next cell                                ║
║  Shift+Tab      Previous cell                            ║
║  Arrow keys     Navigate grid                            ║
║  Ctrl+G         Jump to gallery                          ║
║  Ctrl+L         Jump to leaderboard                      ║
║                                                              ║
║  Actions                                                ║
║  Enter/Space    Reveal current cell                       ║
║  F              Flag/unflag current cell                  ║
║  C              Chord on current cell                     ║
║  H              Use hint                                  ║
║  Z / Ctrl+Z     Undo last action                          ║
║  Ctrl+N         New game                                  ║
║  Ctrl+R         Retry current board                       ║
║                                                              ║
║  Display                                               ║
║  G              Toggle ghost image                        ║
║  M              Toggle mine counter                       ║
║  S              Toggle score display                      ║
║  Escape         Close modal / Surrender                   ║
║  ?              Open shortcuts help                       ║
╠══════════════════════════════════════════════════════════╣
║  All shortcuts visible on Settings page                  ║
║  Customizable in future versions                         ║
╚══════════════════════════════════════════════════════════╝
```
```

---

## 11. Test Specification — `tests/`

```
tests/
├── unit/
│   ├── board-engine.test.ts      # Cell logic, flood-fill, win check
│   ├── state-machine.test.ts     # All transitions, guard evaluation
│   ├── scoring-engine.test.ts    # Score calculation, edge cases
│   ├── hint-engine.test.ts       # Constraint propagation
│   ├── undo-engine.test.ts       # Stack behavior, depth limits
│   └── renderer.test.ts          # Canvas calls (mocked context)
├── integration/
│   ├── game-controller.test.ts   # Action flow, state coordination
│   └── api-client.test.ts        # Request/response mapping
└── e2e/
    └── game-flow.test.ts         # Full game simulation
```

## Unit Test Matrix

### board-engine.test.ts
```
✓ New board has all cells HIDDEN
✓ getCell returns null for out-of-bounds
✓ getNeighbors returns exactly 3 for corner cells
✓ getNeighbors returns exactly 5 for edge cells
✓ getNeighbors returns exactly 8 for interior cells
✓ revealCell on hidden safe cell → REVEALED_SAFE
✓ revealCell on hidden mine cell → REVEALED_MINE (mine_hit)
✓ revealCell on already-revealed cell → already_revealed
✓ revealCell on flagged cell → unflags, then reveals
✓ revealCell(0) → chain_reveal, floods connected zeros
✓ flood-fill never reveals mine cells
✓ toggleFlag hidden→flagged increments correctFlagCount
✓ toggleFlag hidden→flagged increments wrongFlagCount for safe cells
✓ toggleFlag flagged→hidden decrements correct/wrong counters
✓ toggleFlag on revealed cell → invalid_flag
✓ chordCell with matching flags → reveals hidden neighbors
✓ chordCell with mismatched flags → chord_mismatch
✓ chordCell on hidden cell → invalid_chord
✓ chordCell on zero cell → invalid_chord
✓ chord reveals mine → chord_mine_hit
✓ isWinCondition: true when all mines flagged and all safes revealed
✓ isWinCondition: false when one mine unflagged
✓ isWinCondition: false when one safe unrevealed
✓ toSnapshot: serializes all cell states
✓ restoreSnapshot: restores exact state including counters
✓ restoreSnapshot: correctly counts flags/mines/revealed
```

### state-machine.test.ts
```
✓ IDLE → BOARD_GENERATING (always allowed)
✓ BOARD_GENERATING → READY (when board present)
✓ BOARD_GENERATING → IDLE (when board is null)
✓ READY → PLAYING (on hasFirstClick)
✓ READY → BOARD_GENERATING (on playerInitiated)
✓ PLAYING → WON (when all correctly resolved)
✓ PLAYING → FAILED (on contradiction)
✓ PLAYING → READY (on surrender)
✓ WON → REVIEW (always)
✓ WON → READY (on playerInitiated)
✓ FAILED → REVIEW (always)
✓ FAILED → READY (on playerInitiated)
✓ REVIEW → WON (back to parent)
✓ REVIEW → FAILED (back to parent)
✗ PLAYING → IDLE rejected (no valid rule)
✗ IDLE → PLAYING rejected (must generate board first)
✗ Same-state transition is silent no-op (success: true)
✓ transitionLog records every transition with timestamp and reason
✓ onTransition listener fires on state change
✓ canTransitionTo returns correct boolean
```

### scoring-engine.test.ts
```
✓ Perfect game: 100% accuracy, no hints, no undos → 4 stars
✓ Good game: 95% accuracy, 1 hint → 3 stars
✓ Average game: 75% accuracy → 2 stars
✓ Poor game: 50% accuracy → 1 star
✓ Terrible game: <50% → 0 stars
✓ Easy difficulty multiplier: 0.5×
✓ Expert difficulty multiplier: 4.0×
✓ Time bonus: fast completion → 1.5×
✓ Time bonus: slow completion → 0.5× (floor)
✓ No-hint bonus: 1.2× when zero hints
✓ Hint penalty: scales with hint count
✓ Undo penalty: 1% per undo
✓ Undo penalty floor: 0.5× (50% or more penalties)
✓ Zero cells, zero mines → no division by zero
✓ Accuracy calculation with wrong flags reduces score
```

### hint-engine.test.ts
```
✓ findSafeReveal: identifies forced safe cell
✓ findSafeReveal: returns null when no forced safe cell
✓ findFlagMine: identifies forced mine
✓ findFlagMine: returns null when no forced mine
✓ getBestHint: returns safe reveal before flag hint
✓ getBestHint: returns null when no deterministic move
✓ Hint reason is non-empty and descriptive
```

### undo-engine.test.ts
```
✓ Empty stack returns null on pop
✓ Push then pop restores exact board state
✓ Max depth enforced (oldest entries dropped)
✓ depth() returns correct count
✓ isEmpty returns correct boolean
✓ clear() empties the stack
✓ Multiple pushes maintain correct order (LIFO)
✓ Counters restored correctly after undo
```

## Integration Test — Full Game Simulation

```
1. Generate board from test image (32×32, seed=42)
2. Verify board dimensions and mine count match difficulty config
3. Verify solver can fully solve the board (all cells determinable)
4. Simulate optimal play:
   a. First click on (0,0) — must be safe
   b. Use hints to identify forced moves
   c. Reveal cells, chord when valid
   d. Flag all mines
   e. Verify isWinCondition() returns true
5. Verify final score matches manual calculation
6. Simulate failure:
   a. Flag a safe cell
   b. Reveal a mine
   c. Verify state → FAILED
   d. Verify wrong flags are visible
7. Simulate undo:
   a. Reveal cell, then undo
   b. Verify cell returns to HIDDEN
   c. Verify counters correct
8. Simulate replay:
   a. After win, retry same board
   b. Verify same solution (deterministic seed)
```

## E2E Test — Image-to-Board Pipeline

```
1. Upload test image (32×32 PNG)
2. Verify board generation completes < 2s
3. Verify SA loss < 0.01 (good convergence)
4. Verify solver succeeds (route_outcome_detail = "phase2_full_repair")
5. Start game with generated board
6. Play optimally (use solver to determine each move)
7. Verify win condition met
8. Verify reconstructed image visually matches original
9. Verify forensic rerun metrics:
   - removed_mines = 192
   - added_mines = 0
   - changed_cells = 192
   - solver_n_unknown_before = 37285
   - solver_n_unknown_after = 31540
   - accepted_count = 192
```
```

---

## 12. Master Index

All specification modules:

| # | File | Module | Lines |
|---|---|---|---|
| 00 | `00_PROJECT_STRUCTURE.md` | Project layout | ~80 |
| 01 | `01_TYPES.md` | Core types | ~280 |
| 02 | `02_BOARD_ENGINE.md` | Cell logic | ~230 |
| 03 | `03_STATE_MACHINE.md` | Phase transitions | ~130 |
| 04 | `04_SCORING_ENGINE.md` | Score calculation | ~120 |
| 05 | `05_HINT_ENGINE.md` | Constraint-based hints | ~80 |
| 06 | `06_UNDO_ENGINE.md` | Action stack + Renderer | ~300 |
| 07 | `07_GAME_CONTROLLER.md` | Orchestrator + API client | ~320 |
| 08 | `08_UI_COMPONENTS.md` | React component specs | ~400 |
| 09 | `09_GAME_FLOW.md` | Player journey + sequence | ~450 |
| 10 | `10_ACCESSIBILITY.md` | A11y + tests | ~350 |
| — | **Total** | | ~2,710 |

All files are in `docs/frontend_spec/` — one file per module, no cross-file fragmentation, no truncated functions.
```

---

## 13. Implementation Priority

### Sprint 1 — Core Game (2 weeks)
- [ ] `types/game.ts` — all types
- [ ] `engine/board-engine.ts` — cell logic
- [ ] `engine/state-machine.ts` — phase management
- [ ] Basic `CanvasBoard` with reveal/flag
- [ ] Basic `TopBar` with mine counter and timer

### Sprint 2 — Gameplay Features (2 weeks)
- [ ] `engine/scoring-engine.ts`
- [ ] `engine/undo-engine.ts`
- [ ] Chord support
- [ ] Win/fail detection and modals
- [ ] `engine/hint-engine.ts` + hint button

### Sprint 3 — Polish (1 week)
- [ ] `render/renderer.ts` — ghost overlay, animations
- [ ] Result overlay with comparison view
- [ ] Gallery component
- [ ] Leaderboard (localStorage)

### Sprint 4 — Accessibility & Testing (1 week)
- [ ] Keyboard navigation
- [ ] Screen reader support
- [ ] Colorblind modes
- [ ] Unit tests (all engine modules)
- [ ] E2E test (full game flow)

### Sprint 5 — Backend Integration (1 week)
- [ ] API client (`api/client.ts`)
- [ ] WebSocket progress updates
- [ ] Image upload and preprocessing
- [ ] End-to-end pipeline test

**Total estimated time: ~7 weeks (one developer)**
```</tool_call>}