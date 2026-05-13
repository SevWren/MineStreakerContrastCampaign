# Module: engine/hint-engine.ts

Uses constraint propagation on the current board state to find
deterministic moves the player can make with certainty.

Strategy: scan all revealed numbered cells.
  - If number === adjacent flags  → all hidden neighbors are SAFE (reveal)
  - If number − flags === hidden  → all hidden neighbors are MINES (flag)

Returns the first high-confidence hint found.
```typescript
import { BoardEngine } from './board-engine';
import { type Hint } from './board-engine';

// Re-export for convenience
export { Hint };

export class HintEngine {
  constructor(private board: BoardEngine) {}

  /**
   * Find one safe cell to reveal.
   * If a revealed cell's number equals its adjacent flag count,
   * all unflagged neighbors must be safe.
   */
  findSafeReveal(): Hint | null {
    for (let y = 0; y < this.board.height; y++) {
      for (let x = 0; x < this.board.width; x++) {
        const cell = this.board.getCell(x, y);
        if (!cell || cell.number === null || cell.number === 0) continue;

        const neighbors = this.board.getNeighbors(x, y);
        const flagged = neighbors
          .filter((c) => c.state === 'flagged_mine').length;
        const hidden = neighbors.filter(
          (c) => c.state === 'hidden' || c.state === 'flagged_mine'
        ).length;

        if (flagged === cell.number && hidden > flagged) {
          const target = neighbors.find((c) => c.state === 'hidden');
          if (target) {
            return {
              x: target.x,
              y: target.y,
              action: 'reveal',
              confidence: 1.0,
              reason: `Cell (${x},${y}) n=${cell.number}, ${flagged} flags match — remaining hidden cells are safe.`,
            };
          }
        }
      }
    }
    return null;
  }

  /**
   * Find one mine to flag.
   * If remaining mines === hidden neighbor count, all are mines.
   */
  findFlagMine(): Hint | null {
    for (let y = 0; y < this.board.height; y++) {
      for (let x = 0; x < this.board.width; x++) {
        const cell = this.board.getCell(x, y);
        if (!cell || cell.number === null || cell.number === 0) continue;

        const neighbors = this.board.getNeighbors(x, y);
        const flagged = neighbors
          .filter((c) => c.state === 'flagged_mine').length;
        const hidden = neighbors
          .filter((c) => c.state === 'hidden').length;
        const remaining = cell.number - flagged;

        if (remaining > 0 && remaining === hidden) {
          const target = neighbors.find((c) => c.state === 'hidden');
          if (target) {
            return {
              x: target.x,
              y: target.y,
              action: 'flag',
              confidence: 1.0,
              reason: `Cell (${x},${y}) needs ${remaining} mine(s), exactly ${hidden} hidden neighbor(s).`,
            };
          }
        }
      }
    }
    return null;
  }

  /** Return best available hint, or null if no deterministic move. */
  getBestHint(): Hint | null {
    return this.findSafeReveal() ?? this.findFlagMine();
  }
}
```