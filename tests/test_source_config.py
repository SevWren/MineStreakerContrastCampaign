import hashlib
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from source_config import (
    compute_file_sha256,
    project_relative_or_none,
    resolve_source_image_config,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def _pushd(path: Path):
    prior = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prior)


class SourceConfigTests(unittest.TestCase):
    def test_resolve_inside_project_and_metrics_paths(self):
        cfg = resolve_source_image_config(
            "assets/input_source_image.png",
            project_root=PROJECT_ROOT,
            allow_noncanonical=False,
            manifest_path="assets/SOURCE_IMAGE_HASH.json",
        )
        self.assertEqual(cfg.command_arg, "assets/input_source_image.png", msg="command_arg should match the input path")
        self.assertEqual(cfg.project_relative_path, "assets/input_source_image.png", msg="project_relative_path should be the relative path from project root")
        self.assertEqual(cfg.name, "input_source_image.png", msg="name should be the filename with extension")
        self.assertEqual(cfg.stem, "input_source_image", msg="stem should be the filename without extension")
        self.assertGreater(cfg.size_bytes, 0, msg="size_bytes should be > 0 for a real file")
        metrics = cfg.to_metrics_dict()
        self.assertEqual(metrics["project_relative_path"], "assets/input_source_image.png", msg="metrics project_relative_path should match")
        self.assertIn("/", metrics["absolute_path"], msg="absolute_path should use forward slashes")
        self.assertNotIn("\\", metrics["absolute_path"], msg="absolute_path must not contain backslashes")

    def test_compute_sha256_and_size_for_temp_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.bin"
            payload = b"source-config-test"
            path.write_bytes(payload)
            self.assertEqual(compute_file_sha256(path), hashlib.sha256(payload).hexdigest(), msg="sha256 should match hashlib computation")
            cfg = resolve_source_image_config(str(path), project_root=PROJECT_ROOT)
            self.assertEqual(cfg.size_bytes, len(payload), msg="size_bytes should equal len(payload)")

    def test_out_of_repo_project_relative_is_none(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "outside.txt"
            path.write_text("outside", encoding="utf-8")
            cfg = resolve_source_image_config(str(path), project_root=PROJECT_ROOT)
            self.assertIsNone(cfg.project_relative_path, msg="project_relative_path should be None for a file outside the project root")
            rel = project_relative_or_none(path, PROJECT_ROOT)
            self.assertIsNone(rel, msg="project_relative_or_none should return None for paths outside the project root")

    def test_relative_image_path_uses_project_root_when_supplied(self):
        with tempfile.TemporaryDirectory() as td:
            with _pushd(Path(td)):
                cfg = resolve_source_image_config(
                    "assets/input_source_image.png",
                    project_root=PROJECT_ROOT,
                )
        self.assertEqual(cfg.project_relative_path, "assets/input_source_image.png", msg="project_relative_path should be resolved relative to project_root even when cwd differs")
        self.assertEqual(cfg.absolute_path, (PROJECT_ROOT / "assets/input_source_image.png").resolve(), msg="absolute_path should resolve relative to project_root")

    def test_manifest_path_uses_project_root_when_supplied(self):
        with tempfile.TemporaryDirectory() as td:
            with _pushd(Path(td)):
                cfg = resolve_source_image_config(
                    "assets/input_source_image.png",
                    project_root=PROJECT_ROOT,
                    manifest_path="assets/SOURCE_IMAGE_HASH.json",
                )
        self.assertEqual(
            cfg.manifest_path,
            (PROJECT_ROOT / "assets/SOURCE_IMAGE_HASH.json").resolve().as_posix(),
            msg="manifest_path should be resolved relative to project_root even when cwd differs",
        )


if __name__ == "__main__":
    unittest.main()
