# Module: engine/game-controller.ts

Top-level orchestrator. Every game action flows through here.
The React component tree calls methods on this class.

```typescript
import { GameStateMachine } from './state-machine';
import { BoardEngine, DIRECTIONS } from './board-engine';
import { HintEngine } from './hint-engine';
import { UndoEngine } from './undo-engine';
import { calculateScore } from './scoring-engine';
import { GAME_PHASES, type GamePhase, type CellState, type GameAction } from '../types/game';

// ============================================================
// LISTENER INTERFACE
// ============================================================

export interface GameEvents {
  onPhaseChange?: (from: GamePhase, to: GamePhase, reason: string) => void;
  onCellAction?: (action: GameAction) => void;
  onScoreUpdate?: (score: number, stars: number) => void;
  onGameEnd?: (result: 'won' | 'failed' | 'surrendered', score: ReturnType<typeof calculateScore>) => void;
  onLog?: (message: string) => void;
}

// ============================================================
// GAME CONTROLLER
// ============================================================

export class GameController {
  readonly stateMachine = new GameStateMachine();
  board: BoardEngine | null = null;

  // Metrics
  private startTime: number | null = null;
  private hintsUsed = 0;
  private undosUsed = 0;

  // Externalized for difficulty configuration
  private difficulty: import('../types/game').Difficulty = 'medium';
  private maxHints: number = 3;
  private maxUndos: number = 10;
  private timerEnabled: boolean = true;

  // Undo — maxDepth set at game start based on difficulty
  private undoEngine: UndoEngine = new UndoEngine(-1);

  // Listeners
  private listeners: GameEvents = {};

  on(events: GameEvents): () => void {
    const prev = { ...this.listeners };
    this.listeners = { ...this.listeners, ...events };
    return () => { this.listeners = prev; };
  }

  // ============================================================
  // MAIN ENTRY POINT: Start a new game from a board solution
  // ============================================================

  /**
   * Initialize game with a pre-generated board solution.
   * Called when the backend returns a solved board.
   *
   * Does NOT start the timer — that happens on first click.
   */
  initGame(solution: import('../types/game').BoardSolution, difficulty: import('../types/game').Difficulty): void {
    this.difficulty = difficulty;
    this.board = new BoardEngine(solution);
    this.undoEngine = new UndoEngine(getMaxUndos(difficulty));
    this.maxHints = getMaxHints(difficulty);
    this.maxUndos = getMaxUndos(difficulty);
    this.timerEnabled = getTimerEnabled(difficulty);

    this.hintsUsed = 0;
    this.undosUsed = 0;
    this.startTime = null;

    const result = this.stateMachine.transition(GAME_PHASES.READY, {
      currentBoard: solution,
    });

    if (!result.success) {
      throw new Error(`Cannot init game: ${result.reason}`);
    }
  }

  // ============================================================
  // CELL ACTIONS
  // ============================================================

  /**
   * Player reveals a cell (left-click / tap).
   *
   * On first call, starts the game timer.
   * Returns the action result for the UI to animate.
   */
  revealCell(x: number, y: number): ActionResult | null {
    if (!this.board) return null;
    if (this.stateMachine.phase !== GAME_PHASES.READY
        && this.stateMachine.phase !== GAME_PHASES.PLAYING) {
      return null;
    }

    // First click → transition to PLAYING, start timer
    if (this.stateMachine.phase === GAME_PHASES.READY) {
      const result = this.stateMachine.transition(GAME_PHASES.PLAYING, {
        hasFirstClick: true,
        currentBoard: this.board.toSnapshot(),
      });
      if (!result.success) return null;
      this.startTime = Date.now();
      this.listeners.onLog?.('Game started — timer running');
    }

    // Save pre-action snapshot for undo
    const actionDesc = { type: 'reveal' as const, x, y, cellsChanged: [] as any[] };
    this.undoEngine.push(this.board, actionDesc);

    // Execute reveal
    const result = this.board.revealCell(x, y);

    if (!result.success) {
      this.undoEngine.pop(this.board); // revert undo entry on failure
      return result;
    }

    // Record action for listeners
    this._emitAction({
      type: 'reveal', x, y,
      cellsChanged: result.cellsChanged.length,
    });

    // Check win
    if (this.board.isWinCondition()) {
      this._endGame('won');
      return result;
    }

    // Mine hit = game over
    if (result.event === 'mine_hit') {
      this._endGame('failed');
      return result;
    }

    // Update score in real time
    this._emitScore();

    return result;
  }

  /** Player toggles a flag (right-click / long-press). */
  toggleFlag(x: number, y: number): ActionResult | null {
    if (!this.board) return null;
    if (this.stateMachine.phase !== GAME_PHASES.PLAYING) return null;

    this.undoEngine.push(this.board, { type: 'flag', x, y, cellsChanged: [] });
    const result = this.board.toggleFlag(x, y);

    if (!result.success) {
      this.undoEngine.pop(this.board);
      return result;
    }

    this._emitAction({ type: result.event === 'flagged' ? 'flag' : 'unflag', x, y, cellsChanged: 1 });
    this._emitScore();
    return result;
  }

  /** Player chords (middle-click / both clicks on a number). */
  chordCell(x: number, y: number): ActionResult | null {
    if (!this.board) return null;
    if (this.stateMachine.phase !== GAME_PHASES.PLAYING) return null;

    this.undoEngine.push(this.board, { type: 'chord', x, y, cellsChanged: [] });
    const result = this.board.chordCell(x, y);

    if (!result.success) {
      this.undoEngine.pop(this.board);
      return result;
    }

    this._emitAction({
      type: 'chord', x, y,
      cellsChanged: result.cellsChanged.length,
    });

    if (this.board.isWinCondition()) {
      this._endGame('won');
      return result;
    }

    if (result.event === 'chord_mine_hit') {
      this._endGame('failed');
      return result;
    }

    this._emitScore();
    return result;
  }

  // ============================================================
  // HINTS
  // ============================================================

  /**
   * Use a hint. Reveals a safe cell or flags a mine.
   * Consumes one of the limited hint budget.
   * Returns null if no hints available or none needed.
   */
  useHint(): { x: number; y: number; action: 'reveal' | 'flag' } | null {
    if (!this.board) return null;
    if (this.stateMachine.phase !== GAME_PHASES.PLAYING) return null;
    if (this.maxHints >= 0 && this.hintsUsed >= this.maxHints) return null;

    const engine = new HintEngine(this.board);
    const hint = engine.getBestHint();
    if (!hint) return null;

    // Save undo state
    this.undoEngine.push(this.board, {
      type: 'hint',
      x: hint.x,
      y: hint.y,
      cellsChanged: [],
    });

    if (hint.action === 'reveal') {
      const result = this.board.revealCell(hint.x, hint.y);
      this.hintsUsed++;

      this._emitAction({ type: 'hint', x: hint.x, y: hint.y, cellsChanged: result.cellsChanged.length });

      if (this.board.isWinCondition()) this._endGame('won');
      else if (result.event === 'mine_hit') this._endGame('failed');
      else this._emitScore();
    } else {
      this.board.toggleFlag(hint.x, hint.y);
      this.hintsUsed++;

      this._emitAction({ type: 'hint', x: hint.x, y: hint.y, cellsChanged: 1 });
      this._emitScore();
    }

    return { x: hint.x, y: hint.y, action: hint.action };
  }

  // ============================================================
  // UNDO
  // ============================================================

  /** Undo the last player action. Returns the undone action or null. */
  undo(): GameAction | null {
    if (!this.board) return null;
    if (this.undoEngine.isEmpty) return null;

    const undone = this.undoEngine.pop(this.board);
    if (!undone) return null;

    this.undosUsed++;
    this._emitAction({ type: 'undo', x: undone.x, y: undone.y, cellsChanged: undone.cellsChanged.length });
    this._emitScore();

    return undone;
  }

  // ============================================================
  // SURRENDER
  // ============================================================

  /** Player gives up. Reveals entire board. No score penalty. */
  surrender(): void {
    if (!this.board || this.stateMachine.phase !== GAME_PHASES.PLAYING) return;

    // Reveal all cells
    for (let y = 0; y < this.board.height; y++) {
      for (let x = 0; x < this.board.width; x++) {
        const cell = this.board.getCell(x, y);
        if (!cell) continue;
        if (cell.state === 'hidden') {
          cell.state = cell.owner === 'mine' ? 'revealed_mine' : 'revealed_safe';
        }
        if (cell.state === 'wrong_flag') {
          cell.state = 'revealed_mine';
        }
      }
    }

    this._endGame('surrendered');
  }

  // ============================================================
  // GAME END
  // ============================================================

  /**
   * Calculate final score given elapsed seconds.
   * If no timer, elapsedSeconds is ignored.
   */
  calculateFinalScore(elapsedSeconds: number): ReturnType<typeof calculateScore> {
    if (!this.board) throw new Error('No board');

    return calculateScore({
      boardWidth: this.board.width,
      boardHeight: this.board.height,
      mineCount: this.board.mineCount,
      correctFlagCount: this.board.getCorrectFlagCount(),
      wrongFlagCount: this.board.getWrongFlagCount(),
      revealedSafeCount: this.board.getRevealedSafeCount(),
      difficulty: this.difficulty,
      elapsedSeconds,
      hintsUsed: this.hintsUsed,
      undosUsed: this.undosUsed,
    });
  }

  // ============================================================
  // PRIVATE HELPERS
  // ============================================================

  private _endGame(result: 'won' | 'failed' | 'surrendered'): void {
    const from = this.stateMachine.phase;
    const target = result === 'won' ? GAME_PHASES.WON : GAME_PHASES.FAILED;

    this.stateMachine.transition(target, { contradiction: result === 'failed' });
    this.listeners.onGameEnd?.(result, this.calculateFinalScore(this._elapsed()));
  }

  private _elapsed(): number {
    if (!this.startTime) return 0;
    return (Date.now() - this.startTime) / 1000;
  }

  private _emitAction(action: GameAction): void {
    this.listeners.onCellAction?.(action);
  }

  private _emitScore(): void {
    if (!this.board) return;
    const elapsed = this._elapsed();
    const score = calculateScore({
      boardWidth: this.board.width,
      boardHeight: this.board.height,
      mineCount: this.board.mineCount,
      correctFlagCount: this.board.getCorrectFlagCount(),
      wrongFlagCount: this.board.getWrongFlagCount(),
      revealedSafeCount: this.board.getRevealedSafeCount(),
      difficulty: this.difficulty,
      elapsedSeconds: elapsed,
      hintsUsed: this.hintsUsed,
      undosUsed: this.undosUsed,
    });
    this.listeners.onScoreUpdate?.(score.finalScore, score.starRating);
  }
}

// ============================================================
// DIFFICULTY HELPERS
// ============================================================

function getMaxHints(d: import('../types/game').Difficulty): number {
  return { easy: -1, medium: 3, hard: 1, expert: 0 }[d];
}

function getMaxUndos(d: import('../types/game').Difficulty): number {
  return { easy: -1, medium: 10, hard: 3, expert: 1 }[d];
}

function getTimerEnabled(d: import('../types/game').Difficulty): boolean {
  return { easy: false, medium: true, hard: true, expert: true }[d];
}
```

## Controller Rules (Summary)

| Action | Phase Guard | Side Effects |
|---|---|---|
| `revealCell` | PLAYING or READY (first click) | Starts timer, may trigger win/fail |
| `toggleFlag` | PLAYING only | Updates mine counter |
| `chordCell` | PLAYING only | May cascade, may trigger win/fail |
| `useHint` | PLAYING, hints remaining | Consumes hint, updates score |
| `undo` | PLAYING, undo stack not empty | Reverts board, penalizes score |
| `surrender` | PLAYING only | Reveals all cells, ends game with no penalty |
| `solve` | — | Shows full solution (review mode only) |
```

---

# Module: api/client.ts

```typescript
import { type BoardSolution } from '../types/game';

// ============================================================
// API CLIENT
// ============================================================

export interface BoardGenRequest {
  readonly image_url: string;
  readonly image_data?: string;                // Base64 data URL (takes priority)
  readonly board_width: number;
  readonly board_height: number;
  readonly difficulty: string;                  // 'easy' | 'medium' | 'hard' | 'expert'
  readonly seed?: number;
  readonly timeout_seconds?: number;            // Default 120
}

export interface BoardGenResponse {
  readonly status: 'success' | 'failed' | 'cancelled';
  readonly board?: BoardSolution;
  readonly error?: {
    readonly code: string;
    readonly message: string;
    readonly details?: Record<string, unknown>;
  };
  readonly metrics?: {
    readonly generation_time_ms: number;
    readonly sa_final_loss: number;
    readonly solver_passed: boolean;
    readonly route_summary: {
      readonly selected_route: string;
      readonly route_result: string;
      readonly route_outcome_detail: string;
      readonly solver_n_unknown_before: number;
      readonly solver_n_unknown_after: number;
    };
  };
}

export interface HintRequest {
  readonly board_state: any;                    // Serialized board
  readonly hint_type: 'reveal' | 'flag';
}

export interface HintResponse {
  readonly hint: {
    readonly x: number;
    readonly y: number;
    readonly action: 'reveal' | 'flag';
    readonly confidence: number;
    readonly reason: string;
  } | null;
}

// ============================================================
// WebSocket Messages (backend → frontend)
// ============================================================

export type BackendMessage =
  | { type: 'progress'; data: { phase: string; progress: number } }
  | { type: 'board_ready'; data: BoardSolution }
  | { type: 'error'; data: { code: string; message: string } }
  | { type: 'hint_result'; data: HintResponse['hint'] };

// ============================================================
// REST API
// ============================================================

export async function generateBoard(
  request: BoardGenRequest,
  onProgress?: (phase: string, pct: number) => void,
): Promise<BoardGenResponse> {
  // Option A: REST (simple, no progress streaming)
  const resp = await fetch('/api/v1/board/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return resp.json();

  // Option B: WebSocket for progress updates
  // (implementation depends on backend WebSocket endpoint)
}

export async function getHint(request: HintRequest): Promise<HintResponse> {
  const resp = await fetch('/api/v1/hint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });
  return resp.json();
}

export async function getLeaderboard(difficulty?: string): Promise<LeaderboardEntry[]> {
  const url = difficulty
    ? `/api/v1/leaderboard?difficulty=${difficulty}`
    : '/api/v1/leaderboard';
  const resp = await fetch(url);
  return resp.json();
}

export async function submitScore(entry: LeaderboardEntry): Promise<void> {
  await fetch('/api/v1/leaderboard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(entry),
  });
}
```

---

# Module: api/board-gen.ts

```typescript
// ============================================================
// BOARD GENERATION REQUEST/RESPONSE
//
// Frontend representation of the backend contract.
// Maps to pipeline.py / sa.py / solver.py / repair.py.
// ============================================================

import { type BoardSolution } from '../types/game';

// Maximum generation timeout by difficulty
export const GENERATION_TIMEOUTS = {
  easy:   30_000,    // 30s
  medium: 60_000,    // 60s
  hard:   120_000,   // 2min
  expert: 300_000,   // 5min
} as const;

// Generation phases (for progress indicator)
export type GenPhase = 'coarse' | 'fine' | 'refine1' | 'refine2' | 'refine3' | 'solving';

export interface GenProgress {
  readonly phase: GenPhase;
  readonly progress: number;    // 0–100
}

// Backend-to-frontend mapper
export function mapBackendSolution(data: any): BoardSolution {
  return {
    width: data.board_width,
    height: data.board_height,
    totalCells: data.board_width * data.board_height,
    mineCount: data.mine_count,
    safeCount: data.safe_count,
    grid: data.grid.map((c: any) => ({
      x: c.x,
      y: c.y,
      owner: c.is_mine ? 'mine' : 'safe',
      number: c.clue_number ?? 0,
    })),
    thumbnail: data.thumbnail_url ?? '',
    generationTimeMs: data.generation_time_ms,
    saLoss: data.sa_loss ?? 0,
    seed: data.seed ?? 0,
  };
}
```
```</tool_call>}