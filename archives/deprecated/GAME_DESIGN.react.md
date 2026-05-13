# MineStreaker: Image-Reconstruction Minesweeper

## Game Design Document v1.0

**Classification**: Full product specification — not a prototype sketch  
**Scope**: Front-end game logic, rendering pipeline, state machine, scoring, progression, accessibility, long-term architecture  
**Backend contract**: `pipeline.py` + `solver.py` + `sa.py` + `core.py` (existing)  
**Frontend contract**: React/Canvas SPA consuming the `GameAPI` (defined in `GAME_API.md`)

---

## 1. Core Concept

The player provides an image. The system generates a Minesweeper board whose **mine placement, when correctly flagged and revealed, reconstructs the original image**. The game is won when the player has flagged every mine such that the revealed cell pattern matches the source image.

This is **not** a Minesweeper variant. This is an **image reconstruction puzzle** that uses Minesweeper mechanics as the interaction layer.

**Key insight**: The mines ARE the image. Correctly flagging a mine reveals a dark pixel. Correctly identifying a safe cell reveals a light pixel. The number clues guide the player toward the correct flag pattern.

---

## 2. Game State Machine

```
                    ┌──────────────────────────────────────────┐
                    │                                          │
                    ▼                                          │
[IDLE] ──image_load──▶ [BOARD_GENERATING] ──board_ready──▶ [READY]
                                                          │
                                                          │ player_first_click
                                                          ▼
              ┌──────────────────────────────────────────────┐
              │                                               │
              ▼                                               │
         [PLAYING] ◄── cell_reveal / cell_flag ──────────────┤
              │                                               │
              │ board_solved (all mines flagged correctly,    │
              │ all safe cells revealed, no contradictions)   │
              ▼                                               │
         [WON] ──────────────────────────────────────────────┤
              │                                               │
              │ board_failed (contradiction detected:         │
              │ revealed cell N conflicts with all remaining  │
              │ flag assignments)                             │
              ▼                                               │
         [FAILED] ───────────────────────────────────────────┘
              │
              │ retry_same_board
              ▼
         [READY] (same board, reset state)

         [READY] ──new_image──▶ [BOARD_GENERATING]
```

### State Definitions

| State | Allowed Actions | Transitions |
|---|---|---|
| **IDLE** | `load_image(url/file)`, `select_preset()` | → BOARD_GENERATING |
| **BOARD_GENERATING** | `cancel_generation()` | → READY (success), → IDLE (cancelled/failed) |
| **READY** | `start_game()`, `load_new_image()`, `adjust_difficulty()`, `retry_board()` | → PLAYING (first click triggers board reveal), → BOARD_GENERATING |
| **PLAYING** | `reveal_cell(x,y)`, `flag_cell(x,y)`, `chord_cell(x,y)`, `hint_request()`, `undo_last()`, `surrender()` | → WON, → FAILED, → READY (surrender) |
| **WON** | `review_board()`, `share_result()`, `retry_board()`, `load_new_image()` | → READY, → BOARD_GENERATING |
| **FAILED** | `review_board()`, `retry_board()`, `load_new_image()` | → READY, → BOARD_GENERATING |
| **REVIEW** (sub-state of WON/FAILED) | `navigate_reconstruction()`, `compare_pixels()`, `export_result()` | → same parent state |

---

## 3. Gameplay Mechanics

### 3.1 Cell States

Each cell has a **logical state** and a **visual state**:

| Logical State | Visual State | Description |
|---|---|---|
| `HIDDEN` | Covered (░) | Not yet interacted with |
| `FLAGGED` | Flagged (⚑) | Player believes this is a mine (= dark pixel) |
| `QUESTION` | Questioned (?) | Player is uncertain (optional advanced mode) |
| `REVEALED_SAFE` | Open, number shown | This cell is safe; number = adjacent mine count |
| `REVEALED_MINE` | Open, mine shown | Wrong flag or auto-revealed on failure |
| `WRONG_FLAG` | X over flag | Player flagged a safe cell — counts as error |

### 3.2 Board Layers

The board has **three conceptual layers** that the player sees simultaneously:

1. **Mine/Safe Layer**: Standard Minesweeper — mines = dark pixels, safe = light pixels
2. **Number Clue Layer**: Numbers indicate adjacent mine count (standard Minesweeper rules)
3. **Image Preview Layer (Ghost)**: Semi-transparent overlay of the target image, visible at reduced opacity to guide the player. **Toggleable.**

### 3.3 First-Click Guarantee

First click is ALWAYS safe (standard Minesweeper). The system generates the board, then if the first-click cell would be a mine, it regenerates or swaps that cell. This is non-negotiable UX.

### 3.4 Chording

If a revealed cell's number equals the count of adjacent flags, clicking it reveals all non-flagged adjacent cells. Standard Minesweeper behavior.

### 3.5 Win Condition

The game is won when ALL of the following are true:
1. Every cell that should be a mine (dark pixel) is flagged
2. Every cell that should be safe (light pixel) is revealed
3. No contradictions exist (no wrong flags, no wrong reveals)
4. All number clues are satisfied

**Verification**: The system compares the current flag/reveal pattern against the generated solution. No guessing required from the player — the board has a deterministic solution.

### 3.6 Loss Condition

The game is lost when:
1. Player reveals a mine cell directly (not flagged)
2. Player flags a safe cell and the system detects an irrecoverable contradiction
3. Player surrenders

---

## 4. Difficulty System

Difficulty modifies **three independent axes**:

### 4.1 Grid Size — Controls Resolution

| Difficulty | Board W×H | Approx Cells | Image Detail |
|---|---|---|---|
| Easy | 16×16 | 256 | Very low — chunky pixel art |
| Medium | 32×32 | 1,024 | Medium — recognizable shapes |
| Hard | 64×64 | 4,096 | High — detailed images |
| Expert | 100×100 | 10,000 | Photographic detail |

### 4.2 Mine Density — Controls Difficulty

| Difficulty | Mine Density | Approx Mines (32×32) |
|---|---|---|
| Easy | 10% | ~100 |
| Medium | 15% | ~150 |
| Hard | 20% | ~200 |
| Expert | 25% | ~250 |

### 4.3 Time Pressure — Controls Stress

| Difficulty | Timer | Failure Penalty |
|---|---|---|
| Easy | No timer | None |
| Medium | 2× estimated solve time | Score penalty |
| Hard | 1× estimated solve time | Score penalty + no hints |
| Expert | Countdown with visible timer | Hard score penalty |

### 4.4 Image Complexity Parameter

The SA parameters (`COARSE_ITERS`, `FINE_ITERS`, `REFINE_*_ITERS`) scale with difficulty. Easy uses fewer iterations (faster generation, slightly less faithful reconstruction). Expert uses maximum iterations.

---

## 5. Scoring System

### 5.1 Base Score Formula

```
score = (base_reconstruction_score × difficulty_multiplier × time_bonus × accuracy_bonus)
```

### 5.2 Component Breakdown

| Component | Formula | Max Value |
|---|---|---|
| **Base Reconstruction** | `(correctly_flagged_mines + correctly_revealed_safes) / total_cells` → 0-1 ratio | 1.0 |
| **Difficulty Multiplier** | Easy=0.5, Medium=1.0, Hard=2.0, Expert=4.0 | 4.0 |
| **Time Bonus** | `1.0 + (remaining_time / total_time) × 0.5` (if timed) | 1.5 |
| **Accuracy Bonus** | `1.0 + (1.0 - wrong_flags/total_flags) × 0.3` (zero wrong = 1.3 max) | 1.3 |
| **No-Hint Bonus** | ×1.2 if no hints used | 1.2 |

### 5.3 Star Rating

| Stars | Condition |
|---|---|
| ⭐ | Base score ≥ 0.5 |
| ⭐⭐ | Base score ≥ 0.75 |
| ⭐⭐⭐ | Base score ≥ 0.95, no wrong flags |
| ⭐⭐⭐ + PERFECT | 100% accuracy, no hints, completed within time |

### 5.4 Leaderboard Metrics

- Speed (time to solve)
- Accuracy (zero wrong flags)
- Score (composite)
- Streak (consecutive perfect solves)
- Collection (% of image library completed)

---

## 6. Frontend Architecture

### 6.1 Tech Stack

```
├── React 18+ (TypeScript)
├── Canvas API (2D) — primary rendering
├── Zustand — global game state
├── React Query — API caching
├── Tailwind CSS — layout/styling
├── Framer Motion — animations
├── Howler.js — sound effects
└── Vite — build tool
```

### 6.2 Component Hierarchy

```
<App>
├── <GameShell>
│   ├── <TopBar> (score, timer, difficulty, menu)
│   ├── <CanvasRenderer> (main game board)
│   │   ├── <GridLayer> (mine/safe reveal)
│   │   ├── <NumberLayer> (clue numbers)
│   │   ├── <FlagLayer> (flag rendering)
│   │   ├── <GhostImageLayer> (target image overlay, toggleable)
│   │   └── <SelectionOverlay> (hover/selection feedback)
│   ├── <ControlPanel>
│   │   ├── <ImageUploader>
│   │   ├── <DifficultySelector>
│   │   ├── <GhostOpacitySlider>
│   │   ├── <HintButton>
│   │   ├── <UndoButton>
│   │   └── <SurrenderButton>
│   ├── <ScorePanel> (live score, stars, accuracy)
│   └── <ResultModal> (Won / Failed / Review)
│       ├── <ReconstructionComparison> (side-by-side)
│       ├── <ShareButton>
│       └── <NextActionButtons>
├── <Leaderboard>
├── <CollectionGallery>
└── <SettingsModal>
```

### 6.3 Canvas Rendering Pipeline

The Canvas renderer draws in this order (bottom to top):

1. **Background grid** — alternating cell colors for readability
2. **Ghost image layer** — semi-transparent target image (configurable opacity 0-50%)
3. **Revealed safe cells** — light/white with number overlay
4. **Flag markers** — red flags on hidden cells
5. **Question marks** — optional, yellow markers
6. **Number clues** — dark text on revealed cells
7. **Selection highlight** — animated border on hovered cell
8. **Animation overlay** — reveal animations, flag drop animations

### 6.4 Cell Rendering Spec

```typescript
interface CellRenderSpec {
  x: number;           // pixel x
  y: number;           // pixel y
  size: number;        // cell size in px (canvas_size / board_dim)
  state: CellState;    // HIDDEN | FLAGGED | QUESTION | REVEALED_SAFE | REVEALED_MINE | WRONG_FLAG
  number: number | null; // 0-8 for revealed safe cells
  isHovered: boolean;
  isAnimating: boolean; // for reveal/flag animations
  imagePixel?: string;  // hex color from ghost layer (revealed cells only)
}
```

---

## 7. Game Flow — Step by Step

### Phase 1: Image Selection
1. Player uploads an image or selects from gallery
2. System validates image (resolution check, aspect ratio)
3. Player selects difficulty → determines board dimensions
4. Optional: player can adjust "ghost opacity" slider

### Phase 2: Board Generation (async)
1. Server receives image + difficulty parameters
2. `core.py::load_image_smart` converts image to target grid
3. `sa.py` runs simulated annealing optimization
4. `solver.py` validates solvability
5. If unsolvable → `pipeline.py` repair chain runs
6. Final board + solution returned to client
7. Loading animation shows generation progress

### Phase 3: Gameplay
1. Player sees covered board with ghost image overlay
2. First click guaranteed safe → reveals first cell(s)
3. Player left-clicks to reveal, right-clicks to flag
4. Numbers guide player toward mine positions
5. Ghost image helps player match pattern
6. Timer runs (if timed difficulty)
7. Hints available (limited uses):
   - Reveal one safe cell
   - Flag one confirmed mine
8. Undo: reverses last action (limited to N undos based on difficulty)

### Phase 4: Resolution
1. **Win**: All correct flags placed, all safe cells revealed
   - Full image is visible through revealed cells + flags
   - Celebration animation
   - Score calculated and displayed
   - Side-by-side comparison: original vs reconstruction
   - Share button (image export, URL)
2. **Loss**: Mine revealed or contradiction detected
   - All mines revealed (showing pattern)
   - Wrong flags marked with X
   - Score calculated (partial)
   - Retry button (same board) or New Image button
3. **Surrender**: Player gives up
   - Full solution shown
   - No score penalty (or minimal)
   - "View solution" mode with toggle between original and reconstruction

---

## 8. Hint System

Hints are a **limited resource**:

| Difficulty | Max Hints | Cost |
|---|---|---|
| Easy | Unlimited | None |
| Medium | 3 | Small score reduction |
| Hard | 1 | Significant score reduction |
| Expert | 0 | Not available |

Hint types:
1. **Reveal Safe Cell**: System reveals one confirmed safe cell (left-click equivalent)
2. **Flag Confirmed Mine**: System places one flag on a confirmed mine
3. **Region Highlight** (Medium+): Brief flash of a region that has determinable cells
4. **Constraint Display** (Expert only): Shows why a cell is determinable (intersecting constraints)

**Implementation**: Hints use the solver (in "hint mode") to find forced moves — cells where the constraint system determines the state unambiguously.

---

## 9. Undo System

Undo stack stores game actions:

```typescript
type GameAction = 
  | { type: 'reveal', x: number, y: number, previousState: CellState }
  | { type: 'flag', x: number, y: number, previousState: CellState }
  | { type: 'chord', x: number, y: number, revealed: Array<{x,y,state}> }
  | { type: 'hint', x: number, y: number, hintType: HintType };
```

Undo limit:
| Difficulty | Max Undos |
|---|---|
| Easy | Unlimited |
| Medium | 10 |
| Hard | 3 |
| Expert | 1 |

Undo is **not** free — it costs a small portion of the current score (1% per undo, capped at 20%).

---

## 10. Accessibility

### 10.1 Visual
- **Colorblind mode**: Flags use symbols (▲) not just color; numbers have high contrast
- **High contrast mode**: Larger number text, bolder cell borders
- **Ghost image**: Adjustable opacity (0-80%) with independent color inversion
- **Cell size**: Configurable minimum (16px–64px)
- **Screen reader support**: ARIA labels on every cell, live region for game state announcements

### 10.2 Motor
- **Keyboard navigation**: Tab between cells, Enter to reveal, Space to flag
- **One-click mode**: Left-click reveals safe cells only; flag mode toggle
- **Touch support**: Long-press to flag on mobile

### 10.3 Cognitive
- **Tutorial mode**: Step-by-step introduction for first-time players
- **Tooltip**: Hovering a number shows "This cell touches N mines"
- **Progressive difficulty**: Game suggests increasing difficulty after consecutive wins

---

## 11. Image Export & Sharing

### 11.1 Export Formats
1. **PNG**: Final board state (revealed + flagged cells) with ghost overlay
2. **Animated GIF**: Step-by-step reveal animation (all cells in order)
3. **Side-by-side**: Original image | Mine board | Reconstruction

### 11.2 Share URL
```
https://minestreaker.com/play/{image_hash}_{board_w}_{seed}
```
This URL reconstructs the exact same game (image + board generation are deterministic given seed).

---

## 12. Image Gallery & Collection

### 12.1 Built-in Library
- Curated set of 50+ test images (various difficulty characteristics)
- Categorized by: abstract, landscape, portrait, text, patterns
- Each image has a difficulty rating based on SA convergence metrics

### 12.2 Player Collection
- Track which images completed, at what difficulty, scores
- Badge system: "Solved 10 landscape puzzles", "Perfect Expert score", etc.
- Total completion percentage visible to player

---

## 13. Sound Design

| Event | Sound |
|---|---|
| Cell reveal (safe) | Soft click |
| Cell reveal (mine) | Explosion/buzz |
| Flag placement | Paper rustle |
| Flag removal | Paper rustle (reverse) |
| Win | Triumphant fanfare |
| Loss | Sad trombone |
| Hint used | Gentle chime |
| Level start | Whoosh/transition |

All sounds toggleable in settings.

---

## 14. Analytics & Telemetry

Track for game balance and UX improvement:
- Time per action (median, distribution)
- Wrong flag rate
- Hint usage rate
- Undo usage rate
- Win/loss ratio by difficulty
- Abandonment points (where players quit)
- Image difficulty ranking (actual vs predicted)

All telemetry is anonymous and opt-in.

---

## 15. Platform Support

| Platform | Rendering | Input |
|---|---|---|
| Desktop Chrome/Firefox/Safari | Canvas 2D | Mouse (left/right click) |
| Desktop Edge/Opera | Canvas 2D | Mouse |
| Mobile Safari (iOS 16+) | Canvas 2D | Touch |
| Mobile Chrome (Android 10+) | Canvas 2D | Touch |
| Tablet (any browser) | Canvas 2D | Touch + stylus |

No native app. PWA-capable (service worker for offline play with cached assets).

---

## 16. Security

- All game logic runs client-side (no server trust required for standard play)
- Image uploads are client-side only — never sent to server (unless player explicitly shares)
- Leaderboard submission is signed (anti-cheat)
- Rate limiting on leaderboard API (prevent spam)

---

## 17. Monetization (Optional / Future)

- **Free tier**: Standard gameplay, 50 image library, basic stats
- **Pro tier** ($2.99/month): Unlimited image uploads, advanced gallery, analytics, custom themes
- **One-time purchase**: Remove ads ($4.99)
- **Expansion packs**: Curated image collections (famous paintings, pets, landscapes)

---

## 18. Development Roadmap

### Phase 1 (MVP — 4–6 weeks)
- [ ] Core game: image upload → board generation → play → win/lose
- [ ] Canvas rendering: grid, numbers, flags, ghost overlay
- [ ] Basic scoring and star rating
- [ ] 10 built-in test images
- [ ] Undo (unlimited)
- [ ] No timer (casual mode only)

### Phase 2 (Polish — 2–3 weeks)
- [ ] Difficulty system (grid size + mine density)
- [ ] Timer mode (Medium/Hard)
- [ ] Hint system (Medium+)
- [ ] Sound effects
- [ ] Accessibility features (colorblind, keyboard nav)
- [ ] Mobile responsive layout

### Phase 3 (Social — 2–3 weeks)
- [ ] Shareable URLs
- [ ] Image export (PNG, GIF)
- [ ] Side-by-side comparison view
- [ ] Basic leaderboard (local storage first)
- [ ] Collection tracking

### Phase 4 (Scale — ongoing)
- [ ] Online leaderboard (server)
- [ ] Multiplayer (same puzzle, race to solve)
- [ ] Daily challenge (community puzzle)
- [ ] AI-assisted difficulty calibration
- [ ] Expansion packs
- [ ] PWA (offline play)

---

## 19. Technical Constraints

1. **Board generation must complete in <2 seconds** for 32×32, <10 seconds for 100×100. Display generation progress.
2. **Canvas must render at 60fps** during reveal animations.
3. **Memory**: Keep board state in compact typed arrays, not objects.
4. **Determinism**: Same image + seed + difficulty = same board (required for shareable URLs).
5. **Mobile**: Touch targets ≥44×44px. No hover-dependent UI.
6. **Board generation runs server-side** (computationally expensive for large boards). Client sends image + params, receives board state.

---

## 20. Integration with Existing Codebase

The existing MineStreaker pipeline (`run_iter9.py`, `core.py`, `sa.py`, `solver.py`, `pipeline.py`, `repair.py`) is the **backend board generation engine**. The game wraps it with:

1. **REST API layer** — expose board generation as HTTP endpoint
2. **WebSocket** — real-time generation progress updates
3. **Game state manager** — client-side state machine on top of board data
4. **Rendering engine** — Canvas-based visual layer
5. **Input handler** — mouse/touch/keyboard → game actions

No existing code is modified. The game communicates with the pipeline through a well-defined API contract (see `GAME_API.md`).