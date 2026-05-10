# Module: engine/undo-engine.ts

Maintains a stack of board snapshots + action metadata.
Undo restores previous snapshot and returns the action that was undone.
Max depth is set per-difficulty via `DifficultyConfig.maxUndos`.

```typescript
import { BoardEngine } from './board-engine';

// ============================================================
// UNDO ENTRY
// ============================================================

export interface UndoEntry {
  readonly action: {
    readonly type: string;            // 'reveal' | 'flag' | 'unflag' | 'chord' | 'hint'
    readonly x: number;
    readonly y: number;
    readonly cellsChanged: Array<{
      readonly x: number;
      readonly y: number;
      readonly state: string;
    }>;
  };
  readonly snapshot: ReturnType<BoardEngine['toSnapshot']>;
  readonly timestamp: number;
}

// ============================================================
// UNDO ENGINE
// ============================================================

export class UndoEngine {
  private stack: UndoEntry[] = [];
  private maxDepth: number;

  /**
   * @param maxDepth  -1 = unlimited, 0+ = capped
   */
  constructor(maxDepth: number = -1) {
    this.maxDepth = maxDepth;
  }

  /**
   * Save current board state BEFORE executing an action.
   * Call this BEFORE mutate, not after.
   *
   * @param board    Current board (pre-action snapshot)
   * @param action   Description of the action about to happen
   */
  push(board: BoardEngine, action: UndoEntry['action']): void {
    const entry: UndoEntry = {
      action,
      snapshot: board.toSnapshot(),
      timestamp: Date.now(),
    };
    this.stack.push(entry);

    // Enforce max depth — drop oldest entries
    if (this.maxDepth >= 0 && this.stack.length > this.maxDepth) {
      this.stack = this.stack.slice(this.stack.length - this.maxDepth);
    }
  }

  /**
   * Pop most recent snapshot and restore board to pre-action state.
   * Returns the undone action for UI display (e.g., "Undid reveal at (3,4)").
   * Returns null if stack is empty.
   */
  pop(board: BoardEngine): UndoEntry['action'] | null {
    if (this.stack.length === 0) return null;
    const entry = this.stack.pop()!;
    board.restoreSnapshot(entry.snapshot);
    return entry.action;
  }

  get depth(): number { return this.stack.length; }
  get isEmpty(): boolean { return this.stack.length === 0; }

  /** Clear entire undo history (called on new game / board reset). */
  clear(): void {
    this.stack = [];
  }
}
```

## Undo Policy by Difficulty

| Difficulty | Max Undos | Penalty per Undo |
|---|---|---|
| Easy       | Unlimited | 0%               |
| Medium     | 10        | 1% of score      |
| Hard       | 3         | 1% of score      |
| Expert     | 1         | 1% of score      |

## Integration Rules

1. **Before every player action** (reveal, flag, chord, hint), call `undoEngine.push(board, actionDesc)`.
2. **Undo** pops the stack and restores. The controller then re-evaluates win/fail/score.
3. **Surrender** does NOT push to undo stack — there is nothing to undo after surrender.
4. **New game / retry** calls `undoEngine.clear()`.
5. **Chord actions** push ONE entry (the chord itself), but `cellsChanged` lists every cell that flipped. Undo restores ALL of them in one step.
6. **Hint actions** push an entry — undoing a hint reverts the cell to hidden.