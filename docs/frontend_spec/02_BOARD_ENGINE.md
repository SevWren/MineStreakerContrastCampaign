# Module: engine/board-engine.ts

Deterministic game logic. No rendering, no side effects. Fully testable.

```typescript
import {
  type CellData,
  type MutableCell,
  type CellState,
  type CellOwner,
  type BoardSolution,
  type BoardStateSnapshot,
  CELL_STATES,
  CELL_OWNERS,
} from '../types/game';

// ============================================================
// RESULT TYPES
// ============================================================

export type ActionEvent =
  | 'invalid_cell'
  | 'already_revealed'
  | 'mine_hit'
  | 'safe_reveal'
  | 'chain_reveal'
  | 'flagged'
  | 'unflagged'
  | 'invalid_flag'
  | 'invalid_chord'
  | 'chord_mismatch'
  | 'chord_reveal'
  | 'chord_mine_hit';

export interface ActionResult {
  readonly success: boolean;
  readonly cellsChanged: Array<{
    readonly x: number;
    readonly y: number;
    readonly state: CellState;
  }>;
  readonly event: ActionEvent;
}

// ============================================================
// DIRECTIONS (8-connected neighbors)
// ============================================================

export const DIRECTIONS: readonly [number, number][] = [
  [0, -1],  // N
  [1, -1],  // NE
  [1,  0],  // E
  [1,  1],  // SE
  [0,  1],  // S
  [-1,  1], // SW
  [-1,  0], // W
  [-1, -1], // NW
];

// ============================================================
// BOARD CLASS
// ============================================================

export class BoardEngine {
  public readonly width: number;
  public readonly height: number;
  public readonly mineCount: number;
  public readonly totalSafeCells: number;

  private grid: MutableCell[];

  // Incremental counters — never rescanned
  private revealedSafeCount = 0;
  private flaggedCount = 0;
  private correctFlagCount = 0;
  private wrongFlagCount = 0;

  constructor(solution: BoardSolution) {
    this.width = solution.width;
    this.height = solution.height;
    this.mineCount = solution.mineCount;
    this.totalSafeCells = solution.width * solution.height - solution.mineCount;

    this.grid = solution.grid.map(
      (cell): MutableCell => ({
        x: cell.x,
        y: cell.y,
        owner: cell.owner,
        number: cell.number,
        state: CELL_STATES.HIDDEN,
      }),
    );
  }

  // ---- Accessors ----

  getCell(x: number, y: number): MutableCell | null {
    if (x < 0 || x >= this.width || y < 0 || y >= this.height) return null;
    return this.grid[y * this.width + x];
  }

  getNeighbors(x: number, y: number): MutableCell[] {
    const out: MutableCell[] = [];
    for (const [dx, dy] of DIRECTIONS) {
      const c = this.getCell(x + dx, y + dy);
      if (c) out.push(c);
    }
    return out;
  }

  // ---- Derived State (O(1)) ----

  getRevealedSafeCount(): number { return this.revealedSafeCount; }
  getFlaggedCount(): number { return this.flaggedCount; }
  getCorrectFlagCount(): number { return this.correctFlagCount; }
  getWrongFlagCount(): number { return this.wrongFlagCount; }
  getMinesRemaining(): number { return this.mineCount - this.correctFlagCount; }

  getHiddenCount(): number {
    return this.width * this.height
      - this.revealedSafeCount - this.flaggedCount - this.wrongFlagCount;
  }

  isWinCondition(): boolean {
    return this.correctFlagCount === this.mineCount
        && this.revealedSafeCount === this.totalSafeCells;
  }

  // ---- Actions ----

  /**
   * Reveal a cell. If number === 0, flood-fills to connected zeros.
   * Safe cells get state 'revealed_safe'. Mine cells get 'revealed_mine'.
   */
  revealCell(x: number, y: number): ActionResult {
    const cell = this.getCell(x, y);
    if (!cell) return NO;

    if (cell.state === CELL_STATES.REVEALED_SAFE
        || cell.state === CELL_STATES.REVEALED_MINE) {
      return NO;
    }

    if (cell.state === CELL_STATES.FLAGGED_MINE) {
      this._unflag(cell);
    }

    if (cell.owner === CELL_OWNERS.MINE) {
      cell.state = CELL_STATES.REVEALED_MINE;
      return {
        success: true,
        cellsChanged: [{ x, y, state: CELL_STATES.REVEALED_MINE }],
        event: 'mine_hit',
      };
    }

    cell.state = CELL_STATES.REVEALED_SAFE;
    this.revealedSafeCount++;

    const changed: Array<{ x: number; y: number; state: CellState }> = [
      { x, y, state: CELL_STATES.REVEALED_SAFE },
    ];

    if (cell.number === 0) {
      this._floodReveal(x, y, changed);
      return { success: true, cellsChanged: changed, event: 'chain_reveal' };
    }

    return { success: true, cellsChanged: changed, event: 'safe_reveal' };
  }

  /** Toggle flag on a hidden cell. 'hidden' <-> 'flagged_mine'. */
  toggleFlag(x: number, y: number): ActionResult {
    const cell = this.getCell(x, y);
    if (!cell || cell.state === CELL_STATES.REVEALED_SAFE) {
      return NO;
    }

    if (cell.state === CELL_STATES.FLAGGED_MINE) {
      this._unflag(cell);
      return {
        success: true,
        cellsChanged: [{ x, y, state: CELL_STATES.HIDDEN }],
        event: 'unflagged',
      };
    }

    // hidden -> flagged_mine
    cell.state = CELL_STATES.FLAGGED_MINE;
    this.flaggedCount++;
    if (cell.owner === CELL_OWNERS.MINE) {
      this.correctFlagCount++;
    } else {
      this.wrongFlagCount++;
    }

    return {
      success: true,
      cellsChanged: [{ x, y, state: CELL_STATES.FLAGGED_MINE }],
      event: 'flagged',
    };
  }

  /**
   * Chord: if number === adjacent flag count, reveal all
   * unflagged neighbors.
   */
  chordCell(x: number, y: number): ActionResult {
    const cell = this.getCell(x, y);
    if (!cell
        || cell.state !== CELL_STATES.REVEALED_SAFE
        || cell.number === null || cell.number === 0) {
      return NO;
    }

    const neighbors = this.getNeighbors(x, y);
    const flags = neighbors
      .filter((c) => c.state === CELL_STATES.FLAGGED_MINE).length;

    if (cell.number !== flags) {
      return { success: false, cellsChanged: [], event: 'chord_mismatch' };
    }

    const changed: Array<{ x: number; y: number; state: CellState }> = [];
    let hitMine = false;

    for (const nb of neighbors) {
      if (nb.state === CELL_STATES.HIDDEN) {
        const r = this.revealCell(nb.x, nb.y);
        changed.push(...r.cellsChanged);
        if (r.event === 'mine_hit') hitMine = true;
      }
    }

    return {
      success: true,
      cellsChanged: changed,
      event: hitMine ? 'chord_mine_hit' : 'chord_reveal',
    };
  }

  // ---- Private ----

  private _floodReveal(
    sx: number, sy: number,
    out: Array<{ x: number; y: number; state: CellState }>,
  ): void {
    const visited = new Set<string>();
    const queue: [number, number][] = [[sx, sy]];
    visited.add(`${sx},${sy}`);

    while (queue.length > 0) {
      const [cx, cy] = queue.shift()!;
      for (const nb of this.getNeighbors(cx, cy)) {
        const key = `${nb.x},${nb.y}`;
        if (visited.has(key)) continue;
        visited.add(key);

        if (nb.state !== CELL_STATES.HIDDEN
            && nb.state !== CELL_STATES.FLAGGED_MINE) {
          continue;
        }

        if (nb.state === CELL_STATES.FLAGGED_MINE) {
          this._unflag(nb);
        }

        if (nb.owner === CELL_OWNERS.SAFE) {
          nb.state = CELL_STATES.REVEALED_SAFE;
          this.revealedSafeCount++;
          out.push({ x: nb.x, y: nb.y, state: CELL_STATES.REVEALED_SAFE });
          if (nb.number === 0) {
            queue.push([nb.x, nb.y]);
          }
        }
        // Mines stay hidden
      }
    }
  }

  private _unflag(cell: MutableCell): void {
    cell.state = CELL_STATES.HIDDEN;
    this.flaggedCount--;
    if (cell.owner === CELL_OWNERS.MINE) this.correctFlagCount--;
    else this.wrongFlagCount--;
  }

  // ---- Serialization ----

  toSnapshot(): BoardStateSnapshot {
    return {
      width: this.width,
      height: this.height,
      cells: this.grid.map((c) => ({ x: c.x, y: c.y, state: c.state })),
      timestamp: Date.now(),
    };
  }

  restoreSnapshot(snap: BoardStateSnapshot): void {
    this.revealedSafeCount = 0;
    this.flaggedCount = 0;
    this.correctFlagCount = 0;
    this.wrongFlagCount = 0;

    for (const s of snap.cells) {
      const c = this.getCell(s.x, s.y);
      if (!c) continue;
      c.state = s.state;
      if (s.state === CELL_STATES.REVEALED_SAFE) this.revealedSafeCount++;
      if (s.state === CELL_STATES.FLAGGED_MINE) {
        this.flaggedCount++;
        if (c.owner === CELL_OWNERS.MINE) this.correctFlagCount++;
        else this.wrongFlagCount++;
      }
      if (s.state === CELL_STATES.WRONG_FLAG) this.wrongFlagCount++;
    }
  }
}

// ---- Constant for invalid/no-op results ----

const NO: ActionResult = { success: false, cellsChanged: [], event: 'invalid_cell' as ActionEvent };