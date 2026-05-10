# Module: engine/scoring-engine.ts

Pure function, zero side effects, fully deterministic. Same inputs => same outputs always.

```typescript
import { type Difficulty, type ScoreResult, type DifficultyConfig } from '../types/game';

// ============================================================
// DIFFICULTY CONFIGS
// ============================================================

const CONFIGS: Record<Difficulty, DifficultyConfig> = {
  easy: {
    gridWidth: 16, gridHeight: 16, mineDensity: 0.10,
    timer: false, timerMultiplier: 0,
    maxHints: -1, maxUndos: -1, undoPenaltyPercent: 0,
    hintScorePenalty: 0, difficultyMultiplier: 0.5,
  },
  medium: {
    gridWidth: 32, gridHeight: 32, mineDensity: 0.15,
    timer: true, timerMultiplier: 2.0,
    maxHints: 3, maxUndos: 10, undoPenaltyPercent: 1,
    hintScorePenalty: 0.02, difficultyMultiplier: 1.0,
  },
  hard: {
    gridWidth: 64, gridHeight: 64, mineDensity: 0.20,
    timer: true, timerMultiplier: 1.0,
    maxHints: 1, maxUndos: 3, undoPenaltyPercent: 1,
    hintScorePenalty: 0.05, difficultyMultiplier: 2.0,
  },
  expert: {
    gridWidth: 100, gridHeight: 100, mineDensity: 0.25,
    timer: true, timerMultiplier: 1.0,
    maxHints: 0, maxUndos: 1, undoPenaltyPercent: 1,
    hintScorePenalty: 0.08, difficultyMultiplier: 4.0,
  },
};

// ============================================================
// PARAMETERS
// ============================================================

export interface ScoringParams {
  readonly boardWidth: number;
  readonly boardHeight: number;
  readonly mineCount: number;
  readonly correctFlagCount: number;
  readonly wrongFlagCount: number;
  readonly revealedSafeCount: number;
  readonly difficulty: Difficulty;
  readonly elapsedSeconds: number;
  readonly hintsUsed: number;
  readonly undosUsed: number;
}

// ============================================================
// CALCULATE
// ============================================================

export function calculateScore(p: ScoringParams): ScoreResult {
  const cfg = CONFIGS[p.difficulty];
  const totalCells = p.boardWidth * p.boardHeight;
  const safeCells = totalCells - p.mineCount;

  // 1. Base accuracy: fraction of correctly resolved cells
  const resolved = p.correctFlagCount + p.revealedSafeCount;
  const accuracy = totalCells > 0 ? resolved / totalCells : 0;

  // 2. Difficulty multiplier
  const diffMult = cfg.difficultyMultiplier;

  // 3. Time bonus (1.0 base, up to 1.5 for fast, floor 0.5 for slow)
  let timeBonus = 1.0;
  if (cfg.timer && cfg.timerMultiplier > 0) {
    const estTime = safeCells * cfg.timerMultiplier;
    if (p.elapsedSeconds <= estTime) {
      timeBonus = 1.0 + (1.0 - p.elapsedSeconds / estTime) * 0.5;
    } else {
      timeBonus = Math.max(0.5, 1.0 - ((p.elapsedSeconds - estTime) / estTime) * 0.5);
    }
  }

  // 4. Flag precision bonus (1.0 worst → 1.3 perfect)
  const totalFlags = p.correctFlagCount + p.wrongFlagCount;
  const precision = totalFlags > 0 ? p.correctFlagCount / totalFlags : 1.0;
  const accBonus = totalFlags > 0 ? 1.0 + precision * 0.3 : 1.0;

  // 5. No-hint bonus (1.2 if zero hints, decays)
  const noHintBonus = p.hintsUsed === 0
    ? 1.2
    : Math.max(0.8, 1.0 - p.hintsUsed * cfg.hintScorePenalty);

  // 6. Undo penalty (1.0 if zero, floor 0.5)
  const undoPen = Math.max(0.5, 1.0 - p.undosUsed * (cfg.undoPenaltyPercent / 100));

  // Composite
  const raw = accuracy * diffMult * timeBonus * accBonus * noHintBonus * undoPen * 1000;
  const finalScore = Math.round(raw);

  // Stars: 0-3 + possible perfect 4th
  let stars: 0 | 1 | 2 | 3 | 4 = 0;
  if (accuracy >= 0.5)  stars = 1;
  if (accuracy >= 0.75) stars = 2;
  if (accuracy >= 0.95 && p.wrongFlagCount === 0) stars = 3;

  const isPerfect =
    stars === 3
    && p.hintsUsed === 0
    && p.undosUsed === 0
    && (!cfg.timer || p.elapsedSeconds <= safeCells * cfg.timerMultiplier);

  if (isPerfect) stars = 4;

  return {
    rawScore: Math.round(raw),
    finalScore,
    starRating: stars,
    isPerfect,
    breakdown: {
      accuracyScore: accuracy,
      difficultyMultiplier: diffMult,
      timeBonus,
      accuracyBonus: accBonus,
      noHintBonus,
      undoPenalty: undoPen,
    },
  };
}

export function getDifficultyConfig(d: Difficulty): DifficultyConfig {
  return CONFIGS[d];
}
```