# Gameplay Loop Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Core Loop

```
while game_not_over:
    1. Poll events (pygame.event.get)
    2. Dispatch to Renderer.handle_event() → action string
    3. Apply action to GameEngine (left_click/right_click/chord)
    4. Update GameLoop state machine (PLAYING → RESULT)
    5. Draw frame (Renderer.draw())
    6. Tick clock (FPS=60)
```

## Completeness vs GAME_DESIGN.md

| Feature | Spec | Implemented |
|---|---|---|
| Left click reveal | ✓ | ✓ |
| Right click flag cycle (hidden→flag→?→hidden) | ✓ | ✓ |
| Middle click chord | ✓ | ✓ |
| Ctrl+click chord | ✓ | ✓ |
| First click safety | ✓ | ✓ |
| Flood fill on 0-cell | ✓ | ✓ |
| Image ghost overlay | ✓ | ✓ (but performance issues) |
| Win animation (progressive flag reveal) | ✓ | ✓ |
| Loss animation (all mines revealed) | ✓ | ✓ |
| Fog of war toggle | ✓ | ✗ (broken) |
| Save board to .npy | Extension | ✓ |
| Scroll zoom | Extension | ✓ |
| Pan | Extension | ✓ |
| Arrow key pan | Extension | ✓ |
| Scoring system | ✓ in spec | ✗ not implemented |
| Hint system | ✓ in spec | ✗ not implemented |
| Undo | ✓ in spec | ✗ not implemented |
| Timer | ✓ | ✓ |
| Mine counter | ✓ | ✓ |
| Help overlay | Extension | ✓ |

## Win Condition Gap (FIND-STATE-MEDIUM-m007a)

The image-reconstruction mechanic is the core design concept of MineStreaker. Winning by flagging mines is the entire point — each flag reveals a dark pixel of the source image. The current win condition (reveal all safes, no flag check) allows winning without ever seeing the reconstructed image. This must be corrected to fulfill the core game loop.
