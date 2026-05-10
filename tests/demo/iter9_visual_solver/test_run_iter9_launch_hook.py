"""Tests for optional run_iter9 demo hook contract."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


class RunIter9LaunchHookTests(unittest.TestCase):
    def test_launch_hook_module_exists_before_run_iter9_integration(self):
        try:
            from demos.iter9_visual_solver.cli.launch_from_iter9 import run_demo_from_completed_iter9_run
        except ModuleNotFoundError:
            self.skipTest("run_demo_from_completed_iter9_run is not implemented yet")
        self.assertTrue(callable(run_demo_from_completed_iter9_run))

    def test_run_iter9_accepts_optional_demo_flags(self):
        import run_iter9

        args = run_iter9.parse_args(["--demo-gui", "--demo-config", "configs/demo/iter9_visual_solver_demo.default.json"])
        self.assertTrue(args.demo_gui)
        self.assertEqual(args.demo_config, "configs/demo/iter9_visual_solver_demo.default.json")

    def test_run_iter9_demo_gui_delegates_after_successful_run(self):
        import run_iter9
        from source_config import SourceImageConfig

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            image_path = tmp_path / "source.png"
            image_path.write_bytes(b"fake")
            out_dir = tmp_path / "out"
            source_cfg = SourceImageConfig(
                command_arg=image_path.as_posix(),
                absolute_path=image_path.resolve(),
                project_relative_path=None,
                name=image_path.name,
                stem=image_path.stem,
                sha256="a" * 64,
                size_bytes=image_path.stat().st_size,
                allow_noncanonical=True,
                manifest_path=None,
            )
            with (
                mock.patch.object(run_iter9, "resolve_source_image_config", return_value=source_cfg),
                mock.patch.object(run_iter9, "verify_source_image", return_value={"ok": True}),
                mock.patch.object(run_iter9, "compile_sa_kernel", return_value=object()),
                mock.patch.object(run_iter9, "ensure_solver_warmed", return_value=None),
                mock.patch.object(run_iter9, "run_iter9_single", return_value={"board": "8x5"}),
                mock.patch(
                    "demos.iter9_visual_solver.cli.launch_from_iter9.run_demo_from_completed_iter9_run",
                    return_value=0,
                ) as launch,
            ):
                code = run_iter9.main([
                    "--image",
                    image_path.as_posix(),
                    "--out-dir",
                    out_dir.as_posix(),
                    "--demo-gui",
                    "--demo-config",
                    "configs/demo/iter9_visual_solver_demo.default.json",
                ])
            self.assertEqual(code, 0)
            launch.assert_called_once()
            kwargs = launch.call_args.kwargs
            self.assertEqual(kwargs["grid_path"], out_dir.resolve() / "grid_iter9_latest.npy", msg="grid_path must point to the latest grid artifact in out_dir")
            self.assertEqual(kwargs["metrics_path"], out_dir.resolve() / "metrics_iter9_8x5.json", msg="metrics_path must be named using the board label from the run result")
            self.assertEqual(
                kwargs["config_path"],
                (Path(run_iter9.__file__).resolve().parent / "configs/demo/iter9_visual_solver_demo.default.json").resolve(),
                msg="config_path must be resolved relative to the run_iter9 module location",
            )
            self.assertIsNone(kwargs["event_trace_path"], msg="event_trace_path must be None when no event trace was written")


if __name__ == "__main__":
    unittest.main()
