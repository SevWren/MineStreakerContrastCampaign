"""Tests for prompted demo launcher wrapper."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

from tests.demo.iter9_visual_solver.builders.config_builder import DemoConfigBuilder
from tests.demo.iter9_visual_solver.builders.grid_builder import GridBuilder
from tests.demo.iter9_visual_solver.builders.metrics_builder import MetricsBuilder
from tests.demo.iter9_visual_solver.fixtures.temp_runs import make_temp_iter9_run_dir


class PromptedLauncherTests(unittest.TestCase):
    def test_parse_speed_modifier_accepts_x_suffix(self):
        from demos.iter9_visual_solver.cli.prompted_launcher import parse_speed_modifier

        self.assertEqual(parse_speed_modifier("50x"), 50)
        self.assertEqual(parse_speed_modifier(" 300X "), 300)
        self.assertEqual(parse_speed_modifier("200"), 200)

    def test_build_prompted_config_scales_speed_and_sets_auto_close(self):
        from demos.iter9_visual_solver.cli.prompted_launcher import build_prompted_config_dict

        config = DemoConfigBuilder().build_dict()
        prompted = build_prompted_config_dict(config, speed_modifier=50, auto_close=True)
        self.assertEqual(prompted["playback"]["min_events_per_second"], 2500)
        self.assertEqual(prompted["playback"]["base_events_per_second"], 50000)
        self.assertEqual(prompted["playback"]["max_events_per_second"], 600000)
        self.assertEqual(prompted["playback"]["mine_count_multiplier"], 4.0)
        self.assertEqual(prompted["window"]["finish_behavior"]["mode"], "close_immediately")
        self.assertIsNone(prompted["window"]["finish_behavior"]["close_after_seconds"])

    def test_build_demo_argv_uses_resolved_run_artifacts(self):
        from demos.iter9_visual_solver.cli.prompted_launcher import build_demo_argv
        from demos.iter9_visual_solver.io.artifact_paths import resolve_artifact_paths

        with make_temp_iter9_run_dir() as run:
            grid_path = run.write_grid_artifact(GridBuilder(height=2, width=3).build())
            metrics_path = run.write_metrics_artifact(
                MetricsBuilder().with_board("3x2").build_dict(),
                name="metrics_iter9_3x2.json",
            )
            trace_path = run.write_event_trace_artifact("")
            config_path = Path("temp/demo.json")
            artifacts = resolve_artifact_paths(run.path)
            argv = build_demo_argv(artifacts=artifacts, config_path=config_path)

        self.assertEqual(argv[:6], ["--grid", str(grid_path), "--metrics", str(metrics_path), "--config", str(config_path)])
        self.assertEqual(argv[6:], ["--event-trace", str(trace_path)])

    def test_prompted_main_writes_temp_config_and_delegates_to_demo_cli(self):
        from demos.iter9_visual_solver.cli import prompted_launcher

        with make_temp_iter9_run_dir() as run, TemporaryDirectory() as tmp:
            run.write_grid_artifact(GridBuilder(height=2, width=3).build())
            run.write_metrics_artifact(
                MetricsBuilder().with_board("3x2").build_dict(),
                name="metrics_iter9_3x2.json",
            )
            default_config_path = run.write_demo_config(DemoConfigBuilder().build_dict())
            answers = iter([str(run.path), "100x", "Y"])
            with mock.patch.object(prompted_launcher, "commands_main", return_value=0) as demo_main:
                code = prompted_launcher.prompted_main(
                    input_func=lambda _prompt: next(answers),
                    print_func=lambda *_args, **_kwargs: None,
                    default_config_path=default_config_path,
                    temp_config_root=Path(tmp),
                )
            self.assertEqual(code, 0)
            demo_main.assert_called_once()
            argv = demo_main.call_args.args[0]
            generated_config = Path(argv[argv.index("--config") + 1])
            data = json.loads(generated_config.read_text(encoding="utf-8"))
            self.assertEqual(data["window"]["finish_behavior"]["mode"], "close_immediately")
            self.assertEqual(data["playback"]["base_events_per_second"], 100000)


if __name__ == "__main__":
    unittest.main()
