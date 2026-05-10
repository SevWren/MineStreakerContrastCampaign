"""
gameworks/engine.py — Mine-Streaker Minesweeper Game Engine (pure logic).

No rendering dependencies.  Supports:
  - Classic random boards (Easy / Medium / Hard via mine count)
  - Image-generated boards via MineStreaker pipeline (load_from_image)
  - .npy board loading (load_board_from_npy)

State machine (on Board, not Engine — Engine delegates):
  PLAYING  →  WON  (all safe cells revealed)
  PLAYING  →  LOST (stepped on a mine)

Coordinates are (col, row) == (x, y) throughout.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple

import traceback

import numpy as np
from pathlib import Path
from scipy.ndimage import convolve as _ndconvolve


# ═══════════════════════════════════════════════════════════════════════════════
#  Scoring constants
# ═══════════════════════════════════════════════════════════════════════════════

# Points awarded for revealing a cell, indexed by neighbour_mines count (0–8).
# Higher-count cells are harder to deduce → more points.
REVEAL_POINTS = [1, 5, 10, 20, 35, 55, 80, 110, 150]

CORRECT_FLAG_BONUS = 50   # placing a flag on an actual mine
WRONG_FLAG_PENALTY = 25   # placing a flag on a safe cell
MINE_HIT_PENALTY   = 250  # score deducted per mine stepped on (game continues)

# Streak multiplier tiers.  First tier where streak >= threshold is used.
# Sorted descending so we short-circuit on the highest matching tier.
STREAK_TIERS: List[Tuple[int, float]] = [
    (25, 5.0),   # 25+ consecutive safe actions → 5× multiplier
    (15, 3.0),   #  15–24 → 3×
    (10, 2.0),   #  10–14 → 2×
    (5,  1.5),   #   5– 9 → 1.5×
    (0,  1.0),   #   0– 4 → 1× (base)
]


# ═══════════════════════════════════════════════════════════════════════════════
#  Cell Snapshot
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CellState:
    """Immutable snapshot of a single cell for the renderer to read."""
    is_mine: bool = False
    is_revealed: bool = False
    is_flagged: bool = False
    is_questioned: bool = False
    neighbour_mines: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
#  Board — Pure Logic
# ═══════════════════════════════════════════════════════════════════════════════

class Board:
    """
    Minesweeper board with full game rules.

    Invariant: _mine, _revealed, _flagged, _neighbours are all (H, W) numpy arrays.
    Public API uses (x, y) == (col, row); internal arrays index [row, col].
    """

    __slots__ = ("width", "height", "total_mines", "_mine", "_revealed",
                 "_flagged", "_questioned", "_neighbours", "_state")

    def __init__(self, width: int, height: int, mine_positions: Set[Tuple[int, int]]):
        self.width = width
        self.height = height
        self.total_mines = len(mine_positions)

        self._mine = np.zeros((height, width), dtype=bool)
        self._revealed = np.zeros((height, width), dtype=bool)
        self._flagged = np.zeros((height, width), dtype=bool)
        self._questioned = np.zeros((height, width), dtype=bool)

        for (cx, cy) in mine_positions:
            self._mine[cy, cx] = True

        # Pre-compute neighbour counts (0–8) via scipy convolution — O(H*W) vs O(H*W*9)
        _kernel = np.ones((3, 3), dtype=np.uint8)
        _kernel[1, 1] = 0
        raw = _ndconvolve(self._mine.view(np.uint8), _kernel, mode='constant', cval=0)
        self._neighbours = np.where(self._mine, np.uint8(0), raw.astype(np.uint8))

        self._state: str = "playing"  # playing | won | lost

    # ── Internals ──────────────────────────────────────────────────────

    def _count_adj(self, x: int, y: int) -> int:
        x0, x1 = max(0, x - 1), min(self.width, x + 2)
        y0, y1 = max(0, y - 1), min(self.height, y + 2)
        sub = self._mine[y0:y1, x0:x1].astype(np.int32)
        return int(sub.sum()) - int(self._mine[y, x])

    def _neighbours_iter(self, x: int, y: int):
        for dy in range(-1, 2):
            ny = y + dy
            if not (0 <= ny < self.height):
                continue
            for dx in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue
                nx = x + dx
                if 0 <= nx < self.width:
                    yield nx, ny

    # ── Read-only Properties ───────────────────────────────────────────

    @property
    def total_safe(self) -> int:
        return self.width * self.height - self.total_mines

    @property
    def revealed_count(self) -> int:
        return int(self._revealed.sum())

    @property
    def safe_revealed_count(self) -> int:
        """Revealed cells that are NOT mines (excludes mine-hit cells from count)."""
        return int(np.sum(self._revealed & ~self._mine))

    @property
    def flags_placed(self) -> int:
        return int(self._flagged.sum())

    @property
    def questioned_count(self) -> int:
        return int(self._questioned.sum())

    @property
    def mines_remaining(self) -> int:
        return self.total_mines - self.flags_placed

    @property
    def correct_flags(self) -> int:
        return int(np.sum(self._flagged & self._mine))

    @property
    def is_won(self) -> bool:
        return self._state == "won"

    @property
    def is_lost(self) -> bool:
        return self._state == "lost"

    @property
    def game_over(self) -> bool:
        return self._state in ("won", "lost")

    # ── Actions ────────────────────────────────────────────────────────

    def reveal(self, x: int, y: int) -> Tuple[bool, List[Tuple[int, int]]]:
        """
        Reveal cell (x, y).  Returns (hit_mine, newly_revealed_positions).

        Auto-reveals all connected zero-count cells (flood-fill).
        """
        if self._revealed[y, x] or self._flagged[y, x]:
            return False, []

        if self._mine[y, x]:
            self._revealed[y, x] = True
            # No game-over: mine hit is a score penalty, game continues.
            return True, [(x, y)]

        newly: List[Tuple[int, int]] = []
        stack = [(x, y)]
        while stack:
            cx, cy = stack.pop()
            cell = self._revealed[cy, cx] or self._flagged[cy, cx] or self._mine[cy, cx]
            if cell:
                continue
            self._revealed[cy, cx] = True
            newly.append((cx, cy))
            if self._neighbours[cy, cx] == 0:
                for nx, ny in self._neighbours_iter(cx, cy):
                    if not self._revealed[ny, nx] and not self._flagged[ny, nx] and not self._mine[ny, nx]:
                        stack.append((nx, ny))

        if self.revealed_count == self.total_safe:
            self._state = "won"

        return False, newly

    def toggle_flag(self, x: int, y: int) -> str:
        """Right-click cycle: hidden → flag → ? → hidden.
        Returns new state: 'hidden' | 'flag' | 'question'.
        """
        if self._revealed[y, x]:
            return "hidden"

        if self._flagged[y, x]:
            # flag → question
            self._flagged[y, x] = False
            self._questioned[y, x] = True
            return "question"

        if self._questioned[y, x]:
            # question → hidden
            self._questioned[y, x] = False
            return "hidden"

        # hidden → flag
        self._flagged[y, x] = True

        if self.revealed_count == self.total_safe:
            self._state = "won"

        return "flag"

    def snapshot(self, x: int, y: int) -> CellState:
        return CellState(
            is_mine=bool(self._mine[y, x]),
            is_revealed=bool(self._revealed[y, x]),
            is_flagged=bool(self._flagged[y, x]),
            is_questioned=bool(self._questioned[y, x]),
            neighbour_mines=int(self._neighbours[y, x]),
        )

    def chord(self, x: int, y: int) -> Tuple[bool, List[Tuple[int, int]]]:
        """
        Chord: if flag count around (x,y) == its number, reveal all unflagged neighbours.
        Returns (hit_mine, newly_revealed).
        """
        if not self._revealed[y, x] or self._neighbours[y, x] == 0:
            return False, []

        adj = list(self._neighbours_iter(x, y))
        flagged_count = sum(1 for (nx, ny) in adj if self._flagged[ny, nx])

        if flagged_count != int(self._neighbours[y, x]):
            return False, []

        hit_mine = False
        all_new: List[Tuple[int, int]] = []
        for nx, ny in adj:
            if not self._revealed[ny, nx] and not self._flagged[ny, nx]:
                hit, new = self.reveal(nx, ny)
                if hit:
                    hit_mine = True
                all_new.extend(new)

        return hit_mine, all_new

    # ── Mine Query (for loss rendering) ────────────────────────────────

    def all_mine_positions(self) -> List[Tuple[int, int]]:
        ys, xs = np.where(self._mine)
        return list(zip(xs.tolist(), ys.tolist()))

    def wrong_flag_positions(self) -> List[Tuple[int, int]]:
        w = self._flagged & ~self._mine
        ys, xs = np.where(w)
        return list(zip(xs.tolist(), ys.tolist()))

    # ── Snapshot ───────────────────────────────────────────────────────

# snapshot already defined above — moved to include is_questioned


# ═══════════════════════════════════════════════════════════════════════════════
#  Mine Placement
# ═══════════════════════════════════════════════════════════════════════════════

def place_random_mines(width: int, height: int, count: int,
                       safe_x: int = -1, safe_y: int = -1,
                       seed: Optional[int] = None) -> Set[Tuple[int, int]]:
    """Place N mines randomly, optionally excluding a (x,y) + its 3×3 neighbourhood."""
    rng = np.random.default_rng(seed)
    excluded: Set[Tuple[int, int]] = set()
    if 0 <= safe_x < width and 0 <= safe_y < height:
        for dx in range(-1, 2):
            for dy in range(-1, 2):
                nx, ny = safe_x + dx, safe_y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    excluded.add((nx, ny))

    candidates = [(x, y) for y in range(height) for x in range(width) if (x, y) not in excluded]
    count = min(count, len(candidates))

    indices = rng.choice(len(candidates), size=count, replace=False)
    return {candidates[int(i)] for i in indices}


# ═══════════════════════════════════════════════════════════════════════════════
#  Board Loading — Random / .npy / Image Pipeline
# ═══════════════════════════════════════════════════════════════════════════════

def load_board_from_npy(path: str) -> Board:
    """
    Load a board from an .npy file.

    Supports two encodings:
    - Pipeline format (run_iter9.py output): int8, 0=safe, 1=mine
    - Game format (_save_npy() output):      int8, -1=mine, 0-8=neighbour_count

    Format is auto-detected: if all values are in {0, 1} (no negatives, max <= 1)
    the pipeline format is assumed.
    """
    grid = np.load(path)
    if grid.ndim != 2:
        raise ValueError(f"Expected 2D array, got shape {grid.shape}")

    h, w = grid.shape
    is_pipeline_format = int(grid.min()) >= 0 and int(grid.max()) <= 1

    if is_pipeline_format:
        # Pipeline format: 1=mine, 0=safe — no neighbour counts stored
        rows, cols = np.where(grid == 1)
        mine_pos: Set[Tuple[int, int]] = {(int(c), int(r)) for r, c in zip(rows, cols)}
    else:
        # Game format: -1=mine, 0-8=neighbour count
        rows, cols = np.where(grid < 0)
        mine_pos = {(int(c), int(r)) for r, c in zip(rows, cols)}

    board = Board(w, h, mine_pos)

    # Validate neighbour counts only for game format (pipeline boards don't store them)
    if not is_pipeline_format:
        for y in range(h):
            for x in range(w):
                if not board._mine[y, x]:
                    if int(grid[y, x]) != int(board._neighbours[y, x]):
                        raise ValueError(
                            f"Neighbour mismatch at ({x},{y}): file={grid[y,x]}, "
                            f"computed={board._neighbours[y,x]}"
                        )
    return board


def load_board_from_pipeline(image_path: str, board_w: int = 30,
                              seed: int = 42) -> Board:
    """
    Run the MineStreakerContrastCampaign pipeline to produce a Board from an image.
    Falls back to a random board if imports fail.
    """
    import sys as _sys
    _backup = _sys.path.copy()
    try:
        project = str(Path(__file__).resolve().parents[1])
        if project not in _sys.path:
            _sys.path.insert(0, project)

        # ── Imports from the pipeline ──
        from core import load_image_smart, compute_asymmetric_weights
        from sa import run_sa
        from corridors import build_adaptive_corridors
        from repair import run_phase1_repair
        from board_sizing import derive_board_from_width

        info = derive_board_from_width(image_path, board_w)
        board_h: int = info["board_height"]

        # ── Image → target + weights ──
        target = load_image_smart(image_path, board_w, board_h,
                                  invert=True, contrast_factor=2.0)
        weights = compute_asymmetric_weights(target)

        # ── Corridors (mine-free paths) ──
        forbidden, *_ = build_adaptive_corridors(target, border=3)

        # ── Simulated Annealing ──

        # Seed grid on allowed cells
        avail = np.argwhere(forbidden == 0)
        rng = np.random.default_rng(seed)
        density = 0.15
        n_init = min(max(1, int(board_w * board_h * density)), len(avail))
        idx = rng.choice(len(avail), size=n_init, replace=False)
        grid = np.zeros((board_h, board_w), dtype=np.int8)
        for k in idx:
            grid[avail[k, 0], avail[k, 1]] = 1

        from sa import default_config as _sa_cfg
        params = _sa_cfg(board_w, board_h, seed)
        grid, *_ = run_sa(params["kernel"], grid, target, weights, forbidden, **params["sa"])
        grid[forbidden == 1] = 0

        # ── Repair ──
        grid = run_phase1_repair(
            grid, target, weights, forbidden,
            time_budget_s=90.0,
            max_rounds=300,
        ).grid

        # ── Extract mines ──
        positions: Set[Tuple[int, int]] = set()
        for ry in range(board_h):
            for rx in range(board_w):
                if grid[ry, rx] == 1:
                    positions.add((rx, ry))

        if not positions:
            raise RuntimeError("Pipeline produced 0 mines")

        return Board(board_w, board_h, positions)

    except Exception as exc:
        print(f"[WARN] MineStreaker pipeline failed ({exc}); falling back to random.")
        traceback.print_exc()
        c = max(1, board_w * board_h // 8)
        mp = place_random_mines(board_w, board_h, c, seed=seed)
        return Board(board_w, board_h, mp)
    finally:
        _sys.path = _backup


# ═══════════════════════════════════════════════════════════════════════════════
#  Game Engine — Ties Board + Input → State Transitions
# ═══════════════════════════════════════════════════════════════════════════════

class MoveResult:
    """Outcome of a single player action."""
    __slots__ = ("success", "hit_mine", "newly_revealed", "flagged", "state",
                 "score_delta", "streak", "penalty")

    def __init__(self, *, success=True, hit_mine=False, newly_revealed=None,
                 flagged=False, state: str = "playing",
                 score_delta: int = 0, streak: int = 0, penalty: int = 0):
        self.success = success
        self.hit_mine = hit_mine
        self.newly_revealed: List[Tuple[int, int]] = newly_revealed or []
        self.flagged = flagged
        self.state = state
        self.score_delta = score_delta   # net score change this action
        self.streak = streak             # streak count after this action
        self.penalty = penalty           # non-zero when mine was hit


class GameEngine:
    """
    Pure-logic Minesweeper engine.

    Parameters
    ----------
    mode : "random" | "image" | "npy"
    width, height, mines : for random mode
    image_path : for image mode
    npy_path : for npy mode
    seed : reproducibility
    """

    DIFFICULTIES = {
        "easy":   (9,  9,  10),
        "medium": (16, 16, 40),
        "hard":   (30, 16, 99),
    }

    def __init__(self, mode: str = "random", width: int = 16, height: int = 16,
                 mines: int = 0, image_path: str = "", npy_path: str = "",
                 seed: int = 42):
        self.seed = seed
        self.mode = mode
        self.image_path = image_path if mode == "image" else ""
        self.npy_path = npy_path if mode == "npy" else ""

        if mode == "npy" and npy_path:
            self.board = load_board_from_npy(npy_path)
        elif mode == "image" and image_path:
            self.board = load_board_from_pipeline(image_path, width, seed)
        else:
            c = mines if mines > 0 else max(1, width * height // 6)
            mp = place_random_mines(width, height, c, seed=seed)
            self.board = Board(width, height, mp)

        self._first_click = True
        self._start_time: float = 0.0
        self._paused_elapsed: float = 0.0

        # Scoring state
        self.score: int = 0
        self.streak: int = 0
        self.mine_flash: dict = {}   # (x,y) → expiry time (monotonic); read by renderer

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self):
        self._first_click = True
        self._start_time = time.time()
        self._paused_elapsed = 0.0

    @property
    def elapsed(self) -> float:
        if self._start_time > 0 and not self.board.game_over:
            return time.time() - self._start_time
        return self._paused_elapsed

    def stop_timer(self):
        self._paused_elapsed = self.elapsed
        self._start_time = 0.0

    @property
    def state(self) -> str:
        """Expose board state: 'playing' | 'won'."""
        return self.board._state

    @property
    def streak_multiplier(self) -> float:
        """Score multiplier based on current streak."""
        for threshold, mult in STREAK_TIERS:
            if self.streak >= threshold:
                return mult
        return 1.0

    # ── Difficulty helpers ─────────────────────────────────────────────

    @classmethod
    def from_difficulty(cls, diff: str, seed: int = 42) -> "GameEngine":
        w, h, m = cls.DIFFICULTIES.get(diff, cls.DIFFICULTIES["medium"])
        return cls(mode="random", width=w, height=h, mines=m, seed=seed)

    # ── Player Actions ─────────────────────────────────────────────────

    def left_click(self, x: int, y: int) -> MoveResult:
        """Reveal (x, y). First click is always safe. Mine hit = penalty, not game over."""
        board = self.board

        if self._first_click:
            self._first_click = False
            self._start_time = time.time()

            if board._mine[y, x]:
                # Regenerate around the click
                mp = place_random_mines(
                    board.width, board.height, board.total_mines,
                    safe_x=x, safe_y=y, seed=self.seed + 1)
                self.board = Board(board.width, board.height, mp)
                board = self.board

        hit, revealed = board.reveal(x, y)

        score_delta = 0
        penalty = 0
        if hit:
            # Score penalty; mark flash; reset streak
            penalty = MINE_HIT_PENALTY
            self.score = max(0, self.score - penalty)
            score_delta = -penalty
            self.streak = 0
            self.mine_flash[(x, y)] = time.monotonic() + 1.5   # 1.5 s flash
        else:
            # Award points for each newly revealed cell
            mult = self.streak_multiplier
            for rx, ry in revealed:
                n = int(board._neighbours[ry, rx])
                pts = int(REVEAL_POINTS[n] * mult)
                self.score += pts
                score_delta += pts
            if revealed:
                self.streak += 1

            if board.is_won:
                self.stop_timer()

        return MoveResult(hit_mine=hit, newly_revealed=revealed, state=board._state,
                          score_delta=score_delta, streak=self.streak, penalty=penalty)

    def right_click(self, x: int, y: int) -> MoveResult:
        board = self.board
        was_flagged = bool(board._flagged[y, x])
        placed = board.toggle_flag(x, y)

        score_delta = 0
        mult = self.streak_multiplier
        if placed == "flag":
            if board._mine[y, x]:
                pts = int(CORRECT_FLAG_BONUS * mult)
                self.score += pts
                score_delta = pts
            else:
                self.score = max(0, self.score - WRONG_FLAG_PENALTY)
                score_delta = -WRONG_FLAG_PENALTY
        elif placed == "question" and was_flagged:
            # Reversing a flag — reverse the original score change
            if board._mine[y, x]:
                self.score = max(0, self.score - CORRECT_FLAG_BONUS)
                score_delta = -CORRECT_FLAG_BONUS
            else:
                self.score += WRONG_FLAG_PENALTY
                score_delta = WRONG_FLAG_PENALTY

        if board.is_won:
            self.stop_timer()

        return MoveResult(flagged=placed, state=board._state,
                          score_delta=score_delta, streak=self.streak)

    def middle_click(self, x: int, y: int) -> MoveResult:
        hit, revealed = self.board.chord(x, y)
        board = self.board

        score_delta = 0
        penalty = 0
        if hit:
            penalty = MINE_HIT_PENALTY
            self.score = max(0, self.score - penalty)
            score_delta = -penalty
            self.streak = 0
            # Flash all mines that were just hit via chord
            for rx, ry in revealed:
                if board._mine[ry, rx]:
                    self.mine_flash[(rx, ry)] = time.monotonic() + 1.5
        else:
            mult = self.streak_multiplier
            for rx, ry in revealed:
                n = int(board._neighbours[ry, rx])
                pts = int(REVEAL_POINTS[n] * mult)
                self.score += pts
                score_delta += pts
            if revealed:
                self.streak += 1
            if board.is_won:
                self.stop_timer()

        return MoveResult(hit_mine=hit, newly_revealed=revealed, state=board._state,
                          score_delta=score_delta, streak=self.streak, penalty=penalty)

    def restart(self, width=None, height=None, mines=None):
        self._first_click = True
        self._start_time = 0.0
        self._paused_elapsed = 0.0
        self.seed += 1
        self.score = 0
        self.streak = 0
        self.mine_flash = {}
        if self.mode == "npy" and self.npy_path:
            self.board = load_board_from_npy(self.npy_path)
        elif self.mode == "image" and self.image_path:
            self.board = load_board_from_pipeline(
                self.image_path, width or self.board.width, self.seed)
        else:
            w = width or self.board.width
            h = height or self.board.height
            m = mines if mines is not None else self.board.total_mines
            mp = place_random_mines(w, h, m, seed=self.seed)
            self.board = Board(w, h, mp)


# ── Quick correctness test ──────────────────────────────────────────────────

if __name__ == "_test_engine":
    eng = GameEngine(mode="random", width=9, height=9, mines=10, seed=42)
    eng.start()

    # Click centre — should be safe
    r = eng.left_click(4, 4)
    assert not r.hit_mine, "First click hit a mine!"
    print(f"First click OK, revealed {len(r.newly_revealed)} cells")

    # Flag some cells
    r2 = eng.right_click(0, 0)
    assert r2.flagged is True
    r3 = eng.right_click(0, 0)
    assert r3.flagged is False
    print("Flag toggle OK")

    print(f"Difficulty preset easy: {GameEngine.DIFFICULTIES['easy']}")
    print("Engine self-test PASSED")