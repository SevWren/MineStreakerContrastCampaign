"""Tests for window chrome drawing helpers."""

from __future__ import annotations

import unittest
from pathlib import Path

from demos.iter9_visual_solver.rendering.window_chrome import (
    draw_board_border,
    draw_header_strip,
    draw_vertical_divider,
)
from demos.iter9_visual_solver.rendering.window_geometry import RectSpec
from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter
from tests.demo.iter9_visual_solver.fixtures.pygame_fakes import FakePygameModule, FakeSurface


class WindowChromeTests(unittest.TestCase):
    def test_draw_header_strip_fills_rect_and_blits_text(self):
        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        surface = FakeSurface((100, 50))
        font = adapter.create_font()
        draw_header_strip(
            surface,
            adapter=adapter,
            header_rect=RectSpec(0, 0, 100, 34),
            text="header",
            background_rgb=(1, 1, 1),
            text_rgb=(2, 2, 2),
            font=font,
        )
        self.assertIn(((1, 1, 1), (0, 0, 100, 34)), surface.rect_calls, msg="draw_header_strip must fill the header rect with background_rgb (1,1,1)")
        self.assertTrue(surface.blit_calls, msg="draw_header_strip must blit the rendered text surface")
        rendered_texts = [getattr(src, "text", None) for src, _dest in surface.blit_calls]
        self.assertIn("header", rendered_texts, msg="draw_header_strip must render the text 'header'")

    def test_draw_board_border_and_divider_use_given_rects(self):
        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        surface = FakeSurface((100, 50))
        draw_board_border(surface, adapter=adapter, board_rect=RectSpec(0, 34, 20, 10), border_rgb=(9, 9, 9))
        draw_vertical_divider(surface, adapter=adapter, divider_rect=RectSpec(20, 34, 1, 10), divider_rgb=(8, 8, 8))
        self.assertIn(((9, 9, 9), (0, 34, 20, 10)), surface.rect_calls, msg="draw_board_border must draw rect at (0,34,20,10) with border_rgb (9,9,9)")
        self.assertIn(((8, 8, 8), (20, 34, 1, 10)), surface.rect_calls, msg="draw_vertical_divider must draw rect at (20,34,1,10) with divider_rgb (8,8,8)")

    def test_window_chrome_does_not_import_pygame(self):
        path = Path("demos/iter9_visual_solver/rendering/window_chrome.py")
        self.assertTrue(path.exists(), msg=f"Source file missing: {path}")
        source = path.read_text(encoding="utf-8")
        self.assertNotIn("pygame", source)


if __name__ == "__main__":
    unittest.main()
