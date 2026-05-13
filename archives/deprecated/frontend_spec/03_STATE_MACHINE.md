# Module: engine/state-machine.ts

Deterministic. Every transition rule is explicit. Guards in declaration order; first match wins.

```typescript
import { GamePhase, GAME_PHASES } from '../types/game';

// ============================================================
// TRANSITION CONTEXT
// ============================================================

export interface TransitionContext {
  readonly currentBoard?: unknown | null;     // BoardSolution when available
  readonly hasFirstClick?: boolean;            // First cell interaction
  readonly contradiction?: boolean;            // Game-ending contradiction
  readonly playerInitiated?: boolean;          // User-triggered
}

// ============================================================
// TRANSITION TABLE (8 rules, exhaustive)
// ============================================================

interface Rule {
  readonly from: readonly GamePhase[];
  readonly to: GamePhase;
  readonly guard: (ctx: TransitionContext) => boolean;
  readonly desc: string;
}

const RULES: readonly Rule[] = [
  // ---- IDLE ----
  { from: ['idle'],                    to: 'board_generating',   guard: () => true,                                desc: 'Image load initiated' },

  // ---- BOARD_GENERATING ----
  { from: ['board_generating'],        to: 'ready',              guard: (c) => c.currentBoard != null,            desc: 'Board generation succeeded' },
  { from: ['board_generating'],        to: 'idle',               guard: () => true,                                desc: 'Generation cancelled or failed' },

  // ---- READY ----
  { from: ['ready'],                   to: 'playing',            guard: (c) => c.hasFirstClick === true,          desc: 'First cell interaction' },
  { from: ['ready'],                   to: 'board_generating',   guard: (c) => c.playerInitiated === true,         desc: 'Retry or new image' },

  // ---- PLAYING ----
  { from: ['playing'],                 to: 'won',
    guard: (c) => {
      if (!c.currentBoard) return false;
      const b = c.currentBoard as { grid: Array<{ owner: string; state: string }> };
      return b.grid.every((cl) =>
        cl.owner === 'mine' ? cl.state === 'flagged_mine' : cl.state === 'revealed_safe'
      );
    },
    desc: 'All mines flagged, all safes revealed' },

  { from: ['playing'],                 to: 'failed',             guard: (c) => c.contradiction === true,          desc: 'Contradiction detected' },
  { from: ['playing'],                 to: 'ready',              guard: (c) => c.playerInitiated === true,         desc: 'Player surrendered' },

  // ---- WON ----
  { from: ['won'],                     to: 'review',             guard: () => true,                                desc: 'Enter review' },
  { from: ['won'],                     to: 'ready',              guard: (c) => c.playerInitiated === true,         desc: 'New game' },
  { from: ['won'],                     to: 'board_generating',   guard: (c) => c.playerInitiated === true,         desc: 'New image' },

  // ---- FAILED ----
  { from: ['failed'],                  to: 'review',             guard: () => true,                                desc: 'Enter review' },
  { from: ['failed'],                  to: 'ready',              guard: (c) => c.playerInitiated === true,         desc: 'Retry board' },
  { from: ['failed'],                  to: 'board_generating',   guard: (c) => c.playerInitiated === true,         desc: 'New image' },

  // ---- REVIEW -> parents ----
  { from: ['won'],                     to: 'review',             guard: () => true,                                desc: 'Open review from won' },
  { from: ['failed'],                  to: 'review',             guard: () => true,                                desc: 'Open review from failed' },
];

// ============================================================
// STATE MACHINE
// ============================================================

export class GameStateMachine {
  private _phase: GamePhase = 'idle';
  private readonly _listeners = new Set<(phase: GamePhase, prev: GamePhase, reason: string) => void>();
  private readonly _log: Array<{ from: GamePhase; to: GamePhase; ts: number; reason: string }> = [];

  get phase(): GamePhase { return this._phase; }

  /** Test without executing. */
  canTransitionTo(target: GamePhase, ctx: TransitionContext): boolean {
    return RULES.some((r) => r.from.includes(this._phase) && r.to === target && r.guard(ctx));
  }

  /**
   * Attempt a state transition.
   * Same-phase is a silent no-op.
   * Returns `{ success: true }` or `{ success: false, reason }`.
   */
  transition(target: GamePhase, ctx: TransitionContext = {}):
    { success: true } | { success: false; reason: string }
  {
    if (this._phase === target) return { success: true };

    for (const rule of RULES) {
      if (!rule.from.includes(this._phase)) continue;
      if (rule.to !== target) continue;

      if (rule.guard(ctx)) {
        const prev = this._phase;
        this._phase = target;
        this._log.push({ from: prev, to: target, ts: Date.now(), reason: rule.desc });
        this._notify(prev, target, rule.desc);
        return { success: true };
      }

      return { success: false, reason: `${this._phase} -> ${target} rejected: ${rule.desc}` };
    }

    return { success: false, reason: `No rule: ${this._phase} -> ${target}` };
  }

  getLog(): ReadonlyArray<{ readonly from: GamePhase; readonly to: GamePhase; readonly ts: number; readonly reason: string }> {
    return [...this._log];
  }

  onTransition(fn: (phase: GamePhase, prev: GamePhase, reason: string) => void): () => void {
    this._listeners.add(fn);
    return () => { this._listeners.delete(fn); };
  }

  private _notify(prev: GamePhase, cur: GamePhase, reason: string): void {
    this._listeners.forEach((fn) => fn(cur, prev, reason));
  }
}
```