"""Tests for pygame adapter seam."""

from __future__ import annotations

import unittest

from tests.demo.iter9_visual_solver.fixtures.pygame_fakes import FakePygameModule


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


if __name__ == "__main__":
    unittest.main()
