# Module: Game Flow Specification

Complete step-by-step player journey. Every screen, every transition,
every edge case. No gaps.

---

## Phase 1: Landing (GAME_PHASES.IDLE)

**Player sees:**
- Hero section with tagline: "Turn any image into a Minesweeper puzzle"
- Upload area (drag-and-drop or click to browse)
- Gallery grid of preset images
- Difficulty selector (cards showing grid dimensions and mine density)

**Player actions:**
1. Uploads an image OR selects a gallery preset
2. Selects difficulty (Easy / Medium / Hard / Expert)
3. System validates image:
   - Must be a valid image (PNG, JPG, GIF, WebP)
   - Must be ≤ 10MB
   - Auto-crops to square if non-square
   - Preview thumbnail shown
4. Clicks "Generate Board"

**State transition:** `IDLE → BOARD_GENERATING`

---

## Phase 2: Board Generation (GAME_PHASES.BOARD_GENERATING)

**What happens:**
```
Frontend                          Backend
  │                                 │
  │── POST /api/v1/board/generate ─▶│
  │   { image_url, difficulty,     │
  │     board_width, board_height }│
  │                                 │
  │◀── WebSocket progress ──────────│
  │   { phase: "coarse", pct: 25 } │
  │   { phase: "fine", pct: 50 }   │
  │   { phase: "refine1", pct: 65 }│
  │   { phase: "refine2", pct: 80 }│
  │   { phase: "refining", pct: 95 }
  │   { phase: "solving" }         │
  │                                 │
  │◀── Response ────────────────────│
  │   { status: "success",         │
  │     board: { ... },            │
  │     metrics: { ... } }         │
```

**Player sees:**
- Progress bar with phase labels:
  "Optimizing layout (SA Coarse) → Refining details (SA Fine) → Polishing (Refine 1/2/3) → Validating board (Solver) → Ready!"
- Animated visualization of the SA process (optional: heatmap of mine probability)
- Generation time counter

**Outcomes:**
- **Success** → `BOARD_GENERATING → READY`
- **Failed** (SA didn't converge) → Retry prompt or fallback to lower iterations
- **Cancelled** → `BOARD_GENERATING → IDLE`

**On success, board data includes:**
```typescript
{
  width: 32,
  height: 32,
  mineCount: 150,
  grid: [
    { x: 0, y: 0, owner: "safe", number: 2 },
    { x: 1, y: 0, owner: "mine", number: 0 },
    // ... width × height entries
  ],
  thumbnail: "data:image/png;base64,...",
  generationTimeMs: 4235,
  saLoss: 0.003,
}
```

---

## Phase 3: Ready Screen (GAME_PHASES.READY)

**Player sees:**
- Fully covered board (all cells hidden, face-down)
- Semi-transparent ghost image overlay (the original image)
- Controls: Ghost opacity slider, Hint button, Undo button, Timer display
- Mine counter: `0 / 150` (flags placed / total mines)
- Score display: `—` (not yet started)
- Star rating: empty

**Ghost overlay rules:**
- Default opacity: 30%
- Toggleable: G key or Settings
- Player can adjust opacity (0–80%) via slider
- Ghost image is displayed at same grid resolution as the board

**First click rule:**
- The first click is ALWAYS safe
- If the first-clicked cell would be a mine, it's swapped to safe in generation
- This guarantee is enforced server-side

**State transition on first click:** `READY → PLAYING`

---

## Phase 4: Playing (GAME_PHASES.PLAYING)

### 4.1 Core Interactions

| Input | Action | Result |
|---|---|---|
| Left-click on hidden cell | `revealCell(x, y)` | Cell opens, shows number or triggers mine hit |
| Right-click on hidden cell | `toggleFlag(x, y)` | Cell flagged as mine (⚑) |
| Right-click on flagged cell | `toggleFlag(x, y)` | Flag removed |
| Both-click on revealed number | `chordCell(x, y)` | Reveals all unflagged neighbors if flag count matches |
| Middle-click on revealed number | `chordCell(x, y)` | Same as both-click |
| H key | `useHint()` | System reveals/flags one forced cell |
| Z / Ctrl+Z | `undo()` | Revert last action |
| G key | Toggle ghost | Show/hide image overlay |

### 4.2 Reveal Cascade (Flood Fill)

When revealing a cell with number === 0:
1. All 8-connected neighbors are revealed automatically
2. If ANY of those neighbors also have number === 0, the cascade continues recursively
3. This continues until all connected zero-cells and their borders are revealed
4. Mines adjacent to zero-regions are NOT auto-revealed

**Example cascade:**
```
Before click (0,0):       After click (0,0):
[?] [?] [?] [?]            [0] [1] [■] [?]
[?] [?] [?] [?]     →     [1] [2] [■] [?]
[?] [?] [?] [?]            [■] [■] [?] [?]

Where □ = revealed, ■ = mine (still hidden), [n] = number clue
```

### 4.3 Chording Rules

Chord is only valid when:
- Clicked cell is revealed AND numbered (not 0)
- Number of adjacent flags EQUAL to the cell's number
- There are adjacent hidden cells to reveal

If chord would reveal a mine → mine hit, game over.

### 4.4 Hint System

Hints are deterministic — they only reveal cells that are logically deducible:
1. If a revealed cell's number = adjacent flags → remaining hidden neighbors are safe
2. If a revealed cell needs N more mines and has exactly N hidden neighbors → all are mines

**Hint budget:**
| Difficulty | Max Hints | Score Penalty |
|---|---|---|
| Easy | Unlimited | None |
| Medium | 3 | 2% per hint |
| Hard | 1 | 5% per hint |
| Expert | 0 | Not available |

### 4.5 Undo System

Undo reverts the board to the state BEFORE the last action.
Applies to: reveal, flag, unflag, chord, hint.
Does NOT apply to: game start, surrender, new game.

**Undo budget:**
| Difficulty | Max Undos | Score Penalty |
|---|---|---|
| Easy | Unlimited | None |
| Medium | 10 | 1% per undo |
| Hard | 3 | 1% per undo |
| Expert | 1 | 1% per undo |

### 4.6 Score Tracking (During Play)

Score updates after every action:
```
score = accuracy × difficultyMultiplier × timeBonus
      × flagPrecisionBonus × noHintBonus × undoPenalty × 1000
```

Live display: Top bar shows current score, stars, timer.

### 4.7 Win Check

After EVERY action, check:
```
if (correctFlagCount === mineCount && revealedSafeCount === safeCellCount) → WON
```

### 4.8 Failure Check

After EVERY reveal:
```
if (cell.owner === 'mine' && cell.state === 'revealed_safe') → FAILED
if (chord would reveal mine) → FAILED
```

---

## Phase 5: Victory (GAME_PHASES.WON)

**Player sees:**
- Full board with mines correctly flagged (green flags)
- All safe cells revealed with number clues
- Celebration animation (confetti / particle burst)
- Score summary:
  ```
  Score: 2,840
  ★★★★ Perfect!
  Time: 03:45
  Hints: 0/3 used
  Undos: 1 used
  ```
- Side-by-side comparison:
  - Left: Original input image
  - Right: Reconstruction from flags + revealed cells
- Action buttons: Review, Retry, New Image, Share

### Image Reconstruction

The "reconstructed image" is generated from the solved board:
- Flagged cells (mines) → Dark pixel (value 0)
- Revealed safe cells → Light pixel (value mapped from number: 0=brightest, 8=darker)
- This creates a bitmap that should visually resemble the original input

### Share Functionality

Generates a URL:
```
https://minestreaker.com/play/{imageHash}_{width}_{seed}
```
Visiting this URL regenerates the exact same board (deterministic).

Also exports:
- PNG screenshot of final board
- Animated GIF of the solving process
- Score card image

---

## Phase 6: Failure (GAME_PHASES.FAILED)

**Player sees:**
- All mines revealed (💣 icons)
- Wrong flags marked with X (red overlay)
- Score breakdown (partial credit)
- "What went wrong" analysis:
  - "Mine hit at (12, 5)"
  - "Wrong flags: 3"
  - "Board was 87% complete"
- Options: Retry (same board), New Image

---

## Phase 7: Review (GAME_PHASES.REVIEW)

Post-game analysis mode. Accessible from WON or FAILED.

**Features:**
- Step-through replay of all actions
- Heatmap of difficulty (which cells were hardest)
- Constraint analysis: "This cell was determined by clues at (3,4) and (5,6)"
- Comparison slider: drag to compare original vs. reconstruction
- Export options

**Navigation:**
- Close review → returns to parent (WON or FAILED)
- "Learn" tab shows deduction chain for each move

---

## Edge Cases & Error Handling

### Generation Timeout
- If SA doesn't converge within timeout, return best-effort board
- Mark as `partial_convergence` in metrics
- Player sees warning: "Board generated with reduced quality"

### Unsatisfiable Image
- Very high contrast images may produce boards that the solver can't fully resolve
- Repair pipeline (Phase 2 + Last100) handles this automatically
- Metrics report repair route used

### Browser Tab Inactive
- Timer pauses when tab is not visible (use `document.visibilitychange`)

### Network Failure During Generation
- Show "Connection lost" with retry button
- Resume from last checkpoint if WebSocket reconnects

### Disconnection During Game
- Auto-save board state to localStorage every 10 actions
- On reload, restore to last saved state

### Mobile Keyboard
- Virtual keyboard appears for flag/undo shortcuts
- Touch mode: long-press = flag, tap = reveal
```

---

## End-to-End Sequence Diagram

```
Player                    Frontend                 Backend
  │                          │                        │
  │ 1. Upload image          │                        │
  │─────────────────────────>│                        │
  │                          │ 2. POST /generate      │
  │                          │───────────────────────>│
  │                          │                        │
  │                          │◀── WebSocket progress ─│
  │ 3. Watch progress bar    │   {coarse: 25%}        │
  │◀─────────────────────────│   {fine: 50%}          │
  │                          │   {refine: 80%}        │
  │                          │                        │
  │                          │◀── board_ready ────────│
  │                          │   {grid, solution}     │
  │ 4. See covered board     │                        │
  │◀─────────────────────────│                        │
  │                          │                        │
  │ 5. Click cell (2, 3)     │                        │
  │─────────────────────────>│ 6. revealCell(2,3)    │
  │                          │ 7. Update state        │
  │ 8. See cell revealed     │ 8. emitScore()        │
  │◀─────────────────────────│ 9. checkWin()         │
  │                          │                        │
  │  ... repeat for all cells ...                     │
  │                          │                        │
  │ 10. Last cell revealed   │ 11. checkWin() → true │
  │                          │ 12. state → WON        │
  │ 13. Victory screen!      │ 13. emitScore(final)   │
  │◀─────────────────────────│                        │
  │                          │                        │
  │ 14. Click "Share"        │ 15. Generate URL       │
  │─────────────────────────>│ 16. POST /share        │
  │                          │───────────────────────>│
  │◀── Shareable URL ────────│◀── Confirmation ──────│
```
```</tool_call>}