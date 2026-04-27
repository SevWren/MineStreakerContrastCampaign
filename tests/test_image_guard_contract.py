import json
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from assets.image_guard import (
    DEFAULT_IMG_PATH,
    compute_image_hashes,
    verify_source_image,
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


class ImageGuardContractTests(unittest.TestCase):
    def test_default_manifest_success_and_details_schema(self):
        details = verify_source_image(
            DEFAULT_IMG_PATH,
            halt_on_failure=False,
            verbose=False,
            return_details=True,
        )
        self.assertTrue(details["ok"])
        self.assertEqual(details["validation_mode"], "default_manifest")
        expected_keys = {
            "ok",
            "path",
            "absolute_path",
            "manifest_path",
            "canonical_match",
            "noncanonical_allowed",
            "validation_mode",
            "warnings",
            "computed",
            "expected",
        }
        self.assertEqual(set(details.keys()), expected_keys)
        self.assertTrue(any(w["code"] == "DEFAULT_MANIFEST_USED" for w in details["warnings"]))

    def test_explicit_flat_manifest_success(self):
        image_path = "assets/line_art_irl_11_v2.png"
        hashes = compute_image_hashes(image_path)
        manifest = {
            "file_size": hashes["file_size"],
            "file_sha256": hashes["file_sha256"],
            "pixel_sha256": hashes["pixel_sha256"],
            "pixel_shape": hashes["pixel_shape"],
            "pixel_dtype": hashes["pixel_dtype"],
            "pixel_mean": hashes["pixel_mean"],
            "pixel_std": hashes["pixel_std"],
            "pixel_min": hashes["pixel_min"],
            "pixel_max": hashes["pixel_max"],
        }
        with tempfile.TemporaryDirectory() as td:
            manifest_path = Path(td) / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            details = verify_source_image(
                image_path,
                halt_on_failure=False,
                verbose=False,
                manifest_path=str(manifest_path),
                return_details=True,
            )
        self.assertTrue(details["ok"])
        self.assertEqual(details["validation_mode"], "explicit_manifest")
        self.assertTrue(details["canonical_match"])

    def test_custom_image_fails_without_manifest_or_noncanonical(self):
        details = verify_source_image(
            "assets/line_art_irl_11_v2.png",
            halt_on_failure=False,
            verbose=False,
            allow_noncanonical=False,
            return_details=True,
        )
        self.assertFalse(details["ok"])
        self.assertEqual(details["validation_mode"], "noncanonical_allowed")
        self.assertIsNone(details["expected"])
        codes = [w["code"] for w in details["warnings"]]
        self.assertIn("MANIFEST_NOT_SUPPLIED", codes)

    def test_noncanonical_warning_records_are_structured(self):
        details = verify_source_image(
            "assets/line_art_irl_11_v2.png",
            halt_on_failure=False,
            verbose=False,
            allow_noncanonical=True,
            return_details=True,
        )
        self.assertTrue(details["ok"])
        self.assertEqual(details["validation_mode"], "noncanonical_allowed")
        codes = [w["code"] for w in details["warnings"]]
        self.assertIn("MANIFEST_NOT_SUPPLIED", codes)
        self.assertIn("NONCANONICAL_SOURCE_ALLOWED", codes)
        for warning in details["warnings"]:
            self.assertEqual(set(warning.keys()), {"code", "severity", "message"})

    def test_mismatch_failure_with_explicit_manifest(self):
        image_path = str((PROJECT_ROOT / DEFAULT_IMG_PATH).resolve())
        hashes = compute_image_hashes(image_path)
        bad_manifest = {
            "file_size": hashes["file_size"],
            "file_sha256": "0" * 64,
            "pixel_sha256": hashes["pixel_sha256"],
            "pixel_shape": hashes["pixel_shape"],
            "pixel_dtype": hashes["pixel_dtype"],
            "pixel_mean": hashes["pixel_mean"],
            "pixel_std": hashes["pixel_std"],
            "pixel_min": hashes["pixel_min"],
            "pixel_max": hashes["pixel_max"],
        }
        with tempfile.TemporaryDirectory() as td:
            manifest_path = Path(td) / "bad_manifest.json"
            manifest_path.write_text(json.dumps(bad_manifest), encoding="utf-8")
            details = verify_source_image(
                image_path,
                halt_on_failure=False,
                verbose=False,
                manifest_path=str(manifest_path),
                return_details=True,
            )
        self.assertFalse(details["ok"])
        self.assertEqual(details["validation_mode"], "explicit_manifest")
        self.assertFalse(details["canonical_match"])

    def test_default_image_and_manifest_are_repo_root_stable_outside_cwd(self):
        with tempfile.TemporaryDirectory() as td:
            with _pushd(Path(td)):
                details = verify_source_image(
                    DEFAULT_IMG_PATH,
                    halt_on_failure=False,
                    verbose=False,
                    return_details=True,
                )
        self.assertTrue(details["ok"])
        self.assertEqual(details["validation_mode"], "default_manifest")
        self.assertTrue(str(details["manifest_path"]).endswith("/assets/SOURCE_IMAGE_HASH.json"))


if __name__ == "__main__":
    unittest.main()
