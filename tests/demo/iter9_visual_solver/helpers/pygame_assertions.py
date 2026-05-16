"""Shared pygame/rendering assertions."""

from __future__ import annotations


def assert_surface_size(testcase, surface, width: int, height: int) -> None:
    testcase.assertEqual(tuple(surface.size), (int(width), int(height)))


def assert_pixel_rgb(testcase, surface, x: int, y: int, rgb: tuple[int, int, int]) -> None:
    getter = getattr(surface, "get_at", None)
    if getter is None:
        testcase.skipTest("Surface does not expose get_at")
    testcase.assertEqual(tuple(getter((x, y))[:3]), tuple(rgb))


def assert_window_geometry_fits_screen(testcase, geometry, screen_width: int, screen_height: int) -> None:
    testcase.assertLessEqual(geometry.window_width, int(screen_width))
    testcase.assertLessEqual(geometry.window_height, int(screen_height))
