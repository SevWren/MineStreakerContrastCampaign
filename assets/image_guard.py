"""
Mandatory pre-flight image integrity checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

DEFAULT_IMG_PATH = "assets/input_source_image.png"
DEFAULT_MANIFEST_PATH = "assets/SOURCE_IMAGE_HASH.json"
ALLOW_NONCANONICAL_ENV = "MINESTREAKER_ALLOW_NONCANONICAL"

_MEAN_TOL = 0.01
_STD_TOL = 0.01


def _warning(code: str, message: str, severity: str = "warning") -> dict:
    return {"code": code, "severity": severity, "message": message}


def _path_posix(value: str | Path) -> str:
    return Path(value).resolve().as_posix()


def _env_flag_enabled(name: str) -> bool:
    value = os.getenv(name, "").strip().lower()
    return value in {"1", "true", "yes", "on"}


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_manifest(record: dict) -> dict:
    if "file" in record and "pixels" in record:
        file_rec = record.get("file", {})
        pixels_rec = record.get("pixels", {})
        size = file_rec.get("size_bytes")
        sha = file_rec.get("sha256")
        psha = pixels_rec.get("sha256")
        shape = pixels_rec.get("shape")
        dtype = pixels_rec.get("dtype")
        pmean = pixels_rec.get("mean")
        pstd = pixels_rec.get("std")
        pmin = pixels_rec.get("min")
        pmax = pixels_rec.get("max")
    else:
        size = record.get("file_size")
        sha = record.get("file_sha256")
        psha = record.get("pixel_sha256")
        shape = record.get("pixel_shape")
        dtype = record.get("pixel_dtype")
        pmean = record.get("pixel_mean")
        pstd = record.get("pixel_std")
        pmin = record.get("pixel_min")
        pmax = record.get("pixel_max")

    if shape is not None:
        shape = list(shape)

    normalized = {
        "file_size": int(size),
        "file_sha256": str(sha).lower(),
        "pixel_sha256": str(psha).lower(),
        "pixel_shape": shape,
        "pixel_dtype": str(dtype),
        "pixel_mean": float(pmean),
        "pixel_std": float(pstd),
        "pixel_min": int(pmin),
        "pixel_max": int(pmax),
    }
    return normalized


def _compute_stats(path: Path) -> dict:
    raw = path.read_bytes()
    arr = np.array(Image.open(path), dtype=np.uint8)
    return {
        "file_size": int(len(raw)),
        "file_sha256": hashlib.sha256(raw).hexdigest().lower(),
        "pixel_sha256": hashlib.sha256(arr.tobytes()).hexdigest().lower(),
        "pixel_shape": [int(v) for v in arr.shape],
        "pixel_dtype": str(arr.dtype),
        "pixel_mean": float(arr.mean()),
        "pixel_std": float(arr.std()),
        "pixel_min": int(arr.min()),
        "pixel_max": int(arr.max()),
    }


def _compare_expected(computed: dict, expected: dict) -> list[str]:
    failures = []
    if computed["file_size"] != expected["file_size"]:
        failures.append(
            f"File size mismatch: expected {expected['file_size']}, got {computed['file_size']}"
        )
    if computed["file_sha256"] != expected["file_sha256"]:
        failures.append(
            f"File SHA256 mismatch: expected {expected['file_sha256']}, got {computed['file_sha256']}"
        )
    if computed["pixel_sha256"] != expected["pixel_sha256"]:
        failures.append(
            f"Pixel SHA256 mismatch: expected {expected['pixel_sha256']}, got {computed['pixel_sha256']}"
        )
    if computed["pixel_shape"] != expected["pixel_shape"]:
        failures.append(
            f"Pixel shape mismatch: expected {expected['pixel_shape']}, got {computed['pixel_shape']}"
        )
    if computed["pixel_dtype"] != expected["pixel_dtype"]:
        failures.append(
            f"Pixel dtype mismatch: expected {expected['pixel_dtype']}, got {computed['pixel_dtype']}"
        )
    if abs(computed["pixel_mean"] - expected["pixel_mean"]) > _MEAN_TOL:
        failures.append(
            f"Pixel mean mismatch: expected {expected['pixel_mean']}, got {computed['pixel_mean']}"
        )
    if abs(computed["pixel_std"] - expected["pixel_std"]) > _STD_TOL:
        failures.append(
            f"Pixel std mismatch: expected {expected['pixel_std']}, got {computed['pixel_std']}"
        )
    if computed["pixel_min"] != expected["pixel_min"]:
        failures.append(
            f"Pixel min mismatch: expected {expected['pixel_min']}, got {computed['pixel_min']}"
        )
    if computed["pixel_max"] != expected["pixel_max"]:
        failures.append(
            f"Pixel max mismatch: expected {expected['pixel_max']}, got {computed['pixel_max']}"
        )
    return failures


def _print_header(path: str) -> None:
    print("=" * 60)
    print("IMAGE INTEGRITY VERIFICATION")
    print("=" * 60)
    print(f"  Checking: {path}\n")


def _details_template(
    *,
    path: str,
    absolute_path: str,
    manifest_path: str | None,
    canonical_match: bool | None,
    noncanonical_allowed: bool,
    validation_mode: str,
    warnings: list[dict],
    computed: dict,
    expected: dict | None,
    ok: bool,
) -> dict:
    return {
        "ok": bool(ok),
        "path": path,
        "absolute_path": absolute_path,
        "manifest_path": manifest_path,
        "canonical_match": canonical_match,
        "noncanonical_allowed": bool(noncanonical_allowed),
        "validation_mode": validation_mode,
        "warnings": warnings,
        "computed": computed,
        "expected": expected,
    }


def verify_source_image(
    path: str = DEFAULT_IMG_PATH,
    halt_on_failure: bool = True,
    verbose: bool = True,
    allow_noncanonical: bool | None = None,
    manifest_path: str | None = None,
    return_details: bool = False,
):
    resolved_path = Path(path).expanduser().resolve()
    if allow_noncanonical is None:
        allow_noncanonical_flag = _env_flag_enabled(ALLOW_NONCANONICAL_ENV)
    else:
        allow_noncanonical_flag = bool(allow_noncanonical)

    warnings: list[dict] = []
    failures: list[str] = []
    validation_mode: str
    expected: dict | None = None
    canonical_match: bool | None = None
    used_manifest_path: str | None = None

    if verbose:
        _print_header(path)

    if not resolved_path.exists():
        failures.append(f"File not found: {path}")
        details = _details_template(
            path=path,
            absolute_path=resolved_path.as_posix(),
            manifest_path=None,
            canonical_match=None,
            noncanonical_allowed=allow_noncanonical_flag,
            validation_mode="noncanonical_allowed",
            warnings=warnings,
            computed={},
            expected=None,
            ok=False,
        )
        if verbose:
            print(f"  X FAIL: {failures[-1]}")
            print("\n  IMAGE VERIFICATION FAILED - 1 check(s) failed\n")
        if halt_on_failure:
            sys.exit(1)
        return details if return_details else False

    if not resolved_path.is_file():
        failures.append(f"Path is not a file: {path}")
        details = _details_template(
            path=path,
            absolute_path=resolved_path.as_posix(),
            manifest_path=None,
            canonical_match=None,
            noncanonical_allowed=allow_noncanonical_flag,
            validation_mode="noncanonical_allowed",
            warnings=warnings,
            computed={},
            expected=None,
            ok=False,
        )
        if verbose:
            print(f"  X FAIL: {failures[-1]}")
            print("\n  IMAGE VERIFICATION FAILED - 1 check(s) failed\n")
        if halt_on_failure:
            sys.exit(1)
        return details if return_details else False

    computed = _compute_stats(resolved_path)
    if verbose:
        print(f"  OK File size: {computed['file_size']:,} bytes")
        print(f"  OK Pixel dtype: {computed['pixel_dtype']}")
        print(f"  OK Pixel shape: {tuple(computed['pixel_shape'])}")

    default_image_path = Path(DEFAULT_IMG_PATH).resolve()
    explicit_manifest = Path(manifest_path).expanduser().resolve() if manifest_path else None

    if explicit_manifest is not None:
        validation_mode = "explicit_manifest"
        used_manifest_path = explicit_manifest.as_posix()
        manifest_raw = _load_json(explicit_manifest)
        expected = _normalize_manifest(manifest_raw)
    elif resolved_path == default_image_path:
        validation_mode = "default_manifest"
        default_manifest = Path(DEFAULT_MANIFEST_PATH).resolve()
        used_manifest_path = default_manifest.as_posix()
        warnings.append(
            _warning(
                "DEFAULT_MANIFEST_USED",
                f"Using default manifest at {used_manifest_path} for default image validation.",
                "info",
            )
        )
        manifest_raw = _load_json(default_manifest)
        expected = _normalize_manifest(manifest_raw)
    else:
        warnings.append(
            _warning(
                "MANIFEST_NOT_SUPPLIED",
                "No manifest supplied for non-default image.",
                "warning",
            )
        )
        if allow_noncanonical_flag:
            validation_mode = "noncanonical_allowed"
            warnings.append(
                _warning(
                    "NONCANONICAL_SOURCE_ALLOWED",
                    "Source image allowed without manifest validation.",
                    "warning",
                )
            )
        else:
            validation_mode = "noncanonical_allowed"
            failures.append(
                "Manifest not supplied for non-default image. Provide --manifest or enable --allow-noncanonical."
            )

    if expected is not None:
        failures.extend(_compare_expected(computed, expected))
        canonical_match = len(failures) == 0
    else:
        canonical_match = None

    ok = len(failures) == 0
    details = _details_template(
        path=path,
        absolute_path=resolved_path.as_posix(),
        manifest_path=used_manifest_path,
        canonical_match=canonical_match,
        noncanonical_allowed=allow_noncanonical_flag,
        validation_mode=validation_mode,
        warnings=warnings,
        computed=computed,
        expected=expected,
        ok=ok,
    )

    if verbose:
        for entry in warnings:
            label = entry["severity"].upper()
            print(f"  {label} {entry['code']}: {entry['message']}")
        if ok:
            print("\n  ALL CHECKS PASSED - source image is verified authentic")
            print("=" * 60 + "\n")
        else:
            for message in failures:
                print(f"  X FAIL: {message}")
            print(f"\n  IMAGE VERIFICATION FAILED - {len(failures)} check(s) failed\n")

    if not ok and halt_on_failure:
        sys.exit(1)
    if return_details:
        return details
    return ok


def get_canonical_record() -> dict:
    manifest = Path(DEFAULT_MANIFEST_PATH).resolve()
    return _normalize_manifest(_load_json(manifest))


def compute_image_hashes(path: str):
    resolved = Path(path).expanduser().resolve()
    raw = resolved.read_bytes()
    arr = np.array(Image.open(resolved), dtype=np.uint8)
    return {
        "path": resolved.as_posix(),
        "file_size": int(len(raw)),
        "file_md5": hashlib.md5(raw).hexdigest(),
        "file_sha256": hashlib.sha256(raw).hexdigest(),
        "pixel_sha256": hashlib.sha256(arr.tobytes()).hexdigest(),
        "pixel_shape": [int(v) for v in arr.shape],
        "pixel_dtype": str(arr.dtype),
        "pixel_mean": float(arr.mean()),
        "pixel_std": float(arr.std()),
        "pixel_min": int(arr.min()),
        "pixel_max": int(arr.max()),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Image integrity validation.")
    parser.add_argument("--path", default=DEFAULT_IMG_PATH)
    parser.add_argument("--compute", action="store_true")
    parser.add_argument("--allow-noncanonical", action="store_true")
    parser.add_argument("--manifest", default=None)
    args = parser.parse_args()

    if args.compute:
        print(json.dumps(compute_image_hashes(args.path), indent=2))
        raise SystemExit(0)

    result = verify_source_image(
        args.path,
        halt_on_failure=True,
        allow_noncanonical=args.allow_noncanonical,
        manifest_path=args.manifest,
    )
    raise SystemExit(0 if result else 1)
