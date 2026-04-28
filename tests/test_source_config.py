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
        self.assertEqual(cfg.command_arg, "assets/input_source_image.png")
        self.assertEqual(cfg.project_relative_path, "assets/input_source_image.png")
        self.assertEqual(cfg.name, "input_source_image.png")
        self.assertEqual(cfg.stem, "input_source_image")
        self.assertGreater(cfg.size_bytes, 0)
        metrics = cfg.to_metrics_dict()
        self.assertEqual(metrics["project_relative_path"], "assets/input_source_image.png")
        self.assertIn("/", metrics["absolute_path"])
        self.assertNotIn("\\", metrics["absolute_path"])

    def test_compute_sha256_and_size_for_temp_file(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sample.bin"
            payload = b"source-config-test"
            path.write_bytes(payload)
            self.assertEqual(compute_file_sha256(path), hashlib.sha256(payload).hexdigest())
            cfg = resolve_source_image_config(str(path), project_root=PROJECT_ROOT)
            self.assertEqual(cfg.size_bytes, len(payload))

    def test_out_of_repo_project_relative_is_none(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "outside.txt"
            path.write_text("outside", encoding="utf-8")
            cfg = resolve_source_image_config(str(path), project_root=PROJECT_ROOT)
            self.assertIsNone(cfg.project_relative_path)
            rel = project_relative_or_none(path, PROJECT_ROOT)
            self.assertIsNone(rel)

    def test_relative_image_path_uses_project_root_when_supplied(self):
        with tempfile.TemporaryDirectory() as td:
            with _pushd(Path(td)):
                cfg = resolve_source_image_config(
                    "assets/input_source_image.png",
                    project_root=PROJECT_ROOT,
                )
        self.assertEqual(cfg.project_relative_path, "assets/input_source_image.png")
        self.assertEqual(cfg.absolute_path, (PROJECT_ROOT / "assets/input_source_image.png").resolve())

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
        )


if __name__ == "__main__":
    unittest.main()
