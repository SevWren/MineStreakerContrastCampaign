"""Tests for demo CLI commands."""

from __future__ import annotations

from unittest import mock
import unittest

from tests.demo.iter9_visual_solver.builders.config_builder import DemoConfigBuilder
from tests.demo.iter9_visual_solver.builders.grid_builder import GridBuilder
from tests.demo.iter9_visual_solver.builders.metrics_builder import MetricsBuilder
from tests.demo.iter9_visual_solver.fixtures.temp_runs import make_temp_iter9_run_dir


class CliCommandsTests(unittest.TestCase):
    def test_cli_command_module_exposes_main(self):
        try:
            from demos.iter9_visual_solver.cli import commands
        except ModuleNotFoundError:
            self.skipTest("commands module is not implemented yet")
        self.assertTrue(callable(commands.main))

    def test_cli_passes_configured_playback_and_status_to_loop(self):
        from demos.iter9_visual_solver.cli import commands
        from demos.iter9_visual_solver.rendering.pygame_loop import PygameLoopResult

        config = DemoConfigBuilder().with_base_events_per_second(120).with_mine_count_multiplier(0).build_dict()
        config["playback"]["target_fps"] = 60
        config["window"]["finish_behavior"]["mode"] = "close_immediately"
        grid = GridBuilder(height=2, width=3).with_mines([(0, 0), (1, 2)]).build()
        metrics = MetricsBuilder().with_board("3x2").with_seed(13).with_source_image("demo_source.png").build_dict()
        with make_temp_iter9_run_dir() as run:
            grid_path = run.write_grid_artifact(grid)
            metrics_path = run.write_metrics_artifact(metrics, name="metrics_iter9_3x2.json")
            config_path = run.write_demo_config(config)
            with mock.patch.object(
                commands,
                "run_pygame_loop",
                return_value=PygameLoopResult(
                    exit_reason="playback_finished_close_immediately",
                    playback_finished=True,
                    frames_rendered=1,
                    events_applied=6,
                    elapsed_time_s=0.016,
                ),
            ) as loop:
                code = commands.main([
                    "--grid",
                    str(grid_path),
                    "--metrics",
                    str(metrics_path),
                    "--config",
                    str(config_path),
                ])
        self.assertEqual(code, 0)
        loop.assert_called_once()
        kwargs = loop.call_args.kwargs
        self.assertEqual(kwargs["events_per_second"], 120)
        self.assertEqual(kwargs["events_per_frame"], 2)
        self.assertEqual(kwargs["board_width"], 3)
        self.assertEqual(kwargs["board_height"], 2)
        self.assertEqual(kwargs["source_image_name"], "demo_source.png")
        self.assertEqual(kwargs["seed"], 13)
        self.assertEqual(kwargs["replay_source"], "final_grid_replay")
        self.assertEqual(kwargs["finish_config"].mode, "close_immediately")


if __name__ == "__main__":
    unittest.main()
