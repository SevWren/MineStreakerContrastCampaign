# Gameplay Visual Improvement Ideas
## Solved Board vs. Source Image Resemblance — Gap Analysis

**Author:** Claude Sonnet 4.6 — visual forensic audit
**Date:** 2026-05-10
**Branch:** `frontend-game-mockup`
**Source files audited:** `gameworks/renderer.py` (full read), `gameworks/engine.py` (board data model)
**Reference images:** Original B&W comic ink illustration (1792×2400) + in-game solved board screenshot (1456×816)

---

## Foundational Premise

The MineStreaker pipeline encodes the source image's tonal map directly into mine density.
This is the core invariant that makes image reconstruction possible:

```
Dark pixel in source  →  dense mine placement  →  high neighbour_mines (5–8) on surrounding cells
Light pixel in source →  sparse mine placement →  low  neighbour_mines (0–2) on surrounding cells
```

Every revealed cell already carries the luminance information needed to reconstruct the image
pixel-by-pixel. `board._neighbours[y, x]` IS the grayscale pixel value for that tile position.
The entire reconstruction problem is therefore a **rendering problem, not a data problem.**
No engine changes are required — all fixes are in `renderer.py`.

---

## Source Image Characteristics (Reference)

The reference is a high-contrast black-and-white comic/ink illustration — two subjects taking
a selfie at a wedding reception.

**Tonal distribution (approximate):**
- ~30 % pure white — skin highlights, tablecloth, wall panels, dress fabric
- ~35 % pure black — hair mass, deep jacket shadows, heavy ink fills
- ~35 % crosshatch midtones — hatched skin, shadow gradients, fabric folds

**Key spatial observations:**
- No true photographic grays exist — midtones are simulated by crosshatch ink density
- Hard edges everywhere — maximum contrast at every subject boundary
- Large contiguous black regions: hair (upper-left), jacket body (lower-center)
- Large contiguous white regions: tablecloth (center), bright wall (upper-right)
- Transition zones are narrow — the image is bimodal (mostly black or white, thin midtone band)

This bimodal structure means a neighbour-count → luminance mapping that is slightly
contrast-boosted (dark values pushed darker, light values pushed lighter) will produce
a more faithful reconstruction than a linear 0–8 → 255–0 ramp.

---

## Current Rendering State (What the Board Shows Today)

| Element | Current value | Visual result |
|---|---|---|
| Revealed cell background | `(12, 12, 16)` — same for ALL cells regardless of neighbour count | Uniform near-black — all tonal information erased |
| Number text (1–8) | Saturated colors: blue, green, red, purple, pink, cyan | Colored pixel noise at zoom-out; incoherent against dark bg |
| Flagged mine background | `(48, 48, 64)` — medium blue-gray | Lighter than safe cells — luminance inverted vs. source |
| Flag triangle | `(235, 210, 210)` — pale near-white | Brightest element on board; mine areas should be darkest |
| Cell border | `(60, 60, 80)` 1px on every cell unconditionally | Blue-gray mesh dominates at zoom-out (occupies 75 % of 2px tile) |
| Board panel bg | `(28, 28, 38)` with `(60, 60, 80)` outline | Colored frame around the reconstruction area |

**Net effect at zoom-out:** A dark uniform field covered in a blue-gray grid mesh with
scattered colored number specks and bright-white flag triangles. Bears no resemblance to
the source image.

---

## Gap 1 — Revealed Cell Background: The Primary Failure

**Severity:** CRITICAL
**File:** `gameworks/renderer.py`
**Function:** `_draw_cell()`
**Line:** 960

### Current code

```python
bg = C["red"] if _flashing else C["tile_reveal"]
pygame.draw.rect(self._win, bg, (px, py, ts, ts))
```

`C["tile_reveal"] = (12, 12, 16)` is applied to **every** revealed cell regardless of
`neighbour_mines`. The neighbour value is present as a parameter but is used only to
select number text — never to influence the background color.

### Why this is catastrophic

The neighbour count is the image. Setting every background to `(12,12,16)` is equivalent
to replacing the source image with a solid black rectangle. All tonal structure — the
white tablecloth, the light skin, the dark hair — is collapsed to a single value.

### Required mapping

The curve is gamma-boosted to match the bimodal ink-art distribution: the midpoint (count 4)
maps to a medium-dark gray rather than 50 % gray, reflecting that the source image spends
more area in black and white than in midtone.

| `neighbour_mines` | Represents in source image | Required background color |
|---|---|---|
| 0 | Empty white page, zero ink coverage | `(245, 245, 245)` |
| 1 | Single faint crosshatch stroke | `(210, 210, 210)` |
| 2 | Light hatching, sparse ink | `(168, 168, 168)` |
| 3 | Medium crosshatch | `(126, 126, 126)` |
| 4 | Dense crosshatch / medium shadow | `(88,  88,  88)` |
| 5 | Heavy shadow hatching | `(58,  58,  58)` |
| 6 | Near-solid ink fill | `(34,  34,  34)` |
| 7 | Solid black fill | `(16,  16,  16)` |
| 8 | Maximum ink density, pure black | `(4,   4,   4)` |

### Proposed implementation sketch

```python
# Pre-compute once outside the cell loop (in _draw_board, passed in as solved_bgs lookup)
SOLVED_BG = [
    (245,245,245),  # 0
    (210,210,210),  # 1
    (168,168,168),  # 2
    (126,126,126),  # 3
    ( 88, 88, 88),  # 4
    ( 58, 58, 58),  # 5
    ( 34, 34, 34),  # 6
    ( 16, 16, 16),  # 7
    (  4,  4,  4),  # 8
]

# Inside _draw_cell(), when is_solved is True:
bg = SOLVED_BG[int(neighbour_mines)] if is_solved else (C["red"] if _flashing else C["tile_reveal"])
pygame.draw.rect(self._win, bg, (px, py, ts, ts))
```

### Expected visual result

At 1×1 px per tile (300×402 board fully zoomed out), each cell becomes one pixel.
The board renders as a 300×402 grayscale halftone reconstruction of the source:
- Hair mass → contiguous black cluster
- Tablecloth → white rectangle
- Skin zones → mid-gray gradient
- Crosshatch areas → dithered intermediate values

---

## Gap 2 — Number Text: Chromatic Noise Destruction

**Severity:** CRITICAL
**File:** `gameworks/renderer.py`
**Functions:** `_rebuild_num_surfs()` (lines 416–427), `_draw_cell()` (lines 964–969)

### Current code

```python
# _rebuild_num_surfs():
self._num_surfs = {
    n: font.render(str(n), True, NUM_COLS[n])
    for n in range(1, 9)
}

# _draw_cell():
elif neighbour_mines > 0:
    num_surf = self._num_surfs.get(int(neighbour_mines))
    if num_surf:
        self._win.blit(num_surf, num_surf.get_rect(center=(px + ts//2, py + ts//2)))
```

`NUM_COLS = [None, blue(55,120,220), green(70,175,70), red(215,55,55), purple(95,55,175),`
`           pink(175,45,115), cyan(55,175,175), near-black(25,25,25), gray(95,95,105)]`

### Two distinct failure modes

**Failure A — Color inconsistency with grayscale reconstruction.**
After Gap 1 is applied, a 0-count cell has background `(245,245,245)`. A 1-count cell has
background `(210,210,210)`. Number "1" is rendered in `(55,120,220)` blue. This creates a
high-contrast blue speck on a light-gray background — the number text actively fights the
grayscale tonal map instead of contributing to it.

Conversely, number "7" is `(25,25,25)` near-black rendered on a `(16,16,16)` near-black
background — invisible, serving no purpose.

**Failure B — Physical illegibility at zoom-out.**
At tile size 1–3px, each number surface is scaled to sub-pixel dimensions. The number glyph
is not rendered — only its dominant color bleeds through as a single colored pixel. Number
text therefore contributes zero informational value on the solved board and introduces
chromatic noise (RGB speckle over the grayscale reconstruction).

### Required change

On `game_state == "won"`, **suppress all number rendering entirely.** The `elif neighbour_mines > 0`
block in `_draw_cell()` should not execute when `is_solved` is True.

The cell background from Gap 1 carries the complete tonal information for the reconstruction.
Number text is redundant on the solved board and destructive to image fidelity.

### Cache architecture note

`_rebuild_num_surfs()` builds one dict keyed by digit. If numbers are fully suppressed in
won state, no second cache is needed. The suppression is a conditional skip, not a palette
swap. No structural changes to the cache are required.

### Active play note

During active play (not won), the colored number palette serves the standard Minesweeper
readability purpose and should be preserved. The suppression is gated on `is_solved` only.

---

## Gap 3 — Flagged Mine Cells: Luminance Inversion

**Severity:** CRITICAL
**File:** `gameworks/renderer.py`
**Function:** `_draw_cell()` (lines 970–975), `_draw_flag()` (lines 1012–1022)

### Current code

```python
elif is_flagged:
    if fog:
        pygame.draw.rect(self._win, C["tile_hidden"], (px, py, ts, ts))
    else:
        pygame.draw.rect(self._win, C["tile_flag"], (px, py, ts, ts))
    self._draw_flag(px, py, ts)
```

```python
# _draw_flag():
pygame.draw.line(self._win, C["flag_pole"], ...)          # (200, 200, 200) — light gray
pygame.draw.polygon(self._win, C["flag_red"], pts)         # (235, 210, 210) — pale near-white
```

`C["tile_flag"] = (48, 48, 64)` — medium blue-gray background
`C["flag_red"]  = (235, 210, 210)` — pale near-white triangle
`C["flag_pole"] = (200, 200, 200)` — light gray pole

### Why this is a critical inversion

Mines are placed in the **darkest regions** of the source image — the heavy ink fills, the
solid black hair, the deep shadow pools. A correctly-flagged mine cell represents a location
that, in the source image, is near-pure black.

Current rendering makes flagged mines the **brightest elements** on the board:
- Background `(48,48,64)` is **lighter** than the near-black `(12,12,16)` revealed cell background
- Triangle `(235,210,210)` is **near-white** — visually the loudest mark on screen
- The pole at `(200,200,200)` adds further white luminance

This is a direct luminance inversion. The darkest image regions are being displayed as
the lightest board elements. Hair mass and jacket — which should reconstruct as solid black —
are scattered with bright-white triangles.

### Required change on solved board

```python
# On game_state == "won":
elif is_flagged:
    pygame.draw.rect(self._win, (0, 0, 0), (px, py, ts, ts))
    # No _draw_flag() call — suppress triangle and pole entirely
```

Mine cells → pure black rectangle, no decoration.

Result: Mine positions (the darkest source image areas) reconstruct correctly as black pixels.

### Active play preservation

During active play the pale flag on dark background is a legible, distinct marker. The full
`_draw_flag()` call should be preserved for `game_state != "won"`. Change is gated on
`is_solved` only.

---

## Gap 4 — Cell Borders: Grid Mesh Overwrites Reconstruction

**Severity:** HIGH
**File:** `gameworks/renderer.py`
**Function:** `_draw_cell()` (lines 986–997)

### Current code

```python
if in_anim:
    pygame.draw.rect(self._anim_surf, (*C["border"], 60), (0, 0, ts, ts), 1, ...)
    self._win.blit(self._anim_surf, (px, py))
else:
    pygame.draw.rect(self._win, C["border"], (px, py, ts, ts), 1, ...)
```

`C["border"] = (60, 60, 80)` — medium blue-gray, 1px width, drawn on **every cell unconditionally.**

### Quantified impact at zoom-out

| Tile size (px) | Cell area (px²) | Border pixels | Border occupancy |
|---|---|---|---|
| 8 | 64 | 28 | 44 % |
| 4 | 16 | 12 | 75 % |
| 2 | 4 | 4 | 100 % |
| 1 | 1 | 1 | 100 % |

At tile sizes of 2–4px (the zoom-out level visible in the screenshot), the `(60,60,80)`
border occupies the majority of each cell's pixel real estate. The entire board becomes a
uniform blue-gray mesh regardless of what background color Gap 1 applies. Even with Gaps 1–3
fully implemented, the border mesh would dominate the visual and destroy the reconstruction.

### Required change on solved board

Skip the entire border block when `is_solved` is True:

```python
if not is_solved:
    if in_anim:
        ...anim border...
    else:
        pygame.draw.rect(self._win, C["border"], (px, py, ts, ts), 1, ...)
```

No border = clean pixel array = unobstructed image reconstruction.

### Active play preservation

Borders provide essential cell separation for readability at normal play zoom levels.
Keep unconditionally for `game_state != "won"`.

---

## Gap 5 — Image Ghost Overlay: Alpha and Color Consistency

**Severity:** HIGH (image mode only)
**File:** `gameworks/renderer.py`
**Function:** `_draw_image_ghost()` (lines 1058–1092)

### Current behavior

During gameplay, the source image is rendered underneath flagged cells:
- Correctly-flagged mines: source image tile at `alpha=200` (nearly opaque)
- Wrongly-flagged cells: source image tile at `alpha=40` (very faint hint)

### Failure A — Alpha 200 partially un-does the Gap 3 fix

With the Gap 3 fix applied (mine cells → black background), the ghost at `alpha=200` blends
the source image over the black fill. For a white source pixel at a mine position:
```
(0,0,0) × (55/255) + (255,255,255) × (200/255) ≈ (200, 200, 200)
```
The result is near-white — appropriate for white-sourced mine cells. For a black source
pixel at a mine position:
```
(0,0,0) × (55/255) + (0,0,0) × (200/255) = (0, 0, 0)
```
Pure black — also correct. The alpha blend is directionally consistent with the
reconstruction goal, but the 200/255 opacity was tuned for during-play hint visibility, not
post-solve image fidelity.

### Required change on solved board

On `game_state == "won"`, render ghost at `alpha=255` for mine cells (full source image
opacity). The during-play hint value of 200 is intentionally below 255 to avoid spoiling
the board; post-solve there is no reason to withhold.

### Failure B — Color source image vs. grayscale reconstruction theme

The source image is stored as RGB. The reference image (Image 1) is B&W comic art, so
its RGB values are near-greyscale `(r ≈ g ≈ b)`. For this specific source the ghost blit
will appear grayscale in practice. However, if a color photograph is used as source, the
ghost blits will be color while the revealed safe cells are grayscale (Gap 1), creating
a visual inconsistency.

Long-term: desaturate the ghost surface on construction for won-state rendering.
Short-term: acceptable for the current B&W source.

---

## Gap 6 — `_draw_cell()` Receives No Game State: Structural Blocker

**Severity:** HIGH (structural prerequisite for Gaps 1–4)
**File:** `gameworks/renderer.py`
**Functions:** `_draw_board()` (line 899), `_draw_cell()` (line 933)

### Current signature

```python
def _draw_cell(self,
               x, y,
               is_mine, is_revealed, is_flagged, is_questioned,
               neighbour_mines,
               pos, in_anim, is_pressed,
               fog, ts, in_win_anim, now):   # 14 parameters — no game_state
```

`game_state` is a parameter of `_draw_board()` but is never forwarded into `_draw_cell()`.
Every change in Gaps 1–4 requires knowing whether the board is solved. Without this,
`_draw_cell()` cannot conditionally switch rendering modes.

### Options

**Option A — Add `is_solved: bool` as a 15th parameter (recommended)**
```python
def _draw_cell(self, ..., now, is_solved: bool = False):
```
Called from `_draw_board()` with `is_solved = (game_state == "won")`. Minimal, targeted,
no state stored on the renderer object.

**Option B — Store `self._game_state` on the renderer**
Set `self._game_state = game_state` at the top of `draw()` and read it inside `_draw_cell()`.
Avoids signature change but adds mutable renderer state that must be kept in sync.

**Option C — Pre-compute `solved_bg` lookup and pass it**
Pass `solved_bg: Optional[tuple] = None` where the tuple is the pre-looked-up background
color for this cell's neighbour count. Avoids per-cell dict lookup inside `_draw_cell()`.

Option A is the cleanest for a targeted change. Option C is the highest performance.

---

## Gap 7 — Board Panel Background Bleeds Into Reconstruction Area

**Severity:** MEDIUM
**File:** `gameworks/renderer.py`
**Function:** `_draw_board()` (lines 847–849)

### Current code

```python
br = pygame.Rect(ox - 6, oy - 6, bw + 12, bh + 12)
rrect(self._win, C["panel"], br, max(4, ts // 3))
pygame.draw.rect(self._win, C["border"], br, 2, border_radius=max(4, ts // 3))
```

`C["panel"] = (28, 28, 38)` drawn 6px outside the board with a `(60, 60, 80)` outline.

### Failure

On the solved board, 0-count cells at the board edge will be `(245,245,245)` near-white
(Gap 1). The `(60,60,80)` border outline immediately adjacent creates a visible colored
frame around the white board edge, inconsistent with the grayscale reconstruction theme.

### Required change on solved board

Replace the panel background and border with values that blend with the reconstruction:
- Background: `C["bg"] = (18,18,24)` or pure `(0,0,0)` — matches the darkest board cells
- Border: `(20,20,20)` or suppress entirely

---

## Gap 8 — Win Animation Reveals Color Source Before Settled State

**Severity:** MEDIUM (image mode only)
**File:** `gameworks/renderer.py`
**Function:** `_draw_win_animation_fx()` (lines 1218–1240)

### Current behavior

During win animation, each progressively-revealed flag shows the source image tile at
`alpha=255`:
```python
sub.set_alpha(255)
self._win.blit(sub, (px, py))
```

### Issue

The win animation correctly reveals the source image tile-by-tile. Once `win_anim.done`
is True, this function is no longer called and the settled state falls back to standard
`_draw_cell()` rendering. There is no persisted conflict with the Gap 3 fix.

However, during the animation, mine cells show the full-color source image while revealed
safe cells (Gap 1) show grayscale backgrounds. This creates a transient split-mode visual:
color image tiles on mine cells, grayscale tonal cells on safe cells.

For the reference B&W source this is acceptable since the image IS greyscale.
For a color source, the transition looks inconsistent.

### Recommended change (low priority)

Desaturate the `sub` surface before blitting during win animation:
```python
# Convert to grayscale by averaging channels (or using pygame.transform)
# This matches the grayscale reconstruction theme on safe cells
```

---

## Gap 9 — Panel Text: Size, Overflow, and DEV Section Overlap

**Severity:** MEDIUM (UX — independent of image reconstruction)
**File:** `gameworks/renderer.py`
**Function:** `_draw_panel()` (lines 1095–1204)

### Failure A — Fixed font sizes regardless of window/board size

`_font_small` and `_font_tiny` are initialized at fixed pixel sizes. On large boards
(300×402) where the panel is forced into overlay mode, all text is rendered at the same
size as on a 9×9 board. At 1456×816 window resolution the panel stats become illegible.

Font sizes should scale with `PANEL_W` or window height, with a minimum floor of ~11px.

### Failure B — Stats block overflows on large boards

Stats layout:
```
sy = self._btn_restart.bottom + 12   # starts immediately below last button
```
Stats require approximately `5 lines × 16px + 7 tips × 14px + mode badge = ~195px`.
When `_btn_restart.bottom` is positioned near the bottom of the visible panel area (as
happens with tall boards), the stats overflow past the window bottom.

### Failure C — DEV section overlaps stats when `_show_dev = True`

The DEV button is positioned at:
```python
self._btn_dev_solve.y = oy + (btn_h + gap) * 5 + gap * 3
```
The stats block starts at `_btn_restart.bottom + 12` which may be positioned **above** the
DEV section on certain window configurations. The two sections share no awareness of each
other's layout, causing text collision.

### Required changes

1. Derive font size from `max(10, PANEL_W // 18)` or similar responsive formula
2. Clip stats/tips rendering to the panel's visible vertical extent
3. Add the DEV section height into the stats `sy` offset when `_show_dev` is True:
   ```python
   dev_height = (btn_h + gap) if self._show_dev else 0
   sy = max(self._btn_restart.bottom, self._btn_dev_solve.bottom) + 12
   ```

---

## Prioritized Implementation Roadmap

The items below are ordered by combined impact on image reconstruction quality and
implementation risk. Each is independently deliverable.

| Priority | Gap | Description | Impact on reconstruction | Estimated risk |
|---|---|---|---|---|
| 1 | Gap 6 | Add `is_solved` param to `_draw_cell()` | Structural prerequisite | Low |
| 2 | Gap 1 | Per-cell bg from `neighbour_mines` on solved board | Highest — restores full tonal map | Medium |
| 3 | Gap 3 | Flagged mine cells → pure black, no triangle on solved board | High — fixes luminance inversion | Low |
| 4 | Gap 2 | Suppress number text rendering on solved board | High — removes chromatic noise | Low |
| 5 | Gap 4 | Suppress cell borders on solved board | High — removes mesh at zoom-out | Low |
| 6 | Gap 7 | Board panel bg → neutral on solved board | Medium — removes colored frame | Low |
| 7 | Gap 5 | Ghost alpha=255 on won state | Medium — full image on mine cells | Low |
| 8 | Gap 8 | Desaturate win animation blits | Low — transient animation only | Low |
| 9 | Gap 9 | Panel text size / overflow / DEV overlap | UX — independent of reconstruction | Medium |

Gaps 1–5 together constitute the complete minimum viable reconstruction fix. Implementing
all five collapses the board into a clean grayscale halftone of the source image at zoom-out.
Gaps 6–9 are refinements.

---

## Expected Visual Result After All Fixes

With Gaps 1–5 implemented on the 300×402 board:

| Cell type | Before | After |
|---|---|---|
| 0-count revealed | `(12,12,16)` near-black, no number | `(245,245,245)` white, no number, no border |
| 4-count revealed | `(12,12,16)` near-black, colored "4" | `(88,88,88)` medium gray, no number, no border |
| 8-count revealed | `(12,12,16)` near-black, near-invisible "8" | `(4,4,4)` near-black, no number, no border |
| Flagged mine | `(48,48,64)` + pale white triangle | `(0,0,0)` pure black, no decoration |

At full zoom-out (1px per tile), the board becomes a **300×402 grayscale pixelated
reconstruction of the source image**:
- Hair mass → solid black cluster upper-left
- Tablecloth → white horizontal band center
- Deep jacket shadow → black zone lower-center
- Skin and light fabric → mid-gray gradient zones
- Crosshatch skin areas → dithered intermediate values matching ink density

The tonal fidelity of the reconstruction is bounded by the board resolution (300×402 px)
and the accuracy of the pipeline's mine placement relative to the source image's luminance.
All rendering-side information loss is eliminated.

---

## Files Requiring Changes

| File | Functions | Gaps addressed |
|---|---|---|
| `gameworks/renderer.py` | `_draw_cell()` | 1, 2, 3, 4, 6 |
| `gameworks/renderer.py` | `_draw_board()` | 7 |
| `gameworks/renderer.py` | `_draw_image_ghost()` | 5 |
| `gameworks/renderer.py` | `_draw_win_animation_fx()` | 8 |
| `gameworks/renderer.py` | `_draw_panel()` | 9 |

No changes required to `engine.py`. All data is already present and correct.

---

*Gameworks v0.1.1 — part of the Mine-Streaker project.*
