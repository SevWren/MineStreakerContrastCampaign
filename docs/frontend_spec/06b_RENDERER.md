# Module: render/renderer.ts

Canvas 2D renderer. Draws the complete board every frame via requestAnimationFrame.

```typescript
import { BoardEngine, DIRECTIONS } from '../engine/board-engine';
import {
  type CellState,
  type RenderedCell,
  type ThemeConfig,
  type RenderConfig,
  CELL_STATES,
  CELL_OWNERS,
} from '../types/game';

// ============================================================
// DEFAULT THEME
// ============================================================

const THEME: ThemeConfig = {
  hiddenColor:       '#2d3436',
  hiddenHoverColor:  '#636e72',
  revealedColor:     '#dfe6e9',
  flagColor:         '#d63031',
  wrongFlagColor:    '#fdcb6e',
  mineColor:         '#2d3436',
  gridColor:         '#1e272e',
  gridLineColor:     '#485460',
  numberColors: [
    '#0984e3', // 1 — blue
    '#00b894', // 2 — green
    '#d63031', // 3 — red
    '#6c5ce7', // 4 — purple
    '#e17055', // 5 — orange
    '#00cec9', // 6 — teal
    '#d63031', // 7 — red
    '#636e72', // 8 — gray
  ],
  backgroundColor: '#1e272e',
};

// ============================================================
// RENDER STATE
// ============================================================

export interface RenderState {
  readonly hoveredCell: { x: number; y: number } | null;
  readonly animProgress: Map<string, number>;  // "x,y" → 0.0..1.0
  readonly revealedCells: Set<string>;
}

// ============================================================
// RENDERER
// ============================================================

export class Renderer {
  private ctx: CanvasRenderingContext2D;
  private cellSize: number;
  private board: BoardEngine;
  private renderState: RenderState;

  constructor(canvas: HTMLCanvasElement, cellSize: number) {
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas 2D context unavailable');
    this.ctx = ctx;
    this.cellSize = cellSize;
    this.renderState = {
      hoveredCell: null,
      animProgress: new Map(),
      revealedCells: new Set(),
    };
  }

  /** Call when board instance changes (new game). */
  setBoard(board: BoardEngine): void {
    this.board = board;
    this.renderState.revealedCells.clear();
    this.renderState.animProgress.clear();
  }

  /** Main draw call — invoke on every frame. */
  render(
    ghostImage: HTMLImageElement | null,
    ghostOpacity: number,
    colorBlind: boolean,
    highContrast: boolean,
    hovered: { x: number; y: number } | null,
  ): void {
    const ctx = this.ctx;
    const W = this.board.width * this.cellSize;
    const H = this.board.height * this.cellSize;

    // --- Layer 0: Background ---
    ctx.fillStyle = THEME.backgroundColor;
    ctx.fillRect(0, 0, W, H);

    // --- Layer 1: Ghost Image ---
    if (ghostImage && ghostOpacity > 0) {
      ctx.save();
      ctx.globalAlpha = ghostOpacity;
      ctx.globalCompositeOperation = 'multiply';
      ctx.drawImage(ghostImage, 0, 0, W, H);
      ctx.restore();
    }

    // --- Layer 2: Grid Lines ---
    ctx.strokeStyle = THEME.gridLineColor;
    ctx.lineWidth = 0.5;
    for (let x = 0; x <= this.board.width; x++) {
      ctx.beginPath();
      ctx.moveTo(x * this.cellSize + 0.5, 0);
      ctx.lineTo(x * this.cellSize + 0.5, H);
      ctx.stroke();
    }
    for (let y = 0; y <= this.board.height; y++) {
      ctx.beginPath();
      ctx.moveTo(0, y * this.cellSize + 0.5);
      ctx.lineTo(W, y * this.cellSize + 0.5);
      ctx.stroke();
    }

    // --- Layer 3: Cells ---
    for (let y = 0; y < this.board.height; y++) {
      for (let x = 0; x < this.board.width; x++) {
        this._drawCell(x, y, ctx, hovered, colorBlind, highContrast);
      }
    }

    // --- Layer 4: Hover highlight ---
    if (hovered) {
      const hx = hovered.x * this.cellSize;
      const hy = hovered.y * this.cellSize;
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.strokeRect(hx + 1, hy + 1, this.cellSize - 2, this.cellSize - 2);
    }
  }

  // ---- Private: Draw Single Cell ----

  private _drawCell(
    x: number, y: number,
    ctx: CanvasRenderingContext2D,
    hovered: { x: number; y: number } | null,
    colorBlind: boolean,
    highContrast: boolean,
  ): void {
    const cell = this.board.getCell(x, y);
    if (!cell) return;

    const px = x * this.cellSize;
    const py = y * this.cellSize;
    const s = this.cellSize;
    const pad = 1;

    const isHov = hovered?.x === x && hovered?.y === y;

    switch (cell.state) {
      case CELL_STATES.HIDDEN:
        ctx.fillStyle = isHov ? THEME.hiddenHoverColor : THEME.hiddenColor;
        if (highContrast) ctx.fillStyle = isHov ? '#888' : '#555';
        ctx.fillRect(px + pad, py + pad, s - pad * 2, s - pad * 2);
        break;

      case CELL_STATES.FLAGGED_MINE:
        ctx.fillStyle = THEME.revealedColor;
        ctx.fillRect(px + pad, py + pad, s - pad * 2, s - pad * 2);
        this._drawFlag(ctx, px, py, s, cell);
        break;

      case CELL_STATES.REVEALED_SAFE:
        ctx.fillStyle = THEME.revealedColor;
        ctx.fillRect(px, py, s, s);
        if (cell.number > 0) {
          const colorIdx = cell.number - 1;
          let color = THEME.numberColors[colorIdx] || '#fff';
          if (colorBlind) color = this._colorblindNumberColor(cell.number);
          if (highContrast) color = '#fff';
          ctx.fillStyle = color;
          ctx.font = `bold ${s * 0.6}px monospace`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillText(cell.number.toString(), px + s / 2, py + s / 2);
        }
        break;

      case CELL_STATES.REVEALED_MINE:
        ctx.fillStyle = THEME.revealedColor;
        ctx.fillRect(px, py, s, s);
        this._drawMine(ctx, px, py, s);
        break;

      case CELL_STATES.WRONG_FLAG:
        ctx.fillStyle = THEME.revealedColor;
        ctx.fillRect(px, py, s, s);
        this._drawWrongFlag(ctx, px, py, s);
        break;
    }
  }

  // ---- Private: Flag Drawing ----

  private _drawFlag(
    ctx: CanvasRenderingContext2D,
    px: number, py: number, s: number,
    cell: { owner: string },
  ): void {
    const p = s * 0.15;
    const staffW = s * 0.08;
    const flagW = s * 0.4;
    const flagH = s * 0.35;
    const sx = px + p + s * 0.3;

    // Staff
    ctx.fillStyle = '#ecf0f1';
    ctx.fillRect(sx, py + p, staffW, s - p * 2);

    // Fabric triangle
    ctx.fillStyle = cell.owner === CELL_OWNERS.MINE ? '#27ae60' : THEME.flagColor;
    ctx.beginPath();
    ctx.moveTo(sx + staffW, py + p);
    ctx.lineTo(sx + staffW + flagW, py + p + flagH / 2);
    ctx.lineTo(sx + staffW, py + p + flagH);
    ctx.closePath();
    ctx.fill();
  }

  // ---- Private: Mine Drawing ----

  private _drawMine(
    ctx: CanvasRenderingContext2D,
    px: number, py: number, s: number,
  ): void {
    const cx = px + s / 2;
    const cy = py + s / 2;
    const r = s * 0.3;

    // Body
    ctx.beginPath();
    ctx.arc(cx, cy, r, 0, Math.PI * 2);
    ctx.fillStyle = THEME.mineColor;
    ctx.fill();

    // Spikes
    ctx.strokeStyle = THEME.mineColor;
    ctx.lineWidth = 2;
    for (let i = 0; i < 8; i++) {
      const a = (i / 8) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(cx + Math.cos(a) * r, cy + Math.sin(a) * r);
      ctx.lineTo(cx + Math.cos(a) * (r + r * 0.4), cy + Math.sin(a) * (r + r * 0.4));
      ctx.stroke();
    }

    // Highlight
    ctx.beginPath();
    ctx.arc(cx - r * 0.25, cy - r * 0.25, r * 0.18, 0, Math.PI * 2);
    ctx.fillStyle = '#bdc3c7';
    ctx.fill();
  }

  // ---- Private: Wrong Flag Drawing ----

  private _drawWrongFlag(
    ctx: CanvasRenderingContext2D,
    px: number, py: number, s: number,
  ): void {
    this._drawFlag(ctx, px, py, s, { owner: CELL_OWNERS.SAFE });
    const p = s * 0.2;
    ctx.strokeStyle = THEME.wrongFlagColor;
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(px + p, py + p);
    ctx.lineTo(px + s - p, py + s - p);
    ctx.moveTo(px + s - p, py + p);
    ctx.lineTo(px + p, py + s - p);
    ctx.stroke();
  }

  // ---- Private: Colorblind palette ----

  private _colorblindNumberColor(n: number): string {
    const palette = [
      '#0072B2', '#009E73', '#D55E00', '#CC79A7',
      '#F0E442', '#56B4E9', '#E69F00', '#000000',
    ];
    return palette[Math.min(n - 1, palette.length - 1)];
  }
}
```

## Resize Handling

```typescript
/**
 * Recalculate cell size to fit the board within the viewport.
 * Maintains aspect ratio of the board.
 */
export function calcCellSize(
  boardWidth: number,
  boardHeight: number,
  maxWidthPx: number,
  maxHeightPx: number,
  maxCellPx: number = 48,
  minCellPx: number = 16,
): number {
  const cellByWidth = Math.floor(maxWidthPx / boardWidth);
  const cellByHeight = Math.floor(maxHeightPx / boardHeight);
  const cell = Math.min(cellByWidth, cellByHeight, maxCellPx);
  return Math.max(cell, minCellPx);
}
```

## Render Loop Integration

```typescript
// Called once per game tick (60fps target)
function gameLoop(timestamp: number): void {
  requestAnimationFrame(gameLoop);

  // Update animation state
  renderState.animProgress.forEach((v, key) => {
    renderState.animProgress.set(key, Math.min(v + 0.05, 1.0));
  });

  // Draw
  renderer.render(
    ghostImage, settings.ghostOpacity,
    settings.colorBlindMode !== 'none', settings.highContrast,
    gameState.hoveredCell,
  );
}
```
Draw order (bottom to top):

| Layer | Content |
|---|---|
| 0 | Background fill |
| 1 | Ghost image (multiply blend, configurable opacity) |
| 2 | Grid lines |
| 3 | Cell backgrounds (hidden / revealed) |
| 4 | Numbers (1–8) |
| 5 | Flags (green = correct, red = wrong) |
| 6 | Mine symbols (revealed at game end) |
| 7 | Hover highlight |
| 8 | Animation overlays |
```