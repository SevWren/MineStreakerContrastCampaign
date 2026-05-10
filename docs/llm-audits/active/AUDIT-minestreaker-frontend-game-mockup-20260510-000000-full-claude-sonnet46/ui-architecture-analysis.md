# UI Architecture Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## UI Component Inventory

| Component | Implementation | Issues |
|---|---|---|
| Window | Renderer._win — pygame RESIZABLE | Correct |
| Header bar | _draw_header() | Emoji 💣⏱ font-dependent |
| Smiley button | _draw_smiley() — primitive draw | Correct |
| Mine counter | Font render in header | Correct |
| Timer | Font render in header | Correct |
| Board grid | _draw_board() — viewport culled | Correct |
| Cell tiles | _draw_cell() — pygame.draw.rect | Correct |
| Mine glyph | _draw_mine() — circle + spikes | Correct |
| Flag glyph | _draw_flag() — line + polygon | Correct |
| Question mark | _draw_question() — font render | Correct |
| Number glyphs | Font render with color map | Correct |
| Panel (right/bottom) | _draw_panel() | btn_w crash when image |
| 5 Buttons (pill shape) | pill() function | Correct |
| Stats text | Font render list | Correct |
| Tips text | Font render list | Correct |
| Image thumbnail | smoothscale + blit | btn_w crash |
| Fog overlay | _draw_overlay() | Broken — wrong attribute |
| Help modal | _draw_help() | Correct |
| Victory modal | _draw_modal() | Correct |
| Defeat modal | _draw_modal() | Correct |
| Win animation | _draw_win_animation_fx() | Perf issue |
| Reveal cascade | AnimationCascade | Correct |
| Image ghost | _draw_image_ghost() | Critical perf |
| Hover highlight | SRCALPHA surface per frame | Minor |

## Layout Modes

1. **Right-panel** (small boards, w_cols < 100): Panel on right side
2. **Bottom-panel** (large boards, w_cols ≥ 100): Panel below board

Default board is 300×370 → bottom-panel mode.

## Accessibility Gaps
- No keyboard navigation for cell selection (only panning)
- No screen reader support
- No high-contrast mode
- No color-blind mode (numbers use color-coded hues only)
- Emoji in HUD not guaranteed to render
