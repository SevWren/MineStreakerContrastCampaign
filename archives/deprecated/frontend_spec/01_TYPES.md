# Module: types/game.ts

Single source of truth for ALL game types. Nothing is defined elsewhere.

```typescript
// ============================================================
// CELL STATES — 5 values, exhaustive, no others exist
// ============================================================

export const CELL_STATES = {
  HIDDEN:        'hidden',
  REVEALED_SAFE: 'revealed_safe',
  FLAGGED_MINE:  'flagged_mine',
  REVEALED_MINE: 'revealed_mine',
  WRONG_FLAG:    'wrong_flag',
} as const;

export type CellState =
  | 'hidden'
  | 'revealed_safe'
  | 'flagged_mine'
  | 'revealed_mine'
  | 'wrong_flag';

// ============================================================
// CELL OWNERS — 2 values
// ============================================================

export type CellOwner = 'mine' | 'safe';

// ============================================================
// CELL DATA
// ============================================================

export interface CellData {
  readonly x: number;
  readonly y: number;
  readonly owner: CellOwner;
  readonly number: number;  // 0–8 (mine cells use 0)
}

export interface MutableCell extends CellData {
  state: CellState;
}

export interface RenderedCell extends CellData {
  state: CellState;
  isHovered: boolean;
  isAnimating: boolean;
  animationProgress: number;   // 0.0 → 1.0
  imageColor?: string;
}

// ============================================================
// BOARD
// ============================================================

export interface BoardSolution {
  readonly width: number;
  readonly height: number;
  readonly totalCells: number;
  readonly mineCount: number;
  readonly safeCount: number;
  readonly grid: CellData[];        // Row-major: grid[y * width + x]
  readonly thumbnail: string;       // Data URL preview
  readonly generationTimeMs: number;
  readonly saLoss: number;
  readonly seed: number;
}

export interface BoardStateSnapshot {
  readonly width: number;
  readonly height: number;
  readonly cells: Array<{
    readonly x: number;
    readonly y: number;
    readonly state: CellState;
  }>;
  readonly timestamp: number;
}

// ============================================================
// GAME PHASES — 7 states, exhaustive
//
//           IDLE
//            │
//            ▼
//     BOARD_GENERATING
//        │          │
//        ▼          ▼
//      READY       IDLE  (cancel/fail)
//        │
//        ▼ (first click)
//      PLAYING
//      │    │     │
//      ▼    ▼     ▼
//    WON  FAILED  READY  (surrender)
//      │     │
//      ▼     ▼
//    REVIEW  REVIEW
//      │     │
//      ▼     ▼
//   (back to WON or FAILED)
// ============================================================

export const GAME_PHASES = {
  IDLE:             'idle',
  BOARD_GENERATING: 'board_generating',
  READY:            'ready',
  PLAYING:          'playing',
  WON:              'won',
  FAILED:           'failed',
  REVIEW:           'review',
} as const;

export type GamePhase =
  | 'idle'
  | 'board_generating'
  | 'ready'
  | 'playing'
  | 'won'
  | 'failed'
  | 'review';

// ============================================================
// DIFFICULTY — 4 tiers, each fully specified
// ============================================================

export const DIFFICULTY_LEVELS = {
  EASY:   'easy',
  MEDIUM: 'medium',
  HARD:   'hard',
  EXPERT: 'expert',
} as const;

export type Difficulty = 'easy' | 'medium' | 'hard' | 'expert';

export interface DifficultyConfig {
  readonly gridWidth: number;
  readonly gridHeight: number;
  readonly mineDensity: number;
  readonly timer: boolean;
  readonly timerMultiplier: number;
  readonly maxHints: number;          // −1 = unlimited
  readonly maxUndos: number;          // −1 = unlimited
  readonly undoPenaltyPercent: number;
  readonly hintScorePenalty: number;
  readonly difficultyMultiplier: number;
}

// ============================================================
// PLAYER ACTIONS — 7 types
// ============================================================

export type ActionType =
  | 'reveal'
  | 'flag'
  | 'unflag'
  | 'chord'
  | 'hint'
  | 'undo'
  | 'surrender';

export interface GameActionBase {
  readonly type: ActionType;
  readonly x: number;
  readonly y: number;
  readonly timestamp: number;
}

export interface RevealAction extends GameActionBase {
  readonly type: 'reveal';
  readonly cellsRevealed: Array<{
    readonly x: number;
    readonly y: number;
    readonly state: CellState;
  }>;
}

export interface FlagAction extends GameActionBase {
  readonly type: 'flag' | 'unflag';
  readonly previousState: CellState;
}

export interface ChordAction extends GameActionBase {
  readonly type: 'chord';
  readonly cellsRevealed: Array<{
    readonly x: number;
    readonly y: number;
    readonly state: CellState;
  }>;
}

export interface HintAction extends GameActionBase {
  readonly type: 'hint';
  readonly hintType: 'reveal' | 'flag';
}

// ============================================================
// SCORING
// ============================================================

export interface ScoreResult {
  readonly rawScore: number;
  readonly finalScore: number;
  readonly starRating: 0 | 1 | 2 | 3 | 4;
  readonly isPerfect: boolean;
  readonly breakdown: {
    readonly accuracyScore: number;
    readonly difficultyMultiplier: number;
    readonly timeBonus: number;
    readonly accuracyBonus: number;
    readonly noHintBonus: number;
    readonly undoPenalty: number;
  };
}

// ============================================================
// RENDERING
// ============================================================

export interface RenderConfig {
  readonly cellSize: number;
  readonly ghostOpacity: number;
  readonly showNumbers: boolean;
  readonly colorBlindMode: boolean;
  readonly highContrast: boolean;
  readonly animationSpeed: number;   // 0.0 (instant) → 1.0 (slow)
}

export interface ThemeConfig {
  readonly hiddenColor: string;
  readonly hiddenHoverColor: string;
  readonly revealedColor: string;
  readonly flagColor: string;
  readonly wrongFlagColor: string;
  readonly mineColor: string;
  readonly gridColor: string;
  readonly gridLineColor: string;
  readonly numberColors: readonly [
    string, string, string, string,
    string, string, string, string    // Index 0 = number 1
  ];
  readonly backgroundColor: string;
}

// ============================================================
// LEADERBOARD / COLLECTION
// ============================================================

export interface LeaderboardEntry {
  readonly id: string;
  readonly playerName: string;
  readonly score: number;
  readonly stars: number;
  readonly difficulty: Difficulty;
  readonly timeMs: number;
  readonly accuracy: number;       // 0.0 – 1.0
  readonly hintsUsed: number;
  readonly undosUsed: number;
  readonly imageHash: string;
  readonly seed: number;
  readonly timestamp: number;
}

export interface CollectionEntry {
  readonly imageHash: string;
  readonly imageName: string;
  readonly bestScores: Record<Difficulty, ScoreResult | null>;
  readonly completed: boolean;
  readonly firstCompletedAt: number | null;
}

// ============================================================
// EVENTS
// ============================================================

export type GameEventListener = (event: GameEvent) => void;

export interface GameEventBase {
  readonly type: string;
  readonly timestamp: number;
  readonly phase: GamePhase;
}

export interface PhaseChangeEvent extends GameEventBase {
  readonly type: 'phase_change';
  readonly from: GamePhase;
  readonly to: GamePhase;
  readonly reason: string;
}

export interface CellActionEvent extends GameEventBase {
  readonly type: 'cell_action';
  readonly action: ActionType;
  readonly cellsAffected: number;
  readonly coordinates: { readonly x: number; readonly y: number };
}

export interface ScoreUpdateEvent extends GameEventBase {
  readonly type: 'score_update';
  readonly currentScore: number;
  readonly stars: number;
}

export interface GameEndEvent extends GameEventBase {
  readonly type: 'game_end';
  readonly result: 'won' | 'failed' | 'surrendered';
  readonly finalScore: ScoreResult;
}

export type GameEvent =
  | PhaseChangeEvent
  | CellActionEvent
  | ScoreUpdateEvent
  | GameEndEvent;
```