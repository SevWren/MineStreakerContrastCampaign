"""Tests for pygame adapter seam."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.fixtures.pygame_fakes import FakePygameModule
from demos.iter9_visual_solver.rendering.window_geometry import WindowPlacement


class PygameAdapterContractTests(unittest.TestCase):
    def test_adapter_uses_injected_pygame_module(self):
        try:
            from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter
        except ModuleNotFoundError:
            self.skipTest("PygameAdapter is not implemented yet")
        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        adapter.open_window(width=100, height=50, title="test")
        self.assertEqual(fake.display.created_windows, [(100, 50)])

    def test_get_display_bounds_uses_desktop_sizes(self):
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        fake.display.desktop_sizes = [(1440, 900)]
        bounds = PygameAdapter(pygame_module=fake).get_display_bounds()
        self.assertEqual((bounds.width, bounds.height), (1440, 900))

    def test_open_window_records_centered_placement(self):
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        adapter.open_window(
            width=100,
            height=50,
            title="test",
            placement=WindowPlacement(x=22, y=None, horizontally_centered=True),
        )
        self.assertEqual(fake.display.position_calls, [(22, 0)])

    def test_open_window_uses_pygame_ce_tuple_window_position_signature(self):
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        class TupleOnlyDisplay:
            def __init__(self):
                self.position = None

            def set_window_position(self, position):
                if not isinstance(position, tuple) or len(position) != 2:
                    raise TypeError("set_window_position expects one (x, y) tuple")
                self.position = position

            def set_mode(self, size, flags=0):
                return FakePygameModule().display.set_mode(size, flags)

            def set_caption(self, _title):
                return None

        fake = FakePygameModule()
        fake.display = TupleOnlyDisplay()
        adapter = PygameAdapter(pygame_module=fake)
        adapter.open_window(
            width=100,
            height=50,
            title="test",
            placement=WindowPlacement(x=22, y=11, horizontally_centered=True),
        )
        self.assertEqual(fake.display.position, (22, 11))

    def test_resize_window_reopens_surface_with_resizable_flag(self):
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        adapter.resize_window(width=200, height=120, resizable=True)
        self.assertEqual(fake.display.set_mode_calls[-1], ((200, 120), fake.RESIZABLE))

    def test_resize_event_helpers_support_videoresize(self):
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        event = type("ResizeEvent", (), {"type": fake.VIDEORESIZE, "w": 640, "h": 480})()
        self.assertTrue(adapter.is_resize_event(event))
        self.assertEqual(adapter.get_resize_event_size(event), (640, 480))

    def test_maximize_event_uses_display_bounds_when_event_has_no_size(self):
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        fake.display.desktop_sizes = [(1920, 1080)]
        adapter = PygameAdapter(pygame_module=fake)
        event = type("MaximizeEvent", (), {"type": fake.WINDOWMAXIMIZED})()
        self.assertTrue(adapter.is_resize_event(event))
        self.assertEqual(adapter.get_resize_event_size(event), (1920, 1080))

    def test_draw_rect_backwards_compatible_signature(self):
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        surface = fake.display.set_mode((20, 20))
        PygameAdapter(pygame_module=fake).draw_rect(surface, (1, 2, 3), (0, 0, 5, 5))
        self.assertTrue(surface.rect_calls)

    def test_adapter_creates_scales_and_blits_offscreen_surface(self):
        from demos.iter9_visual_solver.rendering.pygame_adapter import PygameAdapter

        fake = FakePygameModule()
        adapter = PygameAdapter(pygame_module=fake)
        target = fake.display.set_mode((100, 100))
        logical = adapter.create_surface(width=10, height=20)
        scaled = adapter.scale_surface_nearest(logical, width=30, height=60)
        adapter.blit_surface(target, scaled, (5, 6))
        self.assertEqual(logical.get_size(), (10, 20))
        self.assertEqual(fake.transform.scale_calls[-1], (logical, (30, 60)))
        self.assertEqual(target.blit_calls[-1], (scaled, (5, 6)))


if __name__ == "__main__":
    unittest.main()
