# Generated Specifications
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Spec: gameworks/engine.py Public API Contract

```
GameEngine:
  Properties:
    state: str           [MUST expose — currently missing]
    board: Board         [read-only access to current board]
    elapsed: float       [seconds since game start]
    mode: str            ["random" | "image" | "npy"]
    seed: int            [current seed]

  Methods:
    start() → None
    stop_timer() → None
    left_click(x: int, y: int) → MoveResult
    right_click(x: int, y: int) → MoveResult
    middle_click(x: int, y: int) → MoveResult
    restart(width?, height?, mines?) → None
    from_difficulty(diff: str, seed: int) → GameEngine  [classmethod]

Board:
  Properties (read-only):
    width, height: int
    total_mines, total_safe: int
    revealed_count, flags_placed: int
    mines_remaining: int
    correct_flags: int
    is_won, is_lost, game_over: bool

  Methods:
    reveal(x, y) → (hit_mine: bool, newly_revealed: List[Tuple])
    toggle_flag(x, y) → str  ["flag" | "question" | "hidden"]
    chord(x, y) → (hit_mine: bool, newly_revealed: List[Tuple])
    snapshot(x, y) → CellState  [immutable]
    all_mine_positions() → List[Tuple]
    wrong_flag_positions() → List[Tuple]
```

## Spec: gameworks/renderer.py Renderer Contract

```
Renderer:
  Constructor:
    __init__(engine: GameEngine, image_path: Optional[str] = None)

  Public Methods:
    handle_event(ev: pygame.Event) → Optional[str]
      Returns: "quit" | "restart" | "click:x,y" | "flag:x,y" | "chord:x,y" | None
    handle_panel(pos: Tuple) → Optional[str]
      Returns: "restart" | "save" | "quit" | None
    draw(mouse_pos, game_state, elapsed, cascade_done) → None
    start_win_animation() → None
    draw_victory(elapsed: float) → None
    draw_defeat() → None

  Public Attributes:
    fog: bool          [toggleable fog of war]
    help_visible: bool [help overlay]
    cascade: Optional[AnimationCascade]
    win_anim: Optional[WinAnimation]
    _clock: pygame.time.Clock  [owned by renderer]
```

## Spec: GameLoop → Renderer Action Protocol

Action strings returned by handle_event():
- `"quit"` → exit game loop
- `"restart"` → call _start_game()
- `"save"` → call _save_npy()
- `"click:x,y"` → call _do_left_click(x, y)
- `"flag:x,y"` → call _do_right_click(x, y)
- `"chord:x,y"` → call _do_chord(x, y)
- `None` → no action (panning, zoom, drag in progress)
