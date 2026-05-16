"""Tests for rendering color palette."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.fixtures.configs import default_demo_config_dict


class ColorPaletteTests(unittest.TestCase):
    def test_color_palette_uses_validated_visual_config(self):
        try:
            from demos.iter9_visual_solver.rendering.color_palette import ColorPalette
        except ModuleNotFoundError:
            self.skipTest("ColorPalette is not implemented yet")
        palette = ColorPalette.from_config(default_demo_config_dict()["visuals"])
        self.assertEqual(palette.flagged_mine_rgb, (255, 80, 40))
        self.assertIsNotNone(palette.unseen_cell_rgb)
        self.assertIsNotNone(palette.safe_cell_rgb)
        self.assertIsNotNone(palette.unknown_cell_rgb)
        self.assertIsNotNone(palette.background_rgb)


if __name__ == "__main__":
    unittest.main()
