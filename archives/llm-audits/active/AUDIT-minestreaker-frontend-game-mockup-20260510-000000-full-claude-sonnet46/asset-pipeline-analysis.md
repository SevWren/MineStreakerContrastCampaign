# Asset Pipeline Analysis
## Audit: AUDIT-minestreaker-frontend-game-mockup-20260510-000000-full-claude-sonnet46

## Assets Inventory

| Asset Type | Count | Usage |
|---|---|---|
| Source images (PNG) | 28 | Pipeline input + game image mode |
| Source images (JPEG) | 5 | Pipeline input + game image mode |
| Canonical source image | 1 (input_source_image.png) | Default pipeline run |
| Research images | 9 (input_source_image_research_irl1-9.png) | Research runs |
| Line art images | 17 (line_art_*) | Research and named runs |

## gameworks Image Asset Flow

```
CLI --image <path>
    │
    └── Renderer.__init__()
         ├── pygame.image.load(image_path).convert_alpha()  [load raw]
         ├── pygame.transform.smoothscale(img, (bw, bh))    [scale to board]
         └── self._image_surf                               [stored once]
              │
              ├── _draw_image_ghost(): pixel-level cell blit [PER FRAME — broken]
              ├── _draw_win_animation_fx(): board-sized blit [per frame during anim]
              └── _draw_panel(): thumbnail blit              [per frame]
```

## Asset Integrity (Pipeline)
`assets/image_guard.py` enforces SHA256 + pixel statistics validation. Canonical images have a manifest file. `--allow-noncanonical` flag bypasses for research images.

## Missing Asset Infrastructure for gameworks
- No sprite sheet / texture atlas
- No sound assets (though GAME_DESIGN.md specifies audio)
- No font assets (uses system Consolas font — not embedded)
