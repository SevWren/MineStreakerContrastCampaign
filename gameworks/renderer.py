"""
gameworks/renderer.py — Full Pygame rendering for Mine-Streaker.

Handles all drawing: tiles, HUD, menus, animations, image overlay,
win/loss sequences.  Uses the engine purely for state queries.

Auto-scales large boards (300×370+) to fit the screen and supports
panning with mouse drag and scroll wheel.
"""

from __future__ import annotations

import math
import time
from typing import List, Optional, Tuple

import numpy as np
import pygame
from pygame.locals import *

try:
    from .engine import Board, CellState, GameEngine, MoveResult
except ImportError:
    from engine import Board, CellState, GameEngine, MoveResult


# ═══════════════════════════════════════════════════════════════════════════════
#  Configuration
# ═══════════════════════════════════════════════════════════════════════════════

BASE_TILE = 32          # nominal size; actual cell size is auto-computed
ANIM_TICK = 0.035       # seconds per tile in cascade reveal
FPS = 30                # Minesweeper needs no more than 30 fps

# Dark modern palette
C = dict(
    bg           =( 18,  18,  24),
    panel        =( 28,  28,  38),
    border       =( 60,  60,  80),
    tile_hidden  =( 45,  45,  60),
    tile_hi       =( 58,  58,  80),
    tile_reveal  =( 35,  35,  45),
    tile_flag    =( 48,  48,  64),
    flag_red     =(220,  50,  50),
    flag_pole    =(200, 200, 200),
    mine_body    =(180,  50,  50),
    mine_spike   =(230,  90,  90),
    mine_core    =( 20,  20,  20),
    num1=( 55, 120, 220),  num2=( 70, 175,  70),  num3=(215,  55,  55),
    num4=( 95,  55, 175),  num5=(175,  45, 115),  num6=(55, 175, 175),
    num7=( 25,  25,  25),  num8=( 95,  95, 105),
    text_light   =(220, 220, 230),
    text_dim     =(120, 120, 140),
    green        =( 75, 200, 115),
    red          =(225,  60,  60),
    yellow       =(220, 200,  55),
    blue         =( 55, 115, 220),
    purple       =(155,  75, 215),
    orange       =(220, 135,  35),
    cyan         =( 35, 195, 195),
)

NUM_COLS = [None, C["num1"], C["num2"], C["num3"], C["num4"],
            C["num5"], C["num6"], C["num7"], C["num8"]]

# Reserve screen edges for panel when board is large
PANEL_W         = 240
PANEL_H         = 520
PAD             = 12
HEADER_H        = 48       # tall enough for mine counter + timer + smiley
MIN_TILE_SIZE   = 10       # never shrink cells below this
TARGET_SCREEN_W = 1400     # preferred desktop width
TARGET_SCREEN_H = 850      # preferred desktop height


# ═══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _luminance(col: Tuple[int, int, int]) -> float:
    r, g, b = col
    return 0.299 * r + 0.587 * g + 0.114 * b


def rrect(surf: pygame.Surface, color, rect: Tuple[int, int, int, int], r: int = 4):
    """Rounded-rect draw — handles tiny radius gracefully."""
    x, y, w, h = rect
    r = min(r, w // 2, h // 2)
    if r == 0:
        surf.fill(color, rect)
        return
    pygame.draw.rect(surf, color, (x + r, y, w - 2 * r, h))
    pygame.draw.rect(surf, color, (x, y + r, w, h - 2 * r))
    for cx, cy in [(x + r, y + r), (x + w - r, y + r),
                   (x + r, y + h - r), (x + w - r, y + h - r)]:
        pygame.draw.circle(surf, color, (cx, cy), r)


def rrect_outline(surf: pygame.Surface, color, rect: Tuple[int, int, int, int],
                  width: int = 1, r: int = 4):
    x, y, w, h = rect
    r = min(r, w // 2, h // 2)
    if r <= 1:
        pygame.draw.rect(surf, color, rect, width)
        return
    pts: list[Tuple[int, int]] = []
    segs = [
        [(x + r, y), (x + w - r, y)],
        [(x + w, y + r), (x + w, y + h - r)],
        [(x + w - r, y + h), (x + r, y + h)],
        [(x, y + h - r), (x, y + r)],
    ]
    arc_centers = [(x + r, y + r), (x + w - r, y + r),
                   (x + w - r, y + h - r), (x + r, y + h - r)]
    starts = [0, math.pi / 2, math.pi, 3 * math.pi / 2]
    path: list[Tuple[float, float]] = []
    for (a, b), (cx, cy), start in zip(segs, arc_centers, starts):
        path.append(a)
        for i in range(1, 9):
            theta = start + i * math.pi / 2 / 8
            path.append((cx + r * math.cos(theta), cy + r * math.sin(theta)))
    path.append((segs[-1][0][0], segs[-1][0][1]))
    if len(path) > 1:
        pygame.draw.lines(surf, color, True, [(int(px), int(py)) for px, py in path], width)


def pill(surf: pygame.Surface, color, rect: Tuple[int, int, int, int]):
    """Pill-shape button."""
    x, y, w, h = rect
    r = h // 2
    rrect(surf, color, rect, r)


class AnimationCascade:
    """
    Tiles revealed by a single action animate open one-by-one.
    """

    def __init__(self, positions: List[Tuple[int, int]], speed: float = ANIM_TICK):
        self.positions = positions
        self.speed = speed
        self._start = time.monotonic()
        self._idx = 0

    @property
    def done(self) -> bool:
        return self._idx >= len(self.positions)

    def current(self) -> List[Tuple[int, int]]:
        """Tiles visible so far, expanding as time passes."""
        if self.done:
            return self.positions[:]
        elapsed = time.monotonic() - self._start
        self._idx = min(int(elapsed / self.speed) + 1, len(self.positions))
        return self.positions[:self._idx]

    def finished_after(self) -> float:
        """Estimated seconds until finished."""
        remaining = max(0, len(self.positions) - self._idx)
        return remaining * self.speed


class WinAnimation:
    """
    Progressive victory animation: flags pop open one-by-one,
    revealing the source image underneath.  After all flags are
    revealed, the victory modal appears.
    """

    def __init__(self, board: Board, speed: float = 0.025):
        # Correctly-flagged mines first, then incorrectly-flagged,
        # giving a satisfying "pattern emerges" feel.
        self._board = board
        self.speed = speed
        self._start = time.monotonic()
        self._phase = 0  # 0 = correct flags, 1 = wrong flags, 2 = done

        # Build ordered reveal list using np.where — C-speed scan, no per-cell snapshot() calls.
        import numpy as _np
        flagged_ys, flagged_xs = _np.where(board._flagged)
        self._correct = []
        self._wrong = []
        for y, x in zip(flagged_ys.tolist(), flagged_xs.tolist()):
            if board._mine[y, x]:
                self._correct.append((x, y))
            else:
                self._wrong.append((x, y))

        # Shuffle within each group for organic feel
        import random
        rng = random.Random(42)
        rng.shuffle(self._correct)
        rng.shuffle(self._wrong)
        self._all_positions = self._correct + self._wrong
        self._correct_count = len(self._correct)

    @property
    def done(self) -> bool:
        return self._phase >= 2

    @property
    def correct_done(self) -> bool:
        return self._phase >= 1

    def current(self) -> List[Tuple[int, int]]:
        """Flagged cells that have been animatically revealed so far."""
        now = time.monotonic() - self._start
        if self._phase == 0:
            idx = min(int(now / self.speed) + 1, len(self._correct))
            if idx >= len(self._correct):
                self._phase = 1
            else:
                return self._correct[:idx]
        if self._phase == 1:
            elapsed = now - len(self._correct) * self.speed
            idx = min(int(elapsed / self.speed) + 1, len(self._wrong))
            if idx >= len(self._wrong):
                self._phase = 2
            else:
                return self._correct + self._wrong[:idx]
        return self._all_positions[:]

    def finished_after(self) -> float:
        return len(self._all_positions) * self.speed


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Renderer
# ═══════════════════════════════════════════════════════════════════════════════

# Module-level default (updated by Renderer.__init__ for auto-scaling)
TILE = BASE_TILE

class Renderer:
    """
    Pygame-based renderer.  Owns the window and all surface resources.
    Receives a GameEngine and draws its state every frame.

    Large boards (≥60 tiles on either axis) are auto-scaled down and
    pannable via mouse-drag and scroll wheel.
    """

    # ── Init ───────────────────────────────────────────────────────────

    def __init__(self, engine: GameEngine, image_path: Optional[str] = None):
        pygame.init()
        self.engine = engine
        self.board = engine.board

        # ── Auto-scale tile size to fit screen ────────────────────────
        w_cols, h_rows = self.board.width, self.board.height

        # For boards ≥ 100 cells, shrink from BASE_TILE toward MIN_TILE_SIZE
        if w_cols >= 100 or h_rows >= 100:
            scale_w = (TARGET_SCREEN_W - PANEL_W - 2 * PAD) / w_cols
            scale_h = (TARGET_SCREEN_H - HEADER_H - 2 * PAD) / h_rows
            auto_tile = max(MIN_TILE_SIZE, int(min(scale_w, scale_h)))
        else:
            auto_tile = BASE_TILE

        self._tile = auto_tile                     # effective cell pixel size
        global TILE
        TILE = self._tile

        # ── Layout ────────────────────────────────────────────────────
        # Decide orientation: side panel (wide boards) vs below-panel
        self._panel_right = w_cols < 100          # enough horizontal room?
        if self._panel_right:
            self.PANEL_W = PANEL_W
            self.PAD = PAD
            self.HEADER_H = HEADER_H
            self.BOARD_OX = self.PAD + self.PANEL_W
            self.BOARD_OY = self.HEADER_H + self.PAD
            bw_px = w_cols * self._tile
            bh_px = h_rows * self._tile
            win_w = self.BOARD_OX + bw_px + self.PAD + self.PANEL_W
            win_h = self.BOARD_OY + bh_px + self.HEADER_H + self.PAD
        else:
            # Panel below the board
            self.PANEL_W = PANEL_W
            self.PAD = PAD
            self.HEADER_H = HEADER_H
            self.BOARD_OX = self.PAD
            self.BOARD_OY = self.HEADER_H + self.PAD
            bw_px = w_cols * self._tile
            bh_px = h_rows * self._tile
            win_w = max(self.PAD + bw_px + self.PAD, self.PANEL_W + 2 * self.PAD)
            panel_top = self.BOARD_OY + bh_px + self.PAD
            win_h = int(panel_top + PANEL_H + self.PAD)

        win_w = max(win_w, 780)
        win_h = max(win_h, 480)
        win_w = min(win_w, pygame.display.Info().current_w)
        win_h = min(win_h, pygame.display.Info().current_h)

        self._win = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
        pygame.display.set_caption("Mine-Streaker · Image Minesweeper")
        self._icon = self._make_icon()
        pygame.display.set_icon(self._icon)
        self._clock = pygame.time.Clock()

        # ── Fonts (scale with tile size) ──────────────────────────────
        font_base = max(9, self._tile * 3 // 5)
        font_big   = max(14, self._tile * 7 // 8)
        self._font_big   = pygame.font.SysFont("consolas", font_big, bold=True)
        self._font_med   = pygame.font.SysFont("consolas", font_base, bold=True)
        self._font_small = pygame.font.SysFont("consolas", max(9, font_base - 2))
        self._font_tiny  = pygame.font.SysFont("consolas", max(8, font_base - 3))

        # ── Panel placement ───────────────────────────────────────────
        # For large boards where board height overflows the window height, the
        # below-board panel lands off-screen (e.g. y=3772 on a 300×370 board at
        # tile=10).  In that case, pin the panel to the window's right edge as a
        # semi-transparent overlay so controls are always reachable.
        self._panel_overlay = (not self._panel_right) and (bh_px > win_h - self.BOARD_OY)

        # ── UI rects (placed after knowing actual tile/font) ──────────
        if self._panel_right:
            px = self.board.width * self._tile + self.BOARD_OX + self.PAD
            oy = self.BOARD_OY
        elif self._panel_overlay:
            px = win_w - self.PANEL_W - self.PAD
            oy = self.BOARD_OY
        else:
            px = self.PAD
            oy = int(self.BOARD_OY + h_rows * self._tile + self.PAD)

        self._btn_w = self.PANEL_W - 2 * self.PAD
        btn_w = self._btn_w
        btn_h = max(28, font_base + 10)
        gap = max(4, btn_h // 5)

        self._btn_new     = pygame.Rect(px, oy,                                btn_w, btn_h)
        self._btn_help    = pygame.Rect(px, oy + (btn_h + gap) * 1,           btn_w, btn_h)
        self._btn_fog     = pygame.Rect(px, oy + (btn_h + gap) * 2,           btn_w, btn_h)
        self._btn_save    = pygame.Rect(px, oy + (btn_h + gap) * 3,           btn_w, btn_h)
        self._btn_restart = pygame.Rect(px, oy + (btn_h + gap) * 4,           btn_w, btn_h)
        self._btn_gap     = gap   # stored so _on_resize can rebuild layout without re-deriving

        # DEV section — extra gap creates visual separation from normal controls
        _dev_offset = (btn_h + gap) * 5 + gap * 3
        self._btn_dev_solve = pygame.Rect(px, oy + _dev_offset,               btn_w, btn_h)

        # ── Image overlay ────────────────────────────────────────────
        self._image_surf: Optional[pygame.Surface] = None
        self._image_enabled = bool(image_path)
        if image_path and pygame.image.get_extended():
            try:
                img = pygame.image.load(image_path).convert_alpha()
                scale = min((w_cols * self._tile) / max(img.get_width(), 1),
                            (h_rows * self._tile) / max(img.get_height(), 1))
                tw = max(1, int(img.get_width() * scale))
                th = max(1, int(img.get_height() * scale))
                self._image_surf = pygame.transform.smoothscale(img, (tw, th))
            except Exception:
                self._image_enabled = False

        # ── State ────────────────────────────────────────────────────
        self.help_visible  = False
        self.fog            = False
        self.pressed_cell:  Optional[Tuple[int, int]] = None
        self.cascade:       Optional[AnimationCascade] = None
        self._pan_x         = 0
        self._pan_y         = 0
        self._dragging      = False
        self._drag_last     = (0, 0)

        # ── Win animation state ───────────────────────────────────────────
        self.win_anim: Optional[WinAnimation] = None
        self._ghost_surf: Optional[pygame.Surface] = None

        # ── Render caches ─────────────────────────────────────────────
        # Number surfaces: pre-rendered text for digits 1-8.
        # Rebuilt only when tile size changes — eliminates font.render() per cell per frame.
        self._num_surfs: dict = {}
        self._num_tile: int = 0
        # Reusable SRCALPHA surface for animation border (avoids per-frame allocation).
        self._anim_surf: Optional[pygame.Surface] = None
        self._anim_surf_ts: int = 0
        # Reusable SRCALPHA surface for cursor highlight.
        self._hover_surf: Optional[pygame.Surface] = None
        self._hover_surf_ts: int = 0
        # Fog overlay — cached SRCALPHA surface, recreated only on window-size change.
        self._fog_surf: Optional[pygame.Surface] = None
        self._fog_surf_size: Tuple[int, int] = (0, 0)
        # Image thumbnail — built once at init, never per-frame.
        self._thumb_surf: Optional[pygame.Surface] = None

        # Initial pan: center the board in the window
        self._center_board()
        self._rebuild_num_surfs()
        # Pre-build thumbnail once — avoids smoothscale every frame in _draw_panel
        if self._image_surf:
            self._thumb_surf = self._build_thumb()

    def _center_board(self):
        """Pan so the board is centered in its drawing area (not the full window)."""
        bw = self.board.width * self._tile
        bh = self.board.height * self._tile
        win_w, win_h = self._win.get_size()
        # Available horizontal space starts after BOARD_OX; exclude right panel if present.
        avail_x = win_w - self.BOARD_OX
        if self._panel_right:
            avail_x -= self.PANEL_W + self.PAD
        avail_y = win_h - self.BOARD_OY
        self._pan_x = max(0, (avail_x - bw) // 2)
        self._pan_y = max(0, (avail_y - bh) // 2)

    def _rebuild_num_surfs(self):
        """Pre-render digit surfaces 1-8 and the '?' mark for the current tile size.
        Called once at init and again whenever the tile size changes (scroll zoom).
        Eliminates font.render() inside the per-cell draw loop.
        """
        font = self._font_med if self._tile >= 20 else self._font_small
        self._num_surfs = {
            n: font.render(str(n), True, NUM_COLS[n])
            for n in range(1, 9)
        }
        self._question_surf = font.render("?", True, C["flag_red"])
        self._num_tile = self._tile

    def _build_thumb(self) -> pygame.Surface:
        """Build the panel thumbnail once — never called per-frame."""
        thumb_h = 64
        ar = self._image_surf.get_width() / max(1, self._image_surf.get_height())
        thumb_w = max(16, int(thumb_h * ar))
        thumb = pygame.transform.smoothscale(self._image_surf, (thumb_w, thumb_h))
        border = pygame.Surface((thumb_w + 4, thumb_h + 4))
        border.fill(C["border"])
        border.blit(thumb, (2, 2))
        return border

    # ── Surface helpers ────────────────────────────────────────────────

    def _make_icon(self) -> pygame.Surface:
        s = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.circle(s, C["mine_body"], (16, 16), 12)
        pygame.draw.circle(s, C["mine_core"], (16, 16), 6)
        for a in range(0, 360, 45):
            r = math.radians(a)
            ex = 16 + int(10 * math.cos(r))
            ey = 16 + int(10 * math.sin(r))
            pygame.draw.line(s, C["mine_spike"], (16, 16), (ex, ey), 2)
        return s

    # ── Input ──────────────────────────────────────────────────────────

    def handle_event(self, ev: pygame.event.Event) -> Optional[str]:
        """Return action string or None."""
        if ev.type == QUIT:
            return "quit"

        if ev.type == VIDEORESIZE:
            self._win = pygame.display.set_mode(ev.size, pygame.RESIZABLE)
            self._center_board()
            return None

        if ev.type == KEYDOWN:
            if ev.key in (K_ESCAPE,):
                return "quit"
            elif ev.key == K_r:
                return "restart"
            elif ev.key == K_h:
                self.help_visible = not self.help_visible
            elif ev.key == K_f:
                self.fog = not self.fog
            # Arrow-key panning for keyboard users
            elif ev.key == K_LEFT:
                self._pan_x = min(self._pan_x + self._tile * 3, 0)
            elif ev.key == K_RIGHT:
                bw = self.board.width * self._tile
                max_pan = max(0, bw - (self._win.get_width() - self.BOARD_OX))
                self._pan_x = max(self._pan_x - self._tile * 3, -max_pan)
            elif ev.key == K_UP:
                self._pan_y = min(self._pan_y + self._tile * 3, 0)
            elif ev.key == K_DOWN:
                bh = self.board.height * self._tile
                max_pan = max(0, bh - (self._win.get_height() - self.BOARD_OY))
                self._pan_y = max(self._pan_y - self._tile * 3, -max_pan)
            return None

        # ── Mouse drag for panning ───────────────────────────────────
        b_rect = self._board_rect()

        if ev.type == MOUSEBUTTONDOWN and ev.button == 1 and b_rect.collidepoint(ev.pos):
            # Middle button (or ctrl+left) = chord
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_CTRL:
                cx = (ev.pos[0] - self.BOARD_OX - self._pan_x) // self._tile
                cy = (ev.pos[1] - self.BOARD_OY - self._pan_y) // self._tile
                if 0 <= cx < self.board.width and 0 <= cy < self.board.height:
                    return f"chord:{cx},{cy}"
            # Start drag
            self._dragging = True
            self._drag_last = ev.pos
            # Also set pressed cell for click-release detection
            cx = (ev.pos[0] - self.BOARD_OX - self._pan_x) // self._tile
            cy = (ev.pos[1] - self.BOARD_OY - self._pan_y) // self._tile
            if 0 <= cx < self.board.width and 0 <= cy < self.board.height:
                self.pressed_cell = (cx, cy)
            return None

        if ev.type == MOUSEMOTION and self._dragging:
            dx = ev.pos[0] - self._drag_last[0]
            dy = ev.pos[1] - self._drag_last[1]
            self._pan_x += dx
            self._pan_y += dy
            # Clamp pan so we don't show too much empty space
            bw = self.board.width * self._tile
            bh = self.board.height * self._tile
            win_w, win_h = self._win.get_size()
            max_pan_x = max(0, bw - (win_w - self.BOARD_OX - self.PAD))
            max_pan_y = max(0, bh - (win_h - self.BOARD_OY - self.HEADER_H))
            if self._pan_x > 0:
                self._pan_x = 0
            if self._pan_y > 0:
                self._pan_y = 0
            if bw <= win_w - self.BOARD_OX - self.PAD:
                self._pan_x = 0
            if bh <= win_h - self.BOARD_OY - self.HEADER_H:
                self._pan_y = 0
            self._drag_last = ev.pos
            return None

        if ev.type == MOUSEBUTTONUP and ev.button == 1:
            self._dragging = False
            cx, cy = self.pressed_cell or (-1, -1)
            self.pressed_cell = None
            if not b_rect.collidepoint(ev.pos):
                return None
            rcx = (ev.pos[0] - self.BOARD_OX - self._pan_x) // self._tile
            rcy = (ev.pos[1] - self.BOARD_OY - self._pan_y) // self._tile
            if (rcx, rcy) != (cx, cy):
                return None  # was a drag, not a click
            if 0 <= rcx < self.board.width and 0 <= rcy < self.board.height:
                return f"click:{rcx},{rcy}"
            return None

        # ── Scroll wheel zoom (increments of BASE_TILE steps) ────────
        if ev.type == MOUSEWHEEL:
            step = max(2, self._tile // 4)
            if ev.y > 0:
                new_tile = min(BASE_TILE, self._tile + step)
            else:
                new_tile = max(MIN_TILE_SIZE, self._tile - step)
            if new_tile != self._tile:
                # Zoom centered on mouse position.
                # MOUSEWHEEL events have no .pos in pygame 2 — use get_pos().
                mx, my = pygame.mouse.get_pos()
                old_tile = self._tile
                self._tile = new_tile
                # Adjust pan so the point under cursor stays fixed
                # Cast to int: float pan causes range() TypeError in _draw_board
                self._pan_x = int(mx - (mx - self._pan_x) * new_tile / old_tile)
                self._pan_y = int(my - (my - self._pan_y) * new_tile / old_tile)
                self._clamp_pan()
                self._on_resize()
                self._rebuild_num_surfs()
            return None

        # ── Right-click anywhere on board ────────────────────────────
        if ev.type == MOUSEBUTTONDOWN and ev.button == 3 and b_rect.collidepoint(ev.pos):
            cx = (ev.pos[0] - self.BOARD_OX - self._pan_x) // self._tile
            cy = (ev.pos[1] - self.BOARD_OY - self._pan_y) // self._tile
            if 0 <= cx < self.board.width and 0 <= cy < self.board.height:
                return f"flag:{cx},{cy}"

        # ── Middle-click chord ────────────────────────────────────────
        if ev.type == MOUSEBUTTONDOWN and ev.button == 2 and b_rect.collidepoint(ev.pos):
            cx = (ev.pos[0] - self.BOARD_OX - self._pan_x) // self._tile
            cy = (ev.pos[1] - self.BOARD_OY - self._pan_y) // self._tile
            if 0 <= cx < self.board.width and 0 <= cy < self.board.height:
                return f"chord:{cx},{cy}"

        # ── Smiley click (restart) ────────────────────────────────────
        if ev.type == MOUSEBUTTONDOWN and ev.button == 1:
            _cx = self._win.get_width() // 2
            _smiley_rect = pygame.Rect(_cx - 25, 4, 50, self.HEADER_H - 4)
            if _smiley_rect.collidepoint(ev.pos):
                return "restart"

        # ── Panel button clicks ───────────────────────────────────────
        if ev.type == MOUSEBUTTONDOWN and ev.button == 1:
            panel_action = self.handle_panel(ev.pos)
            if panel_action:
                return panel_action

        return None

    def handle_panel(self, pos) -> Optional[str]:
        mx, my = pos
        if self._btn_new.collidepoint(mx, my):
            return "restart"
        if self._btn_help.collidepoint(mx, my):
            self.help_visible = not self.help_visible
            return None
        if self._btn_fog.collidepoint(mx, my):
            self.fog = not self.fog
            return None
        if self._btn_save.collidepoint(mx, my):
            return "save"
        if self._btn_restart.collidepoint(mx, my):
            return "restart"
        if self._btn_dev_solve.collidepoint(mx, my):
            return "dev:solve"
        return None

    # ── Geometry helpers ──────────────────────────────────────────────

    def _board_rect(self) -> pygame.Rect:
        bw = self.board.width * self._tile
        bh = self.board.height * self._tile
        return pygame.Rect(self.BOARD_OX + self._pan_x,
                           self.BOARD_OY + self._pan_y, bw, bh)

    def _clamp_pan(self):
        """Keep pan within sensible bounds."""
        bw = self.board.width * self._tile
        bh = self.board.height * self._tile
        win_w, win_h = self._win.get_size()
        max_px = max(0, bw - max(0, win_w - self.BOARD_OX - self.PAD))
        max_py = max(0, bh - max(0, win_h - self.BOARD_OY - self.HEADER_H))
        self._pan_x = max(-max_px, min(0, self._pan_x))
        self._pan_y = max(-max_py, min(0, self._pan_y))

    def _on_resize(self):
        """Recompute button positions after zoom — handles both panel layouts.

        Sub-bugs fixed:
          2A: was computing oy but never assigning it to btn.y (panel_right=False)
          2B: panel_right=True branch was entirely absent — buttons drifted as tile changed
          2C: sy double-count in _draw_panel fixed separately (use btn.bottom directly)
        """
        ts   = self._tile
        bh   = self._btn_new.height
        gap  = self._btn_gap

        if self._panel_right:
            px = self.board.width * ts + self.BOARD_OX + self.PAD
            oy = self.BOARD_OY
        elif self._panel_overlay:
            px = self._win.get_width() - self.PANEL_W - self.PAD
            oy = self.BOARD_OY
        else:
            px = self.PAD
            oy = int(self.BOARD_OY + self.board.height * ts + self.PAD)

        for i, btn in enumerate((self._btn_new, self._btn_help, self._btn_fog,
                                   self._btn_save, self._btn_restart)):
            btn.x = px
            btn.y = oy + (bh + gap) * i

        self._btn_dev_solve.x = px
        self._btn_dev_solve.y = oy + (bh + gap) * 5 + gap * 3

    # ══════════════════════════════════════════════════════════════════════
    #  Draw
    # ══════════════════════════════════════════════════════════════════════

    def draw(self, mouse_pos=(0, 0), game_state: str = "waiting",
             elapsed: float = 0.0, cascade_done: bool = True):
        self._win.fill(C["bg"])
        self._draw_board(mouse_pos, game_state, cascade_done)
        self._draw_overlay()
        self._draw_panel(mouse_pos, game_state, elapsed)
        self._draw_header(elapsed, game_state)  # drawn last — board can't cover it
        if self.help_visible:
            self._draw_help()
        pygame.display.flip()

    # ── Overlay (fog) ─────────────────────────────────────────────────

    def _draw_overlay(self):
        if not self.fog:
            return
        win_size = self._win.get_size()
        # Recreate backing surface only when window is resized — avoids per-frame allocation.
        if self._fog_surf is None or self._fog_surf_size != win_size:
            self._fog_surf = pygame.Surface(win_size, pygame.SRCALPHA)
            self._fog_surf_size = win_size
        surf = self._fog_surf
        surf.fill((0, 0, 0, 140))
        ox, oy = self.BOARD_OX, self.BOARD_OY
        bw = self.board.width * self._tile
        bh = self.board.height * self._tile
        punch = pygame.Rect(ox + self._pan_x, oy + self._pan_y, bw, bh)
        surf.fill((0, 0, 0, 0), punch)
        self._win.blit(surf, (0, 0))

    # ── Header ────────────────────────────────────────────────────────

    def _draw_header(self, elapsed, game_state):
        w = self._win.get_width()
        r = pygame.Rect(0, 0, w, self.HEADER_H + 4)
        pygame.draw.rect(self._win, C["panel"], r)
        pygame.draw.line(self._win, C["border"],
                         (0, self.HEADER_H + 2), (w, self.HEADER_H + 2), 2)

        # ── Left: mine counter (vertically centered) ──────────────────
        mines = self.board.mines_remaining
        mcol = C["red"] if mines < 0 else C["text_light"]
        mt = self._font_big.render(f"M:{mines:>03d}", True, mcol)
        self._win.blit(mt, (self.BOARD_OX + 8, (self.HEADER_H - mt.get_height()) // 2))

        # ── Centre: smiley (clickable reset button) ───────────────────
        cx = self._win.get_width() // 2
        self._draw_smiley(cx - 25, 4, 50, self.HEADER_H - 4, game_state)

        # ── Right: two-row scoreboard — guaranteed no overlap ─────────
        # Uses _font_small so two rows always fit inside HEADER_H=48px.
        score = self.engine.score
        streak = self.engine.streak
        mult = self.engine.streak_multiplier
        secs = int(elapsed)
        win_w = self._win.get_width()

        fsh = self._font_small.get_height()
        # Centre the two rows vertically in the header
        y1 = (self.HEADER_H - 2 * fsh - 2) // 2
        y2 = y1 + fsh + 2

        # Row 1: timer (left of score) + score (right-anchored)
        score_col = C["yellow"] if mult > 1.0 else C["text_light"]
        sc = self._font_small.render(f"SCORE:{score:>6d}", True, score_col)
        self._win.blit(sc, (win_w - sc.get_width() - 8, y1))
        tt = self._font_small.render(f"T:{secs:>03d}", True, C["text_light"])
        self._win.blit(tt, (win_w - sc.get_width() - tt.get_width() - 18, y1))

        # Row 2: streak (only shown when streak >= 5)
        if streak >= 5:
            streak_col = (C["orange"] if mult < 3.0 else
                          C["red"]    if mult < 5.0 else C["cyan"])
            sl = self._font_small.render(f"STREAK x{streak}  {mult:.1f}x", True, streak_col)
            self._win.blit(sl, (win_w - sl.get_width() - 8, y2))

    def _draw_smiley(self, x, y, w, h, state):
        cx, cy = x + w // 2, y + h // 2
        r = min(w, h) // 2 - 2
        col = {"playing": C["yellow"], "won": C["green"], "lost": C["red"]}.get(state, C["yellow"])
        hov = pygame.Rect(x, y, w, h).collidepoint(pygame.mouse.get_pos())
        if hov:
            col = tuple(min(255, c + 40) for c in col)
        pygame.draw.circle(self._win, col, (cx, cy), r)
        pygame.draw.circle(self._win, C["border"], (cx, cy), r, 2)
        er = max(1, r // 5)
        eo = r // 3
        for ex in (cx - eo, cx + eo):
            pygame.draw.circle(self._win, C["bg"], (ex, cy - eo), er)
            pygame.draw.circle(self._win, C["text_light"], (ex, cy - eo), er // 2)
        if state == "won":
            pygame.draw.arc(self._win, C["text_light"],
                            (cx - r // 2, cy - r // 3, r, r * 2 // 3), 0, math.pi, 2)
        elif state == "lost":
            pygame.draw.arc(self._win, C["text_light"],
                            (cx - r // 2, cy + r // 5, r, r * 2 // 3), math.pi, 2 * math.pi, 2)
        else:
            pygame.draw.arc(self._win, C["text_light"],
                            (cx - r // 2, cy - r // 6, r, r // 2), math.pi, 2 * math.pi, 2)

    # ── Board tiles (clipped rendering!) ──────────────────────────────

    def _draw_board(self, mouse_pos, game_state, cascade_done):
        ox = self.BOARD_OX + self._pan_x
        oy = self.BOARD_OY + self._pan_y
        bw = self.board.width * self._tile
        bh = self.board.height * self._tile
        ts = self._tile

        # Board background
        br = pygame.Rect(ox - 6, oy - 6, bw + 12, bh + 12)
        rrect(self._win, C["panel"], br, max(4, ts // 3))
        pygame.draw.rect(self._win, C["border"], br, 2, border_radius=max(4, ts // 3))

        # Clip to board area
        old_clip = self._win.get_clip()
        clip_rect = pygame.Rect(ox, oy, bw, bh)
        self._win.set_clip(clip_rect)

        # Image ghost overlay (behind cells, visible through flagged tiles)
        if self._image_enabled and self._image_surf:
            self._draw_image_ghost(ox, oy, bw, bh)

        # Cascade animation set (reveal animation)
        anim_set = set()
        if self.cascade and not self.cascade.done:
            anim_set = set(self.cascade.current())
        elif not cascade_done:
            pass

        # Win animation set (progressive flag reveal)
        win_anim_set = set()
        if self.win_anim and not self.win_anim.done:
            win_anim_set = set(self.win_anim.current())

        # ── Compute visible tile range (skip off-screen tiles) ──────
        # This is critical for 300×370 boards — only draw what's visible
        win_w, win_h = self._win.get_size()
        # Tiles that could possibly be visible (conservative)
        tx0 = max(0, (-self._pan_x) // ts - 1)
        ty0 = max(0, (-self._pan_y) // ts - 1)
        tx1 = min(self.board.width, (win_w - ox) // ts + 2)
        ty1 = min(self.board.height, (win_h - oy) // ts + 2)

        # Draw visible cells — read board arrays once to avoid per-cell snapshot() overhead
        pressed = self.pressed_cell
        mpos = mouse_pos
        _mine       = self.board._mine
        _revealed   = self.board._revealed
        _flagged    = self.board._flagged
        _questioned = self.board._questioned
        _neighbours = self.board._neighbours

        for y in range(ty0, ty1):
            for x in range(tx0, tx1):
                px = ox + x * ts
                py = oy + y * ts
                cell = CellState(
                    is_mine       =bool(_mine[y, x]),
                    is_revealed   =bool(_revealed[y, x]),
                    is_flagged    =bool(_flagged[y, x]),
                    is_questioned =bool(_questioned[y, x]),
                    neighbour_mines=int(_neighbours[y, x]),
                )
                ip = cell.is_revealed and (x, y) in anim_set
                in_win_anim = (x, y) in win_anim_set
                self._draw_cell(x, y, cell, (px, py), ip,
                                pressed == (x, y), self.fog, ts, in_win_anim)

        # Loss overlay
        if game_state == "lost":
            self._draw_loss_overlay(ox, oy)

        # Win animation progressive reveal (drawn over cells)
        if game_state == "won" and self.win_anim and not self.win_anim.done:
            self._draw_win_animation_fx(ox, oy, win_anim_set)

        # Cursor highlight
        # ox/oy already include _pan_x/_pan_y — subtract directly
        hx = (mpos[0] - ox) // ts if ts > 0 else -1
        hy = (mpos[1] - oy) // ts if ts > 0 else -1
        if 0 <= hx < self.board.width and 0 <= hy < self.board.height:
            self._win.set_clip(clip_rect)
            if not _revealed[hy, hx]:
                hr = pygame.Rect(ox + hx * ts, oy + hy * ts, ts, ts)
                if self._hover_surf is None or self._hover_surf_ts != ts:
                    self._hover_surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
                    self._hover_surf_ts = ts
                self._hover_surf.fill((0, 0, 0, 0))
                pygame.draw.rect(self._hover_surf, (255, 255, 255, 40),
                                 self._hover_surf.get_rect(), 1, border_radius=2)
                self._win.blit(self._hover_surf, hr)

        self._win.set_clip(old_clip)

    def _draw_cell(self, x, y, cell: CellState, pos, in_anim, is_pressed, fog, ts=None,
                    in_win_anim=False):
        if ts is None:
            ts = self._tile
        px, py = pos
        pad = max(1, ts // 16)

        # Mine flash overlay: red background when this cell was just hit
        _flash_end = self.engine.mine_flash.get((x, y), 0)
        _flashing = time.monotonic() < _flash_end

        if cell.is_revealed:
            bg = C["red"] if _flashing else C["tile_reveal"]
            pygame.draw.rect(self._win, bg, (px, py, ts, ts))
            if cell.is_mine:
                self._draw_mine(px, py, ts)
            elif cell.neighbour_mines > 0:
                # Use pre-rendered surface from cache — avoids font.render() per cell per frame
                if self._num_tile != ts:
                    self._rebuild_num_surfs()
                num_surf = self._num_surfs[cell.neighbour_mines]
                self._win.blit(num_surf, num_surf.get_rect(center=(px + ts // 2, py + ts // 2)))
        elif cell.is_flagged:
            if fog:
                pygame.draw.rect(self._win, C["tile_hidden"], (px, py, ts, ts))
            else:
                pygame.draw.rect(self._win, C["tile_flag"], (px, py, ts, ts))
            self._draw_flag(px, py, ts)
        elif cell.is_questioned:
            pygame.draw.rect(self._win, C["tile_flag"], (px, py, ts, ts))
            self._draw_question(px, py, ts)
        else:
            col = C["tile_hi"] if is_pressed else C["tile_hidden"]
            # pygame 2.x draw.rect supports border_radius natively (single C call).
            # rrect() did the same work in Python with 6 draw calls — ~6x slower.
            pygame.draw.rect(self._win, col, (px, py, ts, ts),
                             border_radius=max(2, ts // 8))

        # Cell border
        if in_anim:
            # Reuse pre-allocated SRCALPHA surface — avoids per-frame allocation
            if self._anim_surf is None or self._anim_surf_ts != ts:
                self._anim_surf = pygame.Surface((ts, ts), pygame.SRCALPHA)
                self._anim_surf_ts = ts
            self._anim_surf.fill((0, 0, 0, 0))
            bcol = (*C["border"], 60)
            pygame.draw.rect(self._anim_surf, bcol, (0, 0, ts, ts), 1, border_radius=max(2, ts // 8))
            self._win.blit(self._anim_surf, (px, py))
        else:
            pygame.draw.rect(self._win, C["border"], (px, py, ts, ts), 1, border_radius=max(1, ts // 8))

    def _draw_mine(self, px, py, ts=None):
        if ts is None:
            ts = self._tile
        cx, cy = px + ts // 2, py + ts // 2
        r = max(2, ts // 3)
        pygame.draw.circle(self._win, C["mine_body"], (cx, cy), r)
        pygame.draw.circle(self._win, C["mine_core"], (cx, cy), max(1, r // 2))
        for a in range(0, 360, 45):
            rd = math.radians(a)
            ex = cx + int(math.cos(rd) * r)
            ey = cy + int(math.sin(rd) * r)
            pygame.draw.line(self._win, C["mine_spike"], (cx, cy), (ex, ey), max(1, ts // 16))

    def _draw_flag(self, px, py, ts=None):
        if ts is None:
            ts = self._tile
        pad = max(1, ts // 10)
        pole_x = px + ts // 2
        pygame.draw.line(self._win, C["flag_pole"],
                         (pole_x, py + pad), (pole_x, py + ts - pad), max(1, ts // 10))
        pts = [(pole_x, py + pad + 1),
               (pole_x + ts // 3, py + ts // 3),
               (pole_x, py + ts - pad - 1)]
        pygame.draw.polygon(self._win, C["flag_red"], pts)

    def _draw_question(self, px, py, ts=None):
        if ts is None:
            ts = self._tile
        surf = self._question_surf  # pre-rendered in _rebuild_num_surfs — no per-frame font.render()
        self._win.blit(surf, surf.get_rect(center=(px + ts // 2, py + ts // 2)))

    def _draw_loss_overlay(self, ox, oy):
        ts = self._tile
        win_w, win_h = self._win.get_size()
        tx0 = max(0, (-self._pan_x) // ts - 1)
        ty0 = max(0, (-self._pan_y) // ts - 1)
        tx1 = min(self.board.width, (win_w - ox) // ts + 2)
        ty1 = min(self.board.height, (win_h - oy) // ts + 2)
        _mine    = self.board._mine
        _flagged = self.board._flagged
        for y in range(ty0, ty1):
            for x in range(tx0, tx1):
                is_mine    = bool(_mine[y, x])
                is_flagged = bool(_flagged[y, x])
                px = ox + x * ts
                py = oy + y * ts
                ts2 = ts // 2
                if is_mine and not is_flagged:
                    cx, cy = px + ts2, py + ts2
                    pygame.draw.circle(self._win, C["mine_body"], (cx, cy), max(3, ts // 3))
                    pygame.draw.circle(self._win, C["mine_core"], (cx, cy), max(1, ts // 5))
                if is_flagged and not is_mine:
                    pygame.draw.line(self._win, C["red"],
                                     (px + 4, py + 4), (px + ts - 4, py + ts - 4), max(1, ts // 6))
                    pygame.draw.line(self._win, C["red"],
                                     (px + ts - 4, py + 4), (px + 4, py + ts - 4), max(1, ts // 6))

    # ── Image ghost overlay ───────────────────────────────────────────

    def _draw_image_ghost(self, ox, oy, bw, bh):
        if not self._image_surf:
            return

        # Rebuild cached scaled surface only when board pixel dimensions change
        if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
            self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))

        scaled = self._ghost_surf
        ts = self._tile
        _flagged = self.board._flagged
        _mine    = self.board._mine

        # Viewport culling — only iterate cells actually on screen (matches _draw_board bounds)
        win_w, win_h = self._win.get_size()
        tx0 = max(0, (-self._pan_x) // ts - 1)
        ty0 = max(0, (-self._pan_y) // ts - 1)
        tx1 = min(self.board.width,  (win_w - ox) // ts + 2)
        ty1 = min(self.board.height, (win_h - oy) // ts + 2)

        # np.where scans the flagged slice at C speed — no Python loop over W×H.
        # Only flagged cells in the visible viewport produce Python-level iterations.
        ys, xs = np.where(_flagged[ty0:ty1, tx0:tx1])
        if ys.size == 0:
            return
        ys = ys + ty0
        xs = xs + tx0

        for y, x in zip(ys, xs):
            px = ox + int(x) * ts
            py = oy + int(y) * ts
            src_rect = pygame.Rect(int(x) * ts, int(y) * ts, ts, ts)
            sub = scaled.subsurface(src_rect).copy()
            sub.set_alpha(200 if _mine[y, x] else 40)
            self._win.blit(sub, (px, py))
    # ── Right panel ───────────────────────────────────────────────────

    def _draw_panel(self, mouse_pos, game_state, elapsed):
        win_w = self._win.get_width()
        if self._panel_right:
            px = self.board.width * self._tile + self.BOARD_OX + self.PAD
            oy = self.BOARD_OY
        elif self._panel_overlay:
            px = win_w - self.PANEL_W - self.PAD
            oy = self.BOARD_OY
            # Semi-transparent backdrop so panel text/buttons are readable over board tiles
            _bd_w = self.PANEL_W + self.PAD * 2
            _bd_h = self._win.get_height() - oy
            if _bd_h > 0:
                _ov = pygame.Surface((_bd_w, _bd_h), pygame.SRCALPHA)
                _ov.fill((18, 18, 24, 215))
                self._win.blit(_ov, (px - self.PAD, oy))
        else:
            px = self.PAD
            oy = int(self.BOARD_OY + self.board.height * self._tile + self.PAD)

        win = self._win

        # Title
        surf = self._font_small.render("CONTROLS", True, C["text_dim"])
        win.blit(surf, (px, oy))

        mx, my = mouse_pos
        buttons = [
            (self._btn_new,    "Restart"),
            (self._btn_help,   "Help"),
            (self._btn_fog,    "Hide Fog" if self.fog else "Toggle Fog"),
            (self._btn_save,   "Save .npy"),
            (self._btn_restart,"New Game"),
        ]

        for rect, label in buttons:
            hover = rect.collidepoint(mx, my)
            base_col = C["green"] if "Restart" in label or "New Game" in label else \
                       C["blue"] if "Help" in label else \
                       C["purple"] if "Fog" in label else C["cyan"]
            pill(win, base_col, rect)
            if hover:
                pygame.draw.rect(win, C["text_light"], rect, 2, border_radius=8)
            ts = self._font_small.render(label, True, C["bg"])
            win.blit(ts, ts.get_rect(center=rect.center))

        # ── DEV section ─────────────────────────────────────────────
        dev_sep_y = self._btn_dev_solve.y - self._btn_gap - 4
        pygame.draw.line(win, C["border"], (px, dev_sep_y), (px + self._btn_w, dev_sep_y), 1)
        dev_hdr = self._font_tiny.render("DEV TOOLS", True, C["orange"])
        win.blit(dev_hdr, (px, dev_sep_y - dev_hdr.get_height() - 2))

        dev_active = not self.engine.board.game_over
        dev_col = C["orange"] if dev_active else C["border"]
        pill(win, dev_col, self._btn_dev_solve)
        if self._btn_dev_solve.collidepoint(mx, my) and dev_active:
            pygame.draw.rect(win, C["text_light"], self._btn_dev_solve, 2, border_radius=8)
        dev_label = self._font_small.render("Solve Board", True, C["bg"] if dev_active else C["text_dim"])
        win.blit(dev_label, dev_label.get_rect(center=self._btn_dev_solve.center))

        # Stats — _btn_restart.bottom is already an absolute Y coordinate,
        # so do NOT add oy again (that was the double-count bug on large boards).
        base = self._font_small.get_height()
        sy = self._btn_restart.bottom + 12
        stats = [
            f"Board: {self.board.width} x {self.board.height}",
            f"Mines: {self.board.total_mines}",
            f"Safe left: {self.board.total_safe - self.board.safe_revealed_count}",
            f"Flags: {self.board.flags_placed}",
        ]
        if self.board.questioned_count > 0:
            stats.append(f"?: {self.board.questioned_count}")
        if game_state == "won":
            stats.append("YOU WIN!")
        elif game_state == "lost":
            stats.append("BOOM!")
        elif game_state == "playing":
            m, s = divmod(int(elapsed), 60)
            stats.append(f"Time: {m}:{s:02d}")

        for i, line in enumerate(stats):
            col = C["green"] if game_state == "won" and i == len(stats) - 1 else \
                  C["red"]   if game_state == "lost" and i == len(stats) - 1 else C["text_light"]
            surf = self._font_small.render(line, True, col)
            win.blit(surf, (px, sy + i * (base + 4)))

        # Tips
        ty = sy + len(stats) * (base + 4) + 12
        tips = [
            "L-click  Reveal",
            "R-click  Flag / unflag",
            "M-click  Chord",
            "Scroll   Zoom / Pan",
            "",
            "Keys: R Restart  H Help",
            "      F Fog  ESC Quit",
        ]
        for i, t in enumerate(tips):
            win.blit(self._font_tiny.render(t, True, C["text_dim"]),
                     (px, ty + i * (self._font_tiny.get_height() + 2)))

        # Mode badge
        by = ty + len(tips) * (self._font_tiny.get_height() + 2) + 8
        mode_text = "Mode: Image-Reveal" if self._image_enabled else "Mode: Classic"
        win.blit(self._font_tiny.render(mode_text, True, C["cyan"]), (px, by))

        # Image preview thumbnail — pre-built in __init__, never rebuilt per-frame
        if self._thumb_surf:
            tw = self._thumb_surf.get_width()
            win.blit(self._thumb_surf, (px + (self._btn_w - tw) // 2, oy - 64 - 14))

    # ── Victory overlay ───────────────────────────────────────────────

    def start_win_animation(self):
        """Called once when the game transitions to 'won'."""
        self.win_anim = WinAnimation(self.board)

    def draw_victory(self, elapsed):
        self._draw_modal("YOU WIN!", f"Time: {int(elapsed)}s  |  Flags: {self.board.flags_placed}")

    def draw_defeat(self):
        self._draw_modal("BOOM!", "Better luck next time.")

    def _draw_win_animation_fx(self, ox, oy, win_anim_set):
        """Draw progressively revealed flags during win animation.
        Each correctly-flagged mine shows the underlying source image pixel."""
        if not self._image_surf or not win_anim_set:
            return

        bw = self.board.width * self._tile
        bh = self.board.height * self._tile
        ts = self._tile

        # Reuse the same cached surface as _draw_image_ghost
        if self._ghost_surf is None or self._ghost_surf.get_size() != (bw, bh):
            self._ghost_surf = pygame.transform.smoothscale(self._image_surf, (bw, bh))

        scaled = self._ghost_surf

        for (x, y) in win_anim_set:
            px = ox + x * ts
            py = oy + y * ts
            src_rect = pygame.Rect(x * ts, y * ts, ts, ts)
            sub = scaled.subsurface(src_rect).copy()
            sub.set_alpha(255)
            self._win.blit(sub, (px, py))

    def _draw_modal(self, title, subtitle):
        overlay = pygame.Surface(self._win.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self._win.blit(overlay, (0, 0))

        cx, cy = self._win.get_width() // 2, self._win.get_height() // 2
        bw, bh = 400, 170
        rect = pygame.Rect(cx - bw // 2, cy - bh // 2, bw, bh)
        rrect(self._win, C["panel"], rect, 14)
        pygame.draw.rect(self._win, C["green"], rect, 2, border_radius=14)

        t1 = self._font_big.render(title, True, C["text_light"])
        self._win.blit(t1, t1.get_rect(center=(cx, cy - 30)))
        t2 = self._font_small.render(subtitle, True, C["text_dim"])
        self._win.blit(t2, t2.get_rect(center=(cx, cy + 10)))

        hint = self._font_tiny.render("Press R to restart or ESC to quit", True, C["border"])
        self._win.blit(hint, hint.get_rect(center=(cx, cy + 50)))

    # ── Help overlay ──────────────────────────────────────────────────

    def _draw_help(self):
        overlay = pygame.Surface(self._win.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self._win.blit(overlay, (0, 0))

        cx, cy = self._win.get_width() // 2, self._win.get_height() // 2
        bw, bh = 580, 520
        rect = pygame.Rect(cx - bw // 2, cy - bh // 2, bw, bh)
        rrect(self._win, C["panel"], rect, 14)
        pygame.draw.rect(self._win, C["border"], rect, 2, border_radius=14)

        ty = cy - bh // 2 + 20
        lines = [
            ("MINE-STREAKER", self._font_med, C["cyan"]),
            ("", None, None),
            ("GAMEPLAY", self._font_small, C["yellow"]),
            ("Flag every mine to reveal the hidden image.", self._font_tiny, C["text_light"]),
            ("Each correctly-placed flag exposes part of the source image.", self._font_tiny, C["text_dim"]),
            ("", None, None),
            ("FIRST CLICK", self._font_small, C["yellow"]),
            ("Your first click is always safe.", self._font_tiny, C["text_light"]),
            ("", None, None),
            ("FLOOD-FILL", self._font_small, C["yellow"]),
            ("Revealing a 0 auto-reveals all connected safe cells.", self._font_tiny, C["text_light"]),
            ("", None, None),
            ("CHORDING", self._font_small, C["yellow"]),
            ("Middle-click or Ctrl+click on a number to reveal neighbours", self._font_tiny, C["text_light"]),
            ("when flag count matches.", self._font_tiny, C["text_light"]),
            ("", None, None),
            ("CONTROLS", self._font_small, C["yellow"]),
            ("Left click      - Reveal tile", self._font_tiny, C["text_light"]),
            ("Right click     - Place / remove flag", self._font_tiny, C["text_light"]),
            ("Middle click    - Chord reveal", self._font_tiny, C["text_light"]),
            ("Scroll wheel    - Zoom in/out (pan with drag)", self._font_tiny, C["text_light"]),
            ("Arrow keys      - Pan board", self._font_tiny, C["text_light"]),
            ("R               - Restart game", self._font_tiny, C["text_light"]),
            ("H               - Toggle help", self._font_tiny, C["text_light"]),
            ("F               - Toggle fog of war", self._font_tiny, C["text_light"]),
            ("ESC             - Quit", self._font_tiny, C["text_light"]),
        ]

        for text, font, color in lines:
            if font is None:
                ty += 8
                continue
            surf = font.render(text, True, color)
            self._win.blit(surf, (rect.left + 22, ty))
            ty += surf.get_height() + 4
