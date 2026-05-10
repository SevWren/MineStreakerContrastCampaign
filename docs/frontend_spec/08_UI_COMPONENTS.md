# Module: ui/components — React Component Specifications

Every component's props, state, behavior, and rendering rules.
No implementation details omitted. No ambiguity.

---

## 8.1 GameShell.tsx

Layout container. Owns no game state — delegates everything to Zustand store.

**Responsibilities:**
- Render the top-level grid layout (canvas area | sidebar)
- Mount `store` context
- Handle window resize events

**Layout (desktop):**
```
+----------------------------------------------------------+
|  TopBar (score, timer, stars, mine counter)              |
+----------------------------------------------------------+
|                          |                               |
|   CanvasBoard            |   ControlPanel               |
|   (70% width)            |   (30% width)                |
|                          |   - Image upload             |
|                          |   - Difficulty picker        |
|                          |   - Ghost opacity slider     |
|                          |   - Hint / Undo / Surrender  |
|                          |   - Result modal trigger     |
|                          |                               |
+----------------------------------------------------------+
|  Footer: gallery link | settings | leaderboard          |
+----------------------------------------------------------+
```

**Layout (mobile, < 768px):**
- Canvas full width
- Control panel collapses below canvas
- Single-column flow

**Props:** `none` (reads from Zustand store)

**State:** `none` (dumb shell)

---

## 8.2 CanvasBoard.tsx

Wraps the `<canvas>` element. Handles DOM events and pipes them into the game controller.

**Responsibilities:**
- Create and size `<canvas>` element
- Bind mouse/touch/keyboard events
- Drive the render loop (`requestAnimationFrame`)
- Render ghost image overlay
- Show hover highlight on cursor position

**Props:**
```typescript
interface CanvasBoardProps {
  controller: GameController;    // Reference to game controller
  renderConfig: RenderConfig;    // Cell size, ghost opacity, etc.
  theme: ThemeConfig;            // Colors
  ghostImage: HTMLImageElement | null;
  onCellClick: (x: number, y: number, isRight: boolean) => void;
  onHover: (x: number, y: number | null) => void;
}
```

**Behavior:**
1. On `mousemove` → compute cell under cursor → call `onHover(x, y)` or `onHover(null)` if outside board.
2. On `click` → left button → `onCellClick(x, y, false)`.
3. On `contextmenu` → prevent default → `onCellClick(x, y, true)`.
4. On `touchstart` → if tap-and-hold > 500ms → flag; else → reveal.
5. On `dblclick` on revealed numbered cell → chord.
6. Keyboard: Tab navigates cells (arrow keys), Enter reveals, Space flags.
7. Render loop: `requestAnimationFrame` → clear canvas → call `renderer.render(...)`.

**Accessibility:**
- `role="grid"` on canvas wrapper
- `aria-label` on each cell via hidden DOM overlay or live region
- `aria-live="assertive"` announces cell state changes

---

## 8.3 ControlPanel.tsx

User controls panel. All inputs dispatch to Zustand store / game controller.

**Props:**
```typescript
interface ControlPanelProps {
  difficulty: Difficulty;
  onDifficultyChange: (d: Difficulty) => void;
  onImageUpload: (file: File) => void;
  onImageSelect: (preset: string) => void;    // Gallery preset
  onHint: () => void;
  onUndo: () => void;
  onSurrender: () => void;
  onNewGame: () => void;
  onRetry: () => void;
  ghostOpacity: number;
  onGhostOpacityChange: (v: number) => void;
  hintCount: number;          // Remaining hints
  hintMax: number;            // Max hints for current difficulty
  undoCount: number;          // Remaining undos
  undoMax: number;            // Max undos for current difficulty
  hasBoard: boolean;          // Whether a game is active
  isPlaying: boolean;         // Current phase === PLAYING
}
```

**Sections:**
1. **Image Input** — File upload (drag-and-drop + click), or gallery grid
2. **Difficulty Selector** — 4 radio buttons with grid dimensions shown
3. **Ghost Opacity** — Range slider 0–80%, live preview
4. **Action Buttons** — Hint (with remaining count), Undo (with count), Surrender
5. **New Game / Retry** — Context-sensitive label

**Validation:**
- Upload rejects non-image files (check MIME type).
- Max upload: 10MB.
- Image auto-resizes client-side to fit selected board dimensions before sending to backend.

---

## 8.4 TopBar.tsx

Persistent top-level status display.

**Props:**
```typescript
interface TopBarProps {
  score: number;
  stars: number;           // 0-4
  timer: string;           // Formatted MM:SS (or "—" if no timer)
  minesRemaining: number;  // Flagged / total
  isTimerRunning: boolean;
  difficulty: Difficulty;
}
```

**Rendering:**
```
[★ 847]  [🕐 04:32]  [💣 12/?]  [⚙️ difficulty=HARD]
```

**Behavior:**
- Stars render as filled/empty star icons. 4th star (✨) glows when perfect.
- Timer counts up from 00:00 (no timer if difficulty === 'easy').
- Mine counter: `correctFlags / totalMines`. Updates on every flag toggle.

---

## 8.5 ResultOverlay.tsx

Modal overlay for win/fail/surrender.

**Props:**
```typescript
interface ResultOverlayProps {
  result: 'won' | 'failed' | 'surrendered';
  score: ScoreResult;
  imageA: HTMLImageElement | string;   // Original
  imageB: HTMLImageElement | string;   // Reconstruction (flags + revealed cells)
  onClose: () => void;
  onRetry: () => void;
  onNewImage: () => void;
  onShare: () => void;
}
```

**Layout:**
```
+---------------------------------------------+
|            ✅ PUZZLE COMPLETE! 🎉            |
|  Score: 2,840  ★★★★ Perfect!               |
|  Time: 03:45   Hints: 0   Undos: 0          |
|---------------------------------------------|
|  ┌──────────┐   ┌──────────┐                |
|  | Original |   | Solution |                |
|  |  image   |   |  board   |                |
|  └──────────┘   └──────────┘                |
|---------------------------------------------|
|  [🔄 Retry] [🖼 New Image] [📤 Share] [X]  |
+---------------------------------------------+
```

**Modes:**
- `won`: Green theme, celebration animation, share button enabled.
- `failed`: Red theme, shows all mines, "Retry" button.
- `surrendered`: Gray theme, shows full solution, no score penalty note.

**ComparisonView:** Side-by-side or slider comparison between original image and the mine/reveal pattern. Slider mode lets user drag to see before/after.

---

## 8.6 Gallery.tsx

Built-in image presets organized by category.

**Props:**
```typescript
interface GalleryProps {
  onSelect: (imageUrl: string) => void;
  presets: GalleryItem[];
}

interface GalleryItem {
  id: string;
  name: string;
  url: string;
  thumbnail: string;
  category: 'landscape' | 'portrait' | 'abstract' | 'text' | 'pattern' | 'pixel_art';
  suggestedDifficulty: Difficulty;
  aspectRatio: number;   // width/height
}
```

**Behavior:**
- Grid of thumbnails, filterable by category.
- Hover shows image name and suggested difficulty.
- Click triggers `loadImage` flow.
- Default library: 20+ curated images.

---

## 8.7 Leaderboard.tsx

Score rankings. Supports local (Storage) and server leaderboard.

**Props:**
```typescript
interface LeaderboardProps {
  entries: LeaderboardEntry[];
  difficulty: Difficulty;
  onDifficultyChange: (d: Difficulty) => void;
  currentUserScore?: LeaderboardEntry;   // Highlight player's entry
}
```

**Rendering:**
- Table with rank, name, score, stars, time, date.
- Current player entry highlighted if in viewport.
- Pagination (top 100).
- Filter by difficulty.

---

## 8.8 Tutorial.tsx

First-time onboarding walkthrough.

**Behavior:**
- Shown once (dismissible via localStorage flag `tutorial_completed`).
- Step-by-step overlay highlighting UI elements.
- 6 steps: Upload, Difficulty, Play, Flag, Review, Score.
- Skippable at any step.

**Props:**
```typescript
interface TutorialProps {
  onComplete: () => void;
  onSkip: () => void;
  step: number;               // Current step (1-6)
  highlightedElement: string; // CSS selector of highlighted element
  tooltip: string;            // Instruction text
}
```

---

## 8.9 Settings.tsx

Preferences modal.

**Options:**
- Sound effects: on/off, volume slider
- Music: on/off (if implemented)
- Colorblind mode: off / deuteranopia / protanopia / tritanopia
- High contrast: on/off
- Ghost image opacity
- Cell size: small / medium / large
- Language selector (i18n placeholder)

**Persistence:** All settings saved to `localStorage` under `minestreaker_settings`.

---

## 8.10 Zustand Store — `state/store.ts`

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface GameStore {
  // State
  phase: GamePhase;          // Current game phase
  score: number | null;      // Current score
  stars: number;             // Current star rating
  elapsedSeconds: number;    // Timer value
  hintsUsed: number;
  undosUsed: number;
  difficulty: Difficulty;
  board: BoardSolution | null;
  hoveredCell: { x: number; y: number } | null;
  ghostOpacity: number;
  colorBlindMode: 'none' | 'deuteranopia' | 'protanopia' | 'tritanopia';
  highContrast: boolean;
  settings: SettingsState;

  // Actions
  startNewGame: (imageUrl: string, difficulty: Difficulty) => Promise<void>;
  revealCell: (x: number, y: number) => void;
  toggleFlag: (x: number, y: number) => void;
  chordCell: (x: number, y: number) => void;
  useHint: () => void;
  undo: () => void;
  surrender: () => void;
  retry: () => void;
  goToReview: () => void;
  backFromReview: () => void;
  setGhostOpacity: (v: number) => void;
  setDifficulty: (d: Difficulty) => void;
  updateSettings: (partial: Partial<SettingsState>) => void;
  resetGame: () => void;
}

interface SettingsState {
  soundEnabled: boolean;
  soundVolume: number;
  colorBlindMode: 'none' | 'deuteranopia' | 'protanopia' | 'tritanopia';
  highContrast: boolean;
  animationSpeed: number;
  showNumbers: boolean;
}

export const useGameStore = create<GameStore>()(
  persist(
    (set, get) => ({
      // -- Initial state --
      phase: 'idle',
      score: null,
      stars: 0,
      elapsedSeconds: 0,
      hintsUsed: 0,
      undosUsed: 0,
      difficulty: 'medium',
      board: null,
      hoveredCell: null,
      ghostOpacity: 0.3,
      colorBlindMode: 'none',
      highContrast: false,
      settings: {
        soundEnabled: true,
        soundVolume: 0.7,
        colorBlindMode: 'none',
        highContrast: false,
        animationSpeed: 0.5,
        showNumbers: true,
      },

      // -- Actions --
      startNewGame: async (imageUrl, difficulty) => {
        set({ phase: 'board_generating', difficulty, board: null, score: null });
        try {
          const resp = await fetch('/api/v1/board/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              image_url: imageUrl,
              difficulty,
            }),
          });
          const data = await resp.json();
          if (data.status !== 'success') throw new Error(data.error?.message);
          const board = data.board;
          set({ board, phase: 'ready' });
        } catch (e) {
          set({ phase: 'idle' });
          throw e;
        }
      },

      revealCell: (x, y) => {
        // Delegates to GameController
        const store = get();
        if (store.phase !== 'playing' && store.phase !== 'ready') return;
        // ... controller call
      },

      // ... remaining actions wired to GameController

      updateSettings: (partial) =>
        set((s) => ({
          settings: { ...s.settings, ...partial },
        })),

      resetGame: () =>
        set({
          phase: 'idle',
          score: null,
          stars: 0,
          elapsedSeconds: 0,
          hintsUsed: 0,
          undosUsed: 0,
          board: null,
          hoveredCell: null,
        }),
    }),
    {
      name: 'minestreaker-game',
      partialize: (state) => ({
        difficulty: state.difficulty,
        ghostOpacity: state.ghostOpacity,
        settings: state.settings,
      }),
    }
  )
);
```

---

## 8.11 Component Rendering Order (React Tree)

```
<App>
├── <ThemeProvider theme={resolvedTheme}>
│   ├── <GameProvider>  ← Zustand store context
│   │   ├── <GameShell>
│   │   │   ├── <TopBar>
│   │   │   │   ├── <StarRating stars={} />
│   │   │   │   ├── <Timer elapsed={} running={} />
│   │   │   │   ├── <MineCounter remaining={} />
│   │   │   │   └── <DifficultyBadge difficulty={} />
│   │   │   │
│   │   │   ├── <CanvasBoard>
│   │   │   │   └── <canvas ref />
│   │   │   │
│   │   │   ├── <ControlPanel>
│   │   │   │   ├── <ImageUploader />
│   │   │   │   ├── <DifficultySelector />
│   │   │   │   ├── <GhostSlider />
│   │   │   │   ├── <HintButton />
│   │   │   │   ├── <UndoButton />
│   │   │   │   └── <SurrenderButton />
│   │   │   │
│   │   │   └── <ResultOverlay open={phase in ['won','failed','surrendered']}>
│   │   │       ├── <ComparisonView original={} solution={} />
│   │   │       ├── <ScoreBreakdown score={} />
│   │   │       └── <ActionButtons onRetry onNewImage onShare />
│   │   │
│   │   ├── <Leaderboard>
│   │   ├── <Gallery>
│   │   ├── <Tutorial />
│   │   └── <Settings />
│   │
│   └── <ToastContainer />  ← For transient notifications
└── <Analytics />           ← Optional telemetry
```
```</tool_call>}